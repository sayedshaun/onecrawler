"""Prompt templates for the GenAI extraction strategy.

Keeping prompts here (rather than inline in ``executor.py``) makes them easy to find,
review, and tweak without touching pipeline logic. Fill the placeholders with
``str.format`` at call sites, e.g. ``STRUCTURED_PROMPT.format(markdown=markdown)``.
"""

STRUCTURED_PROMPT = """
        You are a precise web data extractor. Extract the requested fields from
        the content below.

        The content is machine-converted markdown, so it still contains page
        chrome and markup noise. Read it, understand it, and extract clean
        values — do not blindly copy raw markdown.

        Extraction rules:
        - Use ONLY information present in the content. Never guess or invent values.
        - If a field's value is not present in the content, set it to null.
        - Do not fabricate or reword facts. You may drop non-content noise to
          produce a clean value.
        - For main-body/text fields, return only the meaningful article prose.
          Exclude navigation, ads, share/related links, image and photo captions,
          bylines, timestamps, and leftover markup such as image tags
          (![alt](url)) or link syntax ([text](url)) — keep the link's text, drop
          the URL.
        - Normalize dates to ISO 8601 (YYYY-MM-DD) when a full date is available.
        - Collapse incidental whitespace; preserve meaningful line breaks in long text.

        Content:
        {markdown}
        """
