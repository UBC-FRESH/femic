from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from femic.cli import main as cli_main
from femic.cli.main import app
from femic.pipeline.tipsy import BTCRunResult


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


def test_tipsy_run_btc_cli_preserves_preset_name(monkeypatch, tmp_path: Path) -> None:
    input_csv = tmp_path / "MSYT.csv"
    input_csv.write_text("feature_id\n1\n", encoding="utf-8")
    captured: dict[str, object] = {}

    def fake_run_btc_cli(**kwargs: object) -> BTCRunResult:
        captured.update(kwargs)
        return BTCRunResult(
            run_id="btc_test",
            mode="TSR",
            manifest_path=tmp_path / "btc_manifest.json",
            stdout_log_path=tmp_path / "btc_stdout.log",
            stderr_log_path=tmp_path / "btc_stderr.log",
            output_csv_path=tmp_path / "MSYT_output.csv",
            error_csv_path=tmp_path / "MSYT_error.csv",
            executable_path=tmp_path / "btc.exe",
            install_root=tmp_path / "btc_install",
            working_dir=tmp_path / "work",
            command=("btc.exe", "/TSR", "MSYT.csv"),
            copied_install=True,
            exit_code=0,
            duration_sec=2.0,
            report_template_path=tmp_path / "btc_install" / "TimberSupply.rpt",
        )

    monkeypatch.setattr(cli_main, "run_btc_cli", fake_run_btc_cli)

    result = runner.invoke(
        app,
        [
            "tipsy",
            "run-btc",
            str(input_csv),
        ],
    )

    assert result.exit_code == 0
    assert captured["report_template"] is None
    assert captured["report_preset_name"] == "tsr-unattended-default"
    assert captured["copy_install"] is True
