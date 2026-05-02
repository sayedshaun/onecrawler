import logging
import asyncio
from .core import base_scraper
from .genai.extractor import llm_structured_extraction
from ...config.crawler import CrawlerSettings


class ScraperEngine:
    def __init__(self, config: CrawlerSettings):
        self.config = config
        self._closed = False
        self.logger = logging.getLogger(__name__)
        self.logger.info("ScraperEngine initialized")

    async def __aenter__(self):
        self._closed = False
        self.logger.debug("Entering ScraperEngine context")
        return self

    async def __aexit__(self, exc_type, exc, tb):
        self._closed = True
        self.logger.debug("Exiting ScraperEngine context")

    async def run(self, link: str | list[str]) -> dict | list[dict]:
        if self._closed:
            raise RuntimeError("ScraperEngine is closed")

        is_batch = isinstance(link, list)
        links = link if is_batch else [link]
        self.logger.info(
            f"Running scraper on {len(links)} link(s) with strategy: {self.config.scraping_strategy}"
        )

        results = await asyncio.gather(*[self._process(link) for link in links])
        self.logger.info(f"Scraping completed, processed {len(results)} page(s)")
        return results if is_batch else results[0]

    async def _process(self, link: str) -> dict:
        strategy = self.config.scraping_strategy
        self.logger.debug(f"Processing link with strategy: {strategy}")
        if strategy == "heuristic":
            result = await base_scraper(
                url=link, output_format=self.config.scraping_output_format
            )
            self.logger.debug("Heuristic extraction completed")
            return result
        elif strategy == "genai":
            result = await llm_structured_extraction(link)
            self.logger.debug("GenAI extraction completed")
            return result
        else:
            self.logger.error(f"Unknown strategy: {strategy}")
            raise ValueError(f"Unknown strategy: {strategy}")
