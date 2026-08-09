from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from femic.cli import main as cli_main
from femic.cli.main import app
from femic.pipeline.btc_runtime import BTCRuntimeConfig, BTCRuntimeConfigError
from femic.pipeline.tipsy import BTCRunResult, BTCColumnProbeResult
from femic.workflows.legacy import (
    BTCPostTipsyRunResult,
    PostTipsyBundleResult,
    PostTipsyBundleRunResult,
)


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


def test_tipsy_write_btc_report_template_cli_can_append_indicator_bank(
    tmp_path: Path,
) -> None:
    out = tmp_path / "tsr_bank.rpt"
    result = runner.invoke(
        app,
        [
            "tipsy",
            "write-btc-report-template",
            str(out),
            "--preset",
            "tsr-unattended-default",
            "--indicator-bank",
            "stand-structure-basic",
        ],
    )
    assert result.exit_code == 0
    text = out.read_text(encoding="utf-8")
    assert "MAI\t0" in text
    assert "StemCount175\t0" in text


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
    assert captured["indicator_bank_names"] == []
    assert captured["copy_install"] is True
    assert Path(captured["log_dir"]).as_posix().endswith("tipsy_io/logs")


def test_tipsy_run_btc_cli_passes_indicator_banks(monkeypatch, tmp_path: Path) -> None:
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
            "--indicator-bank",
            "stand-structure-basic",
        ],
    )

    assert result.exit_code == 0
    assert captured["indicator_bank_names"] == ["stand-structure-basic"]


def test_tipsy_probe_btc_columns_cli_uses_tipsy_log_dir_default(
    monkeypatch, tmp_path: Path
) -> None:
    input_csv = tmp_path / "MSYT.csv"
    input_csv.write_text("feature_id\n1\n", encoding="utf-8")
    captured: dict[str, object] = {}

    def fake_probe_btc_report_columns(**kwargs: object):
        captured.update(kwargs)
        template = cli_main.btc_report_template_preset("tsr-unattended-default")
        return ([], template)

    monkeypatch.setattr(
        cli_main, "probe_btc_report_columns", fake_probe_btc_report_columns
    )

    result = runner.invoke(
        app,
        [
            "tipsy",
            "probe-btc-columns",
            str(input_csv),
            "--column",
            "VolumeGross",
        ],
    )

    assert result.exit_code == 0
    assert Path(captured["log_dir"]).as_posix().endswith("tipsy_io/logs")


def test_tipsy_probe_btc_columns_cli_writes_summary(
    monkeypatch, tmp_path: Path
) -> None:
    input_csv = tmp_path / "MSYT.csv"
    input_csv.write_text("feature_id\n1\n", encoding="utf-8")
    summary = tmp_path / "summary.json"
    captured: dict[str, object] = {}

    def fake_probe_btc_report_columns(**kwargs: object):
        captured.update(kwargs)
        template = cli_main.btc_report_template_preset("tsr-unattended-default")
        return (
            [
                BTCColumnProbeResult(
                    candidate_token="VolumeGross",
                    status="accepted",
                    accepted_column_tokens=("Year", "VolumeGross"),
                    run_id="probe_01_VolumeGross",
                    exit_code=0,
                    manifest_path=tmp_path / "probe.json",
                    output_csv_path=tmp_path / "out.csv",
                    error_csv_path=tmp_path / "err.csv",
                ),
                BTCColumnProbeResult(
                    candidate_token="SPH:000",
                    status="failed",
                    accepted_column_tokens=("Year", "VolumeGross"),
                    run_id="probe_02_SPH_000",
                    error_message="BTC crashed in BatchProcess()",
                ),
            ],
            template,
        )

    monkeypatch.setattr(
        cli_main, "probe_btc_report_columns", fake_probe_btc_report_columns
    )

    result = runner.invoke(
        app,
        [
            "tipsy",
            "probe-btc-columns",
            str(input_csv),
            "--column",
            "VolumeGross",
            "--column",
            "SPH:000",
            "--summary-json",
            str(summary),
        ],
    )

    assert result.exit_code == 0
    assert captured["source_preset_name"] is None
    assert captured["candidate_tokens"] == ["VolumeGross", "SPH:000"]
    assert captured["copy_install"] is False
    payload = cli_main.json.loads(summary.read_text(encoding="utf-8"))
    assert payload["accepted_tokens"] == ["VolumeGross"]
    assert payload["failed_tokens"] == ["SPH:000"]


