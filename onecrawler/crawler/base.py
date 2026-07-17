import logging
from abc import ABC
from typing import Any, Optional, Type


class BaseEngine(ABC):
    """Abstract base class for all OneCrawler engines.

    Provides a common interface for engine lifecycle management (start, run, close)
    and supports asynchronous context manager usage.

    Attributes:
        _closed (bool): Indicates whether the engine is currently closed.
        logger (logging.Logger): Logger instance for the engine.
    """

    def __init__(self):
        """Initializes the BaseEngine."""
        self._closed: bool = True
        self.logger = logging.getLogger(self.__class__.__name__)

    async def __aenter__(self):
        """Starts the engine when entering the context.

        Returns:
            BaseEngine: The engine instance.
        """
        self._closed = False
        await self.start()
        self.logger.debug("Engine started")
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc: Optional[BaseException],
        tb: Any,
    ):
        """Closes the engine when exiting the context.

        Args:
            exc_type: The exception type if an exception occurred.
            exc: The exception instance if an exception occurred.
            tb: The traceback if an exception occurred.
        """
        try:
            await self.close()
        finally:
            self._closed = True
            self.logger.debug("Engine closed")

    async def start(self):
        """Initializes engine resources.

        Override this method in subclasses to perform any necessary setup before the
        engine starts running.
        """
        pass

    async def close(self):
        """Cleans up engine resources.

        Override this method in subclasses to perform any necessary cleanup after the
        engine finishes running.
        """
        pass

    def _ensure_open(self):
        """Ensures that the engine is currently open.

        Raises:
            RuntimeError: If the engine is closed.
        """
        if self._closed:
            raise RuntimeError(
                f"{self.__class__.__name__} is closed. Use 'async with'."
            )

    @property
    def is_closed(self) -> bool:
        """Indicates whether the engine is closed.

        Returns:
            bool: True if closed, False otherwise.
        """
        return self._closed
