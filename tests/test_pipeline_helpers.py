from __future__ import annotations

import os
from pathlib import Path

from femic.pipeline.io import (
    FALLBACK_DEFAULT_TSA_LIST,
    build_legacy_data_artifact_paths,
    build_ria_vri_checkpoint_paths,
    build_legacy_execution_plan,
    build_pipeline_run_config,
    file_sha256,
    load_pipeline_run_profile,
    load_default_tsa_list,
    normalize_tsa_list,
    resolve_effective_run_options,
    resolve_legacy_external_data_paths,
    resolve_run_paths,
)
from femic.pipeline.plots import (
    StrataDistributionPlotConfig,
    build_strata_distribution_plot_config,
    plot_strata_site_index_diagnostics,
    render_strata_distribution_plot,
    resolve_strata_plot_ordering,
    strata_plot_paths,
    tipsy_vdyp_plot_path,
    tipsy_vdyp_ylim_for_tsa,
)
from femic.pipeline.stages import prepare_tsa_index
from femic.pipeline.vdyp import build_vdyp_cache_paths
import pytest
import pandas as pd
import numpy as np

from femic.pipeline.tsa import (
    DEFAULT_TARGET_NSTRATA,
    MIN_STANDCOUNT,
    assign_au_ids_from_scsi,
    assign_thlb_raw_from_raster,
    assign_thlb_area_and_flag,
    assign_si_levels_from_stratum_quantiles,
    assign_stratum_matches_from_au_table,
    apply_stratum_alias_map,
    build_au_assignment_null_summary,
    build_missing_au_assignment_summary,
    build_strata_summary,
    build_stratum_lexmatch_alias_map,
    emit_missing_au_mapping_warning,
    lookup_scsi_au_base,
    mean_thlb_for_geometry,
    resolve_si_level_quantiles_for_stratum,
    summarize_missing_au_mappings,
    target_nstrata_for,
    normalize_tsa_code,
    select_tsa_slice,
    validate_complete_au_assignment,
    validate_nonempty_au_assignment,
)


def test_normalize_tsa_list_defaults_and_padding(tmp_path: Path) -> None:
    cfg = tmp_path / "dev.toml"
    cfg.write_text("[run]\ndefault_tsa_list = ['24','41']\n", encoding="utf-8")
    assert normalize_tsa_list(None, default_tsa_list=load_default_tsa_list(cfg)) == [
        "24",
        "41",
    ]
    assert normalize_tsa_list([8, "16", "041"]) == ["08", "16", "041"]


def test_load_default_tsa_list_fallback_when_missing(tmp_path: Path) -> None:
    assert load_default_tsa_list(tmp_path / "missing.toml") == FALLBACK_DEFAULT_TSA_LIST


def test_resolve_run_paths_uses_script_parent_as_repo_root(tmp_path: Path) -> None:
    script_path = tmp_path / "00_data-prep.py"
    script_path.write_text("# test\n", encoding="utf-8")

    resolved = resolve_run_paths(script_path=script_path)

    assert resolved.repo_root == tmp_path.resolve()
    assert resolved.log_dir == (tmp_path / "vdyp_io" / "logs").resolve()


def test_resolve_run_paths_uses_instance_root_when_provided(tmp_path: Path) -> None:
    script_path = tmp_path / "scripts" / "00_data-prep.py"
    script_path.parent.mkdir(parents=True, exist_ok=True)
    script_path.write_text("# test\n", encoding="utf-8")
    instance_root = tmp_path / "instance"
    instance_root.mkdir(parents=True, exist_ok=True)

    resolved = resolve_run_paths(script_path=script_path, instance_root=instance_root)

    assert resolved.repo_root == instance_root.resolve()
    assert resolved.log_dir == (instance_root / "vdyp_io" / "logs").resolve()


def test_build_ria_vri_checkpoint_paths_defaults() -> None:
    paths = build_ria_vri_checkpoint_paths()
    assert paths[1] == Path("data/ria_vri_vclr1p_checkpoint1.feather")
    assert paths[8] == Path("data/ria_vri_vclr1p_checkpoint8.feather")


def test_build_legacy_data_artifact_paths_defaults() -> None:
    paths = build_legacy_data_artifact_paths()
    assert paths.vdyp_input_pandl_path == Path(
        "data/VEG_COMP_VDYP7_INPUT_POLY_AND_LAYER_2019.gdb"
    )
    assert paths.tipsy_params_columns_path == Path("data/tipsy_params_columns")
    assert paths.stands_shp_dir == Path("data/shp")
    assert paths.site_prod_bc_gdb_path == Path("data/bc/siteprod/Site_Prod_BC.gdb")


