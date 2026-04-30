from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from femic.workflows.mkrf import build_mkrf_bad_curve_audit


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
            {"res_key": 1, "forest_cover_id": 101, "shape_area_ha": 10.0, "au_id": "au_bad"},
            {"res_key": 2, "forest_cover_id": 102, "shape_area_ha": 12.0, "au_id": "au_bad"},
            {"res_key": 3, "forest_cover_id": 201, "shape_area_ha": 8.0, "au_id": "au_ok"},
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
    monkeypatch.setattr("femic.workflows.mkrf.gpd.read_file", lambda *args, **kwargs: source_table)

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
    assert summary.loc[summary["au_id"] == "au_bad", "population_pattern"].item() == "mixed_low_high"
    assert detail["au_id"].tolist() == ["au_bad", "au_bad"]
    assert detail["forest_cover_id"].tolist() == [101, 102]
