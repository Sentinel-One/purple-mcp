"""Test for purple_mcp.__version__."""

import sys
from pathlib import Path

if sys.version_info < (3, 11):  # pragma: no cover
    import tomli as tomllib
else:  # pragma: no cover
    import tomllib

import purple_mcp


def test_versions_are_in_sync() -> None:
    """Checks if the pyproject.toml and package __version__ are in sync."""
    pyproj_path = Path(__file__).parent.parent.parent / "pyproject.toml"
    with pyproj_path.open("rb") as fd:
        pyproj = tomllib.load(fd)
        pyproj_version = pyproj["project"]["version"]

    package_init_version = purple_mcp.__version__

    assert package_init_version == pyproj_version
