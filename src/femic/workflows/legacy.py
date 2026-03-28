"""Legacy workflow wrappers for FEMIC."""

from __future__ import annotations

from contextlib import contextmanager
import os
import sys
import time
from datetime import datetime, timezone
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, cast
import uuid

import pandas as pd

from femic.pipeline.bundle import (
    build_bundle_tables_from_curves,
    resolve_bundle_paths,
    write_bundle_tables,
)
from femic.pipeline.io import PipelineRunConfig, build_legacy_execution_plan
from femic.pipeline.legacy_runtime import build_legacy_01b_runtime_config
from femic.pipeline.pre_vdyp import load_vdyp_prep_checkpoint
from femic.pipeline.manifest import (
    build_run_manifest_payload,
    collect_runtime_versions,
    write_manifest,
)
from femic.pipeline.tipsy import BTCRunResult, run_btc_cli
from femic.pipeline.stages import load_legacy_module, run_legacy_subprocess
from femic.workflows.legacy_resources import (
    LEGACY_SCRIPT_FILENAMES,
    resolve_legacy_script_bundle,
)


_LEGACY_NOISE_LINES = {"Error in sys.excepthook:", "Original exception was:"}
_DEFAULT_SI_LEVELS = ("L", "M", "H")
_CANFI_MAP = {
    "AC": 1211,
    "AT": 1201,
    "BL": 304,
    "CW": 301,
    "EP": 1303,
    "FD": 500,
    "FDI": 500,
    "FDC": 500,
    "HW": 402,
    "PL": 204,
    "PLI": 204,
    "SB": 101,
    "SS": 103,
    "SE": 104,
    "SW": 105,
    "SX": 100,
    "S": 100,
    "YC": 302,
}


@dataclass(frozen=True)
class PostTipsyBundleResult:
    """Result payload returned by post-TIPSY downstream assembly workflow."""

    tsa_list: list[str]
    au_rows: int
    curve_rows: int
    curve_points_rows: int
    tipsy_curves_paths: list[Path]
    tipsy_sppcomp_paths: list[Path]
    au_table_path: Path
    curve_table_path: Path
    curve_points_table_path: Path


@dataclass(frozen=True)
class PostTipsyBundleRunResult:
    """Manifest path + downstream post-TIPSY bundle assembly result."""

    manifest_path: Path
    result: PostTipsyBundleResult


@dataclass(frozen=True)
class BTCPostTipsyRunResult:
    """Combined unattended BTC run results plus downstream post-TIPSY bundle result."""

    btc_results: list[BTCRunResult]
    post_tipsy_result: PostTipsyBundleRunResult


def _default_canfi_species(stratum_code: str) -> int:
    species = str(stratum_code).split("_")[-1].split("+")[0]
    if species in _CANFI_MAP:
        return _CANFI_MAP[species]
    return _CANFI_MAP.get(species[:2], 100)


def _build_au_maps_from_results(
    *,
    results_for_tsa: list[tuple[int, str, Any]],
    si_levels: tuple[str, ...] = _DEFAULT_SI_LEVELS,
) -> tuple[dict[tuple[str, str], int], dict[int, tuple[str, str]]]:
    scsi_au_tsa: dict[tuple[str, str], int] = {}
    au_scsi_tsa: dict[int, tuple[str, str]] = {}
    for stratumi, stratum_code, _result in results_for_tsa:
        for idx, si_level in enumerate(si_levels, start=1):
            au_base = 1000 * idx + int(stratumi)
            key = (str(stratum_code), str(si_level))
            scsi_au_tsa[key] = au_base
            au_scsi_tsa[au_base] = key
    return scsi_au_tsa, au_scsi_tsa


