import logging
from typing import List, Optional
from urllib.parse import urlparse

from .helper import wildcard_link_match

logger = logging.getLogger(__name__)


async def extract_url_from_current_page(
    url: str,
    browser,
    include_link_patterns: Optional[List[str]] = None,
    exclude_link_patterns: Optional[List[str]] = None,
    max_links: Optional[int] = None,
) -> List[str]:
    """Extracts internal links from a single page.

    Navigates to the specified URL using a browser, extracts all anchor tags,
    filters them based on domain and patterns, and optionally uses AI
    classification.

    Args:
        url (str): The URL of the page to parse.
        browser (GoogleChrome): The browser instance to use.
        include_link_patterns (Optional[List[str]]): Glob patterns for path filtering.
        exclude_link_patterns (Optional[List[str]]): Glob patterns for path filtering.
        max_links (Optional[int]): Maximum number of links to extract.

    Returns:
        List[str]: A list of absolute internal URLs found on the page.
    """
    logger.info(f"Starting shallow link extraction from {url}")

    links = set()
    page = await browser.new_page()
    runtime = browser.settings.runtime

    try:
        logger.debug(f"Navigating to {url}")

        await page.goto(
            url,
            wait_until=runtime.wait_until,
            timeout=runtime.timeout,
        )

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

            parsed = urlparse(href)

            if parsed.netloc != base_domain:
                continue

            if href.rstrip("/") == url.rstrip("/"):
                continue

            logger.debug(f"Considering URL: {href}")

            if include_link_patterns:
                if not wildcard_link_match(
                    href,
                    base_prefix,
                    include_link_patterns,
                ):
                    continue

            if exclude_link_patterns:
                if wildcard_link_match(
                    href,
                    base_prefix,
                    exclude_link_patterns,
                ):
                    logger.debug(f"Excluded URL: {href}")
                    continue

            links.add(href)

            if max_links and len(links) >= max_links:
                logger.info("Reached max_links limit, stopping early")
                break

        logger.info(f"Extracted {len(links)} internal links")

    finally:
        await page.close()

    return list(links)
