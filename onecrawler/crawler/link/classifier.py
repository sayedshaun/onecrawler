import asyncio
from urllib.parse import unquote
import warnings
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

    model = AutoModelForSequenceClassification.from_pretrained(
        repo_id,
        id2label={0: "section", 1: "content"},
        label2id={"section": 0, "content": 1},
    )

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


@lru_cache(maxsize=10000)
def classify_link_type(link: str) -> str:
    if not CLASSIFIER_AVAILABLE:
        return "content"

    try:
        with torch.no_grad():
            result = clf(link, truncation=True, max_length=128)[0]
        return result["label"]

    except Exception:
        return "section"


class LinkClassifierPipeline:
    def __init__(self, enabled: bool):
        self.enabled = enabled

        if self.enabled:
            from .classifier import classify_link_type, CLASSIFIER_AVAILABLE

            self.model = classify_link_type
            self.available = CLASSIFIER_AVAILABLE

            if not self.available:
                warnings.warn(
                    "Link classifier enabled but dependencies are missing (transformers/torch). "
                    "Disabling classifier."
                )
        else:
            self.model = None
            self.available = False

    async def is_valid(self, url: str) -> bool:
        if not self.enabled or not self.available:
            return True

        result = await asyncio.to_thread(self.model, unquote(url))
        return result != "section"
