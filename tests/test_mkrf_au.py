from __future__ import annotations

import pandas as pd
import pytest

from pathlib import Path

from femic.pipeline.mkrf_au import (
    build_mkrf_au_aggregation_audit,
    build_mkrf_au_tables,
    build_mkrf_site_series_split_audit,
    build_mkrf_selected_au_table,
    normalize_mkrf_site_series,
    ordered_top_two_species,
    parse_mkrf_bec,
)
from femic.workflows.mkrf import build_mkrf_selected_au_input_bundle


def test_parse_mkrf_bec_splits_zone_subzone_variant() -> None:
    assert parse_mkrf_bec("CWHvm2") == ("cwh", "vm", "2")
    assert parse_mkrf_bec("CWHdm") == ("cwh", "dm", "x")
    assert parse_mkrf_bec(None) == ("x", "x", "x")


def test_normalize_mkrf_site_series_extracts_stable_suffix() -> None:
    assert normalize_mkrf_site_series("Cw - Swordfern (05)") == "ss05"
    assert normalize_mkrf_site_series("BaCw - Foamflower (05)") == "ss05"
    assert normalize_mkrf_site_series("Non-forested: aquatic") == "ssnonforestedaquatic"
    assert normalize_mkrf_site_series(None) == "ssx"


def test_ordered_top_two_species_uses_lexical_tie_break() -> None:
    row = {
        "TCL_1_TSP_1_TREE_SPECIES_CODE": "HW",
        "TCL_1_TSP_1_SPECIES_PCT": 40,
        "TCL_1_TSP_2_TREE_SPECIES_CODE": "CW",
        "TCL_1_TSP_2_SPECIES_PCT": 40,
        "TCL_1_TSP_3_TREE_SPECIES_CODE": "FDC",
        "TCL_1_TSP_3_SPECIES_PCT": 20,
    }
    out = ordered_top_two_species(row)
    assert out.leading_species_1 == "cw"
    assert out.leading_species_2 == "hw"
    assert out.tie_break_used is True


def test_build_mkrf_au_tables_filters_non_forest_and_groups_assignments() -> None:
    source = pd.DataFrame(
        [
            {
                "RES_KEY": 10,
                "FOREST_COVER_ID": 100,
                "BEC": "CWHvm2",
                "CONTCLAS": "C",
                "TCL_1_TSP_1_TREE_SPECIES_CODE": "HW",
                "TCL_1_TSP_1_SPECIES_PCT": 70,
                "TCL_1_TSP_2_TREE_SPECIES_CODE": "CW",
                "TCL_1_TSP_2_SPECIES_PCT": 30,
            },
            {
                "RES_KEY": 11,
                "FOREST_COVER_ID": 101,
                "BEC": "CWHvm2",
                "CONTCLAS": "C",
                "TCL_1_TSP_1_TREE_SPECIES_CODE": "HW",
                "TCL_1_TSP_1_SPECIES_PCT": 60,
                "TCL_1_TSP_2_TREE_SPECIES_CODE": "CW",
                "TCL_1_TSP_2_SPECIES_PCT": 40,
            },
            {
                "RES_KEY": 12,
                "FOREST_COVER_ID": 102,
                "BEC": "CWHdm",
                "CONTCLAS": "X",
                "TCL_1_TSP_1_TREE_SPECIES_CODE": "DR",
                "TCL_1_TSP_1_SPECIES_PCT": 100,
            },
        ]
    )

    au_table, assignment = build_mkrf_au_tables(source)

    assert list(assignment["res_key"]) == [10, 11]
    assert list(assignment["au_id"].unique()) == ["cwh_vm_2_hw_cw"]
    assert list(au_table["au_id"]) == ["cwh_vm_2_hw_cw"]
    assert list(au_table["stand_count"]) == [2]


