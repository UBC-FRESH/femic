from __future__ import annotations

import math
import os
from pathlib import Path
import re
import sys

import pandas as pd
import pytest
import femic.pipeline.tipsy as tipsy_module

from femic.pipeline.tipsy import (
    DEFAULT_BATCHTIPSY_EXE_ENV,
    DEFAULT_BTC_MSYT_COLUMNS,
    BTCRunResult,
    BTCCustomReportColumn,
    apply_btc_indicator_banks,
    assess_tipsy_input_output_coherence,
    btc_indicator_bank_columns,
    btc_report_template_preset,
    build_btc_cli_command,
    build_btc_msyt_input_table,
    build_tipsy_params_for_tsa,
    build_tipsy_input_table,
    build_btc_custom_report_template,
    btc_msyt_input_csv_path,
    build_tipsy_warning_event,
    compute_file_sha256,
    compute_vdyp_oaf1,
    compute_vdyp_site_index,
    evaluate_tipsy_candidate,
    parse_btc_custom_report_template,
    parse_btc_tsr_transposed_output,
    probe_btc_indicator_banks,
    probe_btc_report_columns,
    prepare_btc_runtime,
    resolve_btc_executable,
    run_btc_cli,
    tipsy_input_dat_path,
    tipsy_output_input_fingerprint_path,
    tipsy_params_excel_path,
    tipsy_stage_output_paths,
    validate_tipsy_output_is_fresh,
    write_btc_msyt_input_csv,
    write_btc_custom_report_template,
    write_tipsy_output_input_fingerprint,
    write_tipsy_input_exports,
)


def test_compute_vdyp_site_index_returns_mean_rounded() -> None:
    vdyp_out = {
        1: pd.DataFrame({"SI": [10.0, 12.0]}),
        2: pd.DataFrame({"SI": [14.0, 16.0]}),
    }
    assert compute_vdyp_site_index(vdyp_out) == 13.0


def test_compute_vdyp_oaf1_ignores_malformed_tables() -> None:
    vdyp_out = {
        1: pd.DataFrame({"% Stk": [85.0]}),
        2: pd.DataFrame({"bad": [1]}),
        3: pd.DataFrame({"% Stk": [95.0]}),
    }
    assert compute_vdyp_oaf1(vdyp_out) == 0.9


def test_compute_helpers_return_nan_when_no_usable_values() -> None:
    vdyp_out = {1: pd.DataFrame({"other": [1.0]})}
    assert math.isnan(compute_vdyp_site_index(vdyp_out))
    assert math.isnan(compute_vdyp_oaf1(vdyp_out))


def test_compute_helpers_unexpected_table_error_propagates() -> None:
    class _BadTable:
        def __getitem__(self, _key: str) -> object:
            raise ZeroDivisionError("unexpected")

    bad = _BadTable()
    with pytest.raises(ZeroDivisionError):
        compute_vdyp_site_index({1: bad})
    with pytest.raises(ZeroDivisionError):
        compute_vdyp_oaf1({1: bad})


def test_build_tipsy_warning_event_payload_shape() -> None:
    payload = build_tipsy_warning_event(
        tsa="08",
        stratumi=3,
        sc="SBS_7A",
        si_level="M",
        au=2003,
        reason="no_species_candidates",
    )
    assert payload["event"] == "vdyp_curve_fit"
    assert payload["status"] == "warning"
    assert payload["stage"] == "tipsy_input"
    assert payload["context"]["tsa"] == "08"
    assert payload["context"]["au"] == 2003


def test_evaluate_tipsy_candidate_returns_reason_for_no_species() -> None:
    vdyp_curve_df = pd.DataFrame({"age": [30, 40, 50], "volume": [150, 170, 180]})
    result_si = {
        "ss": pd.DataFrame({"SITE_INDEX": [18.0, 19.0], "siteprod": [17.0, 18.0]}),
        "species": {},
    }
    exclusion = {
        "min_vol": lambda _code: 140.0,
        "min_si": lambda _species: 10.0,
        "excl_leading_species": [],
        "excl_bec": [],
    }
    out = evaluate_tipsy_candidate(
        sc="SBS_7A",
        vdyp_curve_df=vdyp_curve_df,
        result_si=result_si,
        exclusion=exclusion,
        min_operable_years=10,
        si_iqrlo_quantile=0.5,
    )
    assert out.eligible is False
    assert out.reason == "no_species_candidates"


def test_evaluate_tipsy_candidate_happy_path() -> None:
    vdyp_curve_df = pd.DataFrame({"age": [30, 80, 120], "volume": [150, 200, 240]})
    result_si = {
        "ss": pd.DataFrame({"SITE_INDEX": [18.0, 19.0], "siteprod": [17.0, 18.0]}),
        "species": {"SW": {"pct": 60.0}},
    }
    exclusion = {
        "min_vol": lambda _code: 140.0,
        "min_si": lambda _species: 10.0,
        "excl_leading_species": [],
        "excl_bec": [],
    }
    out = evaluate_tipsy_candidate(
        sc="SBS_7A",
        vdyp_curve_df=vdyp_curve_df,
        result_si=result_si,
        exclusion=exclusion,
        min_operable_years=50,
        si_iqrlo_quantile=0.5,
    )
    assert out.eligible is True
    assert out.reason is None
    assert out.leading_species == "SW"


def test_evaluate_tipsy_candidate_uses_species_siteprod_fallback_when_missing() -> None:
    vdyp_curve_df = pd.DataFrame({"age": [30, 80, 120], "volume": [150, 200, 240]})
    result_si = {
        "ss": pd.DataFrame({"SITE_INDEX": [18.0, 19.0], "siteprod": [0.0, 0.0]}),
        "species": {"DR": {"pct": 60.0}},
    }
    exclusion = {
        "min_vol": lambda _code: 140.0,
        "min_si": lambda _species: 10.0,
        "excl_leading_species": [],
        "excl_bec": [],
    }
    out = evaluate_tipsy_candidate(
        sc="SBS_7A",
        vdyp_curve_df=vdyp_curve_df,
        result_si=result_si,
        exclusion=exclusion,
        min_operable_years=50,
        si_iqrlo_quantile=0.5,
        siteprod_si_fallback_by_species={"DR": 14.5},
    )
    assert out.eligible is True
    assert out.si_spr_med == pytest.approx(14.5)
    assert out.si_spr_iqrlo == pytest.approx(14.5)


def test_build_tipsy_input_table_selects_table_key_and_columns() -> None:
    tipsy_params_for_tsa = {
        1001: {
            "e": {"TBLno": 11, "AU": 1001, "SI": 16.0},
            "f": {"TBLno": 21, "AU": 1001, "SI": 18.0},
        },
        1002: {
            "e": {"TBLno": 12, "AU": 1002, "SI": 17.0},
            "f": {"TBLno": 22, "AU": 1002, "SI": 19.0},
        },
    }
    out = build_tipsy_input_table(
        tipsy_params_for_tsa=tipsy_params_for_tsa,
        tipsy_params_columns=["AU", "SI"],
        pd_module=pd,
        table_key="f",
    )
    assert list(out["AU"]) == [1001, 1002]
    assert list(out["SI"]) == [18.0, 19.0]


def test_build_tipsy_input_table_raises_when_no_rows() -> None:
    tipsy_params_for_tsa = {1001: {"e": {"TBLno": 11, "AU": 1001, "SI": 16.0}}}
    with pytest.raises(RuntimeError, match="No TIPSY parameter tables generated"):
        build_tipsy_input_table(
            tipsy_params_for_tsa=tipsy_params_for_tsa,
            tipsy_params_columns=["AU", "SI"],
            pd_module=pd,
            table_key="f",
        )


def test_build_btc_msyt_input_table_maps_current_tipsy_payload() -> None:
    tipsy_table = pd.DataFrame(
        {
            "AU": [985502001],
            "BEC": ["CWHvm1"],
            "Proportion": [1.0],
            "Regen_Delay": [2],
            "Density": [4000],
            "SPP_1": ["HW"],
            "PCT_1": [77.5],
            "SPP_2": ["FD"],
            "PCT_2": [22.5],
            "GW_1": [4.0],
            "GW_2": [""],
            "OAF1": [0.85],
            "OAF2": [0.95],
            "SI": [20.6],
        }
    )

    out = build_btc_msyt_input_table(tipsy_table=tipsy_table, pd_module=pd)

    assert list(out.columns) == list(DEFAULT_BTC_MSYT_COLUMNS)
    row = out.iloc[0].to_dict()
    assert row["feature_id"] == 985502001
    assert row["bec_zone"] == "CWH"
    assert row["bec_subzone"] == "vm"
    assert row["planted_species1"] == "Hw"
    assert row["planted_species2"] == "Fd"
    assert row["planted_density1"] == 3100
    assert row["planted_density2"] == 900
    assert row["genetic_worth1"] == 4.0
    assert row["planting_delay"] == 2
    assert row["planted_percent"] == 100
    assert row["opening_id"] == 985502001
    assert row["hw_si"] == 20.6
    assert row["fd_si"] == 20.6
    assert row["cw_si"] == 0


def test_write_btc_msyt_input_csv_writes_canonical_path(tmp_path: Path) -> None:
    row = {column: "" for column in DEFAULT_BTC_MSYT_COLUMNS}
    row["feature_id"] = 1
    table = pd.DataFrame([row])
    output_path = write_btc_msyt_input_csv(
        btc_msyt_table=table,
        tsa="08",
        output_root=tmp_path,
    )
    assert output_path == tmp_path / "03_input-tsa08.csv"
    assert output_path.is_file()
    assert btc_msyt_input_csv_path(tsa="08", input_root=tmp_path) == output_path
    assert "feature_id" in output_path.read_text(encoding="utf-8")


def test_write_tipsy_input_exports_writes_excel_and_dat(tmp_path: Path) -> None:
    table = pd.DataFrame({"AU": [1001], "SI": [18.0]})
    prefix = str(tmp_path / "tipsy_params_tsa")
    dat_template = str(tmp_path / "02_input-tsa{tsa}.dat")
    excel_path, dat_path = write_tipsy_input_exports(
        tipsy_table=table,
        tsa="08",
        tipsy_params_path_prefix=prefix,
        dat_path_template=dat_template,
    )
    assert excel_path == str(tmp_path / "tipsy_params_tsa08.xlsx")
    assert dat_path == str(tmp_path / "02_input-tsa08.dat")
    assert Path(excel_path).is_file()
    assert Path(dat_path).is_file()
    assert "AU" in Path(dat_path).read_text()


def test_parse_btc_tsr_transposed_output_maps_feature_rows_to_managed_curve_ids(
    tmp_path: Path,
) -> None:
    output_csv = tmp_path / "MSYT_output.csv"
    pd.DataFrame(
        [
            {
                "feature_id": 1000,
                "MVcon_0": 0.0,
                "MVdec_0": 0.0,
                "HTcon_0": 0.0,
                "HTdec_0": 0.0,
                "gVol_0": 0.0,
                "CC_0": 0.0,
                "MVcon_10": 50.0,
                "MVdec_10": 10.0,
                "HTcon_10": 3.0,
                "HTdec_10": 2.0,
                "gVol_10": 70.0,
                "CC_10": 0.4,
            }
        ]
    ).to_csv(output_csv, index=False)

    out = parse_btc_tsr_transposed_output(output_csv=output_csv, pd_module=pd)

    assert list(out["AU"]) == [21000, 21000]
    assert list(out["Age"]) == [0, 10]
    assert list(out["Yield"]) == [0.0, 60.0]
    assert list(out["Height"]) == [0.0, 3.0]
    assert list(out["GrossYield"]) == [0.0, 70.0]
    assert list(out["CrownCover"]) == [0.0, 0.4]
    assert out["DBHq"].isna().all()
    assert out["TPH"].isna().all()


def test_parse_btc_tsr_transposed_output_preserves_existing_managed_curve_ids(
    tmp_path: Path,
) -> None:
    output_csv = tmp_path / "MSYT_output.csv"
    pd.DataFrame(
        [
            {
                "feature_id": 21000,
                "MVcon_0": 1.0,
                "MVdec_0": 2.0,
                "HTcon_0": 4.0,
                "HTdec_0": 3.0,
                "gVol_0": 5.0,
                "CC_0": 0.6,
            }
        ]
    ).to_csv(output_csv, index=False)

    out = parse_btc_tsr_transposed_output(output_csv=output_csv, pd_module=pd)

    assert list(out["AU"]) == [21000]
    assert list(out["Age"]) == [0]
    assert list(out["Yield"]) == [3.0]
    assert list(out["Height"]) == [4.0]
    assert list(out["GrossYield"]) == [5.0]
    assert list(out["CrownCover"]) == [0.6]
    assert out["DBHq"].isna().all()
    assert out["TPH"].isna().all()


def test_parse_btc_tsr_transposed_output_preserves_log_grade_columns(
    tmp_path: Path,
) -> None:
    output_csv = tmp_path / "MSYT_output.csv"
    pd.DataFrame(
        [
            {
                "feature_id": 1001,
                "MVcon_0": 1.0,
                "MVdec_0": 2.0,
                "HTcon_0": 4.0,
                "HTdec_0": 3.0,
                "gVol_0": 5.0,
                "CC_0": 0.6,
                "Logs_Grade_D_0": 7.0,
                "Logs_Grade_All_0": 9.0,
            }
        ]
    ).to_csv(output_csv, index=False)

    out = parse_btc_tsr_transposed_output(output_csv=output_csv, pd_module=pd)

    assert list(out["AU"]) == [21001]
    assert list(out["Age"]) == [0]
    assert list(out["Yield"]) == [3.0]
    assert list(out["Logs_Grade_D"]) == [7.0]
    assert list(out["Logs_Grade_All"]) == [9.0]