def test_tipsy_probe_btc_columns_cli_stock_matrix_defaults_to_copied_install(
    monkeypatch, tmp_path: Path
) -> None:
    input_csv = tmp_path / "MSYT.csv"
    input_csv.write_text("feature_id\n1\n", encoding="utf-8")
    captured: dict[str, object] = {}

    def fake_probe_btc_report_columns(**kwargs: object):
        captured.update(kwargs)
        template = cli_main.btc_report_template_preset("tsr-unattended-default")
        return ([], template)

    monkeypatch.setattr(
        cli_main, "probe_btc_report_columns", fake_probe_btc_report_columns
    )

    result = runner.invoke(
        app,
        [
            "tipsy",
            "probe-btc-columns",
            str(input_csv),
            "--column",
            "BasalArea000",
            "--variant-strategy",
            "stock-matrix",
            "--alias-override",
            "BasalArea000=BasalArea:000",
        ],
    )

    assert result.exit_code == 0
    assert captured["copy_install"] is True
    assert captured["variant_strategy"] == "stock-matrix"
    assert captured["alias_overrides"] == {"BasalArea000": ("BasalArea:000",)}


def test_tsa_btc_post_tipsy_cli_uses_default_report_preset(
    monkeypatch, tmp_path: Path
) -> None:
    data_root = tmp_path / "data"
    data_root.mkdir()
    (data_root / "03_input-tsa29.csv").write_text(
        "feature_id\n1000\n", encoding="utf-8"
    )

    captured: dict[str, object] = {}

    def fake_btc_post_tipsy(**kwargs: object) -> BTCPostTipsyRunResult:
        captured.update(kwargs)
        btc_result = BTCRunResult(
            run_id="btc_post_tipsy_test_tsa29",
            mode="TSR",
            manifest_path=tmp_path / "logs" / "btc_manifest.json",
            stdout_log_path=tmp_path / "logs" / "btc_stdout.log",
            stderr_log_path=tmp_path / "logs" / "btc_stderr.log",
            output_csv_path=data_root / "04_output-tsa29.csv",
            error_csv_path=data_root / "04_error-tsa29.csv",
            executable_path=tmp_path / "btc" / "TIPSYbtc.exe",
            install_root=tmp_path / "btc",
            working_dir=tmp_path / "scratch" / "work",
            command=("btc.exe", "/TSR", "MSYT.csv"),
            copied_install=True,
            exit_code=0,
            duration_sec=1.0,
            report_template_path=tmp_path / "btc" / "TimberSupply.rpt",
        )
        bundle_result = PostTipsyBundleResult(
            tsa_list=["29"],
            au_rows=1,
            curve_rows=2,
            curve_points_rows=4,
            tipsy_curves_paths=[data_root / "tipsy_curves_tsa29.csv"],
            tipsy_sppcomp_paths=[data_root / "tipsy_sppcomp_tsa29.csv"],
            au_table_path=data_root / "model_input_bundle" / "au_table.csv",
            curve_table_path=data_root / "model_input_bundle" / "curve_table.csv",
            curve_points_table_path=data_root
            / "model_input_bundle"
            / "curve_points_table.csv",
        )
        post_tipsy = PostTipsyBundleRunResult(
            manifest_path=tmp_path / "logs" / "run_manifest.json",
            result=bundle_result,
        )
        return BTCPostTipsyRunResult(
            btc_results=[btc_result],
            post_tipsy_result=post_tipsy,
        )

    monkeypatch.setattr(
        cli_main,
        "run_btc_and_post_tipsy_bundle_with_manifest",
        fake_btc_post_tipsy,
    )

    result = runner.invoke(
        app,
        [
            "tsa",
            "btc-post-tipsy",
            "--instance-root",
            str(tmp_path),
            "--tsa",
            "29",
        ],
    )

    assert result.exit_code == 0
    assert captured["report_preset_name"] == "tsr-unattended-default"
    assert captured["indicator_bank_names"] == []


