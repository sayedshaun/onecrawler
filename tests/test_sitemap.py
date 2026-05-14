import importlib.util

import pytest

from tests._support import (
    ensure_package,
    install_curl_cffi_stub,
    load_link_modules,
    load_module,
    load_settings_modules,
)


def load_sitemap_module():
    if importlib.util.find_spec("lxml") is None:
        pytest.skip("lxml is not installed")

    ensure_package("onecrawler")
    ensure_package("onecrawler.crawler.map")
    load_settings_modules()
    load_link_modules()
    load_module("onecrawler.crawler.map.helper", "onecrawler/crawler/map/helper.py")
    install_curl_cffi_stub()
    return load_module(
        "onecrawler.crawler.map.sitemap", "onecrawler/crawler/map/sitemap.py"
    )


class TestSitemapParser:
    @classmethod
    def setup_class(cls):
        cls.sitemap_module = load_sitemap_module()
        # Import ProxySettings from settings module for tests
        cls.proxy_settings = load_module(
            "onecrawler.settings.proxy", "onecrawler/settings/proxy.py"
        ).ProxySettings

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

        assert children == []
        assert len(records) == 1
        assert records[0].url == "https://example.com/a"
        assert records[0].lastmod == "2026-01-01"
        assert records[0].changefreq == "daily"
        assert records[0].priority == "0.8"

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

        assert records == []
        assert children == ["https://example.com/child.xml"]

    def test_regex_extract_is_used_for_unknown_documents(self):
        parser = self.sitemap_module.SitemapParser(client=None, concurrency=1)
        records, children = parser._parse_xml(
            b'<html><a href="https://example.com/from-html">link</a></html>',
            "https://example.com/not-a-sitemap",
        )

        assert children == []
        assert [record.url for record in records] == ["https://example.com/from-html"]

    @pytest.mark.asyncio
    async def test_robots_parser_extracts_sitemap_directives(self):
        class Client:
            async def get_text(self, url):
                return """
                User-agent: *
                Sitemap: https://example.com/sitemap.xml
                Sitemap: https://example.com/news.xml
                """

        parser = self.sitemap_module.RobotsParser(Client())

        result = await parser.fetch_sitemaps("https://example.com")

        assert result == [
            "https://example.com/sitemap.xml",
            "https://example.com/news.xml",
        ]

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

        assert result == ["https://example.com/a", "https://example.com/b"]

    def test_universal_sitemap_normalizes_base_url(self):
        assert (
            self.sitemap_module.UniversalSiteMap._normalize_base("example.com/path")
            == "https://example.com"
        )
        assert (
            self.sitemap_module.UniversalSiteMap._normalize_base(
                "http://example.com/path"
            )
            == "http://example.com"
        )

    @pytest.mark.asyncio
    async def test_http_client_applies_rotating_proxy_to_requests(self):
        first = self.proxy_settings(server="http://proxy-1.example:8080")
        second = self.proxy_settings(
            server="http://proxy-2.example:8080",
            username="user",
            password="pass",
        )

        class Response:
            status_code = 200
            content = b"ok"
            headers = {}

        class Session:
            def __init__(self):
                self.calls = []

            async def get(self, url, **kwargs):
                self.calls.append(kwargs)
                return Response()

        client = self.sitemap_module.HTTPClient(
            concurrency=1,
            timeout=10,
            user_agent="test",
            retries=1,
            retry_delay=0,
            proxy_pool=self.sitemap_module.ProxyPool([first, second]),
        )
        client._session = Session()

        await client.get("https://example.com/a")
        await client.get("https://example.com/b")

        assert client._session.calls[0]["proxies"] == {
            "http": "http://proxy-1.example:8080",
            "https": "http://proxy-1.example:8080",
        }
        assert client._session.calls[1]["proxies"] == {
            "http": "http://user:pass@proxy-2.example:8080",
            "https": "http://user:pass@proxy-2.example:8080",
        }
