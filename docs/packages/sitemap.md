---
title: Sitemap Discovery
---

# Sitemap Discovery Package

The sitemap package provides discovery and parsing utilities for efficient URL
collection.

!!! tip "Prefer sitemap discovery first"
    Sitemaps are usually faster, cheaper, and more stable than browser crawling.
    Start here before reaching for `LinkExtractor`.

## Classes

### UniversalSiteMap

High-level sitemap resolver that automatically discovers sitemaps through multiple methods.

```python
from onecrawler import Settings, UniversalSiteMap

sitemap = UniversalSiteMap(settings)
urls = await sitemap.run("https://example.com")
```

#### Features

- **robots.txt parsing**: Extracts sitemap directives from robots.txt
- **Common path discovery**: Checks standard sitemap locations
- **Nested index parsing**: Handles sitemap index files
- **HTML fallback**: Crawls pages when no sitemaps are found
- **Compression support**: Handles .xml.gz compressed sitemaps

!!! note "Use the public import"
    Most user code should import `UniversalSiteMap` from `onecrawler`, not from an
    internal package path.

### SiteMap

Lower-level sitemap parser for direct sitemap URL processing.

!!! warning "Deprecated"
    `SiteMap` will be removed in a future major version. It only walks raw
    sitemap XML — it doesn't discover sitemaps via robots.txt or common
    paths, doesn't enforce `respect_robots`, and has no HTML-crawl fallback
    or date/pattern filtering. Use `UniversalSiteMap` instead, which covers
    everything `SiteMap` does plus those.

```python
from onecrawler import Settings, SiteMap

sitemap = SiteMap(settings)
urls = await sitemap.run("https://example.com/sitemap.xml")
```

#### Features

- **Direct parsing**: Parse specific sitemap URLs
- **URL validation**: Validates and normalizes URLs
- **Metadata extraction**: Extracts lastmod, changefreq, priority

### SitemapStats

Statistics tracking for sitemap operations.

```python
from onecrawler import SitemapStats

stats = SitemapStats()
print(f"Discovered {stats.urls} URLs")
```

#### Properties

- `urls`: Total URLs discovered
- `sitemaps`: Number of sitemaps processed
- `errors`: Number of errors encountered
- `elapsed()`: Elapsed processing time in seconds
- `rate()`: URLs discovered per second

## Usage Examples

### Basic Sitemap Discovery

```python
import asyncio
from onecrawler import Settings, UniversalSiteMap

async def discover_urls():
    settings = Settings(
        link_extraction_limit=1000,
        include_link_patterns=["/articles/*"]
    )
    
    sitemap = UniversalSiteMap(settings)
    urls = await sitemap.run("https://example.com")
    
    return urls

if __name__ == "__main__":
    asyncio.run(discover_urls())
```

### Advanced Configuration

```python
from onecrawler import Settings, UniversalSiteMap
from onecrawler.settings import SitemapSettings

settings = Settings(
    sitemap=SitemapSettings(
        follow_index=True,
        html_fallback=True,
        max_depth=3,
        max_pages=500,
        user_agent="MyCrawler/1.0",
        respect_robots=True,
        deduplicate=True
    )
)

sitemap = UniversalSiteMap(settings)
```

!!! warning "HTML fallback can broaden scope"
    `sitemap.html_fallback=True` is useful during exploration, but it can crawl
    same-origin pages when XML sitemaps are missing. Pair it with
    `link_extraction_limit` and `include_link_patterns`.

### Direct Sitemap Parsing

!!! warning "Deprecated — use UniversalSiteMap"
    See the note under [SiteMap](#sitemap) above.

```python
from onecrawler import Settings, SiteMap

async def parse_specific_sitemap():
    settings = Settings()
    sitemap = SiteMap(settings)
    
    urls = await sitemap.run("https://example.com/sitemap.xml")
    return urls
```

## Configuration

Sitemap behavior is controlled through `Settings`:

| Setting | Description | Default |
|---------|-------------|---------|
| `sitemap.follow_index` | Traverse sitemap indexes | `True` |
| `sitemap.html_fallback` | Crawl pages when no sitemaps | `True` |
| `sitemap.max_depth` | Depth limit for HTML fallback | `3` |
| `sitemap.max_pages` | Page limit for HTML fallback | `500` |
| `sitemap.user_agent` | User agent for sitemap requests | Custom |
| `sitemap.respect_robots` | Reserved; not currently enforced by discovery | `True` |
| `sitemap.deduplicate` | Remove duplicate URLs | `True` |

## Discovery Process

UniversalSiteMap follows this discovery order:

1. **robots.txt**: Check for `Sitemap:` directives
2. **Common paths**: Try standard locations:
   - `/sitemap.xml`
   - `/sitemap_index.xml`
   - `/sitemap.xml.gz`
   - `/sitemaps.xml`
3. **Nested indexes**: Parse sitemap index files recursively
4. **HTML fallback**: Crawl pages if no sitemaps found

!!! tip "Disable fallback for strict sitemap jobs"
    If a job should only trust XML sitemap sources, set `sitemap.html_fallback=False`
    after you confirm the sitemap URLs you need.

## Sitemap Formats Supported

### Standard XML Sitemap

```xml
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://example.com/page1</loc>
    <lastmod>2024-01-01</lastmod>
    <changefreq>daily</changefreq>
    <priority>0.8</priority>
  </url>
</urlset>
```

### Sitemap Index

```xml
<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <sitemap>
    <loc>https://example.com/sitemap1.xml</loc>
    <lastmod>2024-01-01</lastmod>
  </sitemap>
</sitemapindex>
```

### Compressed Sitemaps

Supports `.xml.gz` compressed sitemaps for faster downloads.

## Performance Tips

1. **Prefer sitemaps**: Always use sitemaps when available
2. **Set limits**: Use `link_extraction_limit` to control scope
3. **Filter patterns**: Use `include_link_patterns` for targeted URLs
4. **Monitor stats**: Track discovery rates and errors
5. **Fallback control**: Disable HTML fallback for predictable jobs

!!! note "Metadata availability varies"
    Sitemap fields such as `lastmod`, `changefreq`, and `priority` are optional.
    Treat them as hints from the publisher, not guaranteed freshness signals.

## Error Handling

The sitemap system gracefully handles:

- **Network errors**: Automatic retries with exponential backoff
- **Malformed XML**: Parser error recovery
- **Missing sitemaps**: Falls back to HTML discovery
- **Rate limiting**: Respects retry-after headers

## Best Practices

1. **Check robots.txt**: Respect site crawling policies
2. **Use appropriate user agent**: Identify your crawler
3. **Set reasonable limits**: Don't overwhelm target servers
4. **Monitor performance**: Track discovery success rates
5. **Handle errors gracefully**: Implement retry logic

!!! warning "Respect crawl policies"
    Even sitemap discovery can produce a large URL list. Keep limits reasonable,
    identify your crawler with a user agent when appropriate, and follow the target
    site's crawling policies.
