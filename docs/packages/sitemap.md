---
title: Sitemap Discovery
---

# Sitemap Discovery Package

The `onecrawler.map` package provides comprehensive sitemap discovery and parsing capabilities for efficient URL collection.

## Classes

### UniversalSiteMap

High-level sitemap resolver that automatically discovers sitemaps through multiple methods.

```python
from onecrawler import CrawlerSettings, UniversalSiteMap

sitemap = UniversalSiteMap(settings)
urls = await sitemap.run("https://example.com")
```

#### Features

- **robots.txt parsing**: Extracts sitemap directives from robots.txt
- **Common path discovery**: Checks standard sitemap locations
- **Nested index parsing**: Handles sitemap index files
- **HTML fallback**: Crawls pages when no sitemaps are found
- **Compression support**: Handles .xml.gz compressed sitemaps

### SiteMap

Lower-level sitemap parser for direct sitemap URL processing.

```python
from onecrawler import CrawlerSettings, SiteMap

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
from onecrawler.map.sitemap import SitemapStats

stats = SitemapStats()
print(f"Discovered {stats.url_count} URLs")
```

#### Properties

- `url_count`: Total URLs discovered
- `sitemap_count`: Number of sitemaps processed
- `error_count`: Number of errors encountered
- `elapsed_time`: Total processing time

## Usage Examples

### Basic Sitemap Discovery

```python
import asyncio
from onecrawler import CrawlerSettings, UniversalSiteMap

async def discover_urls():
    settings = CrawlerSettings(
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
from onecrawler import CrawlerSettings, UniversalSiteMap

settings = CrawlerSettings(
    follow_sitemap_index=True,
    sitemap_html_fallback=True,
    max_crawl_depth=3,
    max_crawl_pages=500,
    sitemap_user_agent="MyCrawler/1.0",
    sitemap_respect_robots=True,
    sitemap_deduplicate=True
)

sitemap = UniversalSiteMap(settings)
```

### Direct Sitemap Parsing

```python
from onecrawler import CrawlerSettings, SiteMap

async def parse_specific_sitemap():
    settings = CrawlerSettings()
    sitemap = SiteMap(settings)
    
    urls = await sitemap.run("https://example.com/sitemap.xml")
    return urls
```

## Configuration

Sitemap behavior is controlled through `CrawlerSettings`:

| Setting | Description | Default |
|---------|-------------|---------|
| `follow_sitemap_index` | Traverse sitemap indexes | `True` |
| `sitemap_html_fallback` | Crawl pages when no sitemaps | `True` |
| `max_crawl_depth` | Depth limit for HTML fallback | `3` |
| `max_crawl_pages` | Page limit for HTML fallback | `500` |
| `sitemap_user_agent` | User agent for sitemap requests | Custom |
| `sitemap_respect_robots` | Follow robots.txt rules | `True` |
| `sitemap_deduplicate` | Remove duplicate URLs | `True` |

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
