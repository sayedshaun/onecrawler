import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests._support import (
    ensure_package,
    install_trafilatura_stub,
    load_module,
    load_settings_modules,
)


def load_pipeline_modules():
    """Load required modules for Crawler testing"""
    try:
        # Try to import from main package first
        import onecrawler

        if hasattr(onecrawler, "Crawler"):
            return onecrawler
    except ImportError as e:
        pass

    # If main package fails due to missing dependencies or has been stubbed by
    # another test module, load the Crawler module directly.
    ensure_package("onecrawler")
    ensure_package("onecrawler.settings")
    ensure_package("onecrawler.crawler")
    ensure_package("onecrawler.crawler.link")
    ensure_package("onecrawler.crawler.scraper")
    ensure_package("onecrawler.crawler.scraper.heuristic")
    load_settings_modules()
    install_trafilatura_stub()

    mock_module = MagicMock()

    crawl_module = load_module(
        "onecrawler.crawler.crawl", "onecrawler/crawler/crawl.py"
    )

    for attr in ("Crawler", "CrawlerRuntime", "Pipeline", "PipelineRuntime"):
        if hasattr(crawl_module, attr):
            setattr(mock_module, attr, getattr(crawl_module, attr))

    return mock_module


class TestPipeline:
    @classmethod
    def setup_class(cls):
        install_trafilatura_stub()
        cls.onecrawler_module = load_pipeline_modules()
        cls.pipeline_module = load_module(
            "onecrawler.crawler.crawl", "onecrawler/crawler/crawl.py"
        )

        # Load settings modules
        cls.settings_module = load_module(
            "onecrawler.settings.crawler", "onecrawler/settings/crawler.py"
        )
        cls.browser_settings_module = load_module(
            "onecrawler.settings.browser", "onecrawler/settings/browser.py"
        )
        cls.simulation_settings_module = load_module(
            "onecrawler.settings.simulation", "onecrawler/settings/simulation.py"
        )

        # Skip if Crawler is not available
        if not hasattr(cls.onecrawler_module, "Crawler"):
            pytest.skip("Crawler not available due to missing dependencies")

    def setup_method(self):
        """Set up test fixtures before each test method."""
        # Create mock settings
        self.mock_browser_settings = MagicMock()
        self.mock_crawler_settings = self.settings_module.Settings(
            concurrency=2,
            link_extraction_limit=5,
            include_link_patterns=["/news/*"],
            human_behavior_settings=self.simulation_settings_module.HumanBehaviorSettings(),
        )

        # Create settings object with browser_settings attribute
        self.mock_settings = MagicMock()
        self.mock_settings.browser_settings = self.mock_browser_settings
        self.mock_settings.concurrency = 2
        self.mock_settings.link_extraction_limit = 5
        self.mock_settings.include_link_patterns = ["/news/*"]
        self.mock_settings.exclude_link_patterns = None
        self.mock_settings.scraping_strategy = "heuristic"
        self.mock_settings.genai = None
        self.mock_settings.max_retries = 2
        self.mock_settings.human_behavior_settings = (
            self.simulation_settings_module.HumanBehaviorSettings()
        )

    @pytest.mark.asyncio
    async def test_pipeline_engine_initialization(self):
        """Test Crawler can be initialized with basic settings."""
        engine = self.onecrawler_module.Crawler(self.mock_settings)

        assert engine.settings == self.mock_settings
        assert engine.strategy is None
        assert engine.session is None

    @pytest.mark.asyncio
    async def test_pipeline_engine_initialization_with_date_filters(self):
        """Test Crawler initialization with date filters via sitemap settings."""
        from datetime import date

        self.mock_settings.sitemap = self.settings_module.SitemapSettings(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
        )

        engine = self.onecrawler_module.Crawler(self.mock_settings)

        assert engine.settings.sitemap.start_date == date(2024, 1, 1)
        assert engine.settings.sitemap.end_date == date(2024, 12, 31)

    @pytest.mark.asyncio
    async def test_pipeline_engine_start_initializes_browser_and_strategy(self):
        """Test that start() method properly initializes browser and strategy."""
        engine = self.onecrawler_module.Crawler(self.mock_settings)

        # Mock GoogleChrome and HeuristicStrategy where Crawler imports them
        with (
            patch("onecrawler.crawler.crawl.GoogleChrome") as mock_chrome,
            patch("onecrawler.crawler.crawl.HeuristicStrategy") as mock_strategy,
        ):
            mock_chrome_instance = AsyncMock()
            mock_chrome.return_value = mock_chrome_instance
            mock_strategy_instance = MagicMock()
            mock_strategy.return_value = mock_strategy_instance

            await engine.start()

            # Verify browser was created and started
            mock_chrome.assert_called_once_with(
                self.mock_browser_settings,
                proxy_pool=self.mock_settings.create_proxy_pool(),
            )
            mock_chrome_instance.start.assert_called_once()

            # Verify strategy was created with correct parameters
            mock_strategy.assert_called_once_with(
                settings=self.mock_settings, browser=mock_chrome_instance
            )

            # Verify engine attributes are set
            assert engine.browser == mock_chrome_instance
            assert engine.strategy == mock_strategy_instance

    @pytest.mark.asyncio
    async def test_pipeline_engine_start_initializes_genai_strategy(self):
        """Test that start() initializes GenAI strategy when configured."""
        self.mock_settings.scraping_strategy = "genai"
        self.mock_settings.genai = MagicMock()
        engine = self.onecrawler_module.Crawler(self.mock_settings)

        with (
            patch("onecrawler.crawler.crawl.GoogleChrome") as mock_chrome,
            patch("onecrawler.crawler.crawl.LLMStrategy") as mock_strategy,
            patch("onecrawler.crawler.crawl.HeuristicStrategy") as mock_heuristic,
        ):
            mock_chrome_instance = AsyncMock()
            mock_chrome.return_value = mock_chrome_instance
            mock_strategy_instance = MagicMock()
            mock_strategy_instance.initialize = AsyncMock()
            mock_strategy.return_value = mock_strategy_instance

            await engine.start()

            mock_chrome.assert_called_once_with(
                self.mock_browser_settings,
                proxy_pool=self.mock_settings.create_proxy_pool(),
            )
            mock_chrome_instance.start.assert_called_once()
            mock_strategy.assert_called_once_with(
                provider=self.mock_settings.genai.provider,
                model_name=self.mock_settings.genai.model_name,
                max_retries=self.mock_settings.max_retries,
                api_key=self.mock_settings.genai.api_key,
                base_url=self.mock_settings.genai.base_url,
                output_schema=self.mock_settings.genai.output_schema,
                provider_kwargs=self.mock_settings.genai.provider_kwargs,
                timeout=self.mock_settings.genai.timeout,
                think=self.mock_settings.genai.think,
                exclude_selectors=self.mock_settings.exclude_selectors,
                browser=mock_chrome_instance,
            )
            mock_strategy_instance.initialize.assert_called_once()
            mock_heuristic.assert_not_called()

            assert engine.browser == mock_chrome_instance
            assert engine.strategy == mock_strategy_instance

    @pytest.mark.asyncio
    async def test_pipeline_engine_close_cleans_up_resources(self):
        """Test that close() method properly cleans up browser resources."""
        engine = self.onecrawler_module.Crawler(self.mock_settings)

        # Mock browser
        mock_browser = AsyncMock()
        engine.browser = mock_browser

        await engine.close()

        mock_browser.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_pipeline_engine_close_with_no_browser(self):
        """Test that close() handles case when browser is not initialized."""
        engine = self.onecrawler_module.Crawler(self.mock_settings)

        # Should not raise exception
        await engine.close()

    @pytest.mark.asyncio
    async def test_pipeline_engine_run_requires_engine_to_be_open(self):
        """Test that run() method raises error when engine is not started."""
        engine = self.onecrawler_module.Crawler(self.mock_settings)

        with pytest.raises(RuntimeError):
            await engine.run("https://example.com")

    @pytest.mark.asyncio
    async def test_pipeline_engine_run_with_valid_url(self):
        """Test that run() method executes Crawler with valid URL."""
        engine = self.onecrawler_module.Crawler(self.mock_settings)

        # Mock all dependencies
        with (
            patch("onecrawler.crawler.crawl.GoogleChrome") as mock_chrome,
            patch("onecrawler.crawler.crawl.HeuristicStrategy") as mock_strategy,
            patch("onecrawler.crawler.crawl.BFScheduler") as mock_scheduler,
            patch("onecrawler.crawler.crawl.LinkSpider") as mock_spider,
            patch("onecrawler.crawler.crawl.BrowserPool") as mock_pool,
        ):
            # Setup mocks
            mock_chrome_instance = AsyncMock()
            mock_chrome.return_value = mock_chrome_instance
            mock_strategy_instance = MagicMock()
            mock_strategy.return_value = mock_strategy_instance

            mock_scheduler_instance = AsyncMock()
            mock_scheduler.return_value = mock_scheduler_instance

            mock_spider_instance = MagicMock()
            mock_spider.return_value = mock_spider_instance

            mock_pool_instance = AsyncMock()
            mock_pool.return_value = mock_pool_instance

            # Mock CrawlerRuntime
            mock_runtime = AsyncMock()
            mock_runtime.run.return_value = [
                {"url": "https://example.com/test", "content": "test"}
            ]

            with patch(
                "onecrawler.crawler.crawl.CrawlerRuntime", return_value=mock_runtime
            ) as mock_runtime_cls:
                await engine.start()
                result = await engine.run("https://example.com")

                assert result == [
                    {"url": "https://example.com/test", "content": "test"}
                ]
                assert (
                    mock_runtime_cls.call_args.kwargs["strategy"]
                    == mock_strategy_instance
                )
                mock_runtime.run.assert_called_once()

    @pytest.mark.asyncio
    async def test_pipeline_runtime_date_filtering(self):
        """Test CrawlerRuntime correctly filters content by date range via content_filter."""
        import datetime

        start_obj = datetime.datetime.strptime("2024-01-01", "%Y-%m-%d")
        end_obj = datetime.datetime.strptime("2024-12-31", "%Y-%m-%d")

        def date_filter(content):
            date_str = content.get("filedate") or content.get("date")
            if not date_str:
                return False
            try:
                date_obj = datetime.datetime.strptime(date_str, "%Y-%m-%d")
            except (ValueError, TypeError):
                return False
            if date_obj < start_obj:
                return False
            if date_obj > end_obj:
                return False
            return True

        runtime = self.pipeline_module.CrawlerRuntime(
            scheduler=AsyncMock(),
            pool=AsyncMock(),
            spider=MagicMock(),
            strategy=AsyncMock(),
            base_prefix="https://example.com",
            max_links=5,
            include_pattern=None,
            enable_human_behaviors=False,
            human_behavior_settings=self.simulation_settings_module.HumanBehaviorSettings(),
            concurrency=1,
            content_filter=date_filter,
        )

        # Test valid date within range
        valid_content = {"filedate": "2024-06-15", "url": "https://example.com/test"}
        assert runtime.content_filter(valid_content)

        # Test date before range
        invalid_content_early = {
            "filedate": "2023-12-31",
            "url": "https://example.com/test",
        }
        assert not runtime.content_filter(invalid_content_early)

        # Test date after range
        invalid_content_late = {
            "filedate": "2025-01-01",
            "url": "https://example.com/test",
        }
        assert not runtime.content_filter(invalid_content_late)

        # Test content without date
        no_date_content = {"url": "https://example.com/test"}
        assert not runtime.content_filter(no_date_content)

    @pytest.mark.asyncio
    async def test_pipeline_runtime_invalid_date_format(self):
        """Test CrawlerRuntime content_filter handles invalid date formats gracefully."""
        import datetime

        start_obj = datetime.datetime.strptime("2024-01-01", "%Y-%m-%d")
        end_obj = datetime.datetime.strptime("2024-12-31", "%Y-%m-%d")

        def date_filter(content):
            date_str = content.get("filedate") or content.get("date")
            if not date_str:
                return False
            try:
                datetime.datetime.strptime(date_str, "%Y-%m-%d")
            except (ValueError, TypeError):
                return False
            return True

        runtime = self.pipeline_module.CrawlerRuntime(
            scheduler=AsyncMock(),
            pool=AsyncMock(),
            spider=MagicMock(),
            strategy=AsyncMock(),
            base_prefix="https://example.com",
            max_links=5,
            include_pattern=None,
            enable_human_behaviors=False,
            human_behavior_settings=self.simulation_settings_module.HumanBehaviorSettings(),
            concurrency=1,
            content_filter=date_filter,
        )

        # Test invalid date format
        invalid_format_content = {
            "filedate": "invalid-date",
            "url": "https://example.com/test",
        }
        assert not runtime.content_filter(invalid_format_content)

    @pytest.mark.asyncio
    async def test_pipeline_runtime_no_date_filtering(self):
        """Test CrawlerRuntime accepts all content when content_filter is None."""
        runtime = self.pipeline_module.CrawlerRuntime(
            scheduler=AsyncMock(),
            pool=AsyncMock(),
            spider=MagicMock(),
            strategy=AsyncMock(),
            base_prefix="https://example.com",
            max_links=5,
            include_pattern=None,
            enable_human_behaviors=False,
            human_behavior_settings=self.simulation_settings_module.HumanBehaviorSettings(),
            concurrency=1,
            content_filter=None,
        )

        # When content_filter is None, no filtering is applied
        assert runtime.content_filter is None

        # Both items pass when there is no filter
        content_no_date = {"url": "https://example.com/test"}
        assert runtime.content_filter is None or runtime.content_filter(content_no_date)

    @pytest.mark.asyncio
    async def test_worker_reuses_loaded_page_html(self):
        """The worker hands the already-loaded page's HTML to the strategy
        instead of letting it navigate to the URL a second time."""
        html_marker = "<html><body>REUSED</body></html>"

        class FakePage:
            async def goto(self, *args, **kwargs):
                return None

            async def content(self):
                return html_marker

        pool = AsyncMock()
        pool.acquire = AsyncMock(return_value=FakePage())
        pool.release = AsyncMock()

        pending = ["https://example.com/news/1"]

        async def fake_next():
            return pending.pop(0) if pending else None

        scheduler = AsyncMock()
        scheduler.next = fake_next
        scheduler.has_next = AsyncMock(return_value=False)

        spider = MagicMock()
        spider.parse = AsyncMock(return_value=[])

        strategy = AsyncMock()
        strategy.extract = AsyncMock(return_value={"text": "extracted"})

        runtime = self.pipeline_module.CrawlerRuntime(
            scheduler=scheduler,
            pool=pool,
            spider=spider,
            strategy=strategy,
            base_prefix="https://example.com",
            max_links=1,
            include_pattern=None,
            enable_human_behaviors=False,
            human_behavior_settings=self.simulation_settings_module.HumanBehaviorSettings(),
            concurrency=1,
            content_filter=None,
        )

        await runtime.worker()

        strategy.extract.assert_awaited_once()
        args, kwargs = strategy.extract.call_args
        assert args[0] == "https://example.com/news/1"
        assert kwargs.get("html") == html_marker

    @pytest.mark.asyncio
    async def test_run_never_exceeds_max_links_under_concurrency(self):
        """Regression test: workers used to check the max_links cap only
        AFTER unconditionally appending, so several concurrent workers could
        all pass the cap simultaneously and overshoot it. A real (if tiny)
        delay in extraction is required to force genuine task interleaving —
        awaiting an already-resolved coroutine does not yield to sibling
        tasks, so purely instant mocks would never exercise the race."""
        max_links = 5
        concurrency = 10
        pending = [f"https://example.com/page-{i}" for i in range(30)]

        async def fake_next():
            return pending.pop(0) if pending else None

        scheduler = AsyncMock()
        scheduler.next = fake_next
        scheduler.has_next = AsyncMock(side_effect=lambda: bool(pending))

        class FakePage:
            async def goto(self, *args, **kwargs):
                return None

            async def content(self):
                return "<html><body>x</body></html>"

        pool = AsyncMock()
        pool.acquire = AsyncMock(return_value=FakePage())
        pool.release = AsyncMock()

        spider = MagicMock()
        spider.parse = AsyncMock(return_value=[])

        async def slow_extract(url, html=None):
            await asyncio.sleep(0.01)
            return {"text": "extracted"}

        strategy = AsyncMock()
        strategy.extract = AsyncMock(side_effect=slow_extract)

        runtime = self.pipeline_module.CrawlerRuntime(
            scheduler=scheduler,
            pool=pool,
            spider=spider,
            strategy=strategy,
            base_prefix="https://example.com",
            max_links=max_links,
            include_pattern=None,
            enable_human_behaviors=False,
            human_behavior_settings=self.simulation_settings_module.HumanBehaviorSettings(),
            concurrency=concurrency,
            content_filter=None,
            show_progress=False,
        )

        results = await runtime.run()

        assert len(results) == max_links

        content_with_date = {
            "filedate": "2024-06-15",
            "url": "https://example.com/test",
        }
        assert runtime.content_filter is None or runtime.content_filter(
            content_with_date
        )

    def test_pipeline_engine_docstring_exists(self):
        """Test that Crawler has proper documentation."""
        assert self.onecrawler_module.Crawler.__doc__ is not None
        assert "proxy" in self.onecrawler_module.Crawler.__doc__.lower()
        assert "crawler" in self.onecrawler_module.Crawler.__doc__.lower()
