from __future__ import annotations

from typing import Any, Callable

import numpy as np
import pandas as pd
import pytest

from femic.pipeline.vdyp_curves import (
    build_observed_bins_for_fit,
    detect_linear_tail_segment,
    legacy_fit_func1,
    legacy_fit_func1_bounds_func,
    legacy_fit_func2,
    legacy_fit_func2_bounds_func,
    prepend_quasi_origin_point,
    process_vdyp_out,
)


def _fit_func1(x: np.ndarray, a: float, b: float, c: float, s: float) -> np.ndarray:
    return s * (a * ((x - c) ** b)) * np.exp(-a * (x - c))


def _fit_bounds(_x: np.ndarray) -> tuple[list[float], list[float]]:
    return ([0.0, 0.0, 0.0, 0.0], [1.0, 50.0, 100.0, 10.0])


def test_prepend_quasi_origin_point_inserts_first_point() -> None:
    x, y = prepend_quasi_origin_point(np.array([10.0, 20.0]), np.array([5.0, 8.0]))
    assert x[0] == 1.0
    assert y[0] == 1e-6


def test_build_observed_bins_for_fit_aggregates_to_five_year_medians() -> None:
    vdyp_df = pd.DataFrame(
        {
            "Age": [160, 161, 164, 165, 166, 169, 170, 171],
            "Vdwb": [70.0, 72.0, 74.0, 76.0, 77.0, 79.0, 80.0, 82.0],
        }
    ).set_index("Age")
    binned = build_observed_bins_for_fit(
        vdyp_out_concat=vdyp_df,
        volume_flavour="Vdwb",
        min_age=30,
        max_age=300,
        bin_years=5,
    )
    assert binned["age_bin"].tolist() == [160.0, 165.0, 170.0]
    assert binned["median_volume"].tolist() == [72.0, 77.0, 81.0]


def test_detect_linear_tail_segment_accepts_long_flat_tail_with_low_r2() -> None:
    ages = np.arange(160.0, 301.0, 5.0)
    vols = np.where(
        ages < 200.0,
        74.0 + 0.18 * (ages - 160.0),
        81.0 + 0.01 * np.sin((ages - 200.0) / 5.0),
    )
    detected = detect_linear_tail_segment(
        observed_age=ages,
        observed_volume=vols,
        linear_min_points=6,
        linear_min_r2=0.80,
        linear_max_nrmse=0.05,
        linear_prefer_min_age=160.0,
        linear_flat_slope_abs=0.04,
        linear_min_span_years=80.0,
    )
    assert detected is not None
    assert float(detected["anchor_age"]) <= 200.0
    assert float(detected["tail_span_years"]) >= 80.0


def test_process_vdyp_out_body_fit_uses_five_year_binned_ages() -> None:
    ages = np.array([160, 161, 164, 165, 166, 169, 170, 171, 174, 175], dtype=float)
    vols = np.array([70, 72, 74, 76, 77, 79, 80, 82, 83, 84], dtype=float)
    vdyp_df = pd.DataFrame({"Age": ages, "Vdwb": vols}).set_index("Age")
    captured_x: list[np.ndarray] = []

    def curve_fit_capture(
        func: Callable[..., np.ndarray], x: np.ndarray, y: np.ndarray, **kwargs: Any
    ) -> tuple[np.ndarray, Any]:
        _ = (func, y, kwargs)
        captured_x.append(np.asarray(x, dtype=float))
        return np.array([0.04, 2.0, 12.0, 7.0]), None

    _ = process_vdyp_out(
        {1: vdyp_df},
        curve_fit_fn=curve_fit_capture,
        body_fit_func=_fit_func1,
        body_fit_func_bounds_func=_fit_bounds,
        toe_fit_func=_fit_func1,
        toe_fit_func_bounds_func=_fit_bounds,
        log_event=lambda _event: None,
        min_age=150,
        max_age=200,
        window=1,
    )
    assert captured_x
    # Expected fitted ages are 5-year bins, not annual values.
    assert set(captured_x[0].tolist()) <= {160.0, 165.0, 170.0, 175.0}


