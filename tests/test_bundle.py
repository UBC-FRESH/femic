from __future__ import annotations

from pathlib import Path

import pandas as pd
import numpy as np

from femic.pipeline.bundle import (
    assign_curve_ids_from_au_table,
    build_bundle_tables_from_curves,
    bundle_tables_ready,
    emit_missing_au_curve_mapping_warning,
    ensure_au_table_index,
    ensure_scsi_au_from_table,
    load_bundle_tables,
    resolve_bundle_paths,
    write_bundle_tables,
)


def test_resolve_bundle_paths_and_ready(tmp_path: Path) -> None:
    paths = resolve_bundle_paths(base_dir=tmp_path / "bundle", ensure_dir=True)

    assert paths.bundle_dir == tmp_path / "bundle"
    assert bundle_tables_ready(paths=paths) is False

    (paths.au_table).write_text("au_id,tsa,stratum_code,si_level\n", encoding="utf-8")
    (paths.curve_table).write_text("curve_id,curve_type\n", encoding="utf-8")
    (paths.curve_points_table).write_text("curve_id,x,y\n", encoding="utf-8")
    assert bundle_tables_ready(paths=paths) is True


def test_load_write_bundle_tables_and_normalize_tsa(tmp_path: Path) -> None:
    paths = resolve_bundle_paths(base_dir=tmp_path / "bundle", ensure_dir=True)
    au_table = pd.DataFrame(
        [{"au_id": 800001, "tsa": "8", "stratum_code": "S1", "si_level": "M"}]
    )
    curve_table = pd.DataFrame([{"curve_id": 1, "curve_type": "untreated"}])
    curve_points_table = pd.DataFrame([{"curve_id": 1, "x": 10, "y": 50.0}])

    write_bundle_tables(
        paths=paths,
        au_table=au_table,
        curve_table=curve_table,
        curve_points_table=curve_points_table,
    )

    loaded_au, loaded_curve, loaded_points = load_bundle_tables(
        paths=paths,
        pd_module=pd,
        normalize_tsa_code_fn=lambda v: f"{int(v):02d}",
    )

    assert loaded_au.loc[0, "tsa"] == "08"
    assert loaded_curve.loc[0, "curve_type"] == "untreated"
    assert loaded_points.loc[0, "y"] == 50.0


def test_ensure_scsi_au_from_table_populates_missing_entries() -> None:
    au_table = pd.DataFrame(
        [
            {"au_id": 800005, "tsa": "8", "stratum_code": "BWBS_AT", "si_level": "L"},
            {"au_id": 800005, "tsa": "8", "stratum_code": "BWBS_AT", "si_level": "L"},
        ]
    )
    scsi_au: dict[str, dict[tuple[str, str], int]] = {}

    ensure_scsi_au_from_table(
        au_table=au_table,
        scsi_au=scsi_au,
        normalize_tsa_code_fn=lambda v: f"{int(v):02d}",
    )

    assert scsi_au["08"][("BWBS_AT", "L")] == 5


def test_ensure_au_table_index_sets_index_when_column_present() -> None:
    frame = pd.DataFrame([{"au_id": 800001, "tsa": "08"}])
    out = ensure_au_table_index(au_table=frame)
    assert out.index.name == "au_id"
    assert int(out.index[0]) == 800001


def test_ensure_au_table_index_noops_when_column_missing() -> None:
    frame = pd.DataFrame([{"tsa": "08"}]).set_index("tsa")
    out = ensure_au_table_index(au_table=frame)
    assert out.index.name == "tsa"


def test_build_bundle_tables_from_curves_builds_untreated_and_treated_rows() -> None:
    vdyp_curves_smooth = {
        "08": pd.DataFrame(
            [
                {"stratum_code": "BWBS_AT", "si_level": "L", "age": 10, "volume": 1.0},
                {"stratum_code": "BWBS_AT", "si_level": "L", "age": 20, "volume": 2.0},
            ]
        )
    }
    tipsy_curves = {
        "08": pd.DataFrame(
            [
                {"AU": 20005, "Age": 10, "Yield": 1.5},
                {"AU": 20005, "Age": 20, "Yield": 2.5},
            ]
        )
    }
    scsi_au = {"08": {("BWBS_AT", "L"): 5}}

    out = build_bundle_tables_from_curves(
        tsa_list=["08"],
        vdyp_curves_smooth=vdyp_curves_smooth,
        tipsy_curves=tipsy_curves,
        scsi_au=scsi_au,
        canfi_species_fn=lambda _s: 100,
        pd_module=pd,
        message_fn=lambda _m: None,
    )

    assert len(out.au_table) == 1
    assert int(out.au_table.loc[0, "au_id"]) == 800005
    assert int(out.au_table.loc[0, "treated_curve_id"]) == 820005
    assert int(out.au_table.loc[0, "untreated_curve_id"]) == 800005
    assert int(out.au_table.loc[0, "managed_curve_id"]) == 820005
    assert sorted(out.curve_table["curve_type"].tolist()) == ["treated", "untreated"]
    assert len(out.curve_points_table) == 4
    assert out.missing_au_curve_mappings.empty


