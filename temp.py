import asyncio
from onecrawler.crawler.scraper.core import base_scraper

async def main():
    url = "https://www.bbc.com/news/articles/cqxlnrqjvzyo"
    result = await base_scraper(url, output_format="json")
    
    import json
    with open("extracted_content.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    asyncio.run(main())