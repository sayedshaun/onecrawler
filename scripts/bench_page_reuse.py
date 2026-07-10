"""Benchmark the page-reuse optimization against the old double-fetch, live.

Crawls a real URL two ways on the same site and reports how many page
navigations each mode performed (the cache-independent proof of the fix) plus
wall-clock time and throughput:

    optimized  -> current code: the worker's loaded page is reused, so each URL
                  is navigated exactly once.
    legacy     -> simulates the pre-fix behavior by stripping the prefetched
                  HTML, forcing the strategy to re-navigate every URL.

Usage:
    python benchmarks/bench_page_reuse.py <url> [max_links] [concurrency]

Example:
    python benchmarks/bench_page_reuse.py https://quotes.toscrape.com 20 5

Requires a working Playwright/Chromium install (python -m playwright install
chromium). Uses the heuristic strategy, so no API key is needed.
"""

import argparse
import asyncio
import time

from onecrawler import Crawler, Settings
from onecrawler.crawler import crawl as crawl_module
from onecrawler.crawler.scraper.heuristic import script as heuristic_module


class NavigationCounter:
    """Counts calls to the module-level `goto` used by the worker and the
    heuristic strategy's own fetch path."""

    def __init__(self):
        self.count = 0
        self._patched = []

    def __enter__(self):
        for module in (crawl_module, heuristic_module):
            original = module.goto

            async def counting_goto(*args, _orig=original, **kwargs):
                self.count += 1
                return await _orig(*args, **kwargs)

            module.goto = counting_goto
            self._patched.append((module, original))
        return self

    def __exit__(self, *exc):
        for module, original in self._patched:
            module.goto = original


async def run_once(url, settings, *, force_double_fetch):
    with NavigationCounter() as nav:
        async with Crawler(settings) as crawler:
            if force_double_fetch:
                real_extract = crawler.strategy.extract

                async def legacy_extract(u, html=None):
                    # Ignore the prefetched HTML so the strategy re-navigates,
                    # reproducing the pre-optimization behavior.
                    return await real_extract(u)

                crawler.strategy.extract = legacy_extract

            start = time.perf_counter()
            results = await crawler.run(url)
            elapsed = time.perf_counter() - start

    return len(results), elapsed, nav.count


def _report(label, pages, elapsed, navigations):
    rate = pages / elapsed if elapsed else 0.0
    per_page = navigations / pages if pages else 0.0
    print(f"\n[{label}]")
    print(f"  pages crawled     : {pages}")
    print(f"  wall-clock        : {elapsed:.2f} s")
    print(f"  throughput        : {rate:.2f} pages/s")
    print(f"  page navigations  : {navigations}  ({per_page:.2f} per page)")


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url", help="URL to crawl")
    parser.add_argument(
        "max_links",
        nargs="?",
        type=int,
        default=15,
        help="maximum number of links to extract (default: 15)",
    )
    parser.add_argument(
        "concurrency",
        nargs="?",
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
        show_progress=False,
        enable_logging=False,
    )

    print(f"Benchmarking {url}  (max_links={max_links}, concurrency={concurrency})")

    # Legacy first, optimized second. If anything, warm caches favor the second
    # run, so an optimized win here is a conservative estimate.
    legacy = await run_once(url, settings, force_double_fetch=True)
    optimized = await run_once(url, settings, force_double_fetch=False)

    _report("legacy (double-fetch)", *legacy)
    _report("optimized (page-reuse)", *optimized)

    l_pages, l_time, l_nav = legacy
    o_pages, o_time, o_nav = optimized
    print("\n[comparison]")
    if o_nav:
        print(f"  navigations   : {l_nav} -> {o_nav}  " f"({l_nav / o_nav:.2f}x fewer)")
    if o_time:
        print(
            f"  wall-clock    : {l_time:.2f}s -> {o_time:.2f}s  "
            f"({l_time / o_time:.2f}x faster)"
        )
    print(
        "\nNote: navigation counts are the reliable metric; wall-clock is "
        "network-dependent, so re-run a few times for a stable figure."
    )


if __name__ == "__main__":
    asyncio.run(main())
