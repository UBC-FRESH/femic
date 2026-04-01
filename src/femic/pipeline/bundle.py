"""Helpers for model-input bundle table pathing and I/O."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import math
from pathlib import Path
from typing import Any, Callable


TIPSY_SPECIES_CODE_ALIASES = {
    "FD": "FDC",
}


def _normalize_species_proportion_map(
    proportions: dict[str, float],
) -> dict[str, float]:
    """Return a finite, non-negative species proportion map normalized to 1.0."""
    cleaned: dict[str, float] = {}
    for species_code, raw_value in proportions.items():
        try:
            value = float(raw_value)
        except (TypeError, ValueError):
            continue
        if not math.isfinite(value) or value <= 0.0:
            continue
        cleaned[str(species_code).strip().upper()] = value
    total = sum(cleaned.values())
    if total <= 0.0:
        return {}
    return {
        species_code: float(value) / float(total)
        for species_code, value in cleaned.items()
    }


def _repair_treated_species_proportion_map(
    *,
    treated_proportions: dict[str, float],
    untreated_proportions: dict[str, float],
) -> dict[str, float]:
    """Supplement treated species proportions with missing untreated species.

    Legacy TIPSY species-composition exports can collapse treated states to the
    planted species columns present in the 01b workbook handoff. When the
    untreated VDYP/VRI species map still carries additional companion species,
    preserve the treated mix where it exists, add the missing untreated species,
    and renormalize the combined map to 1.0.
    """
    treated = _normalize_species_proportion_map(treated_proportions)
    untreated = _normalize_species_proportion_map(untreated_proportions)
    if not untreated:
        return treated
    if not treated:
        return dict(untreated)

    merged = dict(treated)
    missing_species = {
        species_code: proportion
        for species_code, proportion in untreated.items()
        if species_code not in merged and proportion > 0.0
    }
    if not missing_species:
        return treated
    merged.update(missing_species)
    return _normalize_species_proportion_map(merged)


@dataclass(frozen=True)
class BundlePaths:
    """Resolved file paths for model input bundle tables."""

    bundle_dir: Path
    au_table: Path
    curve_table: Path
    curve_points_table: Path


@dataclass(frozen=True)
class BundleAssemblyResult:
    """Assembled model-input bundle tables and missing-mapping diagnostics."""

    au_table: Any
    curve_table: Any
    curve_points_table: Any
    missing_au_curve_mappings: Any


def tsa_curve_id_prefix(tsa_code: str) -> int:
    """Return deterministic AU/curve id prefix for numeric and named TSA codes."""
    normalized = str(tsa_code)
    if normalized.isdigit():
        return int(normalized)
    digest = hashlib.sha1(normalized.encode("utf-8")).hexdigest()
    # Keep named-unit prefixes in a dedicated numeric range to avoid collision with
    # canonical 2-digit TSA codes.
    return 900 + (int(digest[:6], 16) % 9000)


def resolve_bundle_paths(
    *,
    base_dir: str | Path = "data/model_input_bundle",
    ensure_dir: bool = True,
) -> BundlePaths:
    """Resolve canonical model-input bundle table paths."""
    bundle_dir = Path(base_dir)
    if ensure_dir:
        bundle_dir.mkdir(parents=True, exist_ok=True)
    return BundlePaths(
        bundle_dir=bundle_dir,
        au_table=bundle_dir / "au_table.csv",
        curve_table=bundle_dir / "curve_table.csv",
        curve_points_table=bundle_dir / "curve_points_table.csv",
    )


def bundle_tables_ready(*, paths: BundlePaths) -> bool:
    """Return True when all required bundle tables exist."""
    return (
        paths.au_table.is_file()
        and paths.curve_table.is_file()
        and paths.curve_points_table.is_file()
    )


def load_bundle_tables(
    *,
    paths: BundlePaths,
    pd_module: Any,
    normalize_tsa_code_fn: Callable[[Any], str] | None = None,
) -> tuple[Any, Any, Any]:
    """Load bundle tables from CSV paths, optionally normalizing TSA codes."""
    au_table = pd_module.read_csv(paths.au_table)
    curve_table = pd_module.read_csv(paths.curve_table)
    curve_points_table = pd_module.read_csv(paths.curve_points_table)
    if normalize_tsa_code_fn is not None and "tsa" in au_table.columns:
        au_table["tsa"] = au_table["tsa"].apply(normalize_tsa_code_fn)
    return au_table, curve_table, curve_points_table


def write_bundle_tables(
    *,
    paths: BundlePaths,
    au_table: Any,
    curve_table: Any,
    curve_points_table: Any,
) -> None:
    """Persist bundle tables to their canonical CSV locations."""
    au_table.to_csv(paths.au_table)
    curve_table.to_csv(paths.curve_table)
    curve_points_table.to_csv(paths.curve_points_table)


def ensure_scsi_au_from_table(
    *,
    au_table: Any,
    scsi_au: dict[str, dict[tuple[str, str], int]],
    normalize_tsa_code_fn: Callable[[Any], str],
) -> None:
    """Backfill `scsi_au` map from persisted AU table entries."""
    for row in au_table.itertuples(index=False):
        tsa_code = normalize_tsa_code_fn(row.tsa)
        tsa_map = scsi_au.setdefault(tsa_code, {})
        scsi_key = (str(row.stratum_code), str(row.si_level))
        if scsi_key in tsa_map:
            continue
        au_base = int(row.au_id) - 100000 * tsa_curve_id_prefix(tsa_code)
        tsa_map[scsi_key] = au_base


def ensure_au_table_index(
    *,
    au_table: Any,
    au_id_col: str = "au_id",
) -> Any:
    """Return AU table indexed by AU id when available."""
    if getattr(au_table.index, "name", None) == au_id_col:
        return au_table
    if au_id_col not in au_table.columns:
        return au_table
    return au_table.set_index(au_id_col)


def build_bundle_tables_from_curves(
    *,
    tsa_list: list[str],
    vdyp_curves_smooth: dict[str, Any],
    tipsy_curves: dict[str, Any],
    scsi_au: dict[str, dict[tuple[str, str], int]],
    canfi_species_fn: Callable[[str], int],
    pd_module: Any,
    species_universe: list[str] | None = None,
    vdyp_species_proportions: dict[str, dict[tuple[str, str], dict[str, float]]]
    | None = None,
    tipsy_species_proportions: dict[str, Any] | None = None,
    message_fn: Callable[[str], Any] = print,
) -> BundleAssemblyResult:
    """Build AU/curve tables from per-TSA VDYP and TIPSY curve outputs."""
    au_table_data: dict[str, list[Any]] = {
        "au_id": [],
        "tsa": [],
        "stratum_code": [],
        "si_level": [],
        "canfi_species": [],
        "source_local_au_id": [],
        "source_managed_local_au_id": [],
        "source_unmanaged_local_au_id": [],
        # Canonical upstream naming.
        "untreated_curve_id": [],
        "treated_curve_id": [],
        # Back-compat aliases used by older checkpoints/exporters.
        "unmanaged_curve_id": [],
        "managed_curve_id": [],
    }
    curve_table_data: dict[str, list[Any]] = {"curve_id": [], "curve_type": []}
    curve_points_table_data: dict[str, list[Any]] = {"curve_id": [], "x": [], "y": []}
    missing_au_curve_mappings: list[dict[str, Any]] = []
    ordered_species = [str(s).upper() for s in (species_universe or [])]

    for tsa in tsa_list:
        message_fn(str(tsa))
        vdyp_curves_tsa = vdyp_curves_smooth[tsa].set_index(
            ["stratum_code", "si_level"]
        )
        tipsy_curves_tsa = tipsy_curves[tsa].reset_index().set_index("AU")
        tipsy_spp_tsa = None
        if tipsy_species_proportions is not None:
            tipsy_spp_tsa = tipsy_species_proportions.get(tsa)
            if tipsy_spp_tsa is not None:
                tipsy_spp_tsa = tipsy_spp_tsa.set_index("AU")
        tipsy_curve_ids = set(tipsy_curves_tsa.index.unique())
        for stratum_code, si_level in list(vdyp_curves_tsa.index.unique()):
            scsi_key = (str(stratum_code), str(si_level))
            au_id_ = scsi_au.get(tsa, {}).get(scsi_key)
            if au_id_ is None:
                missing_au_curve_mappings.append(
                    {"tsa": tsa, "stratum_code": stratum_code, "si_level": si_level}
                )
                continue
            tipsy_curve_id = 20000 + au_id_
            is_managed_au = tipsy_curve_id in tipsy_curve_ids
            au_id = 100000 * tsa_curve_id_prefix(tsa) + au_id_
            unmanaged_curve_id = au_id
            managed_curve_id = au_id + 20000 if is_managed_au else unmanaged_curve_id
            au_table_data["au_id"].append(au_id)
            au_table_data["tsa"].append(tsa)
            au_table_data["stratum_code"].append(stratum_code)
            au_table_data["si_level"].append(si_level)
            au_table_data["canfi_species"].append(canfi_species_fn(stratum_code))
            au_table_data["source_local_au_id"].append(au_id_)
            au_table_data["source_managed_local_au_id"].append(
                tipsy_curve_id if is_managed_au else None
            )
            au_table_data["source_unmanaged_local_au_id"].append(au_id_)
            au_table_data["untreated_curve_id"].append(unmanaged_curve_id)
            au_table_data["treated_curve_id"].append(managed_curve_id)
            au_table_data["unmanaged_curve_id"].append(unmanaged_curve_id)
            curve_table_data["curve_id"].append(unmanaged_curve_id)
            curve_table_data["curve_type"].append("untreated")
            vdyp_curve = vdyp_curves_tsa.loc[(stratum_code, si_level)]
            for x, y in zip(vdyp_curve.age, vdyp_curve.volume):
                curve_points_table_data["curve_id"].append(unmanaged_curve_id)
                curve_points_table_data["x"].append(int(x))
                curve_points_table_data["y"].append(round(y, 2))
            if ordered_species:
                vdyp_prop_map = {}
                if vdyp_species_proportions is not None:
                    vdyp_prop_map = (
                        vdyp_species_proportions.get(tsa, {}).get(scsi_key, {}) or {}
                    )
                for species_idx, species_code in enumerate(ordered_species, start=1):
                    species_curve_id = unmanaged_curve_id * 1000 + species_idx
                    curve_table_data["curve_id"].append(species_curve_id)
                    curve_table_data["curve_type"].append(
                        f"untreated_species_prop_{species_code}"
                    )
                    curve_points_table_data["curve_id"].append(species_curve_id)
                    curve_points_table_data["x"].append(1)
                    curve_points_table_data["y"].append(
                        round(float(vdyp_prop_map.get(species_code, 0.0)), 6)
                    )
            au_table_data["managed_curve_id"].append(managed_curve_id)
            if is_managed_au:
                curve_table_data["curve_id"].append(managed_curve_id)
                curve_table_data["curve_type"].append("treated")
                tipsy_curve = tipsy_curves_tsa.loc[tipsy_curve_id]
                for x, y in zip(tipsy_curve.Age, tipsy_curve.Yield):
                    curve_points_table_data["curve_id"].append(managed_curve_id)
                    curve_points_table_data["x"].append(int(x))
                    curve_points_table_data["y"].append(round(y, 2))
                if ordered_species:
                    tipsy_prop_map: dict[str, float] = {}
                    if (
                        tipsy_spp_tsa is not None
                        and tipsy_curve_id in tipsy_spp_tsa.index
                    ):
                        tipsy_row = tipsy_spp_tsa.loc[tipsy_curve_id]
                        if hasattr(tipsy_row, "ndim") and tipsy_row.ndim > 1:
                            tipsy_row = tipsy_row.iloc[0]
                        tipsy_prop_map_raw: dict[str, float] = {
                            str(col).upper(): float(tipsy_row[col]) * 0.01
                            for col in tipsy_row.index
                            if str(col).upper() != "AU"
                        }
                        tipsy_prop_map = {}
                        for species_code, proportion in tipsy_prop_map_raw.items():
                            canonical = TIPSY_SPECIES_CODE_ALIASES.get(
                                species_code, species_code
                            )
                            tipsy_prop_map[canonical] = float(
                                tipsy_prop_map.get(canonical, 0.0)
                            ) + float(proportion)
                        tipsy_prop_map = _normalize_species_proportion_map(
                            tipsy_prop_map
                        )
                    tipsy_prop_map = _repair_treated_species_proportion_map(
                        treated_proportions=tipsy_prop_map,
                        untreated_proportions=vdyp_prop_map,
                    )
                    for species_idx, species_code in enumerate(
                        ordered_species, start=1
                    ):
                        species_curve_id = managed_curve_id * 1000 + species_idx
                        curve_table_data["curve_id"].append(species_curve_id)
                        curve_table_data["curve_type"].append(
                            f"treated_species_prop_{species_code}"
                        )
                        curve_points_table_data["curve_id"].append(species_curve_id)
                        curve_points_table_data["x"].append(1)
                        curve_points_table_data["y"].append(
                            round(float(tipsy_prop_map.get(species_code, 0.0)), 6)
                        )

    return BundleAssemblyResult(
        au_table=pd_module.DataFrame(au_table_data),
        curve_table=pd_module.DataFrame(curve_table_data),
        curve_points_table=pd_module.DataFrame(curve_points_table_data),
        missing_au_curve_mappings=pd_module.DataFrame(missing_au_curve_mappings),
    )


def emit_missing_au_curve_mapping_warning(
    *,
    missing_df: Any,
    message_fn: Callable[[str], Any] = print,
    top_n: int = 10,
) -> None:
    """Emit legacy warning text for missing AU/curve mapping diagnostics."""
    if missing_df.empty:
        return
    message_fn(
        "Warning: skipped VDYP curve combos without AU mapping "
        f"({len(missing_df)} rows). Top {int(top_n)}:"
    )
    message_fn(
        missing_df.value_counts(["tsa", "stratum_code", "si_level"])
        .head(top_n)
        .to_string()
    )


def assign_curve_ids_from_au_table(
    *,
    f_table: Any,
    au_table: Any,
    pd_module: Any,
    np_module: Any,
    au_col: str = "au",
    proj_age_col: str = "PROJ_AGE_1",
    managed_curve_col: str = "treated_curve_id",
    unmanaged_curve_col: str = "untreated_curve_id",
    curve1_col: str = "curve1",
    curve2_col: str = "curve2",
    managed_age_cutoff: int = 60,
) -> Any:
    """Assign curve ids from AU table for treated/untreated curve slots."""
    table = f_table.copy()
    au_indexed = au_table
    if getattr(au_indexed.index, "name", None) != "au_id":
        au_indexed = au_indexed.set_index("au_id")

    # Backward compatibility for older AU table column naming.
    managed_curve_col_resolved = managed_curve_col
    unmanaged_curve_col_resolved = unmanaged_curve_col
    if (
        managed_curve_col_resolved not in au_indexed.columns
        and "managed_curve_id" in au_indexed.columns
    ):
        managed_curve_col_resolved = "managed_curve_id"
    if (
        unmanaged_curve_col_resolved not in au_indexed.columns
        and "unmanaged_curve_id" in au_indexed.columns
    ):
        unmanaged_curve_col_resolved = "unmanaged_curve_id"

    def _first_scalar(value: Any) -> Any:
        if hasattr(value, "empty") and hasattr(value, "iloc"):
            if value.empty:
                return np_module.nan
            non_na = value.dropna()
            if not non_na.empty:
                return non_na.iloc[0]
            return value.iloc[0]
        return value

    curve1_values: list[int | None] = []
    curve2_values: list[int | None] = []
    for au_value, proj_age in zip(table[au_col].values, table[proj_age_col].values):
        if pd_module.isna(au_value):
            curve1_values.append(None)
            curve2_values.append(None)
            continue
        au_id = int(au_value)
        if au_id not in au_indexed.index:
            curve1_values.append(None)
            curve2_values.append(None)
            continue
        au_row = au_indexed.loc[au_id]
        if hasattr(au_row, "ndim") and au_row.ndim > 1:
            unmanaged_curve_id = _first_scalar(au_row[unmanaged_curve_col_resolved])
            managed_curve_id = _first_scalar(au_row[managed_curve_col_resolved])
        else:
            unmanaged_curve_id = au_row[unmanaged_curve_col_resolved]
            managed_curve_id = au_row[managed_curve_col_resolved]
        if proj_age <= managed_age_cutoff and pd_module.notna(managed_curve_id):
            curve1_id = managed_curve_id
        else:
            curve1_id = unmanaged_curve_id
        curve1_values.append(None if pd_module.isna(curve1_id) else int(curve1_id))
        curve2_values.append(
            None if pd_module.isna(unmanaged_curve_id) else int(unmanaged_curve_id)
        )

    table[curve1_col] = curve1_values
    table[curve2_col] = curve2_values
    return table
