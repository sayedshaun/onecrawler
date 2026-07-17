import asyncio
import logging
import re
import warnings
import zlib
from datetime import date
from typing import Callable, List, Optional, Tuple
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

from curl_cffi.requests import AsyncSession
from lxml import etree

from ...proxy.pool import ProxyPool
from ...settings.crawler import Settings
from ...utils.progress import make_progress_bar
from ..link.helper import wildcard_link_match
from .helper import (
    COMMON_SITEMAP_PATHS,
    URLRecord,
    is_same_origin,
    is_xml_url,
    normalize_url,
)

# Sitemaps are untrusted, potentially attacker-controlled XML — disable entity
# resolution/DTD loading to prevent XXE (local file disclosure via external
# entities), and never allow network access from within a parse.
_SAFE_XML_PARSER_KWARGS = dict(
    resolve_entities=False,
    no_network=True,
    dtd_validation=False,
    load_dtd=False,
    huge_tree=False,
)

# Cap decompressed sitemap size to guard against gzip decompression bombs.
_MAX_SITEMAP_DECOMPRESSED_SIZE = 50 * 1024 * 1024  # 50 MB

# When no post-parse filter can drop records unpredictably (robots.txt,
# date range, include patterns), parse_all() can stop early once it has
# collected this many times the requested limit, instead of always walking
# the full sitemap tree. Covers the modest shrinkage from deduplication and
# the is_xml_url/empty-record filters that always run.
_SITEMAP_LIMIT_OVERFETCH_FACTOR = 3


def _safe_gzip_decompress(
    data: bytes, max_size: int = _MAX_SITEMAP_DECOMPRESSED_SIZE
) -> bytes:
    """Decompresses gzip data, aborting if the output would exceed max_size."""
    decompressor = zlib.decompressobj(zlib.MAX_WBITS | 16)
    output = decompressor.decompress(data, max_size)
    if decompressor.unconsumed_tail:
        raise ValueError(
            f"Decompressed sitemap exceeds the {max_size}-byte safety limit"
        )
    output += decompressor.flush()
    if len(output) > max_size:
        raise ValueError(
            f"Decompressed sitemap exceeds the {max_size}-byte safety limit"
        )
    return output


class HTTPClient:
    """A resilient HTTP client with proxy rotation and impersonation.

    Attributes:
        concurrency (int): Max concurrent requests.
        timeout (int): Request timeout.
        user_agent (str): Request user agent.
        max_retries (int): Max retry attempts.
        retry_delay (int): Delay between retries.
        proxy_pool (ProxyPool): Pool for rotating proxies.
    """

    def __init__(
        self,
        concurrency: int,
        timeout: int,
        user_agent: str,
        retries: int,
        retry_delay: int,
        proxy_pool: Optional[ProxyPool] = None,
    ):
        """Initializes HTTPClient."""
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
        """Fetches raw bytes from a URL with retry and proxy logic.

        Args:
            url (str): The URL to fetch.

        Returns:
            Optional[bytes]: The response content, or None on failure.
        """
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
                    if (
                        url.endswith(".gz")
                        or resp.headers.get("Content-Encoding") == "gzip"
                    ):
                        try:
                            data = _safe_gzip_decompress(data)
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
        """Fetches a URL and decodes the response as text.

        Args:
            url (str): The URL to fetch.

        Returns:
            Optional[str]: The decoded text, or None on failure.
        """
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
    """Parses robots.txt and extracts sitemap directives.

    Attributes:
        client (HTTPClient): The HTTP client to use for fetching.
    """

    def __init__(self, client: HTTPClient):
        """Initializes RobotsParser."""
        self.client = client
        self._parser_cache: dict[str, Optional[RobotFileParser]] = {}
        self._fetch_locks: dict[str, asyncio.Lock] = {}

    async def fetch_sitemaps(self, base_url: str) -> List[str]:
        """Extracts Sitemap: directives from robots.txt.

        Args:
            base_url (str): The base site URL.

        Returns:
            List[str]: A list of sitemap URLs found in robots.txt.
        """
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
                    sitemaps.append(urljoin(base_url, sm_url))
        return sitemaps

    async def is_allowed(self, url: str, base_url: str) -> bool:
        """Checks if a URL is allowed by robots.txt.

        Args:
            url (str): The URL to check.
            base_url (str): The base site URL.

        Returns:
            bool: True if allowed, False otherwise.
        """
        robots_url = urljoin(base_url, "/robots.txt")

        if robots_url not in self._parser_cache:
            # is_allowed() is typically fanned out across many records at
            # once via asyncio.gather. Without this lock, every concurrent
            # caller sees the cache miss before any of them populates it,
            # and each fires its own redundant robots.txt fetch.
            lock = self._fetch_locks.setdefault(robots_url, asyncio.Lock())
            async with lock:
                if robots_url not in self._parser_cache:
                    text = await self.client.get_text(robots_url)
                    if not text:
                        rp = None
                    else:
                        rp = RobotFileParser()
                        rp.set_url(robots_url)
                        rp.parse(text.splitlines())
                    self._parser_cache[robots_url] = rp

        rp = self._parser_cache[robots_url]
        if rp is None:
            return True
        return rp.can_fetch("*", url)


