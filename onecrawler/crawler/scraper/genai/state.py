from typing import TypedDict


class AgentState(TypedDict):
    url: str
    llm: object
    markdown: str
    prompt: str
    response: str
