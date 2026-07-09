from typing import Callable, List


class FilterChain:
    """Composable filter system (AND / OR / NOT)."""

    def __init__(self, *filters: Callable[[dict], bool], mode: str = "AND"):
        self.filters: List[Callable[[dict], bool]] = list(filters)
        self.mode = mode.upper()

    def add(self, f: Callable[[dict], bool]):
        self.filters.append(f)
        return self

    def __call__(self, item: dict) -> bool:
        if self.mode == "AND":
            return all(f(item) for f in self.filters)

        if self.mode == "OR":
            return any(f(item) for f in self.filters)

        raise ValueError(f"Unknown mode: {self.mode}")
