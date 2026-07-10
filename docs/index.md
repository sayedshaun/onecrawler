---
title: OneCrawler
hide:
  - navigation
---

<div class="hero" markdown>

<img src="static/onecrawl_logo.svg" alt="OneCrawler logo" class="hero-logo">

# OneCrawler

**An async Python framework for discovering URLs, extracting links, and scraping structured content.**

[![PyPI](https://img.shields.io/badge/pypi-onecrawler-6B45A7.svg)](https://pypi.org/project/onecrawler/)
[![CI](https://img.shields.io/badge/CI-passing-brightgreen.svg)](https://github.com/sayedshaun/onecrawler/actions/workflows/ci.yml)
[![Coverage](https://img.shields.io/badge/coverage-85%25-orange.svg)](https://codecov.io/gh/sayedshaun/onecrawler)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/sayedshaun/onecrawler/blob/main/LICENSE)
[![Python](https://img.shields.io/badge/python-3.10--3.14-blue.svg)](https://www.python.org/downloads/)

[Get started](quick-start.md){ .md-button .md-button--primary }
[Installation](installation.md){ .md-button }
[View on GitHub](https://github.com/sayedshaun/onecrawler){ .md-button }

</div>

```python
from onecrawler import Settings, UniversalSiteMap, Scraper
from onecrawler.utils import writter


async def main():
    settings = Settings(include_link_patterns=["/news/*"], concurrency=10)

    async with UniversalSiteMap(settings) as sitemap:
        urls = await sitemap.run("https://example.com")

    async with Scraper(settings) as scraper:
        results = await scraper.run(urls)

    writter.dump_json(results, "output.json")
```

## Why OneCrawler

Many crawling projects start as small scripts and become hard to maintain once they
need retries, concurrency, browser rendering, sitemap fallback, URL filtering, and
structured extraction. OneCrawler gives those concerns a shared settings model and a
few focused async engines, so production scripts stay readable.

<div class="grid cards" markdown>

-   :material-sitemap:{ .lg .middle } __Sitemap-first discovery__

    ---

    Collect URLs from `robots.txt`, sitemap indexes, `.xml.gz`, and feeds — no browser
    required. Falls back to HTML crawling only when needed.

    [:octicons-arrow-right-24: Sitemap discovery](packages/sitemap.md)

-   :material-web:{ .lg .middle } __Browser link extraction__

    ---

    Playwright-backed `shallow` and `deep` traversal for JavaScript-rendered pages and
    sites without usable sitemaps.

    [:octicons-arrow-right-24: Link extraction](packages/link-extraction.md)

-   :material-text-box-search:{ .lg .middle } __Heuristic & GenAI scraping__

    ---

    Fast trafilatura-based extraction by default, or a typed GenAI pipeline with a
    Pydantic `output_schema` when you need structured fields.

    [:octicons-arrow-right-24: Scraping engine](packages/scraping.md)

-   :material-filter-variant:{ .lg .middle } __Composable filters__

    ---

    Filter extracted content by date, keywords, file type, or similarity — and combine
    predicates with `AND` / `OR` / `NOT`.

    [:octicons-arrow-right-24: Filters](packages/filters.md)

-   :material-lightning-bolt:{ .lg .middle } __Async & concurrent__

    ---

    Every engine is `async with`-managed with tunable concurrency, retries, and
    timeouts from a single `Settings` object.

    [:octicons-arrow-right-24: Configuration](configuration.md)

-   :material-server-network:{ .lg .middle } __Proxy rotation__

    ---

    Fan requests across a proxy pool with round-robin rotation, shared by both the
    sitemap layer and the browser engine.

    [:octicons-arrow-right-24: Settings](packages/settings.md)

</div>

!!! tip "Recommended first path"
    Start with sitemap discovery, store the URL list, then scrape those URLs in a
    separate step. This gives you cleaner retries and easier debugging.

## Choosing the right tool

| Goal | Recommended feature | Why |
| --- | --- | --- |
| Collect most public URLs quickly | `UniversalSiteMap` | Uses `robots.txt`, common sitemap paths, nested sitemap indexes, and optional HTML fallback |
| Inspect one listing page | shallow link extraction | Lower crawl cost and easier to reason about |
| Explore a site section recursively | deep link extraction | Follows internal links until your settings limit |
| Extract readable article text | heuristic scraping | Fast, deterministic, and does not require model calls |
| Produce strongly typed output | GenAI scraping with a Pydantic schema | Best fit when downstream systems require a stable structured shape |
| Filter results by date, keywords, or topic | `onecrawler.filters` with `AND`/`OR`/`NOT` | Composable post-extraction filters keep only relevant content |
| Avoid noisy crawls | `include_link_patterns` | Keeps discovery focused on URL paths you trust |

## The full workflow

Start with sitemap discovery whenever possible — it is the fastest, cleanest, and
least expensive way to collect URLs. If the site has no useful sitemap, use
`LinkExtractor` (`shallow` for one page, `deep` for recursive traversal), then pass the
final URL list to `Scraper`.

```python
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
    import asyncio

    asyncio.run(main())
```

!!! warning "Crawling needs boundaries"
    Always set reasonable limits, filters, retries, and concurrency. Clear crawl
    boundaries protect both your job and the target site.

## Production principles

- **Prefer sitemaps before crawling pages.** They are faster, friendlier to target
  sites, and usually more complete than what a browser can discover from navigation.
- **Constrain every job.** Set `link_extraction_limit`, `include_link_patterns`,
  `concurrency`, `request_timeout`, and `max_retries` explicitly so a crawl behaves
  predictably when the target site changes.
- **Use heuristic scraping by default.** It is cheaper and more repeatable; move to
  GenAI only when you need semantic interpretation, field normalization, or a typed
  Pydantic schema.
- **Treat browser crawling as the heavier tool.** It is useful for JavaScript-rendered
  pages and dynamic link discovery, but has more moving parts than sitemap parsing or
  direct HTTP fetching.

## Where to next

<div class="grid cards" markdown>

-   :material-download:{ .lg .middle } __Installation__

    ---

    Package setup, browser requirements, and optional extras.

    [:octicons-arrow-right-24: Install OneCrawler](installation.md)

-   :material-rocket-launch:{ .lg .middle } __Quick start__

    ---

    First complete discovery and scraping workflows, end to end.

    [:octicons-arrow-right-24: Quick start](quick-start.md)

-   :material-cog:{ .lg .middle } __Configuration__

    ---

    Every `Settings` field, defaults, and how the engines use them.

    [:octicons-arrow-right-24: Configuration](configuration.md)

-   :material-api:{ .lg .middle } __API reference__

    ---

    Public classes and functions exported from `onecrawler`.

    [:octicons-arrow-right-24: API reference](api-reference.md)

</div>
