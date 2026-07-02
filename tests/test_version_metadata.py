from __future__ import annotations

import tomllib
from pathlib import Path

import femic
from typer.testing import CliRunner

from femic.cli.main import app


runner = CliRunner()


def test_package_version_surfaces_are_synchronized() -> None:
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    assert pyproject["project"]["version"] == "0.2.0a1"
    assert femic.__version__ == pyproject["project"]["version"]


def test_cli_version_reports_package_version() -> None:
    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert result.stdout.strip() == femic.__version__
