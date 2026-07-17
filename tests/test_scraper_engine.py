"""Tests for Scraper's url-tagging behavior in _process()/stream()."""

import asyncio
import logging
import types
from unittest.mock import AsyncMock

import pytest

from onecrawler.crawler.engine import Scraper


def _make_scraper(extract):
    """Builds a Scraper instance without going through __init__/start(), which would
    require a live Settings/browser stack."""
    scraper = Scraper.__new__(Scraper)
    scraper._closed = False
    scraper.settings = types.SimpleNamespace(
        show_progress=False, scraping_strategy="heuristic"
    )
    scraper.semaphore = asyncio.Semaphore(5)
    scraper.retries = 1
    scraper.timeout = 5
    scraper.logger = logging.getLogger("test-scraper")
    scraper.strategy = types.SimpleNamespace(extract=AsyncMock(side_effect=extract))
    return scraper


@pytest.mark.asyncio
async def test_process_wraps_dict_result_with_url():
    async def extract(url):
        return {"title": "hello"}

    scraper = _make_scraper(extract)
    result = await scraper._process("https://example.com/a")

    assert result == {"url": "https://example.com/a", "result": {"title": "hello"}}


@pytest.mark.asyncio
async def test_process_wraps_plain_text_result_with_url():
    async def extract(url):
        return "plain markdown text"

    scraper = _make_scraper(extract)
    result = await scraper._process("https://example.com/b")

    assert result == {"url": "https://example.com/b", "result": "plain markdown text"}


@pytest.mark.asyncio
async def test_process_leaves_pydantic_model_instance_unwrapped():
    from pydantic import BaseModel

    class Article(BaseModel):
        title: str

    model = Article(title="hello")

    async def extract(url):
        return model

    scraper = _make_scraper(extract)
    result = await scraper._process("https://example.com/d")

    assert result == {"url": "https://example.com/d", "result": model}
    assert result["result"].title == "hello"


@pytest.mark.asyncio
async def test_process_returns_none_for_failed_extraction():
    async def extract(url):
        return None

    scraper = _make_scraper(extract)
    result = await scraper._process("https://example.com/c")

    assert result is None


@pytest.mark.asyncio
async def test_stream_preserves_url_mapping_despite_out_of_order_completion():
    """The first URL takes longest, so completion order differs from input order — url
    tagging must not rely on positional/index correspondence."""
    delays = {
        "https://example.com/slow": 0.05,
        "https://example.com/fast": 0.0,
    }

    async def extract(url):
        await asyncio.sleep(delays[url])
        return {"marker": url}

    scraper = _make_scraper(extract)
    results = [item async for item in scraper.stream(list(delays.keys()))]

    assert len(results) == 2
    by_url = {item["url"]: item["result"] for item in results}
    assert by_url == {
        "https://example.com/slow": {"marker": "https://example.com/slow"},
        "https://example.com/fast": {"marker": "https://example.com/fast"},
    }
    # The fast one really completes first, proving order isn't assumed.
    assert results[0]["url"] == "https://example.com/fast"
