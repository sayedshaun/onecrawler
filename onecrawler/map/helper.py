from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse, urlunparse

SITEMAP_NS = {
    "sm": "http://www.sitemaps.org/schemas/sitemap/0.9",
    "news": "http://www.google.com/schemas/sitemap-news/0.9",
    "image": "http://www.google.com/schemas/sitemap-image/1.1",
    "video": "http://www.google.com/schemas/sitemap-video/1.1",
    "xhtml": "http://www.w3.org/1999/xhtml",
}


COMMON_SITEMAP_PATHS = [
    "/sitemap.xml",  # universal default — most likely to exist
    "/sitemap_index.xml",  # second most common
    "/wp-sitemap.xml",  # WordPress 5.5+ (often not in robots.txt)
    "/sitemap.xml.gz",  # compressed variant
    "/index-sitemap.xml",  # some news CMSes (e.g. somoynews.tv style)
    "/sitemap/sitemap.xml",  # sites that put sitemap in a subdirectory
]


@dataclass
class URLRecord:
    url: str
    source: str
    lastmod: Optional[str] = None
    changefreq: Optional[str] = None
    priority: Optional[str] = None
    discovered_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


def normalize_url(url: str) -> str:
    """Lowercase scheme+host, strip fragment, strip trailing slash."""
    p = urlparse(url.strip())
    normalized = urlunparse(
        (
            p.scheme.lower(),
            p.netloc.lower(),
            p.path.rstrip("/") or "/",
            p.params,
            p.query,
            "",  # drop fragment
        )
    )
    return normalized


def is_same_origin(url: str, base: str) -> bool:
    return urlparse(url).netloc == urlparse(base).netloc


def looks_like_sitemap(url: str) -> bool:
    path = urlparse(url).path.lower()
    return path.endswith(".xml") or "sitemap" in path or path.endswith(".xml.gz")


def is_xml_url(url: str) -> bool:
    """Return True if the URL points to an XML or XML.gz resource."""
    path = urlparse(url).path.lower()
    return path.endswith(".xml") or path.endswith(".xml.gz")
