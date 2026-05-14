from tests._support import load_module

helper_module = load_module(
    "tests.loaded_map_helper", "onecrawler/crawler/map/helper.py"
)


class TestMapHelper:
    def test_normalize_url_lowercases_origin_and_removes_fragment(self):
        assert (
            helper_module.normalize_url(" HTTPS://Example.COM/News/Story/?a=1#top ")
            == "https://example.com/News/Story?a=1"
        )

    def test_normalize_url_preserves_root_path(self):
        assert helper_module.normalize_url("https://Example.com/#x") == (
            "https://example.com/"
        )

    def test_same_origin_compares_netloc(self):
        assert helper_module.is_same_origin(
            "https://example.com/path",
            "http://example.com/other",
        )
        assert not helper_module.is_same_origin(
            "https://www.example.com/path",
            "https://example.com/other",
        )

    def test_sitemap_url_detection(self):
        assert helper_module.looks_like_sitemap("https://example.com/sitemap-news")
        assert helper_module.is_xml_url("https://example.com/sitemap.xml.gz")
        assert not helper_module.is_xml_url("https://example.com/news/story")

    def test_url_record_sets_discovered_timestamp(self):
        record = helper_module.URLRecord(url="https://example.com", source="test")

        assert record.url == "https://example.com"
        assert record.source == "test"
        assert isinstance(record.discovered_at, str)
