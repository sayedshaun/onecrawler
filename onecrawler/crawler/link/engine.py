from urllib.parse import urlparse

from ...browser import GoogleChrome
from ..base import BaseEngine
from .deep import BFScheduler, BFSRuntime, BrowserPool, LinkSpider
from .shallow import extract_url_from_current_page


class LinkExtractionEngine(BaseEngine):
    def __init__(self, settings):
        super().__init__()

        self.settings = settings

        # future-ready placeholders
        self.session = None

        self.logger.info("LinkExtractionEngine initialized")

    async def start(self):
        self.browser = GoogleChrome(self.settings.browser_settings)
        await self.browser.start()

    async def close(self):
        if hasattr(self, "browser") and self.browser:
            await self.browser.close()

    async def run(self, url: str) -> list[str]:
        """
        Collect all links into memory and return them as a list.
        """

        self._ensure_open()

        strategy = self.settings.link_extraction_strategy

        self.logger.info(
            "Running link extraction on %s with strategy: %s",
            url,
            strategy,
        )

        if strategy == "shallow":
            return await extract_url_from_current_page(
                url=url,
                browser=self.browser,
                include_link_patterns=self.settings.include_link_patterns,
                link_classification=self.settings.link_classification,
                max_links=self.settings.link_extraction_limit,
            )

        if strategy != "deep":
            raise ValueError(f"Unknown strategy: {strategy}")

        results = []
        async for link in self.stream(url):
            results.append(link)

        return results

    async def stream(self, url: str):
        """
        Stream links incrementally as they are discovered.
        """

        self._ensure_open()

        strategy = self.settings.link_extraction_strategy

        assert strategy != "shallow", "Shallow link extraction does not support stream"

        self.logger.info(
            "Running link extraction stream on %s with strategy: %s",
            url,
            strategy,
        )

        if strategy != "deep":
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
            enable_human_behaviors=self.settings.enable_human_behaviors,
            human_behavior_settings=self.settings.human_behavior_settings,
            concurrency=self.settings.concurrency,
            streaming=True,
        )

        try:
            async for link in runtime.stream():
                yield link

        finally:
            await pool.close()
