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
    allow_quantile_fallback: bool,
    anchor_quantile: float,
    blend_years: float,
    slope_min: float,
    slope_max: float,
) -> tuple[np.ndarray, dict[str, float] | None]:
    def _fit_linear(x_tail: np.ndarray, y_tail: np.ndarray) -> dict[str, float] | None:
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

    def _detect_linear_tail(
        x_obs: np.ndarray, y_obs: np.ndarray
    ) -> tuple[int, dict[str, float]] | None:
        min_points = max(int(linear_min_points), 2)
        if x_obs.size < min_points:
            return None
        candidates: list[tuple[int, dict[str, float]]] = []
        for start in range(0, int(x_obs.size - min_points + 1)):
            fit = _fit_linear(x_obs[start:], y_obs[start:])
            if fit is None:
                continue
            if fit["r2"] >= float(linear_min_r2) and fit["nrmse"] <= float(
                linear_max_nrmse
            ):
                candidates.append((start, fit))
        if not candidates:
            return None
        preferred = [
            c for c in candidates if float(x_obs[c[0]]) >= float(linear_prefer_min_age)
        ]
        pool = preferred if preferred else []
        if not pool:
            return None
        pool.sort(
            key=lambda c: (
                int(x_obs.size - c[0]),  # longest linear tail first
                float(c[1]["r2"]),  # then strongest linearity
                -float(c[1]["nrmse"]),  # then lowest normalized error
            ),
            reverse=True,
        )
        return pool[0]

    if observed_age.size < 4 or observed_volume.size < 4:
        return y_curve, None
    order = np.argsort(observed_age)
    x_sorted = np.asarray(observed_age[order], dtype=float)
    y_sorted = np.asarray(observed_volume[order], dtype=float)
    unique_x, unique_idx = np.unique(x_sorted, return_index=True)
    x_sorted = unique_x
    y_sorted = y_sorted[unique_idx]

    tail_detect = _detect_linear_tail(x_sorted, y_sorted)
    if tail_detect is None and allow_quantile_fallback:
        q = float(np.clip(anchor_quantile, 0.50, 0.95))
        anchor_age = float(np.quantile(x_sorted, q))
        tail_mask = x_sorted >= anchor_age
        if int(np.count_nonzero(tail_mask)) < max(int(linear_min_points), 2):
            return y_curve, None
        fit = _fit_linear(x_sorted[tail_mask], y_sorted[tail_mask])
        if fit is None:
            return y_curve, None
        tail_start_idx = int(np.argmax(tail_mask))
    elif tail_detect is not None:
        tail_start_idx, fit = tail_detect
        anchor_age = float(x_sorted[tail_start_idx])
    else:
        return y_curve, None

    slope_raw = float(fit["slope"])
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
        "tail_n_points": float(x_sorted.size - tail_start_idx),
        "tail_r2": float(fit["r2"]),
        "tail_nrmse": float(fit["nrmse"]),
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
) -> tuple[np.ndarray, np.ndarray, tuple[int, np.ndarray]]:
    """Fill left tail with a toe-fit curve and return fitted arrays plus toe metadata."""
    x_ = np.asarray(x, dtype=float).copy()
    y_ = np.asarray(y, dtype=float).copy()
    i1 = int(np.argmax(y_ > 0.0))
    x_fit = np.concatenate(([1 + dx, 2 + dx, 3 + dx], x_[i1 + skip : i1 + skip + di]))
    y_fit = np.concatenate(([1 * cy, 2 * cy, 3 * cy], y_[i1 + skip : i1 + skip + di]))
    bounds = toe_fit_func_bounds_func(x_fit)
    popt, _ = curve_fit_fn(toe_fit_func, x_fit, y_fit, maxfev=maxfev, bounds=bounds)
    y_[: i1 + skip] = toe_fit_func(x_[: i1 + skip], *popt)
    return x_, y_, (i1 + skip, np.asarray(popt, dtype=float))


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
    window: int = 10,
    skip1: int = 0,
    skip2: int = 30,
    tail_blend_enabled: bool = False,
    tail_linear_min_points: int = 4,
    tail_linear_min_r2: float = 0.97,
    tail_linear_max_nrmse: float = 0.08,
    tail_linear_prefer_min_age: float = 200.0,
    tail_linear_allow_quantile_fallback: bool = False,
    tail_anchor_quantile: float = 0.70,
    tail_blend_years: float = 30.0,
    tail_slope_min: float = -1.0,
    tail_slope_max: float = 0.15,
    maxfev: int = 100000,
    max_skip_increase: int = 30,
    skip_step: int = 1,
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
    c_all = vdyp_out_concat.groupby(level="Age")[volume_flavour].median()
    c_all = c_all[c_all > 0]
    c = c_all[c_all.index >= min_age]
    if c.empty:
        return fallback_curve(
            stage="body_input",
            reason="no_points_after_min_age_filter",
            x_raw=c_all.index.values,
            y_raw=c_all.values,
        )

    x = c.index.values
    y = c.rolling(window=window, center=True).median().values
    x, y = x[y > 0], y[y > 0]
    x, y = x[skip1:], y[skip1:]
    if len(x) < 4 or len(y) < 4:
        return fallback_curve(
            stage="body_input",
            reason="insufficient_points_after_smoothing",
            x_raw=c.index.values,
            y_raw=c.values,
        )

    y_mai = pd_mod.Series(y / x, x)
    if y_mai.empty:
        return fallback_curve(
            stage="body_input",
            reason="empty_mai_series",
            x_raw=c.index.values,
            y_raw=c.values,
        )

    y_mai_max_age = y_mai.idxmax()
    sigma = (np.abs(x - y_mai_max_age) + sigma_c1) ** sigma_c2
    if sigma_right_scale != 1.0 or sigma_right_offset != 0.0:
        right_start = float(y_mai_max_age) + float(sigma_right_offset)
        right_mask = x >= right_start
        if np.any(right_mask):
            sigma = np.asarray(sigma, dtype=float)
            sigma[right_mask] = np.maximum(
                float(sigma_min),
                sigma[right_mask] * float(sigma_right_scale),
            )
    try:
        popt, _ = curve_fit_fn(
            body_fit_func,
            x,
            y,
            bounds=body_fit_func_bounds_func(x),
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
            x_points=int(len(x)),
            skip1=int(skip1),
            skip2=int(skip2),
        )
        return fallback_curve(
            stage="body_fit_fallback",
            reason="body_fit_exception",
            x_raw=x,
            y_raw=y,
            exc=exc,
        )

    x = np.array(range(1, max_age), dtype=float)
    y = body_fit_func(x, *popt)
    if not np.any(np.isfinite(y)):
        return fallback_curve(
            stage="body_fit_output",
            reason="non_finite_body_curve",
            x_raw=x,
            y_raw=np.asarray(c.values, dtype=float),
        )
    y = np.nan_to_num(y, nan=0.0, posinf=0.0, neginf=0.0)
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
            )
            used_skip = skip2 + extra
            if used_skip != skip2:
                emit(f"vdyp toe fit: increased skip to {used_skip}")
            emit(str(popt_toe))
            if tail_blend_enabled:
                y_blend, tail_meta = _blend_right_tail_linear(
                    x_curve=np.asarray(x_, dtype=float),
                    y_curve=np.asarray(y_, dtype=float),
                    observed_age=np.asarray(c.index.values, dtype=float),
                    observed_volume=np.asarray(c.values, dtype=float),
                    linear_min_points=int(tail_linear_min_points),
                    linear_min_r2=float(tail_linear_min_r2),
                    linear_max_nrmse=float(tail_linear_max_nrmse),
                    linear_prefer_min_age=float(tail_linear_prefer_min_age),
                    allow_quantile_fallback=bool(tail_linear_allow_quantile_fallback),
                    anchor_quantile=float(tail_anchor_quantile),
                    blend_years=float(tail_blend_years),
                    slope_min=float(tail_slope_min),
                    slope_max=float(tail_slope_max),
                )
                y_ = y_blend
                if tail_meta is not None:
                    tail_meta_payload: dict[str, Any] = dict(tail_meta)
                    emit_curve_event(
                        status="ok",
                        stage="tail_blend",
                        **tail_meta_payload,
                    )
            x_, y_ = _apply_merchantable_floor(
                np.asarray(x_, dtype=float),
                np.asarray(y_, dtype=float),
            )
            x_, y_ = prepend_quasi_origin_point(x_, y_)
            emit_curve_event(
                status="ok",
                stage="toe_fit",
                vdyp_tables=int(len(vdyp_tables)),
                x_points=int(len(x)),
                skip1=int(skip1),
                skip2=int(skip2),
                skip_used=int(used_skip),
                dx=float(dx),
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
        x_points=int(len(x)),
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
    if tail_blend_enabled:
        y_blend, tail_meta = _blend_right_tail_linear(
            x_curve=np.asarray(x, dtype=float),
            y_curve=np.asarray(y, dtype=float),
            observed_age=np.asarray(c.index.values, dtype=float),
            observed_volume=np.asarray(c.values, dtype=float),
            linear_min_points=int(tail_linear_min_points),
            linear_min_r2=float(tail_linear_min_r2),
            linear_max_nrmse=float(tail_linear_max_nrmse),
            linear_prefer_min_age=float(tail_linear_prefer_min_age),
            allow_quantile_fallback=bool(tail_linear_allow_quantile_fallback),
            anchor_quantile=float(tail_anchor_quantile),
            blend_years=float(tail_blend_years),
            slope_min=float(tail_slope_min),
            slope_max=float(tail_slope_max),
        )
        y = y_blend
        if tail_meta is not None:
            tail_meta_payload = dict(tail_meta)
            emit_curve_event(
                status="ok",
                stage="tail_blend",
                **tail_meta_payload,
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
