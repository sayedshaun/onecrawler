---
title: Installation
---

# Installation

OneCrawler targets Python `3.10` and newer.

## Install From PyPI

```bash
pip install onecrawler
```

## Browser Support

OneCrawler uses Playwright for browser-backed link extraction and browser-backed
scraping. Install browser binaries if you plan to use `LinkExtractor` or any
workflow that needs rendered pages.

```bash
python -m playwright install chromium
```

In Linux containers, you may also need Playwright system dependencies:

```bash
python -m playwright install --with-deps chromium
```

!!! note "Sitemap-only installs do not need a browser"
    If your application only uses `SiteMap` for sitemap discovery, you can skip
    Playwright browser installation until you add browser-backed crawling or
    scraping.

!!! warning "Containers often need system dependencies"
    Browser launch failures in Docker and CI are usually missing system libraries or
    sandbox restrictions. Start with `python -m playwright install --with-deps
    chromium` in those environments.

## GenAI Extraction

GenAI extraction needs no extra install — its dependencies ship with the
default package. It only requires access to a provider: an API key for
OpenAI or Google, or a running Ollama instance.

## Install From Source

```bash
pip install git+https://github.com/sayedshaun/onecrawler.git
```

## Local Development Install

```bash
git clone https://github.com/sayedshaun/onecrawler.git
cd onecrawler
python -m pip install -e ".[dev]"
python -m playwright install chromium
```

## Verify The Install

```python
import onecrawler

print(onecrawler.__version__)
```

For browser workflows, run a small shallow extraction against a site you control or a
stable public page.

## Environment Notes

Use a virtual environment for production jobs so browser binaries, optional GenAI
dependencies, and crawler versions are controlled.

In CI or Docker, cache Playwright browsers if possible. Browser installation is often
the slowest part of a fresh environment.

If you only use `SiteMap`, you do not need to launch a browser. Sitemap
discovery uses HTTP clients and XML parsing, so it is lighter than browser crawling.

!!! tip "Pin versions for repeatable jobs"
    For repeatable crawls, pin OneCrawler and Playwright versions in your deployment
    environment. Browser behavior can change across dependency upgrades.
