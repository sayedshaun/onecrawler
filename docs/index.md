---
title: Onecrawler Documentation
---

# Onecrawler

[![PyPI](https://img.shields.io/badge/pypi-onecrawler-6B45A7.svg)](https://pypi.org/project/onecrawler/)
[![CI](https://img.shields.io/badge/CI-passing-brightgreen.svg)](https://github.com/sayedshaun/onecrawler/actions/workflows/ci.yml)
[![Coverage](https://img.shields.io/badge/coverage-85%25-orange.svg)](https://codecov.io/gh/sayedshaun/onecrawler)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/sayedshaun/onecrawler/blob/main/LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)

Onecrawler is an async Python toolkit for discovering URLs, crawling websites, and
extracting page content into formats that are easier to store, search, analyze, or
send into downstream data pipelines.

The library is designed around a practical crawler workflow:

1. Discover candidate URLs from sitemaps or browser-based link traversal.
2. Filter and limit those URLs to the section you actually care about.
3. Scrape the selected pages with either heuristic extraction or structured GenAI
   extraction.
4. Save the result in the format your application needs.

## Why Onecrawler Exists

Many crawling projects start as small scripts and become hard to maintain once they
need retries, concurrency, browser rendering, sitemap fallback, URL filtering, and
structured extraction. Onecrawler gives those concerns a shared settings model
and a few focused async engines so production scripts stay readable.

Use it when you are building:

- content ingestion pipelines for news, blogs, catalogs, or documentation sites
- search indexing jobs
- data collection scripts for analysis or monitoring
- internal tools that need repeatable URL discovery and content extraction
- prototypes that may later become scheduled crawler jobs

## Recommended Workflow

Start with sitemap discovery whenever possible. A sitemap is usually the fastest,
cleanest, and least expensive way to collect URLs because it avoids opening many
browser pages just to discover links.

```python
import asyncio

from onecrawler import CrawlerSettings, UniversalSiteMap


async def main():
    settings = CrawlerSettings(
        link_extraction_limit=500,
        include_link_patterns=["/news/*"],
        concurrency=10,
    )

    sitemap = UniversalSiteMap(settings)
    urls = await sitemap.run("https://example.com")
    print(f"Found {len(urls)} URLs")


if __name__ == "__main__":
    asyncio.run(main())
```

If the site has no useful sitemap, use `LinkExtractionEngine`:

- `shallow` for links present on one page
- `deep` for recursive same-site traversal

Then pass the final URL list to `ScraperEngine`.

## Choosing The Right Tool

| Goal | Recommended feature | Why |
| --- | --- | --- |
| Collect most public URLs quickly | `UniversalSiteMap` | Uses `robots.txt`, common sitemap paths, nested sitemap indexes, and optional HTML fallback |
| Inspect one listing page | shallow link extraction | Lower crawl cost and easier to reason about |
| Explore a site section recursively | deep link extraction | Follows internal links until your settings limit |
| Extract readable article text | heuristic scraping | Fast, deterministic, and does not require model calls |
| Produce strongly typed output | GenAI scraping with a Pydantic schema | Best fit when downstream systems require a stable structured shape |
| Avoid noisy crawls | `include_link_patterns` | Keeps discovery focused on URL paths you trust |

## Documentation Map

- [Installation](installation.md): package setup, browser requirements, optional extras
- [Quick start](quick-start.md): first complete discovery and scraping workflows
- [settings](settings.md): every important setting and how to tune it
- [Sitemap discovery](sitemap-discovery.md): fastest URL collection path and fallbacks
- [Link extraction](link-extraction.md): shallow versus deep browser crawling
- [Scraping](scraping.md): heuristic extraction, GenAI extraction, and output choices
- [API reference](api-reference.md): public classes exported from `onecrawler`
- [Troubleshooting](troubleshooting.md): common failures and fixes
- [Development](development.md): local contributor workflow

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
