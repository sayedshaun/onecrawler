from typing import Any, Optional, Type, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from .base import BaseLLM

T = TypeVar("T", bound=BaseModel)


class OllamaLLM(BaseLLM):
    def __init__(
        self,
        model: str,
        base_url: str = "http://localhost:11434",
        timeout: float = 300.0,
        think: bool = False,
        **options: Any,
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.client = httpx.AsyncClient(timeout=timeout)

        # Thinking models (qwen3, deepseek-r1, ...) return an EMPTY response for
        # structured output (format=schema) when thinking is on, and emit a huge
        # reasoning trace on free-form calls. Both break this pipeline, so we
        # disable thinking by default; pass provider_kwargs={"think": True} to
        # re-enable it. Non-thinking models accept the flag harmlessly.
        self.think = think
        self.options = options

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    async def generate(self, prompt: str, schema: Optional[Type[T]] = None) -> T | str:
        payload: dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "think": self.think,
        }

        if self.options:
            payload["options"] = self.options

        if schema:
            payload["format"] = schema.model_json_schema()

        response = await self.client.post(
            self._url("/api/generate"),
            json=payload,
        )

        response.raise_for_status()

        data = response.json()
        content = data["response"]

        if schema is None:
            return content

        try:
            return schema.model_validate_json(content)
        except ValidationError as exc:
            done_reason = data.get("done_reason", "unknown")
            preview = content[:500].replace("\n", "\\n")
            raise RuntimeError(
                "Ollama returned invalid structured JSON "
                f"(done_reason={done_reason}, response_preview={preview!r})"
            ) from exc

    async def close(self) -> None:
        await self.client.aclose()
