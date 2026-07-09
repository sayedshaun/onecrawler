from typing import Any, Type

from pydantic import BaseModel
from typing_extensions import TypedDict


class AgentState(TypedDict, total=False):
    browser: Any
    llm: Any
    url: str
    prefetched_html: str | None
    html: str | None
    markdown: str | None
    prompt: str | None
    schema: Type[BaseModel]
    response: BaseModel | dict | None
    attempts: int
    max_retries: int
