import asyncio
import time
from typing import Set, Optional, Tuple
import aiohttp
from lxml import etree
from urllib.parse import urlparse


class Stats:
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
    def __init__(
        self,
        url: str,
        filter_pattern: Optional[str] = None,
        concurrency: int = 10,
        save: Optional[str] = None,
        timeout: int = 10,
    ):
        self.sitemap_url = (
            url.rstrip("/") + "/sitemap.xml" if not url.endswith("sitemap.xml") else url
        )

        self.filter_pattern = filter_pattern
        self.timeout = timeout
        self.save = save
        self.semaphore = asyncio.Semaphore(concurrency)

        self.visited_sitemaps: Set[str] = set()
        self.urls: Set[str] = set()
        self.stats = Stats()

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

                parsed = urlparse(url)
                path_segments = parsed.path.strip("/").split("/")

                if self.filter_pattern:
                    if self.filter_pattern not in path_segments:
                        continue

                if url not in self.urls:
                    self.urls.add(url)
                    self.stats.urls += 1

    async def fetch(self) -> Tuple[Set[str], Stats]:
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            await self._parse(session, self.sitemap_url)
        return self.urls, self.stats

    def run(self):
        return asyncio.run(self.fetch())
