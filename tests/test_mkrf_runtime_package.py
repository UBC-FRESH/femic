from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from femic.workflows.mkrf import (
    audit_mkrf_runtime_sanity,
    _build_unmanaged_species_share_table,
    initialize_mkrf_runtime_package,
)


def test_build_unmanaged_species_share_table_aggregates_area_weighted_species_mix() -> None:
    stand_assignment = pd.DataFrame(
        [
            {
                "forest_cover_id": 1,
                "au_id": "cwh_vm_1_hw_cw",
                "shape_area_ha": 10.0,
                "leading_species_1": "HW",
                "leading_species_2": "CW",
                "leading_species_1_share": 60.0,
                "leading_species_2_share": 30.0,
            },
            {
                "forest_cover_id": 2,
                "au_id": "cwh_vm_1_hw_cw",
                "shape_area_ha": 20.0,
                "leading_species_1": "CW",
                "leading_species_2": "FD",
                "leading_species_1_share": 50.0,
                "leading_species_2_share": 40.0,
            },
            {
                "forest_cover_id": 3,
                "au_id": "cwh_vm_2_hw_cw",
                "shape_area_ha": 12.0,
                "leading_species_1": "ACT",
                "leading_species_2": "HW",
                "leading_species_1_share": 55.0,
                "leading_species_2_share": 25.0,
            },
            {
                "forest_cover_id": 4,
                "au_id": "outside_selected",
                "shape_area_ha": 99.0,
                "leading_species_1": "FD",
                "leading_species_2": "CW",
                "leading_species_1_share": 70.0,
                "leading_species_2_share": 20.0,
            },
        ]
    )
    selected_au = pd.DataFrame(
        [
            {"au_id": "cwh_vm_1_hw_cw"},
            {"au_id": "cwh_vm_2_hw_cw"},
        ]
    )

    result = _build_unmanaged_species_share_table(
        stand_assignment,
        selected_au_table=selected_au,
    ).sort_values("au_id", kind="stable")

    assert result["au_id"].tolist() == ["cwh_vm_1_hw_cw", "cwh_vm_2_hw_cw"]

    first = result.loc[result["au_id"] == "cwh_vm_1_hw_cw"].iloc[0]
    assert first["share_hw"] == pytest.approx(20.0)
    assert first["share_cw"] == pytest.approx(43.33, abs=0.01)
    assert first["share_fd"] == pytest.approx(26.67, abs=0.01)
    assert first["share_oth"] == pytest.approx(10.0)
    assert first["share_ba"] == pytest.approx(0.0)
    assert first["share_dec"] == pytest.approx(0.0)
    assert first["share_dr"] == pytest.approx(0.0)
    assert first["share_yc"] == pytest.approx(0.0)

    second = result.loc[result["au_id"] == "cwh_vm_2_hw_cw"].iloc[0]
    assert second["share_dec"] == pytest.approx(55.0)
    assert second["share_hw"] == pytest.approx(25.0)
    assert second["share_oth"] == pytest.approx(20.0)
    assert second["share_cw"] == pytest.approx(0.0)
    assert second["share_fd"] == pytest.approx(0.0)


