from __future__ import annotations

import json
import os
from pathlib import Path
import pickle

import pandas as pd

from femic.pipeline.tipsy import (
    BTCRunResult,
    compute_file_sha256,
    tipsy_output_input_fingerprint_path,
)
from femic.workflows.legacy import (
    BTCPostTipsyRunResult,
    PostTipsyBundleResult,
    PostTipsyBundleRunResult,
    _load_species_universe_for_tsas,
    run_btc_and_post_tipsy_bundle_with_manifest,
    run_post_tipsy_bundle,
    run_post_tipsy_bundle_with_manifest,
)


def test_run_post_tipsy_bundle_builds_bundle_from_cached_artifacts(
    tmp_path: Path,
) -> None:
    data_root = tmp_path / "data"
    data_root.mkdir(parents=True, exist_ok=True)
    tsa = "29"

    results_for_tsa = [
        (0, "IDF_FD", {"L": {"ss": None}, "M": {"ss": None}, "H": {"ss": None}})
    ]
    with (data_root / f"vdyp_prep-tsa{tsa}.pkl").open("wb") as fh:
        pickle.dump(results_for_tsa, fh)

    vdyp_curves = pd.DataFrame(
        {
            "stratum_code": [
                "IDF_FD",
                "IDF_FD",
                "IDF_FD",
                "IDF_FD",
                "IDF_FD",
                "IDF_FD",
            ],
            "si_level": ["L", "L", "M", "M", "H", "H"],
            "age": [0, 10, 0, 10, 0, 10],
            "volume": [0.0, 10.0, 0.0, 20.0, 0.0, 30.0],
        }
    )
    vdyp_curves.to_feather(data_root / f"vdyp_curves_smooth-tsa{tsa}.feather")

    pd.DataFrame({"AU": [21000]}).to_excel(
        data_root / f"tipsy_params_tsa{tsa}.xlsx",
        index=False,
        sheet_name="TIPSY_inputTBL",
    )
    (data_root / f"04_output-tsa{tsa}.csv").write_text(
        "placeholder\n", encoding="utf-8"
    )

    def _fake_run_01b(
        *,
        tsa: str,
        results,
        au_scsi,
        tipsy_curves,
        vdyp_curves_smooth,
        runtime_config,
    ) -> None:
        _ = (results, au_scsi, vdyp_curves_smooth, runtime_config)
        tipsy_df = pd.DataFrame(
            {
                "AU": [21000, 21000, 22000, 22000, 23000, 23000],
                "Age": [0, 10, 0, 10, 0, 10],
                "Yield": [0.0, 12.0, 0.0, 24.0, 0.0, 36.0],
                "Height": [0.0, 2.0, 0.0, 3.0, 0.0, 4.0],
                "DBHq": [0.0, 1.0, 0.0, 1.5, 0.0, 2.0],
                "TPH": [1000, 900, 1000, 900, 1000, 900],
            }
        ).set_index(["AU", "Age"])
        tipsy_curves[tsa] = tipsy_df
        tipsy_df.reset_index().to_csv(
            data_root / f"tipsy_curves_tsa{tsa}.csv",
            index=False,
        )
        pd.DataFrame({"AU": [21000], "FD": [100.0]}).to_csv(
            data_root / f"tipsy_sppcomp_tsa{tsa}.csv",
            index=False,
        )

    result = run_post_tipsy_bundle(
        tsa_list=[tsa],
        repo_root=tmp_path,
        data_root=data_root,
        run_01b_fn=_fake_run_01b,
        message_fn=lambda _msg: None,
    )

    assert result.tsa_list == [tsa]
    assert result.au_rows == 3
    assert result.curve_rows == 6
    assert result.curve_points_rows == 12
    assert result.au_table_path.is_file()
    assert result.curve_table_path.is_file()
    assert result.curve_points_table_path.is_file()


def test_load_species_universe_can_fallback_to_checkpoint1_case_artifact(
    tmp_path: Path,
) -> None:
    data_root = tmp_path / "data"
    data_root.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        {
            "tsa_code": ["k3z", "k3z", "99"],
            "SPECIES_CD_1": ["FD", "HW", "SX"],
            "SPECIES_PCT_1": [60.0, 50.0, 100.0],
            "SPECIES_CD_2": ["HW", "FD", ""],
            "SPECIES_PCT_2": [40.0, 50.0, 0.0],
            "SPECIES_CD_3": ["", "", ""],
            "SPECIES_PCT_3": [0.0, 0.0, 0.0],
            "SPECIES_CD_4": ["", "", ""],
            "SPECIES_PCT_4": [0.0, 0.0, 0.0],
            "SPECIES_CD_5": ["", "", ""],
            "SPECIES_PCT_5": [0.0, 0.0, 0.0],
            "SPECIES_CD_6": ["", "", ""],
            "SPECIES_PCT_6": [0.0, 0.0, 0.0],
        }
    ).to_feather(data_root / "ria_vri_vclr1p_checkpoint1-tsak3z.feather")

    messages: list[str] = []
    out = _load_species_universe_for_tsas(
        data_root=data_root,
        tsa_list=["k3z"],
        message_fn=messages.append,
    )

    assert out == ["FD", "HW"]
    assert any("checkpoint1-tsak3z" in msg for msg in messages)


