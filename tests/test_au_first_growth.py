from __future__ import annotations

import numpy as np
import pandas as pd

from femic.pipeline.au_first_growth import (
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
            "age_bin": [30.0, 80.0, 150.0, 300.0],
            "median_volume": [40.0, 280.0, 360.0, 320.0],
        }
    )

    x_curve, y_curve = build_smoothed_bin_pchip_curve(binned=binned)

    assert x_curve.size == y_curve.size
    assert x_curve[0] == 1.0
    assert np.all(y_curve > 0.0)
