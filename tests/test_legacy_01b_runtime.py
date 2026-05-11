from __future__ import annotations

import importlib.util
import os
from pathlib import Path

import matplotlib
from matplotlib import pyplot as plt
import pandas as pd
from femic.pipeline.legacy_runtime import Legacy01BRuntimeConfig


def _load_legacy_01b_module():
    script_path = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "femic"
        / "resources"
        / "legacy"
        / "01b_run-tsa.py"
    )
    spec = importlib.util.spec_from_file_location("legacy_01b_run_tsa", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_plot_vdyp_overlay_skips_missing_curve_key() -> None:
    matplotlib.use("Agg")
    module = _load_legacy_01b_module()
    vdyp_curves_by_scsi = (
        pd.DataFrame(
            {
                "stratum_code": ["SBS_FD"],
                "si_level": ["M"],
                "age": [10],
                "volume": [12.0],
            }
        )
        .set_index(["stratum_code", "si_level"])
        .sort_index()
    )
    seen: list[str] = []
    fig, ax = plt.subplots(1, 1, figsize=(4, 3))
    try:
        plotted = module._plot_vdyp_overlay(
            ax=ax,
            vdyp_curves_by_scsi=vdyp_curves_by_scsi,
            stratum_code="SBS_FD",
            si_level="L",
            message_fn=seen.append,
        )
    finally:
        plt.close(fig)
    assert plotted is False
    assert seen and "missing VDYP comparison curve" in seen[0]


def test_run_tsa_prefers_btc_csv_input_when_workbook_is_missing(tmp_path: Path) -> None:
    matplotlib.use("Agg")
    module = _load_legacy_01b_module()

    data_root = tmp_path / "data"
    plots_root = tmp_path / "plots"
    tipsy_root = tmp_path / "tipsy_io"
    data_root.mkdir(parents=True, exist_ok=True)
    plots_root.mkdir(parents=True, exist_ok=True)
    tipsy_root.mkdir(parents=True, exist_ok=True)

    pd.DataFrame(
        {
            "feature_id": [21000],
            "planted_species1": ["Pl"],
            "planted_species2": [""],
            "planted_species3": [""],
            "planted_species4": [""],
            "planted_species5": [""],
            "planted_density1": [1100],
            "planted_density2": [0],
            "planted_density3": [0],
            "planted_density4": [0],
            "planted_density5": [0],
            "planted_percent": [30],
            "pl_si": [10.2],
        }
    ).to_csv(data_root / "03_input-tsa29.csv", index=False)
    pd.DataFrame(
        {
            "feature_id": [21000],
            "MVcon_0": [0.0],
            "MVdec_0": [0.0],
            "HTcon_0": [0.0],
            "HTdec_0": [0.0],
            "gVol_0": [0.0],
            "CC_0": [0.0],
            "MVcon_10": [12.0],
            "MVdec_10": [0.0],
            "HTcon_10": [4.0],
            "HTdec_10": [0.0],
            "gVol_10": [12.0],
            "CC_10": [0.0],
        }
    ).to_csv(data_root / "04_output-tsa29.csv", index=False)

    runtime_config = Legacy01BRuntimeConfig(
        tipsy_output_root=data_root,
        tipsy_output_filename_template="04_output-tsa{tsa}.csv",
        tipsy_params_path_prefix=str(data_root / "tipsy_params_tsa"),
    )

    vdyp_curves_smooth = {
        "29": pd.DataFrame(
            {
                "stratum_code": ["SBPS_PLI", "SBPS_PLI"],
                "si_level": ["L", "L"],
                "age": [0, 10],
                "volume": [0.0, 10.0],
            }
        )
    }
    tipsy_curves: dict[str, pd.DataFrame] = {}
    results = {"29": []}
    au_scsi = {"29": {21000: ("SBPS_PLI", "L")}}

    previous_cwd = Path.cwd()
    try:
        os.chdir(tmp_path)
        module.run_tsa(
            tsa="29",
            results=results,
            au_scsi=au_scsi,
            tipsy_curves=tipsy_curves,
            vdyp_curves_smooth=vdyp_curves_smooth,
            runtime_config=runtime_config,
        )
    finally:
        os.chdir(previous_cwd)

    assert (data_root / "tipsy_curves_tsa29.csv").is_file()
    assert (data_root / "tipsy_sppcomp_tsa29.csv").is_file()
    assert (plots_root / "tipsy_vdyp_tsa29-21000.png").is_file()
