[![CI](https://github.com/sayedshaun/onecrawler/actions/workflows/ci.yml/badge.svg)](https://github.com/sayedshaun/onecrawler/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![Package](https://img.shields.io/badge/package-onecrawler-2ea44f.svg)](https://github.com/sayedshaun/onecrawler)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Imports: isort](https://img.shields.io/badge/imports-isort-1674b1.svg)](https://pycqa.github.io/isort/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)


![onecrawl_logo.png](https://raw.githubusercontent.com/sayedshaun/onecrawler/refs/heads/main/docs/static/onecrawl_logo.png)

# Onecrawler

Onecrawler is a feature-rich Python web crawling toolkit for extracting links and scraping page content using heuristic or Generative AI strategies.

## Project Info

- Python: `>=3.10`
- Package manager: `pip`
- Formatting: `black` and `isort`
- Test runner: `./test.sh`
- CI: GitHub Actions on pushes and pull requests to `main`

## Installation

### Standard Installation

```bash
pip install onecrawler
```

### From Source

```bash
git clone https://github.com/sayedshaun/onecrawler.git
cd onecrawler
pip install -e .
```

Or

### From Github

```bash
pip install git+https://github.com/sayedshaun/onecrawler.git
```

## Quick Start

```python
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

    with open("output.json", "w") as f:
        json.dump(data, f, indent=2)

if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
```

## Features

- Deep or shallow link extraction
- Include-only URL filtering with pattern matching
- Optional link classification support
- Concurrent scraping with retry and timeout controls
- Multiple output formats: `markdown`, `json`, `csv`, `html`, `python`, `txt`, `xml`, `xmltei`
- Pluggable scraping strategies: `heuristic` and `genai`
