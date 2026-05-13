---
title: Development
---

# Development

This guide is for contributors working on OneCrawler locally.

## Local Setup

```bash
git clone https://github.com/sayedshaun/onecrawler.git
cd onecrawler
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m playwright install chromium
```

Install GenAI dependencies only when you are working on model-assisted extraction:

```bash
python -m pip install -e ".[dev,genai]"
```

!!! tip "Keep optional dependencies optional"
    Install the GenAI extra only when you are changing model-assisted extraction.
    This keeps normal sitemap, browser, and scraper development lighter.

## Run Tests

```bash
./test.sh
```

The test suite uses `unittest`. Some tests may skip optional integrations when a
dependency is not installed.

!!! note "Use the virtualenv Python if needed"
    If `python` is not on your shell path, run tests with `.venv/bin/python -m
    unittest` or the project test script from an activated environment.

## Formatting

```bash
pre-commit run --all-files
```

If `pre-commit` is not on your shell path, use the virtualenv executable:

```bash
.venv/bin/pre-commit run --all-files
```

## Install Hooks

```bash
pre-commit install
```

The current hooks run Black and isort. Keep formatting-only changes separate from
behavior changes when possible, because it makes reviews easier.

!!! tip "Separate mechanical changes"
    Formatting-only diffs are easiest to review when they are separate from behavior
    fixes, documentation changes, or dependency updates.

## Project Structure

| Path | Purpose |
| --- | --- |
| `onecrawler/settings/` | Shared settings objects |
| `onecrawler/map/` | Sitemap discovery and fallback crawling |
| `onecrawler/crawler/link/` | Browser-based link extraction |
| `onecrawler/crawler/scraper/` | Content extraction strategies |
| `tests/` | Unit tests and loader support |
| `docs/` | User-facing documentation |

## Development Workflow

1. Reproduce the issue or write a focused test.
2. Make the smallest code change that fixes the behavior.
3. Update docs when public behavior or settings change.
4. Run tests.
5. Run pre-commit.
6. Review the diff before committing.

## Testing Guidance

Prefer small tests around behavior boundaries:

- settings validation
- URL normalization and filtering
- sitemap parsing edge cases
- scheduler and worker behavior
- retry and timeout behavior

For browser-heavy behavior, keep tests isolated with fakes where possible. Full
browser tests are useful, but they are slower and more sensitive to environment
differences.

!!! warning "Browser tests are environment-sensitive"
    CI containers, Linux sandboxing, missing browser dependencies, and slow target
    pages can all affect Playwright tests. Prefer focused fakes unless the browser
    behavior itself is what you are testing.

## Documentation Guidance

Documentation should explain the decision behind a feature, not only the method call.
When adding or changing a feature, include:

- what the feature does
- when to use it
- when to avoid it
- performance implications
- a production-shaped example
- caveats or edge cases

Examples should be copy-pasteable and use explicit `CrawlerSettings` values so users
can see the operational tradeoffs.

!!! note "Document the tradeoff"
    When adding a setting, explain what users gain and what it costs: speed,
    reliability, memory, API cost, target-site load, or reproducibility.

## CI

The repository uses GitHub Actions on pushes and pull requests targeting `main`.
The matrix currently covers Python `3.10`, `3.11`, and `3.12`.
