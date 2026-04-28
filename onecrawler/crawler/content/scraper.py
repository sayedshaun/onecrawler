from typing import Union, List, Literal
from crawl4ai import AsyncWebCrawler


async def base_scraper(
    url: Union[str, List[str]], output_format: Literal["markdown", "html"]
) -> Union[str, List[str]]:

    urls = [url] if isinstance(url, str) else url

    async with AsyncWebCrawler() as crawler:
        results = await crawler.arun_many(urls)

    def extract(r):
        return r.markdown if output_format == "markdown" else r.html

    output = [extract(r) for r in results]

    return output[0] if len(output) == 1 else output
