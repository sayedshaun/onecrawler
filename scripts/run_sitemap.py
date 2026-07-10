"""Manually exercise the real UniversalSiteMap class against a live URL.

Usage:
    python scripts/run_sitemap.py --url <url> [--max-links N] [--concurrency N]

Example:
    python scripts/run_sitemap.py --url https://quotes.toscrape.com --max-links 100 --concurrency 5

No browser required — sitemap discovery uses curl_cffi/lxml directly.

Note: UniversalSiteMap has no async-context-manager support (no
__aenter__/__aexit__), unlike Crawler/LinkExtractor/Scraper, so it's used
directly here rather than via `async with`.
"""

import argparse
import asyncio

from onecrawler import Settings, UniversalSiteMap


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True, help="Site URL to discover")
    parser.add_argument(
        "--max-links",
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
    url, max_links, concurrency = args.url, args.max_links, args.concurrency

    settings = Settings(
        link_extraction_limit=max_links,
        concurrency=concurrency,
        show_progress=True,
        enable_logging=True,
    )

    print(
        f"Discovering URLs from {url}  (max_links={max_links}, concurrency={concurrency})"
    )

    sitemap = UniversalSiteMap(settings)
    urls = await sitemap.run(url)

    print(f"\nDiscovered {len(urls)} URL(s):")
    for discovered in urls:
        print(f"  - {discovered}")


if __name__ == "__main__":
    asyncio.run(main())
