from pathlib import Path
import toml
import onecrawler


def test_version_matches_pyproject() -> None:
    root = Path(__file__).resolve().parents[1]
    pyproject_path = root / "pyproject.toml"

    with pyproject_path.open("r", encoding="utf-8") as f:
        pyproject = toml.load(f)

    expected_version = pyproject["project"]["version"]

    assert onecrawler.__version__ == expected_version