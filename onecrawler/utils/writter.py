import csv
import json
from datetime import date, datetime
from pathlib import Path
from typing import Any


def _serialize(obj: Any) -> Any:
    """Convert unsupported objects into serializable Python objects."""

    if hasattr(obj, "model_dump"):
        return obj.model_dump()

    if hasattr(obj, "dict"):
        return obj.dict()

    if isinstance(obj, Path):
        return str(obj)

    if isinstance(obj, (date, datetime)):
        return obj.isoformat()

    if isinstance(obj, (set, frozenset)):
        return list(obj)

    # json.dump's `default` must raise (not return obj unchanged) — returning
    # the same unserializable object back makes the encoder think it found a
    # circular reference and raise a confusing ValueError instead.
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


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

    rows = [row if isinstance(row, dict) else _serialize(row) for row in rows]

    fieldnames: list = []
    seen = set()
    for row in rows:
        for key in row.keys():
            if key not in seen:
                seen.add(key)
                fieldnames.append(key)

    path = Path(filename)

    with path.open("w", newline="", encoding=encoding) as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, restval="")
        writer.writeheader()
        writer.writerows(rows)


__all__ = [
    "dump_json",
    "dump_jsonl",
    "dump_txt",
    "dump_csv",
]
