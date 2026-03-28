from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from femic.cli.main import app


runner = CliRunner()


def test_tipsy_write_btc_report_template_cli_default_preset(tmp_path: Path) -> None:
    out = tmp_path / "tsr_default.rpt"
    result = runner.invoke(
        app,
        ["tipsy", "write-btc-report-template", str(out)],
    )
    assert result.exit_code == 0
    text = out.read_text(encoding="utf-8")
    assert "Name=TSR Unattended Default" in text
    assert "VolumeGross" in text
    assert "\nCC\t0\tCC\t{yr}\n" in text


def test_tipsy_write_btc_report_template_cli_can_clone_and_append_columns(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.rpt"
    source.write_text(
        "[CustomReport]\n"
        "Name=Timber Supply SQL\n"
        "IconID=13\n"
        "Identifier=FirstIDcolumn\n"
        "IdentifierInteger=1\n"
        "Type=databaseByStand\n"
        "OutputFormat=TAB\n"
        "\n"
        "[CustomReportHeader]\n"
        "ModelVersion=1\n"
        "\n"
        "[CustomReportColumns]\n"
        "'enum_db_column\tWidth\tHeader1Override\tHeader2Override\tUnitsOverride\n"
        "Year\t0\tYear\t\t\n"
        "Volume:Auto:Con\t0\tVolumeCon\t\t\n",
        encoding="utf-8",
    )
    out = tmp_path / "extended.rpt"
    result = runner.invoke(
        app,
        [
            "tipsy",
            "write-btc-report-template",
            str(out),
            "--source-rpt",
            str(source),
            "--name",
            "Extended SQL",
            "--column",
            "VolumeGross",
        ],
    )
    assert result.exit_code == 0
    text = out.read_text(encoding="utf-8")
    assert "Name=Extended SQL" in text
    assert "Volume:Auto:Con\t0\tVolumeCon" in text
    assert "VolumeGross\t0" in text