class SitemapParser:
    """A recursive XML sitemap parser.

    Attributes:
        client (HTTPClient): The HTTP client to use for fetching.
    """

    def __init__(self, client: HTTPClient, concurrency: int, follow_index: bool = True):
        """Initializes SitemapParser."""
        self.client = client
        self.follow_index = follow_index
        self._visited_sitemaps: set[str] = set()
        self._semaphore = asyncio.Semaphore(concurrency)

    async def parse_all(
        self,
        sitemap_urls: List[str],
        target_count: Optional[int] = None,
        on_records: Optional[Callable[[int], None]] = None,
    ) -> Tuple[List[URLRecord], List[str]]:
        """Iteratively parses sitemaps, following nested index links.

        Args:
            sitemap_urls (List[str]): Initial sitemap URLs to parse.
            target_count (Optional[int]): If set, stop traversing once at least
                this many records have been collected, instead of following
                every nested sitemap index to exhaustion. Callers are
                responsible for padding this with enough of a margin to
                survive any post-parse filtering they'll apply — this method
                does no filtering of its own.
            on_records (Optional[Callable[[int], None]]): Called with the
                number of new records each time a sitemap fetch completes,
                e.g. to drive a progress bar.

        Returns:
            Tuple[List[URLRecord], List[str]]: A tuple containing all discovered
                URL records and the list of sitemaps traversed.
        """
        all_records: list[URLRecord] = []
        all_sitemaps: list[str] = []

        queue: list[str] = [u for u in sitemap_urls if u not in self._visited_sitemaps]

        while queue:
            batch = []
            for url in queue:
                if url not in self._visited_sitemaps:
                    batch.append(url)

            queue = []
            if not batch:
                break

            all_sitemaps.extend(batch)

            pending = {asyncio.ensure_future(self._parse_one(url)) for url in batch}
            target_reached = False

            # A sitemap index can fan out to many siblings in a single batch
            # (e.g. one file per day for years). Check the running total as
            # each fetch completes rather than waiting for asyncio.gather to
            # finish the whole batch, so a small target_count can cut a wide
            # batch short too, not just a deep chain of nested indexes.
            while pending:
                done, pending = await asyncio.wait(
                    pending, return_when=asyncio.FIRST_COMPLETED
                )

                for task in done:
                    try:
                        records, child_sitemaps = task.result()
                    except Exception:
                        continue
                    all_records.extend(records)
                    if records and on_records is not None:
                        on_records(len(records))

                    # child_sitemaps only ever contains <loc> entries pulled
                    # from <sitemap> elements inside a <sitemapindex> — they
                    # are sitemaps by schema regardless of URL extension, so
                    # re-queue all of them.
                    if self.follow_index:
                        for child_url in child_sitemaps:
                            if child_url not in self._visited_sitemaps:
                                queue.append(child_url)

                if target_count is not None and len(all_records) >= target_count:
                    target_reached = True
                    break

            if pending:
                for task in pending:
                    task.cancel()
                await asyncio.gather(*pending, return_exceptions=True)

            if target_reached:
                break

        return all_records, all_sitemaps

    async def _parse_one(self, url: str) -> Tuple[List[URLRecord], List[str]]:
        """Parses a single sitemap URL."""
        if url in self._visited_sitemaps:
            return [], []
        self._visited_sitemaps.add(url)

        logging.info(f"[sitemap] Fetching: {url}")

        async with self._semaphore:
            data = await self.client.get(url)

        if not data:
            logging.warning(f"[sitemap] No data returned for: {url}")
            return [], []

        records, children = self._parse_xml(data, source=url)
        logging.info(
            f"[sitemap] {url} → {len(records)} URLs, {len(children)} child sitemaps"
        )
        return records, children

    def _parse_xml(self, data: bytes, source: str) -> Tuple[List[URLRecord], List[str]]:
        """Parses XML data into URL records and child sitemap links."""
        records: list[URLRecord] = []
        child_sitemaps: list[str] = []

        try:
            parser = etree.XMLParser(
                recover=True, encoding="utf-8", **_SAFE_XML_PARSER_KWARGS
            )
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
    def _find_text(element: etree._Element, tag: str) -> Optional[str]:
        """Finds the text content of a child tag within an element."""
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
    def _regex_extract(data: bytes, source: str) -> List[URLRecord]:
        """Fallback URL extraction using regular expressions."""
        text = data.decode("utf-8", errors="replace")
        urls = re.findall(r'<loc>\s*(https?://[^\s<>"]+)\s*</loc>', text)
        urls += re.findall(r'href=["\']?(https?://[^\s"\'<>]+)', text)
        return [URLRecord(url=u.strip(), source=source) for u in set(urls)]


