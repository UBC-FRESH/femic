from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping
import json

import numpy as np
import pandas as pd

from femic.pipeline.mkrf_au import parse_mkrf_bec
from femic.pipeline.tipsy import (
    build_btc_msyt_input_table,
    parse_btc_tsr_transposed_output,
)
from femic.pipeline.tsa import build_stratum_lexmatch_alias_map

_MANAGED_TIPSY_SPECIES_COLUMNS = ("BA", "CW", "DR", "FD", "HW", "YC")


@dataclass(frozen=True)
class ManagedSpeciesPayload:
    species_1: str
    species_2: str
    species_3: str
    species_4: str
    species_5: str
    pct_1: float
    pct_2: float
    pct_3: float
    pct_4: float
    pct_5: float


def build_mkrf_legacy_managed_au_table(
    *,
    man_si_by_au: pd.DataFrame,
    tipsy_spp_comp: pd.DataFrame,
) -> pd.DataFrame:
    merged = man_si_by_au.merge(tipsy_spp_comp, on="AU", how="inner")
    bec_parts = merged["BEC"].apply(parse_mkrf_bec)
    merged[["bec_zone", "bec_subzone", "bec_variant"]] = pd.DataFrame(
        bec_parts.tolist(),
        index=merged.index,
    )
    species_pairs = merged.apply(_tipsy_species_pair, axis=1)
    merged["leading_species_1"] = [pair[0] for pair in species_pairs]
    merged["leading_species_2"] = [pair[1] for pair in species_pairs]
    merged["legacy_candidate_au_id"] = (
        merged["bec_zone"].astype(str)
        + "_"
        + merged["bec_subzone"].astype(str)
        + "_"
        + merged["bec_variant"].astype(str)
        + "_"
        + merged["leading_species_1"].astype(str)
        + "_"
        + merged["leading_species_2"].astype(str)
    )
    return merged


def build_mkrf_managed_alias_map(
    *,
    selected_au_table: pd.DataFrame,
    legacy_au_table: pd.DataFrame,
    levenshtein_fn: Any | None = None,
) -> dict[str, str]:
    if levenshtein_fn is None:
        levenshtein_fn = __import__("distance").levenshtein
    selected_frame = pd.DataFrame(
        {
            "stratum": selected_au_table["au_id"],
            "stratum_lexmatch": selected_au_table["au_id"],
            "totalarea_p": selected_au_table["covered_area_ha"],
        }
    ).set_index("stratum")
    candidate_counts = (
        legacy_au_table.groupby("legacy_candidate_au_id", as_index=False)
        .size()
        .rename(columns={"size": "count"})
    )
    candidate_frame = pd.DataFrame(
        {
            "stratum": candidate_counts["legacy_candidate_au_id"],
            "stratum_lexmatch": candidate_counts["legacy_candidate_au_id"],
            "totalarea_p": candidate_counts["count"].astype(float),
        }
    ).set_index("stratum")
    alias_map = build_stratum_lexmatch_alias_map(
        f_table=pd.concat([selected_frame, candidate_frame], axis=0),
        stratum_col="stratum",
        selected_strata_codes=list(selected_au_table["au_id"]),
        levenshtein_fn=levenshtein_fn,
    )
    for selected_id in selected_au_table["au_id"].astype(str):
        alias_map[selected_id] = selected_id
    return alias_map


