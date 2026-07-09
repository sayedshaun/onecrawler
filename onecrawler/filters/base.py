import logging
from typing import Callable, List, Optional, Sequence

logger = logging.getLogger(__name__)

# The canonical keys onecrawler's built-in content strategies emit and that the
# built-in filters read. The heuristic (trafilatura) strategy produces `text`,
# `title`, `date`, `filedate`, `url`; string outputs (markdown/xml) are wrapped
# as {"text": ..., "url": ...}. GenAIStrategy emits a user-defined schema, so
# each filter accepts a `field`/`fields` override to point at the right key.
CONTENT_TEXT_FIELDS = ("text", "content", "title")
CONTENT_DATE_FIELDS = ("date", "filedate")
CONTENT_URL_FIELD = "url"


def resolve_field(
    item: dict, fields: Sequence[str], *, filter_name: str
) -> Optional[str]:
    """Returns the first truthy value among `fields`, or None.

    Logs at debug level when none of the expected fields are present, so a
    filter that silently drops every item (e.g. a date filter run against a
    content format that carries no date) is diagnosable rather than mysterious.
    """
    for field in fields:
        value = item.get(field)
        if value:
            return value
    logger.debug(
        "%s: none of the expected fields %s found in item (available keys: %s)",
        filter_name,
        tuple(fields),
        sorted(item.keys()),
    )
    return None


class FilterChain:
    """Composable filter system (AND / OR / NOT)."""

    def __init__(self, *filters: Callable[[dict], bool], mode: str = "AND"):
        self.filters: List[Callable[[dict], bool]] = list(filters)
        self.mode = mode.upper()

    def add(self, f: Callable[[dict], bool]):
        self.filters.append(f)
        return self

    def __call__(self, item: dict) -> bool:
        if not self.filters:
            return True

        if self.mode == "AND":
            return all(f(item) for f in self.filters)

        if self.mode == "OR":
            return any(f(item) for f in self.filters)

        raise ValueError(f"Unknown mode: {self.mode}")
