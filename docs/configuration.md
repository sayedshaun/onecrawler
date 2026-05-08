---
title: Configuration
---

# Configuration

`CrawlerSettings` is the central configuration object used across the package.

## Common fields

| Field | Type | Description |
| --- | --- | --- |
| `link_extraction_strategy` | `str` | `deep` or `shallow` traversal mode |
| `link_extraction_limit` | `int` | Maximum number of links to extract |
| `include_link_patterns` | `list[str]` | Wildcard filters such as `["/news/*"]` |
| `scraping_strategy` | `str` | `heuristic` or an AI-based strategy |
| `scraping_output_format` | `str` | One of `markdown`, `json`, `csv`, `html`, `txt`, `xml`, `xmltei`, `python` |
| `concurrency` | `int` | Number of concurrent async workers |
| `max_retries` | `int` | Retry attempts per failed request |
| `request_timeout` | `int` | Per-request timeout in seconds |

## Example

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

## Suggested defaults

- use `deep` when you need recursive traversal
- use `shallow` when you only want the first layer of discovered links
- keep `concurrency` conservative at first, then increase gradually
- set a reasonable `request_timeout` for the target site
