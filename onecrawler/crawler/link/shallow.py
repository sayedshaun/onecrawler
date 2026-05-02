from typing import Optional, List
from urllib.parse import urljoin, urlparse
from onecrawler.browser import BrowserManager
from onecrawler.config.brawser import BrowserSettings
import logging

logger = logging.getLogger(__name__)


async def extract_url_from_current_page(
    url: str, browser_config: Optional[BrowserSettings] = None
) -> List[str]:
    logger.info(f"Starting shallow link extraction from {url}")
    links = set()
    browser = BrowserManager(config=browser_config or BrowserSettings())
    await browser.start()
    page = await browser.new_page()

    try:
        logger.debug(f"Navigating to {url}")
        await page.goto(url, wait_until="domcontentloaded", timeout=15000)

        hrefs = await page.eval_on_selector_all(
            "a[href]", "els => els.map(e => e.getAttribute('href'))"
        )
        logger.debug(f"Found {len(hrefs)} anchor elements")

        base_domain = urlparse(url).netloc

        for href in hrefs:
            if not href:
                continue

            absolute = urljoin(url, href)
            parsed = urlparse(absolute)

            if parsed.netloc != base_domain:
                logger.debug(f"Skipping external link: {absolute}")
                continue

            if absolute.rstrip("/") == url.rstrip("/"):
                logger.debug(f"Skipping self-link: {absolute}")
                continue

            links.add(absolute)

        logger.info(f"Extracted {len(links)} internal links")

    finally:
        await page.close()
        await browser.close()

    return list(links)
