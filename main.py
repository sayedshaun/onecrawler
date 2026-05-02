from onecrawler import CrawlerSettings, LinkExtractionEngine, ScraperEngine
import logging


async def main():
    config = CrawlerSettings(
        link_extraction_strategy="deep",
        link_extraction_limit=5,
        include_link_patterns=["*/sport/*"],
        link_classification=True,
        concurrency=5,
        scraping_strategy="heuristic",
        scraping_output_format="json",
        logging=True,
        logging_level="INFO"
    )

    logger = logging.getLogger(__name__)
    logger.info("Starting crawler application")

    async with LinkExtractionEngine(config) as link_engine:
        links = await link_engine.run("https://www.bbc.com/sport")

    print(f"Found {len(links)} links:")
    
    async with ScraperEngine(config) as content_engine:
        data = await content_engine.run(links)

    import json
    with open("output.json", "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
