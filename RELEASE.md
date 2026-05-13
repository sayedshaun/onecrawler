# Release Process

This document describes how to create releases for onecrawler, which will automatically deploy to PyPI.

## Prerequisites

1. **PyPI API Token**: Set up a PyPI API token and add it to GitHub repository secrets:
   - Go to https://pypi.org/manage/account/token/
   - Create a new API token with "Entire account" scope
   - Add it as `PYPI_API_TOKEN` in your GitHub repository secrets

2. **Version Management**: Ensure version is properly set in `onecrawler/version.py`

## Creating a Release

### Method 1: Using GitHub Web Interface (Recommended)

1. Go to your repository's Releases page on GitHub
2. Click "Create a new release"
3. Choose or create a new tag (e.g., `v1.0.0`)
4. Fill in release title and description
5. Click "Publish release"

### Method 2: Using Git CLI

```bash
# Create and push a tag
git tag v1.0.0
git push origin v1.0.0

# Create a release on GitHub (or use the web interface)
gh release create v1.0.0 --title "Release v1.0.0" --notes "Release notes here"
```

## What Happens Automatically

When you create a release on GitHub, the following workflow will trigger:

1. **Build**: The package is built using standard Python build tools
2. **Validate**: The package is checked for common issues
3. **Deploy**: Published to PyPI using your API token
4. **Comment**: A PyPI badge and installation link is added to the release

### Workflow Features

- ✅ **Automatic Triggering**: Runs on every published release
- ✅ **Manual Triggering**: Can be manually run for testing
- ✅ **Version Extraction**: Automatically extracts version from git tag
- ✅ **Package Validation**: Checks package before publishing
- ✅ **PyPI Badges**: Adds professional badges to release comments
- ✅ **Installation Instructions**: Provides ready-to-use pip commands

## Verification

After release:

1. **Check PyPI**: Verify the package appears at https://pypi.org/project/onecrawler/
2. **Test Installation**: `pip install onecrawler==VERSION`
3. **Check GitHub**: Verify the release has PyPI badges and installation instructions

## Troubleshooting

### Common Issues

1. **Authentication Failed**:
   - Check that `PYPI_API_TOKEN` is correctly set in repository secrets
   - Ensure the token has sufficient permissions

2. **Build Failed**:
   - Check `pyproject.toml` for syntax errors
   - Verify all dependencies are properly declared

3. **Upload Failed**:
   - Check if the version already exists on PyPI
   - Verify package name conflicts

### Manual Testing

You can test the workflow manually:

1. Go to Actions tab in your GitHub repository
2. Select "Publish to PyPI" workflow
3. Click "Run workflow"
4. Choose branch and click "Run workflow"

## Version Format

Use semantic versioning (SemVer):
- `v1.0.0` - Major release (breaking changes)
- `v1.1.0` - Minor release (new features)
- `v1.1.1` - Patch release (bug fixes)

The workflow automatically removes the `v` prefix when publishing to PyPI.
