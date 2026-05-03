from dataclasses import dataclass, field
from typing import Optional, Literal, List
from .brawser import BrowserSettings


@dataclass
class CrawlerSettings:
    link_extraction_strategy: Literal["shallow", "deep"] = "deep"
    link_extraction_limit: int = 50
    include_link_patterns: List[str] = field(default_factory=list)
    link_classification: bool = False

    scraping_strategy: Literal["heuristic", "genai"] = "heuristic"
    scraping_output_format: Literal[
        "markdown",
        "json",
        "csv",
        "html",
        "python",
        "txt",
        "xml",
        "xmltei",
    ] = "json"

    genai_provider: Optional[Literal["google", "openai", "ollama"]] = None
    genai_model_name: Optional[str] = None
    genai_api_key: Optional[str] = None

    concurrency: int = 10
    retries: int = 2
    timeout: int = 10
    browser_settings: Optional[BrowserSettings] = None
    logging: bool = False
    logging_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    def __post_init__(self):
        if self.scraping_strategy == "genai" and self.scraping_output_format != "json":
            raise ValueError(
                "GenAI scraping strategy currently only supports 'json' output format"
            )