def test_run_post_tipsy_bundle_can_fallback_to_persisted_au_table_when_prep_missing(
    tmp_path: Path,
) -> None:
    data_root = tmp_path / "data"
    bundle_root = data_root / "model_input_bundle"
    data_root.mkdir(parents=True, exist_ok=True)
    bundle_root.mkdir(parents=True, exist_ok=True)
    tsa = "k3z"

    pd.DataFrame(
        {
            "stratum_code": [
                "CWHvm_HW+FDC",
                "CWHvm_HW+FDC",
                "CWHvm_HW+FDC",
                "CWHvm_HW+FDC",
            ],
            "si_level": ["L", "L", "M", "M"],
            "age": [0, 10, 0, 10],
            "volume": [0.0, 10.0, 0.0, 12.0],
        }
    ).to_feather(data_root / f"vdyp_curves_smooth-tsa{tsa}.feather")
    pd.DataFrame({"AU": [21000]}).to_excel(
        data_root / f"tipsy_params_tsa{tsa}.xlsx",
        index=False,
        sheet_name="TIPSY_inputTBL",
    )
    (data_root / f"04_output-tsa{tsa}.csv").write_text(
        "feature_id,MVcon_0,MVdec_0,HTcon_0,HTdec_0,gVol_0,CC_0\n21000,0,0,0,0,0,0\n",
        encoding="utf-8",
    )
    pd.DataFrame(
        {
            "au_id": [985501000],
            "tsa": [tsa],
            "stratum_code": ["CWHvm_HW+FDC"],
            "si_level": ["L"],
            "canfi_species": [402],
            "unmanaged_curve_id": [985501000],
            "managed_curve_id": [985521000],
        }
    ).to_csv(bundle_root / "au_table.csv", index=False)

    seen_au_scsi: dict[int, tuple[str, str]] = {}

    def _fake_run_01b(
        *,
        tsa: str,
        results,
        au_scsi,
        tipsy_curves,
        vdyp_curves_smooth,
        runtime_config,
    ) -> None:
        _ = (results, vdyp_curves_smooth, runtime_config)
        seen_au_scsi.update(au_scsi[tsa])
        tipsy_df = pd.DataFrame(
            {
                "AU": [21000, 21000],
                "Age": [0, 10],
                "Yield": [0.0, 5.0],
                "Height": [0.0, 2.0],
                "DBHq": [0.0, 1.0],
                "TPH": [0.0, 900.0],
            }
        ).set_index(["AU", "Age"])
        tipsy_curves[tsa] = tipsy_df
        tipsy_df.reset_index().to_csv(
            data_root / f"tipsy_curves_tsa{tsa}.csv",
            index=False,
        )
        pd.DataFrame({"AU": [21000], "HW": [100.0]}).to_csv(
            data_root / f"tipsy_sppcomp_tsa{tsa}.csv",
            index=False,
        )

    result = run_post_tipsy_bundle(
        tsa_list=[tsa],
        repo_root=tmp_path,
        data_root=data_root,
        run_01b_fn=_fake_run_01b,
        message_fn=lambda _msg: None,
    )

    assert seen_au_scsi == {1000: ("CWHvm_HW+FDC", "L")}
    assert result.tsa_list == [tsa]
    assert result.au_table_path.is_file()


def test_run_post_tipsy_bundle_can_rebuild_vdyp_species_props_from_vdyp_layer_when_prep_missing(
    tmp_path: Path,
) -> None:
    data_root = tmp_path / "data"
    bundle_root = data_root / "model_input_bundle"
    data_root.mkdir(parents=True, exist_ok=True)
    bundle_root.mkdir(parents=True, exist_ok=True)
    tsa = "k3z"

    pd.DataFrame(
        {
            "stratum_code": ["CWHvm_DR+HW", "CWHvm_DR+HW"],
            "si_level": ["M", "M"],
            "age": [0, 10],
            "volume": [0.0, 12.0],
        }
    ).to_feather(data_root / f"vdyp_curves_smooth-tsa{tsa}.feather")
    pd.DataFrame({"AU": [22004]}).to_excel(
        data_root / f"tipsy_params_tsa{tsa}.xlsx",
        index=False,
        sheet_name="TIPSY_inputTBL",
    )
    (data_root / f"04_output-tsa{tsa}.csv").write_text(
        "feature_id,MVcon_0,MVdec_0,HTcon_0,HTdec_0,gVol_0,CC_0\n22004,0,0,0,0,0,0\n",
        encoding="utf-8",
    )
    pd.DataFrame(
        {
            "au_id": [985502004],
            "tsa": [tsa],
            "stratum_code": ["CWHvm_DR+HW"],
            "si_level": ["M"],
            "canfi_species": [402],
            "unmanaged_curve_id": [985502004],
            "managed_curve_id": [985522004],
        }
    ).to_csv(bundle_root / "au_table.csv", index=False)
    pd.DataFrame(
        {
            "SPECIES_CD_1": ["DR", "DR"],
            "SPECIES_PCT_1": [70.0, 60.0],
            "SPECIES_CD_2": ["HW", "HW"],
            "SPECIES_PCT_2": [20.0, 30.0],
            "SPECIES_CD_3": ["FDC", "CW"],
            "SPECIES_PCT_3": [10.0, 10.0],
            "SPECIES_CD_4": ["", ""],
            "SPECIES_PCT_4": [0.0, 0.0],
            "SPECIES_CD_5": ["", ""],
            "SPECIES_PCT_5": [0.0, 0.0],
            "SPECIES_CD_6": ["", ""],
            "SPECIES_PCT_6": [0.0, 0.0],
        }
    ).to_feather(data_root / f"vdyp_lyr-tsa{tsa}.feather")
    pd.DataFrame(
        {
            "tsa_code": [tsa],
            "SPECIES_CD_1": ["DR"],
            "SPECIES_PCT_1": [70.0],
            "SPECIES_CD_2": ["HW"],
            "SPECIES_PCT_2": [20.0],
            "SPECIES_CD_3": ["FDC"],
            "SPECIES_PCT_3": [10.0],
            "SPECIES_CD_4": [""],
            "SPECIES_PCT_4": [0.0],
            "SPECIES_CD_5": [""],
            "SPECIES_PCT_5": [0.0],
            "SPECIES_CD_6": [""],
            "SPECIES_PCT_6": [0.0],
        }
    ).to_feather(data_root / f"ria_vri_vclr1p_checkpoint1-tsa{tsa}.feather")

    def _fake_run_01b(
        *,
        tsa: str,
        results,
        au_scsi,
        tipsy_curves,
        vdyp_curves_smooth,
        runtime_config,
    ) -> None:
        _ = (results, au_scsi, vdyp_curves_smooth, runtime_config)
        tipsy_df = pd.DataFrame(
            {
                "AU": [22004, 22004],
                "Age": [0, 10],
                "Yield": [0.0, 5.0],
                "Height": [0.0, 2.0],
                "DBHq": [0.0, 1.0],
                "TPH": [0.0, 900.0],
            }
        ).set_index(["AU", "Age"])
        tipsy_curves[tsa] = tipsy_df
        tipsy_df.reset_index().to_csv(
            data_root / f"tipsy_curves_tsa{tsa}.csv",
            index=False,
        )
        pd.DataFrame({"AU": [22004], "CW": [10.0], "FD": [70.0], "HW": [20.0]}).to_csv(
            data_root / f"tipsy_sppcomp_tsa{tsa}.csv",
            index=False,
        )

    result = run_post_tipsy_bundle(
        tsa_list=[tsa],
        repo_root=tmp_path,
        data_root=data_root,
        run_01b_fn=_fake_run_01b,
        message_fn=lambda _msg: None,
    )

    curve_table = pd.read_csv(result.curve_table_path)
    curve_points = pd.read_csv(result.curve_points_table_path)
    unmanaged_dr_id = curve_table.loc[
        curve_table["curve_type"] == "untreated_species_prop_DR", "curve_id"
    ].iloc[0]
    unmanaged_dr_y = curve_points.loc[
        curve_points["curve_id"] == unmanaged_dr_id, "y"
    ].iloc[0]
    treated_dr_id = curve_table.loc[
        curve_table["curve_type"] == "treated_species_prop_DR", "curve_id"
    ].iloc[0]
    treated_dr_y = curve_points.loc[
        curve_points["curve_id"] == treated_dr_id, "y"
    ].iloc[0]

    assert unmanaged_dr_y > 0.0
    assert treated_dr_y > 0.0


