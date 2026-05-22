---
title: Content Filters
---

# Content Filters Package

The `onecrawler.filters` package provides composable post-extraction filters for
refining crawl results. Filters are passed to `Crawler.run()` or
`Crawler.stream()` and evaluate each content dictionary after extraction.

!!! tip "Filters are post-extraction"
    Filters run after content has been extracted from a page. They do not affect
    URL discovery or link extraction — use `include_link_patterns` for that.

## Quick Example

```python
import asyncio
from onecrawler import Crawler, Settings
from onecrawler.filters import by_date, by_keywords
from onecrawler.filters.chain import AND


async def main():
    settings = Settings(
        link_extraction_limit=50,
        concurrency=5,
    )

    content_filter = AND(
        by_date(start="2025-01-01", end="2025-12-31"),
        by_keywords(["python", "async"]),
    )

    async with Crawler(settings) as engine:
        results = await engine.run(
            "https://example.com/blog",
            filters=content_filter,
        )

    print(f"Matched {len(results)} pages")


if __name__ == "__main__":
    asyncio.run(main())
```

## Available Filters

### by_date

Filter items by publication date range.

```python
from onecrawler.filters import by_date

# Keep items from 2025
f = by_date(start="2025-01-01", end="2025-12-31")

# Keep items after a date (no upper bound)
f = by_date(start="2025-06-01")

# Keep items before a date (no lower bound)
f = by_date(end="2025-06-30")
```

**Parameters:**

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `start` | `str` | No | Start date in `YYYY-MM-DD` format (inclusive) |
| `end` | `str` | No | End date in `YYYY-MM-DD` format (inclusive) |

!!! note "Date field requirements"
    `by_date` reads the `filedate` or `date` field from the content dictionary.
    Pages without a parseable date are excluded when this filter is active.

### by_keywords

Keep items whose text content contains any of the specified keywords.

```python
from onecrawler.filters import by_keywords

f = by_keywords(["machine learning", "neural network", "deep learning"])
```

**Parameters:**

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `keywords` | `Iterable[str]` | Yes | Keywords to search for (case-insensitive) |

The filter checks the `text` field of the content dictionary. Matching is
case-insensitive and uses substring containment — `"learn"` matches
`"machine learning"`.

### by_files

Keep items by logical file type.

```python
from onecrawler.filters import by_files

# Keep only PDF and image URLs
f = by_files(["pdf", "image"])
```

**Parameters:**

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `types` | `Iterable[str]` | Yes | Logical file types to match |

**Supported types:**

| Type | Extensions |
| --- | --- |
| `pdf` | `.pdf` |
| `docx` | `.docx` |
| `image` | `.png`, `.jpg`, `.jpeg`, `.webp`, `.gif` |
| `text` | `.txt`, `.md` |

Unknown types are treated as file extensions (e.g., `"csv"` matches `.csv`).

### by_extension

Keep items by URL file extension.

```python
from onecrawler.filters import by_extension

f = by_extension([".pdf", ".docx", "csv"])  # leading dot is optional
```

**Parameters:**

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `extensions` | `Iterable[str]` | Yes | File extensions to match (case-insensitive) |

### by_cosine_similarity

Keep items whose text content is semantically similar to a query using
bag-of-words cosine similarity.

```python
from onecrawler.filters import by_cosine_similarity

# Keep pages related to "climate change policy"
f = by_cosine_similarity("climate change policy", threshold=0.3)
```

**Parameters:**

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `query` | `str` | Yes | — | Query text to compare against |
| `threshold` | `float` | No | `0.25` | Minimum cosine similarity score to keep |

The filter checks the `content`, `title`, or `text` field (in that order). It
uses word-level tokenization and term-frequency cosine similarity — no external
dependencies or embeddings required.

!!! tip "Adjust threshold for precision"
    Lower thresholds (0.1–0.2) cast a wider net. Higher thresholds (0.3–0.5)
    return fewer but more relevant results. Start with the default and tune based
    on your content.

## Composing Filters

Import `AND`, `OR`, and `NOT` from `onecrawler.filters.chain` to combine
individual filters into complex logic.

```python
from onecrawler.filters import by_date, by_keywords, by_files
from onecrawler.filters.chain import AND, OR, NOT
```

