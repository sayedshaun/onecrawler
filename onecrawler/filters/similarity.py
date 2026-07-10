import math
import re
from collections import Counter
from typing import Callable, Sequence

from .base import CONTENT_TEXT_FIELDS, resolve_field


def _tokenize(text: str):
    return re.findall(r"[a-zA-Z0-9]+", text.lower())


def _vectorize(text: str):
    return Counter(_tokenize(text))


def _cosine_sim(a: Counter, b: Counter) -> float:
    if not a or not b:
        return 0.0

    dot = sum(a[t] * b.get(t, 0) for t in a)

    mag_a = math.sqrt(sum(v * v for v in a.values()))
    mag_b = math.sqrt(sum(v * v for v in b.values()))

    if mag_a == 0 or mag_b == 0:
        return 0.0

    return dot / (mag_a * mag_b)


def by_cosine_similarity(
    query: str,
    threshold: float = 0.25,
    *,
    fields: Sequence[str] = CONTENT_TEXT_FIELDS,
) -> Callable[[dict], bool]:
    """Compare query text vs document text using cosine similarity.

    Scores against the first present field in `fields` (default: the body
    ``text``, then ``content``, then ``title``) so the full document is
    compared rather than a short title when both exist.

    Args:
        query (str): Text to compare each item's content against.
        threshold (float): Minimum cosine similarity score (0-1) required to
            pass.
        fields (Sequence[str]): Content-dict keys to check, in priority order.

    Returns:
        Callable[[dict], bool]: A predicate accepting items scoring at least
        ``threshold`` against ``query``.
    """

    query_vec = _vectorize(query)

    def _filter(item: dict) -> bool:
        doc_text = resolve_field(item, fields, filter_name="by_cosine_similarity")
        if not doc_text:
            return False

        doc_vec = _vectorize(doc_text)
        score = _cosine_sim(query_vec, doc_vec)

        return score >= threshold

    return _filter
