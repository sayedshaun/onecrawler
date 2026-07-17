---
title: API reference
---

# API Reference

This page is generated directly from the source docstrings, so it always matches the
installed version. The guide pages explain *when* and *why* to use each object; this
page is the authoritative *what*.

!!! note "Public imports"
    User-facing code should prefer `from onecrawler import ...`. Internal runtime
    helpers should be imported from their concrete modules only when you are extending
    OneCrawler itself.

```python
from onecrawler import (
    Crawler,
    LinkExtractor,
    Scraper,
    Settings,
    SiteMap,
)
```

## Engines

::: onecrawler.Crawler

::: onecrawler.LinkExtractor

::: onecrawler.Scraper

## Sitemap discovery

::: onecrawler.SiteMap

## Settings

::: onecrawler.Settings

::: onecrawler.BrowserSettings

::: onecrawler.LLMSettings

::: onecrawler.HumanBehaviorSettings

::: onecrawler.ProxySettings

## Filters

Composable predicates over extracted content dicts. Build a filter, then pass it to
`Crawler.run()` / `Crawler.stream()` as the `filters` argument.

::: onecrawler.filters.by_date

::: onecrawler.filters.by_keywords

::: onecrawler.filters.by_files

::: onecrawler.filters.by_extension

::: onecrawler.filters.by_cosine_similarity

### Composition

Combine filters with boolean logic.

::: onecrawler.filters.AND

::: onecrawler.filters.OR

::: onecrawler.filters.NOT

## Output writers

Helpers for persisting results, exported from `onecrawler.utils.writter`.

::: onecrawler.utils.writter.dump_json

::: onecrawler.utils.writter.dump_jsonl

::: onecrawler.utils.writter.dump_txt

::: onecrawler.utils.writter.dump_csv
