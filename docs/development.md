---
title: Development
---

# Development

## Install development dependencies

```bash
python -m pip install -e ".[dev]"
```

## Run tests

```bash
./test.sh
```

## Formatting

```bash
pre-commit run --all-files
```

## Install pre-commit hooks

```bash
pre-commit install
```

## CI

The repository uses GitHub Actions and runs on pushes and pull requests targeting `main`.

The matrix currently covers Python `3.10`, `3.11`, and `3.12`.
