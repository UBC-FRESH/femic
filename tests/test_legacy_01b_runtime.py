from __future__ import annotations

import importlib.util
from pathlib import Path

import matplotlib
from matplotlib import pyplot as plt
import pandas as pd


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
