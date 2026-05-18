---
title: Link Extraction
---

# Link Extraction Package

The link extraction package provides classes for discovering links from rendered web
pages using browser automation.

!!! note "Use this after sitemaps"
    Browser link extraction is best when sitemaps are missing, incomplete, or unable
    to expose JavaScript-rendered links. If a sitemap is available, start with
    `UniversalSiteMap`.

## Classes

### LinkExtractor

The main engine for extracting links from web pages using Playwright browser automation.

```python
from onecrawler import Settings, LinkExtractor

async with LinkExtractor(settings) as engine:
    links = await engine.run("https://example.com")
```

#### Parameters

- `settings` (`Settings`): Configuration for link extraction behavior

#### Methods

- `run(url: str) -> List[str]`: Extract links from the given URL

#### Features

- **Shallow extraction**: Extract links from a single page
- **Deep extraction**: Recursively follow same-site links
- **URL filtering**: Include/exclude patterns for targeted extraction
- **Human behavior simulation**: Optional delays and interactions

!!! tip "Choose shallow before deep"
    Use `shallow` for listing pages where all target links are visible on one page.
    Use `deep` only when you need recursive discovery.

### LinkClassifierPipeline

Crawler for classifying and filtering extracted links based on various criteria.

```python
from onecrawler.crawler.link.classifier import LinkClassifierPipeline

classifier = LinkClassifierPipeline(settings)
filtered_links = classifier.classify(links)
```

#### Features

- **Domain filtering**: Ensure same-origin links
- **Path pattern matching**: Wildcard-based URL filtering
- **Deduplication**: Remove duplicate URLs
- **Normalization**: Clean and standardize URLs

## Usage Examples

### Shallow Link Extraction

```python
import asyncio
from onecrawler import Settings, LinkExtractor

async def extract_shallow():
    settings = Settings(
        link_extraction_strategy="shallow",
        link_extraction_limit=50,
        include_link_patterns=["/articles/*"]
    )
    
    async with LinkExtractor(settings) as engine:
        links = await engine.run("https://example.com/latest")
    
    return links

if __name__ == "__main__":
    asyncio.run(extract_shallow())
```

### Deep Link Extraction

```python
import asyncio
from onecrawler import Settings, LinkExtractor

async def extract_deep():
    settings = Settings(
        link_extraction_strategy="deep",
        link_extraction_limit=300,
        include_link_patterns=["/docs/*"],
        concurrency=5
    )
    
    async with LinkExtractor(settings) as engine:
        links = await engine.run("https://example.com/docs")
    
    return links

if __name__ == "__main__":
    asyncio.run(extract_deep())
```

!!! warning "Deep extraction needs guardrails"
    Always set `link_extraction_limit` for deep crawls. Add
    `include_link_patterns` whenever you only care about one section, such as
    `/news/*` or `/docs/*`.

### With Human Behavior Simulation

```python
from onecrawler import Settings, LinkExtractor, HumanBehaviorSettings

settings = Settings(
    link_extraction_strategy="deep",
    enable_human_behaviors=True,
    human_behavior_settings=HumanBehaviorSettings(
        min_delay=0.5,
        max_delay=1.5,
        max_scrolls=25
    )
)
```

!!! tip "Human behavior is for lazy loading"
    Enable human behavior simulation when links appear after scrolling or delayed
    rendering. Keep it disabled for normal pages because it slows down every worker.

## Configuration

The link extraction behavior is controlled through `Settings`:

| Setting | Description | Default |
|---------|-------------|---------|
| `link_extraction_strategy` | `"shallow"` or `"deep"` | `"deep"` |
| `link_extraction_limit` | Maximum links to extract | `50` |
| `include_link_patterns` | URL path patterns to include | `None` |
| `exclude_link_patterns` | URL path patterns to exclude | `None` |
| `concurrency` | Number of parallel browser workers | `10` |
| `enable_human_behaviors` | Enable human-like interactions | `False` |

## Performance Considerations

- **Memory usage**: Each browser page consumes memory
- **Concurrency**: Start with 3-5 workers, increase gradually
- **Rate limiting**: Respect target site's capacity
- **Timeouts**: Adjust for slow-loading pages

!!! warning "Watch browser resource usage"
    Each concurrent worker may hold a browser page. If memory, CPU, or target errors
    climb, reduce `concurrency` before increasing timeouts or retries.

## Best Practices

1. **Use sitemaps first**: Prefer `UniversalSiteMap` when available
2. **Filter early**: Use `include_link_patterns` to limit scope
3. **Set limits**: Always specify `link_extraction_limit`
4. **Monitor resources**: Watch memory and CPU usage
5. **Handle errors**: Implement retry logic for failed pages

!!! note "Filtering happens on URL paths"
    `include_link_patterns` should usually look like `"/articles/*"` or
    `"/docs/*"`, not full absolute URLs.
