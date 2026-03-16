"""Reusable VDYP curve smoothing/fitting helpers."""

from __future__ import annotations

import importlib
from typing import Any, Callable
import traceback

import numpy as np

from femic.pipeline.diagnostics import build_timestamped_event

CurveFitFn = Callable[..., tuple[np.ndarray, Any]]
BoundsFn = Callable[[np.ndarray], tuple[Any, Any]]
EventLoggerFn = Callable[[dict[str, Any]], None]
MessageFn = Callable[[str], None]


def _curve_fit_fallback_exception_types() -> tuple[type[Exception], ...]:
    """Operational curve-fit/toe-fit failures that should trigger legacy fallback curves."""
    return (
        RuntimeError,
        ValueError,
        TypeError,
        OverflowError,
        FloatingPointError,
        np.linalg.LinAlgError,
    )


def legacy_fit_func1(
    x: np.ndarray, a: float, b: float, c: float, s: float
) -> np.ndarray:
    """Legacy body/toe fit function used in notebook-era curve smoothing."""
    # Guard fractional powers against x<c domain issues by clipping to zero.
    # This preserves the intended gamma-like form while avoiding NaN payloads.
    delta = np.maximum(np.asarray(x, dtype=float) - float(c), 0.0)
    return s * (a * (delta**b)) * np.exp(-a * delta)


def legacy_fit_func1_bounds_func(x: np.ndarray) -> tuple[list[float], list[float]]:
    """Bounds function for legacy_fit_func1 with c capped by min(x) and 100."""
    return ([0.000, 0, 0, 0], [1.00, 50, max(1, min(np.min(x), 100)), 10])


def legacy_fit_func2(x: np.ndarray, a: float, b: float) -> np.ndarray:
    """Legacy splice-fit function used for left-tail blending diagnostics."""
    return a * np.power(x, b) * np.power(x, -a)


def legacy_fit_func2_bounds_func(
    _x: np.ndarray,
) -> tuple[tuple[int, int], tuple[int, int]]:
    """Bounds function for legacy_fit_func2."""
    return (0, 0), (10, 10)


def prepend_quasi_origin_point(
    x: np.ndarray | list[float],
    y: np.ndarray | list[float],
    *,
    age: float = 1.0,
    epsilon: float = 1e-6,
) -> tuple[np.ndarray, np.ndarray]:
    """Ensure curves are anchored at quasi-origin `(age, epsilon)`."""
    x_arr = np.asarray(x, dtype=float)
    y_arr = np.asarray(y, dtype=float)
    if x_arr.size == 0:
        return np.array([age], dtype=float), np.array([epsilon], dtype=float)
    if x_arr[0] == age:
        y_out = y_arr.copy()
        y_out[0] = epsilon
        return x_arr, y_out
    return np.insert(x_arr, 0, age), np.insert(y_arr, 0, epsilon)


def build_observed_bins_for_fit(
    *,
    vdyp_out_concat: Any,
    volume_flavour: str,
    min_age: int,
    max_age: int,
    bin_years: int = 5,
) -> Any:
    """Build time-aggregated observed medians used for NLLS/tail fitting."""
    pd_mod = importlib.import_module("pandas")
    observed = vdyp_out_concat[[volume_flavour]].dropna().reset_index()
    if "Age" not in observed.columns:
        return pd_mod.DataFrame(columns=["age_bin", "median_volume"])
    observed = observed[["Age", volume_flavour]].dropna()
    observed = observed[
        (observed["Age"] >= float(min_age))
        & (observed["Age"] <= float(max_age))
        & np.isfinite(observed["Age"])
        & np.isfinite(observed[volume_flavour])
        & (observed[volume_flavour] > 0)
    ]
    if observed.empty:
        return pd_mod.DataFrame(columns=["age_bin", "median_volume"])
    years = max(1, int(bin_years))
    observed["age_bin"] = np.floor(
        observed["Age"].astype(float) / float(years)
    ) * float(years)
    binned = (
        observed.groupby("age_bin", as_index=False)
        .agg(median_volume=(volume_flavour, "median"))
        .sort_values("age_bin")
        .reset_index(drop=True)
    )
    return binned


