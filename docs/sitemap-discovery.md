---
title: Sitemap discovery
---

# Sitemap Discovery

Sitemap discovery should be your default URL collection strategy. It is usually
faster, simpler, and more respectful than crawling a site page by page because the
site owner has already published the URL inventory.

Use `UniversalSiteMap` when you want a broad set of URLs before scraping, indexing,
or applying deeper filters.

## What It Does

`UniversalSiteMap` normalizes the base URL and tries multiple discovery strategies:

1. Read sitemap directives from `robots.txt`.
2. Probe common sitemap paths such as `/sitemap.xml`.
3. Parse XML sitemap indexes, URL sets, `.xml.gz` files, RSS feeds, and Atom feeds.
4. Fall back to same-origin HTML crawling when sitemap sources are empty and
   `sitemap_html_fallback=True`.
5. Remove sitemap XML URLs from the final result.
6. Apply `include_link_patterns` and deduplicate results.
7. Cap the final list at `link_extraction_limit`.

## Basic Usage

```python
import asyncio
from onecrawler import CrawlerSettings, UniversalSiteMap


async def main():
    settings = CrawlerSettings(
        link_extraction_limit=1000,
        include_link_patterns=["/blog/*"],
        concurrency=10,
        request_timeout=15,
        max_retries=3,
    )

    sitemap = UniversalSiteMap(settings)
    urls = await sitemap.run("https://example.com")

    for url in urls:
        print(url)


if __name__ == "__main__":
    asyncio.run(main())
```

## When To Use It

Use sitemap discovery when:

- the target is a news site, blog, documentation site, ecommerce site, or CMS-backed
  publication
- you want the fastest route to a large URL list
- you need a stable scheduled job
- you want to avoid expensive browser crawling
- you plan to scrape many pages from the same domain

Avoid relying only on sitemaps when:

- the site does not publish one
- the sitemap is stale or incomplete
- URLs are hidden behind logged-in navigation
- important links are generated only after user interaction

In those cases, combine sitemap discovery with `LinkExtractionEngine`.

## Recommended Production Pattern

Run sitemap discovery first, then fall back to deep link extraction only if the
sitemap returns too few URLs.

```python
import asyncio
from onecrawler import CrawlerSettings, LinkExtractionEngine, UniversalSiteMap


async def discover_urls(base_url: str) -> list[str]:
    settings = CrawlerSettings(
        link_extraction_strategy="deep",
        link_extraction_limit=500,
        include_link_patterns=["/docs/*"],
        concurrency=8,
        request_timeout=15,
    )

    sitemap = UniversalSiteMap(settings)
    urls = await sitemap.run(base_url)

    if len(urls) >= 25:
        return urls

    async with LinkExtractionEngine(settings) as engine:
        return await engine.run(base_url)


if __name__ == "__main__":
    print(asyncio.run(discover_urls("https://example.com")))
```

This pattern keeps the common path fast while still handling sites with missing or
weak sitemap coverage.

## Filtering With URL Patterns

`include_link_patterns` keeps discovery focused. Patterns are matched against URL
paths, so these are good filters:

```python
settings = CrawlerSettings(
    include_link_patterns=[
        "/news/*",
        "/features/*",
        "/guides/*",
    ]
)
```

Prefer specific section filters over collecting an entire domain. Broad discovery can
pull in tag pages, author archives, pagination, static assets, and outdated content.

## Performance Notes

Sitemap discovery uses asynchronous HTTP requests and a shared concurrency limit.
Increase `concurrency` for large sitemap indexes, but do it gradually. If you see
timeouts, `403`, or `429` responses, lower concurrency and increase retry delay.

For large sites:

- set `link_extraction_limit` to the maximum number of URLs your pipeline can process
- keep `sitemap_deduplicate=True`
- use `include_link_patterns` to remove irrelevant sections early
- disable HTML fallback if sitemap-only results are required

```python
settings = CrawlerSettings(
    sitemap_html_fallback=False,
    sitemap_deduplicate=True,
    link_extraction_limit=5000,
    include_link_patterns=["/products/*"],
)
```

## Edge Cases

Some sites publish nested sitemap indexes. Onecrawler follows child XML sitemaps and
deduplicates final URLs.

Some sites publish compressed `.xml.gz` sitemaps. Onecrawler decompresses them when
the URL or response headers indicate gzip content.

Some feeds expose URLs in RSS or Atom format rather than a standard URL set.
Onecrawler attempts to extract those links too.

If no sitemap records are found and HTML fallback is enabled, Onecrawler performs a
bounded same-origin crawl using `max_crawl_pages` and `max_crawl_depth`.

## Troubleshooting

If sitemap discovery returns no URLs:

- try the exact sitemap URL directly, such as `https://example.com/sitemap.xml`
- lower `include_link_patterns` restrictions
- increase `request_timeout`
- check whether `robots.txt` points to a different host or subdomain
- use browser-based link extraction as a fallback

If results include URLs you do not want, tighten path filters before increasing the
limit. Filtering early is cheaper than cleaning a noisy result set later.
