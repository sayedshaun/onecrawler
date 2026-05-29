from typing import List
from urllib.parse import urlparse, urldefrag


class LinkSpider:
    """A spider responsible for extracting links from a web page.

    Attributes:
        base_prefix (str): The domain prefix to restrict link extraction to.
    """

    def __init__(self, base_prefix: str):
        self.base_prefix = base_prefix
        parsed = urlparse(base_prefix)
        self.base_scheme = parsed.scheme
        self.base_netloc = parsed.netloc.lower()

    def _same_origin(self, link: str) -> bool:
        parsed = urlparse(link)
        return (
            parsed.scheme == self.base_scheme
            and parsed.netloc.lower() == self.base_netloc
        )

    async def parse(self, page) -> List[str]:

        raw = await page.eval_on_selector_all(
            "a", "els => els.map(e => e.href).filter(Boolean)"
        )
        return [
            urldefrag(link).url
            for link in raw
            if isinstance(link, str) and self._same_origin(link)
        ]
