import asyncio
import warnings
from typing import Any, List, Optional, Union

from ...browser import GoogleChrome
from ...settings.crawler import Settings
from ..base import BaseEngine
from .genai.executor import GenAIStrategy
from .heuristic.script import HeuristicStrategy


class Scraper(BaseEngine):
    """Engine for scraping and extracting data from URLs. Supports both Heuristic and GenAI strategies.

    Attributes:
        settings (Settings): Configuration settings for the engine.

    Example:
        ```python
        from onecrawler import Settings, Scraper

        async with Scraper(settings) as engine:
            result = await engine.run("https://example.com")
            print(result)

        # Stream
        async with Scraper(settings) as engine:
            async for result in engine.stream("https://example.com"):
                print(result)
        ```
    """

    def __init__(self, settings: Settings):
        super().__init__()

        self.settings = settings
        self.browser = None
        self.strategy = None

        self.semaphore = asyncio.Semaphore(settings.concurrency)
        self.retries = settings.max_retries
        self.timeout = settings.request_timeout

        self.logger.info("Scraper initialized")

    async def start(self):
        """Starts the engine and initializes browser and strategy."""
        self._closed = False
        if self.settings.browser_settings:
            self.browser = GoogleChrome(settings=self.settings.browser_settings)
            await self.browser.start()

        if self.settings.scraping_strategy == "heuristic":
            self.strategy = HeuristicStrategy(
                settings=self.settings,
                browser=self.browser,
            )

        elif self.settings.scraping_strategy == "genai":
            if not self.settings.genai:
                raise ValueError("GenAI settings is required for GenAI strategy")

            self.strategy = GenAIStrategy(
                settings=self.settings.genai, browser=self.browser
            )
            await self.strategy.initialize()

        else:
            raise ValueError(f"Unknown strategy: {self.settings.scraping_strategy}")

    async def close(self):
        """Closes the engine and releases resources."""
        if self.browser:
            await self.browser.close()

    async def _retry(self, fn):
        """Retries a function with exponential backoff."""
        for attempt in range(self.retries):
            try:
                return await fn()
            except Exception as e:
                if attempt == self.retries - 1:
                    self.logger.error(f"Final failure [{type(e).__name__}]: {e}")
                    return None
                await asyncio.sleep(2**attempt)

    async def _process(self, url: str) -> Optional[Any]:
        """Processes a single URL using the active strategy."""
        async with self.semaphore:

            async def task():
                return await asyncio.wait_for(
                    self.strategy.extract(url),
                    timeout=self.timeout,
                )

            return await self._retry(task)

    async def run(self, link: Union[str, List[str]]) -> Union[Any, List[Any], None]:
        """Runs the scraper on the given URL or list of URLs.

        Args:
            link (Union[str, List[str]]): A single URL or a list of URLs to scrape.

        Returns:
            Union[Any, List[Any], None]: The extracted data. Returns a list if
                input was a list, otherwise a single result or None.
        """
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
