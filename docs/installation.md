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
scraping. Install browser binaries if you plan to use `LinkExtractionEngine` or any
workflow that needs rendered pages.

```bash
python -m playwright install chromium
```

In Linux containers, you may also need Playwright system dependencies:

```bash
python -m playwright install --with-deps chromium
```

!!! note "Sitemap-only installs do not need a browser"
    If your application only uses `UniversalSiteMap` or direct `SiteMap` parsing,
    you can skip Playwright browser installation until you add browser-backed
    crawling or scraping.

!!! warning "Containers often need system dependencies"
    Browser launch failures in Docker and CI are usually missing system libraries or
    sandbox restrictions. Start with `python -m playwright install --with-deps
    chromium` in those environments.

## Optional GenAI Dependencies

Install the GenAI extra when you use model-assisted extraction.

```bash
pip install "onecrawler[genai]"
```

This installs the optional LangChain and LangGraph dependencies used by the GenAI
components.

!!! tip "Install GenAI extras only when needed"
    The default install is enough for sitemap discovery, link extraction, and
    heuristic scraping. Add `onecrawler[genai]` only for model-assisted structured
    extraction.

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

If you only use `UniversalSiteMap`, you do not need to launch a browser. Sitemap
discovery uses HTTP clients and XML parsing, so it is lighter than browser crawling.

!!! tip "Pin versions for scheduled jobs"
    For repeatable crawls, pin OneCrawler and Playwright versions in your deployment
    environment. Browser behavior can change across dependency upgrades.
