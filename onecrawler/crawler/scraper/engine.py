# import asyncio
# from typing import List, Union

# from ...browser import GoogleChrome
# from ...config.crawler import CrawlerSettings
# from ..base import BaseEngine
# from .genai.executor import GenAIStrategy
# from .heuristic.script import HeuristicStrategy


# class ScraperEngine(BaseEngine):
#     def __init__(self, config: CrawlerSettings):
#         super().__init__()

#         self.config = config

#         self.browser = None
#         self.strategy = None

#         self.semaphore = asyncio.Semaphore(config.concurrency)
#         self.retries = config.max_retries
#         self.timeout = config.request_timeout

#         self.logger.info("ScraperEngine initialized")

#     # ===== lifecycle =====
#     async def start(self):
#         # create browser first (if needed)
#         if self.config.browser_settings:
#             self.browser = GoogleChrome(config=self.config.browser_settings)
#             await self.browser.start()

#         # create strategy AFTER browser is ready
#         if self.config.scraping_strategy == "heuristic":
#             self.strategy = HeuristicStrategy(
#                 output_format=self.config.scraping_output_format,
#                 browser=self.browser,
#             )

#         elif self.config.scraping_strategy == "genai":
#             self.strategy = GenAIStrategy()

#         else:
#             raise ValueError(f"Unknown strategy: {self.config.scraping_strategy}")

#     async def close(self):
#         if self.browser:
#             await self.browser.close()

#     # ===== core logic =====
#     async def _retry(self, coro):
#         for attempt in range(self.retries):
#             try:
#                 return await coro()
#             except Exception as e:
#                 if attempt == self.retries - 1:
#                     self.logger.error(f"Final failure: {e}")
#                     return None
#                 await asyncio.sleep(attempt + 1)

#     async def _process(self, url: str):
#         async with self.semaphore:

#             async def task():
#                 return await asyncio.wait_for(
#                     self.strategy.extract(url),
#                     timeout=self.timeout,
#                 )

#             return await self._retry(task)

#     async def run(self, link: Union[str, List[str]]):
#         self._ensure_open()

#         is_batch = isinstance(link, list)
#         links = link if is_batch else [link]

#         self.logger.info(
#             f"Running scraper on {len(links)} link(s) "
#             f"with strategy: {self.config.scraping_strategy}"
#         )

#         tasks = [self._process(url) for url in links]
#         results = await asyncio.gather(*tasks, return_exceptions=True)

#         cleaned = [r for r in results if r is not None and not isinstance(r, Exception)]

#         self.logger.info(f"Scraping completed: {len(cleaned)}/{len(links)} success")

#         return cleaned if is_batch else (cleaned[0] if cleaned else None)


import asyncio
from typing import List, Union

from ...browser import GoogleChrome
from ...config.crawler import CrawlerSettings
from ..base import BaseEngine
from .genai.executor import GenAIStrategy
from .heuristic.script import HeuristicStrategy


class ScraperEngine(BaseEngine):
    def __init__(self, config: CrawlerSettings):
        super().__init__()

        self.config = config
        self.browser = None
        self.strategy = None

        self.semaphore = asyncio.Semaphore(config.concurrency)
        self.retries = config.max_retries
        self.timeout = config.request_timeout

        self.logger.info("ScraperEngine initialized")

    # ===== lifecycle =====
    async def start(self):
        if self.config.browser_settings:
            self.browser = GoogleChrome(config=self.config.browser_settings)
            await self.browser.start()

        if self.config.scraping_strategy == "heuristic":
            self.strategy = HeuristicStrategy(
                output_format=self.config.scraping_output_format,
                browser=self.browser,
            )

        elif self.config.scraping_strategy == "genai":
            if not self.config.llm:
                raise ValueError("LLM is required for GenAI strategy")

            self.strategy = GenAIStrategy(llm=self.config.llm)

            # IMPORTANT: initialize graph early
            await self.strategy.initialize()

        else:
            raise ValueError(f"Unknown strategy: {self.config.scraping_strategy}")

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
            f"using {self.config.scraping_strategy}"
        )

        results = await asyncio.gather(
            *[self._process(url) for url in links],
            return_exceptions=False,  # IMPORTANT FIX
        )

        cleaned = [r for r in results if r is not None]

        self.logger.info(f"Scraping completed: {len(cleaned)}/{len(links)} success")

        return cleaned if isinstance(link, list) else (cleaned[0] if cleaned else None)
