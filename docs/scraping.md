---
title: Scraping
---

# Scraping

`ScraperEngine` turns URLs into extracted content. It accepts either a single URL or
a list of URLs and runs extraction concurrently using the limits in
`CrawlerSettings`.

There are two extraction approaches:

- `heuristic`: deterministic content extraction with `trafilatura`
- `genai`: model-assisted structured extraction for typed or semantic output

## Heuristic Extraction

Use heuristic extraction by default. It is faster, cheaper, and more repeatable than
LLM extraction, and it works well for article-like pages, documentation pages, and
many content sites.

```python
import asyncio
from onecrawler import CrawlerSettings, ScraperEngine


async def main():
    settings = CrawlerSettings(
        scraping_strategy="heuristic",
        scraping_output_format="json",
        concurrency=10,
        request_timeout=15,
        max_retries=3,
    )

    async with ScraperEngine(settings) as scraper:
        result = await scraper.run("https://example.com/articles/story")

    print(result)


if __name__ == "__main__":
    asyncio.run(main())
```

For a batch:

```python
async with ScraperEngine(settings) as scraper:
    records = await scraper.run([
        "https://example.com/articles/one",
        "https://example.com/articles/two",
    ])
```

## Output Formats

`scraping_output_format` can be:

- `json`
- `markdown`
- `csv`
- `html`
- `python`
- `txt`
- `xml`
- `xmltei`

Use `json` when the next step is a data pipeline, database insert, search index, or
API response. Use `markdown` or `txt` for summarization and text processing. Use XML
formats when your downstream tool already expects those shapes.

## GenAI Extraction

Use GenAI extraction when you need a strongly typed response, semantic
classification, normalization, or fields that are not reliably available through
plain text extraction.

```python
import asyncio
from typing import Optional
from pydantic import BaseModel
from onecrawler import CrawlerSettings, GenerativeAISettings, ScraperEngine


class CompanyProfile(BaseModel):
    name: str
    description: str
    headquarters: Optional[str] = None
    products: list[str]


async def main():
    settings = CrawlerSettings(
        scraping_strategy="genai",
        scraping_output_format="json",
        genai=GenerativeAISettings(
            provider="openai",
            model_name="gpt-4o-mini",
            api_key="YOUR_API_KEY",
            output_schema=CompanyProfile,
        ),
        concurrency=2,
        request_timeout=30,
    )

    async with ScraperEngine(settings) as scraper:
        profile = await scraper.run("https://example.com/about")

    print(profile)


if __name__ == "__main__":
    asyncio.run(main())
```

GenAI extraction is the right choice when downstream code depends on a schema. For
example, a Pydantic model lets your application validate fields before saving them.

Avoid GenAI extraction when:

- you only need raw article text
- you are processing thousands of pages and cost matters
- the page structure is consistent enough for heuristic extraction
- deterministic reproducibility is more important than semantic interpretation

## Recommended Pipeline

For production jobs, split discovery and scraping into separate steps.

```python
import json
import asyncio
from onecrawler import CrawlerSettings, ScraperEngine, UniversalSiteMap


async def main():
    settings = CrawlerSettings(
        link_extraction_limit=500,
        include_link_patterns=["/reports/*"],
        scraping_strategy="heuristic",
        scraping_output_format="json",
        concurrency=8,
        max_retries=3,
    )

    sitemap = UniversalSiteMap(settings)
    urls = await sitemap.run("https://example.com")

    async with ScraperEngine(settings) as scraper:
        records = await scraper.run(urls)

    with open("records.json", "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    asyncio.run(main())
```

This pattern gives you a clear boundary: if scraping fails, you can retry the saved
URL batch without rediscovering links.

## Performance Notes

Scraping runs under a semaphore controlled by `concurrency`. Higher values can
increase throughput, but only until the network, target site, browser, or model API
becomes the bottleneck.

Use these starting points:

| Workload | Suggested settings |
| --- | --- |
| Heuristic article extraction | `concurrency=10`, `request_timeout=15` |
| Slow pages | `concurrency=5`, `request_timeout=30` |
| GenAI extraction | `concurrency=2`, `request_timeout=30` |
| Unstable targets | `max_retries=3`, lower concurrency |

For model-based extraction, keep concurrency low enough to respect provider limits
and avoid expensive retry storms.

## Caveats

Some pages render content only after JavaScript execution. `ScraperEngine` starts a
browser when browser settings are present, so browser-backed extraction can retrieve
rendered HTML before passing it to the extraction strategy.

Heuristic extraction can return `None` when a page is empty, blocked, not article-like,
or unsupported by the extractor. Filter or log failed URLs so you can inspect them
later.

`ScraperEngine.run()` returns a single result for a single input URL and a list of
results for a list input. Empty or failed pages are omitted from batch results.
