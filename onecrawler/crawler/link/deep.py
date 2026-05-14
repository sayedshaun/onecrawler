import asyncio
import logging
from collections import deque
from typing import Optional
from urllib.parse import urldefrag

from ...settings.simulation import HumanBehaviorSettings
from .helper import human_delay, human_mouse_move, human_scroll, wildcard_link_match

logger = logging.getLogger(__name__)


class BFScheduler:
    def __init__(self, base_url: str, max_queue_size: int = 5000):
        self.queue = deque([base_url])
        self.priority = deque()

        self.visited = set()
        self.in_queue = {base_url}

        self.max_queue_size = max_queue_size
        self.lock = asyncio.Lock()

    async def has_next(self) -> bool:
        async with self.lock:
            return bool(self.queue or self.priority)

    async def next(self) -> str | None:
        async with self.lock:
            if self.priority:
                return self.priority.popleft()
            if self.queue:
                return self.queue.popleft()
            return None

    async def add(self, url: str, priority: bool = False):
        async with self.lock:
            if url in self.visited or url in self.in_queue:
                return

            if len(self.in_queue) >= self.max_queue_size:
                return

            self.in_queue.add(url)

            if priority:
                self.priority.append(url)
            else:
                self.queue.append(url)

    def mark_visited(self, url: str):
        self.visited.add(url)
        self.in_queue.discard(url)


class BrowserPool:
    def __init__(self, browser, size: int):
        self.browser = browser
        self.size = size
        self.pages = asyncio.Queue(maxsize=size)
        self._closed = False

    async def init(self):
        # NOTE: browser.start() must already be called before BrowserPool.init()
        # We only create pages here — do NOT call self.browser.start() again.
        for _ in range(self.size):
            page = await self.browser.new_page()
            await self.pages.put(page)

    async def acquire(self):
        return await self.pages.get()

    async def release(self, page):
        if not self._closed:
            await self.pages.put(page)

    async def close(self):
        self._closed = True
        while not self.pages.empty():
            page = await self.pages.get()
            await page.close()
        # NOTE: do NOT close the browser here — the engine owns it


class LinkSpider:
    def __init__(self, base_prefix: str):
        self.base_prefix = base_prefix

    async def parse(self, page):
        raw = await page.eval_on_selector_all(
            "a", "els => els.map(e => e.href).filter(Boolean)"
        )
        return [
            urldefrag(link).url
            for link in raw
            if isinstance(link, str) and link.startswith(self.base_prefix)
        ]


class BFSRuntime:
    def __init__(
        self,
        scheduler,
        pool,
        spider,
        base_prefix: str,
        max_links: int,
        human_behavior_settings: HumanBehaviorSettings,
        include_pattern: Optional[list] = None,
        enable_human_behaviors: bool = False,
        concurrency: int = 5,
        streaming: bool = False,
    ):
        self.scheduler = scheduler
        self.pool = pool
        self.spider = spider

        self.base_prefix = base_prefix
        self.max_links = max_links
        self.include_pattern = include_pattern
        self.enable_human_behaviors = enable_human_behaviors
        self.human_behavior_settings = human_behavior_settings
        self.concurrency = concurrency

        self.stop_event = asyncio.Event()

        self.results = []
        self.results_set = set()
        self.lock = asyncio.Lock()

        # Track how many workers are actively processing a URL
        self._active_workers = 0
        self._active_lock = asyncio.Lock()
        self.stream_queue = asyncio.Queue(maxsize=1000)
        self.streaming = streaming

    async def worker(self):
        while not self.stop_event.is_set():
            async with self._active_lock:
                url = await self.scheduler.next()

                if url is None:
                    # Queue is empty. If no worker has a reserved URL, crawling is done.
                    if self._active_workers == 0:
                        self.stop_event.set()
                        return

                else:
                    self._active_workers += 1

            if url is None:
                # Another worker is still processing and may enqueue more URLs.
                # Wait a bit and retry instead of busy-spinning.
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

                    await self.scheduler.add(link)

                    async with self.lock:
                        if link in self.results_set:
                            continue

                        self.results_set.add(link)

                        if self.streaming:
                            await self.stream_queue.put(link)
                        else:
                            self.results.append(link)

                        logger.info(
                            "Discovered %s/%s links; link=%s",
                            len(self.results_set),
                            self.max_links,
                            link,
                        )

                        if len(self.results_set) >= self.max_links:
                            self.stop_event.set()
                            return

            finally:
                await self.pool.release(page)
                async with self._active_lock:
                    self._active_workers -= 1

    async def run(self):
        tasks = [asyncio.create_task(self.worker()) for _ in range(self.concurrency)]

        await asyncio.gather(*tasks, return_exceptions=True)
        return self.results

    async def stream(self):
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