def test_parse_btc_custom_report_template_reads_sql_style_template(
    tmp_path: Path,
) -> None:
    rpt = tmp_path / "TimberSupply SQL.rpt"
    rpt.write_text(
        "[CustomReport]\n"
        "Name=Timber Supply SQL\n"
        "IconID=13\n"
        "Identifier=FirstIDcolumn\n"
        "IdentifierInteger=1\n"
        "Type=databaseByStand\n"
        "OutputFormat=TAB\n"
        "Border=500\n"
        "HeaderHeight=250\n"
        "FooterHeight=250\n"
        "\n"
        "[CustomReportHeader]\n"
        "ModelVersion=1\n"
        "Species_GenWorth=1\n"
        "\n"
        "[CustomReportColumns]\n"
        "'enum_db_column\tWidth\tHeader1Override\tHeader2Override\tUnitsOverride\n"
        "Year\t0\tYear\t\t\n"
        "Volume:Auto:Con\t0\tVolumeCon\t\t\n",
        encoding="utf-8",
    )
    template = parse_btc_custom_report_template(rpt)
    assert template.name == "Timber Supply SQL"
    assert template.report_type == "databaseByStand"
    assert template.identifier_integer is True
    assert [col.token for col in template.columns] == ["Year", "Volume:Auto:Con"]
    assert template.columns[1].header1_override == "VolumeCon"


def test_btc_report_template_preset_tsr_unattended_default_has_mashup_columns() -> None:
    template = btc_report_template_preset("tsr-unattended-default")
    assert template.report_type == "transposed"
    assert template.output_format == "CSV"
    assert [col.token for col in template.columns] == [
        "Volume:Auto:Con",
        "Volume:Auto:Dec",
        "Height:Con",
        "Height:Dec",
        "VolumeGross",
        "CC",
    ]


def test_btc_indicator_bank_columns_returns_first_safe_bank() -> None:
    columns = btc_indicator_bank_columns("stand-structure-basic")
    assert [column.token for column in columns] == [
        "MAI",
        "BasalArea:000",
        "DBHg:000",
        "SPH:000",
        "StemCount000",
        "StemCount125",
        "StemCount175",
    ]
    assert [column.header1_override for column in columns] == [
        "MAI",
        "BasalArea000",
        "DBHg000",
        "SPH000",
        "StemCount000",
        "StemCount125",
        "StemCount175",
    ]


def test_btc_indicator_bank_columns_returns_threshold_raw_triplet_bank() -> None:
    columns = btc_indicator_bank_columns("stand-structure-threshold-raw")
    assert [column.token for column in columns] == [
        "Volume000",
        "Volume125",
        "Volume175",
        "BasalArea000",
        "BasalArea125",
        "BasalArea175",
        "MeanDBHg000",
        "MeanDBHg125",
        "MeanDBHg175",
        "MAI000",
        "MAI125",
        "MAI175",
        "VPT000",
        "VPT125",
        "VPT175",
        "Juvenille_Volume000",
        "Juvenille_Volume125",
        "Juvenille_Volume175",
        "Juvenille_Percent000",
        "Juvenille_Percent125",
        "Juvenille_Percent175",
    ]
    assert [column.header1_override for column in columns] == [
        "Volume000",
        "Volume125",
        "Volume175",
        "BasalArea000",
        "BasalArea125",
        "BasalArea175",
        "MeanDBHg000",
        "MeanDBHg125",
        "MeanDBHg175",
        "MAI000",
        "MAI125",
        "MAI175",
        "VPT000",
        "VPT125",
        "VPT175",
        "Juvenille_Volume000",
        "Juvenille_Volume125",
        "Juvenille_Volume175",
        "Juvenille_Percent000",
        "Juvenille_Percent125",
        "Juvenille_Percent175",
    ]


def test_btc_indicator_bank_columns_returns_genetics_fertilization_oaf_bank() -> None:
    columns = btc_indicator_bank_columns("genetics-fertilization-and-oaf")
    assert [column.token for column in columns] == [
        "GWgain",
        "FertGain",
        "OAFremoval",
        "OAFmortality",
        "OAFimpact",
        "OAF",
    ]


def test_btc_indicator_bank_columns_returns_tass_site_index_raw_bank() -> None:
    columns = btc_indicator_bank_columns("tass-and-site-index-raw")
    assert [column.token for column in columns] == [
        "YearTASS_Base",
        "HeightSindex_Base",
        "YearTASS_Full",
        "HeightSindex_Full",
    ]


def test_btc_indicator_bank_columns_returns_log_grades_bank() -> None:
    columns = btc_indicator_bank_columns("log-grades")
    assert [column.token for column in columns] == [
        "Logs_Grade_D",
        "Logs_Grade_F",
        "Logs_Grade_H",
        "Logs_Grade_I",
        "Logs_Grade_J",
        "Logs_Grade_U",
        "Logs_Grade_X",
        "Logs_Grade_Y",
        "Logs_Grade_All",
    ]
    assert [column.header1_override for column in columns] == [
        "Logs_Grade_D",
        "Logs_Grade_F",
        "Logs_Grade_H",
        "Logs_Grade_I",
        "Logs_Grade_J",
        "Logs_Grade_U",
        "Logs_Grade_X",
        "Logs_Grade_Y",
        "Logs_Grade_All",
    ]


def test_btc_indicator_bank_columns_returns_lumber_2_or_better_bank() -> None:
    columns = btc_indicator_bank_columns("lumber-2-or-better")
    assert [column.token for column in columns] == [
        "Lumber_2_or_Better_2x4",
        "Lumber_2_or_Better_2x6",
        "Lumber_2_or_Better_2x8",
        "Lumber_2_or_Better_2x10",
        "Lumber_2_or_Better_All",
        "LRF_2_or_Better_All",
    ]


def test_btc_indicator_bank_columns_returns_residual_fibre_bank() -> None:
    columns = btc_indicator_bank_columns("residual-fibre")
    assert [column.token for column in columns] == [
        "Residual_Chips",
        "Residual_Sawdust",
        "Residual_Shavings",
        "Residual_Trim",
        "Residual_Bark",
    ]


def test_btc_indicator_bank_columns_returns_lumber_graded_bank() -> None:
    columns = btc_indicator_bank_columns("lumber-graded")
    assert [column.token for column in columns] == [
        "Lumber_Graded_SS_2x4",
        "Lumber_Graded_SS_2x6",
        "Lumber_Graded_SS_2x8",
        "Lumber_Graded_SS_2x10",
        "Lumber_Graded_1_2x4",
        "Lumber_Graded_1_2x6",
        "Lumber_Graded_1_2x8",
        "Lumber_Graded_1_2x10",
        "Lumber_Graded_2_2x4",
        "Lumber_Graded_2_2x6",
        "Lumber_Graded_2_2x8",
        "Lumber_Graded_2_2x10",
        "Lumber_Graded_3_2x4",
        "Lumber_Graded_3_2x6",
        "Lumber_Graded_3_2x8",
        "Lumber_Graded_3_2x10",
        "Lumber_Graded_4_2x4",
        "Lumber_Graded_4_2x6",
        "Lumber_Graded_4_2x8",
        "Lumber_Graded_4_2x10",
        "Lumber_Graded_All",
        "LRF_Graded_All",
    ]


def test_btc_indicator_bank_columns_returns_lumber_degraded_bank() -> None:
    columns = btc_indicator_bank_columns("lumber-degraded")
    assert [column.token for column in columns] == [
        "Lumber_Degraded_SS_2x4",
        "Lumber_Degraded_SS_2x6",
        "Lumber_Degraded_SS_2x8",
        "Lumber_Degraded_SS_2x10",
        "Lumber_Degraded_1_2x4",
        "Lumber_Degraded_1_2x6",
        "Lumber_Degraded_1_2x8",
        "Lumber_Degraded_1_2x10",
        "Lumber_Degraded_2_2x4",
        "Lumber_Degraded_2_2x6",
        "Lumber_Degraded_2_2x8",
        "Lumber_Degraded_2_2x10",
        "Lumber_Degraded_3_2x4",
        "Lumber_Degraded_3_2x6",
        "Lumber_Degraded_3_2x8",
        "Lumber_Degraded_3_2x10",
        "Lumber_Degraded_4_2x4",
        "Lumber_Degraded_4_2x6",
        "Lumber_Degraded_4_2x8",
        "Lumber_Degraded_4_2x10",
        "Lumber_Degraded_All",
        "LRF_Degraded_All",
    ]


def test_btc_indicator_bank_columns_returns_industrial_logs_bank() -> None:
    columns = btc_indicator_bank_columns("industrial-logs")
    assert [column.token for column in columns] == [
        "Industrial_Logs_D38L13",
        "Industrial_Logs_D38L11",
        "Industrial_Logs_D38L8",
        "Industrial_Logs_D30L13",
        "Industrial_Logs_D30L11",
        "Industrial_Logs_D30L8",
        "Industrial_Logs_D20L13",
        "Industrial_Logs_D20L11",
        "Industrial_Logs_D20L8",
        "Industrial_Logs_D125L13",
        "Industrial_Logs_D125L11",
        "Industrial_Logs_D125L8",
        "Industrial_Logs_D125L63",
        "Industrial_Logs_D125L51",
        "Industrial_Logs_D125L5",
        "Industrial_Logs_D305",
        "Industrial_Logs_D254",
        "Industrial_Logs_D203",
        "Industrial_Logs_D178",
        "Industrial_Logs_D152",
    ]


def test_btc_indicator_bank_columns_returns_mortality_summary_bank() -> None:
    columns = btc_indicator_bank_columns("mortality-summary")
    assert [column.token for column in columns] == [
        "Mortality_Stems",
        "Mortality_DBHg_Mean",
        "Mortality_Height_Mean",
        "Mortality_Basal_Area",
        "Mortality_Volume_Total",
    ]


def test_btc_indicator_bank_columns_returns_crop250_stand_quality_bank() -> None:
    columns = btc_indicator_bank_columns("crop250-stand-quality")
    assert [column.token for column in columns] == [
        "Crop250VolUtil125",
        "Crop250DBHgMean",
        "Crop250LiveCrown",
    ]


def test_btc_indicator_bank_columns_returns_crown_and_fire_bank() -> None:
    columns = btc_indicator_bank_columns("crown-and-fire")
    assert [column.token for column in columns] == [
        "CrownCover",
        "mean_height_to_crown_base",
        "mean_crown_length",
        "Crown_Bulk_Density",
    ]


def test_btc_indicator_bank_columns_returns_biomass_live_bank() -> None:
    columns = btc_indicator_bank_columns("biomass-live")
    assert [column.token for column in columns] == [
        "Biomass_Live_Wood",
        "Biomass_Live_Bark",
        "Biomass_Live_Foliar",
        "Biomass_Live_Branch",
        "Biomass_Live_Roots",
        "Biomass_Live_Total",
        "Biomass_Live_Above",
    ]


def test_btc_indicator_bank_columns_returns_biomass_dead_bank() -> None:
    columns = btc_indicator_bank_columns("biomass-dead")
    assert [column.token for column in columns] == [
        "Biomass_Dead_Wood",
        "Biomass_Dead_Bark",
        "Biomass_Dead_Foliar",
        "Biomass_Dead_Branch",
        "Biomass_Dead_Roots",
        "Biomass_Dead_Total",
        "Biomass_Dead_Above",
    ]


def test_btc_indicator_bank_columns_returns_carbon_bank() -> None:
    columns = btc_indicator_bank_columns("carbon")
    assert [column.token for column in columns] == [
        "Carbon_Live_Wood",
        "Carbon_Live_Bark",
        "Carbon_Live_Foliar",
        "Carbon_Live_Branch",
        "Carbon_Live_Roots",
        "Carbon_Live_Total",
        "Carbon_Live_Above",
        "Carbon_Dead_Wood",
        "Carbon_Dead_Bark",
        "Carbon_Dead_Foliar",
        "Carbon_Dead_Branch",
        "Carbon_Dead_Roots",
        "Carbon_Dead_Total",
        "Carbon_Dead_Above",
    ]


def test_btc_indicator_bank_columns_returns_co2e_bank() -> None:
    columns = btc_indicator_bank_columns("co2e")
    assert [column.token for column in columns] == [
        "CO2e_Live_Wood",
        "CO2e_Live_Bark",
        "CO2e_Live_Foliar",
        "CO2e_Live_Branch",
        "CO2e_Live_Roots",
        "CO2e_Live_Total",
        "CO2e_Live_Above",
        "CO2e_Dead_Wood",
        "CO2e_Dead_Bark",
        "CO2e_Dead_Foliar",
        "CO2e_Dead_Branch",
        "CO2e_Dead_Roots",
        "CO2e_Dead_Total",
        "CO2e_Dead_Above",
    ]


def test_btc_indicator_bank_columns_returns_mortality_size_classes_bank() -> None:
    columns = btc_indicator_bank_columns("mortality-size-classes")
    assert [column.token for column in columns] == [
        *(
            f"Mortality_Stems_Size_Class_{suffix}"
            for suffix in (5, 15, 25, 35, 45, 55, 65)
        ),
        *(
            f"Mortality_Volume_Size_Class_{suffix}"
            for suffix in (5, 15, 25, 35, 45, 55, 65)
        ),
        *(
            f"Mortality_VPT_Size_Class_{suffix}"
            for suffix in (5, 15, 25, 35, 45, 55, 65)
        ),
    ]


def test_btc_indicator_bank_columns_returns_diameter_class_stems_bank() -> None:
    columns = btc_indicator_bank_columns("diameter-class-stems")
    assert [column.token for column in columns] == [
        *(f"Stems_Diameter_Class_{suffix}" for suffix in range(0, 95, 5))
    ]


