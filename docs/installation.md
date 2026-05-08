---
title: Installation
---

# Installation

## Requirements

- Python `>= 3.10`
- `pip`
- Playwright browser binaries, only if you use browser-backed crawling

## Install from PyPI

```bash
pip install onecrawler
```

## Install from source

```bash
pip install git+https://github.com/sayedshaun/onecrawler.git
```

## Local development install

```bash
git clone https://github.com/sayedshaun/onecrawler.git
cd onecrawler
python -m pip install -e ".[dev]"
```

## Optional extras

AI-assisted extraction depends on:

```bash
pip install "onecrawler[genai]"
```

This installs the optional `langchain` and `langgraph` dependencies.
