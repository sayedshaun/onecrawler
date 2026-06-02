from abc import ABC, abstractmethod
from typing import Optional, Type, TypeVar, Any
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class BaseLLM(ABC):
    @abstractmethod
    async def generate(self, prompt: str, schema: Optional[Type[T]] = None, **kwargs: Any) -> T | str:
        pass

    @abstractmethod
    async def close(self) -> None:
        pass
