"""Patchworks export helpers (ForestModel XML + fragments shapefile)."""

from __future__ import annotations

from dataclasses import dataclass
import importlib
import math
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
VALID_IFM_VALUES = {"managed", "unmanaged"}
VALID_ORIGIN_VALUES = {"natural", "planted"}
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


def _source_curve_ref(*, curve_id: int, curve_type: str) -> str:
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
    *, au_id: int, managed: bool, origin: str, species: str
) -> str:
    """Build readable deterministic XML id for derived species-yield curves."""
    mode = "managed" if managed else "unmanaged"
    origin_token = _sanitize_id_component(origin)
    species_token = _sanitize_id_component(species)
    return f"au_{int(au_id)}_{mode}_{origin_token}_yield_{species_token}"


def _seral_curve_ref(*, au_id: int, stage: str) -> str:
    return f"au_{int(au_id)}_seral_{_sanitize_id_component(stage)}"


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
) -> ForestModelDefinition:
    """Build Patchworks ForestModel core definition from shared context."""
    curves: dict[str, tuple[CurvePoint, ...]] = {"unity": (CurvePoint(x=0.0, y=1.0),)}
    source_curve_ref_by_id: dict[int, str] = {}
    for curve_id in sorted(context.curves_by_id):
        curve_def = context.curves_by_id[curve_id]
        curve_ref = _source_curve_ref(
            curve_id=curve_def.curve_id,
            curve_type=curve_def.curve_type,
        )
        source_curve_ref_by_id[curve_id] = curve_ref
        curves[curve_ref] = curve_def.points

    selects: list[SelectDefinition] = []
    transition_assignments_list: list[TreatmentAssignment] = [
        TreatmentAssignment(field="ORIGIN", value=_as_quoted_literal("planted"))
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
        unmanaged_curve_id = au.unmanaged_curve_id
        managed_curve_id = au.managed_curve_id
        unmanaged_curve_ref = source_curve_ref_by_id[unmanaged_curve_id]
        managed_curve_ref = source_curve_ref_by_id[managed_curve_id]
        unmanaged_total_curve = context.curves_by_id.get(unmanaged_curve_id)
        managed_total_curve = context.curves_by_id.get(managed_curve_id)
        effective_cc_min_age = int(cc_min_age)
        if managed_total_curve is not None:
            cmai_age, _ = _derive_curve_metrics(
                managed_total_curve_points=managed_total_curve.points,
                horizon_years=horizon_years,
            )
            effective_cc_min_age = int(cmai_age - 20)
        effective_cc_min_age = max(0, min(effective_cc_min_age, int(cc_max_age)))

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
            ]
            managed_attrs = [
                AttributeBinding(label="feature.Area.managed", curve_idref="unity"),
                AttributeBinding(
                    label="feature.Yield.managed.Total",
                    curve_idref=managed_curve_ref,
                ),
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
                        au_id=au.au_id,
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
                        au_id=au.au_id,
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
                curve_ref = _seral_curve_ref(au_id=au.au_id, stage=stage)
                curves[curve_ref] = _build_seral_curve_points(
                    min_age=stage_min,
                    max_age=stage_max,
                    horizon_years=horizon_years,
                    managed_total_curve_points=seral_points,
                )
                feature_labels = (
                    f"feature.Seral.{stage}",
                    f"feature.Seral.{int(au.au_id)}.{stage}",
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
                            label=(f"product.Seral.area.{stage}.{int(au.au_id)}.CC"),
                            curve_idref=curve_ref,
                        )
                    )

        for origin in ORIGIN_ORDER:
            origin_literal = _as_quoted_literal(origin)
            selects.append(
                SelectDefinition(
                    statement=(
                        f"{_au_eq_statement(au.au_id)} and IFM eq 'unmanaged' and ORIGIN eq {origin_literal}"
                    ),
                    feature_attributes=tuple(unmanaged_attrs_by_origin[origin]),
                    include_track=True,
                )
            )
            selects.append(
                SelectDefinition(
                    statement=(
                        f"{_au_eq_statement(au.au_id)} and IFM eq 'managed' and ORIGIN eq {origin_literal}"
                    ),
                    feature_attributes=tuple(managed_attrs_by_origin[origin]),
                    include_track=True,
                    track_treatment=TreatmentDefinition(
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
                    ),
                )
            )
            selects.append(
                SelectDefinition(
                    statement=(
                        f"{_au_eq_statement(au.au_id)} and IFM eq 'managed' and ORIGIN eq {origin_literal} and treatment eq 'CC'"
                    ),
                    product_attributes=tuple(product_attrs_by_origin[origin]),
                )
            )

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


def _append_track(
    *,
    parent: et.Element,
    include_track: bool,
    track_treatment: TreatmentDefinition | None,
) -> None:
    if not include_track and track_treatment is None:
        return
    track = et.SubElement(parent, "track")
    if track_treatment is None:
        return
    treatment = et.SubElement(
        track,
        "treatment",
        {
            "label": track_treatment.label,
            "minage": str(int(track_treatment.min_age)),
            "maxage": str(int(track_treatment.max_age)),
        },
    )
    if not track_treatment.assignments:
        pass
    else:
        produce = et.SubElement(treatment, "produce")
        for assignment in track_treatment.assignments:
            et.SubElement(
                produce,
                "assign",
                {"field": assignment.field, "value": assignment.value},
            )
    if not track_treatment.transition_assignments:
        return
    transition = et.SubElement(treatment, "transition")
    for assignment in track_treatment.transition_assignments:
        et.SubElement(
            transition,
            "assign",
            {"field": assignment.field, "value": assignment.value},
        )


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
        _append_track(
            parent=select_node,
            include_track=select.include_track,
            track_treatment=select.track_treatment,
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
    for field in ("AU", "IFM", "ORIGIN", "treatment"):
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
    out = pd.DataFrame(
        {
            FRAGMENT_ID_COLUMN: fragment_ids,
            "BLOCK": fragment_ids,
            "AREA_HA": total_area_ha.astype(float),
            "F_AGE": age,
            "AU": scoped["au"].astype(int),
            "IFM": np.where(managed_flag, "managed", "unmanaged"),
            "ORIGIN": np.where(age <= ORIGIN_PLANTED_MAX_AGE, "planted", "natural"),
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

    root = build_forestmodel_xml_tree_from_context(
        context=context,
        start_year=start_year,
        horizon_years=horizon_years,
        cc_min_age=cc_min_age,
        cc_max_age=cc_max_age,
        cc_transition_ifm=cc_transition_ifm,
        seral_stage_config=seral_stage_config,
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
