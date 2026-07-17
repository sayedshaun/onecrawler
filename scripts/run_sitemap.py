"""Manually exercise the real SiteMap class against a live URL.

Defaults to https://quotes.toscrape.com, a free site built for scraping
practice, so you only need to pass --limit/--concurrency. Pass --url to
target a different site.

Usage:
    python scripts/run_sitemap.py [--url <url>] [--limit N] [--concurrency N]

Example:
    python scripts/run_sitemap.py --limit 100 --concurrency 5

No browser required — sitemap discovery uses curl_cffi/lxml directly.

Note: SiteMap has no async-context-manager support (no
__aenter__/__aexit__), unlike Crawler/LinkExtractor/Scraper, so it's used
directly here rather than via `async with`.
"""

import argparse
import asyncio

from onecrawler import Settings, SiteMap

DEFAULT_URL = "https://quotes.toscrape.com"


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--url",
        default=DEFAULT_URL,
        help=f"Site URL to discover (default: {DEFAULT_URL})",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="maximum number of URLs to discover (default: 100)",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=5,
        help="number of concurrent requests (default: 5)",
    )
    return parser.parse_args()


async def main():
    args = parse_args()
    url, limit, concurrency = args.url, args.limit, args.concurrency

    settings = Settings(
        link_extraction_limit=limit,
        concurrency=concurrency,
        show_progress=True,
        logging_level="INFO",
    )

    print(f"Discovering URLs from {url}  (limit={limit}, concurrency={concurrency})")

    sitemap = SiteMap(settings)
    urls = await sitemap.run(url)

    print(f"\nDiscovered {len(urls)} URL(s):")
    for discovered in urls:
        print(f"  - {discovered}")


if __name__ == "__main__":
    asyncio.run(main())