def test_legacy_fit_func1_bounds_caps_c_parameter() -> None:
    values = legacy_fit_func1(np.array([5.0]), 0.5, 2.0, 1.0, 3.0)
    assert values.shape == (1,)
    lower, upper = legacy_fit_func1_bounds_func(np.array([25.0, 40.0]))
    assert lower == [0.0, 0, 0, 0]
    assert upper == [1.0, 50, 25.0, 10]


def test_legacy_fit_func2_and_bounds_behavior() -> None:
    out = legacy_fit_func2(np.array([2.0, 4.0]), 2.0, 3.0)
    assert out.tolist() == [4.0, 8.0]
    assert legacy_fit_func2_bounds_func(np.array([1.0])) == ((0, 0), (10, 10))


def test_process_vdyp_out_empty_input_returns_quasi_anchor() -> None:
    events: list[dict[str, Any]] = []
    x, y = process_vdyp_out(
        {},
        curve_fit_fn=lambda *args, **kwargs: (np.array([0.1, 1.0, 1.0, 1.0]), None),
        body_fit_func=_fit_func1,
        body_fit_func_bounds_func=_fit_bounds,
        toe_fit_func=_fit_func1,
        toe_fit_func_bounds_func=_fit_bounds,
        log_event=events.append,
    )
    assert x.tolist() == [1.0]
    assert y.tolist() == [1e-6]
    assert events[-1]["stage"] == "preflight"
    assert events[-1]["reason"] == "empty_vdyp_out"


def test_process_vdyp_out_toe_failure_falls_back_to_quasi_origin() -> None:
    ages = np.array([30, 40, 50, 60, 70, 80], dtype=float)
    vols = np.array([30, 80, 140, 190, 220, 240], dtype=float)
    vdyp_df = pd.DataFrame({"Age": ages, "Vdwb": vols}).set_index("Age")
    events: list[dict[str, Any]] = []

    def curve_fit_stub(
        func: Callable[..., np.ndarray], x: np.ndarray, y: np.ndarray, **kwargs: Any
    ) -> tuple[np.ndarray, Any]:
        _ = (x, y, kwargs)
        if func is _fit_func1:
            # Body fit succeeds.
            return np.array([0.04, 2.0, 12.0, 7.0]), None
        raise RuntimeError("unexpected function")

    def toe_fail(*args: Any, **kwargs: Any) -> np.ndarray:
        _ = (args, kwargs)
        raise RuntimeError("toe failed")

    x, y = process_vdyp_out(
        {1: vdyp_df},
        curve_fit_fn=curve_fit_stub,
        body_fit_func=_fit_func1,
        body_fit_func_bounds_func=_fit_bounds,
        toe_fit_func=toe_fail,
        toe_fit_func_bounds_func=lambda _: ([0.0], [1.0]),
        log_event=events.append,
        min_age=30,
        max_age=90,
        window=2,
        max_skip_increase=2,
    )
    assert x[0] == 1.0
    assert y[0] == 1e-6
    stages = {event["stage"] for event in events}
    assert "toe_fit" in stages
    assert "quasi_origin_anchor" in stages
    timestamps = {event["timestamp"] for event in events}
    assert len(timestamps) == 1


def test_process_vdyp_out_body_fit_runtime_error_falls_back() -> None:
    ages = np.array([30, 40, 50, 60, 70, 80], dtype=float)
    vols = np.array([30, 80, 140, 190, 220, 240], dtype=float)
    vdyp_df = pd.DataFrame({"Age": ages, "Vdwb": vols}).set_index("Age")
    events: list[dict[str, Any]] = []

    def _body_fit_raises(*args: Any, **kwargs: Any) -> tuple[np.ndarray, Any]:
        _ = (args, kwargs)
        raise RuntimeError("curve fit failed")

    x, y = process_vdyp_out(
        {1: vdyp_df},
        curve_fit_fn=_body_fit_raises,
        body_fit_func=_fit_func1,
        body_fit_func_bounds_func=_fit_bounds,
        toe_fit_func=_fit_func1,
        toe_fit_func_bounds_func=_fit_bounds,
        log_event=events.append,
        min_age=30,
        max_age=90,
        window=2,
    )

    assert x[0] == 1.0
    assert y[0] == 1e-6
    stages = {event["stage"] for event in events}
    assert "body_fit" in stages
    assert "body_fit_fallback" in stages


