"""Version management for onecrawler package."""

import os

import toml


def get_version():
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)

        pyproject_path = os.path.join(project_root, "pyproject.toml")
        with open(pyproject_path, "r") as f:
            data = toml.load(f)
            return data["project"].get("version")
    except Exception:
        return
