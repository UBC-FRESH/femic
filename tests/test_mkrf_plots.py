from __future__ import annotations

from pathlib import Path

import matplotlib
import pandas as pd
import pytest

from femic.pipeline.mkrf_managed import build_mkrf_legacy_managed_au_table
from femic.workflows.mkrf import (
    MkrfAuPlotResult,
    _classify_site_index_levels,
    _filter_assignment_to_selected_aus,
    build_mkrf_all_plots,
)

matplotlib.use("Agg")


def test_classify_site_index_levels_splits_into_lmh_bins() -> None:
    levels = _classify_site_index_levels(
        pd.Series([10.0, 12.0, 20.0, 25.0, 35.0, 40.0])
    )
    assert list(levels.astype(str)) == ["L", "L", "M", "M", "H", "H"]


def test_build_tipsy_legacy_au_table_derives_bec_and_species_pair() -> None:
    man_si_by_au = pd.DataFrame(
        [
            {"AU": 101, "BEC": "CWHvm2", "SI": 28.5},
            {"AU": 102, "BEC": "MHmm1", "SI": 18.0},
        ]
    )
    tipsy_spp_comp = pd.DataFrame(
        [
            {
                "AU": 101,
                "BA": 10.0,
                "CW": 45.0,
                "DR": 0.0,
                "FD": 0.0,
                "HW": 45.0,
                "YC": 0.0,
            },
            {
                "AU": 102,
                "BA": 0.0,
                "CW": 0.0,
                "DR": 20.0,
                "FD": 60.0,
                "HW": 20.0,
                "YC": 0.0,
            },
        ]
    )

    legacy = build_mkrf_legacy_managed_au_table(
        man_si_by_au=man_si_by_au,
        tipsy_spp_comp=tipsy_spp_comp,
    ).sort_values("AU", kind="stable")

    assert list(legacy["bec_zone"]) == ["cwh", "mhm"]
    assert list(legacy["bec_subzone"]) == ["vm", "m"]
    assert list(legacy["bec_variant"]) == ["2", "1"]
    assert list(legacy["leading_species_1"]) == ["cw", "fdc"]
    assert list(legacy["leading_species_2"]) == ["hw", "dr"]
    assert list(legacy["legacy_candidate_au_id"]) == [
        "cwh_vm_2_cw_hw",
        "mhm_m_1_fdc_dr",
    ]


def test_filter_assignment_to_selected_aus_keeps_only_selected_rows() -> None:
    assignment = pd.DataFrame(
        [
            {"res_key": 1, "au_id": "a"},
            {"res_key": 2, "au_id": "b"},
            {"res_key": 3, "au_id": "c"},
        ]
    )
    selected = pd.DataFrame(
        [
            {"au_id": "b", "selected_rank": 1},
            {"au_id": "c", "selected_rank": 2},
        ]
    )

    filtered = _filter_assignment_to_selected_aus(assignment, selected)

    assert list(filtered["res_key"]) == [2, 3]
    assert list(filtered["au_id"]) == ["b", "c"]


