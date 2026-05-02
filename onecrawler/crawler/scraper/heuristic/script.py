import logging
import asyncio
from typing import Union, List
from ..core import fetch_and_extract

logger = logging.getLogger(__name__)


async def heuristic_scraper(
    url: Union[str, List[str]], output_format: List[str] = "json"
) -> Union[str, List[str]]:

    links = [url] if isinstance(url, str) else url

    logger.info(
        f"Starting heuristic scraper for {len(links)} URL(s), format: {output_format}"
    )

    results = await asyncio.gather(*(fetch_and_extract(link) for link in links))
    output = [r for r in results if r is not None]

    logger.info(f"Scraping completed, success: {len(output)}/{len(links)}")

    if not output:
        return []

    return output[0] if len(output) == 1 else output
