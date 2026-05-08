from dataclasses import dataclass, field
from typing import Optional, Literal, List
from .brawser import BrowserSettings
from .genai import GenerativeAISettings


@dataclass
class CrawlerSettings:
    follow_sitemap_index: bool = True
    sitemap_html_fallback: bool = True
    max_crawl_depth: int = 3
    max_crawl_pages: int = 500
    sitemap_user_agent: str = (
        "Mozilla/5.0 (compatible; UniversalURLFetcher/1.0; "
        "+https://github.com/sayedshaun/onecrawler)"
    )
    sitemap_respect_robots: bool = True
    sitemap_deduplicate: bool = True
    verbose: bool = True

    link_extraction_strategy: Literal["shallow", "deep"] = "deep"
    link_extraction_limit: int = 50

    include_link_patterns: Optional[List[str]] = None
    exclude_link_patterns: Optional[List[str]] = None

    scraping_strategy: Literal["heuristic", "genai"] = "heuristic"
    scraping_output_format: Literal[
        "markdown", "json", "csv", "html", "python", "txt", "xml", "xmltei"
    ] = "json"

    genai: Optional[GenerativeAISettings] = None

    concurrency: int = 10
    max_retries: int = 2
    request_timeout: int = 3
    retry_delay: int = 1

    browser_settings: BrowserSettings = field(default_factory=BrowserSettings)

    enable_logging: bool = False
    logging_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # Performance optimization flags
    disable_human_behaviors: bool = False

    def __post_init__(self):
        if self.scraping_strategy == "genai":
            if self.scraping_output_format != "json":
                raise ValueError("GenAI only supports JSON output")

            if not self.genai:
                raise ValueError("genai config is required for genai strategy")
