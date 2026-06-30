from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from femic.workflows.mkrf import (
    _apply_insufficient_support_merge,
    _apply_young_skewed_sibling_borrow,
    build_mkrf_bad_curve_audit,
)


def test_build_mkrf_bad_curve_audit_writes_summary_and_detail(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assignment_csv = tmp_path / "stand_au_assignment.csv"
    selected_au_csv = tmp_path / "selected_au_table.csv"
    first_growth_curves_csv = tmp_path / "first_growth_au_curves.csv"
    vdyp_yields_csv = tmp_path / "vdyp_yields.csv"
    output_dir = tmp_path / "out"

    pd.DataFrame(
        [
            {
                "res_key": 1,
                "forest_cover_id": 101,
                "shape_area_ha": 10.0,
                "au_id": "au_bad",
            },
            {
                "res_key": 2,
                "forest_cover_id": 102,
                "shape_area_ha": 12.0,
                "au_id": "au_bad",
            },
            {
                "res_key": 3,
                "forest_cover_id": 201,
                "shape_area_ha": 8.0,
                "au_id": "au_ok",
            },
        ]
    ).to_csv(assignment_csv, index=False)
    pd.DataFrame(
        [
            {"au_id": "au_bad", "selected_rank": 1, "covered_area_ha": 80.0},
            {"au_id": "au_ok", "selected_rank": 2, "covered_area_ha": 20.0},
        ]
    ).to_csv(selected_au_csv, index=False)
    pd.DataFrame(
        [
            {"au_id": "au_bad", "age": 0, "volume": 0.0},
            {"au_id": "au_bad", "age": 299, "volume": 12.0},
            {"au_id": "au_ok", "age": 0, "volume": 0.0},
            {"au_id": "au_ok", "age": 299, "volume": 450.0},
        ]
    ).to_csv(first_growth_curves_csv, index=False)
    pd.DataFrame(
        [
            {"FEATURE_ID": 101, "PRJ_TOTAL_AGE": 350, "PRJ_VOL_DWB": 5.0},
            {"FEATURE_ID": 102, "PRJ_TOTAL_AGE": 350, "PRJ_VOL_DWB": 420.0},
            {"FEATURE_ID": 201, "PRJ_TOTAL_AGE": 350, "PRJ_VOL_DWB": 500.0},
        ]
    ).to_csv(vdyp_yields_csv, index=False)

    source_table = pd.DataFrame(
        [
            {
                "FOREST_COVER_ID": 101,
                "TCL_1_ESTIMATED_SITE_INDEX": 28.0,
                "AGE_2020": 20,
                "BEC_ZONE_CODE": "CWH",
                "BEC_SUBZONE": "vm",
                "BEC_VARIANT": "1",
            },
            {
                "FOREST_COVER_ID": 102,
                "TCL_1_ESTIMATED_SITE_INDEX": 30.0,
                "AGE_2020": 120,
                "BEC_ZONE_CODE": "CWH",
                "BEC_SUBZONE": "vm",
                "BEC_VARIANT": "1",
            },
            {
                "FOREST_COVER_ID": 201,
                "TCL_1_ESTIMATED_SITE_INDEX": 32.0,
                "AGE_2020": 110,
                "BEC_ZONE_CODE": "CWH",
                "BEC_SUBZONE": "dm",
                "BEC_VARIANT": "x",
            },
        ]
    )
    monkeypatch.setattr(
        "femic.workflows.mkrf.gpd.read_file", lambda *args, **kwargs: source_table
    )

    result = build_mkrf_bad_curve_audit(
        resultant_gdb=tmp_path / "resultant.gdb",
        assignment_csv=assignment_csv,
        selected_au_csv=selected_au_csv,
        first_growth_curves_csv=first_growth_curves_csv,
        vdyp_yields_csv=vdyp_yields_csv,
        output_dir=output_dir,
    )

    summary = pd.read_csv(result.summary_path)
    detail = pd.read_csv(result.detail_path)

    assert result.flagged_au_count == 1
    assert result.total_selected_au_count == 2
    assert summary.loc[summary["au_id"] == "au_bad", "flagged"].item() is True
    assert (
        summary.loc[summary["au_id"] == "au_bad", "population_pattern"].item()
        == "mixed_low_high"
    )
    assert summary.loc[summary["au_id"] == "au_bad", "age_lt_80_count"].item() == 1
    assert summary.loc[summary["au_id"] == "au_bad", "age_gte_80_count"].item() == 1
    assert (
        summary.loc[summary["au_id"] == "au_bad", "curve_issue_class"].item()
        == "mixed_population"
    )
    assert detail["au_id"].tolist() == ["au_bad", "au_bad"]
    assert detail["forest_cover_id"].tolist() == [101, 102]


def test_apply_young_skewed_sibling_borrow_replaces_only_target_curve() -> None:
    curves = pd.DataFrame(
        [
            {"au_id": "cwh_dm_x_dr_cw", "age": 1, "volume": 1.0},
            {"au_id": "cwh_dm_x_dr_cw", "age": 299, "volume": 8.0},
            {"au_id": "cwh_dm_x_cw_dr", "age": 1, "volume": 1.0},
            {"au_id": "cwh_dm_x_cw_dr", "age": 299, "volume": 170.0},
        ]
    )
    diagnostics = pd.DataFrame(
        [
            {
                "au_id": "cwh_dm_x_dr_cw",
                "source_stand_count": 10,
                "selected_path": "primary_nlls",
                "accepted": True,
            },
            {
                "au_id": "cwh_dm_x_cw_dr",
                "source_stand_count": 10,
                "selected_path": "primary_nlls",
                "accepted": True,
            },
        ]
    )
    assignment = pd.DataFrame(
        [
            {
                "res_key": 1,
                "forest_cover_id": 101,
                "au_id": "cwh_dm_x_dr_cw",
                "shape_area_ha": 1.0,
            },
            {
                "res_key": 2,
                "forest_cover_id": 201,
                "au_id": "cwh_dm_x_cw_dr",
                "shape_area_ha": 1.0,
            },
            {
                "res_key": 3,
                "forest_cover_id": 202,
                "au_id": "cwh_dm_x_cw_dr",
                "shape_area_ha": 1.0,
            },
        ]
    )
    source_table = pd.DataFrame(
        [
            {"FOREST_COVER_ID": 101, "AGE_2020": 49},
            {"FOREST_COVER_ID": 201, "AGE_2020": 110},
            {"FOREST_COVER_ID": 202, "AGE_2020": 120},
        ]
    )

    updated_curves, updated_diagnostics = _apply_young_skewed_sibling_borrow(
        curves=curves,
        diagnostics=diagnostics,
        assignment=assignment,
        source_table=source_table,
    )

    borrowed_terminal = (
        updated_curves.loc[updated_curves["au_id"] == "cwh_dm_x_dr_cw"]
        .sort_values("age", kind="stable")
        .iloc[-1]["volume"]
    )
    assert borrowed_terminal == 170.0
    row = updated_diagnostics.loc[
        updated_diagnostics["au_id"] == "cwh_dm_x_dr_cw"
    ].iloc[0]
    assert row["selected_path"] == "borrowed_young_skewed_sibling"
    assert row["borrowed_from_au_id"] == "cwh_dm_x_cw_dr"


def test_apply_insufficient_support_merge_uses_largest_same_bec_neighbor() -> None:
    curves = pd.DataFrame(
        [
            {"au_id": "cwh_vm_1_hw_cw", "age": 1, "volume": 1.0},
            {"au_id": "cwh_vm_1_hw_cw", "age": 299, "volume": 260.0},
            {"au_id": "cwh_vm_1_cw_hw", "age": 1, "volume": 1.0},
            {"au_id": "cwh_vm_1_cw_hw", "age": 299, "volume": 180.0},
        ]
    )
    diagnostics = pd.DataFrame(
        [
            {
                "au_id": "cwh_vm_1_fdc_cw",
                "source_stand_count": 1,
                "selected_path": "insufficient_source_stands",
                "accepted": False,
            },
            {
                "au_id": "cwh_vm_1_hw_cw",
                "source_stand_count": 10,
                "selected_path": "primary_nlls",
                "accepted": True,
            },
            {
                "au_id": "cwh_vm_1_cw_hw",
                "source_stand_count": 8,
                "selected_path": "primary_nlls",
                "accepted": True,
            },
        ]
    )
    assignment = pd.DataFrame(
        [
            {
                "res_key": 1,
                "forest_cover_id": 101,
                "au_id": "cwh_vm_1_fdc_cw",
                "shape_area_ha": 10.0,
            },
            {
                "res_key": 2,
                "forest_cover_id": 201,
                "au_id": "cwh_vm_1_hw_cw",
                "shape_area_ha": 50.0,
            },
            {
                "res_key": 3,
                "forest_cover_id": 202,
                "au_id": "cwh_vm_1_hw_cw",
                "shape_area_ha": 50.0,
            },
            {
                "res_key": 4,
                "forest_cover_id": 301,
                "au_id": "cwh_vm_1_cw_hw",
                "shape_area_ha": 20.0,
            },
        ]
    )

    updated_curves, updated_diagnostics = _apply_insufficient_support_merge(
        curves=curves,
        diagnostics=diagnostics,
        assignment=assignment,
        source_table=pd.DataFrame(
            [
                {"FOREST_COVER_ID": 101, "AGE_2020": 90},
                {"FOREST_COVER_ID": 201, "AGE_2020": 120},
                {"FOREST_COVER_ID": 202, "AGE_2020": 130},
                {"FOREST_COVER_ID": 301, "AGE_2020": 110},
            ]
        ),
    )

    borrowed_terminal = (
        updated_curves.loc[updated_curves["au_id"] == "cwh_vm_1_fdc_cw"]
        .sort_values("age", kind="stable")
        .iloc[-1]["volume"]
    )
    assert borrowed_terminal == 260.0
    row = updated_diagnostics.loc[
        updated_diagnostics["au_id"] == "cwh_vm_1_fdc_cw"
    ].iloc[0]
    assert row["selected_path"] == "borrowed_insufficient_support_neighbor"
    assert row["borrowed_from_au_id"] == "cwh_vm_1_hw_cw"


def test_apply_insufficient_support_merge_handles_missing_curve_targets() -> None:
    curves = pd.DataFrame(
        [
            {"au_id": "cwh_vm_2_fdc_cw", "age": 1, "volume": 1.0},
            {"au_id": "cwh_vm_2_fdc_cw", "age": 299, "volume": 200.0},
        ]
    )
    diagnostics = pd.DataFrame(
        [
            {
                "au_id": "cwh_vm_2_fdc_cw",
                "source_stand_count": 10,
                "selected_path": "primary_nlls",
                "accepted": True,
            }
        ]
    )
    assignment = pd.DataFrame(
        [
            {
                "res_key": 1,
                "forest_cover_id": 101,
                "au_id": "cwh_vm_2_cw_fdc",
                "shape_area_ha": 10.0,
            },
            {
                "res_key": 2,
                "forest_cover_id": 201,
                "au_id": "cwh_vm_2_fdc_cw",
                "shape_area_ha": 50.0,
            },
            {
                "res_key": 3,
                "forest_cover_id": 202,
                "au_id": "cwh_vm_2_fdc_cw",
                "shape_area_ha": 50.0,
            },
        ]
    )
    source_table = pd.DataFrame(
        [
            {"FOREST_COVER_ID": 101, "AGE_2020": 90},
            {"FOREST_COVER_ID": 201, "AGE_2020": 120},
            {"FOREST_COVER_ID": 202, "AGE_2020": 130},
        ]
    )

    updated_curves, updated_diagnostics = _apply_insufficient_support_merge(
        curves=curves,
        diagnostics=diagnostics,
        assignment=assignment,
        source_table=source_table,
    )

    borrowed_terminal = (
        updated_curves.loc[updated_curves["au_id"] == "cwh_vm_2_cw_fdc"]
        .sort_values("age", kind="stable")
        .iloc[-1]["volume"]
    )
    assert borrowed_terminal == 200.0
    row = updated_diagnostics.loc[
        updated_diagnostics["au_id"] == "cwh_vm_2_cw_fdc"
    ].iloc[0]
    assert row["selected_path"] == "borrowed_insufficient_support_neighbor"
    assert row["borrowed_from_au_id"] == "cwh_vm_2_fdc_cw"


def test_apply_insufficient_support_merge_uses_fragment_level_old_support() -> None:
    curves = pd.DataFrame(
        [
            {"au_id": "cwh_vm_2_fdc_cw", "age": 1, "volume": 1.0},
            {"au_id": "cwh_vm_2_fdc_cw", "age": 299, "volume": 220.0},
        ]
    )
    diagnostics = pd.DataFrame(
        [
            {
                "au_id": "cwh_vm_2_fdc_cw",
                "source_stand_count": 10,
                "selected_path": "primary_nlls",
                "accepted": True,
            }
        ]
    )
    assignment = pd.DataFrame(
        [
            {
                "res_key": 1,
                "forest_cover_id": 101,
                "au_id": "cwh_vm_2_cw_fdc",
                "shape_area_ha": 1.0,
            },
            {
                "res_key": 2,
                "forest_cover_id": 101,
                "au_id": "cwh_vm_2_fdc_cw",
                "shape_area_ha": 9.0,
            },
            {
                "res_key": 3,
                "forest_cover_id": 201,
                "au_id": "cwh_vm_2_fdc_cw",
                "shape_area_ha": 50.0,
            },
        ]
    )
    source_table = pd.DataFrame(
        [
            {"FOREST_COVER_ID": 101, "AGE_2020": 90},
            {"FOREST_COVER_ID": 201, "AGE_2020": 120},
        ]
    )

    updated_curves, updated_diagnostics = _apply_insufficient_support_merge(
        curves=curves,
        diagnostics=diagnostics,
        assignment=assignment,
        source_table=source_table,
    )

    borrowed_terminal = (
        updated_curves.loc[updated_curves["au_id"] == "cwh_vm_2_cw_fdc"]
        .sort_values("age", kind="stable")
        .iloc[-1]["volume"]
    )
    assert borrowed_terminal == 220.0
    row = updated_diagnostics.loc[
        updated_diagnostics["au_id"] == "cwh_vm_2_cw_fdc"
    ].iloc[0]
    assert row["selected_path"] == "borrowed_insufficient_support_neighbor"
    assert row["borrowed_from_au_id"] == "cwh_vm_2_fdc_cw"


def test_apply_insufficient_support_merge_skips_low_terminal_donors() -> None:
    curves = pd.DataFrame(
        [
            {"au_id": "cwh_dm_x_dr_ep", "age": 1, "volume": 0.000001},
            {"au_id": "cwh_dm_x_dr_ep", "age": 299, "volume": 1.3},
            {"au_id": "cwh_dm_x_cw_dr", "age": 1, "volume": 1.0},
            {"au_id": "cwh_dm_x_cw_dr", "age": 299, "volume": 241.4},
        ]
    )
    diagnostics = pd.DataFrame(
        [
            {
                "au_id": "cwh_dm_x_dr_ep",
                "source_stand_count": 8,
                "selected_path": "primary_nlls",
                "accepted": True,
            },
            {
                "au_id": "cwh_dm_x_cw_dr",
                "source_stand_count": 12,
                "selected_path": "primary_nlls",
                "accepted": True,
            },
        ]
    )
    assignment = pd.DataFrame(
        [
            {
                "res_key": 1,
                "forest_cover_id": 101,
                "au_id": "cwh_dm_x_dr_mb",
                "shape_area_ha": 1.0,
            },
            {
                "res_key": 2,
                "forest_cover_id": 201,
                "au_id": "cwh_dm_x_dr_ep",
                "shape_area_ha": 100.0,
            },
            {
                "res_key": 3,
                "forest_cover_id": 301,
                "au_id": "cwh_dm_x_cw_dr",
                "shape_area_ha": 50.0,
            },
        ]
    )
    source_table = pd.DataFrame(
        [
            {"FOREST_COVER_ID": 101, "AGE_2020": 84},
            {"FOREST_COVER_ID": 201, "AGE_2020": 120},
            {"FOREST_COVER_ID": 301, "AGE_2020": 120},
        ]
    )

    updated_curves, updated_diagnostics = _apply_insufficient_support_merge(
        curves=curves,
        diagnostics=diagnostics,
        assignment=assignment,
        source_table=source_table,
    )

    borrowed_terminal = (
        updated_curves.loc[updated_curves["au_id"] == "cwh_dm_x_dr_mb"]
        .sort_values("age", kind="stable")
        .iloc[-1]["volume"]
    )
    assert borrowed_terminal == 241.4
    row = updated_diagnostics.loc[
        updated_diagnostics["au_id"] == "cwh_dm_x_dr_mb"
    ].iloc[0]
    assert row["selected_path"] == "borrowed_insufficient_support_neighbor"
    assert row["borrowed_from_au_id"] == "cwh_dm_x_cw_dr"


def test_build_mkrf_bad_curve_audit_classifies_insufficient_source_stands(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assignment_csv = tmp_path / "stand_au_assignment.csv"
    selected_au_csv = tmp_path / "selected_au_table.csv"
    first_growth_curves_csv = tmp_path / "first_growth_au_curves.csv"
    vdyp_yields_csv = tmp_path / "vdyp_yields.csv"
    output_dir = tmp_path / "out"

    pd.DataFrame(
        [
            {
                "res_key": 1,
                "forest_cover_id": 101,
                "shape_area_ha": 10.0,
                "au_id": "au_sparse",
            }
        ]
    ).to_csv(assignment_csv, index=False)
    pd.DataFrame(
        [{"au_id": "au_sparse", "selected_rank": 1, "covered_area_ha": 80.0}]
    ).to_csv(selected_au_csv, index=False)
    pd.DataFrame(columns=["au_id", "age", "volume"]).to_csv(
        first_growth_curves_csv, index=False
    )
    pd.DataFrame(
        [{"FEATURE_ID": 101, "PRJ_TOTAL_AGE": 350, "PRJ_VOL_DWB": 250.0}]
    ).to_csv(vdyp_yields_csv, index=False)

    source_table = pd.DataFrame(
        [
            {
                "FOREST_COVER_ID": 101,
                "TCL_1_ESTIMATED_SITE_INDEX": 28.0,
                "AGE_2020": 90,
                "BEC_ZONE_CODE": "CWH",
                "BEC_SUBZONE": "vm",
                "BEC_VARIANT": "1",
            }
        ]
    )
    monkeypatch.setattr(
        "femic.workflows.mkrf.gpd.read_file", lambda *args, **kwargs: source_table
    )

    result = build_mkrf_bad_curve_audit(
        resultant_gdb=tmp_path / "resultant.gdb",
        assignment_csv=assignment_csv,
        selected_au_csv=selected_au_csv,
        first_growth_curves_csv=first_growth_curves_csv,
        vdyp_yields_csv=vdyp_yields_csv,
        output_dir=output_dir,
    )

    summary = pd.read_csv(result.summary_path)
    assert (
        summary.loc[summary["au_id"] == "au_sparse", "curve_issue_class"].item()
        == "insufficient_source_stands"
    )
    assert (
        summary.loc[summary["au_id"] == "au_sparse", "old_support_stand_count"].item()
        == 1
    )


def test_build_mkrf_bad_curve_audit_uses_unique_old_support_stands(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assignment_csv = tmp_path / "stand_au_assignment.csv"
    selected_au_csv = tmp_path / "selected_au_table.csv"
    first_growth_curves_csv = tmp_path / "first_growth_au_curves.csv"
    vdyp_yields_csv = tmp_path / "vdyp_yields.csv"
    output_dir = tmp_path / "out"

    pd.DataFrame(
        [
            {
                "res_key": 1,
                "forest_cover_id": 101,
                "shape_area_ha": 10.0,
                "au_id": "au_dup",
            },
            {
                "res_key": 2,
                "forest_cover_id": 101,
                "shape_area_ha": 5.0,
                "au_id": "au_dup",
            },
            {
                "res_key": 3,
                "forest_cover_id": 102,
                "shape_area_ha": 5.0,
                "au_id": "au_dup",
            },
        ]
    ).to_csv(assignment_csv, index=False)
    pd.DataFrame(
        [{"au_id": "au_dup", "selected_rank": 1, "covered_area_ha": 20.0}]
    ).to_csv(selected_au_csv, index=False)
    pd.DataFrame(columns=["au_id", "age", "volume"]).to_csv(
        first_growth_curves_csv, index=False
    )
    pd.DataFrame(
        [
            {"FEATURE_ID": 101, "PRJ_TOTAL_AGE": 350, "PRJ_VOL_DWB": 250.0},
            {"FEATURE_ID": 102, "PRJ_TOTAL_AGE": 350, "PRJ_VOL_DWB": 260.0},
        ]
    ).to_csv(vdyp_yields_csv, index=False)

    source_table = pd.DataFrame(
        [
            {
                "FOREST_COVER_ID": 101,
                "TCL_1_ESTIMATED_SITE_INDEX": 28.0,
                "AGE_2020": 90,
                "BEC_ZONE_CODE": "CWH",
                "BEC_SUBZONE": "vm",
                "BEC_VARIANT": "1",
            },
            {
                "FOREST_COVER_ID": 102,
                "TCL_1_ESTIMATED_SITE_INDEX": 30.0,
                "AGE_2020": 40,
                "BEC_ZONE_CODE": "CWH",
                "BEC_SUBZONE": "vm",
                "BEC_VARIANT": "1",
            },
        ]
    )
    monkeypatch.setattr(
        "femic.workflows.mkrf.gpd.read_file", lambda *args, **kwargs: source_table
    )

    result = build_mkrf_bad_curve_audit(
        resultant_gdb=tmp_path / "resultant.gdb",
        assignment_csv=assignment_csv,
        selected_au_csv=selected_au_csv,
        first_growth_curves_csv=first_growth_curves_csv,
        vdyp_yields_csv=vdyp_yields_csv,
        output_dir=output_dir,
    )

    summary = pd.read_csv(result.summary_path)
    row = summary.loc[summary["au_id"] == "au_dup"].iloc[0]
    assert row["age_gte_80_count"] == 2
    assert row["old_support_stand_count"] == 1
    assert row["curve_issue_class"] == "insufficient_source_stands"


def test_build_mkrf_bad_curve_audit_reclassifies_zero_old_support_units_as_managed_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assignment_csv = tmp_path / "stand_au_assignment.csv"
    selected_au_csv = tmp_path / "selected_au_table.csv"
    first_growth_curves_csv = tmp_path / "first_growth_au_curves.csv"
    vdyp_yields_csv = tmp_path / "vdyp_yields.csv"
    output_dir = tmp_path / "out"

    pd.DataFrame(
        [
            {
                "res_key": 1,
                "forest_cover_id": 101,
                "shape_area_ha": 10.0,
                "au_id": "au_logging",
            },
            {
                "res_key": 2,
                "forest_cover_id": 102,
                "shape_area_ha": 12.0,
                "au_id": "au_logging",
            },
        ]
    ).to_csv(assignment_csv, index=False)
    pd.DataFrame(
        [{"au_id": "au_logging", "selected_rank": 1, "covered_area_ha": 80.0}]
    ).to_csv(selected_au_csv, index=False)
    pd.DataFrame(columns=["au_id", "age", "volume"]).to_csv(
        first_growth_curves_csv, index=False
    )
    pd.DataFrame(
        [
            {"FEATURE_ID": 101, "PRJ_TOTAL_AGE": 350, "PRJ_VOL_DWB": 225.0},
            {"FEATURE_ID": 102, "PRJ_TOTAL_AGE": 350, "PRJ_VOL_DWB": 315.0},
        ]
    ).to_csv(vdyp_yields_csv, index=False)

    source_table = pd.DataFrame(
        [
            {
                "FOREST_COVER_ID": 101,
                "TCL_1_ESTIMATED_SITE_INDEX": 24.0,
                "AGE_2020": 40,
                "BEC_ZONE_CODE": "CWH",
                "BEC_SUBZONE": "dm",
                "BEC_VARIANT": "x",
            },
            {
                "FOREST_COVER_ID": 102,
                "TCL_1_ESTIMATED_SITE_INDEX": 28.0,
                "AGE_2020": 59,
                "BEC_ZONE_CODE": "CWH",
                "BEC_SUBZONE": "dm",
                "BEC_VARIANT": "x",
            },
        ]
    )
    monkeypatch.setattr(
        "femic.workflows.mkrf.gpd.read_file", lambda *args, **kwargs: source_table
    )

    result = build_mkrf_bad_curve_audit(
        resultant_gdb=tmp_path / "resultant.gdb",
        assignment_csv=assignment_csv,
        selected_au_csv=selected_au_csv,
        first_growth_curves_csv=first_growth_curves_csv,
        vdyp_yields_csv=vdyp_yields_csv,
        output_dir=output_dir,
    )

    summary = pd.read_csv(result.summary_path)
    row = summary.loc[summary["au_id"] == "au_logging"].iloc[0]
    assert row["age_gte_80_count"] == 0
    assert row["curve_issue_class"] == "managed_only_after_age_floor"
    assert bool(row["flagged"]) is False
