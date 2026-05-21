import asyncio
import contextlib
import logging
import warnings
from typing import AsyncGenerator, Callable, List, Optional, Tuple
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


async def _goto(page, *args, **kwargs):
    navigation = asyncio.create_task(page.goto(*args, **kwargs))
    try:
        return await navigation
    except asyncio.CancelledError:
        navigation.cancel()
        with contextlib.suppress(BaseException):
            await navigation
        raise


class CrawlerRuntime:
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
        streaming: bool = False,
        content_filter: Optional[Callable[[dict], bool]] = None,
        *args,
        **kwargs,
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
        parsed = urlparse(base_prefix)
        self.base_scheme = parsed.scheme
        self.base_netloc = parsed.netloc.lower()
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

        self.content_filter = content_filter

    def _same_origin(self, link: str) -> bool:
        parsed = urlparse(link)
        return (
            parsed.scheme == self.base_scheme
            and parsed.netloc.lower() == self.base_netloc
        )

    async def worker(self):
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

            page = await self.pool.acquire()

            try:
                try:
                    await _goto(page, url, wait_until="domcontentloaded")
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

                    if not self._same_origin(link):
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

                            if self.content_filter is None or self.content_filter(
                                content
                            ):
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

    async def run(self) -> list:
        if self.max_links <= 0:
            return []

        tasks = [asyncio.create_task(self.worker()) for _ in range(self.concurrency)]
        await asyncio.gather(*tasks)
        return self.content

    async def stream(self) -> AsyncGenerator[dict, None]:
        if self.max_links <= 0:
            return

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
            self.stop_event.set()
            for task in tasks:
                if not task.done():
                    task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await asyncio.gather(*tasks, return_exceptions=True)


class Crawler(BaseEngine):
    """Crawls a site and returns all content with no filtering.

    Supports optional proxy configuration via ``Settings.proxy`` for
    anonymised crawling. Acts as the primary crawler entry-point.
    """

    def __init__(self, settings):
        super().__init__()
        self.settings = settings
        self.strategy = None
        self.browser = None
        self.session = None
        self.logger.info("Crawler initialized")

    async def start(self):
        self._closed = False
        self.browser = GoogleChrome(self.settings.browser_settings)
        await self.browser.start()
        self.strategy = HeuristicStrategy(settings=self.settings, browser=self.browser)

    async def close(self):
        if self.browser:
            await self.browser.close()

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
            exclude_pattern=self.settings.exclude_link_patterns,
            enable_human_behaviors=self.settings.enable_human_behaviors,
            human_behavior_settings=self.settings.human_behavior_settings,
            concurrency=self.settings.concurrency,
            streaming=streaming,
            content_filter=None,
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


class Pipeline(Crawler):
    """Deprecated alias for Crawler. Use Crawler instead."""

    def __init__(self, *args, **kwargs):
        warnings.warn(
            "Pipeline is deprecated. Use Crawler instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(*args, **kwargs)


PipelineRuntime = CrawlerRuntime
