"""Patchworks export helpers (ForestModel XML + fragments shapefile)."""

from __future__ import annotations

from dataclasses import dataclass
import importlib
import math
import re
from pathlib import Path
from typing import Any, Iterable
import xml.etree.ElementTree as et

import numpy as np
import pandas as pd
import yaml

from .adapters import (
    build_bundle_model_context,
    build_bundle_model_context_from_tables,
    normalize_tsa_code,
)
from .core import (
    AttributeBinding,
    BundleModelContext,
    CurvePoint,
    DefineFieldDefinition,
    ForestModelDefinition,
    RetentionDefinition,
    SelectDefinition,
    TreatmentAssignment,
    TreatmentDefinition,
)


DEFAULT_START_YEAR = 2026
DEFAULT_HORIZON_YEARS = 300
DEFAULT_CC_MIN_AGE = 0
DEFAULT_CC_MAX_AGE = 1000
DEFAULT_CC_TRANSITION_IFM: str | None = None
DEFAULT_FRAGMENTS_CRS = "EPSG:3005"
DEFAULT_IFM_SOURCE_COL: str | None = None
DEFAULT_IFM_THRESHOLD: float | None = None
DEFAULT_IFM_TARGET_MANAGED_SHARE: float | None = None
DEFAULT_SERAL_STAGE_CONFIG_PATH: Path | None = None
DEFAULT_SILVICULTURE_CONFIG_PATH: Path | None = None
DEFAULT_RETENTION_VALUE = 0.0
DEFAULT_SILV_STATE_NATURAL = "baseline"
DEFAULT_SILV_STATE_PLANTED = "cc_pl"
VALID_IFM_VALUES = {"managed", "unmanaged"}
VALID_ORIGIN_VALUES = {"natural", "planted"}
VALID_SILV_STATE_VALUES = {
    "baseline",
    "cc_pl",
    "cc_pl_pct",
    "cc_pl_pct_ct",
    "cc_pl_ct",
    "cc_pl_ct_f1",
    "cc_pl_ct_f1_f2",
    "cc_pl_ct_f1_f2_f3",
}
ORIGIN_ORDER = ("natural", "planted")
ORIGIN_PLANTED_MAX_AGE = 60
FRAGMENT_ID_COLUMN = "FRAGMENT_ID"
FRAGMENT_ID_SHAPEFILE_COLUMN = "FRAGMENT_I"
REQUIRED_FRAGMENT_COLUMNS = {
    FRAGMENT_ID_COLUMN,
    "BLOCK",
    "AREA_HA",
    "F_AGE",
    "AU",
    "IFM",
    "ORIGIN",
    "SILV_STATE",
    "RETENTION",
    "TSA",
    "geometry",
}
IFM_SIGNAL_PRIORITY = ("thlb", "thlb_fact", "thlb_area", "thlb_raw")
SERAL_STAGE_ORDER = (
    "regenerating",
    "young",
    "immature",
    "mature",
    "overmature",
)
OG2_MIN_AGE_ZERO = 249
OG2_MIN_AGE_ONE = 250


@dataclass(frozen=True)
class PatchworksExportResult:
    """Paths and counts from a Patchworks package export."""

    forestmodel_xml_path: Path
    fragments_shapefile_path: Path
    tsa_list: list[str]
    au_count: int
    fragment_count: int
    curve_count: int


def _add_attribute_with_curve_ref(
    parent: et.Element,
    *,
    label: str,
    curve_ref: str,
) -> None:
    attr = et.SubElement(parent, "attribute", {"label": label})
    et.SubElement(attr, "curve", {"idref": curve_ref})


def _coerce_geometry(value: Any) -> Any:
    """Normalize geometry payloads loaded from checkpoint feather files."""
    if value is None:
        return None
    if hasattr(value, "geom_type") and hasattr(value, "is_valid"):
        return value
    if isinstance(value, memoryview):
        value = value.tobytes()
    if isinstance(value, (bytes, bytearray)):
        shapely_wkb = importlib.import_module("shapely.wkb")
        return shapely_wkb.loads(bytes(value))
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            shapely_wkb = importlib.import_module("shapely.wkb")
            return shapely_wkb.loads(text, hex=True)
        except Exception:
            return value
    return value


def _as_quoted_literal(value: str) -> str:
    text = str(value).strip()
    if text.startswith("'") and text.endswith("'"):
        return text
    return f"'{text}'"


def _au_eq_statement(au_id: int | str) -> str:
    return f"AU eq {int(au_id)}"


def _sanitize_id_component(value: str) -> str:
    text = str(value).strip()
    if not text:
        return "na"
    out = "".join(ch if ch.isalnum() or ch in {"_", "."} else "_" for ch in text)
    out = out.strip("_")
    return out or "na"


def _au_base_display_label(*, stratum_code: str, si_level: str) -> str:
    """Build human-readable AU label from stratum code + SI class."""
    stratum = str(stratum_code).strip().replace("_", "-")
    if not stratum:
        stratum = "unknown-au"
    si = str(si_level).strip().upper()
    if si:
        return f"{stratum}-{si}"
    return stratum


def _build_au_label_maps(
    *, context: BundleModelContext
) -> tuple[dict[int, str], dict[int, str]]:
    """Return readable AU labels and sanitized AU-id tokens keyed by au_id."""
    base_counts: dict[str, int] = {}
    base_by_au_id: dict[int, str] = {}
    for au in context.analysis_units:
        base = _au_base_display_label(
            stratum_code=au.stratum_code,
            si_level=au.si_level,
        )
        base_by_au_id[int(au.au_id)] = base
        base_counts[base] = int(base_counts.get(base, 0)) + 1

    labels: dict[int, str] = {}
    tokens: dict[int, str] = {}
    for au in context.analysis_units:
        base = base_by_au_id[int(au.au_id)]
        label = base
        if base_counts.get(base, 0) > 1:
            label = f"{normalize_tsa_code(au.tsa)}-{base}"
        labels[int(au.au_id)] = label
        tokens[int(au.au_id)] = _sanitize_id_component(label)
    return labels, tokens


def _source_curve_ref(
    *, curve_id: int, curve_type: str, au_token: str | None = None
) -> str:
    """Build readable, deterministic XML curve id from source metadata."""
    ctype = str(curve_type or "").strip()
    if ctype in {"managed", "treated"}:
        prefix = "managed_total"
    elif ctype in {"unmanaged", "untreated"}:
        prefix = "unmanaged_total"
    elif ctype.startswith(("managed_species_prop_", "treated_species_prop_")):
        if ctype.startswith("managed_species_prop_"):
            species = _sanitize_id_component(
                ctype.removeprefix("managed_species_prop_")
            )
        else:
            species = _sanitize_id_component(
                ctype.removeprefix("treated_species_prop_")
            )
        prefix = f"managed_prop_{species}"
    elif ctype.startswith(("unmanaged_species_prop_", "untreated_species_prop_")):
        if ctype.startswith("unmanaged_species_prop_"):
            species = _sanitize_id_component(
                ctype.removeprefix("unmanaged_species_prop_")
            )
        else:
            species = _sanitize_id_component(
                ctype.removeprefix("untreated_species_prop_")
            )
        prefix = f"unmanaged_prop_{species}"
    else:
        prefix = _sanitize_id_component(ctype or "curve")
    if au_token:
        return f"{prefix}_{au_token}_{int(curve_id)}"
    return f"{prefix}_{int(curve_id)}"


def _curve_value_at_x(*, points: tuple[CurvePoint, ...], x: float) -> float:
    """Evaluate a curve at `x` using constant or piecewise-linear interpolation."""
    finite_points = [
        (float(p.x), float(p.y))
        for p in points
        if math.isfinite(float(p.x)) and math.isfinite(float(p.y))
    ]
    if not finite_points:
        return 0.0
    if len(finite_points) == 1:
        return finite_points[0][1]
    x_points = np.array([xy[0] for xy in finite_points], dtype=float)
    y_points = np.array([xy[1] for xy in finite_points], dtype=float)
    order = np.argsort(x_points)
    x_sorted = x_points[order]
    y_sorted = y_points[order]
    return float(
        np.interp(float(x), x_sorted, y_sorted, left=y_sorted[0], right=y_sorted[-1])
    )


def _build_species_yield_curves(
    *,
    total_points: tuple[CurvePoint, ...],
    species_prop_points_by_species: dict[str, tuple[CurvePoint, ...]],
) -> dict[str, tuple[CurvePoint, ...]]:
    """Derive species-yield curves from total yield and species proportion curves.

    Preserve authored species-proportion magnitudes as-is. When the available
    species proportions already sum to ~1.0 at a knot age, adjust the largest
    positive species by the rounding residual so the species-wise yields add back
    to the rounded total exactly.
    """
    if not total_points or not species_prop_points_by_species:
        return {}
    species_list = sorted(species_prop_points_by_species)
    derived: dict[str, list[CurvePoint]] = {species: [] for species in species_list}
    for point in total_points:
        total_y = max(0.0, float(point.y))
        rounded_total_y = round(total_y, 1)
        raw_props: dict[str, float] = {}
        for species, species_prop_points in species_prop_points_by_species.items():
            species_prop = _curve_value_at_x(
                points=species_prop_points,
                x=float(point.x),
            )
            if not math.isfinite(species_prop):
                species_prop = 0.0
            raw_props[species] = max(0.0, min(1.0, species_prop))
        prop_total = sum(raw_props.values())
        raw_yields = {species: total_y * raw_props[species] for species in species_list}
        rounded_yields = {
            species: round(raw_yields[species], 1) for species in species_list
        }
        if math.isclose(prop_total, 1.0, rel_tol=0.0, abs_tol=1e-6):
            positive_species = [
                species for species in species_list if raw_yields[species] > 1e-12
            ]
            residual_species = (
                max(positive_species, key=lambda species: raw_yields[species])
                if positive_species
                else species_list[-1]
            )
            residual_value = rounded_total_y - sum(
                rounded_yields[species]
                for species in species_list
                if species != residual_species
            )
            if residual_value < 0.0:
                residual_value = 0.0
            rounded_yields[residual_species] = residual_value

        x_val = float(point.x)
        for species in species_list:
            derived[species].append(CurvePoint(x=x_val, y=rounded_yields[species]))
    return {species: tuple(points) for species, points in derived.items()}


def _build_species_prop_points_without_species(
    *,
    species_prop_points_by_species: dict[str, tuple[CurvePoint, ...]],
    excluded_species: tuple[str, ...],
) -> dict[str, tuple[CurvePoint, ...]]:
    """Return a post-treatment species-proportion surface with selected species removed."""
    if not species_prop_points_by_species:
        return {}

    excluded = {species.upper() for species in excluded_species}
    x_values = sorted(
        {
            float(point.x)
            for curve_points in species_prop_points_by_species.values()
            for point in curve_points
            if math.isfinite(float(point.x)) and float(point.x) >= 0.0
        }
    )
    if not x_values:
        return dict(species_prop_points_by_species)

    retained_species = sorted(
        species
        for species in species_prop_points_by_species
        if species.upper() not in excluded
    )
    if not retained_species:
        return dict(species_prop_points_by_species)

    out: dict[str, list[CurvePoint]] = {
        species: [] for species in species_prop_points_by_species
    }
    for x_val in x_values:
        retained_raw = {
            species: max(
                0.0,
                _curve_value_at_x(
                    points=species_prop_points_by_species[species],
                    x=float(x_val),
                ),
            )
            for species in retained_species
        }
        retained_total = sum(retained_raw.values())
        if retained_total <= 0.0:
            return dict(species_prop_points_by_species)
        for species in species_prop_points_by_species:
            if species.upper() in excluded:
                y_val = 0.0
            else:
                y_val = retained_raw[species] / retained_total
            out[species].append(CurvePoint(x=float(x_val), y=round(y_val, 5)))
    return {species: tuple(points) for species, points in out.items()}


def _build_species_prop_points_with_stem_removals(
    *,
    species_prop_points_by_species: dict[str, tuple[CurvePoint, ...]],
    remove_stems_per_ha_by_species: tuple[tuple[str, float], ...],
    source_total_stems_per_ha: float,
) -> dict[str, tuple[CurvePoint, ...]]:
    """Return a post-treatment species-proportion surface after fixed stem removals."""
    if not species_prop_points_by_species or not remove_stems_per_ha_by_species:
        return dict(species_prop_points_by_species)
    if source_total_stems_per_ha <= 0.0:
        return dict(species_prop_points_by_species)

    removal_map = {
        str(species).strip().upper(): max(0.0, float(stems))
        for species, stems in remove_stems_per_ha_by_species
        if str(species).strip()
    }
    if not removal_map:
        return dict(species_prop_points_by_species)

    x_values = sorted(
        {
            float(point.x)
            for curve_points in species_prop_points_by_species.values()
            for point in curve_points
            if math.isfinite(float(point.x)) and float(point.x) >= 0.0
        }
    )
    if not x_values:
        return dict(species_prop_points_by_species)

    out: dict[str, list[CurvePoint]] = {
        species: [] for species in species_prop_points_by_species
    }
    for x_val in x_values:
        residual_stems: dict[str, float] = {}
        for species, curve_points in species_prop_points_by_species.items():
            raw_prop = max(0.0, _curve_value_at_x(points=curve_points, x=float(x_val)))
            raw_stems = raw_prop * float(source_total_stems_per_ha)
            residual_stems[species] = max(
                0.0, raw_stems - removal_map.get(species.upper(), 0.0)
            )
        residual_total = sum(residual_stems.values())
        if residual_total <= 0.0:
            return dict(species_prop_points_by_species)
        for species in species_prop_points_by_species:
            y_val = residual_stems[species] / residual_total
            out[species].append(CurvePoint(x=float(x_val), y=round(y_val, 5)))
    return {species: tuple(points) for species, points in out.items()}


def _curve_has_positive_signal(
    points: tuple[CurvePoint, ...], *, abs_tol: float = 1e-12
) -> bool:
    """Return True when curve points contain a positive y value."""
    for point in points:
        y_val = float(point.y)
        if math.isfinite(y_val) and y_val > abs_tol:
            return True
    return False


