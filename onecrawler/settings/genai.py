from dataclasses import dataclass
from enum import Enum
from typing import Any, Literal, Optional, Type

from pydantic import BaseModel


class GenAIProvider(str, Enum):
    """AI service provider for GenAI-based content extraction.

    Subclasses ``str``, so it's interchangeable with the plain string
    values (``"google"``, ``"openai"``, ``"ollama"``) this has always
    accepted.
    """

    GOOGLE = "google"
    OPENAI = "openai"
    OLLAMA = "ollama"


@dataclass
class GenerativeAISettings:
    """Configuration for Generative AI providers and models.

    Attributes:
        provider (Literal["google", "openai", "ollama"]): The AI service provider.
            Use "openai" with a custom ``base_url`` to target any
            OpenAI-compatible server (llama.cpp, vLLM, LM Studio, LocalAI, ...);
            ``api_key`` is optional for those keyless endpoints.
        model_name (str): The name of the specific model to use (e.g., "gemini-1.5-flash").
        api_key (Optional[str]): API key for the provider. Required for the real
            OpenAI/Gemini endpoints; optional when ``base_url`` points at a
            keyless OpenAI-compatible server.
        output_schema (Optional[Type[BaseModel]]): Pydantic model for structured output.
        base_url (Optional[str]): Base URL for Ollama, an OpenAI-compatible
            server, or any custom endpoint.
        provider_kwargs (Optional[dict[str, Any]]): Provider-specific keyword arguments.
        timeout (Optional[float]): Per-request timeout in seconds for the
            provider's API call. ``None`` uses the provider client's own default.
        think (bool): Ollama only. Whether to let a thinking model (qwen3,
            deepseek-r1, ...) emit its reasoning trace. Defaults to ``False``
            because thinking breaks structured output on Ollama (it returns an
            empty response) and makes free-form calls very slow. Ignored by the
            OpenAI and Gemini providers.
    """

    provider: Literal["google", "openai", "ollama"]
    model_name: str
    api_key: Optional[str] = None
    output_schema: Optional[Type[BaseModel]] = None
    base_url: Optional[str] = None
    provider_kwargs: Optional[dict[str, Any]] = None
    timeout: Optional[float] = None
    think: bool = False