def test_process_vdyp_out_unexpected_body_fit_error_propagates() -> None:
    ages = np.array([30, 40, 50, 60, 70, 80], dtype=float)
    vols = np.array([30, 80, 140, 190, 220, 240], dtype=float)
    vdyp_df = pd.DataFrame({"Age": ages, "Vdwb": vols}).set_index("Age")

    def _body_fit_unexpected(*args: Any, **kwargs: Any) -> tuple[np.ndarray, Any]:
        _ = (args, kwargs)
        raise ZeroDivisionError("unexpected")

    with pytest.raises(ZeroDivisionError):
        process_vdyp_out(
            {1: vdyp_df},
            curve_fit_fn=_body_fit_unexpected,
            body_fit_func=_fit_func1,
            body_fit_func_bounds_func=_fit_bounds,
            toe_fit_func=_fit_func1,
            toe_fit_func_bounds_func=_fit_bounds,
            log_event=lambda _event: None,
            min_age=30,
            max_age=90,
            window=2,
        )


def test_process_vdyp_out_unexpected_toe_fit_error_propagates() -> None:
    ages = np.array([30, 40, 50, 60, 70, 80], dtype=float)
    vols = np.array([30, 80, 140, 190, 220, 240], dtype=float)
    vdyp_df = pd.DataFrame({"Age": ages, "Vdwb": vols}).set_index("Age")

    def _curve_fit_stub(
        func: Callable[..., np.ndarray], x: np.ndarray, y: np.ndarray, **kwargs: Any
    ) -> tuple[np.ndarray, Any]:
        _ = (func, x, y, kwargs)
        return np.array([0.04, 2.0, 12.0, 7.0]), None

    def _toe_unexpected(*args: Any, **kwargs: Any) -> np.ndarray:
        _ = (args, kwargs)
        raise ZeroDivisionError("unexpected toe")

    with pytest.raises(ZeroDivisionError):
        process_vdyp_out(
            {1: vdyp_df},
            curve_fit_fn=_curve_fit_stub,
            body_fit_func=_fit_func1,
            body_fit_func_bounds_func=_fit_bounds,
            toe_fit_func=_toe_unexpected,
            toe_fit_func_bounds_func=lambda _: ([0.0], [1.0]),
            log_event=lambda _event: None,
            min_age=30,
            max_age=90,
            window=2,
            max_skip_increase=2,
        )


def test_process_vdyp_out_accepts_sigma_asymmetry_kwargs() -> None:
    ages = np.array([30, 40, 50, 60, 70, 80], dtype=float)
    vols = np.array([30, 80, 140, 190, 220, 240], dtype=float)
    vdyp_df = pd.DataFrame({"Age": ages, "Vdwb": vols}).set_index("Age")
    x, y = process_vdyp_out(
        {1: vdyp_df},
        curve_fit_fn=lambda *args, **kwargs: (np.array([0.04, 2.0, 12.0, 7.0]), None),
        body_fit_func=_fit_func1,
        body_fit_func_bounds_func=_fit_bounds,
        toe_fit_func=_fit_func1,
        toe_fit_func_bounds_func=_fit_bounds,
        log_event=lambda _event: None,
        min_age=30,
        max_age=90,
        window=2,
        sigma_right_scale=0.4,
        sigma_right_offset=5.0,
    )
    assert len(x) == len(y)
    assert x[0] == 1.0


def test_process_vdyp_out_tail_blend_executes_without_error() -> None:
    ages = np.arange(30, 121, 10, dtype=float)
    vols = np.array([20, 45, 80, 110, 135, 150, 155, 152, 149, 147], dtype=float)
    vdyp_df = pd.DataFrame({"Age": ages, "Vdwb": vols}).set_index("Age")

    x_blend, y_blend = process_vdyp_out(
        {1: vdyp_df},
        curve_fit_fn=lambda *args, **kwargs: (np.array([0.03, 2.0, 8.0, 6.0]), None),
        body_fit_func=_fit_func1,
        body_fit_func_bounds_func=_fit_bounds,
        toe_fit_func=_fit_func1,
        toe_fit_func_bounds_func=_fit_bounds,
        log_event=lambda _event: None,
        min_age=30,
        max_age=140,
        window=2,
        tail_blend_enabled=True,
        tail_anchor_quantile=0.7,
        tail_blend_years=20.0,
    )
    assert len(x_blend) == len(y_blend)
    assert np.all(np.isfinite(np.asarray(y_blend)))


