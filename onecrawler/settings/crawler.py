import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Literal, Optional

from ..proxy.pool import ProxyPool
from .browser import BrowserSettings
from .genai import LLMSettings
from .proxy import ProxyRotationMethod, ProxySettings
from .simulation import HumanBehaviorSettings
from .sitemap import SitemapSettings


class ScrapingStrategy(str, Enum):
    """Content-extraction strategy used by a crawl.

    Subclasses ``str``, so it's interchangeable with the plain string values
    (``"heuristic"``, ``"genai"``, ``"markdownify"``) that
    ``Settings.scraping_strategy`` accepts — existing code passing raw strings keeps
    working unchanged, while internal code can compare against named members instead of
    repeating string literals.
    """

    HEURISTIC = "heuristic"
    GENAI = "genai"
    MARKDOWNIFY = "markdownify"


class LinkExtractionStrategy(str, Enum):
    """Strategy for finding links on a page.

    Subclasses ``str``, so it's interchangeable with the plain string values
    (``"shallow"``, ``"deep"``) this has always accepted.
    """

    SHALLOW = "shallow"
    DEEP = "deep"


class OutputFormat(str, Enum):
    """Output format for scraped content.

    Subclasses ``str``, so it's interchangeable with the plain string values
    (``"markdown"``, ``"json"``, ``"xml"``, ``"xmltei"``) this has always accepted, and
    passes straight through to ``trafilatura``'s own ``output_format`` argument, which
    expects these same string values.
    """

    MARKDOWN = "markdown"
    JSON = "json"
    XML = "xml"
    XMLTEI = "xmltei"


_LINK_EXTRACTION_STRATEGIES = tuple(s.value for s in LinkExtractionStrategy)
_SCRAPING_STRATEGIES = tuple(s.value for s in ScrapingStrategy)
_OUTPUT_FORMATS = tuple(s.value for s in OutputFormat)
_PROXY_ROTATION_METHODS = tuple(s.value for s in ProxyRotationMethod)
_LOGGING_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR")


@dataclass
class Settings:
    """Central configuration class for OneCrawler.

    This class coordinates settings for sitemap crawling, link extraction,
    content scraping, browser automation, and proxy management.

    Attributes:
        sitemap (SitemapSettings): Configuration for sitemap discovery.
        link_extraction_strategy (Literal["shallow", "deep"]): Strategy for finding links on pages.
        link_extraction_limit (int): Maximum number of valid links to extract per run.
        include_link_patterns (Optional[List[str]]): Wildcard patterns for links to include.
        exclude_link_patterns (Optional[List[str]]): Wildcard patterns for links to exclude.
        scraping_strategy (Literal["heuristic", "genai", "markdownify"]): Strategy for content extraction.
        scraping_output_format (str): The desired format for scraped data.
        exclude_selectors (Optional[List[str]]): CSS selectors (e.g.
            ``["nav", "footer", ".cookie-banner"]``) to strip before HTML-to-
            Markdown conversion. Applies to the ``markdownify`` and ``genai``
            strategies, which both convert whole-page HTML. ``None`` (the
            default) converts the page as-is.
        genai (Optional[LLMSettings]): Configuration for AI-powered scraping.
        concurrency (int): Number of concurrent workers/pages.
        max_retries (int): Number of retries for failed requests/actions.
        request_timeout (int): Timeout for requests in seconds.
        retry_delay (int): Delay between retries in seconds.
        proxies (Optional[List[ProxySettings]]): Proxies to use. A single proxy
            is just a one-element list; multiple proxies rotate per
            ``proxy_rotation_method``.
        proxy_rotation_method (Literal["round_robin", "random"]): Strategy for proxy rotation.
        browser_settings (BrowserSettings): Configuration for the browser instance.
        show_progress (bool): Whether to display tqdm progress bars.
        logging_level (Optional[str]): Log level (e.g., "INFO"). ``None`` (the
            default) leaves logging unconfigured.
        human_behavior_settings (Optional[HumanBehaviorSettings]): Human-browsing
            simulation config. ``None`` (the default) disables simulation;
            pass a ``HumanBehaviorSettings`` to enable it.
    """

    sitemap: SitemapSettings = field(default_factory=SitemapSettings)

    link_extraction_strategy: Literal["shallow", "deep"] = "deep"
    link_extraction_limit: int = 50

    include_link_patterns: Optional[List[str]] = None
    exclude_link_patterns: Optional[List[str]] = None

    scraping_strategy: Literal["heuristic", "genai", "markdownify"] = "heuristic"
    scraping_output_format: Literal["markdown", "json", "xml", "xmltei"] = "json"
    exclude_selectors: Optional[List[str]] = None

    genai: Optional[LLMSettings] = None

    concurrency: int = 10
    max_retries: int = 2
    request_timeout: int = 10
    retry_delay: int = 1

    proxies: Optional[List[ProxySettings]] = None
    proxy_rotation_method: Literal["round_robin", "random"] = "round_robin"

    browser_settings: BrowserSettings = field(default_factory=BrowserSettings)

    show_progress: bool = True

    logging_level: Optional[Literal["DEBUG", "INFO", "WARNING", "ERROR"]] = None

    human_behavior_settings: Optional[HumanBehaviorSettings] = None

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
        if self.logging_level is not None and self.logging_level not in _LOGGING_LEVELS:
            raise ValueError(
                f"logging_level must be one of {_LOGGING_LEVELS} or None, "
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
                f"link_extraction_limit must be >= 0, got {self.link_extraction_limit}"
            )

        if self.logging_level is not None:
            logging.getLogger("onecrawler").setLevel(self.logging_level)
            logging.getLogger("trafilatura").setLevel(logging.ERROR)

        if self.scraping_strategy == ScrapingStrategy.GENAI:
            if self.scraping_output_format != OutputFormat.JSON:
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
        elif self.browser_settings.proxy:
            proxies = [self.browser_settings.proxy]
        else:
            proxies = []

        return ProxyPool(proxies=proxies, strategy=self.proxy_rotation_method)
