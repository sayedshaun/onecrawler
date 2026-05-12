import asyncio
import gzip
import logging
import re
import time
import warnings
from typing import Optional, Set, Tuple
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import aiohttp
from curl_cffi.requests import AsyncSession
from lxml import etree

from ...proxy.pool import ProxyPool
from ...settings.crawler import CrawlerSettings
from ..link.helper import wildcard_link_match
from .helper import (
    COMMON_SITEMAP_PATHS,
    URLRecord,
    is_same_origin,
    is_xml_url,
    normalize_url,
)


class SitemapStats:
    def __init__(self):
        self.start_time = time.time()
        self.urls = 0
        self.sitemaps = 0
        self.errors = 0

    def elapsed(self):
        return time.time() - self.start_time

    def rate(self):
        e = self.elapsed()
        return self.urls / e if e > 0 else 0


class SiteMap:
    def __init__(self, settings: CrawlerSettings):

        self.semaphore = asyncio.Semaphore(settings.concurrency)
        self.visited_sitemaps: Set[str] = set()
        self.urls: Set[str] = set()
        self.stats = SitemapStats()
        self.timeout = settings.browser_settings.runtime.timeout
        self.filter_pattern = settings.include_link_patterns
        self.base_prefix = ""

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return False

    def _sitemap_url(self, url: str) -> str:
        return (
            url.rstrip("/") + "/sitemap.xml" if not url.endswith("sitemap.xml") else url
        )

    async def _fetch(self, session, url):
        try:
            async with self.semaphore:
                async with session.get(url, timeout=self.timeout) as r:
                    if r.status == 200:
                        return await r.read()
        except Exception:
            self.stats.errors += 1
        return None

    async def _parse(self, session, sitemap_url):
        if sitemap_url in self.visited_sitemaps:
            return

        self.visited_sitemaps.add(sitemap_url)
        self.stats.sitemaps += 1

        data = await self._fetch(session, sitemap_url)
        if not data:
            return

        try:
            root = etree.fromstring(data)
        except Exception:
            self.stats.errors += 1
            return

        tag = root.tag.lower()

        if "sitemapindex" in tag:
            tasks = []
            for sm in root:
                loc = sm.find(".//{*}loc")
                if loc is not None and loc.text:
                    tasks.append(self._parse(session, loc.text.strip()))
            await asyncio.gather(*tasks)

        elif "urlset" in tag:
            for u in root:
                loc = u.find(".//{*}loc")
                if loc is None or not loc.text:
                    continue

                url = loc.text.strip()

                if self.filter_pattern:
                    if not wildcard_link_match(
                        url, self.base_prefix, self.filter_pattern
                    ):
                        continue

                if url not in self.urls:
                    self.urls.add(url)
                    self.stats.urls += 1

    async def fetch(self, url: str) -> Tuple[Set[str], SitemapStats]:
        self.sitemap_url = self._sitemap_url(url)
        parsed = urlparse(url)
        self.base_prefix = f"{parsed.scheme}://{parsed.netloc}"
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            await self._parse(session, self.sitemap_url)
        return list(self.urls), self.stats

    async def run(self, url: str):
        urls, stats = await self.fetch(url)
        return urls


