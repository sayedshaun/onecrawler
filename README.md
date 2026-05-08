<div align="center">

<img src="https://raw.githubusercontent.com/sayedshaun/onecrawler/refs/heads/main/docs/static/onecrawl_logo.png" alt="Onecrawler" width="200"/>

# Onecrawler

**A production-ready Python toolkit for web crawling, sitemap discovery, and structured content extraction.**

[![CI](https://github.com/sayedshaun/onecrawler/actions/workflows/ci.yml/badge.svg)](https://github.com/sayedshaun/onecrawler/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![PyPI](https://img.shields.io/badge/pypi-onecrawler-2ea44f.svg)](https://pypi.org/project/onecrawler/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Imports: isort](https://img.shields.io/badge/imports-isort-1674b1.svg)](https://pycqa.github.io/isort/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

[Installation](#installation) · [Quick Start](#quick-start) · [Configuration](#configuration) · [Examples](#examples) · [Contributing](#development)

</div>

---

## Overview

Onecrawler is a configurable, async-first web crawling toolkit built for real-world use cases. Rather than a one-off scraping script, it provides a structured, reusable framework with support for deep/shallow link traversal, universal sitemap discovery, browser-backed rendering, and both heuristic and AI-powered content extraction — all with first-class concurrency controls.

```python
async with LinkExtractionEngine(config) as engine:
    links = await engine.run("https://www.bbc.com/sport")

async with ScraperEngine(config) as scraper:
    data = await scraper.run(links)
```

---

## Features

| Capability | Details |
|---|---|
| **Link Extraction** | Deep and shallow crawl modes with configurable depth limits |
| **Sitemap Discovery** | Universal resolver — `robots.txt`, common paths, nested indexes, HTML fallback |
| **URL Filtering** | Wildcard pattern matching to include only relevant paths |
| **Concurrency** | Async engine with tunable worker count, retry logic, and per-request timeouts |
| **Browser Crawling** | Full Playwright integration for JavaScript-rendered pages |
| **Content Extraction** | Heuristic mode via `trafilatura`; optional Generative AI extraction strategy |
| **Output Formats** | `markdown`, `json`, `csv`, `html`, `python`, `txt`, `xml`, `xmltei` |
| **Code Quality** | Pre-commit hooks (Black + isort), GitHub Actions CI across Python 3.10–3.12 |

---

## Requirements

- Python `>= 3.10`
- `pip`
- Playwright browser binaries (only required for browser-backed crawling)

---

## Installation

**From PyPI (recommended):**

```bash
pip install onecrawler
```

**From source:**

```bash
pip install git+https://github.com/sayedshaun/onecrawler.git
```

**For local development:**

```bash
git clone https://github.com/sayedshaun/onecrawler.git
cd onecrawler
python -m pip install -e ".[dev]"
```

---

## Quick Start

The following example crawls up to 5 links from a BBC Sport section and writes the scraped content to a JSON file:

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

---

## Examples

### Sitemap Discovery

Use `UniversalSiteMap` to collect URLs from a site's sitemap infrastructure before scraping. Supports `robots.txt` resolution, nested sitemap indexes, and HTML fallback:

```python
import asyncio

from onecrawler import CrawlerSettings, UniversalSiteMap


async def main():
    config = CrawlerSettings(
        link_extraction_limit=100,
        include_link_patterns=["/news/*"],
    )

    sitemap = UniversalSiteMap(config)
    urls = await sitemap.run("https://example.com")
    print(urls)


if __name__ == "__main__":
    asyncio.run(main())
```

### Filtered Crawl

Restrict crawling to specific URL path patterns using wildcard expressions:

```python
from onecrawler import CrawlerSettings

config = CrawlerSettings(
    link_extraction_strategy="deep",
    link_extraction_limit=200,
    include_link_patterns=["/sports/*", "/news/*"],
    concurrency=10,
)
```

### High-Volume Scraping with Retries

For resilient production crawls with timeout and retry controls:

```python
from onecrawler import CrawlerSettings

config = CrawlerSettings(
    link_extraction_strategy="deep",
    link_extraction_limit=500,
    scraping_strategy="heuristic",
    scraping_output_format="markdown",
    concurrency=20,
    max_retries=3,
    request_timeout=10,
)
```

---

## Configuration

`CrawlerSettings` is the central configuration object. All fields are optional with sensible defaults.

| Parameter | Type | Description |
|---|---|---|
| `link_extraction_strategy` | `str` | `"deep"` or `"shallow"` traversal mode |
| `link_extraction_limit` | `int` | Maximum number of links to extract |
| `include_link_patterns` | `list[str]` | Wildcard URL path filters (e.g. `["/news/*"]`) |
| `scraping_strategy` | `str` | `"heuristic"` (trafilatura) or AI-based strategy |
| `scraping_output_format` | `str` | One of `markdown`, `json`, `csv`, `html`, `txt`, `xml`, `xmltei`, `python` |
| `concurrency` | `int` | Number of concurrent async workers |
| `max_retries` | `int` | Retry attempts per failed request |
| `request_timeout` | `int` | Per-request timeout in seconds |

**Full example:**

```python
from onecrawler import CrawlerSettings

config = CrawlerSettings(
    link_extraction_strategy="deep",
    link_extraction_limit=50,
    include_link_patterns=["/sports/*", "/news/*"],
    scraping_strategy="heuristic",
    scraping_output_format="json",
    concurrency=10,
    max_retries=2,
    request_timeout=3,
)
```

---

## Project Structure

```
onecrawler/
├── config/          # Runtime and crawler configuration
├── crawler/         # Link extraction and scraping engines
├── map/             # Sitemap discovery and URL parsing
└── utils/           # Shared utilities

tests/               # Unit tests
.github/             # CI workflow configuration
```

---

## Development

Install with development dependencies:

```bash
python -m pip install -e ".[dev]"
```

Run the test suite:

```bash
./test.sh
```

Run all formatting checks:

```bash
pre-commit run --all-files
```

Install the pre-commit hook (runs Black and isort automatically before each commit):

```bash
pre-commit install
```

---

## CI

The GitHub Actions pipeline runs on all pushes and pull requests targeting `main`.

**Matrix:** Python `3.10`, `3.11`, `3.12`

**Checks:**
- Package installation with dev dependencies
- Code formatting via `pre-commit` (Black + isort)
- Full test execution via `./test.sh`

---

## License

Released under the [MIT License](LICENSE). See `LICENSE` for full terms.

---

<div align="center">

Made with ♥ by [sayedshaun](https://github.com/sayedshaun)

</div>