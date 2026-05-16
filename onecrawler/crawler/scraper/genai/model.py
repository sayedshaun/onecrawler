from typing import Any, Optional, Type

from langchain.chat_models import init_chat_model
from pydantic import BaseModel


class LLMManager:
    """Manager for Large Language Model interactions.

    Handles model initialization, structured output configuration, and
    asynchronous invocation.

    Attributes:
        schema (Optional[Type[BaseModel]]): The Pydantic schema for structured output.
        model_provider (str): The name of the LLM provider (e.g., 'openai', 'anthropic').
        model_name (str): The specific model name to use.
        base_url (Optional[str]): Custom base URL for the API.
        reasoning (bool): Whether to enable 'thinking' or 'reasoning' models.
        api_key (Optional[str]): API key for the provider.
        model (BaseChatModel): The initialized LangChain chat model.
    """

    def __init__(
        self,
        schema: Optional[Type[BaseModel]],
        model_provider: str,
        model_name: str,
        base_url: Optional[str] = None,
        reasoning: bool = False,
        api_key: Optional[str] = None,
    ):
        """Initializes LLMManager.

        Args:
            schema (Optional[Type[BaseModel]]): Pydantic schema for output.
            model_provider (str): The LLM provider name.
            model_name (str): The model name.
            base_url (Optional[str]): Optional custom base URL.
            reasoning (bool): Whether to enable reasoning capabilities.
            api_key (Optional[str]): Optional API key.
        """
        self.schema = schema
        self.model_provider = model_provider
        self.model_name = model_name
        self.base_url = base_url
        self.reasoning = reasoning
        self.api_key = api_key

        self.model = init_chat_model(
            model=self.model_name,
            model_provider=self.model_provider,
            base_url=self.base_url,
            api_key=self.api_key,
            **(
                {
                    "model_kwargs": {
                        "thinking": {"type": "enabled", "budget_tokens": 5000}
                    }
                }
                if self.reasoning
                else {}
            ),
        )

        if self.schema:
            self.model = self.model.with_structured_output(self.schema)

    async def generate(self, prompt: str) -> Any:
        """Invokes the model with a prompt and returns the result.

        Args:
            prompt (str): The input prompt for the LLM.

        Returns:
            Any: The model's response, structured if a schema was provided.
        """
        return await self.model.ainvoke(prompt)
