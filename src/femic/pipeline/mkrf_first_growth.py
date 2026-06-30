"""MKRF AU-wise first-growth curve synthesis from stand-level VDYP evidence."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import math
from typing import Any

import numpy as np
import pandas as pd

from femic.pipeline.au_first_growth import select_au_first_growth_curve
from femic.pipeline.mkrf_au import build_mkrf_assignment_rows
from femic.pipeline.tsa import build_stratum_lexmatch_alias_map
from femic.pipeline.vdyp_curves import process_vdyp_out


_MIN_FIRST_GROWTH_AGE = 80.0
_MIN_FIRST_GROWTH_SOURCE_STANDS = 2


@dataclass(frozen=True)
class StandAssignmentCollapse:
    """Deterministic stand-level AU assignment with ambiguity diagnostics."""

    forest_cover_id: int
    au_id: str
    assignment_weight_basis: str
    fragment_record_count: int
    candidate_au_count: int
    dominant_weight: float
    total_weight: float
    weight_share: float
    tie_break_used: bool


def collapse_stand_assignments(assignment: pd.DataFrame) -> pd.DataFrame:
    """Collapse fragment-level assignment rows to one deterministic AU per stand."""
    table = assignment.copy()
    weight_col = "shape_area_ha" if "shape_area_ha" in table.columns else None
    weight_basis = (
        "shape_area_ha" if weight_col is not None else "fragment_record_count"
    )
    if weight_col is None:
        table["_weight"] = 1.0
    else:
        numeric = pd.to_numeric(table[weight_col], errors="coerce").fillna(0.0)
        table["_weight"] = numeric.astype(float)

    grouped = (
        table.groupby(["forest_cover_id", "au_id"], as_index=False, sort=True)
        .agg(
            fragment_record_count=("res_key", "count"),
            total_weight=("_weight", "sum"),
        )
        .sort_values(
            ["forest_cover_id", "total_weight", "fragment_record_count", "au_id"],
            ascending=[True, False, False, True],
            kind="stable",
        )
    )

    rows: list[StandAssignmentCollapse] = []
    for forest_cover_id, stand_rows in grouped.groupby("forest_cover_id", sort=True):
        ordered = stand_rows.reset_index(drop=True)
        dominant = ordered.iloc[0]
        total_weight = float(ordered["total_weight"].sum())
        top_weight = float(dominant["total_weight"])
        top_count = int(dominant["fragment_record_count"])
        candidate_count = int(len(ordered))
        tie_break_used = False
        if candidate_count > 1:
            same_weight = ordered["total_weight"] == top_weight
            same_count = ordered["fragment_record_count"] == top_count
            tie_break_used = int((same_weight & same_count).sum()) > 1
        rows.append(
            StandAssignmentCollapse(
                forest_cover_id=int(forest_cover_id),
                au_id=str(dominant["au_id"]),
                assignment_weight_basis=weight_basis,
                fragment_record_count=top_count,
                candidate_au_count=candidate_count,
                dominant_weight=top_weight,
                total_weight=total_weight,
                weight_share=(top_weight / total_weight) if total_weight > 0.0 else 0.0,
                tie_break_used=tie_break_used,
            )
        )

    return pd.DataFrame(
        [
            {
                "forest_cover_id": row.forest_cover_id,
                "au_id": row.au_id,
                "assignment_weight_basis": row.assignment_weight_basis,
                "fragment_record_count": row.fragment_record_count,
                "candidate_au_count": row.candidate_au_count,
                "dominant_weight": row.dominant_weight,
                "total_weight": row.total_weight,
                "weight_share": row.weight_share,
                "tie_break_used": row.tie_break_used,
            }
            for row in rows
        ]
    ).sort_values(["au_id", "forest_cover_id"], kind="stable")


def _build_feature_tables(vdyp_yields: pd.DataFrame) -> dict[int, pd.DataFrame]:
    feature_tables: dict[int, pd.DataFrame] = {}
    for feature_id, feature_rows in vdyp_yields.groupby("FEATURE_ID", sort=True):
        ordered = feature_rows.sort_values("PRJ_TOTAL_AGE", kind="stable")
        feature_tables[int(feature_id)] = (
            ordered.rename(
                columns={
                    "PRJ_TOTAL_AGE": "Age",
                    "PRJ_VOL_DWB": "Vdwb",
                }
            )[["Age", "Vdwb"]]
            .set_index("Age")
            .copy()
        )
    return feature_tables


def _build_au_lexmatch_alias_map(
    *,
    selected_assignment: pd.DataFrame,
    candidate_assignment: pd.DataFrame,
    levenshtein_fn: Callable[[str, str], int],
) -> dict[str, str]:
    selected_area_col = (
        "dominant_weight"
        if "dominant_weight" in selected_assignment.columns
        else "shape_area_ha"
    )
    selected_area = (
        selected_assignment.groupby("au_id", as_index=True)[selected_area_col]
        .sum()
        .sort_index()
    )
    candidate_area = (
        candidate_assignment.groupby("au_id", as_index=True)["shape_area_ha"]
        .sum()
        .sort_index()
    )
    f_table = pd.concat(
        [
            pd.DataFrame(
                {
                    "stratum": selected_area.index,
                    "stratum_lexmatch": selected_area.index,
                    "totalarea_p": selected_area.astype(float),
                }
            ).set_index("stratum"),
            pd.DataFrame(
                {
                    "stratum": candidate_area.index,
                    "stratum_lexmatch": candidate_area.index,
                    "totalarea_p": candidate_area.astype(float),
                }
            ).set_index("stratum"),
        ],
        axis=0,
    )
    return build_stratum_lexmatch_alias_map(
        f_table=f_table,
        stratum_col="stratum",
        selected_strata_codes=list(selected_area.index),
        levenshtein_fn=levenshtein_fn,
    )


def _expand_stand_assignment_with_lexmatch(
    *,
    stand_assignment: pd.DataFrame,
    source_table: pd.DataFrame,
    unmatched_feature_ids: set[int],
    levenshtein_fn: Callable[[str, str], int],
) -> pd.DataFrame:
    candidate_rows = source_table.loc[
        source_table["FOREST_COVER_ID"].isin(sorted(unmatched_feature_ids))
    ].copy()
    if candidate_rows.empty:
        return stand_assignment

    candidate_assignment = build_mkrf_assignment_rows(candidate_rows)
    if candidate_assignment.empty:
        return stand_assignment

    candidate_assignment["assignment_status"] = "lexmatch_candidate"
    collapsed_candidates = collapse_stand_assignments(candidate_assignment)
    collapsed_candidates["source_au_id"] = collapsed_candidates["au_id"]
    alias_map = _build_au_lexmatch_alias_map(
        selected_assignment=stand_assignment,
        candidate_assignment=candidate_assignment,
        levenshtein_fn=levenshtein_fn,
    )
    collapsed_candidates["au_id"] = [
        alias_map.get(source_au_id, source_au_id)
        for source_au_id in collapsed_candidates["source_au_id"]
    ]
    collapsed_candidates["assignment_status"] = "lexmatch_assigned"
    collapsed_candidates["lexmatch_alias_used"] = [
        alias_map.get(source_au_id, source_au_id) != source_au_id
        for source_au_id in collapsed_candidates["source_au_id"]
    ]
    combined = pd.concat(
        [
            stand_assignment.assign(
                assignment_status="assigned",
                lexmatch_alias_used=False,
            ),
            collapsed_candidates,
        ],
        ignore_index=True,
        sort=False,
    )
    return combined.sort_values(
        ["au_id", "forest_cover_id"], kind="stable"
    ).reset_index(drop=True)


def _resolve_eligible_first_growth_feature_ids(
    *,
    vdyp_yields: pd.DataFrame,
    source_table: pd.DataFrame | None,
    min_first_growth_age: float,
) -> set[int]:
    vdyp_feature_ids = set(
        pd.to_numeric(vdyp_yields["FEATURE_ID"], errors="coerce").dropna().astype(int)
    )
    if source_table is None or "AGE_2020" not in source_table.columns:
        return vdyp_feature_ids
    source_age = source_table.copy()
    source_age["forest_cover_id"] = pd.to_numeric(
        source_age["FOREST_COVER_ID"], errors="coerce"
    )
    source_age["age_2020"] = pd.to_numeric(source_age["AGE_2020"], errors="coerce")
    eligible = source_age.loc[
        source_age["forest_cover_id"].notna()
        & source_age["age_2020"].ge(float(min_first_growth_age)),
        "forest_cover_id",
    ]
    return vdyp_feature_ids & set(eligible.astype(int))


def build_mkrf_first_growth_curves(
    *,
    vdyp_yields: pd.DataFrame,
    assignment: pd.DataFrame,
    source_table: pd.DataFrame | None = None,
    levenshtein_fn: Callable[[str, str], int] | None = None,
    process_vdyp_out_fn: Callable[
        ..., tuple[np.ndarray, np.ndarray]
    ] = process_vdyp_out,
    min_first_growth_age: float = _MIN_FIRST_GROWTH_AGE,
    min_source_stands: int = _MIN_FIRST_GROWTH_SOURCE_STANDS,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build AU-wise first-growth curves and fit diagnostics from VDYP stand evidence."""
    stand_assignment = collapse_stand_assignments(assignment)
    eligible_feature_ids = _resolve_eligible_first_growth_feature_ids(
        vdyp_yields=vdyp_yields,
        source_table=source_table,
        min_first_growth_age=min_first_growth_age,
    )
    stand_assignment = stand_assignment.loc[
        pd.to_numeric(stand_assignment["forest_cover_id"], errors="coerce")
        .fillna(-1)
        .astype(int)
        .isin(eligible_feature_ids)
    ].copy()
    assigned_feature_ids = set(
        pd.to_numeric(stand_assignment["forest_cover_id"], errors="coerce")
        .dropna()
        .astype(int)
    )
    unmatched_feature_ids = eligible_feature_ids - assigned_feature_ids
    if unmatched_feature_ids:
        if source_table is None:
            raise ValueError(
                "source_table is required when VDYP source stands do not match the "
                "published assignment bundle"
            )
        if levenshtein_fn is None:
            distance_mod = __import__("distance")
            levenshtein_fn = distance_mod.levenshtein
        stand_assignment = _expand_stand_assignment_with_lexmatch(
            stand_assignment=stand_assignment,
            source_table=source_table,
            unmatched_feature_ids=unmatched_feature_ids,
            levenshtein_fn=levenshtein_fn,
        )

    joined = vdyp_yields.merge(
        stand_assignment[["forest_cover_id", "au_id"]],
        left_on="FEATURE_ID",
        right_on="forest_cover_id",
        how="inner",
    )
    feature_tables = _build_feature_tables(joined)

    curve_rows: list[dict[str, Any]] = []
    diagnostic_rows: list[dict[str, Any]] = []

    for au_id, au_rows in joined.groupby("au_id", sort=True):
        feature_ids = sorted({int(v) for v in au_rows["FEATURE_ID"].tolist()})
        assignment_rows = stand_assignment.loc[
            stand_assignment["au_id"] == str(au_id)
        ].copy()
        ambiguous_count = int((assignment_rows["candidate_au_count"] > 1).sum())
        tie_break_count = int(assignment_rows["tie_break_used"].astype(bool).sum())
        assignment_status = assignment_rows.get(
            "assignment_status",
            pd.Series("assigned", index=assignment_rows.index),
        )
        lexmatch_used = assignment_rows.get(
            "lexmatch_alias_used",
            pd.Series(False, index=assignment_rows.index),
        )
        lexmatch_count = int(assignment_status.eq("lexmatch_assigned").sum())
        lexmatch_alias_count = int(lexmatch_used.astype(bool).sum())
        sparse_warning = len(feature_ids) < 5
        vdyp_out = {
            feature_id: feature_tables[feature_id] for feature_id in feature_ids
        }
        selection = select_au_first_growth_curve(
            vdyp_out=vdyp_out,
            min_source_stands=min_source_stands,
        )
        binned = selection.binned
        x_curve = selection.x_curve
        y_curve = selection.y_curve
        metrics = selection.metrics
        selected_path = selection.selected_path
        accepted = selection.accepted

        for age, volume in zip(
            np.asarray(x_curve, dtype=float), np.asarray(y_curve, dtype=float)
        ):
            if not math.isfinite(float(volume)) or float(volume) <= 0.0:
                continue
            curve_rows.append(
                {
                    "au_id": str(au_id),
                    "age": int(age),
                    "volume": round(float(volume), 6),
                }
            )

        diagnostic_rows.append(
            {
                "au_id": str(au_id),
                "source_stand_count": len(feature_ids),
                "source_row_count": int(len(au_rows)),
                "observed_bin_count": int(len(binned)),
                "curve_point_count": int(sum(1 for y in y_curve if float(y) > 0.0)),
                "age_min": int(au_rows["PRJ_TOTAL_AGE"].min()),
                "age_max": int(au_rows["PRJ_TOTAL_AGE"].max()),
                "assignment_weight_basis": assignment_rows[
                    "assignment_weight_basis"
                ].iloc[0],
                "ambiguous_stand_count": ambiguous_count,
                "tie_break_stand_count": tie_break_count,
                "lexmatch_stand_count": lexmatch_count,
                "lexmatch_alias_stand_count": lexmatch_alias_count,
                "sparse_warning": sparse_warning,
                "selected_path": selected_path,
                "rmse": round(metrics["rmse"], 6),
                "mape": round(metrics["mape"], 6),
                "tail_rmse": round(metrics["tail_rmse"], 6),
                "accepted": accepted,
            }
        )

    curves = pd.DataFrame(curve_rows, columns=["au_id", "age", "volume"]).sort_values(
        ["au_id", "age"], kind="stable"
    )
    diagnostics = pd.DataFrame(diagnostic_rows).sort_values("au_id", kind="stable")
    return curves.reset_index(drop=True), diagnostics.reset_index(drop=True)
