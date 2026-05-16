# Contributing to OneCrawler

First off, thank you for considering contributing to OneCrawler! It's people like you that make OneCrawler such a great tool.

## Development Setup

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/sayedshaun/onecrawler.git
    cd onecrawler
    ```

2.  **Create a virtual environment**:
    ```bash
    python -m venv .venv
    source .venv/bin/activate
    ```

3.  **Install dependencies**:
    ```bash
    pip install -e ".[dev]"
    ```

## Testing

We take testing seriously. Before submitting a pull request, please ensure all tests pass.

### Local Testing
You can run tests using `pytest`:
```bash
pytest
```

### Multi-version Testing

We test OneCrawler across Python 3.10, 3.11, 3.12, 3.13, and 3.14. The best way to do this is using Docker, as it ensures a consistent environment.

### Using Docker (Recommended)
You can run all versions at once using our test container:
```bash
docker build -t onecrawler-test -f test.Dockerfile .
docker run --rm onecrawler-test
```

## Commit Message Guidelines

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification. This helps us maintain a clear history and automate versioning.

Your commit message should be prefixed with one of the following types:

| Type | Description |
| :--- | :--- |
| **`feat`** | A new feature for the user |
| **`fix`** | A bug fix |
| **`docs`** | Documentation changes only |
| **`style`** | Formatting, missing semi-colons, etc (no code changes) |
| **`refactor`** | Refactoring code (not a fix, not a feature) |
| **`perf`** | Code change that improves performance |
| **`test`** | Adding or fixing tests |
| **`chore`** | Maintenance, build tasks, dependencies, CI/CD |

**Example**: `feat: add support for recursive sitemap discovery`

## Pull Request Process

1.  Create a new branch for your feature or fix.
2.  Write your code and add tests if applicable.
3.  Ensure all tests pass.
4.  Submit a Pull Request against the `main` branch.
5.  Wait for review and feedback!

Thank you for your contribution!
