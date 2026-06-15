import asyncio
import contextlib
import json
from typing import Any, Optional

import trafilatura

from ...navigation import goto


class HeuristicStrategy:
    """Strategy for extracting content using structural heuristics.

    Uses the `trafilatura` library to identify and extract the main content
    from a web page. Can optionally use a browser to render the page before
    extraction.

    Attributes:
        settings (Settings): Configuration settings.
        browser (Optional[GoogleChrome]): Browser instance for rendering.
    """

    def __init__(self, settings: Any, browser: Any = None):
        self.settings = settings
        self.browser = browser

    async def extract(self, url: str) -> Optional[Any]:
        if self.browser:
            page = await self.browser.new_page()
            try:
                await goto(
                    page,
                    url,
                    wait_until=self.settings.browser_settings.runtime.wait_until,
                    timeout=self.settings.browser_settings.runtime.timeout,
                )
                html = await page.content()
            finally:
                with contextlib.suppress(Exception):
                    await page.close()
        else:
            html = await asyncio.to_thread(trafilatura.fetch_url, url)

        if not html:
            return None

        extracted = await asyncio.to_thread(
            trafilatura.extract,
            html,
            output_format=self.settings.scraping_output_format,
            include_tables=True,
            include_links=True,
            include_comments=True,
            with_metadata=True,
            include_formatting=True,
        )

        if not extracted:
            return None

        if self.settings.scraping_output_format == "json":
            try:
                return json.loads(extracted)
            except Exception as e:
                raise ValueError(f"Failed to parse extracted JSON: {e}")

        return extracted
