from dataclasses import dataclass
from typing import Literal, Optional, Type

from pydantic import BaseModel


@dataclass
class GenerativeAISettings:
    provider: Literal["google", "openai", "ollama"]
    model_name: str
    api_key: Optional[str] = None
    output_schema: Optional[Type[BaseModel]] = None
    base_url: Optional[str] = None
    reasoning: bool = False
