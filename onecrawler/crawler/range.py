import datetime
import logging
from typing import AsyncGenerator, Callable, Optional, Tuple
from urllib.parse import urlparse

from ..browser import GoogleChrome
from .base import BaseEngine
from .general import CrawlerRuntime
from .link.deep import BFScheduler, BrowserPool, LinkSpider
from .scraper.heuristic.script import HeuristicStrategy

logger = logging.getLogger(__name__)


class RangeCrawler(BaseEngine):
    """Crawls a site and returns only content within a date range."""

    def __init__(self, settings, start_date: str = None, end_date: str = None):
        super().__init__()
        self.settings = settings
        self.start_date = start_date  # "YYYY-MM-DD" string or None
        self.end_date = end_date
        self.strategy = None
        self.browser = None
        self.session = None
        self.logger.info("RangeCrawler initialized")

    async def start(self):
        self._closed = False
        self.browser = GoogleChrome(self.settings.browser_settings)
        await self.browser.start()
        self.strategy = HeuristicStrategy(settings=self.settings, browser=self.browser)

    async def close(self):
        if self.browser:
            await self.browser.close()

    def _build_date_filter(self) -> Optional[Callable[[dict], bool]]:
        """Returns a date-range filter closure, or None if no range is set."""
        start = self.start_date
        end = self.end_date

        if not start and not end:
            return None

        start_obj = datetime.datetime.strptime(start, "%Y-%m-%d") if start else None
        end_obj = datetime.datetime.strptime(end, "%Y-%m-%d") if end else None

        def _filter(content: dict) -> bool:
            date_str = content.get("filedate") or content.get("date")
            if not date_str:
                return False
            try:
                date_obj = datetime.datetime.strptime(date_str, "%Y-%m-%d")
            except (ValueError, TypeError):
                return False
            if start_obj and date_obj < start_obj:
                return False
            if end_obj and date_obj > end_obj:
                return False
            return True

        return _filter

    async def _create_runtime(
        self, url: str, streaming: bool = False
    ) -> Tuple[CrawlerRuntime, BrowserPool]:
        parsed = urlparse(url)
        base_prefix = f"{parsed.scheme}://{parsed.netloc}"

        scheduler = BFScheduler(url)
        spider = LinkSpider(base_prefix)
        pool = BrowserPool(self.browser, self.settings.concurrency)
        await pool.init()

        runtime = CrawlerRuntime(
            scheduler=scheduler,
            pool=pool,
            spider=spider,
            strategy=self.strategy,
            base_prefix=base_prefix,
            max_links=self.settings.link_extraction_limit,
            include_pattern=self.settings.include_link_patterns,
            enable_human_behaviors=self.settings.enable_human_behaviors,
            human_behavior_settings=self.settings.human_behavior_settings,
            concurrency=self.settings.concurrency,
            streaming=streaming,
            content_filter=self._build_date_filter(),
        )
        return runtime, pool

    async def run(self, url: str) -> list[dict]:
        self._ensure_open()
        runtime, pool = await self._create_runtime(url)
        try:
            return await runtime.run()
        finally:
            await pool.close()

    async def stream(self, url: str) -> AsyncGenerator[dict, None]:
        self._ensure_open()
        runtime, pool = await self._create_runtime(url, streaming=True)
        try:
            async for item in runtime.stream():
                yield item
        finally:
            await pool.close()
