import math
import re
from collections import Counter
from typing import Callable


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


def by_cosine_similarity(query: str, threshold: float = 0.25) -> Callable[[dict], bool]:
    """
    Compare query text vs document text using cosine similarity.
    """

    query_vec = _vectorize(query)

    def _filter(item: dict) -> bool:
        doc_text = item.get("content") or item.get("title") or item.get("text") or ""

        if not doc_text:
            return False

        doc_vec = _vectorize(doc_text)
        score = _cosine_sim(query_vec, doc_vec)

        return score >= threshold

    return _filter