def test_btc_indicator_bank_columns_returns_diameter_class_volume_bank() -> None:
    columns = btc_indicator_bank_columns("diameter-class-volume")
    assert [column.token for column in columns] == [
        *(f"Volume_Diameter_Class_{suffix}" for suffix in range(0, 95, 5))
    ]


def test_btc_indicator_bank_columns_returns_diameter_class_vpt_bank() -> None:
    columns = btc_indicator_bank_columns("diameter-class-vpt")
    assert [column.token for column in columns] == [
        *(f"VPT_Diameter_Class_{suffix}" for suffix in range(0, 95, 5))
    ]


def test_apply_btc_indicator_banks_appends_without_duplicates() -> None:
    template = btc_report_template_preset("tsr-unattended-default")
    extended = apply_btc_indicator_banks(
        template=template,
        indicator_bank_names=["stand-structure-basic", "stand-structure-basic"],
    )
    assert [column.token for column in extended.columns] == [
        "Volume:Auto:Con",
        "Volume:Auto:Dec",
        "Height:Con",
        "Height:Dec",
        "VolumeGross",
        "CC",
        "MAI",
        "BasalArea:000",
        "DBHg:000",
        "SPH:000",
        "StemCount000",
        "StemCount125",
        "StemCount175",
    ]


def test_apply_btc_indicator_banks_supports_log_grades_bank() -> None:
    template = btc_report_template_preset("tsr-unattended-default")
    extended = apply_btc_indicator_banks(
        template=template,
        indicator_bank_names=["log-grades"],
    )
    assert [column.token for column in extended.columns] == [
        "Volume:Auto:Con",
        "Volume:Auto:Dec",
        "Height:Con",
        "Height:Dec",
        "VolumeGross",
        "CC",
        "Logs_Grade_D",
        "Logs_Grade_F",
        "Logs_Grade_H",
        "Logs_Grade_I",
        "Logs_Grade_J",
        "Logs_Grade_U",
        "Logs_Grade_X",
        "Logs_Grade_Y",
        "Logs_Grade_All",
    ]


def test_apply_btc_indicator_banks_supports_lumber_2_or_better_bank() -> None:
    template = btc_report_template_preset("tsr-unattended-default")
    extended = apply_btc_indicator_banks(
        template=template,
        indicator_bank_names=["lumber-2-or-better"],
    )
    assert [column.token for column in extended.columns] == [
        "Volume:Auto:Con",
        "Volume:Auto:Dec",
        "Height:Con",
        "Height:Dec",
        "VolumeGross",
        "CC",
        "Lumber_2_or_Better_2x4",
        "Lumber_2_or_Better_2x6",
        "Lumber_2_or_Better_2x8",
        "Lumber_2_or_Better_2x10",
        "Lumber_2_or_Better_All",
        "LRF_2_or_Better_All",
    ]


def test_apply_btc_indicator_banks_supports_residual_fibre_bank() -> None:
    template = btc_report_template_preset("tsr-unattended-default")
    extended = apply_btc_indicator_banks(
        template=template,
        indicator_bank_names=["residual-fibre"],
    )
    assert [column.token for column in extended.columns] == [
        "Volume:Auto:Con",
        "Volume:Auto:Dec",
        "Height:Con",
        "Height:Dec",
        "VolumeGross",
        "CC",
        "Residual_Chips",
        "Residual_Sawdust",
        "Residual_Shavings",
        "Residual_Trim",
        "Residual_Bark",
    ]


def test_apply_btc_indicator_banks_supports_lumber_graded_bank() -> None:
    template = btc_report_template_preset("tsr-unattended-default")
    extended = apply_btc_indicator_banks(
        template=template,
        indicator_bank_names=["lumber-graded"],
    )
    assert [column.token for column in extended.columns] == [
        "Volume:Auto:Con",
        "Volume:Auto:Dec",
        "Height:Con",
        "Height:Dec",
        "VolumeGross",
        "CC",
        "Lumber_Graded_SS_2x4",
        "Lumber_Graded_SS_2x6",
        "Lumber_Graded_SS_2x8",
        "Lumber_Graded_SS_2x10",
        "Lumber_Graded_1_2x4",
        "Lumber_Graded_1_2x6",
        "Lumber_Graded_1_2x8",
        "Lumber_Graded_1_2x10",
        "Lumber_Graded_2_2x4",
        "Lumber_Graded_2_2x6",
        "Lumber_Graded_2_2x8",
        "Lumber_Graded_2_2x10",
        "Lumber_Graded_3_2x4",
        "Lumber_Graded_3_2x6",
        "Lumber_Graded_3_2x8",
        "Lumber_Graded_3_2x10",
        "Lumber_Graded_4_2x4",
        "Lumber_Graded_4_2x6",
        "Lumber_Graded_4_2x8",
        "Lumber_Graded_4_2x10",
        "Lumber_Graded_All",
        "LRF_Graded_All",
    ]


def test_apply_btc_indicator_banks_supports_lumber_degraded_bank() -> None:
    template = btc_report_template_preset("tsr-unattended-default")
    extended = apply_btc_indicator_banks(
        template=template,
        indicator_bank_names=["lumber-degraded"],
    )
    assert [column.token for column in extended.columns] == [
        "Volume:Auto:Con",
        "Volume:Auto:Dec",
        "Height:Con",
        "Height:Dec",
        "VolumeGross",
        "CC",
        "Lumber_Degraded_SS_2x4",
        "Lumber_Degraded_SS_2x6",
        "Lumber_Degraded_SS_2x8",
        "Lumber_Degraded_SS_2x10",
        "Lumber_Degraded_1_2x4",
        "Lumber_Degraded_1_2x6",
        "Lumber_Degraded_1_2x8",
        "Lumber_Degraded_1_2x10",
        "Lumber_Degraded_2_2x4",
        "Lumber_Degraded_2_2x6",
        "Lumber_Degraded_2_2x8",
        "Lumber_Degraded_2_2x10",
        "Lumber_Degraded_3_2x4",
        "Lumber_Degraded_3_2x6",
        "Lumber_Degraded_3_2x8",
        "Lumber_Degraded_3_2x10",
        "Lumber_Degraded_4_2x4",
        "Lumber_Degraded_4_2x6",
        "Lumber_Degraded_4_2x8",
        "Lumber_Degraded_4_2x10",
        "Lumber_Degraded_All",
        "LRF_Degraded_All",
    ]


def test_apply_btc_indicator_banks_supports_industrial_logs_bank() -> None:
    template = btc_report_template_preset("tsr-unattended-default")
    extended = apply_btc_indicator_banks(
        template=template,
        indicator_bank_names=["industrial-logs"],
    )
    assert [column.token for column in extended.columns] == [
        "Volume:Auto:Con",
        "Volume:Auto:Dec",
        "Height:Con",
        "Height:Dec",
        "VolumeGross",
        "CC",
        "Industrial_Logs_D38L13",
        "Industrial_Logs_D38L11",
        "Industrial_Logs_D38L8",
        "Industrial_Logs_D30L13",
        "Industrial_Logs_D30L11",
        "Industrial_Logs_D30L8",
        "Industrial_Logs_D20L13",
        "Industrial_Logs_D20L11",
        "Industrial_Logs_D20L8",
        "Industrial_Logs_D125L13",
        "Industrial_Logs_D125L11",
        "Industrial_Logs_D125L8",
        "Industrial_Logs_D125L63",
        "Industrial_Logs_D125L51",
        "Industrial_Logs_D125L5",
        "Industrial_Logs_D305",
        "Industrial_Logs_D254",
        "Industrial_Logs_D203",
        "Industrial_Logs_D178",
        "Industrial_Logs_D152",
    ]


def test_apply_btc_indicator_banks_supports_mortality_summary_bank() -> None:
    template = btc_report_template_preset("tsr-unattended-default")
    extended = apply_btc_indicator_banks(
        template=template,
        indicator_bank_names=["mortality-summary"],
    )
    assert [column.token for column in extended.columns] == [
        "Volume:Auto:Con",
        "Volume:Auto:Dec",
        "Height:Con",
        "Height:Dec",
        "VolumeGross",
        "CC",
        "Mortality_Stems",
        "Mortality_DBHg_Mean",
        "Mortality_Height_Mean",
        "Mortality_Basal_Area",
        "Mortality_Volume_Total",
    ]


def test_apply_btc_indicator_banks_supports_crop250_stand_quality_bank() -> None:
    template = btc_report_template_preset("tsr-unattended-default")
    extended = apply_btc_indicator_banks(
        template=template,
        indicator_bank_names=["crop250-stand-quality"],
    )
    assert [column.token for column in extended.columns] == [
        "Volume:Auto:Con",
        "Volume:Auto:Dec",
        "Height:Con",
        "Height:Dec",
        "VolumeGross",
        "CC",
        "Crop250VolUtil125",
        "Crop250DBHgMean",
        "Crop250LiveCrown",
    ]


def test_apply_btc_indicator_banks_supports_crown_and_fire_bank() -> None:
    template = btc_report_template_preset("tsr-unattended-default")
    extended = apply_btc_indicator_banks(
        template=template,
        indicator_bank_names=["crown-and-fire"],
    )
    assert [column.token for column in extended.columns] == [
        "Volume:Auto:Con",
        "Volume:Auto:Dec",
        "Height:Con",
        "Height:Dec",
        "VolumeGross",
        "CC",
        "CrownCover",
        "mean_height_to_crown_base",
        "mean_crown_length",
        "Crown_Bulk_Density",
    ]


def test_apply_btc_indicator_banks_supports_biomass_live_bank() -> None:
    template = btc_report_template_preset("tsr-unattended-default")
    extended = apply_btc_indicator_banks(
        template=template,
        indicator_bank_names=["biomass-live"],
    )
    assert [column.token for column in extended.columns] == [
        "Volume:Auto:Con",
        "Volume:Auto:Dec",
        "Height:Con",
        "Height:Dec",
        "VolumeGross",
        "CC",
        "Biomass_Live_Wood",
        "Biomass_Live_Bark",
        "Biomass_Live_Foliar",
        "Biomass_Live_Branch",
        "Biomass_Live_Roots",
        "Biomass_Live_Total",
        "Biomass_Live_Above",
    ]


def test_apply_btc_indicator_banks_supports_biomass_dead_bank() -> None:
    template = btc_report_template_preset("tsr-unattended-default")
    extended = apply_btc_indicator_banks(
        template=template,
        indicator_bank_names=["biomass-dead"],
    )
    assert [column.token for column in extended.columns] == [
        "Volume:Auto:Con",
        "Volume:Auto:Dec",
        "Height:Con",
        "Height:Dec",
        "VolumeGross",
        "CC",
        "Biomass_Dead_Wood",
        "Biomass_Dead_Bark",
        "Biomass_Dead_Foliar",
        "Biomass_Dead_Branch",
        "Biomass_Dead_Roots",
        "Biomass_Dead_Total",
        "Biomass_Dead_Above",
    ]


def test_apply_btc_indicator_banks_supports_carbon_bank() -> None:
    template = btc_report_template_preset("tsr-unattended-default")
    extended = apply_btc_indicator_banks(
        template=template,
        indicator_bank_names=["carbon"],
    )
    assert [column.token for column in extended.columns] == [
        "Volume:Auto:Con",
        "Volume:Auto:Dec",
        "Height:Con",
        "Height:Dec",
        "VolumeGross",
        "CC",
        "Carbon_Live_Wood",
        "Carbon_Live_Bark",
        "Carbon_Live_Foliar",
        "Carbon_Live_Branch",
        "Carbon_Live_Roots",
        "Carbon_Live_Total",
        "Carbon_Live_Above",
        "Carbon_Dead_Wood",
        "Carbon_Dead_Bark",
        "Carbon_Dead_Foliar",
        "Carbon_Dead_Branch",
        "Carbon_Dead_Roots",
        "Carbon_Dead_Total",
        "Carbon_Dead_Above",
    ]


def test_apply_btc_indicator_banks_supports_co2e_bank() -> None:
    template = btc_report_template_preset("tsr-unattended-default")
    extended = apply_btc_indicator_banks(
        template=template,
        indicator_bank_names=["co2e"],
    )
    assert [column.token for column in extended.columns] == [
        "Volume:Auto:Con",
        "Volume:Auto:Dec",
        "Height:Con",
        "Height:Dec",
        "VolumeGross",
        "CC",
        "CO2e_Live_Wood",
        "CO2e_Live_Bark",
        "CO2e_Live_Foliar",
        "CO2e_Live_Branch",
        "CO2e_Live_Roots",
        "CO2e_Live_Total",
        "CO2e_Live_Above",
        "CO2e_Dead_Wood",
        "CO2e_Dead_Bark",
        "CO2e_Dead_Foliar",
        "CO2e_Dead_Branch",
        "CO2e_Dead_Roots",
        "CO2e_Dead_Total",
        "CO2e_Dead_Above",
    ]


def test_build_and_write_btc_custom_report_template_round_trip(tmp_path: Path) -> None:
    source = btc_report_template_preset("timber-supply-sql")
    template = build_btc_custom_report_template(
        name="Extended SQL",
        source_template=source,
        columns=[
            *source.columns,
            BTCCustomReportColumn(
                token="VolumeGross", width=0, header1_override="gVol"
            ),
        ],
    )
    out = tmp_path / "extended.rpt"
    write_btc_custom_report_template(output_path=out, template=template)
    reparsed = parse_btc_custom_report_template(out)
    assert reparsed.name == "Extended SQL"
    assert reparsed.columns[-1].token == "VolumeGross"
    assert reparsed.columns[-1].header1_override == "gVol"


