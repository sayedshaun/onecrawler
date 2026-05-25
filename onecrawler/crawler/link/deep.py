import asyncio
import logging
from collections import deque
from typing import AsyncGenerator, List, Optional, Set
from urllib.parse import urldefrag, urlparse

from playwright.async_api import Page

from ...settings.simulation import HumanBehaviorSettings
from .helper import human_delay, human_mouse_move, human_scroll, wildcard_link_match

logger = logging.getLogger(__name__)


class BFScheduler:
    """A scheduler for Breadth-First Search crawling.

    Manages a queue of URLs to visit, a priority queue for immediate visits,
    and a set of already visited URLs to avoid duplicates.

    Attributes:
        queue (deque): The main queue of URLs to visit.
        priority (deque): A high-priority queue for URLs.
        visited (Set[str]): Set of URLs that have already been processed.
        in_queue (Set[str]): Set of URLs currently in one of the queues.
        max_queue_size (int): Maximum allowed size for the queue.
    """

    def __init__(self, base_url: str, max_queue_size: int = 5000):
        """Initializes the BFScheduler.

        Args:
            base_url (str): The starting URL for the crawl.
            max_queue_size (int): Maximum number of URLs to keep in the queue.
        """
        self.queue: deque[str] = deque([base_url])
        self.priority: deque[str] = deque()

        self.visited: Set[str] = set()
        self.in_queue: Set[str] = {base_url}

        self.max_queue_size: int = max_queue_size
        self.lock: asyncio.Lock = asyncio.Lock()

    async def has_next(self) -> bool:
        """Checks if there are any URLs left to process.

        Returns:
            bool: True if there are URLs in either queue, False otherwise.
        """
        async with self.lock:
            return bool(self.queue or self.priority)

    async def next(self) -> Optional[str]:
        """Retrieves the next URL to visit and atomically marks it as visited.

        Marking visited here — inside the scheduler lock — eliminates the
        TOCTOU window that existed when next() and mark_visited() were
        separate operations. No two workers can ever dequeue the same URL.

        Returns:
            Optional[str]: The next URL, or None if queues are empty.
        """
        async with self.lock:
            if self.priority:
                url = self.priority.popleft()
            elif self.queue:
                url = self.queue.popleft()
            else:
                return None

            # Atomically mark as visited so no other worker can pick this URL up.
            self.visited.add(url)
            self.in_queue.discard(url)
            return url

    async def add(self, url: str, priority: bool = False):
        """Adds a new URL to the scheduler.

        Args:
            url (str): The URL to add.
            priority (bool): Whether to add it to the high-priority queue.
        """
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

    # mark_visited() is intentionally removed. Visiting is now done atomically
    # inside next(), so there is no longer a separate mark step.


class BrowserPool:
    """A pool of browser pages for concurrent crawling.

    Attributes:
        browser (GoogleChrome): The browser instance to create pages from.
        size (int): The number of pages in the pool.
        pages (asyncio.Queue): A queue containing the available Page instances.
    """

    def __init__(self, browser, size: int):
        """Initializes the BrowserPool.

        Args:
            browser: The GoogleChrome wrapper instance.
            size (int): Number of pages to maintain in the pool.
        """
        self.browser = browser
        self.size = size
        self.pages = asyncio.Queue(maxsize=size)
        self._closed = False

    async def init(self):
        """Initializes the pool by creating the specified number of pages."""
        # NOTE: browser.start() must already be called before BrowserPool.init()
        # We only create pages here — do NOT call self.browser.start() again.
        for _ in range(self.size):
            page = await self.browser.new_page()
            await self.pages.put(page)

    async def acquire(self):
        """Acquires a page from the pool.

        Returns:
            Page: A Playwright Page instance.
        """
        return await self.pages.get()

    async def release(self, page: Page) -> None:
        """Releases a page back into the pool.

        Args:
            page: The Playwright Page instance to release.
        """
        if not self._closed:
            await self.pages.put(page)

    async def close(self):
        """Closes all pages in the pool and marks the pool as closed."""
        self._closed = True
        while not self.pages.empty():
            page = await self.pages.get()
            await page.close()


class LinkSpider:
    """A spider responsible for extracting links from a web page.

    Attributes:
        base_prefix (str): The domain prefix to restrict link extraction to.
    """

    def __init__(self, base_prefix: str):
        self.base_prefix = base_prefix
        parsed = urlparse(base_prefix)
        self.base_scheme = parsed.scheme
        self.base_netloc = parsed.netloc.lower()

    def _same_origin(self, link: str) -> bool:
        parsed = urlparse(link)
        return (
            parsed.scheme == self.base_scheme
            and parsed.netloc.lower() == self.base_netloc
        )

    async def parse(self, page) -> List[str]:

        raw = await page.eval_on_selector_all(
            "a", "els => els.map(e => e.href).filter(Boolean)"
        )
        return [
            urldefrag(link).url
            for link in raw
            if isinstance(link, str) and self._same_origin(link)
        ]


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
    ):
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

        self.stop_event: asyncio.Event = asyncio.Event()

        self.results: List[str] = []
        self.results_set: Set[str] = set()
        self.lock: asyncio.Lock = asyncio.Lock()

        # Track how many workers are actively processing a URL
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
                    if self._active_workers == 0:
                        # Queue is empty and no worker holds a URL — done.
                        self.stop_event.set()
                        return
                    # Another worker is still processing; it may enqueue more.
                else:
                    self._active_workers += 1

            if url is None:
                await asyncio.sleep(0.2)
                continue

            page = await self.pool.acquire()

            try:
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

                        logger.info(
                            "Discovered %s/%s links; link=%s",
                            len(self.results_set),
                            self.max_links,
                            link,
                        )

                        if len(self.results_set) >= self.max_links:
                            self.stop_event.set()

                    # Enqueue outside the lock — scheduler has its own lock.
                    await self.scheduler.add(link)

                    if should_stream:
                        await self.stream_queue.put(link)

                    if self.stop_event.is_set():
                        break

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
        await asyncio.gather(*tasks)
        return self.results

    async def stream(self) -> AsyncGenerator[str, None]:
        """Starts the workers and yields discovered URLs as they are found.

        Yields:
            str: Discovered absolute URL.
        """
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
            await asyncio.gather(*tasks, return_exceptions=True)
