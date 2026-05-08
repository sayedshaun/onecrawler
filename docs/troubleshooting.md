---
title: Troubleshooting
---

# Troubleshooting

## Playwright errors

If browser-backed crawling fails, install the browser binaries required by Playwright.

## Slow or unstable targets

- lower `concurrency`
- increase `request_timeout`
- raise `max_retries` for flaky pages
- narrow `include_link_patterns`

## Empty results

Check these first:

- the target site allows the crawl path you want
- your URL patterns are not too restrictive
- the site actually exposes links or sitemap entries in the section you are crawling

## Markdown not showing on GitHub Pages

Make sure the file you want to render is in the published source and that the page has YAML front matter at the top.

Example:

```markdown
---
title: Home
---
```

Also make sure the landing page is named `index.md` or `index.html`.
