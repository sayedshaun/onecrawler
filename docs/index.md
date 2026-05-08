---
title: Onecrawler Documentation
---

# Onecrawler

A production-ready Python toolkit for web crawling, sitemap discovery, and structured content extraction.

Onecrawler is designed around three core stages:

1. discover URLs
2. extract content
3. shape the output for downstream use

## What you get

- async-first crawling
- deep and shallow link extraction
- sitemap discovery through `robots.txt`, common sitemap paths, nested indexes, and HTML fallback
- optional Playwright-backed browser crawling
- heuristic content extraction with `trafilatura`
- optional AI-based extraction strategy
- multiple output formats including `markdown`, `json`, `csv`, `html`, `txt`, `xml`, `xmltei`, and `python`

## Start here

- [Installation](installation.md)
- [Quick start](quick-start.md)
- [Configuration](configuration.md)
- [Sitemap discovery](sitemap-discovery.md)
- [Link extraction](link-extraction.md)
- [Scraping](scraping.md)
- [API reference](api-reference.md)
- [Troubleshooting](troubleshooting.md)
- [Development](development.md)

## Public API

The package exports:

- `CrawlerSettings`
- `LinkClassifierPipeline`
- `LinkExtractionEngine`
- `ScraperEngine`
- `SiteMap`
- `SitemapStats`
- `UniversalSiteMap`

## Typical flow

```python
import asyncio
import json

from onecrawler import CrawlerSettings, LinkExtractionEngine, ScraperEngine

async def main():
    config = CrawlerSettings(
        link_extraction_strategy="deep",
        link_extraction_limit=5,
        concurrency=2,
        scraping_strategy="heuristic",
        scraping_output_format="json",
    )

    async with LinkExtractionEngine(config) as link_engine:
        links = await link_engine.run("https://www.bbc.com/sport")

    async with ScraperEngine(config) as scraper_engine:
        data = await scraper_engine.run(links)

    with open("output.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    asyncio.run(main())
```

## GitHub Pages note

Markdown files work well with GitHub Pages because Pages uses Jekyll to build Markdown into a static site. A `docs/` folder is also a supported publishing source. Use a `docs/index.md` file as the landing page. If you are publishing a user site, the repository name must be `sayedshaun/onecrawler.github.io`. For a project site, the default URL is under the repository path, unless you configure a custom domain.
