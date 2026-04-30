from typing import Union, List
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from crawl4ai import LinkPreviewConfig


async def extract_url_from_current_page(
    parent_url: str,
    include_link_patterns: Union[List[str], None] = None,
    query: Union[str, None] = None,
    concurrency: int = 10,
    max_links: int = 500,
) -> Union[list[str], None]:

    config = CrawlerRunConfig(
        link_preview_config=LinkPreviewConfig(
            include_internal=True,
            include_external=False,
            max_links=max_links,
            include_patterns=include_link_patterns,
            exclude_patterns=[
                "*/login*",
                "*/admin*",
            ],
            concurrency=concurrency,
            timeout=5,
            query=query,
            score_threshold=0.7,
        )
    )
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(parent_url, config=config)

        if not result.success:
            raise RuntimeError(f"Crawling failed: {result.error}")

        internal_links = result.links.get("internal", [])
        internal_links = [link["href"] for link in internal_links]
        internal_links = list(set(internal_links))
        return internal_links
