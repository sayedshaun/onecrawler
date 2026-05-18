"""
OneCrawler: A unified, AI-powered web crawling and scraping framework.

This package provides a high-level API for:
- Mapping websites using sitemaps and robots.txt (UniversalSiteMap).
- Discovering and classifying links using AI (LinkExtractor).
- Scraping structured data using heuristics or GenAI (Scraper).
- Building automated crawling pipelines (Crawler).
"""

from .crawler import (
    Crawler,
    LinkExtractionEngine,
    LinkExtractor,
    Pipeline,
    RangeCrawler,
    ScheduleCrawler,
    Scraper,
    ScraperEngine,
)
from .crawler.link.classifier import LinkClassifierPipeline
from .crawler.map.sitemap import SiteMap, SitemapStats, UniversalSiteMap
from .settings import *
from .version import get_version

__version__ = get_version()
