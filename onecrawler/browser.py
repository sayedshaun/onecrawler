from playwright.async_api import async_playwright
from .config.brawser import BrowserSettings


class GoogleChrome:
    def __init__(self, config: BrowserSettings):
        self.config = config
        self.playwright = None
        self.context = None
        self._started = False

    async def start(self):
        if self._started:
            return

        self.playwright = await async_playwright().start()

        launch = self.config.launch
        context = self.config.context

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
            proxy=self.config.proxy.__dict__ if self.config.proxy else None,
        )

        self._started = True

    async def new_page(self):
        if not self._started:
            await self.start()

        page = await self.context.new_page()

        runtime = self.config.runtime
        page.set_default_timeout(runtime.action_timeout)
        page.set_default_navigation_timeout(runtime.navigation_timeout)

        return page

    async def close(self):
        if self.context:
            await self.context.close()
            self.context = None

        if self.playwright:
            await self.playwright.stop()
            self.playwright = None

        self._started = False
