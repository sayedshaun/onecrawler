import datetime
from typing import Callable, Optional


def by_date(
    start: Optional[str] = None,
    end: Optional[str] = None,
) -> Callable[[dict], bool]:
    """
    Filter items by YYYY-MM-DD date range.
    """

    start_dt = datetime.datetime.strptime(start, "%Y-%m-%d") if start else None
    end_dt = datetime.datetime.strptime(end, "%Y-%m-%d") if end else None

    def _filter(item: dict) -> bool:
        date_str = item.get("filedate") or item.get("date")
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
