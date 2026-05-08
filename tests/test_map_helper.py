import unittest

from tests._support import load_module

helper_module = load_module("tests.loaded_map_helper", "onecrawler/map/helper.py")


class MapHelperTests(unittest.TestCase):
    def test_normalize_url_lowercases_origin_and_removes_fragment(self):
        self.assertEqual(
            helper_module.normalize_url(" HTTPS://Example.COM/News/Story/?a=1#top "),
            "https://example.com/News/Story?a=1",
        )

    def test_normalize_url_preserves_root_path(self):
        self.assertEqual(
            helper_module.normalize_url("https://Example.com/#x"),
            "https://example.com/",
        )

    def test_same_origin_compares_netloc(self):
        self.assertTrue(
            helper_module.is_same_origin(
                "https://example.com/path",
                "http://example.com/other",
            )
        )
        self.assertFalse(
            helper_module.is_same_origin(
                "https://www.example.com/path",
                "https://example.com/other",
            )
        )

    def test_sitemap_url_detection(self):
        self.assertTrue(
            helper_module.looks_like_sitemap("https://example.com/sitemap-news")
        )
        self.assertTrue(helper_module.is_xml_url("https://example.com/sitemap.xml.gz"))
        self.assertFalse(helper_module.is_xml_url("https://example.com/news/story"))

    def test_url_record_sets_discovered_timestamp(self):
        record = helper_module.URLRecord(url="https://example.com", source="test")

        self.assertEqual(record.url, "https://example.com")
        self.assertEqual(record.source, "test")
        self.assertIsInstance(record.discovered_at, str)


if __name__ == "__main__":
    unittest.main()
