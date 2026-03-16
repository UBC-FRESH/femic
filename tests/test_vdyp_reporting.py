from __future__ import annotations

from pathlib import Path

from femic.vdyp.reporting import summarize_curve_selection_rows, summarize_vdyp_logs


def _write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def test_summarize_vdyp_logs_counts_and_anchor_match(tmp_path: Path) -> None:
    curve_log = tmp_path / "curve.jsonl"
    run_log = tmp_path / "run.jsonl"
    _write(
        curve_log,
        "\n".join(
            [
                '{"status":"ok","stage":"toe_fit","first_age":1.0,"first_volume":1e-6,'
                '"context":{"tsa":"08"}}',
                '{"status":"warning","stage":"curve_input","context":{"tsa":"08"}}',
                "not-json",
            ]
        )
        + "\n",
    )
    _write(
        run_log,
        "\n".join(
            [
                '{"status":"dispatch","phase":"bootstrap","context":{"tsa":"08"}}',
                '{"status":"ok","phase":"auto_small_sample","context":{"tsa":"08"}}',
                "[]",
            ]
        )
        + "\n",
    )

    summary = summarize_vdyp_logs(
        curve_log_path=curve_log,
        run_log_path=run_log,
        expected_first_age=1.0,
        expected_first_volume=1e-6,
        tolerance=1e-12,
    )

    assert summary.curve_events == 2
    assert summary.curve_parse_errors == 1
    assert summary.curve_status_counts == {"ok": 1, "warning": 1}
    assert summary.curve_stage_counts == {"curve_input": 1, "toe_fit": 1}
    assert summary.first_point_events == 1
    assert summary.first_point_matches == 1
    assert summary.first_point_mismatches == 0

    assert summary.run_events == 2
    assert summary.run_parse_errors == 1
    assert summary.run_status_counts == {"dispatch": 1, "ok": 1}
    assert summary.run_phase_counts == {"auto_small_sample": 1, "bootstrap": 1}


def test_summarize_curve_selection_rows_builds_reviewer_rows(tmp_path: Path) -> None:
    curve_log = tmp_path / "curve.jsonl"
    _write(
        curve_log,
        "\n".join(
            [
                '{"event":"vdyp_curve_fit","stage":"fit_quality_gate",'
                '"reason":"fit_quality_gate_failed",'
                '"context":{"tsa":"29","stratum_code":"SBPS_PL","si_level":"L"}}',
                '{"event":"vdyp_curve_fit","stage":"left_toe_censor",'
                '"reason":"left_toe_censor_selected",'
                '"context":{"tsa":"29","stratum_code":"SBPS_PL","si_level":"L"}}',
                '{"event":"vdyp_curve_fit","stage":"fallback_policy",'
                '"reason":"curve_selected","selected_path":"censored_refit",'
                '"context":{"tsa":"29","stratum_code":"SBPS_PL","si_level":"L"}}',
            ]
        )
        + "\n",
    )

    rows = summarize_curve_selection_rows(curve_log_path=curve_log)
    assert len(rows) == 1
    row = rows[0]
    assert row.tsa == "29"
    assert row.stratum_code == "SBPS_PL"
    assert row.si_level == "L"
    assert row.selected_path == "censored_refit"
    assert row.fit_quality_gate_failed is True
    assert row.left_toe_censor_selected is True


def test_summarize_curve_selection_rows_flags_selected_curve_gate_rescue(
    tmp_path: Path,
) -> None:
    curve_log = tmp_path / "curve.jsonl"
    _write(
        curve_log,
        "\n".join(
            [
                '{"event":"vdyp_curve_fit","stage":"fit_quality_gate",'
                '"reason":"selected_curve_gate_rescue",'
                '"context":{"tsa":"29","stratum_code":"MS_PLI","si_level":"H"}}',
                '{"event":"vdyp_curve_fit","stage":"fallback_policy",'
                '"reason":"curve_selected","selected_path":"censored_refit",'
                '"context":{"tsa":"29","stratum_code":"MS_PLI","si_level":"H"}}',
            ]
        )
        + "\n",
    )

    rows = summarize_curve_selection_rows(curve_log_path=curve_log)
    assert len(rows) == 1
    row = rows[0]
    assert row.fit_quality_gate_failed is True
