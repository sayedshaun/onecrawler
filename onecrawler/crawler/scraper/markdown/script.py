import contextlib
import logging
from typing import Any, Optional

import html_to_markdown as htm

from ...navigation import goto

logger = logging.getLogger(__name__)


class MarkdownifyStrategy:
    """Converts a page's full HTML to Markdown, with no content extraction.

    Unlike :class:`HeuristicStrategy` (which uses ``trafilatura`` to isolate
    the main article and strip boilerplate), this performs a faithful whole-
    page HTML-to-Markdown conversion. It keeps navigation, footers, and other
    chrome, and extracts no metadata — but it never returns ``None`` for a
    rendered page, so it works on the non-article pages (product pages, docs,
    dashboards, listings) where article-biased extraction yields nothing.

    Set ``settings.exclude_selectors`` (e.g. ``["nav", "footer",
    ".cookie-banner"]``) to deterministically strip known chrome before
    conversion, at no LLM cost.

    Attributes:
        settings (Settings): Configuration settings.
        browser (Optional[GoogleChrome]): Browser instance for rendering.
    """

    def __init__(self, settings: Any, browser: Any = None):
        self.settings = settings
        self.browser = browser
        self._conversion_options = htm.ConversionOptions(
            heading_style="atx",
            bullets="-",
            exclude_selectors=list(
                getattr(settings, "exclude_selectors", None) or []
            ),
        )

    async def extract(self, url: str, html: Optional[str] = None) -> Optional[Any]:
        # `html` lets a caller (e.g. the combined Crawler) hand over the page
        # it already loaded, so we skip a redundant second navigation.
        if html is None:
            html = await self._fetch_html(url)

        if not html:
            return None

        markdown = htm.convert(html, self._conversion_options).content
        markdown = "\n".join(line.rstrip() for line in markdown.splitlines())

        return markdown or None

    async def _fetch_html(self, url: str) -> Optional[str]:
        """Fetches raw HTML for `url` when no pre-loaded page is supplied."""
        if self.browser is None:
            logger.warning("MarkdownifyStrategy._fetch_html: browser is missing")
            return None

        page = await self.browser.new_page()
        try:
            await goto(
                page,
                url,
                wait_until=self.settings.browser_settings.wait_until,
                timeout=self.settings.browser_settings.timeout,
                settle_delay=self.settings.browser_settings.settle_delay,
            )
            return await page.content()
        finally:
            with contextlib.suppress(Exception):
                await page.close()

    async def close(self) -> None:
        pass