def test_resolve_btc_executable_prefers_explicit_path(tmp_path: Path) -> None:
    explicit = tmp_path / "TIPSYbtc.exe"
    explicit.write_text("stub", encoding="utf-8")
    env_path = tmp_path / "other.exe"
    env_path.write_text("stub", encoding="utf-8")
    discovered = resolve_btc_executable(
        executable_path=explicit,
        env={DEFAULT_BATCHTIPSY_EXE_ENV: str(env_path)},
    )
    assert discovered.executable_path == explicit.resolve()
    assert discovered.source == "explicit"


def test_build_btc_cli_command_renders_expected_sequence(tmp_path: Path) -> None:
    command = build_btc_cli_command(
        executable_path=tmp_path / "TIPSYbtc.exe",
        mode="TSR",
        input_csv="MSYT.csv",
        output_csv="MSYT_output.csv",
        error_csv="MSYT_error.csv",
        extra_executable_args=("probe.py",),
    )
    assert command == [
        str(tmp_path / "TIPSYbtc.exe"),
        "probe.py",
        "/TSR",
        "MSYT.csv",
        "MSYT_output.csv",
        "MSYT_error.csv",
    ]


def test_run_btc_cli_supervised_writes_outputs_and_manifest(tmp_path: Path) -> None:
    input_csv = tmp_path / "MSYT.csv"
    input_csv.write_text("feature_id\n1\n", encoding="utf-8")
    helper = tmp_path / "fake_btc.py"
    helper.write_text(
        "from pathlib import Path\n"
        "import sys\n"
        "mode, input_name, output_name, error_name = sys.argv[1:5]\n"
        "Path(output_name).write_text('feature_id,MVcon_0,gVol_0,CC_0\\n1,2,3,4\\n', encoding='utf-8')\n"
        "Path(error_name).write_text('warnings,errors\\n0,0\\n', encoding='utf-8')\n"
        "sys.exit(0)\n",
        encoding="utf-8",
    )
    result: BTCRunResult = run_btc_cli(
        input_csv=input_csv,
        mode="TSR",
        executable_path=sys.executable,
        scratch_root=tmp_path / "scratch",
        log_dir=tmp_path / "logs",
        run_id="btc_test",
        env={},
        extra_executable_args=(helper,),
    )
    assert result.exit_code == 0
    assert result.copied_install is False
    assert result.output_csv_path.is_file()
    assert result.error_csv_path.is_file()
    assert result.output_csv_path.parent == tmp_path / "scratch" / "work"
    assert result.error_csv_path.parent == tmp_path / "scratch" / "work"
    assert result.manifest_path.is_file()
    assert "feature_id,MVcon_0,gVol_0,CC_0" in result.output_csv_path.read_text(
        encoding="utf-8"
    )


