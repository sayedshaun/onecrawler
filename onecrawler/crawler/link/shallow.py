import logging
from typing import Optional, List
from urllib.parse import urlparse
from .helper import wildcard_link_match
from .classifier import LinkClassifierPipeline
from ...browser import GoogleChrome
from ...config.brawser import BrowserSettings

logger = logging.getLogger(__name__)


async def extract_url_from_current_page(
    url: str,
    browser_config: Optional[BrowserSettings] = None,
    include_link_patterns: Optional[List[str]] = None,
    link_classification: bool = False,
    concurrency: int = 10,
    max_links: Optional[int] = None,
) -> List[str]:

    logger.info(f"Starting shallow link extraction from {url}")

    links = set()
    browser = GoogleChrome(config=browser_config or BrowserSettings())
    await browser.start()
    page = await browser.new_page()

    classifier = (
        LinkClassifierPipeline(enabled=link_classification)
        if link_classification
        else None
    )
    try:
        logger.debug(f"Navigating to {url}")
        await page.goto(url, wait_until="domcontentloaded", timeout=15000)

        hrefs = await page.eval_on_selector_all(
            "a", "els => els.map(e => e.href).filter(h => h)"
        )

        logger.debug(f"Found {len(hrefs)} anchor elements")
        parsed_base = urlparse(url)
        base_domain = parsed_base.netloc
        base_prefix = f"{parsed_base.scheme}://{parsed_base.netloc}"

        for href in hrefs:
            if not isinstance(href, str) or not href:
                continue

            if href.startswith(("javascript:", "mailto:")):
                continue

            # href is already absolute from e.href
            absolute = href
            parsed = urlparse(absolute)

            if parsed.netloc != base_domain:
                continue

            if absolute.rstrip("/") == url.rstrip("/"):
                continue

            logger.debug(f"Considering URL: {absolute}")

            if include_link_patterns:
                if not wildcard_link_match(
                    absolute, base_prefix, include_link_patterns
                ):
                    logger.debug(f"URL does not match pattern: {absolute}")
                    continue

            if classifier:
                if not await classifier.is_valid(absolute):
                    continue

            logger.debug(f"Adding URL to results: {absolute}")
            links.add(absolute)

            if max_links and len(links) >= max_links:
                logger.info("Reached max_links limit, stopping early")
                break

        logger.info(f"Extracted {len(links)} internal links")

    finally:
        await page.close()
        await browser.close()

    return list(links)
