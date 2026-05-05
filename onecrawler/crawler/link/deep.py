import logging
import asyncio
from collections import deque
from typing import Optional
from urllib.parse import urlparse
from ...browser import GoogleChrome
from .helper import (
    wildcard_link_match,
    human_delay,
    human_scroll,
    human_mouse_move,
)
from ...config.brawser import BrowserSettings
from .classifier import LinkClassifierPipeline

logger = logging.getLogger(__name__)


class BFScheduler:
    def __init__(self, base_url: str, max_queue_size: int = 5000):
        self.queue = deque([base_url])
        self.priority = deque()

        self.visited = set()
        self.in_queue = set([base_url])

        self.lock = asyncio.Lock()
        self.max_queue_size = max_queue_size

    async def has_next(self):
        async with self.lock:
            return bool(self.queue or self.priority)

    async def next(self) -> Optional[str]:
        async with self.lock:
            if self.priority:
                return self.priority.popleft()
            return self.queue.popleft()

    async def add(self, url: str, priority: bool = False) -> None:
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

    def mark_visited(self, url: str) -> None:
        self.visited.add(url)


class BrowserPool:
    def __init__(self, browser: GoogleChrome, size: int):
        self.browser = browser
        self.size = size
        self.pages = asyncio.Queue()

    async def init(self) -> None:
        await self.browser.start()
        for _ in range(self.size):
            page = await self.browser.new_page()
            await self.pages.put(page)

    async def get(self) -> any:
        return await self.pages.get()

    async def release(self, page):
        await self.pages.put(page)

    async def close(self):
        while not self.pages.empty():
            page = await self.pages.get()
            await page.close()

        await self.browser.close()


class LinkSpider:
    def __init__(self, base_prefix: str):
        self.base_prefix = base_prefix

    async def parse(self, page):
        raw_links = await page.eval_on_selector_all(
            "a", "els => els.map(e => e.href).filter(Boolean)"
        )

        links = []
        for link in raw_links:
            if isinstance(link, dict):
                link = link.get("href")

            if isinstance(link, str) and link.startswith(self.base_prefix):
                links.append(link)

        return links


# -------------------------------
# Main BFS extractor
# -------------------------------
async def bfs_link_extractor(
    base_url: str,
    num_links: int = 50,
    include_pattern: list[str] | None = None,
    concurrency: int = 5,
    link_classifier_enabled: bool = False,
    max_scroll_limit: int = 5,
    browser_settings: Optional["BrowserSettings"] = None,
    disable_human_behaviors: bool = False,
):
    logger.info(
        f"Starting deep link extraction from {base_url} with concurrency {concurrency}"
    )

    browser = GoogleChrome(browser_settings or BrowserSettings())
    scheduler = BFScheduler(base_url)
    classifier = LinkClassifierPipeline(link_classifier_enabled)

    parsed = urlparse(base_url)
    base_prefix = f"{parsed.scheme}://{parsed.netloc}"

    spider = LinkSpider(base_prefix)

    browser_pool = BrowserPool(browser, concurrency)
    await browser_pool.init()

    results = []
    results_set = set()

    results_lock = asyncio.Lock()
    stop_event = asyncio.Event()

    async def worker():
        while True:
            if stop_event.is_set():
                return

            if not await scheduler.has_next():
                await asyncio.sleep(0.1)
                continue

            url = await scheduler.next()

            if not url or url in scheduler.visited:
                continue

            scheduler.mark_visited(url)

            page = await browser_pool.get()

            try:
                max_retries = browser_settings.runtime.max_retries

                for attempt in range(max_retries):
                    try:
                        await page.goto(
                            url,
                            wait_until="domcontentloaded",
                            timeout=browser_settings.runtime.timeout
                            if browser_settings
                            else 30000,
                        )
                        break
                    except Exception as e:
                        if "Timeout" in str(e) and attempt < max_retries - 1:
                            await asyncio.sleep(1.5)
                            continue
                        raise

                if not disable_human_behaviors:
                    await human_delay()

                if not disable_human_behaviors:
                    await human_scroll(page, max_scrolls=max_scroll_limit)

                links = await spider.parse(page)

                if not disable_human_behaviors:
                    await human_mouse_move(page)
                    await human_delay(0.1, 1.0)

                filtered_links = list(
                    {link for link in links if link.startswith(base_prefix)}
                )

                if not filtered_links:
                    continue

                for link in filtered_links:
                    await scheduler.add(link)

                    if include_pattern:
                        if not wildcard_link_match(link, base_prefix, include_pattern):
                            continue

                    async with results_lock:
                        if link not in results_set:
                            results_set.add(link)
                            results.append(link)

                            if len(results) >= num_links:
                                stop_event.set()
                                return

            except Exception as e:
                logger.error(f"Error processing {url}: {e}")

            finally:
                await browser_pool.release(page)

    tasks = [asyncio.create_task(worker()) for _ in range(concurrency)]

    await asyncio.gather(*tasks, return_exceptions=True)
    await browser_pool.close()

    logger.info(f"Extraction completed, found {len(results)} links")

    return results
