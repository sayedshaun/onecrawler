import json
import asyncio
import trafilatura
from ..base import BaseStrategy


class HeuristicStrategy(BaseStrategy):
    def __init__(self, output_format: str = "json"):
        self.output_format = output_format

    async def extract(self, url: str):
        html = await asyncio.to_thread(trafilatura.fetch_url, url)
        if not html:
            return None

        extracted = await asyncio.to_thread(
            trafilatura.extract,
            html,
            output_format=self.output_format,
            with_metadata=True,
            fast=True,
            favor_precision=True,
            include_tables=True,
            deduplicate=True,
        )

        if not extracted:
            return None

        if self.output_format == "json":
            try:
                data = json.loads(extracted)
                if not data.get("text") or len(data["text"].strip()) < 200:
                    return None
                return data
            except Exception:
                return None

        return extracted