def test_build_mkrf_au_tables_splits_large_strata_by_site_series() -> None:
    source = pd.DataFrame(
        [
            {
                "RES_KEY": 1,
                "FOREST_COVER_ID": 101,
                "BEC": "CWHvm1",
                "CONTCLAS": "C",
                "Shape_Area": 60000.0,
                "SITE_SERIES": "Cw - Swordfern (05)",
                "TCL_1_TSP_1_TREE_SPECIES_CODE": "CW",
                "TCL_1_TSP_1_SPECIES_PCT": 60,
                "TCL_1_TSP_2_TREE_SPECIES_CODE": "HW",
                "TCL_1_TSP_2_SPECIES_PCT": 40,
            },
            {
                "RES_KEY": 2,
                "FOREST_COVER_ID": 102,
                "BEC": "CWHvm1",
                "CONTCLAS": "C",
                "Shape_Area": 40000.0,
                "SITE_SERIES": "BaCw - Foamflower (06)",
                "TCL_1_TSP_1_TREE_SPECIES_CODE": "CW",
                "TCL_1_TSP_1_SPECIES_PCT": 55,
                "TCL_1_TSP_2_TREE_SPECIES_CODE": "HW",
                "TCL_1_TSP_2_SPECIES_PCT": 45,
            },
            {
                "RES_KEY": 3,
                "FOREST_COVER_ID": 103,
                "BEC": "CWHdm",
                "CONTCLAS": "C",
                "Shape_Area": 3000.0,
                "SITE_SERIES": "Cw - Swordfern (05)",
                "TCL_1_TSP_1_TREE_SPECIES_CODE": "DR",
                "TCL_1_TSP_1_SPECIES_PCT": 70,
                "TCL_1_TSP_2_TREE_SPECIES_CODE": "CW",
                "TCL_1_TSP_2_SPECIES_PCT": 30,
            },
        ]
    )

    au_table, assignment = build_mkrf_au_tables(source)
    audit = build_mkrf_site_series_split_audit(assignment)

    assert set(assignment["au_id"]) == {
        "cwh_vm_1_cw_hw_ss05",
        "cwh_vm_1_cw_hw_ss06",
        "cwh_dm_x_dr_cw",
    }
    assert assignment.loc[
        assignment["res_key"].isin([1, 2]), "site_series_split_applied"
    ].all()
    assert not bool(
        assignment.loc[assignment["res_key"].eq(3), "site_series_split_applied"].iloc[0]
    )
    split_aus = au_table.loc[
        au_table["au_id"].str.startswith("cwh_vm_1_cw_hw")
    ].sort_values("au_id")
    assert split_aus["site_series_id"].tolist() == ["ss05", "ss06"]
    assert split_aus["stand_count"].tolist() == [1, 1]

    base_rows = audit.loc[audit["base_au_id"].eq("cwh_vm_1_cw_hw")]
    assert base_rows["site_series_split_applied"].all()
    assert base_rows["base_au_area_share"].iloc[0] == pytest.approx(100000.0 / 103000.0)
    assert set(base_rows["site_series_share_of_base_au"]) == {0.6, 0.4}


def test_build_mkrf_au_tables_applies_minor_strata_aggregation_auditably() -> None:
    source = pd.DataFrame(
        [
            {
                "RES_KEY": 20,
                "FOREST_COVER_ID": 200,
                "BEC": "CWHvm2",
                "CONTCLAS": "C",
                "Shape_Area": 10000.0,
                "TCL_1_TSP_1_TREE_SPECIES_CODE": "HW",
                "TCL_1_TSP_1_SPECIES_PCT": 60,
                "TCL_1_TSP_2_TREE_SPECIES_CODE": "BA",
                "TCL_1_TSP_2_SPECIES_PCT": 30,
            },
            {
                "RES_KEY": 21,
                "FOREST_COVER_ID": 201,
                "BEC": "CWHvm2",
                "CONTCLAS": "C",
                "Shape_Area": 20000.0,
                "TCL_1_TSP_1_TREE_SPECIES_CODE": "BA",
                "TCL_1_TSP_1_SPECIES_PCT": 55,
                "TCL_1_TSP_2_TREE_SPECIES_CODE": "HW",
                "TCL_1_TSP_2_SPECIES_PCT": 35,
            },
            {
                "RES_KEY": 22,
                "FOREST_COVER_ID": 202,
                "BEC": "CWHdm",
                "CONTCLAS": "C",
                "Shape_Area": 30000.0,
                "TCL_1_TSP_1_TREE_SPECIES_CODE": "CW",
                "TCL_1_TSP_1_SPECIES_PCT": 50,
                "TCL_1_TSP_2_TREE_SPECIES_CODE": "DR",
                "TCL_1_TSP_2_SPECIES_PCT": 40,
            },
        ]
    )

    au_table, assignment = build_mkrf_au_tables(source)
    audit = build_mkrf_au_aggregation_audit(assignment)

    assert assignment.loc[assignment["res_key"].eq(21), "raw_au_id"].iloc[0] == (
        "cwh_vm_2_ba_hw"
    )
    assert assignment.loc[assignment["res_key"].eq(21), "au_id"].iloc[0] == (
        "cwh_vm_2_hw_ba"
    )
    assert (
        assignment.loc[assignment["res_key"].eq(21), "leading_species_1"].iloc[0]
        == "ba"
    )
    assert (
        assignment.loc[assignment["res_key"].eq(21), "leading_species_1_share"].iloc[0]
        == 55
    )

    assert au_table["au_id"].tolist() == ["cwh_dm_x_dr_cw", "cwh_vm_2_hw_ba"]
    merged = au_table.loc[au_table["au_id"].eq("cwh_vm_2_hw_ba")].iloc[0]
    assert merged["stand_count"] == 2
    assert merged["leading_species_1"] == "hw"
    assert merged["leading_species_2"] == "ba"

    aggregated_row = audit.loc[audit["raw_au_id"].eq("cwh_vm_2_ba_hw")].iloc[0]
    assert aggregated_row["au_id"] == "cwh_vm_2_hw_ba"
    assert bool(aggregated_row["was_aggregated"]) is True
    assert aggregated_row["covered_area_ha"] == 2.0
    assert aggregated_row["target_area_ha"] == 3.0
    assert aggregated_row["raw_share_of_target_area"] == 2.0 / 3.0


