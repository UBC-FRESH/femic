"""MKRF-specific AU table and stand-assignment builders."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

import pandas as pd


_SPECIES_SLOT_COUNT = 6


def parse_mkrf_bec(value: object) -> tuple[str, str, str]:
    """Split legacy MKRF BEC code into zone, subzone, and variant."""
    text = "" if value is None else str(value).strip()
    if not text or text.lower() == "nan":
        return ("x", "x", "x")
    zone = text[:3].lower() or "x"
    rest = text[3:]
    boundary = 0
    while boundary < len(rest) and rest[boundary].isalpha():
        boundary += 1
    subzone = (rest[:boundary] or "x").lower()
    variant = (rest[boundary:] or "x").lower()
    return (zone, subzone, variant)


@dataclass(frozen=True)
class OrderedSpeciesPair:
    """Ordered top-two species result for one source row."""

    leading_species_1: str
    leading_species_2: str
    leading_species_1_share: float
    leading_species_2_share: float
    species_count: int
    tie_break_used: bool


def ordered_top_two_species(row: Any) -> OrderedSpeciesPair:
    """Return ordered top-two species using descending share, then lexical tie-break."""
    merged: dict[str, float] = {}
    for idx in range(1, _SPECIES_SLOT_COUNT + 1):
        species = row.get(f"TCL_1_TSP_{idx}_TREE_SPECIES_CODE")
        species_text = "" if species is None else str(species).strip().lower()
        if not species_text or species_text == "nan":
            continue
        raw_share = row.get(f"TCL_1_TSP_{idx}_SPECIES_PCT")
        try:
            share = float(raw_share)
        except (TypeError, ValueError):
            share = 0.0
        if not math.isfinite(share) or share <= 0.0:
            continue
        merged[species_text] = merged.get(species_text, 0.0) + share

    if not merged:
        return OrderedSpeciesPair("x", "x", 0.0, 0.0, 0, False)

    ranked = sorted(merged.items(), key=lambda item: (-item[1], item[0]))
    share_counts: dict[float, int] = {}
    for _, share in ranked:
        share_counts[share] = share_counts.get(share, 0) + 1
    top_two = ranked[:2]
    tie_break_used = any(share_counts[share] > 1 for _, share in top_two)

    lead_1, share_1 = ranked[0]
    if len(ranked) > 1:
        lead_2, share_2 = ranked[1]
    else:
        lead_2, share_2 = "x", 0.0

    return OrderedSpeciesPair(
        leading_species_1=lead_1,
        leading_species_2=lead_2,
        leading_species_1_share=float(share_1),
        leading_species_2_share=float(share_2),
        species_count=len(ranked),
        tie_break_used=tie_break_used,
    )


def annotate_mkrf_au_keys(source_table: pd.DataFrame) -> pd.DataFrame:
    """Annotate MKRF source rows with canonical AU-key fields."""
    table = source_table.copy()

    bec_parts = table["BEC"].apply(parse_mkrf_bec)
    table[["bec_zone", "bec_subzone", "bec_variant"]] = pd.DataFrame(
        bec_parts.tolist(),
        index=table.index,
    )

    species_pairs = table.apply(ordered_top_two_species, axis=1)
    species_frame = pd.DataFrame(
        [
            {
                "leading_species_1": item.leading_species_1,
                "leading_species_2": item.leading_species_2,
                "leading_species_1_share": item.leading_species_1_share,
                "leading_species_2_share": item.leading_species_2_share,
                "species_count": item.species_count,
                "tie_break_used": item.tie_break_used,
            }
            for item in species_pairs
        ],
        index=table.index,
    )
    table = pd.concat([table, species_frame], axis=1)

    table["au_id"] = (
        table["bec_zone"].astype(str)
        + "_"
        + table["bec_subzone"].astype(str)
        + "_"
        + table["bec_variant"].astype(str)
        + "_"
        + table["leading_species_1"].astype(str)
        + "_"
        + table["leading_species_2"].astype(str)
    )
    return table


def build_mkrf_assignment_rows(source_table: pd.DataFrame) -> pd.DataFrame:
    """Build fragment-level MKRF assignment rows from source geometry rows."""
    table = annotate_mkrf_au_keys(source_table)
    shape_area = (
        table["Shape_Area"]
        if "Shape_Area" in table.columns
        else pd.Series(0.0, index=table.index)
    )

    assignment = pd.DataFrame(
        {
            "source_feature_class": "resultant",
            "res_key": table["RES_KEY"].astype(int),
            "forest_cover_id": table["FOREST_COVER_ID"],
            "bec": table["BEC"].astype(str),
            "bec_zone": table["bec_zone"],
            "bec_subzone": table["bec_subzone"],
            "bec_variant": table["bec_variant"],
            "leading_species_1": table["leading_species_1"],
            "leading_species_2": table["leading_species_2"],
            "leading_species_1_share": table["leading_species_1_share"],
            "leading_species_2_share": table["leading_species_2_share"],
            "species_count": table["species_count"].astype(int),
            "tie_break_used": table["tie_break_used"].astype(bool),
            "shape_area_ha": (
                pd.to_numeric(shape_area, errors="coerce").fillna(0.0) / 10000.0
            ),
            "au_id": table["au_id"],
            "assignment_status": "assigned",
        }
    ).sort_values(["au_id", "res_key"], kind="stable")
    return assignment.reset_index(drop=True)


def build_mkrf_au_tables(
    source_table: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build canonical MKRF AU and stand-assignment tables from Resultant records."""
    table = source_table.copy()
    if "CONTCLAS" in table.columns:
        table = table.loc[table["CONTCLAS"] != "X"].copy()

    assignment = build_mkrf_assignment_rows(table)
    au_table = (
        assignment.groupby(
            [
                "au_id",
                "bec_zone",
                "bec_subzone",
                "bec_variant",
                "leading_species_1",
                "leading_species_2",
            ],
            as_index=False,
            sort=True,
        )
        .agg(
            stand_count=("res_key", "count"),
            tie_break_record_count=("tie_break_used", "sum"),
        )
        .sort_values("au_id", kind="stable")
    )

    au_table["tie_break_record_count"] = au_table["tie_break_record_count"].astype(int)
    au_table["stand_count"] = au_table["stand_count"].astype(int)
    return au_table.reset_index(drop=True), assignment


