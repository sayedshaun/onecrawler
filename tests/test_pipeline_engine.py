import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from tests._support import ensure_package, load_module, load_settings_modules


def load_pipeline_modules():
    """Load required modules for PipelineEngine testing"""
    try:
        # Try to import from main package first
        import onecrawler

        return onecrawler
    except ImportError as e:
        # If main package fails due to missing dependencies, load modules individually
        ensure_package("onecrawler")
        ensure_package("onecrawler.settings")
        load_settings_modules()

        # Create a mock module with PipelineEngine
        mock_module = MagicMock()

        # Load the pipeline module directly
        pipeline_module = load_module(
            "onecrawler.crawler.pipeline", "onecrawler/crawler/pipeline.py"
        )

        # Extract the classes we need
        if hasattr(pipeline_module, "PipelineEngine"):
            mock_module.PipelineEngine = pipeline_module.PipelineEngine
        if hasattr(pipeline_module, "PipelineRuntime"):
            mock_module.PipelineRuntime = pipeline_module.PipelineRuntime

        return mock_module


class PipelineEngineTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        cls.onecrawler_module = load_pipeline_modules()

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

        # Skip if PipelineEngine is not available
        if not hasattr(cls.onecrawler_module, "PipelineEngine"):
            raise unittest.SkipTest(
                "PipelineEngine not available due to missing dependencies"
            )

    def setUp(self):
        """Set up test fixtures before each test method."""
        # Create mock settings
        self.mock_browser_settings = MagicMock()
        self.mock_crawler_settings = self.settings_module.CrawlerSettings(
            concurrency=2,
            link_extraction_limit=5,
            include_link_patterns=["/news/*"],
            enable_human_behaviors=False,
            human_behavior_settings=self.simulation_settings_module.HumanBehaviorSettings(),
        )

        # Create settings object with browser_settings attribute
        self.mock_settings = MagicMock()
        self.mock_settings.browser_settings = self.mock_browser_settings
        self.mock_settings.concurrency = 2
        self.mock_settings.link_extraction_limit = 5
        self.mock_settings.include_link_patterns = ["/news/*"]
        self.mock_settings.enable_human_behaviors = False
        self.mock_settings.human_behavior_settings = (
            self.simulation_settings_module.HumanBehaviorSettings()
        )

    async def test_pipeline_engine_initialization(self):
        """Test PipelineEngine can be initialized with basic settings."""
        engine = self.onecrawler_module.PipelineEngine(self.mock_settings)

        self.assertEqual(engine.settings, self.mock_settings)
        self.assertIsNone(engine.start_date)
        self.assertIsNone(engine.end_date)
        self.assertIsNone(engine.strategy)
        self.assertIsNone(engine.session)

    async def test_pipeline_engine_initialization_with_date_filters(self):
        """Test PipelineEngine initialization with date filters."""
        start_date = "2024-01-01"
        end_date = "2024-12-31"

        engine = self.onecrawler_module.PipelineEngine(
            self.mock_settings, start_date=start_date, end_date=end_date
        )

        self.assertEqual(engine.start_date, start_date)
        self.assertEqual(engine.end_date, end_date)

    async def test_pipeline_engine_start_initializes_browser_and_strategy(self):
        """Test that start() method properly initializes browser and strategy."""
        engine = self.onecrawler_module.PipelineEngine(self.mock_settings)

        # Mock GoogleChrome and HeuristicStrategy
        with (
            patch("onecrawler.crawler.pipeline.GoogleChrome") as mock_chrome,
            patch("onecrawler.crawler.pipeline.HeuristicStrategy") as mock_strategy,
        ):

            mock_chrome_instance = AsyncMock()
            mock_chrome.return_value = mock_chrome_instance
            mock_strategy_instance = MagicMock()
            mock_strategy.return_value = mock_strategy_instance

            await engine.start()

            # Verify browser was created and started
            mock_chrome.assert_called_once_with(self.mock_browser_settings)
            mock_chrome_instance.start.assert_called_once()

            # Verify strategy was created with correct parameters
            mock_strategy.assert_called_once_with(
                settings=self.mock_settings, browser=mock_chrome_instance
            )

            # Verify engine attributes are set
            self.assertEqual(engine.browser, mock_chrome_instance)
            self.assertEqual(engine.strategy, mock_strategy_instance)

    async def test_pipeline_engine_close_cleans_up_resources(self):
        """Test that close() method properly cleans up browser resources."""
        engine = self.onecrawler_module.PipelineEngine(self.mock_settings)

        # Mock browser
        mock_browser = AsyncMock()
        engine.browser = mock_browser

        await engine.close()

        mock_browser.close.assert_called_once()

    async def test_pipeline_engine_close_with_no_browser(self):
        """Test that close() handles case when browser is not initialized."""
        engine = self.onecrawler_module.PipelineEngine(self.mock_settings)

        # Should not raise exception
        await engine.close()

    async def test_pipeline_engine_run_requires_engine_to_be_open(self):
        """Test that run() method raises error when engine is not started."""
        engine = self.onecrawler_module.PipelineEngine(self.mock_settings)

        with self.assertRaises(RuntimeError):
            await engine.run("https://example.com")

    async def test_pipeline_engine_run_with_valid_url(self):
        """Test that run() method executes pipeline with valid URL."""
        engine = self.onecrawler_module.PipelineEngine(self.mock_settings)

        # Mock all dependencies
        with (
            patch("onecrawler.crawler.pipeline.GoogleChrome") as mock_chrome,
            patch("onecrawler.crawler.pipeline.HeuristicStrategy") as mock_strategy,
            patch("onecrawler.crawler.pipeline.BFScheduler") as mock_scheduler,
            patch("onecrawler.crawler.pipeline.LinkSpider") as mock_spider,
            patch("onecrawler.crawler.pipeline.BrowserPool") as mock_pool,
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

            # Mock PipelineRuntime
            mock_runtime = AsyncMock()
            mock_runtime.run.return_value = [
                {"url": "https://example.com/test", "content": "test"}
            ]

            with patch(
                "onecrawler.crawler.pipeline.PipelineRuntime", return_value=mock_runtime
            ) as mock_runtime_cls:
                await engine.start()
                result = await engine.run("https://example.com")

                self.assertEqual(
                    result, [{"url": "https://example.com/test", "content": "test"}]
                )
                self.assertEqual(
                    mock_runtime_cls.call_args.kwargs["strategy"],
                    mock_strategy_instance,
                )
                mock_runtime.run.assert_called_once()

    async def test_pipeline_runtime_date_filtering(self):
        """Test PipelineRuntime correctly filters content by date range."""
        from datetime import datetime

        engine = self.onecrawler_module.PipelineEngine(
            self.mock_settings, start_date="2024-01-01", end_date="2024-12-31"
        )

        # Create a PipelineRuntime instance for testing
        runtime = self.onecrawler_module.PipelineRuntime(
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
            start_date="2024-01-01",
            end_date="2024-12-31",
        )

        # Test valid date within range
        valid_content = {"filedate": "2024-06-15", "url": "https://example.com/test"}
        self.assertTrue(runtime._is_valid_content(valid_content))

        # Test date before range
        invalid_content_early = {
            "filedate": "2023-12-31",
            "url": "https://example.com/test",
        }
        self.assertFalse(runtime._is_valid_content(invalid_content_early))

        # Test date after range
        invalid_content_late = {
            "filedate": "2025-01-01",
            "url": "https://example.com/test",
        }
        self.assertFalse(runtime._is_valid_content(invalid_content_late))

        # Test content without date
        no_date_content = {"url": "https://example.com/test"}
        self.assertFalse(runtime._is_valid_content(no_date_content))

    async def test_pipeline_runtime_invalid_date_format(self):
        """Test PipelineRuntime handles invalid date formats gracefully."""
        engine = self.onecrawler_module.PipelineEngine(
            self.mock_settings, start_date="2024-01-01", end_date="2024-12-31"
        )

        runtime = self.onecrawler_module.PipelineRuntime(
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
            start_date="2024-01-01",
            end_date="2024-12-31",
        )

        # Test invalid date format
        invalid_format_content = {
            "filedate": "invalid-date",
            "url": "https://example.com/test",
        }
        self.assertFalse(runtime._is_valid_content(invalid_format_content))

    async def test_pipeline_runtime_no_date_filtering(self):
        """Test PipelineRuntime accepts all content when no date filters are set."""
        runtime = self.onecrawler_module.PipelineRuntime(
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
            start_date=None,
            end_date=None,
        )

        # Should accept content without date when no filtering is applied
        content_no_date = {"url": "https://example.com/test"}
        self.assertTrue(runtime._is_valid_content(content_no_date))

        # Should accept content with date when no filtering is applied
        content_with_date = {
            "filedate": "2024-06-15",
            "url": "https://example.com/test",
        }
        self.assertTrue(runtime._is_valid_content(content_with_date))

    def test_pipeline_engine_docstring_exists(self):
        """Test that PipelineEngine has proper documentation."""
        self.assertIsNotNone(self.onecrawler_module.PipelineEngine.__doc__)
        self.assertIn("proxy", self.onecrawler_module.PipelineEngine.__doc__.lower())
        self.assertIn("crawler", self.onecrawler_module.PipelineEngine.__doc__.lower())


if __name__ == "__main__":
    unittest.main()
