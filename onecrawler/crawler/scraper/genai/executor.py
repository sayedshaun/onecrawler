import asyncio
from typing import TYPE_CHECKING, Any, Optional

from .model import ModelManager

if TYPE_CHECKING:
    from ....browser import GoogleChrome


class GenAIStrategy:
    def __init__(
        self,
        provider: str,
        model_name: str,
        max_retries: int,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        output_schema: Optional[Any] = None,
        provider_kwargs: Optional[dict] = None,
        timeout: Optional[float] = None,
        browser: Optional["GoogleChrome"] = None,
    ):
        self.browser = browser
        self.max_retries = max_retries
        self.llm = ModelManager(
            schema=output_schema,
            model_provider=provider,
            model_name=model_name,
            base_url=base_url,
            api_key=api_key,
            provider_kwargs=provider_kwargs,
            timeout=timeout,
        )
        self.graph = None
        self._init_lock = asyncio.Lock()

    async def initialize(self):
        async with self._init_lock:
            if self.graph is None:
                from .graph import build_graph

                self.graph = build_graph()

    async def extract(self, url: str, html: Optional[str] = None) -> Optional[Any]:
        if self.graph is None:
            await self.initialize()

        state = {
            "url": url,
            "llm": self.llm,
            "browser": self.browser,
            "schema": self.llm.schema,
            "prefetched_html": html,
            "html": None,
            "prompt": None,
            "response": None,
            "max_retries": self.max_retries,
        }

        result = await self.graph.ainvoke(state)
        return result.get("response") if isinstance(result, dict) else result

    async def close(self) -> None:
        await self.llm.close()
