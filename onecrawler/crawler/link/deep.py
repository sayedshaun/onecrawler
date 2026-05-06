# import logging
# import asyncio
# from collections import deque
# from typing import Optional
# from urllib.parse import urlparse
# from ...browser import GoogleChrome
# from .helper import (
#     wildcard_link_match,
#     human_delay,
#     human_scroll,
#     human_mouse_move,
# )
# from ...config.brawser import BrowserSettings

# logger = logging.getLogger(__name__)


# class BFScheduler:
#     def __init__(self, base_url: str, max_queue_size: int = 5000):
#         self.queue = deque([base_url])
#         self.priority = deque()

#         self.visited = set()
#         self.in_queue = set([base_url])

#         self.lock = asyncio.Lock()
#         self.max_queue_size = max_queue_size

#     async def has_next(self):
#         async with self.lock:
#             return bool(self.queue or self.priority)

#     async def next(self) -> Optional[str]:
#         async with self.lock:
#             if self.priority:
#                 return self.priority.popleft()
#             return self.queue.popleft()

#     async def add(self, url: str, priority: bool = False) -> None:
#         async with self.lock:
#             if url in self.visited or url in self.in_queue:
#                 return

#             if len(self.in_queue) >= self.max_queue_size:
#                 return

#             self.in_queue.add(url)

#             if priority:
#                 self.priority.append(url)
#             else:
#                 self.queue.append(url)

#     def mark_visited(self, url: str) -> None:
#         self.visited.add(url)


# class BrowserPool:
#     def __init__(self, browser: GoogleChrome, size: int):
#         self.browser = browser
#         self.size = size
#         self.pages = asyncio.Queue()

#     async def init(self) -> None:
#         await self.browser.start()
#         for _ in range(self.size):
#             page = await self.browser.new_page()
#             await self.pages.put(page)

#     async def get(self) -> any:
#         return await self.pages.get()

#     async def release(self, page):
#         await self.pages.put(page)

#     async def close(self):
#         while not self.pages.empty():
#             page = await self.pages.get()
#             await page.close()

#         await self.browser.close()


# class LinkSpider:
#     def __init__(self, base_prefix: str):
#         self.base_prefix = base_prefix

#     async def parse(self, page):
#         raw_links = await page.eval_on_selector_all(
#             "a", "els => els.map(e => e.href).filter(Boolean)"
#         )

#         links = []
#         for link in raw_links:
#             if isinstance(link, dict):
#                 link = link.get("href")

#             if isinstance(link, str) and link.startswith(self.base_prefix):
#                 links.append(link)

#         return links


# async def bfs_link_extractor(
#     base_url: str,
#     num_links: int = 50,
#     include_pattern: list[str] | None = None,
#     concurrency: int = 5,
#     max_scroll_limit: int = 5,
#     browser_settings: Optional["BrowserSettings"] = None,
#     disable_human_behaviors: bool = False,
# ):
#     logger.info(
#         f"Starting deep link extraction from {base_url} with concurrency {concurrency}"
#     )

#     browser = GoogleChrome(browser_settings or BrowserSettings())
#     scheduler = BFScheduler(base_url)

#     parsed = urlparse(base_url)
#     base_prefix = f"{parsed.scheme}://{parsed.netloc}"

#     spider = LinkSpider(base_prefix)

#     browser_pool = BrowserPool(browser, concurrency)
#     await browser_pool.init()

#     results = []
#     results_set = set()

#     results_lock = asyncio.Lock()
#     stop_event = asyncio.Event()

#     async def worker():
#         while True:
#             if stop_event.is_set():
#                 return

#             if not await scheduler.has_next():
#                 await asyncio.sleep(0.1)
#                 continue

#             url = await scheduler.next()

#             if not url or url in scheduler.visited:
#                 continue

#             scheduler.mark_visited(url)

#             page = await browser_pool.get()

#             try:
#                 max_retries = browser_settings.runtime.max_retries

#                 for attempt in range(max_retries):
#                     try:
#                         await page.goto(
#                             url,
#                             wait_until="domcontentloaded",
#                             timeout=browser_settings.runtime.timeout
#                             if browser_settings
#                             else 30000,
#                         )
#                         break
#                     except Exception as e:
#                         if "Timeout" in str(e) and attempt < max_retries - 1:
#                             await asyncio.sleep(1.5)
#                             continue
#                         raise

#                 if not disable_human_behaviors:
#                     await human_delay()

#                 if not disable_human_behaviors:
#                     await human_scroll(page, max_scrolls=max_scroll_limit)

#                 links = await spider.parse(page)

#                 if not disable_human_behaviors:
#                     await human_mouse_move(page)
#                     await human_delay(0.1, 1.0)

#                 filtered_links = list(
#                     {link for link in links if link.startswith(base_prefix)}
#                 )

#                 if not filtered_links:
#                     continue

#                 for link in filtered_links:
#                     await scheduler.add(link)

#                     if include_pattern:
#                         if not wildcard_link_match(link, base_prefix, include_pattern):
#                             continue

#                     async with results_lock:
#                         if link not in results_set:
#                             results_set.add(link)
#                             results.append(link)

#                             if len(results) >= num_links:
#                                 stop_event.set()
#                                 return

#             except Exception as e:
#                 logger.error(f"Error processing {url}: {e}")

#             finally:
#                 await browser_pool.release(page)

#     tasks = [asyncio.create_task(worker()) for _ in range(concurrency)]

#     await asyncio.gather(*tasks, return_exceptions=True)
#     await browser_pool.close()

#     logger.info(f"Extraction completed, found {len(results)} links")

#     return results


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
                await asyncio.sleep(0.05)
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
