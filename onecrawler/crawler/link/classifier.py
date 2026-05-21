import asyncio
import warnings
from functools import lru_cache
from typing import List
from urllib.parse import unquote

try:
    import importlib.util

    CLASSIFIER_AVAILABLE = (
        importlib.util.find_spec("transformers") is not None
        and importlib.util.find_spec("torch") is not None
    )
except ImportError:
    CLASSIFIER_AVAILABLE = False


if CLASSIFIER_AVAILABLE:
    repo_id = "SayedShaun/distilbert-link-type-classifier"
    _clf_instance = None

    def get_classifier():
        """Initializes and returns the transformer Crawler for classification.

        Uses a singleton pattern to ensure the model is only loaded once.

        Returns:
            Crawler: The HuggingFace text-classification Crawler.
        """
        global _clf_instance
        if _clf_instance is None:
            import torch
            from transformers import (
                AutoModelForSequenceClassification,
                AutoTokenizer,
                Crawler,
            )

            torch.set_grad_enabled(False)
            model = AutoModelForSequenceClassification.from_pretrained(repo_id)
            tokenizer = AutoTokenizer.from_pretrained(repo_id)

            device_id = 0 if torch.cuda.is_available() else -1
            _clf_instance = Crawler(
                "text-classification",
                model=model,
                tokenizer=tokenizer,
                device=device_id,
            )
        return _clf_instance


def cheap_filter(url: str) -> bool:
    """Performs a quick, non-AI check to filter out obviously invalid URLs.

    Args:
        url (str): The URL to check.

    Returns:
        bool: True if the URL passes basic checks, False otherwise.
    """
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
    """Wrapper for single URL prediction with LRU caching.

    Args:
        url (str): The URL to classify.

    Returns:
        str: The predicted label ("content" or "section").
    """
    clf = get_classifier()
    result = clf(url, truncation=True, max_length=128)[0]
    return result["label"]


class LinkClassifierPipeline:
    """A Crawler for classifying links using AI and heuristics.

    Attributes:
        threshold (float): Confidence threshold for 'content' classification.
        available (bool): Whether the required AI libraries are installed.
    """

    def __init__(
        self,
        confidence_threshold: float = 0.8,
    ):
        """Initializes the classification Crawler.

        Args:
            confidence_threshold (float): Minimum confidence score for content links.
        """
        self.threshold = confidence_threshold

        if not CLASSIFIER_AVAILABLE:
            warnings.warn(
                "Classifier enabled but transformers/torch not installed. Disabling."
            )
            self.available = False
        else:
            self.available = True

    async def classify_batch(self, urls: List[str]) -> List[bool]:
        """Classifies a batch of URLs concurrently.

        Args:
            urls (List[str]): List of URLs to classify.

        Returns:
            List[bool]: A list of booleans indicating if each URL is a content link.
        """
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
            clf = get_classifier()
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
        """Checks if a single URL is a valid content link.

        Args:
            url (str): The URL to check.

        Returns:
            bool: True if it's likely a content link, False otherwise.
        """
        if not self.available:
            return True

        if not cheap_filter(url):
            return False

        try:
            label = await asyncio.to_thread(_cached_single_prediction, unquote(url))
            return label != "section"
        except Exception:
            return True