class HTMLCrawler:
    """A basic recursive crawler for site mapping via HTML links.

    Attributes:
        client (HTTPClient): The HTTP client for fetching.
        max_crawl_pages (int): Limit for number of pages to crawl.
        max_crawl_depth (int): Limit for crawl recursion depth.
    """

    def __init__(
        self,
        client: HTTPClient,
        concurrency: int,
        max_crawl_pages: int,
        max_crawl_depth: int,
        robots: Optional["RobotsParser"] = None,
    ):
        """Initializes HTMLCrawler."""
        self.client = client
        self.max_crawl_pages = max_crawl_pages
        self.max_crawl_depth = max_crawl_depth
        self.robots = robots
        self._visited: set[str] = set()
        self._semaphore = asyncio.Semaphore(concurrency)

    async def crawl(
        self, base_url: str, on_record: Optional[Callable[[], None]] = None
    ) -> List[URLRecord]:
        """Crawls a site starting from base_url to find internal links.

        Args:
            base_url (str): The starting URL.
            on_record (Optional[Callable[[], None]]): Called once per page
                successfully crawled, e.g. to drive a progress bar.

        Returns:
            List[URLRecord]: A list of discovered internal URLs.
        """
        records: list[URLRecord] = []
        queue = asyncio.Queue()
        await queue.put((base_url, 0))

        while not queue.empty() and len(self._visited) < self.max_crawl_pages:
            url, depth = await queue.get()
            norm = normalize_url(url)
            if norm in self._visited or depth > self.max_crawl_depth:
                continue
            self._visited.add(norm)

            if self.robots and not await self.robots.is_allowed(url, base_url):
                continue

            async with self._semaphore:
                text = await self.client.get_text(url)
            if not text:
                continue

            records.append(URLRecord(url=url, source="html_crawl"))
            if on_record is not None:
                on_record()
            links = self._extract_links(text, url, base_url)
            for link in links:
                if normalize_url(link) not in self._visited:
                    await queue.put((link, depth + 1))

        return records

    @staticmethod
    def _extract_links(html: str, page_url: str, base_url: str) -> List[str]:
        """Extracts all same-origin href links from HTML."""
        links = []
        for match in re.finditer(r'href=["\']([^"\'#\s]+)', html, re.I):
            href = match.group(1).strip()
            if href.startswith("mailto:") or href.startswith("javascript:"):
                continue
            abs_url = urljoin(page_url, href)
            if is_same_origin(abs_url, base_url):
                links.append(abs_url)
        return links


