---
title: Scraping Engine
---

# Scraping Engine Package

The scraping package provides content extraction engines for scraping web pages:
deterministic heuristic extraction, whole-page Markdown conversion, and AI-powered
structured extraction.

!!! tip "Start with heuristic extraction"
    Use the heuristic strategy for bulk article, blog, documentation, or catalog
    text extraction. Add GenAI only when you need typed fields, summaries,
    normalization, or semantic interpretation.

## Classes

### Scraper

Main scraping engine that supports heuristic, markdownify, and GenAI content extraction strategies.

```python
from onecrawler import Settings, Scraper

async with Scraper(settings) as scraper:
    item = await scraper.run("https://example.com/article")
    print(item["url"], item["result"])
```

#### Parameters

- `settings` (`Settings`): Configuration for scraping behavior

#### Methods

- `run(url: str) -> dict`: Extract content from the given URL, returning
  `{"url": str, "result": Any}` — `result`'s shape depends on
  `scraping_strategy`/`scraping_output_format` (a dict, plain text, or a
  GenAI `output_schema` model instance)
- `run(urls: List[str]) -> List[dict]`: Extract content from multiple URLs,
  returning one `{"url": str, "result": Any}` dict per successful extraction

#### Strategies

- **Heuristic**: Fast, rule-based extraction using trafilatura; isolates
  article-like content and strips boilerplate, but can return little or
  nothing on non-article pages (e-commerce, dashboards, listings)
- **Markdownify**: Faithful whole-page HTML-to-Markdown conversion with no
  content extraction; never returns `None` for a rendered page, so it's the
  fallback for pages heuristic extraction can't handle
- **GenAI**: AI-powered extraction with structured output

!!! note "Single URL vs list behavior"
    `Scraper.run()` returns one `{"url": ..., "result": ...}` dict for a
    single URL and a list of them for multiple URLs. Failed extractions are
    omitted from list results. The `url` key lets you trace a result back to
    its source even though `stream()` completes in `asyncio.as_completed()`
    order rather than input order.

### HeuristicStrategy

Rule-based content extraction using the trafilatura library.

```python
from onecrawler.crawler.scraper.heuristic.script import HeuristicStrategy

strategy = HeuristicStrategy(settings, browser=browser)
content = await strategy.extract(url)
```

#### Features

- **Fast extraction**: No model calls, deterministic results
- **Multiple formats**: Markdown, JSON, XML, and XML-TEI output
- **Language detection**: Automatic language identification
- **Content cleaning**: Removes boilerplate and navigation

### MarkdownifyStrategy

Whole-page HTML-to-Markdown conversion using `html-to-markdown`, with no content
extraction.

```python
from onecrawler.crawler.scraper.markdown.script import MarkdownifyStrategy

strategy = MarkdownifyStrategy(settings, browser=browser)
content = await strategy.extract(url)
```

#### Features

- **Never empty**: Converts the whole rendered page, so it works on pages
  heuristic extraction returns little or nothing for
- **Faithful conversion**: Keeps navigation, footers, and other page chrome —
  no boilerplate removal and no extracted metadata
- **Deterministic filtering**: Set `settings.exclude_selectors` (e.g.
  `["nav", "footer", ".cookie-banner"]`) to strip known chrome before
  conversion, at no LLM cost

### LLMStrategy

AI-powered content extraction using language models.

```python
from onecrawler.crawler.scraper.genai.executor import LLMStrategy

strategy = LLMStrategy(
    provider=genai_settings.provider,
    model_name=genai_settings.model_name,
    max_retries=2,
    api_key=genai_settings.api_key,
    base_url=genai_settings.base_url,
    output_schema=genai_settings.output_schema,
    provider_kwargs=genai_settings.provider_kwargs,
    timeout=genai_settings.timeout,
    think=genai_settings.think,
    exclude_selectors=settings.exclude_selectors,
    browser=browser,
)
content = await strategy.extract(url)
```

#### Features

- **Structured output**: Pydantic schema-based extraction
- **Semantic understanding**: Context-aware content extraction
- **Field normalization**: Consistent data formatting
- **Custom schemas**: Define your own output structure

## Usage Examples

### Heuristic Scraping

```python
from onecrawler import Settings, Scraper

async def scrape_heuristic():
    settings = Settings(
        scraping_strategy="heuristic",
        scraping_output_format="json",
        concurrency=10,
        request_timeout=15
    )
    
    async with Scraper(settings) as scraper:
        item = await scraper.run("https://example.com/article")
    
    return item["result"]

if __name__ == "__main__":
    import asyncio
    asyncio.run(scrape_heuristic())
```

### GenAI Scraping

```python
from pydantic import BaseModel
from onecrawler import Settings, LLMSettings, Scraper

class Article(BaseModel):
    title: str
    author: str
    content: str
    published_date: str

async def scrape_with_ai():
    settings = Settings(
        scraping_strategy="genai",
        scraping_output_format="json",
        genai=LLMSettings(
            provider="openai",
            model_name="gpt-4o-mini",
            api_key="your-api-key",
            output_schema=Article
        ),
        concurrency=2,
        request_timeout=30
    )
    
    async with Scraper(settings) as scraper:
        item = await scraper.run("https://example.com/article")
    
    return item["result"]  # an Article instance

if __name__ == "__main__":
    import asyncio
    asyncio.run(scrape_with_ai())
```

