import trafilatura


def heuristic_structured_extraction(html: str) -> dict:
    extracted = trafilatura.extract(
        filecontent=html,
        output_format="json",
        with_metadata=True,
        fast=True,
        favor_precision=True,
        include_tables=True,
        include_comments=False,
        include_images=False,
        include_links=False,
        include_formatting=False,
        deduplicate=True,
    )
    return extracted
