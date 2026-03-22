from __future__ import annotations

import math
import os
from pathlib import Path

import pandas as pd
import pytest

from femic.pipeline.tipsy import (
    assess_tipsy_input_output_coherence,
    build_tipsy_params_for_tsa,
    build_tipsy_input_table,
    build_tipsy_warning_event,
    compute_file_sha256,
    compute_vdyp_oaf1,
    compute_vdyp_site_index,
    evaluate_tipsy_candidate,
    tipsy_input_dat_path,
    tipsy_output_input_fingerprint_path,
    tipsy_params_excel_path,
    tipsy_stage_output_paths,
    validate_tipsy_output_is_fresh,
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