def _species_curve_points_by_species(
    *,
    context: BundleModelContext,
    species_curve_map: dict[str, int],
) -> dict[str, tuple[CurvePoint, ...]]:
    """Return positive-signal species-proportion curves keyed by species."""
    out: dict[str, tuple[CurvePoint, ...]] = {}
    for species, species_curve_id in sorted(species_curve_map.items()):
        curve_def = context.curves_by_id.get(species_curve_id)
        if curve_def is None:
            continue
        if not _curve_has_positive_signal(curve_def.points):
            continue
        out[species] = curve_def.points
    return out


def _derived_species_yield_curve_ref(
    *, au_token: str, managed: bool, origin: str, species: str
) -> str:
    """Build readable deterministic XML id for derived species-yield curves."""
    mode = "managed" if managed else "unmanaged"
    origin_token = _sanitize_id_component(origin)
    species_token = _sanitize_id_component(species)
    return f"au_{au_token}_{mode}_{origin_token}_yield_{species_token}"


def _seral_curve_ref(*, au_token: str, stage: str) -> str:
    return f"au_{au_token}_seral_{_sanitize_id_component(stage)}"


def _old_growth_curve_ref(*, au_token: str, og_label: str) -> str:
    return f"au_{au_token}_{_sanitize_id_component(og_label)}"


def _build_old_growth_1_curve_points(
    *,
    unmanaged_total_curve_points: tuple[CurvePoint, ...],
    horizon_years: int,
) -> tuple[CurvePoint, ...]:
    if not unmanaged_total_curve_points:
        return (
            CurvePoint(x=0.0, y=0.0),
            CurvePoint(x=1.0, y=1.0),
        )
    cmai_age, peak_yield_age = _derive_curve_metrics(
        managed_total_curve_points=unmanaged_total_curve_points,
        horizon_years=horizon_years,
    )
    ramp_start = max(0, int(cmai_age))
    ramp_end = max(ramp_start + 1, int(peak_yield_age))
    return (
        CurvePoint(x=float(ramp_start), y=0.0),
        CurvePoint(x=float(ramp_end), y=1.0),
    )


def _build_old_growth_2_curve_points() -> tuple[CurvePoint, ...]:
    return (
        CurvePoint(x=float(OG2_MIN_AGE_ZERO), y=0.0),
        CurvePoint(x=float(OG2_MIN_AGE_ONE), y=1.0),
    )


def _load_seral_stage_config(
    *,
    seral_stage_config_path: Path | None,
) -> dict[str, Any] | None:
    if seral_stage_config_path is None:
        return None
    resolved = seral_stage_config_path.expanduser().resolve()
    if not resolved.exists():
        raise FileNotFoundError(f"Seral stage config not found: {resolved}")
    payload = yaml.safe_load(resolved.read_text(encoding="utf-8"))
    if payload is None:
        return {}
    if not isinstance(payload, dict):
        raise ValueError(
            "Seral stage config must contain a top-level mapping/object "
            f"(found {type(payload).__name__})"
        )
    return payload


def _load_silviculture_config(
    *,
    silviculture_config_path: Path | None,
) -> dict[str, Any] | None:
    if silviculture_config_path is None:
        return None
    resolved = silviculture_config_path.expanduser().resolve()
    if not resolved.exists():
        raise FileNotFoundError(f"silviculture config not found: {resolved}")
    payload = yaml.safe_load(resolved.read_text(encoding="utf-8"))
    if payload is None:
        return {}
    if not isinstance(payload, dict):
        raise ValueError(
            "silviculture config must contain a top-level mapping/object "
            f"(found {type(payload).__name__})"
        )
    ct = payload.get("commercial_thinning")
    if ct is not None and not isinstance(ct, dict):
        raise ValueError("commercial_thinning config must contain a mapping/object")
    fert = payload.get("fertilization")
    if fert is not None and not isinstance(fert, dict):
        raise ValueError("fertilization config must contain a mapping/object")
    pct = payload.get("pre_commercial_thinning")
    if pct is not None and not isinstance(pct, dict):
        raise ValueError("pre_commercial_thinning config must contain a mapping/object")
    retention = payload.get("retention")
    if retention is not None and not isinstance(retention, dict):
        raise ValueError("retention config must contain a mapping/object")
    return payload


def _evaluate_curve_on_integer_ages(
    *,
    points: tuple[CurvePoint, ...],
    max_age: int,
) -> list[tuple[int, float]]:
    if max_age < 1:
        return [(1, 0.0)]
    values: list[tuple[int, float]] = []
    for age in range(1, int(max_age) + 1):
        y = max(0.0, float(_curve_value_at_x(points=points, x=float(age))))
        values.append((age, y))
    return values


def _derive_default_seral_bounds(
    *,
    managed_total_curve_points: tuple[CurvePoint, ...],
    horizon_years: int,
) -> dict[str, tuple[int, int | None]]:
    cmai_age, peak_yield_age = _derive_curve_metrics(
        managed_total_curve_points=managed_total_curve_points,
        horizon_years=horizon_years,
    )
    # Keep stage ordering sane even if CMAI happens unusually early.
    cmai_for_bounds = max(cmai_age, 25)
    mature_upper = min(peak_yield_age, 200)
    mature_min = cmai_for_bounds + 1
    mature_upper = max(mature_upper, mature_min)

    return {
        "regenerating": (0, 5),
        "young": (6, 25),
        "immature": (26, cmai_for_bounds),
        "mature": (mature_min, mature_upper),
        "overmature": (mature_upper + 1, None),
    }


def _derive_curve_metrics(
    *,
    managed_total_curve_points: tuple[CurvePoint, ...],
    horizon_years: int,
) -> tuple[int, int]:
    finite_x = [
        float(point.x)
        for point in managed_total_curve_points
        if math.isfinite(float(point.x))
    ]
    max_curve_age = int(max(finite_x, default=float(horizon_years)))
    max_eval_age = max(200, int(horizon_years), max_curve_age, 1)
    evaluated = _evaluate_curve_on_integer_ages(
        points=managed_total_curve_points,
        max_age=max_eval_age,
    )
    peak_yield_age = max(evaluated, key=lambda item: item[1])[0]
    cmai_age = max(
        evaluated,
        key=lambda item: (item[1] / float(item[0])) if item[0] > 0 else -1.0,
    )[0]
    return int(cmai_age), int(peak_yield_age)


def _default_silv_state_for_origin(origin: str) -> str:
    return (
        DEFAULT_SILV_STATE_PLANTED
        if str(origin).strip().lower() == "planted"
        else DEFAULT_SILV_STATE_NATURAL
    )


def _resolve_retention_overrides_by_au(
    *,
    au_table: pd.DataFrame,
    silviculture_config: dict[str, Any] | None,
) -> dict[int, float]:
    if not silviculture_config:
        return {}
    retention_payload = silviculture_config.get("retention")
    if not isinstance(retention_payload, dict):
        return {}

    overrides: dict[int, float] = {}
    configured_au_ids = retention_payload.get("full_retention_au_ids")
    if isinstance(configured_au_ids, list):
        for raw_value in configured_au_ids:
            try:
                overrides[int(raw_value)] = 1.0
            except (TypeError, ValueError):
                continue

    configured_strata = retention_payload.get("full_retention_stratum_codes")
    if isinstance(configured_strata, list) and "stratum_code" in au_table.columns:
        wanted = {
            str(value).strip() for value in configured_strata if str(value).strip()
        }
        if wanted:
            matched = au_table.loc[
                au_table["stratum_code"].astype(str).isin(wanted), "au_id"
            ]
            for au_id in pd.to_numeric(matched, errors="coerce").dropna().astype(int):
                overrides[int(au_id)] = 1.0
    return overrides


def _resolve_pct_age_for_au(
    *, payload: dict[str, Any], au_id: int, default: int
) -> int:
    age_by_au = payload.get("age_by_au") or {}
    age_value = age_by_au.get(str(int(au_id)), age_by_au.get(int(au_id), default))
    try:
        return max(0, int(float(age_value)))
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"Invalid treatment age for AU {au_id}: {age_value!r}"
        ) from exc


def _resolve_eligible_au_ids(payload: dict[str, Any]) -> set[int]:
    eligible_raw = payload.get("eligible_au_ids") or []
    eligible_au_ids: set[int] = set()
    for raw_value in eligible_raw:
        try:
            eligible_au_ids.add(int(raw_value))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid eligible AU identifier: {raw_value!r}") from exc
    return eligible_au_ids


def _resolve_float_override_for_au(
    *,
    payload: dict[str, Any],
    field: str,
    au_id: int,
    default: float,
) -> float:
    by_au = payload.get(f"{field}_by_au") or {}
    if by_au:
        if not isinstance(by_au, dict):
            raise ValueError(f"{field}_by_au must contain a mapping/object")
        raw_value = by_au.get(str(int(au_id)), by_au.get(int(au_id)))
        if raw_value is not None:
            try:
                return float(raw_value)
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"Invalid {field} override for AU {au_id}: {raw_value!r}"
                ) from exc
    return float(default)


def _resolve_remove_species(payload: dict[str, Any]) -> tuple[str, ...]:
    return tuple(
        str(value).strip().upper()
        for value in (payload.get("remove_species") or ["HW"])
        if str(value).strip()
    )


def _resolve_remove_stems_per_ha_by_species(
    *,
    payload: dict[str, Any],
    default_species: tuple[str, ...],
) -> tuple[tuple[str, float], ...]:
    remove_payload = payload.get("remove_stems_per_ha")
    if remove_payload is None:
        return ()
    if isinstance(remove_payload, (int, float)):
        if not default_species:
            raise ValueError(
                "Scalar remove_stems_per_ha requires remove_species to identify the species"
            )
        return ((default_species[0], max(0.0, float(remove_payload))),)
    if not isinstance(remove_payload, dict):
        raise ValueError("remove_stems_per_ha must be a number or mapping/object")

    out: list[tuple[str, float]] = []
    for species, raw_value in remove_payload.items():
        species_key = str(species).strip().upper()
        if not species_key:
            continue
        try:
            stems = max(0.0, float(raw_value))
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"Invalid remove_stems_per_ha value for species {species_key!r}: {raw_value!r}"
            ) from exc
        out.append((species_key, stems))
    return tuple(sorted(out))


def _resolve_pct_configs_for_au(
    *,
    silviculture_config: dict[str, Any] | None,
    au_id: int,
) -> tuple[dict[str, Any], ...]:
    if not silviculture_config:
        return ()
    pct_payload = silviculture_config.get("pre_commercial_thinning")
    if not isinstance(pct_payload, dict) or not bool(pct_payload.get("enabled", False)):
        return ()

    payloads: list[dict[str, Any]]
    configured_treatments = pct_payload.get("treatments")
    if isinstance(configured_treatments, list) and configured_treatments:
        payloads = []
        for raw_item in configured_treatments:
            if not isinstance(raw_item, dict):
                raise ValueError(
                    "pre_commercial_thinning.treatments entries must be mappings/objects"
                )
            payloads.append({**pct_payload, **raw_item})
    else:
        payloads = [pct_payload]

    configs: list[dict[str, Any]] = []
    for index, payload in enumerate(payloads, start=1):
        eligible_au_ids = _resolve_eligible_au_ids(payload)
        if eligible_au_ids and int(au_id) not in eligible_au_ids:
            continue
        remove_species = _resolve_remove_species(payload)
        remove_stems_per_ha_by_species = _resolve_remove_stems_per_ha_by_species(
            payload=payload,
            default_species=remove_species,
        )
        try:
            source_total_stems_per_ha = float(
                payload.get("source_total_stems_per_ha", 0.0)
            )
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"Invalid PCT source_total_stems_per_ha for AU {au_id}"
            ) from exc
        label = str(payload.get("label", "PCT")).strip().upper()
        if not label:
            label = f"PCT_{index}"
        configs.append(
            {
                "label": label,
                "product_label": f"product.Treated.managed.{label}",
                "from_state": str(payload.get("from_state", "cc_pl")).strip().lower(),
                "to_state": str(payload.get("to_state", "cc_pl_pct")).strip().lower(),
                "ct_to_state": str(
                    payload.get(
                        "ct_to_state",
                        f"{str(payload.get('to_state', 'cc_pl_pct')).strip().lower()}_ct",
                    )
                )
                .strip()
                .lower(),
                "min_origin": str(payload.get("min_origin", "planted")).strip().lower(),
                "pct_age": _resolve_pct_age_for_au(
                    payload=payload, au_id=au_id, default=10
                ),
                "remove_species": remove_species,
                "remove_stems_per_ha_by_species": remove_stems_per_ha_by_species,
                "source_total_stems_per_ha": max(0.0, source_total_stems_per_ha),
            }
        )
    return tuple(configs)


def _resolve_ct_configs_for_au(
    *,
    silviculture_config: dict[str, Any] | None,
    au_id: int,
    pct_configs: tuple[dict[str, Any], ...] = (),
) -> tuple[dict[str, Any], ...]:
    if not silviculture_config:
        return ()
    ct_payload = silviculture_config.get("commercial_thinning")
    if not isinstance(ct_payload, dict) or not bool(ct_payload.get("enabled", False)):
        return ()

    eligible_au_ids = _resolve_eligible_au_ids(ct_payload)
    if eligible_au_ids and int(au_id) not in eligible_au_ids:
        return ()
    ct_age = _resolve_pct_age_for_au(payload=ct_payload, au_id=au_id, default=40)
    try:
        basal_area_fraction = float(ct_payload.get("basal_area_removal_fraction", 0.30))
        ba_to_volume_ratio = float(ct_payload.get("basal_area_to_volume_ratio", 1.0))
        qmd_response_fraction = float(ct_payload.get("qmd_response_fraction", 0.10))
        final_felling_gap_factor = _resolve_float_override_for_au(
            payload=ct_payload,
            field="final_felling_gap_factor",
            au_id=au_id,
            default=float(ct_payload.get("final_felling_gap_factor", 1.0)),
        )
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid CT removal parameters for AU {au_id}") from exc
    if final_felling_gap_factor < 0.0:
        raise ValueError(f"final_felling_gap_factor must be >= 0.0 for AU {au_id}")
    removal_fraction = max(0.0, min(1.0, basal_area_fraction * ba_to_volume_ratio))

    transition_payloads = ct_payload.get("transitions")
    if isinstance(transition_payloads, list) and transition_payloads:
        payloads = []
        for raw_item in transition_payloads:
            if not isinstance(raw_item, dict):
                raise ValueError(
                    "commercial_thinning.transitions entries must be mappings/objects"
                )
            payloads.append({**ct_payload, **raw_item})
    elif pct_configs:
        payloads = [
            {
                **ct_payload,
                "from_state": pct_config["to_state"],
                "to_state": pct_config["ct_to_state"],
            }
            for pct_config in pct_configs
        ]
    else:
        payloads = [ct_payload]

    configs: list[dict[str, Any]] = []
    for payload in payloads:
        configs.append(
            {
                "label": str(payload.get("label", "CT")).strip().upper() or "CT",
                "from_state": str(payload.get("from_state", "cc_pl")).strip().lower(),
                "to_state": str(payload.get("to_state", "cc_pl_ct")).strip().lower(),
                "min_origin": str(payload.get("min_origin", "planted")).strip().lower(),
                "ct_age": ct_age,
                "basal_area_fraction": basal_area_fraction,
                "ba_to_volume_ratio": ba_to_volume_ratio,
                "removal_fraction": removal_fraction,
                "qmd_response_fraction": max(0.0, qmd_response_fraction),
                "final_felling_gap_factor": final_felling_gap_factor,
            }
        )
    return tuple(configs)


