---
title: Link extraction
---

# Link Extraction

`LinkExtractionEngine` discovers internal links from a starting URL using a
Playwright-backed browser. It is the right tool when sitemap discovery is missing,
incomplete, or unable to see JavaScript-rendered links.

For most projects, try [sitemap discovery](sitemap-discovery.md) first. Browser link
extraction is more flexible, but it costs more CPU, memory, and wall-clock time.

## Crawl Modes

| Mode | Use it when | Avoid it when |
| --- | --- | --- |
| `shallow` | You only need links from the starting page | You need recursive traversal |
| `deep` | You need to follow same-site links until a limit | A sitemap already gives complete coverage |

## Shallow Extraction

Shallow extraction opens the start page, reads anchor tags, filters same-domain
links, and stops at `link_extraction_limit`.

```python
import asyncio

from onecrawler import CrawlerSettings, LinkExtractionEngine


async def main():
    config = CrawlerSettings(
        link_extraction_strategy="shallow",
        link_extraction_limit=50,
        include_link_patterns=["/articles/*"],
    )

    async with LinkExtractionEngine(config) as engine:
        links = await engine.run("https://example.com/latest")

    print(links)


if __name__ == "__main__":
    asyncio.run(main())
```

Use shallow mode for listing pages, category pages, search result pages, and landing
pages that already expose the URLs you want.

## Deep Extraction

Deep extraction recursively follows same-origin links. It uses a scheduler, a browser
page pool, and async workers controlled by `concurrency`.

```python
import asyncio

from onecrawler import CrawlerSettings, LinkExtractionEngine


async def main():
    config = CrawlerSettings(
        link_extraction_strategy="deep",
        link_extraction_limit=300,
        include_link_patterns=["/docs/*"],
        concurrency=5,
        request_timeout=15,
    )

    async with LinkExtractionEngine(config) as engine:
        links = await engine.run("https://example.com/docs")

    print(f"Discovered {len(links)} links")


if __name__ == "__main__":
    asyncio.run(main())
```

Use deep mode when navigation is discoverable only through page links, such as
documentation trees, article archives, and sites with weak sitemap coverage.

## Filtering

Always filter broad crawls. `include_link_patterns` are wildcard patterns matched
against the URL path.

```python
config = CrawlerSettings(
    include_link_patterns=[
        "/news/*",
        "/analysis/*",
    ]
)
```

Good filters are section-based and stable. Avoid filters that depend on temporary
query parameters unless those parameters are part of the canonical URL design.

## Human Behavior Simulation

Deep extraction can optionally add human-like delays, scrolling, and mouse movement.
This is useful for pages that lazy-load links after scroll or require small delays
before all navigation appears.

```python
from onecrawler import CrawlerSettings, HumanBehaviorSettings


config = CrawlerSettings(
    link_extraction_strategy="deep",
    enable_human_behaviors=True,
    human_behavior_settings=HumanBehaviorSettings(
        min_delay=0.5,
        max_delay=1.5,
        max_scrolls=25,
        min_mouse_moves=2,
        max_mouse_moves=6,
    ),
)
```

Do not enable this by default for high-volume jobs. It intentionally slows each page.
Use it only after you confirm that normal browser traversal misses links.

## Production Pattern

For durable crawler jobs, separate discovery from scraping and persist the URL list.
That makes retries easier and prevents a scraping failure from forcing a fresh crawl.

```python
import asyncio
import json

from onecrawler import CrawlerSettings, LinkExtractionEngine


async def main():
    config = CrawlerSettings(
        link_extraction_strategy="deep",
        link_extraction_limit=1000,
        include_link_patterns=["/guide/*"],
        concurrency=6,
    )

    async with LinkExtractionEngine(config) as engine:
        links = await engine.run("https://example.com/guide")

    with open("discovered-links.json", "w", encoding="utf-8") as f:
        json.dump(links, f, indent=2)


if __name__ == "__main__":
    asyncio.run(main())
```

## Performance Notes

Each browser page consumes memory. A high `concurrency` value can make a crawl slower
if the machine spends time managing browser contexts instead of loading pages.

Start with:

- `concurrency=3` to `5` for browser-heavy sites
- `link_extraction_limit` set to your real batch size
- path filters enabled
- human behavior simulation disabled

Increase concurrency only after you verify that pages are loading reliably and the
target is not responding with rate limits.

## Caveats

Deep extraction only keeps links that start with the same scheme and host as the
start URL. Crawling `https://example.com` will not include
`https://blog.example.com` unless you start from that subdomain.

Anchor fragments are removed during deep parsing, so
`https://example.com/page#section` and `https://example.com/page` collapse to the
same URL.

If the crawl returns fewer links than expected, check whether the site hides links
behind buttons, forms, client-side routing, authentication, or a different subdomain.
