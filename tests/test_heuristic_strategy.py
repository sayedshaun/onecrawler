"""Tests for HeuristicStrategy's page-reuse behavior."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from tests._support import ensure_package, install_trafilatura_stub, load_module


def _load_strategy_module():
    ensure_package("onecrawler")
    ensure_package("onecrawler.crawler")
    ensure_package("onecrawler.crawler.scraper")
    ensure_package("onecrawler.crawler.scraper.heuristic")
    install_trafilatura_stub()
    # HeuristicStrategy imports `from ...navigation import goto`; load it first.
    load_module("onecrawler.crawler.navigation", "onecrawler/crawler/navigation.py")
    return load_module(
        "onecrawler.crawler.scraper.heuristic.script",
        "onecrawler/crawler/scraper/heuristic/script.py",
    )


script_module = _load_strategy_module()


def _make_settings():
    settings = MagicMock()
    settings.scraping_output_format = "markdown"
    settings.browser_settings.wait_until = "load"
    settings.browser_settings.timeout = 30000
    settings.browser_settings.settle_delay = 0
    return settings


@pytest.mark.asyncio
async def test_extract_with_html_skips_browser_fetch(monkeypatch):
    captured = {}

    def fake_extract(html, **kwargs):
        captured["html"] = html
        return "cleaned text"

    monkeypatch.setattr(script_module.trafilatura, "extract", fake_extract)

    browser = AsyncMock()  # must never be touched
    strategy = script_module.HeuristicStrategy(_make_settings(), browser=browser)

    result = await strategy.extract("https://x/a", html="<html>BODY</html>")

    assert result == "cleaned text"
    assert captured["html"] == "<html>BODY</html>"
    browser.new_page.assert_not_called()


@pytest.mark.asyncio
async def test_extract_without_html_falls_back_to_fetch(monkeypatch):
    monkeypatch.setattr(
        script_module.trafilatura, "extract", lambda html, **k: "cleaned"
    )

    class FakePage:
        def __init__(self):
            self.goto_calls = 0

        async def goto(self, *args, **kwargs):
            self.goto_calls += 1

        async def content(self):
            return "<html>FETCHED</html>"

        async def close(self):
            return None

    page = FakePage()
    browser = MagicMock()
    browser.new_page = AsyncMock(return_value=page)

    strategy = script_module.HeuristicStrategy(_make_settings(), browser=browser)

    result = await strategy.extract("https://x/a")

    assert result == "cleaned"
    browser.new_page.assert_awaited_once()
    assert page.goto_calls == 1