def _fit_linear_tail(
    x_tail: np.ndarray,
    y_tail: np.ndarray,
) -> dict[str, float] | None:
    if x_tail.size < 2:
        return None
    x_mean = float(np.mean(x_tail))
    y_mean = float(np.mean(y_tail))
    den = float(np.sum(np.square(x_tail - x_mean)))
    if den <= 0:
        return None
    slope = float(np.sum((x_tail - x_mean) * (y_tail - y_mean)) / den)
    intercept = y_mean - slope * x_mean
    y_hat = slope * x_tail + intercept
    resid = y_tail - y_hat
    rmse = float(np.sqrt(np.mean(np.square(resid))))
    ss_tot = float(np.sum(np.square(y_tail - y_mean)))
    r2 = 1.0 if ss_tot <= 0 else float(1.0 - (np.sum(np.square(resid)) / ss_tot))
    scale = max(
        float(np.nanmedian(np.abs(y_tail))),
        float(np.nanmax(y_tail) - np.nanmin(y_tail)),
        1.0,
    )
    nrmse = float(rmse / scale)
    return {
        "slope": slope,
        "intercept": intercept,
        "rmse": rmse,
        "r2": r2,
        "nrmse": nrmse,
    }


def detect_linear_tail_segment(
    *,
    observed_age: np.ndarray,
    observed_volume: np.ndarray,
    linear_min_points: int,
    linear_min_r2: float,
    linear_max_nrmse: float,
    linear_prefer_min_age: float,
    linear_flat_slope_abs: float,
    linear_min_span_years: float,
) -> dict[str, float] | None:
    """Detect a straight-ish right-tail segment by scanning bins from right to left."""
    if observed_age.size < 4 or observed_volume.size < 4:
        return None
    order = np.argsort(observed_age)
    x_sorted = np.asarray(observed_age[order], dtype=float)
    y_sorted = np.asarray(observed_volume[order], dtype=float)
    unique_x, unique_idx = np.unique(x_sorted, return_index=True)
    x_sorted = unique_x
    y_sorted = y_sorted[unique_idx]

    min_points = max(int(linear_min_points), 2)
    n = int(x_sorted.size)
    if n < min_points:
        return None

    best_start: int | None = None
    best_fit: dict[str, float] | None = None
    best_span_years: float | None = None
    seen_passing_segment = False
    for candidate_start in range(n - min_points, -1, -1):
        candidate_fit = _fit_linear_tail(
            x_sorted[candidate_start:],
            y_sorted[candidate_start:],
        )
        if candidate_fit is None:
            if seen_passing_segment:
                break
            continue
        passes = candidate_fit["nrmse"] <= float(linear_max_nrmse) and (
            candidate_fit["r2"] >= float(linear_min_r2)
            or abs(float(candidate_fit["slope"]))
            <= float(max(0.0, linear_flat_slope_abs))
        )
        if passes:
            anchor_age = float(x_sorted[candidate_start])
            tail_end_age = float(x_sorted[-1])
            tail_span_years = max(0.0, tail_end_age - anchor_age)
            if anchor_age >= float(linear_prefer_min_age) and tail_span_years >= float(
                max(0.0, linear_min_span_years)
            ):
                best_start = candidate_start
                best_fit = candidate_fit
                best_span_years = tail_span_years
            seen_passing_segment = True
            continue
        if seen_passing_segment:
            break

    if best_start is None or best_fit is None or best_span_years is None:
        return None

    anchor_age = float(x_sorted[best_start])
    return {
        "anchor_age": anchor_age,
        "tail_n_points": float(n - best_start),
        "tail_span_years": float(best_span_years),
        "tail_r2": float(best_fit["r2"]),
        "tail_nrmse": float(best_fit["nrmse"]),
        "tail_slope_raw": float(best_fit["slope"]),
        "tail_intercept_raw": float(best_fit["intercept"]),
    }


