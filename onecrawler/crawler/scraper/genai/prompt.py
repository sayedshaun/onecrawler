from langchain_core.prompts import PromptTemplate


def build_scraper_prompt(markdown: str) -> str:
    """Builds a structured extraction prompt for the LLM.

    Args:
        markdown (str): The markdown content of the web page.

    Returns:
        str: The formatted prompt string.
    """
    template = PromptTemplate(
        input_variables=["markdown"],
        template="""
            You are a data extraction assistant.
            Extract the following information from the article content below.

            RULES:
            - You must return in the same language of the content
            - Return only structured data, no explanation

            Content:
            {markdown}
            """,
    )

    return template.format(
        markdown=markdown,
    )
