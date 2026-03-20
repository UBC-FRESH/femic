from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from femic.cli.main import app


runner = CliRunner()
FIXTURE_DIR = Path(__file__).parent / "fixtures" / "vdyp" / "tsa08_debug"


def test_vdyp_report_cli_budget_passes() -> None:
    result = runner.invoke(
        app,
        [
            "vdyp",
            "report",
            "--curve-log",
            str(FIXTURE_DIR / "vdyp_curve_events-tsa08-fixture.jsonl"),
            "--run-log",
            str(FIXTURE_DIR / "vdyp_runs-tsa08-fixture.jsonl"),
            "--max-curve-warnings",
            "2",
            "--max-first-point-mismatches",
            "0",
            "--min-curve-events",
            "5",
            "--min-run-events",
            "6",
        ],
    )

    assert result.exit_code == 0
    assert "Curve events: 5" in result.stdout


def test_vdyp_report_cli_budget_fails() -> None:
    result = runner.invoke(
        app,
        [
            "vdyp",
            "report",
            "--curve-log",
            str(FIXTURE_DIR / "vdyp_curve_events-tsa08-fixture.jsonl"),
            "--run-log",
            str(FIXTURE_DIR / "vdyp_runs-tsa08-fixture.jsonl"),
            "--max-curve-warnings",
            "1",
        ],
    )

    assert result.exit_code == 1
    assert "VDYP warning-budget violations" in result.stdout


def test_vdyp_report_cli_writes_selection_summary_csv(tmp_path: Path) -> None:
    curve_log = tmp_path / "curve.jsonl"
    run_log = tmp_path / "run.jsonl"
    out_csv = tmp_path / "selection_summary.csv"
    curve_log.write_text(
        "\n".join(
            [
                '{"event":"vdyp_curve_fit","stage":"fallback_policy",'
                '"reason":"curve_selected","selected_path":"tail_blend",'
                '"context":{"tsa":"29","stratum_code":"SBPS_PL","si_level":"L"}}'
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    run_log.write_text(
        '{"event":"vdyp_run","status":"ok","phase":"auto","context":{"tsa":"29"}}\n',
        encoding="utf-8",
    )
    result = runner.invoke(
        app,
        [
            "vdyp",
            "report",
            "--curve-log",
            str(curve_log),
            "--run-log",
            str(run_log),
            "--selection-summary-out",
            str(out_csv),
        ],
    )

    assert result.exit_code == 0
    assert out_csv.exists()
    csv_text = out_csv.read_text(encoding="utf-8")
    assert "selected_path" in csv_text
    assert "tail_blend" in csv_text
