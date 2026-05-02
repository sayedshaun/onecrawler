import asyncio
from typing import Union, List, Literal
import trafilatura
import logging

logger = logging.getLogger(__name__)


async def base_scraper(
    url: Union[str, List[str]],
    output_format: Literal[
        "markdown",
        "json",
        "csv",
        "html",
        "python",
        "txt",
        "xml",
        "xmltei",
    ] = "json",
) -> Union[str, List[str]]:

    links = [url] if isinstance(url, str) else url

    logger.info(
        f"Starting base scraper for {len(links)} URL(s), format: {output_format}"
    )

    async def fetch_and_extract(link: str):
        try:
            html = await asyncio.to_thread(trafilatura.fetch_url, link)

            if not html:
                logger.warning(f"Failed to fetch: {link}")
                return None

            extracted = await asyncio.to_thread(
                trafilatura.extract,
                html,
                output_format=output_format,
                with_metadata=True,
                fast=False,
                favor_precision=True,
                include_tables=True,
                include_comments=False,
                include_images=False,
                include_links=False,
                include_formatting=False,
                deduplicate=True,
            )

            return extracted

        except Exception as e:
            logger.error(f"Error scraping {link}: {e}")
            return None

    # run concurrently
    results = await asyncio.gather(*(fetch_and_extract(link) for link in links))
    output = [r for r in results if r is not None]

    logger.info(f"Scraping completed, success: {len(output)}/{len(links)}")

    if not output:
        return []

    return output[0] if len(output) == 1 else output
