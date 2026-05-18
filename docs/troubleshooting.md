---
title: Troubleshooting
---

# Troubleshooting

This page lists common failure modes and the first things to check. Most crawler
issues come from scope, browser setup, target-site behavior, or overly aggressive
concurrency.

!!! tip "Debug in stages"
    Separate discovery from scraping while troubleshooting. First confirm the URL
    list, then scrape one URL, then scale to batches.

## Sitemap Discovery Returns No URLs

Check whether the site publishes a sitemap:

```text
https://example.com/robots.txt
https://example.com/sitemap.xml
```

Then try:

- remove or loosen `include_link_patterns`
- increase `request_timeout`
- keep `sitemap_html_fallback=True`
- lower `concurrency` if the site is rejecting bursts
- start from the canonical origin, such as `https://www.example.com`

Some sites put sitemaps on a different host or subdomain. If `robots.txt` points
there, use the main site URL and let `UniversalSiteMap` follow the sitemap directive.

!!! note "Try the canonical host"
    `https://example.com`, `https://www.example.com`, and regional subdomains can
    publish different `robots.txt` and sitemap files. Start from the public URL users
    actually visit.

## Link Extraction Finds Too Few Links

Common causes:

- the links are outside the starting URL's host
- the links appear only after scrolling or JavaScript interaction
- `include_link_patterns` is too restrictive
- the page uses buttons or client-side routes instead of anchor tags
- the section requires authentication

Try shallow extraction first on the exact page where you can see the links. If that
works, switch to deep extraction with the same filters.

For lazy-loaded pages, enable human behavior simulation:

```python
from onecrawler import Settings, HumanBehaviorSettings


settings = Settings(
    enable_human_behaviors=True,
    human_behavior_settings=HumanBehaviorSettings(max_scrolls=30),
)
```

!!! warning "Some links are not real anchors"
    Pages that navigate with buttons, forms, or client-side router state may not
    expose normal `<a href>` links. Those pages may need custom handling outside
    generic link extraction.

## Playwright Browser Errors

Install browser binaries:

```bash
python -m playwright install chromium
```

In containers:

```bash
python -m playwright install --with-deps chromium
```

If browser launch fails in CI, check sandbox restrictions and system libraries. The
default launch args include `--no-sandbox`, but some environments still need
Playwright's dependency installer.

!!! tip "Verify Playwright separately"
    Before debugging crawler code, run a tiny Playwright script or browser install
    check in the same environment. That isolates dependency problems from crawler
    configuration problems.

## Scraping Returns `None`

`None` means the page could not be fetched, did not contain extractable content, or
the extraction strategy failed.

Try:

- open the URL in a browser and confirm it returns content
- increase `request_timeout`
- lower `concurrency`
- use browser-backed scraping for JavaScript-rendered pages
- inspect whether the target blocks automated requests
- retry with `scraping_output_format="json"` for easier debugging

For batch jobs, persist failed URLs separately so you can retry them without running
discovery again.

!!! note "Check page type"
    Search pages, login pages, image galleries, and policy pages often return little
    or no article-like content. Filter them out with `include_link_patterns`.

## GenAI Configuration Errors

If `scraping_strategy="genai"`, you must provide `genai` settings and keep
`scraping_output_format="json"`.

```python
settings = Settings(
    scraping_strategy="genai",
    scraping_output_format="json",
    genai=GenerativeAISettings(
        provider="openai",
        model_name="gpt-4o-mini",
        api_key="YOUR_API_KEY",
        output_schema=MySchema,
    ),
)
```

Use low concurrency for GenAI workflows to avoid provider rate limits.

!!! warning "GenAI failures may be provider-side"
    Rate limits, model availability, schema validation, and network failures can all
    look similar in batch logs. Capture failed URLs and error messages for retry.

## Slow Crawls

Slow crawls usually come from browser overhead, target latency, retries, or simulated
human behavior.

Improve throughput in this order:

1. Prefer sitemap discovery over browser crawling.
2. Narrow `include_link_patterns`.
3. Disable human behavior simulation unless needed.
4. Increase `concurrency` gradually.
5. Reduce `link_extraction_limit` to the batch size you actually need.
6. Save discovered URLs and scrape them in separate batches.

If failures rise as speed increases, back off. A slightly slower crawl with stable
results is better than a fast crawl full of retries and missing pages.

!!! tip "Tune from narrow to broad"
    Start with one section, a small limit, and low concurrency. Increase scope only
    after results and error rates look healthy.

## Rate Limits And Blocking

Symptoms include `403`, `429`, timeouts, or many empty pages.

Recommended response:

- lower `concurrency`
- increase `retry_delay`
- use a clear user agent
- respect robots.txt and site terms
- crawl narrower sections
- schedule jobs during quieter periods

Avoid treating blocking as only a technical problem. Production crawling should be
predictable and respectful.

!!! warning "Respect target sites"
    Proxies, retries, and delays are operational tools, not permission to ignore
    robots.txt, terms, or rate limits.

## GitHub Pages Markdown Does Not Render

Make sure the page is inside the published `docs/` directory and has YAML front
matter:

```markdown
---
title: My Page
---
```

For a project site, set GitHub Pages to publish from the `main` branch and the
`/docs` folder.
