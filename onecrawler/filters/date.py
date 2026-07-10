import datetime
from typing import Callable, Optional, Sequence

from .base import CONTENT_DATE_FIELDS, resolve_field


def by_date(
    start: Optional[str] = None,
    end: Optional[str] = None,
    *,
    fields: Sequence[str] = CONTENT_DATE_FIELDS,
) -> Callable[[dict], bool]:
    """Filter items by YYYY-MM-DD date range.

    Reads the first present field in `fields` (default: publication ``date``,
    then ``filedate``). Note ``filedate`` is the extraction/download date, so
    ``date`` is checked first to filter by publication rather than crawl time.
    Items with no parseable date are excluded.

    Args:
        start (Optional[str]): Inclusive lower bound, as ``YYYY-MM-DD``.
            No lower bound if omitted.
        end (Optional[str]): Inclusive upper bound, as ``YYYY-MM-DD``.
            No upper bound if omitted.
        fields (Sequence[str]): Content-dict keys to check, in priority order.

    Returns:
        Callable[[dict], bool]: A predicate accepting items whose resolved
        date falls within ``[start, end]``.
    """

    start_dt = datetime.datetime.strptime(start, "%Y-%m-%d") if start else None
    end_dt = datetime.datetime.strptime(end, "%Y-%m-%d") if end else None

    def _filter(item: dict) -> bool:
        date_str = resolve_field(item, fields, filter_name="by_date")
        if not date_str:
            return False

        try:
            dt = datetime.datetime.strptime(date_str, "%Y-%m-%d")
        except (ValueError, TypeError):
            return False

        if start_dt and dt < start_dt:
            return False
        if end_dt and dt > end_dt:
            return False

        return True

    return _filter
