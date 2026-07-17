import asyncio
from typing import Any, AsyncGenerator, List, Optional, Union
from urllib.parse import urlparse

from ..browser import GoogleChrome
from ..settings.crawler import LinkExtractionStrategy, ScrapingStrategy, Settings
from ..utils.progress import make_progress_bar
from .base import BaseEngine
from .link.deep import BFSRuntime
from .link.shallow import extract_url_from_current_page
from .pool import BrowserPool
from .scheduler import BFScheduler
from .scraper.genai.executor import LLMStrategy
from .scraper.heuristic.script import HeuristicStrategy
from .scraper.markdown.script import MarkdownifyStrategy
from .spider import LinkSpider


class Scraper(BaseEngine):
    """Engine for scraping and extracting data from URLs.

    Supports:
    - Heuristic extraction
    - GenAI extraction
    - Concurrent scraping
    - Streaming results

    Attributes:
        settings (Settings): Configuration settings for scraping.
        strategy (Optional[Any]): The content-extraction strategy in use
            (``HeuristicStrategy`` or ``LLMStrategy``); set on ``start()``.
        browser (Optional[GoogleChrome]): The shared browser instance; set on
            ``start()`` if ``settings.browser_settings`` is configured.

    Example:
        ```python
        from onecrawler import Settings, Scraper

        async with Scraper(settings) as engine:
            result = await engine.run("https://example.com")
            print(result)
        ```

        Streaming:

        ```python
        async with Scraper(settings) as engine:
            async for result in engine.stream(urls):
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
        """Starts the scraper engine."""
        self._closed = False

        if self.settings.browser_settings:
            self.browser = GoogleChrome(
                settings=self.settings.browser_settings,
                proxy_pool=self.settings.create_proxy_pool(),
            )
            await self.browser.start()

        if self.settings.scraping_strategy == ScrapingStrategy.HEURISTIC:
            self.strategy = HeuristicStrategy(
                settings=self.settings,
                browser=self.browser,
            )

        elif self.settings.scraping_strategy == ScrapingStrategy.MARKDOWNIFY:
            self.strategy = MarkdownifyStrategy(
                settings=self.settings,
                browser=self.browser,
            )

        elif self.settings.scraping_strategy == ScrapingStrategy.GENAI:
            if not self.settings.genai:
                raise ValueError("GenAI settings are required for GenAI strategy")

            self.strategy = LLMStrategy(
                provider=self.settings.genai.provider,
                model_name=self.settings.genai.model_name,
                max_retries=self.settings.max_retries,
                api_key=self.settings.genai.api_key,
                base_url=self.settings.genai.base_url,
                output_schema=self.settings.genai.output_schema,
                provider_kwargs=self.settings.genai.provider_kwargs,
                timeout=self.settings.genai.timeout,
                think=self.settings.genai.think,
                exclude_selectors=self.settings.exclude_selectors,
                browser=self.browser,
            )

            await self.strategy.initialize()

        else:
            raise ValueError(
                f"Unknown scraping strategy: {self.settings.scraping_strategy}"
            )

        self.logger.info(
            f"Scraper started using {self.settings.scraping_strategy} strategy"
        )

    async def close(self):
        """Closes the scraper engine."""
        if self.strategy:
            await self.strategy.close()

        if self.browser:
            await self.browser.close()

        self.logger.info("Scraper closed")

    async def _retry(self, fn):
        """Retries a coroutine with exponential backoff."""
        for attempt in range(self.retries):
            try:
                return await fn()

            except asyncio.CancelledError:
                raise

            except Exception as e:
                if attempt < self.retries - 1:
                    self.logger.debug(
                        f"Retry {attempt + 1}/{self.retries} "
                        f"failed: [{type(e).__name__}] {e}"
                    )

                    await asyncio.sleep(2**attempt)
                else:
                    self.logger.warning(f"Final failure [{type(e).__name__}]: {e}")

                    return None

    async def _process(self, url: str) -> Optional[dict]:
        """Processes a single URL.

        Wraps the extracted content with its source ``url`` so results stay traceable
        regardless of the extraction strategy's return shape (a dict, plain text, or a
        GenAI ``output_schema`` model instance) and regardless of completion order in
        ``stream()``.
        """

        async with self.semaphore:

            async def task():
                return await asyncio.wait_for(
                    self.strategy.extract(url),
                    timeout=self.timeout,
                )

            result = await self._retry(task)

        if result is None:
            return None

        return {"url": url, "result": result}

    async def stream(self, link: Union[str, List[str]]) -> AsyncGenerator[Any, None]:
        """Streams extracted results as they complete, in completion order.

        Args:
            link (Union[str, List[str]]): One URL or a list of URLs to scrape.

        Yields:
            dict: ``{"url": str, "result": Any}``, where ``result``'s shape
            depends on ``settings.scraping_strategy``/``scraping_output_format``
            (a dict, plain text, or a GenAI ``output_schema`` model instance).
            URLs that fail extraction after retries are silently skipped.
        """
        self._ensure_open()
        links = link if isinstance(link, list) else [link]

        self.logger.info(
            f"Streaming scraper on {len(links)} link(s) "
            f"using {self.settings.scraping_strategy}"
        )

        tasks = [asyncio.create_task(self._process(url)) for url in links]
        show_progress = getattr(
            self.settings,
            "show_progress",
            True,
        )

        with make_progress_bar(
            total=len(tasks),
            desc="Scraping",
            unit="url",
            show_progress=show_progress,
        ) as pbar:
            for task in asyncio.as_completed(tasks):
                try:
                    result = await task

                    if result is not None:
                        yield result

                except asyncio.CancelledError:
                    raise

                except Exception as e:
                    self.logger.warning(
                        f"Streaming task failed: [{type(e).__name__}] {e}"
                    )

                finally:
                    pbar.update(1)

        self.logger.info("Streaming scrape completed")

    async def run(self, link: Union[str, List[str]]) -> Union[dict, List[dict], None]:
        """Runs the scraper and collects all results.

        Args:
            link (Union[str, List[str]]): One URL or a list of URLs to scrape.

        Returns:
            Union[dict, List[dict], None]: A list of ``{"url": str, "result":
            Any}`` dicts when ``link`` is a list (possibly shorter than the
            input if some URLs failed extraction); a single such dict (or
            ``None``) when ``link`` is a single URL.
        """
        results = []
        async for result in self.stream(link):
            results.append(result)

        return results if isinstance(link, list) else (results[0] if results else None)


class LinkExtractor(BaseEngine):
    """Engine for extracting links from websites using various strategies.

    Supports both 'shallow' (single page) and 'deep' (BFS-based) extraction.

    Attributes:
        settings (Settings): Configuration settings for extraction.

    Example:
        ```python
        from onecrawler import Settings, LinkExtractor

        settings = Settings(link_extraction_strategy="shallow")

        async with LinkExtractor(settings) as engine:
            links = await engine.run("https://example.com")
            print(links)
        ```

        Streaming:

        ```python
        async with LinkExtractor(settings) as engine:
            async for link in engine.stream("https://example.com"):
                print(link)
        ```
    """

    def __init__(self, settings: Settings):
        super().__init__()

        self.settings = settings

        self.session = None

        self.logger.info("LinkExtractor initialized")

    async def start(self):
        """Starts the engine and initializes the browser."""
        self._closed = False
        self.browser = GoogleChrome(
            self.settings.browser_settings,
            proxy_pool=self.settings.create_proxy_pool(),
        )
        await self.browser.start()

    async def close(self):
        """Closes the engine and releases browser resources."""
        if hasattr(self, "browser") and self.browser:
            await self.browser.close()

    async def run(self, url: str) -> List[str]:
        """Runs the link extraction for the given URL.

        Args:
            url (str): The starting URL.

        Returns:
            List[str]: A list of absolute URLs discovered.

        Raises:
            ValueError: If an unknown strategy is configured.
        """
        self._ensure_open()

        strategy = self.settings.link_extraction_strategy

        self.logger.info(
            "Running link extraction on %s with strategy: %s",
            url,
            strategy,
        )

        if strategy == LinkExtractionStrategy.SHALLOW:
            return await extract_url_from_current_page(
                url=url,
                browser=self.browser,
                include_link_patterns=self.settings.include_link_patterns,
                exclude_link_patterns=self.settings.exclude_link_patterns,
                max_links=self.settings.link_extraction_limit,
            )

        if strategy != LinkExtractionStrategy.DEEP:
            raise ValueError(f"Unknown strategy: {strategy}")

        results = []
        async for link in self.stream(url):
            results.append(link)

        return results

    async def stream(self, url: str) -> AsyncGenerator[str, None]:
        """Streams discovered links incrementally (deep strategy only).

        Args:
            url (str): The starting URL.

        Yields:
            str: Discovered absolute URL.

        Raises:
            AssertionError: If strategy is 'shallow'.
            ValueError: If an unknown strategy is configured.
        """
        self._ensure_open()

        strategy = self.settings.link_extraction_strategy

        assert (
            strategy != LinkExtractionStrategy.SHALLOW
        ), "Shallow link extraction does not support stream"

        self.logger.info(
            "Running link extraction stream on %s with strategy: %s",
            url,
            strategy,
        )

        if strategy != LinkExtractionStrategy.DEEP:
            raise ValueError(f"Unknown strategy: {strategy}")

        parsed = urlparse(url)
        base_prefix = f"{parsed.scheme}://{parsed.netloc}"

        scheduler = BFScheduler(url)
        spider = LinkSpider(base_prefix)
        pool = BrowserPool(
            self.browser,
            self.settings.concurrency,
        )

        await pool.init()

        runtime = BFSRuntime(
            scheduler=scheduler,
            pool=pool,
            spider=spider,
            base_prefix=base_prefix,
            max_links=self.settings.link_extraction_limit,
            include_pattern=self.settings.include_link_patterns,
            exclude_pattern=self.settings.exclude_link_patterns,
            enable_human_behaviors=self.settings.human_behavior_settings is not None,
            human_behavior_settings=self.settings.human_behavior_settings,
            concurrency=self.settings.concurrency,
            streaming=True,
            wait_until=self.settings.browser_settings.wait_until,
            timeout=self.settings.browser_settings.timeout,
            show_progress=self.settings.show_progress,
        )

        try:
            async for link in runtime.stream():
                yield link

        finally:
            await pool.close()
