import asyncio
import warnings
from urllib.parse import unquote
from typing import List
from functools import lru_cache

CLASSIFIER_AVAILABLE = True
try:
    import torch
    from transformers import (
        AutoModelForSequenceClassification,
        AutoTokenizer,
        pipeline,
    )
except ImportError:
    CLASSIFIER_AVAILABLE = False


if CLASSIFIER_AVAILABLE:
    repo_id = "SayedShaun/distilbert-link-type-classifier"

    torch.set_grad_enabled(False)

    model = AutoModelForSequenceClassification.from_pretrained(repo_id)
    tokenizer = AutoTokenizer.from_pretrained(repo_id)

    def get_classifier(device: str = "cpu"):
        device_id = 0 if device == "cuda" else -1
        return pipeline(
            "text-classification",
            model=model,
            tokenizer=tokenizer,
            device=device_id,
        )

    clf = get_classifier("cuda" if torch.cuda.is_available() else "cpu")


def cheap_filter(url: str) -> bool:
    if not url:
        return False

    bad_patterns = (
        "javascript:",
        "mailto:",
        "tel:",
        "#",
    )

    return not any(p in url for p in bad_patterns)


@lru_cache(maxsize=10000)
def _cached_single_prediction(url: str) -> str:
    result = clf(url, truncation=True, max_length=128)[0]
    return result["label"]


class LinkClassifierPipeline:
    def __init__(
        self,
        confidence_threshold: float = 0.8,
    ):
        self.threshold = confidence_threshold

        if not CLASSIFIER_AVAILABLE:
            warnings.warn(
                "Classifier enabled but transformers/torch not installed. Disabling."
            )
            self.available = False
        else:
            self.available = True

    async def classify_batch(self, urls: List[str]) -> List[bool]:
        if not self.available:
            return [True] * len(urls)

        filtered_urls = []
        index_map = []

        for i, url in enumerate(urls):
            if cheap_filter(url):
                filtered_urls.append(unquote(url))
                index_map.append(i)

        results = [False] * len(urls)

        if not filtered_urls:
            return results

        try:
            predictions = await asyncio.to_thread(
                lambda: clf(filtered_urls, truncation=True, max_length=128)
            )
        except Exception:
            return [True] * len(urls)

        for idx, pred in zip(index_map, predictions):
            label = pred["label"]
            score = pred["score"]

            if label == "content" and score >= self.threshold:
                results[idx] = True
            else:
                results[idx] = False

        return results

    async def is_valid(self, url: str) -> bool:
        if not self.available:
            return True

        if not cheap_filter(url):
            return False

        try:
            label = await asyncio.to_thread(_cached_single_prediction, unquote(url))
            return label != "section"
        except Exception:
            return True