SI_LEVEL_QMD_OFFSET_CM = {"L": -2.0, "M": 0.0, "H": 2.0}


def _build_qmd_curve_points(
    *,
    source_curve_points: tuple[CurvePoint, ...],
    si_level: str,
    response_age: int | None = None,
    response_fraction: float = 0.0,
    response_years: int = 10,
) -> tuple[CurvePoint, ...]:
    x_values = sorted(
        {
            float(point.x)
            for point in source_curve_points
            if math.isfinite(float(point.x)) and float(point.x) >= 0.0
        }
    )
    if not x_values:
        x_values = [0.0, 100.0]
    si_offset = SI_LEVEL_QMD_OFFSET_CM.get(str(si_level).strip().upper(), 0.0)
    out: list[CurvePoint] = []
    for x_val in x_values:
        age = max(0.0, float(x_val))
        qmd = 6.0 + 1.2 * math.sqrt(age) + 0.12 * age + si_offset
        if (
            response_age is not None
            and age >= float(response_age)
            and response_fraction > 0.0
        ):
            if response_years <= 0:
                ramp = 1.0
            else:
                ramp = min(
                    1.0, max(0.0, (age - float(response_age)) / float(response_years))
                )
            qmd *= 1.0 + (response_fraction * ramp)
        out.append(CurvePoint(x=age, y=round(max(0.0, qmd), 1)))
    return tuple(out)


def _build_constant_curve_points_like(
    *,
    source_curve_points: tuple[CurvePoint, ...],
    value: float,
) -> tuple[CurvePoint, ...]:
    x_values = sorted(
        {
            float(point.x)
            for point in source_curve_points
            if math.isfinite(float(point.x)) and float(point.x) >= 0.0
        }
    )
    if not x_values:
        x_values = [0.0, 100.0]
    y_val = round(max(0.0, float(value)), 1)
    return tuple(CurvePoint(x=x_val, y=y_val) for x_val in x_values)


def _build_curve_with_post_thinning_gap(
    *,
    source_curve_points: tuple[CurvePoint, ...],
    transition_age: int,
    gap_at_transition_value: float,
    final_gap_factor: float,
    ramp_end_age: int,
) -> tuple[CurvePoint, ...]:
    out: list[CurvePoint] = []
    gap_at_transition_value = max(0.0, float(gap_at_transition_value))
    final_gap_factor = max(0.0, float(final_gap_factor))
    transition_age = int(transition_age)
    ramp_end_age = int(ramp_end_age)
    for point in source_curve_points:
        x_val = float(point.x)
        y_val = float(point.y)
        gap_factor = 0.0
        if x_val >= float(transition_age):
            gap_factor = 1.0
            if ramp_end_age <= transition_age:
                if x_val > float(transition_age):
                    gap_factor = final_gap_factor
            elif x_val >= float(ramp_end_age):
                gap_factor = final_gap_factor
            else:
                ramp = (x_val - float(transition_age)) / float(
                    ramp_end_age - transition_age
                )
                gap_factor = 1.0 + ((final_gap_factor - 1.0) * ramp)
            y_val -= gap_at_transition_value * gap_factor
        out.append(CurvePoint(x=x_val, y=max(0.0, round(y_val, 1))))
    return tuple(out)


def _build_curve_with_temporary_speedup(
    *,
    source_curve_points: tuple[CurvePoint, ...],
    response_age: int,
    speedup_fraction: float,
    response_years: int,
) -> tuple[CurvePoint, ...]:
    out: list[CurvePoint] = []
    max_shift = max(0.0, float(speedup_fraction)) * max(0, int(response_years))
    for point in source_curve_points:
        x_val = float(point.x)
        sample_x = x_val
        if x_val >= float(response_age) and max_shift > 0.0:
            elapsed = max(0.0, x_val - float(response_age))
            if response_years > 0:
                shift = min(max_shift, elapsed * max(0.0, float(speedup_fraction)))
            else:
                shift = max_shift
            sample_x = x_val + shift
        y_val = _curve_value_at_x(points=source_curve_points, x=sample_x)
        out.append(CurvePoint(x=x_val, y=max(0.0, round(y_val, 1))))
    return tuple(out)


def _derive_peak_cai_age(
    *,
    source_curve_points: tuple[CurvePoint, ...],
    horizon_years: int,
) -> int:
    evaluated = _evaluate_curve_on_integer_ages(
        points=source_curve_points,
        max_age=max(2, int(horizon_years)),
    )
    if len(evaluated) < 2:
        return int(evaluated[0][0]) if evaluated else 1
    best_age = int(evaluated[1][0])
    best_cai = float(evaluated[1][1] - evaluated[0][1])
    for idx in range(1, len(evaluated)):
        age = int(evaluated[idx][0])
        cai = float(evaluated[idx][1] - evaluated[idx - 1][1])
        if cai > best_cai:
            best_cai = cai
            best_age = age
    return max(1, int(best_age))


def _resolve_fertilization_config_for_au(
    *,
    silviculture_config: dict[str, Any] | None,
    au_id: int,
    planted_total_curve_points: tuple[CurvePoint, ...],
    ct_age: int,
    horizon_years: int,
) -> dict[str, Any] | None:
    if not silviculture_config:
        return None
    fert_payload = silviculture_config.get("fertilization")
    if not isinstance(fert_payload, dict) or not bool(
        fert_payload.get("enabled", False)
    ):
        return None
    eligible_au_ids = _resolve_eligible_au_ids(fert_payload)
    if eligible_au_ids and int(au_id) not in eligible_au_ids:
        return None
    first_application = fert_payload.get("first_application") or {}
    if not isinstance(first_application, dict):
        raise ValueError(
            "fertilization.first_application config must contain a mapping/object"
        )
    timing_rule = (
        str(first_application.get("timing_rule", "cai_argmax")).strip().lower()
    )
    age_by_au = first_application.get("age_by_au") or {}
    age_value = age_by_au.get(str(int(au_id)), age_by_au.get(int(au_id)))
    if age_value is not None:
        try:
            fert_age = int(float(age_value))
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"Invalid fertilization age for AU {au_id}: {age_value!r}"
            ) from exc
    elif timing_rule == "cai_argmax":
        fert_age = _derive_peak_cai_age(
            source_curve_points=planted_total_curve_points,
            horizon_years=horizon_years,
        )
    else:
        try:
            fert_age = int(float(first_application.get("age", ct_age + 1)))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid fertilization timing for AU {au_id}") from exc
    fert_age = max(int(ct_age) + 1, int(fert_age))
    try:
        response_years = int(float(fert_payload.get("response_years", 10)))
        speedup_fraction = _resolve_float_override_for_au(
            payload=fert_payload,
            field="growth_speedup_fraction",
            au_id=au_id,
            default=float(fert_payload.get("growth_speedup_fraction", 0.10)),
        )
        qmd_response_fraction = _resolve_float_override_for_au(
            payload=fert_payload,
            field="qmd_response_fraction",
            au_id=au_id,
            default=float(fert_payload.get("qmd_response_fraction", speedup_fraction)),
        )
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"Invalid fertilization response parameters for AU {au_id}"
        ) from exc
    return {
        "label": str(first_application.get("label", "F1")).strip().upper() or "F1",
        "from_state": str(first_application.get("from_state", "cc_pl_ct"))
        .strip()
        .lower(),
        "to_state": str(first_application.get("to_state", "cc_pl_ct_f1"))
        .strip()
        .lower(),
        "fert_age": fert_age,
        "timing_rule": timing_rule,
        "response_years": max(0, response_years),
        "speedup_fraction": max(0.0, speedup_fraction),
        "qmd_response_fraction": max(0.0, qmd_response_fraction),
    }


def _resolve_fertilization_sequence_for_au(
    *,
    silviculture_config: dict[str, Any] | None,
    au_id: int,
    planted_total_curve_points: tuple[CurvePoint, ...],
    ct_age: int,
    horizon_years: int,
) -> tuple[dict[str, Any], ...]:
    first = _resolve_fertilization_config_for_au(
        silviculture_config=silviculture_config,
        au_id=au_id,
        planted_total_curve_points=planted_total_curve_points,
        ct_age=ct_age,
        horizon_years=horizon_years,
    )
    if first is None:
        return ()
    if not silviculture_config:
        return (first,)
    fert_payload = silviculture_config.get("fertilization")
    if not isinstance(fert_payload, dict):
        return (first,)
    sequence: list[dict[str, Any]] = [first]
    previous = first
    for key, default_label, default_to_state in (
        ("second_application", "F2", "cc_pl_ct_f1_f2"),
        ("third_application", "F3", "cc_pl_ct_f1_f2_f3"),
    ):
        payload = fert_payload.get(key)
        if payload is None:
            continue
        if not isinstance(payload, dict):
            raise ValueError(
                f"fertilization.{key} config must contain a mapping/object"
            )
        if not bool(payload.get("enabled", False)):
            continue
        age_by_au = payload.get("age_by_au") or {}
        age_value = age_by_au.get(str(int(au_id)), age_by_au.get(int(au_id)))
        if age_value is not None:
            try:
                fert_age = int(float(age_value))
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"Invalid fertilization age for AU {au_id}: {age_value!r}"
                ) from exc
        else:
            try:
                years_after_previous = int(
                    float(payload.get("years_after_previous", 10))
                )
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"Invalid fertilization spacing for AU {au_id}"
                ) from exc
            fert_age = int(previous["fert_age"]) + max(1, years_after_previous)
        fert_age = max(int(previous["fert_age"]) + 1, int(fert_age))
        config = {
            "label": str(payload.get("label", default_label)).strip().upper()
            or default_label,
            "from_state": str(payload.get("from_state", previous["to_state"]))
            .strip()
            .lower(),
            "to_state": str(payload.get("to_state", default_to_state)).strip().lower(),
            "fert_age": fert_age,
            "timing_rule": "years_after_previous",
            "response_years": int(previous["response_years"]),
            "speedup_fraction": float(previous["speedup_fraction"]),
            "qmd_response_fraction": float(previous["qmd_response_fraction"]),
        }
        sequence.append(config)
        previous = config
    return tuple(sequence)


def _resolve_seral_age_value(
    *,
    value: Any,
    token_values: dict[str, int | None],
    key_name: str,
) -> int | None:
    if value is None:
        return None
    if isinstance(value, str):
        token = value.strip().lower()
        if token in token_values:
            resolved = token_values[token]
            if resolved is None:
                return None
            return int(resolved)
    try:
        as_int = int(float(value))
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"Invalid seral stage boundary value for {key_name}: {value!r}"
        ) from exc
    return as_int


