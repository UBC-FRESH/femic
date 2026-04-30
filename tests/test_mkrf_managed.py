from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from femic.pipeline.mkrf_managed import (
    build_mkrf_managed_au_bootstrap_table,
    build_mkrf_managed_au_msyt_table,
    parse_mkrf_managed_au_curves,
)
from femic.workflows.mkrf import build_mkrf_managed_au_curves


def test_build_mkrf_managed_au_bootstrap_table_marks_direct_and_unmatched() -> None:
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
                "au_id": "cwh_vm_1_hw_cw",
                "selected_rank": 2,
                "covered_area_ha": 50.0,
                "bec_zone": "cwh",
                "bec_subzone": "vm",
                "bec_variant": "1",
                "leading_species_1": "hw",
                "leading_species_2": "cw",
            },
        ]
    )
    assignment = pd.DataFrame(
        [
            {"au_id": "cwh_vm_1_cw_fdc", "shape_area_ha": 60.0},
            {"au_id": "cwh_vm_1_cw_fdc", "shape_area_ha": 40.0},
        ]
    )
    man_si_by_au = pd.DataFrame(
        [
            {"AU": 2011, "BEC": "CWHvm1", "SI": 22.0},
            {"AU": 2012, "BEC": "CWHvm1", "SI": 28.0},
            {"AU": 2013, "BEC": "CWHvm1", "SI": 35.0},
        ]
    )
    tipsy_spp_comp = pd.DataFrame(
        [
            {"AU": 2011, "CW": 60.0, "FD": 40.0},
            {"AU": 2012, "CW": 60.0, "FD": 40.0},
            {"AU": 2013, "CW": 60.0, "FD": 40.0},
        ]
    )

    out = build_mkrf_managed_au_bootstrap_table(
        selected_au_table=selected_au_table,
        assignment=assignment,
        man_si_by_au=man_si_by_au,
        tipsy_spp_comp=tipsy_spp_comp,
    )

    direct = out.loc[out["au_id"] == "cwh_vm_1_cw_fdc"].iloc[0]
    assert direct["bootstrap_status"] == "direct"
    assert direct["managed_curve_id"] == 60001
    assert direct["managed_si"] == 28.0
    assert direct["managed_species_1"] == "CW"
    assert direct["managed_species_2"] == "FD"

    unmatched = out.loc[out["au_id"] == "cwh_vm_1_hw_cw"].iloc[0]
    assert unmatched["bootstrap_status"] == "unmatched"
    assert pd.isna(unmatched["managed_si"])


def test_build_mkrf_managed_au_msyt_table_uses_included_rows_only() -> None:
    bootstrap_table = pd.DataFrame(
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
                "managed_curve_id": 60001,
                "bootstrap_status": "direct",
                "managed_si": 28.0,
                "regen_delay": 1,
                "density_total": 1400,
                "oaf1": 1.0,
                "oaf2": 0.95,
                "managed_species_1": "CW",
                "managed_species_2": "FD",
                "managed_species_3": "",
                "managed_species_4": "",
                "managed_species_5": "",
                "managed_pct_1": 60.0,
                "managed_pct_2": 40.0,
                "managed_pct_3": 0.0,
                "managed_pct_4": 0.0,
                "managed_pct_5": 0.0,
            },
            {
                "au_id": "cwh_vm_1_hw_cw",
                "selected_rank": 2,
                "covered_area_ha": 50.0,
                "bec_zone": "cwh",
                "bec_subzone": "vm",
                "bec_variant": "1",
                "leading_species_1": "hw",
                "leading_species_2": "cw",
                "managed_curve_id": 60002,
                "bootstrap_status": "unmatched",
                "managed_si": None,
                "regen_delay": 1,
                "density_total": 1400,
                "oaf1": 1.0,
                "oaf2": 0.95,
                "managed_species_1": "",
                "managed_species_2": "",
                "managed_species_3": "",
                "managed_species_4": "",
                "managed_species_5": "",
                "managed_pct_1": 0.0,
                "managed_pct_2": 0.0,
                "managed_pct_3": 0.0,
                "managed_pct_4": 0.0,
                "managed_pct_5": 0.0,
            },
        ]
    )

    out = build_mkrf_managed_au_msyt_table(bootstrap_table=bootstrap_table)

    assert len(out) == 1
    row = out.iloc[0].to_dict()
    assert row["feature_id"] == 60001
    assert row["bec_zone"] == "CWH"
    assert row["bec_subzone"] == "vm"
    assert row["planted_species1"] == "Cw"
    assert row["planted_species2"] == "Fd"
    assert row["cw_si"] == 28.0
    assert row["fd_si"] == 28.0


def test_parse_mkrf_managed_au_curves_maps_back_to_au_id(tmp_path: Path) -> None:
    bootstrap_table = pd.DataFrame(
        [
            {
                "au_id": "cwh_vm_1_cw_fdc",
                "managed_curve_id": 60001,
                "bootstrap_status": "direct",
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
                "bootstrap_status": "direct",
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
