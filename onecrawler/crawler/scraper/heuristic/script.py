import asyncio
import json

import trafilatura


class HeuristicStrategy:
    def __init__(self, output_format: str = "json", browser=None):
        self.output_format = output_format
        self.browser = browser

    async def extract(self, url: str):
        if self.browser:
            page = await self.browser.new_page()
            try:
                await page.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=30000,
                )
                html = await page.content()
            finally:
                await page.close()
        else:
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
                return json.loads(extracted)
            except Exception as e:
                raise ValueError(f"Failed to parse extracted JSON: {e}")

        return extracted
