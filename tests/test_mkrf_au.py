from __future__ import annotations

import pandas as pd

from femic.pipeline.mkrf_au import build_mkrf_au_tables, ordered_top_two_species, parse_mkrf_bec


def test_parse_mkrf_bec_splits_zone_subzone_variant() -> None:
    assert parse_mkrf_bec("CWHvm2") == ("cwh", "vm", "2")
    assert parse_mkrf_bec("CWHdm") == ("cwh", "dm", "x")
    assert parse_mkrf_bec(None) == ("x", "x", "x")


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
