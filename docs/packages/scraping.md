---
title: Scraping Engine
---

# Scraping Engine Package

The `onecrawler.scraper` package provides content extraction engines for scraping web pages with both heuristic and AI-powered approaches.

## Classes

### ScraperEngine

Main scraping engine that supports both heuristic and GenAI content extraction strategies.

```python
from onecrawler import CrawlerSettings, ScraperEngine

async with ScraperEngine(settings) as scraper:
    data = await scraper.run("https://example.com/article")
```

#### Parameters

- `settings` (`CrawlerSettings`): Configuration for scraping behavior

#### Methods

- `run(url: str) -> Any`: Extract content from the given URL
- `run(urls: List[str]) -> List[Any]`: Extract content from multiple URLs

#### Strategies

- **Heuristic**: Fast, rule-based extraction using trafilatura
- **GenAI**: AI-powered extraction with structured output

### HeuristicStrategy

Rule-based content extraction using the trafilatura library.

```python
from onecrawler.crawler.scraper.heuristic.script import HeuristicStrategy

strategy = HeuristicStrategy(settings, browser=browser)
content = await strategy.extract(url)
```

#### Features

- **Fast extraction**: No model calls, deterministic results
- **Multiple formats**: HTML, text, metadata extraction
- **Language detection**: Automatic language identification
- **Content cleaning**: Removes boilerplate and navigation

### GenAIStrategy

AI-powered content extraction using language models.

```python
from onecrawler.crawler.scraper.genai.executor import GenAIStrategy

strategy = GenAIStrategy(settings=genai_settings)
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
import asyncio
from onecrawler import CrawlerSettings, ScraperEngine

async def scrape_heuristic():
    settings = CrawlerSettings(
        scraping_strategy="heuristic",
        scraping_output_format="json",
        concurrency=10,
        request_timeout=15
    )
    
    async with ScraperEngine(settings) as scraper:
        data = await scraper.run("https://example.com/article")
    
    return data

if __name__ == "__main__":
    asyncio.run(scrape_heuristic())
```

### GenAI Scraping

```python
import asyncio
from pydantic import BaseModel
from onecrawler import CrawlerSettings, GenerativeAISettings, ScraperEngine

class Article(BaseModel):
    title: str
    author: str
    content: str
    published_date: str

async def scrape_with_ai():
    settings = CrawlerSettings(
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
    
    async with ScraperEngine(settings) as scraper:
        data = await scraper.run("https://example.com/article")
    
    return data

if __name__ == "__main__":
    asyncio.run(scrape_with_ai())
```

### Batch Scraping

```python
async def scrape_multiple():
    urls = [
        "https://example.com/article1",
        "https://example.com/article2",
        "https://example.com/article3"
    ]
    
    settings = CrawlerSettings(
        scraping_strategy="heuristic",
        concurrency=5,
        max_retries=3
    )
    
    async with ScraperEngine(settings) as scraper:
        results = await scraper.run(urls)
    
    return results
```

## Configuration

Scraping behavior is controlled through `CrawlerSettings`:

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
- **HTML**: Original HTML structure
- **Text**: Plain text content

### GenAI Strategy

- **JSON**: Structured output matching Pydantic schema
- **Custom formats**: Based on your schema definition

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
import json
from onecrawler import CrawlerSettings, ScraperEngine

async def scrape_and_save():
    settings = CrawlerSettings(scraping_strategy="heuristic")
    
    async with ScraperEngine(settings) as scraper:
        data = await scraper.run("https://example.com/article")
    
    with open("output.json", "w") as f:
        json.dump(data, f, indent=2)
```

### Database Integration

```python
import asyncio
from onecrawler import CrawlerSettings, ScraperEngine

async def scrape_to_database():
    settings = CrawlerSettings(scraping_strategy="heuristic")
    
    async with ScraperEngine(settings) as scraper:
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
settings = CrawlerSettings(
    enable_logging=True,
    logging_level="DEBUG"
)
```
