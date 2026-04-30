"""MKRF-specific rebuild workflows."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import math

import geopandas as gpd
import numpy as np
import pandas as pd

from femic.pipeline.mkrf_au import (
    build_mkrf_au_tables,
    build_mkrf_selected_au_table,
    parse_mkrf_bec,
)
from femic.pipeline.mkrf_first_growth import (
    build_mkrf_first_growth_curves,
    collapse_stand_assignments,
)
from femic.pipeline.plots import (
    StrataDistributionPlotMetadata,
    build_strata_distribution_plot_config,
    render_strata_distribution_plot,
    resolve_strata_plot_ordering,
    strata_plot_paths,
)
from femic.pipeline.tsa import build_stratum_lexmatch_alias_map


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

    curves_path = output_dir / "first_growth_au_curves.csv"
    diagnostics_path = output_dir / "first_growth_au_fit_diagnostics.csv"
    curves.to_csv(curves_path, index=False)
    diagnostics.to_csv(diagnostics_path, index=False)
    vdyp_feature_ids = set(
        pd.to_numeric(vdyp_yields["FEATURE_ID"], errors="coerce").dropna().astype(int)
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
    output_dir: Path,
    layer: str = "Resultant",
    tsa_code: str = "mkrf",
) -> MkrfAuPlotResult:
    """Render the MKRF AU abundance/site-index distribution plot."""
    import matplotlib.pyplot as plt
    import seaborn as sns

    output_dir.mkdir(parents=True, exist_ok=True)
    assignment = pd.read_csv(assignment_csv)
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


def _tipsy_species_pair(row: pd.Series) -> tuple[str, str]:
    species_map = {
        "BA": "ba",
        "CW": "cw",
        "DR": "dr",
        "FD": "fdc",
        "HW": "hw",
        "YC": "yc",
    }
    ranked: list[tuple[str, float]] = []
    for column, species_code in species_map.items():
        raw = row.get(column)
        try:
            share = float(raw)
        except (TypeError, ValueError):
            share = 0.0
        if not math.isfinite(share) or share <= 0.0:
            continue
        ranked.append((species_code, share))
    ranked.sort(key=lambda item: (-item[1], item[0]))
    if not ranked:
        return ("x", "x")
    if len(ranked) == 1:
        return (ranked[0][0], "x")
    return (ranked[0][0], ranked[1][0])


def _build_tipsy_legacy_au_table(
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


def _build_tipsy_alias_map(
    *,
    selected_au_table: pd.DataFrame,
    legacy_au_table: pd.DataFrame,
) -> dict[str, str]:
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
        levenshtein_fn=__import__("distance").levenshtein,
    )
    for selected_id in selected_au_table["au_id"].astype(str):
        alias_map[selected_id] = selected_id
    return alias_map


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


def build_mkrf_all_plots(
    *,
    resultant_gdb: Path,
    assignment_csv: Path,
    selected_au_csv: Path,
    first_growth_curves_csv: Path,
    vdyp_yields_csv: Path,
    tipsy_yields_csv: Path,
    tipsy_spp_comp_csv: Path,
    man_si_by_au_csv: Path,
    output_dir: Path,
    layer: str = "Resultant",
    tsa_code: str = "mkrf",
) -> MkrfPlotRebuildResult:
    """Recompile MKRF diagnostic and comparison plots for the selected AU subset."""
    import matplotlib.pyplot as plt

    output_dir.mkdir(parents=True, exist_ok=True)
    strata = build_mkrf_au_distribution_plot(
        resultant_gdb=resultant_gdb,
        assignment_csv=assignment_csv,
        output_dir=output_dir,
        layer=layer,
        tsa_code=tsa_code,
    )

    assignment = pd.read_csv(assignment_csv)
    selected_au_table = pd.read_csv(selected_au_csv)
    first_growth_curves = pd.read_csv(first_growth_curves_csv)
    vdyp_yields = pd.read_csv(vdyp_yields_csv)
    tipsy_yields = pd.read_csv(tipsy_yields_csv)
    tipsy_spp_comp = pd.read_csv(tipsy_spp_comp_csv)
    man_si_by_au = pd.read_csv(man_si_by_au_csv)
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

    legacy_tipsy = _build_tipsy_legacy_au_table(
        man_si_by_au=man_si_by_au,
        tipsy_spp_comp=tipsy_spp_comp,
    )
    alias_map = _build_tipsy_alias_map(
        selected_au_table=selected_au_table,
        legacy_au_table=legacy_tipsy,
    )
    legacy_tipsy["au_id"] = legacy_tipsy["legacy_candidate_au_id"].map(
        lambda value: alias_map.get(str(value), str(value))
    )

    tipsy_vdyp_plot_count = 0
    for au_id in selected_ids:
        label = label_map[str(au_id)]
        candidates = legacy_tipsy.loc[legacy_tipsy["au_id"] == str(au_id)].copy()
        if candidates.empty:
            continue
        target_si = canonical_median_si.get(str(au_id), float("nan"))
        candidates["si_distance"] = (
            pd.to_numeric(candidates["SI"], errors="coerce").fillna(float("inf")) - target_si
        ).abs()
        candidates = candidates.sort_values(["si_distance", "AU"], kind="stable")
        legacy_au = int(candidates.iloc[0]["AU"])
        tipsy_curve = tipsy_yields.loc[tipsy_yields["AU"] == legacy_au].copy()
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
            pd.to_numeric(tipsy_curve["Age"], errors="coerce"),
            pd.to_numeric(tipsy_curve["Yield"], errors="coerce"),
            color="tab:green",
            linewidth=2.0,
            linestyle="--",
            label=f"TIPSY legacy AU {legacy_au}",
        )
        ymax = max(
            float(vdyp_curve["volume"].max()),
            float(pd.to_numeric(tipsy_curve["Yield"], errors="coerce").max()),
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
