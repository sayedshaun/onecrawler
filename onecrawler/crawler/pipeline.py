import asyncio
import datetime
import logging
from typing import AsyncGenerator, List, Optional, Tuple
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
    """The execution runtime for a single pipeline run.

    Handles the concurrent processing of URLs discovered during the crawl,
    managing workers, browser pages, and data extraction.

    Attributes:
        scheduler (BFScheduler): The URL scheduler.
        pool (BrowserPool): The browser page pool.
        spider (LinkSpider): The link discovery spider.
        base_prefix (str): Domain prefix for the crawl.
        max_links (int): Limit for the number of results.
        strategy (Optional[HeuristicStrategy]): Extraction strategy. Defaults to None.
        human_behavior_settings (HumanBehaviorSettings): Settings for human simulation.
        include_pattern (Optional[list]): Wildcard patterns for link inclusion.
        enable_human_behaviors (bool): Enable delay/scroll/mouse simulation.
        concurrency (int): Number of concurrent workers.
        start_date (Optional[str]): Start date for filtering content (YYYY-MM-DD).
        end_date (Optional[str]): End date for filtering content (YYYY-MM-DD).
        streaming (bool): Enable streaming mode.
    """

    def __init__(
        self,
        scheduler: BFScheduler,
        pool: BrowserPool,
        spider: LinkSpider,
        base_prefix: str,
        max_links: int,
        strategy: Optional[HeuristicStrategy] = None,
        human_behavior_settings: HumanBehaviorSettings = HumanBehaviorSettings,
        include_pattern: Optional[List[str]] = None,
        exclude_pattern: Optional[List[str]] = None,
        enable_human_behaviors: bool = False,
        concurrency: int = 5,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        streaming: bool = False,
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
        self.exclude_pattern = exclude_pattern
        self.enable_human_behaviors = enable_human_behaviors
        self.human_behavior_settings = human_behavior_settings
        self.concurrency = concurrency

        self.stop_event = asyncio.Event()

        self.results = []
        self.content = []
        self.results_set = set()
        self.lock = asyncio.Lock()
        self.stream_queue = asyncio.Queue(maxsize=1000)
        self.streaming = streaming

        # Track how many workers are actively processing a URL
        self._active_workers = 0
        self._active_lock = asyncio.Lock()

        self.start_date = start_date
        self.end_date = end_date

    async def worker(self):
        """A worker task that processes URLs from the scheduler.

        Each worker acquires a page from the pool, navigates to a URL,
        simulates human behavior (if enabled), discovers new links,
        and extracts content using the provided strategy.
        """
        while not self.stop_event.is_set():
            async with self._active_lock:
                url = await self.scheduler.next()

                if url is None:
                    if self._active_workers == 0:
                        self.stop_event.set()
                        return

                else:
                    self._active_workers += 1

            if url is None:
                await asyncio.sleep(0.2)
                continue

            if url in self.scheduler.visited:
                async with self._active_lock:
                    self._active_workers -= 1
                continue

            page = await self.pool.acquire()

            try:
                self.scheduler.mark_visited(url)

                try:
                    await page.goto(url, wait_until="domcontentloaded")
                except Exception as e:
                    logger.warning("Failed to load %s: %s", url, e)
                    continue

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

                    if self.exclude_pattern:
                        if wildcard_link_match(
                            link,
                            self.base_prefix,
                            self.exclude_pattern,
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
                                if self.streaming:
                                    await self.stream_queue.put(content)
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
        """Checks if the extracted content satisfies the date range filters.

        Args:
            content (dict): The extracted content dictionary.

        Returns:
            bool: True if valid or no range specified, False otherwise.
        """
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

    async def run(self) -> list:
        """Starts the workers and waits for completion.

        Returns:
            list: All extracted content dictionaries.
        """
        tasks = [asyncio.create_task(self.worker()) for _ in range(self.concurrency)]
        await asyncio.gather(*tasks, return_exceptions=True)
        return self.content

    async def stream(self) -> AsyncGenerator[dict, None]:
        """Starts the workers and yields content as it is extracted.

        Yields:
            dict: Extracted content dictionary.
        """
        self.streaming = True
        tasks = [asyncio.create_task(self.worker()) for _ in range(self.concurrency)]

        try:
            while True:
                try:
                    item = await asyncio.wait_for(
                        self.stream_queue.get(),
                        timeout=0.5,
                    )
                    yield item

                except asyncio.TimeoutError:
                    if all(task.done() for task in tasks) and self.stream_queue.empty():
                        break

        finally:
            await asyncio.gather(*tasks, return_exceptions=True)


class Pipeline(BaseEngine):
    """
    A comprehensive web crawling pipeline engine that orchestrates browser automation,
    link extraction, and content scraping with advanced human behavior simulation.

    The Pipeline provides a complete crawling solution that can navigate websites,
    extract links following configurable patterns, and scrape content while respecting
    rate limits and mimicking human browsing patterns.

    Attributes:
        settings (CrawlerSettings): The configuration object for the pipeline.

    Example:
        ```python
        from onecrawler import CrawlerSettings, Pipeline

        # Configure settings with proxy
        settings = CrawlerSettings(
            proxies=[
                ProxySettings(
                    server="http://proxy1.example.com:8080",
                    username="username",
                    password="password",
                ),
                ProxySettings(
                    server="http://proxy2.example.com:8080",
                    username="username",
                    password="password",
                )
            ],
            proxy_rotation_mode="round_robin",
        )
        async with Pipeline(settings) as engine:
            results = await engine.run("https://example.com")
            print(results)

        # Stream
        async with engine.stream("https://example.com") as stream:
            async for item in stream:
                print(item)
        ```
    """

    def __init__(self, settings):
        super().__init__()

        self.settings = settings

        self.strategy = None
        self.browser = None

        # future-ready placeholders
        self.session = None

        self.logger.info("Pipeline initialized")

    async def start(self):
        """Starts the pipeline by initializing the browser and extraction strategy."""
        self._closed = False
        self.browser = GoogleChrome(self.settings.browser_settings)
        await self.browser.start()
        self.strategy = HeuristicStrategy(settings=self.settings, browser=self.browser)

    async def close(self):
        """Closes the pipeline and releases browser resources."""
        if self.browser:
            await self.browser.close()

    async def run(self, url: str) -> list[dict]:
        """Runs the crawling pipeline starting from the provided URL.

        Args:
            url (str): The starting URL for the crawl.

        Returns:
            list[dict]: A list of extracted content dictionaries.
        """
        self._ensure_open()

        runtime, pool = await self._create_runtime(url)

        try:
            return await runtime.run()
        finally:
            await pool.close()

    async def _create_runtime(
        self, url: str, streaming: bool = False
    ) -> Tuple[PipelineRuntime, BrowserPool]:
        """Creates the runtime environment and browser pool for a crawl.

        Args:
            url (str): The starting URL.
            streaming (bool): Whether to enable streaming mode.

        Returns:
            Tuple[PipelineRuntime, BrowserPool]: The runtime and the pool.
        """
        parsed = urlparse(url)
        base_prefix = f"{parsed.scheme}://{parsed.netloc}"

        scheduler = BFScheduler(url)
        spider = LinkSpider(base_prefix)
        pool = BrowserPool(self.browser, self.settings.concurrency)

        await pool.init()

        # Convert date objects from settings to "YYYY-MM-DD" strings for PipelineRuntime
        def _date_str(d) -> Optional[str]:
            return d.strftime("%Y-%m-%d") if d is not None else None

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
            start_date=_date_str(self.settings.start_date),
            end_date=_date_str(self.settings.end_date),
            streaming=streaming,
        )

        return runtime, pool

    async def stream(self, url: str) -> AsyncGenerator[dict, None]:
        """Runs the crawling pipeline and yields results as they are found.

        Args:
            url (str): The starting URL.

        Yields:
            dict: Extracted content dictionary.
        """
        self._ensure_open()

        runtime, pool = await self._create_runtime(url, streaming=True)

        try:
            async for item in runtime.stream():
                yield item
        finally:
            await pool.close()
