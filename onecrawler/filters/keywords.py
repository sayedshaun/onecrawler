from typing import Callable, Iterable

from .base import resolve_field


def by_keywords(
    keywords: Iterable[str],
    *,
    field: str = "text",
) -> Callable[[dict], bool]:
    """Keep items whose content contains ANY keyword (case-insensitive).

    Reads the item's ``field`` (default ``text``); items missing that field
    are dropped.

    Args:
        keywords (Iterable[str]): Keywords to match; matching is case-insensitive.
        field (str): Content-dict key to search.

    Returns:
        Callable[[dict], bool]: A predicate accepting items containing at
        least one keyword.
    """

    keywords = [k.lower() for k in keywords]

    def _filter(item: dict) -> bool:
        text = resolve_field(item, (field,), filter_name="by_keywords")
        if not text:
            return False
        text = text.lower()
        return any(k in text for k in keywords)

    return _filter
