import pytest

from tests._support import load_settings_modules

browser_module, genai_module, crawler_module = load_settings_modules()


class TestCrawlerSettings:
    def test_defaults_create_independent_browser_settings(self):
        first = crawler_module.CrawlerSettings()
        second = crawler_module.CrawlerSettings()

        first.browser_settings.launch.args.append("--first-only")

        assert "--first-only" in first.browser_settings.launch.args
        assert "--first-only" not in second.browser_settings.launch.args

    def test_genai_strategy_requires_genai_settings(self):
        with pytest.raises(ValueError, match="genai settings is required"):
            crawler_module.CrawlerSettings(scraping_strategy="genai")

    def test_genai_strategy_requires_json_output(self):
        settings = genai_module.GenerativeAISettings(
            provider="openai",
            model_name="test-model",
            api_key="test-key",
        )

        with pytest.raises(ValueError, match="only supports JSON"):
            crawler_module.CrawlerSettings(
                scraping_strategy="genai",
                scraping_output_format="markdown",
                genai=settings,
            )

    def test_valid_genai_settings_are_accepted(self):
        genai_settings = genai_module.GenerativeAISettings(
            provider="google",
            model_name="gemini-test",
            api_key="test-key",
        )

        settings = crawler_module.CrawlerSettings(
            scraping_strategy="genai", genai=genai_settings
        )

        assert settings.genai == genai_settings
        assert settings.scraping_output_format == "json"

    def test_single_proxy_is_attached_to_browser_settings(self):
        proxy = browser_module.ProxySettings(server="http://proxy.example:8080")

        settings = crawler_module.CrawlerSettings(proxy=proxy)

        assert settings.browser_settings.proxy == proxy

    def test_multiple_proxies_use_round_robin_pool(self):
        first = browser_module.ProxySettings(server="http://proxy-1.example:8080")
        second = browser_module.ProxySettings(server="http://proxy-2.example:8080")

        settings = crawler_module.CrawlerSettings(proxies=[first, second])
        pool = settings.create_proxy_pool()

        assert pool.next() == first
        assert pool.next() == second
        assert pool.next() == first

    def test_proxy_and_proxies_are_mutually_exclusive(self):
        proxy = browser_module.ProxySettings(server="http://proxy.example:8080")

        with pytest.raises(ValueError, match="either proxy or proxies"):
            crawler_module.CrawlerSettings(proxy=proxy, proxies=[proxy])
