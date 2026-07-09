---
title: API reference
---

# API Reference

This page summarizes the public objects exported from `onecrawler`. The guide pages
explain when and why to use them; this page is for quick lookup.

!!! note "Public imports"
    User-facing code should prefer `from onecrawler import ...`. Internal classes
    such as runtime helpers should be imported from their concrete modules only when
    you are extending OneCrawler itself.

```python
from onecrawler import (
    BrowserSettings,
    Settings,
    LinkExtractor,
    Crawler,
    Scraper,
    SiteMap,
    UniversalSiteMap,
)

from onecrawler.settings import GenerativeAISettings, HumanBehaviorSettings, ProxySettings

# Filters (import from subpackage)
from onecrawler.filters import (
    by_date,
    by_extension,
    by_files,
    by_keywords,
    by_cosine_similarity,
)
from onecrawler.filters.chain import AND, OR, NOT
```

## Settings

Central settings for sitemap discovery, link extraction, and scraping.

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
| `proxy_rotation_method` | `round_robin` or `random` |
| `browser_settings` | Playwright launch and context settings |
| `genai` | GenAI provider, model, key, and optional schema |

```python
settings = Settings(
    link_extraction_limit=200,
    include_link_patterns=["/news/*"],
    concurrency=8,
)
```

## UniversalSiteMap

High-level sitemap resolver. It checks `robots.txt`, common sitemap paths, nested
sitemap indexes, compressed XML, feeds, and optional HTML fallback.

```python
sitemap = UniversalSiteMap(settings)
urls = await sitemap.run("https://example.com")
```

Returns a list of URL strings.

Use this before browser crawling whenever possible.

!!! tip "Sitemaps are the cheapest discovery path"
    `UniversalSiteMap` avoids opening browser pages for discovery. Use it first for
    public sites, then fall back to browser extraction only when coverage is missing.

## SiteMap

Lower-level sitemap parser that fetches and parses a direct sitemap URL. Most users
should prefer `UniversalSiteMap`, which includes discovery and fallback behavior.

```python
sitemap = SiteMap(settings)
urls = await sitemap.run("https://example.com/sitemap.xml")
```

## SitemapStats

Statistics object used by sitemap parsing. It tracks discovered URL count, parsed
sitemap count, error count, elapsed time, and URL rate.

## LinkExtractor

Async browser engine for extracting links from a starting URL.

```python
async with LinkExtractor(settings) as engine:
    links = await engine.run("https://example.com/docs")
```

Returns a list of URL strings. The engine owns its browser lifecycle inside the async
context manager.

!!! warning "Scope browser crawling"
    Use `link_extraction_limit` and `include_link_patterns` with browser crawling,
    especially when `link_extraction_strategy="deep"`.

## Scraper

Async scraping engine for one URL or a list of URLs.

```python
async with Scraper(settings) as scraper:
    item = await scraper.run("https://example.com/story")

async with Scraper(settings) as scraper:
    items = await scraper.run([
        "https://example.com/story-1",
        "https://example.com/story-2",
    ])
```

For a single URL, returns one result or `None`. For a list, returns a list of
successful results.

!!! note "List results omit failures"
    When scraping a list, failed or empty extractions are filtered out. Keep your
    original URL list if you need to reconcile successes and failures.

## GenerativeAISettings

Settings for model-assisted extraction. Required when `scraping_strategy="genai"`.

```python
settings = GenerativeAISettings(
    provider="openai",  # Options: "openai", "google", "ollama"
    model_name="gpt-4o-mini",
    api_key="YOUR_API_KEY",  # Required for OpenAI/Google, optional for Ollama
    output_schema=MyPydanticModel,  # Pydantic model for structured output
    base_url=None,  # Optional: custom endpoint (e.g., Ollama instance)
    provider_kwargs=None,  # Optional: provider-specific keyword arguments
)
```

Fields:

| Field | Type | Required | Purpose |
| --- | --- | --- | --- |
| `provider` | `str` | Yes | Model provider: `"openai"`, `"google"`, or `"ollama"` |
| `model_name` | `str` | Yes | Model identifier (e.g., `"gpt-4o-mini"`, `"llama3:8b"`) |
| `api_key` | `str` | Conditional | API key for OpenAI/Google, optional for Ollama |
| `output_schema` | `BaseModel` | Conditional | Pydantic model for structured output |
| `base_url` | `str` | Optional | Custom endpoint URL (required for Ollama) |
| `timeout` | `float` | Optional | Per-provider request timeout override in seconds (provider default when unset) |
| `provider_kwargs` | `dict[str, Any]` | No | Provider-specific keyword arguments |

### Provider-Specific Requirements

#### OpenAI
- `api_key` required only for the default `api.openai.com` endpoint
- Supports GPT models (gpt-3.5-turbo, gpt-4, gpt-4o, etc.)
- Set `base_url` to target any OpenAI-compatible server (llama.cpp, vLLM, LM Studio, …); `api_key` is optional for those keyless endpoints

#### Google
- `api_key` required
- Supports Gemini models (gemini-pro, gemini-1.5-pro, etc.)
- No `base_url` needed (uses default Google endpoint)

