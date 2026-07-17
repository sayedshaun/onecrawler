import sys

from tqdm import tqdm


def make_progress_bar(total: int, desc: str, unit: str, show_progress: bool) -> tqdm:
    """Builds a tqdm progress bar with the crawler-wide display conventions.

    Disabled when ``show_progress`` is False or stderr isn't a TTY (e.g. output is
    piped/redirected), matching how every engine gates its own bar.
    """
    return tqdm(
        total=total,
        desc=desc,
        unit=unit,
        dynamic_ncols=True,
        disable=(not show_progress or not sys.stderr.isatty()),
    )
