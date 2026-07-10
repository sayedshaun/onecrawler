"""Manually exercise the real Scraper class against a live URL.

Scraper extracts content from an already-known URL list, so this discovers
up to --max-links URLs via UniversalSiteMap first, then scrapes them —
mirroring the project's recommended sitemap-then-scrape workflow.

Usage:
    python scripts/run_scraper.py --url <url> [--max-links N] [--concurrency N]

Example:
    python scripts/run_scraper.py --url https://quotes.toscrape.com --max-links 100 --concurrency 5

Requires a working Playwright/Chromium install (python -m playwright install
chromium). Uses the heuristic strategy, so no API key is needed.
"""

import argparse
import asyncio

from onecrawler import Scraper, Settings, UniversalSiteMap


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True, help="Site URL to discover and scrape")
    parser.add_argument(
        "--max-links",
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
    url, max_links, concurrency = args.url, args.max_links, args.concurrency

    settings = Settings(
        scraping_strategy="heuristic",
        scraping_output_format="json",
        link_extraction_limit=max_links,
        concurrency=concurrency,
        show_progress=True,
        enable_logging=True,
    )

    print(f"Discovering URLs from {url}  (max_links={max_links})")
    sitemap = UniversalSiteMap(settings)
    urls = await sitemap.run(url)
    print(f"Discovered {len(urls)} URL(s); scraping with concurrency={concurrency}")

    async with Scraper(settings) as scraper:
        results = await scraper.run(urls)

    print(f"\nScraped {len(results)} page(s):")
    for item in results:
        page_url = item["url"]
        content = item["result"]
        title = content.get("title") if isinstance(content, dict) else None
        print(f"  - {page_url}  {f'({title})' if title else ''}")


if __name__ == "__main__":
    asyncio.run(main())