def _build_au_maps_from_bundle_au_table(
    *,
    au_table: Any,
) -> tuple[dict[tuple[str, str], int], dict[int, tuple[str, str]]]:
    """Rebuild legacy AU<->(stratum, SI) maps from a persisted bundle AU table."""
    scsi_au_tsa: dict[tuple[str, str], int] = {}
    au_scsi_tsa: dict[int, tuple[str, str]] = {}
    for row in au_table.itertuples(index=False):
        stratum_code = str(getattr(row, "stratum_code"))
        si_level = str(getattr(row, "si_level"))
        managed_curve_id = int(getattr(row, "managed_curve_id"))
        au_base = int(str(managed_curve_id)[-4:])
        key = (stratum_code, si_level)
        scsi_au_tsa[key] = au_base
        au_scsi_tsa[au_base] = key
    return scsi_au_tsa, au_scsi_tsa


def _normalize_species_code(value: object) -> str:
    code = str(value).strip().upper()
    if not code or code in {"NAN", "NONE", "X", "XX"}:
        return ""
    return code


def _load_species_universe_for_tsas(
    *,
    data_root: Path,
    tsa_list: list[str],
    message_fn: Callable[[str], Any] = print,
) -> list[str]:
    """Load unique top-6 VRI species codes for selected TSAs from checkpoint8."""
    checkpoint_path = data_root / "ria_vri_vclr1p_checkpoint8.feather"
    if not checkpoint_path.exists():
        message_fn(f"warning: species-universe scan skipped; missing {checkpoint_path}")
        return []
    table = pd.read_feather(checkpoint_path)
    if "tsa_code" not in table.columns:
        message_fn(
            "warning: species-universe scan skipped; checkpoint missing 'tsa_code'"
        )
        return []
    normalized = {str(tsa).zfill(2).lower() for tsa in tsa_list}
    tsa_mask = table["tsa_code"].astype(str).str.lower().isin(normalized)
    scoped = table.loc[tsa_mask]
    species_codes: set[str] = set()
    for idx in range(1, 7):
        species_col = f"SPECIES_CD_{idx}"
        if species_col not in scoped.columns:
            continue
        pct_col = f"SPECIES_PCT_{idx}"
        if pct_col in scoped.columns:
            pct_mask = pd.to_numeric(scoped[pct_col], errors="coerce").fillna(0) > 0
            species_values = scoped.loc[pct_mask, species_col]
        else:
            species_values = scoped[species_col]
        species_codes.update(
            code for code in species_values.map(_normalize_species_code) if code
        )
    return sorted(species_codes)


def _managed_curve_env_overrides(
    *,
    managed_curve_mode: str | None,
    managed_curve_x_scale: float | None,
    managed_curve_y_scale: float | None,
    managed_curve_truncate_at_culm: bool | None,
    managed_curve_max_age: int | None,
) -> dict[str, str]:
    env: dict[str, str] = {}
    if managed_curve_mode is not None:
        env["FEMIC_MANAGED_CURVE_MODE"] = str(managed_curve_mode)
    if managed_curve_x_scale is not None:
        env["FEMIC_MANAGED_CURVE_X_SCALE"] = str(float(managed_curve_x_scale))
    if managed_curve_y_scale is not None:
        env["FEMIC_MANAGED_CURVE_Y_SCALE"] = str(float(managed_curve_y_scale))
    if managed_curve_truncate_at_culm is not None:
        env["FEMIC_MANAGED_CURVE_TRUNCATE_AT_CULM"] = (
            "1" if managed_curve_truncate_at_culm else "0"
        )
    if managed_curve_max_age is not None:
        env["FEMIC_MANAGED_CURVE_MAX_AGE"] = str(int(managed_curve_max_age))
    return env


@contextmanager
def _temporary_env(overrides: Mapping[str, str]) -> Any:
    previous: dict[str, str | None] = {}
    for key, value in overrides.items():
        previous[key] = os.environ.get(key)
        os.environ[key] = value
    try:
        yield
    finally:
        for key, prior in previous.items():
            if prior is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = prior


@contextmanager
def _temporary_cwd(path: Path) -> Any:
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


