import asyncio
from collections import deque
from typing import Optional
from .helper import wildcard_link_match, human_delay, human_scroll, human_mouse_move


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
                return  # backpressure protection

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
        await self.browser.start()
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

        await self.browser.close()


class LinkSpider:
    def __init__(self, base_prefix: str):
        self.base_prefix = base_prefix

    async def parse(self, page):
        raw = await page.eval_on_selector_all(
            "a", "els => els.map(e => e.href).filter(Boolean)"
        )

        return [
            link
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
        include_pattern: Optional[list] = None,
        disable_human_behaviors: bool = False,
        concurrency: int = 5,
    ):
        self.scheduler = scheduler
        self.pool = pool
        self.spider = spider

        self.base_prefix = base_prefix
        self.max_links = max_links
        self.include_pattern = include_pattern
        self.disable_human_behaviors = disable_human_behaviors
        self.concurrency = concurrency

        self.stop_event = asyncio.Event()

        self.results = []
        self.results_set = set()
        self.lock = asyncio.Lock()

    async def worker(self):
        while not self.stop_event.is_set():
            url = await self.scheduler.next()

            if not url:
                continue

            if url in self.scheduler.visited:
                continue

            self.scheduler.mark_visited(url)

            page = await self.pool.acquire()

            try:
                await page.goto(
                    url,
                    wait_until="domcontentloaded",
                )

                if not self.disable_human_behaviors:
                    await human_delay()
                    await human_scroll(page)

                links = await self.spider.parse(page)

                if not self.disable_human_behaviors:
                    await human_mouse_move(page)

                for link in links:
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
                        self.results.append(link)

                        if len(self.results) >= self.max_links:
                            self.stop_event.set()
                            return

            finally:
                await self.pool.release(page)

    async def run(self):
        tasks = [asyncio.create_task(self.worker()) for _ in range(self.concurrency)]
        await asyncio.gather(*tasks, return_exceptions=True)
        return self.results
