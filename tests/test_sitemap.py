import importlib.util
import unittest

from tests._support import (
    ensure_package,
    install_curl_cffi_stub,
    load_config_modules,
    load_link_modules,
    load_module,
)


def load_sitemap_module():
    if importlib.util.find_spec("lxml") is None:
        raise unittest.SkipTest("lxml is not installed")

    ensure_package("onecrawler")
    ensure_package("onecrawler.map")
    load_config_modules()
    load_link_modules()
    load_module("onecrawler.map.helper", "onecrawler/map/helper.py")
    install_curl_cffi_stub()
    return load_module("onecrawler.map.sitemap", "onecrawler/map/sitemap.py")


class SitemapParserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sitemap_module = load_sitemap_module()

    def test_parse_urlset_records_metadata(self):
        parser = self.sitemap_module.SitemapParser(client=None, concurrency=1)
        records, children = parser._parse_xml(
            b"""
            <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
              <url>
                <loc>https://example.com/a</loc>
                <lastmod>2026-01-01</lastmod>
                <changefreq>daily</changefreq>
                <priority>0.8</priority>
              </url>
            </urlset>
            """,
            "https://example.com/sitemap.xml",
        )

        self.assertEqual(children, [])
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].url, "https://example.com/a")
        self.assertEqual(records[0].lastmod, "2026-01-01")
        self.assertEqual(records[0].changefreq, "daily")
        self.assertEqual(records[0].priority, "0.8")

    def test_parse_sitemap_index_returns_child_sitemaps(self):
        parser = self.sitemap_module.SitemapParser(client=None, concurrency=1)
        records, children = parser._parse_xml(
            b"""
            <sitemapindex>
              <sitemap><loc>https://example.com/child.xml</loc></sitemap>
            </sitemapindex>
            """,
            "https://example.com/sitemap.xml",
        )

        self.assertEqual(records, [])
        self.assertEqual(children, ["https://example.com/child.xml"])

    def test_regex_extract_is_used_for_unknown_documents(self):
        parser = self.sitemap_module.SitemapParser(client=None, concurrency=1)
        records, children = parser._parse_xml(
            b'<html><a href="https://example.com/from-html">link</a></html>',
            "https://example.com/not-a-sitemap",
        )

        self.assertEqual(children, [])
        self.assertEqual(
            [record.url for record in records], ["https://example.com/from-html"]
        )

    def test_robots_parser_extracts_sitemap_directives(self):
        class Client:
            async def get_text(self, url):
                return """
                User-agent: *
                Sitemap: https://example.com/sitemap.xml
                Sitemap: https://example.com/news.xml
                """

        parser = self.sitemap_module.RobotsParser(Client())

        result = self.run_async(parser.fetch_sitemaps("https://example.com"))

        self.assertEqual(
            result,
            ["https://example.com/sitemap.xml", "https://example.com/news.xml"],
        )

    def test_html_crawler_extracts_same_origin_links(self):
        html = """
        <a href="/a">A</a>
        <a href="https://example.com/b#section">B</a>
        <a href="https://other.com/c">C</a>
        <a href="mailto:test@example.com">Mail</a>
        <a href="javascript:void(0)">JS</a>
        """

        result = self.sitemap_module.HTMLCrawler._extract_links(
            html,
            "https://example.com/start",
            "https://example.com",
        )

        self.assertEqual(result, ["https://example.com/a", "https://example.com/b"])

    def test_universal_sitemap_normalizes_base_url(self):
        self.assertEqual(
            self.sitemap_module.UniversalSiteMap._normalize_base("example.com/path"),
            "https://example.com",
        )
        self.assertEqual(
            self.sitemap_module.UniversalSiteMap._normalize_base(
                "http://example.com/path"
            ),
            "http://example.com",
        )

    @staticmethod
    def run_async(awaitable):
        import asyncio

        return asyncio.run(awaitable)


if __name__ == "__main__":
    unittest.main()
