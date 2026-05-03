import logging
import asyncio
from collections import deque
from typing import Optional
from urllib.parse import urlparse
from ...browser import GoogleChrome
from .helper import wildcard_link_match, human_delay, human_scroll, human_mouse_move
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
        links = await page.eval_on_selector_all(
            "a", "els => els.map(e => e.href).filter(Boolean)"
        )

        return [link for link in links if link.startswith(self.base_prefix)]


async def bfs_link_extractor(
    base_url: str,
    num_links: int = 50,
    include_pattern: list[str] | None = None,
    concurrency: int = 5,
    link_classifier_with_bert: bool = False,
    browser_settings: Optional[BrowserSettings] = None,
):
    logger.info(
        f"Starting deep link extraction from {base_url} with concurrency {concurrency}"
    )

    browser = GoogleChrome(browser_settings or BrowserSettings())
    scheduler = BFScheduler(base_url)
    classifier = LinkClassifierPipeline(enabled=link_classifier_with_bert)
    parsed = urlparse(base_url)
    base_prefix = f"{parsed.scheme}://{parsed.netloc}"

    spider = LinkSpider(base_prefix)

    browser_pool = BrowserPool(browser, concurrency)
    await browser_pool.init()
    logger.debug("Browser pool initialized")

    results = []
    results_set = set()

    async def worker():
        while await scheduler.has_next():
            if len(results) >= num_links:
                return

            url = await scheduler.next()

            if url in scheduler.visited:
                continue

            scheduler.mark_visited(url)
            logger.debug(f"Processing URL: {url}")

            page = await browser_pool.get()

            try:
                await page.goto(url, wait_until="domcontentloaded")

                # Human-like behavior to avoid bot detection
                await human_delay()
                await human_scroll(page, max_scrolls=3)
                await human_mouse_move(page)
                await human_delay(0.5, 1.0)

                links = await spider.parse(page)
                logger.debug(f"Extracted {len(links)} links from {url}")

                for link in links:
                    if not link.startswith(base_prefix):
                        continue

                    await scheduler.add(link)

                    if not await classifier.is_valid(link):
                        logger.debug(f"Link filtered by classifier: {link}")
                        continue

                    if include_pattern:
                        if not wildcard_link_match(link, base_prefix, include_pattern):
                            logger.debug(f"Link does not match pattern: {link}")
                            continue

                    if link not in results_set:
                        results_set.add(link)
                        results.append(link)
                        logger.debug(f"Added link to results: {link}")

                    if len(results) >= num_links:
                        break

            except Exception as e:
                logger.error(f"Error processing {url}: {e}")

            finally:
                await browser_pool.release(page)

    tasks = [asyncio.create_task(worker()) for _ in range(concurrency)]
    logger.info(f"Started {concurrency} worker tasks")

    await asyncio.gather(*tasks, return_exceptions=True)
    await browser_pool.close()
    logger.info(f"Deep extraction completed, found {len(results)} links")

    return results