def _vdyp_species_proportions_for_tsa(
    *,
    results_for_tsa: list[tuple[int, str, Any]],
) -> dict[tuple[str, str], dict[str, float]]:
    out: dict[tuple[str, str], dict[str, float]] = {}
    for _stratumi, stratum_code, result in results_for_tsa:
        for si_level in _DEFAULT_SI_LEVELS:
            result_si = result.get(si_level, {}) if isinstance(result, dict) else {}
            species_map = (
                result_si.get("species", {}) if isinstance(result_si, dict) else {}
            )
            normalized: dict[str, float] = {}
            total = 0.0
            for species_code, payload in species_map.items():
                code = _normalize_species_code(species_code)
                if not code:
                    continue
                pct = float(payload.get("pct", 0.0))
                if pct <= 0:
                    continue
                prop = pct * 0.01
                normalized[code] = normalized.get(code, 0.0) + prop
                total += prop
            if total > 0:
                for code in list(normalized.keys()):
                    normalized[code] = normalized[code] / total
            out[(str(stratum_code), str(si_level))] = normalized
    return out


def run_post_tipsy_bundle(
    *,
    tsa_list: list[str],
    repo_root: Path | None = None,
    data_root: Path = Path("data"),
    model_input_bundle_dir: Path | None = None,
    run_01b_fn: Callable[..., Any] | None = None,
    canfi_species_fn: Callable[[str], int] = _default_canfi_species,
    message_fn: Callable[[str], Any] = print,
    managed_curve_mode: str | None = None,
    managed_curve_x_scale: float | None = None,
    managed_curve_y_scale: float | None = None,
    managed_curve_truncate_at_culm: bool | None = None,
    managed_curve_max_age: int | None = None,
    tipsy_output_filename_template: str = "04_output-tsa{tsa}.out",
) -> PostTipsyBundleResult:
    """Run downstream 01b + bundle assembly from cached TSA artifacts only."""
    normalized_tsa_list = [str(tsa).zfill(2) for tsa in tsa_list]
    resolved_repo_root = repo_root if repo_root is not None else Path.cwd()

    if run_01b_fn is None:
        filesystem_script_root = (
            resolved_repo_root
            if all(
                (resolved_repo_root / name).is_file()
                for name in LEGACY_SCRIPT_FILENAMES
            )
            else None
        )
        with resolve_legacy_script_bundle(
            explicit_root=filesystem_script_root
        ) as script_bundle:
            module = load_legacy_module(
                script_path=script_bundle.stage01b_path,
                module_name="run_tsa_01b_post_tipsy",
            )
            run_01b = getattr(module, "run_tsa", None)
            if not callable(run_01b):
                raise RuntimeError("01b_run-tsa.py does not define callable run_tsa")
    else:
        run_01b = run_01b_fn

    results: dict[str, Any] = {}
    au_scsi: dict[str, Any] = {}
    scsi_au: dict[str, Any] = {}
    vdyp_curves_smooth: dict[str, Any] = {}
    tipsy_curves: dict[str, Any] = {}
    tipsy_sppcomp: dict[str, Any] = {}
    vdyp_species_proportions: dict[str, dict[tuple[str, str], dict[str, float]]] = {}
    tipsy_curves_paths: list[Path] = []
    tipsy_sppcomp_paths: list[Path] = []

    managed_env_overrides = _managed_curve_env_overrides(
        managed_curve_mode=managed_curve_mode,
        managed_curve_x_scale=managed_curve_x_scale,
        managed_curve_y_scale=managed_curve_y_scale,
        managed_curve_truncate_at_culm=managed_curve_truncate_at_culm,
        managed_curve_max_age=managed_curve_max_age,
    )
    with _temporary_env(managed_env_overrides):
        for tsa in normalized_tsa_list:
            prep_path = data_root / f"vdyp_prep-tsa{tsa}.pkl"
            smooth_path = data_root / f"vdyp_curves_smooth-tsa{tsa}.feather"
            if not smooth_path.exists():
                raise FileNotFoundError(f"Missing smoothed VDYP curves: {smooth_path}")

            bundle_dir = (
                model_input_bundle_dir
                if model_input_bundle_dir is not None
                else (data_root / "model_input_bundle")
            )
            bundle_au_table_path = bundle_dir / "au_table.csv"

            if prep_path.exists():
                results_for_tsa = cast(
                    list[tuple[int, str, Any]],
                    load_vdyp_prep_checkpoint(prep_path),
                )
                results[tsa] = results_for_tsa
                vdyp_species_proportions[tsa] = _vdyp_species_proportions_for_tsa(
                    results_for_tsa=results_for_tsa
                )
                scsi_au[tsa], au_scsi[tsa] = _build_au_maps_from_results(
                    results_for_tsa=results_for_tsa
                )
            elif bundle_au_table_path.exists():
                bundle_au_table = pd.read_csv(bundle_au_table_path)
                bundle_tsa = bundle_au_table.loc[
                    bundle_au_table["tsa"].astype(str).str.lower() == str(tsa).lower()
                ].copy()
                if bundle_tsa.empty:
                    raise FileNotFoundError(
                        "Missing 01a prep checkpoint and no AU table rows for tsa "
                        f"{tsa}: {prep_path}"
                    )
                results_for_tsa = []
                results[tsa] = results_for_tsa
                vdyp_species_proportions[tsa] = {}
                scsi_au[tsa], au_scsi[tsa] = _build_au_maps_from_bundle_au_table(
                    au_table=bundle_tsa
                )
                message_fn(
                    "warning: missing 01a prep checkpoint for tsa %s; rebuilding AU "
                    "maps from persisted bundle au_table.csv" % tsa
                )
            else:
                raise FileNotFoundError(f"Missing 01a prep checkpoint: {prep_path}")

            vdyp_curves_smooth[tsa] = pd.read_feather(smooth_path)
            runtime_config = build_legacy_01b_runtime_config(
                tipsy_params_path_prefix=data_root / "tipsy_params_tsa",
                tipsy_output_root=data_root,
                tipsy_output_filename_template=tipsy_output_filename_template,
            )
            message_fn(f"running 01b for tsa {tsa}")
            with _temporary_cwd(resolved_repo_root):
                run_01b(
                    tsa=tsa,
                    results=results,
                    au_scsi=au_scsi,
                    tipsy_curves=tipsy_curves,
                    vdyp_curves_smooth=vdyp_curves_smooth,
                    runtime_config=runtime_config,
                )
            tipsy_curves_paths.append(data_root / f"tipsy_curves_tsa{tsa}.csv")
            tipsy_sppcomp_paths.append(data_root / f"tipsy_sppcomp_tsa{tsa}.csv")
            tipsy_spp_path = tipsy_sppcomp_paths[-1]
            if tipsy_spp_path.exists():
                tipsy_sppcomp[tsa] = pd.read_csv(tipsy_spp_path)

    species_universe = _load_species_universe_for_tsas(
        data_root=data_root,
        tsa_list=normalized_tsa_list,
        message_fn=message_fn,
    )
    if species_universe:
        message_fn(
            f"species proportion export enabled for {len(species_universe)} species"
        )

    bundle_dir = (
        model_input_bundle_dir
        if model_input_bundle_dir is not None
        else (data_root / "model_input_bundle")
    )
    bundle_paths = resolve_bundle_paths(base_dir=bundle_dir, ensure_dir=True)
    bundle = build_bundle_tables_from_curves(
        tsa_list=normalized_tsa_list,
        vdyp_curves_smooth=vdyp_curves_smooth,
        tipsy_curves=tipsy_curves,
        scsi_au=scsi_au,
        canfi_species_fn=canfi_species_fn,
        species_universe=species_universe,
        vdyp_species_proportions=vdyp_species_proportions,
        tipsy_species_proportions=tipsy_sppcomp,
        pd_module=pd,
        message_fn=message_fn,
    )
    write_bundle_tables(
        paths=bundle_paths,
        au_table=bundle.au_table,
        curve_table=bundle.curve_table,
        curve_points_table=bundle.curve_points_table,
    )
    return PostTipsyBundleResult(
        tsa_list=normalized_tsa_list,
        au_rows=int(len(bundle.au_table)),
        curve_rows=int(len(bundle.curve_table)),
        curve_points_rows=int(len(bundle.curve_points_table)),
        tipsy_curves_paths=tipsy_curves_paths,
        tipsy_sppcomp_paths=tipsy_sppcomp_paths,
        au_table_path=bundle_paths.au_table,
        curve_table_path=bundle_paths.curve_table,
        curve_points_table_path=bundle_paths.curve_points_table,
    )


