---
title: Settings
---

# Settings

`Settings` is the shared configuration object used by sitemap discovery,
link extraction, and scraping. In production, treat it as the contract for a crawl:
it defines scope, speed, retry behavior, browser behavior, and output shape.

```python
from onecrawler import Settings


settings = Settings(
    link_extraction_limit=500,
    include_link_patterns=["/docs/*"],
    concurrency=8,
    request_timeout=15,
    max_retries=3,
)
```

!!! tip "Make scope explicit"
    Set `link_extraction_limit` and `include_link_patterns` before running broad
    discovery. These two fields are the easiest way to keep crawls predictable.

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
| `enable_logging` | `False` | Whether your app should configure logging |
| `logging_level` | `"INFO"` | Desired log level |

## Sitemap Settings

| Field | Default | Use it for |
| --- | --- | --- |
| `sitemap.follow_index` | `True` | Traverse sitemap indexes and nested XML sitemaps |
| `sitemap.html_fallback` | `True` | Crawl same-origin HTML pages when no sitemap records are found |
| `sitemap.max_depth` | `3` | Depth limit for HTML fallback |
| `sitemap.max_pages` | `500` | Page cap for HTML fallback |
| `sitemap.user_agent` | OneCrawler UA | User agent for sitemap HTTP requests |
| `sitemap.respect_robots` | `True` | Intended robots.txt behavior |
| `sitemap.deduplicate` | `True` | Normalize and remove duplicate sitemap URLs |

Best practice: keep `sitemap.html_fallback=True` during exploration, then turn it
off for predictable production jobs if you only trust XML sitemap sources.

!!! note "HTML fallback is discovery, not scraping"
    Sitemap HTML fallback is only for finding URLs when XML sources are missing. Use
    `Scraper` or `Crawler` to extract page content after URLs are
    discovered.

## Browser Settings

`browser_settings` controls Playwright launch, context, proxy, and timeout behavior.
Use it when the target site needs JavaScript rendering, a custom user agent, proxy
routing, a stored session, or a different viewport.

```python
from onecrawler import BrowserSettings, Settings


settings = Settings(
    browser_settings=BrowserSettings(
        viewport={"width": 1440, "height": 900},
        locale="en-US",
        timezone_id="UTC",
    )
)
```

For authenticated crawling, use Playwright storage state:

```python
from onecrawler import BrowserSettings, Settings


settings = Settings(
    browser_settings=BrowserSettings(storage_state="auth-state.json")
)
```

!!! warning "Do not commit storage state"
    Playwright storage state can contain cookies or authenticated session data. Keep
    those files out of version control and rotate them like credentials.

## Proxy Settings

Use `proxy` for a single proxy or `proxies` for a rotating proxy pool. The top-level
settings are the recommended API because they can be shared across sitemap discovery
and browser-backed workflows.

```python
from onecrawler import Settings, ProxySettings


settings = Settings(
    proxy=ProxySettings(
        server="http://proxy.example:8080",
        username="user",
        password="pass",
    )
)
```

Multiple proxies can rotate with `round_robin` or `random`:

```python
settings = Settings(
    proxies=[
        ProxySettings(server="http://proxy-1.example:8080"),
        ProxySettings(server="http://proxy-2.example:8080"),
    ],
    proxy_rotation_method="round_robin",
)
```

`proxy` and `proxies` are mutually exclusive. Use one proxy for a stable route and a
proxy pool when sitemap discovery or future request-heavy workflows should spread
traffic across multiple endpoints.

!!! warning "Proxy settings are mutually exclusive"
    Configure either `proxy` or `proxies`, not both. `Settings` raises a
    validation error when both are provided.

## Human Behavior Settings

`enable_human_behaviors` adds optional delay, scroll, and mouse-move simulation
during deep browser link extraction.

```python
from onecrawler import Settings, HumanBehaviorSettings


settings = Settings(
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

!!! tip "Use human behavior for lazy-loaded links"
    Enable human behavior simulation when links appear after scrolling. Keep it off
    for static pages because it deliberately slows every page.

## GenAI Settings

`GenerativeAISettings` is required when `scraping_strategy="genai"`. GenAI output is
restricted to JSON because structured model responses should be explicit and
machine-readable.

### Installation

First install the GenAI dependencies:

```bash
pip install "onecrawler[genai]"
```

### Basic Configuration

```python
from pydantic import BaseModel
from onecrawler import Settings, GenerativeAISettings

class Product(BaseModel):
    name: str
    price: str | None = None
    availability: str | None = None

