"""Manually exercise the real LinkExtractor class against a live URL.

Defaults to https://quotes.toscrape.com, a free site built for scraping
practice, so you only need to pass --limit/--concurrency. Pass --url to
target a different site.

Usage:
    python scripts/run_link_extractor.py [--url <url>] [--limit N] [--concurrency N] [--strategy shallow|deep]

Example:
    python scripts/run_link_extractor.py --limit 100 --concurrency 5

Requires a working Playwright/Chromium install (python -m playwright install
chromium).
"""

import argparse
import asyncio

from onecrawler import LinkExtractor, Settings

DEFAULT_URL = "https://quotes.toscrape.com"


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--url",
        default=DEFAULT_URL,
        help=f"URL to extract links from (default: {DEFAULT_URL})",
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
    parser.add_argument(
        "--strategy",
        choices=["shallow", "deep"],
        default="deep",
        help="link extraction strategy (default: deep)",
    )
    return parser.parse_args()


async def main():
    args = parse_args()
    url, limit, concurrency = args.url, args.limit, args.concurrency

    settings = Settings(
        link_extraction_strategy=args.strategy,
        link_extraction_limit=limit,
        concurrency=concurrency,
        show_progress=True,
        logging_level="INFO",
    )

    print(
        f"Extracting links from {url}  (strategy={args.strategy}, "
        f"limit={limit}, concurrency={concurrency})"
    )

    async with LinkExtractor(settings) as extractor:
        links = await extractor.run(url)

    print(f"\nDiscovered {len(links)} link(s):")
    for link in links:
        print(f"  - {link}")


if __name__ == "__main__":
    asyncio.run(main())