def _build_post_tipsy_manifest_payload(
    *,
    run_id: str,
    run_uuid: str,
    tsa_list: list[str],
    log_dir: Path,
    status: str,
    started_at: datetime,
    finished_at: datetime | None,
    duration_sec: float | None,
    exit_code: int | None,
    result: PostTipsyBundleResult | None,
    error_message: str | None = None,
) -> dict[str, object]:
    artifacts: dict[str, list[dict[str, object]]] = {
        "tipsy_curves": [],
        "tipsy_sppcomp": [],
        "bundle_tables": [],
    }
    outputs: dict[str, object] = {}
    if result is not None:
        artifacts["tipsy_curves"] = [
            {"path": str(path), "exists": path.exists()}
            for path in result.tipsy_curves_paths
        ]
        artifacts["tipsy_sppcomp"] = [
            {"path": str(path), "exists": path.exists()}
            for path in result.tipsy_sppcomp_paths
        ]
        bundle_paths = [
            result.au_table_path,
            result.curve_table_path,
            result.curve_points_table_path,
        ]
        artifacts["bundle_tables"] = [
            {"path": str(path), "exists": path.exists()} for path in bundle_paths
        ]
        outputs = {
            "au_rows": result.au_rows,
            "curve_rows": result.curve_rows,
            "curve_points_rows": result.curve_points_rows,
            "au_table_path": str(result.au_table_path),
            "curve_table_path": str(result.curve_table_path),
            "curve_points_table_path": str(result.curve_points_table_path),
        }
    return {
        "run_id": run_id,
        "run_uuid": run_uuid,
        "workflow": "tsa_post_tipsy",
        "status": status,
        "started_at_utc": started_at.isoformat(),
        "finished_at_utc": finished_at.isoformat() if finished_at else None,
        "duration_sec": duration_sec,
        "exit_code": exit_code,
        "tsa_list": tsa_list,
        "log_dir": str(log_dir.resolve()),
        "error_message": error_message,
        "runtime_versions": collect_runtime_versions(),
        "runtime_parameters": {
            "femic_tsa_list": ",".join(tsa_list),
            "femic_run_id": run_id,
            "femic_log_dir": str(log_dir.resolve()),
            "femic_sampling_seed": os.environ.get("FEMIC_SAMPLING_SEED"),
        },
        "env_flags": {
            "FEMIC_DISABLE_IPP": os.environ.get("FEMIC_DISABLE_IPP"),
            "FEMIC_USE_SWIFTER": os.environ.get("FEMIC_USE_SWIFTER"),
            "FEMIC_SAMPLING_SEED": os.environ.get("FEMIC_SAMPLING_SEED"),
        },
        "artifacts": artifacts,
        "outputs": outputs,
    }