def test_run_btc_cli_defaults_to_tipsy_runtime_roots(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    input_csv = tmp_path / "MSYT.csv"
    input_csv.write_text("feature_id\n1\n", encoding="utf-8")
    helper = tmp_path / "fake_btc.py"
    helper.write_text(
        "from pathlib import Path\n"
        "import sys\n"
        "mode, input_name, output_name, error_name = sys.argv[1:5]\n"
        "Path(output_name).write_text('feature_id,MVcon_0,gVol_0,CC_0\\n1,2,3,4\\n', encoding='utf-8')\n"
        "Path(error_name).write_text('warnings,errors\\n0,0\\n', encoding='utf-8')\n"
        "sys.exit(0)\n",
        encoding="utf-8",
    )

    result = run_btc_cli(
        input_csv=input_csv,
        mode="TSR",
        executable_path=sys.executable,
        run_id="btc_default_paths",
        env={},
        extra_executable_args=(helper,),
    )

    assert result.exit_code == 0
    assert result.manifest_path == (
        tmp_path / "tipsy_io" / "logs" / "btc_manifest-btc_default_paths.json"
    )
    assert result.stdout_log_path == (
        tmp_path / "tipsy_io" / "logs" / "btc_stdout-btc_default_paths.log"
    )
    assert result.stderr_log_path == (
        tmp_path / "tipsy_io" / "logs" / "btc_stderr-btc_default_paths.log"
    )
    assert result.working_dir == (
        tmp_path / "tipsy_io" / "scratch" / "btc-btc_default_paths" / "work"
    )


def test_run_btc_cli_windows_missing_output_raises_with_exit_code(
    monkeypatch, tmp_path: Path
) -> None:
    input_csv = tmp_path / "MSYT.csv"
    input_csv.write_text("feature_id\n1\n", encoding="utf-8")
    fake_btc = tmp_path / "TIPSYbtc.exe"
    fake_btc.write_text("stub", encoding="utf-8")
    monkeypatch.setattr(tipsy_module, "_tipsy_is_windows_host", lambda: True)
    monkeypatch.setattr(
        tipsy_module,
        "_run_windows_btc_with_dialog_cleanup",
        lambda **kwargs: (7, "", "", {"close_attempted": False}),
    )

    with pytest.raises(RuntimeError, match=r"exit_code=7"):
        run_btc_cli(
            input_csv=input_csv,
            mode="TSR",
            executable_path=fake_btc,
            scratch_root=tmp_path / "scratch",
            log_dir=tmp_path / "logs",
            run_id="btc_windows_missing_output",
            env={},
        )


def test_run_btc_cli_tsr_preset_uses_overlay_with_backup_restore(
    monkeypatch, tmp_path: Path
) -> None:
    input_csv = tmp_path / "MSYT.csv"
    input_csv.write_text("feature_id\n1\n", encoding="utf-8")
    install_root = tmp_path / "btc"
    install_root.mkdir()
    fake_btc = install_root / "TIPSYbtc.exe"
    fake_btc.write_text("stub", encoding="utf-8")
    (install_root / "TimberSupply.rpt").write_text(
        "[CustomReport]\n"
        "Name=Timber Supply\n"
        "TableRange=0-120:10|#\tMAX=120\tINC=10\n"
        "\n"
        "[CustomReportColumns]\n"
        "Volume:Auto:Con\t\tMVcon\t{yr}\n",
        encoding="utf-8",
    )
    overlay_path = tmp_path / "Docs" / "BatchTIPSY Composer" / "TimberSupply.rpt"
    overlay_path.parent.mkdir(parents=True, exist_ok=True)
    overlay_path.write_text("ORIGINAL OVERLAY\n", encoding="utf-8")
    seen_overlay_text: dict[str, str] = {}

    def fake_windows_run(**kwargs: object):
        seen_overlay_text["text"] = overlay_path.read_text(encoding="utf-8")
        cwd = Path(kwargs["cwd"])
        (cwd / "MSYT_output.csv").write_text(
            "feature_id,MVcon_0,MAI_0\n1,2,3\n", encoding="utf-8"
        )
        (cwd / "MSYT_error.csv").write_text("warnings,errors\n0,0\n", encoding="utf-8")
        return 0, "", "", {"close_attempted": False, "closed_window_count": 0}

    monkeypatch.setattr(tipsy_module, "_tipsy_is_windows_host", lambda: True)
    monkeypatch.setattr(
        tipsy_module,
        "_resolve_btc_user_overlay_report_path",
        lambda **kwargs: overlay_path,
    )
    monkeypatch.setattr(
        tipsy_module,
        "_run_windows_btc_with_dialog_cleanup",
        fake_windows_run,
    )

    result = run_btc_cli(
        input_csv=input_csv,
        mode="TSR",
        executable_path=fake_btc,
        report_preset_name="tsr-unattended-default",
        indicator_bank_names=["stand-structure-basic"],
        scratch_root=tmp_path / "scratch",
        log_dir=tmp_path / "logs",
        run_id="btc_overlay_bank",
        env={},
    )

    assert result.exit_code == 0
    assert result.uses_live_overlay is True
    assert result.report_template_path == overlay_path
    assert "MAI\t\tMAI\t{yr}" in seen_overlay_text["text"]
    assert "SPH:000\t\tSPH000\t{yr}" in seen_overlay_text["text"]
    assert overlay_path.read_text(encoding="utf-8") == "ORIGINAL OVERLAY\n"


def test_resolve_windows_documents_dir_uses_user_shell_folders(
    monkeypatch, tmp_path: Path
) -> None:
    docs_dir = tmp_path / "Docs"

    class _FakeKey:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

    class _FakeWinreg:
        HKEY_CURRENT_USER = object()

        @staticmethod
        def OpenKey(_root, subkey: str):
            assert subkey == (
                r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders"
            )
            return _FakeKey()

        @staticmethod
        def QueryValueEx(_key, value_name: str):
            assert value_name == "Personal"
            return (str(docs_dir), 0)

    monkeypatch.setattr(tipsy_module, "_tipsy_is_windows_host", lambda: True)
    monkeypatch.setitem(sys.modules, "winreg", _FakeWinreg)

    assert tipsy_module._resolve_windows_documents_dir() == docs_dir


def test_resolve_btc_user_overlay_report_path_prefers_windows_documents_dir(
    monkeypatch, tmp_path: Path
) -> None:
    docs_dir = tmp_path / "Docs"
    monkeypatch.setattr(
        tipsy_module,
        "_resolve_windows_documents_dir",
        lambda: docs_dir,
    )

    resolved = tipsy_module._resolve_btc_user_overlay_report_path(mode="TSR")

    assert resolved == docs_dir / "BatchTIPSY Composer" / "TimberSupply.rpt"
    assert resolved.parent.is_dir()


def test_probe_btc_report_columns_ratchets_forward(monkeypatch, tmp_path: Path) -> None:
    input_csv = tmp_path / "MSYT.csv"
    input_csv.write_text("feature_id\n1\n", encoding="utf-8")
    install_root = tmp_path / "btc"
    install_root.mkdir()
    (install_root / "TIPSYbtc.exe").write_text("stub", encoding="utf-8")
    (install_root / "TimberSupply.rpt").write_text(
        "[CustomReport]\n"
        "Name=Timber Supply\n"
        "TableRange=0-120:10|#\tMAX=120\tINC=10\n"
        "\n"
        "[CustomReportColumns]\n"
        "Volume:Auto:Con\t\tMVcon\t{yr}\n",
        encoding="utf-8",
    )
    (install_root / "Yield.rpt").write_text("SPH:000\n", encoding="utf-8")
    (install_root / "OutputColumns.txt").write_text("SPH:000\n", encoding="utf-8")
    overlay_path = tmp_path / "user_overlay" / "TimberSupply.rpt"
    overlay_path.parent.mkdir(parents=True, exist_ok=True)
    overlay_path.write_text("ORIGINAL OVERLAY\n", encoding="utf-8")
    seen_tokens: list[str] = []

    def fake_run_btc_cli(**kwargs: object) -> BTCRunResult:
        assert kwargs["report_template"] is None
        candidate = str(kwargs["run_id"]).split("_", 2)[-1].replace("_", ":")
        if candidate == "SPH:000":
            assert "SPH:000" in overlay_path.read_text(encoding="utf-8")
        seen_tokens.append(candidate)
        if candidate == "SPH:000":
            raise RuntimeError("BTC crashed in BatchProcess()")
        run_id = str(kwargs["run_id"])
        return BTCRunResult(
            run_id=run_id,
            mode="TSR",
            manifest_path=tmp_path / f"{run_id}.json",
            stdout_log_path=tmp_path / f"{run_id}.stdout.log",
            stderr_log_path=tmp_path / f"{run_id}.stderr.log",
            output_csv_path=tmp_path / f"{run_id}_output.csv",
            error_csv_path=tmp_path / f"{run_id}_error.csv",
            executable_path=tmp_path / "TIPSYbtc.exe",
            install_root=tmp_path / "btc_install",
            working_dir=tmp_path / "work",
            command=("btc.exe", "/TSR", "MSYT.csv"),
            copied_install=True,
            exit_code=0,
            duration_sec=1.0,
            report_template_path=tmp_path / "btc_install" / "TimberSupply.rpt",
        )

    monkeypatch.setattr("femic.pipeline.tipsy.run_btc_cli", fake_run_btc_cli)
    monkeypatch.setattr(
        tipsy_module,
        "_resolve_btc_user_overlay_report_path",
        lambda **kwargs: overlay_path,
    )

    results, final_template = probe_btc_report_columns(
        input_csv=input_csv,
        candidate_tokens=["VolumeGross", "SPH:000", "CC"],
        executable_path=install_root / "TIPSYbtc.exe",
        source_preset_name="tsr-unattended-default",
        copy_install=False,
        scratch_root=tmp_path / "scratch",
        log_dir=tmp_path / "logs",
        run_id_prefix="probe",
        compatibility_json=tmp_path / "compatibility.json",
    )

    assert [result.status for result in results] == ["accepted", "failed", "accepted"]
    assert results[1].error_message == "BTC crashed in BatchProcess()"
    final_tokens = [column.token for column in final_template.columns]
    assert "VolumeGross" in final_tokens
    assert "SPH:000" not in final_tokens
    assert "CC" in final_tokens
    assert seen_tokens == ["VolumeGross", "SPH:000", "CC"]
    assert results[1].failure_classification is None
    assert results[1].clues is not None
    assert results[1].clues["present_in_yield_rpt"] is True
    assert (tmp_path / "compatibility.json").is_file()
    assert overlay_path.read_text(encoding="utf-8") == "ORIGINAL OVERLAY\n"


def test_btc_build_probe_variants_default_uses_short_ascii_alias() -> None:
    variants = tipsy_module._btc_build_probe_variants(
        candidate_column=BTCCustomReportColumn(token="Logs_Grade_D"),
        install_root=Path("C:/Program Files/TIPSY 4.7/BTC"),
        variant_strategy="default",
    )

    assert len(variants) == 1
    assert variants[0].variant_id == "default"
    assert re.fullmatch(r"[A-Za-z0-9]{1,8}", variants[0].column.header1_override)
    assert variants[0].column.header2_override == "{yr}"
    assert variants[0].column.render().startswith("Logs_Grade_D\t\t")
    assert variants[0].column.render().endswith("\t{yr}")


def test_probe_btc_report_columns_defaults_compatibility_ledger_under_tipsy_logs(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    input_csv = tmp_path / "MSYT.csv"
    input_csv.write_text("feature_id\n1\n", encoding="utf-8")

    def fake_run_btc_cli(**kwargs: object) -> BTCRunResult:
        run_id = str(kwargs["run_id"])
        return BTCRunResult(
            run_id=run_id,
            mode="TSR",
            manifest_path=tmp_path
            / "tipsy_io"
            / "logs"
            / f"btc_manifest-{run_id}.json",
            stdout_log_path=tmp_path / "tipsy_io" / "logs" / f"btc_stdout-{run_id}.log",
            stderr_log_path=tmp_path / "tipsy_io" / "logs" / f"btc_stderr-{run_id}.log",
            output_csv_path=tmp_path / f"{run_id}_output.csv",
            error_csv_path=tmp_path / f"{run_id}_error.csv",
            executable_path=tmp_path / "TIPSYbtc.exe",
            install_root=tmp_path / "btc_install",
            working_dir=tmp_path / "tipsy_io" / "scratch" / run_id / "work",
            command=("btc.exe", "/TSR", "MSYT.csv"),
            copied_install=False,
            exit_code=0,
            duration_sec=1.0,
            report_template_path=None,
        )

    monkeypatch.setattr("femic.pipeline.tipsy.run_btc_cli", fake_run_btc_cli)

    probe_btc_report_columns(
        input_csv=input_csv,
        candidate_tokens=["VolumeGross"],
        source_preset_name="tsr-unattended-default",
        copy_install=True,
        run_id_prefix="probe_defaults",
        env={},
    )

    assert (
        tmp_path / "tipsy_io" / "logs" / "probe_defaults_compatibility.json"
    ).is_file()


def test_btc_tsr_output_prefixes_accepts_stock_display_headers(tmp_path: Path) -> None:
    output_csv = tmp_path / "output.csv"
    output_csv.write_text(
        "feature_id,Logs (Grade)_10,Mortality Stems (Size Class)_20\n1,2,3\n",
        encoding="utf-8",
    )

    prefixes = tipsy_module._btc_tsr_output_prefixes(output_csv)

    assert "Logs (Grade)" in prefixes
    assert "Mortality Stems (Size Class)" in prefixes


def test_probe_btc_indicator_banks_accepts_whole_bank_in_one_run(
    monkeypatch, tmp_path: Path
) -> None:
    input_csv = tmp_path / "MSYT.csv"
    input_csv.write_text("feature_id\n1\n", encoding="utf-8")
    run_ids: list[str] = []

    def fake_run_btc_cli(**kwargs: object) -> BTCRunResult:
        run_id = str(kwargs["run_id"])
        run_ids.append(run_id)
        output_path = tmp_path / f"{run_id}_output.csv"
        error_path = tmp_path / f"{run_id}_error.csv"
        report_template = kwargs["report_template"]
        columns = list(report_template.columns)
        headers = ["feature_id"]
        for column in columns:
            prefix = column.header1_override or column.token.replace(":", "")
            headers.append(f"{prefix}_10")
        output_path.write_text(
            ",".join(headers) + "\n1," + ",".join("1" for _ in headers[1:]) + "\n",
            encoding="utf-8",
        )
        error_path.write_text("", encoding="utf-8")
        return BTCRunResult(
            run_id=run_id,
            mode="TSR",
            manifest_path=tmp_path / f"{run_id}.json",
            stdout_log_path=tmp_path / f"{run_id}.stdout.log",
            stderr_log_path=tmp_path / f"{run_id}.stderr.log",
            output_csv_path=output_path,
            error_csv_path=error_path,
            executable_path=tmp_path / "TIPSYbtc.exe",
            install_root=tmp_path / "btc_install",
            working_dir=tmp_path / "work",
            command=("btc.exe", "/TSR", "MSYT.csv"),
            copied_install=True,
            exit_code=0,
            duration_sec=1.0,
            report_template_path=tmp_path / "btc_install" / "TimberSupply.rpt",
        )

    monkeypatch.setattr("femic.pipeline.tipsy.run_btc_cli", fake_run_btc_cli)

    results, final_template = probe_btc_indicator_banks(
        input_csv=input_csv,
        indicator_bank_names=["log-grades"],
        source_preset_name="tsr-unattended-default",
        copy_install=True,
        scratch_root=tmp_path / "scratch",
        log_dir=tmp_path / "logs",
        run_id_prefix="bankprobe",
        env={},
    )

    assert run_ids == ["bankprobe_log_grades"]
    assert all(result.status == "accepted" for result in results)
    assert len(results) == 9
    final_tokens = [column.token for column in final_template.columns]
    assert "Logs_Grade_D" in final_tokens
    assert "Logs_Grade_All" in final_tokens


def test_probe_btc_indicator_banks_falls_back_to_ratchet_when_batch_run_misses_output(
    monkeypatch, tmp_path: Path
) -> None:
    input_csv = tmp_path / "MSYT.csv"
    input_csv.write_text("feature_id\n1\n", encoding="utf-8")
    run_ids: list[str] = []

    def fake_run_btc_cli(**kwargs: object) -> BTCRunResult:
        run_id = str(kwargs["run_id"])
        run_ids.append(run_id)
        output_path = tmp_path / f"{run_id}_output.csv"
        error_path = tmp_path / f"{run_id}_error.csv"
        report_template = kwargs["report_template"]
        columns = list(report_template.columns)
        headers = ["feature_id"]
        include_last = run_id != "bankprobe_log_grades"
        for column in columns:
            prefix = column.header1_override or column.token.replace(":", "")
            if not include_last and prefix == "Logs_Grade_All":
                continue
            headers.append(f"{prefix}_10")
        output_path.write_text(
            ",".join(headers) + "\n1," + ",".join("1" for _ in headers[1:]) + "\n",
            encoding="utf-8",
        )
        error_path.write_text("", encoding="utf-8")
        return BTCRunResult(
            run_id=run_id,
            mode="TSR",
            manifest_path=tmp_path / f"{run_id}.json",
            stdout_log_path=tmp_path / f"{run_id}.stdout.log",
            stderr_log_path=tmp_path / f"{run_id}.stderr.log",
            output_csv_path=output_path,
            error_csv_path=error_path,
            executable_path=tmp_path / "TIPSYbtc.exe",
            install_root=tmp_path / "btc_install",
            working_dir=tmp_path / "work",
            command=("btc.exe", "/TSR", "MSYT.csv"),
            copied_install=True,
            exit_code=0,
            duration_sec=1.0,
            report_template_path=tmp_path / "btc_install" / "TimberSupply.rpt",
        )

    monkeypatch.setattr("femic.pipeline.tipsy.run_btc_cli", fake_run_btc_cli)

    results, final_template = probe_btc_indicator_banks(
        input_csv=input_csv,
        indicator_bank_names=["log-grades"],
        source_preset_name="tsr-unattended-default",
        copy_install=True,
        scratch_root=tmp_path / "scratch",
        log_dir=tmp_path / "logs",
        run_id_prefix="bankprobe",
        env={},
    )

    assert run_ids[0] == "bankprobe_log_grades"
    assert any(run_id.startswith("bankprobe_log_grades_01_") for run_id in run_ids[1:])
    assert len(results) == 9
    assert all(result.status == "accepted" for result in results)
    final_tokens = [column.token for column in final_template.columns]
    assert "Logs_Grade_All" in final_tokens


def test_build_btc_probe_variants_includes_alias_and_stock_forms(
    tmp_path: Path,
) -> None:
    install_root = tmp_path / "btc"
    install_root.mkdir()
    (install_root / "Yield.rpt").write_text(
        "[CustomReport]\n"
        "Name=Yield\n"
        "Type=databaseByStand\n"
        "\n"
        "[CustomReportColumns]\n"
        "BasalArea:000\t750\n",
        encoding="utf-8",
    )

    variants = tipsy_module._btc_build_probe_variants(
        candidate_column=BTCCustomReportColumn(token="BasalArea000"),
        install_root=install_root,
        variant_strategy="stock-matrix",
    )

    variant_ids = {variant.variant_id for variant in variants}
    variant_tokens = {variant.column.token for variant in variants}
    short_alias = tipsy_module._btc_preferred_probe_alias(
        BTCCustomReportColumn(token="BasalArea000")
    )
    assert "generic-transposed" in variant_ids
    assert "alias-transposed-BasalArea_000" in variant_ids
    assert "stock-exact-Yield" in variant_ids
    assert "stock-transposed-Yield" in variant_ids
    assert "BasalArea000" in variant_tokens
    assert "BasalArea:000" in variant_tokens
    assert any(
        variant.variant_id == "generic-transposed"
        and variant.column.render() == f"BasalArea000\t\t{short_alias}\t{{yr}}"
        for variant in variants
    )


def test_parse_btc_custom_report_template_handles_utf8_bom(tmp_path: Path) -> None:
    template_path = tmp_path / "Yield.rpt"
    template_path.write_text(
        "[CustomReport]\n"
        "Name=Yield\n"
        "Type=databaseByStand\n"
        "\n"
        "[CustomReportColumns]\n"
        "Crop250VolUtil125\n",
        encoding="utf-8-sig",
    )

    template = parse_btc_custom_report_template(template_path)

    assert template.name == "Yield"
    assert [column.token for column in template.columns] == ["Crop250VolUtil125"]


def test_probe_btc_report_columns_stock_matrix_tries_later_variant(
    monkeypatch, tmp_path: Path
) -> None:
    input_csv = tmp_path / "MSYT.csv"
    input_csv.write_text("feature_id\n1\n", encoding="utf-8")
    install_root = tmp_path / "btc"
    install_root.mkdir()
    (install_root / "TIPSYbtc.exe").write_text("stub", encoding="utf-8")
    (install_root / "Yield.rpt").write_text(
        "[CustomReport]\n"
        "Name=Yield\n"
        "Type=databaseByStand\n"
        "\n"
        "[CustomReportColumns]\n"
        "Crop250VolUtil125\t750\n",
        encoding="utf-8",
    )
    run_ids: list[str] = []

    def fake_run_btc_cli(**kwargs: object) -> BTCRunResult:
        run_id = str(kwargs["run_id"])
        run_ids.append(run_id)
        output_path = tmp_path / f"{run_id}_output.csv"
        error_path = tmp_path / f"{run_id}_error.csv"
        trial_column = list(kwargs["report_template"].columns)[-1]
        headers = ["feature_id"]
        if (
            trial_column.width == 750
            and trial_column.header2_override == "{yr}"
            and trial_column.token == "Crop250VolUtil125"
        ):
            headers.append("Crop250VolUtil125_10")
        output_path.write_text(
            ",".join(headers) + "\n1," + ",".join("1" for _ in headers[1:]) + "\n",
            encoding="utf-8",
        )
        error_path.write_text("", encoding="utf-8")
        return BTCRunResult(
            run_id=run_id,
            mode="TSR",
            manifest_path=tmp_path / f"{run_id}.json",
            stdout_log_path=tmp_path / f"{run_id}.stdout.log",
            stderr_log_path=tmp_path / f"{run_id}.stderr.log",
            output_csv_path=output_path,
            error_csv_path=error_path,
            executable_path=install_root / "TIPSYbtc.exe",
            install_root=install_root,
            working_dir=tmp_path / "work",
            command=("btc.exe", "/TSR", "MSYT.csv"),
            copied_install=True,
            exit_code=0,
            duration_sec=1.0,
            report_template_path=install_root / "TimberSupply.rpt",
        )

    monkeypatch.setattr("femic.pipeline.tipsy.run_btc_cli", fake_run_btc_cli)

    results, final_template = probe_btc_report_columns(
        input_csv=input_csv,
        candidate_tokens=["Crop250VolUtil125"],
        executable_path=install_root / "TIPSYbtc.exe",
        source_preset_name="tsr-unattended-default",
        copy_install=True,
        scratch_root=tmp_path / "scratch",
        log_dir=tmp_path / "logs",
        run_id_prefix="variantprobe",
        variant_strategy="stock-matrix",
    )

    assert len(run_ids) >= 2
    assert run_ids[0].endswith("generic_transposed")
    assert results[0].status == "accepted"
    assert results[0].variant_id == "stock-transposed-Yield"
    assert results[0].probe_token == "Crop250VolUtil125"
    assert "stock-transposed-Yield" in results[0].attempted_variants
    assert final_template.columns[-1].header2_override == "{yr}"


def test_probe_btc_report_columns_stock_matrix_preserves_failure_classification(
    monkeypatch, tmp_path: Path
) -> None:
    input_csv = tmp_path / "MSYT.csv"
    input_csv.write_text("feature_id\n1\n", encoding="utf-8")
    install_root = tmp_path / "btc"
    install_root.mkdir()
    (install_root / "TIPSYbtc.exe").write_text("stub", encoding="utf-8")
    (install_root / "Yield.rpt").write_text(
        "[CustomReport]\n"
        "Name=Yield\n"
        "Type=databaseByStand\n"
        "\n"
        "[CustomReportColumns]\n"
        "BasalArea:000\n",
        encoding="utf-8",
    )

    def fake_run_btc_cli(**kwargs: object) -> BTCRunResult:
        run_id = str(kwargs["run_id"])
        manifest_path = tmp_path / "logs" / f"btc_manifest-{run_id}.json"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(
            '{"exit_code": 1, "artifacts": {"output_csv": {"exists": false}, '
            '"error_csv": {"exists": false}}, "windows_dialog_cleanup": '
            '{"close_attempted": true, "closed_window_count": 1}}',
            encoding="utf-8",
        )
        raise RuntimeError(
            "BTC output is missing requested probe columns: BasalArea000"
        )

    monkeypatch.setattr("femic.pipeline.tipsy.run_btc_cli", fake_run_btc_cli)

    results, _final_template = probe_btc_report_columns(
        input_csv=input_csv,
        candidate_tokens=["BasalArea000"],
        executable_path=install_root / "TIPSYbtc.exe",
        source_preset_name="tsr-unattended-default",
        copy_install=True,
        scratch_root=tmp_path / "scratch",
        log_dir=tmp_path / "logs",
        run_id_prefix="variantprobe",
        variant_strategy="stock-matrix",
    )

    assert results[0].status == "failed"
    assert results[0].failure_classification == "missing_output_exit_1"
    assert results[0].attempted_variants[-1] in {
        "stock-exact-Yield",
        "stock-transposed-Yield",
    }


def test_run_windows_btc_with_dialog_cleanup_force_stops_dialog_tree(
    monkeypatch, tmp_path: Path
) -> None:
    class _FakeProc:
        def __init__(self) -> None:
            self.pid = 4321
            self.returncode: int | None = None

        def poll(self) -> int | None:
            return self.returncode

        def communicate(self, timeout: float | None = None) -> tuple[str, str]:
            self.returncode = self.returncode if self.returncode is not None else -9
            return ("", "")

        def kill(self) -> None:
            self.returncode = -9

    fake_proc = _FakeProc()
    monkeypatch.setattr(tipsy_module, "_tipsy_is_windows_host", lambda: True)
    monkeypatch.setattr(
        tipsy_module.subprocess,
        "Popen",
        lambda *args, **kwargs: fake_proc,
    )
    monkeypatch.setattr(
        tipsy_module,
        "_find_windows_btc_dialog_process_ids",
        lambda **kwargs: {4321},
    )
    monkeypatch.setattr(
        tipsy_module,
        "_find_windows_process_tree_ids",
        lambda **kwargs: {4321, 5000},
    )
    closed: list[int] = []
    stopped: list[int] = []
    monkeypatch.setattr(
        tipsy_module,
        "_close_windows_process_main_windows",
        lambda pid: closed.append(pid) is None or 1,
    )
    monkeypatch.setattr(
        tipsy_module,
        "_force_stop_windows_process",
        lambda pid: stopped.append(pid) is None or True,
    )
    sleep_calls: list[float] = []
    monkeypatch.setattr(
        tipsy_module.time, "sleep", lambda seconds: sleep_calls.append(seconds)
    )

    exit_code, stdout_text, stderr_text, automation = (
        tipsy_module._run_windows_btc_with_dialog_cleanup(
            command=("btc.exe", "/TSR", "MSYT.csv"),
            env={},
            cwd=tmp_path,
        )
    )

    assert exit_code == -9
    assert stdout_text == ""
    assert stderr_text == ""
    assert automation["close_attempted"] is True
    assert automation["matched_dialog_pids"] == [4321]
    assert automation["closed_window_count"] == 1
    assert stopped == [4321, 5000]
    assert sleep_calls == []


def test_prepare_btc_runtime_copies_install_and_writes_report_template(
    tmp_path: Path,
) -> None:
    install_root = tmp_path / "btc"
    install_root.mkdir()
    fake_exe = install_root / "TIPSYbtc.exe"
    fake_exe.write_text("stub", encoding="utf-8")
    (install_root / "TimberSupply.rpt").write_text(
        "[CustomReport]\n"
        "Name=Timber Supply\n"
        "TableRange=0-120:10|#\tMAX=120\tINC=10\n"
        "\n"
        "[CustomReportColumns]\n"
        "Volume:Auto:Con\t0\tMVcon\t{yr}\n",
        encoding="utf-8",
    )
    input_csv = tmp_path / "MSYT.csv"
    input_csv.write_text("feature_id\n1\n", encoding="utf-8")
    prep = prepare_btc_runtime(
        executable_path=fake_exe,
        input_csv=input_csv,
        scratch_root=tmp_path / "scratch",
        mode="TSR",
        report_preset_name="tsr-unattended-default",
        copy_install=True,
    )
    assert prep.copied_install is True
    assert prep.executable_path.is_file()
    assert prep.staged_input_csv.is_file()
    assert prep.report_template_path is not None
    rendered = prep.report_template_path.read_text(encoding="utf-8")
    assert "TableRange=0-350:10|#\tMAX=350\tINC=10" in rendered
    assert "VolumeGross\t\tgVol\t{yr}" in rendered
    assert "CC\t\tCC\t{yr}" in rendered


def test_prepare_btc_runtime_tsr_preset_applies_indicator_bank(
    tmp_path: Path,
) -> None:
    install_root = tmp_path / "btc"
    install_root.mkdir()
    fake_exe = install_root / "TIPSYbtc.exe"
    fake_exe.write_text("stub", encoding="utf-8")
    (install_root / "TimberSupply.rpt").write_text(
        "[CustomReport]\n"
        "Name=Timber Supply\n"
        "TableRange=0-120:10|#\tMAX=120\tINC=10\n"
        "\n"
        "[CustomReportColumns]\n"
        "Volume:Auto:Con\t0\tMVcon\t{yr}\n",
        encoding="utf-8",
    )
    input_csv = tmp_path / "MSYT.csv"
    input_csv.write_text("feature_id\n1\n", encoding="utf-8")

    prep = prepare_btc_runtime(
        executable_path=fake_exe,
        input_csv=input_csv,
        scratch_root=tmp_path / "scratch",
        mode="TSR",
        report_preset_name="tsr-unattended-default",
        indicator_bank_names=["stand-structure-basic"],
        copy_install=True,
    )

    assert prep.report_template_path is not None
    rendered = prep.report_template_path.read_text(encoding="utf-8")
    assert "MAI\t\tMAI\t{yr}" in rendered
    assert "BasalArea:000\t\tBasalArea000\t{yr}" in rendered
    assert "StemCount175\t\tStemCount175\t{yr}" in rendered


def test_prepare_btc_runtime_tsr_preset_applies_log_grades_indicator_bank(
    tmp_path: Path,
) -> None:
    install_root = tmp_path / "btc"
    install_root.mkdir()
    fake_exe = install_root / "TIPSYbtc.exe"
    fake_exe.write_text("stub", encoding="utf-8")
    (install_root / "TimberSupply.rpt").write_text(
        "[CustomReport]\n"
        "Name=Timber Supply\n"
        "TableRange=0-120:10|#\tMAX=120\tINC=10\n"
        "\n"
        "[CustomReportColumns]\n"
        "Volume:Auto:Con\t0\tMVcon\t{yr}\n",
        encoding="utf-8",
    )
    input_csv = tmp_path / "MSYT.csv"
    input_csv.write_text("feature_id\n1\n", encoding="utf-8")

    prep = prepare_btc_runtime(
        executable_path=fake_exe,
        input_csv=input_csv,
        scratch_root=tmp_path / "scratch",
        mode="TSR",
        report_preset_name="tsr-unattended-default",
        indicator_bank_names=["log-grades"],
        copy_install=True,
    )

    assert prep.report_template_path is not None
    rendered = prep.report_template_path.read_text(encoding="utf-8")
    assert "Logs_Grade_D\t\tLogs_Grade_D\t{yr}" in rendered
    assert "Logs_Grade_Y\t\tLogs_Grade_Y\t{yr}" in rendered
    assert "Logs_Grade_All\t\tLogs_Grade_All\t{yr}" in rendered


def test_prepare_btc_runtime_tsr_preset_applies_lumber_2_or_better_indicator_bank(
    tmp_path: Path,
) -> None:
    install_root = tmp_path / "btc"
    install_root.mkdir()
    fake_exe = install_root / "TIPSYbtc.exe"
    fake_exe.write_text("stub", encoding="utf-8")
    (install_root / "TimberSupply.rpt").write_text(
        "[CustomReport]\n"
        "Name=Timber Supply\n"
        "TableRange=0-120:10|#\tMAX=120\tINC=10\n"
        "\n"
        "[CustomReportColumns]\n"
        "Volume:Auto:Con\t0\tMVcon\t{yr}\n",
        encoding="utf-8",
    )
    input_csv = tmp_path / "MSYT.csv"
    input_csv.write_text("feature_id\n1\n", encoding="utf-8")

    prep = prepare_btc_runtime(
        executable_path=fake_exe,
        input_csv=input_csv,
        scratch_root=tmp_path / "scratch",
        mode="TSR",
        report_preset_name="tsr-unattended-default",
        indicator_bank_names=["lumber-2-or-better"],
        copy_install=True,
    )

    assert prep.report_template_path is not None
    rendered = prep.report_template_path.read_text(encoding="utf-8")
    assert "Lumber_2_or_Better_2x4\t\tLumber_2_or_Better_2x4\t{yr}" in rendered
    assert "Lumber_2_or_Better_All\t\tLumber_2_or_Better_All\t{yr}" in rendered
    assert "LRF_2_or_Better_All\t\tLRF_2_or_Better_All\t{yr}" in rendered


def test_prepare_btc_runtime_tsr_preset_applies_residual_fibre_indicator_bank(
    tmp_path: Path,
) -> None:
    install_root = tmp_path / "btc"
    install_root.mkdir()
    fake_exe = install_root / "TIPSYbtc.exe"
    fake_exe.write_text("stub", encoding="utf-8")
    (install_root / "TimberSupply.rpt").write_text(
        "[CustomReport]\n"
        "Name=Timber Supply\n"
        "TableRange=0-120:10|#\tMAX=120\tINC=10\n"
        "\n"
        "[CustomReportColumns]\n"
        "Volume:Auto:Con\t0\tMVcon\t{yr}\n",
        encoding="utf-8",
    )
    input_csv = tmp_path / "MSYT.csv"
    input_csv.write_text("feature_id\n1\n", encoding="utf-8")

    prep = prepare_btc_runtime(
        executable_path=fake_exe,
        input_csv=input_csv,
        scratch_root=tmp_path / "scratch",
        mode="TSR",
        report_preset_name="tsr-unattended-default",
        indicator_bank_names=["residual-fibre"],
        copy_install=True,
    )

    assert prep.report_template_path is not None
    rendered = prep.report_template_path.read_text(encoding="utf-8")
    assert "Residual_Chips\t\tResidual_Chips\t{yr}" in rendered
    assert "Residual_Sawdust\t\tResidual_Sawdust\t{yr}" in rendered
    assert "Residual_Bark\t\tResidual_Bark\t{yr}" in rendered


def test_prepare_btc_runtime_tsr_preset_applies_lumber_graded_indicator_bank(
    tmp_path: Path,
) -> None:
    install_root = tmp_path / "btc"
    install_root.mkdir()
    fake_exe = install_root / "TIPSYbtc.exe"
    fake_exe.write_text("stub", encoding="utf-8")
    (install_root / "TimberSupply.rpt").write_text(
        "[CustomReport]\n"
        "Name=Timber Supply\n"
        "TableRange=0-120:10|#\tMAX=120\tINC=10\n"
        "\n"
        "[CustomReportColumns]\n"
        "Volume:Auto:Con\t0\tMVcon\t{yr}\n",
        encoding="utf-8",
    )
    input_csv = tmp_path / "MSYT.csv"
    input_csv.write_text("feature_id\n1\n", encoding="utf-8")

    prep = prepare_btc_runtime(
        executable_path=fake_exe,
        input_csv=input_csv,
        scratch_root=tmp_path / "scratch",
        mode="TSR",
        report_preset_name="tsr-unattended-default",
        indicator_bank_names=["lumber-graded"],
        copy_install=True,
    )

    assert prep.report_template_path is not None
    rendered = prep.report_template_path.read_text(encoding="utf-8")
    assert "Lumber_Graded_SS_2x4\t\tLumber_Graded_SS_2x4\t{yr}" in rendered
    assert "Lumber_Graded_All\t\tLumber_Graded_All\t{yr}" in rendered
    assert "LRF_Graded_All\t\tLRF_Graded_All\t{yr}" in rendered


def test_prepare_btc_runtime_tsr_preset_applies_lumber_degraded_indicator_bank(
    tmp_path: Path,
) -> None:
    install_root = tmp_path / "btc"
    install_root.mkdir()
    fake_exe = install_root / "TIPSYbtc.exe"
    fake_exe.write_text("stub", encoding="utf-8")
    (install_root / "TimberSupply.rpt").write_text(
        "[CustomReport]\n"
        "Name=Timber Supply\n"
        "TableRange=0-120:10|#\tMAX=120\tINC=10\n"
        "\n"
        "[CustomReportColumns]\n"
        "Volume:Auto:Con\t0\tMVcon\t{yr}\n",
        encoding="utf-8",
    )
    input_csv = tmp_path / "MSYT.csv"
    input_csv.write_text("feature_id\n1\n", encoding="utf-8")

    prep = prepare_btc_runtime(
        executable_path=fake_exe,
        input_csv=input_csv,
        scratch_root=tmp_path / "scratch",
        mode="TSR",
        report_preset_name="tsr-unattended-default",
        indicator_bank_names=["lumber-degraded"],
        copy_install=True,
    )

    assert prep.report_template_path is not None
    rendered = prep.report_template_path.read_text(encoding="utf-8")
    assert "Lumber_Degraded_SS_2x4\t\tLumber_Degraded_SS_2x4\t{yr}" in rendered
    assert "Lumber_Degraded_All\t\tLumber_Degraded_All\t{yr}" in rendered
    assert "LRF_Degraded_All\t\tLRF_Degraded_All\t{yr}" in rendered


def test_prepare_btc_runtime_tsr_preset_applies_industrial_logs_indicator_bank(
    tmp_path: Path,
) -> None:
    install_root = tmp_path / "btc"
    install_root.mkdir()
    fake_exe = install_root / "TIPSYbtc.exe"
    fake_exe.write_text("stub", encoding="utf-8")
    (install_root / "TimberSupply.rpt").write_text(
        "[CustomReport]\n"
        "Name=Timber Supply\n"
        "TableRange=0-120:10|#\tMAX=120\tINC=10\n"
        "\n"
        "[CustomReportColumns]\n"
        "Volume:Auto:Con\t0\tMVcon\t{yr}\n",
        encoding="utf-8",
    )
    input_csv = tmp_path / "MSYT.csv"
    input_csv.write_text("feature_id\n1\n", encoding="utf-8")

    prep = prepare_btc_runtime(
        executable_path=fake_exe,
        input_csv=input_csv,
        scratch_root=tmp_path / "scratch",
        mode="TSR",
        report_preset_name="tsr-unattended-default",
        indicator_bank_names=["industrial-logs"],
        copy_install=True,
    )

    assert prep.report_template_path is not None
    rendered = prep.report_template_path.read_text(encoding="utf-8")
    assert "Industrial_Logs_D38L13\t\tIndustrial_Logs_D38L13\t{yr}" in rendered
    assert "Industrial_Logs_D125L5\t\tIndustrial_Logs_D125L5\t{yr}" in rendered
    assert "Industrial_Logs_D152\t\tIndustrial_Logs_D152\t{yr}" in rendered


def test_write_tipsy_input_exports_fails_fast_on_width_overflow(tmp_path: Path) -> None:
    table = pd.DataFrame(
        {
            "AU": [1001],
            "TBLno": [1001],
            "Proportion": [0.85],
            "Regen_Delay": [2],
            "Density": [900],
            "Regen_Method": ["P"],
            "Util_DBH_cm": [12.5],
            "OAF1": [0.7],
            "OAF2": [0.95],
            "FIZ": ["INVALID"],  # width is 1 char by BatchTIPSY mapping
            "SPP_1": ["PL"],
            "PCT_1": [100],
            "SI": [20.0],
        }
    )
    with pytest.raises(ValueError, match="value overflow.*FIZ"):
        write_tipsy_input_exports(
            tipsy_table=table,
            tsa="08",
            tipsy_params_path_prefix=str(tmp_path / "tipsy_params_tsa"),
            dat_path_template=str(tmp_path / "02_input-tsa{tsa}.dat"),
        )


def test_validate_tipsy_output_is_fresh_raises_on_stale_output(tmp_path: Path) -> None:
    tipsy_input = tmp_path / "tipsy_params_tsa29.xlsx"
    tipsy_dat = tmp_path / "02_input-tsa29.dat"
    tipsy_output = tmp_path / "04_output-tsa29.out"
    tipsy_output.write_text("old\n", encoding="utf-8")
    tipsy_dat.write_text("newer-dat\n", encoding="utf-8")
    tipsy_input.write_text("new\n", encoding="utf-8")
    older = min(tipsy_input.stat().st_mtime, tipsy_dat.stat().st_mtime) - 10
    os.utime(tipsy_output, (older, older))

    with pytest.raises(RuntimeError, match="Stale BatchTIPSY output detected"):
        validate_tipsy_output_is_fresh(
            tipsy_input_excel_path=tipsy_input,
            tipsy_input_dat_path=tipsy_dat,
            tipsy_output_path=tipsy_output,
        )


def test_validate_tipsy_output_is_fresh_warns_and_continues_on_coherent_stale_pair(
    tmp_path: Path,
) -> None:
    tipsy_input = tmp_path / "tipsy_params_tsa29.xlsx"
    tipsy_dat = tmp_path / "02_input-tsa29.dat"
    tipsy_output = tmp_path / "04_output-tsa29.out"
    pd.DataFrame(
        {
            "AU": [2001, 2002],
            "TBLno": [2001, 2002],
            "SI": [30, 32],
        }
    ).to_excel(tipsy_input, sheet_name="TIPSY_inputTBL", index=False)
    tipsy_dat.write_text("newer-dat\n", encoding="utf-8")
    tipsy_output.write_text("h1\nh2\nh3\nh4\n2001\n2002\n", encoding="utf-8")
    older = tipsy_dat.stat().st_mtime - 10
    os.utime(tipsy_output, (older, older))

    with pytest.warns(RuntimeWarning, match="appear coherent"):
        validate_tipsy_output_is_fresh(
            tipsy_input_excel_path=tipsy_input,
            tipsy_input_dat_path=tipsy_dat,
            tipsy_output_path=tipsy_output,
        )


def test_validate_tipsy_output_is_fresh_strict_mode_raises_on_coherent_stale_pair(
    tmp_path: Path,
) -> None:
    tipsy_input = tmp_path / "tipsy_params_tsa29.xlsx"
    tipsy_dat = tmp_path / "02_input-tsa29.dat"
    tipsy_output = tmp_path / "04_output-tsa29.out"
    pd.DataFrame(
        {
            "AU": [2101, 2102],
            "TBLno": [2101, 2102],
            "SI": [25, 28],
        }
    ).to_excel(tipsy_input, sheet_name="TIPSY_inputTBL", index=False)
    tipsy_dat.write_text("newer-dat\n", encoding="utf-8")
    tipsy_output.write_text("h1\nh2\nh3\nh4\n2101\n2102\n", encoding="utf-8")
    older = tipsy_dat.stat().st_mtime - 10
    os.utime(tipsy_output, (older, older))

    with pytest.raises(RuntimeError, match="Strict BatchTIPSY freshness"):
        validate_tipsy_output_is_fresh(
            tipsy_input_excel_path=tipsy_input,
            tipsy_input_dat_path=tipsy_dat,
            tipsy_output_path=tipsy_output,
            strict_timestamp_mismatch=True,
        )


def test_validate_tipsy_output_is_fresh_allows_override(tmp_path: Path) -> None:
    tipsy_input = tmp_path / "tipsy_params_tsa29.xlsx"
    tipsy_dat = tmp_path / "02_input-tsa29.dat"
    tipsy_output = tmp_path / "04_output-tsa29.out"
    tipsy_output.write_text("old\n", encoding="utf-8")
    tipsy_dat.write_text("newer-dat\n", encoding="utf-8")
    tipsy_input.write_text("new\n", encoding="utf-8")

    validate_tipsy_output_is_fresh(
        tipsy_input_excel_path=tipsy_input,
        tipsy_input_dat_path=tipsy_dat,
        tipsy_output_path=tipsy_output,
        allow_stale=True,
    )


def test_assess_tipsy_input_output_coherence_reports_missing_table(
    tmp_path: Path,
) -> None:
    tipsy_input = tmp_path / "tipsy_params_tsa29.xlsx"
    tipsy_output = tmp_path / "04_output-tsa29.out"
    pd.DataFrame(
        {
            "AU": [3001, 3002],
            "TBLno": [3001, 3002],
            "SI": [20, 21],
        }
    ).to_excel(tipsy_input, sheet_name="TIPSY_inputTBL", index=False)
    tipsy_output.write_text("h1\nh2\nh3\nh4\n3001\n", encoding="utf-8")

    coherence = assess_tipsy_input_output_coherence(
        tipsy_input_excel_path=tipsy_input,
        tipsy_output_path=tipsy_output,
    )
    assert coherence.coherent is False
    assert "missing_tables=1" in coherence.summary
    assert "missing_aus=1" in coherence.summary


def test_validate_tipsy_output_is_fresh_requires_dat_when_provided(
    tmp_path: Path,
) -> None:
    tipsy_input = tmp_path / "tipsy_params_tsa29.xlsx"
    tipsy_output = tmp_path / "04_output-tsa29.out"
    missing_dat = tmp_path / "02_input-tsa29.dat"
    tipsy_output.write_text("old\n", encoding="utf-8")
    tipsy_input.write_text("new\n", encoding="utf-8")

    with pytest.raises(
        RuntimeError, match="Missing canonical BatchTIPSY input DAT file"
    ):
        validate_tipsy_output_is_fresh(
            tipsy_input_excel_path=tipsy_input,
            tipsy_input_dat_path=missing_dat,
            tipsy_output_path=tipsy_output,
        )


def test_validate_tipsy_output_is_fresh_accepts_known_dat_fingerprint(
    tmp_path: Path,
) -> None:
    tipsy_input = tmp_path / "tipsy_params_tsa29.xlsx"
    tipsy_dat = tmp_path / "02_input-tsa29.dat"
    tipsy_output = tmp_path / "04_output-tsa29.out"
    tipsy_input.write_text("human-readable\n", encoding="utf-8")
    tipsy_dat.write_text("same-dat-content\n", encoding="utf-8")
    tipsy_output.write_text("old-output\n", encoding="utf-8")
    older = tipsy_dat.stat().st_mtime - 10
    os.utime(tipsy_output, (older, older))

    fingerprint = tipsy_output_input_fingerprint_path(tipsy_output_path=tipsy_output)
    fingerprint.write_text(f"{compute_file_sha256(tipsy_dat)}\n", encoding="utf-8")

    validate_tipsy_output_is_fresh(
        tipsy_input_excel_path=tipsy_input,
        tipsy_input_dat_path=tipsy_dat,
        tipsy_output_path=tipsy_output,
    )


def test_validate_tipsy_output_is_fresh_raises_on_dat_fingerprint_mismatch(
    tmp_path: Path,
) -> None:
    tipsy_input = tmp_path / "tipsy_params_tsa29.xlsx"
    tipsy_dat = tmp_path / "02_input-tsa29.dat"
    tipsy_output = tmp_path / "04_output-tsa29.out"
    tipsy_input.write_text("human-readable\n", encoding="utf-8")
    tipsy_dat.write_text("new-dat-content\n", encoding="utf-8")
    tipsy_output.write_text("some-output\n", encoding="utf-8")

    fingerprint = tipsy_output_input_fingerprint_path(tipsy_output_path=tipsy_output)
    fingerprint.write_text("badfingerprint\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="different 02_input-tsaXX.dat fingerprint"):
        validate_tipsy_output_is_fresh(
            tipsy_input_excel_path=tipsy_input,
            tipsy_input_dat_path=tipsy_dat,
            tipsy_output_path=tipsy_output,
        )


def test_write_tipsy_output_input_fingerprint_writes_sidecar(tmp_path: Path) -> None:
    tipsy_dat = tmp_path / "02_input-tsa29.dat"
    tipsy_output = tmp_path / "04_output-tsa29.out"
    tipsy_dat.write_text("dat-content\n", encoding="utf-8")
    tipsy_output.write_text("output\n", encoding="utf-8")
    path = write_tipsy_output_input_fingerprint(
        tipsy_input_dat_path=tipsy_dat,
        tipsy_output_path=tipsy_output,
    )
    assert path == tipsy_output_input_fingerprint_path(tipsy_output_path=tipsy_output)
    assert path is not None
    assert path.read_text(encoding="utf-8").strip() == compute_file_sha256(tipsy_dat)


def test_tipsy_input_dat_path_default_layout() -> None:
    assert tipsy_input_dat_path(tsa="29") == Path("data/02_input-tsa29.dat")


def test_write_tipsy_input_exports_keeps_regen_method_column_aligned(
    tmp_path: Path,
) -> None:
    table = pd.DataFrame(
        {
            "AU": [21001, 22001],
            "TBLno": [21001, 22001],
            "BEC": ["CWH", "BWBS"],
            "Proportion": [1, 1],
            "Regen_Delay": [2, 2],
            "Density": [1400, 1400],
            "Regen_Method": ["P", "P"],
        }
    )
    _excel_path, dat_path = write_tipsy_input_exports(
        tipsy_table=table,
        tsa="k3z",
        tipsy_params_path_prefix=str(tmp_path / "tipsy_params_tsa"),
        dat_path_template=str(tmp_path / "02_input-tsa{tsa}.dat"),
    )
    lines = Path(dat_path).read_text().splitlines()
    assert len(lines) >= 3
    p_positions = [lines[1].index("P"), lines[2].index("P")]
    assert p_positions[0] == p_positions[1]


def test_write_tipsy_input_exports_uses_stable_reference_column_starts(
    tmp_path: Path,
) -> None:
    table = pd.DataFrame(
        {
            "AU": [22008],
            "TBLno": [22008],
            "BEC": ["CWH"],
            "Proportion": [1],
            "Regen_Delay": [2],
            "Density": [900],
            "Regen_Method": ["P"],
            "Util_DBH_cm": [12.5],
            "OAF1": [0.73],
            "OAF2": [0.95],
            "FIZ": ["I"],
            "SPP_1": ["PLC"],
            "PCT_1": [70],
            "SI": [9.7],
            "GW_1": [""],
            "GW_age_1": [""],
            "SPP_2": ["HW"],
            "PCT_2": [20],
            "GW_2": [""],
            "GW_age_2": [""],
            "SPP_3": ["CW"],
            "PCT_3": [10],
            "GW_3": [""],
            "GW_age_3": [""],
            "SPP_4": [""],
            "PCT_4": [""],
            "GW_4": [""],
            "GW_age_4": [""],
            "SPP_5": [""],
            "PCT_5": [""],
            "GW_5": [""],
            "GW_age_5": [""],
        }
    )
    _excel_path, dat_path = write_tipsy_input_exports(
        tipsy_table=table,
        tsa="k3z",
        tipsy_params_path_prefix=str(tmp_path / "tipsy_params_tsa"),
        dat_path_template=str(tmp_path / "02_input-tsa{tsa}.dat"),
    )
    row = Path(dat_path).read_text().splitlines()[1]
    # Validate against the configured fixed 1-based BatchTIPSY ranges.
    assert row[96:99].strip() == "PLC"  # SPP_1 (97-99)
    assert row[60:63].strip() == "70"  # PCT_1 (61-63)
    assert row[107:111].strip() == "9.7"  # SI (108-111)
    assert row[128:131].strip() == "HW"  # SPP_2 (129-131)
    assert row[135:137].strip() == "20"  # PCT_2 (136-137)
    assert row[154:157].strip() == "CW"  # SPP_3 (155-157)
    assert row[161:163].strip() == "10"  # PCT_3 (162-163)


def test_tipsy_stage_output_paths_uses_expected_naming(tmp_path: Path) -> None:
    curves_path, sppcomp_path = tipsy_stage_output_paths(tsa="08", output_root=tmp_path)
    assert curves_path == tmp_path / "tipsy_curves_tsa08.csv"
    assert sppcomp_path == tmp_path / "tipsy_sppcomp_tsa08.csv"


def test_tipsy_params_excel_path_uses_expected_naming(tmp_path: Path) -> None:
    path = tipsy_params_excel_path(
        tsa="08",
        tipsy_params_path_prefix=tmp_path / "tipsy_params_tsa",
    )
    assert path == tmp_path / "tipsy_params_tsa08.xlsx"


def test_build_tipsy_params_for_tsa_assigns_expected_maps() -> None:
    results_for_tsa = [
        (
            0,
            "SBS_7A",
            {
                "L": {
                    "ss": pd.DataFrame(
                        {
                            "SITE_INDEX": [18.0],
                            "siteprod": [17.0],
                            "BEC_ZONE_CODE": ["SBS"],
                        }
                    ),
                    "species": {"SW": {"pct": 60.0}},
                }
            },
        )
    ]
    vdyp_curves_smooth_tsa = pd.DataFrame(
        {
            "stratum_code": ["SBS_7A", "SBS_7A"],
            "si_level": ["L", "L"],
            "age": [30, 120],
            "volume": [160.0, 220.0],
        }
    )
    exclusion = {
        "min_vol": lambda _code: 140.0,
        "min_si": lambda _species: 10.0,
        "excl_leading_species": [],
        "excl_bec": [],
    }

    def _builder(
        au_id: int,
        _au_data: object,
        _vdyp_out: object,
    ) -> dict[str, dict[str, object]]:
        return {"f": {"TBLno": 20000 + au_id}}

    scsi_au_tsa, au_scsi_tsa, tipsy_params_tsa = build_tipsy_params_for_tsa(
        tsa="08",
        results_for_tsa=results_for_tsa,
        si_levels=["L"],
        vdyp_curves_smooth_tsa=vdyp_curves_smooth_tsa,
        vdyp_results_for_tsa={0: {"L": {"dummy": 1}}},
        exclusion=exclusion,
        tipsy_param_builder=_builder,
        verbose=False,
        message_fn=lambda *_args: None,
    )
    assert scsi_au_tsa == {("SBS_7A", "L"): 1000}
    assert au_scsi_tsa == {1000: ("SBS_7A", "L")}
    assert tipsy_params_tsa[1000]["f"]["TBLno"] == 21000


def test_build_tipsy_params_for_tsa_logs_missing_vdyp_output_warning() -> None:
    events: list[dict[str, object]] = []
    results_for_tsa = [
        (
            0,
            "SBS_7A",
            {
                "L": {
                    "ss": pd.DataFrame(
                        {
                            "SITE_INDEX": [18.0],
                            "siteprod": [17.0],
                            "BEC_ZONE_CODE": ["SBS"],
                        }
                    ),
                    "species": {"SW": {"pct": 60.0}},
                }
            },
        )
    ]
    vdyp_curves_smooth_tsa = pd.DataFrame(
        {
            "stratum_code": ["SBS_7A", "SBS_7A"],
            "si_level": ["L", "L"],
            "age": [30, 120],
            "volume": [160.0, 220.0],
        }
    )
    exclusion = {
        "min_vol": lambda _code: 140.0,
        "min_si": lambda _species: 10.0,
        "excl_leading_species": [],
        "excl_bec": [],
    }

    def _append_jsonl(_path: object, payload: dict[str, object]) -> None:
        events.append(payload)

    scsi_au_tsa, au_scsi_tsa, tipsy_params_tsa = build_tipsy_params_for_tsa(
        tsa="08",
        results_for_tsa=results_for_tsa,
        si_levels=["L"],
        vdyp_curves_smooth_tsa=vdyp_curves_smooth_tsa,
        vdyp_results_for_tsa={},
        exclusion=exclusion,
        tipsy_param_builder=lambda *_args: {"f": {}},
        vdyp_curve_events_path="events.jsonl",
        append_jsonl_fn=_append_jsonl,
        verbose=True,
        message_fn=lambda *_args: None,
    )
    assert scsi_au_tsa == {}
    assert au_scsi_tsa == {}
    assert tipsy_params_tsa == {}
    assert len(events) == 1
    assert events[0]["reason"] == "missing_vdyp_output"


def test_build_tipsy_params_for_tsa_skips_missing_fit_si_level() -> None:
    results_for_tsa = [
        (
            0,
            "SBS_7A",
            {
                "M": {
                    "ss": pd.DataFrame(
                        {
                            "SITE_INDEX": [18.0],
                            "siteprod": [17.0],
                            "BEC_ZONE_CODE": ["SBS"],
                        }
                    ),
                    "species": {"SW": {"pct": 60.0}},
                }
            },
        )
    ]
    vdyp_curves_smooth_tsa = pd.DataFrame(
        {
            "stratum_code": ["SBS_7A", "SBS_7A"],
            "si_level": ["M", "M"],
            "age": [30, 120],
            "volume": [160.0, 220.0],
        }
    )
    exclusion = {
        "min_vol": lambda _code: 140.0,
        "min_si": lambda _species: 10.0,
        "excl_leading_species": [],
        "excl_bec": [],
    }

    scsi_au_tsa, au_scsi_tsa, tipsy_params_tsa = build_tipsy_params_for_tsa(
        tsa="08",
        results_for_tsa=results_for_tsa,
        si_levels=["L", "M", "H"],
        vdyp_curves_smooth_tsa=vdyp_curves_smooth_tsa,
        vdyp_results_for_tsa={0: {"M": {"dummy": 1}}},
        exclusion=exclusion,
        tipsy_param_builder=lambda au_id, _au_data, _vdyp_out: {"f": {"TBLno": au_id}},
        verbose=False,
        message_fn=lambda *_args: None,
    )

    assert scsi_au_tsa == {("SBS_7A", "M"): 2000}
    assert au_scsi_tsa == {2000: ("SBS_7A", "M")}
    assert set(tipsy_params_tsa.keys()) == {2000}


def test_build_tipsy_params_for_tsa_merges_adjacent_similar_si_curves() -> None:
    results_for_tsa = [
        (
            0,
            "SBS_7A",
            {
                "L": {
                    "ss": pd.DataFrame(
                        {
                            "SITE_INDEX": [16.0],
                            "siteprod": [15.0],
                            "BEC_ZONE_CODE": ["SBS"],
                        }
                    ),
                    "species": {"SW": {"pct": 60.0}},
                },
                "M": {
                    "ss": pd.DataFrame(
                        {
                            "SITE_INDEX": [17.0],
                            "siteprod": [16.0],
                            "BEC_ZONE_CODE": ["SBS"],
                        }
                    ),
                    "species": {"SW": {"pct": 62.0}},
                },
                "H": {
                    "ss": pd.DataFrame(
                        {
                            "SITE_INDEX": [24.0],
                            "siteprod": [20.0],
                            "BEC_ZONE_CODE": ["SBS"],
                        }
                    ),
                    "species": {"SW": {"pct": 80.0}},
                },
            },
        )
    ]
    vdyp_curves_smooth_tsa = pd.DataFrame(
        {
            "stratum_code": ["SBS_7A"] * 6,
            "si_level": ["L", "L", "M", "M", "H", "H"],
            "age": [80, 120, 80, 120, 80, 120],
            "volume": [200.0, 260.0, 204.0, 255.0, 320.0, 410.0],
        }
    )
    exclusion = {
        "min_vol": lambda _code: 50.0,
        "min_si": lambda _species: 5.0,
        "excl_leading_species": [],
        "excl_bec": [],
    }

    scsi_au_tsa, au_scsi_tsa, tipsy_params_tsa = build_tipsy_params_for_tsa(
        tsa="08",
        results_for_tsa=results_for_tsa,
        si_levels=["L", "M", "H"],
        vdyp_curves_smooth_tsa=vdyp_curves_smooth_tsa,
        vdyp_results_for_tsa={
            0: {"L": {"dummy": 1}, "M": {"dummy": 2}, "H": {"dummy": 3}}
        },
        exclusion=exclusion,
        tipsy_param_builder=lambda au_id, _au_data, _vdyp_out: {"f": {"TBLno": au_id}},
        min_operable_years=0.0,
        si_merge_min_common_ages=2,
        verbose=False,
        message_fn=lambda *_args: None,
    )

    assert scsi_au_tsa == {
        ("SBS_7A", "L"): 2000,
        ("SBS_7A", "M"): 2000,
        ("SBS_7A", "H"): 3000,
    }
    assert au_scsi_tsa == {2000: ("SBS_7A", "M"), 3000: ("SBS_7A", "H")}
    assert set(tipsy_params_tsa.keys()) == {2000, 3000}


def test_build_tipsy_params_for_tsa_logs_no_species_candidates_warning() -> None:
    events: list[dict[str, object]] = []
    results_for_tsa = [
        (
            0,
            "SBS_7A",
            {
                "L": {
                    "ss": pd.DataFrame(
                        {
                            "SITE_INDEX": [18.0],
                            "siteprod": [17.0],
                            "BEC_ZONE_CODE": ["SBS"],
                        }
                    ),
                    "species": {},
                }
            },
        )
    ]
    vdyp_curves_smooth_tsa = pd.DataFrame(
        {
            "stratum_code": ["SBS_7A", "SBS_7A"],
            "si_level": ["L", "L"],
            "age": [30, 120],
            "volume": [160.0, 220.0],
        }
    )
    exclusion = {
        "min_vol": lambda _code: 140.0,
        "min_si": lambda _species: 10.0,
        "excl_leading_species": [],
        "excl_bec": [],
    }

    def _append_jsonl(_path: object, payload: dict[str, object]) -> None:
        events.append(payload)

    _ = build_tipsy_params_for_tsa(
        tsa="08",
        results_for_tsa=results_for_tsa,
        si_levels=["L"],
        vdyp_curves_smooth_tsa=vdyp_curves_smooth_tsa,
        vdyp_results_for_tsa={0: {"L": {"dummy": 1}}},
        exclusion=exclusion,
        tipsy_param_builder=lambda *_args: {"f": {}},
        vdyp_curve_events_path="events.jsonl",
        append_jsonl_fn=_append_jsonl,
        verbose=True,
        message_fn=lambda *_args: None,
    )
    assert len(events) == 1
    assert events[0]["reason"] == "no_species_candidates"


def test_build_tipsy_params_for_tsa_candidate_value_error_logs_debug_then_raises() -> (
    None
):
    messages: list[tuple[object, ...]] = []
    results_for_tsa = [
        (
            0,
            "BAD",
            {
                "L": {
                    "ss": pd.DataFrame(
                        {
                            "SITE_INDEX": [18.0],
                            "siteprod": [17.0],
                            "BEC_ZONE_CODE": ["SBS"],
                        }
                    ),
                    "species": {"SW": {"pct": 60.0}},
                }
            },
        )
    ]
    vdyp_curves_smooth_tsa = pd.DataFrame(
        {
            "stratum_code": ["BAD", "BAD"],
            "si_level": ["L", "L"],
            "age": [30, 120],
            "volume": [160.0, 220.0],
        }
    )
    exclusion = {
        "min_vol": lambda _code: 140.0,
        "min_si": lambda _species: 10.0,
        "excl_leading_species": [],
        "excl_bec": [],
    }

    with pytest.raises(ValueError, match="invalid stratum code format"):
        build_tipsy_params_for_tsa(
            tsa="08",
            results_for_tsa=results_for_tsa,
            si_levels=["L"],
            vdyp_curves_smooth_tsa=vdyp_curves_smooth_tsa,
            vdyp_results_for_tsa={0: {"L": {"dummy": 1}}},
            exclusion=exclusion,
            tipsy_param_builder=lambda *_args: {"f": {}},
            verbose=False,
            message_fn=lambda *args: messages.append(args),
        )

    assert any(msg == ("BAD", "L") for msg in messages)


def test_build_tipsy_params_for_tsa_unexpected_candidate_error_propagates() -> None:
    results_for_tsa = [
        (
            0,
            "SBS_7A",
            {
                "L": {
                    "ss": pd.DataFrame(
                        {
                            "SITE_INDEX": [18.0],
                            "siteprod": [17.0],
                            "BEC_ZONE_CODE": ["SBS"],
                        }
                    ),
                    "species": {"SW": {"pct": 60.0}},
                }
            },
        )
    ]
    vdyp_curves_smooth_tsa = pd.DataFrame(
        {
            "stratum_code": ["SBS_7A", "SBS_7A"],
            "si_level": ["L", "L"],
            "age": [30, 120],
            "volume": [160.0, 220.0],
        }
    )
    exclusion = {
        "min_vol": lambda _code: (_ for _ in ()).throw(ZeroDivisionError("unexpected")),
        "min_si": lambda _species: 10.0,
        "excl_leading_species": [],
        "excl_bec": [],
    }

    with pytest.raises(ZeroDivisionError, match="unexpected"):
        build_tipsy_params_for_tsa(
            tsa="08",
            results_for_tsa=results_for_tsa,
            si_levels=["L"],
            vdyp_curves_smooth_tsa=vdyp_curves_smooth_tsa,
            vdyp_results_for_tsa={0: {"L": {"dummy": 1}}},
            exclusion=exclusion,
            tipsy_param_builder=lambda *_args: {"f": {}},
            verbose=False,
            message_fn=lambda *_args: None,
        )
