import asyncio
import contextlib
import logging
from typing import Any, AsyncGenerator, Callable, List, Optional, Tuple
from urllib.parse import urlparse

from ..browser import GoogleChrome
from ..settings.browser import BrowserSettings
from ..settings.crawler import ScrapingStrategy
from ..settings.simulation import HumanBehaviorSettings
from ..utils.progress import make_progress_bar
from .base import BaseEngine
from .link.helper import (
    human_delay,
    human_mouse_move,
    human_scroll,
    wildcard_link_match,
)
from .navigation import goto
from .pool import BrowserPool, BrowserPoolExhausted
from .scheduler import BFScheduler
from .scraper.genai.executor import GenerativeAIStrategy
from .scraper.heuristic.script import HeuristicStrategy
from .scraper.markdown.script import MarkdownifyStrategy
from .spider import LinkSpider

logger = logging.getLogger(__name__)


class CrawlerRuntime:
    """Runs one breadth-first crawl of a single site to completion.

    A ``CrawlerRuntime`` is a short-lived, single-use worker pool: it owns a
    :class:`BFScheduler` (the URL queue), a :class:`BrowserPool` (pages to
    navigate with), a :class:`LinkSpider` (link discovery), and a scraping
    strategy (content extraction). ``concurrency`` workers pull URLs from
    the scheduler, navigate to each, extract its content, and feed newly
    discovered same-origin links back into the scheduler — until either
    ``max_links`` pages have been collected or the site runs out of links.

    Call :meth:`run` to crawl to completion and get back a list of
    extracted content dicts, or :meth:`stream` to get an async generator
    that yields each content dict as soon as it's extracted.

    A single instance is meant to be used for exactly one crawl; create a
    new ``CrawlerRuntime`` (via ``Crawler._create_runtime``) per crawl.
    """

    def __init__(
        self,
        scheduler: BFScheduler,
        pool: BrowserPool,
        spider: LinkSpider,
        base_prefix: str,
        max_links: int,
        strategy: Optional[Any] = None,
        human_behavior_settings: Optional[HumanBehaviorSettings] = None,
        include_pattern: Optional[List[str]] = None,
        exclude_pattern: Optional[List[str]] = None,
        enable_human_behaviors: bool = False,
        concurrency: int = 5,
        streaming: bool = False,
        content_filter: Optional[Callable[[dict], bool]] = None,
        wait_until: Optional[str] = None,
        timeout: Optional[int] = None,
        settle_delay: int = 0,
        show_progress: bool = True,
        *args,
        **kwargs,
    ):
        browser_settings = BrowserSettings()
        self.scheduler = scheduler
        self.pool = pool
        self.spider = spider
        if strategy is None:
            raise ValueError(
                "PipelineRuntime requires an initialized scraping strategy"
            )
        self.strategy = strategy

        self.base_prefix = base_prefix
        self.max_links = max_links
        self.include_pattern = include_pattern
        self.exclude_pattern = exclude_pattern
        self.enable_human_behaviors = enable_human_behaviors
        self.human_behavior_settings = human_behavior_settings
        self.concurrency = concurrency

        self.stop_event = asyncio.Event()

        self.results = []
        self.content = []
        self.results_set = set()
        self.lock = asyncio.Lock()
        self.stream_queue = asyncio.Queue(maxsize=1000)
        self.streaming = streaming
        self.wait_until = wait_until or browser_settings.wait_until
        self.timeout = timeout or browser_settings.timeout
        self.settle_delay = settle_delay
        self.show_progress = show_progress

        self._active_workers = 0
        self._active_lock = asyncio.Lock()

        self.content_filter = content_filter
        self._fatal_error: Optional[BaseException] = None
        self._link_allowed_cache: dict = {}

    async def _next_url(self) -> Optional[str]:
        """Pulls the next URL from the scheduler, tracking active-worker count.

        Returns None if there is currently no URL to process (which may or
        may not mean the crawl is finished).
        """
        url = await self.scheduler.next()
        async with self._active_lock:
            if url is None:
                if self._active_workers == 0 and not await self.scheduler.has_next():
                    self.stop_event.set()
            else:
                self._active_workers += 1
        return url

    async def _release_worker_slot(self):
        async with self._active_lock:
            self._active_workers -= 1

    async def _acquire_page(self, url: str):
        """Acquires a page from the pool, or returns None if this attempt
        should be skipped. Raises if the pool is permanently exhausted."""
        try:
            return await self.pool.acquire()
        except BrowserPoolExhausted as e:
            logger.error("Browser pool permanently exhausted; aborting crawl: %s", e)
            self._fatal_error = e
            self.stop_event.set()
            raise
        except Exception as e:
            logger.warning("Failed to acquire page for %s: %s", url, e)
            return None

    async def _simulate_human_behavior_before_parse(self, page):
        await human_delay(
            self.human_behavior_settings.min_delay,
            self.human_behavior_settings.max_delay,
        )
        await human_scroll(page, max_scrolls=self.human_behavior_settings.max_scrolls)

    async def _simulate_human_behavior_after_parse(self, page):
        s = self.human_behavior_settings
        await human_mouse_move(
            page,
            min_mouse_moves=s.min_mouse_moves,
            max_mouse_moves=s.max_mouse_moves,
            mouse_width=s.mouse_width,
            mouse_height=s.mouse_height,
            min_mouse_steps=s.min_mouse_steps,
            max_mouse_steps=s.max_mouse_steps,
            min_mouse_sleep=s.min_mouse_sleep,
            max_mouse_sleep=s.max_mouse_sleep,
        )

    async def _claim_for_extraction(self, url: str) -> bool:
        """Atomically checks whether url still needs extracting, and if so
        marks it as claimed so no other worker duplicates the work."""
        async with self.lock:
            should_extract = (
                not self.stop_event.is_set() and url not in self.results_set
            )
            if should_extract:
                self.results_set.add(url)
        return should_extract

    async def _record_content(self, url: str, content: dict) -> bool:
        """Stores extracted content if under max_links. Returns True if it
        was appended (and thus should be streamed/logged)."""
        async with self.lock:
            appended = len(self.results) < self.max_links
            if appended:
                self.results.append(url)
                self.content.append(content)
            if len(self.results) >= self.max_links:
                self.stop_event.set()
        return appended

    async def _extract_and_store(self, url: str, page):
        if not await self._claim_for_extraction(url):
            return

        try:
            html = await page.content()
            content = await self.strategy.extract(url, html=html)
        except Exception as e:
            logger.warning("Error extracting content for %s: %s", url, e)
            return

        if content is None:
            logger.debug("Content extraction returned None for %s", url)
            return

        if isinstance(content, dict):
            content["url"] = url
        else:
            content = {"text": content, "url": url}

        if self.content_filter is not None and not self.content_filter(content):
            logger.debug("Content did not pass filter for %s", url)
            return

        if not await self._record_content(url, content):
            return

        if self.streaming:
            await self.stream_queue.put(content)
        logger.debug(
            "Discovered %s/%s links; link=%s", len(self.results), self.max_links, url
        )

    def _link_allowed(self, link: str) -> bool:
        cached = self._link_allowed_cache.get(link)
        if cached is not None:
            return cached

        allowed = self._compute_link_allowed(link)
        self._link_allowed_cache[link] = allowed
        return allowed

    def _compute_link_allowed(self, link: str) -> bool:
        # LinkSpider.parse() already restricts links to the same origin
        # before they ever reach here, so no origin check is needed.
        if self.include_pattern and not wildcard_link_match(
            link, self.base_prefix, self.include_pattern
        ):
            return False
        if self.exclude_pattern and wildcard_link_match(
            link, self.base_prefix, self.exclude_pattern
        ):
            return False
        return True

    async def _schedule_links(self, links):
        for link in links:
            if self.stop_event.is_set():
                break
            if not self._link_allowed(link):
                continue
            await self.scheduler.add(link)

    async def _process_url(self, url: str, page):
        try:
            await goto(
                page,
                url,
                wait_until=self.wait_until,
                timeout=self.timeout,
                settle_delay=self.settle_delay,
            )
        except Exception as e:
            logger.warning("Failed to load %s: %s", url, e)
            return

        if self.enable_human_behaviors:
            await self._simulate_human_behavior_before_parse(page)

        links = await self.spider.parse(page)

        if self.enable_human_behaviors:
            await self._simulate_human_behavior_after_parse(page)

        await self._extract_and_store(url, page)
        await self._schedule_links(links)

    async def worker(self):
        while not self.stop_event.is_set():
            url = await self._next_url()
            if url is None:
                await asyncio.sleep(0.05)
                continue

            try:
                page = await self._acquire_page(url)
            except BrowserPoolExhausted:
                await self._release_worker_slot()
                raise
            if page is None:
                await self._release_worker_slot()
                continue

            try:
                await self._process_url(url, page)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.warning(
                    "Worker error processing %s: [%s] %s", url, type(e).__name__, e
                )
            finally:
                await self.pool.release(page)
                await self._release_worker_slot()

    def _spawn_workers(self) -> list:
        return [asyncio.create_task(self.worker()) for _ in range(self.concurrency)]

    def _make_progress_bar(self):
        return make_progress_bar(
            total=self.max_links,
            desc="Crawling",
            unit="page",
            show_progress=self.show_progress,
        )

    async def run(self) -> list:
        if self.max_links <= 0:
            return []

        tasks = self._spawn_workers()
        pbar = self._make_progress_bar()

        async def monitor():
            last = 0
            while not all(task.done() for task in tasks):
                async with self.lock:
                    current = len(self.results)
                if current > last:
                    pbar.update(current - last)
                    last = current
                await asyncio.sleep(0.2)
            async with self.lock:
                current = len(self.results)
            if current > last:
                pbar.update(current - last)

        monitor_task = asyncio.create_task(monitor())

        results = await asyncio.gather(*tasks, return_exceptions=True)
        await monitor_task
        pbar.close()

        for result in results:
            if isinstance(result, Exception):
                logger.warning(
                    "Worker task failed: [%s] %s", type(result).__name__, result
                )

        if self._fatal_error is not None:
            raise self._fatal_error

        return self.content

    async def stream(self) -> AsyncGenerator[dict, None]:
        if self.max_links <= 0:
            return

        tasks = self._spawn_workers()
        pbar = self._make_progress_bar()

        try:
            while True:
                try:
                    item = await asyncio.wait_for(
                        self.stream_queue.get(),
                        timeout=0.5,
                    )
                    pbar.update(1)
                    yield item

                except asyncio.TimeoutError:
                    if all(task.done() for task in tasks) and self.stream_queue.empty():
                        break

        finally:
            self.stop_event.set()
            for task in tasks:
                if not task.done():
                    task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for result in results:
                    if isinstance(result, Exception) and not isinstance(
                        result, asyncio.CancelledError
                    ):
                        logger.warning(
                            "Worker task failed: [%s] %s", type(result).__name__, result
                        )
            pbar.close()

            if self._fatal_error is not None:
                raise self._fatal_error


