import unittest

from tests._support import load_config_modules

_, genai_module, crawler_module = load_config_modules()


class CrawlerSettingsTests(unittest.TestCase):
    def test_defaults_create_independent_browser_settings(self):
        first = crawler_module.CrawlerSettings()
        second = crawler_module.CrawlerSettings()

        first.browser_settings.launch.args.append("--first-only")

        self.assertIn("--first-only", first.browser_settings.launch.args)
        self.assertNotIn("--first-only", second.browser_settings.launch.args)

    def test_genai_strategy_requires_genai_settings(self):
        with self.assertRaisesRegex(ValueError, "genai config is required"):
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
        settings = genai_module.GenerativeAISettings(
            provider="google",
            model_name="gemini-test",
            api_key="test-key",
        )

        config = crawler_module.CrawlerSettings(
            scraping_strategy="genai", genai=settings
        )

        self.assertEqual(config.genai, settings)
        self.assertEqual(config.scraping_output_format, "json")


if __name__ == "__main__":
    unittest.main()
