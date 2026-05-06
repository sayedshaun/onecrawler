import logging
from abc import ABC, abstractmethod
from typing import Optional, Type


class BaseEngine(ABC):
    def __init__(self):
        self._closed: bool = True
        self.logger = logging.getLogger(self.__class__.__name__)

    # ===== Context Manager =====
    async def __aenter__(self):
        self._closed = False
        await self.start()
        self.logger.debug("Engine started")
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc: Optional[BaseException],
        tb,
    ):
        try:
            await self.close()
        finally:
            self._closed = True
            self.logger.debug("Engine closed")

    # ===== Lifecycle Hooks =====
    async def start(self):
        """Override to initialize resources."""
        pass

    async def close(self):
        """Override to cleanup resources."""
        pass

    # ===== REQUIRED API =====
    @abstractmethod
    async def run(self, *args, **kwargs):
        """Main execution method for the engine."""
        raise NotImplementedError

    # ===== Safety =====
    def _ensure_open(self):
        if self._closed:
            raise RuntimeError(
                f"{self.__class__.__name__} is closed. Use 'async with'."
            )

    @property
    def is_closed(self) -> bool:
        return self._closed