def _extract_stage_overrides(
    *,
    payload: dict[str, Any],
    au_id: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    defaults = payload.get("default")
    if not isinstance(defaults, dict):
        defaults = payload.get("defaults")
    if not isinstance(defaults, dict):
        defaults = payload.get("stages")
    if not isinstance(defaults, dict):
        defaults = {}

    au_overrides = payload.get("au_overrides")
    if not isinstance(au_overrides, dict):
        au_overrides = payload.get("aus")
    if not isinstance(au_overrides, dict):
        au_overrides = payload.get("au")
    if not isinstance(au_overrides, dict):
        au_overrides = {}

    by_au = au_overrides.get(str(int(au_id)))
    if by_au is None:
        by_au = au_overrides.get(int(au_id))
    if isinstance(by_au, dict) and isinstance(by_au.get("stages"), dict):
        by_au = by_au.get("stages")
    if not isinstance(by_au, dict):
        by_au = {}

    return defaults, by_au


def _resolve_seral_bounds_for_au(
    *,
    au_id: int,
    managed_total_curve_points: tuple[CurvePoint, ...],
    horizon_years: int,
    seral_stage_config: dict[str, Any],
) -> dict[str, tuple[int, int | None]]:
    resolved = _derive_default_seral_bounds(
        managed_total_curve_points=managed_total_curve_points,
        horizon_years=horizon_years,
    )
    default_overrides, au_overrides = _extract_stage_overrides(
        payload=seral_stage_config,
        au_id=au_id,
    )

    for stage in SERAL_STAGE_ORDER:
        stage_defaults = default_overrides.get(stage)
        stage_au = au_overrides.get(stage)
        min_age, max_age = resolved[stage]
        token_values: dict[str, int | None] = {
            "cmai": resolved["immature"][1],
            "cmai_plus_1": (resolved["immature"][1] or 0) + 1,
            "peak_yield_age": resolved["mature"][1],
            "min_peak_or_200": resolved["mature"][1],
            "mature_plus_1": ((resolved["mature"][1] or min_age) + 1),
        }
        if isinstance(stage_defaults, dict):
            if "min_age" in stage_defaults:
                resolved_min = _resolve_seral_age_value(
                    value=stage_defaults["min_age"],
                    token_values=token_values,
                    key_name=f"default.{stage}.min_age",
                )
                if resolved_min is not None:
                    min_age = resolved_min
            if "max_age" in stage_defaults:
                max_age = _resolve_seral_age_value(
                    value=stage_defaults["max_age"],
                    token_values=token_values,
                    key_name=f"default.{stage}.max_age",
                )
        token_values["mature_plus_1"] = (resolved["mature"][1] or min_age) + 1
        if isinstance(stage_au, dict):
            if "min_age" in stage_au:
                resolved_min = _resolve_seral_age_value(
                    value=stage_au["min_age"],
                    token_values=token_values,
                    key_name=f"au_overrides.{au_id}.{stage}.min_age",
                )
                if resolved_min is not None:
                    min_age = resolved_min
            if "max_age" in stage_au:
                max_age = _resolve_seral_age_value(
                    value=stage_au["max_age"],
                    token_values=token_values,
                    key_name=f"au_overrides.{au_id}.{stage}.max_age",
                )

        if max_age is not None and max_age < min_age:
            # Configuration/token combinations can produce a max below min
            # (for example immature max=cmai when cmai<26). Clamp to a
            # one-age stage instead of aborting export.
            max_age = int(min_age)
        resolved[stage] = (int(min_age), None if max_age is None else int(max_age))

    return resolved


def _build_seral_curve_points(
    *,
    min_age: int,
    max_age: int | None,
    horizon_years: int,
    managed_total_curve_points: tuple[CurvePoint, ...],
) -> tuple[CurvePoint, ...]:
    finite_x = [
        float(point.x)
        for point in managed_total_curve_points
        if math.isfinite(float(point.x))
    ]
    max_curve_age = int(max(finite_x, default=float(horizon_years)))
    max_age_eval = max(max_curve_age, int(horizon_years), 200)
    points: list[CurvePoint] = []
    for age in range(0, max_age_eval + 1):
        if age < int(min_age):
            y = 0.0
        elif max_age is None:
            y = 1.0
        elif age <= int(max_age):
            y = 1.0
        else:
            y = 0.0
        points.append(CurvePoint(x=float(age), y=y))
    return tuple(points)


def _trim_flat_tail_points(
    points: tuple[CurvePoint, ...], *, abs_tol: float = 1e-12
) -> tuple[CurvePoint, ...]:
    """Drop redundant far-left/far-right points where terminal y-values repeat."""
    if len(points) <= 1:
        return points
    left = 0
    first_y = float(points[0].y)
    while left + 1 < len(points) and math.isclose(
        float(points[left + 1].y), first_y, rel_tol=0.0, abs_tol=abs_tol
    ):
        left += 1
    right = len(points) - 1
    last_y = float(points[right].y)
    while right > left and math.isclose(
        float(points[right - 1].y), last_y, rel_tol=0.0, abs_tol=abs_tol
    ):
        right -= 1
    trimmed = points[left : right + 1]
    if len(trimmed) > 1:
        return trimmed
    # Edge case: entire curve is flat; keep earliest point so XML doesn't collapse to max age.
    return (points[0],)


def _sanitize_curve_points_for_xml(
    points: tuple[CurvePoint, ...], *, abs_tol: float = 1e-12
) -> tuple[CurvePoint, ...]:
    """Sanitize points for ForestModel XML (finite numeric values, monotonic x, no duplicate x)."""
    finite: list[CurvePoint] = []
    for point in points:
        x_val = float(point.x)
        y_val = float(point.y)
        if not math.isfinite(x_val):
            continue
        if not math.isfinite(y_val):
            y_val = 0.0
        finite.append(CurvePoint(x=x_val, y=y_val))
    if not finite:
        return ()
    finite = sorted(finite, key=lambda p: p.x)
    deduped: list[CurvePoint] = []
    for point in finite:
        if deduped and math.isclose(
            point.x, deduped[-1].x, rel_tol=0.0, abs_tol=abs_tol
        ):
            deduped[-1] = point
        else:
            deduped.append(point)
    return tuple(deduped)


def _format_xml_x(x_value: float, *, abs_tol: float = 1e-9) -> str:
    """Format x for XML using integer ages when effectively integral."""
    if math.isclose(x_value, round(x_value), rel_tol=0.0, abs_tol=abs_tol):
        return str(int(round(x_value)))
    return f"{x_value:.6f}".rstrip("0").rstrip(".")


def _is_volume_yield_curve_id(curve_id: str) -> bool:
    """Return True for absolute volume-yield curves (not normalized proportions)."""
    return curve_id.startswith(("managed_total_", "unmanaged_total_", "au_"))


def _format_xml_y(curve_id: str, y_value: float) -> str:
    """Format y with practical precision by curve family."""
    if curve_id == "unity":
        return str(y_value)
    if _is_volume_yield_curve_id(curve_id):
        # Volume yields are communicated at 0.1 precision.
        rounded = round(float(y_value), 1)
        if math.isclose(rounded, 0.0, rel_tol=0.0, abs_tol=1e-12):
            rounded = 0.0
        return f"{rounded:.1f}"
    # Normalized/proportion curves keep more precision, but cap display detail.
    rounded = round(float(y_value), 5)
    if math.isclose(rounded, 0.0, rel_tol=0.0, abs_tol=1e-12):
        rounded = 0.0
    text = f"{rounded:.5f}".rstrip("0").rstrip(".")
    return text or "0"


def _gpd_module() -> Any:
    return importlib.import_module("geopandas")


def _context_to_au_table(context: BundleModelContext) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "au_id": au.au_id,
                "tsa": au.tsa,
                "stratum_code": au.stratum_code,
                "si_level": au.si_level,
                "managed_curve_id": au.managed_curve_id,
                "unmanaged_curve_id": au.unmanaged_curve_id,
            }
            for au in context.analysis_units
        ]
    )


def build_forestmodel_xml_tree(
    *,
    au_table: pd.DataFrame,
    curve_table: pd.DataFrame,
    curve_points_table: pd.DataFrame,
    start_year: int = DEFAULT_START_YEAR,
    horizon_years: int = DEFAULT_HORIZON_YEARS,
    cc_min_age: int = DEFAULT_CC_MIN_AGE,
    cc_max_age: int = DEFAULT_CC_MAX_AGE,
    cc_transition_ifm: str | None = DEFAULT_CC_TRANSITION_IFM,
    seral_stage_config: dict[str, Any] | None = None,
    silviculture_config: dict[str, Any] | None = None,
) -> et.Element:
    """Build a Patchworks ForestModel XML tree from FEMIC bundle tables."""
    context = build_bundle_model_context_from_tables(
        au_table=au_table,
        curve_table=curve_table,
        curve_points_table=curve_points_table,
        tsa_list=None,
    )
    return build_forestmodel_xml_tree_from_context(
        context=context,
        start_year=start_year,
        horizon_years=horizon_years,
        cc_min_age=cc_min_age,
        cc_max_age=cc_max_age,
        cc_transition_ifm=cc_transition_ifm,
        seral_stage_config=seral_stage_config,
        silviculture_config=silviculture_config,
    )


def build_forestmodel_xml_tree_from_context(
    *,
    context: BundleModelContext,
    start_year: int = DEFAULT_START_YEAR,
    horizon_years: int = DEFAULT_HORIZON_YEARS,
    cc_min_age: int = DEFAULT_CC_MIN_AGE,
    cc_max_age: int = DEFAULT_CC_MAX_AGE,
    cc_transition_ifm: str | None = DEFAULT_CC_TRANSITION_IFM,
    seral_stage_config: dict[str, Any] | None = None,
    silviculture_config: dict[str, Any] | None = None,
) -> et.Element:
    """Build a Patchworks ForestModel XML tree from shared FMG context."""
    definition = build_patchworks_forestmodel_definition(
        context=context,
        start_year=start_year,
        horizon_years=horizon_years,
        cc_min_age=cc_min_age,
        cc_max_age=cc_max_age,
        cc_transition_ifm=cc_transition_ifm,
        seral_stage_config=seral_stage_config,
        silviculture_config=silviculture_config,
    )
    return forestmodel_definition_to_xml_tree(definition=definition)


