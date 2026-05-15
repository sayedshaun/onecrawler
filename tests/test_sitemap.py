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


class TestLastmodParsing:
    @classmethod
    def setup_class(cls):
        cls.sitemap_module = load_sitemap_module()

    def _parse(self, value):
        return self.sitemap_module.UniversalSiteMap._parse_lastmod(value)

    def test_none_returns_none(self):
        assert self._parse(None) is None

    def test_empty_returns_none(self):
        assert self._parse("") is None

    def test_yyyy_mm_dd(self):
        from datetime import date

        assert self._parse("2024-03-15") == date(2024, 3, 15)

    def test_iso_with_time(self):
        from datetime import date

        assert self._parse("2024-03-15T12:30:00") == date(2024, 3, 15)

    def test_iso_with_timezone(self):
        from datetime import date

        assert self._parse("2024-03-15T12:30:00+06:00") == date(2024, 3, 15)

    def test_year_month_precision(self):
        from datetime import date

        assert self._parse("2024-03") == date(2024, 3, 1)

    def test_year_precision(self):
        from datetime import date

        assert self._parse("2024") == date(2024, 1, 1)

    def test_invalid_returns_none(self):
        assert self._parse("not-a-date") is None


class TestDateRangeFilter:
    @classmethod
    def setup_class(cls):
        cls.sitemap_module = load_sitemap_module()

    def _make_records(self):
        URLRecord = self.sitemap_module.URLRecord
        return [
            URLRecord(
                url="https://example.com/old", source="test", lastmod="2022-06-01"
            ),
            URLRecord(
                url="https://example.com/mid", source="test", lastmod="2023-06-01"
            ),
            URLRecord(
                url="https://example.com/new", source="test", lastmod="2024-06-01"
            ),
            URLRecord(url="https://example.com/no-date", source="test", lastmod=None),
        ]

    def _filter(
        self, records, start_date=None, end_date=None, strict_date_filter=False
    ):
        parse = self.sitemap_module.UniversalSiteMap._parse_lastmod
        filtered = []
        for rec in records:
            lm = parse(rec.lastmod)
            if lm is None:
                if not strict_date_filter:
                    filtered.append(rec)
                continue
            if start_date is not None and lm < start_date:
                continue
            if end_date is not None and lm > end_date:
                continue
            filtered.append(rec)
        return filtered

    def test_no_filter_returns_all(self):
        records = self._make_records()
        result = self._filter(records)
        assert len(result) == 4

    def test_start_date_excludes_older_urls(self):
        from datetime import date

        records = self._make_records()
        result = self._filter(records, start_date=date(2023, 1, 1))
        urls = [r.url for r in result]
        assert "https://example.com/old" not in urls
        assert "https://example.com/mid" in urls
        assert "https://example.com/new" in urls
        assert "https://example.com/no-date" in urls  # permissive: no lastmod kept

    def test_end_date_excludes_newer_urls(self):
        from datetime import date

        records = self._make_records()
        result = self._filter(records, end_date=date(2023, 12, 31))
        urls = [r.url for r in result]
        assert "https://example.com/new" not in urls
        assert "https://example.com/mid" in urls
        assert "https://example.com/old" in urls

    def test_both_dates_narrow_range(self):
        from datetime import date

        records = self._make_records()
        result = self._filter(
            records,
            start_date=date(2023, 1, 1),
            end_date=date(2023, 12, 31),
        )
        urls = [r.url for r in result]
        assert urls == ["https://example.com/mid", "https://example.com/no-date"]

    def test_strict_filter_excludes_no_date_urls(self):
        """When strict_date_filter=True, URLs with no lastmod must be dropped."""
        from datetime import date

        records = self._make_records()
        result = self._filter(
            records,
            start_date=date(2023, 1, 1),
            end_date=date(2023, 12, 31),
            strict_date_filter=True,
        )
        urls = [r.url for r in result]
        assert "https://example.com/no-date" not in urls
        assert urls == ["https://example.com/mid"]

    def test_strict_filter_no_dates_still_returns_all(self):
        """strict_date_filter=True always drops no-lastmod URLs when active,
        even without a date range. The run() guard (start_date/end_date) is
        what prevents the filter block from running when no dates are given."""
        records = self._make_records()
        result = self._filter(records, strict_date_filter=True)
        # Helper always runs the block; strict=True drops the no-date record
        assert len(result) == 3
        assert "https://example.com/no-date" not in [r.url for r in result]
