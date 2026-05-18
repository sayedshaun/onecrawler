import asyncio
import datetime
import logging
from typing import Callable, Optional, Tuple
from urllib.parse import urlparse

from ..browser import GoogleChrome
from .base import BaseEngine
from .general import CrawlerRuntime
from .link.deep import BFScheduler, BrowserPool, LinkSpider
from .scraper.heuristic.script import HeuristicStrategy

logger = logging.getLogger(__name__)


class ScheduleCrawler(BaseEngine):
    """Runs a crawl repeatedly on a fixed interval (e.g. every 2 hours).

    Each run collects only content published since the previous run,
    so results never overlap between cycles.

    Args:
        settings: Crawler settings.
        interval_seconds (int): How often to run, in seconds.
        on_results (Callable): Async callback invoked with each run's
            content list: ``async def handler(results: list[dict]) -> None``.

    Example:
        async def save(results):
            for item in results:
                print(item)

        async with ScheduleCrawler(settings, interval_seconds=7200, on_results=save) as crawler:
            await crawler.run("https://example.com")
    """

    def __init__(
        self,
        settings,
        interval_seconds: int,
        on_results: Callable[[list[dict]], None],
    ):
        super().__init__()
        self.settings = settings
        self.interval_seconds = interval_seconds
        self.on_results = on_results
        self.strategy = None
        self.browser = None
        self.session = None
        self._last_run: Optional[datetime.datetime] = None
        self.logger.info("ScheduleCrawler initialized (interval=%ds)", interval_seconds)

    async def start(self):
        self._closed = False
        self.browser = GoogleChrome(self.settings.browser_settings)
        await self.browser.start()
        self.strategy = HeuristicStrategy(settings=self.settings, browser=self.browser)

    async def close(self):
        if self.browser:
            await self.browser.close()

    def _build_schedule_filter(self) -> Optional[Callable[[dict], bool]]:
        """Returns a filter that accepts only content newer than the last run."""
        if self._last_run is None:
            return None  # first run — accept everything

        since = self._last_run

        def _filter(content: dict) -> bool:
            date_str = content.get("filedate") or content.get("date")
            if not date_str:
                return False
            try:
                date_obj = datetime.datetime.strptime(date_str, "%Y-%m-%d")
            except (ValueError, TypeError):
                return False
            return date_obj >= since

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
            content_filter=self._build_schedule_filter(),
        )
        return runtime, pool

    async def run(self, url: str) -> None:
        """Runs the crawl loop forever until cancelled.

        Calls ``on_results`` after each cycle with that cycle's content.
        Cancel the task (``task.cancel()``) to stop gracefully.
        """
        self._ensure_open()

        while True:
            self.logger.info("ScheduleCrawler: starting crawl cycle")
            run_start = datetime.datetime.now()

            runtime, pool = await self._create_runtime(url)
            try:
                results = await runtime.run()
            finally:
                await pool.close()

            self._last_run = run_start  # advance the window after the run completes

            if results:
                self.logger.info(
                    "ScheduleCrawler: %d results, invoking callback", len(results)
                )
                await self.on_results(results)
            else:
                self.logger.info("ScheduleCrawler: no new content this cycle")

            elapsed = (datetime.datetime.now() - run_start).total_seconds()
            sleep_for = max(0, self.interval_seconds - elapsed)
            self.logger.info(
                "ScheduleCrawler: sleeping %.1fs until next cycle", sleep_for
            )
            await asyncio.sleep(sleep_for)
