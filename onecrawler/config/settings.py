from dataclasses import dataclass, field
from typing import Optional, Literal, List


@dataclass
class CrawlerSettings:
    # link crawling
    link_extraction_strategy: Literal["shallow", "deep"] = "deep"
    link_extraction_limit: int = 50
    include_link_patterns: List[str] = field(default_factory=list)
    link_classification: bool = False

    # content extraction
    scraping_strategy: Literal["heuristic", "genai"] = "heuristic"

    # LLM config
    genai_provider: Optional[Literal["google", "openai", "ollama"]] = None
    genai_model_name: Optional[str] = None
    genai_api_key: Optional[str] = None

    concurrency: int = 10
