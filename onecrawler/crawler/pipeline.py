import asyncio
import datetime
import logging
from typing import Optional
from urllib.parse import urlparse

from ..browser import GoogleChrome
from ..settings.simulation import HumanBehaviorSettings
from .base import BaseEngine
from .link.deep import BFScheduler, BrowserPool, LinkSpider
from .link.helper import (
    human_delay,
    human_mouse_move,
    human_scroll,
    wildcard_link_match,
)
from .scraper.heuristic.script import HeuristicStrategy

logger = logging.getLogger(__name__)


class PipelineRuntime:
    def __init__(
        self,
        scheduler,
        pool,
        spider,
        base_prefix: str,
        max_links: int,
        strategy: Optional[HeuristicStrategy] = None,
        human_behavior_settings: HumanBehaviorSettings = HumanBehaviorSettings,
        include_pattern: Optional[list] = None,
        enable_human_behaviors: bool = False,
        concurrency: int = 5,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ):
        self.scheduler = scheduler
        self.pool = pool
        self.spider = spider
        if strategy is None:
            raise ValueError(
                "PipelineRuntime requires an initialized scraping strategy"
            )
        self.strategy = strategy

        self.base_prefix = base_prefix
        self.max_links = max_links
        self.include_pattern = include_pattern
        self.enable_human_behaviors = enable_human_behaviors
        self.human_behavior_settings = human_behavior_settings
        self.concurrency = concurrency

        self.stop_event = asyncio.Event()

        self.results = []
        self.content = []
        self.results_set = set()
        self.lock = asyncio.Lock()

        # Track how many workers are actively processing a URL
        self._active_workers = 0
        self._active_lock = asyncio.Lock()

        self.start_date = start_date
        self.end_date = end_date

    async def worker(self):
        while not self.stop_event.is_set():
            url = await self.scheduler.next()

            if url is None:
                async with self._active_lock:
                    if self._active_workers == 0:
                        self.stop_event.set()
                        return

                await asyncio.sleep(0.2)
                continue

            if url in self.scheduler.visited:
                continue

            async with self._active_lock:
                self._active_workers += 1

            page = await self.pool.acquire()

            try:
                self.scheduler.mark_visited(url)

                try:
                    await page.goto(url, wait_until="domcontentloaded")
                except Exception as e:
                    logger.warning("Failed to load %s: %s", url, e)
                    return

                if self.enable_human_behaviors:
                    await human_delay(
                        self.human_behavior_settings.min_delay,
                        self.human_behavior_settings.max_delay,
                    )
                    await human_scroll(
                        page, max_scrolls=self.human_behavior_settings.max_scrolls
                    )

                links = await self.spider.parse(page)

                if self.enable_human_behaviors:
                    await human_mouse_move(
                        page,
                        min_mouse_moves=self.human_behavior_settings.min_mouse_moves,
                        max_mouse_moves=self.human_behavior_settings.max_mouse_moves,
                        mouse_width=self.human_behavior_settings.mouse_width,
                        mouse_height=self.human_behavior_settings.mouse_height,
                        min_mouse_steps=self.human_behavior_settings.min_mouse_steps,
                        max_mouse_steps=self.human_behavior_settings.max_mouse_steps,
                        min_mouse_sleep=self.human_behavior_settings.min_mouse_sleep,
                        max_mouse_sleep=self.human_behavior_settings.max_mouse_sleep,
                    )

                for link in links:
                    if self.stop_event.is_set():
                        break

                    if not link.startswith(self.base_prefix):
                        continue

                    if self.include_pattern:
                        if not wildcard_link_match(
                            link,
                            self.base_prefix,
                            self.include_pattern,
                        ):
                            continue

                    await self.scheduler.add(link)

                    async with self.lock:
                        if len(self.results) >= self.max_links:
                            self.stop_event.set()
                            return

                        if link in self.results_set:
                            continue

                        self.results_set.add(link)

                        try:
                            content = await self.strategy.extract(link)
                            if content is None:
                                logger.info(
                                    "Content extraction returned None for %s", link
                                )
                                continue

                            if self._is_valid_content(content):
                                self.results.append(link)
                                self.content.append(content)
                                logger.info("Content is valid, added to results")
                            else:
                                logger.info("Content is not valid for date range")
                        except Exception as e:
                            logger.error("Error extracting content for %s: %s", link, e)
                            continue

                        logger.info(
                            "Discovered %s/%s links; link=%s",
                            len(self.results),
                            self.max_links,
                            link,
                        )

                        if len(self.results) >= self.max_links:
                            self.stop_event.set()
                            return

            finally:
                await self.pool.release(page)
                async with self._active_lock:
                    self._active_workers -= 1

    def _is_valid_content(self, content: dict) -> bool:
        if not self.start_date and not self.end_date:
            return True

        date = content.get("filedate") or content.get("date")
        if date is None:
            logger.info("No date found in content")
            return False

        try:
            date_obj = datetime.datetime.strptime(date, "%Y-%m-%d")
        except (ValueError, TypeError):
            logger.info("Invalid date format: %s", date)
            return False

        logger.info(
            "Checking date %s against range %s to %s",
            date,
            self.start_date,
            self.end_date,
        )

        if self.start_date:
            try:
                start_date_obj = datetime.datetime.strptime(self.start_date, "%Y-%m-%d")
                if date_obj < start_date_obj:
                    logger.info(
                        "Date %s is before start date %s", date, self.start_date
                    )
                    return False
            except ValueError:
                logger.warning("Invalid start_date format: %s", self.start_date)

        if self.end_date:
            try:
                end_date_obj = datetime.datetime.strptime(self.end_date, "%Y-%m-%d")
                if date_obj > end_date_obj:
                    logger.info("Date %s is after end date %s", date, self.end_date)
                    return False
            except ValueError:
                logger.warning("Invalid end_date format: %s", self.end_date)

        logger.info("Date %s is valid for range", date)
        return True

    async def run(self):
        tasks = [asyncio.create_task(self.worker()) for _ in range(self.concurrency)]
        await asyncio.gather(*tasks, return_exceptions=True)
        return self.content


