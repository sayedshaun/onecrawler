.DEFAULT_GOAL := help
.PHONY: help install test test-matrix lint format precommit docs docs-build build clean

help:  ## Show this help
	@grep -hE '^[a-z-]+:.*?## ' $(MAKEFILE_LIST) \
		| awk -F':.*?## ' '{printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

install:  ## Install the package with its dev extras, plus the git hooks
	uv sync --extra dev
	uv run pre-commit install

test:  ## Run the test suite
	uv run pytest

test-matrix:  ## Run the suite on every supported Python version, in Docker
	docker build -t onecrawler-test -f test.Dockerfile .
	docker run --rm onecrawler-test

lint:  ## Report lint and formatting problems without changing anything
	ruff check .
	ruff format --check .

format:  ## Apply the fixes lint only reports
	ruff check --fix .
	ruff format .

precommit:  ## Run every pre-commit hook over the whole tree
	uv run pre-commit run --all-files

docs:  ## Serve the documentation with live reload
	uv run mkdocs serve

docs-build:  ## Build the documentation into site/
	uv run mkdocs build

build:  ## Build the sdist and wheel into dist/
	uv build

clean:  ## Remove build artifacts and caches
	rm -rf build dist site .pytest_cache .ruff_cache *.egg-info
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
