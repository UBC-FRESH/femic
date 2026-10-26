"""Tests for the site-index provenance and reconciliation surface."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from femic.site_index import (
    AuSiteIndexError,
    SibecError,
    aggregate_sibec_by_bgc_unit,
    combine_sibec_tables,
    compose_bec_unit,
    load_au_site_index,
    load_sibec_addendum,
    load_sibec_table,
    load_vdyp_site_index,
    load_vri_site_index,
    normalise_species,
    reconcile_site_index,
    select_sibec_source,
    summarize_au_site_index,
    summarize_reconciliation,
)
from femic.site_index.cli import main as site_index_main

FIXTURES = Path(__file__).parent / "fixtures" / "site_index"
SIBEC_FIXTURE = FIXTURES / "sibec_sample.csv"
VRI_FIXTURE = FIXTURES / "vri_sample.csv"
VDYP_FIXTURE = FIXTURES / "vdyp_sample.csv"
AU_FIXTURE = FIXTURES / "au_input_sample.csv"


def _sibec() -> pd.DataFrame:
    return select_sibec_source(
        aggregate_sibec_by_bgc_unit(load_sibec_table(SIBEC_FIXTURE))
    )


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
        "source_table",
        "region",
        "bgc_unit",
        "site_series",
        "site_association",
        "species",
        "plot_count",
        "mean_site_index",
        "standard_error",
    ]
    assert table["schema_version"].unique().tolist() == ["femic.sibec.v2"]
    assert table["source_table"].unique().tolist() == ["2013_approximation"]
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


def _write_addendum(path: Path) -> Path:
    source = pd.DataFrame(
        {
            "BGC\nUnit": ["CWHvh2", "CWHvh2", "BGC\nUnit"],
            "Site\nSeries": ["01", "02", "Site\nSeries"],
            "Site Association": ["CwHw - Salal", "CwHw - Deer fern", "Species"],
            "Species": ["Cw", "Cw", "Species"],
            "Sample Size": [12, 5, None],
            "Mean Site Index": [19.5, 21.0, None],
            "Standard Error": [0.4, 0.8, None],
        }
    )
    source.to_excel(path, sheet_name="ciReportByUnit", index=False, startrow=2)
    return path


def test_sibec_addendum_loads_with_source_provenance(tmp_path: Path) -> None:
    path = _write_addendum(tmp_path / "addendum.xlsx")

    table = load_sibec_addendum(path)

    assert list(table.columns) == [
        "schema_version",
        "source_table",
        "region",
        "bgc_unit",
        "site_series",
        "site_association",
        "species",
        "plot_count",
        "mean_site_index",
        "standard_error",
    ]
    assert len(table) == 2
    assert table["schema_version"].unique().tolist() == ["femic.sibec.v2"]
    assert table["source_table"].unique().tolist() == ["2014_addendum"]
    assert table.loc[0, "plot_count"] == 12
    assert table.loc[0, "standard_error"] == pytest.approx(0.4)


def test_addendum_is_preferred_by_explicit_source_selection(tmp_path: Path) -> None:
    base = load_sibec_table(SIBEC_FIXTURE)
    addendum = load_sibec_addendum(_write_addendum(tmp_path / "addendum.xlsx"))
    combined = combine_sibec_tables(base, addendum)

    aggregated = aggregate_sibec_by_bgc_unit(combined)
    selected = select_sibec_source(aggregated)
    row = selected[
        (selected["bgc_unit_key"] == "CWHVH2") & (selected["species_key"] == "CW")
    ].iloc[0]

    assert row["si_sibec_source"] == "2014_addendum"
    assert row["si_sibec_mean"] == pytest.approx(339.0 / 17.0)
    assert set(selected["si_sibec_source"]) == {"2014_addendum", "2013_approximation"}


def test_au_reader_returns_species_rows_and_leading_flags() -> None:
    table = load_au_site_index(AU_FIXTURE)

    assert list(table.columns) == [
        "schema_version",
        "au_id",
        "bec_zone",
        "bec_subzone",
        "planted_species",
        "natural_species",
        "leading_species",
        "species",
        "species_key",
        "si_au",
        "is_leading",
    ]
    assert len(table) == 12
    assert table["schema_version"].unique().tolist() == ["femic.site-index.au.v1"]
    assert table.loc[table["au_id"] == 21000, "is_leading"].sum() == 1
    assert (
        table.loc[(table["au_id"] == 21000) & table["is_leading"], "species_key"].item()
        == "CW"
    )
    assert (
        table.loc[(table["au_id"] == 21002) & table["is_leading"], "species_key"].item()
        == "HM"
    )


def test_au_summary_states_the_grain_and_counts() -> None:
    summary = summarize_au_site_index(load_au_site_index(AU_FIXTURE))

    assert summary["schema_version"] == "femic.site-index.au.v1"
    assert summary["grain"] == "analysis_unit_species"
    assert summary["au_count"] == 3
    assert summary["row_count"] == 12
    assert summary["species_count"] == 4
    assert summary["bec_zones"] == ["CWH", "MH"]
    assert summary["leading_species_counts"] == {"CW": 1, "HW": 1, "HM": 1}
    assert summary["leading_si"]["count"] == 3


def test_au_reader_rejects_missing_si_columns(tmp_path: Path) -> None:
    target = tmp_path / "au.csv"
    target.write_text("feature_id,bec_zone,bec_subzone\n1,CWH,vh\n", encoding="utf-8")

    with pytest.raises(AuSiteIndexError, match="species.*_si|_si"):
        load_au_site_index(target)


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
    assert first["si_sibec_vri_source"] == "2013_approximation"
    assert first["si_sibec_vdyp_source"] == "2013_approximation"
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
    assert summary["sibec_sources"]["si_sibec_vri"] == {
        "2013_approximation": 5,
        "none": 1,
    }


def test_cli_writes_csv_and_json(tmp_path: Path) -> None:
    out_csv = tmp_path / "reconciliation.csv"
    out_json = tmp_path / "summary.json"
    out_au_csv = tmp_path / "au_site_index.csv"
    out_au_json = tmp_path / "au_summary.json"
    addendum = _write_addendum(tmp_path / "addendum.xlsx")

    return_code = site_index_main(
        [
            "--vri",
            str(VRI_FIXTURE),
            "--vdyp",
            str(VDYP_FIXTURE),
            "--sibec",
            str(SIBEC_FIXTURE),
            "--sibec-addendum",
            str(addendum),
            "--au-input",
            str(AU_FIXTURE),
            "--out-csv",
            str(out_csv),
            "--out-json",
            str(out_json),
            "--out-au-csv",
            str(out_au_csv),
            "--out-au-json",
            str(out_au_json),
            "--delta-threshold",
            "1.0",
        ]
    )

    assert return_code == 0
    assert out_csv.exists()
    assert out_json.exists()
    assert out_au_csv.exists()
    assert out_au_json.exists()
    summary = json.loads(out_json.read_text(encoding="utf-8"))
    assert summary["feature_count"] == 6
    assert summary["sibec_sources"]["si_sibec_vri"]["2014_addendum"] >= 1
    written = pd.read_csv(out_csv)
    assert len(written) == 6
    au_summary = json.loads(out_au_json.read_text(encoding="utf-8"))
    assert au_summary["grain"] == "analysis_unit_species"
    assert au_summary["au_count"] == 3
    au_written = pd.read_csv(out_au_csv)
    assert len(au_written) == 12
