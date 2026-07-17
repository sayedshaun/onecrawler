from typing import List
from urllib.parse import urldefrag, urlparse


class LinkSpider:
    """Extracts same-origin, fragment-free links from a loaded page.

    Given a base URL prefix (e.g. ``"https://www.example.com"``), a
    ``LinkSpider`` reads every ``<a href>`` on a Playwright page and returns
    only the links that share that origin, with any ``#fragment`` stripped.
    Cross-origin links (e.g. links to other domains) are discarded.

    Same-origin results are memoized per link string, since the same
    navigation/footer links typically reappear on every page of a crawl.

    Attributes:
        base_prefix (str): The site origin (scheme + host) links must match.
    """

    def __init__(self, base_prefix: str):
        self.base_prefix = base_prefix
        parsed = urlparse(base_prefix)
        self.base_scheme = parsed.scheme
        self.base_netloc = parsed.netloc.lower()
        self._same_origin_cache: dict = {}

    def _same_origin(self, link: str) -> bool:
        cached = self._same_origin_cache.get(link)
        if cached is not None:
            return cached

        parsed = urlparse(link)
        same_origin = (
            parsed.scheme == self.base_scheme
            and parsed.netloc.lower() == self.base_netloc
        )
        self._same_origin_cache[link] = same_origin
        return same_origin

    async def parse(self, page) -> List[str]:
        """Returns all same-origin links found on ``page``, deduplicated of URL
        fragments (but not of each other — callers dedupe as needed)."""
        raw = await page.eval_on_selector_all(
            "a", "els => els.map(e => e.href).filter(Boolean)"
        )
        return [
            urldefrag(link).url
            for link in raw
            if isinstance(link, str) and self._same_origin(link)
        ]
