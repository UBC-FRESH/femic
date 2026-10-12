"""Woodstock compatibility export helpers (CSV package from FEMIC bundle outputs)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

import pandas as pd

from femic.pipeline.tipsy_config import BROADLEAF_SPECIES_CODES

from .adapters import (
    build_bundle_model_context,
    normalize_tsa_code,
)
from .core import BundleModelContext
from .patchworks import (
    DEFAULT_CC_MAX_AGE,
    DEFAULT_CC_MIN_AGE,
    DEFAULT_FRAGMENTS_CRS,
    build_fragments_geodataframe,
)


DEFAULT_WOODSTOCK_OUTPUT_DIR = Path("output/woodstock")
SPECIES_VOLUME_COLUMN_PREFIX = "live_vol_per_ha_125_"
DEFAULT_SPECIES_CHECKPOINT_NAME = "ria_vri_vclr1p_checkpoint4.feather"
DEFAULT_WOODSTOCK_CC_MIN_AGE = DEFAULT_CC_MIN_AGE
DEFAULT_WOODSTOCK_CC_MAX_AGE = DEFAULT_CC_MAX_AGE


@dataclass(frozen=True)
class WoodstockExportResult:
    """Paths and row counts from Woodstock compatibility export."""

    yields_csv_path: Path
    areas_csv_path: Path
    actions_csv_path: Path
    transitions_csv_path: Path
    tsa_list: list[str]
    yield_rows: int
    area_rows: int
    action_rows: int
    transition_rows: int


def _context_to_au_table(context: BundleModelContext) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "au_id": au.au_id,
                "tsa": au.tsa,
                "stratum_code": au.stratum_code,
                "si_level": au.si_level,
                "managed_curve_id": au.managed_curve_id,
                "unmanaged_curve_id": au.unmanaged_curve_id,
            }
            for au in context.analysis_units
        ]
    )


def compute_au_species_shares(
    *,
    species_checkpoint_path: Path,
    au_checkpoint_path: Path,
    hardwood_species: Iterable[str] = BROADLEAF_SPECIES_CODES,
) -> dict[int, dict[str, float]]:
    """Area-weighted softwood/hardwood volume shares per AU.

    Merges the VRI species live-volume columns (stand checkpoint) with the AU
    assignment checkpoint on ``FEATURE_ID`` and aggregates area-weighted
    species volumes per AU.
    """
    species_df = pd.read_feather(species_checkpoint_path)
    species_columns = [
        column
        for column in species_df.columns
        if column.startswith(SPECIES_VOLUME_COLUMN_PREFIX)
    ]
    if not species_columns:
        return {}
    species_df = species_df[["FEATURE_ID", "FEATURE_AREA_SQM", *species_columns]]
    au_df = pd.read_feather(au_checkpoint_path, columns=["FEATURE_ID", "au"])
    merged = species_df.merge(au_df, on="FEATURE_ID", how="inner")
    merged = merged.loc[merged["au"].notna()].copy()
    if merged.empty:
        return {}
    merged["au"] = merged["au"].astype("int64")
    merged["FEATURE_AREA_SQM"] = merged["FEATURE_AREA_SQM"].astype(float)
    hardwood = {str(code).upper() for code in hardwood_species}
    shares: dict[int, dict[str, float]] = {}
    for au_id, block in merged.groupby("au", sort=True):
        area = block["FEATURE_AREA_SQM"]
        softwood_volume = 0.0
        hardwood_volume = 0.0
        for column in species_columns:
            code = column[len(SPECIES_VOLUME_COLUMN_PREFIX) :].upper()
            volume = float((area * block[column].astype(float)).sum())
            if code in hardwood:
                hardwood_volume += volume
            else:
                softwood_volume += volume
        total = softwood_volume + hardwood_volume
        if total <= 0.0:
            continue
        shares[int(au_id)] = {
            "sw": softwood_volume / total,
            "hw": hardwood_volume / total,
        }
    return shares


def build_woodstock_yields_table(
    *,
    context: BundleModelContext,
    species_shares: Mapping[int, Mapping[str, float]] | None = None,
) -> pd.DataFrame:
    """Build long-format Woodstock compatibility yields table.

    Emits one row per (curve, age, product): ``totvol`` always, plus
    ``swdvol``/``hwdvol`` when ``species_shares`` provides softwood/hardwood
    volume shares for the AU (area-weighted VRI species volumes; the treated
    lane reuses the untreated shares until treated species curves land).
    """
    shares = dict(species_shares or {})
    rows: list[dict[str, Any]] = []
    for au in context.analysis_units:
        au_id = au.au_id
        tsa = au.tsa
        stratum_code = au.stratum_code
        si_level = au.si_level
        share = shares.get(au_id)
        for ifm, curve_id in (
            ("unmanaged", au.unmanaged_curve_id),
            ("managed", au.managed_curve_id),
        ):
            curve = context.curves_by_id.get(curve_id)
            if curve is None:
                continue
            for point in curve.points:
                base = {
                    "tsa": tsa,
                    "au_id": au_id,
                    "stratum_code": stratum_code,
                    "si_level": si_level,
                    "ifm": ifm,
                    "curve_id": curve_id,
                    "age": int(point.x),
                }
                rows.append({**base, "product": "totvol", "volume": float(point.y)})
                if share:
                    rows.append(
                        {
                            **base,
                            "product": "swdvol",
                            "volume": float(point.y) * float(share.get("sw", 0.0)),
                        }
                    )
                    rows.append(
                        {
                            **base,
                            "product": "hwdvol",
                            "volume": float(point.y) * float(share.get("hw", 0.0)),
                        }
                    )
    return pd.DataFrame(rows)


def build_woodstock_areas_table(
    *,
    checkpoint_path: Path,
    au_table: pd.DataFrame,
    tsa_list: Iterable[str],
    fragments_crs: str = DEFAULT_FRAGMENTS_CRS,
    initial_age_cap: int | None = None,
    age_class_width: int | None = None,
) -> pd.DataFrame:
    """Build Woodstock compatibility areas table from checkpoint geometries.

    ``initial_age_cap`` clamps initial stand ages; ``age_class_width`` snaps
    ages to class midpoints (e.g. width 10 -> 5, 15, 25, ...). Both shrink the
    ws3 development-type x age root space without materially changing the
    inventory (ages beyond 300 are < 1% of the TSA24 landbase).
    """
    fragments = build_fragments_geodataframe(
        checkpoint_path=checkpoint_path,
        au_table=au_table,
        tsa_list=tsa_list,
        fragments_crs=fragments_crs,
    )
    ages = pd.to_numeric(fragments["F_AGE"], errors="coerce").fillna(0).astype(int)
    if initial_age_cap is not None:
        ages = ages.clip(upper=int(initial_age_cap))
    if age_class_width is not None:
        width = int(age_class_width)
        if width <= 0:
            raise ValueError("age_class_width must be a positive integer")
        ages = (ages // width) * width + width // 2
        if initial_age_cap is not None:
            ages = ages.clip(upper=int(initial_age_cap))
    return pd.DataFrame(
        {
            "stand_id": fragments["BLOCK"].astype(int),
            "tsa": fragments["TSA"].astype(str),
            "au_id": fragments["AU"].astype(int),
            "ifm": fragments["IFM"].astype(str),
            "age": ages,
            "area_ha": pd.to_numeric(fragments["AREA_HA"], errors="coerce").fillna(0.0),
        }
    )


def build_woodstock_actions_table(
    *,
    context: BundleModelContext,
    cc_min_age: int = DEFAULT_WOODSTOCK_CC_MIN_AGE,
    cc_max_age: int = DEFAULT_WOODSTOCK_CC_MAX_AGE,
) -> pd.DataFrame:
    """Build Woodstock action table from managed AU treatment defaults."""
    rows: list[dict[str, Any]] = []
    for au in context.analysis_units:
        rows.append(
            {
                "tsa": au.tsa,
                "au_id": au.au_id,
                "action_id": "CC",
                "from_ifm": "managed",
                "to_ifm": "managed",
                "min_age": int(cc_min_age),
                "max_age": int(cc_max_age),
                "managed_curve_id": au.managed_curve_id,
            }
        )
    return pd.DataFrame(rows)


def build_woodstock_transitions_table(
    *,
    context: BundleModelContext,
) -> pd.DataFrame:
    """Build Woodstock transition table from baseline managed treatment flow."""
    rows: list[dict[str, Any]] = []
    for au in context.analysis_units:
        rows.append(
            {
                "tsa": au.tsa,
                "au_id": au.au_id,
                "action_id": "CC",
                "from_ifm": "managed",
                "to_ifm": "managed",
                "next_au_id": au.au_id,
            }
        )
    return pd.DataFrame(rows)


def export_woodstock_package(
    *,
    bundle_dir: Path,
    checkpoint_path: Path,
    output_dir: Path = DEFAULT_WOODSTOCK_OUTPUT_DIR,
    tsa_list: Iterable[str],
    cc_min_age: int = DEFAULT_WOODSTOCK_CC_MIN_AGE,
    cc_max_age: int = DEFAULT_WOODSTOCK_CC_MAX_AGE,
    fragments_crs: str = DEFAULT_FRAGMENTS_CRS,
    species_checkpoint_path: Path | None = None,
    initial_age_cap: int | None = None,
    age_class_width: int | None = None,
) -> WoodstockExportResult:
    """Export Woodstock compatibility CSV package from FEMIC outputs."""
    normalized_tsa = sorted({normalize_tsa_code(tsa) for tsa in tsa_list})
    if not normalized_tsa:
        raise ValueError("provide at least one TSA code for Woodstock export")

    context = build_bundle_model_context(
        bundle_dir=bundle_dir,
        tsa_list=normalized_tsa,
    )
    au_table = _context_to_au_table(context)

    resolved_species_checkpoint = (
        species_checkpoint_path
        if species_checkpoint_path is not None
        else checkpoint_path.parent / DEFAULT_SPECIES_CHECKPOINT_NAME
    )
    species_shares: dict[int, dict[str, float]] = {}
    if resolved_species_checkpoint.is_file():
        species_shares = compute_au_species_shares(
            species_checkpoint_path=resolved_species_checkpoint,
            au_checkpoint_path=checkpoint_path,
        )
    yields = build_woodstock_yields_table(
        context=context,
        species_shares=species_shares,
    )
    areas = build_woodstock_areas_table(
        checkpoint_path=checkpoint_path,
        au_table=au_table,
        tsa_list=normalized_tsa,
        fragments_crs=fragments_crs,
        initial_age_cap=initial_age_cap,
        age_class_width=age_class_width,
    )
    actions = build_woodstock_actions_table(
        context=context,
        cc_min_age=cc_min_age,
        cc_max_age=cc_max_age,
    )
    transitions = build_woodstock_transitions_table(context=context)

    output_dir.mkdir(parents=True, exist_ok=True)
    yields_path = output_dir / "woodstock_yields.csv"
    areas_path = output_dir / "woodstock_areas.csv"
    actions_path = output_dir / "woodstock_actions.csv"
    transitions_path = output_dir / "woodstock_transitions.csv"
    yields.to_csv(yields_path, index=False)
    areas.to_csv(areas_path, index=False)
    actions.to_csv(actions_path, index=False)
    transitions.to_csv(transitions_path, index=False)

    return WoodstockExportResult(
        yields_csv_path=yields_path,
        areas_csv_path=areas_path,
        actions_csv_path=actions_path,
        transitions_csv_path=transitions_path,
        tsa_list=normalized_tsa,
        yield_rows=int(yields.shape[0]),
        area_rows=int(areas.shape[0]),
        action_rows=int(actions.shape[0]),
        transition_rows=int(transitions.shape[0]),
    )
