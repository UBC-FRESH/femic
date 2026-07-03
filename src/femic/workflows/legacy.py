"""Legacy workflow wrappers for FEMIC."""

from __future__ import annotations

from contextlib import contextmanager
import os
import sys
import time
from datetime import datetime, timezone
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence, cast
import uuid

import pandas as pd
import yaml

from femic.pipeline.bundle import (
    BundleAssemblyResult,
    build_bundle_tables_from_curves,
    resolve_bundle_paths,
    validate_complete_au_curve_mappings,
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
from femic.pipeline.vri import is_conifer_species_code, is_deciduous_species_code
from femic.pipeline.tipsy import (
    BTCRunResult,
    run_btc_cli,
    write_tipsy_output_input_fingerprint,
)
from femic.pipeline.stages import load_legacy_module, run_legacy_subprocess
from femic.workflows.legacy_resources import (
    LEGACY_SCRIPT_FILENAMES,
    resolve_legacy_script_bundle,
)


_LEGACY_NOISE_LINES = {"Error in sys.excepthook:", "Original exception was:"}
_DEFAULT_SI_LEVELS = ("L", "M", "H")
_DEFAULT_YIELD_ASSUMPTIONS_RELATIVE_PATH = Path("config/tsr/yield_assumptions.yaml")
_BROADLEAF_VOLUME_EXCLUSION_RULE_TYPE = "broadleaf_volume_exclusion"
_BROADLEAF_VOLUME_EXCLUSION_SCOPE = "untreated_only"
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
    yield_assumptions_summary: dict[str, Any] | None = None


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
    """Load unique top-6 VRI species codes for selected TSAs from best checkpoint."""
    required_columns = (
        {"tsa_code"}
        | {f"SPECIES_CD_{idx}" for idx in range(1, 7)}
        | {f"SPECIES_PCT_{idx}" for idx in range(1, 7)}
    )
    normalized = {str(tsa).zfill(2).lower() for tsa in tsa_list}
    candidate_paths: list[Path] = [data_root / "ria_vri_vclr1p_checkpoint8.feather"]
    candidate_paths.extend(
        data_root / f"ria_vri_vclr1p_checkpoint1-tsa{tsa}.feather"
        for tsa in sorted(normalized)
    )
    candidate_paths.append(data_root / "ria_vri_vclr1p_checkpoint1.feather")
    candidate_paths.extend(
        sorted(data_root.glob("ria_vri_vclr1p_checkpoint1-tsa*.feather"))
    )
    seen_candidates: set[Path] = set()
    checkpoint_path: Path | None = None
    table: pd.DataFrame | None = None
    for candidate in candidate_paths:
        if candidate in seen_candidates or not candidate.exists():
            continue
        seen_candidates.add(candidate)
        candidate_table = pd.read_feather(candidate)
        if not required_columns.issubset(candidate_table.columns):
            continue
        candidate_mask = (
            candidate_table["tsa_code"].astype(str).str.lower().isin(normalized)
        )
        if not candidate_mask.any():
            continue
        checkpoint_path = candidate
        table = candidate_table
        break
    if checkpoint_path is None or table is None:
        message_fn(
            "warning: species-universe scan skipped; no usable checkpoint artifact "
            f"found under {data_root}"
        )
        return []
    message_fn(f"species-universe scan using {checkpoint_path.name}")
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


def _resolve_yield_assumptions_path(
    *,
    explicit_path: Path | None,
    repo_root: Path,
) -> Path | None:
    if explicit_path is not None:
        return Path(explicit_path)
    default_path = repo_root / _DEFAULT_YIELD_ASSUMPTIONS_RELATIVE_PATH
    if default_path.exists():
        return default_path
    return None


def _load_yield_assumptions_rules(path: Path) -> list[dict[str, object]]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if raw is None:
        return []
    if not isinstance(raw, dict):
        raise ValueError(f"Yield assumptions config must be a mapping: {path}")
    rules = raw.get("rules", [])
    if rules is None:
        return []
    if not isinstance(rules, list):
        raise ValueError(f"`rules` must be a list in yield assumptions config: {path}")
    normalized: list[dict[str, object]] = []
    for idx, raw_rule in enumerate(rules, start=1):
        if not isinstance(raw_rule, dict):
            raise ValueError(f"Rule {idx} must be a mapping in {path}")
        rule_type = str(raw_rule.get("rule_type", "")).strip().lower()
        if rule_type != _BROADLEAF_VOLUME_EXCLUSION_RULE_TYPE:
            raise ValueError(
                f"Unsupported yield assumption rule_type {rule_type!r} in {path}"
            )
        scope = str(raw_rule.get("scope", "")).strip().lower()
        if scope != _BROADLEAF_VOLUME_EXCLUSION_SCOPE:
            raise ValueError(
                f"Rule {idx} scope must be {_BROADLEAF_VOLUME_EXCLUSION_SCOPE!r} in {path}"
            )
        tsa_list_raw = raw_rule.get("tsa_list")
        if not isinstance(tsa_list_raw, list) or not tsa_list_raw:
            raise ValueError(f"Rule {idx} must declare non-empty tsa_list in {path}")
        normalized.append(
            {
                "rule_type": rule_type,
                "scope": scope,
                "tsa_list": [str(tsa).zfill(2) for tsa in tsa_list_raw],
            }
        )
    return normalized


def _normalized_species_map_for_curve(
    *,
    base_curve_id: int,
    curve_table: pd.DataFrame,
    curve_points_table: pd.DataFrame,
    curve_type_prefix: str,
) -> dict[str, float]:
    species_rows = curve_table.loc[
        curve_table["curve_type"].astype(str).str.startswith(curve_type_prefix)
    ].copy()
    if species_rows.empty:
        return {}
    species_rows["base_curve_id"] = (
        pd.to_numeric(species_rows["curve_id"], errors="coerce").fillna(0).astype(int)
        // 1000
    )
    species_rows = species_rows.loc[species_rows["base_curve_id"] == int(base_curve_id)]
    if species_rows.empty:
        return {}
    point_values = (
        curve_points_table.loc[
            curve_points_table["curve_id"].isin(species_rows["curve_id"]),
            ["curve_id", "y"],
        ]
        .drop_duplicates(subset=["curve_id"])
        .set_index("curve_id")["y"]
        .to_dict()
    )
    species_map: dict[str, float] = {}
    for row in species_rows.itertuples(index=False):
        curve_type = str(getattr(row, "curve_type"))
        species_code = curve_type.removeprefix(curve_type_prefix).strip().upper()
        if not species_code:
            continue
        raw_value = point_values.get(getattr(row, "curve_id"))
        if raw_value is None:
            continue
        try:
            value = float(raw_value)
        except (TypeError, ValueError):
            continue
        if value <= 0.0:
            continue
        species_map[species_code] = value
    total = sum(species_map.values())
    if total <= 0.0:
        return {}
    return {
        species_code: float(value) / float(total)
        for species_code, value in species_map.items()
    }


def _rounded_species_share_map(shares: dict[str, float]) -> dict[str, float]:
    if not shares:
        return {}
    ordered_items = sorted(shares.items())
    rounded: dict[str, float] = {}
    running = 0.0
    for idx, (species_code, value) in enumerate(ordered_items, start=1):
        if idx == len(ordered_items):
            rounded_value = round(max(0.0, 1.0 - running), 6)
        else:
            rounded_value = round(float(value), 6)
            running += rounded_value
        rounded[species_code] = rounded_value
    return rounded


def _apply_broadleaf_volume_exclusion_to_bundle(
    *,
    bundle: BundleAssemblyResult,
    tsa_list: list[str],
    assumptions_path: Path,
    message_fn: Callable[[str], Any],
) -> tuple[BundleAssemblyResult, dict[str, Any]]:
    rules = _load_yield_assumptions_rules(assumptions_path)
    matching_rules = [
        rule
        for rule in rules
        if set(cast(list[str], rule["tsa_list"])).intersection(set(tsa_list))
    ]
    summary: dict[str, Any] = {
        "assumptions_path": str(assumptions_path),
        "rule_type": _BROADLEAF_VOLUME_EXCLUSION_RULE_TYPE,
        "scope": _BROADLEAF_VOLUME_EXCLUSION_SCOPE,
        "matched_tsa_list": sorted(
            {
                tsa
                for rule in matching_rules
                for tsa in cast(list[str], rule["tsa_list"])
                if tsa in tsa_list
            }
        ),
        "adjusted_au_count": 0,
        "adjusted_au_ids": [],
        "adjusted_aus": [],
        "skipped_aus": [],
        "total_untreated_volume_removed": 0.0,
    }
    if not matching_rules:
        summary["status"] = "no_matching_rules"
        return bundle, summary

    au_table = bundle.au_table.copy()
    curve_table = bundle.curve_table.copy()
    curve_points_table = bundle.curve_points_table.copy()

    for row in au_table.itertuples(index=False):
        if str(getattr(row, "tsa")).zfill(2) not in summary["matched_tsa_list"]:
            continue
        untreated_curve_id = int(getattr(row, "untreated_curve_id"))
        species_map = _normalized_species_map_for_curve(
            base_curve_id=untreated_curve_id,
            curve_table=curve_table,
            curve_points_table=curve_points_table,
            curve_type_prefix="untreated_species_prop_",
        )
        if not species_map:
            summary["skipped_aus"].append(
                {
                    "tsa": str(getattr(row, "tsa")).zfill(2),
                    "au_id": int(getattr(row, "au_id")),
                    "reason": "missing_untreated_species_proportions",
                }
            )
            continue
        broadleaf_share = sum(
            value
            for species_code, value in species_map.items()
            if is_deciduous_species_code(species_code)
        )
        if broadleaf_share <= 0.0:
            continue
        max_share = max(species_map.values())
        leaders = [
            species_code
            for species_code, value in species_map.items()
            if abs(float(value) - float(max_share)) <= 1e-9
        ]
        if any(is_deciduous_species_code(species_code) for species_code in leaders):
            continue
        if not all(is_conifer_species_code(species_code) for species_code in leaders):
            continue
        conifer_shares = {
            species_code: value
            for species_code, value in species_map.items()
            if is_conifer_species_code(species_code)
        }
        conifer_share = sum(conifer_shares.values())
        if conifer_share <= 0.0:
            continue

        total_mask = curve_points_table["curve_id"] == untreated_curve_id
        total_before = pd.to_numeric(
            curve_points_table.loc[total_mask, "y"], errors="coerce"
        ).fillna(0.0)
        total_after = (total_before * float(conifer_share)).round(2)
        removed_volume = round(float((total_before - total_after).sum()), 6)
        curve_points_table.loc[total_mask, "y"] = total_after

        normalized_conifer = _rounded_species_share_map(
            {
                species_code: float(value) / float(conifer_share)
                for species_code, value in conifer_shares.items()
            }
        )
        species_rows = curve_table.loc[
            curve_table["curve_type"]
            .astype(str)
            .str.startswith("untreated_species_prop_")
        ].copy()
        species_rows["base_curve_id"] = (
            pd.to_numeric(species_rows["curve_id"], errors="coerce")
            .fillna(0)
            .astype(int)
            // 1000
        )
        species_rows = species_rows.loc[
            species_rows["base_curve_id"] == untreated_curve_id
        ]
        for species_row in species_rows.itertuples(index=False):
            species_code = (
                str(getattr(species_row, "curve_type"))
                .removeprefix("untreated_species_prop_")
                .strip()
                .upper()
            )
            if is_deciduous_species_code(species_code):
                new_value = 0.0
            else:
                new_value = normalized_conifer.get(species_code, 0.0)
            curve_points_table.loc[
                curve_points_table["curve_id"] == int(getattr(species_row, "curve_id")),
                "y",
            ] = round(float(new_value), 6)

        summary["adjusted_au_ids"].append(int(getattr(row, "au_id")))
        summary["adjusted_aus"].append(
            {
                "tsa": str(getattr(row, "tsa")).zfill(2),
                "au_id": int(getattr(row, "au_id")),
                "stratum_code": str(getattr(row, "stratum_code")),
                "si_level": str(getattr(row, "si_level")),
                "untreated_curve_id": untreated_curve_id,
                "leading_species_code": sorted(leaders)[0],
                "broadleaf_share": round(float(broadleaf_share), 6),
                "conifer_share": round(float(conifer_share), 6),
                "untreated_volume_removed": removed_volume,
            }
        )
        summary["total_untreated_volume_removed"] = round(
            float(summary["total_untreated_volume_removed"]) + removed_volume,
            6,
        )
        message_fn(
            "yield assumption broadleaf_volume_exclusion adjusted "
            f"tsa={str(getattr(row, 'tsa')).zfill(2)} au_id={int(getattr(row, 'au_id'))} "
            f"broadleaf_share={round(float(broadleaf_share), 6)}"
        )

    summary["adjusted_au_count"] = len(summary["adjusted_au_ids"])
    summary["status"] = "applied" if summary["adjusted_au_count"] > 0 else "no_changes"
    adjusted_bundle = BundleAssemblyResult(
        au_table=au_table,
        curve_table=curve_table,
        curve_points_table=curve_points_table,
        missing_au_curve_mappings=bundle.missing_au_curve_mappings,
    )
    return adjusted_bundle, summary


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


def _species_mix_from_layer_row(row: Any) -> dict[str, float]:
    normalized: dict[str, float] = {}
    total = 0.0
    for idx in range(1, 7):
        species_code = _normalize_species_code(row.get(f"SPECIES_CD_{idx}", ""))
        if not species_code:
            continue
        pct_raw = row.get(f"SPECIES_PCT_{idx}", 0.0)
        if pd.isna(pct_raw):
            continue
        pct = float(pct_raw)
        if pct <= 0:
            continue
        prop = pct * 0.01
        normalized[species_code] = normalized.get(species_code, 0.0) + prop
        total += prop
    if total > 0:
        for code in list(normalized.keys()):
            normalized[code] = normalized[code] / total
    return normalized


def _parse_stratum_species_tokens(stratum_code: str) -> list[str]:
    suffix = str(stratum_code).split("_")[-1]
    out: list[str] = []
    for token in suffix.split("+"):
        code = _normalize_species_code(token)
        if not code:
            continue
        if code not in out:
            out.append(code)
    return out


def _vdyp_species_proportions_from_vdyp_layer_fallback(
    *,
    data_root: Path,
    tsa: str,
    bundle_au_table: pd.DataFrame,
) -> dict[tuple[str, str], dict[str, float]]:
    artifact_code = _legacy_case_artifact_code(tsa)
    layer_path = data_root / f"vdyp_lyr-{artifact_code}.feather"
    if not layer_path.exists():
        return {}

    vdyp_lyr = pd.read_feather(layer_path)
    row_pairs: list[tuple[frozenset[str], dict[str, float]]] = []
    for _, row in vdyp_lyr.iterrows():
        species_mix = _species_mix_from_layer_row(row)
        if not species_mix:
            continue
        dominant_pair = frozenset(list(species_mix.keys())[:2])
        if len(dominant_pair) < 2:
            continue
        row_pairs.append((dominant_pair, species_mix))

    out: dict[tuple[str, str], dict[str, float]] = {}
    unique_pairs = (
        bundle_au_table[["stratum_code", "si_level"]]
        .drop_duplicates()
        .itertuples(index=False)
    )
    for stratum_code, si_level in unique_pairs:
        target_pair = frozenset(_parse_stratum_species_tokens(stratum_code)[:2])
        matched = [
            species_mix for pair, species_mix in row_pairs if pair == target_pair
        ]
        aggregate: dict[str, float] = {}
        if matched:
            for species_mix in matched:
                for code, prop in species_mix.items():
                    aggregate[code] = aggregate.get(code, 0.0) + float(prop)
            total = sum(aggregate.values())
            if total > 0:
                for code in list(aggregate.keys()):
                    aggregate[code] = aggregate[code] / total
        elif target_pair:
            equal = 1.0 / len(target_pair)
            aggregate = {code: equal for code in target_pair}
        out[(str(stratum_code), str(si_level))] = aggregate
    return out


def _legacy_case_artifact_code(value: str) -> str:
    raw = str(value).strip().lower()
    if raw.isdigit():
        return f"tsa{raw.zfill(2)}"
    return raw


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
    yield_assumptions_path: Path | None = None,
    tipsy_input_filename_template: str = "03_input-{artifact_code}.csv",
    tipsy_output_filename_template: str = "04_output-tsa{tsa}.csv",
) -> PostTipsyBundleResult:
    """Run downstream 01b + bundle assembly from cached TSA artifacts only."""
    normalized_tsa_list = [str(tsa).zfill(2) for tsa in tsa_list]
    resolved_repo_root = repo_root if repo_root is not None else Path.cwd()
    resolved_yield_assumptions_path = _resolve_yield_assumptions_path(
        explicit_path=yield_assumptions_path,
        repo_root=resolved_repo_root,
    )

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
            artifact_code = _legacy_case_artifact_code(tsa)
            prep_path = data_root / f"vdyp_prep-{artifact_code}.pkl"
            smooth_path = data_root / f"vdyp_curves_smooth-{artifact_code}.feather"
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
                vdyp_species_proportions[tsa] = (
                    _vdyp_species_proportions_from_vdyp_layer_fallback(
                        data_root=data_root,
                        tsa=tsa,
                        bundle_au_table=bundle_tsa,
                    )
                )
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
                tipsy_input_filename_template=tipsy_input_filename_template,
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
            tipsy_curves_paths.append(data_root / f"tipsy_curves_{artifact_code}.csv")
            tipsy_sppcomp_paths.append(data_root / f"tipsy_sppcomp_{artifact_code}.csv")
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
    validate_complete_au_curve_mappings(
        missing_df=bundle.missing_au_curve_mappings,
        top_n=10,
    )
    yield_assumptions_summary: dict[str, Any] | None = None
    if resolved_yield_assumptions_path is not None:
        bundle, yield_assumptions_summary = _apply_broadleaf_volume_exclusion_to_bundle(
            bundle=bundle,
            tsa_list=normalized_tsa_list,
            assumptions_path=resolved_yield_assumptions_path,
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
        yield_assumptions_summary=yield_assumptions_summary,
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
        if result.yield_assumptions_summary is not None:
            outputs["yield_assumptions"] = result.yield_assumptions_summary
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
    log_dir: Path = Path("runtime/logs"),
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
    yield_assumptions_path: Path | None = None,
    tipsy_input_filename_template: str = "03_input-{artifact_code}.csv",
    tipsy_output_filename_template: str = "04_output-tsa{tsa}.csv",
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
            yield_assumptions_path=yield_assumptions_path,
            tipsy_input_filename_template=tipsy_input_filename_template,
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


def _resolve_btc_handoff_paths(
    *,
    data_root: Path,
    tsa: str,
) -> tuple[Path, Path, Path, str, str]:
    artifact_code = _legacy_case_artifact_code(tsa)
    legacy_input = data_root / f"03_input-{artifact_code}.csv"
    if legacy_input.exists():
        return (
            legacy_input,
            data_root / f"04_output-{artifact_code}.csv",
            data_root / f"04_error-{artifact_code}.csv",
            "03_input-{artifact_code}.csv",
            "04_output-{artifact_code}.csv",
        )

    case_input = data_root / f"03_input-{tsa}.csv"
    if case_input.exists():
        return (
            case_input,
            data_root / f"04_output-{tsa}.csv",
            data_root / f"04_error-{tsa}.csv",
            "03_input-{tsa}.csv",
            "04_output-{tsa}.csv",
        )

    raise FileNotFoundError(
        f"Missing BTC Stage 01a input CSV: {legacy_input} or {case_input}"
    )


def run_btc_and_post_tipsy_bundle_with_manifest(
    *,
    tsa_list: list[str],
    run_id: str | None = None,
    log_dir: Path = Path("runtime/logs"),
    repo_root: Path | None = None,
    data_root: Path = Path("data"),
    model_input_bundle_dir: Path | None = None,
    btc_mode: str = "TSR",
    btc_executable_path: Path | None = None,
    report_preset_name: str | None = "tsr-unattended-default",
    report_template: Path | None = None,
    indicator_bank_names: Sequence[str] = (),
    scratch_root: Path | None = None,
    canfi_species_fn: Callable[[str], int] = _default_canfi_species,
    message_fn: Callable[[str], Any] = print,
    managed_curve_mode: str | None = None,
    managed_curve_x_scale: float | None = None,
    managed_curve_y_scale: float | None = None,
    managed_curve_truncate_at_culm: bool | None = None,
    managed_curve_max_age: int | None = None,
    yield_assumptions_path: Path | None = None,
) -> BTCPostTipsyRunResult:
    """Run unattended BTC for selected TSAs, then resume downstream post-TIPSY bundling."""
    normalized_tsa_list = [str(tsa).zfill(2) for tsa in tsa_list]
    effective_run_id = run_id or datetime.now(timezone.utc).strftime(
        "btc_post_tipsy_%Y%m%dT%H%M%SZ"
    )
    resolved_log_dir = Path(log_dir)
    resolved_data_root = Path(data_root)
    btc_results: list[BTCRunResult] = []
    tipsy_input_template = "03_input-{artifact_code}.csv"
    tipsy_output_template = "04_output-{artifact_code}.csv"
    for tsa in normalized_tsa_list:
        artifact_code = _legacy_case_artifact_code(tsa)
        (
            input_csv,
            output_csv,
            error_csv,
            input_template,
            output_template,
        ) = _resolve_btc_handoff_paths(
            data_root=resolved_data_root,
            tsa=tsa,
        )
        tipsy_input_template = input_template
        tipsy_output_template = output_template
        tsa_run_id = f"{effective_run_id}_{artifact_code}"
        result = run_btc_cli(
            input_csv=input_csv,
            mode=btc_mode,
            output_csv=output_csv,
            error_csv=error_csv,
            executable_path=btc_executable_path,
            report_template=report_template,
            report_preset_name=report_preset_name,
            indicator_bank_names=indicator_bank_names,
            copy_install=True,
            scratch_root=(
                (scratch_root / artifact_code) if scratch_root is not None else None
            ),
            log_dir=resolved_log_dir,
            run_id=tsa_run_id,
        )
        btc_results.append(result)
        write_tipsy_output_input_fingerprint(
            btc_input_csv_path=input_csv,
            tipsy_output_path=output_csv,
        )
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
        yield_assumptions_path=yield_assumptions_path,
        tipsy_input_filename_template=tipsy_input_template,
        tipsy_output_filename_template=tipsy_output_template,
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
