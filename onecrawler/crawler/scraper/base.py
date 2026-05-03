from abc import ABC, abstractmethod
from typing import Any


class BaseStrategy(ABC):
    @abstractmethod
    async def extract(self, url: str) -> Any:
        pass