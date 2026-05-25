import csv
import json
from pathlib import Path
from typing import Any


def _serialize(obj: Any) -> Any:
    """Convert unsupported objects into serializable Python objects."""

    # Pydantic v2
    if hasattr(obj, "model_dump"):
        return obj.model_dump()

    # Pydantic v1
    if hasattr(obj, "dict"):
        return obj.dict()

    # pathlib.Path
    if isinstance(obj, Path):
        return str(obj)

    # fallback
    return obj


def dump_json(
    data: Any,
    filename: str | Path,
    indent: int = 2,
    ensure_ascii: bool = False,
    encoding: str = "utf-8",
) -> None:
    path = Path(filename)

    with path.open("w", encoding=encoding) as f:
        json.dump(
            data,
            f,
            indent=indent,
            ensure_ascii=ensure_ascii,
            default=_serialize,
        )


def dump_jsonl(
    data: Any,
    filename: str | Path,
    ensure_ascii: bool = False,
    encoding: str = "utf-8",
) -> None:
    path = Path(filename)

    # single object → wrap into list
    if not isinstance(data, list):
        data = [data]

    with path.open("w", encoding=encoding) as f:
        for item in data:
            f.write(
                json.dumps(
                    item,
                    ensure_ascii=ensure_ascii,
                    default=_serialize,
                )
                + "\n"
            )


def dump_txt(
    text: str,
    filename: str | Path,
    encoding: str = "utf-8",
) -> None:
    Path(filename).write_text(text, encoding=encoding)


def dump_csv(
    rows: list[dict],
    filename: str | Path,
    encoding: str = "utf-8",
) -> None:
    if not rows:
        return

    rows = [_serialize(row) for row in rows]

    path = Path(filename)

    with path.open("w", newline="", encoding=encoding) as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


__all__ = [
    "dump_json",
    "dump_jsonl",
    "dump_txt",
    "dump_csv",
]
