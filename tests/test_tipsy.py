from __future__ import annotations

import json
import math
import os
from pathlib import Path
import re
import shutil
import sys
import types

import pandas as pd
import pytest
import femic.pipeline.tipsy as tipsy_module

from femic.pipeline.btc_runtime import (
    FEMIC_BTC_WINEPREFIX,
    BTCRuntimeConfig,
    BTCRuntimeConfigError,
)
from femic.pipeline.tipsy import (
    DEFAULT_BATCHTIPSY_EXE_ENV,
    DEFAULT_BTC_MSYT_COLUMNS,
    DEFAULT_WINE_EXE_ENV,
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
    tipsy_output_input_fingerprint_path,
    tipsy_params_excel_path,
    tipsy_stage_output_paths,
    validate_tipsy_output_is_fresh,
    write_btc_msyt_input_csv,
    write_btc_custom_report_template,
    write_tipsy_output_input_fingerprint,
    write_tipsy_input_exports,
)

# Optional guard for any real-runtime Wine tests. The BTC launcher suite is
# fully monkeypatched (no real Wine/TIPSY/xvfb processes are launched), so no
# test currently needs this marker; it exists for future opt-in real runs.
needs_real_wine = pytest.mark.skipif(
    not shutil.which("wine"), reason="wine not available"
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


def test_build_tipsy_input_table_infers_columns_when_schema_missing() -> None:
    tipsy_params_for_tsa = {
        1001: {
            "f": {"TBLno": 21, "AU": 1001, "SI": 18.0, "Density": 1200},
        }
    }
    out = build_tipsy_input_table(
        tipsy_params_for_tsa=tipsy_params_for_tsa,
        tipsy_params_columns=[],
        pd_module=pd,
        table_key="f",
    )

    assert list(out.columns) == ["TBLno", "AU", "SI", "Density"]
    assert int(out.iloc[0]["AU"]) == 1001


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


def test_build_btc_msyt_input_table_populates_natural_payload_for_mixed_share() -> None:
    planted_table = pd.DataFrame(
        {
            "AU": [23001],
            "BEC": ["IDFdk3"],
            "Proportion": [0.85],
            "Regen_Delay": [2],
            "Density": [1133],
            "SPP_1": ["PL"],
            "PCT_1": [62],
            "SPP_2": ["FD"],
            "PCT_2": [8],
            "GW_1": [3.0],
            "OAF1": [0.85],
            "OAF2": [0.95],
            "SI": [18.5],
        }
    )
    natural_table = pd.DataFrame(
        {
            "AU": [13001],
            "BEC": ["IDFdk3"],
            "Proportion": [0.15],
            "Regen_Delay": [2],
            "Density": [1133],
            "SPP_1": ["PL"],
            "PCT_1": [62],
            "SPP_2": ["AT"],
            "PCT_2": [17],
            "SPP_3": ["SX"],
            "PCT_3": [10],
            "OAF1": [0.85],
            "OAF2": [0.95],
            "SI": [16.5],
        }
    )

    out = build_btc_msyt_input_table(
        tipsy_table=planted_table,
        natural_tipsy_table=natural_table,
        pd_module=pd,
    )

    row = out.iloc[0].to_dict()
    assert row["feature_id"] == 23001
    assert row["planted_percent"] == 85
    assert row["planted_species1"] == "Pl"
    assert row["planted_density1"] == 702
    assert row["natural_species1"] == "Pl"
    assert row["natural_density1"] == 702
    assert row["natural_species2"] == "At"
    assert row["natural_density2"] == 193
    assert row["sx_si"] == 16.5
    assert row["pl_si"] == 18.5


def test_build_btc_msyt_input_table_rejects_mixed_share_without_natural_payload() -> (
    None
):
    planted_table = pd.DataFrame(
        {
            "AU": [23001],
            "BEC": ["IDFdk3"],
            "Proportion": [0.85],
            "Regen_Delay": [2],
            "Density": [1133],
            "SPP_1": ["PL"],
            "PCT_1": [62],
            "OAF1": [0.85],
            "OAF2": [0.95],
            "SI": [18.5],
        }
    )

    with pytest.raises(
        ValueError, match="missing a matching natural-side TIPSY payload"
    ):
        build_btc_msyt_input_table(tipsy_table=planted_table, pd_module=pd)


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


def test_write_tipsy_input_exports_writes_excel_only(tmp_path: Path) -> None:
    table = pd.DataFrame({"AU": [1001], "SI": [18.0]})
    prefix = str(tmp_path / "tipsy_params_tsa")
    excel_path = write_tipsy_input_exports(
        tipsy_table=table,
        tsa="08",
        tipsy_params_path_prefix=prefix,
    )
    assert excel_path == str(tmp_path / "tipsy_params_tsa08.xlsx")
    assert Path(excel_path).is_file()


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


def test_btc_indicator_bank_columns_returns_yield_and_age_core_bank() -> None:
    columns = btc_indicator_bank_columns("yield-and-age-core")
    assert [column.token for column in columns] == [
        "Year",
        "TotalAge",
        "BHAge",
        "StandAge",
        "HeightSindex",
        "Height",
        "Volume",
        "VPT",
        "HeightTassTop",
        "HeightTassMean",
        "HeightTassPredom",
    ]
    assert [column.header1_override for column in columns] == [
        "Year",
        "TotalAge",
        "BHAge",
        "StandAge",
        "HeightSindex",
        "Height",
        "Volume",
        "VPT",
        "HeightTassTop",
        "HeightTassMean",
        "HeightTassPredom",
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
    ]


def test_btc_indicator_bank_columns_can_opt_into_log_grades_all() -> None:
    columns = btc_indicator_bank_columns(
        "log-grades",
        options={"include_all_grades": True},
    )
    assert [column.token for column in columns][-1] == "Logs_Grade_All"
    assert [column.header1_override for column in columns][-1] == "Logs_Grade_All"


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


def test_wrap_btc_command_for_host_wraps_windows_executable_with_discovered_wine(
    monkeypatch,
) -> None:
    monkeypatch.setattr(tipsy_module, "_tipsy_is_windows_host", lambda: False)
    monkeypatch.setattr(
        tipsy_module,
        "find_wine_executable",
        lambda: "/usr/bin/wine64",
    )

    command = tipsy_module._wrap_btc_command_for_host(
        ("/opt/TIPSY/TIPSYbtc.exe", "/TSR"),
        env={},
    )

    assert command == ["/usr/bin/wine64", "/opt/TIPSY/TIPSYbtc.exe", "/TSR"]


def test_wrap_btc_command_for_host_preserves_native_commands_and_windows_behavior(
    monkeypatch,
) -> None:
    native_command = [sys.executable, "fake_btc.py", "/TSR"]
    monkeypatch.setattr(
        tipsy_module,
        "find_wine_executable",
        lambda: (_ for _ in ()).throw(AssertionError("Wine lookup was unexpected")),
    )

    monkeypatch.setattr(tipsy_module, "_tipsy_is_windows_host", lambda: False)
    assert tipsy_module._wrap_btc_command_for_host(native_command, env={}) == (
        native_command
    )

    monkeypatch.setattr(tipsy_module, "_tipsy_is_windows_host", lambda: True)
    assert tipsy_module._wrap_btc_command_for_host(
        ["/opt/TIPSY/TIPSYbtc.exe", "/TSR"],
        env={},
    ) == ["/opt/TIPSY/TIPSYbtc.exe", "/TSR"]


def test_wrap_btc_command_for_host_honors_wine_override_and_reports_missing_wine(
    monkeypatch,
) -> None:
    monkeypatch.setattr(tipsy_module, "_tipsy_is_windows_host", lambda: False)
    monkeypatch.setattr(
        tipsy_module,
        "find_wine_executable",
        lambda: (_ for _ in ()).throw(AssertionError("Discovery should be skipped")),
    )

    assert tipsy_module._wrap_btc_command_for_host(
        ["/opt/TIPSY/TIPSYbtc.exe"],
        env={DEFAULT_WINE_EXE_ENV: "  /custom/wine  "},
    ) == ["/custom/wine", "/opt/TIPSY/TIPSYbtc.exe"]

    monkeypatch.setattr(tipsy_module, "find_wine_executable", lambda: None)
    with pytest.raises(RuntimeError, match=f"{DEFAULT_WINE_EXE_ENV}"):
        tipsy_module._wrap_btc_command_for_host(
            ["/opt/TIPSY/TIPSYbtc.exe"],
            env={},
        )


def test_wrap_btc_command_for_host_prefers_runtime_wine_executable(
    monkeypatch,
) -> None:
    monkeypatch.setattr(tipsy_module, "_tipsy_is_windows_host", lambda: False)
    monkeypatch.setattr(
        tipsy_module,
        "find_wine_executable",
        lambda: (_ for _ in ()).throw(AssertionError("Discovery should be skipped")),
    )
    runtime_config = BTCRuntimeConfig(
        batch_tipsy_exe=None,
        wine_executable="/opt/custom-wine",
        wine_prefix=None,
        host_mode="wine",
    )

    command = tipsy_module._wrap_btc_command_for_host(
        ["/opt/TIPSY/TIPSYbtc.exe", "/TSR"],
        env={DEFAULT_WINE_EXE_ENV: "/env/wine"},
        runtime=runtime_config,
    )

    assert command == ["/opt/custom-wine", "/opt/TIPSY/TIPSYbtc.exe", "/TSR"]


def test_wrap_btc_command_for_host_wsl_interop_builds_powershell_carrier(
    monkeypatch,
) -> None:
    monkeypatch.setattr(tipsy_module, "_tipsy_is_windows_host", lambda: False)
    runtime_config = BTCRuntimeConfig(
        batch_tipsy_exe=None,
        wine_executable="powershell.exe",
        wine_prefix=None,
        host_mode="wsl-interop",
    )

    command = tipsy_module._wrap_btc_command_for_host(
        [
            "/mnt/c/Program Files/TIPSY 4.7/BTC/TIPSYbtc.exe",
            "/TSR",
            "MSYT.csv",
            "MSYT_output.csv",
            "MSYT_error.csv",
        ],
        env={},
        runtime=runtime_config,
    )

    assert command == [
        "powershell.exe",
        "-NoProfile",
        "-Command",
        "& 'C:\\Program Files\\TIPSY 4.7\\BTC\\TIPSYbtc.exe' "
        "'/TSR' 'MSYT.csv' 'MSYT_output.csv' 'MSYT_error.csv'",
    ]


def test_wrap_btc_command_for_host_wsl_interop_explicit_cmd_carrier_uses_cmd_argv(
    monkeypatch,
) -> None:
    """Explicit ``cmd.exe`` carrier yields cmd-style argv, not PowerShell."""
    monkeypatch.setattr(tipsy_module, "_tipsy_is_windows_host", lambda: False)
    runtime_config = BTCRuntimeConfig(
        batch_tipsy_exe=None,
        wine_executable="cmd.exe",
        wine_prefix=None,
        host_mode="wsl-interop",
    )

    command = tipsy_module._wrap_btc_command_for_host(
        ["/mnt/c/Program Files/TIPSY 4.7/BTC/TIPSYbtc.exe", "/TSR"],
        env={},
        runtime=runtime_config,
    )

    assert command == [
        "cmd.exe",
        "/c",
        '"C:\\Program Files\\TIPSY 4.7\\BTC\\TIPSYbtc.exe" /TSR',
    ]


def test_wrap_btc_command_for_host_wsl_interop_falls_back_to_powershell_carrier(
    monkeypatch,
) -> None:
    monkeypatch.setattr(tipsy_module, "_tipsy_is_windows_host", lambda: False)
    monkeypatch.setattr(
        tipsy_module.shutil,
        "which",
        lambda name: "/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe"
        if name == "powershell.exe"
        else None,
    )
    runtime_config = BTCRuntimeConfig(
        batch_tipsy_exe=None,
        wine_executable=None,
        wine_prefix=None,
        host_mode="wsl-interop",
    )

    command = tipsy_module._wrap_btc_command_for_host(
        ["/mnt/c/Program Files/TIPSY 4.7/BTC/TIPSYbtc.exe", "/TSR"],
        env={},
        runtime=runtime_config,
    )

    assert command == [
        "/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe",
        "-NoProfile",
        "-Command",
        "& 'C:\\Program Files\\TIPSY 4.7\\BTC\\TIPSYbtc.exe' '/TSR'",
    ]


def test_wrap_btc_command_for_host_wsl_interop_explicit_uppercase_cmd_carrier_uses_cmd_argv(
    monkeypatch,
) -> None:
    """Explicit ``CMD.EXE`` (uppercase) also yields cmd-style argv."""
    monkeypatch.setattr(tipsy_module, "_tipsy_is_windows_host", lambda: False)
    runtime_config = BTCRuntimeConfig(
        batch_tipsy_exe=None,
        wine_executable="CMD.EXE",
        wine_prefix=None,
        host_mode="wsl-interop",
    )

    command = tipsy_module._wrap_btc_command_for_host(
        ["/mnt/c/Program Files/TIPSY 4.7/BTC/TIPSYbtc.exe", "/TSR"],
        env={},
        runtime=runtime_config,
    )

    assert command == [
        "CMD.EXE",
        "/c",
        '"C:\\Program Files\\TIPSY 4.7\\BTC\\TIPSYbtc.exe" /TSR',
    ]
    assert "-NoProfile" not in command
    assert "-Command" not in command


def test_wrap_btc_command_for_host_wsl_interop_explicit_absolute_cmd_carrier_uses_cmd_argv(
    monkeypatch,
) -> None:
    """Absolute-path ``cmd.exe`` carrier branches on basename to cmd-style."""
    monkeypatch.setattr(tipsy_module, "_tipsy_is_windows_host", lambda: False)
    runtime_config = BTCRuntimeConfig(
        batch_tipsy_exe=None,
        wine_executable="/mnt/c/Windows/System32/cmd.exe",
        wine_prefix=None,
        host_mode="wsl-interop",
    )

    command = tipsy_module._wrap_btc_command_for_host(
        ["/mnt/c/Program Files/TIPSY 4.7/BTC/TIPSYbtc.exe", "/TSR"],
        env={},
        runtime=runtime_config,
    )

    assert command == [
        "/mnt/c/Windows/System32/cmd.exe",
        "/c",
        '"C:\\Program Files\\TIPSY 4.7\\BTC\\TIPSYbtc.exe" /TSR',
    ]
    assert "-NoProfile" not in command
    assert "-Command" not in command


def test_wrap_btc_command_for_host_wsl_interop_translates_absolute_mnt_args(
    monkeypatch,
) -> None:
    monkeypatch.setattr(tipsy_module, "_tipsy_is_windows_host", lambda: False)
    runtime_config = BTCRuntimeConfig(
        batch_tipsy_exe=None,
        wine_executable="powershell.exe",
        wine_prefix=None,
        host_mode="wsl-interop",
    )

    command = tipsy_module._wrap_btc_command_for_host(
        [
            "/mnt/c/Program Files/TIPSY 4.7/BTC/TIPSYbtc.exe",
            "/TSR",
            "/mnt/c/femic/scratch/MSYT.csv",
            "MSYT_output.csv",
        ],
        env={},
        runtime=runtime_config,
    )

    assert command == [
        "powershell.exe",
        "-NoProfile",
        "-Command",
        "& 'C:\\Program Files\\TIPSY 4.7\\BTC\\TIPSYbtc.exe' "
        "'/TSR' 'C:\\femic\\scratch\\MSYT.csv' 'MSYT_output.csv'",
    ]


def test_wrap_btc_command_for_host_wsl_interop_falls_back_to_cmd_carrier(
    monkeypatch,
) -> None:
    monkeypatch.setattr(tipsy_module, "_tipsy_is_windows_host", lambda: False)
    monkeypatch.setattr(
        tipsy_module.shutil,
        "which",
        lambda name: "/mnt/c/Windows/System32/cmd.exe"
        if name == "cmd.exe"
        else None,
    )
    runtime_config = BTCRuntimeConfig(
        batch_tipsy_exe=None,
        wine_executable=None,
        wine_prefix=None,
        host_mode="wsl-interop",
    )

    command = tipsy_module._wrap_btc_command_for_host(
        ["/mnt/c/Program Files/TIPSY 4.7/BTC/TIPSYbtc.exe", "/TSR"],
        env={},
        runtime=runtime_config,
    )

    assert command == [
        "/mnt/c/Windows/System32/cmd.exe",
        "/c",
        '"C:\\Program Files\\TIPSY 4.7\\BTC\\TIPSYbtc.exe" /TSR',
    ]


def test_wrap_btc_command_for_host_wsl_interop_requires_carrier(
    monkeypatch,
) -> None:
    monkeypatch.setattr(tipsy_module, "_tipsy_is_windows_host", lambda: False)
    monkeypatch.setattr(tipsy_module.shutil, "which", lambda _name: None)
    runtime_config = BTCRuntimeConfig(
        batch_tipsy_exe=None,
        wine_executable=None,
        wine_prefix=None,
        host_mode="wsl-interop",
    )

    with pytest.raises(RuntimeError, match="powershell.exe"):
        tipsy_module._wrap_btc_command_for_host(
            ["/mnt/c/Program Files/TIPSY 4.7/BTC/TIPSYbtc.exe", "/TSR"],
            env={},
            runtime=runtime_config,
        )


@pytest.mark.parametrize(
    "non_carrier",
    ["/usr/bin/wine", "bash.exe", "wine64"],
)
def test_validate_btc_run_prerequisites_wsl_interop_rejects_non_carrier(
    non_carrier: str,
) -> None:
    """m2: interop validation rejects a wine_executable that is not a carrier."""
    runtime_config = BTCRuntimeConfig(
        batch_tipsy_exe=None,
        wine_executable=non_carrier,
        wine_prefix=None,
        host_mode="wsl-interop",
    )
    discovery = tipsy_module.BTCRuntimeDiscovery(
        executable_path=Path("/mnt/c/femic/TIPSYbtc.exe"),
        source="wineprefix:/mnt/c/femic",
    )
    with pytest.raises(RuntimeError, match="wsl-interop mode carrier must be"):
        tipsy_module._validate_btc_run_prerequisites(
            runtime=runtime_config,
            discovery=discovery,
            scratch_root=Path("/mnt/c/femic/scratch"),
        )


@pytest.mark.parametrize(
    "carrier",
    [
        "powershell.exe",
        "cmd.exe",
        "PowerShell.exe",
        "CMD.EXE",
        "/mnt/c/Windows/System32/powershell.exe",
    ],
)
def test_validate_btc_run_prerequisites_wsl_interop_accepts_carrier(
    carrier: str,
) -> None:
    """m2: interop validation accepts powershell.exe/cmd.exe case-insensitively."""
    runtime_config = BTCRuntimeConfig(
        batch_tipsy_exe=None,
        wine_executable=carrier,
        wine_prefix=None,
        host_mode="wsl-interop",
    )
    discovery = tipsy_module.BTCRuntimeDiscovery(
        executable_path=Path("/mnt/c/femic/TIPSYbtc.exe"),
        source="wineprefix:/mnt/c/femic",
    )
    tipsy_module._validate_btc_run_prerequisites(
        runtime=runtime_config,
        discovery=discovery,
        scratch_root=Path("/mnt/c/femic/scratch"),
    )


def test_require_windows_visible_working_dir_accepts_interop_paths() -> None:
    tipsy_module._require_windows_visible_working_dir(
        Path("/mnt/c/femic/scratch/work")
    )
    tipsy_module._require_windows_visible_working_dir(Path(r"C:\femic\scratch\work"))
    with pytest.raises(RuntimeError, match="scratch-dir"):
        tipsy_module._require_windows_visible_working_dir(
            Path("/home/gep/scratch/work")
        )


def test_apply_xvfb_wrap_wraps_headless_wine_command(
    monkeypatch,
) -> None:
    monkeypatch.setattr(tipsy_module, "is_headless", lambda env: True)
    monkeypatch.setattr(tipsy_module, "find_xvfb_run", lambda: "/opt/xvfb-run")
    runtime_config = BTCRuntimeConfig(
        batch_tipsy_exe=None,
        wine_executable="wine",
        wine_prefix=None,
        host_mode="wine",
        use_xvfb=True,
    )

    command = tipsy_module._apply_xvfb_wrap(
        ["wine", "/opt/TIPSY/TIPSYbtc.exe", "/TSR"],
        runtime=runtime_config,
        env={},
    )

    assert command == ["/opt/xvfb-run", "-a", "wine", "/opt/TIPSY/TIPSYbtc.exe", "/TSR"]


def test_apply_xvfb_wrap_uses_runtime_xvfb_executable(
    monkeypatch,
) -> None:
    monkeypatch.setattr(tipsy_module, "is_headless", lambda env: True)
    runtime_config = BTCRuntimeConfig(
        batch_tipsy_exe=None,
        wine_executable="wine",
        wine_prefix=None,
        host_mode="wine",
        use_xvfb=True,
        xvfb_executable="/custom/xvfb-run",
    )

    command = tipsy_module._apply_xvfb_wrap(
        ["wine", "/opt/TIPSY/TIPSYbtc.exe", "/TSR"],
        runtime=runtime_config,
        env={},
    )

    assert command[0] == "/custom/xvfb-run"


def test_apply_xvfb_wrap_skips_non_wine_modes(
    monkeypatch,
) -> None:
    monkeypatch.setattr(tipsy_module, "is_headless", lambda env: True)
    runtime_config = BTCRuntimeConfig(
        batch_tipsy_exe=None,
        wine_executable=None,
        wine_prefix=None,
        host_mode="windows",
        use_xvfb=True,
    )

    command = tipsy_module._apply_xvfb_wrap(
        ["C:\\Program Files\\TIPSY 4.7\\BTC\\TIPSYbtc.exe", "/TSR"],
        runtime=runtime_config,
        env={},
    )

    assert command == ["C:\\Program Files\\TIPSY 4.7\\BTC\\TIPSYbtc.exe", "/TSR"]


def test_apply_xvfb_wrap_skips_non_headless_wine_runs(
    monkeypatch,
) -> None:
    monkeypatch.setattr(tipsy_module, "is_headless", lambda env: False)
    runtime_config = BTCRuntimeConfig(
        batch_tipsy_exe=None,
        wine_executable="wine",
        wine_prefix=None,
        host_mode="wine",
        use_xvfb=True,
    )

    command = tipsy_module._apply_xvfb_wrap(
        ["wine", "/opt/TIPSY/TIPSYbtc.exe", "/TSR"],
        runtime=runtime_config,
        env={},
    )

    assert command == ["wine", "/opt/TIPSY/TIPSYbtc.exe", "/TSR"]


def test_apply_xvfb_wrap_raises_when_xvfb_missing(
    monkeypatch,
) -> None:
    monkeypatch.setattr(tipsy_module, "is_headless", lambda env: True)
    monkeypatch.setattr(tipsy_module, "find_xvfb_run", lambda: None)
    runtime_config = BTCRuntimeConfig(
        batch_tipsy_exe=None,
        wine_executable="wine",
        wine_prefix=None,
        host_mode="wine",
        use_xvfb=True,
        xvfb_executable=None,
    )

    with pytest.raises(RuntimeError, match="xvfb-run"):
        tipsy_module._apply_xvfb_wrap(
            ["wine", "/opt/TIPSY/TIPSYbtc.exe", "/TSR"],
            runtime=runtime_config,
            env={},
        )


def test_apply_xvfb_wrap_leaves_disabled_runs_untouched(
    monkeypatch,
) -> None:
    monkeypatch.setattr(tipsy_module, "is_headless", lambda env: True)
    runtime_config = BTCRuntimeConfig(
        batch_tipsy_exe=None,
        wine_executable="wine",
        wine_prefix=None,
        host_mode="wine",
        use_xvfb=False,
    )

    command = tipsy_module._apply_xvfb_wrap(
        ["wine", "/opt/TIPSY/TIPSYbtc.exe", "/TSR"],
        runtime=runtime_config,
        env={},
    )

    assert command == ["wine", "/opt/TIPSY/TIPSYbtc.exe", "/TSR"]


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


def test_run_btc_cli_wraps_windows_executable_and_records_wine_command(
    monkeypatch, tmp_path: Path
) -> None:
    input_csv = tmp_path / "MSYT.csv"
    input_csv.write_text("feature_id\n1\n", encoding="utf-8")
    fake_btc = tmp_path / "fake_btc.exe"
    fake_btc.write_text(
        "from pathlib import Path\n"
        "import os\n"
        "import sys\n"
        "mode, input_name, output_name, error_name = sys.argv[1:5]\n"
        "Path(output_name).write_text(os.environ['WINEPREFIX'], encoding='utf-8')\n"
        "Path(error_name).write_text('warnings,errors\\n0,0\\n', encoding='utf-8')\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(tipsy_module, "_tipsy_is_windows_host", lambda: False)
    monkeypatch.setattr(tipsy_module, "find_wine_executable", lambda: sys.executable)
    wine_prefix = tmp_path / "wine-prefix"

    result = run_btc_cli(
        input_csv=input_csv,
        mode="TSR",
        executable_path=fake_btc,
        scratch_root=tmp_path / "scratch",
        log_dir=tmp_path / "logs",
        run_id="btc_wine_command",
        wine_executable=sys.executable,
        env={"WINEPREFIX": str(wine_prefix)},
    )

    assert result.command[:2] == (sys.executable, str(fake_btc.resolve()))
    assert result.output_csv_path.read_text(encoding="utf-8") == str(wine_prefix)
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["command"] == list(result.command)


def test_run_btc_cli_records_runtime_fields_in_manifest_and_result(
    monkeypatch, tmp_path: Path
) -> None:
    input_csv = tmp_path / "MSYT.csv"
    input_csv.write_text("feature_id\n1\n", encoding="utf-8")
    fake_btc = tmp_path / "fake_btc.exe"
    fake_btc.write_text(
        "from pathlib import Path\n"
        "import sys\n"
        "mode, input_name, output_name, error_name = sys.argv[1:5]\n"
        "Path(output_name).write_text('feature_id,MVcon_0\\n1,2\\n', encoding='utf-8')\n"
        "Path(error_name).write_text('warnings,errors\\n0,0\\n', encoding='utf-8')\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(tipsy_module, "_tipsy_is_windows_host", lambda: False)
    monkeypatch.setattr(tipsy_module, "find_wine_executable", lambda: sys.executable)
    wine_prefix = tmp_path / "wine-prefix"

    result = run_btc_cli(
        input_csv=input_csv,
        mode="TSR",
        executable_path=fake_btc,
        scratch_root=tmp_path / "scratch",
        log_dir=tmp_path / "logs",
        run_id="btc_runtime_fields",
        wine_prefix=wine_prefix,
        wine_executable=sys.executable,
        use_xvfb=False,
        host_mode="wine",
        env={},
    )

    assert result.host_mode == "wine"
    assert result.wine_prefix == str(wine_prefix.resolve())
    assert result.wine_executable == sys.executable
    assert result.use_xvfb is False
    assert result.command[:2] == (sys.executable, str(fake_btc.resolve()))
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["host_mode"] == "wine"
    assert manifest["wine_prefix"] == str(wine_prefix.resolve())
    assert manifest["wine_executable"] == sys.executable
    assert manifest["use_xvfb"] is False
    assert manifest["command"] == list(result.command)


def test_run_btc_cli_uses_supplied_runtime_config_without_re_resolution(
    monkeypatch, tmp_path: Path
) -> None:
    input_csv = tmp_path / "MSYT.csv"
    input_csv.write_text("feature_id\n1\n", encoding="utf-8")
    fake_btc = tmp_path / "fake_btc.exe"
    fake_btc.write_text(
        "from pathlib import Path\n"
        "import sys\n"
        "mode, input_name, output_name, error_name = sys.argv[1:5]\n"
        "Path(output_name).write_text('feature_id,MVcon_0\\n1,2\\n', encoding='utf-8')\n"
        "Path(error_name).write_text('warnings,errors\\n0,0\\n', encoding='utf-8')\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(tipsy_module, "_tipsy_is_windows_host", lambda: False)
    monkeypatch.setattr(tipsy_module, "find_wine_executable", lambda: sys.executable)
    monkeypatch.setattr(
        tipsy_module,
        "resolve_btc_runtime_config",
        lambda **kwargs: (_ for _ in ()).throw(
            AssertionError("resolution should be skipped when config is supplied")
        ),
    )
    wine_prefix = tmp_path / "wine-prefix"
    supplied_runtime = BTCRuntimeConfig(
        batch_tipsy_exe=None,
        wine_executable=sys.executable,
        wine_prefix=wine_prefix,
        host_mode="wine",
        use_xvfb=False,
    )

    result = run_btc_cli(
        input_csv=input_csv,
        mode="TSR",
        executable_path=fake_btc,
        scratch_root=tmp_path / "scratch",
        log_dir=tmp_path / "logs",
        run_id="btc_supplied_runtime",
        btc_runtime_config=supplied_runtime,
        env={},
    )

    assert result.host_mode == "wine"
    assert result.wine_prefix == str(wine_prefix.resolve())
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["host_mode"] == "wine"
    assert manifest["wine_prefix"] == str(wine_prefix.resolve())


def test_run_btc_cli_rejects_conflicting_runtime_config(
    monkeypatch, tmp_path: Path
) -> None:
    input_csv = tmp_path / "MSYT.csv"
    input_csv.write_text("feature_id\n1\n", encoding="utf-8")
    fake_btc = tmp_path / "fake_btc.exe"
    fake_btc.write_text("stub", encoding="utf-8")
    monkeypatch.setattr(tipsy_module, "_tipsy_is_windows_host", lambda: False)
    supplied_runtime = BTCRuntimeConfig(
        batch_tipsy_exe=None,
        wine_executable=sys.executable,
        wine_prefix=None,
        host_mode="wine",
        use_xvfb=False,
    )

    with pytest.raises(BTCRuntimeConfigError, match="host_mode"):
        run_btc_cli(
            input_csv=input_csv,
            mode="TSR",
            executable_path=fake_btc,
            scratch_root=tmp_path / "scratch",
            log_dir=tmp_path / "logs",
            run_id="btc_conflicting_runtime",
            btc_runtime_config=supplied_runtime,
            host_mode="windows",
            env={},
        )


def test_run_btc_cli_rejects_conflicting_wine_prefix_option(
    monkeypatch, tmp_path: Path
) -> None:
    input_csv = tmp_path / "MSYT.csv"
    input_csv.write_text("feature_id\n1\n", encoding="utf-8")
    fake_btc = tmp_path / "fake_btc.exe"
    fake_btc.write_text("stub", encoding="utf-8")
    monkeypatch.setattr(tipsy_module, "_tipsy_is_windows_host", lambda: False)
    supplied_runtime = BTCRuntimeConfig(
        batch_tipsy_exe=None,
        wine_executable=sys.executable,
        wine_prefix=tmp_path / "configured-prefix",
        host_mode="wine",
        use_xvfb=False,
    )

    with pytest.raises(BTCRuntimeConfigError, match="wine_prefix"):
        run_btc_cli(
            input_csv=input_csv,
            mode="TSR",
            executable_path=fake_btc,
            scratch_root=tmp_path / "scratch",
            log_dir=tmp_path / "logs",
            run_id="btc_conflicting_prefix",
            btc_runtime_config=supplied_runtime,
            wine_prefix=tmp_path / "different-prefix",
            env={},
        )


def test_run_btc_cli_xvfb_wraps_headless_wine_command(
    monkeypatch, tmp_path: Path
) -> None:
    input_csv = tmp_path / "MSYT.csv"
    input_csv.write_text("feature_id\n1\n", encoding="utf-8")
    fake_btc = tmp_path / "fake_btc.exe"
    fake_btc.write_text(
        "from pathlib import Path\n"
        "import sys\n"
        "mode, input_name, output_name, error_name = sys.argv[1:5]\n"
        "Path(output_name).write_text('feature_id,MVcon_0\\n1,2\\n', encoding='utf-8')\n"
        "Path(error_name).write_text('warnings,errors\\n0,0\\n', encoding='utf-8')\n",
        encoding="utf-8",
    )
    fake_xvfb = tmp_path / "fake_xvfb_run"
    fake_xvfb.write_text(
        "#!/bin/sh\nif [ \"$1\" = \"-a\" ]; then shift; fi\nexec \"$@\"\n",
        encoding="utf-8",
    )
    fake_xvfb.chmod(0o755)
    monkeypatch.setattr(tipsy_module, "_tipsy_is_windows_host", lambda: False)
    monkeypatch.setattr(tipsy_module, "find_wine_executable", lambda: sys.executable)
    monkeypatch.setattr(tipsy_module, "is_headless", lambda env: True)
    wine_prefix = tmp_path / "wine-prefix"
    runtime_config = BTCRuntimeConfig(
        batch_tipsy_exe=None,
        wine_executable=sys.executable,
        wine_prefix=wine_prefix,
        host_mode="wine",
        use_xvfb=True,
        xvfb_executable=str(fake_xvfb),
    )

    result = run_btc_cli(
        input_csv=input_csv,
        mode="TSR",
        executable_path=fake_btc,
        scratch_root=tmp_path / "scratch",
        log_dir=tmp_path / "logs",
        run_id="btc_xvfb",
        btc_runtime_config=runtime_config,
        env={},
    )

    assert result.exit_code == 0
    assert result.command[0] == str(fake_xvfb)
    assert result.command[1] == "-a"
    assert result.command[2:4] == (sys.executable, str(fake_btc.resolve()))
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["command"] == list(result.command)
    assert manifest["host_mode"] == "wine"
    assert manifest["use_xvfb"] is True


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


def test_run_btc_cli_wsl_interop_full_run_with_windows_visible_scratch(
    monkeypatch, tmp_path: Path
) -> None:
    """End-to-end wsl-interop run: powershell carrier, WINEPREFIX popped, no /mnt writes."""
    # Make the WINEPREFIX-popping assertion meaningful: interop must strip a
    # non-empty WINEPREFIX from the child env, not a no-op empty lookup.
    monkeypatch.setenv("WINEPREFIX", "/tmp/fake-wineprefix-for-interop-test")
    input_csv = tmp_path / "MSYT.csv"
    input_csv.write_text("feature_id\n1\n", encoding="utf-8")
    fake_powershell = tmp_path / "powershell.exe"
    fake_powershell.write_text(
        "#!/usr/bin/env python3\n"
        "import os, shlex, sys\n"
        "from pathlib import Path\n"
        "tokens = shlex.split(sys.argv[3])\n"
        "exe, mode, input_name, output_name, error_name = tokens[1:6]\n"
        "Path(output_name).write_text('WINEPREFIX=' + os.environ.get('WINEPREFIX', '__UNSET__') + '\\n', encoding='utf-8')\n"
        "Path(error_name).write_text('warnings,errors\\n0,0\\n', encoding='utf-8')\n"
        "sys.exit(0)\n",
        encoding="utf-8",
    )
    fake_powershell.chmod(0o755)
    monkeypatch.setattr(tipsy_module, "_tipsy_is_windows_host", lambda: False)
    monkeypatch.setattr(
        tipsy_module,
        "resolve_btc_executable",
        lambda **kwargs: tipsy_module.BTCRuntimeDiscovery(
            executable_path=Path("/mnt/c/femic/TIPSYbtc.exe"),
            source="wineprefix:/mnt/c/femic",
        ),
    )
    work_dir = tmp_path / "work"
    work_dir.mkdir(parents=True, exist_ok=True)

    def _fake_prepare(**kwargs):
        return types.SimpleNamespace(
            working_dir=work_dir,
            executable_path=kwargs["executable_path"],
            staged_input_csv=work_dir / "MSYT.csv",
            install_root=Path("/mnt/c/femic"),
            copied_install=False,
            uses_live_overlay=False,
            report_template_path=None,
        )

    monkeypatch.setattr(tipsy_module, "prepare_btc_runtime", _fake_prepare)
    runtime_config = BTCRuntimeConfig(
        batch_tipsy_exe=None,
        wine_executable=str(fake_powershell),
        wine_prefix=None,
        host_mode="wsl-interop",
        use_xvfb=False,
    )

    result = run_btc_cli(
        input_csv=input_csv,
        mode="TSR",
        scratch_root=Path("/mnt/c/femic/scratch"),
        log_dir=tmp_path / "logs",
        run_id="btc_wsl_interop",
        btc_runtime_config=runtime_config,
        env={},
    )

    assert result.exit_code == 0
    assert result.host_mode == "wsl-interop"
    assert result.wine_prefix is None
    assert tuple(result.command) == (
        str(fake_powershell),
        "-NoProfile",
        "-Command",
        "& 'C:\\femic\\TIPSYbtc.exe' '/TSR' 'MSYT.csv' 'MSYT_output.csv' 'MSYT_error.csv'",
    )
    assert result.output_csv_path.read_text(encoding="utf-8") == (
        "WINEPREFIX=__UNSET__\n"
    )
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["host_mode"] == "wsl-interop"
    assert manifest["command"] == list(result.command)


def test_btc_runtime_prefix_candidates_ordering_env_beats_discovered(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """m5: FEMIC_BTC_WINEPREFIX > WINEPREFIX > discovered prefix, no re-resolution."""
    discovered_prefix = tmp_path / "discovered"
    monkeypatch.setattr(
        tipsy_module,
        "resolve_btc_runtime_config",
        lambda **kwargs: BTCRuntimeConfig(
            batch_tipsy_exe=None,
            wine_executable=None,
            wine_prefix=discovered_prefix,
            host_mode="wine",
            use_xvfb=False,
        ),
    )
    candidates = tipsy_module._btc_runtime_prefix_candidates(
        {
            FEMIC_BTC_WINEPREFIX: str(tmp_path / "from-femic-env"),
            "WINEPREFIX": str(tmp_path / "from-wine-env"),
        }
    )
    assert candidates == [
        tmp_path / "from-femic-env",
        tmp_path / "from-wine-env",
        discovered_prefix,
    ]


def test_resolve_btc_executable_prefix_ordering_and_windows_default(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Ordering: FEMIC_BTC_WINEPREFIX > WINEPREFIX > discovered prefix > C:\\ default."""
    discovered_prefix = tmp_path / "discovered"
    monkeypatch.setattr(
        tipsy_module,
        "resolve_btc_runtime_config",
        lambda **kwargs: BTCRuntimeConfig(
            batch_tipsy_exe=None,
            wine_executable=None,
            wine_prefix=discovered_prefix,
            host_mode="wine",
            use_xvfb=False,
        ),
    )
    # No prefix install exists -> nothing to run; the C:\ default is only a
    # native-Windows fallback, so discovery fails loudly on POSIX.
    with pytest.raises(FileNotFoundError, match="Could not resolve BatchTIPSY"):
        resolve_btc_executable(env={})

    # A discovered-prefix install wins over the C:\ default.
    discovered_install = (
        discovered_prefix
        / "drive_c"
        / "Program Files"
        / "TIPSY 4.7"
        / "BTC"
        / "TIPSYbtc.exe"
    )
    discovered_install.parent.mkdir(parents=True)
    discovered_install.write_text("stub", encoding="utf-8")
    discovered = resolve_btc_executable(env={})
    assert discovered.executable_path == discovered_install.resolve()
    assert discovered.source == f"wineprefix:{discovered_prefix}"

    # FEMIC_BTC_WINEPREFIX install wins over WINEPREFIX install, and both
    # beat the discovered prefix.
    femic_install = (
        tmp_path
        / "femic-env"
        / "drive_c"
        / "Program Files"
        / "TIPSY 4.7"
        / "BTC"
        / "TIPSYbtc.exe"
    )
    femic_install.parent.mkdir(parents=True)
    femic_install.write_text("stub", encoding="utf-8")
    wine_install = (
        tmp_path
        / "wine-env"
        / "drive_c"
        / "Program Files"
        / "TIPSY 4.7"
        / "BTC"
        / "TIPSYbtc.exe"
    )
    wine_install.parent.mkdir(parents=True)
    wine_install.write_text("stub", encoding="utf-8")
    discovered = resolve_btc_executable(
        env={
            FEMIC_BTC_WINEPREFIX: str(tmp_path / "femic-env"),
            "WINEPREFIX": str(tmp_path / "wine-env"),
        }
    )
    assert discovered.executable_path == femic_install.resolve()
    assert discovered.source == f"wineprefix:{tmp_path / 'femic-env'}"

    # WINEPREFIX install wins over the discovered prefix when no FEMIC env
    # variable is set.
    discovered = resolve_btc_executable(
        env={"WINEPREFIX": str(tmp_path / "wine-env")}
    )
    assert discovered.executable_path == wine_install.resolve()
    assert discovered.source == f"wineprefix:{tmp_path / 'wine-env'}"


def test_assert_btc_runtime_config_matches_rejects_wine_executable_conflict() -> None:
    runtime_config = BTCRuntimeConfig(
        batch_tipsy_exe=None,
        wine_executable="/opt/wine",
        wine_prefix=None,
        host_mode="wine",
        use_xvfb=False,
    )
    with pytest.raises(BTCRuntimeConfigError, match="wine_executable"):
        tipsy_module._assert_btc_runtime_config_matches(
            runtime=runtime_config,
            executable_path=None,
            wine_prefix=None,
            wine_executable="/different/wine",
            use_xvfb=None,
            host_mode=None,
        )


def test_assert_btc_runtime_config_matches_rejects_use_xvfb_conflict() -> None:
    runtime_config = BTCRuntimeConfig(
        batch_tipsy_exe=None,
        wine_executable=None,
        wine_prefix=None,
        host_mode="wine",
        use_xvfb=False,
    )
    with pytest.raises(BTCRuntimeConfigError, match="use_xvfb"):
        tipsy_module._assert_btc_runtime_config_matches(
            runtime=runtime_config,
            executable_path=None,
            wine_prefix=None,
            wine_executable=None,
            use_xvfb=True,
            host_mode=None,
        )


def test_assert_btc_runtime_config_matches_rejects_option_without_config_value() -> None:
    runtime_config = BTCRuntimeConfig(
        batch_tipsy_exe=None,
        wine_executable=None,
        wine_prefix=None,
        host_mode="wine",
        use_xvfb=False,
    )
    with pytest.raises(BTCRuntimeConfigError, match="wine_prefix"):
        tipsy_module._assert_btc_runtime_config_matches(
            runtime=runtime_config,
            executable_path=None,
            wine_prefix=Path("/x"),
            wine_executable=None,
            use_xvfb=None,
            host_mode=None,
        )
    with pytest.raises(BTCRuntimeConfigError, match="wine_executable"):
        tipsy_module._assert_btc_runtime_config_matches(
            runtime=runtime_config,
            executable_path=None,
            wine_prefix=None,
            wine_executable="/opt/wine",
            use_xvfb=None,
            host_mode=None,
        )
    # Contrast: the executable_path/batch_tipsy_exe pair only fires when both
    # sides are set and disagree, so a one-sided option is accepted.
    tipsy_module._assert_btc_runtime_config_matches(
        runtime=runtime_config,
        executable_path=Path("/x/TIPSYbtc.exe"),
        wine_prefix=None,
        wine_executable=None,
        use_xvfb=None,
        host_mode=None,
    )


def test_assert_btc_runtime_config_matches_expanduser_tilde_match(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """m4: ~-relative options match an already-expanded config path."""
    monkeypatch.setenv("HOME", str(tmp_path))
    runtime_config = BTCRuntimeConfig(
        batch_tipsy_exe=tmp_path / "TIPSYbtc.exe",
        wine_executable=None,
        wine_prefix=tmp_path / "prefix",
        host_mode="wine",
        use_xvfb=False,
    )
    tipsy_module._assert_btc_runtime_config_matches(
        runtime=runtime_config,
        executable_path=Path("~/TIPSYbtc.exe"),
        wine_prefix=Path("~/prefix"),
        wine_executable=None,
        use_xvfb=None,
        host_mode=None,
    )


def test_assert_btc_runtime_config_matches_expanduser_mismatch_raises(
    tmp_path: Path,
) -> None:
    """m4: expanduser-normalized mismatch still fails fast."""
    runtime_config = BTCRuntimeConfig(
        batch_tipsy_exe=tmp_path / "a.exe",
        wine_executable=None,
        wine_prefix=None,
        host_mode="wine",
        use_xvfb=False,
    )
    with pytest.raises(BTCRuntimeConfigError, match="executable_path"):
        tipsy_module._assert_btc_runtime_config_matches(
            runtime=runtime_config,
            executable_path=tmp_path / "b.exe",
            wine_prefix=None,
            wine_executable=None,
            use_xvfb=None,
            host_mode=None,
        )


def test_run_btc_cli_rejects_conflicting_executable_path_option(
    monkeypatch, tmp_path: Path
) -> None:
    """M2: executable_path must agree with a supplied trusted config."""
    input_csv = tmp_path / "MSYT.csv"
    input_csv.write_text("feature_id\n1\n", encoding="utf-8")
    fake_btc = tmp_path / "fake_btc.exe"
    fake_btc.write_text("stub", encoding="utf-8")
    monkeypatch.setattr(tipsy_module, "_tipsy_is_windows_host", lambda: False)
    supplied_runtime = BTCRuntimeConfig(
        batch_tipsy_exe=tmp_path / "configured.exe",
        wine_executable=None,
        wine_prefix=None,
        host_mode="wine",
        use_xvfb=False,
    )

    with pytest.raises(BTCRuntimeConfigError, match="executable_path"):
        run_btc_cli(
            input_csv=input_csv,
            mode="TSR",
            executable_path=tmp_path / "different.exe",
            scratch_root=tmp_path / "scratch",
            log_dir=tmp_path / "logs",
            run_id="btc_conflicting_exe",
            btc_runtime_config=supplied_runtime,
            env={},
        )


def test_run_btc_cli_wsl_interop_validates_before_staging(
    monkeypatch, tmp_path: Path
) -> None:
    """M3: an unmappable interop executable fails before prepare_btc_runtime."""
    input_csv = tmp_path / "MSYT.csv"
    input_csv.write_text("feature_id\n1\n", encoding="utf-8")
    monkeypatch.setattr(tipsy_module, "_tipsy_is_windows_host", lambda: False)
    monkeypatch.setattr(
        tipsy_module,
        "resolve_btc_executable",
        lambda **kwargs: tipsy_module.BTCRuntimeDiscovery(
            executable_path=Path("/home/gep/TIPSYbtc.exe"),
            source="explicit",
        ),
    )
    monkeypatch.setattr(
        tipsy_module,
        "prepare_btc_runtime",
        lambda **kwargs: (_ for _ in ()).throw(
            AssertionError("staging must not start on a guaranteed failure")
        ),
    )
    runtime_config = BTCRuntimeConfig(
        batch_tipsy_exe=None,
        wine_executable="powershell.exe",
        wine_prefix=None,
        host_mode="wsl-interop",
        use_xvfb=False,
    )

    with pytest.raises(RuntimeError, match=DEFAULT_BATCHTIPSY_EXE_ENV):
        run_btc_cli(
            input_csv=input_csv,
            mode="TSR",
            scratch_root=tmp_path / "scratch",
            log_dir=tmp_path / "logs",
            run_id="btc_wsl_interop_pre",
            btc_runtime_config=runtime_config,
            env={},
        )


def test_run_btc_cli_windows_mode_on_posix_validates_before_staging(
    monkeypatch, tmp_path: Path
) -> None:
    """M3: windows mode on POSIX fails before prepare_btc_runtime."""
    input_csv = tmp_path / "MSYT.csv"
    input_csv.write_text("feature_id\n1\n", encoding="utf-8")
    fake_btc = tmp_path / "TIPSYbtc.exe"
    fake_btc.write_text("stub", encoding="utf-8")
    monkeypatch.setattr(tipsy_module, "_tipsy_is_windows_host", lambda: False)
    monkeypatch.setattr(
        tipsy_module,
        "prepare_btc_runtime",
        lambda **kwargs: (_ for _ in ()).throw(
            AssertionError("staging must not start on a guaranteed failure")
        ),
    )
    runtime_config = BTCRuntimeConfig(
        batch_tipsy_exe=None,
        wine_executable=None,
        wine_prefix=None,
        host_mode="windows",
        use_xvfb=False,
    )

    with pytest.raises(RuntimeError, match="not native Windows"):
        run_btc_cli(
            input_csv=input_csv,
            mode="TSR",
            executable_path=fake_btc,
            scratch_root=tmp_path / "scratch",
            log_dir=tmp_path / "logs",
            run_id="btc_windows_pre",
            btc_runtime_config=runtime_config,
            env={},
        )


def test_resolve_btc_executable_uses_wine_runtime_without_rereading_config(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """m5: wine_runtime is trusted; resolve_btc_runtime_config is never re-invoked."""
    prefix = tmp_path / "prefix"
    exe = prefix / "drive_c" / "Program Files" / "TIPSY 4.7" / "BTC" / "TIPSYbtc.exe"
    exe.parent.mkdir(parents=True)
    exe.write_text("stub", encoding="utf-8")
    runtime = BTCRuntimeConfig(
        batch_tipsy_exe=None,
        wine_executable=None,
        wine_prefix=prefix,
        host_mode="wine",
        use_xvfb=False,
    )
    monkeypatch.setattr(
        tipsy_module,
        "resolve_btc_runtime_config",
        lambda **kwargs: (_ for _ in ()).throw(
            AssertionError("config re-resolution should be skipped with wine_runtime")
        ),
    )
    discovered = resolve_btc_executable(env={}, wine_runtime=runtime)
    assert discovered.executable_path == exe.resolve()
    assert discovered.source == f"wineprefix:{prefix}"


def test_cmd_quote_arg_quotes_whitespace_and_escapes_percent() -> None:
    """m6: cmd.exe quoting escapes % and double-quotes whitespace."""
    assert tipsy_module._cmd_quote_arg("MSYT.csv") == "MSYT.csv"
    assert tipsy_module._cmd_quote_arg("MSYT output.csv") == '"MSYT output.csv"'
    assert tipsy_module._cmd_quote_arg("100%") == "100%%"
    assert tipsy_module._cmd_quote_arg("a b%c") == '"a b%%c"'


def test_cmd_quote_arg_rejects_embedded_quotes_and_metacharacters() -> None:
    """m6: cmd.exe quoting rejects ambiguous arguments with a loud error."""
    with pytest.raises(RuntimeError, match="double quote"):
        tipsy_module._cmd_quote_arg('say "hi"')
    for character in "&|<>^":
        with pytest.raises(RuntimeError, match="cmd.exe"):
            tipsy_module._cmd_quote_arg(f"a{character}b")


def test_resolve_btc_executable_env_none_consults_os_environ(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """m7: env=None consults the full os.environ."""
    env_exe = tmp_path / "env.exe"
    env_exe.write_text("stub", encoding="utf-8")
    monkeypatch.setenv(DEFAULT_BATCHTIPSY_EXE_ENV, str(env_exe))
    discovered = resolve_btc_executable()
    assert discovered.executable_path == env_exe.resolve()
    assert discovered.source == f"env:{DEFAULT_BATCHTIPSY_EXE_ENV}"


def test_resolve_btc_executable_env_empty_dict_skips_os_environ(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """m7: env={} is an explicitly empty environment; no env lookups happen."""
    env_exe = tmp_path / "env.exe"
    env_exe.write_text("stub", encoding="utf-8")
    monkeypatch.setenv(DEFAULT_BATCHTIPSY_EXE_ENV, str(env_exe))
    monkeypatch.setattr(
        tipsy_module,
        "resolve_btc_runtime_config",
        lambda **kwargs: BTCRuntimeConfig(
            batch_tipsy_exe=None,
            wine_executable=None,
            wine_prefix=None,
            host_mode="wine",
            use_xvfb=False,
        ),
    )
    with pytest.raises(FileNotFoundError, match=DEFAULT_BATCHTIPSY_EXE_ENV):
        resolve_btc_executable(env={})


def test_run_btc_cli_threads_instance_root_to_runtime_resolution(
    monkeypatch, tmp_path: Path
) -> None:
    """m8: instance_root flows into runtime resolution when no config is supplied."""
    input_csv = tmp_path / "MSYT.csv"
    input_csv.write_text("feature_id\n1\n", encoding="utf-8")
    fake_btc = tmp_path / "fake_btc.py"
    fake_btc.write_text(
        "from pathlib import Path\n"
        "import sys\n"
        "mode, input_name, output_name, error_name = sys.argv[1:5]\n"
        "Path(output_name).write_text('feature_id,MVcon_0\\n1,2\\n', encoding='utf-8')\n"
        "Path(error_name).write_text('warnings,errors\\n0,0\\n', encoding='utf-8')\n",
        encoding="utf-8",
    )
    seen_kwargs: dict = {}
    monkeypatch.setattr(
        tipsy_module,
        "resolve_btc_runtime_config",
        lambda **kwargs: seen_kwargs.update(kwargs)
        or BTCRuntimeConfig(
            batch_tipsy_exe=None,
            wine_executable=sys.executable,
            wine_prefix=None,
            host_mode="wine",
            use_xvfb=False,
        ),
    )
    instance_root = tmp_path / "instance-root"
    result = run_btc_cli(
        input_csv=input_csv,
        mode="TSR",
        executable_path=sys.executable,
        scratch_root=tmp_path / "scratch",
        log_dir=tmp_path / "logs",
        run_id="btc_instance_root",
        instance_root=instance_root,
        env={},
        extra_executable_args=(fake_btc,),
    )

    assert result.exit_code == 0
    assert seen_kwargs.get("instance_root") == instance_root


def test_run_btc_cli_rejects_auto_runtime_config(
    monkeypatch, tmp_path: Path
) -> None:
    """m9: a supplied trusted config with host_mode='auto' is rejected up front."""
    input_csv = tmp_path / "MSYT.csv"
    input_csv.write_text("feature_id\n1\n", encoding="utf-8")
    monkeypatch.setattr(tipsy_module, "_tipsy_is_windows_host", lambda: False)
    auto_runtime = BTCRuntimeConfig(
        batch_tipsy_exe=None,
        wine_executable=None,
        wine_prefix=None,
        host_mode="auto",
        use_xvfb=False,
    )
    with pytest.raises(BTCRuntimeConfigError, match="host_mode must be resolved"):
        run_btc_cli(
            input_csv=input_csv,
            mode="TSR",
            scratch_root=tmp_path / "scratch",
            log_dir=tmp_path / "logs",
            run_id="btc_auto_rejected",
            btc_runtime_config=auto_runtime,
            env={},
        )


def test_wrap_btc_command_for_host_rejects_auto_runtime(monkeypatch) -> None:
    """m9: the host wrapper refuses an unresolved 'auto' runtime mode."""
    monkeypatch.setattr(tipsy_module, "_tipsy_is_windows_host", lambda: False)
    auto_runtime = BTCRuntimeConfig(
        batch_tipsy_exe=None,
        wine_executable=None,
        wine_prefix=None,
        host_mode="auto",
        use_xvfb=False,
    )
    with pytest.raises(RuntimeError, match="host_mode must be resolved"):
        tipsy_module._wrap_btc_command_for_host(
            ["/opt/TIPSY/TIPSYbtc.exe", "/TSR"],
            env={},
            runtime=auto_runtime,
        )


def test_wrap_btc_command_for_host_legacy_wsl_wine_prefix_env_selects_wine(
    monkeypatch,
) -> None:
    """M1: legacy wrapper path treats env Wine intent as Wine, not wsl-interop."""
    monkeypatch.setattr(tipsy_module, "_tipsy_is_windows_host", lambda: False)
    monkeypatch.setattr(
        "femic.pipeline.btc_runtime.shutil.which",
        lambda _name: None,
    )
    monkeypatch.setattr(tipsy_module, "find_wine_executable", lambda: "/usr/bin/wine64")

    command = tipsy_module._wrap_btc_command_for_host(
        ["/opt/TIPSY/TIPSYbtc.exe", "/TSR"],
        env={"WSL_DISTRO_NAME": "Ubuntu", FEMIC_BTC_WINEPREFIX: "/opt/wine"},
    )

    assert command == ["/usr/bin/wine64", "/opt/TIPSY/TIPSYbtc.exe", "/TSR"]


def test_wrap_btc_command_for_host_legacy_wsl_no_wine_intent_selects_interop(
    monkeypatch,
) -> None:
    """M1: without Wine intent the legacy wrapper still auto-selects wsl-interop."""
    monkeypatch.setattr(tipsy_module, "_tipsy_is_windows_host", lambda: False)
    monkeypatch.setattr(
        "femic.pipeline.btc_runtime.shutil.which",
        lambda name: "/mnt/c/Windows/System32/powershell.exe"
        if name == "powershell.exe"
        else None,
    )

    command = tipsy_module._wrap_btc_command_for_host(
        ["/mnt/c/Program Files/TIPSY 4.7/BTC/TIPSYbtc.exe", "/TSR"],
        env={"WSL_DISTRO_NAME": "Ubuntu"},
    )

    assert command == [
        "/mnt/c/Windows/System32/powershell.exe",
        "-NoProfile",
        "-Command",
        "& 'C:\\Program Files\\TIPSY 4.7\\BTC\\TIPSYbtc.exe' '/TSR'",
    ]


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
    assert len(results) == 8
    final_tokens = [column.token for column in final_template.columns]
    assert "Logs_Grade_D" in final_tokens
    assert "Logs_Grade_All" not in final_tokens


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
            if not include_last and prefix == "Logs_Grade_Y":
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
    assert len(results) == 8
    assert all(result.status == "accepted" for result in results)
    final_tokens = [column.token for column in final_template.columns]
    assert "Logs_Grade_Y" in final_tokens
    assert "Logs_Grade_All" not in final_tokens


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
    assert "Logs_Grade_All\t\tLogs_Grade_All\t{yr}" not in rendered


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


def test_validate_tipsy_output_is_fresh_raises_on_stale_output(tmp_path: Path) -> None:
    input_csv = tmp_path / "03_input-tsa29.csv"
    tipsy_output = tmp_path / "04_output-tsa29.csv"
    tipsy_output.write_text("old\n", encoding="utf-8")
    input_csv.write_text("newer-csv\n", encoding="utf-8")
    older = input_csv.stat().st_mtime - 10
    os.utime(tipsy_output, (older, older))

    with pytest.raises(RuntimeError, match="Stale BatchTIPSY output detected"):
        validate_tipsy_output_is_fresh(
            tipsy_input_excel_path=None,
            btc_input_csv_path=input_csv,
            tipsy_output_path=tipsy_output,
        )


def test_validate_tipsy_output_is_fresh_warns_and_continues_on_coherent_stale_pair(
    tmp_path: Path,
) -> None:
    tipsy_input = tmp_path / "tipsy_params_tsa29.xlsx"
    input_csv = tmp_path / "03_input-tsa29.csv"
    tipsy_output = tmp_path / "04_output-tsa29.csv"
    pd.DataFrame(
        {
            "AU": [2001, 2002],
            "TBLno": [2001, 2002],
            "SI": [30, 32],
        }
    ).to_excel(tipsy_input, sheet_name="TIPSY_inputTBL", index=False)
    input_csv.write_text("feature_id,MVcon_0\n2001,0\n2002,0\n", encoding="utf-8")
    tipsy_output.write_text("feature_id,MVcon_0\n2001,0\n2002,0\n", encoding="utf-8")
    older = input_csv.stat().st_mtime - 10
    os.utime(tipsy_output, (older, older))

    with pytest.warns(RuntimeWarning, match="appear coherent"):
        validate_tipsy_output_is_fresh(
            tipsy_input_excel_path=tipsy_input,
            btc_input_csv_path=input_csv,
            tipsy_output_path=tipsy_output,
        )


def test_validate_tipsy_output_is_fresh_strict_mode_raises_on_coherent_stale_pair(
    tmp_path: Path,
) -> None:
    tipsy_input = tmp_path / "tipsy_params_tsa29.xlsx"
    input_csv = tmp_path / "03_input-tsa29.csv"
    tipsy_output = tmp_path / "04_output-tsa29.csv"
    pd.DataFrame(
        {
            "AU": [2101, 2102],
            "TBLno": [2101, 2102],
            "SI": [25, 28],
        }
    ).to_excel(tipsy_input, sheet_name="TIPSY_inputTBL", index=False)
    input_csv.write_text("feature_id,MVcon_0\n2101,0\n2102,0\n", encoding="utf-8")
    tipsy_output.write_text("feature_id,MVcon_0\n2101,0\n2102,0\n", encoding="utf-8")
    older = input_csv.stat().st_mtime - 10
    os.utime(tipsy_output, (older, older))

    with pytest.raises(RuntimeError, match="Strict BatchTIPSY freshness"):
        validate_tipsy_output_is_fresh(
            tipsy_input_excel_path=tipsy_input,
            btc_input_csv_path=input_csv,
            tipsy_output_path=tipsy_output,
            strict_timestamp_mismatch=True,
        )


def test_validate_tipsy_output_is_fresh_allows_override(tmp_path: Path) -> None:
    tipsy_input = tmp_path / "tipsy_params_tsa29.xlsx"
    input_csv = tmp_path / "03_input-tsa29.csv"
    tipsy_output = tmp_path / "04_output-tsa29.csv"
    tipsy_output.write_text("old\n", encoding="utf-8")
    input_csv.write_text("newer-csv\n", encoding="utf-8")
    tipsy_input.write_text("new\n", encoding="utf-8")

    validate_tipsy_output_is_fresh(
        tipsy_input_excel_path=tipsy_input,
        btc_input_csv_path=input_csv,
        tipsy_output_path=tipsy_output,
        allow_stale=True,
    )


def test_assess_tipsy_input_output_coherence_reports_missing_table(
    tmp_path: Path,
) -> None:
    tipsy_input = tmp_path / "tipsy_params_tsa29.xlsx"
    tipsy_output = tmp_path / "04_output-tsa29.csv"
    pd.DataFrame(
        {
            "AU": [3001, 3002],
            "TBLno": [3001, 3002],
            "SI": [20, 21],
        }
    ).to_excel(tipsy_input, sheet_name="TIPSY_inputTBL", index=False)
    tipsy_output.write_text("feature_id,MVcon_0\n3001,0\n", encoding="utf-8")

    coherence = assess_tipsy_input_output_coherence(
        tipsy_input_excel_path=tipsy_input,
        tipsy_output_path=tipsy_output,
    )
    assert coherence.coherent is False
    assert "missing_tables=1" in coherence.summary
    assert "missing_aus=1" in coherence.summary


def test_validate_tipsy_output_is_fresh_requires_csv_when_provided(
    tmp_path: Path,
) -> None:
    tipsy_input = tmp_path / "tipsy_params_tsa29.xlsx"
    tipsy_output = tmp_path / "04_output-tsa29.csv"
    missing_csv = tmp_path / "03_input-tsa29.csv"
    tipsy_output.write_text("old\n", encoding="utf-8")
    tipsy_input.write_text("new\n", encoding="utf-8")

    with pytest.raises(
        RuntimeError, match="Missing canonical BatchTIPSY input CSV file"
    ):
        validate_tipsy_output_is_fresh(
            tipsy_input_excel_path=tipsy_input,
            btc_input_csv_path=missing_csv,
            tipsy_output_path=tipsy_output,
        )


def test_validate_tipsy_output_is_fresh_accepts_known_csv_fingerprint(
    tmp_path: Path,
) -> None:
    input_csv = tmp_path / "03_input-tsa29.csv"
    tipsy_output = tmp_path / "04_output-tsa29.csv"
    input_csv.write_text("same-csv-content\n", encoding="utf-8")
    tipsy_output.write_text("old-output\n", encoding="utf-8")
    older = input_csv.stat().st_mtime - 10
    os.utime(tipsy_output, (older, older))

    fingerprint = tipsy_output_input_fingerprint_path(tipsy_output_path=tipsy_output)
    fingerprint.write_text(f"{compute_file_sha256(input_csv)}\n", encoding="utf-8")

    validate_tipsy_output_is_fresh(
        tipsy_input_excel_path=None,
        btc_input_csv_path=input_csv,
        tipsy_output_path=tipsy_output,
    )


def test_validate_tipsy_output_is_fresh_raises_on_csv_fingerprint_mismatch(
    tmp_path: Path,
) -> None:
    input_csv = tmp_path / "03_input-tsa29.csv"
    tipsy_output = tmp_path / "04_output-tsa29.csv"
    input_csv.write_text("new-csv-content\n", encoding="utf-8")
    tipsy_output.write_text("some-output\n", encoding="utf-8")

    fingerprint = tipsy_output_input_fingerprint_path(tipsy_output_path=tipsy_output)
    fingerprint.write_text("badfingerprint\n", encoding="utf-8")

    with pytest.raises(
        RuntimeError,
        match="different canonical BTC input CSV fingerprint",
    ):
        validate_tipsy_output_is_fresh(
            tipsy_input_excel_path=None,
            btc_input_csv_path=input_csv,
            tipsy_output_path=tipsy_output,
        )


def test_write_tipsy_output_input_fingerprint_writes_sidecar(tmp_path: Path) -> None:
    input_csv = tmp_path / "03_input-tsa29.csv"
    tipsy_output = tmp_path / "04_output-tsa29.csv"
    input_csv.write_text("csv-content\n", encoding="utf-8")
    tipsy_output.write_text("output\n", encoding="utf-8")
    path = write_tipsy_output_input_fingerprint(
        btc_input_csv_path=input_csv,
        tipsy_output_path=tipsy_output,
    )
    assert path == tipsy_output_input_fingerprint_path(tipsy_output_path=tipsy_output)
    assert path is not None
    assert path.read_text(encoding="utf-8").strip() == compute_file_sha256(input_csv)


def test_tipsy_stage_output_paths_uses_expected_naming(tmp_path: Path) -> None:
    curves_path, sppcomp_path = tipsy_stage_output_paths(tsa="08", output_root=tmp_path)
    assert curves_path == tmp_path / "tipsy_curves_tsa08.csv"
    assert sppcomp_path == tmp_path / "tipsy_sppcomp_tsa08.csv"


def test_tipsy_stage_output_paths_preserves_non_numeric_case_code(
    tmp_path: Path,
) -> None:
    curves_path, sppcomp_path = tipsy_stage_output_paths(
        tsa="tfl6", output_root=tmp_path
    )
    assert curves_path == tmp_path / "tipsy_curves_tfl6.csv"
    assert sppcomp_path == tmp_path / "tipsy_sppcomp_tfl6.csv"


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


def test_build_tipsy_params_for_tsa_passes_si_level_to_builder() -> None:
    captured: list[dict[str, object]] = []
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
        au_data: object,
        _vdyp_out: object,
    ) -> dict[str, dict[str, object]]:
        captured.append(dict(au_data))
        return {"f": {"TBLno": 20000 + au_id}}

    _ = build_tipsy_params_for_tsa(
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

    assert len(captured) == 1
    assert captured[0]["stratum_code"] == "SBS_7A"
    assert captured[0]["si_level"] == "L"


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
