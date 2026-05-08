---
title: Quick start
---

# Quick start

The simplest workflow is:

1. create a `CrawlerSettings` instance
2. extract links with `LinkExtractionEngine`
3. scrape those links with `ScraperEngine`

## Example

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

## What the example does

- crawls a target section
- extracts up to 5 links
- scrapes the collected pages
- writes the result to `output.json`
