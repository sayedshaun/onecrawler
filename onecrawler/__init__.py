"""
OneCrawler: A unified, AI-powered web crawling and scraping framework.

This package provides a high-level API for:
- Mapping websites using sitemaps and robots.txt (UniversalSiteMap).
- Discovering and classifying links using AI (LinkExtractionEngine).
- Scraping structured data using heuristics or GenAI (ScraperEngine).
- Building automated crawling pipelines (Pipeline).
"""

from .crawler.link.classifier import LinkClassifierPipeline
from .crawler.link.engine import LinkExtractionEngine
from .crawler.map.sitemap import SiteMap, SitemapStats, UniversalSiteMap
from .crawler.pipeline import Pipeline
from .crawler.scraper.engine import ScraperEngine
from .settings import *
from .version import get_version

__version__ = get_version()
