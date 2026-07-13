import asyncio
import contextlib
import json
from typing import Any, Optional

import trafilatura

from ....settings.crawler import OutputFormat
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

    async def extract(self, url: str, html: Optional[str] = None) -> Optional[Any]:
        # `html` lets a caller (e.g. the combined Crawler) hand over the page
        # it already loaded, so we skip a redundant second navigation.
        if html is None:
            html = await self._fetch_html(url)

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

        if self.settings.scraping_output_format == OutputFormat.JSON:
            try:
                return json.loads(extracted)
            except Exception as e:
                raise ValueError(f"Failed to parse extracted JSON: {e}")

        return extracted

    async def _fetch_html(self, url: str) -> Optional[str]:
        """Fetches raw HTML for `url` when no pre-loaded page is supplied."""
        if self.browser:
            page = await self.browser.new_page()
            try:
                await goto(
                    page,
                    url,
                    wait_until=self.settings.browser_settings.wait_until,
                    timeout=self.settings.browser_settings.timeout,
                )
                return await page.content()
            finally:
                with contextlib.suppress(Exception):
                    await page.close()
        return await asyncio.to_thread(trafilatura.fetch_url, url)

    async def close(self) -> None:
        pass
