from __future__ import annotations

import numpy as np
import pandas as pd

from femic.pipeline.mkrf_first_growth import (
    build_mkrf_first_growth_curves,
    collapse_stand_assignments,
)
from femic.workflows.mkrf import _format_mkrf_au_label


def test_collapse_stand_assignments_uses_area_and_lexical_tie_break() -> None:
    assignment = pd.DataFrame(
        [
            {
                "res_key": 1,
                "forest_cover_id": 100,
                "au_id": "cwh_vm_2_hw_cw",
                "shape_area_ha": 3.0,
            },
            {
                "res_key": 2,
                "forest_cover_id": 100,
                "au_id": "cwh_vm_2_cw_hw",
                "shape_area_ha": 3.0,
            },
            {
                "res_key": 3,
                "forest_cover_id": 101,
                "au_id": "cwh_vm_2_hw_cw",
                "shape_area_ha": 4.0,
            },
            {
                "res_key": 4,
                "forest_cover_id": 101,
                "au_id": "cwh_vm_2_cw_hw",
                "shape_area_ha": 2.0,
            },
        ]
    )

    collapsed = collapse_stand_assignments(assignment)

    row_100 = collapsed.loc[collapsed["forest_cover_id"] == 100].iloc[0]
    assert row_100["au_id"] == "cwh_vm_2_cw_hw"
    assert bool(row_100["tie_break_used"]) is True
    assert row_100["assignment_weight_basis"] == "shape_area_ha"

    row_101 = collapsed.loc[collapsed["forest_cover_id"] == 101].iloc[0]
    assert row_101["au_id"] == "cwh_vm_2_hw_cw"
    assert np.isclose(float(row_101["weight_share"]), 4.0 / 6.0)


def test_build_mkrf_first_growth_curves_groups_stands_by_au() -> None:
    assignment = pd.DataFrame(
        [
            {
                "res_key": 1,
                "forest_cover_id": 10,
                "au_id": "cwh_vm_2_hw_cw",
                "shape_area_ha": 2.0,
            },
            {
                "res_key": 2,
                "forest_cover_id": 10,
                "au_id": "cwh_vm_2_hw_cw",
                "shape_area_ha": 1.0,
            },
            {
                "res_key": 3,
                "forest_cover_id": 11,
                "au_id": "cwh_vm_2_hw_cw",
                "shape_area_ha": 1.0,
            },
            {
                "res_key": 4,
                "forest_cover_id": 12,
                "au_id": "cwh_dm_x_act_dr",
                "shape_area_ha": 1.0,
            },
        ]
    )
    vdyp_yields = pd.DataFrame(
        [
            {"FEATURE_ID": 10, "PRJ_TOTAL_AGE": 0, "PRJ_VOL_DWB": 5.0},
            {"FEATURE_ID": 10, "PRJ_TOTAL_AGE": 50, "PRJ_VOL_DWB": 35.0},
            {"FEATURE_ID": 10, "PRJ_TOTAL_AGE": 100, "PRJ_VOL_DWB": 70.0},
            {"FEATURE_ID": 10, "PRJ_TOTAL_AGE": 150, "PRJ_VOL_DWB": 90.0},
            {"FEATURE_ID": 11, "PRJ_TOTAL_AGE": 0, "PRJ_VOL_DWB": 8.0},
            {"FEATURE_ID": 11, "PRJ_TOTAL_AGE": 50, "PRJ_VOL_DWB": 40.0},
            {"FEATURE_ID": 11, "PRJ_TOTAL_AGE": 100, "PRJ_VOL_DWB": 80.0},
            {"FEATURE_ID": 11, "PRJ_TOTAL_AGE": 150, "PRJ_VOL_DWB": 95.0},
            {"FEATURE_ID": 12, "PRJ_TOTAL_AGE": 0, "PRJ_VOL_DWB": 3.0},
            {"FEATURE_ID": 12, "PRJ_TOTAL_AGE": 50, "PRJ_VOL_DWB": 25.0},
            {"FEATURE_ID": 12, "PRJ_TOTAL_AGE": 100, "PRJ_VOL_DWB": 60.0},
            {"FEATURE_ID": 12, "PRJ_TOTAL_AGE": 150, "PRJ_VOL_DWB": 70.0},
        ]
    )

    curves, diagnostics = build_mkrf_first_growth_curves(
        vdyp_yields=vdyp_yields,
        assignment=assignment,
        min_source_stands=1,
    )

    assert sorted(curves["au_id"].unique().tolist()) == [
        "cwh_dm_x_act_dr",
        "cwh_vm_2_hw_cw",
    ]
    assert len(diagnostics) == 2

    hw_cw = diagnostics.loc[diagnostics["au_id"] == "cwh_vm_2_hw_cw"].iloc[0]
    assert int(hw_cw["source_stand_count"]) == 2
    assert int(hw_cw["ambiguous_stand_count"]) == 0
    assert hw_cw["selected_path"] == "smoothed_bin_pchip"
    assert bool(hw_cw["accepted"]) is True


