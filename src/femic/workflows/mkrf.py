"""MKRF-specific rebuild workflows."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
from textwrap import dedent
import xml.etree.ElementTree as et

import geopandas as gpd
import numpy as np
import pandas as pd

from femic.pipeline.mkrf_au import (
    build_mkrf_au_tables,
    build_mkrf_selected_au_table,
)
from femic.pipeline.mkrf_first_growth import (
    _MIN_FIRST_GROWTH_SOURCE_STANDS,
    build_mkrf_first_growth_curves,
    collapse_stand_assignments,
    _resolve_eligible_first_growth_feature_ids,
)
from femic.pipeline.mkrf_managed import (
    build_mkrf_stand_origin_assignment,
    build_mkrf_managed_au_bootstrap_table,
    build_mkrf_managed_au_msyt_table,
    load_mkrf_managed_rule_config,
    parse_mkrf_managed_au_curves,
    write_mkrf_managed_run_manifest,
)
from femic.pipeline.plots import (
    StrataDistributionPlotMetadata,
    build_strata_distribution_plot_config,
    render_strata_distribution_plot,
    resolve_strata_plot_ordering,
    strata_plot_paths,
)
from femic.pipeline.tipsy import run_btc_cli
from femic.fmg.patchworks import validate_forestmodel_xml_tree, write_forestmodel_xml


@dataclass(frozen=True)
class MkrfAuBuildResult:
    """Result payload for MKRF AU-input bundle materialization."""

    resultant_gdb: Path
    output_dir: Path
    au_table_path: Path
    stand_assignment_path: Path
    source_row_count: int
    au_count: int


@dataclass(frozen=True)
class MkrfFirstGrowthBuildResult:
    """Result payload for MKRF AU-wise first-growth curve materialization."""

    vdyp_yields_csv: Path
    assignment_csv: Path
    output_dir: Path
    curves_path: Path
    diagnostics_path: Path
    au_count: int
    assigned_stand_count: int
    raw_unmatched_source_stand_count: int
    residual_unmatched_source_stand_count: int
    lexmatch_assigned_stand_count: int


def _parse_mkrf_au_id(au_id: str) -> tuple[str, str, str, str, str] | None:
    parts = str(au_id).split("_")
    if len(parts) != 5:
        return None
    return (parts[0], parts[1], parts[2], parts[3], parts[4])


def _normalize_species_bucket(species_code: str) -> str:
    code = str(species_code).strip().upper()
    if code in {"BA"}:
        return "Ba"
    if code in {"CW"}:
        return "Cw"
    if code in {"DR"}:
        return "Dr"
    if code in {"FD", "FDC"}:
        return "Fd"
    if code in {"HW"}:
        return "Hw"
    if code in {"YC"}:
        return "Yc"
    if code in {"AC", "ACT", "AT", "EP", "MB"}:
        return "Dec"
    if code:
        return "Oth"
    return ""


_SPECIES_BUCKETS = ("Ba", "Cw", "Dec", "Dr", "Fd", "Hw", "Oth", "Yc")
_MKRF_CT_BUCKET_ANCHORS = (35, 40, 45)
_MKRF_CT_BUCKET_WIDTH = 5
_MKRF_CT_BUCKET_PREFIX_WIDTH = 3
_MKRF_CT_TARGET_BA_REMOVAL_FRACTION = 0.45
_MKRF_CT_MIN_CW_FD_SHARE_PCT = 50.0


def _build_lookup_expr(keys: list[str], values: list[str], *, key_expr: str) -> str:
    return f"lookupTable({key_expr},'{','.join(keys)}','{','.join(values)}')"


def _mkrf_ct_bucket_label(anchor_age: int) -> str:
    return f"CT{int(anchor_age)}"


def _mkrf_ct_bucket_prefix(anchor_age: int) -> str:
    return f"thn{int(anchor_age):0{_MKRF_CT_BUCKET_PREFIX_WIDTH}d}_"


def _mkrf_ct_bucket_specs() -> tuple[dict[str, int | str], ...]:
    return tuple(
        {
            "anchor_age": int(anchor_age),
            "label": _mkrf_ct_bucket_label(anchor_age),
            "prefix": _mkrf_ct_bucket_prefix(anchor_age),
            "min_age": int(anchor_age),
            "max_age": int(anchor_age) + _MKRF_CT_BUCKET_WIDTH - 1,
        }
        for anchor_age in _MKRF_CT_BUCKET_ANCHORS
    )


def _ct_product_species_fraction_expr(
    share_column: str,
    origin_share_lookup_exprs: dict[str, str],
) -> str:
    target = str(_MKRF_CT_TARGET_BA_REMOVAL_FRACTION)
    hw_share = origin_share_lookup_exprs["share_hw"]
    fd_share = origin_share_lookup_exprs["share_fd"]
    if share_column == "share_cw":
        return "0"
    if share_column == "share_hw":
        return f"if(({hw_share}) gt {target},1,({hw_share})/{target})"
    if share_column == "share_fd":
        return (
            f"if(({hw_share}) gt {target},0,"
            f"if(({hw_share})+({fd_share}) gt {target},"
            f"({target}-({hw_share}))/{target},({fd_share})/{target}))"
        )
    if share_column == "share_oth":
        return (
            f"if(({hw_share})+({fd_share}) gt {target},0,"
            f"({target}-({hw_share})-({fd_share}))/{target})"
        )
    return "0"


def _build_managed_species_share_table(
    managed_bootstrap_table: pd.DataFrame,
    *,
    species_prefix: str = "managed",
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for row in managed_bootstrap_table.itertuples(index=False):
        shares = {bucket: 0.0 for bucket in _SPECIES_BUCKETS}
        for index in range(1, 6):
            species_code = getattr(row, f"{species_prefix}_species_{index}", "")
            pct_value = pd.to_numeric(
                getattr(row, f"{species_prefix}_pct_{index}", 0.0), errors="coerce"
            )
            if pd.isna(pct_value) or float(pct_value) <= 0:
                continue
            bucket = _normalize_species_bucket(str(species_code))
            if bucket:
                shares[bucket] += float(pct_value)
        row_payload = {"au_id": str(row.au_id).strip()}
        row_payload.update({f"share_{bucket.lower()}": shares[bucket] for bucket in shares})
        rows.append(row_payload)
    return pd.DataFrame(rows)


def _build_unmanaged_species_share_table(
    stand_assignment: pd.DataFrame,
    *,
    selected_au_table: pd.DataFrame | None = None,
) -> pd.DataFrame:
    rows = stand_assignment.copy()
    rows["au_id"] = rows["au_id"].astype(str).str.strip()
    if selected_au_table is not None:
        selected_ids = set(selected_au_table["au_id"].astype(str).str.strip())
        rows = rows.loc[rows["au_id"].isin(selected_ids)].copy()

    rows["shape_area_ha"] = pd.to_numeric(rows["shape_area_ha"], errors="coerce").fillna(0.0)
    rows["leading_species_1_share"] = pd.to_numeric(
        rows["leading_species_1_share"], errors="coerce"
    ).fillna(0.0)
    rows["leading_species_2_share"] = pd.to_numeric(
        rows["leading_species_2_share"], errors="coerce"
    ).fillna(0.0)

    payload_rows: list[dict[str, object]] = []
    for row in rows.itertuples(index=False):
        area_ha = float(row.shape_area_ha)
        if area_ha <= 0:
            continue

        shares = {bucket: 0.0 for bucket in _SPECIES_BUCKETS}
        species_1 = _normalize_species_bucket(getattr(row, "leading_species_1", ""))
        species_2 = _normalize_species_bucket(getattr(row, "leading_species_2", ""))
        species_1_share = max(float(row.leading_species_1_share), 0.0)
        species_2_share = max(float(row.leading_species_2_share), 0.0)

        if species_1:
            shares[species_1] += area_ha * species_1_share / 100.0
        if species_2:
            shares[species_2] += area_ha * species_2_share / 100.0

        residual_share = max(0.0, 100.0 - species_1_share - species_2_share)
        shares["Oth"] += area_ha * residual_share / 100.0

        payload = {
            "au_id": str(row.au_id).strip(),
            "area_ha": area_ha,
        }
        payload.update({f"share_{bucket.lower()}_ha": shares[bucket] for bucket in _SPECIES_BUCKETS})
        payload_rows.append(payload)

    if not payload_rows:
        return pd.DataFrame(
            columns=["au_id", "area_ha", *[f"share_{bucket.lower()}" for bucket in _SPECIES_BUCKETS]]
        )

    aggregated = pd.DataFrame(payload_rows).groupby("au_id", as_index=False).sum(numeric_only=True)
    for bucket in _SPECIES_BUCKETS:
        area_column = f"share_{bucket.lower()}_ha"
        share_column = f"share_{bucket.lower()}"
        aggregated[share_column] = np.where(
            aggregated["area_ha"].gt(0),
            aggregated[area_column] / aggregated["area_ha"] * 100.0,
            0.0,
        )

    return aggregated[["au_id", *[f"share_{bucket.lower()}" for bucket in _SPECIES_BUCKETS]]]


def _build_species_share_audit_table(
    *,
    managed_species_shares: pd.DataFrame,
    unmanaged_species_shares: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for origin_lane, source_name, frame in (
        ("treated", "managed_bootstrap", managed_species_shares),
        ("natural", "stand_au_assignment", unmanaged_species_shares),
    ):
        if frame.empty:
            continue
        working = frame.copy()
        working["au_id"] = working["au_id"].astype(str).str.strip()
        for row in working.itertuples(index=False):
            for bucket in _SPECIES_BUCKETS:
                share_pct = float(pd.to_numeric(getattr(row, f"share_{bucket.lower()}", 0.0), errors="coerce") or 0.0)
                rows.append(
                    {
                        "origin_lane": origin_lane,
                        "source_name": source_name,
                        "au_id": str(row.au_id).strip(),
                        "species_bucket": bucket,
                        "share_pct": share_pct,
                        "share_class": "nonzero" if share_pct > 0 else "zero",
                    }
                )
    return pd.DataFrame(rows).sort_values(
        ["origin_lane", "source_name", "au_id", "species_bucket"],
        kind="stable",
    )


def _build_ct_eligibility_audit_table(
    *,
    selected_au_table: pd.DataFrame,
    ct_eligibility_species_shares: pd.DataFrame,
) -> pd.DataFrame:
    selected = selected_au_table.copy()
    selected["au_id"] = selected["au_id"].astype(str).str.strip()
    if "leading_species_1" not in selected.columns or "leading_species_2" not in selected.columns:
        parsed = selected["au_id"].map(_parse_mkrf_au_id)
        selected["leading_species_1"] = [
            parts[3] if parts is not None else "" for parts in parsed
        ]
        selected["leading_species_2"] = [
            parts[4] if parts is not None else "" for parts in parsed
        ]
    selected = selected.drop_duplicates(subset=["au_id"], keep="first")
    shares = ct_eligibility_species_shares.copy()
    shares["au_id"] = shares["au_id"].astype(str).str.strip()
    audit = selected[["au_id", "leading_species_1", "leading_species_2"]].merge(
        shares[
            [
                "au_id",
                "share_cw",
                "share_fd",
                "share_hw",
                "share_cw_fd",
            ]
        ],
        on="au_id",
        how="left",
        validate="one_to_one",
    )
    for column in ("share_cw", "share_fd", "share_hw", "share_cw_fd"):
        audit[column] = pd.to_numeric(audit[column], errors="coerce").fillna(0.0)
    leading_species = (
        audit["leading_species_1"].astype(str).str.lower()
        + "_"
        + audit["leading_species_2"].astype(str).str.lower()
    )
    audit["runtime_operable_or_ground_candidate"] = ~leading_species.str.contains(
        r"(?:^|_)ba(?:$|_)", regex=True
    )
    audit["runtime_ct_eligible_before_species_filter"] = audit[
        "runtime_operable_or_ground_candidate"
    ]
    audit["cw_fd_threshold_pct"] = float(_MKRF_CT_MIN_CW_FD_SHARE_PCT)
    audit["cw_fd_ge_threshold"] = audit["share_cw_fd"].ge(_MKRF_CT_MIN_CW_FD_SHARE_PCT)
    audit["final_ct_eligible"] = (
        audit["runtime_ct_eligible_before_species_filter"]
        & audit["cw_fd_ge_threshold"]
    )

    def _reasons(row: pd.Series) -> str:
        reasons: list[str] = []
        if not bool(row["runtime_ct_eligible_before_species_filter"]):
            reasons.append("runtime_ct_or_operability_seam")
        if not bool(row["cw_fd_ge_threshold"]):
            reasons.append("cw_fd_share_lt_50")
        return ";".join(reasons)

    audit["exclusion_reasons"] = audit.apply(_reasons, axis=1)
    audit = audit.rename(
        columns={
            "share_cw": "base_cw_share_pct",
            "share_fd": "base_fd_share_pct",
            "share_hw": "base_hw_share_pct",
            "share_cw_fd": "base_cw_fd_share_pct",
        }
    )
    return audit[
        [
            "au_id",
            "runtime_operable_or_ground_candidate",
            "runtime_ct_eligible_before_species_filter",
            "base_cw_share_pct",
            "base_fd_share_pct",
            "base_hw_share_pct",
            "base_cw_fd_share_pct",
            "cw_fd_threshold_pct",
            "cw_fd_ge_threshold",
            "final_ct_eligible",
            "exclusion_reasons",
        ]
    ].sort_values("au_id", kind="stable")


def _ct_product_fraction_values(*, hw_share: float, fd_share: float) -> dict[str, float]:
    target = float(_MKRF_CT_TARGET_BA_REMOVAL_FRACTION)
    hw_fraction = 1.0 if hw_share > target else hw_share / target
    if hw_share > target:
        fd_fraction = 0.0
    elif hw_share + fd_share > target:
        fd_fraction = (target - hw_share) / target
    else:
        fd_fraction = fd_share / target
    other_fraction = (
        0.0
        if hw_share + fd_share > target
        else (target - hw_share - fd_share) / target
    )
    return {
        "cw": 0.0,
        "hw": max(0.0, hw_fraction),
        "fd": max(0.0, fd_fraction),
        "other": max(0.0, other_fraction),
    }


def _build_ct_intensity_audit_tables(
    *,
    ct_eligibility_audit: pd.DataFrame,
    treated_species_shares: pd.DataFrame,
    ct_bucket_specs: tuple[dict[str, int | str], ...],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    eligible = ct_eligibility_audit.loc[
        ct_eligibility_audit["final_ct_eligible"].fillna(False).astype(bool)
    ].copy()
    treated = treated_species_shares.copy()
    treated["au_id"] = treated["au_id"].astype(str).str.strip()
    rows: list[dict[str, object]] = []
    for eligible_row in eligible.itertuples(index=False):
        share_row = treated.loc[treated["au_id"].eq(str(eligible_row.au_id))]
        if share_row.empty:
            continue
        share = share_row.iloc[0]
        treated_cw = float(pd.to_numeric(share.get("share_cw", 0.0), errors="coerce") or 0.0)
        treated_hw = float(pd.to_numeric(share.get("share_hw", 0.0), errors="coerce") or 0.0)
        treated_fd = float(pd.to_numeric(share.get("share_fd", 0.0), errors="coerce") or 0.0)
        treated_other = max(0.0, 100.0 - treated_cw - treated_hw - treated_fd)
        fractions = _ct_product_fraction_values(
            hw_share=treated_hw / 100.0,
            fd_share=treated_fd / 100.0,
        )
        for bucket_spec in ct_bucket_specs:
            rows.append(
                {
                    "au_id": str(eligible_row.au_id),
                    "treatment": str(bucket_spec["label"]),
                    "ct_target_removal_fraction": float(
                        _MKRF_CT_TARGET_BA_REMOVAL_FRACTION
                    ),
                    "base_cw_fd_share_pct": float(eligible_row.base_cw_fd_share_pct),
                    "treated_cw_share_pct": treated_cw,
                    "treated_hw_share_pct": treated_hw,
                    "treated_fd_share_pct": treated_fd,
                    "previous_composition_proportional_cw_product_fraction": treated_cw
                    / 100.0,
                    "previous_composition_proportional_hw_product_fraction": treated_hw
                    / 100.0,
                    "previous_composition_proportional_fd_product_fraction": treated_fd
                    / 100.0,
                    "previous_composition_proportional_other_product_fraction": treated_other
                    / 100.0,
                    "implemented_ct_cw_product_fraction": fractions["cw"],
                    "implemented_ct_hw_product_fraction": fractions["hw"],
                    "implemented_ct_fd_product_fraction": fractions["fd"],
                    "implemented_ct_other_product_fraction": fractions["other"],
                    "implemented_ct_product_fraction_sum": sum(fractions.values()),
                    "prescription_note": "target_bounded_hw_first_fd_balancer_cw_retained_fd_secondary",
                }
            )
    audit = pd.DataFrame(rows)
    if audit.empty:
        summary = pd.DataFrame(
            columns=[
                "treatment",
                "au_count",
                "max_implemented_cw_product_fraction",
                "min_implemented_hw_product_fraction",
                "max_implemented_hw_product_fraction",
                "max_implemented_fd_product_fraction",
            ]
        )
        return audit, summary
    summary = (
        audit.groupby("treatment", as_index=False)
        .agg(
            au_count=("au_id", "nunique"),
            max_implemented_cw_product_fraction=(
                "implemented_ct_cw_product_fraction",
                "max",
            ),
            min_implemented_hw_product_fraction=(
                "implemented_ct_hw_product_fraction",
                "min",
            ),
            max_implemented_hw_product_fraction=(
                "implemented_ct_hw_product_fraction",
                "max",
            ),
            max_implemented_fd_product_fraction=(
                "implemented_ct_fd_product_fraction",
                "max",
            ),
        )
        .sort_values("treatment", kind="stable")
    )
    return audit.sort_values(["au_id", "treatment"], kind="stable"), summary


def _build_hw_ingrowth_overlay_audit_tables(
    *,
    managed_bootstrap: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    species_codes = ("BA", "CW", "DR", "FD", "HW", "PW", "SS", "YC")
    rows: list[dict[str, object]] = []
    if "included_in_msyt" in managed_bootstrap.columns:
        included = managed_bootstrap.loc[
            managed_bootstrap["included_in_msyt"].fillna(False).astype(bool)
        ].copy()
    else:
        included = managed_bootstrap.copy()
    for bootstrap_row in included.itertuples(index=False):
        density_total = float(
            pd.to_numeric(getattr(bootstrap_row, "density_total", 0.0), errors="coerce")
            or 0.0
        )
        payload: dict[str, object] = {
            "au_id": str(getattr(bootstrap_row, "au_id")),
            "managed_family_id": str(getattr(bootstrap_row, "managed_family_id", "")),
            "density_total": density_total,
            "hw_ingrowth_pct": float(
                pd.to_numeric(
                    getattr(bootstrap_row, "hw_ingrowth_pct", 0.0),
                    errors="coerce",
                )
                or 0.0
            ),
            "hw_ingrowth_source": str(
                getattr(bootstrap_row, "hw_ingrowth_source", "")
            ),
            "managed_species_overflow_to_hw_pct": float(
                pd.to_numeric(
                    getattr(bootstrap_row, "managed_species_overflow_to_hw_pct", 0.0),
                    errors="coerce",
                )
                or 0.0
            ),
            "managed_species_overflow_to_hw_codes": str(
                getattr(bootstrap_row, "managed_species_overflow_to_hw_codes", "")
            ),
        }
        for species_code in species_codes:
            code = species_code.lower()
            base_pct = 0.0
            adjusted_pct = 0.0
            for index in range(1, 6):
                base_species = str(
                    getattr(bootstrap_row, f"base_managed_species_{index}", "")
                ).upper()
                adjusted_species = str(
                    getattr(bootstrap_row, f"managed_species_{index}", "")
                ).upper()
                base_value = pd.to_numeric(
                    getattr(bootstrap_row, f"base_managed_pct_{index}", 0.0),
                    errors="coerce",
                )
                adjusted_value = pd.to_numeric(
                    getattr(bootstrap_row, f"managed_pct_{index}", 0.0),
                    errors="coerce",
                )
                if base_species == species_code and not pd.isna(base_value):
                    base_pct += float(base_value)
                if adjusted_species == species_code and not pd.isna(adjusted_value):
                    adjusted_pct += float(adjusted_value)
            payload[f"base_{code}_pct"] = base_pct
            payload[f"adjusted_{code}_pct"] = adjusted_pct
            payload[f"delta_{code}_pct"] = adjusted_pct - base_pct
            payload[f"base_{code}_sph"] = density_total * base_pct / 100.0
            payload[f"adjusted_{code}_sph"] = density_total * adjusted_pct / 100.0
            payload[f"delta_{code}_sph"] = density_total * (adjusted_pct - base_pct) / 100.0
        payload["base_pct_total"] = sum(
            float(payload[f"base_{species_code.lower()}_pct"])
            for species_code in species_codes
        )
        payload["adjusted_pct_total"] = sum(
            float(payload[f"adjusted_{species_code.lower()}_pct"])
            for species_code in species_codes
        )
        payload["base_sph_total"] = density_total * float(payload["base_pct_total"]) / 100.0
        payload["adjusted_sph_total"] = (
            density_total * float(payload["adjusted_pct_total"]) / 100.0
        )
        rows.append(payload)
    audit = pd.DataFrame(rows).sort_values("au_id", kind="stable")
    if audit.empty:
        return audit, pd.DataFrame(
            columns=[
                "managed_family_id",
                "au_count",
                "mean_hw_ingrowth_pct",
                "mean_base_hw_sph",
                "mean_adjusted_hw_sph",
                "mean_delta_hw_sph",
                "overflow_au_count",
            ]
        )
    summary = (
        audit.groupby("managed_family_id", as_index=False)
        .agg(
            au_count=("au_id", "nunique"),
            mean_hw_ingrowth_pct=("hw_ingrowth_pct", "mean"),
            mean_base_hw_sph=("base_hw_sph", "mean"),
            mean_adjusted_hw_sph=("adjusted_hw_sph", "mean"),
            mean_delta_hw_sph=("delta_hw_sph", "mean"),
            overflow_au_count=(
                "managed_species_overflow_to_hw_pct",
                lambda values: int((pd.to_numeric(values, errors="coerce").fillna(0.0) > 0).sum()),
            ),
        )
        .sort_values("managed_family_id", kind="stable")
    )
    return audit, summary


def _normalize_runtime_au_assignments(
    *,
    selected_au_table: pd.DataFrame,
    stand_origin_assignment: pd.DataFrame,
    managed_curves: pd.DataFrame,
    first_growth_diagnostics: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Normalize raw stand-origin AU assignments onto the canonical selected AU set."""
    selected = selected_au_table.copy()
    selected["au_id"] = selected["au_id"].astype(str).str.strip()
    selected_parts = selected["au_id"].map(_parse_mkrf_au_id)
    selected = selected.loc[selected_parts.notna()].copy()
    selected[["bec_zone", "bec_subzone", "bec_variant", "leading_species_1", "leading_species_2"]] = (
        pd.DataFrame(selected_parts.loc[selected.index].tolist(), index=selected.index)
    )
    if "selected_rank" in selected.columns:
        selected["selected_rank"] = pd.to_numeric(
            selected["selected_rank"], errors="coerce"
        ).fillna(10**9)
    else:
        selected["selected_rank"] = float(10**9)

    managed_ids = set(managed_curves["au_id"].astype(str).str.strip().unique())
    fg_paths = (
        first_growth_diagnostics[["au_id", "selected_path"]]
        .drop_duplicates(subset=["au_id"], keep="last")
        .assign(
            au_id=lambda df: df["au_id"].astype(str).str.strip(),
            selected_path=lambda df: df["selected_path"].astype(str).str.strip(),
        )
    )
    selected = selected.merge(fg_paths, on="au_id", how="left")
    selected["has_managed_curve"] = selected["au_id"].isin(managed_ids)
    selected["has_first_growth_curve"] = selected["selected_path"].notna() & (
        ~selected["selected_path"].eq("insufficient_source_stands")
    )
    selected["runtime_coverage_rank"] = np.where(
        selected["has_first_growth_curve"] & selected["has_managed_curve"],
        2,
        np.where(selected["has_managed_curve"], 1, 0),
    )

    selected_by_bec: dict[tuple[str, str, str], list[dict[str, object]]] = {}
    for row in selected.itertuples(index=False):
        key = (str(row.bec_zone), str(row.bec_subzone), str(row.bec_variant))
        selected_by_bec.setdefault(key, []).append(
            {
                "au_id": str(row.au_id),
                "leading_species_1": str(row.leading_species_1),
                "leading_species_2": str(row.leading_species_2),
                "runtime_coverage_rank": int(row.runtime_coverage_rank),
                "selected_rank": float(row.selected_rank),
            }
        )

    def choose_canonical_au(raw_au_id: str) -> tuple[str, str]:
        parsed = _parse_mkrf_au_id(raw_au_id)
        if parsed is None:
            return raw_au_id, "unparsed_raw_au_id"
        bec_zone, bec_subzone, bec_variant, raw_sp1, raw_sp2 = parsed
        candidates = selected_by_bec.get((bec_zone, bec_subzone, bec_variant), [])
        if not candidates:
            return raw_au_id, "no_selected_au_same_bec"

        def score(candidate: dict[str, object]) -> tuple[int, int, int, int, float, str]:
            cand_sp1 = str(candidate["leading_species_1"])
            cand_sp2 = str(candidate["leading_species_2"])
            overlap = len({raw_sp1, raw_sp2} & {cand_sp1, cand_sp2})
            return (
                int(cand_sp1 == raw_sp1),
                int(candidate["runtime_coverage_rank"]),
                int(cand_sp2 == raw_sp2),
                overlap,
                -float(candidate["selected_rank"]),
                str(candidate["au_id"]),
            )

        best = max(candidates, key=score)
        return str(best["au_id"]), "same_bec_species_coverage_rank"

    normalized = (
        stand_origin_assignment.copy()
        .assign(
            forest_cover_id=lambda df: pd.to_numeric(df["forest_cover_id"], errors="coerce"),
            raw_au_id=lambda df: df["au_id"].astype(str).str.strip(),
        )
        .dropna(subset=["forest_cover_id"])
        .loc[lambda df: df["raw_au_id"].ne("")]
    )
    normalized["au_id"] = normalized["raw_au_id"]
    normalized["remap_reason"] = "already_selected"
    selected_ids = set(selected["au_id"])
    remap_mask = ~normalized["raw_au_id"].isin(selected_ids)
    remap_targets = normalized.loc[remap_mask, "raw_au_id"].map(choose_canonical_au)
    normalized.loc[remap_mask, "au_id"] = remap_targets.map(lambda item: item[0])
    normalized.loc[remap_mask, "remap_reason"] = remap_targets.map(lambda item: item[1])
    normalized["was_remapped"] = normalized["raw_au_id"] != normalized["au_id"]

    remap_audit = (
        normalized.groupby(
            ["raw_au_id", "au_id", "was_remapped", "remap_reason"], dropna=False, as_index=False
        )
        .agg(
            forest_cover_id_count=("forest_cover_id", "nunique"),
            assignment_row_count=("forest_cover_id", "size"),
        )
        .sort_values(
            ["was_remapped", "forest_cover_id_count", "raw_au_id"],
            ascending=[False, False, True],
            kind="stable",
        )
        .reset_index(drop=True)
    )
    return normalized, remap_audit