def test_tsa_btc_post_tipsy_cli_passes_indicator_bank(
    monkeypatch, tmp_path: Path
) -> None:
    data_root = tmp_path / "data"
    data_root.mkdir()
    (data_root / "03_input-tsa29.csv").write_text(
        "feature_id\n1000\n", encoding="utf-8"
    )

    captured: dict[str, object] = {}

    def fake_btc_post_tipsy(**kwargs: object) -> BTCPostTipsyRunResult:
        captured.update(kwargs)
        btc_result = BTCRunResult(
            run_id="btc_post_tipsy_test_tsa29",
            mode="TSR",
            manifest_path=tmp_path / "logs" / "btc_manifest.json",
            stdout_log_path=tmp_path / "logs" / "btc_stdout.log",
            stderr_log_path=tmp_path / "logs" / "btc_stderr.log",
            output_csv_path=data_root / "04_output-tsa29.csv",
            error_csv_path=data_root / "04_error-tsa29.csv",
            executable_path=tmp_path / "btc" / "TIPSYbtc.exe",
            install_root=tmp_path / "btc",
            working_dir=tmp_path / "scratch" / "work",
            command=("btc.exe", "/TSR", "MSYT.csv"),
            copied_install=True,
            exit_code=0,
            duration_sec=1.0,
            report_template_path=tmp_path / "btc" / "TimberSupply.rpt",
        )
        bundle_result = PostTipsyBundleResult(
            tsa_list=["29"],
            au_rows=1,
            curve_rows=2,
            curve_points_rows=4,
            tipsy_curves_paths=[data_root / "tipsy_curves_tsa29.csv"],
            tipsy_sppcomp_paths=[data_root / "tipsy_sppcomp_tsa29.csv"],
            au_table_path=data_root / "model_input_bundle" / "au_table.csv",
            curve_table_path=data_root / "model_input_bundle" / "curve_table.csv",
            curve_points_table_path=data_root
            / "model_input_bundle"
            / "curve_points_table.csv",
        )
        post_tipsy = PostTipsyBundleRunResult(
            manifest_path=tmp_path / "logs" / "run_manifest.json",
            result=bundle_result,
        )
        return BTCPostTipsyRunResult(
            btc_results=[btc_result],
            post_tipsy_result=post_tipsy,
        )

    monkeypatch.setattr(
        cli_main,
        "run_btc_and_post_tipsy_bundle_with_manifest",
        fake_btc_post_tipsy,
    )

    result = runner.invoke(
        app,
        [
            "tsa",
            "btc-post-tipsy",
            "--instance-root",
            str(tmp_path),
            "--tsa",
            "29",
            "--indicator-bank",
            "stand-structure-basic",
        ],
    )

    assert result.exit_code == 0
    assert captured["indicator_bank_names"] == ["stand-structure-basic"]


