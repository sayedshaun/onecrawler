import logging
from dataclasses import dataclass, field
from typing import List, Literal, Optional

from ..proxy.pool import ProxyPool
from .browser import BrowserSettings
from .genai import GenerativeAISettings
from .proxy import ProxySettings
from .simulation import HumanBehaviorSettings
from .sitemap import SitemapSettings

_LINK_EXTRACTION_STRATEGIES = ("shallow", "deep")
_SCRAPING_STRATEGIES = ("heuristic", "genai")
_OUTPUT_FORMATS = ("markdown", "json", "xml", "xmltei")
_PROXY_ROTATION_METHODS = ("round_robin", "random")
_LOGGING_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR")


@dataclass
class Settings:
    """Central configuration class for OneCrawler.

    This class coordinates settings for sitemap crawling, link extraction,
    content scraping, browser automation, and proxy management.

    Attributes:
        sitemap (SitemapSettings): Configuration for sitemap discovery.
        verbose (bool): Whether to enable verbose output/logging.
        link_extraction_strategy (Literal["shallow", "deep"]): Strategy for finding links on pages.
        link_extraction_limit (int): Maximum number of valid links to extract per run.
        include_link_patterns (Optional[List[str]]): Wildcard patterns for links to include.
        exclude_link_patterns (Optional[List[str]]): Wildcard patterns for links to exclude.
        scraping_strategy (Literal["heuristic", "genai"]): Strategy for content extraction.
        scraping_output_format (str): The desired format for scraped data.
        genai (Optional[GenerativeAISettings]): Configuration for AI-powered scraping.
        concurrency (int): Number of concurrent workers/pages.
        max_retries (int): Number of retries for failed requests/actions.
        request_timeout (int): Timeout for requests in seconds.
        retry_delay (int): Delay between retries in seconds.
        proxy (Optional[ProxySettings]): Single proxy configuration.
        proxies (Optional[List[ProxySettings]]): List of proxies for rotation.
        proxy_rotation_method (Literal["round_robin", "random"]): Strategy for proxy rotation.
        browser_settings (BrowserSettings): Configuration for the browser instance.
        show_progress (bool): Whether to display tqdm progress bars.
        enable_logging (bool): Whether to enable standard logging.
        logging_level (str): The logging level (e.g., "INFO").
        enable_human_behaviors (bool): Whether to simulate human browsing patterns.
        human_behavior_settings (HumanBehaviorSettings): Configuration for human simulation.
    """

    sitemap: SitemapSettings = field(default_factory=SitemapSettings)
    verbose: bool = True

    link_extraction_strategy: Literal["shallow", "deep"] = "deep"
    link_extraction_limit: int = 50

    include_link_patterns: Optional[List[str]] = None
    exclude_link_patterns: Optional[List[str]] = None

    scraping_strategy: Literal["heuristic", "genai"] = "heuristic"
    scraping_output_format: Literal["markdown", "json", "xml", "xmltei"] = "json"

    genai: Optional[GenerativeAISettings] = None

    concurrency: int = 10
    max_retries: int = 2
    request_timeout: int = 10
    retry_delay: int = 1

    proxy: Optional[ProxySettings] = None
    proxies: Optional[List[ProxySettings]] = None
    proxy_rotation_method: Literal["round_robin", "random"] = "round_robin"

    browser_settings: BrowserSettings = field(default_factory=BrowserSettings)

    show_progress: bool = True

    enable_logging: bool = False
    logging_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    enable_human_behaviors: bool = False
    human_behavior_settings: HumanBehaviorSettings = field(
        default_factory=HumanBehaviorSettings
    )

    def __post_init__(self):
        """Validates settings after initialization."""
        if self.link_extraction_strategy not in _LINK_EXTRACTION_STRATEGIES:
            raise ValueError(
                "link_extraction_strategy must be one of "
                f"{_LINK_EXTRACTION_STRATEGIES}, got {self.link_extraction_strategy!r}"
            )
        if self.scraping_strategy not in _SCRAPING_STRATEGIES:
            raise ValueError(
                f"scraping_strategy must be one of {_SCRAPING_STRATEGIES}, "
                f"got {self.scraping_strategy!r}"
            )
        if self.scraping_output_format not in _OUTPUT_FORMATS:
            raise ValueError(
                f"scraping_output_format must be one of {_OUTPUT_FORMATS}, "
                f"got {self.scraping_output_format!r}"
            )
        if self.proxy_rotation_method not in _PROXY_ROTATION_METHODS:
            raise ValueError(
                "proxy_rotation_method must be one of "
                f"{_PROXY_ROTATION_METHODS}, got {self.proxy_rotation_method!r}"
            )
        if self.logging_level not in _LOGGING_LEVELS:
            raise ValueError(
                f"logging_level must be one of {_LOGGING_LEVELS}, "
                f"got {self.logging_level!r}"
            )

        if self.concurrency < 1:
            raise ValueError(f"concurrency must be >= 1, got {self.concurrency}")
        if self.max_retries < 1:
            raise ValueError(f"max_retries must be >= 1, got {self.max_retries}")
        if self.request_timeout <= 0:
            raise ValueError(f"request_timeout must be > 0, got {self.request_timeout}")
        if self.retry_delay < 0:
            raise ValueError(f"retry_delay must be >= 0, got {self.retry_delay}")
        if self.link_extraction_limit < 0:
            raise ValueError(
                "link_extraction_limit must be >= 0, got "
                f"{self.link_extraction_limit}"
            )

        if self.enable_logging:
            logging.getLogger("onecrawler").setLevel(self.logging_level)
            logging.getLogger("trafilatura").setLevel(logging.ERROR)

        if self.proxy and self.proxies:
            raise ValueError("Use either proxy or proxies, not both")

        if self.proxy and not self.browser_settings.proxy:
            self.browser_settings.proxy = self.proxy

        if self.scraping_strategy == "genai":
            if self.scraping_output_format != "json":
                raise ValueError("GenAI only supports JSON output")

            if not self.genai:
                raise ValueError("genai settings is required for genai strategy")

    def create_proxy_pool(self) -> ProxyPool:
        """Creates a ProxyPool based on the provided proxy settings.

        Returns:
            ProxyPool: An initialized proxy pool.
        """
        if self.proxies:
            proxies = self.proxies
        elif self.proxy:
            proxies = [self.proxy]
        elif self.browser_settings.proxy:
            proxies = [self.browser_settings.proxy]
        else:
            proxies = []

        return ProxyPool(proxies=proxies, strategy=self.proxy_rotation_method)
