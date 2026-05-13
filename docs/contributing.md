---
title: Contributing
---

# Contributing

Thanks for improving OneCrawler. The project values small, well-tested changes and
documentation that helps users make good crawler decisions.

!!! tip "Small PRs are easier to merge"
    A focused change with tests and a short explanation is usually better than a
    broad cleanup that mixes behavior, formatting, and documentation.

## Workflow

1. Create a branch for your change.
2. Add or update tests for behavior changes.
3. Update docs when settings, public API, or recommended workflows change.
4. Run `./test.sh`.
5. Run `pre-commit run --all-files`.
6. Open a pull request with a short summary and verification notes.

## What Good Contributions Include

For code changes:

- a focused implementation
- tests that fail without the fix
- no unrelated formatting churn
- clear error handling for network and browser edge cases

For documentation changes:

- real-world context
- recommended usage
- caveats and performance notes
- examples that match the current public API

## Design Principles

Prefer explicit settings over hidden behavior. Crawlers can affect external
systems, so users should be able to see limits, filters, retries, and concurrency in
their scripts.

Prefer sitemap discovery before browser crawling. It is faster and easier to operate.

Prefer deterministic extraction before GenAI extraction. GenAI is powerful when users
need typed or semantic output, but it should not be the default for simple text
extraction.

!!! warning "Crawler changes affect external systems"
    Be careful with defaults that increase concurrency, retries, browser usage, or
    crawl breadth. They can change how much traffic users send to target sites.

## Before Opening A Pull Request

Run:

```bash
./test.sh
pre-commit run --all-files
```

If you cannot run a check, mention it in the pull request with the reason.

!!! note "Verification notes matter"
    Include the exact commands you ran and any checks you skipped. It helps reviewers
    understand residual risk without guessing.

## Commit Messages

Use short, behavior-focused messages:

```text
Add sitemap fallback documentation
Fix deep crawler human behavior wiring
Improve scraper timeout handling
```

Avoid vague messages such as `update files` or `fix bug`.