def test_tsa_btc_post_tipsy_cli_passes_yield_assumptions_path(
    monkeypatch, tmp_path: Path
) -> None:
    data_root = tmp_path / "data"
    data_root.mkdir()
    (data_root / "03_input-tsa29.csv").write_text(
        "feature_id\n1000\n", encoding="utf-8"
    )
    captured: dict[str, object] = {}

    def fake_btc_post_tipsy(**kwargs: object) -> BTCPostTipsyRunResult:
        captured.update(kwargs)
        btc_result = BTCRunResult(
            run_id="btc_post_tipsy_test_tsa29",
            mode="TSR",
            manifest_path=tmp_path / "logs" / "btc_manifest.json",
            stdout_log_path=tmp_path / "logs" / "btc_stdout.log",
            stderr_log_path=tmp_path / "logs" / "btc_stderr.log",
            output_csv_path=data_root / "04_output-tsa29.csv",
            error_csv_path=data_root / "04_error-tsa29.csv",
            executable_path=tmp_path / "btc" / "TIPSYbtc.exe",
            install_root=tmp_path / "btc",
            working_dir=tmp_path / "scratch" / "work",
            command=("btc.exe", "/TSR", "MSYT.csv"),
            copied_install=True,
            exit_code=0,
            duration_sec=1.0,
            report_template_path=tmp_path / "btc" / "TimberSupply.rpt",
        )
        bundle_result = PostTipsyBundleResult(
            tsa_list=["29"],
            au_rows=1,
            curve_rows=2,
            curve_points_rows=4,
            tipsy_curves_paths=[data_root / "tipsy_curves_tsa29.csv"],
            tipsy_sppcomp_paths=[data_root / "tipsy_sppcomp_tsa29.csv"],
            au_table_path=data_root / "model_input_bundle" / "au_table.csv",
            curve_table_path=data_root / "model_input_bundle" / "curve_table.csv",
            curve_points_table_path=data_root
            / "model_input_bundle"
            / "curve_points_table.csv",
        )
        post_tipsy = PostTipsyBundleRunResult(
            manifest_path=tmp_path / "logs" / "run_manifest.json",
            result=bundle_result,
        )
        return BTCPostTipsyRunResult(
            btc_results=[btc_result],
            post_tipsy_result=post_tipsy,
        )

    monkeypatch.setattr(
        cli_main,
        "run_btc_and_post_tipsy_bundle_with_manifest",
        fake_btc_post_tipsy,
    )

    result = runner.invoke(
        app,
        [
            "tsa",
            "btc-post-tipsy",
            "--instance-root",
            str(tmp_path),
            "--tsa",
            "29",
            "--yield-assumptions-path",
            "config/tsr/yield_assumptions.yaml",
        ],
    )

    assert result.exit_code == 0
    assert captured["yield_assumptions_path"] == (
        tmp_path / "config" / "tsr" / "yield_assumptions.yaml"
    )


def _fake_btc_runtime_config(*, exe: Path, prefix: Path) -> BTCRuntimeConfig:
    return BTCRuntimeConfig(
        batch_tipsy_exe=exe,
        wine_executable="wine",
        wine_prefix=prefix,
        use_xvfb=False,
        host_mode="wine",
        xvfb_executable=None,
    )


def test_tipsy_preflight_btc_cli_reports_ok(monkeypatch, tmp_path: Path) -> None:
    exe = tmp_path / "TIPSYbtc.exe"
    exe.write_text("", encoding="utf-8")
    fake_runtime = _fake_btc_runtime_config(
        exe=exe,
        prefix=tmp_path / ".wine-tipsy64",
    )
    monkeypatch.setattr(
        cli_main, "resolve_btc_runtime_config", lambda **kwargs: fake_runtime
    )

    result = runner.invoke(
        app,
        ["tipsy", "preflight-btc", "--instance-root", str(tmp_path)],
    )

    assert result.exit_code == 0
    assert "BTC runtime preflight passed" in result.output
    assert "host_mode=Wine" in result.output
    assert "batch_tipsy_exe=" in result.output
    assert "wine_prefix=" in result.output
    assert "config_file=" in result.output


def test_tipsy_preflight_btc_cli_config_invalid_exit_1(
    monkeypatch, tmp_path: Path
) -> None:
    def raise_config_error(**kwargs: object) -> object:
        raise BTCRuntimeConfigError("bad wine prefix in runtime yaml")

    monkeypatch.setattr(cli_main, "resolve_btc_runtime_config", raise_config_error)

    result = runner.invoke(
        app,
        ["tipsy", "preflight-btc", "--instance-root", str(tmp_path)],
    )

    assert result.exit_code == 1
    assert "BTC runtime config invalid" in result.output
    assert "bad wine prefix in runtime yaml" in result.output