def test_resolve_legacy_external_data_paths_prefers_first_existing_vri_root(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    fallback_data = (repo_root / ".." / "data").resolve()
    (fallback_data / "bc/vri/2019/VEG_COMP_LYR_R1_POLY.gdb").mkdir(parents=True)
    (fallback_data / "VEG_COMP_VDYP7_INPUT_POLY_AND_LAYER_2019.gdb").mkdir(parents=True)
    (fallback_data / "bc/tsa/FADM_TSA.gdb").mkdir(parents=True)
    (fallback_data / "bc/siteprod/Site_Prod_BC.gdb").mkdir(parents=True)

    resolved = resolve_legacy_external_data_paths(repo_root=repo_root)
    assert resolved.external_data_root == fallback_data
    assert resolved.vri_vclr1p_path == (
        fallback_data / "bc/vri/2019/VEG_COMP_LYR_R1_POLY.gdb"
    )
    assert resolved.vdyp_input_pandl_path == (
        fallback_data / "VEG_COMP_VDYP7_INPUT_POLY_AND_LAYER_2019.gdb"
    )
    assert resolved.tsa_boundaries_path == (fallback_data / "bc/tsa/FADM_TSA.gdb")
    assert resolved.site_prod_bc_gdb_path == (
        fallback_data / "bc/siteprod/Site_Prod_BC.gdb"
    )


def test_resolve_legacy_external_data_paths_prefers_root_with_vri_and_tsa(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    primary_data = (repo_root / "data").resolve()
    fallback_data = (repo_root / ".." / "data").resolve()
    (primary_data / "bc/vri/2019/VEG_COMP_LYR_R1_POLY.gdb").mkdir(parents=True)
    (fallback_data / "bc/vri/2019/VEG_COMP_LYR_R1_POLY.gdb").mkdir(parents=True)
    (fallback_data / "VEG_COMP_VDYP7_INPUT_POLY_AND_LAYER_2019.gdb").mkdir(parents=True)
    (fallback_data / "bc/tsa/FADM_TSA.gdb").mkdir(parents=True)
    (fallback_data / "bc/siteprod/Site_Prod_BC.gdb").mkdir(parents=True)

    resolved = resolve_legacy_external_data_paths(repo_root=repo_root)

    assert resolved.external_data_root == fallback_data
    assert resolved.vri_vclr1p_path == (
        fallback_data / "bc/vri/2019/VEG_COMP_LYR_R1_POLY.gdb"
    )
    assert resolved.vdyp_input_pandl_path == (
        fallback_data / "VEG_COMP_VDYP7_INPUT_POLY_AND_LAYER_2019.gdb"
    )
    assert resolved.tsa_boundaries_path == (fallback_data / "bc/tsa/FADM_TSA.gdb")
    assert resolved.site_prod_bc_gdb_path == (
        fallback_data / "bc/siteprod/Site_Prod_BC.gdb"
    )


def test_resolve_legacy_external_data_paths_prefers_2024_vri_when_available(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    fallback_data = (repo_root / ".." / "data").resolve()
    (fallback_data / "bc/vri/2019/VEG_COMP_LYR_R1_POLY.gdb").mkdir(parents=True)
    (fallback_data / "bc/vri/2024/VEG_COMP_LYR_R1_POLY_2024.gdb").mkdir(parents=True)
    (fallback_data / "bc/vri/2024/VEG_COMP_VDYP7_INPUT_POLY_AND_LAYER_2024.gdb").mkdir(
        parents=True
    )
    (fallback_data / "bc/tsa/FADM_TSA.gdb").mkdir(parents=True)
    (fallback_data / "bc/siteprod/Site_Prod_BC.gdb").mkdir(parents=True)

    resolved = resolve_legacy_external_data_paths(repo_root=repo_root)
    assert resolved.external_data_root == fallback_data
    assert resolved.vri_vclr1p_path == (
        fallback_data / "bc/vri/2024/VEG_COMP_LYR_R1_POLY_2024.gdb"
    )
    assert resolved.vdyp_input_pandl_path == (
        fallback_data / "bc/vri/2024/VEG_COMP_VDYP7_INPUT_POLY_AND_LAYER_2024.gdb"
    )
    assert resolved.tsa_boundaries_path == (fallback_data / "bc/tsa/FADM_TSA.gdb")
    assert resolved.site_prod_bc_gdb_path == (
        fallback_data / "bc/siteprod/Site_Prod_BC.gdb"
    )


def test_tsa_target_nstrata_lookup() -> None:
    assert target_nstrata_for("8") == 9
    assert target_nstrata_for("16") == 13
    assert target_nstrata_for("29") == DEFAULT_TARGET_NSTRATA
    assert target_nstrata_for("custom") == DEFAULT_TARGET_NSTRATA
    assert MIN_STANDCOUNT == 1000


def test_select_tsa_slice_handles_string_numeric_equivalence() -> None:
    frame = pd.DataFrame({"value": [1.0, 2.0]}, index=pd.Index([29, 40], name="tsa"))

    sliced = select_tsa_slice(f_table=frame, tsa_value="29")

    assert list(sliced.index) == [29]
    assert float(sliced.iloc[0]["value"]) == 1.0


def test_select_tsa_slice_handles_numeric_against_string_index() -> None:
    frame = pd.DataFrame(
        {"value": [1.0, 2.0]}, index=pd.Index(["29", "40"], name="tsa")
    )

    sliced = select_tsa_slice(f_table=frame, tsa_value=29)

    assert list(sliced.index) == ["29"]
    assert float(sliced.iloc[0]["value"]) == 1.0


def test_select_tsa_slice_handles_mixed_case_named_tsa() -> None:
    frame = pd.DataFrame({"value": [1.0]}, index=pd.Index(["k3z"], name="tsa"))

    sliced = select_tsa_slice(f_table=frame, tsa_value="K3Z")

    assert list(sliced.index) == ["k3z"]
    assert float(sliced.iloc[0]["value"]) == 1.0


def test_prepare_tsa_index_normalizes_column_values() -> None:
    frame = pd.DataFrame({"tsa_code": [29, "08", "K3Z"], "value": [1, 2, 3]})

    prepared = prepare_tsa_index(f_table=frame, tsa_column="tsa_code")

    assert prepared.index.name == "tsa_code"
    assert list(prepared.index) == ["29", "08", "k3z"]
    assert normalize_tsa_code("K3Z") == "k3z"


def test_build_strata_summary_filters_and_computes_expected_fields() -> None:
    f_table = pd.DataFrame(
        {
            "stratum": ["A", "A", "A", "B", "B", "C"],
            "FEATURE_AREA_SQM": [10.0, 10.0, 10.0, 20.0, 20.0, 30.0],
            "SITE_INDEX": [10.0, 11.0, 12.0, 20.0, 21.0, 30.0],
            "FEATURE_ID": [1, 2, 3, 4, 5, 6],
            "CROWN_CLOSURE": [50.0, 60.0, 55.0, 70.0, 65.0, 80.0],
        }
    ).set_index("stratum")
    f_table["totalarea_p"] = f_table.FEATURE_AREA_SQM / f_table.FEATURE_AREA_SQM.sum()

    strata_df, largestn, site_index_iqr_mean = build_strata_summary(
        f_table=f_table,
        stratum_col="stratum",
        pd_module=pd,
        target_nstrata=2,
        min_standcount=2,
    )

    assert set(strata_df.index) == {"A", "B"}
    assert set(largestn) == {"A", "B"}
    assert strata_df.loc["A", "median_si"] == 11.0
    assert strata_df.loc["B", "median_si"] == 20.5
    assert round(site_index_iqr_mean, 2) == 0.5


def test_build_strata_summary_falls_back_when_min_standcount_filters_all() -> None:
    f_table = pd.DataFrame(
        {
            "stratum": ["A", "A", "B"],
            "FEATURE_AREA_SQM": [10.0, 20.0, 30.0],
            "SITE_INDEX": [10.0, 11.0, 20.0],
            "FEATURE_ID": [1, 2, 3],
            "CROWN_CLOSURE": [45.0, 55.0, 65.0],
        }
    ).set_index("stratum")
    f_table["totalarea_p"] = f_table.FEATURE_AREA_SQM / f_table.FEATURE_AREA_SQM.sum()

    strata_df, largestn, _site_index_iqr_mean = build_strata_summary(
        f_table=f_table,
        stratum_col="stratum",
        pd_module=pd,
        target_nstrata=2,
        min_standcount=1000,
    )

    assert set(strata_df.index) == {"A", "B"}
    assert set(largestn) == {"A", "B"}
    assert float(strata_df["totalarea_p"].sum()) == pytest.approx(1.0)
    assert strata_df["totalarea_p"].isna().sum() == 0
    assert strata_df["stand_count"].isna().sum() == 0
    assert strata_df.loc["A", "median_si"] == 10.5
    assert strata_df.loc["B", "median_si"] == 20.0


def test_build_strata_summary_requires_target_or_tsa_code() -> None:
    f_table = pd.DataFrame(
        {
            "stratum": ["A", "A"],
            "FEATURE_AREA_SQM": [1.0, 1.0],
            "SITE_INDEX": [10.0, 11.0],
            "FEATURE_ID": [1, 2],
            "CROWN_CLOSURE": [50.0, 55.0],
            "totalarea_p": [0.5, 0.5],
        }
    ).set_index("stratum")

    with pytest.raises(ValueError, match="target_nstrata or tsa_code"):
        build_strata_summary(
            f_table=f_table,
            stratum_col="stratum",
            pd_module=pd,
        )


def test_build_strata_summary_selects_by_target_coverage() -> None:
    f_table = pd.DataFrame(
        {
            "stratum": ["A", "A", "B", "B", "C", "D"],
            "FEATURE_AREA_SQM": [30.0, 30.0, 20.0, 20.0, 10.0, 5.0],
            "SITE_INDEX": [10.0, 11.0, 20.0, 21.0, 30.0, 40.0],
            "FEATURE_ID": [1, 2, 3, 4, 5, 6],
            "CROWN_CLOSURE": [50.0, 55.0, 60.0, 62.0, 70.0, 75.0],
        }
    ).set_index("stratum")
    f_table["totalarea_p"] = f_table.FEATURE_AREA_SQM / f_table.FEATURE_AREA_SQM.sum()

    strata_df, largestn, _site_index_iqr_mean = build_strata_summary(
        f_table=f_table,
        stratum_col="stratum",
        pd_module=pd,
        target_nstrata=1,
        target_coverage=0.90,
        min_standcount=1,
    )

    assert list(strata_df.index) == ["A", "B", "C"]
    assert largestn == ["A", "B", "C"]
    assert float(strata_df.coverage.sum()) >= 0.90


def test_build_stratum_lexmatch_alias_map_prefers_highest_area_on_distance_tie() -> (
    None
):
    f_table = pd.DataFrame(
        {
            "stratum": ["SAA", "SBB", "SAB"],
            "stratum_lexmatch": ["AA", "BB", "AB"],
            "totalarea_p": [0.3, 0.6, 0.1],
        }
    ).set_index("stratum")

    distances = {
        ("AA", "AB"): 1,
        ("BB", "AB"): 1,
    }

    def fake_levenshtein(a: str, b: str) -> int:
        return distances.get((a, b), distances.get((b, a), 9))

    alias_map = build_stratum_lexmatch_alias_map(
        f_table=f_table,
        stratum_col="stratum",
        selected_strata_codes=["SAA", "SBB"],
        levenshtein_fn=fake_levenshtein,
    )

    assert alias_map == {"SAB": "SBB"}


def test_apply_stratum_alias_map_assigns_selected_or_best_match() -> None:
    frame = pd.DataFrame(
        {
            "stratum": ["SAA", "SAB", "SXX"],
            "value": [1, 2, 3],
        }
    )
    matched_col = apply_stratum_alias_map(
        f_table=frame,
        stratum_col="stratum",
        selected_strata_codes=["SAA", "SBB"],
        best_match={"SAB": "SBB"},
    )

    assert matched_col == "stratum_matched"
    assert frame["stratum_matched"].tolist() == ["SAA", "SBB", "SXX"]


def test_assign_stratum_matches_from_au_table_assigns_expected_aliases() -> None:
    f_table = pd.DataFrame(
        {
            "FEATURE_ID": [1, 2, 3],
            "tsa_code": ["08", "08", "08"],
            "stratum": ["BWBS_AT", "BWBS_AA", "BWBS_SB"],
            "stratum_lexmatch": ["AT", "AA", "SB"],
            "FEATURE_AREA_SQM": [10.0, 20.0, 30.0],
            "totalarea_p": [0.2, 0.3, 0.5],
        }
    )
    au_table = pd.DataFrame(
        {
            "tsa": ["08", "08"],
            "stratum_code": ["BWBS_AT", "BWBS_SB"],
        }
    )

    matched = assign_stratum_matches_from_au_table(
        f_table=f_table,
        au_table=au_table,
        tsa_list=["08"],
        stratum_col="stratum",
        levenshtein_fn=lambda a, b: 0 if a == b else 1,
        message_fn=lambda _m: None,
    )

    assert matched.index.name == "FEATURE_ID"
    assert matched.loc[1, "stratum_matched"] == "BWBS_AT"
    assert matched.loc[2, "stratum_matched"] in {"BWBS_AT", "BWBS_SB"}
    assert matched.loc[3, "stratum_matched"] == "BWBS_SB"


def test_assign_si_levels_from_stratum_quantiles_assigns_levels() -> None:
    f_table = pd.DataFrame(
        {
            "stratum_matched": ["S1", "S1", "S1", "S1"],
            "SITE_INDEX": [10.0, 20.0, 30.0, 40.0],
        }
    )
    si_levelquants = {"L": [5, 20, 35], "M": [35, 50, 65], "H": [65, 80, 95]}

    out, stats = assign_si_levels_from_stratum_quantiles(
        f_table=f_table,
        si_levelquants=si_levelquants,
        message_fn=lambda _m: None,
    )

    assert "S1" in stats.index
    assert set(out["si_level"].dropna().unique()) <= {"L", "M", "H"}


def test_resolve_si_level_quantiles_for_stratum_returns_fixed_quantiles() -> None:
    stats = pd.DataFrame(
        {
            "5%": [10.0, 10.0, 10.0],
            "95%": [14.0, 19.0, 24.5],
        },
        index=["NARROW", "MID", "WIDE"],
    )
    base = {"L": [5, 20, 35], "M": [35, 50, 65], "H": [65, 80, 95]}

    for code in ("NARROW", "MID", "WIDE"):
        out = resolve_si_level_quantiles_for_stratum(
            stratum_si_stats=stats,
            stratum_code=code,
            si_levelquants=base,
        )
        assert out == {"L": (5, 20, 35), "M": (35, 50, 65), "H": (65, 80, 95)}


def test_assign_si_levels_from_stratum_quantiles_respects_allowed_levels() -> None:
    f_table = pd.DataFrame(
        {
            "stratum_matched": ["S1"] * 8,
            "SITE_INDEX": [10.0, 12.0, 14.0, 16.0, 18.0, 20.0, 22.0, 24.0],
        }
    )
    base = {"L": [5, 20, 35], "M": [35, 50, 65], "H": [65, 80, 95]}

    out, _stats = assign_si_levels_from_stratum_quantiles(
        f_table=f_table,
        si_levelquants=base,
        allowed_levels_by_stratum={"S1": ["L", "H"]},
        message_fn=lambda _m: None,
    )

    assert set(out["si_level"].dropna().unique()) == {"L", "H"}


def test_assign_si_levels_from_stratum_quantiles_assigns_tail_rows() -> None:
    f_table = pd.DataFrame(
        {
            "stratum_matched": ["S1"] * 8,
            "SITE_INDEX": [1.0, 5.0, 10.0, 15.0, 20.0, 30.0, 40.0, 100.0],
        }
    )
    base = {"L": [5, 20, 35], "M": [35, 50, 65], "H": [65, 80, 95]}

    out, _stats = assign_si_levels_from_stratum_quantiles(
        f_table=f_table,
        si_levelquants=base,
        message_fn=lambda _m: None,
    )

    assert out.loc[0, "si_level"] == "L"
    assert out.loc[7, "si_level"] == "H"
    assert out["si_level"].notna().all()


def test_assign_si_levels_from_stratum_quantiles_handles_no_matched_rows() -> None:
    f_table = pd.DataFrame(
        {
            "stratum_matched": [None, None],
            "SITE_INDEX": [10.0, 20.0],
        }
    )

    out, stats = assign_si_levels_from_stratum_quantiles(
        f_table=f_table,
        si_levelquants={"L": [5, 20, 35]},
        message_fn=lambda _m: None,
    )

    assert stats.empty
    assert "si_level" in out.columns
    assert out["si_level"].isnull().all()


def test_lookup_scsi_au_base_and_assign_au_ids_from_scsi() -> None:
    scsi_au = {"08": {("S1", "L"): 7}}
    assert (
        lookup_scsi_au_base(
            scsi_au=scsi_au,
            tsa_code="08",
            stratum_code="S1",
            si_level="L",
        )
        == 7
    )
    frame = pd.DataFrame(
        {
            "tsa_code": ["08", "08"],
            "stratum_matched": ["S1", "S2"],
            "si_level": ["L", "L"],
        }
    )
    out = assign_au_ids_from_scsi(f_table=frame, scsi_au=scsi_au)
    assert int(out["au"].iloc[0]) == 800007
    assert pd.isna(out["au"].iloc[1])


def test_assign_au_ids_from_scsi_handles_tsa_code_as_index() -> None:
    scsi_au = {"29": {("IDF_AT", "L"): 11}}
    frame = pd.DataFrame(
        {
            "tsa_code": ["29"],
            "stratum_matched": ["IDF_AT"],
            "si_level": ["L"],
        }
    ).set_index("tsa_code")
    out = assign_au_ids_from_scsi(f_table=frame, scsi_au=scsi_au)
    assert int(out.loc[0, "au"]) == 2900011


def test_assign_au_ids_from_scsi_handles_unnamed_index_fallback() -> None:
    scsi_au = {"29": {("IDF_AT", "L"): 11}}
    frame = pd.DataFrame(
        {
            "index": ["29"],
            "stratum_matched": ["IDF_AT"],
            "si_level": ["L"],
        }
    ).set_index("index")
    out = assign_au_ids_from_scsi(f_table=frame, scsi_au=scsi_au)
    assert int(out.loc[0, "au"]) == 2900011


def test_summarize_missing_au_mappings_and_null_summary() -> None:
    frame = pd.DataFrame(
        {
            "tsa_code": ["08", "08", "16"],
            "stratum_matched": ["S1", "S1", "S9"],
            "si_level": ["L", "L", "H"],
            "SITE_INDEX": [10.0, None, None],
            "au": [None, None, None],
        }
    )
    missing = summarize_missing_au_mappings(f_table=frame, top_n=1)
    assert missing.index[0] == ("08", "S1", "L")
    summary = build_au_assignment_null_summary(f_table=frame)
    assert summary["rows"] == 3
    assert summary["site_index_null"] == 2
    missing_summary = build_missing_au_assignment_summary(f_table=frame, top_n=1)
    assert missing_summary["rows"] == 3
    assert missing_summary["top_missing"][0]["tsa_code"] == "08"
    with pytest.raises(ValueError, match="AU assignment produced no rows"):
        validate_nonempty_au_assignment(f_table=frame)


def test_validate_complete_au_assignment_raises_on_residual_missing_rows() -> None:
    frame = pd.DataFrame(
        {
            "tsa_code": ["29", "29"],
            "stratum_matched": ["IDF_FD", "IDF_FD"],
            "si_level": ["L", "M"],
            "SITE_INDEX": [12.0, 18.0],
            "FEATURE_AREA_SQM": [1000.0, 2000.0],
            "au": [2900001, None],
        }
    )

    with pytest.raises(
        ValueError, match="residual AFLB rows unmapped after lexicographical"
    ):
        validate_complete_au_assignment(f_table=frame)


def test_emit_missing_au_mapping_warning_emits_header_and_summary() -> None:
    messages: list[object] = []
    emit_missing_au_mapping_warning(
        summary={"missing": 2},
        message_fn=messages.append,
    )
    assert messages[0] == "Warning: missing AU mappings for some strata (top 10 shown):"
    assert messages[1] == {"missing": 2}


def test_assign_thlb_area_and_flag() -> None:
    f_table = pd.DataFrame(
        [
            {
                "tsa_code": "08",
                "thlb_raw": 95,
                "FEATURE_AREA_SQM": 10000.0,
                "SPECIES_CD_1": "SW",
                "SITE_INDEX": 20.0,
            },
            {
                "tsa_code": "08",
                "thlb_raw": 80,
                "FEATURE_AREA_SQM": 10000.0,
                "SPECIES_CD_1": "SW",
                "SITE_INDEX": 20.0,
            },
            {
                "tsa_code": "24",
                "thlb_raw": 70,
                "FEATURE_AREA_SQM": 10000.0,
                "SPECIES_CD_1": "PL",
                "SITE_INDEX": 20.0,
            },
        ]
    )

    out = assign_thlb_area_and_flag(
        f_table=f_table,
        species_spruce=["SW"],
        species_pine=["PL"],
        species_aspen=["AT"],
        species_fir=["BL"],
    )

    assert out["thlb_area"].iloc[0] > 0.0
    assert out["thlb_area"].iloc[1] == 0.0
    assert out["thlb"].tolist() == [1, 0, 1]


def test_mean_thlb_for_geometry_and_assign_thlb_raw_from_raster() -> None:
    def _mask(
        _src: object, _shapes: list[object], crop: bool
    ) -> tuple[np.ndarray, None]:
        assert crop is True
        return np.array([[-1, 5, 7]]), None

    value = mean_thlb_for_geometry(
        geometry=object(),
        raster_src=object(),
        mask_fn=_mask,
        np_module=np,
    )
    assert value == 6.0

    class _FakeSrc:
        def __enter__(self) -> "_FakeSrc":
            return self

        def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
            return None

    opened_paths: list[Path] = []

    class _FakeRio:
        def open(self, path: Path) -> _FakeSrc:
            opened_paths.append(path)
            return _FakeSrc()

    frame = pd.DataFrame({"geometry": [object(), object()]})

    def _row_apply(table: pd.DataFrame, fn: object, axis: int) -> pd.Series:
        assert axis == 1
        return table.apply(fn, axis=axis)  # type: ignore[arg-type]

    out = assign_thlb_raw_from_raster(
        f_table=frame,
        thlb_raster_path=Path("misc.thlb.tif"),
        rio_module=_FakeRio(),
        mask_fn=_mask,
        np_module=np,
        row_apply_fn=_row_apply,
    )
    assert out["thlb_raw"].tolist() == [6.0, 6.0]
    assert opened_paths == [Path("misc.thlb.tif")]


def test_mean_thlb_for_geometry_fallback_scope() -> None:
    def _runtime_error_mask(
        _src: object, _shapes: list[object], crop: bool
    ) -> tuple[np.ndarray, None]:
        assert crop is True
        raise RuntimeError("mask failed")

    fallback_value = mean_thlb_for_geometry(
        geometry=object(),
        raster_src=object(),
        mask_fn=_runtime_error_mask,
        np_module=np,
        default_on_error=11.0,
    )
    assert fallback_value == 11.0

    def _unexpected_error_mask(
        _src: object, _shapes: list[object], crop: bool
    ) -> tuple[np.ndarray, None]:
        assert crop is True
        raise ZeroDivisionError("unexpected")

    with pytest.raises(ZeroDivisionError):
        mean_thlb_for_geometry(
            geometry=object(),
            raster_src=object(),
            mask_fn=_unexpected_error_mask,
            np_module=np,
        )


def test_mean_thlb_for_geometry_returns_default_when_no_valid_cells() -> None:
    def _empty_valid_mask(
        _src: object, _shapes: list[object], crop: bool
    ) -> tuple[np.ndarray, None]:
        assert crop is True
        return np.array([[-1, -1, -1]]), None

    value = mean_thlb_for_geometry(
        geometry=object(),
        raster_src=object(),
        mask_fn=_empty_valid_mask,
        np_module=np,
        default_on_error=3.5,
    )
    assert value == 3.5


def test_plot_path_helpers() -> None:
    pdf_path, png_path = strata_plot_paths("8")
    tipsy_path = tipsy_vdyp_plot_path(23005, "08")
    configured_ylim = tipsy_vdyp_ylim_for_tsa("custom", configured=(0.0, 2000.0))
    default_ylim = tipsy_vdyp_ylim_for_tsa("08")

    assert pdf_path == Path("plots/strata-tsa08.pdf")
    assert png_path == Path("plots/strata-tsa08.png")
    assert tipsy_path == Path("plots/tipsy_vdyp_tsa08-23005.png")
    assert configured_ylim == (0.0, 2000.0)
    assert default_ylim == (0.0, 600.0)


def test_build_vdyp_cache_paths() -> None:
    paths = build_vdyp_cache_paths(
        tsa_code="08",
        vdyp_results_tsa_pickle_path_prefix="./data/vdyp_results-tsa",
        vdyp_curves_smooth_tsa_feather_path_prefix="./data/vdyp_curves_smooth-tsa",
    )

    assert paths["vdyp_results_tsa_pickle_path"] == Path(
        "./data/vdyp_results-tsa08.pkl"
    )
    assert paths["vdyp_curves_smooth_tsa_feather_path"] == Path(
        "./data/vdyp_curves_smooth-tsa08.feather"
    )


def test_build_strata_distribution_plot_config_defaults() -> None:
    cfg = build_strata_distribution_plot_config()

    assert isinstance(cfg, StrataDistributionPlotConfig)
    assert cfg.figsize == (8, 12)
    assert cfg.alpha == 0.2
    assert cfg.linewidth == 1.0
    assert cfg.inner == "box"
    assert cfg.width == 0.8
    assert cfg.bw == "scott"
    assert cfg.cut == 0.0
    assert cfg.site_index_xlim == (0, 30)
    assert cfg.site_index_focus_quantiles == (0.02, 0.98)
    assert cfg.site_index_focus_padding == 0.75
    assert cfg.stripplot_alpha == 0.15
    assert cfg.stripplot_size == 1.4
    assert cfg.stripplot_max_points == 3000
    assert cfg.stripplot_min_points_per_stratum == 1
    assert cfg.stripplot_random_seed == 19
    assert cfg.write_pdf is False


def test_resolve_strata_plot_ordering_abundance_and_lex_modes() -> None:
    strata_df = pd.DataFrame(
        {
            "totalarea_p": [0.6, 0.4],
        },
        index=["B2", "A1"],
    )

    props_default, labels_default = resolve_strata_plot_ordering(
        strata_df=strata_df,
        sort_lex=False,
    )
    props_lex, labels_lex = resolve_strata_plot_ordering(
        strata_df=strata_df,
        sort_lex=True,
    )

    assert props_default == [0.6, 0.4]
    assert labels_default == ["B2", "A1"]
    assert props_lex == [0.4, 0.6]
    assert labels_lex == ["A1", "B2"]


def test_plot_strata_site_index_diagnostics_calls_hist_and_scatter() -> None:
    class _FakeAx:
        def __init__(self) -> None:
            self.xlim_calls: list[list[float]] = []

        def set_xlim(self, value: list[float]) -> None:
            self.xlim_calls.append(value)

    class _SiteIndexSeries:
        def __init__(self, ax: _FakeAx) -> None:
            self.ax = ax
            self.hist_bins: list[list[float]] = []

        def hist(self, bins: list[float]) -> _FakeAx:
            self.hist_bins.append(bins)
            return self.ax

    class _FakeStrata:
        def __init__(self) -> None:
            self.ax = _FakeAx()
            self.site_index_median = _SiteIndexSeries(self.ax)
            self.totalarea_p = [0.4, 0.6]
            self.median_si = [12.0, 18.0]

    class _FakeNp:
        @staticmethod
        def arange(stop: float, step: float = 1.0) -> list[float]:
            vals = []
            v = 0.0
            while v < stop:
                vals.append(v)
                v += step
            return vals

    class _FakePlt:
        def __init__(self) -> None:
            self.scatter_calls: list[tuple[object, object]] = []

        def scatter(self, x: object, y: object) -> None:
            self.scatter_calls.append((x, y))

    strata = _FakeStrata()
    fake_plt = _FakePlt()
    plot_strata_site_index_diagnostics(
        strata_df=strata,
        np_module=_FakeNp(),
        plt_module=fake_plt,
    )

    assert strata.site_index_median.hist_bins == [[float(i) for i in range(25)]]
    assert strata.ax.xlim_calls == [[0.0, 26.0]]
    assert fake_plt.scatter_calls == [([0.4, 0.6], [12.0, 18.0])]


def test_render_strata_distribution_plot_uses_helper_config_and_paths() -> None:
    class _FakeAxis:
        def __init__(self) -> None:
            self.xlabel_calls: list[str] = []
            self.xlim_calls: list[tuple[float, float]] = []

        def twiny(self) -> "_FakeAxis":
            return self

        def set_xlabel(self, value: str) -> None:
            self.xlabel_calls.append(value)

        def set_xlim(self, value: tuple[float, float]) -> None:
            self.xlim_calls.append(value)

    class _FakePlt:
        def __init__(self) -> None:
            self.subplots_calls: list[tuple[float, float]] = []
            self.savefig_calls: list[tuple[Path, dict[str, object]]] = []

        def subplots(self, *, figsize: tuple[float, float]) -> tuple[None, _FakeAxis]:
            self.subplots_calls.append(figsize)
            return None, _FakeAxis()

        def savefig(self, path: Path, **kwargs: object) -> None:
            self.savefig_calls.append((path, dict(kwargs)))

    class _FakeSns:
        def __init__(self) -> None:
            self.barplot_calls = 0
            self.violinplot_calls = 0
            self.stripplot_calls = 0
            self.violin_rows: list[int] = []
            self.strip_rows: list[int] = []

        def barplot(self, **_kwargs: object) -> None:
            self.barplot_calls += 1

        def violinplot(self, **kwargs: object) -> None:
            self.violinplot_calls += 1
            self.violin_rows.append(len(kwargs["data"]))  # type: ignore[arg-type]

        def stripplot(self, **kwargs: object) -> None:
            self.stripplot_calls += 1
            self.strip_rows.append(len(kwargs["data"]))  # type: ignore[arg-type]

    cfg = build_strata_distribution_plot_config()
    fake_plt = _FakePlt()
    fake_sns = _FakeSns()
    metadata = render_strata_distribution_plot(
        tsa_code="08",
        f_table=pd.DataFrame({"stratum": ["S1"], "SITE_INDEX": [20.0]}),
        stratum_col="stratum",
        labels=["S1"],
        stratum_props=[1.0],
        plot_config=cfg,
        sns_module=fake_sns,
        plt_module=fake_plt,
        strata_plot_paths_fn=lambda _tsa: (
            Path("plots/strata-tsa08.pdf"),
            Path("plots/strata-tsa08.png"),
        ),
    )

    assert fake_sns.barplot_calls == 1
    assert fake_sns.violinplot_calls == 1
    assert fake_sns.stripplot_calls == 1
    assert fake_sns.violin_rows == [1]
    assert fake_sns.strip_rows == [1]
    assert fake_plt.subplots_calls == [cfg.figsize]
    assert len(fake_plt.savefig_calls) == 1
    assert fake_plt.savefig_calls[0][0] == Path("plots/strata-tsa08.png")
    assert metadata.total_points == 1
    assert metadata.window_points == 1
    assert metadata.strip_points_plotted == 1
    assert metadata.clipped_total_count == 0
    assert metadata.site_index_xlim == (0.0, 21.0)


def test_render_strata_distribution_plot_clips_outliers_and_thins_strip_points() -> (
    None
):
    class _FakeAxis:
        def __init__(self) -> None:
            self.xlim_calls: list[tuple[float, float]] = []

        def twiny(self) -> "_FakeAxis":
            return self

        def set_xlabel(self, _value: str) -> None:
            return None

        def set_xlim(self, value: tuple[float, float]) -> None:
            self.xlim_calls.append(value)

    class _FakePlt:
        def subplots(self, *, figsize: tuple[float, float]) -> tuple[None, _FakeAxis]:
            return None, _FakeAxis()

        def savefig(self, _path: Path, **_kwargs: object) -> None:
            return None

    class _FakeSns:
        def __init__(self) -> None:
            self.violin_rows = 0
            self.strip_rows = 0

        def barplot(self, **_kwargs: object) -> None:
            return None

        def violinplot(self, **kwargs: object) -> None:
            self.violin_rows = len(kwargs["data"])  # type: ignore[arg-type]

        def stripplot(self, **kwargs: object) -> None:
            self.strip_rows = len(kwargs["data"])  # type: ignore[arg-type]

    cfg = build_strata_distribution_plot_config(
        stripplot_max_points=25,
        site_index_focus_quantiles=(0.05, 0.95),
        site_index_focus_padding=0.5,
        site_index_xlim=(0, 30),
    )

    core = np.linspace(10.0, 20.0, 200)
    site_index = np.concatenate([core, np.array([45.0, 60.0])])
    f_table = pd.DataFrame(
        {
            "stratum": ["S1"] * len(site_index),
            "SITE_INDEX": site_index,
        }
    )
    fake_sns = _FakeSns()
    metadata = render_strata_distribution_plot(
        tsa_code="29",
        f_table=f_table,
        stratum_col="stratum",
        labels=["S1"],
        stratum_props=[1.0],
        plot_config=cfg,
        sns_module=fake_sns,
        plt_module=_FakePlt(),
        strata_plot_paths_fn=lambda _tsa: (
            Path("plots/strata-tsa29.pdf"),
            Path("plots/strata-tsa29.png"),
        ),
    )

    assert metadata.total_points == 202
    assert metadata.clipped_high_count == 2
    assert metadata.clipped_low_count == 0
    assert metadata.clipped_total_count == 2
    assert metadata.window_points == 200
    assert metadata.strip_points_plotted <= 25
    assert metadata.site_index_xlim[0] == 0.0
    assert fake_sns.violin_rows == 200
    assert fake_sns.strip_rows <= 25


def test_render_strata_distribution_plot_can_optionally_write_pdf() -> None:
    class _FakeAxis:
        def twiny(self) -> "_FakeAxis":
            return self

        def set_xlabel(self, _value: str) -> None:
            return None

        def set_xlim(self, _value: tuple[float, float]) -> None:
            return None

    class _FakePlt:
        def __init__(self) -> None:
            self.savefig_calls: list[Path] = []

        def subplots(self, *, figsize: tuple[float, float]) -> tuple[None, _FakeAxis]:
            _ = figsize
            return None, _FakeAxis()

        def savefig(self, path: Path, **_kwargs: object) -> None:
            self.savefig_calls.append(path)

    class _FakeSns:
        def barplot(self, **_kwargs: object) -> None:
            return None

        def violinplot(self, **_kwargs: object) -> None:
            return None

        def stripplot(self, **_kwargs: object) -> None:
            return None

    cfg = build_strata_distribution_plot_config(write_pdf=True)
    fake_plt = _FakePlt()
    render_strata_distribution_plot(
        tsa_code="08",
        f_table=pd.DataFrame({"stratum": ["S1"], "SITE_INDEX": [20.0]}),
        stratum_col="stratum",
        labels=["S1"],
        stratum_props=[1.0],
        plot_config=cfg,
        sns_module=_FakeSns(),
        plt_module=fake_plt,
        strata_plot_paths_fn=lambda _tsa: (
            Path("plots/strata-tsa08.pdf"),
            Path("plots/strata-tsa08.png"),
        ),
    )
    assert fake_plt.savefig_calls == [
        Path("plots/strata-tsa08.pdf"),
        Path("plots/strata-tsa08.png"),
    ]


def test_build_pipeline_run_config_normalizes_tsa_values() -> None:
    cfg = build_pipeline_run_config(
        tsa_list=[8, "16"],
        resume=True,
        debug_rows=25,
        run_id="test123",
        log_dir=Path("vdyp_io/logs"),
    )
    assert cfg.tsa_list == ["08", "16"]
    assert cfg.resume is True
    assert cfg.debug_rows == 25
    assert cfg.run_id == "test123"


def test_load_pipeline_run_profile_from_yaml(tmp_path: Path) -> None:
    profile_path = tmp_path / "run_profile.yaml"
    profile_path.write_text(
        "\n".join(
            [
                "selection:",
                "  tsa: ['8', '16']",
                "  strata: ['SBSdk', 'IDF']",
                "  boundary_path: data/bc/cfa/k3z/CFA K3Z Tenure.shp",
                "  boundary_layer: tenure",
                "  boundary_code: k3z",
                "  stratification:",
                "    bec_grouping: subzone",
                "    species_combo_count: 2",
                "    include_tm_species2_for_single: false",
                "    top_area_coverage: 0.95",
                "    target_nstrata: 4",
                "plots:",
                "  tipsy_vdyp_ylim: [0.0, 2000.0]",
                "vdyp_curve_selection:",
                "  force_tail_blend: true",
                "  enable_late_gate_rescue: false",
                "source_paths:",
                "  vri_rel_candidates:",
                "    - bc/vri/2025/VEG_COMP_LYR_R1_POLY_2025.gdb",
                "    - bc/vri/2024/VEG_COMP_LYR_R1_POLY_2024.gdb",
                "  vdyp_input_rel_candidates:",
                "    - bc/vri/2025/VEG_COMP_VDYP7_INPUT_POLY_AND_LAYER_2025.gdb",
                "    - bc/vri/2024/VEG_COMP_VDYP7_INPUT_POLY_AND_LAYER_2024.gdb",
                "modes:",
                "  resume: true",
                "  dry_run: false",
                "  verbose: true",
                "  skip_checks: true",
                "  debug_rows: 25",
                "  vdyp_sampling_mode: all",
                "  vdyp_two_pass_rebin: true",
                "  vdyp_min_stands_per_si_bin: 10",
                "  vdyp_toe_shift_years: 15.0",
                "  managed_curve_mode: vdyp_transform",
                "  managed_curve_x_scale: 0.8",
                "  managed_curve_y_scale: 1.2",
                "  managed_curve_truncate_at_culm: true",
                "  managed_curve_max_age: 300",
                "  yield_assumptions_path: config/tsr/yield_assumptions.yaml",
                "run:",
                "  run_id: cfg001",
                "  log_dir: vdyp_io/custom_logs",
                "",
            ]
        ),
        encoding="utf-8",
    )

    profile = load_pipeline_run_profile(profile_path)
    assert profile.tsa_list == ["8", "16"]
    assert profile.strata_list == ["SBSdk", "IDF"]
    assert profile.resume is True
    assert profile.verbose is True
    assert profile.skip_checks is True
    assert profile.debug_rows == 25
    assert profile.run_id == "cfg001"
    assert profile.log_dir == Path("vdyp_io/custom_logs")
    assert profile.boundary_path == Path("data/bc/cfa/k3z/CFA K3Z Tenure.shp")
    assert profile.boundary_layer == "tenure"
    assert profile.boundary_code == "k3z"
    assert profile.strat_bec_grouping == "subzone"
    assert profile.strat_species_combo_count == 2
    assert profile.strat_include_tm_species2_for_single is False
    assert profile.strat_top_area_coverage == pytest.approx(0.95)
    assert profile.strat_target_nstrata == 4
    assert profile.tipsy_vdyp_ylim == (0.0, 2000.0)
    assert profile.vri_rel_candidates == [
        Path("bc/vri/2025/VEG_COMP_LYR_R1_POLY_2025.gdb"),
        Path("bc/vri/2024/VEG_COMP_LYR_R1_POLY_2024.gdb"),
    ]
    assert profile.vdyp_input_rel_candidates == [
        Path("bc/vri/2025/VEG_COMP_VDYP7_INPUT_POLY_AND_LAYER_2025.gdb"),
        Path("bc/vri/2024/VEG_COMP_VDYP7_INPUT_POLY_AND_LAYER_2024.gdb"),
    ]
    assert profile.vdyp_sampling_mode == "all"
    assert profile.vdyp_two_pass_rebin is True
    assert profile.vdyp_min_stands_per_si_bin == 10
    assert profile.vdyp_toe_shift_years == pytest.approx(15.0)
    assert profile.vdyp_force_tail_blend is True
    assert profile.vdyp_enable_late_gate_rescue is False
    assert profile.managed_curve_mode == "vdyp_transform"
    assert profile.managed_curve_x_scale == pytest.approx(0.8)
    assert profile.managed_curve_y_scale == pytest.approx(1.2)
    assert profile.managed_curve_truncate_at_culm is True
    assert profile.managed_curve_max_age == 300
    assert profile.yield_assumptions_path == Path("config/tsr/yield_assumptions.yaml")


def test_resolve_effective_run_options_merges_profile_and_cli() -> None:
    profile = load_pipeline_run_profile(Path("config/run_profile.example.yaml"))
    resolved = resolve_effective_run_options(
        tsa_list=["24"],
        resume=False,
        dry_run=False,
        verbose=False,
        skip_checks=False,
        debug_rows=None,
        run_id=None,
        log_dir=Path("runtime/logs"),
        profile=profile,
    )

    assert resolved.tsa_list == ["24"]
    assert resolved.strata_list == ["SBSdk", "IDFdk"]
    assert resolved.resume is True
    assert resolved.verbose is True
    assert resolved.skip_checks is True
    assert resolved.debug_rows == 250
    assert resolved.run_id == "dev-profile"
    assert resolved.log_dir == Path("runtime/profile_logs")
    assert resolved.boundary_path is None
    assert resolved.boundary_layer is None
    assert resolved.boundary_code is None
    assert resolved.strat_bec_grouping is None
    assert resolved.strat_species_combo_count is None
    assert resolved.strat_include_tm_species2_for_single is None
    assert resolved.strat_top_area_coverage is None
    assert resolved.strat_target_nstrata is None
    assert resolved.tipsy_vdyp_ylim is None
    assert resolved.vdyp_sampling_mode is None
    assert resolved.vdyp_two_pass_rebin is None
    assert resolved.vdyp_min_stands_per_si_bin is None
    assert resolved.vdyp_toe_shift_years is None
    assert resolved.vdyp_force_tail_blend is None
    assert resolved.vdyp_enable_late_gate_rescue is None
    assert resolved.managed_curve_mode is None
    assert resolved.managed_curve_x_scale is None
    assert resolved.managed_curve_y_scale is None
    assert resolved.managed_curve_truncate_at_culm is None
    assert resolved.managed_curve_max_age is None
    assert resolved.yield_assumptions_path is None


def test_load_pipeline_run_profile_rejects_invalid_root_type(tmp_path: Path) -> None:
    profile_path = tmp_path / "bad.json"
    profile_path.write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError, match="Run config root must be a mapping"):
        load_pipeline_run_profile(profile_path)


def test_load_pipeline_run_profile_rejects_invalid_vdyp_sampling_mode(
    tmp_path: Path,
) -> None:
    profile_path = tmp_path / "run_profile.yaml"
    profile_path.write_text("modes:\n  vdyp_sampling_mode: zero\n", encoding="utf-8")
    with pytest.raises(ValueError, match="modes.vdyp_sampling_mode"):
        load_pipeline_run_profile(profile_path)


def test_load_pipeline_run_profile_rejects_non_positive_vdyp_min_stands(
    tmp_path: Path,
) -> None:
    profile_path = tmp_path / "run_profile.yaml"
    profile_path.write_text(
        "modes:\n  vdyp_min_stands_per_si_bin: 0\n", encoding="utf-8"
    )
    with pytest.raises(ValueError, match="modes.vdyp_min_stands_per_si_bin"):
        load_pipeline_run_profile(profile_path)


def test_load_pipeline_run_profile_rejects_invalid_vdyp_toe_shift_years(
    tmp_path: Path,
) -> None:
    profile_path = tmp_path / "run_profile.yaml"
    profile_path.write_text(
        "modes:\n  vdyp_toe_shift_years: not-a-number\n", encoding="utf-8"
    )
    with pytest.raises(ValueError, match="modes.vdyp_toe_shift_years"):
        load_pipeline_run_profile(profile_path)


def test_load_pipeline_run_profile_rejects_invalid_managed_curve_mode(
    tmp_path: Path,
) -> None:
    profile_path = tmp_path / "run_profile.yaml"
    profile_path.write_text("modes:\n  managed_curve_mode: bogus\n", encoding="utf-8")
    with pytest.raises(ValueError, match="modes.managed_curve_mode"):
        load_pipeline_run_profile(profile_path)


def test_build_legacy_execution_plan_resolves_env_and_paths(tmp_path: Path) -> None:
    script_path = tmp_path / "00_data-prep.py"
    script_path.write_text("# test\n", encoding="utf-8")
    cfg = build_pipeline_run_config(
        tsa_list=["8", "24"],
        resume=False,
        debug_rows=100,
        run_id="runabc",
        log_dir=tmp_path / "logs",
        output_root=tmp_path / "outputs",
        run_config_path=tmp_path / "config" / "run_profile.yaml",
        run_config_sha256="abc123",
        boundary_path=Path("data/bc/cfa/k3z/CFA K3Z Tenure.shp"),
        boundary_layer="tenure",
        boundary_code="k3z",
        strat_bec_grouping="subzone",
        strat_species_combo_count=2,
        strat_include_tm_species2_for_single=False,
        strat_top_area_coverage=0.95,
        strat_target_nstrata=4,
        tipsy_vdyp_ylim=(0.0, 2000.0),
        vdyp_sampling_mode="all",
        vdyp_two_pass_rebin=True,
        vdyp_min_stands_per_si_bin=10,
        vdyp_toe_shift_years=15.0,
        vdyp_force_tail_blend=True,
        vdyp_enable_late_gate_rescue=False,
        managed_curve_mode="vdyp_transform",
        managed_curve_x_scale=0.8,
        managed_curve_y_scale=1.2,
        managed_curve_truncate_at_culm=True,
        managed_curve_max_age=300,
        yield_assumptions_path=Path("config/tsr/yield_assumptions.yaml"),
        vri_rel_candidates=[
            Path("bc/vri/2025/VEG_COMP_LYR_R1_POLY_2025.gdb"),
            Path("bc/vri/2024/VEG_COMP_LYR_R1_POLY_2024.gdb"),
        ],
        vdyp_input_rel_candidates=[
            Path("bc/vri/2025/VEG_COMP_VDYP7_INPUT_POLY_AND_LAYER_2025.gdb"),
            Path("bc/vri/2024/VEG_COMP_VDYP7_INPUT_POLY_AND_LAYER_2024.gdb"),
        ],
    )

    plan = build_legacy_execution_plan(
        run_config=cfg,
        script_path=script_path,
        python_executable="/usr/bin/python3",
        base_env={},
    )

    assert plan.run_id == "runabc"
    assert plan.tsa_list == ["08", "24"]
    assert (
        plan.manifest_path == (tmp_path / "logs" / "run_manifest-runabc.json").resolve()
    )
    assert plan.env["FEMIC_TSA_LIST"] == "08,24"
    assert plan.env["FEMIC_RESUME"] == "0"
    assert plan.env["FEMIC_DEBUG_ROWS"] == "100"
    assert plan.env["FEMIC_RUN_ID"] == "runabc"
    assert plan.env["FEMIC_OUTPUT_ROOT"] == str(tmp_path / "outputs")
    assert plan.env["FEMIC_INSTANCE_ROOT"] == str(script_path.parent.resolve())
    assert plan.env["PYTHONUNBUFFERED"] == "1"
    assert plan.env["FEMIC_RUN_CONFIG_PATH"] == str(
        tmp_path / "config" / "run_profile.yaml"
    )
    assert plan.env["FEMIC_RUN_CONFIG_SHA256"] == "abc123"
    assert plan.env["FEMIC_BOUNDARY_PATH"] == "data/bc/cfa/k3z/CFA K3Z Tenure.shp"
    assert plan.env["FEMIC_BOUNDARY_LAYER"] == "tenure"
    assert plan.env["FEMIC_BOUNDARY_CODE"] == "k3z"
    assert plan.env["FEMIC_STRAT_BEC_GROUPING"] == "subzone"
    assert plan.env["FEMIC_STRAT_SPECIES_COMBO_COUNT"] == "2"
    assert plan.env["FEMIC_STRAT_INCLUDE_TM_SPECIES2_FOR_SINGLE"] == "0"
    assert plan.env["FEMIC_STRAT_TOP_AREA_COVERAGE"] == "0.95"
    assert plan.env["FEMIC_STRAT_TARGET_NSTRATA"] == "4"
    assert plan.env["FEMIC_TIPSY_VDYP_YLIM"] == "0.0,2000.0"
    assert plan.env["FEMIC_VDYP_SAMPLING_MODE"] == "all"
    assert plan.env["FEMIC_VDYP_TWO_PASS_REBIN"] == "1"
    assert plan.env["FEMIC_VDYP_MIN_STANDS_PER_SI_BIN"] == "10"
    assert plan.env["FEMIC_VDYP_TOE_SHIFT_YEARS"] == "15.0"
    assert plan.env["FEMIC_VDYP_FORCE_TAIL_BLEND"] == "1"
    assert plan.env["FEMIC_VDYP_ENABLE_LATE_GATE_RESCUE"] == "0"
    assert plan.env["FEMIC_MANAGED_CURVE_MODE"] == "vdyp_transform"
    assert plan.env["FEMIC_MANAGED_CURVE_X_SCALE"] == "0.8"
    assert plan.env["FEMIC_MANAGED_CURVE_Y_SCALE"] == "1.2"
    assert plan.env["FEMIC_MANAGED_CURVE_TRUNCATE_AT_CULM"] == "1"
    assert plan.env["FEMIC_MANAGED_CURVE_MAX_AGE"] == "300"
    assert plan.env["FEMIC_VRI_REL_CANDIDATES"] == os.pathsep.join(
        [
            "bc/vri/2025/VEG_COMP_LYR_R1_POLY_2025.gdb",
            "bc/vri/2024/VEG_COMP_LYR_R1_POLY_2024.gdb",
        ]
    )
    assert plan.env["FEMIC_VDYP_INPUT_REL_CANDIDATES"] == os.pathsep.join(
        [
            "bc/vri/2025/VEG_COMP_VDYP7_INPUT_POLY_AND_LAYER_2025.gdb",
            "bc/vri/2024/VEG_COMP_VDYP7_INPUT_POLY_AND_LAYER_2024.gdb",
        ]
    )
    assert plan.cmd == ["/usr/bin/python3", str(script_path)]
    assert plan.working_dir == script_path.parent.resolve()


def test_file_sha256_is_deterministic(tmp_path: Path) -> None:
    path = tmp_path / "a.txt"
    path.write_text("abc", encoding="utf-8")
    assert (
        file_sha256(path)
        == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    )
