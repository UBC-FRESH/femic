from __future__ import annotations

import tomllib
from pathlib import Path

import femic


def test_package_version_surfaces_are_synchronized() -> None:
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    assert pyproject["project"]["version"] == "0.2.0a1"
    assert femic.__version__ == pyproject["project"]["version"]
