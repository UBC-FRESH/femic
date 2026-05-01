from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from femic.pipeline.mkrf_managed import (
    build_mkrf_managed_au_bootstrap_table,
    build_mkrf_managed_au_msyt_table,
    build_mkrf_stand_origin_assignment,
    classify_mkrf_origin,
    load_mkrf_managed_rule_config,
    parse_mkrf_managed_au_curves,
)
from femic.workflows.mkrf import build_mkrf_managed_au_curves


def _write_managed_rules_yaml(tmp_path: Path) -> Path:
    path = tmp_path / "tsamkrf.yaml"
    path.write_text(
        """
schema_version: 1
case_code: "mkrf"
origin_rules:
  fire_origin_min_age: 80
managed_defaults:
  density_total: 1500
  regen_delay: 1
  oaf1: 1.0
  oaf2: 0.95
  planted_percent: 100
  baseline_system: "clearcut"
  ct_eligible: true
  ct_target_age: 40
  ct_on_fire_origin: false
families:
  cwh_vm_1:
    bec_zone: "cwh"
    bec_subzone: "vm"
    bec_variant: "1"
    species_mix:
      FD: 45
      CW: 45
      PW: 10
  cwh_vm_2:
    bec_zone: "cwh"
    bec_subzone: "vm"
    bec_variant: "2"
    species_mix:
      CW: 70
      FD: 15
      PW: 5
      BA: 5
      SS: 5
""".strip(),
        encoding="utf-8",
    )
    return path


def test_classify_mkrf_origin_uses_79_80_boundary() -> None:
    assert classify_mkrf_origin(age_2020=79) == "logging_origin"
    assert classify_mkrf_origin(age_2020=80) == "fire_origin"
    assert classify_mkrf_origin(age_2020=None) == "unknown"


def test_build_mkrf_stand_origin_assignment_publishes_origin_classes() -> None:
    assignment = pd.DataFrame(
        [
            {
                "forest_cover_id": 101,
                "res_key": 1,
                "shape_area_ha": 10.0,
                "au_id": "cwh_vm_1_cw_fdc",
                "bec_zone": "cwh",
                "bec_subzone": "vm",
                "bec_variant": "1",
                "leading_species_1": "cw",
                "leading_species_2": "fdc",
            },
            {
                "forest_cover_id": 102,
                "res_key": 2,
                "shape_area_ha": 11.0,
                "au_id": "cwh_vm_1_cw_fdc",
                "bec_zone": "cwh",
                "bec_subzone": "vm",
                "bec_variant": "1",
                "leading_species_1": "cw",
                "leading_species_2": "fdc",
            },
        ]
    )
    source_table = pd.DataFrame(
        [
            {
                "FOREST_COVER_ID": 101,
                "AGE_2020": 79,
                "TCL_1_ESTIMATED_SITE_INDEX": 24.0,
            },
            {
                "FOREST_COVER_ID": 102,
                "AGE_2020": 80,
                "TCL_1_ESTIMATED_SITE_INDEX": 30.0,
            },
        ]
    )

    out = build_mkrf_stand_origin_assignment(
        assignment=assignment,
        source_table=source_table,
        fire_origin_min_age=80.0,
    )

    assert out["forest_cover_id"].tolist() == [101, 102]
    assert out["origin_class"].tolist() == ["logging_origin", "fire_origin"]
    assert out["site_index"].tolist() == [24.0, 30.0]


def test_build_mkrf_managed_au_bootstrap_table_uses_expert_rules_and_si_fallback(
    tmp_path: Path,
) -> None:
    rules_yaml = _write_managed_rules_yaml(tmp_path)
    rule_config = load_mkrf_managed_rule_config(rules_yaml)
    selected_au_table = pd.DataFrame(
        [
            {
                "au_id": "cwh_vm_1_cw_fdc",
                "selected_rank": 1,
                "covered_area_ha": 100.0,
                "bec_zone": "cwh",
                "bec_subzone": "vm",
                "bec_variant": "1",
                "leading_species_1": "cw",
                "leading_species_2": "fdc",
            },
            {
                "au_id": "cwh_vm_2_cw_hw",
                "selected_rank": 2,
                "covered_area_ha": 80.0,
                "bec_zone": "cwh",
                "bec_subzone": "vm",
                "bec_variant": "2",
                "leading_species_1": "cw",
                "leading_species_2": "hw",
            },
            {
                "au_id": "mh_mm_1_hw_cw",
                "selected_rank": 3,
                "covered_area_ha": 10.0,
                "bec_zone": "mh",
                "bec_subzone": "mm",
                "bec_variant": "1",
                "leading_species_1": "hw",
                "leading_species_2": "cw",
            },
        ]
    )
    stand_origin_assignment = pd.DataFrame(
        [
            {
                "forest_cover_id": 101,
                "au_id": "cwh_vm_1_cw_fdc",
                "origin_class": "logging_origin",
                "site_index": 24.0,
            },
            {
                "forest_cover_id": 102,
                "au_id": "cwh_vm_1_cw_fdc",
                "origin_class": "logging_origin",
                "site_index": 30.0,
            },
            {
                "forest_cover_id": 103,
                "au_id": "cwh_vm_1_cw_fdc",
                "origin_class": "fire_origin",
                "site_index": 36.0,
            },
            {
                "forest_cover_id": 201,
                "au_id": "cwh_vm_2_cw_hw",
                "origin_class": "fire_origin",
                "site_index": 21.0,
            },
            {
                "forest_cover_id": 202,
                "au_id": "cwh_vm_2_cw_hw",
                "origin_class": "fire_origin",
                "site_index": 27.0,
            },
        ]
    )

    out = build_mkrf_managed_au_bootstrap_table(
        selected_au_table=selected_au_table,
        stand_origin_assignment=stand_origin_assignment,
        rule_config=rule_config,
    )

    vm1 = out.loc[out["au_id"] == "cwh_vm_1_cw_fdc"].iloc[0]
    assert vm1["bootstrap_status"] == "expert_rule"
    assert vm1["managed_si_source"] == "logging_origin_median"
    assert vm1["managed_si"] == 27.0
    assert vm1["managed_species_1"] == "CW"
    assert vm1["managed_species_2"] == "FD"
    assert vm1["managed_species_3"] == "PW"
    assert vm1["density_total"] == 1500
    assert bool(vm1["ct_eligible"]) is True

    vm2 = out.loc[out["au_id"] == "cwh_vm_2_cw_hw"].iloc[0]
    assert vm2["bootstrap_status"] == "expert_rule"
    assert vm2["managed_si_source"] == "all_stands_median"
    assert vm2["managed_si"] == 24.0
    assert vm2["managed_species_1"] == "CW"
    assert vm2["managed_species_2"] == "FD"
    assert vm2["managed_species_3"] == "BA"
    assert vm2["managed_species_4"] == "PW"
    assert vm2["managed_species_5"] == "SS"

    unmatched = out.loc[out["au_id"] == "mh_mm_1_hw_cw"].iloc[0]
    assert unmatched["bootstrap_status"] == "unmatched"
    assert unmatched["mapping_path"] == "no_matching_managed_rule"