def test_build_mkrf_all_plots_uses_managed_curve_bundle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assignment_csv = tmp_path / "stand_au_assignment.csv"
    selected_au_csv = tmp_path / "selected_au_table.csv"
    first_growth_curves_csv = tmp_path / "first_growth_au_curves.csv"
    managed_curves_csv = tmp_path / "managed_au_curves.csv"
    vdyp_yields_csv = tmp_path / "vdyp_yields.csv"
    output_dir = tmp_path / "plots"

    pd.DataFrame(
        [
            {
                "res_key": 1,
                "forest_cover_id": 101,
                "shape_area_ha": 10.0,
                "au_id": "cwh_dm_x_cw_fdc",
            },
            {
                "res_key": 2,
                "forest_cover_id": 102,
                "shape_area_ha": 10.0,
                "au_id": "cwh_dm_x_cw_fdc",
            },
            {
                "res_key": 3,
                "forest_cover_id": 103,
                "shape_area_ha": 10.0,
                "au_id": "cwh_dm_x_cw_fdc",
            },
            {
                "res_key": 4,
                "forest_cover_id": 104,
                "shape_area_ha": 10.0,
                "au_id": "cwh_dm_x_cw_fdc",
            },
            {
                "res_key": 4,
                "forest_cover_id": 104,
                "shape_area_ha": 10.0,
                "au_id": "cwh_dm_x_cw_fdc",
            },
        ]
    ).to_csv(assignment_csv, index=False)
    pd.DataFrame(
        [
            {
                "au_id": "cwh_dm_x_cw_fdc",
                "selected_rank": 1,
                "covered_area_ha": 30.0,
                "bec_zone": "cwh",
                "bec_subzone": "dm",
                "bec_variant": "x",
                "leading_species_1": "cw",
                "leading_species_2": "fdc",
            }
        ]
    ).to_csv(selected_au_csv, index=False)
    pd.DataFrame(
        [
            {"au_id": "cwh_dm_x_cw_fdc", "age": 0, "volume": 0.0},
            {"au_id": "cwh_dm_x_cw_fdc", "age": 10, "volume": 50.0},
            {"au_id": "cwh_dm_x_cw_fdc", "age": 20, "volume": 100.0},
        ]
    ).to_csv(first_growth_curves_csv, index=False)
    pd.DataFrame(
        [
            {
                "au_id": "cwh_dm_x_cw_fdc",
                "managed_curve_id": 60001,
                "age": 0,
                "volume": 0.0,
            },
            {
                "au_id": "cwh_dm_x_cw_fdc",
                "managed_curve_id": 60001,
                "age": 10,
                "volume": 60.0,
            },
            {
                "au_id": "cwh_dm_x_cw_fdc",
                "managed_curve_id": 60001,
                "age": 20,
                "volume": 110.0,
            },
        ]
    ).to_csv(managed_curves_csv, index=False)
    pd.DataFrame(
        [
            {"FEATURE_ID": 101, "PRJ_TOTAL_AGE": 30, "PRJ_VOL_DWB": 20.0},
            {"FEATURE_ID": 101, "PRJ_TOTAL_AGE": 40, "PRJ_VOL_DWB": 40.0},
            {"FEATURE_ID": 101, "PRJ_TOTAL_AGE": 50, "PRJ_VOL_DWB": 85.0},
            {"FEATURE_ID": 102, "PRJ_TOTAL_AGE": 30, "PRJ_VOL_DWB": 25.0},
            {"FEATURE_ID": 102, "PRJ_TOTAL_AGE": 40, "PRJ_VOL_DWB": 45.0},
            {"FEATURE_ID": 102, "PRJ_TOTAL_AGE": 50, "PRJ_VOL_DWB": 90.0},
            {"FEATURE_ID": 103, "PRJ_TOTAL_AGE": 30, "PRJ_VOL_DWB": 30.0},
            {"FEATURE_ID": 103, "PRJ_TOTAL_AGE": 40, "PRJ_VOL_DWB": 50.0},
            {"FEATURE_ID": 103, "PRJ_TOTAL_AGE": 50, "PRJ_VOL_DWB": 95.0},
            {"FEATURE_ID": 104, "PRJ_TOTAL_AGE": 30, "PRJ_VOL_DWB": 22.0},
            {"FEATURE_ID": 104, "PRJ_TOTAL_AGE": 40, "PRJ_VOL_DWB": 42.0},
            {"FEATURE_ID": 104, "PRJ_TOTAL_AGE": 50, "PRJ_VOL_DWB": 88.0},
            {"FEATURE_ID": 104, "PRJ_TOTAL_AGE": 0, "PRJ_VOL_DWB": 0.0},
            {"FEATURE_ID": 104, "PRJ_TOTAL_AGE": 10, "PRJ_VOL_DWB": 42.0},
            {"FEATURE_ID": 104, "PRJ_TOTAL_AGE": 20, "PRJ_VOL_DWB": 88.0},
        ]
    ).to_csv(vdyp_yields_csv, index=False)

    def _fake_distribution_plot(**_: object) -> MkrfAuPlotResult:
        strata_png = output_dir / "strata-tsamkrf.png"
        strata_pdf = output_dir / "strata-tsamkrf.pdf"
        output_dir.mkdir(parents=True, exist_ok=True)
        strata_png.write_bytes(b"png")
        strata_pdf.write_bytes(b"pdf")
        return MkrfAuPlotResult(
            resultant_gdb=tmp_path / "resultant.gdb",
            assignment_csv=assignment_csv,
            output_dir=output_dir,
            png_path=strata_png,
            pdf_path=strata_pdf,
            au_count=1,
            point_count=3,
            metadata=None,  # type: ignore[arg-type]
        )

    source_table = pd.DataFrame(
        [
            {"FOREST_COVER_ID": 101, "TCL_1_ESTIMATED_SITE_INDEX": 20.0},
            {"FOREST_COVER_ID": 102, "TCL_1_ESTIMATED_SITE_INDEX": 25.0},
            {"FOREST_COVER_ID": 103, "TCL_1_ESTIMATED_SITE_INDEX": 30.0},
        ]
    )

    monkeypatch.setattr(
        "femic.workflows.mkrf.build_mkrf_au_distribution_plot", _fake_distribution_plot
    )
    monkeypatch.setattr(
        "femic.workflows.mkrf.gpd.read_file", lambda *args, **kwargs: source_table
    )

    result = build_mkrf_all_plots(
        resultant_gdb=tmp_path / "resultant.gdb",
        assignment_csv=assignment_csv,
        selected_au_csv=selected_au_csv,
        first_growth_curves_csv=first_growth_curves_csv,
        managed_curves_csv=managed_curves_csv,
        vdyp_yields_csv=vdyp_yields_csv,
        output_dir=output_dir,
    )

    assert result.tipsy_vdyp_plot_count == 1
    assert any(output_dir.glob("tipsy_vdyp_tsamkrf-*.png"))


