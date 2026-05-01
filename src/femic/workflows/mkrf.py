"""MKRF-specific rebuild workflows."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path

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
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Borrow a larger accepted curve from the same BEC bucket for sparse units."""
    if diagnostics.empty:
        return curves, diagnostics

    area_by_au = (
        assignment.groupby("au_id", as_index=False)["shape_area_ha"]
        .sum()
        .rename(columns={"shape_area_ha": "covered_area_ha"})
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

    summary = diagnostics_out.merge(area_by_au, on="au_id", how="left").merge(
        terminal_curves, on="au_id", how="left"
    )
    summary["covered_area_ha"] = pd.to_numeric(summary["covered_area_ha"], errors="coerce").fillna(0.0)
    summary["terminal_volume"] = pd.to_numeric(summary["terminal_volume"], errors="coerce")

    curves_out = curves.copy()
    for _, row in summary.sort_values(["covered_area_ha", "au_id"], ascending=[False, True]).iterrows():
        target_au_id = str(row["au_id"])
        if str(row.get("selected_path", "")) != "insufficient_source_stands":
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
            if pd.isna(candidate_terminal) or float(candidate_terminal) <= 0.0:
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
        diagnostics_out.loc[diagnostics_out["au_id"] == target_au_id, "selected_path"] = (
            "borrowed_insufficient_support_neighbor"
        )
        diagnostics_out.loc[diagnostics_out["au_id"] == target_au_id, "borrowed_from_au_id"] = (
            source_au_id
        )
        diagnostics_out.loc[diagnostics_out["au_id"] == target_au_id, "borrow_reason"] = (
            "insufficient_source_stands_same_bec_largest_neighbor"
        )
        diagnostics_out.loc[diagnostics_out["au_id"] == target_au_id, "accepted"] = True

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


def _manifest_path_value(path: Path | str | None) -> str | None:
    if path is None:
        return None
    candidate = Path(path)
    try:
        return os.path.relpath(candidate.resolve(), Path.cwd().resolve()).replace("\\", "/")
    except Exception:
        return candidate.name


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
    curves, diagnostics = _apply_young_skewed_sibling_borrow(
        curves=curves,
        diagnostics=diagnostics,
        assignment=assignment,
        source_table=source_table,
    )
    curves, diagnostics = _apply_insufficient_support_merge(
        curves=curves,
        diagnostics=diagnostics,
        assignment=assignment,
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
    if level_assignment_rows:
        level_assignment = pd.DataFrame(level_assignment_rows)
        lmh_curves, lmh_diagnostics = build_mkrf_first_growth_curves(
            vdyp_yields=vdyp_yields.loc[
                vdyp_yields["FEATURE_ID"].isin(level_assignment["forest_cover_id"])
            ].copy(),
            assignment=level_assignment,
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
            stand_ids = stand_level_map.get((str(au_id), level), [])
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
    selected["flagged"] = (
        pd.to_numeric(selected["terminal_volume"], errors="coerce").fillna(0.0)
        < low_terminal_threshold
    ) | (
        (pd.to_numeric(selected["covered_area_ha"], errors="coerce").fillna(0.0) > large_area_threshold)
        & (
            pd.to_numeric(selected["terminal_volume"], errors="coerce").fillna(0.0)
            < low_large_area_threshold
        )
    )

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
    flagged_ids = set(selected.loc[selected["flagged"], "au_id"].astype(str))

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
        if pd.isna(terminal_volume):
            if age_gte_80_count == 0:
                issue_class = "no_first_growth_after_age_floor"
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

        summary_rows.append(
            {
                "selected_rank": int(selected_row["selected_rank"]),
                "au_id": au_id,
                "covered_area_ha": float(selected_row["covered_area_ha"]),
                "terminal_age": float(selected_row["terminal_age"]),
                "terminal_volume": float(selected_row["terminal_volume"]),
                "flagged": bool(selected_row["flagged"]),
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

        if au_id not in flagged_ids:
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
