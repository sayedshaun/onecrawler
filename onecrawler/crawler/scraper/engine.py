from .heuristic.script import heuristic_structured_extraction
from .genai.extractor import llm_structured_extraction
from .scraper import base_scraper


class ScraperEngine:
    def __init__(self, config):
        self.config = config
        self._closed = False


    async def __aenter__(self):
        self._closed = False
        return self

    async def __aexit__(self, exc_type, exc, tb):
        self._closed = True


    async def run(self, link: str | list[str]) -> dict | list[dict]:
        if self._closed:
            raise RuntimeError("ScraperEngine is closed")

        is_batch = isinstance(link, list)
        links = link if is_batch else [link]
        html_pages = await self._fetch_html(links)
        results = [self._process(html) for html in html_pages]
        return results if is_batch else results[0]


    async def _fetch_html(self, links: list[str]):
        return await base_scraper(links, output_format="html")


    def _process(self, html: str) -> dict:
        strategy = self.config.scraping_strategy
        if strategy == "heuristic":
            return heuristic_structured_extraction(html)
        elif strategy == "genai":
            return llm_structured_extraction(html)
        else:
            raise ValueError(f"Unknown strategy: {strategy}")