settings = Settings(
    scraping_strategy="genai",  # Required for GenAI extraction
    scraping_output_format="json",  # GenAI only supports JSON
    genai=GenerativeAISettings(
        provider="openai",  # Options: "openai", "google", "ollama"
        model_name="gpt-4o-mini",
        api_key="YOUR_API_KEY",  # Required for OpenAI/Google, optional for Ollama
        output_schema=Product,  # Pydantic model for structured output
    ),
    concurrency=2,  # Lower concurrency recommended for GenAI
    request_timeout=30,  # Increase timeout for model responses
)
```

### Provider-Specific Configuration

#### OpenAI
```python
genai=GenerativeAISettings(
    provider="openai",
    model_name="gpt-4o-mini",
    api_key="sk-...",  # Your OpenAI API key
    output_schema=Product,
)
```

#### Google
```python
genai=GenerativeAISettings(
    provider="google",
    model_name="gemini-1.5-pro",
    api_key="AIza...",  # Your Google API key
    output_schema=Product,
)
```

#### Ollama
```python
genai=GenerativeAISettings(
    provider="ollama",
    model_name="llama3:8b",
    base_url="http://localhost:11434/",  # Your Ollama instance
    output_schema=Product,
    # api_key optional for Ollama
)
```

### All Available Fields

| Field | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `provider` | `str` | Yes | - | Model provider: `"openai"`, `"google"`, or `"ollama"` |
| `model_name` | `str` | Yes | - | Model identifier |
| `api_key` | `str` | Conditional | `None` | API key for OpenAI/Google, optional for Ollama |
| `output_schema` | `BaseModel` | Conditional | `None` | Pydantic model for structured output |
| `base_url` | `str` | Optional | `None` | Custom endpoint URL (required for Ollama) |
| `provider_kwargs` | `dict[str, Any]` | No | `None` | Provider-specific keyword arguments |

### Usage Tips

- **Lower concurrency**: GenAI calls are slower and more expensive. Use `concurrency=1-3`.
- **Increase timeout**: Model responses can take 10-30+ seconds. Use `request_timeout=30+`.
- **Structured schemas**: Define clear Pydantic models for reliable extraction.
- **Error handling**: GenAI calls may fail due to rate limits or model errors.

Use GenAI when you need typed fields, normalization, summaries, or extraction that
requires interpretation. Avoid it for simple bulk text extraction where heuristic
strategy is faster, cheaper, and easier to reproduce.

!!! warning "GenAI requires JSON output"
    When `scraping_strategy="genai"`, keep `scraping_output_format="json"` and
    provide `GenerativeAISettings`. Other output formats are rejected during
    settings validation.

## Crawler Configuration

`Crawler` uses the same `Settings` object but emphasizes specific fields for its orchestrated workflow:

### Required for Production

!!! warning "Proxy configuration is required for production"
    `Crawler` combines browser navigation and extraction across multiple
    pages. Use a proxy or proxy pool for production jobs to reduce blocking and keep
    traffic routing explicit.

**Proxy Configuration:**
```python
settings = Settings(
    proxies=[
        ProxySettings(server="http://proxy1.example.com:8080"),
        ProxySettings(server="http://proxy2.example.com:8080"),
    ],
    proxy_rotation_method="round_robin",
)
```

### Key Crawler Settings

| Field | Recommended for Crawler | Purpose |
| --- | --- | --- |
| `link_extraction_limit` | `50-200` | Controls total pages crawled in Crawler |
| `include_link_patterns` | Strongly recommended | Scope crawling to relevant sections |
| `concurrency` | `3-8` | Browser workers for link discovery |
| `enable_human_behaviors` | `False` (default) or `True` | Simulate human browsing patterns |
| `human_behavior_settings` | Customizable if enabled | Configure delays, scrolls, mouse movements |

### Content Filtering

Crawler supports composable content filtering via the `filters` parameter on
`.run()` and `.stream()`. Filters are applied after content extraction.

```python
from onecrawler.filters import by_date, by_keywords
from onecrawler.filters.chain import AND

content_filter = AND(
    by_date(start="2024-01-01", end="2024-12-31"),
    by_keywords(["python", "async"]),
)

async with Crawler(settings) as engine:
    results = await engine.run("https://example.com/news", filters=content_filter)
```

**Available filters:**

| Filter | Purpose |
| --- | --- |
| `by_date(start, end)` | Keep items within a `YYYY-MM-DD` date range |
| `by_keywords(keywords)` | Keep items whose text contains any keyword |
| `by_files(types)` | Keep items by logical file type (`pdf`, `image`, `docx`, `text`) |
| `by_extension(extensions)` | Keep items by URL file extension |
| `by_cosine_similarity(query, threshold)` | Keep items semantically similar to a query |

**Composing filters:**

Use `AND`, `OR`, and `NOT` from `onecrawler.filters.chain`:

```python
from onecrawler.filters.chain import AND, OR, NOT

f = AND(by_date(start="2024-01-01"), NOT(by_files(["pdf"])))
```

!!! note "Filters run post-extraction"
    Content must be extracted before filters can evaluate it. Date filters read
    the `filedate` or `date` field; pages without a parseable date are excluded.

### Human Behavior Settings

When `enable_human_behaviors=True`, configure realistic browsing:

```python
settings = Settings(
    enable_human_behaviors=True,
    human_behavior_settings=HumanBehaviorSettings(
        min_delay=1.0,        # Minimum delay between actions (seconds)
        max_delay=3.0,        # Maximum delay between actions (seconds)
        max_scrolls=5,        # Maximum scroll gestures per page
        min_mouse_moves=2,    # Minimum mouse movements
        max_mouse_moves=5,    # Maximum mouse movements
        mouse_width=100,      # Mouse movement area width
        mouse_height=100,     # Mouse movement area height
        min_mouse_steps=5,    # Minimum steps per movement
        max_mouse_steps=15,   # Maximum steps per movement
        min_mouse_sleep=0.1,  # Minimum sleep between steps
        max_mouse_sleep=0.3,  # Maximum sleep between steps
    ),
)
```

### Crawler Performance Profiles

| Use Case | Recommended Settings |
| --- | --- |
| **Small blog** | `link_extraction_limit=50`, `concurrency=3`, no human behaviors |
| **News site** | `link_extraction_limit=200`, `concurrency=5`, focused path filters |
| **JavaScript-heavy** | `link_extraction_limit=100`, `concurrency=3`, enable human behaviors |
| **Production crawling** | `link_extraction_limit=150`, `concurrency=4`, proxy pool required |

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

`Settings` validates GenAI output format at initialization. If you choose
`scraping_strategy="genai"`, keep `scraping_output_format="json"`.

!!! tip "Tune one variable at a time"
    When performance changes, adjust filters, limits, concurrency, timeout, and
    retries separately. Changing them together makes failures much harder to
    diagnose.
