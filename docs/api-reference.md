---
title: API reference
---

# API reference

The package exports the following public symbols from `onecrawler.__init__`:

- `CrawlerSettings`
- `LinkClassifierPipeline`
- `LinkExtractionEngine`
- `ScraperEngine`
- `SiteMap`
- `SitemapStats`
- `UniversalSiteMap`

## CrawlerSettings

Configuration object used by the crawler, sitemap, and scraper components.

## LinkExtractionEngine

Async engine for extracting links from a target page or site.

Common usage:

```python
async with LinkExtractionEngine(config) as engine:
    links = await engine.run(url)
```

## ScraperEngine

Async engine for scraping structured content from discovered URLs.

Common usage:

```python
async with ScraperEngine(config) as engine:
    data = await engine.run(urls)
```

## UniversalSiteMap

Sitemap resolver for discovering URLs through a site's sitemap ecosystem.

Common usage:

```python
sitemap = UniversalSiteMap(config)
urls = await sitemap.run(base_url)
```

## SiteMap and SitemapStats

Helper types associated with sitemap discovery and reporting.

## LinkClassifierPipeline

Publicly exported classifier pipeline for link categorization and filtering.

## Notes

This project currently documents the public API that is exposed from the package root. For deeper module-level details, keep the source tree and examples in sync as the code evolves.