def test_build_mkrf_first_growth_curves_lexmatches_unmatched_stands() -> None:
    assignment = pd.DataFrame(
        [
            {
                "res_key": 1,
                "forest_cover_id": 10,
                "au_id": "cwh_vm_1_cw_hw",
                "bec": "CWHvm1",
                "bec_zone": "cwh",
                "bec_subzone": "vm",
                "bec_variant": "1",
                "leading_species_1": "cw",
                "leading_species_2": "hw",
                "leading_species_1_share": 60.0,
                "leading_species_2_share": 40.0,
                "species_count": 2,
                "tie_break_used": False,
                "shape_area_ha": 5.0,
            }
        ]
    )
    source_table = pd.DataFrame(
        [
            {
                "RES_KEY": 101,
                "FOREST_COVER_ID": 99,
                "CONTCLAS": "X",
                "BEC": "CWHvm1",
                "Shape_Area": 12000.0,
                "TCL_1_TSP_1_TREE_SPECIES_CODE": "cw",
                "TCL_1_TSP_1_SPECIES_PCT": 60.0,
                "TCL_1_TSP_2_TREE_SPECIES_CODE": "dr",
                "TCL_1_TSP_2_SPECIES_PCT": 30.0,
                "TCL_1_TSP_3_TREE_SPECIES_CODE": "hw",
                "TCL_1_TSP_3_SPECIES_PCT": 10.0,
            }
        ]
    )
    vdyp_yields = pd.DataFrame(
        [
            {"FEATURE_ID": 10, "PRJ_TOTAL_AGE": 0, "PRJ_VOL_DWB": 5.0},
            {"FEATURE_ID": 10, "PRJ_TOTAL_AGE": 50, "PRJ_VOL_DWB": 35.0},
            {"FEATURE_ID": 10, "PRJ_TOTAL_AGE": 100, "PRJ_VOL_DWB": 70.0},
            {"FEATURE_ID": 10, "PRJ_TOTAL_AGE": 150, "PRJ_VOL_DWB": 90.0},
            {"FEATURE_ID": 99, "PRJ_TOTAL_AGE": 0, "PRJ_VOL_DWB": 3.0},
            {"FEATURE_ID": 99, "PRJ_TOTAL_AGE": 50, "PRJ_VOL_DWB": 30.0},
            {"FEATURE_ID": 99, "PRJ_TOTAL_AGE": 100, "PRJ_VOL_DWB": 60.0},
            {"FEATURE_ID": 99, "PRJ_TOTAL_AGE": 150, "PRJ_VOL_DWB": 80.0},
        ]
    )

    curves, diagnostics = build_mkrf_first_growth_curves(
        vdyp_yields=vdyp_yields,
        assignment=assignment,
        source_table=source_table,
        levenshtein_fn=lambda a, b: 0 if a == b else 1,
        min_source_stands=1,
    )

    assert curves["au_id"].unique().tolist() == ["cwh_vm_1_cw_hw"]
    row = diagnostics.iloc[0]
    assert int(row["source_stand_count"]) == 2
    assert int(row["lexmatch_stand_count"]) == 1
    assert int(row["lexmatch_alias_stand_count"]) == 1


def test_build_mkrf_first_growth_curves_excludes_stands_younger_than_80() -> None:
    assignment = pd.DataFrame(
        [
            {"res_key": 1, "forest_cover_id": 10, "au_id": "cwh_vm_1_cw_fdc", "shape_area_ha": 2.0},
            {"res_key": 2, "forest_cover_id": 11, "au_id": "cwh_vm_1_cw_fdc", "shape_area_ha": 2.0},
        ]
    )
    source_table = pd.DataFrame(
        [
            {"FOREST_COVER_ID": 10, "AGE_2020": 40},
            {"FOREST_COVER_ID": 11, "AGE_2020": 120},
        ]
    )
    vdyp_yields = pd.DataFrame(
        [
            {"FEATURE_ID": 10, "PRJ_TOTAL_AGE": 0, "PRJ_VOL_DWB": 5.0},
            {"FEATURE_ID": 10, "PRJ_TOTAL_AGE": 50, "PRJ_VOL_DWB": 35.0},
            {"FEATURE_ID": 10, "PRJ_TOTAL_AGE": 100, "PRJ_VOL_DWB": 70.0},
            {"FEATURE_ID": 11, "PRJ_TOTAL_AGE": 0, "PRJ_VOL_DWB": 8.0},
            {"FEATURE_ID": 11, "PRJ_TOTAL_AGE": 50, "PRJ_VOL_DWB": 40.0},
            {"FEATURE_ID": 11, "PRJ_TOTAL_AGE": 100, "PRJ_VOL_DWB": 80.0},
        ]
    )

    curves, diagnostics = build_mkrf_first_growth_curves(
        vdyp_yields=vdyp_yields,
        assignment=assignment,
        source_table=source_table,
        min_source_stands=1,
    )

    assert curves["au_id"].unique().tolist() == ["cwh_vm_1_cw_fdc"]
    row = diagnostics.iloc[0]
    assert int(row["source_stand_count"]) == 1


