import asyncio

from playwright.async_api import Page


class BrowserPool:
    """A pool of browser pages for concurrent crawling.

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
        if not self._closed:
            await self.pages.put(page)

    async def close(self):
        self._closed = True
        while not self.pages.empty():
            page = await self.pages.get()
            await page.close()