def build_patchworks_forestmodel_definition(
    *,
    context: BundleModelContext,
    start_year: int = DEFAULT_START_YEAR,
    horizon_years: int = DEFAULT_HORIZON_YEARS,
    cc_min_age: int = DEFAULT_CC_MIN_AGE,
    cc_max_age: int = DEFAULT_CC_MAX_AGE,
    cc_transition_ifm: str | None = DEFAULT_CC_TRANSITION_IFM,
    seral_stage_config: dict[str, Any] | None = None,
    silviculture_config: dict[str, Any] | None = None,
) -> ForestModelDefinition:
    """Build Patchworks ForestModel core definition from shared context."""
    curves: dict[str, tuple[CurvePoint, ...]] = {"unity": (CurvePoint(x=0.0, y=1.0),)}
    au_label_by_id, au_token_by_id = _build_au_label_maps(context=context)
    curve_au_id_by_curve_id: dict[int, int] = {}
    for au in context.analysis_units:
        au_id = int(au.au_id)
        curve_au_id_by_curve_id[int(au.unmanaged_curve_id)] = au_id
        curve_au_id_by_curve_id[int(au.managed_curve_id)] = au_id
        for curve_id in context.unmanaged_species_curve_ids.get(
            int(au.unmanaged_curve_id), {}
        ).values():
            curve_au_id_by_curve_id[int(curve_id)] = au_id
        for curve_id in context.managed_species_curve_ids.get(
            int(au.managed_curve_id), {}
        ).values():
            curve_au_id_by_curve_id[int(curve_id)] = au_id
    source_curve_ref_by_id: dict[int, str] = {}
    for curve_id in sorted(context.curves_by_id):
        curve_def = context.curves_by_id[curve_id]
        source_curve_au_id: int | None = curve_au_id_by_curve_id.get(int(curve_id))
        curve_ref = _source_curve_ref(
            curve_id=curve_def.curve_id,
            curve_type=curve_def.curve_type,
            au_token=(
                au_token_by_id.get(source_curve_au_id)
                if source_curve_au_id is not None
                else None
            ),
        )
        source_curve_ref_by_id[curve_id] = curve_ref
        curves[curve_ref] = curve_def.points

    selects: list[SelectDefinition] = []
    transition_assignments_list: list[TreatmentAssignment] = [
        TreatmentAssignment(field="ORIGIN", value=_as_quoted_literal("planted")),
        TreatmentAssignment(field="SILV_STATE", value=_as_quoted_literal("cc_pl")),
    ]
    if cc_transition_ifm is not None and str(cc_transition_ifm).strip():
        transition_ifm = str(cc_transition_ifm).strip().lower()
        if transition_ifm not in VALID_IFM_VALUES:
            raise ValueError(
                "cc_transition_ifm must be one of "
                f"{sorted(VALID_IFM_VALUES)} (received {cc_transition_ifm!r})"
            )
        # IFM='managed' inside a managed-only select is redundant/noisy.
        if transition_ifm != "managed":
            transition_assignments_list.append(
                TreatmentAssignment(
                    field="IFM",
                    value=_as_quoted_literal(transition_ifm),
                )
            )
    transition_assignments = tuple(transition_assignments_list)
    for au in context.analysis_units:
        au_token = au_token_by_id[int(au.au_id)]
        unmanaged_curve_id = au.unmanaged_curve_id
        managed_curve_id = au.managed_curve_id
        unmanaged_curve_ref = source_curve_ref_by_id[unmanaged_curve_id]
        managed_curve_ref = source_curve_ref_by_id[managed_curve_id]
        unmanaged_total_curve = context.curves_by_id.get(unmanaged_curve_id)
        managed_total_curve = context.curves_by_id.get(managed_curve_id)
        og_source_curve = unmanaged_total_curve or managed_total_curve
        og_source_points = (
            og_source_curve.points
            if og_source_curve is not None
            else (CurvePoint(x=0.0, y=0.0),)
        )
        og1_curve_ref = _old_growth_curve_ref(au_token=au_token, og_label="og1")
        og2_curve_ref = _old_growth_curve_ref(au_token=au_token, og_label="og2")
        curves[og1_curve_ref] = _build_old_growth_1_curve_points(
            unmanaged_total_curve_points=og_source_points,
            horizon_years=horizon_years,
        )
        curves[og2_curve_ref] = _build_old_growth_2_curve_points()
        old_growth_feature_attrs = (
            AttributeBinding(
                label=f"feature.Area.og1.{au_token}",
                curve_idref=og1_curve_ref,
            ),
            AttributeBinding(
                label="feature.Area.og1.total",
                curve_idref=og1_curve_ref,
            ),
            AttributeBinding(
                label=f"feature.Area.og2.{au_token}",
                curve_idref=og2_curve_ref,
            ),
            AttributeBinding(
                label="feature.Area.og2.total",
                curve_idref=og2_curve_ref,
            ),
        )
        managed_cmai_age = max(1, int(cc_max_age))
        effective_cc_min_age = int(cc_min_age)
        if managed_total_curve is not None:
            cmai_age, _ = _derive_curve_metrics(
                managed_total_curve_points=managed_total_curve.points,
                horizon_years=horizon_years,
            )
            managed_cmai_age = int(cmai_age)
            effective_cc_min_age = int(cmai_age - 20)
        effective_cc_min_age = max(0, min(effective_cc_min_age, int(cc_max_age)))
        pct_configs = _resolve_pct_configs_for_au(
            silviculture_config=silviculture_config,
            au_id=au.au_id,
        )
        ct_configs = _resolve_ct_configs_for_au(
            silviculture_config=silviculture_config,
            au_id=au.au_id,
            pct_configs=pct_configs,
        )
        qmd_payload = (silviculture_config or {}).get("qmd")
        qmd_enabled = isinstance(qmd_payload, dict) and bool(
            qmd_payload.get("enabled", False)
        )

        natural_species_curve_map = context.unmanaged_species_curve_ids.get(
            unmanaged_curve_id, {}
        )
        planted_species_curve_map = context.managed_species_curve_ids.get(
            managed_curve_id, {}
        )
        planted_species_has_any_signal = any(
            (curve_def is not None and _curve_has_positive_signal(curve_def.points))
            for curve_def in (
                context.curves_by_id.get(curve_id)
                for curve_id in planted_species_curve_map.values()
            )
        )
        if not planted_species_has_any_signal:
            planted_species_curve_map = natural_species_curve_map

        species_curve_maps_by_origin = {
            "natural": natural_species_curve_map,
            "planted": planted_species_curve_map,
        }
        unmanaged_attrs_by_origin: dict[str, list[AttributeBinding]] = {}
        managed_attrs_by_origin: dict[str, list[AttributeBinding]] = {}
        product_attrs_by_origin: dict[str, list[AttributeBinding]] = {}

        for origin in ORIGIN_ORDER:
            species_curve_map = species_curve_maps_by_origin[origin]
            species_prop_points_by_species = _species_curve_points_by_species(
                context=context,
                species_curve_map=species_curve_map,
            )
            unmanaged_derived_yield_curves = (
                _build_species_yield_curves(
                    total_points=unmanaged_total_curve.points,
                    species_prop_points_by_species=species_prop_points_by_species,
                )
                if unmanaged_total_curve is not None
                else {}
            )
            managed_derived_yield_curves = (
                _build_species_yield_curves(
                    total_points=managed_total_curve.points,
                    species_prop_points_by_species=species_prop_points_by_species,
                )
                if managed_total_curve is not None
                else {}
            )

            unmanaged_attrs = [
                AttributeBinding(label="feature.Area.unmanaged", curve_idref="unity"),
                AttributeBinding(
                    label="feature.Yield.unmanaged.Total",
                    curve_idref=unmanaged_curve_ref,
                ),
                *old_growth_feature_attrs,
            ]
            managed_attrs = [
                AttributeBinding(label="feature.Area.managed", curve_idref="unity"),
                AttributeBinding(
                    label="feature.Yield.managed.Total",
                    curve_idref=managed_curve_ref,
                ),
                *old_growth_feature_attrs,
            ]
            product_attrs = [
                AttributeBinding(
                    label="product.Treated.managed.CC", curve_idref="unity"
                ),
                AttributeBinding(
                    label="product.Yield.managed.Total",
                    curve_idref=managed_curve_ref,
                ),
                AttributeBinding(
                    label="product.HarvestedVolume.managed.Total.CC",
                    curve_idref=managed_curve_ref,
                ),
            ]

            if qmd_enabled:
                unmanaged_qmd_curve_ref = f"au_{au_token}_unmanaged_qmd"
                managed_qmd_curve_ref = f"au_{au_token}_managed_qmd"
                unmanaged_qmd_source = (
                    unmanaged_total_curve.points
                    if unmanaged_total_curve is not None
                    else og_source_points
                )
                managed_qmd_source = (
                    managed_total_curve.points
                    if managed_total_curve is not None
                    else unmanaged_qmd_source
                )
                curves[unmanaged_qmd_curve_ref] = _build_qmd_curve_points(
                    source_curve_points=unmanaged_qmd_source,
                    si_level=au.si_level,
                )
                curves[managed_qmd_curve_ref] = _build_qmd_curve_points(
                    source_curve_points=managed_qmd_source,
                    si_level=au.si_level,
                )
                unmanaged_attrs.append(
                    AttributeBinding(
                        label=f"feature.QMD.unmanaged.{au_token}",
                        curve_idref=unmanaged_qmd_curve_ref,
                    )
                )
                managed_attrs.append(
                    AttributeBinding(
                        label=f"feature.QMD.managed.{au_token}",
                        curve_idref=managed_qmd_curve_ref,
                    )
                )

            for species, species_curve_id in sorted(species_curve_map.items()):
                species_prop_curve = context.curves_by_id.get(species_curve_id)
                species_curve_ref = source_curve_ref_by_id.get(species_curve_id)
                species_has_signal = (
                    species_prop_curve is not None
                    and _curve_has_positive_signal(species_prop_curve.points)
                )

                unmanaged_curve_points = unmanaged_derived_yield_curves.get(species, ())
                if unmanaged_curve_points and _curve_has_positive_signal(
                    unmanaged_curve_points
                ):
                    derived_curve_ref = _derived_species_yield_curve_ref(
                        au_token=au_token,
                        managed=False,
                        origin=origin,
                        species=species,
                    )
                    curves[derived_curve_ref] = unmanaged_curve_points
                    unmanaged_attrs.append(
                        AttributeBinding(
                            label=f"feature.Yield.unmanaged.{species}",
                            curve_idref=derived_curve_ref,
                        )
                    )

                managed_curve_points = managed_derived_yield_curves.get(species, ())
                if managed_curve_points and _curve_has_positive_signal(
                    managed_curve_points
                ):
                    derived_curve_ref = _derived_species_yield_curve_ref(
                        au_token=au_token,
                        managed=True,
                        origin=origin,
                        species=species,
                    )
                    curves[derived_curve_ref] = managed_curve_points
                    managed_attrs.append(
                        AttributeBinding(
                            label=f"feature.Yield.managed.{species}",
                            curve_idref=derived_curve_ref,
                        )
                    )
                    product_attrs.append(
                        AttributeBinding(
                            label=f"product.Yield.managed.{species}",
                            curve_idref=derived_curve_ref,
                        )
                    )
                    product_attrs.append(
                        AttributeBinding(
                            label=f"product.HarvestedVolume.managed.{species}.CC",
                            curve_idref=derived_curve_ref,
                        )
                    )

                if species_curve_ref is not None and species_has_signal:
                    unmanaged_attrs.append(
                        AttributeBinding(
                            label=f"feature.SpeciesProp.unmanaged.{species}",
                            curve_idref=species_curve_ref,
                        )
                    )
                    managed_attrs.append(
                        AttributeBinding(
                            label=f"feature.SpeciesProp.managed.{species}",
                            curve_idref=species_curve_ref,
                        )
                    )
                    product_attrs.append(
                        AttributeBinding(
                            label=f"product.SpeciesProp.managed.{species}",
                            curve_idref=species_curve_ref,
                        )
                    )

            unmanaged_attrs_by_origin[origin] = unmanaged_attrs
            managed_attrs_by_origin[origin] = managed_attrs
            product_attrs_by_origin[origin] = product_attrs

        if seral_stage_config is not None:
            seral_source_curve = managed_total_curve
            if seral_source_curve is None:
                seral_source_curve = unmanaged_total_curve
            seral_points = (
                seral_source_curve.points
                if seral_source_curve is not None
                else (CurvePoint(x=0.0, y=0.0),)
            )
            seral_bounds = _resolve_seral_bounds_for_au(
                au_id=au.au_id,
                managed_total_curve_points=seral_points,
                horizon_years=horizon_years,
                seral_stage_config=seral_stage_config,
            )
            for stage in SERAL_STAGE_ORDER:
                stage_min, stage_max = seral_bounds[stage]
                curve_ref = _seral_curve_ref(au_token=au_token, stage=stage)
                curves[curve_ref] = _build_seral_curve_points(
                    min_age=stage_min,
                    max_age=stage_max,
                    horizon_years=horizon_years,
                    managed_total_curve_points=seral_points,
                )
                feature_labels = (
                    f"feature.Seral.{stage}",
                    f"feature.Seral.{au_token}.{stage}",
                )
                for origin in ORIGIN_ORDER:
                    for feature_label in feature_labels:
                        unmanaged_attrs_by_origin[origin].append(
                            AttributeBinding(
                                label=feature_label,
                                curve_idref=curve_ref,
                            )
                        )
                        managed_attrs_by_origin[origin].append(
                            AttributeBinding(
                                label=feature_label,
                                curve_idref=curve_ref,
                            )
                        )
                    product_attrs_by_origin[origin].append(
                        AttributeBinding(
                            label=(f"product.Seral.area.{stage}.{au_token}.CC"),
                            curve_idref=curve_ref,
                        )
                    )

        cc_treatment = TreatmentDefinition(
            label="CC",
            min_age=effective_cc_min_age,
            max_age=int(cc_max_age),
            assignments=(
                TreatmentAssignment(
                    field="treatment",
                    value=_as_quoted_literal("CC"),
                ),
            ),
            transition_assignments=transition_assignments,
        )

        for origin in ORIGIN_ORDER:
            default_silv_state = _default_silv_state_for_origin(origin)
            origin_literal = _as_quoted_literal(origin)
            silv_literal = _as_quoted_literal(default_silv_state)
            selects.append(
                SelectDefinition(
                    statement=(
                        f"{_au_eq_statement(au.au_id)} and IFM eq 'unmanaged' and ORIGIN eq {origin_literal} and SILV_STATE eq {silv_literal}"
                    ),
                    feature_attributes=tuple(unmanaged_attrs_by_origin[origin]),
                    include_track=True,
                )
            )
            track_treatments_list: list[TreatmentDefinition] = [cc_treatment]
            if origin == "planted":
                for pct_config in pct_configs:
                    if pct_config["from_state"] != default_silv_state:
                        continue
                    track_treatments_list.append(
                        TreatmentDefinition(
                            label=str(pct_config["label"]),
                            min_age=int(pct_config["pct_age"]),
                            max_age=int(pct_config["pct_age"]),
                            assignments=(
                                TreatmentAssignment(
                                    field="treatment",
                                    value=_as_quoted_literal(str(pct_config["label"])),
                                ),
                            ),
                            transition_assignments=(
                                TreatmentAssignment(
                                    field="SILV_STATE",
                                    value=_as_quoted_literal(pct_config["to_state"]),
                                ),
                            ),
                        )
                    )
                for ct_config in ct_configs:
                    if ct_config["from_state"] != default_silv_state:
                        continue
                    track_treatments_list.append(
                        TreatmentDefinition(
                            label=str(ct_config["label"]),
                            min_age=int(ct_config["ct_age"]),
                            max_age=int(ct_config["ct_age"]),
                            adjust="R",
                            assignments=(
                                TreatmentAssignment(
                                    field="treatment",
                                    value=_as_quoted_literal(str(ct_config["label"])),
                                ),
                            ),
                            transition_assignments=(
                                TreatmentAssignment(
                                    field="SILV_STATE",
                                    value=_as_quoted_literal(ct_config["to_state"]),
                                ),
                            ),
                        )
                    )
            track_treatments = tuple(track_treatments_list)
            selects.append(
                SelectDefinition(
                    statement=(
                        f"{_au_eq_statement(au.au_id)} and IFM eq 'managed' and ORIGIN eq {origin_literal} and SILV_STATE eq {silv_literal}"
                    ),
                    feature_attributes=tuple(managed_attrs_by_origin[origin]),
                    retention_definitions=(
                        RetentionDefinition(
                            factor="RETENTION",
                            assignments=(
                                TreatmentAssignment(
                                    field="IFM",
                                    value=_as_quoted_literal("unmanaged"),
                                ),
                            ),
                        ),
                    ),
                    include_track=True,
                    track_treatment=cc_treatment,
                    track_treatments=track_treatments,
                )
            )
            selects.append(
                SelectDefinition(
                    statement=(
                        f"{_au_eq_statement(au.au_id)} and IFM eq 'managed' and ORIGIN eq {origin_literal} and SILV_STATE eq {silv_literal} and treatment eq 'CC'"
                    ),
                    product_attributes=tuple(product_attrs_by_origin[origin]),
                )
            )

        planted_species_prop_points = _species_curve_points_by_species(
            context=context,
            species_curve_map=planted_species_curve_map,
        )
        pct_state_payload_by_to_state: dict[str, dict[str, Any]] = {}
        if pct_configs and managed_total_curve is not None:
            for pct_config in pct_configs:
                if pct_config["remove_stems_per_ha_by_species"]:
                    pct_species_prop_points = (
                        _build_species_prop_points_with_stem_removals(
                            species_prop_points_by_species=planted_species_prop_points,
                            remove_stems_per_ha_by_species=tuple(
                                pct_config["remove_stems_per_ha_by_species"]
                            ),
                            source_total_stems_per_ha=float(
                                pct_config["source_total_stems_per_ha"]
                            ),
                        )
                    )
                else:
                    pct_species_prop_points = (
                        _build_species_prop_points_without_species(
                            species_prop_points_by_species=planted_species_prop_points,
                            excluded_species=tuple(pct_config["remove_species"]),
                        )
                    )
                pct_species_curve_refs: dict[str, str] = {}
                pct_feature_attrs = [
                    AttributeBinding(label="feature.Area.managed", curve_idref="unity"),
                    AttributeBinding(
                        label="feature.Yield.managed.Total",
                        curve_idref=managed_curve_ref,
                    ),
                    *old_growth_feature_attrs,
                ]
                pct_product_attrs = [
                    AttributeBinding(
                        label=str(pct_config["product_label"]), curve_idref="unity"
                    )
                ]
                pct_cc_product_attrs = [
                    AttributeBinding(
                        label="product.Treated.managed.CC", curve_idref="unity"
                    ),
                    AttributeBinding(
                        label="product.Yield.managed.Total",
                        curve_idref=managed_curve_ref,
                    ),
                    AttributeBinding(
                        label="product.HarvestedVolume.managed.Total.CC",
                        curve_idref=managed_curve_ref,
                    ),
                ]
                pct_species_yield_curves = _build_species_yield_curves(
                    total_points=managed_total_curve.points,
                    species_prop_points_by_species=pct_species_prop_points,
                )
                for species, species_curve_points in sorted(
                    pct_species_yield_curves.items()
                ):
                    if species_curve_points and _curve_has_positive_signal(
                        species_curve_points
                    ):
                        pct_yield_curve_ref = (
                            f"au_{au_token}_managed_{_sanitize_id_component(str(pct_config['to_state']))}_yield_"
                            f"{_sanitize_id_component(species)}"
                        )
                        curves[pct_yield_curve_ref] = species_curve_points
                        pct_feature_attrs.append(
                            AttributeBinding(
                                label=f"feature.Yield.managed.{species}",
                                curve_idref=pct_yield_curve_ref,
                            )
                        )
                        pct_cc_product_attrs.append(
                            AttributeBinding(
                                label=f"product.Yield.managed.{species}",
                                curve_idref=pct_yield_curve_ref,
                            )
                        )
                        pct_cc_product_attrs.append(
                            AttributeBinding(
                                label=f"product.HarvestedVolume.managed.{species}.CC",
                                curve_idref=pct_yield_curve_ref,
                            )
                        )
                for species, species_prop_points in sorted(
                    pct_species_prop_points.items()
                ):
                    if not _curve_has_positive_signal(species_prop_points):
                        continue
                    pct_prop_curve_ref = (
                        f"au_{au_token}_managed_{_sanitize_id_component(str(pct_config['to_state']))}_species_prop_"
                        f"{_sanitize_id_component(species)}"
                    )
                    curves[pct_prop_curve_ref] = species_prop_points
                    pct_species_curve_refs[species] = pct_prop_curve_ref
                    pct_feature_attrs.append(
                        AttributeBinding(
                            label=f"feature.SpeciesProp.managed.{species}",
                            curve_idref=pct_prop_curve_ref,
                        )
                    )
                    pct_cc_product_attrs.append(
                        AttributeBinding(
                            label=f"product.SpeciesProp.managed.{species}",
                            curve_idref=pct_prop_curve_ref,
                        )
                    )
                pct_state_literal = _as_quoted_literal(pct_config["to_state"])
                pct_state_track_treatments_list: list[TreatmentDefinition] = [
                    cc_treatment
                ]
                for ct_config in ct_configs:
                    if ct_config["from_state"] != pct_config["to_state"]:
                        continue
                    pct_state_track_treatments_list.append(
                        TreatmentDefinition(
                            label=str(ct_config["label"]),
                            min_age=int(ct_config["ct_age"]),
                            max_age=int(ct_config["ct_age"]),
                            adjust="R",
                            assignments=(
                                TreatmentAssignment(
                                    field="treatment",
                                    value=_as_quoted_literal(str(ct_config["label"])),
                                ),
                            ),
                            transition_assignments=(
                                TreatmentAssignment(
                                    field="SILV_STATE",
                                    value=_as_quoted_literal(ct_config["to_state"]),
                                ),
                            ),
                        )
                    )
                selects.append(
                    SelectDefinition(
                        statement=(
                            f"{_au_eq_statement(au.au_id)} and IFM eq 'unmanaged' and ORIGIN eq 'planted' and SILV_STATE eq {pct_state_literal}"
                        ),
                        feature_attributes=tuple(unmanaged_attrs_by_origin["planted"]),
                        include_track=True,
                    )
                )
                selects.append(
                    SelectDefinition(
                        statement=(
                            f"{_au_eq_statement(au.au_id)} and IFM eq 'managed' and ORIGIN eq 'planted' and SILV_STATE eq {pct_state_literal}"
                        ),
                        feature_attributes=tuple(pct_feature_attrs),
                        retention_definitions=(
                            RetentionDefinition(
                                factor="RETENTION",
                                assignments=(
                                    TreatmentAssignment(
                                        field="IFM",
                                        value=_as_quoted_literal("unmanaged"),
                                    ),
                                ),
                            ),
                        ),
                        include_track=True,
                        track_treatment=cc_treatment,
                        track_treatments=tuple(pct_state_track_treatments_list),
                    )
                )
                selects.append(
                    SelectDefinition(
                        statement=(
                            f"{_au_eq_statement(au.au_id)} and IFM eq 'managed' and ORIGIN eq 'planted' and SILV_STATE eq {_as_quoted_literal(pct_config['from_state'])} and treatment eq {_as_quoted_literal(str(pct_config['label']))}"
                        ),
                        product_attributes=tuple(pct_product_attrs),
                    )
                )
                selects.append(
                    SelectDefinition(
                        statement=(
                            f"{_au_eq_statement(au.au_id)} and IFM eq 'managed' and ORIGIN eq 'planted' and SILV_STATE eq {pct_state_literal} and treatment eq 'CC'"
                        ),
                        product_attributes=tuple(pct_cc_product_attrs),
                    )
                )
                pct_state_payload_by_to_state[str(pct_config["to_state"])] = {
                    "species_prop_points": pct_species_prop_points,
                    "species_curve_refs": dict(pct_species_curve_refs),
                }

        if ct_configs and managed_total_curve is not None:
            for ct_config in ct_configs:
                ct_species_prop_points = planted_species_prop_points
                ct_species_prop_curve_refs = {
                    species: source_curve_ref_by_id[curve_id]
                    for species, curve_id in planted_species_curve_map.items()
                    if curve_id in source_curve_ref_by_id
                }
                pct_state_payload = pct_state_payload_by_to_state.get(
                    str(ct_config["from_state"])
                )
                if pct_state_payload is not None:
                    ct_species_prop_points = pct_state_payload["species_prop_points"]
                    ct_species_prop_curve_refs = dict(
                        pct_state_payload["species_curve_refs"]
                    )
                ct_age = int(ct_config["ct_age"])
                fert_sequence: tuple[dict[str, Any], ...] = ()
                if managed_total_curve is not None:
                    fert_sequence = _resolve_fertilization_sequence_for_au(
                        silviculture_config=silviculture_config,
                        au_id=au.au_id,
                        planted_total_curve_points=managed_total_curve.points,
                        ct_age=ct_age,
                        horizon_years=horizon_years,
                    )
                    if fert_sequence:
                        max_ct_age = max(1, int(fert_sequence[0]["fert_age"]) - 10)
                        effective_ct_age = min(ct_age, max_ct_age)
                        if effective_ct_age != ct_age:
                            ct_config = {**ct_config, "ct_age": effective_ct_age}
                            ct_age = effective_ct_age
                            fert_sequence = _resolve_fertilization_sequence_for_au(
                                silviculture_config=silviculture_config,
                                au_id=au.au_id,
                                planted_total_curve_points=managed_total_curve.points,
                                ct_age=ct_age,
                                horizon_years=horizon_years,
                            )
                fert1_config = fert_sequence[0] if fert_sequence else None
                state_slug = _sanitize_id_component(str(ct_config["to_state"]))
                ct_removed_volume = round(
                    max(
                        0.0,
                        _curve_value_at_x(
                            points=managed_total_curve.points, x=float(ct_age)
                        )
                        * float(ct_config["removal_fraction"]),
                    ),
                    1,
                )
                ct_product_curve_ref = f"au_{au_token}_{state_slug}_harvest_total"
                ct_residual_curve_ref = f"au_{au_token}_{state_slug}_residual_total"
                curves[ct_product_curve_ref] = _build_constant_curve_points_like(
                    source_curve_points=managed_total_curve.points,
                    value=ct_removed_volume,
                )
                curves[ct_residual_curve_ref] = _build_curve_with_post_thinning_gap(
                    source_curve_points=managed_total_curve.points,
                    transition_age=ct_age,
                    gap_at_transition_value=ct_removed_volume,
                    final_gap_factor=float(ct_config["final_felling_gap_factor"]),
                    ramp_end_age=managed_cmai_age,
                )
                ct_product_attrs = [
                    AttributeBinding(
                        label="product.Treated.managed.CT", curve_idref="unity"
                    ),
                    AttributeBinding(
                        label="product.Yield.managed.Total",
                        curve_idref=ct_product_curve_ref,
                    ),
                    AttributeBinding(
                        label="product.HarvestedVolume.managed.Total.CT",
                        curve_idref=ct_product_curve_ref,
                    ),
                ]
                ct_cc_product_attrs = [
                    AttributeBinding(
                        label="product.Treated.managed.CC", curve_idref="unity"
                    ),
                    AttributeBinding(
                        label="product.Yield.managed.Total",
                        curve_idref=ct_residual_curve_ref,
                    ),
                    AttributeBinding(
                        label="product.HarvestedVolume.managed.Total.CC",
                        curve_idref=ct_residual_curve_ref,
                    ),
                ]
                ct_residual_attrs = [
                    AttributeBinding(label="feature.Area.managed", curve_idref="unity"),
                    AttributeBinding(
                        label="feature.Yield.managed.Total",
                        curve_idref=ct_residual_curve_ref,
                    ),
                    *old_growth_feature_attrs,
                ]
                if qmd_enabled:
                    ct_qmd_curve_ref = f"au_{au_token}_managed_{state_slug}_qmd"
                    curves[ct_qmd_curve_ref] = _build_qmd_curve_points(
                        source_curve_points=managed_total_curve.points,
                        si_level=au.si_level,
                        response_age=ct_age,
                        response_fraction=float(ct_config["qmd_response_fraction"]),
                    )
                    ct_residual_attrs.append(
                        AttributeBinding(
                            label=f"feature.QMD.managed.{au_token}",
                            curve_idref=ct_qmd_curve_ref,
                        )
                    )
                ct_species_product_curves = _build_species_yield_curves(
                    total_points=curves[ct_product_curve_ref],
                    species_prop_points_by_species=ct_species_prop_points,
                )
                ct_species_residual_curves = _build_species_yield_curves(
                    total_points=curves[ct_residual_curve_ref],
                    species_prop_points_by_species=ct_species_prop_points,
                )
                for species, species_curve_points in sorted(
                    ct_species_residual_curves.items()
                ):
                    if species_curve_points and _curve_has_positive_signal(
                        species_curve_points
                    ):
                        residual_curve_ref = (
                            f"au_{au_token}_managed_{state_slug}_yield_"
                            f"{_sanitize_id_component(species)}"
                        )
                        curves[residual_curve_ref] = species_curve_points
                        ct_residual_attrs.append(
                            AttributeBinding(
                                label=f"feature.Yield.managed.{species}",
                                curve_idref=residual_curve_ref,
                            )
                        )
                        ct_cc_product_attrs.append(
                            AttributeBinding(
                                label=f"product.Yield.managed.{species}",
                                curve_idref=residual_curve_ref,
                            )
                        )
                        ct_cc_product_attrs.append(
                            AttributeBinding(
                                label=f"product.HarvestedVolume.managed.{species}.CC",
                                curve_idref=residual_curve_ref,
                            )
                        )
                for species, species_curve_points in sorted(
                    ct_species_product_curves.items()
                ):
                    if species_curve_points and _curve_has_positive_signal(
                        species_curve_points
                    ):
                        product_curve_ref = (
                            f"au_{au_token}_{state_slug}_harvest_"
                            f"{_sanitize_id_component(species)}"
                        )
                        curves[product_curve_ref] = species_curve_points
                        ct_product_attrs.append(
                            AttributeBinding(
                                label=f"product.Yield.managed.{species}",
                                curve_idref=product_curve_ref,
                            )
                        )
                        ct_product_attrs.append(
                            AttributeBinding(
                                label=f"product.HarvestedVolume.managed.{species}.CT",
                                curve_idref=product_curve_ref,
                            )
                        )
                for species, species_prop_curve_ref in sorted(
                    ct_species_prop_curve_refs.items()
                ):
                    if species_prop_curve_ref is not None:
                        ct_residual_attrs.append(
                            AttributeBinding(
                                label=f"feature.SpeciesProp.managed.{species}",
                                curve_idref=species_prop_curve_ref,
                            )
                        )
                        ct_product_attrs.append(
                            AttributeBinding(
                                label=f"product.SpeciesProp.managed.{species}",
                                curve_idref=species_prop_curve_ref,
                            )
                        )
                        ct_cc_product_attrs.append(
                            AttributeBinding(
                                label=f"product.SpeciesProp.managed.{species}",
                                curve_idref=species_prop_curve_ref,
                            )
                        )
                ct_state_literal = _as_quoted_literal(ct_config["to_state"])
                ct_state_track_treatments: tuple[TreatmentDefinition, ...] = (
                    cc_treatment,
                )
                if (
                    fert1_config is not None
                    and fert1_config["from_state"] == ct_config["to_state"]
                ):
                    fert1_treatment = TreatmentDefinition(
                        label=fert1_config["label"],
                        min_age=int(fert1_config["fert_age"]),
                        max_age=int(fert1_config["fert_age"]),
                        adjust="R",
                        assignments=(
                            TreatmentAssignment(
                                field="treatment",
                                value=_as_quoted_literal(fert1_config["label"]),
                            ),
                        ),
                        transition_assignments=(
                            TreatmentAssignment(
                                field="SILV_STATE",
                                value=_as_quoted_literal(fert1_config["to_state"]),
                            ),
                        ),
                    )
                    ct_state_track_treatments = (cc_treatment, fert1_treatment)
                selects.append(
                    SelectDefinition(
                        statement=(
                            f"{_au_eq_statement(au.au_id)} and IFM eq 'unmanaged' and ORIGIN eq 'planted' and SILV_STATE eq {ct_state_literal}"
                        ),
                        feature_attributes=tuple(unmanaged_attrs_by_origin["planted"]),
                        include_track=True,
                    )
                )
                selects.append(
                    SelectDefinition(
                        statement=(
                            f"{_au_eq_statement(au.au_id)} and IFM eq 'managed' and ORIGIN eq 'planted' and SILV_STATE eq {ct_state_literal}"
                        ),
                        feature_attributes=tuple(ct_residual_attrs),
                        retention_definitions=(
                            RetentionDefinition(
                                factor="RETENTION",
                                assignments=(
                                    TreatmentAssignment(
                                        field="IFM",
                                        value=_as_quoted_literal("unmanaged"),
                                    ),
                                ),
                            ),
                        ),
                        include_track=True,
                        track_treatment=cc_treatment,
                        track_treatments=ct_state_track_treatments,
                    )
                )
                selects.append(
                    SelectDefinition(
                        statement=(
                            f"{_au_eq_statement(au.au_id)} and IFM eq 'managed' and ORIGIN eq 'planted' and SILV_STATE eq {_as_quoted_literal(ct_config['from_state'])} and treatment eq {_as_quoted_literal(str(ct_config['label']))}"
                        ),
                        product_attributes=tuple(ct_product_attrs),
                    )
                )
                selects.append(
                    SelectDefinition(
                        statement=(
                            f"{_au_eq_statement(au.au_id)} and IFM eq 'managed' and ORIGIN eq 'planted' and SILV_STATE eq {ct_state_literal} and treatment eq 'CC'"
                        ),
                        product_attributes=tuple(ct_cc_product_attrs),
                    )
                )

            if fert_sequence:
                current_source_points = curves[ct_residual_curve_ref]
                for fert_index, fert_config in enumerate(fert_sequence, start=1):
                    fert_curve_ref = f"au_{au_token}_fert{fert_index}_total"
                    curves[fert_curve_ref] = _build_curve_with_temporary_speedup(
                        source_curve_points=current_source_points,
                        response_age=int(fert_config["fert_age"]),
                        speedup_fraction=float(fert_config["speedup_fraction"]),
                        response_years=int(fert_config["response_years"]),
                    )
                    fert_feature_attrs = [
                        AttributeBinding(
                            label="feature.Area.managed", curve_idref="unity"
                        ),
                        AttributeBinding(
                            label="feature.Yield.managed.Total",
                            curve_idref=fert_curve_ref,
                        ),
                        *old_growth_feature_attrs,
                    ]
                    fert_product_attrs = [
                        AttributeBinding(
                            label=f"product.Treated.managed.{fert_config['label']}",
                            curve_idref="unity",
                        )
                    ]
                    fert_cc_product_attrs = [
                        AttributeBinding(
                            label="product.Treated.managed.CC", curve_idref="unity"
                        ),
                        AttributeBinding(
                            label="product.Yield.managed.Total",
                            curve_idref=fert_curve_ref,
                        ),
                        AttributeBinding(
                            label="product.HarvestedVolume.managed.Total.CC",
                            curve_idref=fert_curve_ref,
                        ),
                    ]
                    if qmd_enabled:
                        fert_qmd_curve_ref = f"au_{au_token}_managed_{_sanitize_id_component(str(fert_config['to_state']))}_qmd"
                        curves[fert_qmd_curve_ref] = _build_qmd_curve_points(
                            source_curve_points=current_source_points,
                            si_level=au.si_level,
                            response_age=int(fert_config["fert_age"]),
                            response_fraction=float(
                                fert_config["qmd_response_fraction"]
                            ),
                            response_years=int(fert_config["response_years"]),
                        )
                        fert_feature_attrs.append(
                            AttributeBinding(
                                label=f"feature.QMD.managed.{au_token}",
                                curve_idref=fert_qmd_curve_ref,
                            )
                        )
                    fert_species_curves = _build_species_yield_curves(
                        total_points=curves[fert_curve_ref],
                        species_prop_points_by_species=ct_species_prop_points,
                    )
                    for species, species_curve_points in sorted(
                        fert_species_curves.items()
                    ):
                        if species_curve_points and _curve_has_positive_signal(
                            species_curve_points
                        ):
                            fert_species_curve_ref = (
                                f"au_{au_token}_managed_{_sanitize_id_component(str(fert_config['to_state']))}_yield_"
                                f"{_sanitize_id_component(species)}"
                            )
                            curves[fert_species_curve_ref] = species_curve_points
                            fert_feature_attrs.append(
                                AttributeBinding(
                                    label=f"feature.Yield.managed.{species}",
                                    curve_idref=fert_species_curve_ref,
                                )
                            )
                            fert_cc_product_attrs.append(
                                AttributeBinding(
                                    label=f"product.Yield.managed.{species}",
                                    curve_idref=fert_species_curve_ref,
                                )
                            )
                            fert_cc_product_attrs.append(
                                AttributeBinding(
                                    label=f"product.HarvestedVolume.managed.{species}.CC",
                                    curve_idref=fert_species_curve_ref,
                                )
                            )
                    for species, species_prop_curve_ref in sorted(
                        ct_species_prop_curve_refs.items()
                    ):
                        if species_prop_curve_ref is not None:
                            fert_feature_attrs.append(
                                AttributeBinding(
                                    label=f"feature.SpeciesProp.managed.{species}",
                                    curve_idref=species_prop_curve_ref,
                                )
                            )
                            fert_cc_product_attrs.append(
                                AttributeBinding(
                                    label=f"product.SpeciesProp.managed.{species}",
                                    curve_idref=species_prop_curve_ref,
                                )
                            )
                    fert_state_literal = _as_quoted_literal(fert_config["to_state"])
                    next_track_treatments: tuple[TreatmentDefinition, ...] = (
                        cc_treatment,
                    )
                    if fert_index < len(fert_sequence):
                        next_fert = fert_sequence[fert_index]
                        if next_fert["from_state"] == fert_config["to_state"]:
                            next_treatment = TreatmentDefinition(
                                label=next_fert["label"],
                                min_age=int(next_fert["fert_age"]),
                                max_age=int(next_fert["fert_age"]),
                                adjust="R",
                                assignments=(
                                    TreatmentAssignment(
                                        field="treatment",
                                        value=_as_quoted_literal(next_fert["label"]),
                                    ),
                                ),
                                transition_assignments=(
                                    TreatmentAssignment(
                                        field="SILV_STATE",
                                        value=_as_quoted_literal(next_fert["to_state"]),
                                    ),
                                ),
                            )
                            next_track_treatments = (cc_treatment, next_treatment)
                    selects.append(
                        SelectDefinition(
                            statement=(
                                f"{_au_eq_statement(au.au_id)} and IFM eq 'unmanaged' and ORIGIN eq 'planted' and SILV_STATE eq {fert_state_literal}"
                            ),
                            feature_attributes=tuple(
                                unmanaged_attrs_by_origin["planted"]
                            ),
                            include_track=True,
                        )
                    )
                    selects.append(
                        SelectDefinition(
                            statement=(
                                f"{_au_eq_statement(au.au_id)} and IFM eq 'managed' and ORIGIN eq 'planted' and SILV_STATE eq {fert_state_literal}"
                            ),
                            feature_attributes=tuple(fert_feature_attrs),
                            retention_definitions=(
                                RetentionDefinition(
                                    factor="RETENTION",
                                    assignments=(
                                        TreatmentAssignment(
                                            field="IFM",
                                            value=_as_quoted_literal("unmanaged"),
                                        ),
                                    ),
                                ),
                            ),
                            include_track=True,
                            track_treatment=cc_treatment,
                            track_treatments=next_track_treatments,
                        )
                    )
                    selects.append(
                        SelectDefinition(
                            statement=(
                                f"{_au_eq_statement(au.au_id)} and IFM eq 'managed' and ORIGIN eq 'planted' and SILV_STATE eq {_as_quoted_literal(fert_config['from_state'])} and treatment eq '{fert_config['label']}'"
                            ),
                            product_attributes=tuple(fert_product_attrs),
                        )
                    )
                    selects.append(
                        SelectDefinition(
                            statement=(
                                f"{_au_eq_statement(au.au_id)} and IFM eq 'managed' and ORIGIN eq 'planted' and SILV_STATE eq {fert_state_literal} and treatment eq 'CC'"
                            ),
                            product_attributes=tuple(fert_cc_product_attrs),
                        )
                    )
                    current_source_points = curves[fert_curve_ref]

    return ForestModelDefinition(
        description="FEMIC Patchworks export",
        horizon=int(horizon_years),
        year=int(start_year),
        match="multi",
        input_attributes={
            "block": "BLOCK",
            "area": "AREA_HA",
            "age": "F_AGE",
            "exclude": "BLOCK=0",
        },
        output_attributes={
            "messages": "messages.csv",
            "blocks": "blocks.csv",
            "features": "features.csv",
            "products": "products.csv",
            "treatments": "treatments.csv",
            "curves": "curves.csv",
            "tracknames": "tracknames.csv",
        },
        define_fields=(
            DefineFieldDefinition(field="AU", column="AU"),
            DefineFieldDefinition(field="IFM", column="IFM"),
            DefineFieldDefinition(field="ORIGIN", column="ORIGIN"),
            DefineFieldDefinition(field="SILV_STATE", column="SILV_STATE"),
            DefineFieldDefinition(
                field="RETENTION", column="Number(column('RETENTION'))"
            ),
            DefineFieldDefinition(field="treatment"),
        ),
        curves=curves,
        selects=tuple(selects),
    )


