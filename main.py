from onecrawler.config.settings import CrawlerSettings
from onecrawler.crawler.link.engine import LinkExtractorEngine
from onecrawler.crawler.content.engine import CrawlerEngine


async def main():
    config = CrawlerSettings(
        url_extraction_strategy="shallow",
        url_extraction_limit=2,
        concurrency=10,
        content_scraping_strategy="heuristic",
    )
    async with LinkExtractorEngine(config) as link_engine:
        urls = await link_engine.run("https://www.prothomalo.com/")
    
    async with CrawlerEngine(config) as content_engine:
        data = await content_engine.run(urls)

    print(data)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
