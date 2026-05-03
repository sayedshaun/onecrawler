from .shallow import extract_url_from_current_page
from .deep import bfs_link_extractor
import logging


class LinkExtractionEngine:
    def __init__(self, settings):
        self.settings = settings
        self._closed = False
        self.logger = logging.getLogger(__name__)

        # future-ready placeholders (e.g., aiohttp / playwright / llm clients)
        self.session = None
        self.logger.info("LinkExtractionEngine initialized")

    # Async context manager
    async def __aenter__(self):
        # Initialize async resources here (if needed)
        # Example:
        # import aiohttp
        # self.session = aiohttp.ClientSession()

        self._closed = False
        self.logger.debug("Entering LinkExtractionEngine context")
        return self

    async def __aexit__(self, exc_type, exc, tb):
        # Cleanup async resources here
        # Example:
        # if self.session:
        #     await self.session.close()

        self._closed = True
        self.logger.debug("Exiting LinkExtractionEngine context")

    async def run(self, url: str) -> dict:
        if self._closed:
            raise RuntimeError("Engine is closed. Use 'async with' context.")

        strategy = self.settings.link_extraction_strategy
        self.logger.info(f"Running link extraction on {url} with strategy: {strategy}")

        if strategy == "shallow":
            return await self._run_shallow(url)
        elif strategy == "deep":
            return await self._run_deep(url)
        else:
            self.logger.error(f"Unknown strategy: {strategy}")
            raise ValueError(f"Unknown strategy: {strategy}")

    async def _run_shallow(self, url: str) -> dict:
        self.logger.debug(f"Starting shallow link extraction for {url}")
        result = await extract_url_from_current_page(
            url=url,
            include_link_patterns=self.settings.include_link_patterns,
            link_classification=self.settings.link_classification,
            concurrency=self.settings.concurrency,
            max_links=self.settings.link_extraction_limit,
        )
        self.logger.info(f"Shallow extraction completed, found {len(result)} links")
        return result

    async def _run_deep(self, url: str) -> dict:
        self.logger.debug(f"Starting deep link extraction for {url}")
        result = await bfs_link_extractor(
            base_url=url,
            num_links=self.settings.link_extraction_limit,
            include_pattern=self.settings.include_link_patterns,
            concurrency=self.settings.concurrency,
            link_classifier_with_bert=self.settings.link_classification,
        )
        self.logger.info(f"Deep extraction completed, found {len(result)} links")
        return result