def _blend_right_tail_linear(
    *,
    x_curve: np.ndarray,
    y_curve: np.ndarray,
    observed_age: np.ndarray,
    observed_volume: np.ndarray,
    linear_min_points: int,
    linear_min_r2: float,
    linear_max_nrmse: float,
    linear_prefer_min_age: float,
    linear_flat_slope_abs: float,
    linear_min_span_years: float,
    allow_quantile_fallback: bool,
    anchor_quantile: float,
    blend_years: float,
    slope_min: float,
    slope_max: float,
    tail_detect_hint: dict[str, float] | None = None,
) -> tuple[np.ndarray, dict[str, float] | None]:
    if observed_age.size < 4 or observed_volume.size < 4:
        return y_curve, None
    order = np.argsort(observed_age)
    x_sorted = np.asarray(observed_age[order], dtype=float)
    y_sorted = np.asarray(observed_volume[order], dtype=float)
    unique_x, unique_idx = np.unique(x_sorted, return_index=True)
    x_sorted = unique_x
    y_sorted = y_sorted[unique_idx]

    tail_meta = dict(tail_detect_hint) if tail_detect_hint is not None else None
    if tail_meta is None:
        detected = detect_linear_tail_segment(
            observed_age=x_sorted,
            observed_volume=y_sorted,
            linear_min_points=linear_min_points,
            linear_min_r2=linear_min_r2,
            linear_max_nrmse=linear_max_nrmse,
            linear_prefer_min_age=linear_prefer_min_age,
            linear_flat_slope_abs=linear_flat_slope_abs,
            linear_min_span_years=linear_min_span_years,
        )
        if detected is not None:
            tail_meta = dict(detected)
    if tail_meta is None and allow_quantile_fallback:
        q = float(np.clip(anchor_quantile, 0.50, 0.95))
        anchor_age_fallback = float(np.quantile(x_sorted, q))
        tail_mask = x_sorted >= anchor_age_fallback
        if int(np.count_nonzero(tail_mask)) < max(int(linear_min_points), 2):
            return y_curve, None
        fit = _fit_linear_tail(x_sorted[tail_mask], y_sorted[tail_mask])
        if fit is None:
            return y_curve, None
        tail_meta = {
            "anchor_age": anchor_age_fallback,
            "tail_n_points": float(np.count_nonzero(tail_mask)),
            "tail_span_years": float(
                max(0.0, float(np.max(x_sorted)) - anchor_age_fallback)
            ),
            "tail_r2": float(fit["r2"]),
            "tail_nrmse": float(fit["nrmse"]),
            "tail_slope_raw": float(fit["slope"]),
            "tail_intercept_raw": float(fit["intercept"]),
        }
    if tail_meta is None:
        return y_curve, None

    anchor_age = float(tail_meta["anchor_age"])
    slope_raw = float(tail_meta["tail_slope_raw"])
    slope = float(np.clip(slope_raw, slope_min, slope_max))
    y_anchor = float(np.interp(anchor_age, x_curve, y_curve))
    intercept = y_anchor - slope * anchor_age
    y_tail_line = slope * x_curve + intercept
    y_tail_line = np.maximum(y_tail_line, 0.0)

    end_age = min(float(np.max(x_curve)), anchor_age + max(1.0, float(blend_years)))
    y_new = y_curve.copy()
    mid = (x_curve >= anchor_age) & (x_curve <= end_age)
    if np.any(mid):
        w = (x_curve[mid] - anchor_age) / max(1.0, end_age - anchor_age)
        y_new[mid] = (1.0 - w) * y_curve[mid] + w * y_tail_line[mid]
    right = x_curve > end_age
    y_new[right] = y_tail_line[right]
    return y_new, {
        "anchor_age": anchor_age,
        "tail_n_points": float(tail_meta["tail_n_points"]),
        "tail_span_years": float(tail_meta.get("tail_span_years", 0.0)),
        "tail_r2": float(tail_meta["tail_r2"]),
        "tail_nrmse": float(tail_meta["tail_nrmse"]),
        "tail_slope_raw": slope_raw,
        "tail_slope": slope,
        "tail_end_age": end_age,
    }