def build_mkrf_managed_au_bootstrap_table(
    *,
    selected_au_table: pd.DataFrame,
    assignment: pd.DataFrame,
    man_si_by_au: pd.DataFrame,
    tipsy_spp_comp: pd.DataFrame,
) -> pd.DataFrame:
    legacy_au_table = build_mkrf_legacy_managed_au_table(
        man_si_by_au=man_si_by_au,
        tipsy_spp_comp=tipsy_spp_comp,
    )
    alias_map = build_mkrf_managed_alias_map(
        selected_au_table=selected_au_table,
        legacy_au_table=legacy_au_table,
    )
    legacy_au_table = legacy_au_table.copy()
    legacy_au_table["mapped_au_id"] = legacy_au_table["legacy_candidate_au_id"].map(
        lambda value: alias_map.get(str(value), str(value))
    )
    area_by_au = (
        assignment.groupby("au_id", as_index=True)["shape_area_ha"].sum().to_dict()
    )

    rows: list[dict[str, Any]] = []
    ordered_selected = selected_au_table.sort_values(
        ["selected_rank", "au_id"], kind="stable"
    )
    for _, selected_row in ordered_selected.iterrows():
        au_id = str(selected_row["au_id"])
        selected_candidates = legacy_au_table.loc[
            legacy_au_table["mapped_au_id"].astype(str) == au_id
        ].copy()
        direct_candidates = selected_candidates.loc[
            selected_candidates["legacy_candidate_au_id"].astype(str) == au_id
        ].copy()

        if not direct_candidates.empty:
            chosen = direct_candidates
            bootstrap_status = "direct"
        elif not selected_candidates.empty:
            chosen = selected_candidates
            bootstrap_status = "lexmatch"
        else:
            chosen = selected_candidates
            bootstrap_status = "unmatched"

        base_row = {
            "au_id": au_id,
            "selected_rank": int(selected_row["selected_rank"]),
            "covered_area_ha": float(selected_row["covered_area_ha"]),
            "bec_zone": str(selected_row["bec_zone"]),
            "bec_subzone": str(selected_row["bec_subzone"]),
            "bec_variant": str(selected_row["bec_variant"]),
            "leading_species_1": str(selected_row["leading_species_1"]),
            "leading_species_2": str(selected_row["leading_species_2"]),
            "managed_curve_id": 60000 + int(selected_row["selected_rank"]),
            "bootstrap_status": bootstrap_status,
            "mapping_path": bootstrap_status,
            "density_total": 1400,
            "regen_delay": 1,
            "oaf1": 1.0,
            "oaf2": 0.95,
            "planted_percent": 100,
            "legacy_row_count": int(len(chosen)),
            "direct_match_count": int(len(direct_candidates)),
            "lexmatch_match_count": int(len(selected_candidates) - len(direct_candidates)),
        }
        if chosen.empty:
            rows.append(
                {
                    **base_row,
                    "managed_si": np.nan,
                    "legacy_au_ids": "",
                    "legacy_candidate_au_ids": "",
                    **_managed_species_payload_dict(
                        ManagedSpeciesPayload("", "", "", "", "", 0, 0, 0, 0, 0)
                    ),
                }
            )
            continue

        weights = chosen["legacy_candidate_au_id"].map(
            lambda value: float(
                area_by_au.get(str(value), float(selected_row["covered_area_ha"]))
            )
        )
        managed_si = _weighted_median(
            pd.to_numeric(chosen["SI"], errors="coerce"),
            pd.to_numeric(weights, errors="coerce"),
        )
        payload = _aggregate_managed_species_payload(chosen, weights)
        rows.append(
            {
                **base_row,
                "managed_si": managed_si,
                "legacy_au_ids": ";".join(
                    str(int(v))
                    for v in sorted(
                        pd.to_numeric(chosen["AU"], errors="coerce")
                        .dropna()
                        .astype(int)
                        .unique()
                    )
                ),
                "legacy_candidate_au_ids": ";".join(
                    sorted(chosen["legacy_candidate_au_id"].astype(str).unique().tolist())
                ),
                **_managed_species_payload_dict(payload),
            }
        )

    return pd.DataFrame(rows)


def build_mkrf_managed_au_msyt_table(
    *,
    bootstrap_table: pd.DataFrame,
) -> pd.DataFrame:
    included = bootstrap_table.loc[
        bootstrap_table["bootstrap_status"].isin(["direct", "lexmatch"])
    ].copy()
    if included.empty:
        raise RuntimeError("No managed AU bootstrap rows available for MSYT generation.")
    included = included.sort_values(["selected_rank", "au_id"], kind="stable")
    tipsy_rows: list[dict[str, Any]] = []
    for _, row in included.iterrows():
        tipsy_row: dict[str, Any] = {
            "AU": int(row["managed_curve_id"]),
            "BEC": _format_mkrf_bec(
                str(row["bec_zone"]),
                str(row["bec_subzone"]),
                str(row["bec_variant"]),
            ),
            "Proportion": 1.0,
            "Regen_Delay": int(row["regen_delay"]),
            "Density": int(row["density_total"]),
            "OAF1": float(row["oaf1"]),
            "OAF2": float(row["oaf2"]),
            "SI": float(row["managed_si"]),
        }
        for i in range(1, 6):
            tipsy_row[f"SPP_{i}"] = row.get(f"managed_species_{i}", "")
            tipsy_row[f"PCT_{i}"] = row.get(f"managed_pct_{i}", "")
            tipsy_row[f"GW_{i}"] = ""
        tipsy_rows.append(tipsy_row)
    tipsy_table = pd.DataFrame(tipsy_rows)
    return build_btc_msyt_input_table(tipsy_table=tipsy_table, pd_module=pd)