def run_post_tipsy_bundle_with_manifest(
    *,
    tsa_list: list[str],
    run_id: str | None = None,
    log_dir: Path = Path("vdyp_io/logs"),
    repo_root: Path | None = None,
    data_root: Path = Path("data"),
    model_input_bundle_dir: Path | None = None,
    run_01b_fn: Callable[..., Any] | None = None,
    canfi_species_fn: Callable[[str], int] = _default_canfi_species,
    message_fn: Callable[[str], Any] = print,
    managed_curve_mode: str | None = None,
    managed_curve_x_scale: float | None = None,
    managed_curve_y_scale: float | None = None,
    managed_curve_truncate_at_culm: bool | None = None,
    managed_curve_max_age: int | None = None,
    tipsy_output_filename_template: str = "04_output-tsa{tsa}.out",
) -> PostTipsyBundleRunResult:
    """Run post-TIPSY downstream assembly and emit run-manifest metadata."""
    normalized_tsa_list = [str(tsa).zfill(2) for tsa in tsa_list]
    effective_run_id = run_id or datetime.now(timezone.utc).strftime(
        "post_tipsy_%Y%m%dT%H%M%SZ"
    )
    resolved_log_dir = Path(log_dir)
    resolved_log_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = resolved_log_dir / f"run_manifest-{effective_run_id}.json"
    run_uuid = str(uuid.uuid4())
    started_at = datetime.now(timezone.utc)
    write_manifest(
        manifest_path,
        _build_post_tipsy_manifest_payload(
            run_id=effective_run_id,
            run_uuid=run_uuid,
            tsa_list=normalized_tsa_list,
            log_dir=resolved_log_dir,
            status="started",
            started_at=started_at,
            finished_at=None,
            duration_sec=None,
            exit_code=None,
            result=None,
        ),
    )

    monotonic_started = time.monotonic()
    try:
        bundle_result = run_post_tipsy_bundle(
            tsa_list=normalized_tsa_list,
            repo_root=repo_root,
            data_root=data_root,
            model_input_bundle_dir=model_input_bundle_dir,
            run_01b_fn=run_01b_fn,
            canfi_species_fn=canfi_species_fn,
            message_fn=message_fn,
            managed_curve_mode=managed_curve_mode,
            managed_curve_x_scale=managed_curve_x_scale,
            managed_curve_y_scale=managed_curve_y_scale,
            managed_curve_truncate_at_culm=managed_curve_truncate_at_culm,
            managed_curve_max_age=managed_curve_max_age,
            tipsy_output_filename_template=tipsy_output_filename_template,
        )
    except Exception as exc:
        finished_at = datetime.now(timezone.utc)
        duration_sec = round(time.monotonic() - monotonic_started, 3)
        write_manifest(
            manifest_path,
            _build_post_tipsy_manifest_payload(
                run_id=effective_run_id,
                run_uuid=run_uuid,
                tsa_list=normalized_tsa_list,
                log_dir=resolved_log_dir,
                status="failed",
                started_at=started_at,
                finished_at=finished_at,
                duration_sec=duration_sec,
                exit_code=1,
                result=None,
                error_message=str(exc),
            ),
        )
        raise

    finished_at = datetime.now(timezone.utc)
    duration_sec = round(time.monotonic() - monotonic_started, 3)
    write_manifest(
        manifest_path,
        _build_post_tipsy_manifest_payload(
            run_id=effective_run_id,
            run_uuid=run_uuid,
            tsa_list=normalized_tsa_list,
            log_dir=resolved_log_dir,
            status="ok",
            started_at=started_at,
            finished_at=finished_at,
            duration_sec=duration_sec,
            exit_code=0,
            result=bundle_result,
        ),
    )
    return PostTipsyBundleRunResult(manifest_path=manifest_path, result=bundle_result)