def test_build_bundle_tables_from_curves_tracks_missing_mappings() -> None:
    vdyp_curves_smooth = {
        "08": pd.DataFrame(
            [{"stratum_code": "BWBS_AT", "si_level": "L", "age": 10, "volume": 1.0}]
        )
    }
    tipsy_curves = {"08": pd.DataFrame(columns=["AU", "Age", "Yield"])}
    scsi_au: dict[str, dict[tuple[str, str], int]] = {"08": {}}

    out = build_bundle_tables_from_curves(
        tsa_list=["08"],
        vdyp_curves_smooth=vdyp_curves_smooth,
        tipsy_curves=tipsy_curves,
        scsi_au=scsi_au,
        canfi_species_fn=lambda _s: 100,
        pd_module=pd,
        message_fn=lambda _m: None,
    )

    assert out.au_table.empty
    assert len(out.missing_au_curve_mappings) == 1
    assert out.missing_au_curve_mappings.loc[0, "stratum_code"] == "BWBS_AT"


def test_build_bundle_tables_from_curves_adds_species_proportion_curves() -> None:
    vdyp_curves_smooth = {
        "08": pd.DataFrame(
            [
                {"stratum_code": "BWBS_AT", "si_level": "L", "age": 10, "volume": 1.0},
                {"stratum_code": "BWBS_AT", "si_level": "L", "age": 20, "volume": 2.0},
            ]
        )
    }
    tipsy_curves = {
        "08": pd.DataFrame(
            [
                {"AU": 20005, "Age": 10, "Yield": 1.5},
                {"AU": 20005, "Age": 20, "Yield": 2.5},
            ]
        )
    }
    tipsy_spp = {"08": pd.DataFrame([{"AU": 20005, "SW": 60.0, "PL": 40.0}])}
    vdyp_spp = {"08": {("BWBS_AT", "L"): {"SW": 0.7, "PL": 0.3}}}
    scsi_au = {"08": {("BWBS_AT", "L"): 5}}

    out = build_bundle_tables_from_curves(
        tsa_list=["08"],
        vdyp_curves_smooth=vdyp_curves_smooth,
        tipsy_curves=tipsy_curves,
        scsi_au=scsi_au,
        canfi_species_fn=lambda _s: 100,
        species_universe=["SW", "PL"],
        vdyp_species_proportions=vdyp_spp,
        tipsy_species_proportions=tipsy_spp,
        pd_module=pd,
        message_fn=lambda _m: None,
    )

    curve_types = set(out.curve_table["curve_type"].tolist())
    assert "untreated_species_prop_SW" in curve_types
    assert "untreated_species_prop_PL" in curve_types
    assert "treated_species_prop_SW" in curve_types
    assert "treated_species_prop_PL" in curve_types

    unmanaged_sw_id = out.curve_table.loc[
        out.curve_table["curve_type"] == "untreated_species_prop_SW", "curve_id"
    ].iloc[0]
    managed_sw_id = out.curve_table.loc[
        out.curve_table["curve_type"] == "treated_species_prop_SW", "curve_id"
    ].iloc[0]
    unmanaged_sw_y = out.curve_points_table.loc[
        out.curve_points_table["curve_id"] == unmanaged_sw_id, "y"
    ].iloc[0]
    managed_sw_y = out.curve_points_table.loc[
        out.curve_points_table["curve_id"] == managed_sw_id, "y"
    ].iloc[0]
    assert unmanaged_sw_y == 0.7
    assert managed_sw_y == 0.6