def test_build_mkrf_all_plots_removes_stale_plot_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assignment_csv = tmp_path / "stand_au_assignment.csv"
    selected_au_csv = tmp_path / "selected_au_table.csv"
    first_growth_curves_csv = tmp_path / "first_growth_au_curves.csv"
    managed_curves_csv = tmp_path / "managed_au_curves.csv"
    vdyp_yields_csv = tmp_path / "vdyp_yields.csv"
    output_dir = tmp_path / "plots"
    output_dir.mkdir(parents=True)

    stale_tipsy = output_dir / "tipsy_vdyp_tsamkrf-stale.png"
    stale_lmh = output_dir / "vdyp_lmh_tsamkrf-stale.png"
    stale_fit = output_dir / "vdyp_fitdiag_tsamkrf-stale.png"
    stale_tipsy.write_bytes(b"old")
    stale_lmh.write_bytes(b"old")
    stale_fit.write_bytes(b"old")

    pd.DataFrame(
        [
            {
                "res_key": 1,
                "forest_cover_id": 101,
                "shape_area_ha": 10.0,
                "au_id": "cwh_dm_x_cw_fdc",
            },
            {
                "res_key": 2,
                "forest_cover_id": 102,
                "shape_area_ha": 10.0,
                "au_id": "cwh_dm_x_cw_fdc",
            },
            {
                "res_key": 3,
                "forest_cover_id": 103,
                "shape_area_ha": 10.0,
                "au_id": "cwh_dm_x_cw_fdc",
            },
            {
                "res_key": 4,
                "forest_cover_id": 104,
                "shape_area_ha": 10.0,
                "au_id": "cwh_dm_x_cw_fdc",
            },
        ]
    ).to_csv(assignment_csv, index=False)
    pd.DataFrame(
        [
            {
                "au_id": "cwh_dm_x_cw_fdc",
                "selected_rank": 1,
                "covered_area_ha": 30.0,
                "bec_zone": "cwh",
                "bec_subzone": "dm",
                "bec_variant": "x",
                "leading_species_1": "cw",
                "leading_species_2": "fdc",
            }
        ]
    ).to_csv(selected_au_csv, index=False)
    pd.DataFrame(
        [
            {"au_id": "cwh_dm_x_cw_fdc", "age": 0, "volume": 0.0},
            {"au_id": "cwh_dm_x_cw_fdc", "age": 10, "volume": 50.0},
            {"au_id": "cwh_dm_x_cw_fdc", "age": 20, "volume": 100.0},
        ]
    ).to_csv(first_growth_curves_csv, index=False)
    pd.DataFrame(
        [
            {
                "au_id": "cwh_dm_x_cw_fdc",
                "managed_curve_id": 60001,
                "age": 0,
                "volume": 0.0,
            },
            {
                "au_id": "cwh_dm_x_cw_fdc",
                "managed_curve_id": 60001,
                "age": 10,
                "volume": 60.0,
            },
            {
                "au_id": "cwh_dm_x_cw_fdc",
                "managed_curve_id": 60001,
                "age": 20,
                "volume": 110.0,
            },
        ]
    ).to_csv(managed_curves_csv, index=False)
    pd.DataFrame(
        [
            {"FEATURE_ID": 101, "PRJ_TOTAL_AGE": 30, "PRJ_VOL_DWB": 20.0},
            {"FEATURE_ID": 101, "PRJ_TOTAL_AGE": 40, "PRJ_VOL_DWB": 40.0},
            {"FEATURE_ID": 101, "PRJ_TOTAL_AGE": 50, "PRJ_VOL_DWB": 85.0},
            {"FEATURE_ID": 102, "PRJ_TOTAL_AGE": 30, "PRJ_VOL_DWB": 25.0},
            {"FEATURE_ID": 102, "PRJ_TOTAL_AGE": 40, "PRJ_VOL_DWB": 45.0},
            {"FEATURE_ID": 102, "PRJ_TOTAL_AGE": 50, "PRJ_VOL_DWB": 90.0},
            {"FEATURE_ID": 103, "PRJ_TOTAL_AGE": 30, "PRJ_VOL_DWB": 30.0},
            {"FEATURE_ID": 103, "PRJ_TOTAL_AGE": 40, "PRJ_VOL_DWB": 50.0},
            {"FEATURE_ID": 103, "PRJ_TOTAL_AGE": 50, "PRJ_VOL_DWB": 95.0},
            {"FEATURE_ID": 104, "PRJ_TOTAL_AGE": 30, "PRJ_VOL_DWB": 22.0},
            {"FEATURE_ID": 104, "PRJ_TOTAL_AGE": 40, "PRJ_VOL_DWB": 42.0},
            {"FEATURE_ID": 104, "PRJ_TOTAL_AGE": 50, "PRJ_VOL_DWB": 88.0},
        ]
    ).to_csv(vdyp_yields_csv, index=False)

    def _fake_distribution_plot(**_: object) -> MkrfAuPlotResult:
        strata_png = output_dir / "strata-tsamkrf.png"
        strata_pdf = output_dir / "strata-tsamkrf.pdf"
        strata_png.write_bytes(b"png")
        strata_pdf.write_bytes(b"pdf")
        return MkrfAuPlotResult(
            resultant_gdb=tmp_path / "resultant.gdb",
            assignment_csv=assignment_csv,
            output_dir=output_dir,
            png_path=strata_png,
            pdf_path=strata_pdf,
            au_count=1,
            point_count=3,
            metadata=None,  # type: ignore[arg-type]
        )

    source_table = pd.DataFrame(
        [
            {"FOREST_COVER_ID": 101, "TCL_1_ESTIMATED_SITE_INDEX": 20.0},
            {"FOREST_COVER_ID": 102, "TCL_1_ESTIMATED_SITE_INDEX": 25.0},
            {"FOREST_COVER_ID": 103, "TCL_1_ESTIMATED_SITE_INDEX": 30.0},
        ]
    )

    monkeypatch.setattr(
        "femic.workflows.mkrf.build_mkrf_au_distribution_plot", _fake_distribution_plot
    )
    monkeypatch.setattr(
        "femic.workflows.mkrf.gpd.read_file", lambda *args, **kwargs: source_table
    )

    build_mkrf_all_plots(
        resultant_gdb=tmp_path / "resultant.gdb",
        assignment_csv=assignment_csv,
        selected_au_csv=selected_au_csv,
        first_growth_curves_csv=first_growth_curves_csv,
        managed_curves_csv=managed_curves_csv,
        vdyp_yields_csv=vdyp_yields_csv,
        output_dir=output_dir,
    )

    assert stale_tipsy.exists() is False
    assert stale_lmh.exists() is False
    assert stale_fit.exists() is False


