import asyncio
import logging
from contextlib import suppress
from typing import Optional, Set

from playwright.async_api import Page

logger = logging.getLogger(__name__)


class BrowserPoolExhausted(RuntimeError):
    """Raised by ``acquire()`` once every slot has permanently failed to replenish."""


class BrowserPool:
    """A pool of browser pages for concurrent crawling.

    Each slot is used for exactly one URL by convention (workers acquire a
    page, navigate/parse once, then release it) so ``release()`` closes the
    used page and replaces it with a freshly created one rather than putting
    the same page back. This lets proxies configured on the browser's
    ``ProxyPool`` rotate across requests instead of being pinned to whichever
    proxy each of the ``size`` slots happened to get at ``init()`` time.

    If creating a replacement page fails, the slot is retried in the
    background with capped exponential backoff for up to ``replenish_budget``
    seconds before that slot is given up on — so a transient proxy/network
    blip doesn't permanently shrink the pool. If every slot in the pool ends
    up permanently lost this way (the browser/proxy is genuinely down, not
    just flaky), further ``acquire()`` calls raise ``BrowserPoolExhausted``
    instead of blocking forever, so a permanent failure surfaces as a clear
    error rather than a silent hang.

    Attributes:
        browser (GoogleChrome): The browser instance to create pages from.
        size (int): The number of pages in the pool.
        pages (asyncio.Queue): A queue containing the available Page instances.
        replenish_budget (float): Seconds to keep retrying a lost slot before
            giving up on it.
    """

    def __init__(self, browser, size: int, replenish_budget: float = 120.0):
        self.browser = browser
        self.size = size
        self.replenish_budget = replenish_budget
        self.pages: asyncio.Queue = asyncio.Queue(maxsize=size)
        self._closed = False
        self._replenish_tasks: Set[asyncio.Task] = set()
        self._lost_slots = 0
        self._exhausted_event = asyncio.Event()
        self._last_error: Optional[Exception] = None

    async def init(self):
        for _ in range(self.size):
            page = await self.browser.new_page()
            await self.pages.put(page)

    async def acquire(self):
        get_task = asyncio.ensure_future(self.pages.get())
        exhausted_task = asyncio.ensure_future(self._exhausted_event.wait())

        done, pending = await asyncio.wait(
            {get_task, exhausted_task}, return_when=asyncio.FIRST_COMPLETED
        )
        for task in pending:
            task.cancel()

        if get_task in done:
            return get_task.result()

        raise BrowserPoolExhausted(
            f"Browser pool has no working slots left: {self._last_error}"
        )

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
                "background for up to %ss: %s",
                self.replenish_budget,
                e,
            )
            task = asyncio.create_task(self._replenish_with_budget())
            self._replenish_tasks.add(task)
            task.add_done_callback(self._replenish_tasks.discard)
            return

        if self._closed:
            with suppress(Exception):
                await fresh_page.close()
            return

        await self.pages.put(fresh_page)

    async def _replenish_with_budget(self) -> None:
        loop = asyncio.get_running_loop()
        deadline = loop.time() + self.replenish_budget
        delay = 1.0
        last_error: Optional[Exception] = None

        while not self._closed:
            remaining = deadline - loop.time()
            if remaining <= 0:
                self._lost_slots += 1
                self._last_error = last_error
                logger.error(
                    "Giving up replenishing browser pool slot after %ss "
                    "(%s/%s slot(s) now permanently lost): %s",
                    self.replenish_budget,
                    self._lost_slots,
                    self.size,
                    last_error,
                )
                if self._lost_slots >= self.size:
                    logger.error(
                        "All browser pool slots are permanently lost; "
                        "failing pending and future acquire() calls"
                    )
                    self._exhausted_event.set()
                return

            try:
                fresh_page = await self.browser.new_page()
            except Exception as e:
                last_error = e
                logger.warning("Still failed to replenish browser pool slot: %s", e)
                await asyncio.sleep(min(delay, remaining))
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
        self._exhausted_event.set()

        for task in list(self._replenish_tasks):
            task.cancel()
        if self._replenish_tasks:
            await asyncio.gather(*self._replenish_tasks, return_exceptions=True)

        while not self.pages.empty():
            page = await self.pages.get()
            with suppress(Exception):
                await page.close()
