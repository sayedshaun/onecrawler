from dataclasses import dataclass, field
from typing import Optional, Literal, List
from .brawser import BrowserSettings
from .genai import GenerativeAISettings


@dataclass
class CrawlerSettings:
    link_extraction_strategy: Literal["shallow", "deep"] = "deep"
    link_extraction_limit: int = 50

    include_link_patterns: Optional[List[str]] = None
    exclude_link_patterns: Optional[List[str]] = None

    link_classification: bool = False

    scraping_strategy: Literal["heuristic", "genai"] = "heuristic"
    scraping_output_format: Literal[
        "markdown", "json", "csv", "html", "python", "txt", "xml", "xmltei"
    ] = "json"

    genai: Optional[GenerativeAISettings] = None

    concurrency: int = 10
    max_retries: int = 2
    request_timeout: int = 10
    infinite_scroll_limit: int = 1

    browser_settings: BrowserSettings = field(default_factory=BrowserSettings)

    enable_logging: bool = False
    logging_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    def __post_init__(self):
        if self.scraping_strategy == "genai":
            if self.scraping_output_format != "json":
                raise ValueError("GenAI only supports JSON output")

            if not self.genai:
                raise ValueError("genai config is required for genai strategy")
