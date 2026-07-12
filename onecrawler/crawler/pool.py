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
            logger.warning("Failed to replenish browser pool slot: %s", e)
            return

        if self._closed:
            with suppress(Exception):
                await fresh_page.close()
            return

        await self.pages.put(fresh_page)

    async def close(self):
        self._closed = True
        while not self.pages.empty():
            page = await self.pages.get()
            with suppress(Exception):
                await page.close()