def parse_mkrf_managed_au_curves(
    *,
    output_csv: Path,
    bootstrap_table: pd.DataFrame,
) -> pd.DataFrame:
    parsed = parse_btc_tsr_transposed_output(output_csv=output_csv, pd_module=pd)
    lookup = (
        bootstrap_table.loc[
            bootstrap_table["bootstrap_status"].isin(["direct", "lexmatch"]),
            ["managed_curve_id", "au_id"],
        ]
        .copy()
        .assign(managed_curve_id=lambda df: pd.to_numeric(df["managed_curve_id"]).astype(int))
    )
    merged = parsed.merge(
        lookup,
        left_on="AU",
        right_on="managed_curve_id",
        how="left",
        validate="many_to_one",
    )
    curves = merged.rename(
        columns={
            "Age": "age",
            "Yield": "volume",
            "Height": "height",
            "DBHq": "dbhq",
            "TPH": "tph",
            "GrossYield": "gross_yield",
            "CrownCover": "crown_cover",
        }
    )
    ordered_columns = [
        "au_id",
        "managed_curve_id",
        "age",
        "volume",
        "height",
        "dbhq",
        "tph",
        "gross_yield",
        "crown_cover",
    ]
    for column in ordered_columns:
        if column not in curves.columns:
            curves[column] = np.nan
    return curves[ordered_columns].sort_values(
        ["managed_curve_id", "age"], kind="stable"
    ).reset_index(drop=True)


def write_mkrf_managed_run_manifest(
    *,
    manifest_path: Path,
    payload: Mapping[str, Any],
) -> Path:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return manifest_path


def _tipsy_species_pair(row: pd.Series) -> tuple[str, str]:
    ranked: list[tuple[str, float]] = []
    for column in _MANAGED_TIPSY_SPECIES_COLUMNS:
        raw = row.get(column)
        try:
            share = float(raw)
        except (TypeError, ValueError):
            share = 0.0
        if not np.isfinite(share) or share <= 0.0:
            continue
        ranked.append((column.lower() if column != "FD" else "fdc", share))
    ranked.sort(key=lambda item: (-item[1], item[0]))
    if not ranked:
        return ("x", "x")
    if len(ranked) == 1:
        return (ranked[0][0], "x")
    return (ranked[0][0], ranked[1][0])


def _managed_species_payload_dict(payload: ManagedSpeciesPayload) -> dict[str, Any]:
    return {
        "managed_species_1": payload.species_1,
        "managed_species_2": payload.species_2,
        "managed_species_3": payload.species_3,
        "managed_species_4": payload.species_4,
        "managed_species_5": payload.species_5,
        "managed_pct_1": payload.pct_1,
        "managed_pct_2": payload.pct_2,
        "managed_pct_3": payload.pct_3,
        "managed_pct_4": payload.pct_4,
        "managed_pct_5": payload.pct_5,
    }


def _aggregate_managed_species_payload(
    candidates: pd.DataFrame,
    weights: pd.Series,
) -> ManagedSpeciesPayload:
    weighted_shares: list[tuple[str, float]] = []
    norm_weights = pd.to_numeric(weights, errors="coerce").fillna(0.0)
    if float(norm_weights.sum()) <= 0.0:
        norm_weights = pd.Series(
            np.ones(len(candidates), dtype=float),
            index=candidates.index,
        )
    for column in _MANAGED_TIPSY_SPECIES_COLUMNS:
        if column in candidates.columns:
            raw_shares = candidates[column]
        else:
            raw_shares = pd.Series(0.0, index=candidates.index)
        shares = pd.to_numeric(raw_shares, errors="coerce").fillna(0.0)
        total_share = float(np.average(shares, weights=norm_weights))
        if total_share <= 0.0:
            continue
        weighted_shares.append((column, total_share))
    weighted_shares.sort(key=lambda item: (-item[1], item[0]))
    top = weighted_shares[:5]
    normalized = []
    total = sum(share for _code, share in top)
    for code, share in top:
        pct = (share / total * 100.0) if total > 0 else 0.0
        normalized.append((code, round(pct, 3)))
    while len(normalized) < 5:
        normalized.append(("", 0.0))
    return ManagedSpeciesPayload(
        species_1=normalized[0][0],
        species_2=normalized[1][0],
        species_3=normalized[2][0],
        species_4=normalized[3][0],
        species_5=normalized[4][0],
        pct_1=normalized[0][1],
        pct_2=normalized[1][1],
        pct_3=normalized[2][1],
        pct_4=normalized[3][1],
        pct_5=normalized[4][1],
    )


def _weighted_median(values: pd.Series, weights: pd.Series) -> float:
    table = pd.DataFrame(
        {
            "value": pd.to_numeric(values, errors="coerce"),
            "weight": pd.to_numeric(weights, errors="coerce"),
        }
    ).dropna(subset=["value", "weight"])
    table = table.loc[table["weight"] > 0].sort_values(["value", "weight"], kind="stable")
    if table.empty:
        return float("nan")
    cutoff = float(table["weight"].sum()) / 2.0
    cumulative = table["weight"].cumsum()
    idx = int(cumulative.ge(cutoff).idxmax())
    return float(table.loc[idx, "value"])


def _format_mkrf_bec(zone: str, subzone: str, variant: str) -> str:
    base = f"{zone.upper()}{subzone}"
    if variant == "x":
        return base
    return f"{base}{variant}"
