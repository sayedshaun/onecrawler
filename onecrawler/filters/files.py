from typing import Callable, Iterable

from .base import CONTENT_URL_FIELD, resolve_field

FILE_TYPE_MAP = {
    "pdf": [".pdf"],
    "docx": [".docx"],
    "image": [".png", ".jpg", ".jpeg", ".webp", ".gif"],
    "text": [".txt", ".md"],
}


def by_extension(
    extensions: Iterable[str],
    *,
    field: str = CONTENT_URL_FIELD,
) -> Callable[[dict], bool]:
    """Filter by the file extension of the item's URL (``field``).

    Args:
        extensions (Iterable[str]): Extensions to allow, with or without a
            leading dot (e.g. ``"pdf"`` or ``".pdf"``); matching is case-insensitive.
        field (str): Content-dict key holding the URL to check.

    Returns:
        Callable[[dict], bool]: A predicate accepting items whose URL ends
        with one of ``extensions``.
    """
    allowed = {
        ext.lower() if ext.startswith(".") else f".{ext.lower()}" for ext in extensions
    }

    def _filter(item: dict) -> bool:
        url = resolve_field(item, (field,), filter_name="by_extension")
        if not url:
            return False
        url = url.lower()
        return any(url.endswith(ext) for ext in allowed)

    return _filter


def by_files(
    types: Iterable[str],
    *,
    field: str = CONTENT_URL_FIELD,
) -> Callable[[dict], bool]:
    """Filter by logical file types: pdf, docx, image, etc.

    Args:
        types (Iterable[str]): Logical type names from ``FILE_TYPE_MAP``
            (``"pdf"``, ``"docx"``, ``"image"``, ``"text"``), or a raw
            extension (with or without a leading dot) for anything else.
        field (str): Content-dict key holding the URL to check.

    Returns:
        Callable[[dict], bool]: A predicate accepting items whose URL matches
        one of the resolved extensions.
    """
    allowed_exts = set()

    for t in types:
        t = t.lower()
        if t in FILE_TYPE_MAP:
            allowed_exts.update(FILE_TYPE_MAP[t])
        else:
            allowed_exts.add(f".{t}")

    return by_extension(allowed_exts, field=field)