def test_build_mkrf_selected_au_table_uses_smallest_prefix_meeting_coverage() -> None:
    au_table = pd.DataFrame(
        [
            {
                "au_id": "au_c",
                "bec_zone": "cwh",
                "bec_subzone": "vm",
                "bec_variant": "2",
                "leading_species_1": "cw",
                "leading_species_2": "hw",
                "stand_count": 1,
                "tie_break_record_count": 0,
            },
            {
                "au_id": "au_a",
                "bec_zone": "cwh",
                "bec_subzone": "vm",
                "bec_variant": "2",
                "leading_species_1": "hw",
                "leading_species_2": "cw",
                "stand_count": 1,
                "tie_break_record_count": 0,
            },
            {
                "au_id": "au_b",
                "bec_zone": "cwh",
                "bec_subzone": "vm",
                "bec_variant": "2",
                "leading_species_1": "fdc",
                "leading_species_2": "hw",
                "stand_count": 1,
                "tie_break_record_count": 0,
            },
        ]
    )
    assignment = pd.DataFrame(
        [
            {"au_id": "au_a", "shape_area_ha": 50.0},
            {"au_id": "au_b", "shape_area_ha": 30.0},
            {"au_id": "au_c", "shape_area_ha": 20.0},
        ]
    )

    selected = build_mkrf_selected_au_table(au_table, assignment, target_coverage=0.8)

    assert list(selected["au_id"]) == ["au_a", "au_b"]
    assert list(selected["selected_rank"]) == [1, 2]
    assert list(selected["covered_area_ha"]) == [50.0, 30.0]
    assert list(selected["covered_area_share"]) == [0.5, 0.3]
    assert list(selected["cumulative_covered_area_share"]) == [0.5, 0.8]
    assert selected["target_coverage"].tolist() == [0.8, 0.8]


def test_build_mkrf_selected_au_input_bundle_writes_selected_csv(
    tmp_path: Path,
) -> None:
    bundle_dir = tmp_path / "data" / "model_input_bundle"
    bundle_dir.mkdir(parents=True)
    au_table_csv = bundle_dir / "au_table.csv"
    assignment_csv = bundle_dir / "stand_au_assignment.csv"
    output_csv = bundle_dir / "selected_au_table.csv"

    pd.DataFrame(
        [
            {
                "au_id": "au_a",
                "bec_zone": "cwh",
                "bec_subzone": "vm",
                "bec_variant": "2",
                "leading_species_1": "hw",
                "leading_species_2": "cw",
                "stand_count": 1,
                "tie_break_record_count": 0,
            },
            {
                "au_id": "au_b",
                "bec_zone": "cwh",
                "bec_subzone": "vm",
                "bec_variant": "2",
                "leading_species_1": "fdc",
                "leading_species_2": "hw",
                "stand_count": 1,
                "tie_break_record_count": 0,
            },
            {
                "au_id": "au_c",
                "bec_zone": "cwh",
                "bec_subzone": "vm",
                "bec_variant": "2",
                "leading_species_1": "cw",
                "leading_species_2": "hw",
                "stand_count": 1,
                "tie_break_record_count": 0,
            },
        ]
    ).to_csv(au_table_csv, index=False)
    pd.DataFrame(
        [
            {"au_id": "au_a", "shape_area_ha": 50.0},
            {"au_id": "au_b", "shape_area_ha": 30.0},
            {"au_id": "au_c", "shape_area_ha": 20.0},
        ]
    ).to_csv(assignment_csv, index=False)

    result = build_mkrf_selected_au_input_bundle(
        au_table_csv=au_table_csv,
        assignment_csv=assignment_csv,
        output_path=output_csv,
        target_coverage=0.8,
    )

    written = pd.read_csv(output_csv)
    assert output_csv.exists()
    assert list(written["au_id"]) == ["au_a", "au_b"]
    assert result.selected_au_count == 2
    assert result.total_au_count == 3
    assert result.realized_coverage == 0.8