class HTTPClient:
    def __init__(
        self,
        concurrency: int,
        timeout: int,
        user_agent: str,
        retries: int,
        retry_delay: int,
        proxy_pool: Optional[ProxyPool] = None,
    ):
        self.concurrency = concurrency
        self.timeout = timeout
        self.user_agent = user_agent
        self.max_retries = retries
        self.retry_delay = retry_delay
        self.proxy_pool = proxy_pool or ProxyPool()
        self._session: Optional[AsyncSession] = None
        self._semaphore = asyncio.Semaphore(concurrency)

    async def __aenter__(self):
        self._session = AsyncSession(
            impersonate="chrome136",  # impersonate latest Chrome TLS fingerprint
            timeout=self.timeout,
        )
        return self

    async def __aexit__(self, *_):
        if self._session:
            await self._session.close()

    async def get(self, url: str) -> Optional[bytes]:
        """Fetch raw bytes with retry logic. Returns None on failure."""
        for attempt in range(1, self.max_retries + 1):
            try:
                proxy = self.proxy_pool.next()
                request_kwargs = {
                    "allow_redirects": True,
                    "max_redirects": 10,
                }
                if proxy:
                    request_kwargs["proxies"] = proxy.as_requests_proxies()

                async with self._semaphore:
                    resp = await self._session.get(url, **request_kwargs)

                if resp.status_code == 200:
                    data = resp.content
                    # Handle gzip-compressed sitemaps
                    if (
                        url.endswith(".gz")
                        or resp.headers.get("Content-Encoding") == "gzip"
                    ):
                        try:
                            data = gzip.decompress(data)
                        except Exception:
                            pass
                    return data

                elif resp.status_code == 404:
                    return None

                elif resp.status_code in (403, 429):
                    warnings.warn(
                        f"HTTP {resp.status_code} for {url} (attempt {attempt}) — "
                        f"Cf-Mitigated: {resp.headers.get('Cf-Mitigated', 'none')}"
                    )

            except asyncio.TimeoutError:
                warnings.warn(f"Timeout for {url} (attempt {attempt})")
            except Exception as e:
                warnings.warn(f"Unexpected error for {url}: {e} (attempt {attempt})")

            if attempt < self.max_retries:
                await asyncio.sleep(self.retry_delay * attempt)

        return None

    async def get_text(self, url: str) -> Optional[str]:
        data = await self.get(url)
        if data is None:
            return None
        for enc in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
            try:
                return data.decode(enc)
            except UnicodeDecodeError:
                continue
        return data.decode("utf-8", errors="replace")


class RobotsParser:
    def __init__(self, client: HTTPClient):
        self.client = client

    async def fetch_sitemaps(self, base_url: str) -> list[str]:
        """Extract Sitemap: directives from robots.txt."""
        robots_url = urljoin(base_url, "/robots.txt")
        text = await self.client.get_text(robots_url)
        if not text:
            return []

        sitemaps = []
        for line in text.splitlines():
            line = line.strip()
            if line.lower().startswith("sitemap:"):
                sm_url = line.split(":", 1)[1].strip()
                if sm_url:
                    sitemaps.append(sm_url)
        return sitemaps

    async def is_allowed(self, url: str, base_url: str) -> bool:
        """Basic robots.txt compliance check."""
        robots_url = urljoin(base_url, "/robots.txt")
        text = await self.client.get_text(robots_url)
        if not text:
            return True
        rp = RobotFileParser()
        rp.set_url(robots_url)
        rp.parse(text.splitlines())
        return rp.can_fetch("*", url)


