import asyncio
import logging
import sys
from typing import AsyncGenerator, List, Optional, Set

from tqdm import tqdm

from ...settings.browser import BrowserSettings
from ...settings.simulation import HumanBehaviorSettings
from ..pool import BrowserPool
from ..scheduler import BFScheduler
from ..spider import LinkSpider
from .helper import human_delay, human_mouse_move, human_scroll, wildcard_link_match

logger = logging.getLogger(__name__)


class BFSRuntime:
    """The runtime orchestrator for a BFS crawl.

    Attributes:
        scheduler (BFScheduler): The URL scheduler.
        pool (BrowserPool): The browser page pool.
        spider (LinkSpider): The link discovery spider.
        base_prefix (str): The domain prefix for the crawl.
        max_links (int): Maximum number of links to discover.
        include_pattern (Optional[list]): List of patterns for link inclusion.
        exclude_pattern (Optional[list]): List of patterns for link exclusion.
        enable_human_behaviors (bool): Whether to simulate human browsing.
        human_behavior_settings (HumanBehaviorSettings): Configuration for simulation.
        concurrency (int): Number of concurrent worker tasks.
        streaming (bool): Whether to stream results via a queue.
    """

    def __init__(
        self,
        scheduler: BFScheduler,
        pool: BrowserPool,
        spider: LinkSpider,
        base_prefix: str,
        max_links: int,
        human_behavior_settings: HumanBehaviorSettings,
        include_pattern: Optional[List[str]] = None,
        exclude_pattern: Optional[List[str]] = None,
        enable_human_behaviors: bool = False,
        concurrency: int = 5,
        streaming: bool = False,
        wait_until: Optional[str] = None,
        timeout: Optional[int] = None,
        show_progress: bool = True,
    ):
        browser_settings = BrowserSettings()
        self.scheduler = scheduler
        self.pool = pool
        self.spider = spider

        self.base_prefix = base_prefix
        self.max_links = max_links
        self.include_pattern = include_pattern
        self.exclude_pattern = exclude_pattern
        self.enable_human_behaviors = enable_human_behaviors
        self.human_behavior_settings = human_behavior_settings
        self.concurrency = concurrency
        self.wait_until = wait_until or browser_settings.wait_until
        self.timeout = timeout or browser_settings.timeout
        self.show_progress = show_progress

        self.stop_event: asyncio.Event = asyncio.Event()
        self.results: List[str] = []
        self.results_set: Set[str] = set()
        self.lock: asyncio.Lock = asyncio.Lock()

        self._active_workers: int = 0
        self._active_lock: asyncio.Lock = asyncio.Lock()
        self.stream_queue: asyncio.Queue[str] = asyncio.Queue(maxsize=1000)
        self.streaming: bool = streaming

    async def worker(self):
        """A worker task that processes URLs and discovers new links.

        Workers acquire pages, navigate to URLs, simulate human behavior,
        and enqueue newly found links back into the scheduler.
        """
        while not self.stop_event.is_set():
            url = await self.scheduler.next()

            async with self._active_lock:
                if url is None:
                    if (
                        self._active_workers == 0
                        and not await self.scheduler.has_next()
                    ):
                        self.stop_event.set()
                        return
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
                    await page.goto(
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

                for link in links:
                    if self.stop_event.is_set():
                        break

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

                    should_stream = False
                    async with self.lock:
                        if len(self.results_set) >= self.max_links:
                            self.stop_event.set()
                            break

                        if link in self.results_set:
                            continue

                        self.results_set.add(link)

                        if self.streaming:
                            should_stream = True
                        else:
                            self.results.append(link)

                        logger.debug(
                            "Discovered %s/%s links; link=%s",
                            len(self.results_set),
                            self.max_links,
                            link,
                        )

                        if len(self.results_set) >= self.max_links:
                            self.stop_event.set()

                    await self.scheduler.add(link)
                    if should_stream:
                        await self.stream_queue.put(link)

                    if self.stop_event.is_set():
                        break

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

    async def run(self) -> List[str]:
        """Starts the workers and waits for discovery completion.

        Returns:
            List[str]: A list of all discovered absolute URLs.
        """
        if self.max_links <= 0:
            return []

        tasks = [asyncio.create_task(self.worker()) for _ in range(self.concurrency)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for result in results:
            if isinstance(result, Exception):
                logger.warning(
                    "Worker task failed: [%s] %s", type(result).__name__, result
                )
        return self.results

    # async def stream(self) -> AsyncGenerator[str, None]:
    #     """Starts the workers and yields discovered URLs as they are found.

    #     Yields:
    #         str: Discovered absolute URL.
    #     """
    #     if self.max_links <= 0:
    #         return

    #     tasks = [asyncio.create_task(self.worker()) for _ in range(self.concurrency)]

    #     try:
    #         while True:
    #             try:
    #                 item = await asyncio.wait_for(
    #                     self.stream_queue.get(),
    #                     timeout=0.5,
    #                 )
    #                 yield item

    #             except asyncio.TimeoutError:
    #                 if all(task.done() for task in tasks) and self.stream_queue.empty():
    #                     break

    #     finally:
    #         self.stop_event.set()
    #         for task in tasks:
    #             if not task.done():
    #                 task.cancel()
    #         await asyncio.gather(*tasks, return_exceptions=True)

    async def stream(self) -> AsyncGenerator[str, None]:
        if self.max_links <= 0:
            return

        tasks = [asyncio.create_task(self.worker()) for _ in range(self.concurrency)]

        pbar = tqdm(
            total=self.max_links,
            desc="Link Extracting",
            unit="link",
            dynamic_ncols=True,
            disable=(not self.show_progress or not sys.stderr.isatty()),
        )

        try:
            while True:
                try:
                    item = await asyncio.wait_for(
                        self.stream_queue.get(),
                        timeout=0.5,
                    )
                    pbar.update(1)
                    yield item

                except asyncio.TimeoutError:
                    if all(t.done() for t in tasks) and self.stream_queue.empty():
                        break

        finally:
            self.stop_event.set()
            for t in tasks:
                if not t.done():
                    t.cancel()

            results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, Exception) and not isinstance(
                    result, asyncio.CancelledError
                ):
                    logger.warning(
                        "Worker task failed: [%s] %s", type(result).__name__, result
                    )
            pbar.close()
