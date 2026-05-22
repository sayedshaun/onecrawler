from typing import Callable, Iterable

# Mapping logical file types → extensions
FILE_TYPE_MAP = {
    "pdf": [".pdf"],
    "docx": [".docx"],
    "image": [".png", ".jpg", ".jpeg", ".webp", ".gif"],
    "text": [".txt", ".md"],
}


def by_extension(extensions: Iterable[str]) -> Callable[[dict], bool]:
    """
    Filter by URL file extension.
    """

    allowed = {
        ext.lower() if ext.startswith(".") else f".{ext.lower()}" for ext in extensions
    }

    def _filter(item: dict) -> bool:
        url = (item.get("url") or "").lower()
        return any(url.endswith(ext) for ext in allowed)

    return _filter


def by_files(types: Iterable[str]) -> Callable[[dict], bool]:
    """
    Filter by logical file types: pdf, docx, image, etc.
    """

    allowed_exts = set()

    for t in types:
        t = t.lower()
        if t in FILE_TYPE_MAP:
            allowed_exts.update(FILE_TYPE_MAP[t])
        else:
            # treat unknown type as extension
            allowed_exts.add(f".{t}")

    return by_extension(allowed_exts)
