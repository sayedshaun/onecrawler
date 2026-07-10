from typing import Any, Optional, Type, TypeVar

import httpx
from pydantic import BaseModel

from .base import BaseLLM

T = TypeVar("T", bound=BaseModel)


class GeminiLLM(BaseLLM):
    def __init__(
        self,
        api_key: str,
        model: str = "gemini-2.5-pro",
        base_url: str = "https://generativelanguage.googleapis.com/v1beta",
        timeout: float = 300.0,
        **generation_config: Any,
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.client = httpx.AsyncClient(
            timeout=timeout,
            headers={"x-goog-api-key": api_key},
        )

        self.generation_config = generation_config

    def _url(self) -> str:
        return f"{self.base_url}/models/{self.model}:generateContent"

    async def generate(self, prompt: str, schema: Optional[Type[T]] = None) -> T | str:
        payload: dict[str, Any] = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": prompt,
                        }
                    ]
                }
            ]
        }

        generation_config = dict(self.generation_config)

        if schema:
            generation_config["responseMimeType"] = "application/json"
            generation_config["responseSchema"] = schema.model_json_schema()

        if generation_config:
            payload["generationConfig"] = generation_config

        response = await self.client.post(
            self._url(),
            json=payload,
        )

        response.raise_for_status()
        data = response.json()
        content = data["candidates"][0]["content"]["parts"][0]["text"]

        if schema is None:
            return content

        return schema.model_validate_json(content)

    async def close(self) -> None:
        await self.client.aclose()