def test_build_mkrf_all_plots_applies_age_floor_to_lmh_diagnostics(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assignment_csv = tmp_path / "stand_au_assignment.csv"
    selected_au_csv = tmp_path / "selected_au_table.csv"
    first_growth_curves_csv = tmp_path / "first_growth_au_curves.csv"
    managed_curves_csv = tmp_path / "managed_au_curves.csv"
    vdyp_yields_csv = tmp_path / "vdyp_yields.csv"
    output_dir = tmp_path / "plots"

    pd.DataFrame(
        [
            {
                "res_key": 1,
                "forest_cover_id": 101,
                "shape_area_ha": 10.0,
                "au_id": "cwh_dm_x_cw_fdc",
            },
            {
                "res_key": 2,
                "forest_cover_id": 102,
                "shape_area_ha": 10.0,
                "au_id": "cwh_dm_x_cw_fdc",
            },
            {
                "res_key": 3,
                "forest_cover_id": 103,
                "shape_area_ha": 10.0,
                "au_id": "cwh_dm_x_cw_fdc",
            },
            {
                "res_key": 4,
                "forest_cover_id": 104,
                "shape_area_ha": 10.0,
                "au_id": "cwh_dm_x_cw_fdc",
            },
        ]
    ).to_csv(assignment_csv, index=False)
    pd.DataFrame(
        [
            {
                "au_id": "cwh_dm_x_cw_fdc",
                "selected_rank": 1,
                "covered_area_ha": 30.0,
                "bec_zone": "cwh",
                "bec_subzone": "dm",
                "bec_variant": "x",
                "leading_species_1": "cw",
                "leading_species_2": "fdc",
            }
        ]
    ).to_csv(selected_au_csv, index=False)
    pd.DataFrame(
        [
            {"au_id": "cwh_dm_x_cw_fdc", "age": 0, "volume": 0.0},
            {"au_id": "cwh_dm_x_cw_fdc", "age": 10, "volume": 50.0},
            {"au_id": "cwh_dm_x_cw_fdc", "age": 20, "volume": 100.0},
        ]
    ).to_csv(first_growth_curves_csv, index=False)
    pd.DataFrame(
        [
            {
                "au_id": "cwh_dm_x_cw_fdc",
                "managed_curve_id": 60001,
                "age": 0,
                "volume": 0.0,
            },
            {
                "au_id": "cwh_dm_x_cw_fdc",
                "managed_curve_id": 60001,
                "age": 10,
                "volume": 60.0,
            },
            {
                "au_id": "cwh_dm_x_cw_fdc",
                "managed_curve_id": 60001,
                "age": 20,
                "volume": 110.0,
            },
        ]
    ).to_csv(managed_curves_csv, index=False)
    pd.DataFrame(
        [
            {"FEATURE_ID": 101, "PRJ_TOTAL_AGE": 0, "PRJ_VOL_DWB": 0.0},
            {"FEATURE_ID": 101, "PRJ_TOTAL_AGE": 10, "PRJ_VOL_DWB": 40.0},
            {"FEATURE_ID": 101, "PRJ_TOTAL_AGE": 20, "PRJ_VOL_DWB": 85.0},
            {"FEATURE_ID": 102, "PRJ_TOTAL_AGE": 0, "PRJ_VOL_DWB": 0.0},
            {"FEATURE_ID": 102, "PRJ_TOTAL_AGE": 10, "PRJ_VOL_DWB": 45.0},
            {"FEATURE_ID": 102, "PRJ_TOTAL_AGE": 20, "PRJ_VOL_DWB": 90.0},
            {"FEATURE_ID": 103, "PRJ_TOTAL_AGE": 0, "PRJ_VOL_DWB": 0.0},
            {"FEATURE_ID": 103, "PRJ_TOTAL_AGE": 10, "PRJ_VOL_DWB": 50.0},
            {"FEATURE_ID": 103, "PRJ_TOTAL_AGE": 20, "PRJ_VOL_DWB": 95.0},
            {"FEATURE_ID": 104, "PRJ_TOTAL_AGE": 0, "PRJ_VOL_DWB": 0.0},
            {"FEATURE_ID": 104, "PRJ_TOTAL_AGE": 10, "PRJ_VOL_DWB": 42.0},
            {"FEATURE_ID": 104, "PRJ_TOTAL_AGE": 20, "PRJ_VOL_DWB": 88.0},
        ]
    ).to_csv(vdyp_yields_csv, index=False)

    def _fake_distribution_plot(**_: object) -> MkrfAuPlotResult:
        strata_png = output_dir / "strata-tsamkrf.png"
        strata_pdf = output_dir / "strata-tsamkrf.pdf"
        output_dir.mkdir(parents=True, exist_ok=True)
        strata_png.write_bytes(b"png")
        strata_pdf.write_bytes(b"pdf")
        return MkrfAuPlotResult(
            resultant_gdb=tmp_path / "resultant.gdb",
            assignment_csv=assignment_csv,
            output_dir=output_dir,
            png_path=strata_png,
            pdf_path=strata_pdf,
            au_count=1,
            point_count=3,
            metadata=None,  # type: ignore[arg-type]
        )

    source_table = pd.DataFrame(
        [
            {
                "FOREST_COVER_ID": 101,
                "TCL_1_ESTIMATED_SITE_INDEX": 20.0,
                "AGE_2020": 40.0,
            },
            {
                "FOREST_COVER_ID": 102,
                "TCL_1_ESTIMATED_SITE_INDEX": 25.0,
                "AGE_2020": 120.0,
            },
            {
                "FOREST_COVER_ID": 103,
                "TCL_1_ESTIMATED_SITE_INDEX": 30.0,
                "AGE_2020": 130.0,
            },
        ]
    )

    monkeypatch.setattr(
        "femic.workflows.mkrf.build_mkrf_au_distribution_plot", _fake_distribution_plot
    )
    monkeypatch.setattr(
        "femic.workflows.mkrf.gpd.read_file", lambda *args, **kwargs: source_table
    )

    result = build_mkrf_all_plots(
        resultant_gdb=tmp_path / "resultant.gdb",
        assignment_csv=assignment_csv,
        selected_au_csv=selected_au_csv,
        first_growth_curves_csv=first_growth_curves_csv,
        managed_curves_csv=managed_curves_csv,
        vdyp_yields_csv=vdyp_yields_csv,
        output_dir=output_dir,
    )

    assert result.lmh_plot_count == 0
    assert result.fitdiag_plot_count == 0


def test_build_mkrf_all_plots_filters_fitdiag_overlay_to_age_eligible_stands(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assignment_csv = tmp_path / "stand_au_assignment.csv"
    selected_au_csv = tmp_path / "selected_au_table.csv"
    first_growth_curves_csv = tmp_path / "first_growth_au_curves.csv"
    managed_curves_csv = tmp_path / "managed_au_curves.csv"
    vdyp_yields_csv = tmp_path / "vdyp_yields.csv"
    output_dir = tmp_path / "plots"

    pd.DataFrame(
        [
            {
                "res_key": 1,
                "forest_cover_id": 101,
                "shape_area_ha": 10.0,
                "au_id": "cwh_dm_x_cw_fdc",
            },
            {
                "res_key": 2,
                "forest_cover_id": 102,
                "shape_area_ha": 10.0,
                "au_id": "cwh_dm_x_cw_fdc",
            },
            {
                "res_key": 3,
                "forest_cover_id": 103,
                "shape_area_ha": 10.0,
                "au_id": "cwh_dm_x_cw_fdc",
            },
            {
                "res_key": 4,
                "forest_cover_id": 104,
                "shape_area_ha": 10.0,
                "au_id": "cwh_dm_x_cw_fdc",
            },
        ]
    ).to_csv(assignment_csv, index=False)
    pd.DataFrame(
        [
            {
                "au_id": "cwh_dm_x_cw_fdc",
                "selected_rank": 1,
                "covered_area_ha": 30.0,
                "bec_zone": "cwh",
                "bec_subzone": "dm",
                "bec_variant": "x",
                "leading_species_1": "cw",
                "leading_species_2": "fdc",
            }
        ]
    ).to_csv(selected_au_csv, index=False)
    pd.DataFrame(
        [
            {"au_id": "cwh_dm_x_cw_fdc", "age": 0, "volume": 0.0},
            {"au_id": "cwh_dm_x_cw_fdc", "age": 10, "volume": 50.0},
            {"au_id": "cwh_dm_x_cw_fdc", "age": 20, "volume": 100.0},
        ]
    ).to_csv(first_growth_curves_csv, index=False)
    pd.DataFrame(
        [
            {
                "au_id": "cwh_dm_x_cw_fdc",
                "managed_curve_id": 60001,
                "age": 0,
                "volume": 0.0,
            },
            {
                "au_id": "cwh_dm_x_cw_fdc",
                "managed_curve_id": 60001,
                "age": 10,
                "volume": 60.0,
            },
            {
                "au_id": "cwh_dm_x_cw_fdc",
                "managed_curve_id": 60001,
                "age": 20,
                "volume": 110.0,
            },
        ]
    ).to_csv(managed_curves_csv, index=False)
    pd.DataFrame(
        [
            {"FEATURE_ID": 101, "PRJ_TOTAL_AGE": 30, "PRJ_VOL_DWB": 20.0},
            {"FEATURE_ID": 101, "PRJ_TOTAL_AGE": 40, "PRJ_VOL_DWB": 40.0},
            {"FEATURE_ID": 101, "PRJ_TOTAL_AGE": 50, "PRJ_VOL_DWB": 85.0},
            {"FEATURE_ID": 102, "PRJ_TOTAL_AGE": 30, "PRJ_VOL_DWB": 25.0},
            {"FEATURE_ID": 102, "PRJ_TOTAL_AGE": 40, "PRJ_VOL_DWB": 45.0},
            {"FEATURE_ID": 102, "PRJ_TOTAL_AGE": 50, "PRJ_VOL_DWB": 90.0},
            {"FEATURE_ID": 103, "PRJ_TOTAL_AGE": 30, "PRJ_VOL_DWB": 30.0},
            {"FEATURE_ID": 103, "PRJ_TOTAL_AGE": 40, "PRJ_VOL_DWB": 50.0},
            {"FEATURE_ID": 103, "PRJ_TOTAL_AGE": 50, "PRJ_VOL_DWB": 95.0},
            {"FEATURE_ID": 104, "PRJ_TOTAL_AGE": 30, "PRJ_VOL_DWB": 22.0},
            {"FEATURE_ID": 104, "PRJ_TOTAL_AGE": 40, "PRJ_VOL_DWB": 42.0},
            {"FEATURE_ID": 104, "PRJ_TOTAL_AGE": 50, "PRJ_VOL_DWB": 88.0},
        ]
    ).to_csv(vdyp_yields_csv, index=False)

    def _fake_distribution_plot(**_: object) -> MkrfAuPlotResult:
        strata_png = output_dir / "strata-tsamkrf.png"
        strata_pdf = output_dir / "strata-tsamkrf.pdf"
        output_dir.mkdir(parents=True, exist_ok=True)
        strata_png.write_bytes(b"png")
        strata_pdf.write_bytes(b"pdf")
        return MkrfAuPlotResult(
            resultant_gdb=tmp_path / "resultant.gdb",
            assignment_csv=assignment_csv,
            output_dir=output_dir,
            png_path=strata_png,
            pdf_path=strata_pdf,
            au_count=1,
            point_count=3,
            metadata=None,  # type: ignore[arg-type]
        )

    source_table = pd.DataFrame(
        [
            {
                "FOREST_COVER_ID": 101,
                "TCL_1_ESTIMATED_SITE_INDEX": 10.0,
                "AGE_2020": 40.0,
            },
            {
                "FOREST_COVER_ID": 102,
                "TCL_1_ESTIMATED_SITE_INDEX": 12.0,
                "AGE_2020": 120.0,
            },
            {
                "FOREST_COVER_ID": 103,
                "TCL_1_ESTIMATED_SITE_INDEX": 30.0,
                "AGE_2020": 130.0,
            },
            {
                "FOREST_COVER_ID": 104,
                "TCL_1_ESTIMATED_SITE_INDEX": 14.0,
                "AGE_2020": 110.0,
            },
        ]
    )

    captured_feature_ids: list[set[int]] = []
    original_build_fitdiag_summary = __import__(
        "femic.workflows.mkrf", fromlist=["_build_fitdiag_summary"]
    )._build_fitdiag_summary

    def _fake_build_first_growth_curves(
        **_: object,
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        curves = pd.DataFrame(
            [
                {"au_id": "cwh_dm_x_cw_fdc__L", "age": 1, "volume": 1.0},
                {"au_id": "cwh_dm_x_cw_fdc__L", "age": 50, "volume": 80.0},
                {"au_id": "cwh_dm_x_cw_fdc__L", "age": 100, "volume": 120.0},
                {"au_id": "cwh_dm_x_cw_fdc__L", "age": 300, "volume": 140.0},
            ]
        )
        diagnostics = pd.DataFrame(
            [
                {
                    "au_id": "cwh_dm_x_cw_fdc__L",
                    "rmse": 1.0,
                    "mape": 0.01,
                    "tail_rmse": 1.0,
                    "source_stand_count": 2,
                }
            ]
        )
        return curves, diagnostics

    def _capturing_fitdiag_summary(raw_subset: pd.DataFrame) -> pd.DataFrame:
        captured_feature_ids.append(set(raw_subset["FEATURE_ID"].astype(int).tolist()))
        return original_build_fitdiag_summary(raw_subset)

    monkeypatch.setattr(
        "femic.workflows.mkrf.build_mkrf_au_distribution_plot", _fake_distribution_plot
    )
    monkeypatch.setattr(
        "femic.workflows.mkrf.build_mkrf_first_growth_curves",
        _fake_build_first_growth_curves,
    )
    monkeypatch.setattr(
        "femic.workflows.mkrf.gpd.read_file", lambda *args, **kwargs: source_table
    )
    monkeypatch.setattr(
        "femic.workflows.mkrf._build_fitdiag_summary", _capturing_fitdiag_summary
    )

    result = build_mkrf_all_plots(
        resultant_gdb=tmp_path / "resultant.gdb",
        assignment_csv=assignment_csv,
        selected_au_csv=selected_au_csv,
        first_growth_curves_csv=first_growth_curves_csv,
        managed_curves_csv=managed_curves_csv,
        vdyp_yields_csv=vdyp_yields_csv,
        output_dir=output_dir,
    )

    assert result.lmh_plot_count == 1
    assert result.fitdiag_plot_count == 1
    assert captured_feature_ids == [{102}]