def test_run_post_tipsy_bundle_emits_species_prop_curves_from_checkpoint1_case_artifact(
    tmp_path: Path,
) -> None:
    data_root = tmp_path / "data"
    data_root.mkdir(parents=True, exist_ok=True)
    tsa = "k3z"

    results_for_tsa = [
        (
            0,
            "CWHvm_HW+FDC",
            {
                "L": {"species": {"HW": {"pct": 70.0}, "FD": {"pct": 30.0}}},
                "M": {"species": {"HW": {"pct": 70.0}, "FD": {"pct": 30.0}}},
                "H": {"species": {"HW": {"pct": 70.0}, "FD": {"pct": 30.0}}},
            },
        )
    ]
    with (data_root / f"vdyp_prep-tsa{tsa}.pkl").open("wb") as fh:
        pickle.dump(results_for_tsa, fh)

    pd.DataFrame(
        {
            "tsa_code": ["k3z"],
            "SPECIES_CD_1": ["HW"],
            "SPECIES_PCT_1": [70.0],
            "SPECIES_CD_2": ["FD"],
            "SPECIES_PCT_2": [30.0],
            "SPECIES_CD_3": [""],
            "SPECIES_PCT_3": [0.0],
            "SPECIES_CD_4": [""],
            "SPECIES_PCT_4": [0.0],
            "SPECIES_CD_5": [""],
            "SPECIES_PCT_5": [0.0],
            "SPECIES_CD_6": [""],
            "SPECIES_PCT_6": [0.0],
        }
    ).to_feather(data_root / "ria_vri_vclr1p_checkpoint1-tsak3z.feather")

    pd.DataFrame(
        {
            "stratum_code": [
                "CWHvm_HW+FDC",
                "CWHvm_HW+FDC",
                "CWHvm_HW+FDC",
                "CWHvm_HW+FDC",
                "CWHvm_HW+FDC",
                "CWHvm_HW+FDC",
            ],
            "si_level": ["L", "L", "M", "M", "H", "H"],
            "age": [0, 10, 0, 10, 0, 10],
            "volume": [0.0, 10.0, 0.0, 11.0, 0.0, 12.0],
        }
    ).to_feather(data_root / f"vdyp_curves_smooth-tsa{tsa}.feather")
    pd.DataFrame({"AU": [21000]}).to_excel(
        data_root / f"tipsy_params_tsa{tsa}.xlsx",
        index=False,
        sheet_name="TIPSY_inputTBL",
    )
    (data_root / f"04_output-tsa{tsa}.csv").write_text(
        "feature_id,MVcon_0,MVdec_0,HTcon_0,HTdec_0,gVol_0,CC_0\n21000,0,0,0,0,0,0\n",
        encoding="utf-8",
    )

    def _fake_run_01b(
        *,
        tsa: str,
        results,
        au_scsi,
        tipsy_curves,
        vdyp_curves_smooth,
        runtime_config,
    ) -> None:
        _ = (results, au_scsi, vdyp_curves_smooth, runtime_config)
        tipsy_df = pd.DataFrame(
            {
                "AU": [21000, 21000, 22000, 22000, 23000, 23000],
                "Age": [0, 10, 0, 10, 0, 10],
                "Yield": [0.0, 12.0, 0.0, 24.0, 0.0, 36.0],
                "Height": [0.0, 2.0, 0.0, 3.0, 0.0, 4.0],
                "DBHq": [0.0, 1.0, 0.0, 1.5, 0.0, 2.0],
                "TPH": [1000, 900, 1000, 900, 1000, 900],
            }
        ).set_index(["AU", "Age"])
        tipsy_curves[tsa] = tipsy_df
        tipsy_df.reset_index().to_csv(
            data_root / f"tipsy_curves_tsa{tsa}.csv",
            index=False,
        )
        pd.DataFrame({"AU": [21000], "HW": [70.0], "FD": [30.0]}).to_csv(
            data_root / f"tipsy_sppcomp_tsa{tsa}.csv",
            index=False,
        )

    result = run_post_tipsy_bundle(
        tsa_list=[tsa],
        repo_root=tmp_path,
        data_root=data_root,
        run_01b_fn=_fake_run_01b,
        message_fn=lambda _msg: None,
    )

    curve_table = pd.read_csv(result.curve_table_path)
    curve_types = set(curve_table["curve_type"].tolist())
    assert "untreated_species_prop_FD" in curve_types
    assert "untreated_species_prop_HW" in curve_types
    assert "treated_species_prop_FD" in curve_types
    assert "treated_species_prop_HW" in curve_types