def test_process_vdyp_out_applies_optional_merchantable_floor() -> None:
    ages = np.arange(30, 121, 10, dtype=float)
    vols = np.array([20, 45, 80, 110, 135, 150, 155, 152, 149, 147], dtype=float)
    vdyp_df = pd.DataFrame({"Age": ages, "Vdwb": vols}).set_index("Age")
    events: list[dict[str, Any]] = []
    common_kwargs = dict(
        curve_fit_fn=lambda *args, **kwargs: (np.array([0.03, 2.0, 8.0, 6.0]), None),
        body_fit_func=_fit_func1,
        body_fit_func_bounds_func=_fit_bounds,
        toe_fit_func=_fit_func1,
        toe_fit_func_bounds_func=_fit_bounds,
        min_age=30,
        max_age=140,
        window=2,
    )

    x_base, y_base = process_vdyp_out(
        {1: vdyp_df},
        log_event=lambda _event: None,
        **common_kwargs,
    )

    x_floor, y_floor = process_vdyp_out(
        {1: vdyp_df},
        log_event=events.append,
        **common_kwargs,
        merchantable_floor_enabled=True,
        merchantable_floor_age=20.0,
        merchantable_floor_value=0.0,
    )

    floor_band = (x_floor >= 2.0) & (x_floor <= 20.0)
    assert np.allclose(np.asarray(y_floor)[floor_band], 0.0)
    shifted_expected = np.interp(
        np.asarray(x_floor, dtype=float) - 20.0,
        np.asarray(x_base, dtype=float),
        np.asarray(y_base, dtype=float),
        left=0.0,
        right=float(np.asarray(y_base, dtype=float)[-1]),
    )
    assert np.allclose(
        np.asarray(y_floor)[x_floor > 21.0], shifted_expected[x_floor > 21.0]
    )
    assert float(np.asarray(y_floor)[np.where(x_floor == 21.0)[0][0]]) > 0.0
    assert any(event.get("stage") == "merchantable_floor" for event in events)


def test_process_vdyp_out_applies_toe_location_shift_without_non_finite() -> None:
    ages = np.arange(30, 121, 10, dtype=float)
    vols = np.array([20, 45, 80, 110, 135, 150, 155, 152, 149, 147], dtype=float)
    vdyp_df = pd.DataFrame({"Age": ages, "Vdwb": vols}).set_index("Age")
    common_kwargs = dict(
        curve_fit_fn=lambda *args, **kwargs: (np.array([0.03, 2.0, 8.0, 6.0]), None),
        body_fit_func=_fit_func1,
        body_fit_func_bounds_func=_fit_bounds,
        toe_fit_func=_fit_func1,
        toe_fit_func_bounds_func=_fit_bounds,
        min_age=30,
        max_age=140,
        window=2,
    )
    x_base, y_base = process_vdyp_out(
        {1: vdyp_df},
        log_event=lambda _event: None,
        **common_kwargs,
    )
    x_shift, y_shift = process_vdyp_out(
        {1: vdyp_df},
        log_event=lambda _event: None,
        toe_shift_years=20.0,
        **common_kwargs,
    )
    assert np.array_equal(np.asarray(x_shift), np.asarray(x_base))
    assert np.all(np.isfinite(np.asarray(y_shift, dtype=float)))
    # Toe location shift should mainly perturb the left-end ramp and leave far-right
    # body/tail values effectively unchanged.
    assert not np.allclose(
        np.asarray(y_shift)[x_shift <= 60.0], np.asarray(y_base)[x_base <= 60.0]
    )
    assert np.allclose(
        np.asarray(y_shift)[x_shift >= 120.0],
        np.asarray(y_base)[x_base >= 120.0],
        atol=1e-6,
    )


