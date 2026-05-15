"""Version management for the OneCrawler package."""

import os
from typing import Optional

import toml

__version__: Optional[str] = None


def _initialize_version() -> None:
    """Initializes __version__ by reading pyproject.toml"""
    global __version__
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)

        pyproject_path = os.path.join(project_root, "pyproject.toml")
        with open(pyproject_path, "r") as f:
            data = toml.load(f)
            __version__ = data["project"].get("version")
    except Exception:
        __version__ = None


# Initialize version on import
_initialize_version()


def get_version() -> Optional[str]:
    """Retrieves the package version from pyproject.toml.

    This function attempts to find the pyproject.toml file in the project root,
    parse it, and extract the version defined in the [project] section.

    Returns:
        Optional[str]: The version string if found, otherwise None.
    """
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)

        pyproject_path = os.path.join(project_root, "pyproject.toml")
        with open(pyproject_path, "r") as f:
            data = toml.load(f)
            return data["project"].get("version")
    except Exception:
        return None