class SiteMap:
    """The high-level orchestrator for site discovery.

    Combines robots.txt parsing, common path probing, XML sitemap traversal,
    and HTML crawling to find all relevant URLs on a site.

    Attributes:
        settings (Settings): Configuration settings.
    """

    def __init__(self, settings: Settings):
        """Initializes SiteMap."""
        self.settings = settings

    @staticmethod
    def _parse_lastmod(lastmod: Optional[str]) -> Optional[date]:
        """Parses a sitemap lastmod string into a date object."""
        if not lastmod:
            return None
        s = lastmod.strip()
        # Slice candidates from longest to shortest to avoid partial matches
        slice_fmts = [
            (19, "%Y-%m-%dT%H:%M:%S"),
            (10, "%Y-%m-%d"),
            (7, "%Y-%m"),
            (4, "%Y"),
        ]
        from datetime import datetime as _dt

        for length, fmt in slice_fmts:
            try:
                return _dt.strptime(s[:length], fmt).date()
            except ValueError:
                continue
        return None

    async def run(self, url: str) -> List[str]:
        """Runs the universal sitemap discovery process.

        Args:
            url (str): The starting URL.

        Returns:
            List[str]: A list of discovered absolute internal URLs.
        """
        base_url = self._normalize_base(url)

        strategies_used: list[str] = []
        all_records: list[URLRecord] = []

        pbar = make_progress_bar(
            total=self.settings.link_extraction_limit,
            desc="Sitemap Discovery",
            unit="url",
            show_progress=self.settings.show_progress,
        )

        def _bump(n: int = 1) -> None:
            remaining = pbar.total - pbar.n
            if remaining > 0:
                pbar.update(min(n, remaining))

        try:
            async with HTTPClient(
                self.settings.concurrency,
                self.settings.request_timeout,
                self.settings.sitemap.user_agent,
                self.settings.max_retries,
                self.settings.retry_delay,
                self.settings.create_proxy_pool(),
            ) as client:
                robots = RobotsParser(client)
                sitemap_parser = SitemapParser(
                    client,
                    self.settings.concurrency,
                    follow_index=self.settings.sitemap.follow_index,
                )

                sitemap_urls = await robots.fetch_sitemaps(base_url)
                if sitemap_urls:
                    strategies_used.append("robots.txt")

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

                if sitemap_urls:
                    strategies_used.append("sitemap_xml")

                    # Only let parse_all() stop early when no downstream filter
                    # can unpredictably drop a large fraction of records — those
                    # filters run after this point and could otherwise leave us
                    # under the requested limit despite more URLs being available.
                    # robots.txt disallow rules are excluded from this check: they
                    # typically remove a small, roughly uniform slice of a site's
                    # URL space (unlike a narrow date range or include pattern,
                    # which can trivially drop the vast majority of records), so
                    # the overfetch margin below is expected to absorb them too.
                    filters_may_shrink_results = (
                        self.settings.sitemap.start_date is not None
                        or self.settings.sitemap.end_date is not None
                        or bool(self.settings.include_link_patterns)
                    )
                    target_count = (
                        None
                        if filters_may_shrink_results
                        else self.settings.link_extraction_limit
                        * _SITEMAP_LIMIT_OVERFETCH_FACTOR
                    )

                    records, _ = await sitemap_parser.parse_all(
                        sitemap_urls, target_count=target_count, on_records=_bump
                    )
                    all_records.extend(records)

                if not all_records and self.settings.sitemap.html_fallback:
                    strategies_used.append("html_crawl")
                    crawler = HTMLCrawler(
                        client,
                        self.settings.concurrency,
                        self.settings.sitemap.max_pages,
                        self.settings.sitemap.max_depth,
                        robots=robots if self.settings.sitemap.respect_robots else None,
                    )
                    crawl_records = await crawler.crawl(base_url, on_record=_bump)
                    all_records.extend(crawl_records)

                # Respect robots.txt for sitemap-sourced URLs too (the HTML crawl
                # fallback above already gates each fetch as it happens).
                if self.settings.sitemap.respect_robots and all_records:
                    allowed_flags = await asyncio.gather(
                        *(robots.is_allowed(rec.url, base_url) for rec in all_records)
                    )
                    all_records = [
                        rec for rec, ok in zip(all_records, allowed_flags) if ok
                    ]
        finally:
            pbar.close()

        logging.info(f"Strategies used: {strategies_used}")

        start_date = self.settings.sitemap.start_date
        end_date = self.settings.sitemap.end_date
        strict_date_filter = self.settings.sitemap.strict_date_filter
        if start_date is not None or end_date is not None:
            filtered: list[URLRecord] = []
            for rec in all_records:
                lm = self._parse_lastmod(rec.lastmod)
                if lm is None:
                    if not strict_date_filter:
                        filtered.append(rec)
                    continue
                if start_date is not None and lm < start_date:
                    continue
                if end_date is not None and lm > end_date:
                    continue
                filtered.append(rec)
            all_records = filtered

        all_records = [r for r in all_records if not is_xml_url(r.url)]

        if self.settings.include_link_patterns:
            all_records = [
                r
                for r in all_records
                if wildcard_link_match(
                    r.url, base_url, self.settings.include_link_patterns
                )
            ]

        if self.settings.sitemap.deduplicate:
            seen: set[str] = set()
            deduped: list[URLRecord] = []
            for rec in all_records:
                norm = normalize_url(rec.url)
                if norm not in seen:
                    seen.add(norm)
                    deduped.append(rec)
            all_records = deduped

        if len(all_records) > self.settings.link_extraction_limit:
            all_records = all_records[: self.settings.link_extraction_limit]

        return [rec.url for rec in all_records]

    @staticmethod
    async def _probe_url(client: HTTPClient, url: str) -> bool:
        """Probes a URL to see if it exists and is not empty."""
        data = await client.get(url)
        return data is not None and len(data) > 0

    @staticmethod
    def _normalize_base(url: str) -> str:
        """Ensures the base URL has a scheme and trailing slash removed."""
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        p = urlparse(url)
        return f"{p.scheme}://{p.netloc}"
