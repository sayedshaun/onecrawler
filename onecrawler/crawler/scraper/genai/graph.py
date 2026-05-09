import asyncio

import trafilatura
from langgraph.graph import END, START, StateGraph

from .prompt import build_scraper_prompt
from .state import AgentState


# ===== utils =====
async def fetch_html(url: str) -> str:
    return await asyncio.to_thread(trafilatura.fetch_url, url)


# ===== nodes =====
async def url_to_markdown_node(state: AgentState) -> AgentState:
    html = await fetch_html(state["url"])

    if not html:
        state["markdown"] = None
        return state

    markdown = trafilatura.extract(html, output_format="markdown")
    state["markdown"] = markdown
    return state


async def prompt_builder_node(state: AgentState) -> AgentState:
    markdown = state.get("markdown")

    if not markdown:
        state["prompt"] = None
        return state

    state["prompt"] = build_scraper_prompt(markdown)
    return state


async def markdown_to_structured_output(state: AgentState) -> AgentState:
    llm = state["llm"]
    prompt = state.get("prompt")

    if not prompt:
        state["response"] = None
        return state

    state["response"] = await llm.generate(prompt)
    return state


# ===== graph builder (SYNC) =====
def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("url_to_markdown", url_to_markdown_node)
    graph.add_node("prompt_builder", prompt_builder_node)
    graph.add_node("markdown_to_structured_output", markdown_to_structured_output)

    graph.add_edge(START, "url_to_markdown")
    graph.add_edge("url_to_markdown", "prompt_builder")
    graph.add_edge("prompt_builder", "markdown_to_structured_output")
    graph.add_edge("markdown_to_structured_output", END)

    return graph.compile()