def test_build_mkrf_managed_au_msyt_table_supports_pw_ss_species() -> None:
    bootstrap_table = pd.DataFrame(
        [
            {
                "au_id": "cwh_vm_2_cw_hw",
                "selected_rank": 2,
                "bec_zone": "cwh",
                "bec_subzone": "vm",
                "bec_variant": "2",
                "managed_curve_id": 60002,
                "included_in_msyt": True,
                "managed_si": 24.0,
                "regen_delay": 1,
                "density_total": 1500,
                "oaf1": 1.0,
                "oaf2": 0.95,
                "managed_species_1": "CW",
                "managed_species_2": "FD",
                "managed_species_3": "PW",
                "managed_species_4": "BA",
                "managed_species_5": "SS",
                "managed_pct_1": 70.0,
                "managed_pct_2": 15.0,
                "managed_pct_3": 5.0,
                "managed_pct_4": 5.0,
                "managed_pct_5": 5.0,
            }
        ]
    )

    out = build_mkrf_managed_au_msyt_table(bootstrap_table=bootstrap_table)

    row = out.iloc[0].to_dict()
    assert row["feature_id"] == 60002
    assert row["planted_species1"] == "Cw"
    assert row["planted_species2"] == "Fd"
    assert row["planted_species3"] == "Pw"
    assert row["planted_species4"] == "Ba"
    assert row["planted_species5"] == "Ss"
    assert row["cw_si"] == 24.0
    assert row["fd_si"] == 24.0
    assert row["pw_si"] == 24.0
    assert row["ss_si"] == 24.0
    assert row["planted_density1"] == 1050


def test_parse_mkrf_managed_au_curves_maps_back_to_au_id(tmp_path: Path) -> None:
    bootstrap_table = pd.DataFrame(
        [
            {
                "au_id": "cwh_vm_1_cw_fdc",
                "managed_curve_id": 60001,
                "included_in_msyt": True,
            }
        ]
    )
    output_csv = tmp_path / "managed_output.csv"
    pd.DataFrame(
        [
            {
                "feature_id": 60001,
                "MVcon_0": 0.0,
                "MVdec_0": 0.0,
                "HTcon_0": 0.0,
                "HTdec_0": 0.0,
                "gVol_0": 0.0,
                "CC_0": 0.0,
                "MVcon_10": 55.0,
                "MVdec_10": 5.0,
                "HTcon_10": 3.5,
                "HTdec_10": 0.0,
                "gVol_10": 65.0,
                "CC_10": 0.5,
            }
        ]
    ).to_csv(output_csv, index=False)

    out = parse_mkrf_managed_au_curves(
        output_csv=output_csv,
        bootstrap_table=bootstrap_table,
    )

    assert out["au_id"].unique().tolist() == ["cwh_vm_1_cw_fdc"]
    assert out["managed_curve_id"].unique().tolist() == [60001]
    assert out["age"].tolist() == [0, 10]
    assert out["volume"].tolist() == [0.0, 60.0]


def test_build_mkrf_managed_au_curves_writes_blocked_manifest(
    monkeypatch,
    tmp_path: Path,
) -> None:
    bootstrap_csv = tmp_path / "managed_au_bootstrap_table.csv"
    msyt_csv = tmp_path / "managed_au_msyt.csv"
    pd.DataFrame(
        [
            {
                "au_id": "cwh_vm_1_cw_fdc",
                "managed_curve_id": 60001,
                "included_in_msyt": True,
            }
        ]
    ).to_csv(bootstrap_csv, index=False)
    pd.DataFrame([{"feature_id": 60001}]).to_csv(msyt_csv, index=False)

    def _missing_btc(**_kwargs: object) -> None:
        raise FileNotFoundError("TIPSYbtc.exe not found")

    monkeypatch.setattr("femic.workflows.mkrf.run_btc_cli", _missing_btc)

    result = build_mkrf_managed_au_curves(
        bootstrap_csv=bootstrap_csv,
        msyt_csv=msyt_csv,
        output_dir=tmp_path,
        log_dir=tmp_path / "logs",
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert result.status == "blocked"
    assert manifest["reason"] == "missing_btc_runtime"
    assert result.curves_path is None
