from typing import Callable, Iterable


def by_keywords(keywords: Iterable[str]) -> Callable[[dict], bool]:
    """
    Keep items whose content contains ANY keyword.
    """

    keywords = [k.lower() for k in keywords]

    def _filter(item: dict) -> bool:
        text = (item.get("text") or "").lower()
        return any(k in text for k in keywords)

    return _filter