def test_build_bundle_tables_from_curves_normalizes_treated_species_mix_to_one() -> (
    None
):
    vdyp_curves_smooth = {
        "08": pd.DataFrame(
            [
                {"stratum_code": "BWBS_FD", "si_level": "L", "age": 10, "volume": 1.0},
                {"stratum_code": "BWBS_FD", "si_level": "L", "age": 20, "volume": 2.0},
            ]
        )
    }
    tipsy_curves = {
        "08": pd.DataFrame(
            [
                {"AU": 20005, "Age": 10, "Yield": 1.5},
                {"AU": 20005, "Age": 20, "Yield": 2.5},
            ]
        )
    }
    # NaN columns should be ignored and the remaining finite shares normalized.
    tipsy_spp = {
        "08": pd.DataFrame(
            [{"AU": 20005, "CW": 20.0, "FD": 10.0, "HW": 70.0, "PLC": float("nan")}]
        )
    }
    vdyp_spp = {"08": {("BWBS_FD", "L"): {"FDC": 0.1, "HW": 0.9}}}
    scsi_au = {"08": {("BWBS_FD", "L"): 5}}

    out = build_bundle_tables_from_curves(
        tsa_list=["08"],
        vdyp_curves_smooth=vdyp_curves_smooth,
        tipsy_curves=tipsy_curves,
        scsi_au=scsi_au,
        canfi_species_fn=lambda _s: 101,
        species_universe=["CW", "FDC", "HW", "PLC"],
        vdyp_species_proportions=vdyp_spp,
        tipsy_species_proportions=tipsy_spp,
        pd_module=pd,
        message_fn=lambda _m: None,
    )

    managed_rows = out.curve_table[
        out.curve_table["curve_type"].str.startswith("treated_species_prop_")
    ].merge(out.curve_points_table, on="curve_id", how="left")
    assert managed_rows["y"].sum() == 1.0

    treated_fdc_id = out.curve_table.loc[
        out.curve_table["curve_type"] == "treated_species_prop_FDC", "curve_id"
    ].iloc[0]
    treated_fdc_y = out.curve_points_table.loc[
        out.curve_points_table["curve_id"] == treated_fdc_id, "y"
    ].iloc[0]
    assert treated_fdc_y == 0.1


def test_build_bundle_tables_from_curves_maps_tipsy_fd_to_fdc() -> None:
    vdyp_curves_smooth = {
        "08": pd.DataFrame(
            [
                {"stratum_code": "BWBS_FD", "si_level": "L", "age": 10, "volume": 1.0},
                {"stratum_code": "BWBS_FD", "si_level": "L", "age": 20, "volume": 2.0},
            ]
        )
    }
    tipsy_curves = {
        "08": pd.DataFrame(
            [
                {"AU": 20005, "Age": 10, "Yield": 1.5},
                {"AU": 20005, "Age": 20, "Yield": 2.5},
            ]
        )
    }
    # Legacy TIPSY outputs use FD; bundle species universe uses canonical FDC.
    tipsy_spp = {"08": pd.DataFrame([{"AU": 20005, "FD": 10.0, "HW": 90.0}])}
    vdyp_spp = {"08": {("BWBS_FD", "L"): {"FDC": 0.1, "HW": 0.9}}}
    scsi_au = {"08": {("BWBS_FD", "L"): 5}}

    out = build_bundle_tables_from_curves(
        tsa_list=["08"],
        vdyp_curves_smooth=vdyp_curves_smooth,
        tipsy_curves=tipsy_curves,
        scsi_au=scsi_au,
        canfi_species_fn=lambda _s: 101,
        species_universe=["FDC", "HW"],
        vdyp_species_proportions=vdyp_spp,
        tipsy_species_proportions=tipsy_spp,
        pd_module=pd,
        message_fn=lambda _m: None,
    )

    treated_fdc_id = out.curve_table.loc[
        out.curve_table["curve_type"] == "treated_species_prop_FDC", "curve_id"
    ].iloc[0]
    treated_fdc_y = out.curve_points_table.loc[
        out.curve_points_table["curve_id"] == treated_fdc_id, "y"
    ].iloc[0]
    assert treated_fdc_y == 0.1


def test_build_bundle_tables_from_curves_repairs_treated_mix_with_missing_untreated_species() -> (
    None
):
    vdyp_curves_smooth = {
        "08": pd.DataFrame(
            [
                {
                    "stratum_code": "CWH_DR_HW",
                    "si_level": "L",
                    "age": 10,
                    "volume": 1.0,
                },
                {
                    "stratum_code": "CWH_DR_HW",
                    "si_level": "L",
                    "age": 20,
                    "volume": 2.0,
                },
            ]
        )
    }
    tipsy_curves = {
        "08": pd.DataFrame(
            [
                {"AU": 20005, "Age": 10, "Yield": 1.5},
                {"AU": 20005, "Age": 20, "Yield": 2.5},
            ]
        )
    }
    tipsy_spp = {
        "08": pd.DataFrame([{"AU": 20005, "CW": 20.0, "FD": 10.0, "HW": 70.0}])
    }
    vdyp_spp = {
        "08": {("CWH_DR_HW", "L"): {"CW": 0.1, "DR": 0.3, "FDC": 0.1, "HW": 0.5}}
    }
    scsi_au = {"08": {("CWH_DR_HW", "L"): 5}}

    out = build_bundle_tables_from_curves(
        tsa_list=["08"],
        vdyp_curves_smooth=vdyp_curves_smooth,
        tipsy_curves=tipsy_curves,
        scsi_au=scsi_au,
        canfi_species_fn=lambda _s: 101,
        species_universe=["CW", "DR", "FDC", "HW"],
        vdyp_species_proportions=vdyp_spp,
        tipsy_species_proportions=tipsy_spp,
        pd_module=pd,
        message_fn=lambda _m: None,
    )

    treated_rows = out.curve_table[
        out.curve_table["curve_type"].str.startswith("treated_species_prop_")
    ].merge(out.curve_points_table, on="curve_id", how="left")
    assert treated_rows["y"].sum() == 1.0

    treated_dr_id = out.curve_table.loc[
        out.curve_table["curve_type"] == "treated_species_prop_DR", "curve_id"
    ].iloc[0]
    treated_dr_y = out.curve_points_table.loc[
        out.curve_points_table["curve_id"] == treated_dr_id, "y"
    ].iloc[0]
    assert treated_dr_y > 0.0

    treated_cw_id = out.curve_table.loc[
        out.curve_table["curve_type"] == "treated_species_prop_CW", "curve_id"
    ].iloc[0]
    treated_cw_y = out.curve_points_table.loc[
        out.curve_points_table["curve_id"] == treated_cw_id, "y"
    ].iloc[0]
    # CW remains present after repair, but shrinks to make room for missing DR.
    assert treated_cw_y < 0.2


