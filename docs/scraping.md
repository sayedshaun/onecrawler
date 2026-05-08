---
title: Scraping
---

# Scraping

`ScraperEngine` extracts structured content from a set of URLs.

## Supported approaches

- heuristic extraction via `trafilatura`
- optional AI-based extraction strategy

## Output formats

- `markdown`
- `json`
- `csv`
- `html`
- `txt`
- `xml`
- `xmltei`
- `python`

## Example

```python
import asyncio

from onecrawler import CrawlerSettings, ScraperEngine

async def main():
    config = CrawlerSettings(
        scraping_strategy="heuristic",
        scraping_output_format="markdown",
        concurrency=20,
        max_retries=3,
        request_timeout=10,
    )

    async with ScraperEngine(config) as scraper:
        data = await scraper.run([
            "https://example.com/article-1",
            "https://example.com/article-2",
        ])

    print(data)

if __name__ == "__main__":
    asyncio.run(main())
```

## Practical notes

- increase `concurrency` carefully
- use retries for unstable pages
- choose the output format that matches your downstream pipeline
