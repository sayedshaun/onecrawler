"""Version management for onecrawler package."""

import os

import toml


def get_version():
    """Get current version string from pyproject.toml."""
    try:
        # Get project root directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)

        # Read pyproject.toml
        pyproject_path = os.path.join(project_root, "pyproject.toml")
        with open(pyproject_path, "r") as f:
            data = toml.load(f)
            return data["project"].get("version", "0.1.1")
    except Exception:
        return "0.1.1"
