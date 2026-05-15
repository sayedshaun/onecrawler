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

    async def start(self):
        """Starts the browser and creates a new context.

        If the browser is already started, this method does nothing. It initializes
        the Playwright instance, launches Chromium, and sets up the browser context
        based on the provided settings.

        Returns:
            None
        """
        if self._started:
            return

        self.playwright = await async_playwright().start()

        launch = self.settings.launch
        context = self.settings.context

        self.browser = await self.playwright.chromium.launch(
            headless=launch.headless,
            slow_mo=launch.slow_mo,
            args=launch.args,
            executable_path=launch.executable_path,
            channel=launch.channel,
            env=launch.env,
        )

        self.context = await self.browser.new_context(
            viewport=context.viewport,
            screen=context.screen,
            no_viewport=context.no_viewport,
            locale=context.locale,
            timezone_id=context.timezone_id,
            user_agent=context.user_agent,
            java_script_enabled=context.java_script_enabled,
            bypass_csp=context.bypass_csp,
            ignore_https_errors=context.ignore_https_errors,
            extra_http_headers=context.extra_http_headers,
            offline=context.offline,
            geolocation=context.geolocation,
            permissions=context.permissions,
            storage_state=context.storage_state,
            base_url=context.base_url,
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

        page = await self.context.new_page()

        runtime = self.settings.runtime
        page.set_default_timeout(runtime.action_timeout)
        page.set_default_navigation_timeout(runtime.navigation_timeout)

        return page

    async def close(self):
        """Safely closes the browser context, browser, and Playwright instance.

        Ensures all resources are released. If already closed, this method does nothing.

        Returns:
            None
        """
        if self._closed:
            return

        self._closed = True

        # Close context safely
        if self.context:
            with suppress(Exception):
                await self.context.close()
            self.context = None

        # Close browser
        if self.browser:
            with suppress(Exception):
                await self.browser.close()
            self.browser = None

        # Stop playwright
        if self.playwright:
            with suppress(Exception):
                await self.playwright.stop()
            self.playwright = None

        self._started = False
