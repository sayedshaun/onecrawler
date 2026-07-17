<div align="center">

<img src="https://raw.githubusercontent.com/sayedshaun/onecrawler/main/docs/static/onecrawl_logo.svg" alt="Onecrawler" width="200"/>

# Onecrawler

**An async Python crawling framework for discovering URLs, extracting links, and scraping structured content.**

[![CI](https://github.com/sayedshaun/onecrawler/actions/workflows/ci.yml/badge.svg)](https://github.com/sayedshaun/onecrawler/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10--3.14-blue.svg)](https://www.python.org/downloads/)
[![PyPI](https://img.shields.io/badge/pypi-onecrawler-2ea44f.svg)](https://pypi.org/project/onecrawler/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Imports: isort](https://img.shields.io/badge/imports-isort-1674b1.svg)](https://pycqa.github.io/isort/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

[Installation](#installation) · [Quick Start](#quick-start) · [CLI](#command-line-interface) · [Documentation](https://sayedshaun.github.io/onecrawler/)

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
async with LinkExtractor(settings) as link_engine:
    links = await link_engine.run("https://example.com")

async with Scraper(settings) as scraper_engine:
    records = await scraper_engine.run(links)  # [{"url": ..., "result": ...}, ...]
```

---

## Features

| Capability | Details |
| --- | --- |
| **Sitemap discovery** | Resolves `robots.txt`, common sitemap paths, nested indexes, `.xml.gz`, feeds, and HTML fallback |
| **Browser link extraction** | Shallow and deep Playwright-backed discovery for JavaScript-rendered or sitemap-poor sites |
| **URL filtering** | Wildcard path filters with `include_link_patterns` |
| **Content filtering** | Composable post-extraction filters by date, keywords, file type, and cosine similarity with `AND`/`OR`/`NOT` logic |
| **Async performance** | Tunable concurrency, retries, timeouts, and crawl limits |
| **Content extraction** | Heuristic extraction with `trafilatura` for fast article-like content |
| **Markdown conversion** | Whole-page HTML-to-Markdown fallback for pages heuristic extraction can't handle (non-article, e-commerce, dashboards) |
| **GenAI extraction** | Optional model-assisted extraction for strongly typed Pydantic outputs |
| **Output formats** | `markdown`, `json`, `xml`, `xmltei` |
| **Proxy support** | Single proxy or rotating proxy pools for browser and sitemap workflows |
| **Browser controls** | Viewport, user agent, locale, timezone, storage state, and runtime settings |

---

## When To Use What

| Need | Use | Why |
| --- | --- | --- |
| Fast URL discovery from a public site | `SiteMap` | Simplest, fastest, and least expensive way to collect URLs |
| Links from one listing page | Shallow `LinkExtractor` | Reads direct same-site links from the page |
| Recursive discovery through navigation | Deep `LinkExtractor` | Follows internal links until your configured limit |
| Bulk article or page text extraction | Heuristic `Scraper` | Deterministic and avoids model cost |
| Non-article pages (product, docs, dashboards) | `markdownify` `Scraper` | Never returns empty; heuristic extraction is article-biased |
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

> [!NOTE]
> GenAI extraction works out of the box — no extra install is needed. It only requires an API key from your chosen provider (OpenAI, Google) or a running Ollama instance. See [GenAI Extraction](#genai-extraction-with-a-schema) for details.

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
docker pull ghcr.io/sayedshaun/onecrawler:latest
```
> [!TIP]
You can rename it for convenience
```bash
docker tag ghcr.io/sayedshaun/onecrawler:latest onecrawler
```

### Run a Script with Docker
```bash
docker run -it --rm -v $(pwd):/app onecrawler python your_script.py
```
> [!NOTE]
> The script must be located at the root of the mounted volume.

### Run the Built-in CLI with Docker
```bash
docker run --rm onecrawler python -m onecrawler crawl https://example.com --limit 20
```

---

## Command-Line Interface

For a quick one-off crawl without writing a script:

```bash
python -m onecrawler crawl https://example.com --limit 20 --concurrency 5
```

Each extracted page is printed to stdout as a JSON line. Run `python -m onecrawler crawl --help` for the full flag list (`--strategy`, `--format`, `--include`, `--exclude`). The CLI covers heuristic-strategy crawling only — proxies, GenAI extraction, and human-behavior simulation need the Python API below.

---

## Quick Start
```python
from onecrawler import Settings, Crawler
from onecrawler.utils import writter

async def main():
    settings = Settings(link_extraction_limit=100, concurrency=5)

    async with Crawler(settings) as engine:
        results = await engine.run("https://www.prothomalo.com/")

    writter.dump_json(results, "output.json")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```


## Separate Workflow

```python
from onecrawler import HumanBehaviorSettings, LinkExtractor, Scraper, Settings
from onecrawler.utils import writter

async def main():
    settings = Settings(
        link_extraction_strategy="deep",
        link_extraction_limit=10,
        concurrency=7,
        scraping_strategy="heuristic",
        scraping_output_format="json",
        human_behavior_settings=HumanBehaviorSettings(),
    )

    async with LinkExtractor(settings) as link_engine:
        links = await link_engine.run("https://www.example.com/")

    async with Scraper(settings) as scraper_engine:
        results = await scraper_engine.run(links)  # [{"url": ..., "result": ...}, ...]

    writter.dump_json(results, "output.json")


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
from onecrawler import Settings, LinkExtractor


async def main():
    settings = Settings(
        link_extraction_strategy="deep",
        link_extraction_limit=250,
        include_link_patterns=["/news/*"],
        concurrency=5,
    )

    async with LinkExtractor(settings) as engine:
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

## Content Filtering

Filter crawled results by date, keywords, file type, or semantic similarity. Filters are passed to `Crawler.run()` or `Crawler.stream()` and applied after content extraction.

```python
import asyncio
from onecrawler import Crawler, Settings
from onecrawler.filters import AND, by_date, by_keywords


async def main():
    settings = Settings(
        link_extraction_limit=50,
        concurrency=5,
    )

    # Keep only pages from 2025 that mention "python" or "async"
    content_filter = AND(
        by_date(start="2025-01-01", end="2025-12-31"),
        by_keywords(["python", "async"]),
    )

    async with Crawler(settings) as engine:
        results = await engine.run(
            "https://example.com/blog",
            filters=content_filter,
        )

    print(f"Matched {len(results)} pages")


if __name__ == "__main__":
    asyncio.run(main())
```

### Available Filters

| Filter | Import | Purpose |
| --- | --- | --- |
| `by_date(start, end)` | `onecrawler.filters` | Keep items within a `YYYY-MM-DD` date range |
| `by_keywords(keywords)` | `onecrawler.filters` | Keep items whose text contains any keyword |
| `by_files(types)` | `onecrawler.filters` | Keep items by logical file type (`pdf`, `image`, `docx`, `text`) |
| `by_extension(extensions)` | `onecrawler.filters` | Keep items by URL file extension (`.pdf`, `.jpg`) |
| `by_cosine_similarity(query, threshold)` | `onecrawler.filters` | Keep items whose text is semantically similar to a query |

### Composing Filters

Use `AND`, `OR`, and `NOT` from `onecrawler.filters` to combine filters:

```python
from onecrawler.filters import AND, OR, NOT, by_date, by_keywords, by_files

# Pages from 2025 that mention "python" but are not PDFs
f = AND(
    by_date(start="2025-01-01"),
    by_keywords(["python"]),
    NOT(by_files(["pdf"])),
)

# Pages that mention "AI" or are from 2025
f = OR(
    by_keywords(["AI"]),
    by_date(start="2025-01-01", end="2025-12-31"),
)
```

### Streaming With Filters

Filters work with `Crawler.stream()` for real-time filtered output:

```python
async with Crawler(settings) as engine:
    async for item in engine.stream(
        "https://example.com/news",
        filters=by_cosine_similarity("climate policy", threshold=0.3),
    ):
        print(item["title"])
```

> [!TIP]
> Filters run after content extraction, so they work with any scraping strategy. Use `by_cosine_similarity` for topic-focused crawls and `by_date` to keep results fresh.

> [!NOTE]
> `by_date` reads the `date` or `filedate` field from extracted content. Pages without a parseable date are excluded when a date filter is active.

---

## GenAI Extraction With a Schema

Use GenAI extraction when you need a strongly typed response shape instead of plain content.

```python
import asyncio
from typing import Optional
from pydantic import BaseModel
from onecrawler import Settings, LLMSettings, Scraper


class ArticleSummary(BaseModel):
    title: str
    author: Optional[str] = None
    published_at: Optional[str] = None
    summary: str
    topics: list[str]


async def main():
    settings = Settings(
        scraping_strategy="genai",
        scraping_output_format="json",
        genai=LLMSettings(
            provider="openai",
            model_name="gpt-4o-mini",
            api_key="YOUR_API_KEY",
            output_schema=ArticleSummary,
        ),
        concurrency=2,
        request_timeout=30,
    )

    async with Scraper(settings) as scraper:
        item = await scraper.run("https://example.com/articles/story")

    result = item["result"]
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
| **OpenAI** | `api_key` (optional with a custom `base_url`) | GPT-4o, GPT-4o-mini, or any OpenAI-compatible server |
| **Google** | `api_key` | Gemini models |
| **Ollama** | `base_url` (no key needed) | Any locally hosted model |

> [!NOTE]
> Set `base_url` on the `openai` provider to target any OpenAI-compatible server (llama.cpp, vLLM, LM Studio, LocalAI, …). `api_key` is optional for those keyless endpoints — it is only required for the real `api.openai.com` default.

### Ollama Example

```python
settings = Settings(
    scraping_strategy="genai",
    genai=LLMSettings(
        provider="ollama",
        model_name="llama3:8b",
        base_url="http://localhost:11434/",
        output_schema=ArticleSummary,
    ),
)
```

> [!NOTE]
> Ollama requires a running local instance. Install it from [ollama.com](https://ollama.com) and pull your model (`ollama pull llama3:8b`) before running.

> [!WARNING]
> For "thinking" models (qwen3, deepseek-r1, etc.), keep `LLMSettings(think=False)` (the default). Ollama returns an empty response for schema-constrained structured output when thinking is enabled. Set `think=True` only for free-form, non-schema use.

---

## Proxy Support

Attach one proxy or a rotating proxy pool directly to `Settings`.

```python
from onecrawler import Settings, ProxySettings


settings = Settings(
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

Use `proxies=[ProxySettings(...)]` for a single proxy (a one-element list), or add more entries with `proxy_rotation_method` for a pool.

> [!TIP]
> `round_robin` rotation distributes requests evenly across your proxy pool. For rate-limited targets, pair this with a modest `concurrency` value and a `retry_delay` to avoid triggering bans.

---

## Production Tips

> [!IMPORTANT]
> Split URL discovery and scraping into separate pipeline steps. Collecting all URLs first gives you a checkpoint to resume from if scraping fails partway through — without re-running discovery.

> [!TIP]
> Start with `SiteMap` before reaching for browser extraction. Sitemap-based discovery is faster, cheaper, and more complete on well-maintained sites. Fall back to `LinkExtractor` only when sitemaps are missing or stale.

> [!TIP]
> Use heuristic scraping (`scraping_strategy="heuristic"`) for bulk content extraction. Reserve GenAI extraction for cases where you genuinely need structured, schema-shaped output — it adds latency and cost at scale.

> [!TIP]
> If heuristic extraction returns `None` or very little on non-article pages (product listings, dashboards, docs), switch to `scraping_strategy="markdownify"`. It never returns empty for a rendered page, at the cost of including page chrome (nav, footers) in the output.

> [!CAUTION]
> Respect `robots.txt` and a site's terms of service before crawling. Onecrawler does not enforce crawl policies automatically — you are responsible for staying within allowed access patterns.

---

## License

Released under the [MIT License](LICENSE). See `LICENSE` for full terms.
