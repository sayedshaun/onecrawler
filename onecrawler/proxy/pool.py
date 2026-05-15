import random
from itertools import cycle
from typing import List, Literal, Optional

from ..settings.proxy import ProxySettings


class ProxyPool:
    """A pool of proxy servers with rotation support.

    Attributes:
        proxies (List[ProxySettings]): The list of proxy configurations in the pool.
        strategy (Literal["round_robin", "random"]): The strategy for selecting the next proxy.
    """

    def __init__(
        self,
        proxies: Optional[List[ProxySettings]] = None,
        strategy: Literal["round_robin", "random"] = "round_robin",
    ):
        """Initializes the ProxyPool.

        Args:
            proxies (Optional[List[ProxySettings]]): Initial list of proxies.
            strategy (Literal["round_robin", "random"]): Rotation strategy to use.

        Raises:
            ValueError: If an invalid strategy is provided.
        """
        self.proxies = proxies or []
        self.strategy = strategy
        self._cycle = cycle(self.proxies)

        if self.strategy not in ("round_robin", "random"):
            raise ValueError("proxy_rotation must be 'round_robin' or 'random'")

    def next(self) -> Optional[ProxySettings]:
        """Returns the next proxy from the pool based on the rotation strategy.

        Returns:
            Optional[ProxySettings]: The next proxy configuration, or None if the pool is empty.
        """
        if not self.proxies:
            return None

        if self.strategy == "random":
            return random.choice(self.proxies)

        return next(self._cycle)
