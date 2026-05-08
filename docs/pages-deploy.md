---
title: Publishing with GitHub Pages
---

# Publishing with GitHub Pages

GitHub Pages can publish Markdown content from a `docs/` folder.

## Recommended layout

```text
docs/
├── index.md
├── installation.md
├── quick-start.md
├── configuration.md
├── sitemap-discovery.md
├── link-extraction.md
├── scraping.md
├── api-reference.md
├── development.md
├── troubleshooting.md
└── contributing.md
```

## Setup steps

1. commit the `docs/` folder to the repository
2. go to repository settings
3. open the GitHub Pages section
4. choose `main` as the source
5. choose `/docs` as the folder
6. save

## Important naming note

A user or organization site must use a repository named `<user>.github.io` or `<organization>.github.io`. A project repository can still use GitHub Pages, but its default site path is under the repository URL unless you configure a custom domain.

## Custom domain

If you want a custom domain, GitHub Pages supports that too through repository settings and DNS configuration.