def fill_curve_left(
    x: np.ndarray,
    y: np.ndarray,
    *,
    curve_fit_fn: CurveFitFn,
    toe_fit_func: Callable[..., np.ndarray],
    toe_fit_func_bounds_func: BoundsFn,
    maxfev: int = 10000,
    skip: int = 10,
    dx: float = 0.0,
    di: int = 20,
    cy: float = 0.1,
    toe_shift_years: float = 0.0,
) -> tuple[np.ndarray, np.ndarray, tuple[int, np.ndarray]]:
    """Fill left tail with a toe-fit curve and return fitted arrays plus toe metadata."""
    x_ = np.asarray(x, dtype=float).copy()
    y_ = np.asarray(y, dtype=float).copy()
    i1 = int(np.argmax(y_ > 0.0))
    join_idx = int(min(max(i1 + skip, 0), max(y_.size - 1, 0)))
    x_fit = np.concatenate(([1 + dx, 2 + dx, 3 + dx], x_[join_idx : join_idx + di]))
    y_fit = np.concatenate(([1 * cy, 2 * cy, 3 * cy], y_[join_idx : join_idx + di]))
    bounds = toe_fit_func_bounds_func(x_fit)
    popt, _ = curve_fit_fn(
        toe_fit_func,
        x_fit,
        y_fit,
        maxfev=maxfev,
        bounds=bounds,
    )
    x_left = np.asarray(x_[:join_idx], dtype=float)
    body_left = np.asarray(y_[:join_idx], dtype=float)
    shift = max(0.0, float(toe_shift_years))
    popt_eval = np.asarray(popt, dtype=float).copy()
    has_location_param = popt_eval.size >= 3
    effective_shift = 0.0 if has_location_param else shift
    if effective_shift > 0.0:
        # No explicit location parameter available; shift x with an epsilon floor.
        y_left = toe_fit_func(np.maximum(x_left - effective_shift, 1e-6), *popt_eval)
    else:
        y_left = toe_fit_func(x_left, *popt_eval)

    y_left = np.nan_to_num(
        np.asarray(y_left, dtype=float), nan=0.0, posinf=0.0, neginf=0.0
    )
    if y_left.size:
        join_value = float(y_[join_idx])
        y_left = np.clip(y_left, 0.0, max(join_value, 0.0))
        y_left = np.maximum.accumulate(y_left)
        # Force a smooth splice by blending toe into body over the final window.
        blend_width = min(
            int(y_left.size),
            max(6, int(np.clip(effective_shift, 6.0, 20.0))),
        )
        if blend_width > 1:
            blend_start = int(y_left.size - blend_width)
            w = np.linspace(0.0, 1.0, blend_width)
            y_left[blend_start:] = (1.0 - w) * y_left[blend_start:] + w * body_left[
                blend_start:
            ]
    y_[:join_idx] = y_left
    return x_, y_, (join_idx, np.asarray(popt, dtype=float))


