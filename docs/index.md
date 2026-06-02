---
title: OneCrawler Documentation
---

# OneCrawler

[![PyPI](https://img.shields.io/badge/pypi-onecrawler-6B45A7.svg)](https://pypi.org/project/onecrawler/)
[![CI](https://img.shields.io/badge/CI-passing-brightgreen.svg)](https://github.com/sayedshaun/onecrawler/actions/workflows/ci.yml)
[![Coverage](https://img.shields.io/badge/coverage-85%25-orange.svg)](https://codecov.io/gh/sayedshaun/onecrawler)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/sayedshaun/onecrawler/blob/main/LICENSE)
[![Python](https://img.shields.io/badge/python-3.10--3.14-blue.svg)](https://www.python.org/downloads/)

OneCrawler is an async Python crawling framework for discovering URLs, extracting
links, and scraping structured content.

The framework is designed around a practical crawler workflow:

1. Discover candidate URLs from sitemaps or browser-based link traversal.
2. Filter and limit those URLs to the section you actually care about.
3. Scrape the selected pages with either heuristic extraction or structured GenAI
   extraction.
4. Save the result in the format your application needs.

!!! tip "Recommended first path"
    Start with sitemap discovery, store the URL list, then scrape those URLs in a
    separate step. This gives you cleaner retries and easier debugging.

## Why OneCrawler Exists

Many crawling projects start as small scripts and become hard to maintain once they
need retries, concurrency, browser rendering, sitemap fallback, URL filtering, and
structured extraction. OneCrawler gives those concerns a shared settings model
and a few focused async engines so production scripts stay readable.

!!! warning "Crawling needs boundaries"
    Always set reasonable limits, filters, retries, and concurrency. Clear crawl
    boundaries protect both your job and the target site.

Use it when you are building:

- content ingestion pipelines for news, blogs, catalogs, or documentation sites
- search indexing jobs
- data collection scripts for analysis or monitoring
- internal tools that need repeatable URL discovery and content extraction
- prototypes that may later become production crawlers

!!! note "Use GenAI for semantics, not bulk text"
    Heuristic extraction is the better default for large text extraction jobs. Use
    GenAI when you need summaries, field normalization, or a typed schema.

## Recommended Workflow

Start with sitemap discovery whenever possible. A sitemap is usually the fastest,
cleanest, and least expensive way to collect URLs because it avoids opening many
browser pages just to discover links.

```python
import asyncio

from onecrawler import Settings, LinkExtractor, Scraper
from onecrawler.utils import writter

async def main():
    settings = Settings(
        link_extraction_limit=500,
        include_link_patterns=["/news/*"],
        concurrency=10,
    )

    async with LinkExtractor(settings) as extractor:
        urls = await extractor.run("https://example.com")
        print(f"Found {len(urls)} URLs")

    async with Scraper(settings) as scraper:
        results = await scraper.run(urls)
        print(f"Scraped {len(results)} pages")

    writter.dump_json(results, "output.json")


if __name__ == "__main__":
    asyncio.run(main())
```

If the site has no useful sitemap, use `LinkExtractor`:

- `shallow` for links present on one page
- `deep` for recursive same-site traversal

Then pass the final URL list to `Scraper`.

## Choosing The Right Tool

| Goal | Recommended feature | Why |
| --- | --- | --- |
| Collect most public URLs quickly | `UniversalSiteMap` | Uses `robots.txt`, common sitemap paths, nested sitemap indexes, and optional HTML fallback |
| Inspect one listing page | shallow link extraction | Lower crawl cost and easier to reason about |
| Explore a site section recursively | deep link extraction | Follows internal links until your settings limit |
| Extract readable article text | heuristic scraping | Fast, deterministic, and does not require model calls |
| Produce strongly typed output | GenAI scraping with a Pydantic schema | Best fit when downstream systems require a stable structured shape |
| Filter results by date, keywords, or topic | `onecrawler.filters` with `AND`/`OR`/`NOT` | Composable post-extraction filters keep only relevant content |
| Avoid noisy crawls | `include_link_patterns` | Keeps discovery focused on URL paths you trust |

## Documentation Map

- [Installation](installation.md): package setup, browser requirements, optional extras
- [Quick start](quick-start.md): first complete discovery and scraping workflows
- [Configuration](configuration.md): crawler settings and configuration
- [Filters](packages/filters.md): composable content filters for date, keywords, file type, and similarity
- [Link Extraction](packages/link-extraction.md): `LinkExtractor` and link discovery
- [Sitemap Discovery](packages/sitemap.md): `UniversalSiteMap` and URL collection
- [Scraping Engine](packages/scraping.md): `Scraper` and content extraction
- [Settings Configuration](packages/settings.md): `Settings` and configuration classes
- [API reference](api-reference.md): public classes exported from `onecrawler`
- [Troubleshooting](troubleshooting.md): common failures and fixes

## Production Principles

Prefer sitemaps before crawling pages. They are faster, friendlier to target sites,
and usually more complete than what a browser can discover from navigation pages.

Constrain every job. Set `link_extraction_limit`, `include_link_patterns`,
`concurrency`, `request_timeout`, and `max_retries` explicitly so a crawl behaves
predictably when the target site changes.

Use heuristic scraping by default. It is cheaper and more repeatable. Move to GenAI
when you need semantic interpretation, field normalization, or structured output in a
predefined Pydantic schema.

Treat browser crawling as the heavier tool. It is useful for JavaScript-rendered
pages and dynamic link discovery, but it has more moving parts than sitemap parsing
or direct HTTP fetching.
