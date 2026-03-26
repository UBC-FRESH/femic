"""Bundle-table adapters into shared FMG core objects."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

from .core import (
    AnalysisUnitDefinition,
    BundleModelContext,
    CurveDefinition,
    CurvePoint,
)


def normalize_tsa_code(value: Any) -> str:
    """Normalize TSA code to zero-padded numeric or lowercase text."""
    code = str(value).strip()
    if code.isdigit():
        return code.zfill(2)
    return code.lower()


def _coerce_int(value: Any) -> int:
    if isinstance(value, (int, np.integer)):
        return int(value)
    if isinstance(value, (float, np.floating)):
        return int(value)
    return int(str(value))


def _load_bundle_tables(
    bundle_dir: Path,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    au_table = pd.read_csv(bundle_dir / "au_table.csv")
    curve_table = pd.read_csv(bundle_dir / "curve_table.csv")
    curve_points_table = pd.read_csv(bundle_dir / "curve_points_table.csv")
    return au_table, curve_table, curve_points_table


def _dedupe_au_table(au_table: pd.DataFrame) -> pd.DataFrame:
    if "au_id" not in au_table.columns:
        raise ValueError("au_table.csv missing required column: au_id")
    curve_cols = {
        "managed_curve_id": (
            "managed_curve_id"
            if "managed_curve_id" in au_table.columns
            else "treated_curve_id"
        ),
        "unmanaged_curve_id": (
            "unmanaged_curve_id"
            if "unmanaged_curve_id" in au_table.columns
            else "untreated_curve_id"
        ),
    }
    missing_curve_cols = [
        alias for alias, source in curve_cols.items() if source not in au_table.columns
    ]
    if missing_curve_cols:
        raise ValueError(
            "au_table.csv missing required curve id columns "
            "(need treated/untreated or managed/unmanaged ids)"
        )
    table = au_table.copy()
    table["managed_curve_id"] = table[curve_cols["managed_curve_id"]]
    table["unmanaged_curve_id"] = table[curve_cols["unmanaged_curve_id"]]
    deduped = (
        table.sort_values(["au_id"])
        .groupby("au_id", as_index=False)
        .agg(
            {
                "tsa": "first",
                "stratum_code": "first",
                "si_level": "first",
                "managed_curve_id": "first",
                "unmanaged_curve_id": "first",
            }
        )
    )
    deduped["au_id"] = deduped["au_id"].astype(int)
    deduped["managed_curve_id"] = deduped["managed_curve_id"].astype(int)
    deduped["unmanaged_curve_id"] = deduped["unmanaged_curve_id"].astype(int)
    return deduped


def _curve_points_by_id(
    curve_points_table: pd.DataFrame,
) -> dict[int, list[CurvePoint]]:
    if not {"curve_id", "x", "y"}.issubset(curve_points_table.columns):
        raise ValueError(
            "curve_points_table.csv missing required columns: curve_id,x,y"
        )

    out: dict[int, list[CurvePoint]] = {}
    for curve_id_raw, subdf in curve_points_table.groupby("curve_id"):
        curve_id = _coerce_int(curve_id_raw)
        rows = subdf.sort_values("x")
        out[curve_id] = [
            CurvePoint(x=float(x), y=float(y))
            for x, y in zip(rows["x"].tolist(), rows["y"].tolist())
        ]
    return out


def _thin_curve_points_to_decadal_knots(
    points: tuple[CurvePoint, ...],
) -> tuple[CurvePoint, ...]:
    if len(points) <= 2:
        return points
    thinned: list[CurvePoint] = []
    last_index = len(points) - 1
    for idx, point in enumerate(points):
        x_val = float(point.x)
        rounded_x = int(round(x_val))
        keep = (
            idx == 0
            or idx == last_index
            or (float(rounded_x) == x_val and rounded_x >= 0 and rounded_x % 10 == 0)
        )
        if keep:
            if not thinned or (
                float(thinned[-1].x) != x_val or float(thinned[-1].y) != float(point.y)
            ):
                thinned.append(point)
    return tuple(thinned)


def _species_curve_maps(
    curve_table: pd.DataFrame,
) -> tuple[dict[int, dict[str, int]], dict[int, dict[str, int]]]:
    managed: dict[int, dict[str, int]] = {}
    unmanaged: dict[int, dict[str, int]] = {}
    if not {"curve_id", "curve_type"}.issubset(curve_table.columns):
        return managed, unmanaged

    for _, row in curve_table.iterrows():
        curve_id = _coerce_int(row["curve_id"])
        curve_type = str(row["curve_type"])
        if curve_type.startswith(("managed_species_prop_", "treated_species_prop_")):
            if curve_type.startswith("managed_species_prop_"):
                species = curve_type.removeprefix("managed_species_prop_")
            else:
                species = curve_type.removeprefix("treated_species_prop_")
            base = curve_id // 1000
            managed.setdefault(base, {})[species] = curve_id
        elif curve_type.startswith(
            ("unmanaged_species_prop_", "untreated_species_prop_")
        ):
            if curve_type.startswith("unmanaged_species_prop_"):
                species = curve_type.removeprefix("unmanaged_species_prop_")
            else:
                species = curve_type.removeprefix("untreated_species_prop_")
            base = curve_id // 1000
            unmanaged.setdefault(base, {})[species] = curve_id
    return managed, unmanaged


def build_bundle_model_context_from_tables(
    *,
    au_table: pd.DataFrame,
    curve_table: pd.DataFrame,
    curve_points_table: pd.DataFrame,
    tsa_list: Iterable[str] | None = None,
) -> BundleModelContext:
    """Build shared bundle context from in-memory bundle tables."""
    if tsa_list is None:
        normalized_tsa = sorted(
            {normalize_tsa_code(value) for value in au_table.get("tsa", pd.Series())}
        )
    else:
        normalized_tsa = sorted({normalize_tsa_code(value) for value in tsa_list})
    if not normalized_tsa:
        raise ValueError("provide at least one TSA code for bundle context")

    scoped_au = au_table.copy()
    if "tsa" not in scoped_au.columns:
        raise ValueError("au_table.csv missing required column: tsa")
    scoped_au["tsa"] = scoped_au["tsa"].map(normalize_tsa_code)
    scoped_au = scoped_au[scoped_au["tsa"].isin(normalized_tsa)].copy()
    if scoped_au.empty:
        raise ValueError("no au_table rows matched requested TSA list")

    deduped_au = _dedupe_au_table(scoped_au)
    analysis_units = tuple(
        AnalysisUnitDefinition(
            au_id=_coerce_int(row.au_id),
            tsa=str(row.tsa),
            stratum_code=str(row.stratum_code),
            si_level=str(row.si_level),
            managed_curve_id=_coerce_int(row.managed_curve_id),
            unmanaged_curve_id=_coerce_int(row.unmanaged_curve_id),
        )
        for row in deduped_au.itertuples(index=False)
    )

    points_by_id = _curve_points_by_id(curve_points_table=curve_points_table)
    curve_type_map: dict[int, str] = {}
    if {"curve_id", "curve_type"}.issubset(curve_table.columns):
        for _, row in curve_table.iterrows():
            curve_type_map[_coerce_int(row["curve_id"])] = str(row["curve_type"])
    curves_by_id = {
        curve_id: CurveDefinition(
            curve_id=curve_id,
            curve_type=curve_type_map.get(curve_id, ""),
            points=(
                _thin_curve_points_to_decadal_knots(tuple(points))
                if curve_type_map.get(curve_id, "") in {"unmanaged", "untreated"}
                else tuple(points)
            ),
        )
        for curve_id, points in points_by_id.items()
    }

    managed_species_curve_ids, unmanaged_species_curve_ids = _species_curve_maps(
        curve_table=curve_table
    )
    return BundleModelContext(
        tsa_list=normalized_tsa,
        analysis_units=analysis_units,
        curves_by_id=curves_by_id,
        managed_species_curve_ids=managed_species_curve_ids,
        unmanaged_species_curve_ids=unmanaged_species_curve_ids,
        curve_row_count=int(curve_table.shape[0]),
    )


def build_bundle_model_context(
    *,
    bundle_dir: Path,
    tsa_list: Iterable[str],
) -> BundleModelContext:
    """Build shared bundle context from bundle directory CSV files."""
    au_table, curve_table, curve_points_table = _load_bundle_tables(
        bundle_dir=bundle_dir
    )
    return build_bundle_model_context_from_tables(
        au_table=au_table,
        curve_table=curve_table,
        curve_points_table=curve_points_table,
        tsa_list=tsa_list,
    )