class SitemapParser:
    def __init__(self, client: HTTPClient, concurrency: int):
        self.client = client
        self._visited_sitemaps: set[str] = set()
        self._semaphore = asyncio.Semaphore(concurrency)

    async def parse_all(
        self, sitemap_urls: list[str]
    ) -> tuple[list[URLRecord], list[str]]:
        """Iteratively parse all sitemaps, following nested .xml/.xml.gz links."""
        all_records: list[URLRecord] = []
        all_sitemaps: list[str] = []

        # Seed the queue
        queue: list[str] = [u for u in sitemap_urls if u not in self._visited_sitemaps]

        while queue:
            # Deduplicate current batch against already-visited
            batch = []
            for url in queue:
                if url not in self._visited_sitemaps:
                    batch.append(url)

            queue = []  # Reset for next wave of children
            if not batch:
                break

            all_sitemaps.extend(batch)

            # Fetch + parse this batch concurrently
            tasks = [self._parse_one(url) for url in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, Exception):
                    continue
                records, child_sitemaps = result
                all_records.extend(records)

                # Only re-queue children that are XML sitemaps and not yet visited
                for child_url in child_sitemaps:
                    if (
                        child_url not in self._visited_sitemaps
                        and self._is_xml_sitemap_url(child_url)
                    ):
                        queue.append(child_url)

        return all_records, all_sitemaps

    @staticmethod
    def _is_xml_sitemap_url(url: str) -> bool:
        """Return True if the URL looks like an XML sitemap (to be traversed, not scraped)."""
        path = urlparse(url).path.lower()
        return path.endswith(".xml") or path.endswith(".xml.gz")

    async def _parse_one(self, url: str) -> tuple[list[URLRecord], list[str]]:
        """Parse a single sitemap URL. Returns (records, child_sitemap_urls)."""
        if url in self._visited_sitemaps:
            return [], []
        self._visited_sitemaps.add(url)

        logging.info(f"[sitemap] Fetching: {url}")  # ← add this line

        async with self._semaphore:
            data = await self.client.get(url)

        if not data:
            logging.warning(f"[sitemap] No data returned for: {url}")  # ← and this
            return [], []

        records, children = self._parse_xml(data, source=url)
        logging.info(
            f"[sitemap] {url} → {len(records)} URLs, {len(children)} child sitemaps"
        )
        return records, children

    def _parse_xml(self, data: bytes, source: str) -> tuple[list[URLRecord], list[str]]:
        """Parse XML bytes → (URLRecord list, child sitemap URLs) using lxml."""
        records: list[URLRecord] = []
        child_sitemaps: list[str] = []

        try:
            parser = etree.XMLParser(recover=True, encoding="utf-8")
            root = etree.fromstring(data, parser=parser)
        except etree.XMLSyntaxError as e:
            logging.warning(f"XML parse error for {source}: {e}")
            return self._regex_extract(data, source), child_sitemaps

        def local(el) -> str:
            t = el.tag or ""
            return t.split("}")[-1].lower() if "}" in t else t.lower()

        tag = (root.tag or "").lower()

        if "sitemapindex" in tag:
            for el in root.iter():
                if local(el) == "sitemap":
                    loc = self._find_text(el, "loc")
                    if loc:
                        child_sitemaps.append(loc.strip())

        elif "urlset" in tag:
            for el in root.iter():
                if local(el) == "url":
                    loc = self._find_text(el, "loc")
                    if loc:
                        records.append(
                            URLRecord(
                                url=loc.strip(),
                                source=source,
                                lastmod=self._find_text(el, "lastmod"),
                                changefreq=self._find_text(el, "changefreq"),
                                priority=self._find_text(el, "priority"),
                            )
                        )

        elif "rss" in tag or "feed" in tag:
            for el in root.iter():
                if local(el) in ("link", "id"):
                    url_text = (el.text or "").strip()
                    if url_text.startswith("http"):
                        records.append(URLRecord(url=url_text, source=source))

        else:
            records = self._regex_extract(data, source)

        return records, child_sitemaps

    @staticmethod
    def _find_text(element, tag: str) -> Optional[str]:
        """Return the text of the first child whose local name matches *tag*."""
        for child in element:
            local = (
                child.tag.split("}")[-1].lower()
                if "}" in child.tag
                else child.tag.lower()
            )
            if local == tag:
                return (child.text or "").strip() or None
        return None

    @staticmethod
    def _regex_extract(data: bytes, source: str) -> list[URLRecord]:
        """Last-resort URL extraction using regex."""
        text = data.decode("utf-8", errors="replace")
        urls = re.findall(r'<loc>\s*(https?://[^\s<>"]+)\s*</loc>', text)
        urls += re.findall(r'href=["\']?(https?://[^\s"\'<>]+)', text)
        return [URLRecord(url=u.strip(), source=source) for u in set(urls)]


class HTMLCrawler:
    def __init__(
        self,
        client: HTTPClient,
        concurrency: int,
        max_crawl_pages: int,
        max_crawl_depth: int,
    ):
        self.client = client
        self.max_crawl_pages = max_crawl_pages
        self.max_crawl_depth = max_crawl_depth
        self._visited: set[str] = set()
        self._semaphore = asyncio.Semaphore(concurrency)

    async def crawl(self, base_url: str) -> list[URLRecord]:
        records: list[URLRecord] = []
        queue = asyncio.Queue()
        await queue.put((base_url, 0))

        while not queue.empty() and len(self._visited) < self.max_crawl_pages:
            url, depth = await queue.get()
            norm = normalize_url(url)
            if norm in self._visited or depth > self.max_crawl_depth:
                continue
            self._visited.add(norm)

            async with self._semaphore:
                text = await self.client.get_text(url)
            if not text:
                continue

            records.append(URLRecord(url=url, source="html_crawl"))
            links = self._extract_links(text, url, base_url)
            for link in links:
                if normalize_url(link) not in self._visited:
                    await queue.put((link, depth + 1))

        return records

    @staticmethod
    def _extract_links(html: str, page_url: str, base_url: str) -> list[str]:
        """Extract all same-origin href links from HTML."""
        links = []
        for match in re.finditer(r'href=["\']([^"\'#\s]+)', html, re.I):
            href = match.group(1).strip()
            if href.startswith("mailto:") or href.startswith("javascript:"):
                continue
            abs_url = urljoin(page_url, href)
            if is_same_origin(abs_url, base_url):
                links.append(abs_url)
        return links