def _append_attribute_bindings(
    *,
    parent: et.Element,
    tag_name: str,
    bindings: tuple[AttributeBinding, ...],
) -> None:
    node = et.SubElement(parent, tag_name)
    for binding in bindings:
        attr = et.SubElement(node, "attribute", {"label": binding.label})
        et.SubElement(attr, "curve", {"idref": binding.curve_idref})


def _append_retention_definitions(
    *,
    parent: et.Element,
    retention_definitions: tuple[RetentionDefinition, ...],
) -> None:
    for retention_definition in retention_definitions:
        retention = et.SubElement(
            parent,
            "retention",
            {"factor": retention_definition.factor},
        )
        for assignment in retention_definition.assignments:
            et.SubElement(
                retention,
                "assign",
                {"field": assignment.field, "value": assignment.value},
            )
        if retention_definition.feature_attributes:
            _append_attribute_bindings(
                parent=retention,
                tag_name="features",
                bindings=retention_definition.feature_attributes,
            )


def _append_track_treatment(
    *, parent: et.Element, treatment_def: TreatmentDefinition
) -> None:
    attrs = {
        "label": treatment_def.label,
        "minage": str(int(treatment_def.min_age)),
        "maxage": str(int(treatment_def.max_age)),
    }
    if treatment_def.adjust:
        attrs["adjust"] = treatment_def.adjust
    treatment = et.SubElement(parent, "treatment", attrs)
    if treatment_def.assignments:
        produce = et.SubElement(treatment, "produce")
        for assignment in treatment_def.assignments:
            et.SubElement(
                produce,
                "assign",
                {"field": assignment.field, "value": assignment.value},
            )
    if treatment_def.transition_assignments:
        transition = et.SubElement(treatment, "transition")
        for assignment in treatment_def.transition_assignments:
            et.SubElement(
                transition,
                "assign",
                {"field": assignment.field, "value": assignment.value},
            )