### AND

Keep items that pass **all** filters:

```python
# Pages from 2025 that mention "python"
f = AND(
    by_date(start="2025-01-01", end="2025-12-31"),
    by_keywords(["python"]),
)
```

### OR

Keep items that pass **any** filter:

```python
# Pages about "AI" or "robotics"
f = OR(
    by_keywords(["artificial intelligence"]),
    by_keywords(["robotics"]),
)
```

### NOT

Invert a single filter:

```python
# Exclude PDFs
f = NOT(by_files(["pdf"]))
```

### Nested Composition

Operators can be nested for complex logic:

```python
# (recent AND about python) OR (any date AND about AI, but not PDFs)
f = OR(
    AND(
        by_date(start="2025-01-01"),
        by_keywords(["python"]),
    ),
    AND(
        by_keywords(["artificial intelligence"]),
        NOT(by_files(["pdf"])),
    ),
)
```

## Usage With Crawler

### Batch Filtering

```python
async with Crawler(settings) as engine:
    results = await engine.run(
        "https://example.com/news",
        filters=content_filter,
    )
```

### Streaming With Filters

Filters work with `Crawler.stream()` for real-time filtered output:

```python
async with Crawler(settings) as engine:
    async for item in engine.stream(
        "https://example.com/news",
        filters=by_cosine_similarity("election results"),
    ):
        print(item["title"])
```

!!! tip "Streaming is ideal for large crawls"
    Use `.stream()` with filters to process results as they arrive instead of
    waiting for the full crawl to complete.

## FilterChain Class

For advanced use, you can work with `FilterChain` directly:

```python
from onecrawler.filters.base import FilterChain

chain = FilterChain(
    by_date(start="2025-01-01"),
    by_keywords(["python"]),
    mode="AND",
)

# Add filters incrementally
chain.add(by_cosine_similarity("web scraping"))

# Use as a callable
keep = chain({"text": "python web scraping", "date": "2025-03-15"})
```

## Custom Filters

You can easily write your own custom filters to implement advanced filtering logic (such as deep semantic similarity, content analysis, or third-party API integration). 

A custom filter is simply any callable that takes a `dict` (the extracted page item) and returns a `bool` (`True` to keep the item, `False` to discard it). If you want your filter to accept parameters, you can write a factory function that returns a closure.

Here is an example of a custom semantic similarity filter using the `sentence-transformers` library:

```python
from typing import Callable
from sentence_transformers import SentenceTransformer, util

def by_semantic_similarity(query: str, threshold: float = 0.3) -> Callable[[dict], bool]:
    # Load the model once when the filter is initialized
    model = SentenceTransformer('all-MiniLM-L6-v2')
    query_emb = model.encode(query, convert_to_tensor=True)

    def _filter(item: dict) -> bool:
        # Check title, content or text fields
        doc_text = item.get("content") or item.get("title") or item.get("text") or ""
        if not doc_text:
            return False
        
        # Compute semantic similarity using embeddings
        doc_emb = model.encode(doc_text, convert_to_tensor=True)
        score = float(util.cos_sim(query_emb, doc_emb)[0][0])
        return score >= threshold

    return _filter
```

### Usage with the Crawler

You can pass your custom filter directly to the crawler's execution or streaming methods, exactly like built-in filters:

```python
async with Crawler(settings) as engine:
    async for item in engine.stream(
        "https://example.com/news",
        filters=by_semantic_similarity("artificial intelligence", threshold=0.35),
    ):
        print(item["title"])
```

## Best Practices

1. **Combine URL and content filters**: Use `include_link_patterns` for URL-level
   scoping and `onecrawler.filters` for content-level refinement.
2. **Start broad, then narrow**: Begin with loose filters and tighten as you
   understand the content structure.
3. **Use `by_cosine_similarity` for topic crawls**: It works well for
   news monitoring, research collection, and topical indexing.
4. **Date filter requires metadata**: Not all pages expose dates. Test with a
   small crawl first to verify your target site includes date fields.

!!! warning "Filters do not reduce extraction cost"
    Every page is still extracted before filters run. To reduce the number of
    pages extracted, use `include_link_patterns` or `link_extraction_limit` to
    limit discovery scope.
