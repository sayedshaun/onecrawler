# Onecrawler

Onecrawler is a feature-rich Python web crawling toolkit for extracting links and scraping page content using heuristic or Generative AI strategies.

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
        json.dump(data, f, indent=2, ensure_ascii=False)

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