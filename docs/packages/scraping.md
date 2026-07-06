---
title: Scraping Engine
---

# Scraping Engine Package

The scraping package provides content extraction engines for scraping web pages with
both heuristic and AI-powered approaches.

!!! tip "Start with heuristic extraction"
    Use the heuristic strategy for bulk article, blog, documentation, or catalog
    text extraction. Add GenAI only when you need typed fields, summaries,
    normalization, or semantic interpretation.

## Classes

### Scraper

Main scraping engine that supports both heuristic and GenAI content extraction strategies.

```python
from onecrawler import Settings, Scraper

async with Scraper(settings) as scraper:
    data = await scraper.run("https://example.com/article")
```

#### Parameters

- `settings` (`Settings`): Configuration for scraping behavior

#### Methods

- `run(url: str) -> Any`: Extract content from the given URL
- `run(urls: List[str]) -> List[Any]`: Extract content from multiple URLs

#### Strategies

- **Heuristic**: Fast, rule-based extraction using trafilatura
- **GenAI**: AI-powered extraction with structured output

!!! note "Single URL vs list behavior"
    `Scraper.run()` returns one item for a single URL and a list for multiple
    URLs. Failed extractions are omitted from list results.

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

### GenAIStrategy

AI-powered content extraction using language models.

```python
from onecrawler.crawler.scraper.genai.executor import GenAIStrategy

strategy = GenAIStrategy(
    provider=genai_settings.provider,
    model_name=genai_settings.model_name,
    max_retries=2,
    api_key=genai_settings.api_key,
    base_url=genai_settings.base_url,
    output_schema=genai_settings.output_schema,
    provider_kwargs=genai_settings.provider_kwargs,
    timeout=genai_settings.timeout,
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
        data = await scraper.run("https://example.com/article")
    
    return data

if __name__ == "__main__":
    import asyncio
    asyncio.run(scrape_heuristic())
```

### GenAI Scraping

```python
from pydantic import BaseModel
from onecrawler import Settings, GenerativeAISettings, Scraper

class Article(BaseModel):
    title: str
    author: str
    content: str
    published_date: str

async def scrape_with_ai():
    settings = Settings(
        scraping_strategy="genai",
        scraping_output_format="json",
        genai=GenerativeAISettings(
            provider="openai",
            model_name="gpt-4o-mini",
            api_key="your-api-key",
            output_schema=Article
        ),
        concurrency=2,
        request_timeout=30
    )
    
    async with Scraper(settings) as scraper:
        data = await scraper.run("https://example.com/article")
    
    return data

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
        results = await scraper.run(urls)
    
    return results
```

!!! tip "Persist failed URLs"
    For large batches, save failed or empty URLs separately. Retrying only failures
    is faster than repeating discovery and scraping the whole batch.

## Configuration

Scraping behavior is controlled through `Settings`:

| Setting | Description | Default |
|---------|-------------|---------|
| `scraping_strategy` | `"heuristic"` or `"genai"` | `"heuristic"` |
| `scraping_output_format` | Output format | `"json"` |
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
        data = await scraper.run("https://example.com/article")

    writter.dump_json(data, "output.json")
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
    for result in results:
        await save_to_database(result)
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
    enable_logging=True,
    logging_level="DEBUG"
)
```

!!! note "Empty content is not always an error"
    Some pages are navigation, search, login, or media-only pages with little
    extractable text. Use URL filters to keep these out of scraping batches.
