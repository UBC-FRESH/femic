from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from femic.ws3_smoke import run_ws3_smoke


def _write_minimal_woodstock(woodstock_dir: Path) -> None:
    woodstock_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [
            {
                "tsa": "29",
                "au_id": 1,
                "ifm": "managed",
                "curve_id": 11,
                "age": 1,
                "volume": 1.2,
            }
        ]
    ).to_csv(woodstock_dir / "woodstock_yields.csv", index=False)
    pd.DataFrame(
        [
            {
                "stand_id": 1,
                "tsa": "29",
                "au_id": 1,
                "ifm": "managed",
                "age": 1,
                "area_ha": 3.4,
            }
        ]
    ).to_csv(woodstock_dir / "woodstock_areas.csv", index=False)
    pd.DataFrame(
        [
            {
                "tsa": "29",
                "au_id": 1,
                "action_id": "CC",
                "from_ifm": "managed",
                "to_ifm": "managed",
            }
        ]
    ).to_csv(woodstock_dir / "woodstock_actions.csv", index=False)
    pd.DataFrame(
        [
            {
                "tsa": "29",
                "au_id": 1,
                "action_id": "CC",
                "from_ifm": "managed",
                "to_ifm": "managed",
            }
        ]
    ).to_csv(woodstock_dir / "woodstock_transitions.csv", index=False)


def test_run_ws3_smoke_warns_without_command(tmp_path: Path) -> None:
    woodstock_dir = tmp_path / "output" / "woodstock"
    report_path = tmp_path / "evidence" / "ws3_smoke_report.latest.json"
    _write_minimal_woodstock(woodstock_dir)

    result = run_ws3_smoke(
        woodstock_dir=woodstock_dir,
        output_path=report_path,
        run_builtin_model_smoke=False,
    )

    assert result.status == "warn"
    assert result.required_files_present is True
    assert result.yields_rows == 1
    assert result.areas_rows == 1
    assert report_path.exists()
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["status"] == "warn"


def test_run_ws3_smoke_ok_with_command(tmp_path: Path) -> None:
    woodstock_dir = tmp_path / "output" / "woodstock"
    report_path = tmp_path / "evidence" / "ws3_smoke_report.latest.json"
    _write_minimal_woodstock(woodstock_dir)

    result = run_ws3_smoke(
        woodstock_dir=woodstock_dir,
        output_path=report_path,
        ws3_command="true",
        timeout_seconds=5,
        run_builtin_model_smoke=False,
    )

    assert result.status == "ok"
    assert result.ws3_command_executed is True
    assert result.ws3_returncode == 0
    assert report_path.exists()


def test_run_ws3_smoke_fails_when_missing_files(tmp_path: Path) -> None:
    woodstock_dir = tmp_path / "output" / "woodstock"
    woodstock_dir.mkdir(parents=True, exist_ok=True)

    result = run_ws3_smoke(woodstock_dir=woodstock_dir, run_builtin_model_smoke=False)

    assert result.status == "failed"
    assert result.required_files_present is False


def test_run_ws3_smoke_builtin_reports_import_failure(tmp_path: Path) -> None:
    woodstock_dir = tmp_path / "output" / "woodstock"
    report_path = tmp_path / "evidence" / "ws3_smoke_report.latest.json"
    _write_minimal_woodstock(woodstock_dir)

    result = run_ws3_smoke(
        woodstock_dir=woodstock_dir,
        output_path=report_path,
        ws3_repo_path=tmp_path / "does_not_exist",
        run_builtin_model_smoke=True,
    )

    assert result.status == "failed"
    assert result.ws3_builtin_smoke_executed is True
    assert (
        "Failed to import ws3 runtime" in result.message
        or "failed" in result.message.lower()
    )
