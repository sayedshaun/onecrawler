import argparse
import asyncio
import json
import sys

from . import Crawler, Settings
from .version import __version__


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="onecrawler",
        description=(
            "OneCrawler is an async Python crawling library. Run a crawl "
            "directly from the command line, or use it as a library:\n\n"
            "    import onecrawler\n"
            "    crawler = onecrawler.Crawler(...)\n\n"
            "See https://sayedshaun.github.io/onecrawler/ for full usage, "
            "including proxy, GenAI, and human-behavior configuration."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version", action="version", version=f"onecrawler {__version__}"
    )

    subparsers = parser.add_subparsers(dest="command")

    crawl_parser = subparsers.add_parser(
        "crawl",
        help="Crawl a site starting from a URL, printing extracted content as JSON lines",
    )
    crawl_parser.add_argument(
        "url", help="Starting URL; the crawl stays within its origin"
    )
    crawl_parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Maximum number of pages to extract (default: 50)",
    )
    crawl_parser.add_argument(
        "--concurrency",
        type=int,
        default=10,
        help="Number of concurrent browser pages (default: 10)",
    )
    crawl_parser.add_argument(
        "--strategy",
        choices=["shallow", "deep"],
        default="deep",
        help="Link discovery strategy (default: deep)",
    )
    crawl_parser.add_argument(
        "--format",
        choices=["markdown", "json", "xml", "xmltei"],
        default="json",
        help="Content extraction format (default: json)",
    )
    crawl_parser.add_argument(
        "--include",
        action="append",
        default=None,
        metavar="PATTERN",
        help="Wildcard pattern for links to include; repeatable",
    )
    crawl_parser.add_argument(
        "--exclude",
        action="append",
        default=None,
        metavar="PATTERN",
        help="Wildcard pattern for links to exclude; repeatable",
    )

    return parser


async def _run_crawl(args: argparse.Namespace) -> None:
    settings = Settings(
        link_extraction_strategy=args.strategy,
        link_extraction_limit=args.limit,
        include_link_patterns=args.include,
        exclude_link_patterns=args.exclude,
        scraping_output_format=args.format,
        concurrency=args.concurrency,
    )
    async with Crawler(settings) as crawler:
        async for item in crawler.stream(args.url):
            print(json.dumps(item))


def main() -> None:
    parser = _build_parser()

    if len(sys.argv) == 1:
        parser.print_help()
        return

    args = parser.parse_args()

    if args.command == "crawl":
        asyncio.run(_run_crawl(args))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
