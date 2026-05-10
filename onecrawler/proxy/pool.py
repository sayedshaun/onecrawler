import random
from itertools import cycle
from typing import List, Literal, Optional

from ..settings.proxy import ProxySettings


class ProxyPool:
    def __init__(
        self,
        proxies: Optional[List[ProxySettings]] = None,
        strategy: Literal["round_robin", "random"] = "round_robin",
    ):
        self.proxies = proxies or []
        self.strategy = strategy
        self._cycle = cycle(self.proxies)

        if self.strategy not in ("round_robin", "random"):
            raise ValueError("proxy_rotation must be 'round_robin' or 'random'")

    def next(self) -> Optional[ProxySettings]:
        if not self.proxies:
            return None

        if self.strategy == "random":
            return random.choice(self.proxies)

        return next(self._cycle)
