import asyncio
import logging
from typing import List, Union
from ...config.crawler import CrawlerSettings
from .genai.executor import GenAIStrategy
from .heuristic.script import HeuristicStrategy


class StrategyFactory:
    @staticmethod
    def create(config: CrawlerSettings, browser_config=None):
        if config.scraping_strategy == "heuristic":
            return HeuristicStrategy(
                output_format=config.scraping_output_format,
                browser_config=browser_config,
            )

        elif config.scraping_strategy == "genai":
            return GenAIStrategy()

        else:
            raise ValueError(f"Unknown strategy: {config.scraping_strategy}")


class ScraperEngine:
    def __init__(self, config: CrawlerSettings):
        self.config = config
        self._closed = False
        self.logger = logging.getLogger(__name__)

        self.strategy = StrategyFactory.create(
            config, browser_config=config.browser_settings
        )

        self.semaphore = asyncio.Semaphore(config.concurrency)
        self.retries = config.max_retries
        self.timeout = config.request_timeout

        self.logger.info("ScraperEngine initialized")

    async def __aenter__(self):
        self._closed = False
        await self.strategy.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        self._closed = True
        await self.strategy.__aexit__(exc_type, exc, tb)

    async def _retry(self, coro):
        for attempt in range(self.retries):
            try:
                return await coro()
            except Exception as e:
                if attempt == self.retries - 1:
                    self.logger.error(f"Final failure: {e}")
                    return None
                await asyncio.sleep(1 * (attempt + 1))

    async def _process(self, url: str):
        async with self.semaphore:

            async def task():
                return await asyncio.wait_for(
                    self.strategy.extract(url),
                    timeout=self.timeout,
                )

            result = await self._retry(task)

            if not result:
                return None

            return result

    async def run(self, link: Union[str, List[str]]):
        if self._closed:
            raise RuntimeError("ScraperEngine is closed")

        is_batch = isinstance(link, list)
        links = link if is_batch else [link]

        self.logger.info(
            f"Running scraper on {len(links)} link(s) with strategy: {self.config.scraping_strategy}"
        )

        tasks = [self._process(url) for url in links]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        cleaned = []
        for r in results:
            if isinstance(r, Exception):
                self.logger.error(f"Error: {r}")
                continue
            if r is None:
                continue
            cleaned.append(r)

        self.logger.info(f"Scraping completed: {len(cleaned)}/{len(links)} success")

        return cleaned if is_batch else (cleaned[0] if cleaned else None)
