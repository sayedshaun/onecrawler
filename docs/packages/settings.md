---
title: Settings Configuration
---

# Settings Package

The `onecrawler.settings` package provides comprehensive configuration classes for all crawler components.

!!! tip "Treat settings as the crawl contract"
    Put scope, limits, concurrency, retries, proxy behavior, and output format in
    `Settings`. Explicit settings make crawls easier to review, reproduce,
    and operate.

## Classes

### Settings

Central configuration class that controls all crawler behavior.

```python
from onecrawler import Settings

settings = Settings(
    link_extraction_limit=500,
    include_link_patterns=["/articles/*"],
    concurrency=10,
    scraping_strategy="heuristic"
)
```

#### Core Settings

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `link_extraction_strategy` | `str` | `"deep"` | Browser discovery mode: `"deep"` or `"shallow"` |
| `link_extraction_limit` | `int` | `50` | Maximum number of URLs to collect |
| `include_link_patterns` | `List[str]` | `None` | URL path patterns to include |
| `exclude_link_patterns` | `List[str]` | `None` | URL path patterns to exclude |
| `scraping_strategy` | `str` | `"heuristic"` | Extraction strategy: `"heuristic"`, `"genai"`, or `"markdownify"` |
| `scraping_output_format` | `str` | `"json"` | Output format for scraped content (ignored by `"markdownify"`) |
| `exclude_selectors` | `List[str]` | `None` | CSS selectors to strip before HTML-to-Markdown conversion; used by `"markdownify"` and `"genai"` |
| `concurrency` | `int` | `10` | Number of async workers |
| `request_timeout` | `int` | `10` | Per-request timeout in seconds |
| `max_retries` | `int` | `2` | Retry attempts for failed requests |
| `retry_delay` | `int` | `1` | Base delay between retries |

!!! warning "Do not run broad crawls without limits"
    `link_extraction_limit` and `include_link_patterns` are your main safety rails.
    Set them before using deep browser discovery or `Crawler`.

#### Sitemap Settings

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `sitemap.follow_index` | `bool` | `True` | Traverse sitemap indexes |
| `sitemap.html_fallback` | `bool` | `True` | Crawl pages when no sitemaps found |
| `sitemap.max_depth` | `int` | `3` | Depth limit for HTML fallback |
| `sitemap.max_pages` | `int` | `500` | Page limit for HTML fallback |
| `sitemap.user_agent` | `str` | Custom | User agent for sitemap requests |
| `sitemap.respect_robots` | `bool` | `True` | Enforced by `SiteMap`: filters sitemap URLs and gates HTML fallback via `robots.txt` |
| `sitemap.deduplicate` | `bool` | `True` | Remove duplicate URLs |

#### Browser Settings

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `browser_settings` | `BrowserSettings` | `Default` | Playwright browser configuration |

#### Proxy Settings

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `proxies` | `List[ProxySettings]` | `None` | Proxies to use; one element for a single proxy, more to rotate |
| `proxy_rotation_method` | `str` | `"round_robin"` | Proxy rotation strategy |

!!! note "Use top-level proxy settings"
    Prefer `proxies` on `Settings` so sitemap, browser, and Crawler workflows
    share the same network configuration.

#### GenAI Settings

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `genai` | `LLMSettings` | `None` | AI extraction configuration |

### LLMSettings

Configuration for AI-powered content extraction.

```python
from onecrawler import LLMSettings

genai = LLMSettings(
    provider="openai",
    model_name="gpt-4o-mini",
    api_key="your-api-key",
    output_schema=ArticleModel
)
```

!!! warning "Keep API keys out of source"
    Pass provider keys through environment variables or your secret manager. Avoid
    committing keys in examples, settings files, or notebooks.

#### Fields

| Setting | Type | Required | Description |
|---------|------|----------|-------------|
| `provider` | `str` | Yes | Model provider: `"openai"`, `"google"`, or `"ollama"` |
| `model_name` | `str` | Yes | Model identifier |
| `api_key` | `str` | Conditional | API key for OpenAI/Google |
| `output_schema` | `BaseModel` | Conditional | Pydantic model for structured output |
| `base_url` | `str` | Optional | Custom endpoint URL (required for Ollama) |
| `timeout` | `float` | Optional | Per-provider request timeout override in seconds (provider default when unset) |
| `provider_kwargs` | `dict[str, Any]` | No | Provider-specific keyword arguments |
| `think` | `bool` | No | Ollama only; default `False`. Enables the model's reasoning trace. Keep `False` for structured output — Ollama returns an empty response for schema-constrained calls when thinking is on. Ignored by OpenAI/Google |

### BrowserSettings

Playwright browser configuration.

```python
from onecrawler import BrowserSettings

browser_settings = BrowserSettings(
    viewport={"width": 1440, "height": 900},
    locale="en-US",
    timezone_id="UTC",
)
```

!!! tip "Use storage state for authenticated pages"
    For logged-in crawls, create a Playwright `storage_state` file and reference it
    from `BrowserSettings`. Keep that file private because it may contain cookies.