class Crawler(BaseEngine):
    """Crawls a site and returns all content with no filtering.

    Supports optional proxy configuration via ``Settings.proxy`` for
    anonymised crawling. Acts as the primary crawler entry-point.

    Attributes:
        settings (Settings): Configuration for the crawl.
        strategy (Optional[Any]): The content-extraction strategy in use
            (``HeuristicStrategy`` or ``GenerativeAIStrategy``); set on ``start()``.
        browser (Optional[GoogleChrome]): The shared browser instance; set on
            ``start()``.

    Example:
        ```python
        from onecrawler import Crawler, Settings

        async with Crawler(Settings()) as crawler:
            results = await crawler.run("https://example.com")
            print(results)
        ```

        Streaming:

        ```python
        async with Crawler(Settings()) as crawler:
            async for result in crawler.stream("https://example.com"):
                print(result)
        ```
    """

    def __init__(self, settings):
        """Initializes the crawler with the given settings.

        Args:
            settings (Settings): Configuration for the crawl.
        """
        super().__init__()
        self.settings = settings
        self.strategy = None
        self.browser = None
        self.session = None
        self.logger.info("Crawler initialized")

    async def start(self):
        """Starts the browser and initializes the configured scraping strategy.

        Raises:
            ValueError: If ``scraping_strategy`` is ``"genai"`` but
                ``settings.genai`` is not configured, or an unknown strategy
                is requested.
        """
        self._closed = False

        scraping_strategy = getattr(
            self.settings, "scraping_strategy", ScrapingStrategy.HEURISTIC
        )
        if not isinstance(scraping_strategy, str):
            scraping_strategy = ScrapingStrategy.HEURISTIC

        if scraping_strategy == ScrapingStrategy.GENAI:
            if not getattr(self.settings, "genai", None):
                raise ValueError("GenAI settings is required for GenAI strategy")
        elif scraping_strategy not in (
            ScrapingStrategy.HEURISTIC,
            ScrapingStrategy.MARKDOWNIFY,
        ):
            raise ValueError(f"Unknown strategy: {scraping_strategy}")

        self.browser = GoogleChrome(
            self.settings.browser_settings,
            proxy_pool=self.settings.create_proxy_pool(),
        )
        await self.browser.start()

        if scraping_strategy == ScrapingStrategy.HEURISTIC:
            strategy = HeuristicStrategy(
                settings=self.settings,
                browser=self.browser,
            )
        elif scraping_strategy == ScrapingStrategy.MARKDOWNIFY:
            strategy = MarkdownifyStrategy(
                settings=self.settings,
                browser=self.browser,
            )
        else:
            strategy = GenerativeAIStrategy(
                provider=self.settings.genai.provider,
                model_name=self.settings.genai.model_name,
                max_retries=self.settings.max_retries,
                api_key=self.settings.genai.api_key,
                base_url=self.settings.genai.base_url,
                output_schema=self.settings.genai.output_schema,
                provider_kwargs=self.settings.genai.provider_kwargs,
                timeout=self.settings.genai.timeout,
                think=self.settings.genai.think,
                exclude_selectors=self.settings.exclude_selectors,
                browser=self.browser,
            )
            await strategy.initialize()

        self.strategy = strategy

    async def close(self):
        """Closes the scraping strategy and the browser."""
        if self.strategy:
            await self.strategy.close()

        if self.browser:
            await self.browser.close()

    async def _create_runtime(
        self,
        url: str,
        streaming: bool = False,
        content_filter: Optional[Callable[[dict], bool]] = None,
    ) -> Tuple[CrawlerRuntime, BrowserPool]:
        parsed = urlparse(url)
        base_prefix = f"{parsed.scheme}://{parsed.netloc}"

        scheduler = BFScheduler(url)
        spider = LinkSpider(base_prefix)
        pool = BrowserPool(self.browser, self.settings.concurrency)
        await pool.init()

        runtime = CrawlerRuntime(
            scheduler=scheduler,
            pool=pool,
            spider=spider,
            strategy=self.strategy,
            base_prefix=base_prefix,
            max_links=self.settings.link_extraction_limit,
            include_pattern=self.settings.include_link_patterns,
            exclude_pattern=self.settings.exclude_link_patterns,
            enable_human_behaviors=self.settings.human_behavior_settings is not None,
            human_behavior_settings=self.settings.human_behavior_settings,
            concurrency=self.settings.concurrency,
            streaming=streaming,
            content_filter=content_filter,
            wait_until=self.settings.browser_settings.wait_until,
            timeout=self.settings.browser_settings.timeout,
            settle_delay=self.settings.browser_settings.settle_delay,
            show_progress=self.settings.show_progress,
        )
        return runtime, pool

    async def run(self, url: str, filters=None) -> list[dict]:
        """Crawls ``url`` and collects all extracted content.

        Args:
            url (str): The starting URL; the crawl stays within its origin.
            filters (Optional[Callable[[dict], bool]]): Predicate applied to
                each extracted content dict post-extraction, pre-collection;
                items failing it are dropped. See ``onecrawler.filters``.

        Returns:
            list[dict]: Extracted content dicts, each including its source
            ``url``.
        """
        self._ensure_open()
        runtime, pool = await self._create_runtime(url, content_filter=filters)
        try:
            return await runtime.run()
        finally:
            await pool.close()

    async def stream(self, url: str, filters=None) -> AsyncGenerator[dict, None]:
        """Crawls ``url``, yielding extracted content dicts as they arrive.

        Args:
            url (str): The starting URL; the crawl stays within its origin.
            filters (Optional[Callable[[dict], bool]]): Predicate applied to
                each extracted content dict post-extraction, pre-yield; items
                failing it are dropped. See ``onecrawler.filters``.

        Yields:
            dict: An extracted content dict, including its source ``url``.
        """
        self._ensure_open()
        runtime, pool = await self._create_runtime(
            url, streaming=True, content_filter=filters
        )
        try:
            async for item in runtime.stream():
                yield item
        finally:
            await pool.close()
