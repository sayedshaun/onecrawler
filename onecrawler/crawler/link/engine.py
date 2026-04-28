from .shallow import extract_url_from_current_page
from .deep import bfs_url_extractor


class LinkExtractorEngine:
    def __init__(self, settings):
        self.settings = settings
        self._closed = False

        # future-ready placeholders (e.g., aiohttp / playwright / llm clients)
        self.session = None


    # Async context manager
    async def __aenter__(self):
        # Initialize async resources here (if needed)
        # Example:
        # import aiohttp
        # self.session = aiohttp.ClientSession()

        self._closed = False
        return self

    async def __aexit__(self, exc_type, exc, tb):
        # Cleanup async resources here
        # Example:
        # if self.session:
        #     await self.session.close()

        self._closed = True


    async def run(self, url: str) -> dict:
        if self._closed:
            raise RuntimeError("Engine is closed. Use 'async with' context.")

        strategy = self.settings.url_extraction_strategy

        if strategy == "shallow":
            return await self._run_shallow(url)
        elif strategy == "deep":
            return await self._run_deep(url)
        else:
            raise ValueError(f"Unknown strategy: {strategy}")


    async def _run_shallow(self, url: str) -> dict:
        return await extract_url_from_current_page(
            parent_url=url,
            concurrency=self.settings.concurrency,
            max_links=self.settings.url_extraction_limit,
        )

    async def _run_deep(self, url: str) -> dict:
        return await bfs_url_extractor(
            base_url=url,
            num_urls=self.settings.url_extraction_limit,
            filter_tags=self.settings.filter_url_tags,
            concurrency=self.settings.concurrency,
        )