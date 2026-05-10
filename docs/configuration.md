---
title: settings
---

# settings

`CrawlerSettings` is the shared settingsuration object used by sitemap discovery,
link extraction, and scraping. In production, treat it as the contract for a crawl:
it defines scope, speed, retry behavior, browser behavior, and output shape.

```python
from onecrawler import CrawlerSettings


settings = CrawlerSettings(
    link_extraction_limit=500,
    include_link_patterns=["/docs/*"],
    concurrency=8,
    request_timeout=15,
    max_retries=3,
)
```

## Core Settings

| Field | Default | Use it for |
| --- | --- | --- |
| `link_extraction_strategy` | `"deep"` | Browser link discovery mode: `deep` or `shallow` |
| `link_extraction_limit` | `50` | Hard cap on collected links |
| `include_link_patterns` | `None` | Allow-list URL paths such as `["/news/*"]` |
| `exclude_link_patterns` | `None` | Reserved for exclusion-style filtering |
| `scraping_strategy` | `"heuristic"` | `heuristic` or `genai` extraction |
| `scraping_output_format` | `"json"` | `markdown`, `json`, `csv`, `html`, `python`, `txt`, `xml`, or `xmltei` |
| `concurrency` | `10` | Number of async workers |
| `max_retries` | `2` | Retry attempts for transient failures |
| `request_timeout` | `10` | Per-request timeout in seconds |
| `retry_delay` | `1` | Base delay between retries |
| `enable_logging` | `False` | Whether your app should settingsure logging |
| `logging_level` | `"INFO"` | Desired log level |

## Sitemap Settings

| Field | Default | Use it for |
| --- | --- | --- |
| `follow_sitemap_index` | `True` | Traverse sitemap indexes and nested XML sitemaps |
| `sitemap_html_fallback` | `True` | Crawl same-origin HTML pages when no sitemap records are found |
| `max_crawl_depth` | `3` | Depth limit for HTML fallback |
| `max_crawl_pages` | `500` | Page cap for HTML fallback |
| `sitemap_user_agent` | Onecrawler UA | User agent for sitemap HTTP requests |
| `sitemap_respect_robots` | `True` | Intended robots.txt behavior |
| `sitemap_deduplicate` | `True` | Normalize and remove duplicate sitemap URLs |

Best practice: keep `sitemap_html_fallback=True` during exploration, then turn it
off for predictable scheduled jobs if you only trust XML sitemap sources.

## Browser Settings

`browser_settings` controls Playwright launch, context, proxy, and timeout behavior.
Use it when the target site needs JavaScript rendering, a custom user agent, proxy
routing, a stored session, or a different viewport.

```python
from onecrawler import BrowserSettings, ContextSettings, CrawlerSettings


settings = CrawlerSettings(
    browser_settings=BrowserSettings(
        context=ContextSettings(
            viewport={"width": 1440, "height": 900},
            locale="en-US",
            timezone_id="UTC",
        )
    )
)
```

For authenticated crawling, use Playwright storage state:

```python
from onecrawler import BrowserSettings, ContextSettings, CrawlerSettings


settings = CrawlerSettings(
    browser_settings=BrowserSettings(
        context=ContextSettings(storage_state="auth-state.json")
    )
)
```

## Proxy Settings

Use `proxy` for a single proxy or `proxies` for a rotating proxy pool. The top-level
settings are the recommended API because they can be shared across sitemap discovery
and browser-backed workflows.

```python
from onecrawler import CrawlerSettings, ProxySettings


settings = CrawlerSettings(
    proxy=ProxySettings(
        server="http://proxy.example:8080",
        username="user",
        password="pass",
    )
)
```

Multiple proxies can rotate with `round_robin` or `random`:

```python
settings = CrawlerSettings(
    proxies=[
        ProxySettings(server="http://proxy-1.example:8080"),
        ProxySettings(server="http://proxy-2.example:8080"),
    ],
    proxy_rotation="round_robin",
)
```

`proxy` and `proxies` are mutually exclusive. Use one proxy for a stable route and a
proxy pool when sitemap discovery or future request-heavy workflows should spread
traffic across multiple endpoints.

## Human Behavior Settings

`enable_human_behaviors` adds optional delay, scroll, and mouse-move simulation
during deep browser link extraction.

```python
from onecrawler import CrawlerSettings, HumanBehaviorSettings


settings = CrawlerSettings(
    enable_human_behaviors=True,
    human_behavior_settings=HumanBehaviorSettings(
        min_delay=0.5,
        max_delay=2.0,
        max_scrolls=20,
        min_mouse_moves=2,
        max_mouse_moves=8,
    ),
)
```

Use this sparingly. It can help pages that lazy-load links after scroll, but it also
slows crawls significantly. For high-volume discovery, prefer sitemaps first, then
plain deep crawling, then human behavior simulation only where needed.

## GenAI Settings

`GenerativeAISettings` is required when `scraping_strategy="genai"`. GenAI output is
restricted to JSON because structured model responses should be explicit and
machine-readable.

```python
from pydantic import BaseModel

from onecrawler import CrawlerSettings, GenerativeAISettings


class Product(BaseModel):
    name: str
    price: str | None = None
    availability: str | None = None


settings = CrawlerSettings(
    scraping_strategy="genai",
    scraping_output_format="json",
    genai=GenerativeAISettings(
        provider="openai",
        model_name="gpt-4o-mini",
        api_key="YOUR_API_KEY",
        output_schema=Product,
    ),
)
```

Use GenAI when you need typed fields, normalization, summaries, or extraction that
requires interpretation. Avoid it for simple bulk text extraction where the heuristic
strategy is faster, cheaper, and easier to reproduce.

## Performance Tuning

Tune in this order:

1. Narrow `include_link_patterns`.
2. Set a realistic `link_extraction_limit`.
3. Start with moderate `concurrency`.
4. Increase `request_timeout` only for slow sites.
5. Add retries for flaky targets.

Good starting profiles:

| Scenario | Settings |
| --- | --- |
| Small docs site | `concurrency=5`, `link_extraction_limit=100` |
| News section sitemap | `concurrency=10`, `link_extraction_limit=500`, path filter |
| JavaScript-heavy site | `concurrency=3`, browser extraction, longer timeout |
| GenAI extraction | `concurrency=2`, `request_timeout=30`, schema required |

## Caveats

High concurrency is not always faster. Browser pages, network limits, target rate
limits, and model APIs can all become bottlenecks. Increase concurrency gradually and
watch error rates.

`include_link_patterns` are matched against URL paths. Prefer patterns like
`"/news/*"` or `"/docs/*"` instead of full URLs.

`CrawlerSettings` validates GenAI output format at initialization. If you choose
`scraping_strategy="genai"`, keep `scraping_output_format="json"`.