def _append_track(
    *,
    parent: et.Element,
    include_track: bool,
    track_treatment: TreatmentDefinition | None,
    track_treatments: tuple[TreatmentDefinition, ...] = (),
) -> None:
    treatment_defs = track_treatments or (
        (track_treatment,) if track_treatment is not None else ()
    )
    if not include_track and not treatment_defs:
        return
    track = et.SubElement(parent, "track")
    for treatment_def in treatment_defs:
        _append_track_treatment(parent=track, treatment_def=treatment_def)


def forestmodel_definition_to_xml_tree(
    *,
    definition: ForestModelDefinition,
) -> et.Element:
    """Serialize ForestModel core definition to XML tree."""
    root = et.Element(
        "ForestModel",
        {
            "description": definition.description,
            "horizon": str(int(definition.horizon)),
            "year": str(int(definition.year)),
            "match": definition.match,
        },
    )

    curve_ids = sorted([cid for cid in definition.curves if cid != "unity"])
    if "unity" in definition.curves:
        curve_ids = ["unity", *curve_ids]
    for curve_id in curve_ids:
        curve_node = et.SubElement(root, "curve", {"id": curve_id})
        points = _sanitize_curve_points_for_xml(definition.curves[curve_id])
        if curve_id != "unity":
            points = _trim_flat_tail_points(points)
        if not points and curve_id == "unity":
            points = (CurvePoint(x=0.0, y=1.0),)
        elif not points:
            points = (CurvePoint(x=0.0, y=0.0),)
        for point in points:
            x_val = _format_xml_x(float(point.x))
            y_val = _format_xml_y(curve_id, float(point.y))
            et.SubElement(
                curve_node,
                "point",
                {"x": x_val, "y": y_val},
            )

    for define_field in definition.define_fields:
        attrs = {"field": define_field.field}
        if define_field.column is not None:
            attrs["column"] = define_field.column
        et.SubElement(root, "define", attrs)

    et.SubElement(root, "input", definition.input_attributes)
    et.SubElement(root, "output", definition.output_attributes)

    for select in definition.selects:
        select_node = et.SubElement(root, "select", {"statement": select.statement})
        if select.feature_attributes:
            _append_attribute_bindings(
                parent=select_node,
                tag_name="features",
                bindings=select.feature_attributes,
            )
        if select.retention_definitions:
            _append_retention_definitions(
                parent=select_node,
                retention_definitions=select.retention_definitions,
            )
        _append_track(
            parent=select_node,
            include_track=select.include_track,
            track_treatment=select.track_treatment,
            track_treatments=select.track_treatments,
        )
        if select.product_attributes:
            _append_attribute_bindings(
                parent=select_node,
                tag_name="products",
                bindings=select.product_attributes,
            )

    return root