def test_bundle_tables_support_named_unit_codes() -> None:
    vdyp_curves_smooth = {
        "k3z": pd.DataFrame(
            [
                {"stratum_code": "CWH_HW", "si_level": "L", "age": 10, "volume": 1.0},
                {"stratum_code": "CWH_HW", "si_level": "L", "age": 20, "volume": 2.0},
            ]
        )
    }
    tipsy_curves = {"k3z": pd.DataFrame(columns=["AU", "Age", "Yield"])}
    scsi_au = {"k3z": {("CWH_HW", "L"): 5}}

    out = build_bundle_tables_from_curves(
        tsa_list=["k3z"],
        vdyp_curves_smooth=vdyp_curves_smooth,
        tipsy_curves=tipsy_curves,
        scsi_au=scsi_au,
        canfi_species_fn=lambda _s: 402,
        pd_module=pd,
        message_fn=lambda _m: None,
    )
    assert len(out.au_table) == 1
    assert int(out.au_table.loc[0, "au_id"]) > 90_000_000

    rebuilt_scsi: dict[str, dict[tuple[str, str], int]] = {}
    ensure_scsi_au_from_table(
        au_table=out.au_table,
        scsi_au=rebuilt_scsi,
        normalize_tsa_code_fn=lambda value: str(value),
    )
    assert rebuilt_scsi["k3z"][("CWH_HW", "L")] == 5


def test_emit_missing_au_curve_mapping_warning_emits_expected_lines() -> None:
    missing_df = pd.DataFrame(
        [
            {"tsa": "08", "stratum_code": "BWBS_AT", "si_level": "L"},
            {"tsa": "08", "stratum_code": "BWBS_AT", "si_level": "L"},
        ]
    )
    messages: list[str] = []
    emit_missing_au_curve_mapping_warning(
        missing_df=missing_df,
        message_fn=messages.append,
        top_n=1,
    )
    assert messages[0].startswith(
        "Warning: skipped VDYP curve combos without AU mapping (2 rows). Top 1:"
    )
    assert "BWBS_AT" in messages[1]


def test_assign_curve_ids_from_au_table_assigns_managed_and_unmanaged() -> None:
    f_table = pd.DataFrame(
        [
            {"au": 800005, "PROJ_AGE_1": 40},
            {"au": 800005, "PROJ_AGE_1": 80},
            {"au": None, "PROJ_AGE_1": 40},
        ]
    )
    au_table = pd.DataFrame(
        [
            {
                "au_id": 800005,
                "managed_curve_id": 820005,
                "unmanaged_curve_id": 800005,
            }
        ]
    )

    out = assign_curve_ids_from_au_table(
        f_table=f_table,
        au_table=au_table,
        pd_module=pd,
        np_module=np,
    )

    assert out["curve1"].iloc[:2].tolist() == [820005, 800005]
    assert out["curve2"].iloc[:2].tolist() == [800005, 800005]
    assert pd.isna(out["curve1"].iloc[2])
    assert pd.isna(out["curve2"].iloc[2])


def test_assign_curve_ids_from_au_table_handles_duplicate_au_rows() -> None:
    f_table = pd.DataFrame([{"au": 800005, "PROJ_AGE_1": 40}])
    au_table = pd.DataFrame(
        [
            {
                "au_id": 800005,
                "managed_curve_id": 820005,
                "unmanaged_curve_id": 800005,
            },
            {
                "au_id": 800005,
                "managed_curve_id": 820005,
                "unmanaged_curve_id": 800005,
            },
        ]
    )

    out = assign_curve_ids_from_au_table(
        f_table=f_table,
        au_table=au_table,
        pd_module=pd,
        np_module=np,
    )

    assert out["curve1"].iloc[0] == 820005
    assert out["curve2"].iloc[0] == 800005
