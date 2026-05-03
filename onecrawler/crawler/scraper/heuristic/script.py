import json
import asyncio
import trafilatura
from ....browser import GoogleChrome
from ..base import BaseStrategy


class HeuristicStrategy(BaseStrategy):
    def __init__(self, output_format: str = "json", browser_config=None):
        self.output_format = output_format
        self.browser_config = browser_config
        self.browser = None

    async def __aenter__(self):
        if self.browser_config:
            self.browser = GoogleChrome(config=self.browser_config)
            await self.browser.start()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self.browser:
            await self.browser.close()

    async def extract(self, url: str):
        if self.browser:
            # Use browser to fetch HTML
            page = await self.browser.new_page()
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                html = await page.content()
            finally:
                await page.close()
        else:
            # Fallback to direct HTTP request
            html = await asyncio.to_thread(trafilatura.fetch_url, url)

        if not html:
            return None

        extracted = await asyncio.to_thread(
            trafilatura.extract,
            html,
            output_format="json",
            include_tables=True,
            include_links=True,
            include_comments=True,
            with_metadata=True,
            include_formatting=True,
        )

        if not extracted:
            return None

        if self.output_format == "json":
            try:
                data = json.loads(extracted)
                return data
            except Exception as e:
                raise ValueError(f"Failed to parse extracted JSON: {e}")

        return extracted