def run_btc_and_post_tipsy_bundle_with_manifest(
    *,
    tsa_list: list[str],
    run_id: str | None = None,
    log_dir: Path = Path("vdyp_io/logs"),
    repo_root: Path | None = None,
    data_root: Path = Path("data"),
    model_input_bundle_dir: Path | None = None,
    btc_mode: str = "TSR",
    btc_executable_path: Path | None = None,
    report_preset_name: str | None = "tsr-unattended-default",
    report_template: Path | None = None,
    scratch_root: Path | None = None,
    canfi_species_fn: Callable[[str], int] = _default_canfi_species,
    message_fn: Callable[[str], Any] = print,
    managed_curve_mode: str | None = None,
    managed_curve_x_scale: float | None = None,
    managed_curve_y_scale: float | None = None,
    managed_curve_truncate_at_culm: bool | None = None,
    managed_curve_max_age: int | None = None,
) -> BTCPostTipsyRunResult:
    """Run unattended BTC for selected TSAs, then resume downstream post-TIPSY bundling."""
    normalized_tsa_list = [str(tsa).zfill(2) for tsa in tsa_list]
    effective_run_id = run_id or datetime.now(timezone.utc).strftime(
        "btc_post_tipsy_%Y%m%dT%H%M%SZ"
    )
    resolved_log_dir = Path(log_dir)
    resolved_data_root = Path(data_root)
    btc_results: list[BTCRunResult] = []
    for tsa in normalized_tsa_list:
        input_csv = resolved_data_root / f"03_input-tsa{tsa}.csv"
        if not input_csv.exists():
            raise FileNotFoundError(f"Missing BTC Stage 01a input CSV: {input_csv}")
        output_csv = resolved_data_root / f"04_output-tsa{tsa}.csv"
        error_csv = resolved_data_root / f"04_error-tsa{tsa}.csv"
        tsa_run_id = f"{effective_run_id}_tsa{tsa}"
        result = run_btc_cli(
            input_csv=input_csv,
            mode=btc_mode,
            output_csv=output_csv,
            error_csv=error_csv,
            executable_path=btc_executable_path,
            report_template=report_template,
            report_preset_name=report_preset_name,
            copy_install=True,
            scratch_root=(
                (scratch_root / f"tsa{tsa}") if scratch_root is not None else None
            ),
            log_dir=resolved_log_dir,
            run_id=tsa_run_id,
        )
        btc_results.append(result)
        message_fn(
            "btc completed tsa=%s mode=%s output=%s"
            % (tsa, result.mode, result.output_csv_path)
        )

    post_tipsy_result = run_post_tipsy_bundle_with_manifest(
        tsa_list=normalized_tsa_list,
        run_id=effective_run_id,
        log_dir=resolved_log_dir,
        repo_root=repo_root,
        data_root=resolved_data_root,
        model_input_bundle_dir=model_input_bundle_dir,
        canfi_species_fn=canfi_species_fn,
        message_fn=message_fn,
        managed_curve_mode=managed_curve_mode,
        managed_curve_x_scale=managed_curve_x_scale,
        managed_curve_y_scale=managed_curve_y_scale,
        managed_curve_truncate_at_culm=managed_curve_truncate_at_culm,
        managed_curve_max_age=managed_curve_max_age,
        tipsy_output_filename_template="04_output-tsa{tsa}.csv",
    )
    return BTCPostTipsyRunResult(
        btc_results=btc_results,
        post_tipsy_result=post_tipsy_result,
    )


