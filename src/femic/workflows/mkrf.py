"""MKRF-specific rebuild workflows."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import geopandas as gpd
import pandas as pd

from femic.pipeline.mkrf_au import build_mkrf_au_tables
from femic.pipeline.mkrf_first_growth import build_mkrf_first_growth_curves
from femic.pipeline.plots import (
    StrataDistributionPlotMetadata,
    build_strata_distribution_plot_config,
    render_strata_distribution_plot,
    resolve_strata_plot_ordering,
    strata_plot_paths,
)


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
        pd.to_numeric(assignment["forest_cover_id"], errors="coerce").dropna().astype(int)
    )
    raw_unmatched_feature_ids = vdyp_feature_ids - assigned_feature_ids
    source_feature_ids = set(
        pd.to_numeric(source_table["FOREST_COVER_ID"], errors="coerce").dropna().astype(int)
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
            "site_index_median": plot_frame.groupby("au_id")["SITE_INDEX"].median().reindex(
                abundance.index
            ),
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
        site_index_xlim=(0, 40),
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
