from abc import ABC, abstractmethod
from typing import Any


class BaseStrategy(ABC):
    @abstractmethod
    async def __aenter__(self) -> Any:
        pass

    @abstractmethod
    async def __aexit__(self, exc_type, exc, tb) -> None:
        pass

    @abstractmethod
    async def extract(self, url: str) -> Any:
        pass