def write_forestmodel_xml(*, root: et.Element, path: Path) -> None:
    """Write ForestModel XML tree with Patchworks XSD model hint."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tree = et.ElementTree(root)
    et.indent(tree, space="  ")
    xml_body = et.tostring(root, encoding="unicode")
    payload = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<?xml-model href="https://www.spatial.ca/ForestModel.xsd"?>\n'
        f"{xml_body}\n"
    )
    path.write_text(payload, encoding="utf-8")


def validate_forestmodel_xml_tree(*, root: et.Element) -> None:
    """Validate required ForestModel structure and curve references."""
    issues: list[str] = []
    if root.tag != "ForestModel":
        issues.append(f"root tag must be ForestModel (found {root.tag!r})")

    for attr in ("horizon", "year", "match"):
        if not root.get(attr):
            issues.append(f"ForestModel missing required attribute: {attr}")

    input_nodes = root.findall("./input")
    if not input_nodes:
        issues.append("ForestModel missing <input> node")
    else:
        required_input_attrs = {"block", "area", "age"}
        for attr in required_input_attrs:
            if not input_nodes[0].get(attr):
                issues.append(f"<input> missing required attribute: {attr}")

    output_nodes = root.findall("./output")
    if not output_nodes:
        issues.append("ForestModel missing <output> node")

    define_fields = {
        field
        for node in root.findall("./define")
        for field in [node.get("field")]
        if field is not None
    }
    for field in ("AU", "IFM", "ORIGIN", "SILV_STATE", "RETENTION", "treatment"):
        if field not in define_fields:
            issues.append(f"missing define field: {field}")

    curve_ids = {
        curve_id
        for node in root.findall(".//curve")
        for curve_id in [node.get("id")]
        if isinstance(curve_id, str)
    }
    if "unity" not in curve_ids:
        issues.append("missing required curve id 'unity'")
    if not root.findall("./curve[@id='unity']/point"):
        issues.append("unity curve missing point(s)")

    idrefs = {
        idref
        for node in root.findall(".//attribute/curve")
        for idref in [node.get("idref")]
        if isinstance(idref, str)
    }
    missing_idrefs = sorted(ref for ref in idrefs if ref not in curve_ids)
    if missing_idrefs:
        issues.append(
            f"attribute curve idref(s) missing matching curve: {missing_idrefs}"
        )

    for assign_node in root.findall(".//assign"):
        field_name = assign_node.get("field")
        if field_name and field_name not in define_fields:
            issues.append(f"assign references undefined field: {field_name}")

    identifier_pattern = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
    for retention_node in root.findall(".//retention"):
        factor = retention_node.get("factor")
        if not factor:
            issues.append("retention element missing factor attribute")
            continue
        if identifier_pattern.fullmatch(factor) and factor not in define_fields:
            issues.append(f"retention factor references undefined field: {factor}")

    if not root.findall(".//treatment[@label='CC']"):
        issues.append("missing required CC treatment definition")

    if issues:
        raise ValueError("invalid ForestModel XML tree: " + "; ".join(issues))


def build_fragments_geodataframe(
    *,
    checkpoint_path: Path,
    au_table: pd.DataFrame,
    tsa_list: Iterable[str],
    fragments_crs: str = DEFAULT_FRAGMENTS_CRS,
    ifm_source_col: str | None = DEFAULT_IFM_SOURCE_COL,
    ifm_threshold: float | None = DEFAULT_IFM_THRESHOLD,
    ifm_target_managed_share: float | None = DEFAULT_IFM_TARGET_MANAGED_SHARE,
    silviculture_config: dict[str, Any] | None = None,
) -> Any:
    """Build Patchworks fragments GeoDataFrame from FEMIC checkpoint output."""
    df = pd.read_feather(checkpoint_path)
    required = {"geometry", "tsa_code", "au", "PROJ_AGE_1"}
    missing = sorted(required.difference(df.columns))
    if missing:
        raise ValueError(
            f"checkpoint missing required columns: {','.join(missing)} "
            f"({checkpoint_path})"
        )
    if "au_id" not in au_table.columns:
        raise ValueError("au_table missing required column: au_id")
    normalized_tsa = {normalize_tsa_code(tsa) for tsa in tsa_list}
    au_ids = set(pd.to_numeric(au_table["au_id"], errors="coerce").dropna().astype(int))
    tsa_mask = df["tsa_code"].map(normalize_tsa_code).isin(normalized_tsa)
    scoped = df.loc[tsa_mask].copy()
    scoped = scoped[scoped["au"].notna()].copy()
    scoped["au"] = scoped["au"].astype(int)
    scoped = scoped[scoped["au"].isin(au_ids)].copy()
    scoped = scoped[scoped["geometry"].notna()].copy()
    scoped["geometry"] = scoped["geometry"].map(_coerce_geometry)
    scoped = scoped[scoped["geometry"].notna()].copy()
    if scoped.empty:
        raise ValueError("no checkpoint rows matched selected TSA/AU export filters")

    if "FEATURE_AREA_SQM" in scoped.columns:
        total_area_ha = (
            pd.to_numeric(scoped["FEATURE_AREA_SQM"], errors="coerce") * 0.0001
        )
    elif "POLYGON_AREA" in scoped.columns:
        total_area_ha = pd.to_numeric(scoped["POLYGON_AREA"], errors="coerce") * 0.0001
    else:
        total_area_ha = None

    if total_area_ha is None:
        gpd = _gpd_module()
        tmp = gpd.GeoDataFrame(scoped, geometry="geometry", crs=fragments_crs)
        total_area_ha = pd.to_numeric(tmp.geometry.area * 0.0001, errors="coerce")
    total_area_ha = (
        pd.to_numeric(total_area_ha, errors="coerce").fillna(0.0).clip(lower=0.0)
    )

    managed_flag = _resolve_managed_flag(
        scoped=scoped,
        ifm_source_col=ifm_source_col,
        ifm_threshold=ifm_threshold,
        ifm_target_managed_share=ifm_target_managed_share,
    )

    age = pd.to_numeric(scoped["PROJ_AGE_1"], errors="coerce").fillna(0).astype(int)
    fragment_ids = np.arange(1, len(scoped) + 1, dtype=int)
    au_values = scoped["au"].astype(int)
    retention_overrides = _resolve_retention_overrides_by_au(
        au_table=au_table,
        silviculture_config=silviculture_config,
    )
    retention_values = np.full(len(scoped), DEFAULT_RETENTION_VALUE, dtype=float)
    for au_id, factor in retention_overrides.items():
        retention_values[au_values == int(au_id)] = float(factor)
    out = pd.DataFrame(
        {
            FRAGMENT_ID_COLUMN: fragment_ids,
            "BLOCK": fragment_ids,
            "AREA_HA": total_area_ha.astype(float),
            "F_AGE": age,
            "AU": au_values,
            "IFM": np.where(managed_flag, "managed", "unmanaged"),
            "ORIGIN": np.where(age <= ORIGIN_PLANTED_MAX_AGE, "planted", "natural"),
            "SILV_STATE": np.where(
                age <= ORIGIN_PLANTED_MAX_AGE,
                DEFAULT_SILV_STATE_PLANTED,
                DEFAULT_SILV_STATE_NATURAL,
            ),
            "RETENTION": retention_values,
            "TSA": scoped["tsa_code"].astype(str),
            "geometry": scoped["geometry"],
        }
    )
    out["AREA_HA"] = pd.to_numeric(out["AREA_HA"], errors="coerce").fillna(0.0)
    gpd = _gpd_module()
    return gpd.GeoDataFrame(out, geometry="geometry", crs=fragments_crs)


def write_fragments_shapefile(*, fragments_gdf: Any, path: Path) -> None:
    """Write fragments shapefile (directory + sidecar files)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    export_gdf = fragments_gdf.copy()
    if FRAGMENT_ID_COLUMN in export_gdf.columns:
        export_gdf = export_gdf.rename(
            columns={FRAGMENT_ID_COLUMN: FRAGMENT_ID_SHAPEFILE_COLUMN}
        )
    export_gdf.to_file(path)


def _resolve_ifm_signal_col(
    *, scoped: pd.DataFrame, ifm_source_col: str | None
) -> str | None:
    if ifm_source_col is not None and ifm_source_col.strip():
        candidate = ifm_source_col.strip()
        if candidate not in scoped.columns:
            raise ValueError(
                f"ifm_source_col {candidate!r} was requested but not found in checkpoint"
            )
        return candidate
    for candidate in IFM_SIGNAL_PRIORITY:
        if candidate in scoped.columns:
            return candidate
    return None


def _resolve_managed_flag(
    *,
    scoped: pd.DataFrame,
    ifm_source_col: str | None,
    ifm_threshold: float | None,
    ifm_target_managed_share: float | None,
) -> pd.Series:
    if ifm_threshold is not None and ifm_target_managed_share is not None:
        raise ValueError(
            "ifm_threshold and ifm_target_managed_share are mutually exclusive"
        )
    signal_col = _resolve_ifm_signal_col(scoped=scoped, ifm_source_col=ifm_source_col)
    if signal_col is None:
        # If no THLB signal exists, default to fully managed.
        return pd.Series(True, index=scoped.index)

    signal = pd.to_numeric(scoped[signal_col], errors="coerce").fillna(0.0)
    if ifm_target_managed_share is not None:
        share = float(ifm_target_managed_share)
        if not 0.0 < share < 1.0:
            raise ValueError("ifm_target_managed_share must be between 0 and 1")
        target_count = int(np.ceil(len(signal) * share))
        managed = pd.Series(False, index=scoped.index)
        if target_count > 0:
            ranked = signal.sort_values(ascending=False, kind="mergesort")
            managed.loc[ranked.index[:target_count]] = True
        return managed

    threshold = float(ifm_threshold) if ifm_threshold is not None else 0.0
    return signal > threshold


def validate_fragments_geodataframe(*, fragments_gdf: Any) -> None:
    """Validate required Patchworks fragments fields and value domains."""
    issues: list[str] = []
    missing_columns = sorted(
        REQUIRED_FRAGMENT_COLUMNS.difference(fragments_gdf.columns)
    )
    if missing_columns:
        issues.append(f"missing required fragments columns: {missing_columns}")
    if fragments_gdf.empty:
        issues.append("fragments dataset is empty")

    if fragments_gdf.crs is None:
        issues.append("fragments CRS is missing")

    if "geometry" in fragments_gdf.columns:
        if fragments_gdf["geometry"].isna().any():
            issues.append("fragments contains null geometry")
        elif fragments_gdf.geometry.is_empty.any():
            issues.append("fragments contains empty geometry")

    for col in (FRAGMENT_ID_COLUMN, "BLOCK", "F_AGE", "AU"):
        if col in fragments_gdf.columns:
            numeric = pd.to_numeric(fragments_gdf[col], errors="coerce")
            if numeric.isna().any():
                issues.append(f"{col} contains non-numeric value(s)")
            elif (numeric < 0).any():
                issues.append(f"{col} contains negative value(s)")

    if FRAGMENT_ID_COLUMN in fragments_gdf.columns:
        fragment_values = pd.to_numeric(
            fragments_gdf[FRAGMENT_ID_COLUMN], errors="coerce"
        )
        if fragment_values.duplicated().any():
            issues.append(f"{FRAGMENT_ID_COLUMN} values must be unique")

    if "BLOCK" in fragments_gdf.columns:
        block_values = pd.to_numeric(fragments_gdf["BLOCK"], errors="coerce")
        if block_values.duplicated().any():
            issues.append("BLOCK values must be unique")

    if "AREA_HA" in fragments_gdf.columns:
        area = pd.to_numeric(fragments_gdf["AREA_HA"], errors="coerce")
        if area.isna().any():
            issues.append("AREA_HA contains non-numeric value(s)")
        elif (area <= 0).any():
            issues.append("AREA_HA must be strictly positive")

    if "IFM" in fragments_gdf.columns:
        ifm_values = set(
            fragments_gdf["IFM"].astype(str).str.strip().str.lower().unique()
        )
        invalid_ifm = sorted(ifm_values.difference(VALID_IFM_VALUES))
        if invalid_ifm:
            issues.append(f"IFM contains invalid values: {invalid_ifm}")

    if "ORIGIN" in fragments_gdf.columns:
        origin_values = set(
            fragments_gdf["ORIGIN"].astype(str).str.strip().str.lower().unique()
        )
        invalid_origin = sorted(origin_values.difference(VALID_ORIGIN_VALUES))
        if invalid_origin:
            issues.append(f"ORIGIN contains invalid values: {invalid_origin}")

    if "SILV_STATE" in fragments_gdf.columns:
        silv_values = set(
            fragments_gdf["SILV_STATE"].astype(str).str.strip().str.lower().unique()
        )
        invalid_silv = sorted(silv_values.difference(VALID_SILV_STATE_VALUES))
        if invalid_silv:
            issues.append(f"SILV_STATE contains invalid values: {invalid_silv}")

    if "RETENTION" in fragments_gdf.columns:
        retention = pd.to_numeric(fragments_gdf["RETENTION"], errors="coerce")
        if retention.isna().any():
            issues.append("RETENTION contains non-numeric value(s)")
        elif ((retention < 0.0) | (retention > 1.0)).any():
            issues.append("RETENTION must be between 0.0 and 1.0")

    if issues:
        raise ValueError("invalid fragments dataset: " + "; ".join(issues))


def export_patchworks_package(
    *,
    bundle_dir: Path,
    checkpoint_path: Path,
    output_dir: Path,
    tsa_list: Iterable[str],
    start_year: int = DEFAULT_START_YEAR,
    horizon_years: int = DEFAULT_HORIZON_YEARS,
    cc_min_age: int = DEFAULT_CC_MIN_AGE,
    cc_max_age: int = DEFAULT_CC_MAX_AGE,
    cc_transition_ifm: str | None = DEFAULT_CC_TRANSITION_IFM,
    fragments_crs: str = DEFAULT_FRAGMENTS_CRS,
    ifm_source_col: str | None = DEFAULT_IFM_SOURCE_COL,
    ifm_threshold: float | None = DEFAULT_IFM_THRESHOLD,
    ifm_target_managed_share: float | None = DEFAULT_IFM_TARGET_MANAGED_SHARE,
    seral_stage_config_path: Path | None = DEFAULT_SERAL_STAGE_CONFIG_PATH,
    silviculture_config_path: Path | None = DEFAULT_SILVICULTURE_CONFIG_PATH,
) -> PatchworksExportResult:
    """Export Patchworks package artifacts from FEMIC outputs."""
    normalized_tsa = sorted({normalize_tsa_code(tsa) for tsa in tsa_list})
    if not normalized_tsa:
        raise ValueError("provide at least one TSA code for Patchworks export")
    context = build_bundle_model_context(
        bundle_dir=bundle_dir,
        tsa_list=normalized_tsa,
    )
    au_table = _context_to_au_table(context)
    seral_stage_config = _load_seral_stage_config(
        seral_stage_config_path=seral_stage_config_path,
    )
    silviculture_config = _load_silviculture_config(
        silviculture_config_path=silviculture_config_path,
    )

    root = build_forestmodel_xml_tree_from_context(
        context=context,
        start_year=start_year,
        horizon_years=horizon_years,
        cc_min_age=cc_min_age,
        cc_max_age=cc_max_age,
        cc_transition_ifm=cc_transition_ifm,
        seral_stage_config=seral_stage_config,
        silviculture_config=silviculture_config,
    )
    validate_forestmodel_xml_tree(root=root)
    forestmodel_path = output_dir / "forestmodel.xml"
    write_forestmodel_xml(root=root, path=forestmodel_path)

    fragments_gdf = build_fragments_geodataframe(
        checkpoint_path=checkpoint_path,
        au_table=au_table,
        tsa_list=normalized_tsa,
        fragments_crs=fragments_crs,
        ifm_source_col=ifm_source_col,
        ifm_threshold=ifm_threshold,
        ifm_target_managed_share=ifm_target_managed_share,
        silviculture_config=silviculture_config,
    )
    validate_fragments_geodataframe(fragments_gdf=fragments_gdf)
    fragments_path = output_dir / "fragments" / "fragments.shp"
    write_fragments_shapefile(fragments_gdf=fragments_gdf, path=fragments_path)

    return PatchworksExportResult(
        forestmodel_xml_path=forestmodel_path,
        fragments_shapefile_path=fragments_path,
        tsa_list=normalized_tsa,
        au_count=int(len(context.analysis_units)),
        fragment_count=int(fragments_gdf.shape[0]),
        curve_count=int(len(root.findall("./curve"))),
    )
