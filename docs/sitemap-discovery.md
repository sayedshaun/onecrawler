---
title: Sitemap discovery
---

# Sitemap discovery

Onecrawler includes `UniversalSiteMap` for collecting URLs from a site's sitemap infrastructure before scraping.

## What it supports

- `robots.txt` resolution
- common sitemap paths
- nested sitemap indexes
- HTML fallback when sitemap discovery is incomplete

## Example

```python
import asyncio

from onecrawler import CrawlerSettings, UniversalSiteMap

async def main():
    config = CrawlerSettings(
        link_extraction_limit=100,
        include_link_patterns=["/news/*"],
    )

    sitemap = UniversalSiteMap(config)
    urls = await sitemap.run("https://example.com")
    print(urls)

if __name__ == "__main__":
    asyncio.run(main())
```

## When to use it

Use sitemap discovery when you want a broad and efficient starting point before moving into crawling or scraping.