def process_vdyp_out(
    vdyp_out: dict[Any, Any],
    *,
    curve_fit_fn: CurveFitFn,
    body_fit_func: Callable[..., np.ndarray],
    body_fit_func_bounds_func: BoundsFn,
    toe_fit_func: Callable[..., np.ndarray],
    toe_fit_func_bounds_func: BoundsFn,
    log_event: EventLoggerFn,
    message: MessageFn | None = None,
    curve_context: dict[str, Any] | None = None,
    volume_flavour: str = "Vdwb",
    min_age: int = 30,
    max_age: int = 300,
    sigma_c1: float = 10,
    sigma_c2: float = 0.4,
    sigma_right_scale: float = 1.0,
    sigma_right_offset: float = 0.0,
    sigma_min: float = 1e-6,
    dx_c1: float = 0.5,
    dx_c2: float = 10,
    window: int = 3,
    skip1: int = 0,
    skip2: int = 30,
    tail_blend_enabled: bool = False,
    tail_linear_min_points: int = 4,
    tail_linear_min_r2: float = 0.97,
    tail_linear_max_nrmse: float = 0.08,
    tail_linear_prefer_min_age: float = 200.0,
    tail_linear_flat_slope_abs: float = 0.04,
    tail_linear_min_span_years: float = 80.0,
    tail_linear_allow_quantile_fallback: bool = False,
    tail_anchor_quantile: float = 0.70,
    tail_blend_years: float = 30.0,
    tail_slope_min: float = -1.0,
    tail_slope_max: float = 0.15,
    maxfev: int = 100000,
    max_skip_increase: int = 30,
    skip_step: int = 1,
    toe_shift_years: float = 0.0,
    merchantable_floor_enabled: bool = False,
    merchantable_floor_age: float = 20.0,
    merchantable_floor_value: float = 0.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Build smoothed VDYP curve with toe splice and quasi-origin fallback behavior."""
    base_event = build_timestamped_event(
        event="vdyp_curve",
        context=dict(curve_context) if curve_context else {},
    )
    base_timestamp = str(base_event["timestamp"])
    base_context = dict(base_event.get("context", {}))

    def emit(msg: str) -> None:
        if message is not None:
            message(msg)

    def emit_curve_event(
        *,
        status: str,
        stage: str,
        event: str = "vdyp_curve",
        **fields: Any,
    ) -> None:
        log_event(
            build_timestamped_event(
                event=event,
                timestamp=base_timestamp,
                context=base_context,
                status=status,
                stage=stage,
                **fields,
            )
        )

    def _apply_merchantable_floor(
        x_curve: np.ndarray,
        y_curve: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray]:
        if not merchantable_floor_enabled:
            return x_curve, y_curve
        x_arr = np.asarray(x_curve, dtype=float)
        y_arr = np.asarray(y_curve, dtype=float)
        floor_age = float(merchantable_floor_age)
        floor_value = float(merchantable_floor_value)
        shifted_age = x_arr - floor_age
        shifted_curve = np.interp(
            shifted_age,
            x_arr,
            y_arr,
            left=floor_value,
            right=float(y_arr[-1]) if y_arr.size else floor_value,
        )
        floor_mask = x_arr <= floor_age
        if np.any(floor_mask):
            shifted_curve[floor_mask] = floor_value
        emit_curve_event(
            status="ok",
            stage="merchantable_floor",
            floor_age=floor_age,
            floor_value=floor_value,
            mode="right_shift",
            shift_years=floor_age,
            floor_point_count=int(np.count_nonzero(floor_mask)),
        )
        return x_arr, shifted_curve

    toe_shift = max(0.0, float(toe_shift_years))

    def fallback_curve(
        *,
        stage: str,
        reason: str,
        x_raw: np.ndarray | None = None,
        y_raw: np.ndarray | None = None,
        exc: Exception | None = None,
    ) -> tuple[np.ndarray, np.ndarray]:
        if x_raw is None or y_raw is None:
            x_arr = np.array([], dtype=float)
            y_arr = np.array([], dtype=float)
        else:
            x_arr = np.asarray(x_raw, dtype=float)
            y_arr = np.asarray(y_raw, dtype=float)
            mask = np.isfinite(x_arr) & np.isfinite(y_arr) & (y_arr > 0)
            x_arr, y_arr = x_arr[mask], y_arr[mask]
            if x_arr.size:
                order = np.argsort(x_arr)
                x_arr, y_arr = x_arr[order], y_arr[order]
                x_arr, unique_idx = np.unique(x_arr, return_index=True)
                y_arr = y_arr[unique_idx]
        x_arr, y_arr = prepend_quasi_origin_point(x_arr, y_arr)
        payload: dict[str, Any] = {
            "reason": reason,
            "first_age": float(x_arr[0]),
            "first_volume": float(y_arr[0]),
        }
        if exc is not None:
            payload["error"] = str(exc)
            payload["error_type"] = type(exc).__name__
            payload["traceback"] = traceback.format_exc()
        emit_curve_event(status="warning", stage=stage, **payload)
        return x_arr, y_arr

    pd_mod = importlib.import_module("pandas")
    vdyp_tables = [v for v in vdyp_out.values() if isinstance(v, pd_mod.DataFrame)]
    if not vdyp_tables:
        return fallback_curve(stage="preflight", reason="empty_vdyp_out")

    vdyp_out_concat = pd_mod.concat(vdyp_tables)
    binned = build_observed_bins_for_fit(
        vdyp_out_concat=vdyp_out_concat,
        volume_flavour=volume_flavour,
        min_age=min_age,
        max_age=max_age,
        bin_years=5,
    )
    if binned.empty:
        return fallback_curve(
            stage="body_input",
            reason="no_points_after_min_age_filter",
            x_raw=np.array([], dtype=float),
            y_raw=np.array([], dtype=float),
        )

    x = np.asarray(binned["age_bin"].values, dtype=float)
    y = (
        binned["median_volume"]
        .rolling(window=int(max(1, window)), center=True, min_periods=1)
        .median()
        .values
    )
    x, y = (
        x[np.asarray(y, dtype=float) > 0],
        np.asarray(y, dtype=float)[np.asarray(y, dtype=float) > 0],
    )
    x, y = x[skip1:], y[skip1:]
    x_obs_fit = np.asarray(x, dtype=float)
    y_obs_fit = np.asarray(y, dtype=float)
    tail_detect_prefit: dict[str, float] | None = None
    if tail_blend_enabled:
        tail_detect_prefit = detect_linear_tail_segment(
            observed_age=np.asarray(binned["age_bin"].values, dtype=float),
            observed_volume=np.asarray(binned["median_volume"].values, dtype=float),
            linear_min_points=int(tail_linear_min_points),
            linear_min_r2=float(tail_linear_min_r2),
            linear_max_nrmse=float(tail_linear_max_nrmse),
            linear_prefer_min_age=float(tail_linear_prefer_min_age),
            linear_flat_slope_abs=float(tail_linear_flat_slope_abs),
            linear_min_span_years=float(tail_linear_min_span_years),
        )
    if tail_detect_prefit is not None:
        tail_anchor_age = float(tail_detect_prefit["anchor_age"])
        body_mask = x_obs_fit < tail_anchor_age
        if int(np.count_nonzero(body_mask)) >= 4:
            x_fit_base = x_obs_fit[body_mask]
            y_fit_base = y_obs_fit[body_mask]
        else:
            x_fit_base = x_obs_fit
            y_fit_base = y_obs_fit
    else:
        x_fit_base = x_obs_fit
        y_fit_base = y_obs_fit
    x_fit = np.asarray(x_fit_base, dtype=float)
    if len(x_fit_base) < 4 or len(y_fit_base) < 4:
        return fallback_curve(
            stage="body_input",
            reason="insufficient_points_after_smoothing",
            x_raw=np.asarray(binned["age_bin"].values, dtype=float),
            y_raw=np.asarray(binned["median_volume"].values, dtype=float),
        )

    y_mai = pd_mod.Series(y_fit_base / np.maximum(x_fit, 1.0), x_fit_base)
    if y_mai.empty:
        return fallback_curve(
            stage="body_input",
            reason="empty_mai_series",
            x_raw=np.asarray(binned["age_bin"].values, dtype=float),
            y_raw=np.asarray(binned["median_volume"].values, dtype=float),
        )

    y_mai_max_age = y_mai.idxmax()
    sigma = (np.abs(x_fit_base - y_mai_max_age) + sigma_c1) ** sigma_c2
    if sigma_right_scale != 1.0 or sigma_right_offset != 0.0:
        right_start = float(y_mai_max_age) + float(sigma_right_offset)
        right_mask = x_fit_base >= right_start
        if np.any(right_mask):
            sigma = np.asarray(sigma, dtype=float)
            sigma[right_mask] = np.maximum(
                float(sigma_min),
                sigma[right_mask] * float(sigma_right_scale),
            )
    try:
        popt, _ = curve_fit_fn(
            body_fit_func,
            x_fit,
            y_fit_base,
            bounds=body_fit_func_bounds_func(x_fit),
            maxfev=maxfev,
            sigma=sigma,
        )
    except _curve_fit_fallback_exception_types() as exc:
        emit_curve_event(
            status="error",
            stage="body_fit",
            error=str(exc),
            traceback=traceback.format_exc(),
            vdyp_tables=int(len(vdyp_tables)),
            x_points=int(len(x_fit_base)),
            skip1=int(skip1),
            skip2=int(skip2),
        )
        return fallback_curve(
            stage="body_fit_fallback",
            reason="body_fit_exception",
            x_raw=x_fit_base,
            y_raw=y_fit_base,
            exc=exc,
        )

    x = np.array(range(1, max_age), dtype=float)
    y = body_fit_func(x, *popt)
    if not np.any(np.isfinite(y)):
        return fallback_curve(
            stage="body_fit_output",
            reason="non_finite_body_curve",
            x_raw=x,
            y_raw=np.asarray(binned["median_volume"].values, dtype=float),
        )
    y = np.nan_to_num(y, nan=0.0, posinf=0.0, neginf=0.0)
    if tail_blend_enabled:
        y_blend, tail_meta = _blend_right_tail_linear(
            x_curve=np.asarray(x, dtype=float),
            y_curve=np.asarray(y, dtype=float),
            observed_age=np.asarray(binned["age_bin"].values, dtype=float),
            observed_volume=np.asarray(binned["median_volume"].values, dtype=float),
            linear_min_points=int(tail_linear_min_points),
            linear_min_r2=float(tail_linear_min_r2),
            linear_max_nrmse=float(tail_linear_max_nrmse),
            linear_prefer_min_age=float(tail_linear_prefer_min_age),
            linear_flat_slope_abs=float(tail_linear_flat_slope_abs),
            linear_min_span_years=float(tail_linear_min_span_years),
            allow_quantile_fallback=bool(tail_linear_allow_quantile_fallback),
            anchor_quantile=float(tail_anchor_quantile),
            blend_years=float(tail_blend_years),
            slope_min=float(tail_slope_min),
            slope_max=float(tail_slope_max),
            tail_detect_hint=tail_detect_prefit,
        )
        y = y_blend
        if tail_meta is not None:
            emit_curve_event(
                status="ok",
                stage="tail_blend",
                anchor_age=float(tail_meta["anchor_age"]),
                tail_n_points=float(tail_meta["tail_n_points"]),
                tail_span_years=float(tail_meta["tail_span_years"]),
                tail_r2=float(tail_meta["tail_r2"]),
                tail_nrmse=float(tail_meta["tail_nrmse"]),
                tail_slope_raw=float(tail_meta["tail_slope_raw"]),
                tail_slope=float(tail_meta["tail_slope"]),
                tail_end_age=float(tail_meta["tail_end_age"]),
            )
    dx = max(0, dx_c1 * float(popt[2]) - dx_c2)
    emit(str(dx))
    used_skip: int | None = None
    last_exc: Exception | None = None
    for extra in range(0, max_skip_increase + 1, skip_step):
        try:
            x_, y_, (_, popt_toe) = fill_curve_left(
                x.copy(),
                y.copy(),
                curve_fit_fn=curve_fit_fn,
                toe_fit_func=toe_fit_func,
                toe_fit_func_bounds_func=toe_fit_func_bounds_func,
                skip=skip2 + extra,
                dx=dx,
                maxfev=maxfev,
                toe_shift_years=toe_shift,
            )
            used_skip = skip2 + extra
            if used_skip != skip2:
                emit(f"vdyp toe fit: increased skip to {used_skip}")
            emit(str(popt_toe))
            x_, y_ = _apply_merchantable_floor(
                np.asarray(x, dtype=float),
                np.asarray(y_, dtype=float),
            )
            x_, y_ = prepend_quasi_origin_point(x_, y_)
            emit_curve_event(
                status="ok",
                stage="toe_fit",
                vdyp_tables=int(len(vdyp_tables)),
                x_points=int(len(x_fit_base)),
                skip1=int(skip1),
                skip2=int(skip2),
                skip_used=int(used_skip),
                dx=float(dx),
                toe_shift_years=float(toe_shift),
                first_age=float(x_[0]),
                first_volume=float(y_[0]),
            )
            return x_, y_
        except _curve_fit_fallback_exception_types() as exc:
            last_exc = exc
            continue

    emit_curve_event(
        status="warning",
        stage="toe_fit",
        vdyp_tables=int(len(vdyp_tables)),
        x_points=int(len(x_fit_base)),
        skip1=int(skip1),
        skip2=int(skip2),
        skip_max=int(skip2 + max_skip_increase),
        dx=float(dx),
        error=str(last_exc),
    )
    emit(
        "vdyp toe fit failed; returning body fit curve with quasi-origin "
        "(1, epsilon) anchor"
    )
    x, y = _apply_merchantable_floor(
        np.asarray(x, dtype=float),
        np.asarray(y, dtype=float),
    )
    x, y = prepend_quasi_origin_point(x, y)
    emit_curve_event(
        event="vdyp_curve_anchor",
        status="warning",
        stage="quasi_origin_anchor",
        first_age=float(x[0]),
        first_volume=float(y[0]),
    )
    return x, y
