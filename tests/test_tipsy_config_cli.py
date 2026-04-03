from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from femic.cli.main import app


runner = CliRunner()


def test_tipsy_validate_cli_passes_with_repo_configs() -> None:
    result = runner.invoke(app, ["tipsy", "validate", "--config-dir", "config/tipsy"])
    assert result.exit_code == 0
    assert "Validated case/FMU TIPSY configs" in result.stdout


def test_tipsy_validate_cli_fails_when_requested_tsa_missing(tmp_path: Path) -> None:
    cfg = tmp_path / "tipsy"
    cfg.mkdir()
    (cfg / "tsa08.yaml").write_text(
        "schema_version: 1\ntsa_code: '08'\nrules:\n  - id: r\n    when: {}\n    assign:\n      e: {}\n      f: {}\n",
        encoding="utf-8",
    )
    result = runner.invoke(
        app,
        ["tipsy", "validate", "--config-dir", str(cfg), "--tsa", "08", "--tsa", "16"],
    )
    assert result.exit_code == 1
    assert "Missing case/FMU TIPSY config files" in result.stdout


def test_tipsy_validate_cli_supports_named_unit_codes(tmp_path: Path) -> None:
    cfg = tmp_path / "tipsy"
    cfg.mkdir()
    (cfg / "tsak3z.yaml").write_text(
        "schema_version: 1\n"
        "tsa_code: 'k3z'\n"
        "rules:\n"
        "  - id: r\n"
        "    when: {}\n"
        "    assign:\n"
        "      e: {}\n"
        "      f: {}\n",
        encoding="utf-8",
    )
    result = runner.invoke(
        app,
        ["tipsy", "validate", "--config-dir", str(cfg), "--tsa", "k3z"],
    )
    assert result.exit_code == 0
    assert "k3z" in result.stdout
