import asyncio
import contextlib
import logging
from typing import Any, AsyncGenerator, Callable, List, Optional, Tuple
from urllib.parse import urlparse

from ..browser import GoogleChrome
from ..settings.browser import BrowserSettings
from ..settings.simulation import HumanBehaviorSettings
from .base import BaseEngine
from .link.helper import (
    human_delay,
    human_mouse_move,
    human_scroll,
    wildcard_link_match,
)
from .navigation import goto
from .pool import BrowserPool
from .scheduler import BFScheduler
from .scraper.genai.executor import GenAIStrategy
from .scraper.heuristic.script import HeuristicStrategy
from .spider import LinkSpider

logger = logging.getLogger(__name__)


class CrawlerRuntime:
    def __init__(
        self,
        scheduler: BFScheduler,
        pool: BrowserPool,
        spider: LinkSpider,
        base_prefix: str,
        max_links: int,
        strategy: Optional[Any] = None,
        human_behavior_settings: Optional[HumanBehaviorSettings] = None,
        include_pattern: Optional[List[str]] = None,
        exclude_pattern: Optional[List[str]] = None,
        enable_human_behaviors: bool = False,
        concurrency: int = 5,
        streaming: bool = False,
        content_filter: Optional[Callable[[dict], bool]] = None,
        wait_until: Optional[str] = None,
        timeout: Optional[int] = None,
        *args,
        **kwargs,
    ):
        browser_settings = BrowserSettings()
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
        self.wait_until = wait_until or browser_settings.wait_until
        self.timeout = timeout or browser_settings.timeout

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
            url = await self.scheduler.next()

            async with self._active_lock:
                if url is None:
                    if (
                        self._active_workers == 0
                        and not await self.scheduler.has_next()
                    ):
                        self.stop_event.set()
                else:
                    self._active_workers += 1

            if url is None:
                await asyncio.sleep(0.05)
                continue

            try:
                page = await self.pool.acquire()
            except Exception as e:
                logger.warning("Failed to acquire page for %s: %s", url, e)
                async with self._active_lock:
                    self._active_workers -= 1
                continue

            try:
                try:
                    await goto(
                        page,
                        url,
                        wait_until=self.wait_until,
                        timeout=self.timeout,
                    )
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

                async with self.lock:
                    should_extract = (
                        not self.stop_event.is_set() and url not in self.results_set
                    )
                    if should_extract:
                        self.results_set.add(url)

                if should_extract:
                    try:
                        content = await self.strategy.extract(url)
                        if content is None:
                            logger.debug("Content extraction returned None for %s", url)
                        else:
                            if isinstance(content, dict):
                                content["url"] = url
                            else:
                                content = {"text": content, "url": url}

                            if self.content_filter is None or self.content_filter(
                                content
                            ):
                                async with self.lock:
                                    self.results.append(url)
                                    self.content.append(content)
                                    if len(self.results) >= self.max_links:
                                        self.stop_event.set()

                                if self.streaming:
                                    await self.stream_queue.put(content)

                                logger.debug(
                                    "Discovered %s/%s links; link=%s",
                                    len(self.results),
                                    self.max_links,
                                    url,
                                )
                            else:
                                logger.debug("Content did not pass filter for %s", url)
                    except Exception as e:
                        logger.warning("Error extracting content for %s: %s", url, e)

                # Enqueue discovered child links for future visits
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

                    async with self.lock:
                        if link not in self.results_set:
                            await self.scheduler.add(link)

            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.warning(
                    "Worker error processing %s: [%s] %s", url, type(e).__name__, e
                )
            finally:
                await self.pool.release(page)
                async with self._active_lock:
                    self._active_workers -= 1

    async def run(self) -> list:
        if self.max_links <= 0:
            return []

        tasks = [asyncio.create_task(self.worker()) for _ in range(self.concurrency)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for result in results:
            if isinstance(result, Exception):
                logger.warning(
                    "Worker task failed: [%s] %s", type(result).__name__, result
                )
        return self.content

    async def stream(self) -> AsyncGenerator[dict, None]:
        if self.max_links <= 0:
            return

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
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for result in results:
                    if isinstance(result, Exception) and not isinstance(
                        result, asyncio.CancelledError
                    ):
                        logger.warning(
                            "Worker task failed: [%s] %s", type(result).__name__, result
                        )


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

        scraping_strategy = getattr(self.settings, "scraping_strategy", "heuristic")
        if not isinstance(scraping_strategy, str):
            scraping_strategy = "heuristic"

        if scraping_strategy == "genai":
            if not getattr(self.settings, "genai", None):
                raise ValueError("GenAI settings is required for GenAI strategy")
        elif scraping_strategy != "heuristic":
            raise ValueError(f"Unknown strategy: {scraping_strategy}")

        self.browser = GoogleChrome(self.settings.browser_settings)
        await self.browser.start()

        if scraping_strategy == "heuristic":
            strategy = HeuristicStrategy(
                settings=self.settings,
                browser=self.browser,
            )
        else:
            strategy = GenAIStrategy(
                provider=self.settings.genai.provider,
                model_name=self.settings.genai.model_name,
                max_retries=self.settings.max_retries,
                api_key=self.settings.genai.api_key,
                base_url=self.settings.genai.base_url,
                output_schema=self.settings.genai.output_schema,
                provider_kwargs=self.settings.genai.provider_kwargs,
                timeout=self.settings.genai.timeout,
                browser=self.browser,
            )
            await strategy.initialize()

        self.strategy = strategy

    async def close(self):
        if self.strategy:
            await self.strategy.close()

        if self.browser:
            await self.browser.close()

    async def _create_runtime(
        self,
        url: str,
        streaming: bool = False,
        content_filter: Optional[Callable[[dict], bool]] = None,
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
            content_filter=content_filter,
            wait_until=self.settings.browser_settings.wait_until,
            timeout=self.settings.browser_settings.timeout,
        )
        return runtime, pool

    async def run(self, url: str, filters=None) -> list[dict]:
        self._ensure_open()
        runtime, pool = await self._create_runtime(url, content_filter=filters)
        try:
            return await runtime.run()
        finally:
            await pool.close()

    async def stream(self, url: str, filters=None) -> AsyncGenerator[dict, None]:
        self._ensure_open()
        runtime, pool = await self._create_runtime(
            url, streaming=True, content_filter=filters
        )
        try:
            async for item in runtime.stream():
                yield item
        finally:
            await pool.close()
