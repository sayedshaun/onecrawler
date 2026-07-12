import contextlib
import logging

import markdownify as md
from langgraph.graph import END, START, StateGraph

from .state import AgentState

logger = logging.getLogger(__name__)


async def fetch_html_node(state: AgentState) -> AgentState:
    browser = state.get("browser")
    url = state["url"]
    page = None

    # Reuse HTML the caller already fetched (the combined Crawler passes the
    # page it loaded), avoiding a second navigation. Survives retries too,
    # since retry_node clears `html` but not `prefetched_html`.
    prefetched = state.get("prefetched_html")
    if prefetched is not None:
        state["html"] = prefetched
        return state

    if browser is None:
        logger.warning("fetch_html_node: browser is missing")
        state["html"] = None
        return state

    try:
        page = await browser.new_page()
        browser_settings = browser.settings

        await page.goto(
            url,
            wait_until=browser_settings.wait_until,
            timeout=browser_settings.timeout,
        )

        with contextlib.suppress(Exception):
            await page.wait_for_load_state(
                browser_settings.wait_until,
                timeout=browser_settings.timeout,
            )

        state["html"] = await page.content()
        return state

    except Exception as exc:
        logger.warning("fetch_html_node failed for %s: %s", url, exc)
        state["html"] = None
        state["markdown"] = None
        return state

    finally:
        if page is not None:
            with contextlib.suppress(Exception):
                await page.close()


def html_to_markdown_node(state: AgentState) -> AgentState:
    html = state.get("html")

    if not html:
        state["markdown"] = None
        return state

    markdown = md.markdownify(
        html,
        heading_style="ATX",
        bullets="-",
    )

    markdown = "\n".join(line.rstrip() for line in markdown.splitlines())

    state["markdown"] = markdown
    return state


async def prettify_markdown_node(state: AgentState) -> AgentState:
    markdown = state.get("markdown")

    if not markdown:
        return state

    prompt = f"""
        You are a markdown cleaner.

        Remove:
        - navigation
        - footer
        - cookie banners
        - repeated links
        - boilerplate

        Keep:
        - meaningful content
        - tables
        - headings

        Return only cleaned markdown.

        Markdown:
        {markdown}
        """

    llm = state["llm"]

    try:
        cleaned = await llm.generate(prompt)
        state["markdown"] = cleaned
    except Exception as exc:
        logger.warning(
            "prettify_markdown_node failed: %s",
            exc,
            exc_info=True,
        )

    return state


def prompt_builder_node(state: AgentState) -> AgentState:
    markdown = state.get("markdown")
    schema = state.get("schema")

    if not markdown:
        logger.warning("prompt_builder_node: markdown is empty")
        state["prompt"] = None
        return state

    if schema is None:
        logger.warning("prompt_builder_node: schema is missing")
        state["prompt"] = None
        return state

    try:
        schema_json = schema.model_json_schema()
    except Exception:
        schema_json = str(schema)

    prompt = f"""
        You are a structured web scraping assistant.

        Extract information from the markdown and return ONLY valid JSON.

        Rules:
        - Return only JSON.
        - Do not explain anything.
        - Do not include markdown fences.
        - If information is missing, use null.
        - Follow the schema exactly.

        Markdown:
        {markdown}

        Schema:
        {schema_json}
    """

    state["prompt"] = prompt
    return state


async def structured_output_node(state: AgentState) -> AgentState:
    llm = state["llm"]
    prompt = state.get("prompt")
    schema = state.get("schema")

    if not prompt:
        logger.warning("structured_output_node: prompt is empty")
        state["response"] = None
        return state

    if schema is None:
        logger.warning("structured_output_node: schema is missing")
        state["response"] = None
        return state

    try:
        response = await llm.generate(
            prompt,
            schema=schema,
        )

        try:
            response = schema.model_validate(response)
        except Exception:
            pass

        state["response"] = response

    except Exception as exc:
        logger.error(
            "structured_output_node failed: %s",
            exc,
            exc_info=True,
        )
        state["response"] = None

    return state


def retry_router(state: AgentState) -> str:
    """Routes to success/retry/failed.

    ``max_retries`` is the total number of attempts (matching
    ``Scraper._retry``'s semantics), not the number of retries on top of the
    first attempt, so the check is against ``max_retries - 1`` (the first
    attempt already happened before this router ever runs).
    """
    max_retries = state["max_retries"]
    if state.get("response") is not None:
        return "success"

    attempts = state.get("attempts", 0)

    if attempts >= max_retries - 1:
        return "failed"

    return "retry"


def retry_node(state: AgentState) -> AgentState:
    attempts = state.get("attempts", 0)
    state["attempts"] = attempts + 1
    state["html"] = None
    state["markdown"] = None
    state["response"] = None
    state["prompt"] = None

    return state


def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("fetch_html_node", fetch_html_node)
    graph.add_node("html_to_markdown_node", html_to_markdown_node)
    graph.add_node("prettify_markdown_node", prettify_markdown_node)
    graph.add_node("prompt_builder_node", prompt_builder_node)
    graph.add_node("structured_output_node", structured_output_node)
    graph.add_node("retry_node", retry_node)

    graph.add_edge(START, "fetch_html_node")
    graph.add_edge("fetch_html_node", "html_to_markdown_node")
    graph.add_edge("html_to_markdown_node", "prettify_markdown_node")
    graph.add_edge("prettify_markdown_node", "prompt_builder_node")
    graph.add_edge("prompt_builder_node", "structured_output_node")
    graph.add_conditional_edges(
        "structured_output_node",
        retry_router,
        {
            "success": END,
            "retry": "retry_node",
            "failed": END,
        },
    )
    graph.add_edge("retry_node", "fetch_html_node")
    return graph.compile()
