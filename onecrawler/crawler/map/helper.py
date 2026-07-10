from dataclasses import dataclass, field
from datetime import datetime, timezone
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
    "/sitemap.xml",
    "/sitemap_index.xml",
    "/wp-sitemap.xml",
    "/sitemap.xml.gz",
    "/index-sitemap.xml",
    "/sitemap/sitemap.xml",
]


@dataclass
class URLRecord:
    """Represents a URL discovered from a sitemap or link extraction.

    Attributes:
        url (str): The absolute URL.
        source (str): The source where the URL was found (e.g., sitemap path).
        lastmod (Optional[str]): The last modification date from the sitemap.
        changefreq (Optional[str]): How frequently the page is likely to change.
        priority (Optional[str]): The priority of this URL relative to others.
        discovered_at (str): ISO timestamp of when the URL was discovered.
    """

    url: str
    source: str
    lastmod: Optional[str] = None
    changefreq: Optional[str] = None
    priority: Optional[str] = None
    discovered_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


def normalize_url(url: str) -> str:
    """Normalizes a URL by lowercasing scheme/host and stripping fragments.

    Args:
        url (str): The URL to normalize.

    Returns:
        str: The normalized URL.
    """
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
    """Checks if two URLs have the same network location (netloc).

    Args:
        url (str): The candidate URL.
        base (str): The base URL to compare against.

    Returns:
        bool: True if they share the same origin, False otherwise.
    """
    return urlparse(url).netloc.lower() == urlparse(base).netloc.lower()


def looks_like_sitemap(url: str) -> bool:
    """Heuristically determines if a URL refers to a sitemap.

    Args:
        url (str): The URL to check.

    Returns:
        bool: True if the URL likely points to a sitemap, False otherwise.
    """
    path = urlparse(url).path.lower()
    return path.endswith(".xml") or "sitemap" in path or path.endswith(".xml.gz")


def is_xml_url(url: str) -> bool:
    """Checks if a URL points to an XML or compressed XML resource.

    Args:
        url (str): The URL to check.

    Returns:
        bool: True if the URL ends in .xml or .xml.gz, False otherwise.
    """
    path = urlparse(url).path.lower()
    return path.endswith(".xml") or path.endswith(".xml.gz")
