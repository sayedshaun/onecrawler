from __future__ import annotations

from typing import Any, Optional, Type

from pydantic import BaseModel

from ....settings.genai import GenAIProvider
from .llms import GeminiLLM, OllamaLLM, OpenAILLM
from .llms.base import BaseLLM


class ModelManager:
    """Provider-agnostic LLM factory + runtime wrapper.

    - Keeps provider isolation
    - Prevents invalid kwargs leaking across providers
    - Supports structured outputs via Pydantic
    """

    def __init__(
        self,
        schema: Optional[Type[BaseModel]],
        model_provider: str,
        model_name: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        provider_kwargs: Optional[dict[str, Any]] = None,
        timeout: Optional[float] = None,
        think: bool = False,
        strict: bool = True,
    ) -> None:
        self.schema = schema
        self.model_provider = model_provider.lower()
        self.model_name = model_name
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = timeout
        self.think = think
        self.strict = strict

        self.provider_kwargs = provider_kwargs or {}

        self.model: BaseLLM = self._build_model()

    def _build_model(self) -> BaseLLM:
        provider = self.model_provider

        if provider == GenAIProvider.OLLAMA:
            return OllamaLLM(
                model=self.model_name,
                base_url=self.base_url or "http://localhost:11434",
                think=self.think,
                **self._timeout_kwargs(),
                **self._filter_kwargs("ollama"),
            )

        if provider in {"gemini", GenAIProvider.GOOGLE}:
            if not self.api_key:
                raise ValueError("api_key is required for Gemini")

            return GeminiLLM(
                api_key=self.api_key,
                model=self.model_name,
                base_url=(
                    self.base_url or "https://generativelanguage.googleapis.com/v1beta"
                ),
                **self._timeout_kwargs(),
                **self._filter_kwargs("gemini"),
            )

        if provider == GenAIProvider.OPENAI:
            # A custom base_url means an OpenAI-compatible server (llama.cpp,
            # vLLM, LM Studio, ...), which is typically keyless. Only require a
            # key when targeting the real api.openai.com default.
            if not self.api_key and not self.base_url:
                raise ValueError(
                    "api_key is required for OpenAI. Set base_url to use a "
                    "keyless OpenAI-compatible server (e.g. llama.cpp, vLLM)."
                )

            return OpenAILLM(
                api_key=self.api_key,
                model=self.model_name,
                base_url=self.base_url or "https://api.openai.com/v1",
                **self._timeout_kwargs(),
                **self._filter_kwargs("openai"),
            )

        raise ValueError(f"Unsupported provider: {self.model_provider}")

    def _timeout_kwargs(self) -> dict[str, Any]:
        # Only override each provider's own default timeout when the caller
        # actually configured one — passing timeout=None would otherwise
        # disable httpx's timeout entirely instead of falling back to it.
        return {"timeout": self.timeout} if self.timeout is not None else {}

    def _filter_kwargs(self, provider: str) -> dict[str, Any]:
        if not self.strict:
            return self.provider_kwargs

        allowed = {
            "ollama": {
                "num_ctx",
                "num_predict",
                "temperature",
                "top_p",
                "repeat_penalty",
            },
            "openai": {
                "temperature",
                "max_tokens",
                "top_p",
                "response_format",
            },
            "gemini": {
                "temperature",
                "topP",
                "maxOutputTokens",
                "responseMimeType",
                "responseSchema",
            },
        }.get(provider, set())

        return {k: v for k, v in self.provider_kwargs.items() if k in allowed}

    async def generate(
        self,
        prompt: str,
        schema: Optional[Type[BaseModel]] = None,
    ) -> Any:
        resolved_schema = schema or self.schema
        return await self.model.generate(prompt, resolved_schema)

    async def close(self) -> None:
        await self.model.close()

    async def __aenter__(self) -> "ModelManager":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()


LLMManager = ModelManager