class UniversalSiteMap:
    def __init__(self, settings: CrawlerSettings):
        self.settings = settings

    async def run(self, url: str) -> list[str]:

        base_url = self._normalize_base(url)

        strategies_used: list[str] = []
        all_records: list[URLRecord] = []

        async with HTTPClient(
            self.settings.concurrency,
            self.settings.request_timeout,
            self.settings.sitemap_user_agent,
            self.settings.max_retries,
            self.settings.retry_delay,
            self.settings.create_proxy_pool(),
        ) as client:
            robots = RobotsParser(client)
            sitemap_parser = SitemapParser(client, self.settings.concurrency)

            # STRATEGY 1: robots.txt
            sitemap_urls = await robots.fetch_sitemaps(base_url)
            if sitemap_urls:
                strategies_used.append("robots.txt")

            # STRATEGY 2: Common sitemap paths
            probe_tasks = [
                self._probe_url(client, urljoin(base_url, path))
                for path in COMMON_SITEMAP_PATHS
            ]
            probe_results = await asyncio.gather(*probe_tasks)
            found_common = [
                urljoin(base_url, path)
                for path, ok in zip(COMMON_SITEMAP_PATHS, probe_results)
                if ok
            ]
            new_common = [u for u in found_common if u not in sitemap_urls]
            if new_common:
                strategies_used.append("common_paths")
                sitemap_urls.extend(new_common)

            # STRATEGY 3: Parse all sitemaps
            if sitemap_urls:
                strategies_used.append("sitemap_xml")
                records, _ = await sitemap_parser.parse_all(sitemap_urls)
                all_records.extend(records)

            # STRATEGY 4: HTML crawl fallback
            if not all_records and self.settings.sitemap_html_fallback:
                strategies_used.append("html_crawl")
                crawler = HTMLCrawler(
                    client,
                    self.settings.concurrency,
                    self.settings.max_crawl_pages,
                    self.settings.max_crawl_depth,
                )
                crawl_records = await crawler.crawl(base_url)
                all_records.extend(crawl_records)

        if self.settings.verbose:
            logging.info(f"Strategies used: {strategies_used}")

        # Filter out XML URLs
        all_records = [r for r in all_records if not is_xml_url(r.url)]

        # Section filter (include_patterns)
        if self.settings.include_link_patterns:
            all_records = [
                r
                for r in all_records
                if wildcard_link_match(
                    r.url, base_url, self.settings.include_link_patterns
                )
            ]

        # Deduplication
        if self.settings.sitemap_deduplicate:
            seen: set[str] = set()
            deduped: list[URLRecord] = []
            for rec in all_records:
                norm = normalize_url(rec.url)
                if norm not in seen:
                    seen.add(norm)
                    deduped.append(rec)
            all_records = deduped

        # Cap at max_urls
        if len(all_records) > self.settings.link_extraction_limit:
            all_records = all_records[: self.settings.link_extraction_limit]

        # Return plain list of URL strings
        return [rec.url for rec in all_records]

    @staticmethod
    async def _probe_url(client: HTTPClient, url: str) -> bool:
        """Return True if URL responds with HTTP 200 and non-empty body."""
        data = await client.get(url)
        return data is not None and len(data) > 0

    @staticmethod
    def _normalize_base(url: str) -> str:
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        p = urlparse(url)
        return f"{p.scheme}://{p.netloc}"
