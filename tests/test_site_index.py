"""Tests for the site-index provenance and reconciliation surface."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from femic.site_index import (
    SibecError,
    aggregate_sibec_by_bgc_unit,
    compose_bec_unit,
    load_sibec_table,
    load_vdyp_site_index,
    load_vri_site_index,
    normalise_species,
    reconcile_site_index,
    summarize_reconciliation,
)
from femic.site_index.cli import main as site_index_main

FIXTURES = Path(__file__).parent / "fixtures" / "site_index"
SIBEC_FIXTURE = FIXTURES / "sibec_sample.csv"
VRI_FIXTURE = FIXTURES / "vri_sample.csv"
VDYP_FIXTURE = FIXTURES / "vdyp_sample.csv"


def _sibec() -> pd.DataFrame:
    return aggregate_sibec_by_bgc_unit(load_sibec_table(SIBEC_FIXTURE))


def _reconciled() -> pd.DataFrame:
    return reconcile_site_index(
        load_vri_site_index(VRI_FIXTURE),
        load_vdyp_site_index(VDYP_FIXTURE),
        _sibec(),
        delta_threshold=1.0,
    )


def test_sibec_loader_normalises_columns_and_values() -> None:
    table = load_sibec_table(SIBEC_FIXTURE)

    assert list(table.columns) == [
        "schema_version",
        "region",
        "bgc_unit",
        "site_series",
        "site_association",
        "species",
        "plot_count",
        "mean_site_index",
        "standard_error",
    ]
    assert table["schema_version"].unique().tolist() == ["femic.sibec.v1"]
    assert table.loc[0, "bgc_unit"] == "CWHvh2"
    assert table.loc[0, "species"] == "CW"
    assert table.loc[0, "plot_count"] == 10


def test_sibec_xlsx_uses_third_row_header(tmp_path: Path) -> None:
    source = pd.DataFrame(
        {
            "Region": ["Coast"],
            "BGCUnit": ["CWHvh2"],
            "SiteSeries": ["01"],
            "SiteAssociation": ["CwHw - Salal"],
            "TreeSpp": ["Cw"],
            "PlotCountSpp": [10],
            "MeanPlotSiteIndex": [18.0],
            "StandardErrorOfMean": [0.5],
        }
    )
    target = tmp_path / "sibec.xlsx"
    source.to_excel(target, index=False, startrow=2)

    table = load_sibec_table(target)

    assert len(table) == 1
    assert table.loc[0, "mean_site_index"] == 18.0


def test_sibec_aggregation_weights_by_plot_count() -> None:
    table = _sibec()
    row = table[
        (table["bgc_unit_key"] == "CWHVH2") & (table["species_key"] == "CW")
    ].iloc[0]

    assert row["si_sibec_mean"] == pytest.approx(18.75)
    assert row["si_sibec_min"] == pytest.approx(18.0)
    assert row["si_sibec_max"] == pytest.approx(20.0)
    assert row["si_sibec_plot_count"] == 16
    assert row["si_sibec_site_series_count"] == 2
    assert row["si_sibec_se"] == pytest.approx(0.6)


def test_sibec_missing_required_column_is_rejected(tmp_path: Path) -> None:
    target = tmp_path / "bad.csv"
    target.write_text(
        "BGCUnit,SiteSeries,TreeSpp\nCWHvh2,01,Cw\n",
        encoding="utf-8",
    )

    with pytest.raises(SibecError, match="mean_site_index"):
        load_sibec_table(target)


def test_vri_reader_maps_bec_and_species_keys() -> None:
    vri = load_vri_site_index(VRI_FIXTURE)

    assert len(vri) == 6
    assert vri.loc[0, "bec_unit"] == "CWHvh2"
    assert vri.loc[0, "bec_unit_key"] == "CWHVH2"
    assert vri.loc[0, "species_key"] == "CW"
    assert vri.loc[0, "si_vri"] == 19.0
    assert vri.loc[1, "species_key"] == "HW"
    assert vri.loc[2, "species_key"] == "FD"
    assert vri.loc[3, "si_vri"] != vri.loc[3, "si_vri"]
    assert vri.loc[3, "si_vri_est"] == 13.0


def test_vdyp_reader_keeps_primary_layer_only() -> None:
    vdyp = load_vdyp_site_index(VDYP_FIXTURE)

    assert len(vdyp) == 6
    assert vdyp.loc[vdyp["feature_id"] == 5, "si_vdyp"].item() == 12.0
    assert vdyp.loc[vdyp["feature_id"] == 1, "species_key"].item() == "CW"


def test_species_and_bec_helpers() -> None:
    assert normalise_species("FDC") == "FD"
    assert normalise_species("H") == "HW"
    assert normalise_species("ZZ") == "ZZ"
    assert normalise_species(None) is None
    assert compose_bec_unit("CWH", "vh", 2) == "CWHvh2"
    assert compose_bec_unit("CWH", "vh", None) == "CWHvh"


def test_reconciliation_flags_conflicts_and_sets_reference() -> None:
    frame = _reconciled()

    assert len(frame) == 6

    first = frame.loc[0]
    assert first["si_status"] == "complete"
    assert first["delta_vri_vdyp"] == pytest.approx(0.5)
    assert first["delta_vri_sibec"] == pytest.approx(-0.25)
    assert first["delta_vdyp_sibec"] == pytest.approx(-0.75)
    assert first["delta_vri_sibec_range"] == pytest.approx(0.0)
    assert first["delta_vdyp_sibec_range"] == pytest.approx(0.0)
    assert first["si_reference"] == pytest.approx(19.0)
    assert first["si_reference_source"] == "vri"

    second = frame.loc[1]
    assert second["si_status"] == "conflict"
    assert second["delta_vri_sibec_range"] == pytest.approx(1.0)
    assert second["delta_vdyp_sibec_range"] == pytest.approx(2.0)
    assert second["delta_abs_max"] == pytest.approx(2.0)

    fourth = frame.loc[3]
    assert fourth["si_status"] == "conflict"
    assert fourth["delta_vdyp_sibec_range"] == pytest.approx(3.0)
    assert fourth["si_reference"] == pytest.approx(18.75)
    assert fourth["si_reference_source"] == "sibec"
    assert fourth["delta_reference_curve"] == pytest.approx(3.75)

    fifth = frame.loc[4]
    assert fifth["si_status"] == "partial"
    assert fifth["si_sibec_vri"] != fifth["si_sibec_vri"]
    assert fifth["si_reference_source"] == "vri"

    sixth = frame.loc[5]
    assert not sixth["species_match"]
    assert sixth["delta_vri_vdyp"] != sixth["delta_vri_vdyp"]
    assert sixth["si_status"] == "complete"


def test_summary_reports_coverage_and_conflicts() -> None:
    summary = summarize_reconciliation(_reconciled(), delta_threshold=1.0)

    assert summary["feature_count"] == 6
    assert summary["coverage"]["si_vri"] == 5
    assert summary["coverage"]["si_vri_est"] == 2
    assert summary["coverage"]["si_vdyp"] == 6
    assert summary["coverage"]["si_sibec_vri"] == 5
    assert summary["status_counts"] == {
        "complete": 3,
        "conflict": 2,
        "partial": 1,
        "missing": 0,
    }
    assert summary["species_mismatch_count"] == 1
    assert summary["deltas"]["vri_vdyp"]["count"] == 4
    assert summary["top_conflict_bec_units"] == {"CWHvh2": 2}
    assert summary["reference_sources"] == {"vri": 5, "sibec": 1}


def test_cli_writes_csv_and_json(tmp_path: Path) -> None:
    out_csv = tmp_path / "reconciliation.csv"
    out_json = tmp_path / "summary.json"

    return_code = site_index_main(
        [
            "--vri",
            str(VRI_FIXTURE),
            "--vdyp",
            str(VDYP_FIXTURE),
            "--sibec",
            str(SIBEC_FIXTURE),
            "--out-csv",
            str(out_csv),
            "--out-json",
            str(out_json),
            "--delta-threshold",
            "1.0",
        ]
    )

    assert return_code == 0
    assert out_csv.exists()
    assert out_json.exists()
    summary = json.loads(out_json.read_text(encoding="utf-8"))
    assert summary["feature_count"] == 6
    written = pd.read_csv(out_csv)
    assert len(written) == 6