class PipelineEngine(BaseEngine):
    """
    A comprehensive web crawling pipeline engine that orchestrates browser automation,
    link extraction, and content scraping with advanced human behavior simulation.

    The PipelineEngine provides a complete crawling solution that can navigate websites,
    extract links following configurable patterns, and scrape content while respecting
    rate limits and mimicking human browsing patterns.

    **Proxy Usage:**
    IMPORTANT: Proxy configuration is REQUIRED for production use to avoid IP blocking
    and rate limiting. Configure proxy settings in your crawler settings:

    ```python
    # Example proxy configuration
    settings.crawler_settings.proxy_pool = [
        "http://proxy1.example.com:8080",
        "http://proxy2.example.com:8080",
        # Add more proxies for rotation
    ]
    ```

    Without proper proxy configuration, your crawler may be blocked by target websites.

    Args:
        settings: Configuration object containing crawler, browser, and behavior settings
        start_date (Optional[str]): Filter content by start date in YYYY-MM-DD format
        end_date (Optional[str]): Filter content by end date in YYYY-MM-DD format

    Attributes:
        settings: The configuration settings for the crawler
        start_date: Start date filter for content extraction
        end_date: End date filter for content extraction
        browser: GoogleChrome browser instance for web automation
        strategy: HeuristicStrategy for content extraction

    Example:
        ```python
        from onecrawler import CrawlerSettings
        from onecrawler.crawler.pipeline import PipelineEngine

        # Configure settings with proxy
        settings = CrawlerSettings()
        settings.crawler_settings.proxy_pool = ["http://proxy.example.com:8080"]

        engine = PipelineEngine(settings)
        await engine.start()
        results = await engine.run("https://example.com")
        await engine.close()
        ```
    """

    def __init__(
        self, settings, start_date: Optional[str] = None, end_date: Optional[str] = None
    ):
        super().__init__()

        self.settings = settings
        self.start_date = start_date
        self.end_date = end_date

        self.strategy = None
        self.browser = None

        # future-ready placeholders
        self.session = None

        self.logger.info("PipelineEngine initialized")

    async def start(self):
        self._closed = False
        self.browser = GoogleChrome(self.settings.browser_settings)
        await self.browser.start()
        self.strategy = HeuristicStrategy(settings=self.settings, browser=self.browser)

    async def close(self):
        if self.browser:
            await self.browser.close()

    async def run(self, url: str) -> dict:
        self._ensure_open()
        return await self._run_pipeline(url)

    async def _run_pipeline(self, url: str) -> dict:
        self._ensure_open()

        parsed = urlparse(url)
        base_prefix = f"{parsed.scheme}://{parsed.netloc}"

        scheduler = BFScheduler(url)
        spider = LinkSpider(base_prefix)
        pool = BrowserPool(self.browser, self.settings.concurrency)

        await pool.init()

        runtime = PipelineRuntime(
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
            start_date=self.start_date,
            end_date=self.end_date,
        )

        try:
            return await runtime.run()
        finally:
            await pool.close()
