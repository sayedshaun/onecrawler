"""
OneCrawler Example Usage

This file demonstrates various usage patterns for the PipelineEngine class,
including basic crawling, date filtering, proxy configuration, and human behavior simulation.
"""

import asyncio
import json
import logging
from datetime import date

from dateutil.relativedelta import relativedelta

from onecrawler import (
    CrawlerSettings,
    HumanBehaviorSettings,
    PipelineEngine,
    ProxySettings,
)


async def basic_crawling_example():
    """Basic PipelineEngine usage for simple web crawling."""
    print("=== Basic Crawling Example ===")

    settings = CrawlerSettings(
        link_extraction_limit=10,
        concurrency=3,
        include_link_patterns=["/business/*"],
        enable_logging=True,
        logging_level="INFO",
    )

    logging.basicConfig(
        level=settings.logging_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    async with PipelineEngine(settings) as pipeline:
        results = await pipeline.run("https://www.prothomalo.com/business")

    print(f"Found {len(results)} results")
    return results


async def date_filtered_crawling_example():
    """Example with date-based content filtering."""
    print("\n=== Date-Filtered Crawling Example ===")

    # Set date range for content filtering
    end_date = date.today()
    start_date = end_date - relativedelta(months=3)

    settings = CrawlerSettings(
        link_extraction_limit=15,
        concurrency=5,
        include_link_patterns=["/business/*"],
        enable_logging=True,
        logging_level="INFO",
    )

    async with PipelineEngine(
        settings=settings,
        start_date=start_date.strftime("%Y-%m-%d"),
        end_date=end_date.strftime("%Y-%m-%d"),
    ) as pipeline:
        results = await pipeline.run("https://www.prothomalo.com/business")

    print(f"Found {len(results)} results from {start_date} to {end_date}")
    return results


async def proxy_configured_crawling_example():
    """Example with proxy configuration for production use."""
    print("\n=== Proxy-Configured Crawling Example ===")

    settings = CrawlerSettings(
        link_extraction_limit=20,
        concurrency=4,
        include_link_patterns=["/technology/*"],
        # IMPORTANT: Proxy configuration required for production
        proxies=[
            ProxySettings(server="http://proxy1.example.com:8080"),
            ProxySettings(server="http://proxy2.example.com:8080"),
        ],
        proxy_rotation="round_robin",
        enable_logging=True,
        logging_level="INFO",
    )

    async with PipelineEngine(settings) as pipeline:
        results = await pipeline.run("https://example-tech-news.com")

    print(f"Found {len(results)} results using proxy pool")
    return results


async def human_behavior_simulation_example():
    """Example with human behavior simulation for JavaScript-heavy sites."""
    print("\n=== Human Behavior Simulation Example ===")

    settings = CrawlerSettings(
        link_extraction_limit=12,
        concurrency=2,  # Lower concurrency with human behaviors
        include_link_patterns=["/news/*"],
        enable_human_behaviors=True,
        human_behavior_settings=HumanBehaviorSettings(
            min_delay=1.0,
            max_delay=3.0,
            max_scrolls=3,
            min_mouse_moves=2,
            max_mouse_moves=4,
            mouse_width=100,
            mouse_height=100,
            min_mouse_steps=5,
            max_mouse_steps=10,
            min_mouse_sleep=0.1,
            max_mouse_sleep=0.3,
        ),
        enable_logging=True,
        logging_level="INFO",
    )

    async with PipelineEngine(settings) as pipeline:
        results = await pipeline.run("https://example-javascript-site.com")

    print(f"Found {len(results)} results with human behavior simulation")
    return results


async def manual_lifecycle_example():
    """Example showing manual lifecycle management."""
    print("\n=== Manual Lifecycle Management Example ===")

    settings = CrawlerSettings(
        link_extraction_limit=8,
        concurrency=3,
        enable_logging=True,
        logging_level="INFO",
    )

    engine = PipelineEngine(settings)

    try:
        await engine.start()
        results = await engine.run("https://example-blog.com")
        print(f"Found {len(results)} results with manual lifecycle")
        return results
    finally:
        await engine.close()


async def comprehensive_example():
    """Comprehensive example combining multiple features."""
    print("\n=== Comprehensive Example ===")

    # Date range for filtering
    end_date = date.today()
    start_date = end_date - relativedelta(months=1)

    settings = CrawlerSettings(
        link_extraction_limit=25,
        concurrency=4,
        include_link_patterns=["/articles/*", "/blog/*"],
        exclude_link_patterns=["/admin/*", "/profile/*"],
        # Production proxy configuration
        proxies=[
            ProxySettings(server="http://proxy1.example.com:8080"),
            ProxySettings(
                server="http://proxy2.example.com:8080",
                username="user",
                password="pass",
            ),
        ],
        proxy_rotation="round_robin",
        # Optional human behaviors for dynamic content
        enable_human_behaviors=True,
        human_behavior_settings=HumanBehaviorSettings(
            min_delay=0.5,
            max_delay=2.0,
            max_scrolls=2,
        ),
        enable_logging=True,
        logging_level="INFO",
    )

    async with PipelineEngine(
        settings=settings,
        start_date=start_date.strftime("%Y-%m-%d"),
        end_date=end_date.strftime("%Y-%m-%d"),
    ) as pipeline:
        results = await pipeline.run("https://example-news-site.com")

    print(f"Found {len(results)} results with comprehensive configuration")

    # Save results to file
    with open("comprehensive_output.json", "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print("Results saved to comprehensive_output.json")
    return results


async def main():
    """Run all examples."""
    print("OneCrawler PipelineEngine Examples")
    print("=" * 50)

    try:
        # Run examples (comment out any you don't want to execute)
        await basic_crawling_example()
        await date_filtered_crawling_example()
        # await proxy_configured_crawling_example()  # Requires actual proxies
        # await human_behavior_simulation_example()  # Requires JS-heavy site
        await manual_lifecycle_example()
        # await comprehensive_example()  # Requires actual proxies and site

        print("\n" + "=" * 50)
        print("All examples completed successfully!")

    except Exception as e:
        print(f"Error running examples: {e}")
        logging.exception("Detailed error information:")


if __name__ == "__main__":
    asyncio.run(main())
