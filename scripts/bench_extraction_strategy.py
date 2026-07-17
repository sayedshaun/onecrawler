"""Benchmark 'heuristic' (trafilatura) vs 'markdownify' extraction, live.

Discovers a shared URL set once via UniversalSiteMap (falling back to a
shallow LinkExtractor if sitemap discovery finds nothing), then scrapes the
SAME pages with both strategies so the comparison is apples-to-apples, and
reports:

    - success rate (non-None / non-empty result)
    - "likely-failed" rate: extracted text shorter than --min-chars, which is
      the symptom trafilatura shows on non-article pages (e.g. it grabbing
      only a cookie banner instead of real content)
    - average/median extracted length
    - wall-clock and throughput

Defaults to https://quotes.toscrape.com, a free site built for scraping
practice, so you only need to pass --limit/--concurrency. Pass --url to
target a different site.

Usage:
    python scripts/bench_extraction_strategy.py [--url <url>] [--limit N]
        [--concurrency N] [--min-chars N]

Example:
    python scripts/bench_extraction_strategy.py --limit 20

Requires a working Playwright/Chromium install (python -m playwright install
chromium). Both strategies are non-LLM, so no API key is needed.
"""

import argparse
import asyncio
import statistics
import time

from onecrawler import LinkExtractor, Scraper, Settings, UniversalSiteMap

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
        default=20,
        help="maximum number of URLs to discover/scrape (default: 20)",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=5,
        help="number of concurrent workers (default: 5)",
    )
    parser.add_argument(
        "--min-chars",
        type=int,
        default=80,
        help="extracted text shorter than this counts as 'likely failed' (default: 80)",
    )
    return parser.parse_args()


async def discover_urls(url, limit, concurrency):
    """Sitemap first (matches onecrawler's recommended workflow); shallow link
    extraction as a fallback when a site has no usable sitemap."""
    settings = Settings(
        link_extraction_limit=limit,
        concurrency=concurrency,
        show_progress=False,
        logging_level=None,
    )

    sitemap = UniversalSiteMap(settings)
    urls = await sitemap.run(url)
    if urls:
        return urls[:limit], "sitemap"

    settings.link_extraction_strategy = "shallow"
    async with LinkExtractor(settings) as extractor:
        urls = await extractor.run(url)
    return urls[:limit], "shallow link extraction"


def extract_text(result):
    """Normalizes a strategy's result shape to plain text for measurement.

    Heuristic (json format) returns a dict with a 'text' key; markdownify returns a
    plain markdown string.
    """
    if result is None:
        return None
    if isinstance(result, dict):
        return result.get("text") or result.get("raw_text") or ""
    return str(result)


async def run_strategy(strategy, urls, concurrency, output_format="json"):
    settings = Settings(
        scraping_strategy=strategy,
        scraping_output_format=output_format if strategy == "heuristic" else "json",
        concurrency=concurrency,
        show_progress=False,
        logging_level=None,
    )

    start = time.perf_counter()
    async with Scraper(settings) as scraper:
        results = await scraper.run(urls)
    elapsed = time.perf_counter() - start

    by_url = {item["url"]: item["result"] for item in results}
    per_url = []
    for u in urls:
        result = by_url.get(u)
        text = extract_text(result)
        per_url.append(
            {
                "url": u,
                "length": len(text) if text is not None else 0,
                "success": text is not None and len(text) > 0,
            }
        )

    return per_url, elapsed


def report(label, per_url, elapsed, total_urls, min_chars):
    lengths = [r["length"] for r in per_url]
    successes = [r for r in per_url if r["success"]]
    likely_failed = [r for r in per_url if r["success"] and r["length"] < min_chars]

    success_rate = len(successes) / total_urls * 100 if total_urls else 0.0
    failed_rate = len(likely_failed) / total_urls * 100 if total_urls else 0.0
    avg_len = statistics.mean(lengths) if lengths else 0
    median_len = statistics.median(lengths) if lengths else 0
    rate = total_urls / elapsed if elapsed else 0.0

    print(f"\n[{label}]")
    print(
        f"  success rate       : {success_rate:.0f}%  ({len(successes)}/{total_urls} non-empty)"
    )
    print(
        f"  likely-failed rate : {failed_rate:.0f}%  "
        f"({len(likely_failed)}/{total_urls} shorter than {min_chars} chars)"
    )
    print(f"  avg length         : {avg_len:.0f} chars")
    print(f"  median length      : {median_len:.0f} chars")
    print(f"  wall-clock         : {elapsed:.2f} s")
    print(f"  throughput         : {rate:.2f} pages/s")


async def main():
    args = parse_args()

    print(f"Discovering URLs from {args.url}  (limit={args.limit})")
    urls, method = await discover_urls(args.url, args.limit, args.concurrency)
    if not urls:
        print("No URLs discovered; nothing to benchmark.")
        return
    print(f"Discovered {len(urls)} URL(s) via {method}")

    print(f"\nScraping {len(urls)} page(s) with 'heuristic' (trafilatura)...")
    heuristic_per_url, heuristic_elapsed = await run_strategy(
        "heuristic", urls, args.concurrency
    )

    print(f"Scraping {len(urls)} page(s) with 'markdownify'...")
    markdownify_per_url, markdownify_elapsed = await run_strategy(
        "markdownify", urls, args.concurrency
    )

    report(
        "heuristic (trafilatura)",
        heuristic_per_url,
        heuristic_elapsed,
        len(urls),
        args.min_chars,
    )
    report(
        "markdownify",
        markdownify_per_url,
        markdownify_elapsed,
        len(urls),
        args.min_chars,
    )


if __name__ == "__main__":
    asyncio.run(main())
