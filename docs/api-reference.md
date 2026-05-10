---
title: API reference
---

# API Reference

This page summarizes the public objects exported from `onecrawler`. The guide pages
explain when and why to use them; this page is for quick lookup.

```python
from onecrawler import (
    BrowserSettings,
    ContextSettings,
    CrawlerSettings,
    GenerativeAISettings,
    HumanBehaviorSettings,
    LinkExtractionEngine,
    ProxySettings,
    ScraperEngine,
    SiteMap,
    SitemapStats,
    UniversalSiteMap,
)
```

## CrawlerSettings

Central configuration for sitemap discovery, link extraction, and scraping.

Important fields:

| Field | Purpose |
| --- | --- |
| `link_extraction_strategy` | `deep` or `shallow` browser discovery |
| `link_extraction_limit` | Maximum number of URLs returned |
| `include_link_patterns` | URL path allow-list |
| `scraping_strategy` | `heuristic` or `genai` |
| `scraping_output_format` | Output format for scraper results |
| `concurrency` | Async worker count |
| `request_timeout` | Timeout in seconds |
| `max_retries` | Retry attempts |
| `proxy` | Single package-level proxy |
| `proxies` | Rotating proxy pool |
| `proxy_rotation` | `round_robin` or `random` |
| `browser_settings` | Playwright launch and context settings |
| `genai` | GenAI provider, model, key, and optional schema |

```python
config = CrawlerSettings(
    link_extraction_limit=200,
    include_link_patterns=["/news/*"],
    concurrency=8,
)
```

## UniversalSiteMap

High-level sitemap resolver. It checks `robots.txt`, common sitemap paths, nested
sitemap indexes, compressed XML, feeds, and optional HTML fallback.

```python
sitemap = UniversalSiteMap(config)
urls = await sitemap.run("https://example.com")
```

Returns a list of URL strings.

Use this before browser crawling whenever possible.

## SiteMap

Lower-level sitemap parser that fetches and parses a direct sitemap URL. Most users
should prefer `UniversalSiteMap`, which includes discovery and fallback behavior.

```python
sitemap = SiteMap(config)
urls = await sitemap.run("https://example.com/sitemap.xml")
```

## SitemapStats

Statistics object used by sitemap parsing. It tracks discovered URL count, parsed
sitemap count, error count, elapsed time, and URL rate.

## LinkExtractionEngine

Async browser engine for extracting links from a starting URL.

```python
async with LinkExtractionEngine(config) as engine:
    links = await engine.run("https://example.com/docs")
```

Returns a list of URL strings. The engine owns its browser lifecycle inside the async
context manager.

## ScraperEngine

Async scraping engine for one URL or a list of URLs.

```python
async with ScraperEngine(config) as scraper:
    item = await scraper.run("https://example.com/story")

async with ScraperEngine(config) as scraper:
    items = await scraper.run([
        "https://example.com/story-1",
        "https://example.com/story-2",
    ])
```

For a single URL, returns one result or `None`. For a list, returns a list of
successful results.

## GenerativeAISettings

Configuration for model-assisted extraction.

```python
settings = GenerativeAISettings(
    provider="openai",
    model_name="gpt-4o-mini",
    api_key="YOUR_API_KEY",
    output_schema=MyPydanticModel,
)
```

Fields:

| Field | Purpose |
| --- | --- |
| `provider` | `google`, `openai`, or `ollama` |
| `model_name` | Model identifier |
| `api_key` | Provider API key |
| `output_schema` | Optional Pydantic model for structured output |

## BrowserSettings

Top-level browser configuration. It contains launch, context, runtime, and proxy
settings.

```python
config = CrawlerSettings(
    browser_settings=BrowserSettings(
        context=ContextSettings(viewport={"width": 1366, "height": 768})
    )
)
```

Use browser settings for custom viewport, user agent, proxy, locale, timezone,
storage state, HTTPS behavior, and Playwright runtime timeouts.

## ProxySettings

Proxy configuration for browser and sitemap workflows.

```python
config = CrawlerSettings(
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

Use `proxy=ProxySettings(...)` for one proxy. Use `proxies=[...]` for a rotating
pool. Supported rotation strategies are `round_robin` and `random`.

## HumanBehaviorSettings

Delay, scroll, and mouse movement settings for optional browser behavior simulation.

```python
config = CrawlerSettings(
    enable_human_behaviors=True,
    human_behavior_settings=HumanBehaviorSettings(max_scrolls=20),
)
```

This affects deep browser link extraction. It is useful for lazy-loaded links but
reduces throughput.

## LinkClassifierPipeline

Publicly exported link classifier pipeline used by shallow extraction when
`link_classification=True`. Most users should start with `include_link_patterns`
because path filters are explicit, easy to debug, and deterministic.
