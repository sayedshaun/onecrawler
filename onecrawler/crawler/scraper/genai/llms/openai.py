from typing import Any, Optional, Type, TypeVar

import httpx
from pydantic import BaseModel

from .base import BaseLLM

T = TypeVar("T", bound=BaseModel)


class OpenAILLM(BaseLLM):
    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        base_url: str = "https://api.openai.com/v1",
        timeout: float = 300.0,
        **model_kwargs: Any,
    ) -> None:
        self.model = model
        self.model_kwargs = model_kwargs

        self.client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            timeout=timeout,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )

    async def generate(self, prompt: str, schema: Optional[Type[T]] = None) -> T | str:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            **self.model_kwargs,
        }

        if schema:
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": schema.__name__,
                    "strict": True,
                    "schema": schema.model_json_schema(),
                },
            }

        response = await self.client.post(
            "/chat/completions",
            json=payload,
        )

        response.raise_for_status()

        data = response.json()

        choices = data.get("choices", [])
        if not choices:
            raise RuntimeError(f"OpenAI returned no choices: {data}")

        message = choices[0]["message"]

        refusal = message.get("refusal")
        if refusal:
            raise RuntimeError(refusal)

        content = message.get("content")
        if not content:
            raise RuntimeError(f"OpenAI returned empty content: {data}")

        if schema is None:
            return content

        return schema.model_validate_json(content)

    async def close(self) -> None:
        await self.client.aclose()
