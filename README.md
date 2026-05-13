<div align="center">

<img src="https://raw.githubusercontent.com/sayedshaun/onecrawler/refs/heads/main/docs/static/onecrawl_logo.png" alt="OneCrawler" width="200"/>

# OneCrawler

**OneCrawler is an async Python crawling library for discovering URLs, extracting links, and scraping structured content.**

[![CI](https://github.com/sayedshaun/onecrawler/actions/workflows/ci.yml/badge.svg)](https://github.com/sayedshaun/onecrawler/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![PyPI](https://img.shields.io/badge/pypi-onecrawler-2ea44f.svg)](https://pypi.org/project/onecrawler/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Imports: isort](https://img.shields.io/badge/imports-isort-1674b1.svg)](https://pycqa.github.io/isort/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

[Installation](#installation) · [Quick Start](#quick-start) · [Documentation](#documentation) · [Development](#development)

</div>

---

## Overview

OneCrawler helps you build maintainable crawling and extraction workflows without
turning every project into a custom scraping script. It gives you a shared
configuration model, async execution, sitemap discovery, browser-backed link
extraction, heuristic content extraction, and optional GenAI extraction for typed
outputs.

The recommended workflow is:

1. Use sitemaps first whenever possible.
2. Fall back to browser link extraction when sitemap coverage is missing or dynamic.
3. Scrape the final URL list with heuristic extraction by default.
4. Use GenAI extraction when you need structured output in a Pydantic schema.

```python
async with LinkExtractionEngine(settings) as link_engine:
    links = await link_engine.run("https://example.com")

async with ScraperEngine(settings) as scraper_engine:
    records = await scraper_engine.run(links)
```

---

## Features

| Capability | Details |
| --- | --- |
| **Sitemap discovery** | Resolves `robots.txt`, common sitemap paths, nested indexes, `.xml.gz`, feeds, and HTML fallback |
| **Browser link extraction** | Shallow and deep Playwright-backed discovery for JavaScript-rendered or sitemap-poor sites |
| **URL filtering** | Wildcard path filters with `include_link_patterns` |
| **Async performance** | Tunable concurrency, retries, timeouts, and crawl limits |
| **Content extraction** | Heuristic extraction with `trafilatura` for fast article-like content extraction |
| **GenAI extraction** | Optional model-assisted extraction for strongly typed Pydantic outputs |
| **Output formats** | `markdown`, `json`, `csv`, `html`, `python`, `txt`, `xml`, `xmltei` |
| **Proxy support** | Single proxy or rotating proxy pools for browser and sitemap workflows |
| **Browser controls** | Viewport, user agent, locale, timezone, storage state, and runtime settings |

---

## When To Use What

| Need | Use | Why |
| --- | --- | --- |
| Fast URL discovery from a public site | `UniversalSiteMap` | It is usually the simplest, fastest, and least expensive way to collect URLs |
| Links from one listing page | Shallow `LinkExtractionEngine` | It reads direct same-site links from the page |
| Recursive discovery through navigation | Deep `LinkExtractionEngine` | It follows internal links until your configured limit |
| Bulk article or page text extraction | Heuristic `ScraperEngine` | It is deterministic and avoids model cost |
| Typed fields or semantic normalization | GenAI extraction | It can produce schema-shaped output for downstream systems |

---

## Installation

```bash
pip install onecrawler
```

Install Playwright browser binaries when you use browser-backed crawling or scraping:

```bash
python -m playwright install chromium
```

Install optional GenAI dependencies when you use model-assisted extraction:

```bash
pip install "onecrawler[genai]"
```

For local development:

```bash
git clone https://github.com/sayedshaun/onecrawler.git
cd onecrawler
python -m pip install -e ".[dev]"
python -m playwright install chromium
```

---

## Quick Start

This example uses the common browser-backed workflow: discover links first, then
scrape the discovered URLs.

```python
import json
from onecrawler import CrawlerSettings, LinkExtractionEngine, ScraperEngine


async def main():
    settings = CrawlerSettings(
        link_extraction_strategy="deep",
        link_extraction_limit=10,
        concurrency=7,
        scraping_strategy="heuristic",
        scraping_output_format="json",
        enable_human_behaviors=True,
    )

    async with LinkExtractionEngine(settings) as link_engine:
        links = await link_engine.run("https://www.example.com/")

    async with ScraperEngine(settings) as scraper_engine:
        results = await scraper_engine.run(links)

    with open("output.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=4)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
```

For a large production crawl, add `include_link_patterns` to keep discovery focused
and use a proxy or proxy pool when the target site requires it.

### GenAI Extraction With A Schema

Use GenAI extraction when you need a strongly typed response shape instead of plain
content. This requires installing the GenAI dependencies:

```bash
pip install "onecrawler[genai]"
```

```python
import asyncio
from typing import Optional
from pydantic import BaseModel
from onecrawler import CrawlerSettings, GenerativeAISettings, ScraperEngine


class ArticleSummary(BaseModel):
    title: str
    author: Optional[str] = None
    published_at: Optional[str] = None
    summary: str
    topics: list[str]


async def main():
    settings = CrawlerSettings(
        scraping_strategy="genai",
        scraping_output_format="json",
        genai=GenerativeAISettings(
            provider="openai",
            model_name="gpt-4o-mini",
            api_key="YOUR_API_KEY",
            output_schema=ArticleSummary,
        ),
        concurrency=2,
        request_timeout=30,
    )

    async with ScraperEngine(settings) as scraper:
        result = await scraper.run("https://example.com/articles/story")

    # Convert Pydantic model to dict for JSON serialization
    print(result.model_dump() if hasattr(result, 'model_dump') else result)


if __name__ == "__main__":
    asyncio.run(main())
```

#### Supported Providers

- **OpenAI**: Requires `api_key`, supports GPT models
- **Google**: Requires `api_key`, supports Gemini models  
- **Ollama**: No API key needed, requires `base_url`, supports local models

#### Ollama Example

```python
settings = CrawlerSettings(
    scraping_strategy="genai",
    genai=GenerativeAISettings(
        provider="ollama",
        model_name="llama3:8b",
        base_url="http://localhost:11434/",  # Your Ollama instance
        output_schema=ArticleSummary,
    ),
)
```

### Proxy Support

Attach one proxy or a rotating proxy pool directly to `CrawlerSettings`.

```python
from onecrawler import CrawlerSettings, ProxySettings


settings = CrawlerSettings(
    proxies=[
        ProxySettings(server="http://proxy-1.example:8080"),
        ProxySettings(
            server="http://proxy-2.example:8080",
            username="user",
            password="pass",
        ),
    ],
    proxy_rotation_method="round_robin",
)
```

Use `proxy=ProxySettings(...)` for one proxy, or `proxies=[...]` for rotation.

---

## Few Tips

- Prefer `UniversalSiteMap` before browser crawling.
- Always set `link_extraction_limit` for broad jobs.
- Use `include_link_patterns` to keep discovery focused.
- Start with moderate `concurrency`, then increase gradually.
- Use heuristic scraping for bulk content extraction.
- Use GenAI extraction for schema-shaped output, summaries, classification, or field
  normalization.
- Split discovery and scraping into separate steps for easier retries.

---

## License

Released under the [MIT License](LICENSE). See `LICENSE` for full terms.
