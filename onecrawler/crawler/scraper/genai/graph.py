import trafilatura
from langgraph.graph import END, START, StateGraph

from .prompt import build_scraper_prompt
from .state import AgentState


async def url_to_markdown_node(state: AgentState) -> AgentState:
    html = trafilatura.fetch_url(state["url"])
    markdown = trafilatura.extract(html, output_format="markdown")
    state["markdown"] = markdown
    return state


async def prompt_builder_node(state: AgentState) -> AgentState:
    markdown = state["markdown"]
    prompt = build_scraper_prompt(markdown)
    state["prompt"] = prompt
    return state


async def markdown_to_structured_output(state: AgentState) -> AgentState:
    llm = state["llm"]
    prompt = state["prompt"]
    response = await llm.generate(prompt)
    state["response"] = response
    return state


async def compiled_graph():
    graph = StateGraph(AgentState)

    graph.add_node("url_to_markdown", url_to_markdown_node)
    graph.add_node("markdown_to_structured_output", markdown_to_structured_output)

    graph.add_edge(START, "url_to_markdown")
    graph.add_edge("url_to_markdown", "markdown_to_structured_output")
    graph.add_edge("markdown_to_structured_output", END)

    return graph.compile()
