---
title: Link extraction
---

# Link extraction

`LinkExtractionEngine` is responsible for discovering links from a starting URL.

## Crawl modes

- `deep`: follow links recursively within the configured limits
- `shallow`: keep the crawl more constrained and focused

## Example

```python
import asyncio

from onecrawler import CrawlerSettings, LinkExtractionEngine

async def main():
    config = CrawlerSettings(
        link_extraction_strategy="deep",
        link_extraction_limit=200,
        include_link_patterns=["/sports/*", "/news/*"],
        concurrency=10,
    )

    async with LinkExtractionEngine(config) as engine:
        links = await engine.run("https://example.com")

    print(links)

if __name__ == "__main__":
    asyncio.run(main())
```

## Filtering

`include_link_patterns` lets you narrow the crawl to specific URL path patterns using wildcard matching.

Example patterns:

- `/news/*`
- `/sports/*`
- `/articles/*`
