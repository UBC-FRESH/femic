"""Shared default kwarg overrides for VDYP curve smoothing by TSA/stratum/SI."""

from __future__ import annotations

from typing import Mapping

CurveOverrideKey = tuple[str, str]
CurveOverrideMap = dict[CurveOverrideKey, dict[str, float]]

DEFAULT_VDYP_KWARG_OVERRIDES: dict[str, CurveOverrideMap] = {
    "08": {
        ("BWBS_SB", "H"): {"skip1": 30},
        ("BWBS_S", "L"): {"skip1": 50},
        ("SWB_S", "L"): {"skip1": 30},
        ("BWBS_AT", "H"): {"skip1": 30},
    },
    "16": {("SWB_SX", "L"): {"skip1": 30}},
    "24": {("ESSF_BL", "L"): {"skip1": 30}},
    "40": {
        ("BWBS_SX", "L"): {"skip1": 30},
        ("SWB_SX", "L"): {"skip1": 60, "dx_c1": 1.0, "dx_c2": 0.0},
    },
    "41": {("ESSF_BL", "L"): {"skip1": 60}, ("ESSF_SE", "M"): {"skip1": 30}},
    # TSA29: suppress pathological early-age spike for SBPS_PL low-SI curve.
    "29": {("SBPS_PL", "L"): {"skip1": 50}},
    "k3z": {
        ("CWHvm_DR+HW", "L"): {
            "body_c_min": -40,
            "toe_shift_years": 0,
            "tail_linear_min_r2": 0.05,
            "tail_linear_max_nrmse": 0.80,
            "tail_linear_prefer_min_age": 50,
            "tail_linear_flat_slope_abs": 0.35,
            "tail_linear_min_span_years": 5,
            "tail_blend_years": 150,
            "tail_linear_allow_quantile_fallback": True,
        },
        ("CWHvm_DR+HW", "M"): {
            "body_c_min": -40,
            "toe_shift_years": 0,
            "tail_linear_min_r2": 0.05,
            "tail_linear_max_nrmse": 0.80,
            "tail_linear_prefer_min_age": 50,
            "tail_linear_flat_slope_abs": 0.35,
            "tail_linear_min_span_years": 5,
            "tail_blend_years": 150,
            "tail_linear_allow_quantile_fallback": True,
        },
        ("CWHvm_DR+HW", "H"): {
            "body_c_min": -40,
            "toe_shift_years": 0,
            "tail_linear_min_r2": 0.05,
            "tail_linear_max_nrmse": 0.80,
            "tail_linear_prefer_min_age": 50,
            "tail_linear_flat_slope_abs": 0.35,
            "tail_linear_min_span_years": 5,
            "tail_blend_years": 150,
            "tail_linear_allow_quantile_fallback": True,
        },
    },
}


def vdyp_kwarg_overrides_for_tsa(
    tsa_code: str,
    *,
    defaults: Mapping[str, Mapping[CurveOverrideKey, Mapping[str, float]]]
    | None = None,
) -> CurveOverrideMap:
    """Return a defensive copy of configured smoothing-kwarg overrides for one TSA."""
    tsa = str(tsa_code).zfill(2)
    source = defaults or DEFAULT_VDYP_KWARG_OVERRIDES
    raw = source.get(tsa, {})
    return {key: dict(kwargs) for key, kwargs in raw.items()}
