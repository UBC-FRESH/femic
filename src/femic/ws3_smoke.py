"""Woodstock-to-ws3 smoke-test helpers for instance validation workflows."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
import subprocess
import sys

import pandas as pd

from femic.ws3_bridge import build_ws3_sections_from_femic_woodstock


@dataclass(frozen=True)
class Ws3SmokeResult:
    """Machine-readable summary of a ws3 smoke-test execution."""

    status: str
    woodstock_dir: str
    required_files_present: bool
    yields_rows: int
    areas_rows: int
    actions_rows: int
    transitions_rows: int
    yields_total_volume: float
    areas_total_ha: float
    ws3_command_executed: bool
    ws3_command: str | None
    ws3_returncode: int | None
    ws3_stdout_log: str | None
    ws3_stderr_log: str | None
    ws3_bridge_dir: str | None
    ws3_bridge_model_name: str | None
    ws3_builtin_smoke_executed: bool
    message: str
    timestamp_utc: str


def run_ws3_smoke(
    *,
    woodstock_dir: Path,
    output_path: Path | None = None,
    ws3_command: str | None = None,
    ws3_workdir: Path | None = None,
    timeout_seconds: int = 600,
    require_command: bool = False,
    ws3_repo_path: Path | None = None,
    run_builtin_model_smoke: bool = False,
    ws3_bridge_dir: Path | None = None,
    ws3_bridge_model_name: str = "femic_tsa_ws3",
) -> Ws3SmokeResult:
    """Validate Woodstock exports and optionally execute a ws3 smoke command."""
    resolved_dir = woodstock_dir.expanduser().resolve()
    required = {
        "yields": resolved_dir / "woodstock_yields.csv",
        "areas": resolved_dir / "woodstock_areas.csv",
        "actions": resolved_dir / "woodstock_actions.csv",
        "transitions": resolved_dir / "woodstock_transitions.csv",
    }
    missing = [str(path) for path in required.values() if not path.exists()]
    now = _iso_utc(datetime.now(UTC))
    if missing:
        result = Ws3SmokeResult(
            status="failed",
            woodstock_dir=str(resolved_dir),
            required_files_present=False,
            yields_rows=0,
            areas_rows=0,
            actions_rows=0,
            transitions_rows=0,
            yields_total_volume=0.0,
            areas_total_ha=0.0,
            ws3_command_executed=False,
            ws3_command=ws3_command,
            ws3_returncode=None,
            ws3_stdout_log=None,
            ws3_stderr_log=None,
            ws3_bridge_dir=None,
            ws3_bridge_model_name=None,
            ws3_builtin_smoke_executed=False,
            message=f"Missing required Woodstock artifacts: {', '.join(missing)}",
            timestamp_utc=now,
        )
        _write_output(result=result, output_path=output_path)
        return result

    yields = pd.read_csv(required["yields"])
    areas = pd.read_csv(required["areas"])
    actions = pd.read_csv(required["actions"])
    transitions = pd.read_csv(required["transitions"])

    yields_rows = int(yields.shape[0])
    areas_rows = int(areas.shape[0])
    actions_rows = int(actions.shape[0])
    transitions_rows = int(transitions.shape[0])
    yields_total_volume = float(
        pd.to_numeric(yields["volume"], errors="coerce").fillna(0.0).sum()
    )
    areas_total_ha = float(
        pd.to_numeric(areas["area_ha"], errors="coerce").fillna(0.0).sum()
    )

    if (
        yields_rows <= 0
        or areas_rows <= 0
        or actions_rows <= 0
        or transitions_rows <= 0
        or yields_total_volume <= 0
        or areas_total_ha <= 0
    ):
        result = Ws3SmokeResult(
            status="failed",
            woodstock_dir=str(resolved_dir),
            required_files_present=True,
            yields_rows=yields_rows,
            areas_rows=areas_rows,
            actions_rows=actions_rows,
            transitions_rows=transitions_rows,
            yields_total_volume=yields_total_volume,
            areas_total_ha=areas_total_ha,
            ws3_command_executed=False,
            ws3_command=ws3_command,
            ws3_returncode=None,
            ws3_stdout_log=None,
            ws3_stderr_log=None,
            ws3_bridge_dir=None,
            ws3_bridge_model_name=None,
            ws3_builtin_smoke_executed=False,
            message="Woodstock tables are present but failed sanity thresholds.",
            timestamp_utc=now,
        )
        _write_output(result=result, output_path=output_path)
        return result

    ws3_command_executed = False
    ws3_returncode: int | None = None
    ws3_stdout_log: Path | None = None
    ws3_stderr_log: Path | None = None
    bridge_dir: Path | None = None
    bridge_model_name: str | None = None
    ws3_builtin_smoke_executed = False
    status = "ok"
    message = "Woodstock structure and sanity checks passed."
    if ws3_command:
        ws3_command_executed = True
        run_root = (
            ws3_workdir.expanduser().resolve()
            if ws3_workdir is not None
            else resolved_dir
        )
        log_root = (
            output_path.parent.expanduser().resolve()
            if output_path is not None
            else (resolved_dir / "evidence")
        )
        log_root.mkdir(parents=True, exist_ok=True)
        ws3_stdout_log = log_root / "ws3_smoke_stdout.log"
        ws3_stderr_log = log_root / "ws3_smoke_stderr.log"
        completed = subprocess.run(
            ws3_command,
            cwd=run_root,
            shell=True,
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
        )
        ws3_returncode = int(completed.returncode)
        ws3_stdout_log.write_text(completed.stdout, encoding="utf-8")
        ws3_stderr_log.write_text(completed.stderr, encoding="utf-8")
        if ws3_returncode != 0:
            status = "failed"
            message = f"ws3 command failed with return code {ws3_returncode}."
        else:
            message = "Woodstock checks passed and ws3 smoke command exited cleanly."
    elif run_builtin_model_smoke:
        ws3_builtin_smoke_executed = True
        bridge_dir = (
            ws3_bridge_dir.expanduser().resolve()
            if ws3_bridge_dir is not None
            else (resolved_dir / "ws3_bridge")
        )
        bridge_model_name = ws3_bridge_model_name
        bridge = build_ws3_sections_from_femic_woodstock(
            woodstock_dir=resolved_dir,
            output_dir=bridge_dir,
            model_name=bridge_model_name,
        )
        builtin_status, builtin_message = _run_builtin_ws3_model_smoke(
            ws3_repo_path=ws3_repo_path,
            model_path=bridge.output_dir,
            model_name=bridge.model_name,
        )
        if builtin_status != "ok":
            status = "failed"
        else:
            status = "ok"
        message = builtin_message
    elif require_command:
        status = "failed"
        message = "No ws3 command provided while require_command=true."
    else:
        status = "warn"
        message = (
            "Woodstock checks passed; ws3 command not executed "
            "(set --ws3-command for full smoke test)."
        )

    result = Ws3SmokeResult(
        status=status,
        woodstock_dir=str(resolved_dir),
        required_files_present=True,
        yields_rows=yields_rows,
        areas_rows=areas_rows,
        actions_rows=actions_rows,
        transitions_rows=transitions_rows,
        yields_total_volume=yields_total_volume,
        areas_total_ha=areas_total_ha,
        ws3_command_executed=ws3_command_executed,
        ws3_command=ws3_command,
        ws3_returncode=ws3_returncode,
        ws3_stdout_log=str(ws3_stdout_log) if ws3_stdout_log is not None else None,
        ws3_stderr_log=str(ws3_stderr_log) if ws3_stderr_log is not None else None,
        ws3_bridge_dir=str(bridge_dir) if bridge_dir is not None else None,
        ws3_bridge_model_name=bridge_model_name,
        ws3_builtin_smoke_executed=ws3_builtin_smoke_executed,
        message=message,
        timestamp_utc=now,
    )
    _write_output(result=result, output_path=output_path)
    return result


def _write_output(*, result: Ws3SmokeResult, output_path: Path | None) -> None:
    if output_path is None:
        return
    resolved = output_path.expanduser().resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(json.dumps(asdict(result), indent=2), encoding="utf-8")


def _iso_utc(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return (
        value.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    )


def _run_builtin_ws3_model_smoke(
    *,
    ws3_repo_path: Path | None,
    model_path: Path,
    model_name: str,
) -> tuple[str, str]:
    try:
        if ws3_repo_path is not None:
            repo_root = ws3_repo_path.expanduser().resolve()
            if str(repo_root) not in sys.path:
                sys.path.insert(0, str(repo_root))
        from ws3.forest import ForestModel  # type: ignore[import-not-found]
    except Exception as exc:  # pragma: no cover - environment dependent
        return ("failed", f"Failed to import ws3 runtime: {exc}")

    try:
        fm = ForestModel(
            model_name=model_name,
            model_path=str(model_path),
            base_year=2026,
            horizon=2,
            period_length=10,
        )
        fm.import_landscape_section()
        fm.import_areas_section(convert_periods_to_years=10)
        fm.import_yields_section(convert_periods_to_years=10)
        fm.import_actions_section(convert_periods_to_years=10)
        fm.import_transitions_section(convert_periods_to_years=10)
        fm.initialize_areas()
        fm.compile_actions()
        action_codes = sorted(fm.actions.keys())
        if not action_codes:
            return ("failed", "ws3 model loaded but has no actions.")
        total_area = float(fm.inventory(0))
        if total_area <= 0:
            return ("failed", "ws3 model loaded but inventory area is zero.")
        # Model-agnostic smoke check: verify the schedule compiler runs.
        # We do not force an areaselector operation here because action-mask
        # semantics vary across inputs and can produce false-negative smoke failures.
        schedule = fm.compile_schedule()
        schedule_len = len(schedule) if schedule is not None else 0
        return (
            "ok",
            (
                "ws3 builtin smoke passed "
                f"(actions={len(action_codes)}, schedule_rows={schedule_len}, "
                f"inventory_area={total_area:.3f})."
            ),
        )
    except Exception as exc:  # pragma: no cover - environment dependent
        return ("failed", f"ws3 builtin smoke failed: {exc}")
