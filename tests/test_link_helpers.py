import unittest

from tests._support import load_link_modules

helper_module, _ = load_link_modules()


class WildcardLinkMatchTests(unittest.TestCase):
    def test_empty_patterns_accept_same_site_links(self):
        self.assertTrue(
            helper_module.wildcard_link_match(
                "https://example.com/news/story",
                "https://example.com",
                [],
            )
        )

    def test_patterns_are_matched_against_path(self):
        self.assertTrue(
            helper_module.wildcard_link_match(
                "https://example.com/sports/football",
                "https://example.com",
                ["/sports/*"],
            )
        )
        self.assertFalse(
            helper_module.wildcard_link_match(
                "https://example.com/tech/ai",
                "https://example.com",
                ["/sports/*"],
            )
        )

    def test_rejects_external_or_non_string_links(self):
        self.assertFalse(
            helper_module.wildcard_link_match(
                "https://other.example.com/sports",
                "https://example.com",
                [],
            )
        )
        self.assertFalse(
            helper_module.wildcard_link_match(None, "https://example.com", [])
        )


if __name__ == "__main__":
    unittest.main()
