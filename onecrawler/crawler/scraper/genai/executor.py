import asyncio

from .graph import build_graph


class GenAIStrategy:
    def __init__(self, llm):
        self.llm = llm
        self.graph = None
        self._init_lock = asyncio.Lock()

    async def initialize(self):
        # prevents double initialization
        async with self._init_lock:
            if self.graph is None:
                self.graph = build_graph()

    async def extract(self, url: str):
        # ensure initialized (safe even if called multiple times)
        if self.graph is None:
            await self.initialize()

        state = {
            "url": url,
            "llm": self.llm,
        }

        result = await self.graph.ainvoke(state)

        # normalize output (important for production)
        return result.get("response") if isinstance(result, dict) else result
