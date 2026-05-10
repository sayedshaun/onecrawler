import asyncio
from typing import List, Union

from ...browser import GoogleChrome
from ...settings.crawler import CrawlerSettings
from ..base import BaseEngine
from .genai.executor import GenAIStrategy
from .heuristic.script import HeuristicStrategy


class ScraperEngine(BaseEngine):
    def __init__(self, settings: CrawlerSettings):
        super().__init__()

        self.settings = settings
        self.browser = None
        self.strategy = None

        self.semaphore = asyncio.Semaphore(settings.concurrency)
        self.retries = settings.max_retries
        self.timeout = settings.request_timeout

        self.logger.info("ScraperEngine initialized")

    async def start(self):
        if self.settings.browser_settings:
            self.browser = GoogleChrome(settings=self.settings.browser_settings)
            await self.browser.start()

        if self.settings.scraping_strategy == "heuristic":
            self.strategy = HeuristicStrategy(
                settings=self.settings,
                browser=self.browser,
            )

        elif self.settings.scraping_strategy == "genai":
            if not self.settings.llm:
                raise ValueError("LLM is required for GenAI strategy")

            self.strategy = GenAIStrategy(llm=self.settings.llm)

            await self.strategy.initialize()

        else:
            raise ValueError(f"Unknown strategy: {self.settings.scraping_strategy}")

    async def close(self):
        if self.browser:
            await self.browser.close()

    async def _retry(self, fn):
        for attempt in range(self.retries):
            try:
                return await fn()
            except Exception as e:
                if attempt == self.retries - 1:
                    self.logger.error(f"Final failure: {e}")
                    return None
                await asyncio.sleep(2**attempt)

    async def _process(self, url: str):
        async with self.semaphore:

            async def task():
                return await asyncio.wait_for(
                    self.strategy.extract(url),
                    timeout=self.timeout,
                )

            return await self._retry(task)

    async def run(self, link: Union[str, List[str]]):
        self._ensure_open()

        links = link if isinstance(link, list) else [link]

        self.logger.info(
            f"Running scraper on {len(links)} link(s) "
            f"using {self.settings.scraping_strategy}"
        )

        results = await asyncio.gather(
            *[self._process(url) for url in links],
            return_exceptions=False,
        )

        cleaned = [r for r in results if r is not None]

        self.logger.info(f"Scraping completed: {len(cleaned)}/{len(links)} success")

        return cleaned if isinstance(link, list) else (cleaned[0] if cleaned else None)