def test_process_vdyp_out_tail_blend_skips_when_no_linear_tail_detected() -> None:
    ages = np.arange(30, 181, 10, dtype=float)
    # Strongly curved/oscillatory right tail to fail strict linearity gates.
    vols = np.array(
        [25, 40, 58, 79, 101, 118, 130, 138, 141, 139, 133, 124, 112, 98, 83, 68],
        dtype=float,
    )
    vdyp_df = pd.DataFrame({"Age": ages, "Vdwb": vols}).set_index("Age")
    events: list[dict[str, Any]] = []
    common_kwargs = dict(
        curve_fit_fn=lambda *args, **kwargs: (np.array([0.03, 2.0, 8.0, 6.0]), None),
        body_fit_func=_fit_func1,
        body_fit_func_bounds_func=_fit_bounds,
        toe_fit_func=_fit_func1,
        toe_fit_func_bounds_func=_fit_bounds,
        min_age=30,
        max_age=200,
        window=2,
    )
    x_base, y_base = process_vdyp_out(
        {1: vdyp_df},
        log_event=lambda _event: None,
        **common_kwargs,
    )
    x_tail, y_tail = process_vdyp_out(
        {1: vdyp_df},
        log_event=events.append,
        tail_blend_enabled=True,
        tail_linear_min_r2=0.9999,
        tail_linear_max_nrmse=1e-8,
        tail_linear_allow_quantile_fallback=False,
        **common_kwargs,
    )
    assert np.array_equal(np.asarray(x_base), np.asarray(x_tail))
    assert np.array_equal(np.asarray(y_base), np.asarray(y_tail))
    assert not any(event.get("stage") == "tail_blend" for event in events)


def test_process_vdyp_out_tail_blend_prefers_late_linear_segment() -> None:
    ages = np.arange(30, 301, 10, dtype=float)
    vols = np.where(
        ages < 200,
        18 + 1.12 * ages - 0.0022 * np.square(ages),
        160 - 0.28 * (ages - 200),
    )
    vdyp_df = pd.DataFrame({"Age": ages, "Vdwb": vols}).set_index("Age")
    events: list[dict[str, Any]] = []
    _ = process_vdyp_out(
        {1: vdyp_df},
        curve_fit_fn=lambda *args, **kwargs: (np.array([0.03, 2.0, 8.0, 6.0]), None),
        body_fit_func=_fit_func1,
        body_fit_func_bounds_func=_fit_bounds,
        toe_fit_func=_fit_func1,
        toe_fit_func_bounds_func=_fit_bounds,
        log_event=events.append,
        min_age=30,
        max_age=320,
        window=2,
        tail_blend_enabled=True,
        tail_linear_min_points=4,
        tail_linear_min_r2=0.90,
        tail_linear_max_nrmse=0.10,
        tail_linear_prefer_min_age=200.0,
        tail_linear_allow_quantile_fallback=False,
        tail_blend_years=30.0,
    )
    tail_events = [event for event in events if event.get("stage") == "tail_blend"]
    assert tail_events
    tail_event = tail_events[-1]
    assert float(tail_event["anchor_age"]) >= 200.0
    assert float(tail_event["tail_n_points"]) >= 8.0


def test_process_vdyp_out_tail_blend_requires_preferred_min_age_segment() -> None:
    ages = np.arange(30, 181, 10, dtype=float)
    # Early section is very linear, but nothing exists at/after age 200.
    vols = 30 + 0.9 * ages
    vdyp_df = pd.DataFrame({"Age": ages, "Vdwb": vols}).set_index("Age")
    events: list[dict[str, Any]] = []
    common_kwargs = dict(
        curve_fit_fn=lambda *args, **kwargs: (np.array([0.03, 2.0, 8.0, 6.0]), None),
        body_fit_func=_fit_func1,
        body_fit_func_bounds_func=_fit_bounds,
        toe_fit_func=_fit_func1,
        toe_fit_func_bounds_func=_fit_bounds,
        min_age=30,
        max_age=220,
        window=2,
    )
    x_base, y_base = process_vdyp_out(
        {1: vdyp_df},
        log_event=lambda _event: None,
        **common_kwargs,
    )
    x_tail, y_tail = process_vdyp_out(
        {1: vdyp_df},
        log_event=events.append,
        tail_blend_enabled=True,
        tail_linear_min_points=4,
        tail_linear_min_r2=0.90,
        tail_linear_max_nrmse=0.10,
        tail_linear_prefer_min_age=200.0,
        tail_linear_allow_quantile_fallback=False,
        **common_kwargs,
    )
    assert np.array_equal(np.asarray(x_base), np.asarray(x_tail))
    assert np.array_equal(np.asarray(y_base), np.asarray(y_tail))
    assert not any(event.get("stage") == "tail_blend" for event in events)
