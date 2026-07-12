import asyncio
from contextlib import suppress
from typing import TYPE_CHECKING, Optional

from playwright.async_api import async_playwright

from .settings.browser import BrowserSettings

if TYPE_CHECKING:
    # Only used for type hints. Importing these for real at module load time
    # creates a circular import: settings/crawler.py imports ProxyPool from
    # onecrawler.proxy.pool at runtime (to build a ProxyPool from Settings),
    # and onecrawler.proxy.pool importing settings.proxy here would re-enter
    # the still-initializing settings package before ProxyPool is defined.
    from .proxy.pool import ProxyPool
    from .settings.proxy import ProxySettings


class GoogleChrome:
    """A wrapper for managing a Google Chrome (Chromium) instance via Playwright.

    This class handles the lifecycle of a Playwright browser, including startup,
    context creation with custom settings, and safe shutdown.

    When ``proxy_pool`` contains more than one proxy, each page returned by
    ``new_page()`` gets its own dedicated browser context bound to the next
    proxy in the pool (Playwright only supports assigning a proxy at the
    context level, not per-request), so proxies genuinely rotate across
    pages/requests instead of being pinned once for the whole session. The
    dedicated context is closed automatically when the page is closed. With
    zero or one proxy, pages share a single default context as before.

    Attributes:
        settings (BrowserSettings): Configuration for the browser and context.
        proxy_pool (Optional[ProxyPool]): Pool of proxies to rotate across pages.
        playwright (Optional[Playwright]): The Playwright instance.
        browser (Optional[Browser]): The Chromium browser instance.
        context (Optional[BrowserContext]): The default (shared) browser context.
    """

    def __init__(
        self, settings: BrowserSettings, proxy_pool: Optional["ProxyPool"] = None
    ):
        """Initializes the GoogleChrome wrapper.

        Args:
            settings (BrowserSettings): The settings to use for the browser.
            proxy_pool (Optional[ProxyPool]): Proxies to rotate across pages.
        """
        self.settings = settings
        self.proxy_pool = proxy_pool
        self.playwright = None
        self.browser = None
        self.context = None
        self._started = False
        self._closed = False
        self._lifecycle_lock = asyncio.Lock()

    def _rotates_proxies(self) -> bool:
        """Whether new_page() creates a dedicated per-page context instead of
        sharing the default one (i.e. more than one proxy is configured)."""
        return bool(self.proxy_pool and len(self.proxy_pool.proxies) > 1)

    def _context_kwargs(self, proxy: Optional["ProxySettings"]) -> dict:
        """Builds the ``browser.new_context()`` kwargs for the given proxy."""
        return dict(
            viewport=self.settings.viewport,
            screen=self.settings.screen,
            no_viewport=self.settings.no_viewport,
            locale=self.settings.locale,
            timezone_id=self.settings.timezone_id,
            user_agent=self.settings.user_agent,
            java_script_enabled=self.settings.java_script_enabled,
            bypass_csp=self.settings.bypass_csp,
            ignore_https_errors=self.settings.ignore_https_errors,
            extra_http_headers=self.settings.extra_http_headers,
            offline=self.settings.offline,
            geolocation=self.settings.geolocation,
            permissions=self.settings.permissions,
            storage_state=self.settings.storage_state,
            base_url=self.settings.base_url,
            proxy=proxy.as_playwright() if proxy else None,
        )

    async def start(self):
        """Starts the browser and creates a new context.

        If the browser is already started, this method does nothing. It initializes
        the Playwright instance, launches Chromium, and sets up the browser context
        based on the provided settings.

        Returns:
            None
        """
        async with self._lifecycle_lock:
            if self._started:
                return

            self.playwright = await async_playwright().start()

            self.browser = await self.playwright.chromium.launch(
                headless=self.settings.headless,
                slow_mo=self.settings.slow_mo,
                args=self.settings.args,
                executable_path=self.settings.executable_path,
                channel=self.settings.channel,
                env=self.settings.env,
            )

            default_proxy = self.settings.proxy
            if self.proxy_pool and self.proxy_pool.proxies:
                default_proxy = self.proxy_pool.next()

            self.context = await self.browser.new_context(
                **self._context_kwargs(default_proxy)
            )

            self._started = True
            self._closed = False

    async def new_page(self):
        """Creates and returns a new page.

        Automatically starts the browser if it hasn't been started yet. Sets
        default timeouts for actions and navigation as defined in settings.

        If ``proxy_pool`` has more than one proxy, the page is created in a
        brand-new context bound to the next proxy in the pool, so proxies
        rotate per page; that dedicated context is closed automatically when
        the page is closed. Otherwise the page is created in the shared
        default context.

        Returns:
            Page: A new Playwright Page instance.
        """
        if not self._started:
            await self.start()

        async with self._lifecycle_lock:
            if not self._started or self.context is None:
                raise RuntimeError("Browser context is not available")

            browser = self.browser
            shared_context = self.context

        dedicated_context = None
        if self._rotates_proxies():
            proxy = self.proxy_pool.next()
            dedicated_context = await browser.new_context(**self._context_kwargs(proxy))
            try:
                page = await dedicated_context.new_page()
            except Exception:
                with suppress(Exception):
                    await dedicated_context.close()
                raise
        else:
            page = await shared_context.new_page()

        if dedicated_context is not None:
            original_close = page.close

            async def _close_with_context(*args, **kwargs):
                try:
                    await original_close(*args, **kwargs)
                finally:
                    with suppress(Exception):
                        await dedicated_context.close()

            page.close = _close_with_context

        page.set_default_timeout(self.settings.timeout)
        page.set_default_navigation_timeout(self.settings.timeout)

        return page

    async def close(self):
        """Safely closes the browser context, browser, and Playwright instance.

        Ensures all resources are released. If already closed, this method does nothing.

        Returns:
            None
        """
        async with self._lifecycle_lock:
            if self._closed:
                return

            self._closed = True

            if self.context:
                with suppress(Exception):
                    await self.context.close()
                self.context = None

            if self.browser:
                with suppress(Exception):
                    await self.browser.close()
                self.browser = None

            if self.playwright:
                with suppress(Exception):
                    await self.playwright.stop()
                self.playwright = None

            self._started = False
