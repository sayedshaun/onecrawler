from .extractor import llm_structured_extraction

class GenAIStrategy:
    async def extract(self, url: str):
        return await llm_structured_extraction(url)