def build_mkrf_selected_au_table(
    au_table: pd.DataFrame,
    assignment: pd.DataFrame,
    *,
    target_coverage: float = 0.95,
) -> pd.DataFrame:
    """Select the smallest top-N AU subset reaching the target covered-area share."""
    if not 0.0 < float(target_coverage) <= 1.0:
        raise ValueError("target_coverage must be in the interval (0, 1].")

    if au_table.empty:
        selected = au_table.copy()
        selected["covered_area_ha"] = pd.Series(dtype=float)
        selected["covered_area_share"] = pd.Series(dtype=float)
        selected["cumulative_covered_area_share"] = pd.Series(dtype=float)
        selected["selected_rank"] = pd.Series(dtype=int)
        selected["target_coverage"] = float(target_coverage)
        return selected

    area_by_au = (
        assignment.groupby("au_id", as_index=True)["shape_area_ha"]
        .sum()
        .rename("covered_area_ha")
    )
    selected = au_table.merge(area_by_au, on="au_id", how="left")
    selected["covered_area_ha"] = pd.to_numeric(
        selected["covered_area_ha"], errors="coerce"
    ).fillna(0.0)
    selected = selected.sort_values(
        ["covered_area_ha", "au_id"],
        ascending=[False, True],
        kind="stable",
    ).reset_index(drop=True)

    total_area = float(selected["covered_area_ha"].sum())
    if total_area <= 0.0:
        selected["covered_area_share"] = 0.0
        selected["cumulative_covered_area_share"] = 0.0
        selected["selected_rank"] = pd.Series(range(1, len(selected) + 1), dtype=int)
        selected["target_coverage"] = float(target_coverage)
        return selected.iloc[0:0].copy()

    selected["covered_area_share"] = selected["covered_area_ha"] / total_area
    selected["cumulative_covered_area_share"] = selected["covered_area_share"].cumsum()
    cutoff_idx = (
        selected["cumulative_covered_area_share"].ge(float(target_coverage)).idxmax()
    )
    selected = selected.iloc[: cutoff_idx + 1].copy()
    selected["selected_rank"] = pd.Series(range(1, len(selected) + 1), dtype=int)
    selected["target_coverage"] = float(target_coverage)
    return selected.reset_index(drop=True)
