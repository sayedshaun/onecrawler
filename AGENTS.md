# AGENTS.md

Guidance for AI coding agents working in this repository.

## Commands

```bash
# Setup (editable install with dev deps + browser binaries)
python -m pip install -e ".[dev]"
python -m playwright install chromium

# Optional GenAI extras (needed for GenAI scraping strategy / genai tests)
pip install -e ".[genai]"

# Run the full test suite
pytest

# Run a single test file / test
pytest tests/test_deep_crawler.py
pytest tests/test_deep_crawler.py::test_name -v

# Formatting & linting (must pass before commit, enforced in CI via pre-commit)
pre-commit run --all-files
black onecrawler tests
isort onecrawler tests

# Docs (mkdocs-material)
mkdocs serve
```

CI (`.github/workflows/ci.yml`) runs `pre-commit run --all-files` then `pytest` across Python 3.10–3.14. There is no separate lint-only or build-only command — formatting is entirely delegated to the `black`/`isort` pre-commit hooks (`.pre-commit-config.yaml`).

Tests use `pytest-asyncio` in `auto` mode (`pytest.ini`), so async test functions do not need `@pytest.mark.asyncio`.

## Architecture

Onecrawler is an async crawling/scraping framework built around three public engines exported from `onecrawler/__init__.py`: `Crawler`, `LinkExtractor`, `Scraper` (defined in `onecrawler/crawler/crawl.py` and `onecrawler/crawler/engine.py`). All engines subclass `BaseEngine` (`onecrawler/crawler/base.py`), which provides `async with` lifecycle management (`start`/`close`) and a `_ensure_open()` guard — engines are unusable outside their context manager.

A single `Settings` object (`onecrawler/settings/crawler.py`, re-exported via `onecrawler/settings/__init__.py`) configures every engine: concurrency, retries/timeouts, link extraction strategy/limits, include/exclude URL patterns, scraping strategy/output format, proxy config, browser config, and human-behavior simulation. Sub-settings live in their own modules (`browser.py`, `genai.py`, `proxy.py`, `simulation.py`, `sitemap.py`) and are composed onto `Settings`.

**Three usage tiers, in order of preference (see README "Recommended workflow"):**
1. `UniversalSiteMap` / `SiteMap` (`onecrawler/crawler/map/sitemap.py`) — discovers URLs via `robots.txt`, sitemap indexes, `.xml.gz`, feeds, HTML fallback. No browser needed; uses `curl_cffi`/`lxml`.
2. `LinkExtractor` (`onecrawler/crawler/engine.py`) — browser-backed (Playwright) link discovery when sitemaps are missing/incomplete. `shallow` reads one page (`crawler/link/shallow.py`); `deep` does BFS crawling via `BFSRuntime` (`crawler/link/deep.py`), `BFScheduler` (`crawler/scheduler.py`), and `BrowserPool` (`crawler/pool.py`).
3. `Scraper` (`onecrawler/crawler/engine.py`) — extracts content from a URL list using a pluggable strategy: `HeuristicStrategy` (`crawler/scraper/heuristic/script.py`, trafilatura-based, no model calls) or `GenAIStrategy` (`crawler/scraper/genai/`, LangGraph-based pipeline over pluggable LLM providers in `genai/llms/{openai,gemini,ollama}.py`, typed by a Pydantic `output_schema`).

`Crawler` (`crawler/crawl.py`) combines discovery + extraction into one pass: `CrawlerRuntime` runs a BFS worker pool that navigates pages with Playwright (`crawler/navigation.py`), parses links via `LinkSpider` (`crawler/spider.py`), immediately extracts content through the configured strategy, and optionally applies a `content_filter` before appending to results — this is the one place filters and extraction interleave with live crawling (as opposed to `Scraper`, which only extracts from an already-known URL list).

Both `Crawler` and `LinkExtractor`'s deep strategy expose `run()` (collect-all) and `stream()` (async generator, real-time results) built on the same underlying runtime — `run()` is implemented as `stream()` fully consumed into a list.

**Filters** (`onecrawler/filters/`) are composable predicates over extracted content dicts: `by_date`, `by_keywords`, `by_files`, `by_extension`, `by_cosine_similarity`. They compose via `AND`/`OR`/`NOT` (`filters/chain.py`, built on `FilterChain` in `filters/base.py`) and are passed to `Crawler.run()`/`.stream()` as the `filters` argument, applied post-extraction, pre-yield.

**Proxies**: `ProxySettings`/pools live in `onecrawler/proxy/`; `Settings.proxies` + `proxy_rotation_method` (e.g. `round_robin`) fan out requests across a pool, used by both the sitemap module (`curl_cffi`) and the browser layer.

Output writers (`onecrawler.utils.writter`, e.g. `dump_json`) and crawl statistics (`onecrawler.utils.stats`) are utility-only — they don't participate in engine control flow.

## Contribution conventions

- Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/) (`feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `chore`) — see `CONTRIBUTING.md`.
- PRs target `main`.
