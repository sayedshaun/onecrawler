from dataclasses import dataclass
from typing import Literal, Optional, Type

from pydantic import BaseModel


@dataclass
class GenerativeAISettings:
    """Configuration for Generative AI providers and models.

    Attributes:
        provider (Literal["google", "openai", "ollama"]): The AI service provider.
        model_name (str): The name of the specific model to use (e.g., "gemini-1.5-flash").
        api_key (Optional[str]): API key for the provider, if required.
        output_schema (Optional[Type[BaseModel]]): Pydantic model for structured output.
        base_url (Optional[str]): Base URL for providers like Ollama or custom endpoints.
        reasoning (bool): Whether to enable reasoning/thought processes if supported.
    """

    provider: Literal["google", "openai", "ollama"]
    model_name: str
    api_key: Optional[str] = None
    output_schema: Optional[Type[BaseModel]] = None
    base_url: Optional[str] = None
    reasoning: bool = False