#### Browser Settings Fields

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `viewport` | `dict` | `{"width": 1366, "height": 768}` | Browser viewport size |
| `locale` | `str` | `"en-US"` | Browser locale |
| `timezone_id` | `str` | `"Asia/Dhaka"` | Timezone identifier |
| `user_agent` | `str` | Default | Custom user agent |
| `storage_state` | `str` | `None` | Path to browser storage state |
| `wait_until` | `str` | `"domcontentloaded"` | Navigation completion condition |
| `timeout` | `int` | `30000` | Browser operation timeout in milliseconds |
| `settle_delay` | `int` | `1500` | Extra wait (ms) after navigation for client-side/JS-rendered content (e.g. SPA prices, listings) to hydrate before the page is captured. Set `0` to disable for faster crawls on static sites |

### ProxySettings

Proxy configuration for network requests.

```python
from onecrawler import ProxySettings

proxy = ProxySettings(
    server="http://proxy.example:8080",
    username="user",
    password="pass"
)
```

#### Fields

| Setting | Type | Required | Description |
|---------|------|----------|-------------|
| `server` | `str` | Yes | Proxy server URL |
| `username` | `str` | No | Proxy username |
| `password` | `str` | No | Proxy password |

### HumanBehaviorSettings

Configuration for human-like browser interactions.

```python
from onecrawler import HumanBehaviorSettings

human_settings = HumanBehaviorSettings(
    min_delay=0.5,
    max_delay=2.0,
    max_scrolls=20,
    min_mouse_moves=2,
    max_mouse_moves=8
)
```

#### Fields

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `min_delay` | `float` | `0.3` | Minimum delay between actions |
| `max_delay` | `float` | `1.2` | Maximum delay between actions |
| `max_scrolls` | `int` | `50` | Maximum scroll actions |
| `min_mouse_moves` | `int` | `5` | Minimum mouse movements |
| `max_mouse_moves` | `int` | `15` | Maximum mouse movements |

!!! note "Simulation trades speed for coverage"
    Human behavior settings can reveal lazy-loaded links, but each delay and scroll
    lowers throughput. Enable it only for pages that need it.

## Usage Examples

### Basic Configuration

```python
from onecrawler import Settings

settings = Settings(
    link_extraction_limit=100,
    include_link_patterns=["/news/*"],
    concurrency=5,
    request_timeout=15
)
```

### GenAI Configuration

```python
from pydantic import BaseModel
from onecrawler import Settings, LLMSettings

class Article(BaseModel):
    title: str
    author: str
    content: str

settings = Settings(
    scraping_strategy="genai",
    genai=LLMSettings(
        provider="openai",
        model_name="gpt-4o-mini",
        api_key="your-api-key",
        output_schema=Article
    )
)
```

### Proxy Configuration

```python
from onecrawler import Settings, ProxySettings

settings = Settings(
    proxies=[
        ProxySettings(server="http://proxy1.example:8080"),
        ProxySettings(server="http://proxy2.example:8080")
    ],
    proxy_rotation_method="round_robin"
)
```

### Browser Configuration

```python
from onecrawler import Settings, BrowserSettings

settings = Settings(
    browser_settings=BrowserSettings(
        viewport={"width": 1920, "height": 1080},
        locale="en-US",
        user_agent="MyCrawler/1.0",
    )
)
```

## Configuration Validation

`Settings` includes automatic validation:

```python
# This will raise an error
try:
    settings = Settings(
        scraping_strategy="genai",
        scraping_output_format="markdown"  # GenAI only supports JSON
    )
except ValueError as e:
    print(f"Configuration error: {e}")
```

### Validation Rules

1. **GenAI strategy**: Requires `genai` settings and JSON output format
2. **Human behavior**: Only applies to deep link extraction; enabled by passing `human_behavior_settings`
3. **Output formats**: GenAI extraction limited to JSON format

!!! tip "Let validation fail early"
    Build `Settings` near application startup. Invalid GenAI output formats or
    logging levels will fail before a long crawl begins.

## Environment Variables

Settings can be configured using environment variables:

```bash
export CRAWLER_CONCURRENCY=5
export CRAWLER_REQUEST_TIMEOUT=30
export OPENAI_API_KEY=your-api-key
```

```python
import os
from onecrawler import Settings, LLMSettings

settings = Settings(
    concurrency=int(os.getenv("CRAWLER_CONCURRENCY", 10)),
    request_timeout=int(os.getenv("CRAWLER_REQUEST_TIMEOUT", 10)),
    genai=LLMSettings(
        provider="openai",
        api_key=os.getenv("OPENAI_API_KEY"),
        model_name="gpt-4o-mini"
    )
)
```

## Configuration Files

Settings can be loaded from configuration files:

```python
import yaml
from onecrawler import Settings

# config.yaml
# link_extraction_limit: 500
# concurrency: 8
# scraping_strategy: "heuristic"

with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

settings = Settings(**config)
```

## Best Practices

1. **Set explicit limits**: Always configure `link_extraction_limit`
2. **Use path filters**: Apply `include_link_patterns` for focused crawling
3. **Configure timeouts**: Set appropriate `request_timeout` values
4. **Monitor resources**: Adjust `concurrency` based on system capacity
5. **Validate early**: Check configuration before starting crawls
6. **Use environment variables**: Keep sensitive data out of code
7. **Document settings**: Maintain configuration documentation
