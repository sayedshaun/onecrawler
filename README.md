<div align="center">

<img src="https://raw.githubusercontent.com/sayedshaun/onecrawler/refs/heads/main/docs/static/onecrawl_logo.png" alt="Onecrawler" width="200"/>

# Onecrawler

**An async Python toolkit for sitemap discovery, browser crawling, and structured content extraction.**

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

Onecrawler helps you build maintainable crawling and extraction workflows without
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
sitemap = UniversalSiteMap(config)
urls = await sitemap.run("https://example.com")

async with ScraperEngine(config) as scraper:
    records = await scraper.run(urls)
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
| **Browser controls** | Viewport, user agent, locale, timezone, proxy, storage state, and runtime settings |

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

This example uses the production-friendly path: discover URLs from the sitemap, then
scrape them.

```python
import asyncio
import json

from onecrawler import CrawlerSettings, ScraperEngine, UniversalSiteMap


async def main():
    config = CrawlerSettings(
        link_extraction_limit=100,
        include_link_patterns=["/articles/*"],
        scraping_strategy="heuristic",
        scraping_output_format="json",
        concurrency=8,
        request_timeout=15,
        max_retries=3,
    )

    sitemap = UniversalSiteMap(config)
    urls = await sitemap.run("https://example.com")

    async with ScraperEngine(config) as scraper:
        records = await scraper.run(urls)

    with open("articles.json", "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    asyncio.run(main())
```

### Browser Link Extraction

Use browser extraction when sitemaps are incomplete, unavailable, or unable to expose
JavaScript-rendered links.

```python
import asyncio

from onecrawler import CrawlerSettings, LinkExtractionEngine


async def main():
    config = CrawlerSettings(
        link_extraction_strategy="deep",
        link_extraction_limit=250,
        include_link_patterns=["/news/*"],
        concurrency=5,
    )

    async with LinkExtractionEngine(config) as engine:
        links = await engine.run("https://example.com/news")

    print(f"Collected {len(links)} links")


if __name__ == "__main__":
    asyncio.run(main())
```

### GenAI Extraction With A Schema

Use GenAI extraction when you need a strongly typed response shape instead of plain
content.

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
    config = CrawlerSettings(
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

    async with ScraperEngine(config) as scraper:
        result = await scraper.run("https://example.com/articles/story")

    print(result)


if __name__ == "__main__":
    asyncio.run(main())
```

---

## Documentation

The README is the project overview. The full documentation in [`docs/`](docs/index.md)
contains production guidance, caveats, performance notes, and copy-paste examples.

| Topic | Guide |
| --- | --- |
| Install the package | [Installation](docs/installation.md) |
| Run your first crawl | [Quick start](docs/quick-start.md) |
| Tune crawler settings | [Configuration](docs/configuration.md) |
| Discover URLs from sitemaps | [Sitemap discovery](docs/sitemap-discovery.md) |
| Extract and filter links | [Link extraction](docs/link-extraction.md) |
| Scrape page content | [Scraping](docs/scraping.md) |
| Public classes and exports | [API reference](docs/api-reference.md) |
| Common fixes | [Troubleshooting](docs/troubleshooting.md) |
| Contribute locally | [Contributing](docs/contributing.md) |
| Work on the project | [Development](docs/development.md) |

See [Contributing](docs/contributing.md) for how to improve the docs.

---

## Production Tips

- Prefer `UniversalSiteMap` before browser crawling.
- Always set `link_extraction_limit` for broad jobs.
- Use `include_link_patterns` to keep discovery focused.
- Start with moderate `concurrency`, then increase gradually.
- Use heuristic scraping for bulk content extraction.
- Use GenAI extraction for schema-shaped output, summaries, classification, or field
  normalization.
- Split discovery and scraping into separate steps for easier retries.

---

## Development

Install with development dependencies:

```bash
python -m pip install -e ".[dev]"
```

Run tests:

```bash
./test.sh
```

Run formatting checks:

```bash
pre-commit run --all-files
```

Install hooks:

```bash
pre-commit install
```

See [Development](docs/development.md) and [Contributing](docs/contributing.md) for
the full local workflow.

---

## License

Released under the [MIT License](LICENSE). See `LICENSE` for full terms.

---

<div align="center">

Built by [sayedshaun](https://github.com/sayedshaun)

</div>
