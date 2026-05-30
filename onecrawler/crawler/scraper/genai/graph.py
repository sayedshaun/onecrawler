import asyncio
from typing import Optional

import trafilatura
from langgraph.graph import END, START, StateGraph

from .prompt import build_scraper_prompt
from .state import AgentState


async def _fetch_with_browser(url: str, browser) -> Optional[str]:
    """Fetches fully-rendered HTML using a Playwright browser page.

    Args:
        url (str): The URL to navigate to.
        browser (GoogleChrome): The active browser instance.

    Returns:
        Optional[str]: The page's inner HTML, or None if navigation failed.
    """
    page = await browser.new_page()
    runtime = browser.settings.runtime
    try:
        await page.goto(
            url,
            wait_until=runtime.wait_until,
            timeout=runtime.timeout,
        )
        return await page.content()
    except Exception:
        return None
    finally:
        await page.close()


async def _fetch_with_trafilatura(url: str) -> Optional[str]:
    """Fetches raw HTML using trafilatura in a thread.

    Args:
        url (str): The URL to fetch.

    Returns:
        Optional[str]: The fetched HTML, or None if failed.
    """
    return await asyncio.to_thread(trafilatura.fetch_url, url)


async def url_to_markdown_node(state: AgentState) -> AgentState:
    """Converts a URL to markdown. Uses browser if available, else trafilatura."""

    browser = state.get("browser")
    url = state["url"]

    html = (
        await _fetch_with_browser(url, browser)
        if browser
        else await _fetch_with_trafilatura(url)
    )

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
