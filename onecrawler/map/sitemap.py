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
        timeout: int = 10,
        retries: int = 2,
        debug: bool = False,
    ):
        self.sitemap_url = (
            url.rstrip("/") + "/sitemap.xml"
            if not url.endswith("sitemap.xml")
            else url
        )

        self.filter_pattern = filter_pattern
        self.timeout = timeout
        self.retries = retries
        self.debug = debug

        self.semaphore = asyncio.Semaphore(concurrency)

        self.visited_sitemaps: Set[str] = set()
        self.urls: Set[str] = set()
        self.stats = Stats()

        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120 Safari/537.36"
            )
        }

    # ---------------- FETCH ----------------
    async def _fetch(self, session, url):
        for attempt in range(self.retries + 1):
            try:
                async with self.semaphore:
                    async with session.get(
                        url,
                        timeout=self.timeout,
                        headers=self.headers
                    ) as r:

                        text = await r.text(errors="ignore")

                        if self.debug:
                            print(f"[FETCH] {url} -> {r.status}")

                        if r.status == 200:
                            # detect HTML fallback
                            if "<html" in text.lower():
                                self.stats.errors += 1
                                return None

                            return text.encode("utf-8")

            except Exception as e:
                if self.debug:
                    print(f"[ERROR] {url} attempt {attempt}: {e}")
                self.stats.errors += 1

        return None

    # ---------------- PARSE ----------------
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
        except Exception as e:
            if self.debug:
                print(f"[PARSE ERROR] {sitemap_url}: {e}")
            self.stats.errors += 1
            return

        tag = root.tag.lower()

        # ---------------- SITEMAP INDEX ----------------
        if "sitemapindex" in tag:
            locs = root.xpath("//*[local-name()='loc']/text()")

            tasks = []
            for loc in locs:
                tasks.append(self._parse(session, loc.strip()))

            await asyncio.gather(*tasks)

        # ---------------- URLSET ----------------
        elif "urlset" in tag:
            urls = root.xpath("//*[local-name()='loc']/text()")

            for url in urls:
                url = url.strip()

                parsed = urlparse(url)
                path_segments = parsed.path.strip("/").split("/")

                if self.filter_pattern:
                    if self.filter_pattern not in path_segments:
                        continue

                if url not in self.urls:
                    self.urls.add(url)
                    self.stats.urls += 1

    # ---------------- PUBLIC API ----------------
    async def fetch(self) -> Tuple[Set[str], Stats]:
        timeout = aiohttp.ClientTimeout(total=self.timeout)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            await self._parse(session, self.sitemap_url)

        return self.urls, self.stats
    
    def run(self) -> Set[str]:
        loop = asyncio.get_event_loop()
        urls, stats = loop.run_until_complete(self.fetch())

        if self.debug:
            print(f"\nStats: {stats.urls} URLs, {stats.sitemaps} sitemaps, "
                  f"{stats.errors} errors, elapsed {stats.elapsed():.2f}s, "
                  f"rate {stats.rate():.2f} URLs/s")

        return urls


# 🚀 Run
if __name__ == "__main__":
    crawler = SiteMap(
        "https://www.ittefaq.com.bd/",
        concurrency=20
    )

    urls = crawler.run()
    print(f"\nDone. Collected {len(urls)} URLs")