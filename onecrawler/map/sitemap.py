import asyncio
import time
from typing import Set, Tuple
import aiohttp
from lxml import etree
from urllib.parse import urlparse
from ..config.crawler import CrawlerSettings
from ..crawler.link.helper import wildcard_link_match


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
    def __init__(self, config: CrawlerSettings):

        self.semaphore = asyncio.Semaphore(config.concurrency)
        self.visited_sitemaps: Set[str] = set()
        self.urls: Set[str] = set()
        self.stats = SitemapStats()
        self.timeout = config.browser_settings.runtime.timeout
        self.filter_pattern = config.include_link_patterns
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
        return self.urls, self.stats

    async def run(self, url: str):
        urls, stats = await self.fetch(url)
        return urls
