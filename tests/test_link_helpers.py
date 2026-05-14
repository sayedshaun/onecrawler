from tests._support import load_link_modules

helper_module, _ = load_link_modules()


class TestWildcardLinkMatch:
    def test_empty_patterns_accept_same_site_links(self):
        assert helper_module.wildcard_link_match(
            "https://example.com/news/story",
            "https://example.com",
            [],
        )

    def test_patterns_are_matched_against_path(self):
        assert helper_module.wildcard_link_match(
            "https://example.com/sports/football",
            "https://example.com",
            ["/sports/*"],
        )
        assert not helper_module.wildcard_link_match(
            "https://example.com/tech/ai",
            "https://example.com",
            ["/sports/*"],
        )

    def test_rejects_external_or_non_string_links(self):
        assert not helper_module.wildcard_link_match(
            "https://other.example.com/sports",
            "https://example.com",
            [],
        )
        assert not helper_module.wildcard_link_match(None, "https://example.com", [])
