from __future__ import annotations

import numpy as np
import pandas as pd

from femic.pipeline.au_first_growth import (
    _prune_bad_leading_anchors,
    _splice_exponential_toe,
    build_smoothed_bin_pchip_curve,
    select_au_first_growth_curve,
)


def test_select_au_first_growth_curve_returns_insufficient_support_for_small_input() -> None:
    vdyp_out = {
        10: pd.DataFrame(
            {
                "Vdwb": [40.0, 280.0, 360.0],
            },
            index=pd.Index([30, 80, 150], name="Age"),
        )
    }

    result = select_au_first_growth_curve(vdyp_out=vdyp_out, min_source_stands=2)

    assert result.selected_path == "insufficient_source_stands"
    assert result.accepted is False
    assert result.x_curve.size == 0
    assert result.y_curve.size == 0
    assert result.binned.empty


def test_select_au_first_growth_curve_uses_smoothed_bin_pchip_default() -> None:
    vdyp_out = {
        10: pd.DataFrame(
            {
                "Vdwb": [40.0, 280.0, 360.0, 320.0],
            },
            index=pd.Index([30, 80, 150, 300], name="Age"),
        ),
        11: pd.DataFrame(
            {
                "Vdwb": [50.0, 300.0, 380.0, 340.0],
            },
            index=pd.Index([30, 80, 150, 300], name="Age"),
        ),
    }

    result = select_au_first_growth_curve(vdyp_out=vdyp_out, min_source_stands=2)

    assert result.selected_path == "smoothed_bin_pchip"
    assert result.accepted is True
    assert result.x_curve.size > 0
    assert result.y_curve.size > 0
    assert len(result.binned) > 0
    assert result.metrics["rmse"] >= 0.0


def test_build_smoothed_bin_pchip_curve_keeps_positive_monotone_curve() -> None:
    binned = pd.DataFrame(
        {
            "age_bin": [50.0, 80.0, 150.0, 300.0],
            "median_volume": [40.0, 280.0, 360.0, 320.0],
        }
    )

    x_curve, y_curve = build_smoothed_bin_pchip_curve(binned=binned)

    assert x_curve.size == y_curve.size
    assert x_curve[0] == 1.0
    assert np.all(y_curve > 0.0)


def test_build_smoothed_bin_pchip_curve_ignores_bins_below_60() -> None:
    binned = pd.DataFrame(
        {
            "age_bin": [30.0, 50.0, 60.0, 80.0, 150.0, 200.0],
            "median_volume": [400.0, 180.0, 45.0, 220.0, 310.0, 300.0],
        }
    )

    x_curve, y_curve = build_smoothed_bin_pchip_curve(binned=binned)

    age_30_idx = int(np.where(x_curve == 30.0)[0][0])
    age_60_idx = int(np.where(x_curve == 60.0)[0][0])
    assert y_curve[age_30_idx] < 150.0
    assert y_curve[age_30_idx] < y_curve[age_60_idx]


def test_build_smoothed_bin_pchip_curve_flattens_after_last_anchor() -> None:
    binned = pd.DataFrame(
        {
            "age_bin": [50.0, 80.0, 120.0, 180.0, 200.0],
            "median_volume": [30.0, 180.0, 260.0, 290.0, 285.0],
        }
    )

    x_curve, y_curve = build_smoothed_bin_pchip_curve(binned=binned)

    tail = y_curve[x_curve >= 200.0]
    assert tail.size > 0
    assert np.allclose(tail, tail[0])


def test_prune_bad_leading_anchors_removes_early_high_outliers() -> None:
    anchors = pd.DataFrame(
        {
            "age_bin": [60.0, 65.0, 70.0, 75.0, 80.0],
            "median_volume": [30.0, 12.0, 14.0, 18.0, 24.0],
        }
    )

    cleaned = _prune_bad_leading_anchors(anchors)

    assert cleaned["age_bin"].tolist() == [65.0, 70.0, 75.0, 80.0]
    assert cleaned["median_volume"].tolist() == [12.0, 14.0, 18.0, 24.0]


def test_prune_bad_leading_anchors_ignores_late_tail_outliers() -> None:
    anchors = pd.DataFrame(
        {
            "age_bin": [60.0, 65.0, 70.0, 75.0, 80.0, 85.0, 90.0, 95.0, 100.0, 300.0],
            "median_volume": [36.2, 42.85, 45.65, 51.55, 61.4, 69.2, 75.6, 82.6, 89.05, 20.0],
        }
    )

    cleaned = _prune_bad_leading_anchors(anchors)

    assert cleaned.iloc[0]["age_bin"] == 60.0
    assert len(cleaned) == len(anchors)


def test_prune_bad_leading_anchors_can_drop_local_ugly_left_block() -> None:
    anchors = pd.DataFrame(
        {
            "age_bin": [60.0, 65.0, 70.0, 75.0, 80.0, 85.0, 90.0, 95.0, 100.0, 105.0, 110.0],
            "median_volume": [1.9, 1.9, 30.5, 34.6, 31.75, 34.25, 22.5, 26.0, 24.7, 28.4, 31.3],
        }
    )

    cleaned = _prune_bad_leading_anchors(anchors)

    assert cleaned.iloc[0]["age_bin"] >= 90.0


def test_splice_exponential_toe_overwrites_left_edge_with_monotone_toe() -> None:
    x_curve = np.arange(1.0, 300.0, dtype=float)
    y_curve = np.interp(
        x_curve,
        np.asarray([1.0, 100.0, 120.0, 160.0, 200.0], dtype=float),
        np.asarray([1e-6, 24.7, 38.35, 57.5, 62.5], dtype=float),
    )

    y_toe = _splice_exponential_toe(
        x_curve=x_curve,
        y_curve=y_curve,
        first_anchor_age=100.0,
    )

    assert not np.allclose(y_toe[:110], y_curve[:110])
    assert np.all(np.diff(y_toe[:110]) >= -1e-6)
    assert float(y_toe[99]) <= float(y_curve[99]) + 0.1
