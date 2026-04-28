from .heuristic.script import heuristic_structured_extraction
from .genai.extractor import llm_structured_extraction
from .scraper import base_scraper


class CrawlerEngine:
    def __init__(self, config):
        self.config = config
        self._closed = False

    # -------------------------
    # async context manager
    # -------------------------
    async def __aenter__(self):
        self._closed = False
        return self

    async def __aexit__(self, exc_type, exc, tb):
        self._closed = True

    # -------------------------
    # public API (supports single OR batch)
    # -------------------------
    async def run(self, url: str | list[str]) -> dict | list[dict]:
        if self._closed:
            raise RuntimeError("CrawlerEngine is closed")

        is_batch = isinstance(url, list)

        urls = url if is_batch else [url]

        html_pages = await self._fetch_html(urls)

        results = [
            self._process(html)
            for html in html_pages
        ]

        return results if is_batch else results[0]

    # -------------------------
    # scraping layer
    # -------------------------
    async def _fetch_html(self, urls: list[str]):
        return await base_scraper(urls, output_format="html")

    # -------------------------
    # processing layer
    # -------------------------
    def _process(self, html: str) -> dict:
        strategy = self.config.content_scraping_strategy

        if strategy == "heuristic":
            return heuristic_structured_extraction(html)

        elif strategy == "genai":
            return llm_structured_extraction(html)

        else:
            raise ValueError(f"Unknown strategy: {strategy}")