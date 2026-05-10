"""Reusable AU-level first-growth curve selection helpers."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.interpolate import PchipInterpolator

from femic.pipeline.vdyp_curves import build_observed_bins_for_fit


_TAIL_START_AGE = 150.0
_CURVE_MAX_AGE = 300
_SMOOTHING_WEIGHTS = np.asarray([1.0, 2.0, 3.0, 2.0, 1.0], dtype=float)
_SMOOTHING_WEIGHTS = _SMOOTHING_WEIGHTS / _SMOOTHING_WEIGHTS.sum()
_SMOOTHING_PASSES = 2
_DEFAULT_MIN_SOURCE_STANDS = 2


@dataclass(frozen=True)
class AuFirstGrowthSelectionResult:
    """Selected AU-level first-growth curve and diagnostics."""

    selected_path: str
    accepted: bool
    x_curve: np.ndarray
    y_curve: np.ndarray
    binned: pd.DataFrame
    metrics: dict[str, float]


def fit_au_first_growth_quality(
    *,
    binned: pd.DataFrame,
    x_curve: np.ndarray,
    y_curve: np.ndarray,
    tail_start_age: float = _TAIL_START_AGE,
) -> dict[str, float]:
    """Measure fit quality against observed AU-level median bins."""
    observed_age = np.asarray(binned["age_bin"].values, dtype=float)
    observed_volume = np.asarray(binned["median_volume"].values, dtype=float)
    fitted = np.interp(observed_age, x_curve, y_curve)
    residual = fitted - observed_volume
    abs_obs = np.maximum(np.abs(observed_volume), 1e-6)
    rmse = float(np.sqrt(np.mean(np.square(residual))))
    mape = float(np.mean(np.abs(residual) / abs_obs))
    tail_mask = observed_age >= float(tail_start_age)
    tail_rmse = (
        float(np.sqrt(np.mean(np.square(residual[tail_mask]))))
        if np.any(tail_mask)
        else rmse
    )
    return {
        "rmse": rmse,
        "mape": mape,
        "tail_rmse": tail_rmse,
    }


def build_smoothed_bin_pchip_curve(
    *,
    binned: pd.DataFrame,
    smoothing_passes: int = _SMOOTHING_PASSES,
    curve_max_age: int = _CURVE_MAX_AGE,
    min_anchor_age: float = 30.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Build a strongly smoothed observed-bin PCHIP curve."""
    anchors = binned.loc[:, ["age_bin", "median_volume"]].copy()
    anchors["age_bin"] = pd.to_numeric(anchors["age_bin"], errors="coerce")
    anchors["median_volume"] = pd.to_numeric(anchors["median_volume"], errors="coerce")
    anchors = anchors.dropna().sort_values("age_bin", kind="stable")
    anchors = anchors.loc[anchors["age_bin"] >= float(min_anchor_age)].copy()
    if anchors.empty:
        return np.asarray([], dtype=float), np.asarray([], dtype=float)

    smoothed = anchors["median_volume"].to_numpy(dtype=float).copy()
    if len(smoothed) >= 5:
        for _ in range(int(smoothing_passes)):
            updated = smoothed.copy()
            for idx in range(2, len(smoothed) - 2):
                updated[idx] = float(np.dot(_SMOOTHING_WEIGHTS, smoothed[idx - 2 : idx + 3]))
            smoothed = updated

    anchor_ages = np.concatenate([[1.0], anchors["age_bin"].to_numpy(dtype=float)])
    anchor_volumes = np.concatenate([[1e-6], smoothed])
    pchip = PchipInterpolator(anchor_ages, anchor_volumes, extrapolate=True)
    curve_x = np.arange(1, int(curve_max_age), dtype=float)
    curve_y = np.asarray(pchip(curve_x), dtype=float)
    curve_y = np.nan_to_num(curve_y, nan=0.0, posinf=0.0, neginf=0.0)
    curve_y = np.maximum(curve_y, 1e-6)
    return curve_x, curve_y


def select_au_first_growth_curve(
    *,
    vdyp_out: dict[int, pd.DataFrame],
    min_source_stands: int = _DEFAULT_MIN_SOURCE_STANDS,
    min_age: int = 30,
    max_age: int = 350,
    bin_years: int = 5,
    smoothing_passes: int = _SMOOTHING_PASSES,
) -> AuFirstGrowthSelectionResult:
    """Select the default AU-level first-growth curve from stand-level VDYP evidence."""
    empty_binned = pd.DataFrame(columns=["age_bin", "median_volume"])
    if len(vdyp_out) < int(min_source_stands):
        return AuFirstGrowthSelectionResult(
            selected_path="insufficient_source_stands",
            accepted=False,
            x_curve=np.asarray([], dtype=float),
            y_curve=np.asarray([], dtype=float),
            binned=empty_binned,
            metrics={"rmse": np.nan, "mape": np.nan, "tail_rmse": np.nan},
        )

    binned = build_observed_bins_for_fit(
        vdyp_out_concat=pd.concat(vdyp_out.values()),
        volume_flavour="Vdwb",
        min_age=int(min_age),
        max_age=int(max_age),
        bin_years=int(bin_years),
    )
    if binned.empty:
        return AuFirstGrowthSelectionResult(
            selected_path="insufficient_source_stands",
            accepted=False,
            x_curve=np.asarray([], dtype=float),
            y_curve=np.asarray([], dtype=float),
            binned=binned,
            metrics={"rmse": np.nan, "mape": np.nan, "tail_rmse": np.nan},
        )
    x_curve, y_curve = build_smoothed_bin_pchip_curve(
        binned=binned,
        smoothing_passes=int(smoothing_passes),
    )
    if x_curve.size == 0 or y_curve.size == 0:
        return AuFirstGrowthSelectionResult(
            selected_path="insufficient_source_stands",
            accepted=False,
            x_curve=x_curve,
            y_curve=y_curve,
            binned=binned,
            metrics={"rmse": np.nan, "mape": np.nan, "tail_rmse": np.nan},
        )
    metrics = fit_au_first_growth_quality(
        binned=binned,
        x_curve=x_curve,
        y_curve=y_curve,
    )
    return AuFirstGrowthSelectionResult(
        selected_path="smoothed_bin_pchip",
        accepted=True,
        x_curve=x_curve,
        y_curve=y_curve,
        binned=binned,
        metrics=metrics,
    )