def run_data_prep(
    run_config: PipelineRunConfig,
) -> Path:
    """Run the legacy 00_data-prep.py workflow with explicit run configuration."""
    explicit_script_root = None
    if run_config.instance_root is not None:
        resolved_instance_root = run_config.instance_root.expanduser().resolve()
        if all(
            (resolved_instance_root / name).is_file()
            for name in LEGACY_SCRIPT_FILENAMES
        ):
            explicit_script_root = resolved_instance_root

    with resolve_legacy_script_bundle(
        explicit_root=explicit_script_root
    ) as script_bundle:
        execution_plan = build_legacy_execution_plan(
            run_config=run_config,
            script_path=script_bundle.stage00_path,
            python_executable=sys.executable,
            base_env=os.environ,
        )

        started_at = datetime.now(timezone.utc)
        monotonic_started = time.monotonic()
        write_manifest(
            execution_plan.manifest_path,
            build_run_manifest_payload(
                execution_plan=execution_plan,
                status="started",
                started_at=started_at,
                finished_at=None,
                duration_sec=None,
                exit_code=None,
            ),
        )

        stage_result = run_legacy_subprocess(
            execution_plan=execution_plan,
            drop_lines=_LEGACY_NOISE_LINES,
        )
        finished_at = datetime.now(timezone.utc)
        duration_sec = round(time.monotonic() - monotonic_started, 3)
        write_manifest(
            execution_plan.manifest_path,
            build_run_manifest_payload(
                execution_plan=execution_plan,
                status="ok" if stage_result.exit_code == 0 else "failed",
                started_at=started_at,
                finished_at=finished_at,
                duration_sec=duration_sec,
                exit_code=stage_result.exit_code,
            ),
        )

        if stage_result.exit_code != 0:
            raise RuntimeError(
                "Legacy workflow failed with exit code "
                f"{stage_result.exit_code}: {' '.join(execution_plan.cmd)}"
            )
        return execution_plan.manifest_path
