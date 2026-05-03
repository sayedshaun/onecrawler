from dataclasses import dataclass
from typing import Optional, Literal, Type
from pydantic import BaseModel

@dataclass
class GenerativeAISettings:
    provider: Literal["google", "openai", "ollama"]
    model_name: str
    api_key: str
    output_schema: Optional[Type[BaseModel]] = None
