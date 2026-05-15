import asyncio
from typing import Any, Optional

from ....settings.genai import GenerativeAISettings
from .graph import build_graph
from .model import LLMManager


class GenAIStrategy:
    """Strategy for extracting content using Generative AI.

    Orchestrates the LLM-based extraction process using a compiled state graph.

    Attributes:
        llm (LLMManager): Manager for the underlying Large Language Model.
        graph (Optional[CompiledGraph]): The compiled state graph for extraction.
    """

    def __init__(self, settings: GenerativeAISettings):
        """Initializes GenAIStrategy.

        Args:
            settings (GenerativeAISettings): The GenAI configuration settings.
        """
        self.llm = LLMManager(
            schema=settings.output_schema,
            model_provider=settings.provider,
            model_name=settings.model_name,
            base_url=settings.base_url,
            reasoning=settings.reasoning,
            api_key=settings.api_key,
        )
        self.graph = None
        self._init_lock = asyncio.Lock()

    async def initialize(self):
        """Initializes the state graph.

        This method is thread-safe and prevents multiple initializations.
        """
        async with self._init_lock:
            if self.graph is None:
                self.graph = build_graph()

    async def extract(self, url: str) -> Optional[Any]:
        """Extracts structured data from a URL using GenAI.

        Args:
            url (str): The URL to extract data from.

        Returns:
            Optional[Any]: The extracted structured data, or None if failed.
        """
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
