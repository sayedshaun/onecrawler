from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class SitemapSettings:
    """Configuration for sitemap discovery and parsing.

    Attributes:
        follow_index (bool): Whether to follow sitemap index files.
        html_fallback (bool): Whether to fallback to HTML parsing if sitemap is missing.
        max_depth (int): Maximum depth for sitemap/link discovery.
        max_pages (int): Maximum number of pages to discover via sitemaps.
        start_date (Optional[date]): Filter URLs with lastmod on or after this date.
        end_date (Optional[date]): Filter URLs with lastmod on or before this date.
        strict_date_filter (bool): Whether to discard URLs where lastmod cannot be determined.
        user_agent (str): User agent specifically for sitemap fetching.
        respect_robots (bool): Whether to respect robots.txt.
        deduplicate (bool): Whether to deduplicate URLs during discovery.
    """

    follow_index: bool = True
    html_fallback: bool = True
    max_depth: int = 3
    max_pages: int = 500
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    strict_date_filter: bool = False
    user_agent: str = (
        "Mozilla/5.0 (compatible; UniversalURLFetcher/1.0; "
        "+https://github.com/sayedshaun/onecrawler)"
    )
    respect_robots: bool = True
    deduplicate: bool = True
