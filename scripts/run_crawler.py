"""Manually exercise the real Crawler class against a live URL.

Defaults to https://quotes.toscrape.com, a free site built for scraping
practice, so you only need to pass --limit/--concurrency. Pass --url to
target a different site.

Usage:
    python scripts/run_crawler.py [--url <url>] [--limit N] [--concurrency N]

Example:
    python scripts/run_crawler.py --limit 100 --concurrency 5

Requires a working Playwright/Chromium install (python -m playwright install
chromium). Uses the heuristic strategy, so no API key is needed.
"""

import argparse
import asyncio

from onecrawler import Crawler, Settings
from onecrawler.utils import writter

DEFAULT_URL = "https://quotes.toscrape.com"


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--url",
        default=DEFAULT_URL,
        help=f"URL to crawl (default: {DEFAULT_URL})",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="maximum number of links to extract (default: 100)",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=5,
        help="number of concurrent workers/pages (default: 5)",
    )
    return parser.parse_args()


async def main():
    args = parse_args()
    url, limit, concurrency = args.url, args.limit, args.concurrency

    settings = Settings(
        scraping_strategy="heuristic",
        scraping_output_format="markdown",
        link_extraction_limit=limit,
        concurrency=concurrency,
        show_progress=True,
        logging_level="INFO",
    )

    print(f"Crawling {url}  (limit={limit}, concurrency={concurrency})")

    async with Crawler(settings) as crawler:
        results = await crawler.run(url)

    print(f"\nCrawled {len(results)} page(s):")
    for item in results:
        title = item.get("title") if isinstance(item, dict) else None
        page_url = item.get("url") if isinstance(item, dict) else None
        print(f"  - {page_url}  {f'({title})' if title else ''}")

    writter.dump_json(results, "crawled_results.json")
    print("\nSaved results to crawled_results.json")


if __name__ == "__main__":
    asyncio.run(main())