def test_build_mkrf_first_growth_curves_rejects_single_old_stand_support() -> None:
    assignment = pd.DataFrame(
        [
            {"res_key": 1, "forest_cover_id": 10, "au_id": "cwh_vm_1_dr_hw", "shape_area_ha": 1.0},
            {"res_key": 2, "forest_cover_id": 11, "au_id": "cwh_vm_1_dr_hw", "shape_area_ha": 1.0},
        ]
    )
    source_table = pd.DataFrame(
        [
            {"FOREST_COVER_ID": 10, "AGE_2020": 79},
            {"FOREST_COVER_ID": 11, "AGE_2020": 84},
        ]
    )
    vdyp_yields = pd.DataFrame(
        [
            {"FEATURE_ID": 10, "PRJ_TOTAL_AGE": 50, "PRJ_VOL_DWB": 180.0},
            {"FEATURE_ID": 10, "PRJ_TOTAL_AGE": 100, "PRJ_VOL_DWB": 240.0},
            {"FEATURE_ID": 11, "PRJ_TOTAL_AGE": 50, "PRJ_VOL_DWB": 210.0},
            {"FEATURE_ID": 11, "PRJ_TOTAL_AGE": 100, "PRJ_VOL_DWB": 280.0},
        ]
    )

    curves, diagnostics = build_mkrf_first_growth_curves(
        vdyp_yields=vdyp_yields,
        assignment=assignment,
        source_table=source_table,
    )

    assert curves.empty
    row = diagnostics.iloc[0]
    assert int(row["source_stand_count"]) == 1
    assert row["selected_path"] == "insufficient_source_stands"
    assert bool(row["accepted"]) is False


def test_build_mkrf_first_growth_curves_uses_smoothed_bin_pchip_curve_family() -> None:
    assignment = pd.DataFrame(
        [
            {"res_key": 1, "forest_cover_id": 10, "au_id": "cwh_vm_1_cw_hw", "shape_area_ha": 1.0},
            {"res_key": 2, "forest_cover_id": 11, "au_id": "cwh_vm_1_cw_hw", "shape_area_ha": 1.0},
        ]
    )
    source_table = pd.DataFrame(
        [
            {"FOREST_COVER_ID": 10, "AGE_2020": 90},
            {"FOREST_COVER_ID": 11, "AGE_2020": 95},
        ]
    )
    vdyp_yields = pd.DataFrame(
        [
            {"FEATURE_ID": 10, "PRJ_TOTAL_AGE": 30, "PRJ_VOL_DWB": 40.0},
            {"FEATURE_ID": 10, "PRJ_TOTAL_AGE": 80, "PRJ_VOL_DWB": 280.0},
            {"FEATURE_ID": 10, "PRJ_TOTAL_AGE": 150, "PRJ_VOL_DWB": 360.0},
            {"FEATURE_ID": 10, "PRJ_TOTAL_AGE": 300, "PRJ_VOL_DWB": 320.0},
            {"FEATURE_ID": 11, "PRJ_TOTAL_AGE": 30, "PRJ_VOL_DWB": 50.0},
            {"FEATURE_ID": 11, "PRJ_TOTAL_AGE": 80, "PRJ_VOL_DWB": 300.0},
            {"FEATURE_ID": 11, "PRJ_TOTAL_AGE": 150, "PRJ_VOL_DWB": 380.0},
            {"FEATURE_ID": 11, "PRJ_TOTAL_AGE": 300, "PRJ_VOL_DWB": 340.0},
        ]
    )

    curves, diagnostics = build_mkrf_first_growth_curves(
        vdyp_yields=vdyp_yields,
        assignment=assignment,
        source_table=source_table,
    )

    row = diagnostics.iloc[0]
    assert row["selected_path"] == "smoothed_bin_pchip"
    terminal = (
        curves.loc[curves["au_id"] == "cwh_vm_1_cw_hw"]
        .sort_values("age", kind="stable")
        .iloc[-1]["volume"]
    )
    assert terminal > 200.0
    mid = curves.loc[
        (curves["au_id"] == "cwh_vm_1_cw_hw") & (curves["age"] == 150),
        "volume",
    ].iloc[0]
    assert mid > 250.0


def test_format_mkrf_au_label_uses_k3z_style_display_shape() -> None:
    assert _format_mkrf_au_label("cwh_vm_1_cw_hw") == "CWHvm1_CW+HW"
