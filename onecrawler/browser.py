import asyncio
from contextlib import suppress

from playwright.async_api import async_playwright

from .settings.browser import BrowserSettings


class GoogleChrome:
    """A wrapper for managing a Google Chrome (Chromium) instance via Playwright.

    This class handles the lifecycle of a Playwright browser, including startup,
    context creation with custom settings, and safe shutdown.

    Attributes:
        settings (BrowserSettings): Configuration for the browser and context.
        playwright (Optional[Playwright]): The Playwright instance.
        browser (Optional[Browser]): The Chromium browser instance.
        context (Optional[BrowserContext]): The browser context.
    """

    def __init__(self, settings: BrowserSettings):
        """Initializes the GoogleChrome wrapper.

        Args:
            settings (BrowserSettings): The settings to use for the browser.
        """
        self.settings = settings
        self.playwright = None
        self.browser = None
        self.context = None
        self._started = False
        self._closed = False
        self._lifecycle_lock = asyncio.Lock()

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

            self.context = await self.browser.new_context(
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
                proxy=self.settings.proxy.as_playwright() if self.settings.proxy else None,
            )

            self._started = True
            self._closed = False

    async def new_page(self):
        """Creates and returns a new page within the current context.

        Automatically starts the browser if it hasn't been started yet. Sets
        default timeouts for actions and navigation as defined in settings.

        Returns:
            Page: A new Playwright Page instance.
        """
        if not self._started:
            await self.start()

        async with self._lifecycle_lock:
            if not self._started or self.context is None:
                raise RuntimeError("Browser context is not available")

            page = await self.context.new_page()

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
