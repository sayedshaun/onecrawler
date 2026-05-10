from typing import Optional, Type

from langchain.chat_models import init_chat_model
from pydantic import BaseModel


class LLMManager:
    def __init__(
        self,
        schema: Optional[Type[BaseModel]],
        model_provider: str,
        model_name: str,
        base_url: Optional[str] = None,
        reasoning: bool = False,
        api_key: Optional[str] = None,
    ):
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

    async def generate(self, prompt: str):
        return await self.model.ainvoke(prompt)
