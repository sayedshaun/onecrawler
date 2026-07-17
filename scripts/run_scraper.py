"""Manually exercise the real Scraper class against a live URL.

Scraper extracts content from an already-known URL list, so this discovers
up to --limit URLs via SiteMap first, then scrapes them —
mirroring the project's recommended sitemap-then-scrape workflow.

Defaults to https://quotes.toscrape.com, a free site built for scraping
practice, so you only need to pass --limit/--concurrency. Pass --url to
target a different site.

Usage:
    python scripts/run_scraper.py [--url <url>] [--limit N] [--concurrency N]

Example:
    python scripts/run_scraper.py --limit 100 --concurrency 5

Requires a working Playwright/Chromium install (python -m playwright install
chromium). Uses the markdownify strategy, so no API key is needed.
"""

import argparse
import asyncio

from onecrawler import Scraper, Settings, SiteMap
from onecrawler.utils import writter

DEFAULT_URL = "https://quotes.toscrape.com"


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--url",
        default=DEFAULT_URL,
        help=f"Site URL to discover and scrape (default: {DEFAULT_URL})",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="maximum number of URLs to discover/scrape (default: 100)",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=5,
        help="number of concurrent workers (default: 5)",
    )
    return parser.parse_args()


async def main():
    args = parse_args()
    url, limit, concurrency = args.url, args.limit, args.concurrency

    settings = Settings(
        scraping_strategy="markdownify",
        scraping_output_format="json",
        link_extraction_limit=limit,
        concurrency=concurrency,
        show_progress=True,
        logging_level="INFO",
    )

    sitemap = SiteMap(settings)
    urls = await sitemap.run(url)

    async with Scraper(settings) as scraper:
        results = await scraper.run(urls)

    print(f"\nScraped {len(results)} page(s):")
    for item in results:
        page_url = item["url"]
        content = item["result"]
        title = content.get("title") if isinstance(content, dict) else None
        print(f"  - {page_url}  {f'({title})' if title else ''}")

    # Write results to a file
    writter.dump_json(results, "scraped_results.json")


if __name__ == "__main__":
    asyncio.run(main())
