"""Manually exercise the real Crawler class against a live URL.

Usage:
    python scripts/run_crawler.py --url <url> [--max-links N] [--concurrency N]

Example:
    python scripts/run_crawler.py --url https://quotes.toscrape.com --max-links 100 --concurrency 5

Requires a working Playwright/Chromium install (python -m playwright install
chromium). Uses the heuristic strategy, so no API key is needed.
"""

import argparse
import asyncio

from onecrawler import Crawler, Settings


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True, help="URL to crawl")
    parser.add_argument(
        "--max-links",
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
    url, max_links, concurrency = args.url, args.max_links, args.concurrency

    settings = Settings(
        scraping_strategy="heuristic",
        scraping_output_format="markdown",
        link_extraction_limit=max_links,
        concurrency=concurrency,
        show_progress=True,
        enable_logging=True,
    )

    print(f"Crawling {url}  (max_links={max_links}, concurrency={concurrency})")

    async with Crawler(settings) as crawler:
        results = await crawler.run(url)

    print(f"\nCrawled {len(results)} page(s):")
    for item in results:
        title = item.get("title") if isinstance(item, dict) else None
        page_url = item.get("url") if isinstance(item, dict) else None
        print(f"  - {page_url}  {f'({title})' if title else ''}")


if __name__ == "__main__":
    asyncio.run(main())