def test_tipsy_preflight_btc_cli_tool_missing_exit_2(
    monkeypatch, tmp_path: Path
) -> None:
    no_wine_runtime = BTCRuntimeConfig(
        batch_tipsy_exe=None,
        wine_executable=None,
        wine_prefix=None,
        use_xvfb=False,
        host_mode="wine",
        xvfb_executable=None,
    )
    monkeypatch.setattr(
        cli_main,
        "resolve_btc_runtime_config",
        lambda **kwargs: no_wine_runtime,
    )

    result = runner.invoke(
        app,
        ["tipsy", "preflight-btc", "--instance-root", str(tmp_path)],
    )

    assert result.exit_code == 2
    assert "no Wine executable was resolved" in result.output


def test_tipsy_preflight_btc_cli_missing_exe_exit_1(monkeypatch, tmp_path: Path) -> None:
    missing_exe_runtime = BTCRuntimeConfig(
        batch_tipsy_exe=None,
        wine_executable="wine",
        wine_prefix=None,
        use_xvfb=False,
        host_mode="wine",
        xvfb_executable=None,
    )
    monkeypatch.setattr(
        cli_main,
        "resolve_btc_runtime_config",
        lambda **kwargs: missing_exe_runtime,
    )

    def raise_not_found(**kwargs: object) -> object:
        raise FileNotFoundError("Could not resolve BatchTIPSY BTC executable.")

    monkeypatch.setattr(cli_main, "resolve_btc_executable", raise_not_found)

    result = runner.invoke(
        app,
        ["tipsy", "preflight-btc", "--instance-root", str(tmp_path)],
    )

    assert result.exit_code == 1
    assert "Could not resolve BatchTIPSY BTC executable" in result.output


def test_tipsy_preflight_btc_cli_wsl_interop_rejects_non_carrier_wine_executable(
    monkeypatch, tmp_path: Path
) -> None:
    """m2: preflight agrees with the runtime validator on interop carriers."""
    bad_carrier_runtime = BTCRuntimeConfig(
        batch_tipsy_exe=None,
        wine_executable="/usr/bin/wine",
        wine_prefix=None,
        use_xvfb=False,
        host_mode="wsl-interop",
        xvfb_executable=None,
    )
    monkeypatch.setattr(
        cli_main,
        "resolve_btc_runtime_config",
        lambda **kwargs: bad_carrier_runtime,
    )

    result = runner.invoke(
        app,
        ["tipsy", "preflight-btc", "--instance-root", str(tmp_path)],
    )

    assert result.exit_code == 2
    assert "wsl-interop" in result.output
    assert "powershell.exe or cmd.exe" in result.output
    assert "/usr/bin/wine" in result.output


def test_tipsy_preflight_btc_cli_probe_wires_run_btc_cli(
    monkeypatch, tmp_path: Path
) -> None:
    exe = tmp_path / "TIPSYbtc.exe"
    exe.write_text("", encoding="utf-8")
    fake_runtime = _fake_btc_runtime_config(
        exe=exe,
        prefix=tmp_path / ".wine-tipsy64",
    )
    monkeypatch.setattr(
        cli_main, "resolve_btc_runtime_config", lambda **kwargs: fake_runtime
    )
    captured: dict[str, object] = {}

    def fake_run_btc_cli(**kwargs: object) -> BTCRunResult:
        captured.update(kwargs)
        return BTCRunResult(
            run_id="btc_preflight_probe",
            mode="TSR",
            manifest_path=tmp_path / "probe_manifest.json",
            stdout_log_path=tmp_path / "probe_stdout.log",
            stderr_log_path=tmp_path / "probe_stderr.log",
            output_csv_path=tmp_path / "probe_output.csv",
            error_csv_path=tmp_path / "probe_error.csv",
            executable_path=exe,
            install_root=tmp_path / "btc_install",
            working_dir=tmp_path / "work",
            command=(str(exe), "/TSR", "preflight_probe_input.csv"),
            copied_install=False,
            exit_code=0,
            duration_sec=1.0,
            report_template_path=None,
        )

    monkeypatch.setattr(cli_main, "run_btc_cli", fake_run_btc_cli)

    result = runner.invoke(
        app,
        ["tipsy", "preflight-btc", "--instance-root", str(tmp_path), "--probe"],
    )

    assert result.exit_code == 0
    assert captured["btc_runtime_config"] is fake_runtime
    assert Path(captured["input_csv"]).name == "preflight_probe_input.csv"
    assert "probe exit_code=0" in result.output
    assert "BTC runtime preflight passed" in result.output