#### Ollama
- `base_url` required (e.g., `"http://localhost:11434/"`)
- `api_key` optional
- Supports local models (llama3, mistral, codellama, etc.)
- Must have Ollama server running with the specified model

!!! warning "Model names change over time"
    Check your provider's current model list before publishing examples. Keep model
    identifiers configurable in production.

## BrowserSettings

Top-level browser settings. It contains launch, context, runtime, and proxy
settings.

```python
settings = Settings(
    browser_settings=BrowserSettings(
        viewport={"width": 1366, "height": 768}
    )
)
```

Use browser settings for custom viewport, user agent, proxy, locale, timezone,
storage state, HTTPS behavior, and Playwright runtime timeouts.

## ProxySettings

Proxy settings for browser and sitemap workflows.

```python
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

Use `proxy=ProxySettings(...)` for one proxy. Use `proxies=[...]` for a rotating
pool. Supported rotation strategies are `round_robin` and `random`.

## HumanBehaviorSettings

Delay, scroll, and mouse movement settings for optional browser behavior simulation.

```python
settings = Settings(
    enable_human_behaviors=True,
    human_behavior_settings=HumanBehaviorSettings(max_scrolls=20),
)
```

This affects deep browser link extraction. It is useful for lazy-loaded links but
reduces throughput.

!!! tip "Use only where needed"
    Human behavior simulation is helpful for lazy-loaded pages, but it should not be
    a default for every crawl.

## Crawler

A comprehensive web crawling Crawler that orchestrates browser automation,
link extraction, and content scraping in a single unified workflow.

!!! warning "Proxy configuration is required for production"
    `Crawler` performs browser discovery and content extraction together. Use
    explicit proxy settings and conservative concurrency for production runs.

```python
# Basic usage
settings = Settings(
    link_extraction_limit=100,
    concurrency=5,
    proxies=[ProxySettings(server="http://proxy.example.com:8080")]
)

async with Crawler(settings) as engine:
    results = await engine.run("https://example.com")
```

Returns a list of content dictionaries with extracted data from discovered pages.

### Key Features

- **Orchestrated Workflow:** Combines link discovery, browser automation, and content extraction
- **Human Behavior Simulation:** Optional realistic browsing patterns
- **Proxy Support:** Built-in proxy rotation for production crawling
- **Concurrent Processing:** Configurable worker pool for efficient crawling

### Constructor Parameters

| Parameter | Type | Required | Default | Purpose |
| --- | --- | --- | --- | --- |
| `settings` | `Settings` | Yes | - | Configuration for all crawling components |

### Proxy Configuration

**Required for production use:**

```python
settings = Settings(
    proxies=[
        ProxySettings(server="http://proxy1.example.com:8080"),
        ProxySettings(server="http://proxy2.example.com:8080"),
    ],
    proxy_rotation_method="round_robin",
)
```

Without proper proxy configuration, your crawler may be blocked by target websites.

### Usage Patterns

**Simple crawling:**
```python
async with Crawler(settings) as engine:
    content = await engine.run("https://example.com")
```

**Manual lifecycle:**
```python
engine = Crawler(settings)
await engine.start()
try:
    content = await engine.run("https://example.com")
finally:
    await engine.close()
```

**With content filters:**
```python
from onecrawler.filters import by_date, by_keywords
from onecrawler.filters.chain import AND

filter_fn = AND(
    by_date(start="2024-01-01"),
    by_keywords(["python"]),
)

async with Crawler(settings) as engine:
    results = await engine.run("https://example.com", filters=filter_fn)
```

## Filters

Post-extraction content filters that can be passed to `Crawler.run()` and
`Crawler.stream()`. Filters are composable using `AND`, `OR`, and `NOT`.

### Individual Filters

```python
from onecrawler.filters import (
    by_date,
    by_extension,
    by_files,
    by_keywords,
    by_cosine_similarity,
)
```

| Filter | Signature | Purpose |
| --- | --- | --- |
| `by_date` | `by_date(start=None, end=None)` | Keep items within a `YYYY-MM-DD` range |
| `by_keywords` | `by_keywords(keywords)` | Keep items whose text contains any keyword |
| `by_files` | `by_files(types)` | Keep items by logical file type: `pdf`, `image`, `docx`, `text` |
| `by_extension` | `by_extension(extensions)` | Keep items by URL file extension |
| `by_cosine_similarity` | `by_cosine_similarity(query, threshold=0.25)` | Keep items semantically similar to a query |

Each filter function returns a `Callable[[dict], bool]` that accepts a content
dictionary and returns `True` to keep or `False` to discard.

### FilterChain Operators

```python
from onecrawler.filters.chain import AND, OR, NOT
```

| Operator | Purpose |
| --- | --- |
| `AND(*filters)` | Keep items that pass **all** filters |
| `OR(*filters)` | Keep items that pass **any** filter |
| `NOT(filter)` | Invert a single filter |

```python
from onecrawler.filters import by_date, by_keywords, by_files
from onecrawler.filters.chain import AND, NOT

f = AND(
    by_date(start="2024-01-01", end="2024-12-31"),
    by_keywords(["python", "async"]),
    NOT(by_files(["pdf"])),
)
```

!!! tip "Filters are post-extraction"
    Filters evaluate content after extraction. They work with both heuristic and
    GenAI scraping strategies.
