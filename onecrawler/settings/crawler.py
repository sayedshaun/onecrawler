from dataclasses import dataclass, field
from datetime import date
from typing import List, Literal, Optional

from ..proxy.pool import ProxyPool
from .browser import BrowserSettings
from .genai import GenerativeAISettings
from .proxy import ProxySettings
from .simulation import HumanBehaviorSettings


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
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    strict_date_filter: bool = False
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
    request_timeout: int = 10
    retry_delay: int = 1

    proxy: Optional[ProxySettings] = None
    proxies: Optional[List[ProxySettings]] = None
    proxy_rotation_method: Literal["round_robin", "random"] = "round_robin"

    browser_settings: BrowserSettings = field(default_factory=BrowserSettings)

    enable_logging: bool = False
    logging_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # Performance optimization flags
    enable_human_behaviors: bool = False
    human_behavior_settings: HumanBehaviorSettings = field(
        default_factory=HumanBehaviorSettings
    )

    def __post_init__(self):
        if self.proxy and self.proxies:
            raise ValueError("Use either proxy or proxies, not both")

        proxy_pool = self.create_proxy_pool()
        if not self.browser_settings.proxy:
            self.browser_settings.proxy = proxy_pool.next()

        if self.scraping_strategy == "genai":
            if self.scraping_output_format != "json":
                raise ValueError("GenAI only supports JSON output")

            if not self.genai:
                raise ValueError("genai settings is required for genai strategy")

    def create_proxy_pool(self) -> ProxyPool:
        if self.proxies:
            proxies = self.proxies
        elif self.proxy:
            proxies = [self.proxy]
        elif self.browser_settings.proxy:
            proxies = [self.browser_settings.proxy]
        else:
            proxies = []

        return ProxyPool(proxies=proxies, strategy=self.proxy_rotation_method)