def test_initialize_mkrf_runtime_package_writes_manifest(tmp_path: Path) -> None:
    package_root = tmp_path / "models" / "mkrf_patchworks_model"

    selected_au_csv = tmp_path / "selected_au_table.csv"
    pd.DataFrame(
        [
            {"au_id": "cwh_vm_1_hw_cw"},
            {"au_id": "cwh_vm_1_dr_hw"},
        ]
    ).to_csv(selected_au_csv, index=False)

    stand_origin_assignment_csv = tmp_path / "stand_origin_assignment.csv"
    pd.DataFrame(
        [
            {
                "forest_cover_id": 101,
                "au_id": "cwh_vm_1_hw_cw",
                "origin_class": "fire_origin",
            },
            {
                "forest_cover_id": 102,
                "au_id": "cwh_vm_1_dr_cw",
                "origin_class": "logging_origin",
            },
        ]
    ).to_csv(stand_origin_assignment_csv, index=False)

    stand_au_assignment_csv = tmp_path / "stand_au_assignment.csv"
    pd.DataFrame(
        [
            {
                "forest_cover_id": 101,
                "au_id": "cwh_vm_1_hw_cw",
                "shape_area_ha": 10.0,
                "leading_species_1": "HW",
                "leading_species_2": "CW",
                "leading_species_1_share": 60.0,
                "leading_species_2_share": 30.0,
            },
            {
                "forest_cover_id": 102,
                "au_id": "cwh_vm_1_dr_cw",
                "shape_area_ha": 8.0,
                "leading_species_1": "DR",
                "leading_species_2": "HW",
                "leading_species_1_share": 55.0,
                "leading_species_2_share": 25.0,
            },
        ]
    ).to_csv(stand_au_assignment_csv, index=False)

    managed_bootstrap_csv = tmp_path / "managed_au_bootstrap_table.csv"
    pd.DataFrame(
        [
            {
                "au_id": "cwh_vm_1_hw_cw",
                "managed_species_1": "CW",
                "managed_species_2": "FD",
                "managed_species_3": "BA",
                "managed_species_4": "",
                "managed_species_5": "",
                "managed_pct_1": 50.0,
                "managed_pct_2": 30.0,
                "managed_pct_3": 20.0,
                "managed_pct_4": 0.0,
                "managed_pct_5": 0.0,
            },
            {
                "au_id": "cwh_vm_1_dr_hw",
                "managed_species_1": "DR",
                "managed_species_2": "HW",
                "managed_species_3": "",
                "managed_species_4": "",
                "managed_species_5": "",
                "managed_pct_1": 60.0,
                "managed_pct_2": 40.0,
                "managed_pct_3": 0.0,
                "managed_pct_4": 0.0,
                "managed_pct_5": 0.0,
            },
        ]
    ).to_csv(managed_bootstrap_csv, index=False)

    first_growth_curves_csv = tmp_path / "first_growth_au_curves.csv"
    pd.DataFrame(
        [
            {"au_id": "cwh_vm_1_hw_cw", "age": 0, "volume": 0.0},
            {"au_id": "cwh_vm_1_hw_cw", "age": 10, "volume": 12.0},
        ]
    ).to_csv(first_growth_curves_csv, index=False)

    first_growth_diagnostics_csv = tmp_path / "first_growth_au_fit_diagnostics.csv"
    pd.DataFrame(
        [
            {"au_id": "cwh_vm_1_hw_cw", "selected_path": "smoothed_bin_pchip"},
            {"au_id": "cwh_vm_1_dr_hw", "selected_path": "insufficient_source_stands"},
        ]
    ).to_csv(first_growth_diagnostics_csv, index=False)

    managed_curves_csv = tmp_path / "managed_au_curves.csv"
    pd.DataFrame(
        [
            {"au_id": "cwh_vm_1_hw_cw", "age": 0, "volume": 0.0},
            {"au_id": "cwh_vm_1_dr_hw", "age": 0, "volume": 0.0},
        ]
    ).to_csv(managed_curves_csv, index=False)

    managed_run_manifest_json = tmp_path / "managed_au_run_manifest.json"
    managed_run_manifest_json.write_text(
        json.dumps(
            {
                "status": "completed",
                "curve_au_count": 2,
                "included_au_count": 2,
            }
        ),
        encoding="utf-8",
    )

    bad_curve_audit_summary_csv = tmp_path / "bad_curve_audit_summary.csv"
    pd.DataFrame(
        [
            {"au_id": "cwh_vm_1_hw_cw", "flagged": False},
            {"au_id": "cwh_vm_1_dr_hw", "flagged": True},
        ]
    ).to_csv(bad_curve_audit_summary_csv, index=False)

    result = initialize_mkrf_runtime_package(
        package_root=package_root,
        selected_au_csv=selected_au_csv,
        stand_origin_assignment_csv=stand_origin_assignment_csv,
        stand_au_assignment_csv=stand_au_assignment_csv,
        managed_bootstrap_csv=managed_bootstrap_csv,
        first_growth_curves_csv=first_growth_curves_csv,
        first_growth_diagnostics_csv=first_growth_diagnostics_csv,
        managed_curves_csv=managed_curves_csv,
        managed_run_manifest_json=managed_run_manifest_json,
        bad_curve_audit_summary_csv=bad_curve_audit_summary_csv,
    )

    assert result.package_root == package_root.resolve()
    assert result.selected_au_count == 2
    assert result.first_growth_curve_au_count == 1
    assert result.first_growth_missing_au_count == 1
    assert result.managed_curve_au_count == 2
    assert result.manifest_path.exists()
    assert result.curve_status_path.exists()
    assert result.analysis_au_runtime_status_path.exists()
    assert result.analysis_au_curve_refs_path.exists()
    assert result.runtime_au_remap_audit_path.exists()
    assert result.species_share_audit_path.exists()
    assert result.analysis_pin_path.exists()
    assert result.headless_runtime_common_path.exists()
    assert result.flow_targets_script_path.exists()
    assert result.xml_contract_path.exists()
    assert result.xml_curve_bank_path.exists()
    assert result.forestmodel_xml_path.exists()

    payload = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert payload["runtime_generation_status"] == "initialized_only"
    assert payload["counts"]["selected_au_count"] == 2
    assert payload["counts"]["first_growth_missing_au_count"] == 1
    assert payload["counts"]["managed_only_runtime_au_count"] == 1
    assert payload["curve_policy"]["first_growth_borrowing_allowed"] is False
    assert payload["source_contracts"]["stand_origin_assignment_csv"] == str(
        stand_origin_assignment_csv.resolve()
    )
    assert payload["source_contracts"]["stand_au_assignment_csv"] == str(
        stand_au_assignment_csv.resolve()
    )
    assert payload["source_contracts"]["managed_bootstrap_csv"] == str(
        managed_bootstrap_csv.resolve()
    )
    assert payload["source_contracts"]["runtime_au_remap_audit_csv"] == str(
        result.runtime_au_remap_audit_path.resolve()
    )
    assert payload["source_contracts"]["runtime_species_share_audit_csv"] == str(
        result.species_share_audit_path.resolve()
    )
    assert payload["source_contracts"]["analysis_pin"] == str(result.analysis_pin_path.resolve())
    assert payload["source_contracts"]["headless_runtime_common_bsh"] == str(
        result.headless_runtime_common_path.resolve()
    )
    assert payload["source_contracts"]["flow_targets_bsh"] == str(
        result.flow_targets_script_path.resolve()
    )
    assert payload["managed_only_runtime_policy"]["insufficient_support_borrowing"] == "forbidden"
    assert payload["runtime_au_normalization"]["remapped_source_au_count"] == 1

    curve_status = pd.read_csv(result.curve_status_path)
    assert curve_status["au_id"].tolist() == ["cwh_vm_1_dr_hw", "cwh_vm_1_hw_cw"]
    assert curve_status["runtime_curve_mode"].tolist() == [
        "managed_only",
        "first_growth_and_managed",
    ]
    assert curve_status["runtime_curve_note"].fillna("").tolist() == [
        "insufficient_source_stands_managed_only",
        "",
    ]

    tracks_status = pd.read_csv(result.analysis_au_runtime_status_path)
    assert tracks_status["au_id"].tolist() == ["cwh_vm_1_dr_hw", "cwh_vm_1_hw_cw"]
    assert tracks_status["runtime_curve_mode"].tolist() == [
        "managed_only",
        "first_growth_and_managed",
    ]

    curve_refs = pd.read_csv(result.analysis_au_curve_refs_path)
    assert curve_refs["au_id"].tolist() == ["cwh_vm_1_dr_hw", "cwh_vm_1_hw_cw"]
    assert curve_refs["first_growth_curve_id"].fillna("").tolist() == ["", "FG_CWH_VM_1_HW_CW"]
    assert curve_refs["managed_curve_id"].fillna("").tolist() == [
        "MG_CWH_VM_1_DR_HW",
        "MG_CWH_VM_1_HW_CW",
    ]

    remap_audit = pd.read_csv(result.runtime_au_remap_audit_path)
    assert remap_audit["raw_au_id"].tolist() == ["cwh_vm_1_dr_cw", "cwh_vm_1_hw_cw"]
    assert remap_audit["au_id"].tolist() == ["cwh_vm_1_dr_hw", "cwh_vm_1_hw_cw"]
    assert remap_audit["was_remapped"].tolist() == [True, False]

    species_share_audit = pd.read_csv(result.species_share_audit_path)
    natural_dr = species_share_audit.loc[
        (species_share_audit["origin_lane"] == "natural")
        & (species_share_audit["au_id"] == "cwh_vm_1_dr_hw")
        & (species_share_audit["species_bucket"] == "Dr")
    ].iloc[0]
    assert natural_dr["source_name"] == "stand_au_assignment"
    assert natural_dr["share_pct"] == pytest.approx(55.0)
    assert natural_dr["share_class"] == "nonzero"
    treated_hw = species_share_audit.loc[
        (species_share_audit["origin_lane"] == "treated")
        & (species_share_audit["au_id"] == "cwh_vm_1_dr_hw")
        & (species_share_audit["species_bucket"] == "Hw")
    ].iloc[0]
    assert treated_hw["source_name"] == "managed_bootstrap"
    assert treated_hw["share_pct"] == pytest.approx(40.0)
    assert treated_hw["share_class"] == "nonzero"

    xml_text = result.xml_contract_path.read_text(encoding="utf-8")
    assert "<mkrfRuntimeCurveContract" in xml_text
    assert 'runtimeCurveMode="managed_only"' in xml_text
    assert 'firstGrowthBorrowingAllowed="false"' in xml_text

    curve_bank_text = result.xml_curve_bank_path.read_text(encoding="utf-8")
    assert "<mkrfRuntimeCurveBank" in curve_bank_text
    assert '<analysisUnit id="cwh_vm_1_hw_cw" runtimeCurveMode="first_growth_and_managed">' in curve_bank_text
    assert "<firstGrowthCurve" in curve_bank_text
    assert "<managedCurve>" in curve_bank_text

    forestmodel_text = result.forestmodel_xml_path.read_text(encoding="utf-8")
    assert "<ForestModel" in forestmodel_text
    assert "MKRF canonical rebuild" in forestmodel_text
    assert (
        '<input block="Int(RES_KEY)" area="Shape_Area/10000" age="Int(AGE_2020)" '
        'exclude="CONTCLAS eq \'X\'" />' in forestmodel_text
    )
    assert forestmodel_text.index('curve id="FG_CWH_VM_1_HW_CW"') < forestmodel_text.index(
        '<define field="status"'
    )
    assert 'curve id="FG_CWH_VM_1_HW_CW"' in forestmodel_text
    assert 'curve id="MG_CWH_VM_1_DR_HW"' in forestmodel_text
    assert 'curve id="le10"' in forestmodel_text
    assert '<define field="status" column="CONTCLAS" />' in forestmodel_text
    assert '<define field="origin" column="lookupTable(Int(FOREST_COV),\'101,102\',\'natural,treated\')" />' in forestmodel_text
    assert (
        "<define field=\"statecode\" column=\"if(lookupTable(Int(FOREST_COV),'101,102',"
        "'natural,treated') eq 'natural','EN','EM')\" />"
        in forestmodel_text
    )
    assert '<define field="au" column="' in forestmodel_text
    assert "<define field=\"au\" column=\"lookupTable(Int(FOREST_COV),'101,102','cwh_vm_1_hw_cw,cwh_vm_1_dr_hw')\" />" in forestmodel_text
    assert "<define field=\"auf\" column=\"lookupTable(Int(FOREST_COV),'101,102','cwh_vm_1_hw_cw,cwh_vm_1_dr_hw')\" />" in forestmodel_text

    analysis_pin_text = result.analysis_pin_path.read_text(encoding="utf-8")
    assert 'String tracks_path_prefix = "../tracks/";' in analysis_pin_text
    assert 'sourceRelative("headless_runtime_common.bsh");' in analysis_pin_text
    assert 'sourceRelative("../scripts/targets/flowtargets.bsh");' in analysis_pin_text
    assert 'block_shape = "../spatial/fragments.shp";' in analysis_pin_text
    assert "setupYieldFlowTargets(control, periods, tracks_path_prefix);" in analysis_pin_text
    assert 'currTreatTheme.setFieldname("CURRENTTREATMENT");' in analysis_pin_text
    assert 'latestTreatTheme.setFieldname("LASTTREATMENT");' in analysis_pin_text
    assert 'patch0Theme.setFieldname("product.area.managed.treat.CC.size");' in analysis_pin_text
    assert 'patch1Theme.setFieldname("feature.area.managed.seral.le10.size");' in analysis_pin_text
    assert "femicQueueHeadlessStage();" in analysis_pin_text

    headless_common_text = result.headless_runtime_common_path.read_text(encoding="utf-8")
    assert "product.yield.managed.total" in headless_common_text
    assert "flow.even." in headless_common_text

    flow_targets_text = result.flow_targets_script_path.read_text(encoding="utf-8")
    assert '_collectAccounts("product.yield.managed.", tracksPathPrefix);' in flow_targets_text
    assert '_collectAccounts("feature.yield.managed.", tracksPathPrefix);' in flow_targets_text
    assert '<define field="aux" column="Int(FOREST_COV)" />' in forestmodel_text
    assert '<define field="hasfg"' not in forestmodel_text
    assert '<define field="managed" constant="\'C\'" />' in forestmodel_text
    assert '<attribute label="feature.area.retention.total">' in forestmodel_text
    assert '<attribute label="%f.area.%m.total">' in forestmodel_text
    assert '<attribute label="%f.area.%m.seral.le10">' in forestmodel_text
    assert (
        "<attribute label=\"'%f.area.%m.state.'+if(startswith(au,'thn_'),'THN',statecode)\""
        in forestmodel_text
    )
    assert '<attribute label="%f.yield.%m.total">' in forestmodel_text
    assert (
        "<attribute label=\"'%f.yield.%m.state.'+if(startswith(au,'thn_'),'THN',statecode)\""
        in forestmodel_text
    )
    assert '<attribute label="%f.yield.%m.merch.total">' in forestmodel_text
    assert '<attribute label="%f.yield.%m.indsp.Ba">' in forestmodel_text
    assert '<attribute label="%f.yield.%m.indsp.Cw">' in forestmodel_text
    assert '<attribute label="%f.yield.%m.indsp.Dr">' in forestmodel_text
    assert '<attribute label="%f.yield.%m.indsp.Hw">' in forestmodel_text
    assert 'select statement="status in unmanaged"' in forestmodel_text
    assert "hasfg eq" not in forestmodel_text
    assert "startswith(au,'em_')" not in forestmodel_text
    assert "startswith(au,'thn_')" in forestmodel_text
    assert "substring(au,4)" in forestmodel_text
    assert forestmodel_text.count('<attribute label="%f.yield.%m.indsp.Ba">') == 2
    assert forestmodel_text.count('<attribute label="%f.yield.%m.indsp.Cw">') == 2
    assert forestmodel_text.count('<attribute label="%f.yield.%m.indsp.Dr">') == 2
    assert forestmodel_text.count('<attribute label="%f.yield.%m.indsp.Hw">') == 2
    assert "*(" in forestmodel_text
    assert "<products>" in forestmodel_text
    assert '<attribute label="product.area.managed.total">' in forestmodel_text
    assert '<attribute label="\'product.area.managed.treat.\'+treatment">' in forestmodel_text
    assert '<attribute label="product.yield.managed.total">' in forestmodel_text
    assert '<attribute label="product.yield.managed.indsp.Ba">' in forestmodel_text
    assert '<attribute label="\'product.yield.managed.treat.\'+treatment">' in forestmodel_text
    assert "if(origin eq 'natural' and hasnatcurve eq 'Y'," in forestmodel_text
    assert (
        "curveId(lookupTable(if(startswith(au,'thn_'),substring(au,4),au),"
        "'cwh_vm_1_dr_hw,cwh_vm_1_hw_cw',"
        in forestmodel_text
    )
    assert "if(startswith(au,'thn_'),0.6,1)" in forestmodel_text
    assert "if(treatment eq 'CT',0.4,1)" in forestmodel_text
    assert '<curve idref="unity"' in forestmodel_text
    assert '<curve idref="le10"' in forestmodel_text
    assert 'select statement="status in managed and oper in operable"' in forestmodel_text
    assert 'select statement="status in managed"' in forestmodel_text
    assert "not startswith(au,'thn_')" in forestmodel_text
    assert "'thn_'+au" in forestmodel_text
    assert 'field="statecode" value="\'THN\'"' not in forestmodel_text
    assert "<track>" in forestmodel_text
    assert 'treatment label="CC"' in forestmodel_text
    assert 'treatment label="CT"' in forestmodel_text


