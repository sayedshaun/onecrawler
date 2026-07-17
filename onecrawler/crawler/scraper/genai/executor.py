import contextlib
import logging
from typing import TYPE_CHECKING, Any, List, Optional

import html_to_markdown as htm

from .model import ModelManager
from .prompt import STRUCTURED_PROMPT

if TYPE_CHECKING:
    from ....browser import GoogleChrome

logger = logging.getLogger(__name__)


class LLMStrategy:
    """Extracts structured content from a page using an LLM.

    The extraction pipeline is a straight line with a bounded retry loop:

        fetch HTML -> HTML to markdown -> build prompt -> structured output

    If any step yields no usable result, the whole pipeline is retried up to
    ``max_retries`` total attempts. When the caller supplies ``html`` (the
    combined ``Crawler`` hands over the page it already loaded), that HTML is
    reused on every attempt instead of re-navigating.

    Pass ``exclude_selectors`` (e.g. ``["nav", "footer", ".cookie-banner"]``)
    to deterministically strip known chrome before conversion, at no LLM cost.
    """

    def __init__(
        self,
        provider: str,
        model_name: str,
        max_retries: int,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        output_schema: Optional[Any] = None,
        provider_kwargs: Optional[dict] = None,
        timeout: Optional[float] = None,
        browser: Optional["GoogleChrome"] = None,
        think: bool = False,
        exclude_selectors: Optional[List[str]] = None,
    ):
        self.browser = browser
        self.max_retries = max_retries
        self.llm = ModelManager(
            schema=output_schema,
            model_provider=provider,
            model_name=model_name,
            base_url=base_url,
            api_key=api_key,
            provider_kwargs=provider_kwargs,
            timeout=timeout,
            think=think,
        )
        self._conversion_options = htm.ConversionOptions(
            heading_style="atx",
            bullets="-",
            exclude_selectors=list(exclude_selectors or []),
        )

    async def initialize(self) -> None:
        # Retained for API compatibility with the Crawler's start() flow.
        # There is no graph to build any more, so this is a no-op.
        return None

    async def extract(self, url: str, html: Optional[str] = None) -> Optional[Any]:
        if self.llm.schema is None:
            logger.warning("LLMStrategy.extract: schema is missing")
            return None

        # A caller-supplied `html` is reused across every retry; only
        # self-fetched HTML is re-fetched on each attempt.
        prefetched = html

        for attempt in range(max(self.max_retries, 1)):
            page_html = (
                prefetched if prefetched is not None else await self._fetch_html(url)
            )
            markdown = self._html_to_markdown(page_html)

            response = await self._structured_output(markdown)
            if response is not None:
                return response

            if attempt < self.max_retries - 1:
                logger.debug("LLMStrategy.extract: retrying %s", url)

        return None

    async def _fetch_html(self, url: str) -> Optional[str]:
        if self.browser is None:
            logger.warning("LLMStrategy._fetch_html: browser is missing")
            return None

        page = None
        try:
            page = await self.browser.new_page()
            browser_settings = self.browser.settings

            await page.goto(
                url,
                wait_until=browser_settings.wait_until,
                timeout=browser_settings.timeout,
            )

            with contextlib.suppress(Exception):
                await page.wait_for_load_state(
                    browser_settings.wait_until,
                    timeout=browser_settings.timeout,
                )

            # Let client-side/JS-rendered content (e.g. prices on SPA sites)
            # hydrate before capturing. Best-effort; never fail over the wait.
            settle_delay = getattr(browser_settings, "settle_delay", 0)
            if settle_delay and settle_delay > 0:
                with contextlib.suppress(Exception):
                    await page.wait_for_timeout(settle_delay)

            return await page.content()

        except Exception as exc:
            logger.warning("LLMStrategy._fetch_html failed for %s: %s", url, exc)
            return None

        finally:
            if page is not None:
                with contextlib.suppress(Exception):
                    await page.close()

    def _html_to_markdown(self, html: Optional[str]) -> Optional[str]:
        if not html:
            return None

        markdown = htm.convert(html, self._conversion_options).content
        return "\n".join(line.rstrip() for line in markdown.splitlines())

    def _build_prompt(self, markdown: str) -> str:
        return STRUCTURED_PROMPT.format(markdown=markdown)

    async def _structured_output(self, markdown: Optional[str]) -> Optional[Any]:
        if not markdown:
            logger.warning("LLMStrategy._structured_output: markdown is empty")
            return None

        schema = self.llm.schema
        prompt = self._build_prompt(markdown)

        try:
            response = await self.llm.generate(prompt, schema=schema)
            with contextlib.suppress(Exception):
                response = schema.model_validate(response)
            return response
        except Exception as exc:
            logger.error(
                "LLMStrategy._structured_output failed: %s", exc, exc_info=True
            )
            return None

    async def close(self) -> None:
        await self.llm.close()