def _apply_young_skewed_sibling_borrow(
    *,
    curves: pd.DataFrame,
    diagnostics: pd.DataFrame,
    assignment: pd.DataFrame,
    source_table: pd.DataFrame,
    min_first_growth_age: float = 80.0,
    max_old_support_count: int = 1,
    low_terminal_threshold: float = 100.0,
    sibling_terminal_threshold: float = 100.0,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Borrow a sane sibling curve for clearly too-young low-terminal cases."""
    if curves.empty or diagnostics.empty:
        return curves, diagnostics

    stand_assignment = collapse_stand_assignments(assignment)
    source_subset = source_table.copy()
    source_subset["forest_cover_id"] = pd.to_numeric(
        source_subset["FOREST_COVER_ID"], errors="coerce"
    )
    source_subset["AGE_2020"] = pd.to_numeric(source_subset["AGE_2020"], errors="coerce")
    age_rows = stand_assignment.merge(
        source_subset[["forest_cover_id", "AGE_2020"]],
        on="forest_cover_id",
        how="left",
    )
    old_support = (
        age_rows.groupby("au_id", as_index=False)["AGE_2020"]
        .apply(lambda s: int((pd.to_numeric(s, errors="coerce") >= min_first_growth_age).sum()))
        .rename(columns={"AGE_2020": "age_gte_80_count"})
    )

    terminal_curves = (
        curves.sort_values(["au_id", "age"], kind="stable")
        .groupby("au_id", as_index=False)
        .tail(1)[["au_id", "volume"]]
        .rename(columns={"volume": "terminal_volume"})
    )

    diagnostics_out = diagnostics.copy()
    for column in ["borrowed_from_au_id", "borrow_reason"]:
        if column not in diagnostics_out.columns:
            diagnostics_out[column] = ""

    summary = diagnostics_out.merge(old_support, on="au_id", how="left").merge(
        terminal_curves, on="au_id", how="left"
    )
    summary["age_gte_80_count"] = (
        pd.to_numeric(summary["age_gte_80_count"], errors="coerce").fillna(0).astype(int)
    )
    summary["terminal_volume"] = pd.to_numeric(summary["terminal_volume"], errors="coerce")

    curves_out = curves.copy()
    terminal_lookup = {
        str(row["au_id"]): float(row["terminal_volume"])
        for _, row in summary.dropna(subset=["terminal_volume"]).iterrows()
    }

    for _, row in summary.iterrows():
        au_id = str(row["au_id"])
        terminal_volume = pd.to_numeric(row["terminal_volume"], errors="coerce")
        if pd.isna(terminal_volume):
            continue
        if int(row["age_gte_80_count"]) > max_old_support_count:
            continue
        if float(terminal_volume) >= low_terminal_threshold:
            continue

        parsed = _parse_mkrf_au_id(au_id)
        if parsed is None:
            continue
        bec_zone, bec_subzone, bec_variant, sp1, sp2 = parsed
        sibling_au_id = f"{bec_zone}_{bec_subzone}_{bec_variant}_{sp2}_{sp1}"
        sibling_terminal = terminal_lookup.get(sibling_au_id)
        if sibling_terminal is None or sibling_terminal < sibling_terminal_threshold:
            continue

        sibling_curve = curves_out.loc[curves_out["au_id"] == sibling_au_id].copy()
        if sibling_curve.empty:
            continue
        curves_out = curves_out.loc[curves_out["au_id"] != au_id].copy()
        sibling_curve["au_id"] = au_id
        curves_out = pd.concat([curves_out, sibling_curve], ignore_index=True, sort=False)
        diagnostics_out.loc[diagnostics_out["au_id"] == au_id, "selected_path"] = (
            "borrowed_young_skewed_sibling"
        )
        diagnostics_out.loc[diagnostics_out["au_id"] == au_id, "borrowed_from_au_id"] = (
            sibling_au_id
        )
        diagnostics_out.loc[diagnostics_out["au_id"] == au_id, "borrow_reason"] = (
            f"old_support<={max_old_support_count}_and_terminal<{low_terminal_threshold:g}"
        )

    curves_out = curves_out.sort_values(["au_id", "age"], kind="stable").reset_index(drop=True)
    diagnostics_out = diagnostics_out.sort_values("au_id", kind="stable").reset_index(drop=True)
    return curves_out, diagnostics_out


def _apply_insufficient_support_merge(
    *,
    curves: pd.DataFrame,
    diagnostics: pd.DataFrame,
    assignment: pd.DataFrame,
    source_table: pd.DataFrame,
    min_first_growth_age: float = 80.0,
    min_source_stands: int = _MIN_FIRST_GROWTH_SOURCE_STANDS,
    min_donor_terminal_volume: float = 100.0,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Borrow a larger accepted curve from the same BEC bucket for sparse units.

    Old-support stand counts intentionally use fragment-level assignment rows so
    this helper stays aligned with the bad-curve audit surface.
    """
    if diagnostics.empty and curves.empty:
        return curves, diagnostics

    area_by_au = (
        assignment.groupby("au_id", as_index=False)["shape_area_ha"]
        .sum()
        .rename(columns={"shape_area_ha": "covered_area_ha"})
    )
    assignment_rows = assignment.copy()
    assignment_rows["forest_cover_id"] = pd.to_numeric(
        assignment_rows["forest_cover_id"], errors="coerce"
    )
    source_subset = source_table.copy()
    source_subset["forest_cover_id"] = pd.to_numeric(
        source_subset["FOREST_COVER_ID"], errors="coerce"
    )
    source_subset["AGE_2020"] = pd.to_numeric(source_subset["AGE_2020"], errors="coerce")
    age_rows = assignment_rows.merge(
        source_subset[["forest_cover_id", "AGE_2020"]],
        on="forest_cover_id",
        how="left",
    )
    old_support = (
        age_rows.loc[age_rows["AGE_2020"] >= min_first_growth_age]
        .groupby("au_id", as_index=False)["forest_cover_id"]
        .nunique()
        .rename(columns={"forest_cover_id": "old_support_stand_count"})
    )
    terminal_curves = (
        curves.sort_values(["au_id", "age"], kind="stable")
        .groupby("au_id", as_index=False)
        .tail(1)[["au_id", "volume"]]
        .rename(columns={"volume": "terminal_volume"})
    )

    diagnostics_out = diagnostics.copy()
    for column in ["borrowed_from_au_id", "borrow_reason"]:
        if column not in diagnostics_out.columns:
            diagnostics_out[column] = ""

    base_summary = (
        pd.DataFrame({"au_id": sorted(assignment["au_id"].astype(str).unique())})
        .merge(diagnostics_out, on="au_id", how="left")
        .merge(old_support, on="au_id", how="left")
    )
    summary = base_summary.merge(area_by_au, on="au_id", how="left").merge(
        terminal_curves, on="au_id", how="left"
    )
    summary["covered_area_ha"] = pd.to_numeric(summary["covered_area_ha"], errors="coerce").fillna(0.0)
    summary["terminal_volume"] = pd.to_numeric(summary["terminal_volume"], errors="coerce")
    summary["old_support_stand_count"] = (
        pd.to_numeric(summary["old_support_stand_count"], errors="coerce")
        .fillna(0)
        .astype(int)
    )
    summary["accepted"] = summary["accepted"].fillna(False)

    curves_out = curves.copy()
    for _, row in summary.sort_values(["covered_area_ha", "au_id"], ascending=[False, True]).iterrows():
        target_au_id = str(row["au_id"])
        target_selected_path = str(row.get("selected_path", ""))
        has_missing_curve = pd.isna(row.get("terminal_volume"))
        insufficient_support = 0 < int(row["old_support_stand_count"]) < int(min_source_stands)
        if not (
            target_selected_path == "insufficient_source_stands"
            or (has_missing_curve and insufficient_support)
        ):
            continue

        parsed_target = _parse_mkrf_au_id(target_au_id)
        if parsed_target is None:
            continue
        target_zone, target_subzone, target_variant, target_sp1, target_sp2 = parsed_target

        candidates: list[tuple[int, float, str]] = []
        for _, candidate in summary.iterrows():
            candidate_au_id = str(candidate["au_id"])
            if candidate_au_id == target_au_id:
                continue
            if not bool(candidate.get("accepted", False)):
                continue
            candidate_terminal = pd.to_numeric(candidate.get("terminal_volume"), errors="coerce")
            if (
                pd.isna(candidate_terminal)
                or float(candidate_terminal) <= 0.0
                or float(candidate_terminal) < float(min_donor_terminal_volume)
            ):
                continue
            parsed_candidate = _parse_mkrf_au_id(candidate_au_id)
            if parsed_candidate is None:
                continue
            cand_zone, cand_subzone, cand_variant, cand_sp1, cand_sp2 = parsed_candidate
            if (cand_zone, cand_subzone, cand_variant) != (
                target_zone,
                target_subzone,
                target_variant,
            ):
                continue
            shared_species = len({target_sp1, target_sp2} & {cand_sp1, cand_sp2})
            candidate_area = float(pd.to_numeric(candidate["covered_area_ha"], errors="coerce"))
            candidates.append((shared_species, candidate_area, candidate_au_id))

        if not candidates:
            continue

        _, _, source_au_id = max(candidates, key=lambda item: (item[0], item[1], item[2]))
        source_curve = curves_out.loc[curves_out["au_id"] == source_au_id].copy()
        if source_curve.empty:
            continue
        curves_out = curves_out.loc[curves_out["au_id"] != target_au_id].copy()
        source_curve["au_id"] = target_au_id
        curves_out = pd.concat([curves_out, source_curve], ignore_index=True, sort=False)
        target_mask = diagnostics_out["au_id"] == target_au_id
        if not target_mask.any():
            diagnostics_out = pd.concat(
                [
                    diagnostics_out,
                    pd.DataFrame(
                        [
                            {
                                "au_id": target_au_id,
                                "selected_path": "borrowed_insufficient_support_neighbor",
                                "accepted": True,
                                "borrowed_from_au_id": source_au_id,
                                "borrow_reason": "insufficient_source_stands_same_bec_largest_neighbor",
                                "source_stand_count": 0,
                            }
                        ]
                    ),
                ],
                ignore_index=True,
                sort=False,
            )
        else:
            diagnostics_out.loc[target_mask, "selected_path"] = (
                "borrowed_insufficient_support_neighbor"
            )
            diagnostics_out.loc[target_mask, "borrowed_from_au_id"] = source_au_id
            diagnostics_out.loc[target_mask, "borrow_reason"] = (
                "insufficient_source_stands_same_bec_largest_neighbor"
            )
            diagnostics_out.loc[target_mask, "accepted"] = True

    curves_out = curves_out.sort_values(["au_id", "age"], kind="stable").reset_index(drop=True)
    diagnostics_out = diagnostics_out.sort_values("au_id", kind="stable").reset_index(drop=True)
    return curves_out, diagnostics_out


@dataclass(frozen=True)
class MkrfAuPlotResult:
    """Result payload for MKRF AU distribution plot generation."""

    resultant_gdb: Path
    assignment_csv: Path
    output_dir: Path
    png_path: Path
    pdf_path: Path
    au_count: int
    point_count: int
    metadata: StrataDistributionPlotMetadata


@dataclass(frozen=True)
class MkrfSelectedAuBuildResult:
    """Result payload for MKRF top-N AU subset publication."""

    au_table_csv: Path
    assignment_csv: Path
    output_path: Path
    target_coverage: float
    selected_au_count: int
    total_au_count: int
    realized_coverage: float


@dataclass(frozen=True)
class MkrfPlotRebuildResult:
    """Result payload for MKRF diagnostic plot regeneration."""

    output_dir: Path
    strata_png: Path
    strata_pdf: Path
    lmh_plot_count: int
    fitdiag_plot_count: int
    tipsy_vdyp_plot_count: int


@dataclass(frozen=True)
class MkrfManagedAuBootstrapResult:
    """Result payload for MKRF managed AU bootstrap publication."""

    output_dir: Path
    stand_origin_assignment_path: Path
    bootstrap_table_path: Path
    msyt_path: Path
    selected_au_count: int
    included_au_count: int
    unmatched_au_count: int
    logging_origin_si_au_count: int
    all_stands_si_fallback_au_count: int


@dataclass(frozen=True)
class MkrfManagedAuCurvesResult:
    """Result payload for MKRF managed AU BTC attempt."""

    output_dir: Path
    manifest_path: Path
    curves_path: Path | None
    status: str
    included_au_count: int
    curve_au_count: int


@dataclass(frozen=True)
class MkrfBadCurveAuditResult:
    """Result payload for MKRF bad-curve audit publication."""

    output_dir: Path
    summary_path: Path
    detail_path: Path
    flagged_au_count: int
    total_selected_au_count: int


@dataclass(frozen=True)
class MkrfRuntimePackageInitResult:
    """Result payload for MKRF canonical runtime-package initialization."""

    package_root: Path
    readme_path: Path
    manifest_path: Path
    curve_status_path: Path
    analysis_au_runtime_status_path: Path
    analysis_au_curve_refs_path: Path
    runtime_au_remap_audit_path: Path
    species_share_audit_path: Path
    ct_eligibility_audit_path: Path
    ct_intensity_audit_path: Path
    ct_intensity_summary_path: Path
    hw_ingrowth_overlay_audit_path: Path
    hw_ingrowth_overlay_summary_path: Path
    analysis_pin_path: Path
    headless_runtime_common_path: Path
    flow_targets_script_path: Path
    xml_contract_path: Path
    xml_curve_bank_path: Path
    forestmodel_xml_path: Path
    selected_au_count: int
    first_growth_curve_au_count: int
    first_growth_missing_au_count: int
    managed_curve_au_count: int


@dataclass(frozen=True)
class MkrfRuntimeSanityAuditResult:
    """Result payload for MKRF canonical runtime-sanity auditing."""

    package_root: Path
    stage_dir: Path
    audit_csv_path: Path
    summary_json_path: Path
    row_count: int
    failure_count: int


@dataclass(frozen=True)
class MkrfRuntimeSpatialPublishResult:
    """Result payload for MKRF source-faithful runtime spatial publication."""

    package_root: Path
    spatial_dir: Path
    fragments_path: Path
    manifest_path: Path
    source_feature_count: int
    published_feature_count: int
    excluded_feature_count: int


def _manifest_path_value(path: Path | str | None) -> str | None:
    if path is None:
        return None
    candidate = Path(path)
    try:
        return os.path.relpath(candidate.resolve(), Path.cwd().resolve()).replace("\\", "/")
    except Exception:
        return candidate.name


_MKRF_RUNTIME_FRAGMENT_FIELD_MAP: tuple[tuple[str, str], ...] = (
    ("FOREST_COVER_ID", "FOREST_COV"),
    ("Operability", "Operabilit"),
    ("Shape_Length", "Shape_Leng"),
    ("Shape_Area", "Shape_Area"),
    ("CONTCLAS", "CONTCLAS"),
    ("AGE_2020", "AGE_2020"),
    ("AU_EX", "AU_EX"),
    ("AU_FU", "AU_FU"),
    ("RES_KEY", "RES_KEY"),
    ("CT_eligib", "CT_eligib"),
)


def _project_mkrf_runtime_fragments(*, source_gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Project MKRF Resultant rows into the recovered runtime fragments field surface."""
    missing = sorted(
        source_name
        for source_name, _target_name in _MKRF_RUNTIME_FRAGMENT_FIELD_MAP
        if source_name not in source_gdf.columns
    )
    if missing:
        raise ValueError(
            "Resultant layer missing required MKRF runtime fragment columns: "
            + ", ".join(missing)
        )

    filtered = source_gdf.loc[source_gdf["CONTCLAS"].astype(str) != "X"].copy()
    projected = gpd.GeoDataFrame(
        {
            target_name: filtered[source_name]
            for source_name, target_name in _MKRF_RUNTIME_FRAGMENT_FIELD_MAP
        },
        geometry=filtered.geometry,
        crs=source_gdf.crs,
    )
    return projected


def build_mkrf_au_input_bundle(
    *,
    resultant_gdb: Path,
    output_dir: Path,
    layer: str = "Resultant",
) -> MkrfAuBuildResult:
    """Materialize MKRF AU and stand-assignment inputs from Resultant.gdb."""
    output_dir.mkdir(parents=True, exist_ok=True)
    source_table = gpd.read_file(resultant_gdb, layer=layer, ignore_geometry=True)
    au_table, assignment = build_mkrf_au_tables(source_table)

    au_table_path = output_dir / "au_table.csv"
    stand_assignment_path = output_dir / "stand_au_assignment.csv"
    au_table.to_csv(au_table_path, index=False)
    assignment.to_csv(stand_assignment_path, index=False)

    return MkrfAuBuildResult(
        resultant_gdb=resultant_gdb,
        output_dir=output_dir,
        au_table_path=au_table_path,
        stand_assignment_path=stand_assignment_path,
        source_row_count=len(assignment),
        au_count=len(au_table),
    )


def publish_mkrf_runtime_spatial_handoff(
    *,
    resultant_gdb: Path,
    package_root: Path,
    layer: str = "Resultant",
) -> MkrfRuntimeSpatialPublishResult:
    """Publish MKRF source-faithful runtime fragments from Resultant.gdb."""
    package_root = package_root.resolve()
    spatial_dir = package_root / "spatial"
    spatial_dir.mkdir(parents=True, exist_ok=True)
    fragments_path = spatial_dir / "fragments.shp"
    manifest_path = spatial_dir / "runtime_spatial_manifest.json"

    source_gdf = gpd.read_file(resultant_gdb, layer=layer)
    source_feature_count = int(len(source_gdf))
    published_gdf = _project_mkrf_runtime_fragments(source_gdf=source_gdf)
    published_feature_count = int(len(published_gdf))
    excluded_feature_count = int(source_feature_count - published_feature_count)

    published_gdf.to_file(fragments_path)

    excluded_rows = source_gdf.loc[source_gdf["CONTCLAS"].astype(str) == "X"].copy()
    excluded_reason_counts = (
        excluded_rows["CONTCLAS"].astype(str).value_counts(dropna=False).to_dict()
        if not excluded_rows.empty
        else {}
    )
    manifest_payload = {
        "schema_version": 1,
        "source_layer": layer,
        "source_resultant_gdb": str(resultant_gdb.resolve()),
        "publication_rule": "CONTCLAS != 'X'",
        "field_projection": [
            {"source": source_name, "target": target_name}
            for source_name, target_name in _MKRF_RUNTIME_FRAGMENT_FIELD_MAP
        ],
        "package_root": str(package_root),
        "fragments_path": str(fragments_path.resolve()),
        "source_feature_count": source_feature_count,
        "published_feature_count": published_feature_count,
        "excluded_feature_count": excluded_feature_count,
        "excluded_reason_counts": excluded_reason_counts,
    }
    manifest_path.write_text(
        json.dumps(manifest_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    return MkrfRuntimeSpatialPublishResult(
        package_root=package_root,
        spatial_dir=spatial_dir,
        fragments_path=fragments_path,
        manifest_path=manifest_path,
        source_feature_count=source_feature_count,
        published_feature_count=published_feature_count,
        excluded_feature_count=excluded_feature_count,
    )


def build_mkrf_first_growth_input_bundle(
    *,
    vdyp_yields_csv: Path,
    assignment_csv: Path,
    output_dir: Path,
    resultant_gdb: Path,
    layer: str = "Resultant",
) -> MkrfFirstGrowthBuildResult:
    """Materialize MKRF AU-wise first-growth curves from VDYP stand evidence."""
    output_dir.mkdir(parents=True, exist_ok=True)
    vdyp_yields = pd.read_csv(vdyp_yields_csv)
    assignment = pd.read_csv(assignment_csv)
    source_table = gpd.read_file(resultant_gdb, layer=layer, ignore_geometry=True)
    curves, diagnostics = build_mkrf_first_growth_curves(
        vdyp_yields=vdyp_yields,
        assignment=assignment,
        source_table=source_table,
    )

    curves_path = output_dir / "first_growth_au_curves.csv"
    diagnostics_path = output_dir / "first_growth_au_fit_diagnostics.csv"
    curves.to_csv(curves_path, index=False)
    diagnostics.to_csv(diagnostics_path, index=False)
    vdyp_feature_ids = _resolve_eligible_first_growth_feature_ids(
        vdyp_yields=vdyp_yields,
        source_table=source_table,
        min_first_growth_age=80.0,
    )
    assigned_feature_ids = set(
        pd.to_numeric(assignment["forest_cover_id"], errors="coerce")
        .dropna()
        .astype(int)
    )
    raw_unmatched_feature_ids = vdyp_feature_ids - assigned_feature_ids
    source_feature_ids = set(
        pd.to_numeric(source_table["FOREST_COVER_ID"], errors="coerce")
        .dropna()
        .astype(int)
    )
    residual_unmatched_feature_ids = raw_unmatched_feature_ids - source_feature_ids

    return MkrfFirstGrowthBuildResult(
        vdyp_yields_csv=vdyp_yields_csv,
        assignment_csv=assignment_csv,
        output_dir=output_dir,
        curves_path=curves_path,
        diagnostics_path=diagnostics_path,
        au_count=int(diagnostics["au_id"].nunique()),
        assigned_stand_count=int(diagnostics["source_stand_count"].sum()),
        raw_unmatched_source_stand_count=int(len(raw_unmatched_feature_ids)),
        residual_unmatched_source_stand_count=int(len(residual_unmatched_feature_ids)),
        lexmatch_assigned_stand_count=int(diagnostics["lexmatch_stand_count"].sum()),
    )


def _format_mkrf_au_label(au_id: str) -> str:
    parts = str(au_id).split("_")
    if len(parts) != 5:
        return str(au_id).upper()
    bec_zone, bec_subzone, bec_variant, sp1, sp2 = parts
    bec = f"{bec_zone.upper()}{bec_subzone}{bec_variant}"
    return f"{bec}_{sp1.upper()}+{sp2.upper()}"


def build_mkrf_au_distribution_plot(
    *,
    resultant_gdb: Path,
    assignment_csv: Path,
    selected_au_csv: Path | None = None,
    output_dir: Path,
    layer: str = "Resultant",
    tsa_code: str = "mkrf",
) -> MkrfAuPlotResult:
    """Render the MKRF AU abundance/site-index distribution plot."""
    import matplotlib.pyplot as plt
    import seaborn as sns

    output_dir.mkdir(parents=True, exist_ok=True)
    assignment = pd.read_csv(assignment_csv)
    if selected_au_csv is not None:
        selected_au_table = pd.read_csv(selected_au_csv)
        assignment = _filter_assignment_to_selected_aus(
            assignment,
            selected_au_table,
        )
    source_table = gpd.read_file(resultant_gdb, layer=layer, ignore_geometry=True)
    source_subset = source_table[["RES_KEY", "TCL_1_ESTIMATED_SITE_INDEX"]].copy()
    source_subset = source_subset.rename(
        columns={
            "RES_KEY": "res_key",
            "TCL_1_ESTIMATED_SITE_INDEX": "SITE_INDEX",
        }
    )
    plot_frame = assignment.merge(source_subset, on="res_key", how="left")
    plot_frame["SITE_INDEX"] = pd.to_numeric(plot_frame["SITE_INDEX"], errors="coerce")

    abundance = (
        assignment.groupby("au_id", as_index=True)["shape_area_ha"]
        .sum()
        .sort_values(ascending=False)
    )
    strata_df = pd.DataFrame(
        {
            "totalarea_p": abundance / float(abundance.sum()),
            "site_index_median": plot_frame.groupby("au_id")["SITE_INDEX"]
            .median()
            .reindex(abundance.index),
        }
    )

    stratum_props, labels_raw = resolve_strata_plot_ordering(
        strata_df=strata_df,
        sort_lex=False,
    )
    label_map = {label: _format_mkrf_au_label(label) for label in labels_raw}
    labels = [label_map[label] for label in labels_raw]
    plot_frame["au_label"] = plot_frame["au_id"].map(label_map)

    plot_config = build_strata_distribution_plot_config(
        site_index_xlim=(0, 50),
        write_pdf=True,
    )
    metadata = render_strata_distribution_plot(
        tsa_code=tsa_code,
        f_table=plot_frame[["au_label", "SITE_INDEX"]].rename(
            columns={"au_label": "au_id"}
        ),
        stratum_col="au_id",
        labels=labels,
        stratum_props=stratum_props,
        plot_config=plot_config,
        sns_module=sns,
        plt_module=plt,
        strata_plot_paths_fn=lambda _tsa: strata_plot_paths(_tsa, root=output_dir),
    )
    pdf_path, png_path = strata_plot_paths(tsa_code, root=output_dir)
    plt.close("all")
    return MkrfAuPlotResult(
        resultant_gdb=resultant_gdb,
        assignment_csv=assignment_csv,
        output_dir=output_dir,
        png_path=png_path,
        pdf_path=pdf_path,
        au_count=int(assignment["au_id"].nunique()),
        point_count=int(plot_frame["SITE_INDEX"].notna().sum()),
        metadata=metadata,
    )


def _build_selected_au_label_map(selected_au_table: pd.DataFrame) -> dict[str, str]:
    ordered = selected_au_table.sort_values(["selected_rank", "au_id"], kind="stable")
    labels: dict[str, str] = {}
    for _, row in ordered.iterrows():
        au_id = str(row["au_id"])
        rank = int(row["selected_rank"]) - 1
        labels[au_id] = f"{rank:02d}-{_format_mkrf_au_label(au_id)}"
    return labels


def _filter_assignment_to_selected_aus(
    assignment: pd.DataFrame,
    selected_au_table: pd.DataFrame,
) -> pd.DataFrame:
    selected_ids = set(selected_au_table["au_id"].astype(str))
    return assignment.loc[
        assignment["au_id"].astype(str).isin(selected_ids)
    ].copy()


def _classify_site_index_levels(site_index: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(site_index, errors="coerce")
    valid = numeric.dropna()
    if valid.empty:
        return pd.Series(index=site_index.index, dtype="object")
    if len(valid) == 1 or valid.nunique() == 1:
        labeled = pd.Series("M", index=valid.index, dtype="object")
    else:
        quantile_count = min(3, int(valid.nunique()))
        labels = ["M"] if quantile_count == 1 else (
            ["L", "H"] if quantile_count == 2 else ["L", "M", "H"]
        )
        ranked = valid.rank(method="first")
        labeled = pd.qcut(ranked, q=quantile_count, labels=labels).astype("object")
    return labeled.reindex(site_index.index)


def _extract_feature_curve_tables(vdyp_rows: pd.DataFrame) -> dict[int, pd.DataFrame]:
    tables: dict[int, pd.DataFrame] = {}
    for feature_id, feature_rows in vdyp_rows.groupby("FEATURE_ID", sort=True):
        ordered = feature_rows.sort_values("PRJ_TOTAL_AGE", kind="stable").rename(
            columns={"PRJ_TOTAL_AGE": "Age", "PRJ_VOL_DWB": "Vdwb"}
        )
        tables[int(feature_id)] = ordered[["Age", "Vdwb"]].set_index("Age")
    return tables


def _build_fitdiag_summary(raw_subset: pd.DataFrame) -> pd.DataFrame:
    table = raw_subset.rename(
        columns={"PRJ_TOTAL_AGE": "Age", "PRJ_VOL_DWB": "Vdwb"}
    ).copy()
    table["Age"] = pd.to_numeric(table["Age"], errors="coerce")
    table["Vdwb"] = pd.to_numeric(table["Vdwb"], errors="coerce")
    table = table.dropna(subset=["Age", "Vdwb"])
    table = table.loc[(table["Age"] >= 30) & (table["Age"] <= 350) & (table["Vdwb"] >= 0)]
    if table.empty:
        return pd.DataFrame(columns=["age_bin", "median_volume", "p25", "p75"])
    table["age_bin"] = (np.floor(table["Age"] / 5.0) * 5.0).astype(float)
    return (
        table.groupby("age_bin", as_index=False)
        .agg(
            median_volume=("Vdwb", "median"),
            p25=("Vdwb", lambda s: float(s.quantile(0.25))),
            p75=("Vdwb", lambda s: float(s.quantile(0.75))),
        )
        .sort_values("age_bin", kind="stable")
        .reset_index(drop=True)
    )


def _fitdiag_plot_path(*, output_dir: Path, tsa_code: str, au_label: str, level: str) -> Path:
    tsa = str(tsa_code).zfill(2)
    return output_dir / f"vdyp_fitdiag_tsa{tsa}-{au_label}-{level}.png"


def _lmh_plot_path(*, output_dir: Path, tsa_code: str, au_label: str) -> Path:
    tsa = str(tsa_code).zfill(2)
    return output_dir / f"vdyp_lmh_tsa{tsa}-{au_label}.png"


def _tipsy_vdyp_plot_path(*, output_dir: Path, tsa_code: str, au_label: str) -> Path:
    tsa = str(tsa_code).zfill(2)
    return output_dir / f"tipsy_vdyp_tsa{tsa}-{au_label}.png"


def build_mkrf_selected_au_input_bundle(
    *,
    au_table_csv: Path,
    assignment_csv: Path,
    output_path: Path,
    target_coverage: float = 0.95,
) -> MkrfSelectedAuBuildResult:
    """Publish the canonical top-N AU subset by cumulative covered-area share."""
    au_table = pd.read_csv(au_table_csv)
    assignment = pd.read_csv(assignment_csv)
    selected = build_mkrf_selected_au_table(
        au_table=au_table,
        assignment=assignment,
        target_coverage=target_coverage,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    selected.to_csv(output_path, index=False)
    realized_coverage = (
        float(selected["cumulative_covered_area_share"].iloc[-1])
        if not selected.empty
        else 0.0
    )
    return MkrfSelectedAuBuildResult(
        au_table_csv=au_table_csv,
        assignment_csv=assignment_csv,
        output_path=output_path,
        target_coverage=float(target_coverage),
        selected_au_count=int(len(selected)),
        total_au_count=int(len(au_table)),
        realized_coverage=realized_coverage,
    )


def build_mkrf_managed_au_input_bundle(
    *,
    resultant_gdb: Path,
    selected_au_csv: Path,
    assignment_csv: Path,
    tipsy_rules_yaml: Path,
    output_dir: Path,
    layer: str = "Resultant",
) -> MkrfManagedAuBootstrapResult:
    """Build the expert-rule managed AU bootstrap and BTC MSYT input tables."""
    output_dir.mkdir(parents=True, exist_ok=True)
    selected_au_table = pd.read_csv(selected_au_csv)
    assignment = pd.read_csv(assignment_csv)
    source_table = gpd.read_file(resultant_gdb, layer=layer, ignore_geometry=True)
    rule_config = load_mkrf_managed_rule_config(tipsy_rules_yaml)
    stand_origin_assignment = build_mkrf_stand_origin_assignment(
        assignment=assignment,
        source_table=source_table,
        fire_origin_min_age=rule_config.fire_origin_min_age,
    )
    stand_origin_assignment_path = output_dir / "stand_origin_assignment.csv"
    stand_origin_assignment.to_csv(stand_origin_assignment_path, index=False)

    bootstrap_table = build_mkrf_managed_au_bootstrap_table(
        selected_au_table=selected_au_table,
        stand_origin_assignment=stand_origin_assignment,
        rule_config=rule_config,
    )
    bootstrap_path = output_dir / "managed_au_bootstrap_table.csv"
    bootstrap_table.to_csv(bootstrap_path, index=False)

    msyt_table = build_mkrf_managed_au_msyt_table(bootstrap_table=bootstrap_table)
    msyt_path = output_dir / "managed_au_msyt.csv"
    msyt_table.to_csv(msyt_path, index=False)

    included = bootstrap_table["included_in_msyt"].fillna(False)
    return MkrfManagedAuBootstrapResult(
        output_dir=output_dir,
        stand_origin_assignment_path=stand_origin_assignment_path,
        bootstrap_table_path=bootstrap_path,
        msyt_path=msyt_path,
        selected_au_count=int(len(selected_au_table)),
        included_au_count=int(included.sum()),
        unmatched_au_count=int((bootstrap_table["bootstrap_status"] == "unmatched").sum()),
        logging_origin_si_au_count=int(
            (bootstrap_table["managed_si_source"] == "logging_origin_median").sum()
        ),
        all_stands_si_fallback_au_count=int(
            (bootstrap_table["managed_si_source"] == "all_stands_median").sum()
        ),
    )


def build_mkrf_managed_au_curves(
    *,
    bootstrap_csv: Path,
    msyt_csv: Path,
    output_dir: Path,
    log_dir: Path,
    run_id: str = "mkrf_managed_au_curves",
    executable_path: Path | None = None,
) -> MkrfManagedAuCurvesResult:
    """Attempt a BTC compile for the provisional managed AU lane."""
    output_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)
    bootstrap_table = pd.read_csv(bootstrap_csv)
    manifest_path = output_dir / "managed_au_run_manifest.json"
    included_count = int(
        bootstrap_table["included_in_msyt"].fillna(False).sum()
    )
    try:
        btc_result = run_btc_cli(
            input_csv=msyt_csv,
            mode="TSR",
            executable_path=executable_path,
            report_preset_name="tsr-unattended-default",
            log_dir=log_dir,
            run_id=run_id,
        )
    except FileNotFoundError as exc:
        write_mkrf_managed_run_manifest(
            manifest_path=manifest_path,
            payload={
                "status": "blocked",
                "reason": "missing_btc_runtime",
                "message": str(exc),
                "msyt_csv": _manifest_path_value(msyt_csv),
                "bootstrap_csv": _manifest_path_value(bootstrap_csv),
                "included_au_count": included_count,
            },
        )
        return MkrfManagedAuCurvesResult(
            output_dir=output_dir,
            manifest_path=manifest_path,
            curves_path=None,
            status="blocked",
            included_au_count=included_count,
            curve_au_count=0,
        )

    curves = parse_mkrf_managed_au_curves(
        output_csv=btc_result.output_csv_path,
        bootstrap_table=bootstrap_table,
    )
    curves_path = output_dir / "managed_au_curves.csv"
    curves.to_csv(curves_path, index=False)
    write_mkrf_managed_run_manifest(
        manifest_path=manifest_path,
        payload={
            "status": "completed",
            "msyt_csv": _manifest_path_value(msyt_csv),
            "bootstrap_csv": _manifest_path_value(bootstrap_csv),
            "curves_csv": _manifest_path_value(curves_path),
            "included_au_count": included_count,
            "curve_au_count": int(curves["au_id"].nunique()),
            "btc_manifest_path": _manifest_path_value(btc_result.manifest_path),
            "btc_stdout_log_path": _manifest_path_value(btc_result.stdout_log_path),
            "btc_stderr_log_path": _manifest_path_value(btc_result.stderr_log_path),
            "btc_output_csv_path": _manifest_path_value(btc_result.output_csv_path),
            "btc_error_csv_path": _manifest_path_value(btc_result.error_csv_path),
        },
    )
    return MkrfManagedAuCurvesResult(
        output_dir=output_dir,
        manifest_path=manifest_path,
        curves_path=curves_path,
        status="completed",
        included_au_count=included_count,
        curve_au_count=int(curves["au_id"].nunique()),
    )


def build_mkrf_all_plots(
    *,
    resultant_gdb: Path,
    assignment_csv: Path,
    selected_au_csv: Path,
    first_growth_curves_csv: Path,
    vdyp_yields_csv: Path,
    managed_curves_csv: Path,
    output_dir: Path,
    layer: str = "Resultant",
    tsa_code: str = "mkrf",
) -> MkrfPlotRebuildResult:
    """Recompile MKRF diagnostic and comparison plots for the selected AU subset."""
    import matplotlib.pyplot as plt

    output_dir.mkdir(parents=True, exist_ok=True)
    for pattern in (
        "strata-tsa*.png",
        "strata-tsa*.pdf",
        "vdyp_lmh_tsa*.png",
        "vdyp_fitdiag_tsa*.png",
        "tipsy_vdyp_tsa*.png",
    ):
        for path in output_dir.glob(pattern):
            path.unlink()
    strata = build_mkrf_au_distribution_plot(
        resultant_gdb=resultant_gdb,
        assignment_csv=assignment_csv,
        selected_au_csv=selected_au_csv,
        output_dir=output_dir,
        layer=layer,
        tsa_code=tsa_code,
    )

    assignment = pd.read_csv(assignment_csv)
    selected_au_table = pd.read_csv(selected_au_csv)
    first_growth_curves = pd.read_csv(first_growth_curves_csv)
    managed_curves = pd.read_csv(managed_curves_csv)
    vdyp_yields = pd.read_csv(vdyp_yields_csv)
    source_table = gpd.read_file(resultant_gdb, layer=layer, ignore_geometry=True)

    selected_ids = list(
        selected_au_table.sort_values(["selected_rank", "au_id"], kind="stable")["au_id"]
    )
    label_map = _build_selected_au_label_map(selected_au_table)

    stand_assignment = collapse_stand_assignments(assignment).rename(
        columns={"dominant_weight": "shape_area_ha"}
    )
    stand_assignment = stand_assignment.merge(
        source_table[["FOREST_COVER_ID", "TCL_1_ESTIMATED_SITE_INDEX"]]
        .drop_duplicates("FOREST_COVER_ID")
        .rename(
            columns={
                "FOREST_COVER_ID": "forest_cover_id",
                "TCL_1_ESTIMATED_SITE_INDEX": "site_index",
            }
        ),
        on="forest_cover_id",
        how="left",
    )
    stand_assignment["site_index"] = pd.to_numeric(
        stand_assignment["site_index"], errors="coerce"
    )
    stand_assignment = stand_assignment.loc[
        stand_assignment["au_id"].isin(selected_ids)
    ].copy()

    level_assignment_rows: list[dict[str, object]] = []
    stand_level_map: dict[tuple[str, str], list[int]] = {}
    canonical_median_si: dict[str, float] = {}
    for au_id, au_rows in stand_assignment.groupby("au_id", sort=True):
        level_series = _classify_site_index_levels(au_rows["site_index"])
        au_rows = au_rows.assign(si_level=level_series.values)
        canonical_median_si[str(au_id)] = float(au_rows["site_index"].median())
        for level, level_rows in au_rows.dropna(subset=["si_level"]).groupby(
            "si_level", sort=True
        ):
            temp_au_id = f"{au_id}__{level}"
            stand_level_map[(str(au_id), str(level))] = [
                int(v) for v in level_rows["forest_cover_id"].tolist()
            ]
            for _, row in level_rows.iterrows():
                level_assignment_rows.append(
                    {
                        "res_key": int(row["forest_cover_id"]),
                        "forest_cover_id": int(row["forest_cover_id"]),
                        "shape_area_ha": float(row["shape_area_ha"]),
                        "au_id": temp_au_id,
                    }
                )

    lmh_curves = pd.DataFrame(columns=["au_id", "age", "volume"])
    lmh_diagnostics = pd.DataFrame(columns=["au_id", "rmse", "mape", "tail_rmse"])
    eligible_first_growth_feature_ids = _resolve_eligible_first_growth_feature_ids(
        vdyp_yields=vdyp_yields,
        source_table=source_table,
        min_first_growth_age=80.0,
    )
    if level_assignment_rows:
        level_assignment = pd.DataFrame(level_assignment_rows)
        lmh_curves, lmh_diagnostics = build_mkrf_first_growth_curves(
            vdyp_yields=vdyp_yields.loc[
                vdyp_yields["FEATURE_ID"].isin(level_assignment["forest_cover_id"])
            ].copy(),
            assignment=level_assignment,
            source_table=source_table,
        )

    lmh_plot_count = 0
    fitdiag_plot_count = 0
    for au_id in selected_ids:
        label = label_map[str(au_id)]
        au_curves = lmh_curves.loc[
            lmh_curves["au_id"].astype(str).str.startswith(f"{au_id}__")
        ].copy()
        if au_curves.empty:
            continue

        fig, ax = plt.subplots(1, 1, figsize=(8, 5))
        ymax = 1.0
        plotted = False
        for level, color in (("L", "tab:blue"), ("M", "tab:green"), ("H", "tab:red")):
            temp_au_id = f"{au_id}__{level}"
            curve = au_curves.loc[au_curves["au_id"] == temp_au_id]
            if curve.empty:
                continue
            plotted = True
            ax.plot(curve["age"], curve["volume"], linewidth=2.0, color=color, label=level)
            ymax = max(ymax, float(curve["volume"].max()))
        if plotted:
            ax.set_title(f"VDYP L/M/H Comparison: {label}")
            ax.set_xlabel("Age")
            ax.set_ylabel("Volume (m3/ha)")
            ax.set_xlim(0, 300)
            ax.set_ylim(0, ymax * 1.05)
            ax.grid(alpha=0.25)
            ax.legend(fontsize=8)
            fig.tight_layout()
            fig.savefig(
                _lmh_plot_path(output_dir=output_dir, tsa_code=tsa_code, au_label=label),
                dpi=150,
            )
            lmh_plot_count += 1
        plt.close(fig)

        for level in ("L", "M", "H"):
            temp_au_id = f"{au_id}__{level}"
            curve = au_curves.loc[au_curves["au_id"] == temp_au_id]
            if curve.empty:
                continue
            stand_ids = [
                stand_id
                for stand_id in stand_level_map.get((str(au_id), level), [])
                if stand_id in eligible_first_growth_feature_ids
            ]
            if not stand_ids:
                continue
            raw_subset = vdyp_yields.loc[vdyp_yields["FEATURE_ID"].isin(stand_ids)].copy()
            feature_tables = _extract_feature_curve_tables(raw_subset)
            if not feature_tables:
                continue
            observed = _build_fitdiag_summary(raw_subset)
            diag_matches = lmh_diagnostics.loc[lmh_diagnostics["au_id"] == temp_au_id]
            if diag_matches.empty:
                continue
            diag_row = diag_matches.iloc[0]
            fig, (ax, ax_resid) = plt.subplots(
                2,
                1,
                figsize=(8, 8),
                sharex=True,
                gridspec_kw={"height_ratios": [3, 1]},
            )
            raw_label_used = False
            for table in feature_tables.values():
                raw = table.reset_index().dropna()
                raw = raw.loc[(raw["Age"] >= 0) & (raw["Age"] <= 350) & (raw["Vdwb"] >= 0)]
                if raw.empty:
                    continue
                ax.plot(
                    raw["Age"],
                    raw["Vdwb"],
                    color="0.5",
                    alpha=0.08,
                    linewidth=0.4,
                    label="Raw VDYP curves" if not raw_label_used else None,
                    zorder=1,
                )
                raw_label_used = True
            if not observed.empty:
                ax.fill_between(
                    observed["age_bin"],
                    observed["p25"],
                    observed["p75"],
                    color="lightblue",
                    alpha=0.35,
                    label="Observed P25-P75 (5y bins)",
                )
                ax.scatter(
                    observed["age_bin"],
                    observed["median_volume"],
                    s=14,
                    color="tab:blue",
                    label="Observed median (5y bins)",
                )
            ax.plot(curve["age"], curve["volume"], color="black", linewidth=2.2, label="Selected fit")
            ax.set_title(f"VDYP Fit Diagnostic: {label} {level}")
            ax.set_xlabel("Age")
            ax.set_ylabel("Volume (m3/ha)")
            ax.set_xlim(0, 300)
            ymax = max(
                float(curve["volume"].max()) * 1.05,
                float(observed["p75"].max()) * 1.15 if not observed.empty else 1.0,
                1.0,
            )
            ax.set_ylim(0, ymax)
            ax.grid(alpha=0.25)
            ax.legend(fontsize=8)
            ax.text(
                0.01,
                0.99,
                "\n".join(
                    [
                        f"rmse={float(diag_row['rmse']):.1f}",
                        f"mape={float(diag_row['mape']):.3f}",
                        f"tail_rmse={float(diag_row['tail_rmse']):.1f}",
                        f"stands={int(diag_row['source_stand_count'])}",
                    ]
                ),
                transform=ax.transAxes,
                ha="left",
                va="top",
                fontsize=7,
                bbox={"facecolor": "white", "alpha": 0.75, "edgecolor": "none"},
            )
            if not observed.empty:
                predicted = np.interp(
                    observed["age_bin"].to_numpy(dtype=float),
                    curve["age"].to_numpy(dtype=float),
                    curve["volume"].to_numpy(dtype=float),
                )
                residual = predicted - observed["median_volume"].to_numpy(dtype=float)
                ax_resid.axhline(0.0, color="black", linewidth=1.0, alpha=0.6)
                ax_resid.scatter(
                    observed["age_bin"],
                    residual,
                    s=14,
                    color="tab:gray",
                    alpha=0.8,
                )
                ax_resid.plot(
                    observed["age_bin"],
                    residual,
                    color="tab:gray",
                    linewidth=1.2,
                    alpha=0.7,
                )
            ax_resid.set_ylabel("Residual")
            ax_resid.set_xlabel("Age")
            ax_resid.grid(alpha=0.25)
            fig.tight_layout()
            fig.savefig(
                _fitdiag_plot_path(
                    output_dir=output_dir,
                    tsa_code=tsa_code,
                    au_label=label,
                    level=level,
                ),
                dpi=150,
            )
            fitdiag_plot_count += 1
            plt.close(fig)

    tipsy_vdyp_plot_count = 0
    for au_id in selected_ids:
        label = label_map[str(au_id)]
        tipsy_curve = managed_curves.loc[managed_curves["au_id"] == str(au_id)].copy()
        vdyp_curve = first_growth_curves.loc[first_growth_curves["au_id"] == str(au_id)].copy()
        if tipsy_curve.empty or vdyp_curve.empty:
            continue
        fig, ax = plt.subplots(1, 1, figsize=(8, 6))
        ax.plot(
            vdyp_curve["age"],
            vdyp_curve["volume"],
            color="black",
            linewidth=2.0,
            label="VDYP first-growth",
        )
        ax.plot(
            pd.to_numeric(tipsy_curve["age"], errors="coerce"),
            pd.to_numeric(tipsy_curve["volume"], errors="coerce"),
            color="tab:green",
            linewidth=2.0,
            linestyle="--",
            label="TIPSY managed",
        )
        ymax = max(
            float(vdyp_curve["volume"].max()),
            float(pd.to_numeric(tipsy_curve["volume"], errors="coerce").max()),
            1.0,
        )
        ax.set_title(f"TIPSY vs VDYP: {label}")
        ax.set_xlabel("Age")
        ax.set_ylabel("Yield (m3/ha)")
        ax.set_xlim(0, 300)
        ax.set_ylim(0, ymax * 1.05)
        ax.grid(alpha=0.25)
        ax.legend(fontsize=8)
        fig.tight_layout()
        fig.savefig(
            _tipsy_vdyp_plot_path(output_dir=output_dir, tsa_code=tsa_code, au_label=label),
            dpi=150,
        )
        tipsy_vdyp_plot_count += 1
        plt.close(fig)

    return MkrfPlotRebuildResult(
        output_dir=output_dir,
        strata_png=strata.png_path,
        strata_pdf=strata.pdf_path,
        lmh_plot_count=lmh_plot_count,
        fitdiag_plot_count=fitdiag_plot_count,
        tipsy_vdyp_plot_count=tipsy_vdyp_plot_count,
    )


def build_mkrf_bad_curve_audit(
    *,
    resultant_gdb: Path,
    assignment_csv: Path,
    selected_au_csv: Path,
    first_growth_curves_csv: Path,
    vdyp_yields_csv: Path,
    output_dir: Path,
    layer: str = "Resultant",
    low_terminal_threshold: float = 100.0,
    large_area_threshold: float = 50.0,
    low_large_area_threshold: float = 200.0,
    low_terminal_stand_threshold: float = 20.0,
    high_terminal_stand_threshold: float = 300.0,
) -> MkrfBadCurveAuditResult:
    """Audit bad first-growth curve cases against source-stand evidence."""
    output_dir.mkdir(parents=True, exist_ok=True)

    assignment = pd.read_csv(assignment_csv)
    selected_au_table = pd.read_csv(selected_au_csv)
    first_growth_curves = pd.read_csv(first_growth_curves_csv)
    vdyp_yields = pd.read_csv(vdyp_yields_csv)
    source_table = gpd.read_file(resultant_gdb, layer=layer, ignore_geometry=True)

    terminal_curves = (
        first_growth_curves.sort_values(["au_id", "age"], kind="stable")
        .groupby("au_id", as_index=False)
        .tail(1)[["au_id", "age", "volume"]]
        .rename(columns={"age": "terminal_age", "volume": "terminal_volume"})
    )
    selected = selected_au_table.merge(terminal_curves, on="au_id", how="left")

    source_subset = source_table.copy()
    source_subset["forest_cover_id"] = pd.to_numeric(
        source_subset["FOREST_COVER_ID"], errors="coerce"
    )
    keep_columns = {
        "forest_cover_id",
        "TCL_1_ESTIMATED_SITE_INDEX",
        "AGE_2020",
        "BEC_ZONE_CODE",
        "BEC_SUBZONE",
        "BEC_VARIANT",
    }
    source_subset = source_subset[[c for c in source_subset.columns if c in keep_columns]].copy()
    terminal_stands = (
        vdyp_yields.sort_values(["FEATURE_ID", "PRJ_TOTAL_AGE"], kind="stable")
        .groupby("FEATURE_ID", as_index=False)
        .tail(1)[["FEATURE_ID", "PRJ_TOTAL_AGE", "PRJ_VOL_DWB"]]
        .rename(
            columns={
                "FEATURE_ID": "forest_cover_id",
                "PRJ_TOTAL_AGE": "terminal_vdyp_age",
                "PRJ_VOL_DWB": "terminal_vdyp_volume",
            }
        )
    )

    detail_rows: list[dict[str, object]] = []
    summary_rows: list[dict[str, object]] = []
    for _, selected_row in selected.sort_values(["selected_rank", "au_id"], kind="stable").iterrows():
        au_id = str(selected_row["au_id"])
        assignment_rows = assignment.loc[assignment["au_id"].astype(str) == au_id].copy()
        joined = assignment_rows.merge(source_subset, on="forest_cover_id", how="left").merge(
            terminal_stands,
            on="forest_cover_id",
            how="left",
        )
        si = pd.to_numeric(joined.get("TCL_1_ESTIMATED_SITE_INDEX"), errors="coerce")
        age = pd.to_numeric(joined.get("AGE_2020"), errors="coerce")
        terminal = pd.to_numeric(joined.get("terminal_vdyp_volume"), errors="coerce")
        stand_count = int(len(joined))
        valid_age = age.dropna()
        old_support_stand_count = int(
            joined.loc[
                pd.to_numeric(joined.get("AGE_2020"), errors="coerce") >= 80.0,
                "forest_cover_id",
            ]
            .dropna()
            .astype(int)
            .nunique()
        )

        def _share(count: int) -> float:
            if stand_count == 0:
                return 0.0
            return float(count) / float(stand_count)

        age_lt_20_count = int((valid_age < 20.0).sum())
        age_lt_30_count = int((valid_age < 30.0).sum())
        age_lt_80_count = int((valid_age < 80.0).sum())
        age_gte_80_count = int((valid_age >= 80.0).sum())

        low_count = int((terminal.fillna(0.0) < low_terminal_stand_threshold).sum())
        high_count = int((terminal.fillna(0.0) > high_terminal_stand_threshold).sum())
        if low_count > 0 and high_count > 0:
            pattern = "mixed_low_high"
        elif low_count > 0:
            pattern = "mostly_low"
        elif high_count > 0:
            pattern = "mostly_high"
        else:
            pattern = "midrange"

        terminal_volume = pd.to_numeric(selected_row["terminal_volume"], errors="coerce")
        initial_flag = (
            float(pd.to_numeric(pd.Series([selected_row["terminal_volume"]]), errors="coerce").fillna(0.0).iloc[0])
            < low_terminal_threshold
        ) or (
            float(pd.to_numeric(pd.Series([selected_row["covered_area_ha"]]), errors="coerce").fillna(0.0).iloc[0])
            > large_area_threshold
            and float(
                pd.to_numeric(pd.Series([selected_row["terminal_volume"]]), errors="coerce")
                .fillna(0.0)
                .iloc[0]
            )
            < low_large_area_threshold
        )
        if pd.isna(terminal_volume):
            if age_gte_80_count == 0:
                issue_class = "managed_only_after_age_floor"
            elif old_support_stand_count < _MIN_FIRST_GROWTH_SOURCE_STANDS:
                issue_class = "insufficient_source_stands"
            else:
                issue_class = "missing_first_growth_curve"
        elif low_count > 0 and high_count > 0:
            issue_class = "mixed_population"
        elif _share(age_lt_80_count) >= 0.5:
            issue_class = "young_skewed_population"
        else:
            issue_class = "persistently_low_old_unit"

        flagged = bool(initial_flag)
        if issue_class == "managed_only_after_age_floor":
            flagged = False

        summary_rows.append(
            {
                "selected_rank": int(selected_row["selected_rank"]),
                "au_id": au_id,
                "covered_area_ha": float(selected_row["covered_area_ha"]),
                "terminal_age": float(selected_row["terminal_age"]),
                "terminal_volume": float(selected_row["terminal_volume"]),
                "flagged": flagged,
                "stand_count": stand_count,
                "site_index_min": float(si.min()) if len(si.dropna()) else np.nan,
                "site_index_median": float(si.median()) if len(si.dropna()) else np.nan,
                "site_index_max": float(si.max()) if len(si.dropna()) else np.nan,
                "age_2020_min": float(age.min()) if len(age.dropna()) else np.nan,
                "age_2020_median": float(age.median()) if len(age.dropna()) else np.nan,
                "age_2020_max": float(age.max()) if len(age.dropna()) else np.nan,
                "age_lt_20_count": age_lt_20_count,
                "age_lt_20_share": _share(age_lt_20_count),
                "age_lt_30_count": age_lt_30_count,
                "age_lt_30_share": _share(age_lt_30_count),
                "age_lt_80_count": age_lt_80_count,
                "age_lt_80_share": _share(age_lt_80_count),
                "age_gte_80_count": age_gte_80_count,
                "age_gte_80_share": _share(age_gte_80_count),
                "old_support_stand_count": old_support_stand_count,
                "terminal_vdyp_min": float(terminal.min()) if len(terminal.dropna()) else np.nan,
                "terminal_vdyp_p25": float(terminal.quantile(0.25)) if len(terminal.dropna()) else np.nan,
                "terminal_vdyp_median": float(terminal.median()) if len(terminal.dropna()) else np.nan,
                "terminal_vdyp_p75": float(terminal.quantile(0.75)) if len(terminal.dropna()) else np.nan,
                "terminal_vdyp_max": float(terminal.max()) if len(terminal.dropna()) else np.nan,
                "low_terminal_stand_count": low_count,
                "high_terminal_stand_count": high_count,
                "population_pattern": pattern,
                "curve_issue_class": issue_class,
            }
        )

        if not flagged:
            continue
        for _, row in joined.sort_values(
            ["terminal_vdyp_volume", "forest_cover_id"], kind="stable", na_position="last"
        ).iterrows():
            detail_rows.append(
                {
                    "au_id": au_id,
                    "selected_rank": int(selected_row["selected_rank"]),
                    "forest_cover_id": int(row["forest_cover_id"]),
                    "shape_area_ha": float(row["shape_area_ha"]),
                    "site_index": row.get("TCL_1_ESTIMATED_SITE_INDEX"),
                    "age_2020": row.get("AGE_2020"),
                    "terminal_vdyp_age": row.get("terminal_vdyp_age"),
                    "terminal_vdyp_volume": row.get("terminal_vdyp_volume"),
                }
            )

    summary_frame = pd.DataFrame(summary_rows)
    if not summary_frame.empty:
        summary_frame = summary_frame.sort_values(
            ["flagged", "terminal_volume", "selected_rank"],
            ascending=[False, True, True],
            kind="stable",
        )

    detail_frame = pd.DataFrame(detail_rows)
    if not detail_frame.empty:
        detail_frame = detail_frame.sort_values(
            ["selected_rank", "terminal_vdyp_volume", "forest_cover_id"],
            kind="stable",
            na_position="last",
        )

    summary_path = output_dir / "bad_curve_audit_summary.csv"
    detail_path = output_dir / "bad_curve_audit_detail.csv"
    summary_frame.to_csv(summary_path, index=False)
    detail_frame.to_csv(detail_path, index=False)

    return MkrfBadCurveAuditResult(
        output_dir=output_dir,
        summary_path=summary_path,
        detail_path=detail_path,
        flagged_au_count=int(summary_frame["flagged"].astype(bool).sum()),
        total_selected_au_count=int(len(summary_frame)),
    )


def initialize_mkrf_runtime_package(
    *,
    package_root: Path,
    selected_au_csv: Path,
    stand_origin_assignment_csv: Path,
    stand_au_assignment_csv: Path,
    managed_bootstrap_csv: Path,
    first_growth_curves_csv: Path,
    first_growth_diagnostics_csv: Path,
    managed_curves_csv: Path,
    managed_run_manifest_json: Path,
    bad_curve_audit_summary_csv: Path,
) -> MkrfRuntimePackageInitResult:
    """Initialize the canonical MKRF runtime-package root and write an init manifest."""
    package_root = package_root.resolve()
    readme_path = package_root / "README.md"
    analysis_dir = package_root / "analysis"
    analysis_pin_path = analysis_dir / "base.pin"
    headless_runtime_common_path = analysis_dir / "headless_runtime_common.bsh"
    xml_dir = package_root / "xml"
    tracks_dir = package_root / "tracks"
    targets_dir = package_root / "scripts" / "targets"
    flow_targets_script_path = targets_dir / "flowtargets.bsh"
    manifest_path = analysis_dir / "runtime_package_init_manifest.json"
    curve_status_path = analysis_dir / "runtime_curve_status.csv"
    analysis_au_runtime_status_path = analysis_dir / "au_runtime_status.csv"
    analysis_au_curve_refs_path = analysis_dir / "au_curve_refs.csv"
    runtime_au_remap_audit_path = analysis_dir / "runtime_au_remap_audit.csv"
    species_share_audit_path = analysis_dir / "runtime_species_share_audit.csv"
    ct_eligibility_audit_path = analysis_dir / "ct_eligibility_audit.csv"
    ct_intensity_audit_path = analysis_dir / "ct_intensity_audit.csv"
    ct_intensity_summary_path = analysis_dir / "ct_intensity_summary.csv"
    hw_ingrowth_overlay_audit_path = analysis_dir / "planted_hw_ingrowth_overlay_audit.csv"
    hw_ingrowth_overlay_summary_path = (
        analysis_dir / "planted_hw_ingrowth_overlay_summary.csv"
    )
    xml_contract_path = xml_dir / "runtime_curve_contract.xml"
    xml_curve_bank_path = xml_dir / "runtime_curve_bank.xml"
    forestmodel_xml_path = xml_dir / "forestmodel.xml"
    required_dirs = (
        analysis_dir,
        xml_dir,
        tracks_dir,
        package_root / "spatial",
        package_root / "scripts",
        targets_dir,
        package_root / "targets",
        package_root / "initial_targets",
    )
    for directory in required_dirs:
        directory.mkdir(parents=True, exist_ok=True)

    selected_au = pd.read_csv(selected_au_csv)
    stand_origin_assignment = pd.read_csv(stand_origin_assignment_csv)
    stand_au_assignment = pd.read_csv(stand_au_assignment_csv)
    managed_bootstrap = pd.read_csv(managed_bootstrap_csv)
    first_growth_curves = pd.read_csv(first_growth_curves_csv)
    first_growth_diagnostics = pd.read_csv(first_growth_diagnostics_csv)
    managed_curves = pd.read_csv(managed_curves_csv)
    bad_curve_summary = pd.read_csv(bad_curve_audit_summary_csv)
    managed_manifest = json.loads(managed_run_manifest_json.read_text(encoding="utf-8"))

    normalized_assignment, remap_audit = _normalize_runtime_au_assignments(
        selected_au_table=selected_au,
        stand_origin_assignment=stand_origin_assignment,
        managed_curves=managed_curves,
        first_growth_diagnostics=first_growth_diagnostics,
    )
    remap_audit.to_csv(runtime_au_remap_audit_path, index=False)
    au_lookup = (
        normalized_assignment[["forest_cover_id", "au_id"]]
        .drop_duplicates(subset=["forest_cover_id"], keep="first")
        .sort_values("forest_cover_id", kind="stable")
    )
    forest_cover_ids = au_lookup["forest_cover_id"].astype(int).astype(str).tolist()
    rebuild_au_ids = au_lookup["au_id"].tolist()
    au_lookup_expr = _build_lookup_expr(
        forest_cover_ids,
        rebuild_au_ids,
        key_expr="Int(FOREST_COV)",
    )
    forest_cover_origin_lookup = (
        normalized_assignment[["forest_cover_id", "origin_class"]]
        .drop_duplicates(subset=["forest_cover_id"], keep="first")
        .assign(
            forest_cover_id=lambda df: df["forest_cover_id"].astype(int).astype(str),
            runtime_origin=lambda df: np.where(
                df["origin_class"].astype(str).eq("fire_origin"),
                "natural",
                "treated",
            ),
        )
        .sort_values("forest_cover_id", kind="stable")
    )
    origin_lookup_expr = _build_lookup_expr(
        forest_cover_origin_lookup["forest_cover_id"].tolist(),
        forest_cover_origin_lookup["runtime_origin"].tolist(),
        key_expr="Int(FOREST_COV)",
    )

    selected_au_count = int(selected_au["au_id"].astype(str).nunique())
    first_growth_curve_au_count = int(first_growth_curves["au_id"].astype(str).nunique())
    first_growth_missing_au_count = int(
        first_growth_diagnostics.loc[
            first_growth_diagnostics["selected_path"]
            .astype(str)
            .eq("insufficient_source_stands"),
            "au_id",
        ]
        .astype(str)
        .nunique()
    )
    managed_curve_au_count = int(managed_curves["au_id"].astype(str).nunique())
    flagged_au_count = int(bad_curve_summary["flagged"].fillna(False).astype(bool).sum())

    first_growth_path_by_au = (
        first_growth_diagnostics[["au_id", "selected_path"]]
        .drop_duplicates(subset=["au_id"], keep="last")
        .assign(
            au_id=lambda df: df["au_id"].astype(str),
            selected_path=lambda df: df["selected_path"].astype(str),
        )
    )
    managed_curve_aus = set(managed_curves["au_id"].astype(str).unique())
    bad_curve_flagged = (
        bad_curve_summary[["au_id", "flagged"]]
        .drop_duplicates(subset=["au_id"], keep="last")
        .assign(
            au_id=lambda df: df["au_id"].astype(str),
            flagged=lambda df: df["flagged"].fillna(False).astype(bool),
        )
    )
    runtime_curve_status = (
        selected_au[["au_id"]]
        .assign(au_id=lambda df: df["au_id"].astype(str))
        .merge(first_growth_path_by_au, on="au_id", how="left")
        .merge(bad_curve_flagged, on="au_id", how="left")
    )
    runtime_curve_status["flagged_bad_curve"] = (
        runtime_curve_status["flagged"].fillna(False).astype(bool)
    )
    runtime_curve_status = runtime_curve_status.drop(columns=["flagged"])
    runtime_curve_status["has_first_growth_curve"] = runtime_curve_status["selected_path"].notna() & (
        ~runtime_curve_status["selected_path"].eq("insufficient_source_stands")
    )
    runtime_curve_status["has_managed_curve"] = runtime_curve_status["au_id"].isin(managed_curve_aus)
    runtime_curve_status["runtime_curve_mode"] = np.where(
        runtime_curve_status["has_first_growth_curve"] & runtime_curve_status["has_managed_curve"],
        "first_growth_and_managed",
        np.where(
            (~runtime_curve_status["has_first_growth_curve"])
            & runtime_curve_status["has_managed_curve"]
            & runtime_curve_status["selected_path"].fillna("").eq("insufficient_source_stands"),
            "managed_only",
            "incomplete",
        ),
    )
    runtime_curve_status["runtime_curve_note"] = np.where(
        runtime_curve_status["runtime_curve_mode"].eq("managed_only"),
        "insufficient_source_stands_managed_only",
        "",
    )
    runtime_curve_status = runtime_curve_status.rename(
        columns={"selected_path": "first_growth_selected_path"}
    ).sort_values("au_id", kind="stable")
    runtime_curve_status.to_csv(curve_status_path, index=False)
    tracks_status = (
        selected_au.assign(au_id=lambda df: df["au_id"].astype(str))
        .merge(
            runtime_curve_status[
                [
                    "au_id",
                    "first_growth_selected_path",
                    "has_first_growth_curve",
                    "has_managed_curve",
                    "runtime_curve_mode",
                    "runtime_curve_note",
                    "flagged_bad_curve",
                ]
            ],
            on="au_id",
            how="left",
        )
    )
    tracks_sort_columns = ["au_id"]
    if "selected_rank" in tracks_status.columns:
        tracks_sort_columns = ["selected_rank", "au_id"]
    tracks_status = tracks_status.sort_values(tracks_sort_columns, kind="stable")
    tracks_status.to_csv(analysis_au_runtime_status_path, index=False)
    curve_ref_rows: list[dict[str, object]] = []
    for row in runtime_curve_status.sort_values("au_id", kind="stable").itertuples(index=False):
        au_token = str(row.au_id).upper().replace("-", "_")
        curve_ref_rows.append(
            {
                "au_id": str(row.au_id),
                "runtime_curve_mode": str(row.runtime_curve_mode),
                "first_growth_selected_path": (
                    str(row.first_growth_selected_path)
                    if pd.notna(row.first_growth_selected_path)
                    else ""
                ),
                "has_first_growth_curve": bool(row.has_first_growth_curve),
                "has_managed_curve": bool(row.has_managed_curve),
                "first_growth_curve_id": (
                    f"FG_{au_token}" if bool(row.has_first_growth_curve) else ""
                ),
                "managed_curve_id": f"MG_{au_token}" if bool(row.has_managed_curve) else "",
                "flagged_bad_curve": bool(row.flagged_bad_curve),
                "runtime_curve_note": (
                    str(row.runtime_curve_note)
                    if pd.notna(row.runtime_curve_note) and str(row.runtime_curve_note).strip()
                    else ""
                ),
            }
        )
    pd.DataFrame(curve_ref_rows).to_csv(analysis_au_curve_refs_path, index=False)
    managed_curve_lookup_rows = [row for row in curve_ref_rows if row["managed_curve_id"]]
    managed_curve_au_ids = [str(row["au_id"]) for row in managed_curve_lookup_rows]
    managed_curve_ids = [str(row["managed_curve_id"]) for row in managed_curve_lookup_rows]
    first_growth_curve_lookup_rows = [row for row in curve_ref_rows if row["first_growth_curve_id"]]
    first_growth_curve_au_ids = [str(row["au_id"]) for row in first_growth_curve_lookup_rows]
    first_growth_curve_ids = [str(row["first_growth_curve_id"]) for row in first_growth_curve_lookup_rows]
    ct_bucket_specs = _mkrf_ct_bucket_specs()
    runtime_base_au_expr = (
        f"if(startswith(au,'thn'),substring(au,{len(_mkrf_ct_bucket_prefix(40))}),au)"
    )
    runtime_state_expr = "if(startswith(au,'thn'),'THN',statecode)"
    managed_curve_lookup_expr = _build_lookup_expr(
        managed_curve_au_ids,
        managed_curve_ids,
        key_expr=runtime_base_au_expr,
    )
    first_growth_curve_lookup_expr = _build_lookup_expr(
        first_growth_curve_au_ids,
        first_growth_curve_ids,
        key_expr=runtime_base_au_expr,
    )
    forest_cover_fg_lookup = (
        normalized_assignment[["forest_cover_id", "au_id"]]
        .drop_duplicates(subset=["forest_cover_id"], keep="first")
        .merge(
            runtime_curve_status[["au_id", "has_first_growth_curve"]],
            on="au_id",
            how="left",
        )
        .assign(
            forest_cover_id=lambda df: df["forest_cover_id"].astype(int).astype(str),
            has_first_growth_curve=lambda df: np.where(
                df["has_first_growth_curve"].fillna(False).astype(bool), "Y", "N"
            ),
        )
        .sort_values("forest_cover_id", kind="stable")
    )
    has_first_growth_lookup_expr = _build_lookup_expr(
        forest_cover_fg_lookup["forest_cover_id"].tolist(),
        forest_cover_fg_lookup["has_first_growth_curve"].tolist(),
        key_expr="Int(FOREST_COV)",
    )
    managed_species_shares = _build_managed_species_share_table(managed_bootstrap)
    managed_species_shares = managed_species_shares.assign(
        au_id=lambda df: df["au_id"].astype(str)
    ).sort_values("au_id", kind="stable")
    ct_eligibility_species_shares = _build_managed_species_share_table(
        managed_bootstrap,
        species_prefix=(
            "base_managed"
            if "base_managed_species_1" in managed_bootstrap.columns
            else "managed"
        ),
    )
    ct_eligibility_species_shares = ct_eligibility_species_shares.assign(
        au_id=lambda df: df["au_id"].astype(str)
    ).sort_values("au_id", kind="stable")
    unmanaged_share_assignment = stand_au_assignment.merge(
        normalized_assignment[["forest_cover_id", "au_id"]]
        .drop_duplicates(subset=["forest_cover_id"], keep="first")
        .rename(columns={"au_id": "runtime_au_id"}),
        on="forest_cover_id",
        how="left",
    )
    unmanaged_share_assignment["au_id"] = (
        unmanaged_share_assignment["runtime_au_id"]
        .fillna(unmanaged_share_assignment["au_id"])
        .astype(str)
        .str.strip()
    )
    unmanaged_share_assignment = unmanaged_share_assignment.drop(columns=["runtime_au_id"])
    unmanaged_species_shares = _build_unmanaged_species_share_table(
        unmanaged_share_assignment,
        selected_au_table=selected_au,
    )
    unmanaged_species_shares = unmanaged_species_shares.assign(
        au_id=lambda df: df["au_id"].astype(str)
    ).sort_values("au_id", kind="stable")
    managed_share_label_map = {
        "share_ba": "Ba",
        "share_cw": "Cw",
        "share_dec": "Dec",
        "share_dr": "Dr",
        "share_fd": "Fd",
        "share_hw": "Hw",
        "share_oth": "Oth",
        "share_yc": "Yc",
    }
    managed_share_lookup_exprs: dict[str, str] = {}
    managed_share_keys = managed_species_shares["au_id"].tolist()
    for share_column in managed_share_label_map:
        managed_share_values = [
            str(float(value))
            for value in managed_species_shares[share_column].fillna(0.0).tolist()
        ]
        lookup_expr = _build_lookup_expr(
            managed_share_keys,
            managed_share_values,
            key_expr=runtime_base_au_expr,
        )
        managed_share_lookup_exprs[share_column] = f"Number({lookup_expr})/100"
    ct_eligibility_species_shares = ct_eligibility_species_shares.assign(
        share_cw_fd=lambda df: pd.to_numeric(
            df["share_cw"], errors="coerce"
        ).fillna(0.0)
        + pd.to_numeric(df["share_fd"], errors="coerce").fillna(0.0)
    )
    ct_eligibility_cw_fd_values = [
        str(float(value))
        for value in ct_eligibility_species_shares["share_cw_fd"].fillna(0.0).tolist()
    ]
    ct_eligibility_cw_fd_lookup_expr = (
        "Number("
        + _build_lookup_expr(
            ct_eligibility_species_shares["au_id"].tolist(),
            ct_eligibility_cw_fd_values,
            key_expr=runtime_base_au_expr,
        )
        + ")/100"
    )
    unmanaged_share_lookup_exprs: dict[str, str] = {}
    unmanaged_share_keys = unmanaged_species_shares["au_id"].tolist()
    for share_column in managed_share_label_map:
        unmanaged_share_values = [
            str(float(value))
            for value in unmanaged_species_shares[share_column].fillna(0.0).tolist()
        ]
        lookup_expr = _build_lookup_expr(
            unmanaged_share_keys,
            unmanaged_share_values,
            key_expr=runtime_base_au_expr,
        )
        unmanaged_share_lookup_exprs[share_column] = f"Number({lookup_expr})/100"
    species_share_audit = _build_species_share_audit_table(
        managed_species_shares=managed_species_shares,
        unmanaged_species_shares=unmanaged_species_shares,
    )
    species_share_audit.to_csv(species_share_audit_path, index=False)
    ct_eligibility_audit = _build_ct_eligibility_audit_table(
        selected_au_table=selected_au,
        ct_eligibility_species_shares=ct_eligibility_species_shares,
    )
    ct_eligibility_audit.to_csv(ct_eligibility_audit_path, index=False)
    ct_intensity_audit, ct_intensity_summary = _build_ct_intensity_audit_tables(
        ct_eligibility_audit=ct_eligibility_audit,
        treated_species_shares=managed_species_shares,
        ct_bucket_specs=ct_bucket_specs,
    )
    ct_intensity_audit.to_csv(ct_intensity_audit_path, index=False)
    ct_intensity_summary.to_csv(ct_intensity_summary_path, index=False)
    hw_ingrowth_overlay_audit, hw_ingrowth_overlay_summary = (
        _build_hw_ingrowth_overlay_audit_tables(managed_bootstrap=managed_bootstrap)
    )
    hw_ingrowth_overlay_audit.to_csv(hw_ingrowth_overlay_audit_path, index=False)
    hw_ingrowth_overlay_summary.to_csv(hw_ingrowth_overlay_summary_path, index=False)
    origin_share_lookup_exprs = {
        share_column: (
            f"if(origin eq 'natural',{unmanaged_share_lookup_exprs[share_column]},"
            f"{managed_share_lookup_exprs[share_column]})"
        )
        for share_column in managed_share_label_map
    }
    first_growth_by_au = {
        str(au_id): group.sort_values("age", kind="stable")
        for au_id, group in first_growth_curves.groupby("au_id", sort=True)
    }
    managed_by_au = {
        str(au_id): group.sort_values("age", kind="stable")
        for au_id, group in managed_curves.groupby("au_id", sort=True)
    }

    def _curve_group_value_at_age(curve_group: pd.DataFrame, age: int) -> float:
        if curve_group.empty:
            return 0.0
        x_vals = curve_group["age"].astype(float).to_numpy()
        y_vals = curve_group["volume"].astype(float).to_numpy()
        return float(np.interp(float(age), x_vals, y_vals))

    bucketed_thn_keys: list[str] = []
    natural_bucketed_thn_curve_ids: list[str] = []
    treated_bucketed_thn_curve_ids: list[str] = []
    ct_product_keys: list[str] = []
    natural_ct_product_curve_ids: list[str] = []
    treated_ct_product_curve_ids: list[str] = []
    for row in runtime_curve_status.sort_values("au_id", kind="stable").itertuples(index=False):
        au_id = str(row.au_id)
        managed_group = managed_by_au.get(au_id)
        if managed_group is None or managed_group.empty:
            continue
        natural_group = first_growth_by_au.get(au_id, managed_group)
        au_token = au_id.upper().replace("-", "_")
        for bucket_spec in ct_bucket_specs:
            anchor_age = int(bucket_spec["anchor_age"])
            bucket_prefix = str(bucket_spec["prefix"])
            bucket_label = str(bucket_spec["label"])
            natural_gap = round(
                _curve_group_value_at_age(natural_group, anchor_age)
                * _MKRF_CT_TARGET_BA_REMOVAL_FRACTION,
                6,
            )
            treated_gap = round(
                _curve_group_value_at_age(managed_group, anchor_age)
                * _MKRF_CT_TARGET_BA_REMOVAL_FRACTION,
                6,
            )
            natural_residual_curve_id = f"THN{anchor_age:03d}_FG_{au_token}"
            treated_residual_curve_id = f"THN{anchor_age:03d}_MG_{au_token}"
            natural_extraction_curve_id = f"CT{anchor_age:03d}_FG_{au_token}"
            treated_extraction_curve_id = f"CT{anchor_age:03d}_MG_{au_token}"
            bucketed_thn_keys.append(f"{bucket_prefix}{au_id}")
            natural_bucketed_thn_curve_ids.append(natural_residual_curve_id)
            treated_bucketed_thn_curve_ids.append(treated_residual_curve_id)
            ct_product_keys.append(f"{bucket_label}|{au_id}")
            natural_ct_product_curve_ids.append(natural_extraction_curve_id)
            treated_ct_product_curve_ids.append(treated_extraction_curve_id)
    origin_curve_lookup_expr = (
        "if(origin eq 'natural' and hasnatcurve eq 'Y',"
        f"curveId({first_growth_curve_lookup_expr}),"
        f"curveId({managed_curve_lookup_expr}))"
    )
    natural_bucketed_thn_curve_lookup_expr = _build_lookup_expr(
        bucketed_thn_keys,
        natural_bucketed_thn_curve_ids,
        key_expr="au",
    )
    treated_bucketed_thn_curve_lookup_expr = _build_lookup_expr(
        bucketed_thn_keys,
        treated_bucketed_thn_curve_ids,
        key_expr="au",
    )
    ct_product_key_expr = f"treatment+'|'+{runtime_base_au_expr}"
    natural_ct_product_curve_lookup_expr = _build_lookup_expr(
        ct_product_keys,
        natural_ct_product_curve_ids,
        key_expr=ct_product_key_expr,
    )
    treated_ct_product_curve_lookup_expr = _build_lookup_expr(
        ct_product_keys,
        treated_ct_product_curve_ids,
        key_expr=ct_product_key_expr,
    )
    standing_curve_expr = (
        f"if(startswith(au,'thn'),"
        "curveId("
        f"if(origin eq 'natural',{natural_bucketed_thn_curve_lookup_expr},"
        f"{treated_bucketed_thn_curve_lookup_expr})"
        "),"
        f"{origin_curve_lookup_expr})"
    )
    product_curve_expr = (
        "if(startswith(treatment,'CT'),"
        "curveId("
        f"if(origin eq 'natural',{natural_ct_product_curve_lookup_expr},"
        f"{treated_ct_product_curve_lookup_expr})"
        "),"
        f"{standing_curve_expr})"
    )
    for obsolete_path in (
        tracks_dir / "au_runtime_status.csv",
        tracks_dir / "au_curve_refs.csv",
    ):
        if obsolete_path.exists():
            obsolete_path.unlink()

    root = et.Element(
        "mkrfRuntimeCurveContract",
        {
            "schemaVersion": "1",
            "runtimeGenerationStatus": "initialized_only",
        },
    )
    counts_node = et.SubElement(root, "counts")
    counts_node.set("selectedAuCount", str(selected_au_count))
    counts_node.set("firstGrowthCurveAuCount", str(first_growth_curve_au_count))
    counts_node.set("firstGrowthMissingAuCount", str(first_growth_missing_au_count))
    counts_node.set("managedCurveAuCount", str(managed_curve_au_count))
    counts_node.set(
        "managedOnlyRuntimeAuCount",
        str(int(runtime_curve_status["runtime_curve_mode"].eq("managed_only").sum())),
    )
    policy_node = et.SubElement(root, "policy")
    policy_node.set("firstGrowthCurveFamily", "smoothed_bin_pchip")
    policy_node.set("firstGrowthBorrowingAllowed", "false")
    policy_node.set("managedOnlyRuntimeUnitsAllowed", "true")
    policy_node.set("insufficientSupportFallbackGeneration", "forbidden")
    policy_node.set("insufficientSupportBorrowing", "forbidden")
    source_node = et.SubElement(root, "sourceContracts")
    for tag, path in (
        ("selectedAuCsv", selected_au_csv),
        ("standOriginAssignmentCsv", stand_origin_assignment_csv),
        ("standAuAssignmentCsv", stand_au_assignment_csv),
        ("managedBootstrapCsv", managed_bootstrap_csv),
        ("firstGrowthCurvesCsv", first_growth_curves_csv),
        ("firstGrowthDiagnosticsCsv", first_growth_diagnostics_csv),
        ("managedCurvesCsv", managed_curves_csv),
        ("managedRunManifestJson", managed_run_manifest_json),
        ("badCurveAuditSummaryCsv", bad_curve_audit_summary_csv),
        ("runtimeCurveStatusCsv", curve_status_path),
        ("speciesShareAuditCsv", species_share_audit_path),
    ):
        child = et.SubElement(source_node, tag)
        child.text = str(path.resolve())
    aus_node = et.SubElement(root, "analysisUnits")
    for row in runtime_curve_status.itertuples(index=False):
        au_node = et.SubElement(aus_node, "au")
        au_node.set("id", str(row.au_id))
        au_node.set("runtimeCurveMode", str(row.runtime_curve_mode))
        au_node.set("hasManagedCurve", "true" if bool(row.has_managed_curve) else "false")
        au_node.set(
            "hasFirstGrowthCurve", "true" if bool(row.has_first_growth_curve) else "false"
        )
        au_node.set("flaggedBadCurve", "true" if bool(row.flagged_bad_curve) else "false")
        if pd.notna(row.first_growth_selected_path):
            au_node.set("firstGrowthSelectedPath", str(row.first_growth_selected_path))
        if pd.notna(row.runtime_curve_note) and str(row.runtime_curve_note).strip():
            au_node.set("note", str(row.runtime_curve_note))
    et.ElementTree(root).write(xml_contract_path, encoding="utf-8", xml_declaration=True)

    curve_bank_root = et.Element(
        "mkrfRuntimeCurveBank",
        {
            "schemaVersion": "1",
            "curveFamily": "au_wise_runtime_curve_bank",
        },
    )
    for row in runtime_curve_status.itertuples(index=False):
        au_bank_node = et.SubElement(
            curve_bank_root,
            "analysisUnit",
            {
                "id": str(row.au_id),
                "runtimeCurveMode": str(row.runtime_curve_mode),
            },
        )
        if bool(row.has_first_growth_curve):
            fg_group = first_growth_by_au.get(str(row.au_id))
            if fg_group is not None and not fg_group.empty:
                fg_node = et.SubElement(
                    au_bank_node,
                    "firstGrowthCurve",
                    {
                        "selectedPath": str(row.first_growth_selected_path),
                    },
                )
                for curve_row in fg_group.itertuples(index=False):
                    point_node = et.SubElement(fg_node, "point")
                    point_node.set("age", str(float(curve_row.age)))
                    point_node.set("volume", str(float(curve_row.volume)))
        if bool(row.has_managed_curve):
            managed_group = managed_by_au.get(str(row.au_id))
            if managed_group is not None and not managed_group.empty:
                managed_node = et.SubElement(au_bank_node, "managedCurve")
                for curve_row in managed_group.itertuples(index=False):
                    point_node = et.SubElement(managed_node, "point")
                    point_node.set("age", str(float(curve_row.age)))
                    point_node.set("volume", str(float(curve_row.volume)))
    et.ElementTree(curve_bank_root).write(
        xml_curve_bank_path, encoding="utf-8", xml_declaration=True
    )

    forestmodel_root = et.Element(
        "ForestModel",
        {
            "description": "MKRF canonical rebuild",
            "horizon": "300",
            "year": "2020",
            "match": "multi",
        },
    )
    forestmodel_root.append(
        et.Comment(
            "Generated from accepted MKRF AU-wise runtime curve surfaces. Not yet runnable."
        )
    )
    forestmodel_root.append(
        et.Comment(
            f"Curve contract: {xml_contract_path.name}; curve bank: {xml_curve_bank_path.name}"
        )
    )
    curve_node = et.SubElement(forestmodel_root, "curve", {"id": "unity"})
    et.SubElement(curve_node, "point", {"x": "0", "y": "1"})
    le10_curve = et.SubElement(forestmodel_root, "curve", {"id": "le10"})
    et.SubElement(le10_curve, "point", {"x": "10", "y": "1"})
    et.SubElement(le10_curve, "point", {"x": "11", "y": "0"})
    for row in runtime_curve_status.itertuples(index=False):
        au_token = str(row.au_id).upper().replace("-", "_")
        if bool(row.has_first_growth_curve):
            fg_group = first_growth_by_au.get(str(row.au_id))
            if fg_group is not None and not fg_group.empty:
                fg_curve = et.SubElement(forestmodel_root, "curve", {"id": f"FG_{au_token}"})
                for curve_row in fg_group.itertuples(index=False):
                    et.SubElement(
                        fg_curve,
                        "point",
                        {"x": str(float(curve_row.age)), "y": str(float(curve_row.volume))},
                    )
        if bool(row.has_managed_curve):
            managed_group = managed_by_au.get(str(row.au_id))
            if managed_group is not None and not managed_group.empty:
                mg_curve = et.SubElement(forestmodel_root, "curve", {"id": f"MG_{au_token}"})
                for curve_row in managed_group.itertuples(index=False):
                    et.SubElement(
                        mg_curve,
                        "point",
                        {"x": str(float(curve_row.age)), "y": str(float(curve_row.volume))},
                    )
        managed_group = managed_by_au.get(str(row.au_id))
        if managed_group is None or managed_group.empty:
            continue
        natural_group = first_growth_by_au.get(str(row.au_id), managed_group)
        for bucket_spec in ct_bucket_specs:
            anchor_age = int(bucket_spec["anchor_age"])
            natural_gap = round(
                _curve_group_value_at_age(natural_group, anchor_age)
                * _MKRF_CT_TARGET_BA_REMOVAL_FRACTION,
                6,
            )
            treated_gap = round(
                _curve_group_value_at_age(managed_group, anchor_age)
                * _MKRF_CT_TARGET_BA_REMOVAL_FRACTION,
                6,
            )
            natural_residual_curve = et.SubElement(
                forestmodel_root,
                "curve",
                {"id": f"THN{anchor_age:03d}_FG_{au_token}"},
            )
            treated_residual_curve = et.SubElement(
                forestmodel_root,
                "curve",
                {"id": f"THN{anchor_age:03d}_MG_{au_token}"},
            )
            natural_extraction_curve = et.SubElement(
                forestmodel_root,
                "curve",
                {"id": f"CT{anchor_age:03d}_FG_{au_token}"},
            )
            treated_extraction_curve = et.SubElement(
                forestmodel_root,
                "curve",
                {"id": f"CT{anchor_age:03d}_MG_{au_token}"},
            )
            age_values = sorted(
                {
                    float(point.age)
                    for point in natural_group.itertuples(index=False)
                    if np.isfinite(float(point.age))
                }
                | {
                    float(point.age)
                    for point in managed_group.itertuples(index=False)
                    if np.isfinite(float(point.age))
                }
            )
            if not age_values:
                age_values = [0.0, 100.0]
            for age_value in age_values:
                natural_volume = _curve_group_value_at_age(natural_group, int(age_value))
                treated_volume = _curve_group_value_at_age(managed_group, int(age_value))
                et.SubElement(
                    natural_residual_curve,
                    "point",
                    {
                        "x": str(float(age_value)),
                        "y": str(max(0.0, natural_volume - natural_gap)),
                    },
                )
                et.SubElement(
                    treated_residual_curve,
                    "point",
                    {
                        "x": str(float(age_value)),
                        "y": str(max(0.0, treated_volume - treated_gap)),
                    },
                )
                et.SubElement(
                    natural_extraction_curve,
                    "point",
                    {"x": str(float(age_value)), "y": str(max(0.0, natural_gap))},
                )
                et.SubElement(
                    treated_extraction_curve,
                    "point",
                    {"x": str(float(age_value)), "y": str(max(0.0, treated_gap))},
                )
    define_specs = (
        {"field": "status", "column": "CONTCLAS"},
        {"field": "origin", "column": origin_lookup_expr},
        {
            "field": "statecode",
            "column": f"if({origin_lookup_expr} eq 'natural','EN','EM')",
        },
        {"field": "au", "column": au_lookup_expr},
        {"field": "auf", "column": au_lookup_expr},
        {"field": "oper", "column": "Operabilit"},
        {"field": "ct", "column": "CT_eligib"},
        {"field": "aux", "column": "Int(FOREST_COV)"},
        {"field": "hasnatcurve", "column": has_first_growth_lookup_expr},
        {"field": "treatment"},
        {"field": "managed", "constant": "'C'"},
        {"field": "unmanaged", "constant": "'N'"},
        {"field": "operable", "constant": "'Operable'"},
        {"field": "lowoper", "constant": "'Low Operability'"},
        {"field": "frd", "constant": "0.027"},
    )
    for define_spec in define_specs:
        et.SubElement(forestmodel_root, "define", define_spec)
    et.SubElement(
        forestmodel_root,
        "input",
        {
            "block": "Int(RES_KEY)",
            "area": "Shape_Area/10000",
            "age": "Int(AGE_2020)",
            "exclude": "CONTCLAS eq 'X'",
        },
    )
    et.SubElement(
        forestmodel_root,
        "output",
        {
            "messages": "messages.csv",
            "blocks": "blocks.csv",
            "features": "features.csv",
            "products": "products.csv",
            "treatments": "treatments.csv",
            "curves": "curves.csv",
            "tracknames": "tracknames.csv",
        },
    )
    forestmodel_root.append(
        et.Comment(
            "Runtime references: "
            f"{xml_contract_path.name}, {xml_curve_bank_path.name}, {curve_status_path.name}"
        )
    )
    managed_operable_select = et.SubElement(
        forestmodel_root,
        "select",
        {"statement": "status in managed and oper in operable"},
    )
    managed_operable_retention = et.SubElement(
        managed_operable_select, "retention", {"factor": "0.1"}
    )
    et.SubElement(
        managed_operable_retention,
        "assign",
        {"field": "status", "value": "unmanaged"},
    )
    managed_operable_features = et.SubElement(managed_operable_retention, "features")
    managed_operable_attr = et.SubElement(
        managed_operable_features,
        "attribute",
        {"label": "feature.area.retention.total"},
    )
    et.SubElement(managed_operable_attr, "curve", {"idref": "unity"})

    managed_lowoper_select = et.SubElement(
        forestmodel_root,
        "select",
        {"statement": "status in managed and oper in lowoper"},
    )
    managed_lowoper_retention = et.SubElement(
        managed_lowoper_select, "retention", {"factor": "0.2"}
    )
    et.SubElement(
        managed_lowoper_retention,
        "assign",
        {"field": "status", "value": "unmanaged"},
    )
    managed_lowoper_features = et.SubElement(managed_lowoper_retention, "features")
    managed_lowoper_attr = et.SubElement(
        managed_lowoper_features,
        "attribute",
        {"label": "feature.area.retention.total"},
    )
    et.SubElement(managed_lowoper_attr, "curve", {"idref": "unity"})

    unmanaged_select = et.SubElement(
        forestmodel_root,
        "select",
        {"statement": "status in unmanaged"},
    )
    et.SubElement(unmanaged_select, "track")

    succession_select = et.SubElement(forestmodel_root, "select")
    et.SubElement(succession_select, "succession", {"breakup": "999", "renew": "0"})

    managed_cc_select = et.SubElement(
        forestmodel_root,
        "select",
        {"statement": "status in managed"},
    )
    managed_cc_track = et.SubElement(managed_cc_select, "track")
    managed_cc_treatment = et.SubElement(
        managed_cc_track,
        "treatment",
        {"label": "CC", "minage": "if(oper in operable, 60, 150)"},
    )
    managed_cc_produce = et.SubElement(managed_cc_treatment, "produce")
    et.SubElement(
        managed_cc_produce,
        "assign",
        {"field": "treatment", "value": "'CC'"},
    )
    managed_cc_transition = et.SubElement(managed_cc_treatment, "transition")
    et.SubElement(
        managed_cc_transition,
        "assign",
        {"field": "au", "value": "auf"},
    )
    et.SubElement(
        managed_cc_transition,
        "assign",
        {"field": "origin", "value": "'treated'"},
    )
    et.SubElement(
        managed_cc_transition,
        "assign",
        {"field": "statecode", "value": "'FM'"},
    )

    ct_select = et.SubElement(
        forestmodel_root,
        "select",
        {
            "statement": (
                "status in managed and oper in operable and ct eq 'Y' "
                "and not startswith(au,'thn') "
                f"and {ct_eligibility_cw_fd_lookup_expr} ge "
                f"{_MKRF_CT_MIN_CW_FD_SHARE_PCT / 100.0}"
            )
        },
    )
    ct_track = et.SubElement(ct_select, "track")
    for bucket_spec in ct_bucket_specs:
        ct_treatment = et.SubElement(
            ct_track,
            "treatment",
            {
                "label": str(bucket_spec["label"]),
                "minage": str(int(bucket_spec["min_age"])),
                "maxage": str(int(bucket_spec["max_age"])),
                "retain": "20",
            },
        )
        ct_produce = et.SubElement(ct_treatment, "produce")
        et.SubElement(
            ct_produce,
            "assign",
            {"field": "treatment", "value": f"'{str(bucket_spec['label'])}'"},
        )
        ct_transition = et.SubElement(ct_treatment, "transition")
        et.SubElement(
            ct_transition,
            "assign",
            {"field": "au", "value": f"'{str(bucket_spec['prefix'])}'+au"},
        )
    area_features_select = et.SubElement(forestmodel_root, "select")
    area_features = et.SubElement(area_features_select, "features")
    area_total_attr = et.SubElement(
        area_features,
        "attribute",
        {"label": "%f.area.%m.total"},
    )
    et.SubElement(area_total_attr, "curve", {"idref": "unity"})
    area_state_attr = et.SubElement(
        area_features,
        "attribute",
        {"label": f"'%f.area.%m.state.'+{runtime_state_expr}"},
    )
    et.SubElement(area_state_attr, "curve", {"idref": "unity"})
    area_seral_select = et.SubElement(
        forestmodel_root,
        "select",
        {"statement": "status ne 'X'"},
    )
    area_seral_features = et.SubElement(area_seral_select, "features")
    area_seral_attr = et.SubElement(
        area_seral_features,
        "attribute",
        {"label": "%f.area.%m.seral.le10"},
    )
    et.SubElement(area_seral_attr, "curve", {"idref": "le10"})
    managed_yield_select = et.SubElement(
        forestmodel_root,
        "select",
        {"statement": "status in managed"},
    )
    managed_yield_features = et.SubElement(managed_yield_select, "features")
    managed_yield_total = et.SubElement(
        managed_yield_features,
        "attribute",
        {"label": "%f.yield.%m.total"},
    )
    et.SubElement(
        managed_yield_total,
        "expression",
        {
            "statement": standing_curve_expr,
            "by": "1",
            "ignoreMissingAttributes": "false",
        },
    )
    managed_yield_state = et.SubElement(
        managed_yield_features,
        "attribute",
        {"label": f"'%f.yield.%m.state.'+{runtime_state_expr}"},
    )
    et.SubElement(
        managed_yield_state,
        "expression",
        {
            "statement": standing_curve_expr,
            "by": "1",
            "ignoreMissingAttributes": "false",
        },
    )
    managed_yield_merch_select = et.SubElement(
        forestmodel_root,
        "select",
        {"statement": "status in managed"},
    )
    managed_yield_merch_features = et.SubElement(managed_yield_merch_select, "features")
    managed_yield_merch_attr = et.SubElement(
        managed_yield_merch_features,
        "attribute",
        {"label": "%f.yield.%m.merch.total"},
    )
    et.SubElement(
        managed_yield_merch_attr,
        "expression",
        {
            "statement": "operable(attribute('feature.yield.%m.total'))",
            "by": "1",
            "ignoreMissingAttributes": "false",
        },
    )
    managed_indsp_select = et.SubElement(
        forestmodel_root,
        "select",
        {"statement": "status in managed"},
    )
    managed_indsp_features = et.SubElement(managed_indsp_select, "features")
    for share_column, species_label in managed_share_label_map.items():
        managed_indsp_attr = et.SubElement(
            managed_indsp_features,
            "attribute",
            {"label": f"%f.yield.%m.indsp.{species_label}"},
        )
        et.SubElement(
            managed_indsp_attr,
            "expression",
            {
                "statement": (
                    f"{standing_curve_expr}*({origin_share_lookup_exprs[share_column]})"
                ),
                "by": "1",
                "ignoreMissingAttributes": "false",
            },
        )
    unmanaged_yield_select = et.SubElement(
        forestmodel_root,
        "select",
        {"statement": "status in unmanaged"},
    )
    unmanaged_yield_features = et.SubElement(unmanaged_yield_select, "features")
    unmanaged_yield_total = et.SubElement(
        unmanaged_yield_features,
        "attribute",
        {"label": "%f.yield.%m.total"},
    )
    et.SubElement(
        unmanaged_yield_total,
        "expression",
        {
            "statement": standing_curve_expr,
            "by": "1",
            "ignoreMissingAttributes": "false",
        },
    )
    unmanaged_yield_state = et.SubElement(
        unmanaged_yield_features,
        "attribute",
        {"label": f"'%f.yield.%m.state.'+{runtime_state_expr}"},
    )
    et.SubElement(
        unmanaged_yield_state,
        "expression",
        {
            "statement": standing_curve_expr,
            "by": "1",
            "ignoreMissingAttributes": "false",
        },
    )
    for share_column, species_label in managed_share_label_map.items():
        unmanaged_yield_indsp = et.SubElement(
            unmanaged_yield_features,
            "attribute",
            {"label": f"%f.yield.%m.indsp.{species_label}"},
        )
        et.SubElement(
            unmanaged_yield_indsp,
            "expression",
            {
                "statement": (
                    f"{standing_curve_expr}*({origin_share_lookup_exprs[share_column]})"
                ),
                "by": "1",
                "ignoreMissingAttributes": "false",
            },
        )
    products_select = et.SubElement(
        forestmodel_root,
        "select",
        {"statement": ""},
    )
    products_node = et.SubElement(products_select, "products")
    product_area_total = et.SubElement(
        products_node,
        "attribute",
        {"label": "product.area.managed.total"},
    )
    et.SubElement(product_area_total, "curve", {"idref": "unity"})
    product_area_state = et.SubElement(
        products_node,
        "attribute",
        {"label": f"'product.area.managed.state.'+{runtime_state_expr}"},
    )
    et.SubElement(product_area_state, "curve", {"idref": "unity"})
    product_area_treat = et.SubElement(
        products_node,
        "attribute",
        {"label": "'product.area.managed.treat.'+treatment"},
    )
    et.SubElement(product_area_treat, "curve", {"idref": "unity"})
    product_yield_total = et.SubElement(
        products_node,
        "attribute",
        {"label": "product.yield.managed.total"},
    )
    et.SubElement(
        product_yield_total,
        "expression",
        {
            "statement": product_curve_expr,
            "by": "1",
            "ignoreMissingAttributes": "false",
        },
    )
    product_yield_state = et.SubElement(
        products_node,
        "attribute",
        {"label": f"'product.yield.managed.state.'+{runtime_state_expr}"},
    )
    et.SubElement(
        product_yield_state,
        "expression",
        {
            "statement": product_curve_expr,
            "by": "1",
            "ignoreMissingAttributes": "false",
        },
    )
    for share_column, species_label in managed_share_label_map.items():
        product_indsp_attr = et.SubElement(
            products_node,
            "attribute",
            {"label": f"product.yield.managed.indsp.{species_label}"},
        )
        ct_product_species_fraction_expr = _ct_product_species_fraction_expr(
            share_column,
            origin_share_lookup_exprs,
        )
        et.SubElement(
            product_indsp_attr,
            "expression",
            {
                "statement": (
                    f"{product_curve_expr}*("
                    f"if(startswith(treatment,'CT'),"
                    f"{ct_product_species_fraction_expr},"
                    f"{origin_share_lookup_exprs[share_column]}))"
                ),
                "by": "1",
                "ignoreMissingAttributes": "false",
            },
        )
    product_yield_treat = et.SubElement(
        products_node,
        "attribute",
        {"label": "'product.yield.managed.treat.'+treatment"},
    )
    et.SubElement(
        product_yield_treat,
        "expression",
        {
            "statement": product_curve_expr,
            "by": "1",
            "ignoreMissingAttributes": "false",
        },
    )
    validate_forestmodel_xml_tree(
        root=forestmodel_root,
        required_define_fields=(
            "status",
            "origin",
            "statecode",
            "au",
            "auf",
            "oper",
            "ct",
            "aux",
            "hasnatcurve",
            "treatment",
            "managed",
            "unmanaged",
            "operable",
            "lowoper",
            "frd",
        ),
        required_curve_ids=("unity", "le10"),
        require_cc_treatment=True,
    )
    write_forestmodel_xml(root=forestmodel_root, path=forestmodel_xml_path)

    headless_runtime_common_path.write_text(
        dedent(
            """
            /*
             * Shared helpers for FEMIC-triggered no-GUI Patchworks runs.
             * MKRF canonical runtime variant: lowercase managed yield targets.
             */

            boolean femicHeadlessMode = false;
            String femicHeadlessStageLabel = "headless_runs/femic";
            int femicHeadlessIterations = 1;
            double femicHeadlessImprovement = 0.0d;
            String femicHeadlessTraceLogPath = null;
            String femicHeadlessScenarioMode = "none";
            String femicHeadlessScenarioTargetLabel = null;
            Double femicHeadlessScenarioMinAnnual = null;

            String femicThrowableToString(Throwable ex) {
               java.io.StringWriter sw = new java.io.StringWriter();
               java.io.PrintWriter pw = new java.io.PrintWriter(sw);
               ex.printStackTrace(pw);
               pw.flush();
               return sw.toString();
            }

            void femicHeadlessTrace(String message) {
               String line = "[FEMIC headless] " + message;
               print(line);
               if (femicHeadlessTraceLogPath == null || femicHeadlessTraceLogPath.trim().length() == 0)
                  return;

               java.io.PrintWriter writer = null;
               try {
                  java.io.File traceFile = new java.io.File(femicHeadlessTraceLogPath);
                  java.io.File parent = traceFile.getParentFile();
                  if (parent != null)
                     parent.mkdirs();
                  writer = new java.io.PrintWriter(new java.io.FileWriter(traceFile, true));
                  writer.println(line);
                  writer.flush();
               } catch (Throwable ex) {
                  print("[FEMIC headless] trace write failed: " + ex);
               } finally {
                  if (writer != null)
                     writer.close();
               }
            }

            boolean femicConfigureHeadlessFromArgs() {
               if (args == void || args.length < 2)
                  return false;

               if (!"__femic_headless__".equals(args[1]))
                  return false;

               femicHeadlessMode = true;

               if (args.length >= 3 && args[2] != null && args[2].trim().length() > 0)
                  femicHeadlessStageLabel = args[2].trim();

               if (args.length >= 4 && args[3] != null && args[3].trim().length() > 0)
                  femicHeadlessIterations = Integer.parseInt(args[3].trim());

               if (args.length >= 5 && args[4] != null && args[4].trim().length() > 0)
                  femicHeadlessImprovement = Double.parseDouble(args[4].trim());

               if (args.length >= 6 && args[5] != null && args[5].trim().length() > 0)
                  femicHeadlessTraceLogPath = args[5].trim();

               if (args.length >= 7 && args[6] != null && args[6].trim().length() > 0)
                  femicHeadlessScenarioMode = args[6].trim();

               if (args.length >= 8 && args[7] != null && args[7].trim().length() > 0)
                  femicHeadlessScenarioTargetLabel = args[7].trim();

               if (args.length >= 9 && args[8] != null && args[8].trim().length() > 0)
                  femicHeadlessScenarioMinAnnual = new Double(Double.parseDouble(args[8].trim()));

               femicHeadlessTrace("mode enabled: stage="
                                  + femicHeadlessStageLabel
                                  + " iterations="
                                  + femicHeadlessIterations
                                  + " improvement="
                                  + femicHeadlessImprovement
                                  + " scenario_mode="
                                  + femicHeadlessScenarioMode
                                  + " scenario_target="
                                  + femicHeadlessScenarioTargetLabel
                                  + " scenario_min_annual="
                                  + femicHeadlessScenarioMinAnnual
                                  + " trace="
                                  + femicHeadlessTraceLogPath);
               return true;
            }

            void femicConfigureHeadlessScenario() {
               String mode = femicHeadlessScenarioMode == null ? "none" : femicHeadlessScenarioMode.trim();
               if (mode.length() == 0 || "none".equalsIgnoreCase(mode)) {
                  femicHeadlessTrace("no headless scenario mode requested");
                  return;
               }

               if ("max-even-flow-smoke".equalsIgnoreCase(mode)) {
                  String targetLabel = femicHeadlessScenarioTargetLabel;
                  if (targetLabel == null || targetLabel.trim().length() == 0)
                     targetLabel = "product.yield.managed.total";

                  double minAnnual = 1000.0d;
                  if (femicHeadlessScenarioMinAnnual != null)
                     minAnnual = femicHeadlessScenarioMinAnnual.doubleValue();

                  Target target = control.getTarget(targetLabel);
                  if (target == null)
                     throw new IllegalStateException("Missing headless scenario target: " + targetLabel);

                  femicHeadlessTrace("validated max-even-flow smoke target="
                                     + targetLabel
                                     + " minAnnual="
                                     + minAnnual);
                  return;
               }

               throw new IllegalStateException("Unsupported FEMIC headless scenario mode: " + mode);
            }

            void femicConfigureHeadlessBaseHarvestTarget(String targetLabel, double minAnnual) {
               Target target = control.getTarget(targetLabel);
               if (target == null)
                  throw new IllegalStateException("Missing headless scenario target: " + targetLabel);

               target.setActive(true);
               target.setMinActive(true);
               target.setMaxActive(true);
               target.setLinear(true);

               target.setMaximum(200000f, 0);
               for (int i = 1; i < Horizon.periods; i++) {
                  target.setMinimum((float)(minAnnual * Horizon.intervals[i]), i);
                  target.setMaximum(200000f, i);
               }
            }

            void femicConfigureHeadlessEvenFlowTarget(String targetLabel) {
               Target target = control.getTarget(targetLabel);
               if (target == null)
                  throw new IllegalStateException("Missing headless scenario target: " + targetLabel);

               target.setActive(true);
               target.setMinActive(true);
               target.setMaxActive(true);

               for (int i = 0; i < Horizon.periods; i++) {
                  target.setMinimum(0f, i);
                  target.setMaximum(0f, i);
                  target.setMinWeight(100f, i);
                  target.setMaxWeight(100f, i);
               }
            }

            void femicWaitHeadlessIterations(int waitCount) {
               if (waitCount <= 0) {
                  femicHeadlessTrace("wait count <= 0; skipping scheduler wait");
                  return;
               }

               if (femicHeadlessImprovement > 0.0d)
                  femicHeadlessTrace("waiting for progress: attempts="
                                     + waitCount
                                     + " improvement="
                                     + femicHeadlessImprovement);
               else
                  femicHeadlessTrace("waiting for iterations: attempts=" + waitCount);

               if (femicHeadlessImprovement > 0.0d)
                  control.waitForProgress(waitCount, femicHeadlessImprovement);
               else
                  control.waitForIterations(waitCount);

               femicHeadlessTrace("wait completed; isSuspended=" + control.isSuspended());
            }

            void femicRunHeadlessStage() {
               try {
                  femicHeadlessTrace("run stage entered; isSuspended=" + control.isSuspended());
                  femicConfigureHeadlessScenario();

                  if ("max-even-flow-smoke".equalsIgnoreCase(femicHeadlessScenarioMode)) {
                     String requestedTargetLabel = femicHeadlessScenarioTargetLabel;
                     if (requestedTargetLabel == null || requestedTargetLabel.trim().length() == 0)
                        requestedTargetLabel = "product.yield.managed.total";

                     String baseTargetLabel = requestedTargetLabel;
                     if (requestedTargetLabel.startsWith("flow.even."))
                        baseTargetLabel = requestedTargetLabel.substring("flow.even.".length());

                     String flowTargetLabel = "flow.even." + baseTargetLabel;
                     double minAnnual = 1000.0d;
                     if (femicHeadlessScenarioMinAnnual != null)
                        minAnnual = femicHeadlessScenarioMinAnnual.doubleValue();

                     femicConfigureHeadlessBaseHarvestTarget(baseTargetLabel, minAnnual);
                     femicHeadlessTrace("seeded underlying harvest target="
                                        + baseTargetLabel
                                        + " minAnnual="
                                        + minAnnual
                                        + " linear=true max=200000");

                     int seedIterations = femicHeadlessIterations;
                     int flowIterations = 0;
                     if (control.getTarget(flowTargetLabel) != null && femicHeadlessIterations > 1) {
                        seedIterations = Math.max(1, femicHeadlessIterations / 2);
                        flowIterations = femicHeadlessIterations - seedIterations;
                     }

                     femicHeadlessTrace("delegating scheduler start to waitFor*; initial isSuspended="
                                        + control.isSuspended());
                     femicWaitHeadlessIterations(seedIterations);

                     if (flowIterations > 0) {
                        if (!control.isSuspended()) {
                           femicHeadlessTrace("issuing suspend between seed and flow phases");
                           control.suspend();
                        }

                        femicConfigureHeadlessEvenFlowTarget(flowTargetLabel);
                        femicHeadlessTrace("activated even-flow companion target="
                                           + flowTargetLabel
                                           + " target=0 weight=100 after seed phase");
                        femicHeadlessTrace("delegating scheduler restart to waitFor* after seed phase; initial isSuspended="
                                           + control.isSuspended());
                        femicWaitHeadlessIterations(flowIterations);
                     }
                  } else if (femicHeadlessIterations > 0) {
                     femicHeadlessTrace("delegating scheduler start to waitFor*; initial isSuspended="
                                        + control.isSuspended());
                     femicWaitHeadlessIterations(femicHeadlessIterations);
                  } else {
                     femicHeadlessTrace("iterations <= 0; skipping scheduler wait");
                  }
               } finally {
                  if (!control.isSuspended()) {
                     femicHeadlessTrace("issuing suspend after wait");
                     control.suspend();
                  } else {
                     femicHeadlessTrace("scheduler already suspended before cleanup");
                  }
               }

               femicHeadlessTrace("saving stage " + femicHeadlessStageLabel);
               reportWriter.saveStage(femicHeadlessStageLabel);
               femicHeadlessTrace("saveStage completed");
            }

            void femicQueueHeadlessStage() {
               if (!femicHeadlessMode)
                  return;

               Runnable worker = new Runnable() {
                  public void run() {
                     try {
                        femicHeadlessTrace("worker thread started");
                        femicHeadlessTrace("waiting until initialized");
                        control.waitUntilInitialized();
                        femicHeadlessTrace("waitUntilInitialized completed");
                        femicRunHeadlessStage();
                     } catch (InterruptedException ex) {
                        femicHeadlessTrace("stage interrupted: " + ex);
                     } catch (Throwable ex) {
                        femicHeadlessTrace("stage failed: " + ex);
                        femicHeadlessTrace(femicThrowableToString(ex));
                        ex.printStackTrace();
                     }
                  }
               };

               Thread headlessThread = new Thread(worker, "femic-headless-stage");
               headlessThread.setDaemon(false);
               femicHeadlessTrace("starting worker thread");
               headlessThread.start();
            }
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    flow_targets_script_path.write_text(
        dedent(
            """
            /*************************************************************
             *
             * Configure flow ratio accounts for managed yield accounts.
             * MKRF canonical runtime variant: lowercase managed yield accounts.
             *
             *************************************************************/

            _resolveAccountsFile(String tracksPathPrefix) {
               String accountsPath = "../tracks/accounts.csv";
               if (tracksPathPrefix != null) {
                  accountsPath = tracksPathPrefix + "accounts.csv";
               }

               File accountsFile = AttributeStore.absoluteFile(accountsPath);
               if (accountsFile == null) {
                  accountsFile = new File(accountsPath).getAbsoluteFile();
               }
               return accountsFile;
            }

            _collectAccounts(String prefix, String tracksPathPrefix) {
               TreeSet out = new TreeSet();
               File accountsFile = _resolveAccountsFile(tracksPathPrefix);
               if (!accountsFile.exists()) {
                  throw new IllegalStateException("Missing tracks/accounts.csv: " + accountsFile.getPath());
               }

               BufferedReader reader = new BufferedReader(new FileReader(accountsFile));
               try {
                  String line = null;
                  boolean first = true;
                  while ((line = reader.readLine()) != null) {
                     if (first) {
                        first = false;
                        continue;
                     }
                     String[] parts = line.split(",");
                     if (parts.length < 3) {
                        continue;
                     }
                     String account = parts[2].trim();
                     if (account.startsWith(prefix)) {
                        out.add(account);
                     }
                  }
               } finally {
                  reader.close();
               }

               return out;
            }

            setupYieldFlowTargets(control, int periods) {
               setupYieldFlowTargets(control, periods, null);
            }

            setupYieldFlowTargets(control, int periods, String tracksPathPrefix) {
               FlowSpec evenflow = new FlowSpec().even();
               int ndyStart = Math.max(1, periods - 9);
               FlowSpec ndyflow = new FlowSpec().ndy(ndyStart, periods, -1);

               TreeSet productAccounts = _collectAccounts("product.yield.managed.", tracksPathPrefix);
               TreeSet featureAccounts = _collectAccounts("feature.yield.managed.", tracksPathPrefix);

               for (Iterator it = productAccounts.iterator(); it.hasNext();) {
                  String account = (String)it.next();
                  control.addFlowRatioAccount("flow.even." + account, account, evenflow, 100);
               }

               for (Iterator it = featureAccounts.iterator(); it.hasNext();) {
                  String account = (String)it.next();
                  control.addFlowRatioAccount("flow.ndy." + account, account, ndyflow, 100);
               }

               print("Configured flow targets: even=" + productAccounts.size() + " ndy=" + featureAccounts.size());
            }
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    analysis_pin_path.write_text(
        dedent(
            """
            /*
             * Minimal canonical MKRF Patchworks control lane.
             * Generated by FEMIC for headless/runtime smoke use.
             */

            int periods = 30;
            Horizon.setHorizon(periods, 10);

            boolean useRoutes = false;
            boolean usePatches = false;

            String tracks_path_prefix = "../tracks/";
            sourceRelative("headless_runtime_common.bsh");
            sourceRelative("../scripts/targets/flowtargets.bsh");

            blocks = tracks_path_prefix + "blocks.csv";
            curves = tracks_path_prefix + "curves.csv";
            features = tracks_path_prefix + "features.csv";
            products = tracks_path_prefix + "products.csv";
            tracknames = tracks_path_prefix + "tracknames.csv";
            treatments = tracks_path_prefix + "treatments.csv";
            accounts = tracks_path_prefix + "accounts.csv";
            stratas = tracks_path_prefix + "strata.csv";
            if (
                AttributeStore.absoluteFile(tracks_path_prefix + "packages.csv").exists()
                && AttributeStore.absoluteFile(tracks_path_prefix + "packageSequences.csv").exists()
            ) {
               packages = tracks_path_prefix + "packages.csv";
               sequences = tracks_path_prefix + "packageSequences.csv";
            }

            block_shape = "../spatial/fragments.shp";
            block_key = "RES_KEY";

            int Patchworks_TargetInit() {
               setupYieldFlowTargets(control, periods, tracks_path_prefix);
               return 1;
            }

            int PatchWorks_Init() {
               femicConfigureHeadlessFromArgs();

               if (!femicHeadlessMode) {
                  classic_GUI(control);

                  DefaultTheme def = new DefaultTheme(
                     blockData,
                     new PolygonSymbol(new Color(128, 128, 128, 128))
                  );
                  def.setCaption("Forest Outline");
                  Layer defLayer = new GeoRelLayer(blockData, def);
                  layers.add(defLayer);

                  NumericTheme ageClassTheme = new NumericTheme(blockData);
                  ageClassTheme.setFieldname("0.5 * (MANAGEDOFFSET + UNMANAGEDOFFSET)");
                  ageClassTheme.addElement(
                     new ThemeElement(
                        "age_000_019",
                        PolygonSymbol.getDefault(Symbol.FILL, Symbol.APPLE, 0)
                     ),
                     "0 - 19"
                  );
                  ageClassTheme.addElement(
                     new ThemeElement(
                        "age_020_039",
                        PolygonSymbol.getDefault(Symbol.FILL, Symbol.APPLE, 1)
                     ),
                     "20 - 39"
                  );
                  ageClassTheme.addElement(
                     new ThemeElement(
                        "age_040_059",
                        PolygonSymbol.getDefault(Symbol.FILL, Symbol.APPLE, 2)
                     ),
                     "40 - 59"
                  );
                  ageClassTheme.addElement(
                     new ThemeElement(
                        "age_060_079",
                        PolygonSymbol.getDefault(Symbol.FILL, Symbol.APPLE, 3)
                     ),
                     "60 - 79"
                  );
                  ageClassTheme.addElement(
                     new ThemeElement(
                        "age_080_099",
                        PolygonSymbol.getDefault(Symbol.FILL, Symbol.APPLE, 4)
                     ),
                     "80 - 99"
                  );
                  ageClassTheme.addElement(
                     new ThemeElement(
                        "age_100_119",
                        PolygonSymbol.getDefault(Symbol.FILL, Symbol.APPLE, 5)
                     ),
                     "100 - 119"
                  );
                  ageClassTheme.addElement(
                     new ThemeElement(
                        "age_120_139",
                        PolygonSymbol.getDefault(Symbol.FILL, Symbol.APPLE, 6)
                     ),
                     "120 - 139"
                  );
                  ageClassTheme.addElement(
                     new ThemeElement(
                        "age_140_159",
                        PolygonSymbol.getDefault(Symbol.FILL, Symbol.APPLE, 7)
                     ),
                     "140 - 159"
                  );
                  ageClassTheme.addElement(
                     new ThemeElement(
                        "age_160_179",
                        PolygonSymbol.getDefault(Symbol.FILL, Symbol.APPLE, 8)
                     ),
                     "160 - 179"
                  );
                  ageClassTheme.addElement(
                     new ThemeElement(
                        "age_180_199",
                        PolygonSymbol.getDefault(Symbol.FILL, Symbol.APPLE, 9)
                     ),
                     "180 - 199"
                  );
                  ageClassTheme.addElement(
                     new ThemeElement(
                        "age_200plus",
                        PolygonSymbol.getDefault(Symbol.FILL, Symbol.APPLE, 10)
                     ),
                     "200 - 99999"
                  );
                  ageClassTheme.setCaption("Age Class (20-year)");
                  ageClassTheme.setUnclassified(new ThemeElement("", PolygonSymbol.erase));
                  blockData.addTheme(ageClassTheme);
                  GeoRelLayer ageClassLayer = new GeoRelLayer(blockData, ageClassTheme);
                  ageClassLayer.setVisible(false);
                  layers.add(ageClassLayer);

                  UniqueValueTheme currTreatTheme = new UniqueValueTheme(blockData);
                  currTreatTheme.setFieldname("CURRENTTREATMENT");
                  currTreatTheme.addElement(
                     new ThemeElement(
                        "CC",
                        PolygonSymbol.getDefault(Symbol.FILL, Symbol.GEMS, 0)
                     ),
                     "CC"
                  );
                  currTreatTheme.addElement(
                     new ThemeElement(
                        "CT35",
                        PolygonSymbol.getDefault(Symbol.FILL, Symbol.GEMS, 1)
                     ),
                     "CT35"
                  );
                  currTreatTheme.addElement(
                     new ThemeElement(
                        "CT40",
                        PolygonSymbol.getDefault(Symbol.FILL, Symbol.GEMS, 2)
                     ),
                     "CT40"
                  );
                  currTreatTheme.addElement(
                     new ThemeElement(
                        "CT45",
                        PolygonSymbol.getDefault(Symbol.FILL, Symbol.GEMS, 3)
                     ),
                     "CT45"
                  );
                  currTreatTheme.setCaption("Current Treatments");
                  currTreatTheme.setUnclassified(new ThemeElement("", PolygonSymbol.erase));
                  blockData.addTheme(currTreatTheme);
                  GeoRelLayer currTreatLayer = new GeoRelLayer(blockData, currTreatTheme);
                  currTreatLayer.setVisible(false);
                  layers.add(currTreatLayer);

                  UniqueValueTheme latestTreatTheme = new UniqueValueTheme(blockData);
                  latestTreatTheme.setFieldname("LASTTREATMENT");
                  latestTreatTheme.addElement(
                     new ThemeElement(
                        "CC",
                        PolygonSymbol.getDefault(Symbol.FILL, Symbol.GEMS, 0)
                     ),
                     "CC"
                  );
                  latestTreatTheme.addElement(
                     new ThemeElement(
                        "CT35",
                        PolygonSymbol.getDefault(Symbol.FILL, Symbol.GEMS, 1)
                     ),
                     "CT35"
                  );
                  latestTreatTheme.addElement(
                     new ThemeElement(
                        "CT40",
                        PolygonSymbol.getDefault(Symbol.FILL, Symbol.GEMS, 2)
                     ),
                     "CT40"
                  );
                  latestTreatTheme.addElement(
                     new ThemeElement(
                        "CT45",
                        PolygonSymbol.getDefault(Symbol.FILL, Symbol.GEMS, 3)
                     ),
                     "CT45"
                  );
                  latestTreatTheme.setCaption("Latest Treatments");
                  latestTreatTheme.setUnclassified(new ThemeElement("", PolygonSymbol.erase));
                  blockData.addTheme(latestTreatTheme);
                  GeoRelLayer latestTreatLayer = new GeoRelLayer(blockData, latestTreatTheme);
                  latestTreatLayer.setVisible(false);
                  layers.add(latestTreatLayer);

                  if (usePatches) {
                     NumericTheme patch0Theme = new NumericTheme(blockData);
                     patch0Theme.setFieldname("product.area.managed.treat.CC.size");
                     patch0Theme.addElement(
                        new ThemeElement(
                           "0_1",
                           PolygonSymbol.getDefault(Symbol.FILL, Symbol.APPLE, 0)
                        ),
                        "0.001 - 1.0"
                     );
                     patch0Theme.addElement(
                        new ThemeElement(
                           "1_5",
                           PolygonSymbol.getDefault(Symbol.FILL, Symbol.APPLE, 1)
                        ),
                        "1.0 - 5.0"
                     );
                     patch0Theme.addElement(
                        new ThemeElement(
                           "5_40",
                           PolygonSymbol.getDefault(Symbol.FILL, Symbol.APPLE, 2)
                        ),
                        "5.0 - 40.0"
                     );
                     patch0Theme.addElement(
                        new ThemeElement(
                           "40_50",
                           PolygonSymbol.getDefault(Symbol.FILL, Symbol.APPLE, 3)
                        ),
                        "40.0 - 50.0"
                     );
                     patch0Theme.addElement(
                        new ThemeElement(
                           "50plus",
                           PolygonSymbol.getDefault(Symbol.FILL, Symbol.APPLE, 4)
                        ),
                        "50.0 - 99999.0"
                     );
                     patch0Theme.setCaption("patch.grpblk patches");
                     patch0Theme.setUnclassified(new ThemeElement("", PolygonSymbol.erase));
                     blockData.addTheme(patch0Theme);
                     GeoRelLayer patch0Layer = new GeoRelLayer(blockData, patch0Theme);
                     layers.add(patch0Layer);

                     NumericTheme patch1Theme = new NumericTheme(blockData);
                     patch1Theme.setFieldname("feature.area.managed.seral.le10.size");
                     patch1Theme.addElement(
                        new ThemeElement(
                           "0_40",
                           PolygonSymbol.getDefault(Symbol.FILL, Symbol.APPLE, 0)
                        ),
                        "0.001 - 40.0"
                     );
                     patch1Theme.addElement(
                        new ThemeElement(
                           "40_50",
                           PolygonSymbol.getDefault(Symbol.FILL, Symbol.APPLE, 1)
                        ),
                        "40.0 - 50.0"
                     );
                     patch1Theme.addElement(
                        new ThemeElement(
                           "50plus",
                           PolygonSymbol.getDefault(Symbol.FILL, Symbol.APPLE, 2)
                        ),
                        "50.0 - 99999.0"
                     );
                     patch1Theme.setCaption("patch.sepblk patches");
                     patch1Theme.setUnclassified(new ThemeElement("", PolygonSymbol.erase));
                     blockData.addTheme(patch1Theme);
                     GeoRelLayer patch1Layer = new GeoRelLayer(blockData, patch1Theme);
                     layers.add(patch1Layer);
                  }
               }

               if (femicHeadlessMode)
                  femicQueueHeadlessStage();

               return 1;
            }
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    manifest_payload = {
        "schema_version": 1,
        "package_root": str(package_root),
        "runtime_generation_status": "initialized_only",
        "source_contracts": {
            "selected_au_csv": str(selected_au_csv.resolve()),
            "stand_origin_assignment_csv": str(stand_origin_assignment_csv.resolve()),
            "stand_au_assignment_csv": str(stand_au_assignment_csv.resolve()),
            "managed_bootstrap_csv": str(managed_bootstrap_csv.resolve()),
            "first_growth_curves_csv": str(first_growth_curves_csv.resolve()),
            "first_growth_diagnostics_csv": str(first_growth_diagnostics_csv.resolve()),
            "managed_curves_csv": str(managed_curves_csv.resolve()),
            "managed_run_manifest_json": str(managed_run_manifest_json.resolve()),
            "bad_curve_audit_summary_csv": str(bad_curve_audit_summary_csv.resolve()),
            "runtime_curve_status_csv": str(curve_status_path.resolve()),
            "analysis_au_runtime_status_csv": str(analysis_au_runtime_status_path.resolve()),
            "analysis_au_curve_refs_csv": str(analysis_au_curve_refs_path.resolve()),
            "runtime_au_remap_audit_csv": str(runtime_au_remap_audit_path.resolve()),
            "runtime_species_share_audit_csv": str(species_share_audit_path.resolve()),
            "ct_eligibility_audit_csv": str(ct_eligibility_audit_path.resolve()),
            "ct_intensity_audit_csv": str(ct_intensity_audit_path.resolve()),
            "ct_intensity_summary_csv": str(ct_intensity_summary_path.resolve()),
            "hw_ingrowth_overlay_audit_csv": str(
                hw_ingrowth_overlay_audit_path.resolve()
            ),
            "hw_ingrowth_overlay_summary_csv": str(
                hw_ingrowth_overlay_summary_path.resolve()
            ),
            "runtime_curve_contract_xml": str(xml_contract_path.resolve()),
            "runtime_curve_bank_xml": str(xml_curve_bank_path.resolve()),
            "forestmodel_xml": str(forestmodel_xml_path.resolve()),
            "analysis_pin": str(analysis_pin_path.resolve()),
            "headless_runtime_common_bsh": str(headless_runtime_common_path.resolve()),
            "flow_targets_bsh": str(flow_targets_script_path.resolve()),
        },
        "counts": {
            "selected_au_count": selected_au_count,
            "first_growth_curve_au_count": first_growth_curve_au_count,
            "first_growth_missing_au_count": first_growth_missing_au_count,
            "managed_curve_au_count": managed_curve_au_count,
            "bad_curve_flagged_au_count": flagged_au_count,
            "managed_only_runtime_au_count": int(
                runtime_curve_status["runtime_curve_mode"].eq("managed_only").sum()
            ),
        },
        "runtime_au_normalization": {
            "selected_passthrough_count": int((~remap_audit["was_remapped"]).sum()),
            "remapped_source_au_count": int(remap_audit["was_remapped"].sum()),
            "remapped_forest_cover_id_count": int(
                remap_audit.loc[remap_audit["was_remapped"], "forest_cover_id_count"].sum()
            ),
        },
        "curve_policy": {
            "first_growth_curve_family": "smoothed_bin_pchip",
            "first_growth_borrowing_allowed": False,
            "managed_only_runtime_units_allowed": True,
        },
        "managed_only_runtime_policy": {
            "insufficient_support_requires_first_growth_curve": False,
            "insufficient_support_fallback_generation": "forbidden",
            "insufficient_support_borrowing": "forbidden",
        },
        "managed_run_summary": {
            "status": managed_manifest.get("status"),
            "curve_au_count": managed_manifest.get("curve_au_count"),
            "included_au_count": managed_manifest.get("included_au_count"),
        },
    }
    manifest_path.write_text(
        json.dumps(manifest_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    if not readme_path.exists():
        readme_path.write_text(
            "\n".join(
                [
                    "# MKRF Patchworks Canonical Rebuild Package",
                    "",
                    "This directory is the target home for the source-faithful MKRF rebuild package",
                    "tracked under `P60.8+`.",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

    return MkrfRuntimePackageInitResult(
        package_root=package_root,
        readme_path=readme_path,
        manifest_path=manifest_path,
        curve_status_path=curve_status_path,
        analysis_au_runtime_status_path=analysis_au_runtime_status_path,
        analysis_au_curve_refs_path=analysis_au_curve_refs_path,
        runtime_au_remap_audit_path=runtime_au_remap_audit_path,
        species_share_audit_path=species_share_audit_path,
        ct_eligibility_audit_path=ct_eligibility_audit_path,
        ct_intensity_audit_path=ct_intensity_audit_path,
        ct_intensity_summary_path=ct_intensity_summary_path,
        hw_ingrowth_overlay_audit_path=hw_ingrowth_overlay_audit_path,
        hw_ingrowth_overlay_summary_path=hw_ingrowth_overlay_summary_path,
        analysis_pin_path=analysis_pin_path,
        headless_runtime_common_path=headless_runtime_common_path,
        flow_targets_script_path=flow_targets_script_path,
        xml_contract_path=xml_contract_path,
        xml_curve_bank_path=xml_curve_bank_path,
        forestmodel_xml_path=forestmodel_xml_path,
        selected_au_count=selected_au_count,
        first_growth_curve_au_count=first_growth_curve_au_count,
        first_growth_missing_au_count=first_growth_missing_au_count,
        managed_curve_au_count=managed_curve_au_count,
    )


def _read_track_attribute_labels(csv_path: Path) -> set[str]:
    if not csv_path.exists():
        return set()
    frame = pd.read_csv(csv_path)
    for column in ("ATTRIBUTE", "attribute", "LABEL", "label"):
        if column in frame.columns:
            return set(frame[column].astype(str).str.strip())
    return set()


def _target_signal_status(target_csv_path: Path) -> tuple[bool, float | None]:
    if not target_csv_path.exists():
        return False, None
    frame = pd.read_csv(target_csv_path)
    if "CURRENT" not in frame.columns:
        return False, None
    current = pd.to_numeric(frame["CURRENT"], errors="coerce").fillna(0.0)
    max_signal = float(current.abs().max()) if not current.empty else 0.0
    return bool(max_signal > 0), max_signal


def audit_mkrf_runtime_sanity(
    *,
    package_root: Path,
    stage_dir: Path,
) -> MkrfRuntimeSanityAuditResult:
    """Audit canonical MKRF runtime signal against published species-share sources."""
    package_root = package_root.resolve()
    stage_dir = stage_dir.resolve()
    analysis_dir = package_root / "analysis"
    tracks_dir = package_root / "tracks"
    targets_dir = stage_dir / "targets"
    sanity_dir = stage_dir / "sanity"
    sanity_dir.mkdir(parents=True, exist_ok=True)
    audit_csv_path = sanity_dir / "mkrf_runtime_sanity_audit.csv"
    summary_json_path = sanity_dir / "mkrf_runtime_sanity_summary.json"
    species_share_audit_path = analysis_dir / "runtime_species_share_audit.csv"

    species_share_audit = pd.read_csv(species_share_audit_path)
    accounts_labels = _read_track_attribute_labels(tracks_dir / "accounts.csv")
    feature_labels = _read_track_attribute_labels(tracks_dir / "features.csv")
    product_labels = _read_track_attribute_labels(tracks_dir / "products.csv")

    rows: list[dict[str, object]] = []
    for ifm_lane, surface in (
        ("managed", "feature"),
        ("unmanaged", "feature"),
        ("managed", "product"),
    ):
        for bucket in _SPECIES_BUCKETS:
            label = f"{surface}.yield.{ifm_lane}.indsp.{bucket}"
            target_csv_path = targets_dir / f"{label.replace('.', '_')}.csv"
            target_has_signal, target_max_current = _target_signal_status(target_csv_path)
            track_labels = feature_labels if surface == "feature" else product_labels
            account_present = label in accounts_labels
            track_present = label in track_labels
            target_file_present = target_csv_path.exists()
            source_rows = species_share_audit.loc[
                species_share_audit["species_bucket"].astype(str).eq(bucket)
            ].copy()
            natural_nonzero = bool(
                pd.to_numeric(
                    source_rows.loc[
                        source_rows["origin_lane"].astype(str).eq("natural"), "share_pct"
                    ],
                    errors="coerce",
                )
                .fillna(0.0)
                .gt(0)
                .any()
            )
            treated_nonzero = bool(
                pd.to_numeric(
                    source_rows.loc[
                        source_rows["origin_lane"].astype(str).eq("treated"), "share_pct"
                    ],
                    errors="coerce",
                )
                .fillna(0.0)
                .gt(0)
                .any()
            )
            any_source_nonzero = natural_nonzero or treated_nonzero
            if not account_present and not track_present and not target_file_present:
                audit_status = "not_emitted"
            elif target_has_signal and not any_source_nonzero:
                audit_status = "fail_signal_without_source_share"
            elif account_present and track_present and not target_file_present:
                audit_status = "fail_missing_target_output"
            elif (not target_has_signal) and any_source_nonzero:
                audit_status = "fail_zero_signal_with_source_share"
            elif target_has_signal and any_source_nonzero:
                audit_status = "pass_signal_matches_source_share"
            else:
                audit_status = "pass_zero_signal_zero_source_share"
            rows.append(
                {
                    "surface": surface,
                    "ifm_lane": ifm_lane,
                    "species_bucket": bucket,
                    "target_label": label,
                    "target_csv_path": str(target_csv_path),
                    "account_present": account_present,
                    "track_present": track_present,
                    "target_file_present": target_file_present,
                    "target_has_signal": target_has_signal,
                    "target_max_current": target_max_current,
                    "natural_source_nonzero": natural_nonzero,
                    "treated_source_nonzero": treated_nonzero,
                    "any_source_nonzero": any_source_nonzero,
                    "audit_status": audit_status,
                }
            )

    audit_frame = pd.DataFrame(rows).sort_values(
        ["surface", "ifm_lane", "species_bucket"],
        kind="stable",
    )
    audit_frame.to_csv(audit_csv_path, index=False)
    failure_count = int(audit_frame["audit_status"].astype(str).str.startswith("fail_").sum())
    summary_payload = {
        "schema_version": 1,
        "package_root": str(package_root),
        "stage_dir": str(stage_dir),
        "row_count": int(len(audit_frame)),
        "failure_count": failure_count,
        "failures": audit_frame.loc[
            audit_frame["audit_status"].astype(str).str.startswith("fail_")
        ].to_dict(orient="records"),
    }
    summary_json_path.write_text(
        json.dumps(summary_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return MkrfRuntimeSanityAuditResult(
        package_root=package_root,
        stage_dir=stage_dir,
        audit_csv_path=audit_csv_path,
        summary_json_path=summary_json_path,
        row_count=int(len(audit_frame)),
        failure_count=failure_count,
    )