def test_run_post_tipsy_bundle_sets_managed_curve_env_for_01b(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_root = tmp_path / "data"
    data_root.mkdir(parents=True, exist_ok=True)
    tsa = "29"

    results_for_tsa = [
        (0, "IDF_FD", {"L": {"ss": None}, "M": {"ss": None}, "H": {"ss": None}})
    ]
    with (data_root / f"vdyp_prep-tsa{tsa}.pkl").open("wb") as fh:
        pickle.dump(results_for_tsa, fh)
    pd.DataFrame(
        {
            "stratum_code": ["IDF_FD", "IDF_FD"],
            "si_level": ["L", "L"],
            "age": [0, 10],
            "volume": [0.0, 10.0],
        }
    ).to_feather(data_root / f"vdyp_curves_smooth-tsa{tsa}.feather")
    pd.DataFrame({"AU": [21000]}).to_excel(
        data_root / f"tipsy_params_tsa{tsa}.xlsx",
        index=False,
        sheet_name="TIPSY_inputTBL",
    )
    (data_root / f"04_output-tsa{tsa}.csv").write_text(
        "placeholder\n", encoding="utf-8"
    )

    seen_env: dict[str, str | None] = {}

    def _fake_run_01b(
        *,
        tsa: str,
        results,
        au_scsi,
        tipsy_curves,
        vdyp_curves_smooth,
        runtime_config,
    ) -> None:
        _ = (results, au_scsi, vdyp_curves_smooth, runtime_config)
        seen_env["mode"] = os.environ.get("FEMIC_MANAGED_CURVE_MODE")
        seen_env["x"] = os.environ.get("FEMIC_MANAGED_CURVE_X_SCALE")
        seen_env["y"] = os.environ.get("FEMIC_MANAGED_CURVE_Y_SCALE")
        seen_env["truncate"] = os.environ.get("FEMIC_MANAGED_CURVE_TRUNCATE_AT_CULM")
        seen_env["max_age"] = os.environ.get("FEMIC_MANAGED_CURVE_MAX_AGE")
        tipsy_df = pd.DataFrame(
            {
                "AU": [21000, 21000, 22000, 22000, 23000, 23000],
                "Age": [0, 10, 0, 10, 0, 10],
                "Yield": [0.0, 12.0, 0.0, 24.0, 0.0, 36.0],
                "Height": [0.0, 2.0, 0.0, 3.0, 0.0, 4.0],
                "DBHq": [0.0, 1.0, 0.0, 1.5, 0.0, 2.0],
                "TPH": [1000, 900, 1000, 900, 1000, 900],
            }
        ).set_index(["AU", "Age"])
        tipsy_curves[tsa] = tipsy_df
        tipsy_df.reset_index().to_csv(
            data_root / f"tipsy_curves_tsa{tsa}.csv",
            index=False,
        )
        pd.DataFrame({"AU": [21000], "FD": [100.0]}).to_csv(
            data_root / f"tipsy_sppcomp_tsa{tsa}.csv",
            index=False,
        )

    monkeypatch.delenv("FEMIC_MANAGED_CURVE_MODE", raising=False)
    monkeypatch.delenv("FEMIC_MANAGED_CURVE_X_SCALE", raising=False)
    monkeypatch.delenv("FEMIC_MANAGED_CURVE_Y_SCALE", raising=False)
    monkeypatch.delenv("FEMIC_MANAGED_CURVE_TRUNCATE_AT_CULM", raising=False)
    monkeypatch.delenv("FEMIC_MANAGED_CURVE_MAX_AGE", raising=False)

    run_post_tipsy_bundle(
        tsa_list=[tsa],
        repo_root=tmp_path,
        data_root=data_root,
        run_01b_fn=_fake_run_01b,
        managed_curve_mode="vdyp_transform",
        managed_curve_x_scale=0.8,
        managed_curve_y_scale=1.2,
        managed_curve_truncate_at_culm=True,
        managed_curve_max_age=300,
        message_fn=lambda _msg: None,
    )

    assert seen_env["mode"] == "vdyp_transform"
    assert seen_env["x"] == "0.8"
    assert seen_env["y"] == "1.2"
    assert seen_env["truncate"] == "1"
    assert seen_env["max_age"] == "300"
    assert os.environ.get("FEMIC_MANAGED_CURVE_MODE") is None


def test_run_post_tipsy_bundle_with_manifest_writes_manifest(
    tmp_path: Path,
) -> None:
    log_dir = tmp_path / "logs"
    expected_result = PostTipsyBundleResult(
        tsa_list=["29"],
        au_rows=30,
        curve_rows=60,
        curve_points_rows=1234,
        tipsy_curves_paths=[tmp_path / "data" / "tipsy_curves_tsa29.csv"],
        tipsy_sppcomp_paths=[tmp_path / "data" / "tipsy_sppcomp_tsa29.csv"],
        au_table_path=tmp_path / "data" / "model_input_bundle" / "au_table.csv",
        curve_table_path=tmp_path / "data" / "model_input_bundle" / "curve_table.csv",
        curve_points_table_path=tmp_path
        / "data"
        / "model_input_bundle"
        / "curve_points_table.csv",
        yield_assumptions_summary={
            "assumptions_path": "config/tsr/yield_assumptions.yaml",
            "adjusted_au_count": 1,
            "total_untreated_volume_removed": 12.0,
        },
    )
    for path in [
        *expected_result.tipsy_curves_paths,
        *expected_result.tipsy_sppcomp_paths,
        expected_result.au_table_path,
        expected_result.curve_table_path,
        expected_result.curve_points_table_path,
    ]:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x\n", encoding="utf-8")

    def _fake_run_post_tipsy_bundle(**_kwargs):
        return expected_result

    # Patch at module import boundary to avoid preparing real TSA artifacts here.
    import femic.workflows.legacy as legacy_module

    original = legacy_module.run_post_tipsy_bundle
    legacy_module.run_post_tipsy_bundle = _fake_run_post_tipsy_bundle
    try:
        run_result = run_post_tipsy_bundle_with_manifest(
            tsa_list=["29"],
            run_id="post_tipsy_manifest_test",
            log_dir=log_dir,
            message_fn=lambda _msg: None,
        )
    finally:
        legacy_module.run_post_tipsy_bundle = original

    assert run_result.result == expected_result
    assert run_result.manifest_path.is_file()
    payload = json.loads(run_result.manifest_path.read_text(encoding="utf-8"))
    assert payload["status"] == "ok"
    assert payload["workflow"] == "tsa_post_tipsy"
    assert payload["run_id"] == "post_tipsy_manifest_test"
    assert payload["outputs"]["yield_assumptions"]["adjusted_au_count"] == 1


def test_run_post_tipsy_bundle_applies_broadleaf_volume_exclusion_to_conifer_leading_untreated_aus(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path
    data_root = repo_root / "data"
    data_root.mkdir(parents=True, exist_ok=True)
    (repo_root / "config" / "tsr").mkdir(parents=True, exist_ok=True)
    tsa = "29"

    (repo_root / "config" / "tsr" / "yield_assumptions.yaml").write_text(
        "\n".join(
            [
                "rules:",
                "  - rule_type: broadleaf_volume_exclusion",
                "    tsa_list: ['29']",
                "    scope: untreated_only",
            ]
        ),
        encoding="utf-8",
    )
    pd.DataFrame(
        {
            "tsa_code": [tsa],
            "SPECIES_CD_1": ["FDC"],
            "SPECIES_PCT_1": [60.0],
            "SPECIES_CD_2": ["AT"],
            "SPECIES_PCT_2": [40.0],
            "SPECIES_CD_3": [""],
            "SPECIES_PCT_3": [0.0],
            "SPECIES_CD_4": [""],
            "SPECIES_PCT_4": [0.0],
            "SPECIES_CD_5": [""],
            "SPECIES_PCT_5": [0.0],
            "SPECIES_CD_6": [""],
            "SPECIES_PCT_6": [0.0],
        }
    ).to_feather(data_root / f"ria_vri_vclr1p_checkpoint1-tsa{tsa}.feather")

    results_for_tsa = [
        (
            0,
            "IDF_FDC+AT",
            {
                "L": {
                    "species": {
                        "FDC": {"pct": 60.0},
                        "AT": {"pct": 40.0},
                    }
                }
            },
        )
    ]
    with (data_root / f"vdyp_prep-tsa{tsa}.pkl").open("wb") as fh:
        pickle.dump(results_for_tsa, fh)

    pd.DataFrame(
        {
            "stratum_code": ["IDF_FDC+AT", "IDF_FDC+AT"],
            "si_level": ["L", "L"],
            "age": [10, 20],
            "volume": [10.0, 20.0],
        }
    ).to_feather(data_root / f"vdyp_curves_smooth-tsa{tsa}.feather")
    pd.DataFrame({"AU": [21000]}).to_excel(
        data_root / f"tipsy_params_tsa{tsa}.xlsx",
        index=False,
        sheet_name="TIPSY_inputTBL",
    )
    (data_root / f"04_output-tsa{tsa}.csv").write_text(
        "placeholder\n",
        encoding="utf-8",
    )

    def _fake_run_01b(
        *,
        tsa: str,
        results,
        au_scsi,
        tipsy_curves,
        vdyp_curves_smooth,
        runtime_config,
    ) -> None:
        _ = (results, au_scsi, vdyp_curves_smooth, runtime_config)
        tipsy_df = pd.DataFrame(
            {
                "AU": [21000, 21000],
                "Age": [10, 20],
                "Yield": [12.0, 24.0],
                "Height": [2.0, 4.0],
                "DBHq": [1.0, 2.0],
                "TPH": [900, 850],
            }
        ).set_index(["AU", "Age"])
        tipsy_curves[tsa] = tipsy_df
        tipsy_df.reset_index().to_csv(
            data_root / f"tipsy_curves_tsa{tsa}.csv",
            index=False,
        )
        pd.DataFrame({"AU": [21000], "FDC": [100.0]}).to_csv(
            data_root / f"tipsy_sppcomp_tsa{tsa}.csv",
            index=False,
        )

    result = run_post_tipsy_bundle(
        tsa_list=[tsa],
        repo_root=repo_root,
        data_root=data_root,
        run_01b_fn=_fake_run_01b,
        message_fn=lambda _msg: None,
    )

    curve_table = pd.read_csv(result.curve_table_path)
    curve_points_table = pd.read_csv(result.curve_points_table_path)
    au_table = pd.read_csv(result.au_table_path)
    untreated_curve_id = int(au_table.loc[0, "untreated_curve_id"])

    untreated_points = curve_points_table.loc[
        curve_points_table["curve_id"] == untreated_curve_id, "y"
    ].tolist()
    assert untreated_points == [6.0, 12.0]

    untreated_fdc_curve_id = int(
        curve_table.loc[
            curve_table["curve_type"] == "untreated_species_prop_FDC", "curve_id"
        ].iloc[0]
    )
    untreated_at_curve_id = int(
        curve_table.loc[
            curve_table["curve_type"] == "untreated_species_prop_AT", "curve_id"
        ].iloc[0]
    )
    assert (
        float(
            curve_points_table.loc[
                curve_points_table["curve_id"] == untreated_fdc_curve_id, "y"
            ].iloc[0]
        )
        == 1.0
    )
    assert (
        float(
            curve_points_table.loc[
                curve_points_table["curve_id"] == untreated_at_curve_id, "y"
            ].iloc[0]
        )
        == 0.0
    )
    assert result.yield_assumptions_summary is not None
    assert result.yield_assumptions_summary["adjusted_au_count"] == 1
    assert result.yield_assumptions_summary["total_untreated_volume_removed"] == 12.0


def test_run_post_tipsy_bundle_leaves_broadleaf_leading_untreated_aus_unchanged(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path
    data_root = repo_root / "data"
    data_root.mkdir(parents=True, exist_ok=True)
    (repo_root / "config" / "tsr").mkdir(parents=True, exist_ok=True)
    tsa = "29"

    (repo_root / "config" / "tsr" / "yield_assumptions.yaml").write_text(
        "\n".join(
            [
                "rules:",
                "  - rule_type: broadleaf_volume_exclusion",
                "    tsa_list: ['29']",
                "    scope: untreated_only",
            ]
        ),
        encoding="utf-8",
    )
    pd.DataFrame(
        {
            "tsa_code": [tsa],
            "SPECIES_CD_1": ["AT"],
            "SPECIES_PCT_1": [60.0],
            "SPECIES_CD_2": ["FDC"],
            "SPECIES_PCT_2": [40.0],
            "SPECIES_CD_3": [""],
            "SPECIES_PCT_3": [0.0],
            "SPECIES_CD_4": [""],
            "SPECIES_PCT_4": [0.0],
            "SPECIES_CD_5": [""],
            "SPECIES_PCT_5": [0.0],
            "SPECIES_CD_6": [""],
            "SPECIES_PCT_6": [0.0],
        }
    ).to_feather(data_root / f"ria_vri_vclr1p_checkpoint1-tsa{tsa}.feather")

    results_for_tsa = [
        (
            0,
            "IDF_AT+FDC",
            {
                "L": {
                    "species": {
                        "AT": {"pct": 60.0},
                        "FDC": {"pct": 40.0},
                    }
                }
            },
        )
    ]
    with (data_root / f"vdyp_prep-tsa{tsa}.pkl").open("wb") as fh:
        pickle.dump(results_for_tsa, fh)
    pd.DataFrame(
        {
            "stratum_code": ["IDF_AT+FDC", "IDF_AT+FDC"],
            "si_level": ["L", "L"],
            "age": [10, 20],
            "volume": [10.0, 20.0],
        }
    ).to_feather(data_root / f"vdyp_curves_smooth-tsa{tsa}.feather")
    pd.DataFrame({"AU": [21000]}).to_excel(
        data_root / f"tipsy_params_tsa{tsa}.xlsx",
        index=False,
        sheet_name="TIPSY_inputTBL",
    )
    (data_root / f"04_output-tsa{tsa}.csv").write_text(
        "placeholder\n", encoding="utf-8"
    )

    def _fake_run_01b(
        *,
        tsa: str,
        results,
        au_scsi,
        tipsy_curves,
        vdyp_curves_smooth,
        runtime_config,
    ) -> None:
        _ = (results, au_scsi, vdyp_curves_smooth, runtime_config)
        tipsy_df = pd.DataFrame(
            {
                "AU": [21000, 21000],
                "Age": [10, 20],
                "Yield": [12.0, 24.0],
                "Height": [2.0, 4.0],
                "DBHq": [1.0, 2.0],
                "TPH": [900, 850],
            }
        ).set_index(["AU", "Age"])
        tipsy_curves[tsa] = tipsy_df
        tipsy_df.reset_index().to_csv(
            data_root / f"tipsy_curves_tsa{tsa}.csv",
            index=False,
        )
        pd.DataFrame({"AU": [21000], "FDC": [100.0]}).to_csv(
            data_root / f"tipsy_sppcomp_tsa{tsa}.csv",
            index=False,
        )

    result = run_post_tipsy_bundle(
        tsa_list=[tsa],
        repo_root=repo_root,
        data_root=data_root,
        run_01b_fn=_fake_run_01b,
        message_fn=lambda _msg: None,
    )

    au_table = pd.read_csv(result.au_table_path)
    curve_points_table = pd.read_csv(result.curve_points_table_path)
    untreated_curve_id = int(au_table.loc[0, "untreated_curve_id"])
    untreated_points = curve_points_table.loc[
        curve_points_table["curve_id"] == untreated_curve_id, "y"
    ].tolist()
    assert untreated_points == [10.0, 20.0]
    assert result.yield_assumptions_summary is not None
    assert result.yield_assumptions_summary["adjusted_au_count"] == 0


def test_run_post_tipsy_bundle_reports_noop_when_species_props_are_unavailable(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path
    data_root = repo_root / "data"
    data_root.mkdir(parents=True, exist_ok=True)
    (repo_root / "config" / "tsr").mkdir(parents=True, exist_ok=True)
    tsa = "29"

    (repo_root / "config" / "tsr" / "yield_assumptions.yaml").write_text(
        "\n".join(
            [
                "rules:",
                "  - rule_type: broadleaf_volume_exclusion",
                "    tsa_list: ['29']",
                "    scope: untreated_only",
            ]
        ),
        encoding="utf-8",
    )
    results_for_tsa = [(0, "IDF_FDC+HW", {"L": {}})]
    with (data_root / f"vdyp_prep-tsa{tsa}.pkl").open("wb") as fh:
        pickle.dump(results_for_tsa, fh)
    pd.DataFrame(
        {
            "stratum_code": ["IDF_FDC+HW", "IDF_FDC+HW"],
            "si_level": ["L", "L"],
            "age": [10, 20],
            "volume": [10.0, 20.0],
        }
    ).to_feather(data_root / f"vdyp_curves_smooth-tsa{tsa}.feather")
    pd.DataFrame({"AU": [21000]}).to_excel(
        data_root / f"tipsy_params_tsa{tsa}.xlsx",
        index=False,
        sheet_name="TIPSY_inputTBL",
    )
    (data_root / f"04_output-tsa{tsa}.csv").write_text(
        "placeholder\n", encoding="utf-8"
    )

    def _fake_run_01b(
        *,
        tsa: str,
        results,
        au_scsi,
        tipsy_curves,
        vdyp_curves_smooth,
        runtime_config,
    ) -> None:
        _ = (results, au_scsi, vdyp_curves_smooth, runtime_config)
        tipsy_df = pd.DataFrame(
            {
                "AU": [21000, 21000],
                "Age": [10, 20],
                "Yield": [12.0, 24.0],
                "Height": [2.0, 4.0],
                "DBHq": [1.0, 2.0],
                "TPH": [900, 850],
            }
        ).set_index(["AU", "Age"])
        tipsy_curves[tsa] = tipsy_df
        tipsy_df.reset_index().to_csv(
            data_root / f"tipsy_curves_tsa{tsa}.csv",
            index=False,
        )
        pd.DataFrame({"AU": [21000], "FDC": [100.0]}).to_csv(
            data_root / f"tipsy_sppcomp_tsa{tsa}.csv",
            index=False,
        )

    result = run_post_tipsy_bundle(
        tsa_list=[tsa],
        repo_root=repo_root,
        data_root=data_root,
        run_01b_fn=_fake_run_01b,
        message_fn=lambda _msg: None,
    )

    assert result.yield_assumptions_summary is not None
    assert result.yield_assumptions_summary["adjusted_au_count"] == 0
    assert result.yield_assumptions_summary["skipped_aus"][0]["reason"] == (
        "missing_untreated_species_proportions"
    )


def test_run_post_tipsy_bundle_passes_custom_output_template_to_01b(
    tmp_path: Path,
) -> None:
    data_root = tmp_path / "data"
    data_root.mkdir(parents=True, exist_ok=True)
    tsa = "29"

    results_for_tsa = [
        (0, "IDF_FD", {"L": {"ss": None}, "M": {"ss": None}, "H": {"ss": None}})
    ]
    with (data_root / f"vdyp_prep-tsa{tsa}.pkl").open("wb") as fh:
        pickle.dump(results_for_tsa, fh)
    pd.DataFrame(
        {
            "stratum_code": ["IDF_FD", "IDF_FD"],
            "si_level": ["L", "L"],
            "age": [0, 10],
            "volume": [0.0, 10.0],
        }
    ).to_feather(data_root / f"vdyp_curves_smooth-tsa{tsa}.feather")
    pd.DataFrame({"AU": [21000]}).to_excel(
        data_root / f"tipsy_params_tsa{tsa}.xlsx",
        index=False,
        sheet_name="TIPSY_inputTBL",
    )
    (data_root / f"04_output-tsa{tsa}.csv").write_text(
        "placeholder\n", encoding="utf-8"
    )

    seen_template: dict[str, str] = {}

    def _fake_run_01b(
        *,
        tsa: str,
        results,
        au_scsi,
        tipsy_curves,
        vdyp_curves_smooth,
        runtime_config,
    ) -> None:
        _ = (results, au_scsi, vdyp_curves_smooth)
        seen_template["value"] = runtime_config.tipsy_output_filename_template
        tipsy_df = pd.DataFrame(
            {
                "AU": [21000, 21000, 22000, 22000, 23000, 23000],
                "Age": [0, 10, 0, 10, 0, 10],
                "Yield": [0.0, 12.0, 0.0, 24.0, 0.0, 36.0],
                "Height": [0.0, 2.0, 0.0, 3.0, 0.0, 4.0],
                "DBHq": [0.0, 1.0, 0.0, 1.5, 0.0, 2.0],
                "TPH": [1000, 900, 1000, 900, 1000, 900],
            }
        ).set_index(["AU", "Age"])
        tipsy_curves[tsa] = tipsy_df
        tipsy_df.reset_index().to_csv(
            data_root / f"tipsy_curves_tsa{tsa}.csv",
            index=False,
        )
        pd.DataFrame({"AU": [21000], "FD": [100.0]}).to_csv(
            data_root / f"tipsy_sppcomp_tsa{tsa}.csv",
            index=False,
        )

    run_post_tipsy_bundle(
        tsa_list=[tsa],
        repo_root=tmp_path,
        data_root=data_root,
        run_01b_fn=_fake_run_01b,
        tipsy_output_filename_template="04_output-tsa{tsa}.csv",
        message_fn=lambda _msg: None,
    )

    assert seen_template["value"] == "04_output-tsa{tsa}.csv"


def test_run_btc_and_post_tipsy_bundle_with_manifest_orchestrates_paths(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_root = tmp_path / "data"
    data_root.mkdir(parents=True, exist_ok=True)
    (data_root / "03_input-tsa29.csv").write_text(
        "feature_id\n1000\n", encoding="utf-8"
    )

    btc_calls: list[dict[str, object]] = []
    post_tipsy_calls: list[dict[str, object]] = []

    def _fake_run_btc_cli(**kwargs: object) -> BTCRunResult:
        btc_calls.append(kwargs)
        output_csv = Path(kwargs["output_csv"])
        error_csv = Path(kwargs["error_csv"])
        output_csv.write_text("feature_id,MVcon_0\n1000,0\n", encoding="utf-8")
        error_csv.write_text("warnings,errors\n0,0\n", encoding="utf-8")
        return BTCRunResult(
            run_id=str(kwargs["run_id"]),
            mode="TSR",
            manifest_path=tmp_path / "logs" / "btc_manifest.json",
            stdout_log_path=tmp_path / "logs" / "btc_stdout.log",
            stderr_log_path=tmp_path / "logs" / "btc_stderr.log",
            output_csv_path=output_csv,
            error_csv_path=error_csv,
            executable_path=tmp_path / "btc" / "TIPSYbtc.exe",
            install_root=tmp_path / "btc",
            working_dir=tmp_path / "scratch" / "work",
            command=("btc.exe", "/TSR", "MSYT.csv"),
            copied_install=True,
            exit_code=0,
            duration_sec=1.0,
            report_template_path=tmp_path / "btc" / "TimberSupply.rpt",
        )

    def _fake_post_tipsy(**kwargs: object) -> PostTipsyBundleRunResult:
        post_tipsy_calls.append(kwargs)
        result = PostTipsyBundleResult(
            tsa_list=["29"],
            au_rows=1,
            curve_rows=2,
            curve_points_rows=4,
            tipsy_curves_paths=[data_root / "tipsy_curves_tsa29.csv"],
            tipsy_sppcomp_paths=[data_root / "tipsy_sppcomp_tsa29.csv"],
            au_table_path=data_root / "model_input_bundle" / "au_table.csv",
            curve_table_path=data_root / "model_input_bundle" / "curve_table.csv",
            curve_points_table_path=data_root
            / "model_input_bundle"
            / "curve_points_table.csv",
        )
        return PostTipsyBundleRunResult(
            manifest_path=tmp_path / "logs" / "run_manifest.json",
            result=result,
        )

    monkeypatch.setattr("femic.workflows.legacy.run_btc_cli", _fake_run_btc_cli)
    monkeypatch.setattr(
        "femic.workflows.legacy.run_post_tipsy_bundle_with_manifest",
        _fake_post_tipsy,
    )

    run_result = run_btc_and_post_tipsy_bundle_with_manifest(
        tsa_list=["29"],
        run_id="btc_post_tipsy_test",
        log_dir=tmp_path / "logs",
        repo_root=tmp_path,
        data_root=data_root,
        scratch_root=tmp_path / "scratch",
        message_fn=lambda _msg: None,
    )

    assert isinstance(run_result, BTCPostTipsyRunResult)
    assert len(run_result.btc_results) == 1
    assert len(btc_calls) == 1
    assert Path(btc_calls[0]["input_csv"]) == data_root / "03_input-tsa29.csv"
    assert Path(btc_calls[0]["output_csv"]) == data_root / "04_output-tsa29.csv"
    assert Path(btc_calls[0]["error_csv"]) == data_root / "04_error-tsa29.csv"
    assert btc_calls[0]["report_preset_name"] == "tsr-unattended-default"
    assert btc_calls[0]["indicator_bank_names"] == ()
    assert btc_calls[0]["copy_install"] is True
    assert Path(btc_calls[0]["scratch_root"]) == tmp_path / "scratch" / "tsa29"
    assert len(post_tipsy_calls) == 1
    assert (
        post_tipsy_calls[0]["tipsy_output_filename_template"]
        == "04_output-tsa{tsa}.csv"
    )
    fingerprint_path = tipsy_output_input_fingerprint_path(
        tipsy_output_path=data_root / "04_output-tsa29.csv"
    )
    assert fingerprint_path.is_file()
    assert fingerprint_path.read_text(encoding="utf-8").strip() == compute_file_sha256(
        data_root / "03_input-tsa29.csv"
    )


def test_run_btc_and_post_tipsy_bundle_with_manifest_passes_indicator_banks(
    monkeypatch, tmp_path: Path
) -> None:
    data_root = tmp_path / "data"
    data_root.mkdir()
    (data_root / "03_input-tsa29.csv").write_text(
        "feature_id\n1000\n", encoding="utf-8"
    )
    btc_calls: list[dict[str, object]] = []

    def _fake_run_btc_cli(**kwargs: object) -> BTCRunResult:
        btc_calls.append(kwargs)
        return BTCRunResult(
            run_id="btc_post_tipsy_test_tsa29",
            mode="TSR",
            manifest_path=tmp_path / "logs" / "btc_manifest.json",
            stdout_log_path=tmp_path / "logs" / "btc_stdout.log",
            stderr_log_path=tmp_path / "logs" / "btc_stderr.log",
            output_csv_path=data_root / "04_output-tsa29.csv",
            error_csv_path=data_root / "04_error-tsa29.csv",
            executable_path=tmp_path / "btc" / "TIPSYbtc.exe",
            install_root=tmp_path / "btc",
            working_dir=tmp_path / "scratch" / "work",
            command=("btc.exe", "/TSR", "MSYT.csv"),
            copied_install=True,
            exit_code=0,
            duration_sec=1.0,
            report_template_path=tmp_path / "btc" / "TimberSupply.rpt",
        )

    def _fake_post_tipsy(**kwargs: object) -> PostTipsyBundleRunResult:
        result = PostTipsyBundleResult(
            tsa_list=["29"],
            au_rows=1,
            curve_rows=2,
            curve_points_rows=4,
            tipsy_curves_paths=[data_root / "tipsy_curves_tsa29.csv"],
            tipsy_sppcomp_paths=[data_root / "tipsy_sppcomp_tsa29.csv"],
            au_table_path=data_root / "model_input_bundle" / "au_table.csv",
            curve_table_path=data_root / "model_input_bundle" / "curve_table.csv",
            curve_points_table_path=data_root
            / "model_input_bundle"
            / "curve_points_table.csv",
        )
        return PostTipsyBundleRunResult(
            manifest_path=tmp_path / "logs" / "run_manifest.json",
            result=result,
        )

    monkeypatch.setattr("femic.workflows.legacy.run_btc_cli", _fake_run_btc_cli)
    monkeypatch.setattr(
        "femic.workflows.legacy.run_post_tipsy_bundle_with_manifest",
        _fake_post_tipsy,
    )

    run_btc_and_post_tipsy_bundle_with_manifest(
        tsa_list=["29"],
        run_id="btc_post_tipsy_test",
        log_dir=tmp_path / "logs",
        repo_root=tmp_path,
        data_root=data_root,
        scratch_root=tmp_path / "scratch",
        indicator_bank_names=("stand-structure-basic",),
        message_fn=lambda _msg: None,
    )

    assert len(btc_calls) == 1
    assert btc_calls[0]["indicator_bank_names"] == ("stand-structure-basic",)
