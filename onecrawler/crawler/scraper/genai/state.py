from typing import Any, Optional, TypedDict


class AgentState(TypedDict):
    """The state of the GenAI scraping workflow.

    Attributes:
        url (str): The target URL being scraped.
        llm (Any): The LLM manager instance.
        markdown (Optional[str]): Extracted markdown content from the URL.
        prompt (Optional[str]): The generated prompt for the LLM.
        response (Optional[Any]): The structured response from the LLM.
    """

    url: str
    llm: Any
    markdown: Optional[str]
    prompt: Optional[str]
    response: Optional[Any]
