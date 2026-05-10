import unittest

from tests._support import load_settings_modules

browser_module, genai_module, crawler_module = load_settings_modules()


class CrawlerSettingsTests(unittest.TestCase):
    def test_defaults_create_independent_browser_settings(self):
        first = crawler_module.CrawlerSettings()
        second = crawler_module.CrawlerSettings()

        first.browser_settings.launch.args.append("--first-only")

        self.assertIn("--first-only", first.browser_settings.launch.args)
        self.assertNotIn("--first-only", second.browser_settings.launch.args)

    def test_genai_strategy_requires_genai_settings(self):
        with self.assertRaisesRegex(ValueError, "genai settings is required"):
            crawler_module.CrawlerSettings(scraping_strategy="genai")

    def test_genai_strategy_requires_json_output(self):
        settings = genai_module.GenerativeAISettings(
            provider="openai",
            model_name="test-model",
            api_key="test-key",
        )

        with self.assertRaisesRegex(ValueError, "only supports JSON"):
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

        self.assertEqual(settings.genai, genai_settings)
        self.assertEqual(settings.scraping_output_format, "json")

    def test_single_proxy_is_attached_to_browser_settings(self):
        proxy = browser_module.ProxySettings(server="http://proxy.example:8080")

        settings = crawler_module.CrawlerSettings(proxy=proxy)

        self.assertEqual(settings.browser_settings.proxy, proxy)

    def test_multiple_proxies_use_round_robin_pool(self):
        first = browser_module.ProxySettings(server="http://proxy-1.example:8080")
        second = browser_module.ProxySettings(server="http://proxy-2.example:8080")

        settings = crawler_module.CrawlerSettings(proxies=[first, second])
        pool = settings.create_proxy_pool()

        self.assertEqual(pool.next(), first)
        self.assertEqual(pool.next(), second)
        self.assertEqual(pool.next(), first)

    def test_proxy_and_proxies_are_mutually_exclusive(self):
        proxy = browser_module.ProxySettings(server="http://proxy.example:8080")

        with self.assertRaisesRegex(ValueError, "either proxy or proxies"):
            crawler_module.CrawlerSettings(proxy=proxy, proxies=[proxy])


if __name__ == "__main__":
    unittest.main()
