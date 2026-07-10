"""Manually exercise the real LinkExtractor class against a live URL.

Usage:
    python scripts/run_link_extractor.py --url <url> [--max-links N] [--concurrency N] [--strategy shallow|deep]

Example:
    python scripts/run_link_extractor.py --url https://quotes.toscrape.com --max-links 100 --concurrency 5

Requires a working Playwright/Chromium install (python -m playwright install
chromium).
"""

import argparse
import asyncio

from onecrawler import LinkExtractor, Settings


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True, help="URL to extract links from")
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
    parser.add_argument(
        "--strategy",
        choices=["shallow", "deep"],
        default="deep",
        help="link extraction strategy (default: deep)",
    )
    return parser.parse_args()


async def main():
    args = parse_args()
    url, max_links, concurrency = args.url, args.max_links, args.concurrency

    settings = Settings(
        link_extraction_strategy=args.strategy,
        link_extraction_limit=max_links,
        concurrency=concurrency,
        show_progress=True,
        enable_logging=True,
    )

    print(
        f"Extracting links from {url}  (strategy={args.strategy}, "
        f"max_links={max_links}, concurrency={concurrency})"
    )

    async with LinkExtractor(settings) as extractor:
        links = await extractor.run(url)

    print(f"\nDiscovered {len(links)} link(s):")
    for link in links:
        print(f"  - {link}")


if __name__ == "__main__":
    asyncio.run(main())
