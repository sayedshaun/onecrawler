import asyncio
import logging
from contextlib import suppress

from playwright.async_api import Page

logger = logging.getLogger(__name__)


class BrowserPool:
    """A pool of browser pages for concurrent crawling.

    Each slot is used for exactly one URL by convention (workers acquire a
    page, navigate/parse once, then release it) so ``release()`` closes the
    used page and replaces it with a freshly created one rather than putting
    the same page back. This lets proxies configured on the browser's
    ``ProxyPool`` rotate across requests instead of being pinned to whichever
    proxy each of the ``size`` slots happened to get at ``init()`` time.

    Attributes:
        browser (GoogleChrome): The browser instance to create pages from.
        size (int): The number of pages in the pool.
        pages (asyncio.Queue): A queue containing the available Page instances.
    """

    def __init__(self, browser, size: int):
        self.browser = browser
        self.size = size
        self.pages = asyncio.Queue(maxsize=size)
        self._closed = False
        self._replenish_tasks: set = set()

    async def init(self):
        for _ in range(self.size):
            page = await self.browser.new_page()
            await self.pages.put(page)

    async def acquire(self):
        return await self.pages.get()

    async def release(self, page: Page) -> None:
        with suppress(Exception):
            await page.close()

        if self._closed:
            return

        try:
            fresh_page = await self.browser.new_page()
        except Exception as e:
            logger.warning(
                "Failed to replenish browser pool slot, retrying in the "
                "background until it recovers: %s",
                e,
            )
            task = asyncio.create_task(self._replenish_until_success())
            self._replenish_tasks.add(task)
            task.add_done_callback(self._replenish_tasks.discard)
            return

        if self._closed:
            with suppress(Exception):
                await fresh_page.close()
            return

        await self.pages.put(fresh_page)

    async def _replenish_until_success(self) -> None:
        """Keeps retrying to create a replacement page for a lost slot.

        Never gives up: a slot must always eventually be restored, or a
        permanently empty pool leaves workers blocked forever in
        ``acquire()``. Backoff is capped so a persistently broken
        browser/proxy doesn't spin tightly, but retries continue for as long
        as the pool is open.
        """
        delay = 1
        while not self._closed:
            try:
                fresh_page = await self.browser.new_page()
            except Exception as e:
                logger.warning("Still failed to replenish browser pool slot: %s", e)
                await asyncio.sleep(delay)
                delay = min(delay * 2, 30)
                continue

            if self._closed:
                with suppress(Exception):
                    await fresh_page.close()
                return

            await self.pages.put(fresh_page)
            return

    async def close(self):
        self._closed = True

        for task in list(self._replenish_tasks):
            task.cancel()
        if self._replenish_tasks:
            await asyncio.gather(*self._replenish_tasks, return_exceptions=True)

        while not self.pages.empty():
            page = await self.pages.get()
            with suppress(Exception):
                await page.close()
