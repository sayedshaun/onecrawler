<div align="center">

<img src="https://raw.githubusercontent.com/sayedshaun/onecrawler/refs/heads/main/docs/static/onecrawl_logo.png" alt="Onecrawler" width="180"/>

# Onecrawler

**An async Python crawling framework for discovering URLs, extracting links, and scraping structured content.**

[![CI](https://github.com/sayedshaun/onecrawler/actions/workflows/ci.yml/badge.svg)](https://github.com/sayedshaun/onecrawler/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![PyPI](https://img.shields.io/badge/pypi-onecrawler-2ea44f.svg)](https://pypi.org/project/onecrawler/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Imports: isort](https://img.shields.io/badge/imports-isort-1674b1.svg)](https://pycqa.github.io/isort/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

[Installation](#installation) · [Quick Start](#quick-start) · [Documentation](https://sayedshaun.github.io/onecrawler/)

</div>

---

## Overview

Onecrawler helps you build maintainable crawling and extraction workflows without turning every project into a custom scraping script. It provides a shared configuration model, async execution, sitemap discovery, browser-backed link extraction, heuristic content extraction, and optional GenAI extraction for typed outputs.

**Recommended workflow:**

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
| **Content extraction** | Heuristic extraction with `trafilatura` for fast article-like content |
| **GenAI extraction** | Optional model-assisted extraction for strongly typed Pydantic outputs |
| **Output formats** | `markdown`, `json`, `csv`, `html`, `python`, `txt`, `xml`, `xmltei` |
| **Proxy support** | Single proxy or rotating proxy pools for browser and sitemap workflows |
| **Browser controls** | Viewport, user agent, locale, timezone, storage state, and runtime settings |

---

## When To Use What

| Need | Use | Why |
| --- | --- | --- |
| Fast URL discovery from a public site | `UniversalSiteMap` | Simplest, fastest, and least expensive way to collect URLs |
| Links from one listing page | Shallow `LinkExtractionEngine` | Reads direct same-site links from the page |
| Recursive discovery through navigation | Deep `LinkExtractionEngine` | Follows internal links until your configured limit |
| Bulk article or page text extraction | Heuristic `ScraperEngine` | Deterministic and avoids model cost |
| Typed fields or semantic normalization | GenAI extraction | Produces schema-shaped output for downstream systems |

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

> [!NOTE]
> GenAI extraction requires an API key from your chosen provider (OpenAI, Google) or a running Ollama instance. See [GenAI Extraction](#genai-extraction-with-a-schema) for details.

For local development:

```bash
git clone https://github.com/sayedshaun/onecrawler.git
cd onecrawler
python -m pip install -e ".[dev]"
python -m playwright install chromium
```

---

## Docker Support

OneCrawler provides an optimized Docker image that includes all necessary browser dependencies. This is the recommended way to run the framework in production or CI/CD environments.

### Build the Image
```bash
docker pull sayedshaun/onecrawler:latest
```

### Run a Script with Docker
```bash
docker run -it --rm -v $(pwd):/app onecrawler python your_script.py
```
> [!NOTE]
> The script must be located at the root of the mounted volume.

---

## Quick Start

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

> [!TIP]
> Always set `link_extraction_limit` when crawling broad sites. Without it, discovery can run indefinitely on large domains.

---

## Browser Link Extraction

Use browser extraction when sitemaps are incomplete, unavailable, or unable to expose JavaScript-rendered links.

```python
import asyncio
from onecrawler import CrawlerSettings, LinkExtractionEngine


async def main():
    settings = CrawlerSettings(
        link_extraction_strategy="deep",
        link_extraction_limit=250,
        include_link_patterns=["/news/*"],
        concurrency=5,
    )

    async with LinkExtractionEngine(settings) as engine:
        links = await engine.run("https://example.com/news")

    print(f"Collected {len(links)} links")


if __name__ == "__main__":
    asyncio.run(main())
```

> [!TIP]
> Use `include_link_patterns` to keep discovery focused on relevant paths. For example, `["/blog/*", "/docs/*"]` prevents the crawler from wandering into auth pages, admin routes, or unrelated sections.

> [!NOTE]
> Deep extraction follows internal links recursively. Use `shallow` strategy when you only need links visible on a single listing page — it's significantly faster.

---

## GenAI Extraction With a Schema

Use GenAI extraction when you need a strongly typed response shape instead of plain content.

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

    print(result.model_dump() if hasattr(result, "model_dump") else result)


if __name__ == "__main__":
    asyncio.run(main())
```

> [!TIP]
> Keep `concurrency` low (2–4) for GenAI extraction. Each page triggers a model call; high concurrency can exhaust rate limits quickly and inflate costs.

> [!WARNING]
> Never hardcode your API key in source files. Use environment variables or a secrets manager instead:
> ```python
> import os
> api_key=os.environ["OPENAI_API_KEY"]
> ```

### Supported Providers

| Provider | Requires | Models |
| --- | --- | --- |
| **OpenAI** | `api_key` | GPT-4o, GPT-4o-mini, etc. |
| **Google** | `api_key` | Gemini models |
| **Ollama** | `base_url` (no key needed) | Any locally hosted model |

### Ollama Example

```python
settings = CrawlerSettings(
    scraping_strategy="genai",
    genai=GenerativeAISettings(
        provider="ollama",
        model_name="llama3:8b",
        base_url="http://localhost:11434/",
        output_schema=ArticleSummary,
    ),
)
```

> [!NOTE]
> Ollama requires a running local instance. Install it from [ollama.com](https://ollama.com) and pull your model (`ollama pull llama3:8b`) before running.

---

## Proxy Support

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
    proxy_rotation="round_robin",
)
```

Use `proxy=ProxySettings(...)` for a single proxy, or `proxies=[...]` with `proxy_rotation` for a pool.

> [!TIP]
> `round_robin` rotation distributes requests evenly across your proxy pool. For rate-limited targets, pair this with a modest `concurrency` value and a `request_delay` to avoid triggering bans.

---

## Production Tips

> [!IMPORTANT]
> Split URL discovery and scraping into separate pipeline steps. Collecting all URLs first gives you a checkpoint to resume from if scraping fails partway through — without re-running discovery.

> [!TIP]
> Start with `UniversalSiteMap` before reaching for browser extraction. Sitemap-based discovery is faster, cheaper, and more complete on well-maintained sites. Fall back to `LinkExtractionEngine` only when sitemaps are missing or stale.

> [!TIP]
> Use heuristic scraping (`scraping_strategy="heuristic"`) for bulk content extraction. Reserve GenAI extraction for cases where you genuinely need structured, schema-shaped output — it adds latency and cost at scale.

> [!CAUTION]
> Respect `robots.txt` and a site's terms of service before crawling. Onecrawler does not enforce crawl policies automatically — you are responsible for staying within allowed access patterns.

---

## License

Released under the [MIT License](LICENSE). See `LICENSE` for full terms.
