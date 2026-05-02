from playwright.async_api import async_playwright
from .config.brawser import BrowserSettings


class BrowserManager:
    def __init__(self, config: BrowserSettings):
        self.config = config
        self.playwright = None
        self.context = None
        self._started = False

    async def start(self):
        self.playwright = await async_playwright().start()

        self.context = await self.playwright.chromium.launch_persistent_context(
            user_data_dir=self.config.user_data_dir,
            headless=self.config.headless,
            slow_mo=self.config.slow_mo,
            viewport=self.config.viewport,
            locale=self.config.locale,
            timezone_id=self.config.timezone_id,
            user_agent=self.config.user_agent,
            ignore_https_errors=self.config.ignore_https_errors,
            java_script_enabled=self.config.java_script_enabled,
            bypass_csp=self.config.bypass_csp,
            args=self.config.args,
            proxy=self.config.proxy,
        )

        self._started = True

    async def new_page(self):
        if not self._started:
            raise RuntimeError("Browser not started. Call await browser.start() first.")

        page = await self.context.new_page()
        page.set_default_timeout(self.config.timeout)
        return page

    async def close(self):
        self._started = False

        if self.context:
            await self.context.close()
        if self.playwright:
            await self.playwright.stop()