def test_tipsy_run_btc_cli_passes_runtime_options(monkeypatch, tmp_path: Path) -> None:
    input_csv = tmp_path / "MSYT.csv"
    input_csv.write_text("feature_id\n1\n", encoding="utf-8")
    wine_prefix = tmp_path / "wine-prefix"
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
            "--instance-root",
            str(tmp_path),
            "--wine-prefix",
            str(wine_prefix),
            "--wine-exe",
            "wine-8.0",
            "--use-xvfb",
            "--host-mode",
            "wine",
        ],
    )

    assert result.exit_code == 0
    assert captured["wine_prefix"] == wine_prefix
    assert captured["wine_executable"] == "wine-8.0"
    assert captured["use_xvfb"] is True
    assert captured["host_mode"] == "wine"


def test_tsa_btc_post_tipsy_cli_passes_runtime_options(
    monkeypatch, tmp_path: Path
) -> None:
    data_root = tmp_path / "data"
    data_root.mkdir()
    (data_root / "03_input-tsa29.csv").write_text(
        "feature_id\n1000\n", encoding="utf-8"
    )
    wine_prefix = tmp_path / "wine-prefix"
    captured: dict[str, object] = {}

    def fake_btc_post_tipsy(**kwargs: object) -> BTCPostTipsyRunResult:
        captured.update(kwargs)
        btc_result = BTCRunResult(
            run_id="btc_post_tipsy_test_tsa29",
            mode="TSR",
            manifest_path=tmp_path / "logs" / "btc_manifest.json",
            stdout_log_path=tmp_path / "logs" / "btc_stdout.log",
            stderr_log_path=tmp_path / "logs" / "btc_stderr.log",
            output_csv_path=data_root / "04_output-tsa29.csv",
            error_csv_path=data_root / "04_error-tsa29.csv",
            executable_path=tmp_path / "btc" / "TIPSYbtc.exe",
            install_root=tmp_path / "btc",
            working_dir=tmp_path / "scratch" / "work",
            command=("btc.exe", "/TSR", "MSYT.csv"),
            copied_install=True,
            exit_code=0,
            duration_sec=1.0,
            report_template_path=tmp_path / "btc" / "TimberSupply.rpt",
        )
        bundle_result = PostTipsyBundleResult(
            tsa_list=["29"],
            au_rows=1,
            curve_rows=2,
            curve_points_rows=4,
            tipsy_curves_paths=[data_root / "tipsy_curves_tsa29.csv"],
            tipsy_sppcomp_paths=[data_root / "tipsy_sppcomp_tsa29.csv"],
            au_table_path=data_root / "model_input_bundle" / "au_table.csv",
            curve_table_path=data_root / "model_input_bundle" / "curve_table.csv",
            curve_points_table_path=data_root
            / "model_input_bundle"
            / "curve_points_table.csv",
        )
        post_tipsy = PostTipsyBundleRunResult(
            manifest_path=tmp_path / "logs" / "run_manifest.json",
            result=bundle_result,
        )
        return BTCPostTipsyRunResult(
            btc_results=[btc_result],
            post_tipsy_result=post_tipsy,
        )

    monkeypatch.setattr(
        cli_main,
        "run_btc_and_post_tipsy_bundle_with_manifest",
        fake_btc_post_tipsy,
    )

    result = runner.invoke(
        app,
        [
            "tsa",
            "btc-post-tipsy",
            "--instance-root",
            str(tmp_path),
            "--tsa",
            "29",
            "--wine-prefix",
            str(wine_prefix),
            "--wine-exe",
            "wine-8.0",
            "--use-xvfb",
            "--host-mode",
            "wine",
        ],
    )

    assert result.exit_code == 0
    assert captured["wine_prefix"] == wine_prefix
    assert captured["wine_executable"] == "wine-8.0"
    assert captured["use_xvfb"] is True
    assert captured["host_mode"] == "wine"