def test_audit_mkrf_runtime_sanity_flags_zero_signal_with_nonzero_source_share(
    tmp_path: Path,
) -> None:
    package_root = tmp_path / "models" / "mkrf_patchworks_model"
    analysis_dir = package_root / "analysis"
    tracks_dir = package_root / "tracks"
    analysis_dir.mkdir(parents=True)
    tracks_dir.mkdir(parents=True)

    pd.DataFrame(
        [
            {
                "origin_lane": "natural",
                "source_name": "stand_au_assignment",
                "au_id": "cwh_vm_1_hw_cw",
                "species_bucket": "Dr",
                "share_pct": 35.0,
                "share_class": "nonzero",
            },
            {
                "origin_lane": "treated",
                "source_name": "managed_bootstrap",
                "au_id": "cwh_vm_1_hw_cw",
                "species_bucket": "Hw",
                "share_pct": 25.0,
                "share_class": "nonzero",
            },
        ]
    ).to_csv(analysis_dir / "runtime_species_share_audit.csv", index=False)

    pd.DataFrame(
        [
            {"ATTRIBUTE": "feature.yield.managed.indsp.Dr"},
            {"ATTRIBUTE": "product.yield.managed.indsp.Hw"},
        ]
    ).to_csv(tracks_dir / "accounts.csv", index=False)
    pd.DataFrame(
        [
            {"ATTRIBUTE": "feature.yield.managed.indsp.Dr"},
        ]
    ).to_csv(tracks_dir / "features.csv", index=False)
    pd.DataFrame(
        [
            {"ATTRIBUTE": "product.yield.managed.indsp.Hw"},
        ]
    ).to_csv(tracks_dir / "products.csv", index=False)

    stage_dir = tmp_path / "runtime" / "logs" / "headless_stage" / "demo"
    targets_dir = stage_dir / "targets"
    targets_dir.mkdir(parents=True)
    pd.DataFrame(
        [
            {"CURRENT": 100.0},
            {"CURRENT": 150.0},
        ]
    ).to_csv(targets_dir / "feature_yield_managed_indsp_Dr.csv", index=False)
    pd.DataFrame(
        [
            {"CURRENT": 0.0},
            {"CURRENT": 0.0},
        ]
    ).to_csv(targets_dir / "product_yield_managed_indsp_Hw.csv", index=False)

    result = audit_mkrf_runtime_sanity(
        package_root=package_root,
        stage_dir=stage_dir,
    )

    assert result.audit_csv_path.exists()
    assert result.summary_json_path.exists()
    assert result.row_count == 24
    assert result.failure_count == 1

    audit_frame = pd.read_csv(result.audit_csv_path)
    managed_dr = audit_frame.loc[
        audit_frame["target_label"].eq("feature.yield.managed.indsp.Dr")
    ].iloc[0]
    assert managed_dr["target_has_signal"]
    assert managed_dr["audit_status"] == "pass_signal_matches_source_share"

    managed_hw_product = audit_frame.loc[
        audit_frame["target_label"].eq("product.yield.managed.indsp.Hw")
    ].iloc[0]
    assert not managed_hw_product["target_has_signal"]
    assert managed_hw_product["audit_status"] == "fail_zero_signal_with_source_share"
