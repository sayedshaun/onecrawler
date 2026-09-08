from typing import List, Optional
from urllib.parse import urldefrag, urlparse


def origin_of(url: str) -> str:
    """Returns ``url``'s scheme+host, the form a crawl's ``base_prefix`` takes."""
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"


def redirected_origin(base_prefix: str, final_url: str) -> Optional[str]:
    """Returns ``final_url``'s origin when a redirect moved it off ``base_prefix``.

    A seed that redirects — an apex domain sent to its ``www`` host, say — would
    otherwise leave every link on the landing page looking cross-origin, ending the
    crawl after a single page.
    """
    origin = origin_of(final_url)
    if not urlparse(origin).netloc or origin == base_prefix:
        return None
    return origin


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
        self._same_origin_cache: dict = {}
        self.retarget(base_prefix)

    def retarget(self, base_prefix: str) -> None:
        """Re-anchors the spider on ``base_prefix``, e.g. after the seed URL redirected
        to another origin."""
        self.base_prefix = base_prefix
        parsed = urlparse(base_prefix)
        self.base_scheme = parsed.scheme
        self.base_netloc = parsed.netloc.lower()
        self._same_origin_cache.clear()

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