!!! warning "GenAI has operational cost"
    Model extraction is slower and can hit provider rate limits. Keep
    `concurrency` low, increase `request_timeout`, and monitor cost per page.

### Batch Scraping

```python
async def scrape_multiple():
    urls = [
        "https://example.com/article1",
        "https://example.com/article2",
        "https://example.com/article3"
    ]
    
    settings = Settings(
        scraping_strategy="heuristic",
        concurrency=5,
        max_retries=3
    )
    
    async with Scraper(settings) as scraper:
        results = await scraper.run(urls)  # [{"url": ..., "result": ...}, ...]
    
    return results
```

!!! tip "Persist failed URLs"
    For large batches, save failed or empty URLs separately. Retrying only failures
    is faster than repeating discovery and scraping the whole batch. Since each
    result carries its own `url`, you can find failures by diffing the input
    list against `[r["url"] for r in results]`.

## Configuration

Scraping behavior is controlled through `Settings`:

| Setting | Description | Default |
|---------|-------------|---------|
| `scraping_strategy` | `"heuristic"`, `"genai"`, or `"markdownify"` | `"heuristic"` |
| `scraping_output_format` | Output format (ignored by `"markdownify"`) | `"json"` |
| `exclude_selectors` | CSS selectors to strip before conversion (`"markdownify"`/`"genai"`) | `None` |
| `concurrency` | Number of parallel workers | `10` |
| `request_timeout` | Per-request timeout | `10` |
| `max_retries` | Retry attempts | `2` |
| `genai` | GenAI configuration | `None` |

## Output Formats

### Heuristic Strategy

- **JSON**: Structured data with metadata
- **Markdown**: Clean text formatting
- **XML**: Original TEI-agnostic XML structure
- **XML-TEI**: TEI-conformant XML output

### Markdownify Strategy

- **Markdown only**: `scraping_output_format` is ignored; always returns a
  plain Markdown string of the whole page, with no extracted metadata

### GenAI Strategy

- **JSON**: Structured output matching Pydantic schema
- **Custom formats**: Based on your schema definition

!!! warning "GenAI output is JSON-only"
    Configure `scraping_output_format="json"` when using
    `scraping_strategy="genai"`. Other formats are rejected during settings
    validation.

## Performance Considerations

### Heuristic Scraping

- **Fast**: No model calls, deterministic timing
- **Lightweight**: Lower memory and CPU usage
- **Scalable**: Higher concurrency possible
- **Consistent**: Predictable performance

### GenAI Scraping

- **Slower**: Model response time (10-30 seconds)
- **Expensive**: API costs per request
- **Limited concurrency**: Lower parallelism
- **Variable**: Response time depends on model

!!! tip "Split discovery and scraping"
    Discover URLs once, store them, then scrape in controlled batches. This makes
    retries, rate-limit recovery, and cost tracking much easier.

## Best Practices

### When to Use Heuristic

- **Bulk content extraction**: Large numbers of pages
- **Fast processing**: Time-sensitive operations
- **Cost efficiency**: Budget-conscious projects
- **Simple content**: Articles, blog posts, documentation

### When to Use GenAI

- **Structured data**: Specific fields required
- **Complex content**: Mixed or unstructured pages
- **Normalization**: Consistent data formatting
- **Semantic extraction**: Understanding context

### General Tips

1. **Start with heuristic**: Faster and cheaper
2. **Filter URLs**: Only scrape relevant pages
3. **Set timeouts**: Handle slow pages gracefully
4. **Monitor errors**: Track failure rates
5. **Batch processing**: Group similar requests

## Error Handling

The scraper handles various error conditions:

- **Network errors**: Automatic retries with backoff
- **Parsing errors**: Graceful degradation
- **Timeout errors**: Configurable timeouts
- **Rate limiting**: Respects server limits
- **Model errors**: Fallback strategies for GenAI

## Integration Examples

### Save to File

```python
from onecrawler import Settings, Scraper
from onecrawler.utils import writter

async def scrape_and_save():
    settings = Settings(scraping_strategy="heuristic")
    
    async with Scraper(settings) as scraper:
        item = await scraper.run("https://example.com/article")

    writter.dump_json(item, "output.json")  # includes both "url" and "result"
```

### Database Integration

```python
from onecrawler import Settings, Scraper

async def scrape_to_database():
    settings = Settings(scraping_strategy="heuristic")
    
    async with Scraper(settings) as scraper:
        urls = ["https://example.com/page1", "https://example.com/page2"]
        results = await scraper.run(urls)
    
    # Save to database
    for item in results:
        await save_to_database(item["url"], item["result"])
```

## Troubleshooting

### Common Issues

1. **Empty results**: Check URL accessibility and content structure
2. **Timeout errors**: Increase `request_timeout` or reduce concurrency
3. **GenAI failures**: Verify API keys and model availability
4. **Memory issues**: Reduce concurrency for large batches
5. **Rate limits**: Implement delays between requests

### Debug Mode

Enable detailed logging for troubleshooting:

```python
settings = Settings(
    logging_level="DEBUG"
)
```

!!! note "Empty content is not always an error"
    Some pages are navigation, search, login, or media-only pages with little
    extractable text. Use URL filters to keep these out of scraping batches.
