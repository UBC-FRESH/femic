"""Patchworks export helpers (ForestModel XML + fragments shapefile)."""

from __future__ import annotations

import ast
from dataclasses import dataclass, replace
import importlib
from importlib import resources as importlib_resources
import math
import re
from pathlib import Path
from typing import Any, Iterable
import xml.etree.ElementTree as et

import numpy as np
import pandas as pd
import yaml

from femic.user_config import default_femic_recipe_overlay_root
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
    SuccessionDefinition,
    TreatmentAssignment,
    TreatmentDefinition,
)


DEFAULT_START_YEAR = 2026
DEFAULT_HORIZON_YEARS = 300
DEFAULT_FORESTMODEL_DESCRIPTION = "FEMIC Patchworks export"
DEFAULT_INPUT_ATTRIBUTE_BLOCK = "BLOCK"
DEFAULT_INPUT_ATTRIBUTE_AREA = "AREA_HA"
DEFAULT_INPUT_ATTRIBUTE_AGE = "F_AGE"
DEFAULT_INPUT_ATTRIBUTE_EXCLUDE = "BLOCK=0"
DEFAULT_CC_MIN_AGE = 0
DEFAULT_CC_MAX_AGE = 1000
DEFAULT_CC_TRANSITION_IFM: str | None = None
DEFAULT_FRAGMENTS_CRS = "EPSG:3005"
MIN_FRAGMENT_EXPORT_AREA_HA = 1.0e-3
DEFAULT_IFM_MODE = "proportional"
DEFAULT_IFM_SOURCE_COL: str | None = None
DEFAULT_IFM_THRESHOLD: float | None = None
DEFAULT_IFM_TARGET_MANAGED_SHARE: float | None = None
DEFAULT_SERAL_STAGE_CONFIG_PATH: Path | None = None
DEFAULT_SILVICULTURE_CONFIG_PATH: Path | None = None
DEFAULT_LEGACY_INPUT_VARIABLES_CONFIG_PATH: Path | None = None
DEFAULT_RETENTION_VALUE = 0.0
DEFAULT_SILV_STATE_NATURAL = "baseline"
DEFAULT_SILV_STATE_PLANTED = "cc_pl"
DEFAULT_LEGACY_TREATMENT_ELIGIBILITY_FIELD = "treat_inel"
DEFAULT_PASS_THROUGH_SUCCESSION_BREAKUP = "999"
DEFAULT_PASS_THROUGH_SUCCESSION_RENEW = "0"
SUPPORTED_BTC_INDICATOR_BANKS = {"stand-structure-basic", "log-grades"}
STAND_STRUCTURE_BASIC_FEATURE_COLUMNS = (
    ("MAI", "feature.MAI.managed.{au_token}"),
    ("BasalArea000", "feature.BasalArea000.managed.{au_token}"),
    ("DBHg000", "feature.DBHg000.managed.{au_token}"),
    ("SPH000", "feature.SPH000.managed.{au_token}"),
    ("StemCount000", "feature.StemCount000.managed.{au_token}"),
    ("StemCount125", "feature.StemCount125.managed.{au_token}"),
    ("StemCount175", "feature.StemCount175.managed.{au_token}"),
)
LOG_GRADES_EXPLICIT_PRODUCT_COLUMNS = (
    "Logs_Grade_D",
    "Logs_Grade_F",
    "Logs_Grade_H",
    "Logs_Grade_I",
    "Logs_Grade_J",
    "Logs_Grade_U",
    "Logs_Grade_X",
    "Logs_Grade_Y",
)
LOG_GRADES_ALL_PRODUCT_COLUMN = "Logs_Grade_All"
_BTC_INDICATOR_BANK_COMPILE_RECIPES_PACKAGE = "femic.resources.patchworks"
_BTC_INDICATOR_BANK_COMPILE_RECIPES_RESOURCE = "btc_indicator_bank_compile_recipes.yaml"
_LOG_GRADE_PRICE_MATRICES_RESOURCE = "log_grade_price_matrices.yaml"
VALID_IFM_VALUES = {"managed", "unmanaged"}
VALID_IFM_MODES = {"legacy_binary", "proportional"}
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
_LEGACY_EXPRESSION_IDENTIFIER_PATTERN = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*\b")
_LEGACY_EXPRESSION_FUNCTION_PATTERN = re.compile(
    r"^(?P<func>Int|string|Number)\((?P<column>[A-Za-z_][A-Za-z0-9_]*)\)$",
    flags=re.IGNORECASE,
)
_LEGACY_MEMBERSHIP_EXPRESSION_PATTERN = re.compile(
    r"^(?P<left>[A-Za-z_][A-Za-z0-9_]*)\s+in\s+"
    r"(?P<right>[A-Za-z_][A-Za-z0-9_]*|'[^']*'|\"[^\"]*\")$",
    flags=re.IGNORECASE,
)
_LEGACY_EXPRESSION_QUOTED_LITERAL_PATTERN = re.compile(r"'[^']*'|\"[^\"]*\"")
_LEGACY_EXPRESSION_KEYWORDS = {
    "and",
    "area",
    "eq",
    "in",
    "int",
    "not",
    "number",
    "or",
    "string",
}
IFM_SIGNAL_PRIORITY = ("thlb", "thlb_fact", "thlb_area", "thlb_raw")
IFM_PROPORTIONAL_SIGNAL_PRIORITY = ("thlb_fact", "thlb_raw", "thlb_area", "thlb")
SERAL_STAGE_ORDER = (
    "regenerating",
    "young",
    "immature",
    "mature",
    "overmature",
)
OG2_MIN_AGE_ZERO = 249
OG2_MIN_AGE_ONE = 250


def _collapse_subprecision_retention_splits(
    *,
    area_ha: pd.Series,
    ifm_values: pd.Series,
    final_retention: np.ndarray,
    precision_limit_ha: float = MIN_FRAGMENT_EXPORT_AREA_HA,
) -> tuple[pd.Series, np.ndarray]:
    """Collapse managed/unmanaged split parts below Patchworks precision."""

    normalized_ifm = ifm_values.astype(str).copy()
    normalized_retention = np.clip(
        pd.to_numeric(pd.Series(final_retention), errors="coerce")
        .fillna(0.0)
        .to_numpy(dtype=float),
        0.0,
        1.0,
    )
    area_values = (
        pd.to_numeric(area_ha, errors="coerce").fillna(0.0).clip(lower=0.0).to_numpy()
    )
    managed_mask = normalized_ifm.eq("managed").to_numpy(dtype=bool)
    split_mask = (
        managed_mask & (normalized_retention > 0.0) & (normalized_retention < 1.0)
    )
    if not split_mask.any():
        return normalized_ifm, normalized_retention

    managed_area = area_values * (1.0 - normalized_retention)
    unmanaged_area = area_values * normalized_retention
    subprecision_mask = split_mask & (
        (managed_area < precision_limit_ha) | (unmanaged_area < precision_limit_ha)
    )
    if not subprecision_mask.any():
        return normalized_ifm, normalized_retention

    collapse_to_managed = subprecision_mask & (managed_area >= unmanaged_area)
    collapse_to_unmanaged = subprecision_mask & ~collapse_to_managed
    normalized_retention[collapse_to_managed] = 0.0
    normalized_retention[collapse_to_unmanaged] = 0.0
    normalized_ifm.loc[collapse_to_unmanaged] = "unmanaged"
    return normalized_ifm, normalized_retention


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


def _harvested_qmd_numerator_product_label(
    *, au_token: str, treatment_label: str
) -> str:
    treatment_token = _sanitize_id_component(treatment_label).upper()
    return f"product.QMDNumerator.managed.{au_token}.{treatment_token}"


def _harvested_qmd_ratio_account_label(*, au_token: str, treatment_label: str) -> str:
    treatment_token = _sanitize_id_component(treatment_label).upper()
    return f"product.QMD.managed.{au_token}.{treatment_token}"


def _harvested_treated_area_product_label(
    *, au_token: str, treatment_label: str
) -> str:
    treatment_token = _sanitize_id_component(treatment_label).upper()
    return f"product.Treated.managed.{au_token}.{treatment_token}"


def _log_grade_product_label(*, indicator_key: str, treatment_label: str) -> str:
    treatment_token = _sanitize_id_component(treatment_label).upper()
    return f"product.{indicator_key}.managed.Total.{treatment_token}"


def _log_grade_species_product_label(
    *,
    indicator_key: str,
    au_token: str,
    species: str,
    treatment_label: str,
) -> str:
    treatment_token = _sanitize_id_component(treatment_label).upper()
    return f"product.{indicator_key}.managed.{au_token}.{species}.{treatment_token}"


def _log_grade_species_value_product_label(
    *,
    indicator_key: str,
    au_token: str,
    species: str,
    treatment_label: str,
) -> str:
    treatment_token = _sanitize_id_component(treatment_label).upper()
    grade_token = _sanitize_id_component(
        indicator_key.removeprefix("Logs_Grade_") or indicator_key
    ).upper()
    return f"product.Logs_Grade_Value_{grade_token}.managed.{au_token}.{species}.{treatment_token}"


def _load_default_btc_indicator_bank_compile_recipes() -> dict[str, dict[str, Any]]:
    resource = importlib_resources.files(
        _BTC_INDICATOR_BANK_COMPILE_RECIPES_PACKAGE
    ).joinpath(_BTC_INDICATOR_BANK_COMPILE_RECIPES_RESOURCE)
    with resource.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}
    if not isinstance(raw, dict):
        raise ValueError(
            "BTC indicator bank compile recipes must deserialize to a mapping"
        )
    return {
        str(bank).strip(): dict(recipe)
        for bank, recipe in raw.items()
        if str(bank).strip() and isinstance(recipe, dict)
    }


def _merge_nested_mapping(
    base: dict[str, Any],
    override: dict[str, Any],
) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge_nested_mapping(dict(merged[key]), value)
        else:
            merged[key] = value
    return merged


def _load_user_btc_indicator_bank_compile_recipes() -> dict[str, dict[str, Any]]:
    overlay_path = (
        default_femic_recipe_overlay_root()
        / _BTC_INDICATOR_BANK_COMPILE_RECIPES_RESOURCE
    )
    if not overlay_path.exists():
        return {}
    raw = yaml.safe_load(overlay_path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError(
            "User BTC indicator bank compile recipe overlay must deserialize "
            "to a mapping"
        )
    return {
        str(bank).strip(): dict(recipe)
        for bank, recipe in raw.items()
        if str(bank).strip() and isinstance(recipe, dict)
    }


def _load_default_log_grade_price_matrices() -> dict[str, dict[str, Any]]:
    resource = importlib_resources.files(
        _BTC_INDICATOR_BANK_COMPILE_RECIPES_PACKAGE
    ).joinpath(_LOG_GRADE_PRICE_MATRICES_RESOURCE)
    with resource.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}
    if not isinstance(raw, dict):
        raise ValueError("log grade price matrices must deserialize to a mapping")
    return {
        str(matrix_name).strip(): dict(payload)
        for matrix_name, payload in raw.items()
        if str(matrix_name).strip() and isinstance(payload, dict)
    }


def _load_user_log_grade_price_matrices() -> dict[str, dict[str, Any]]:
    overlay_path = (
        default_femic_recipe_overlay_root() / _LOG_GRADE_PRICE_MATRICES_RESOURCE
    )
    if not overlay_path.exists():
        return {}
    raw = yaml.safe_load(overlay_path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError(
            "User log grade price matrix overlay must deserialize to a mapping"
        )
    return {
        str(matrix_name).strip(): dict(payload)
        for matrix_name, payload in raw.items()
        if str(matrix_name).strip() and isinstance(payload, dict)
    }


def _resolve_log_grade_price_matrices() -> dict[str, dict[str, Any]]:
    defaults = _load_default_log_grade_price_matrices()
    user_overlays = _load_user_log_grade_price_matrices()
    resolved: dict[str, dict[str, Any]] = {}
    for matrix_name, payload in defaults.items():
        overlay = user_overlays.get(matrix_name, {})
        resolved[matrix_name] = (
            _merge_nested_mapping(payload, overlay) if overlay else dict(payload)
        )
    for matrix_name, payload in user_overlays.items():
        if matrix_name not in resolved:
            resolved[matrix_name] = dict(payload)
    return resolved


def _resolve_btc_indicator_bank_compile_recipes(
    *,
    silviculture_config: dict[str, Any] | None,
    btc_indicator_bank_names: Iterable[str],
) -> dict[str, dict[str, Any]]:
    defaults = _load_default_btc_indicator_bank_compile_recipes()
    user_overlays = _load_user_btc_indicator_bank_compile_recipes()
    raw_overrides = (silviculture_config or {}).get(
        "btc_indicator_bank_compile_recipes", {}
    ) or {}
    if not isinstance(raw_overrides, dict):
        raise ValueError("btc_indicator_bank_compile_recipes must be a mapping by bank")

    resolved: dict[str, dict[str, Any]] = {}
    for bank_name in btc_indicator_bank_names:
        recipe = dict(defaults.get(bank_name, {}))
        user_overlay = user_overlays.get(bank_name, {})
        if user_overlay:
            recipe = _merge_nested_mapping(recipe, user_overlay)
        override_value = raw_overrides.get(bank_name, {})
        if override_value in (None, {}):
            resolved[bank_name] = recipe
            continue
        if not isinstance(override_value, dict):
            raise ValueError(
                "btc_indicator_bank_compile_recipes entries must be mappings "
                f"(received {type(override_value).__name__} for {bank_name!r})"
            )
        recipe = _merge_nested_mapping(recipe, override_value)
        resolved[bank_name] = recipe
    return resolved


def _resolve_log_grade_product_columns(
    *, compile_recipe: dict[str, Any] | None
) -> tuple[str, ...]:
    recipe = dict(compile_recipe or {})
    raw_emit_columns = recipe.get("emit_columns", LOG_GRADES_EXPLICIT_PRODUCT_COLUMNS)
    if not isinstance(raw_emit_columns, (list, tuple)):
        raise ValueError("log-grades compile recipe emit_columns must be a list/tuple")
    columns: list[str] = []
    for raw_column in raw_emit_columns:
        column = str(raw_column).strip()
        if not column:
            continue
        if (
            column not in LOG_GRADES_EXPLICIT_PRODUCT_COLUMNS
            and column != LOG_GRADES_ALL_PRODUCT_COLUMN
        ):
            raise ValueError(
                f"Unsupported log-grades compile recipe emit_columns entry {column!r}"
            )
        if column not in columns:
            columns.append(column)
    if (
        bool(recipe.get("include_all_grades"))
        and LOG_GRADES_ALL_PRODUCT_COLUMN not in columns
    ):
        columns.append(LOG_GRADES_ALL_PRODUCT_COLUMN)
    return tuple(columns)


def _resolve_log_grade_ratio_scaling_factors(
    *,
    compile_recipe: dict[str, Any] | None,
    denominator_columns: Iterable[str],
    treatment_label: str | None = None,
    silv_state: str | None = None,
) -> dict[str, float]:
    recipe = dict(compile_recipe or {})
    raw_weights = recipe.get("ratio_scaling_factors", {}) or {}
    if not isinstance(raw_weights, dict):
        raise ValueError("log-grades ratio_scaling_factors must be a mapping/object")
    if treatment_label:
        raw_by_treatment = recipe.get("ratio_scaling_factors_by_treatment", {}) or {}
        if not isinstance(raw_by_treatment, dict):
            raise ValueError(
                "log-grades ratio_scaling_factors_by_treatment must be a mapping/object"
            )
        treatment_weights = raw_by_treatment.get(treatment_label, {}) or {}
        if not isinstance(treatment_weights, dict):
            raise ValueError(
                "log-grades ratio_scaling_factors_by_treatment entries must be "
                "mappings/objects"
            )
        raw_weights = {**raw_weights, **treatment_weights}
    if treatment_label and silv_state:
        raw_by_treatment_state = (
            recipe.get("ratio_scaling_factors_by_treatment_and_state", {}) or {}
        )
        if raw_by_treatment_state:
            if not isinstance(raw_by_treatment_state, dict):
                raise ValueError(
                    "log-grades ratio_scaling_factors_by_treatment_and_state must "
                    "be a mapping/object"
                )
            state_map = raw_by_treatment_state.get(treatment_label, {}) or {}
            if state_map and not isinstance(state_map, dict):
                raise ValueError(
                    "log-grades ratio_scaling_factors_by_treatment_and_state "
                    "entries must be mappings/objects"
                )
            normalized_silv_state = str(silv_state).strip()
            treatment_state_weights = state_map.get(normalized_silv_state, {}) or {}
            if (
                not treatment_state_weights
                and normalized_silv_state.lower() != normalized_silv_state
            ):
                treatment_state_weights = (
                    state_map.get(normalized_silv_state.lower(), {}) or {}
                )
            if treatment_state_weights and not isinstance(
                treatment_state_weights, dict
            ):
                raise ValueError(
                    "log-grades ratio_scaling_factors_by_treatment_and_state "
                    "state entries must be mappings/objects"
                )
            raw_weights = {**raw_weights, **treatment_state_weights}

    weights: dict[str, float] = {}
    for column in denominator_columns:
        raw_value = raw_weights.get(column, 1.0)
        try:
            weight = float(raw_value)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"Invalid log-grades ratio scaling factor for {column!r}: {raw_value!r}"
            ) from exc
        if weight < 0.0:
            raise ValueError(
                "log-grades ratio scaling factors must be non-negative "
                f"(received {weight!r} for {column!r})"
            )
        weights[column] = weight
    if not any(weight > 0.0 for weight in weights.values()):
        raise ValueError(
            "log-grades ratio_scaling_factors must leave at least one explicit "
            "grade with a positive weight"
        )
    return weights


def _resolve_log_grade_species_grade_split_recipe(
    *, compile_recipe: dict[str, Any] | None
) -> dict[str, Any]:
    recipe = dict(compile_recipe or {})
    split_recipe = recipe.get("species_grade_split", {}) or {}
    if not isinstance(split_recipe, dict):
        raise ValueError("log-grades species_grade_split must be a mapping/object")
    return dict(split_recipe)


def _resolve_log_grade_price_matrix_name(
    *,
    compile_recipe: dict[str, Any] | None,
    origin: str,
    treatment_label: str,
) -> str | None:
    split_recipe = _resolve_log_grade_species_grade_split_recipe(
        compile_recipe=compile_recipe
    )
    selector = split_recipe.get("price_matrix_selector", {}) or {}
    if not isinstance(selector, dict):
        raise ValueError("log-grades price_matrix_selector must be a mapping/object")
    by_origin_treatment = selector.get("by_origin_treatment", {}) or {}
    if by_origin_treatment:
        if not isinstance(by_origin_treatment, dict):
            raise ValueError(
                "log-grades price_matrix_selector.by_origin_treatment must be a "
                "mapping/object"
            )
        origin_map = by_origin_treatment.get(origin, {}) or {}
        if not isinstance(origin_map, dict):
            raise ValueError(
                "log-grades price_matrix_selector.by_origin_treatment entries must "
                "be mappings/objects"
            )
        matrix_name = str(origin_map.get(treatment_label, "")).strip()
        if matrix_name:
            return matrix_name
    by_origin = selector.get("by_origin", {}) or {}
    if by_origin:
        if not isinstance(by_origin, dict):
            raise ValueError(
                "log-grades price_matrix_selector.by_origin must be a mapping/object"
            )
        matrix_name = str(by_origin.get(origin, "")).strip()
        if matrix_name:
            return matrix_name
    by_treatment = selector.get("by_treatment", {}) or {}
    if by_treatment:
        if not isinstance(by_treatment, dict):
            raise ValueError(
                "log-grades price_matrix_selector.by_treatment must be a mapping/object"
            )
        matrix_name = str(by_treatment.get(treatment_label, "")).strip()
        if matrix_name:
            return matrix_name
    matrix_name = str(selector.get("default", "")).strip()
    return matrix_name or None


def _resolve_log_grade_market_species(
    *,
    compile_recipe: dict[str, Any] | None,
    matrix_name: str,
    species: str,
) -> str | None:
    split_recipe = _resolve_log_grade_species_grade_split_recipe(
        compile_recipe=compile_recipe
    )
    raw_proxy_map = split_recipe.get("species_market_proxies", {}) or {}
    if raw_proxy_map and not isinstance(raw_proxy_map, dict):
        raise ValueError(
            "log-grades species_grade_split.species_market_proxies must be a "
            "mapping/object"
        )
    matrix_proxy_map = raw_proxy_map.get(matrix_name, {}) or {}
    if matrix_proxy_map and not isinstance(matrix_proxy_map, dict):
        raise ValueError(
            "log-grades species_market_proxies entries must be mappings/objects"
        )
    market_species = str(matrix_proxy_map.get(species, "")).strip()
    return market_species or None


def _normalize_margin_to_total(
    *,
    values: dict[str, float],
    target_total: float,
) -> dict[str, float]:
    normalized = {
        key: round(max(0.0, float(value)), 1) for key, value in values.items()
    }
    if not normalized:
        return {}
    positive_keys = [key for key, value in normalized.items() if value > 0.0]
    residual_key = (
        max(positive_keys, key=lambda key: normalized[key])
        if positive_keys
        else next(reversed(normalized))
    )
    residual_value = round(
        max(
            0.0,
            float(target_total)
            - sum(value for key, value in normalized.items() if key != residual_key),
        ),
        1,
    )
    normalized[residual_key] = residual_value
    return normalized


def _build_species_grade_split_curve_points(
    *,
    total_curve_points: tuple[CurvePoint, ...],
    species_curve_points_by_species: dict[str, tuple[CurvePoint, ...]],
    grade_curve_points_by_indicator: dict[str, tuple[CurvePoint, ...]],
) -> dict[tuple[str, str], tuple[CurvePoint, ...]]:
    if (
        not total_curve_points
        or not species_curve_points_by_species
        or not grade_curve_points_by_indicator
    ):
        return {}

    species_list = sorted(species_curve_points_by_species)
    grade_list = tuple(
        indicator_key
        for indicator_key in LOG_GRADES_EXPLICIT_PRODUCT_COLUMNS
        if indicator_key in grade_curve_points_by_indicator
    )
    if not species_list or not grade_list:
        return {}

    split_points: dict[tuple[str, str], list[CurvePoint]] = {
        (species, grade): [] for species in species_list for grade in grade_list
    }
    for total_point in total_curve_points:
        age = float(total_point.x)
        total_value = round(max(0.0, float(total_point.y)), 1)
        if total_value <= 0.0:
            for species in species_list:
                for grade in grade_list:
                    split_points[(species, grade)].append(CurvePoint(x=age, y=0.0))
            continue

        species_totals = _normalize_margin_to_total(
            values={
                species: _curve_value_at_x(
                    points=species_curve_points_by_species[species],
                    x=age,
                )
                for species in species_list
            },
            target_total=total_value,
        )
        grade_totals = _normalize_margin_to_total(
            values={
                grade: _curve_value_at_x(
                    points=grade_curve_points_by_indicator[grade],
                    x=age,
                )
                for grade in grade_list
            },
            target_total=total_value,
        )

        remaining_grade_totals = dict(grade_totals)
        for species_index, species in enumerate(species_list):
            row_remaining = species_totals[species]
            for grade_index, grade in enumerate(grade_list):
                is_last_species = species_index == len(species_list) - 1
                is_last_grade = grade_index == len(grade_list) - 1
                if row_remaining <= 0.0:
                    cell_value = 0.0
                elif is_last_species and is_last_grade:
                    cell_value = round(
                        max(0.0, min(row_remaining, remaining_grade_totals[grade])),
                        1,
                    )
                elif is_last_species:
                    cell_value = round(max(0.0, remaining_grade_totals[grade]), 1)
                elif is_last_grade:
                    cell_value = round(max(0.0, row_remaining), 1)
                else:
                    raw_value = (
                        species_totals[species] * grade_totals[grade] / total_value
                    )
                    cell_value = round(
                        max(
                            0.0,
                            min(
                                raw_value, row_remaining, remaining_grade_totals[grade]
                            ),
                        ),
                        1,
                    )
                split_points[(species, grade)].append(CurvePoint(x=age, y=cell_value))
                row_remaining = round(max(0.0, row_remaining - cell_value), 1)
                remaining_grade_totals[grade] = round(
                    max(0.0, remaining_grade_totals[grade] - cell_value),
                    1,
                )
    return {key: tuple(points) for key, points in split_points.items()}


def _build_value_curve_points(
    *,
    volume_curve_points: tuple[CurvePoint, ...],
    unit_price: float,
) -> tuple[CurvePoint, ...]:
    return tuple(
        CurvePoint(x=float(point.x), y=round(max(0.0, float(point.y)) * unit_price, 2))
        for point in volume_curve_points
    )


def _build_compiled_log_grade_curve_points(
    *,
    source_curve_points: tuple[CurvePoint, ...],
    managed_indicator_curves: dict[str, tuple[CurvePoint, ...]],
    indicator_key: str,
    treatment_label: str,
    silv_state: str | None = None,
    compile_recipe: dict[str, Any] | None = None,
) -> tuple[CurvePoint, ...]:
    recipe = dict(compile_recipe or {})
    if not bool(recipe.get("scale_to_harvested_volume_total", False)):
        return tuple(managed_indicator_curves.get(indicator_key, ()))

    source_indicator_points = tuple(managed_indicator_curves.get(indicator_key, ()))
    if not source_curve_points or not source_indicator_points:
        return ()

    denominator_columns = tuple(
        column
        for column in _resolve_log_grade_product_columns(compile_recipe=recipe)
        if column != LOG_GRADES_ALL_PRODUCT_COLUMN
    )
    if not denominator_columns:
        denominator_columns = LOG_GRADES_EXPLICIT_PRODUCT_COLUMNS
    ratio_weights = _resolve_log_grade_ratio_scaling_factors(
        compile_recipe=recipe,
        denominator_columns=denominator_columns,
        treatment_label=treatment_label,
        silv_state=silv_state,
    )

    out: list[CurvePoint] = []
    for point in source_curve_points:
        age = float(point.x)
        source_total = max(0.0, float(point.y))
        denominator = 0.0
        for column in denominator_columns:
            denominator += (
                max(
                    0.0,
                    float(
                        _interpolate_curve_y(
                            curve_points=tuple(
                                managed_indicator_curves.get(column, ())
                            ),
                            x_value=age,
                        )
                        or 0.0
                    ),
                )
                * ratio_weights[column]
            )
        if denominator <= 0.0 or source_total <= 0.0:
            out.append(CurvePoint(x=age, y=0.0))
            continue
        numerator = max(
            0.0,
            float(
                _interpolate_curve_y(
                    curve_points=source_indicator_points,
                    x_value=age,
                )
                or 0.0
            ),
        )
        if indicator_key != LOG_GRADES_ALL_PRODUCT_COLUMN:
            numerator *= ratio_weights.get(indicator_key, 1.0)
        out.append(
            CurvePoint(
                x=age,
                y=round(source_total * (numerator / denominator), 1),
            )
        )
    return tuple(out)


def _append_log_grade_product_attrs(
    *,
    product_attrs: list[AttributeBinding],
    curves: dict[str, tuple[CurvePoint, ...]],
    managed_indicator_curves: dict[str, tuple[CurvePoint, ...]],
    source_curve_points: tuple[CurvePoint, ...],
    au_token: str,
    treatment_label: str,
    silv_state: str | None = None,
    curve_ref_prefix: str,
    compile_recipe: dict[str, Any] | None = None,
) -> dict[str, tuple[CurvePoint, ...]]:
    built_curves: dict[str, tuple[CurvePoint, ...]] = {}
    for indicator_key in _resolve_log_grade_product_columns(
        compile_recipe=compile_recipe
    ):
        curve_points = _build_compiled_log_grade_curve_points(
            source_curve_points=source_curve_points,
            managed_indicator_curves=managed_indicator_curves,
            indicator_key=indicator_key,
            treatment_label=treatment_label,
            silv_state=silv_state,
            compile_recipe=compile_recipe,
        )
        if not curve_points:
            continue
        curve_ref = (
            f"{curve_ref_prefix}_{au_token}_{_sanitize_id_component(indicator_key)}"
        )
        curves.setdefault(curve_ref, curve_points)
        built_curves[indicator_key] = curve_points
        product_attrs.append(
            AttributeBinding(
                label=_log_grade_product_label(
                    indicator_key=indicator_key,
                    treatment_label=treatment_label,
                ),
                curve_idref=curve_ref,
            )
        )
    return built_curves


def _append_species_log_grade_product_attrs(
    *,
    product_attrs: list[AttributeBinding],
    curves: dict[str, tuple[CurvePoint, ...]],
    total_curve_points: tuple[CurvePoint, ...],
    species_total_curve_points_by_species: dict[str, tuple[CurvePoint, ...]],
    grade_curve_points_by_indicator: dict[str, tuple[CurvePoint, ...]],
    au_token: str,
    origin: str,
    treatment_label: str,
    curve_ref_prefix: str,
    compile_recipe: dict[str, Any] | None,
    log_grade_price_matrices: dict[str, dict[str, Any]],
) -> None:
    split_recipe = _resolve_log_grade_species_grade_split_recipe(
        compile_recipe=compile_recipe
    )
    if not bool(split_recipe.get("enabled", False)):
        return

    split_curves = _build_species_grade_split_curve_points(
        total_curve_points=total_curve_points,
        species_curve_points_by_species=species_total_curve_points_by_species,
        grade_curve_points_by_indicator=grade_curve_points_by_indicator,
    )
    if not split_curves:
        return

    matrix_name = _resolve_log_grade_price_matrix_name(
        compile_recipe=compile_recipe,
        origin=origin,
        treatment_label=treatment_label,
    )
    matrix_payload = (
        log_grade_price_matrices.get(matrix_name, {}) if matrix_name is not None else {}
    )
    matrix_species_payload = matrix_payload.get("species", {}) or {}
    if matrix_species_payload and not isinstance(matrix_species_payload, dict):
        raise ValueError(
            f"log grade price matrix {matrix_name!r} species payload must be a "
            "mapping/object"
        )
    emit_value_products = bool(split_recipe.get("emit_value_products", False))

    for species, indicator_key in sorted(split_curves):
        curve_points = split_curves[(species, indicator_key)]
        if not curve_points:
            continue
        curve_ref = (
            f"{curve_ref_prefix}_{au_token}_{_sanitize_id_component(species)}_"
            f"{_sanitize_id_component(indicator_key)}"
        )
        curves.setdefault(curve_ref, curve_points)
        product_attrs.append(
            AttributeBinding(
                label=_log_grade_species_product_label(
                    indicator_key=indicator_key,
                    au_token=au_token,
                    species=species,
                    treatment_label=treatment_label,
                ),
                curve_idref=curve_ref,
            )
        )
        if not emit_value_products:
            continue
        market_species = (
            _resolve_log_grade_market_species(
                compile_recipe=compile_recipe,
                matrix_name=matrix_name,
                species=species,
            )
            if matrix_name is not None
            else None
        )
        if not market_species:
            continue
        market_species_payload = matrix_species_payload.get(market_species, {}) or {}
        if market_species_payload and not isinstance(market_species_payload, dict):
            raise ValueError(
                f"log grade price matrix {matrix_name!r} species entry {market_species!r} "
                "must be a mapping/object"
            )
        try:
            unit_price = float(market_species_payload.get(indicator_key, 0.0) or 0.0)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"Invalid price for {matrix_name!r} {market_species!r} "
                f"{indicator_key!r}: {market_species_payload.get(indicator_key)!r}"
            ) from exc
        value_curve_points = _build_value_curve_points(
            volume_curve_points=curve_points,
            unit_price=unit_price,
        )
        value_curve_ref = f"{curve_ref}_value"
        curves.setdefault(value_curve_ref, value_curve_points)
        product_attrs.append(
            AttributeBinding(
                label=_log_grade_species_value_product_label(
                    indicator_key=indicator_key,
                    au_token=au_token,
                    species=species,
                    treatment_label=treatment_label,
                ),
                curve_idref=value_curve_ref,
            )
        )


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


def _load_legacy_input_variables_config(
    *,
    legacy_input_variables_config_path: Path | None,
) -> dict[str, Any] | None:
    if legacy_input_variables_config_path is None:
        return None
    resolved = legacy_input_variables_config_path.expanduser().resolve()
    if not resolved.exists():
        raise FileNotFoundError(f"legacy input-variables config not found: {resolved}")
    payload = yaml.safe_load(resolved.read_text(encoding="utf-8"))
    if payload is None:
        return {}
    if not isinstance(payload, dict):
        raise ValueError(
            "legacy input-variables config must contain a top-level "
            f"mapping/object (found {type(payload).__name__})"
        )
    description = payload.get("description")
    if description is not None and not isinstance(description, str):
        raise ValueError("legacy input-variables field description must be a string")
    start_year = payload.get("start_year")
    if start_year is not None and not isinstance(start_year, int):
        raise ValueError("legacy input-variables field start_year must be an integer")
    horizon_years = payload.get("horizon_years")
    if horizon_years is not None and not isinstance(horizon_years, int):
        raise ValueError(
            "legacy input-variables field horizon_years must be an integer"
        )
    staged = payload.get("staged")
    if staged is not None and not isinstance(staged, dict):
        raise ValueError("legacy input-variables field staged must be a mapping/object")
    if isinstance(staged, dict):
        for field_name in (
            "exclude_expression",
            "unique_record_label_expression",
            "polygon_area_expression",
            "stand_age_expression",
            "treatment_eligibility_expression",
        ):
            raw_value = staged.get(field_name)
            if raw_value is not None and not isinstance(raw_value, str):
                raise ValueError(
                    f"legacy input-variables field staged.{field_name} must be a string"
                )
        raw_additional_columns = staged.get("additional_stratification_columns")
        if raw_additional_columns is not None:
            if not isinstance(raw_additional_columns, list):
                raise ValueError(
                    "legacy input-variables field staged.additional_stratification_columns "
                    "must be a list"
                )
            for index, item in enumerate(raw_additional_columns):
                if not isinstance(item, dict):
                    raise ValueError(
                        "legacy input-variables field "
                        f"staged.additional_stratification_columns[{index}] "
                        "must be a mapping/object"
                    )
                key = item.get("key")
                source_expression = item.get("source_expression")
                if not isinstance(key, str) or not key.strip():
                    raise ValueError(
                        "legacy input-variables field "
                        f"staged.additional_stratification_columns[{index}].key "
                        "must be a non-empty string"
                    )
                if (
                    not isinstance(source_expression, str)
                    or not source_expression.strip()
                ):
                    raise ValueError(
                        "legacy input-variables field "
                        f"staged.additional_stratification_columns[{index}].source_expression "
                        "must be a non-empty string"
                    )
        raw_constants = staged.get("constants")
        if raw_constants is not None and not isinstance(raw_constants, dict):
            raise ValueError(
                "legacy input-variables field staged.constants must be a mapping/object"
            )
        raw_constant_contract = staged.get("constant_contract")
        if raw_constant_contract is not None:
            if not isinstance(raw_constant_contract, list):
                raise ValueError(
                    "legacy input-variables field staged.constant_contract must be a list"
                )
            for index, item in enumerate(raw_constant_contract):
                if not isinstance(item, dict):
                    raise ValueError(
                        "legacy input-variables field "
                        f"staged.constant_contract[{index}] must be a mapping/object"
                    )
                key = item.get("key")
                status = item.get("status")
                if not isinstance(key, str) or not key.strip():
                    raise ValueError(
                        "legacy input-variables field "
                        f"staged.constant_contract[{index}].key must be a non-empty string"
                    )
                if not isinstance(status, str) or not status.strip():
                    raise ValueError(
                        "legacy input-variables field "
                        f"staged.constant_contract[{index}].status "
                        "must be a non-empty string"
                    )
    return payload


def _legacy_input_variables_staged_mapping(
    legacy_input_variables_config: dict[str, Any] | None,
) -> dict[str, Any]:
    if legacy_input_variables_config is None:
        return {}
    staged = legacy_input_variables_config.get("staged")
    return dict(staged) if isinstance(staged, dict) else {}


def _normalize_optional_expression(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_legacy_constant_literal(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        if len(text) >= 2 and text[0] == text[-1] and text[0] in {"'", '"'}:
            return text[1:-1]
        if text.startswith("="):
            return _evaluate_legacy_constant_formula(text)
        return text
    return value


def _format_legacy_define_constant_value(value: Any) -> str | None:
    normalized = _normalize_optional_expression(value)
    if normalized is None:
        return None
    if re.fullmatch(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)", normalized):
        return normalized
    if (
        len(normalized) >= 2
        and normalized[0] == normalized[-1]
        and normalized[0] == "'"
    ):
        return normalized
    escaped = normalized.replace("'", "''")
    return f"'{escaped}'"


def _evaluate_legacy_constant_formula(expression: str) -> str:
    text = str(expression).strip()
    if not text.startswith("="):
        return text
    parsed = ast.parse(text[1:], mode="eval")

    def _evaluate(node: ast.AST) -> float:
        if isinstance(node, ast.Expression):
            return _evaluate(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return float(node.value)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            value = _evaluate(node.operand)
            return value if isinstance(node.op, ast.UAdd) else -value
        if isinstance(node, ast.BinOp) and isinstance(
            node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div)
        ):
            left = _evaluate(node.left)
            right = _evaluate(node.right)
            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Sub):
                return left - right
            if isinstance(node.op, ast.Mult):
                return left * right
            return left / right
        raise ValueError(f"unsupported legacy constant formula {expression!r}")

    value = _evaluate(parsed)
    return format(value, ".15g")


def _legacy_expression_is_area_ha(expression: str) -> bool:
    normalized = re.sub(r"\s+", "", str(expression).strip()).lower()
    return normalized == "area()/10000"


def _extract_legacy_expression_source_columns(
    expression: str | None,
) -> tuple[str, ...]:
    if expression is None:
        return ()
    text = str(expression).strip()
    if not text or _legacy_expression_is_area_ha(text):
        return ()
    cleaned = _LEGACY_EXPRESSION_QUOTED_LITERAL_PATTERN.sub(" ", text)
    columns: list[str] = []
    for token in _LEGACY_EXPRESSION_IDENTIFIER_PATTERN.findall(cleaned):
        if token.lower() in _LEGACY_EXPRESSION_KEYWORDS:
            continue
        if token not in columns:
            columns.append(token)
    return tuple(columns)


def _evaluate_legacy_export_expression(
    *,
    expression: str,
    scoped: pd.DataFrame,
    area_ha: pd.Series,
) -> pd.Series:
    text = str(expression).strip()
    if not text:
        raise ValueError("legacy export expression must not be blank")
    if _legacy_expression_is_area_ha(text):
        return pd.to_numeric(area_ha, errors="coerce").fillna(0.0)
    func_match = _LEGACY_EXPRESSION_FUNCTION_PATTERN.fullmatch(text)
    if func_match is not None:
        column_name = str(func_match.group("column"))
        func_name = str(func_match.group("func")).lower()
        if column_name not in scoped.columns:
            raise ValueError(
                f"legacy export expression references missing checkpoint column "
                f"{column_name!r}"
            )
        series = scoped[column_name]
        if func_name in {"int", "number"}:
            return pd.to_numeric(series, errors="coerce")
        if func_name == "string":
            return series.astype(str)
    if text in scoped.columns:
        return scoped[text]
    raise ValueError(
        f"unsupported legacy export expression {expression!r}; "
        "expected area()/10000, <COLUMN>, or Int(<COLUMN>)/Number(<COLUMN>)/string(<COLUMN>)"
    )


def _build_live_legacy_input_attribute_contract(
    *,
    legacy_input_variables_config: dict[str, Any] | None,
) -> tuple[dict[str, str], tuple[str, ...]]:
    staged = _legacy_input_variables_staged_mapping(legacy_input_variables_config)
    block_expression = _normalize_optional_expression(
        staged.get("unique_record_label_expression")
    )
    area_expression = _normalize_optional_expression(
        staged.get("polygon_area_expression")
    )
    age_expression = _normalize_optional_expression(staged.get("stand_age_expression"))
    exclude_expression = _normalize_optional_expression(
        staged.get("exclude_expression")
    )
    input_attributes = {
        "block": block_expression or DEFAULT_INPUT_ATTRIBUTE_BLOCK,
        "area": area_expression or DEFAULT_INPUT_ATTRIBUTE_AREA,
        "age": age_expression or DEFAULT_INPUT_ATTRIBUTE_AGE,
        "exclude": exclude_expression or DEFAULT_INPUT_ATTRIBUTE_EXCLUDE,
    }
    required_columns: list[str] = []
    for expression in (
        block_expression,
        area_expression,
        age_expression,
        exclude_expression,
    ):
        for column_name in _extract_legacy_expression_source_columns(expression):
            if column_name not in required_columns:
                required_columns.append(column_name)
    return input_attributes, tuple(required_columns)


def _build_live_legacy_additional_stratification_contract(
    *,
    legacy_input_variables_config: dict[str, Any] | None,
) -> tuple[tuple[tuple[str, str], ...], tuple[str, ...]]:
    staged = _legacy_input_variables_staged_mapping(legacy_input_variables_config)
    raw_columns = staged.get("additional_stratification_columns")
    if not isinstance(raw_columns, list):
        return (), ()
    live_columns: list[tuple[str, str]] = []
    required_columns: list[str] = []
    for item in raw_columns:
        if not isinstance(item, dict):
            continue
        key = str(item.get("key", "")).strip()
        source_expression = _normalize_optional_expression(
            item.get("source_expression")
        )
        if not key or source_expression is None:
            continue
        live_columns.append((key, source_expression))
        for column_name in _extract_legacy_expression_source_columns(source_expression):
            if column_name not in required_columns:
                required_columns.append(column_name)
    return tuple(live_columns), tuple(required_columns)


def _build_legacy_define_column_contract(
    *,
    legacy_input_variables_config: dict[str, Any] | None,
) -> tuple[tuple[tuple[str, str], ...], tuple[str, ...]]:
    staged = _legacy_input_variables_staged_mapping(legacy_input_variables_config)
    raw_columns = staged.get("additional_stratification_columns")
    if not isinstance(raw_columns, list):
        return (), ()
    live_columns: list[tuple[str, str]] = []
    required_fields: list[str] = []
    for item in raw_columns:
        if not isinstance(item, dict):
            continue
        key = str(item.get("key", "")).strip()
        source_expression = _normalize_optional_expression(
            item.get("source_expression")
        )
        if not key or source_expression is None:
            continue
        live_columns.append((key, source_expression))
    return tuple(live_columns), tuple(required_fields)


def _build_live_legacy_constants_contract(
    *,
    legacy_input_variables_config: dict[str, Any] | None,
) -> dict[str, Any]:
    staged = _legacy_input_variables_staged_mapping(legacy_input_variables_config)
    raw_constants = staged.get("constants")
    if not isinstance(raw_constants, dict):
        return {}
    raw_constant_contract = staged.get("constant_contract")
    live_constant_keys: set[str] | None = None
    if isinstance(raw_constant_contract, list):
        live_constant_keys = {
            str(item.get("key", "")).strip()
            for item in raw_constant_contract
            if isinstance(item, dict)
            and str(item.get("status", "")).strip()
            in {"live_export", "live_build_input"}
            and str(item.get("key", "")).strip()
        }
    return {
        str(key).strip(): _normalize_legacy_constant_literal(value)
        for key, value in raw_constants.items()
        if str(key).strip()
        and (live_constant_keys is None or str(key).strip() in live_constant_keys)
    }


def _resolve_legacy_treatment_expression_operand(
    *,
    token: str,
    scoped: pd.DataFrame,
    exported: pd.DataFrame,
    legacy_constants: dict[str, Any],
) -> pd.Series | Any:
    normalized = str(token).strip()
    if (
        len(normalized) >= 2
        and normalized[0] == normalized[-1]
        and normalized[0] in {"'", '"'}
    ):
        return normalized[1:-1]
    if normalized in exported.columns:
        return exported[normalized]
    if normalized in scoped.columns:
        return scoped[normalized]
    if normalized in legacy_constants:
        return legacy_constants[normalized]
    raise ValueError(
        "legacy treatment eligibility expression references unresolved symbol "
        f"{normalized!r}"
    )


def _evaluate_legacy_treatment_eligibility_expression(
    *,
    expression: str,
    scoped: pd.DataFrame,
    exported: pd.DataFrame,
    legacy_constants: dict[str, Any],
) -> pd.Series:
    text = str(expression).strip()
    if not text:
        raise ValueError("legacy treatment eligibility expression must not be blank")
    membership_match = _LEGACY_MEMBERSHIP_EXPRESSION_PATTERN.fullmatch(text)
    if membership_match is None:
        raise ValueError(
            "unsupported legacy treatment eligibility expression "
            f"{expression!r}; expected <field> in <constant_or_literal>"
        )
    left_operand = _resolve_legacy_treatment_expression_operand(
        token=str(membership_match.group("left")),
        scoped=scoped,
        exported=exported,
        legacy_constants=legacy_constants,
    )
    right_operand = _resolve_legacy_treatment_expression_operand(
        token=str(membership_match.group("right")),
        scoped=scoped,
        exported=exported,
        legacy_constants=legacy_constants,
    )
    if not isinstance(left_operand, pd.Series):
        left_operand = pd.Series([left_operand] * len(exported), index=exported.index)
    if isinstance(right_operand, pd.Series):
        right_series = right_operand.reindex(exported.index)
    else:
        right_series = pd.Series([right_operand] * len(exported), index=exported.index)
    left_series = left_operand.reindex(exported.index)
    return left_series.astype(str) == right_series.astype(str)


def _resolve_legacy_additional_export_field_name(
    *,
    requested_key: str,
    used_names: set[str],
) -> str:
    candidate = str(requested_key).strip()
    if not candidate:
        raise ValueError(
            "legacy additional stratification column key must not be blank"
        )
    if len(candidate) > 10:
        candidate = candidate[:10]
    if candidate.casefold() not in used_names:
        used_names.add(candidate.casefold())
        return candidate
    suffix_index = 1
    while True:
        suffix = f"_{suffix_index}"
        stem = candidate[: max(0, 10 - len(suffix))]
        resolved = f"{stem}{suffix}"
        if resolved.casefold() not in used_names:
            used_names.add(resolved.casefold())
            return resolved
        suffix_index += 1


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


def _resolve_btc_indicator_bank_names(
    *, silviculture_config: dict[str, Any] | None
) -> tuple[str, ...]:
    if not silviculture_config:
        return ()
    raw_value = silviculture_config.get("btc_indicator_banks", ())
    if raw_value is None:
        return ()
    if not isinstance(raw_value, (list, tuple)):
        raise ValueError("btc_indicator_banks must be a list/tuple of bank names")
    seen: set[str] = set()
    out: list[str] = []
    for item in raw_value:
        bank = str(item).strip()
        if not bank:
            continue
        if bank not in SUPPORTED_BTC_INDICATOR_BANKS:
            raise ValueError(
                "Unsupported btc_indicator_banks entry "
                f"{bank!r}; expected one of {sorted(SUPPORTED_BTC_INDICATOR_BANKS)}"
            )
        if bank not in seen:
            seen.add(bank)
            out.append(bank)
    return tuple(out)


DEFAULT_QMD_CONE_FORM_FACTOR = 1.1
DEFAULT_QMD_SITE_INDEX_BY_LEVEL = {"L": 15.0, "M": 25.0, "H": 35.0}


def _interpolate_curve_y(
    *,
    curve_points: tuple[CurvePoint, ...],
    x_value: float,
) -> float | None:
    if not curve_points:
        return None
    if x_value <= float(curve_points[0].x):
        return float(curve_points[0].y)
    if x_value >= float(curve_points[-1].x):
        return float(curve_points[-1].y)
    for left, right in zip(curve_points, curve_points[1:]):
        x0 = float(left.x)
        x1 = float(right.x)
        if x0 <= x_value <= x1 and x1 > x0:
            y0 = float(left.y)
            y1 = float(right.y)
            fraction = (x_value - x0) / (x1 - x0)
            return y0 + (fraction * (y1 - y0))
    return None


def _estimate_qmd_height_m(
    *,
    age: float,
    site_index: float | None,
    height_curve_points: tuple[CurvePoint, ...],
) -> float:
    height_from_curve = _interpolate_curve_y(
        curve_points=height_curve_points,
        x_value=age,
    )
    if height_from_curve is not None and height_from_curve > 0.0:
        return float(height_from_curve)
    if site_index is None or site_index <= 0.0:
        return 0.0
    return max(0.0, (float(site_index) / 50.0) * float(age))


def _estimate_qmd_stems_per_ha(
    *,
    age: float,
    tph_curve_points: tuple[CurvePoint, ...],
    stems_per_ha: float | None,
) -> float:
    tph_from_curve = _interpolate_curve_y(
        curve_points=tph_curve_points,
        x_value=age,
    )
    if tph_from_curve is not None and tph_from_curve > 0.0:
        return float(tph_from_curve)
    if stems_per_ha is None:
        return 0.0
    return max(0.0, float(stems_per_ha))


def _estimate_qmd_cm_from_volume(
    *,
    stand_volume_m3_per_ha: float,
    height_m: float,
    stems_per_ha: float,
    cone_form_factor: float = DEFAULT_QMD_CONE_FORM_FACTOR,
) -> float:
    if (
        stand_volume_m3_per_ha <= 0.0
        or height_m <= 0.0
        or stems_per_ha <= 0.0
        or cone_form_factor <= 0.0
    ):
        return 0.0
    tree_volume_m3 = float(stand_volume_m3_per_ha) / float(stems_per_ha)
    diameter_m = math.sqrt(
        (12.0 * tree_volume_m3) / (float(cone_form_factor) * math.pi * float(height_m))
    )
    return max(0.0, diameter_m * 100.0)


def _estimate_qmd_cm_from_basal_area(
    *,
    basal_area_m2_per_ha: float,
    stems_per_ha: float,
) -> float:
    if basal_area_m2_per_ha <= 0.0 or stems_per_ha <= 0.0:
        return 0.0
    diameter_cm = math.sqrt(
        (float(basal_area_m2_per_ha) * 40000.0) / (math.pi * float(stems_per_ha))
    )
    return max(0.0, diameter_cm)


def _build_qmd_curve_points(
    *,
    source_curve_points: tuple[CurvePoint, ...],
    si_level: str,
    site_index: float | None = None,
    height_curve_points: tuple[CurvePoint, ...] = (),
    tph_curve_points: tuple[CurvePoint, ...] = (),
    stems_per_ha: float | None = None,
    direct_diameter_curve_points: tuple[CurvePoint, ...] = (),
    basal_area_curve_points: tuple[CurvePoint, ...] = (),
    stand_structure_stems_curve_points: tuple[CurvePoint, ...] = (),
    response_age: int | None = None,
    response_fraction: float = 0.0,
    response_years: int = 10,
    cone_form_factor: float = DEFAULT_QMD_CONE_FORM_FACTOR,
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
    resolved_site_index = (
        float(site_index)
        if site_index is not None and math.isfinite(float(site_index))
        else DEFAULT_QMD_SITE_INDEX_BY_LEVEL.get(str(si_level).strip().upper(), 25.0)
    )
    source_y_by_age = {float(point.x): float(point.y) for point in source_curve_points}
    out: list[CurvePoint] = []
    for x_val in x_values:
        age = max(0.0, float(x_val))
        stand_volume = max(0.0, float(source_y_by_age.get(x_val, 0.0)))
        qmd = _interpolate_curve_y(
            curve_points=direct_diameter_curve_points,
            x_value=age,
        )
        if qmd is None or qmd <= 0.0:
            basal_area = _interpolate_curve_y(
                curve_points=basal_area_curve_points,
                x_value=age,
            )
            stand_structure_stems = _interpolate_curve_y(
                curve_points=stand_structure_stems_curve_points,
                x_value=age,
            )
            if (
                basal_area is not None
                and basal_area > 0.0
                and stand_structure_stems is not None
                and stand_structure_stems > 0.0
            ):
                qmd = _estimate_qmd_cm_from_basal_area(
                    basal_area_m2_per_ha=basal_area,
                    stems_per_ha=stand_structure_stems,
                )
            else:
                height_m = _estimate_qmd_height_m(
                    age=age,
                    site_index=resolved_site_index,
                    height_curve_points=height_curve_points,
                )
                tph = _estimate_qmd_stems_per_ha(
                    age=age,
                    tph_curve_points=tph_curve_points,
                    stems_per_ha=stems_per_ha,
                )
                qmd = _estimate_qmd_cm_from_volume(
                    stand_volume_m3_per_ha=stand_volume,
                    height_m=height_m,
                    stems_per_ha=tph,
                    cone_form_factor=cone_form_factor,
                )
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


def _build_stems_per_ha_curve_points(
    *,
    source_curve_points: tuple[CurvePoint, ...],
    tph_curve_points: tuple[CurvePoint, ...] = (),
    stems_per_ha: float | None = None,
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
    out: list[CurvePoint] = []
    for x_val in x_values:
        stems = _estimate_qmd_stems_per_ha(
            age=float(x_val),
            tph_curve_points=tph_curve_points,
            stems_per_ha=stems_per_ha,
        )
        out.append(CurvePoint(x=float(x_val), y=round(max(0.0, stems), 1)))
    return tuple(out)


def _build_height_curve_points(
    *,
    source_curve_points: tuple[CurvePoint, ...],
    si_level: str,
    site_index: float | None = None,
    height_curve_points: tuple[CurvePoint, ...] = (),
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
    resolved_site_index = (
        float(site_index)
        if site_index is not None and math.isfinite(float(site_index))
        else DEFAULT_QMD_SITE_INDEX_BY_LEVEL.get(str(si_level).strip().upper(), 25.0)
    )
    out: list[CurvePoint] = []
    for x_val in x_values:
        height_m = _estimate_qmd_height_m(
            age=float(x_val),
            site_index=resolved_site_index,
            height_curve_points=height_curve_points,
        )
        out.append(CurvePoint(x=float(x_val), y=round(max(0.0, height_m), 1)))
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


def _build_curve_with_post_transition_multiplier(
    *,
    source_curve_points: tuple[CurvePoint, ...],
    transition_age: int,
    multiplier: float,
) -> tuple[CurvePoint, ...]:
    out: list[CurvePoint] = []
    transition_age = int(transition_age)
    multiplier = max(0.0, float(multiplier))
    for point in source_curve_points:
        x_val = float(point.x)
        y_val = float(point.y)
        if x_val >= float(transition_age):
            y_val *= multiplier
        out.append(CurvePoint(x=x_val, y=max(0.0, round(y_val, 1))))
    return tuple(out)


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
    forestmodel_description: str = DEFAULT_FORESTMODEL_DESCRIPTION,
    input_attributes: dict[str, str] | None = None,
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
        forestmodel_description=forestmodel_description,
        input_attributes=input_attributes,
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
    forestmodel_description: str = DEFAULT_FORESTMODEL_DESCRIPTION,
    input_attributes: dict[str, str] | None = None,
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
        forestmodel_description=forestmodel_description,
        input_attributes=input_attributes,
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
    forestmodel_description: str = DEFAULT_FORESTMODEL_DESCRIPTION,
    input_attributes: dict[str, str] | None = None,
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
    btc_indicator_bank_names = _resolve_btc_indicator_bank_names(
        silviculture_config=silviculture_config
    )
    btc_indicator_bank_compile_recipes = _resolve_btc_indicator_bank_compile_recipes(
        silviculture_config=silviculture_config,
        btc_indicator_bank_names=btc_indicator_bank_names,
    )
    log_grade_price_matrices = _resolve_log_grade_price_matrices()
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
        qmd_harvested_product_accounts_enabled = isinstance(qmd_payload, dict) and bool(
            qmd_payload.get("harvested_product_accounts_enabled", False)
        )
        qmd_support = context.qmd_support_by_au.get(int(au.au_id))
        height_payload = (silviculture_config or {}).get("height")
        height_enabled = isinstance(height_payload, dict) and bool(
            height_payload.get("enabled", False)
        )
        stems_payload = (silviculture_config or {}).get("stems_per_ha")
        stems_per_ha_enabled = isinstance(stems_payload, dict) and bool(
            stems_payload.get("enabled", False)
        )
        managed_indicator_curves = context.managed_indicator_curves_by_au.get(
            int(au.au_id), {}
        )
        managed_native_qmd_curve_points = tuple(
            managed_indicator_curves.get("DBHg000", ())
        )
        managed_native_basal_area_curve_points = tuple(
            managed_indicator_curves.get("BasalArea000", ())
        )
        managed_native_stems_curve_points = tuple(
            managed_indicator_curves.get("SPH000")
            or managed_indicator_curves.get("StemCount000")
            or ()
        )

        natural_species_curve_map = context.unmanaged_species_curve_ids.get(
            unmanaged_curve_id, {}
        )
        planted_species_curve_map = context.managed_species_curve_ids.get(
            managed_curve_id, {}
        )
        natural_species_has_any_signal = any(
            (curve_def is not None and _curve_has_positive_signal(curve_def.points))
            for curve_def in (
                context.curves_by_id.get(curve_id)
                for curve_id in natural_species_curve_map.values()
            )
        )
        planted_species_has_any_signal = any(
            (curve_def is not None and _curve_has_positive_signal(curve_def.points))
            for curve_def in (
                context.curves_by_id.get(curve_id)
                for curve_id in planted_species_curve_map.values()
            )
        )
        if not natural_species_has_any_signal:
            natural_species_curve_map = planted_species_curve_map
        if not planted_species_has_any_signal:
            planted_species_curve_map = natural_species_curve_map

        species_curve_maps_by_origin = {
            "natural": natural_species_curve_map,
            "planted": planted_species_curve_map,
        }
        unmanaged_attrs_by_origin: dict[str, list[AttributeBinding]] = {}
        managed_attrs_by_origin: dict[str, list[AttributeBinding]] = {}
        product_attrs_by_origin: dict[str, list[AttributeBinding]] = {}
        unmanaged_height_curve_ref: str | None = None
        managed_height_curve_ref: str | None = None
        unmanaged_stems_curve_ref: str | None = None
        managed_stems_curve_ref: str | None = None
        unmanaged_height_curve_points: tuple[CurvePoint, ...] = ()
        managed_height_curve_points: tuple[CurvePoint, ...] = ()
        unmanaged_stems_curve_points: tuple[CurvePoint, ...] = ()
        managed_stems_curve_points: tuple[CurvePoint, ...] = ()

        if height_enabled:
            unmanaged_height_source = (
                unmanaged_total_curve.points
                if unmanaged_total_curve is not None
                else og_source_points
            )
            managed_height_source = (
                managed_total_curve.points
                if managed_total_curve is not None
                else unmanaged_height_source
            )
            site_index = (
                float(qmd_support.site_index)
                if qmd_support is not None and qmd_support.site_index is not None
                else None
            )
            managed_height_support_points = (
                tuple(qmd_support.managed_height_points)
                if qmd_support is not None
                else ()
            )
            unmanaged_height_curve_ref = f"au_{au_token}_unmanaged_height"
            unmanaged_height_curve_points = _build_height_curve_points(
                source_curve_points=unmanaged_height_source,
                si_level=au.si_level,
                site_index=site_index,
            )
            curves[unmanaged_height_curve_ref] = unmanaged_height_curve_points
            managed_height_curve_ref = f"au_{au_token}_managed_height"
            managed_height_curve_points = _build_height_curve_points(
                source_curve_points=managed_height_source,
                si_level=au.si_level,
                site_index=site_index,
                height_curve_points=managed_height_support_points,
            )
            curves[managed_height_curve_ref] = managed_height_curve_points

        if stems_per_ha_enabled:
            unmanaged_stems_source = (
                unmanaged_total_curve.points
                if unmanaged_total_curve is not None
                else og_source_points
            )
            managed_stems_source = (
                managed_total_curve.points
                if managed_total_curve is not None
                else unmanaged_stems_source
            )
            unmanaged_fallback_stems_per_ha = (
                float(qmd_support.unmanaged_stems_per_ha)
                if qmd_support is not None
                and qmd_support.unmanaged_stems_per_ha is not None
                else None
            )
            managed_fallback_stems_per_ha = (
                float(qmd_support.managed_stems_per_ha)
                if qmd_support is not None
                and qmd_support.managed_stems_per_ha is not None
                else None
            )
            managed_tph_points = (
                tuple(qmd_support.managed_tph_points) if qmd_support is not None else ()
            )
            if unmanaged_fallback_stems_per_ha is not None:
                unmanaged_stems_curve_ref = f"au_{au_token}_unmanaged_stems_per_ha"
                unmanaged_stems_curve_points = _build_stems_per_ha_curve_points(
                    source_curve_points=unmanaged_stems_source,
                    stems_per_ha=unmanaged_fallback_stems_per_ha,
                )
                curves[unmanaged_stems_curve_ref] = unmanaged_stems_curve_points
            if managed_tph_points or managed_fallback_stems_per_ha is not None:
                managed_stems_curve_ref = f"au_{au_token}_managed_stems_per_ha"
                managed_stems_curve_points = _build_stems_per_ha_curve_points(
                    source_curve_points=managed_stems_source,
                    tph_curve_points=managed_tph_points,
                    stems_per_ha=managed_fallback_stems_per_ha,
                )
                curves[managed_stems_curve_ref] = managed_stems_curve_points

        for origin in ORIGIN_ORDER:
            default_silv_state = _default_silv_state_for_origin(origin)
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
            if (
                origin == "planted"
                and "stand-structure-basic" in btc_indicator_bank_names
            ):
                for (
                    indicator_key,
                    label_template,
                ) in STAND_STRUCTURE_BASIC_FEATURE_COLUMNS:
                    curve_points = managed_indicator_curves.get(indicator_key)
                    if not curve_points:
                        continue
                    curve_ref = (
                        f"au_{au_token}_managed_{_sanitize_id_component(indicator_key)}"
                    )
                    curves[curve_ref] = tuple(curve_points)
                    managed_attrs.append(
                        AttributeBinding(
                            label=label_template.format(au_token=au_token),
                            curve_idref=curve_ref,
                        )
                    )
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
            if "log-grades" in btc_indicator_bank_names:
                log_grade_curves = _append_log_grade_product_attrs(
                    product_attrs=product_attrs,
                    curves=curves,
                    managed_indicator_curves=managed_indicator_curves,
                    source_curve_points=(
                        managed_total_curve.points
                        if managed_total_curve is not None
                        else ()
                    ),
                    au_token=au_token,
                    treatment_label="CC",
                    silv_state=default_silv_state,
                    curve_ref_prefix=(
                        f"au_{au_token}_{_sanitize_id_component(origin)}_cc_log_grade"
                    ),
                    compile_recipe=btc_indicator_bank_compile_recipes.get("log-grades"),
                )
                _append_species_log_grade_product_attrs(
                    product_attrs=product_attrs,
                    curves=curves,
                    total_curve_points=(
                        managed_total_curve.points
                        if managed_total_curve is not None
                        else ()
                    ),
                    species_total_curve_points_by_species=managed_derived_yield_curves,
                    grade_curve_points_by_indicator=log_grade_curves,
                    au_token=au_token,
                    origin=origin,
                    treatment_label="CC",
                    curve_ref_prefix=(
                        f"au_{au_token}_{_sanitize_id_component(origin)}_cc_log_grade_species"
                    ),
                    compile_recipe=btc_indicator_bank_compile_recipes.get("log-grades"),
                    log_grade_price_matrices=log_grade_price_matrices,
                )
            if unmanaged_stems_curve_ref is not None:
                unmanaged_attrs.append(
                    AttributeBinding(
                        label=f"feature.StemsPerHa.unmanaged.{au_token}",
                        curve_idref=unmanaged_stems_curve_ref,
                    )
                )
            if managed_stems_curve_ref is not None:
                managed_attrs.append(
                    AttributeBinding(
                        label=f"feature.StemsPerHa.managed.{au_token}",
                        curve_idref=managed_stems_curve_ref,
                    )
                )
            if unmanaged_height_curve_ref is not None:
                unmanaged_attrs.append(
                    AttributeBinding(
                        label=f"feature.Height.unmanaged.{au_token}",
                        curve_idref=unmanaged_height_curve_ref,
                    )
                )
            if managed_height_curve_ref is not None:
                managed_attrs.append(
                    AttributeBinding(
                        label=f"feature.Height.managed.{au_token}",
                        curve_idref=managed_height_curve_ref,
                    )
                )

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
                    site_index=(
                        float(qmd_support.site_index)
                        if qmd_support is not None
                        and qmd_support.site_index is not None
                        else None
                    ),
                    stems_per_ha=(
                        float(qmd_support.unmanaged_stems_per_ha)
                        if qmd_support is not None
                        and qmd_support.unmanaged_stems_per_ha is not None
                        else None
                    ),
                )
                curves[managed_qmd_curve_ref] = _build_qmd_curve_points(
                    source_curve_points=managed_qmd_source,
                    si_level=au.si_level,
                    site_index=(
                        float(qmd_support.site_index)
                        if qmd_support is not None
                        and qmd_support.site_index is not None
                        else None
                    ),
                    height_curve_points=(
                        tuple(qmd_support.managed_height_points)
                        if qmd_support is not None
                        else ()
                    ),
                    tph_curve_points=(
                        tuple(qmd_support.managed_tph_points)
                        if qmd_support is not None
                        else ()
                    ),
                    stems_per_ha=(
                        float(qmd_support.managed_stems_per_ha)
                        if qmd_support is not None
                        and qmd_support.managed_stems_per_ha is not None
                        else None
                    ),
                    direct_diameter_curve_points=managed_native_qmd_curve_points,
                    basal_area_curve_points=managed_native_basal_area_curve_points,
                    stand_structure_stems_curve_points=(
                        managed_native_stems_curve_points
                    ),
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
                if qmd_harvested_product_accounts_enabled:
                    product_attrs.append(
                        AttributeBinding(
                            label=_harvested_treated_area_product_label(
                                au_token=au_token,
                                treatment_label="CC",
                            ),
                            curve_idref="unity",
                        )
                    )
                    product_attrs.append(
                        AttributeBinding(
                            label=_harvested_qmd_numerator_product_label(
                                au_token=au_token,
                                treatment_label="CC",
                            ),
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
                            adjust="R",
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
                pct_cc_log_grade_curves: dict[str, tuple[CurvePoint, ...]] = {}
                if "log-grades" in btc_indicator_bank_names:
                    pct_cc_log_grade_curves = _append_log_grade_product_attrs(
                        product_attrs=pct_cc_product_attrs,
                        curves=curves,
                        managed_indicator_curves=managed_indicator_curves,
                        source_curve_points=managed_total_curve.points,
                        au_token=au_token,
                        treatment_label="CC",
                        silv_state=str(pct_config["to_state"]),
                        curve_ref_prefix=(
                            "au_"
                            f"{au_token}_{_sanitize_id_component(str(pct_config['to_state']))}"
                            "_cc_log_grade"
                        ),
                        compile_recipe=btc_indicator_bank_compile_recipes.get(
                            "log-grades"
                        ),
                    )
                pct_stems_curve_ref: str | None = None
                pct_stems_curve_points: tuple[CurvePoint, ...] = ()
                if managed_stems_curve_points:
                    source_total_stems = max(
                        0.0, float(pct_config["source_total_stems_per_ha"])
                    )
                    removed_stems = max(
                        0.0,
                        sum(
                            float(stems)
                            for _species, stems in pct_config[
                                "remove_stems_per_ha_by_species"
                            ]
                        ),
                    )
                    residual_fraction = 1.0
                    if source_total_stems > 0.0 and removed_stems > 0.0:
                        residual_fraction = max(
                            0.0,
                            (source_total_stems - removed_stems) / source_total_stems,
                        )
                    pct_stems_curve_ref = (
                        f"au_{au_token}_managed_"
                        f"{_sanitize_id_component(str(pct_config['to_state']))}_stems_per_ha"
                    )
                    pct_stems_curve_points = (
                        _build_curve_with_post_transition_multiplier(
                            source_curve_points=managed_stems_curve_points,
                            transition_age=int(pct_config["pct_age"]),
                            multiplier=residual_fraction,
                        )
                    )
                    curves[pct_stems_curve_ref] = pct_stems_curve_points
                    pct_feature_attrs.append(
                        AttributeBinding(
                            label=f"feature.StemsPerHa.managed.{au_token}",
                            curve_idref=pct_stems_curve_ref,
                        )
                    )
                if qmd_enabled:
                    pct_feature_attrs.append(
                        AttributeBinding(
                            label=f"feature.QMD.managed.{au_token}",
                            curve_idref=managed_qmd_curve_ref,
                        )
                    )
                    if qmd_harvested_product_accounts_enabled:
                        pct_product_attrs.append(
                            AttributeBinding(
                                label=_harvested_treated_area_product_label(
                                    au_token=au_token,
                                    treatment_label=str(pct_config["label"]),
                                ),
                                curve_idref="unity",
                            )
                        )
                        pct_product_attrs.append(
                            AttributeBinding(
                                label=_harvested_qmd_numerator_product_label(
                                    au_token=au_token,
                                    treatment_label=str(pct_config["label"]),
                                ),
                                curve_idref=managed_qmd_curve_ref,
                            )
                        )
                        pct_cc_product_attrs.append(
                            AttributeBinding(
                                label=_harvested_treated_area_product_label(
                                    au_token=au_token,
                                    treatment_label="CC",
                                ),
                                curve_idref="unity",
                            )
                        )
                        pct_cc_product_attrs.append(
                            AttributeBinding(
                                label=_harvested_qmd_numerator_product_label(
                                    au_token=au_token,
                                    treatment_label="CC",
                                ),
                                curve_idref=managed_qmd_curve_ref,
                            )
                        )
                if height_enabled and managed_height_curve_ref is not None:
                    pct_feature_attrs.append(
                        AttributeBinding(
                            label=f"feature.Height.managed.{au_token}",
                            curve_idref=managed_height_curve_ref,
                        )
                    )
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
                if "log-grades" in btc_indicator_bank_names:
                    _append_species_log_grade_product_attrs(
                        product_attrs=pct_cc_product_attrs,
                        curves=curves,
                        total_curve_points=managed_total_curve.points,
                        species_total_curve_points_by_species=pct_species_yield_curves,
                        grade_curve_points_by_indicator=pct_cc_log_grade_curves,
                        au_token=au_token,
                        origin="planted",
                        treatment_label="CC",
                        curve_ref_prefix=(
                            "au_"
                            f"{au_token}_{_sanitize_id_component(str(pct_config['to_state']))}"
                            "_cc_log_grade_species"
                        ),
                        compile_recipe=btc_indicator_bank_compile_recipes.get(
                            "log-grades"
                        ),
                        log_grade_price_matrices=log_grade_price_matrices,
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
                    "stems_curve_ref": pct_stems_curve_ref,
                    "stems_curve_points": pct_stems_curve_points,
                }

        if ct_configs and managed_total_curve is not None:
            for ct_config in ct_configs:
                ct_species_prop_points = planted_species_prop_points
                ct_species_prop_curve_refs = {
                    species: source_curve_ref_by_id[curve_id]
                    for species, curve_id in planted_species_curve_map.items()
                    if curve_id in source_curve_ref_by_id
                }
                ct_stems_source_points = managed_stems_curve_points
                pct_state_payload = pct_state_payload_by_to_state.get(
                    str(ct_config["from_state"])
                )
                if pct_state_payload is not None:
                    ct_species_prop_points = pct_state_payload["species_prop_points"]
                    ct_species_prop_curve_refs = dict(
                        pct_state_payload["species_curve_refs"]
                    )
                    ct_stems_source_points = tuple(
                        pct_state_payload.get("stems_curve_points", ())
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
                if "log-grades" in btc_indicator_bank_names:
                    ct_log_grade_curves = _append_log_grade_product_attrs(
                        product_attrs=ct_product_attrs,
                        curves=curves,
                        managed_indicator_curves=managed_indicator_curves,
                        source_curve_points=curves[ct_product_curve_ref],
                        au_token=au_token,
                        treatment_label="CT",
                        silv_state=str(ct_config["from_state"]),
                        curve_ref_prefix=(f"au_{au_token}_{state_slug}_ct_log_grade"),
                        compile_recipe=btc_indicator_bank_compile_recipes.get(
                            "log-grades"
                        ),
                    )
                    ct_cc_log_grade_curves = _append_log_grade_product_attrs(
                        product_attrs=ct_cc_product_attrs,
                        curves=curves,
                        managed_indicator_curves=managed_indicator_curves,
                        source_curve_points=curves[ct_residual_curve_ref],
                        au_token=au_token,
                        treatment_label="CC",
                        silv_state=str(ct_config["to_state"]),
                        curve_ref_prefix=(f"au_{au_token}_{state_slug}_cc_log_grade"),
                        compile_recipe=btc_indicator_bank_compile_recipes.get(
                            "log-grades"
                        ),
                    )
                ct_residual_attrs = [
                    AttributeBinding(label="feature.Area.managed", curve_idref="unity"),
                    AttributeBinding(
                        label="feature.Yield.managed.Total",
                        curve_idref=ct_residual_curve_ref,
                    ),
                    *old_growth_feature_attrs,
                ]
                ct_stems_curve_ref: str | None = None
                ct_stems_curve_points: tuple[CurvePoint, ...] = ()
                if ct_stems_source_points:
                    ct_stems_curve_ref = (
                        f"au_{au_token}_managed_{state_slug}_stems_per_ha"
                    )
                    ct_stems_curve_points = (
                        _build_curve_with_post_transition_multiplier(
                            source_curve_points=ct_stems_source_points,
                            transition_age=ct_age,
                            multiplier=max(
                                0.0, 1.0 - float(ct_config["removal_fraction"])
                            ),
                        )
                    )
                    curves[ct_stems_curve_ref] = ct_stems_curve_points
                    ct_residual_attrs.append(
                        AttributeBinding(
                            label=f"feature.StemsPerHa.managed.{au_token}",
                            curve_idref=ct_stems_curve_ref,
                        )
                    )
                if height_enabled and managed_height_curve_points:
                    ct_height_curve_ref = f"au_{au_token}_managed_{state_slug}_height"
                    curves[ct_height_curve_ref] = tuple(managed_height_curve_points)
                    ct_residual_attrs.append(
                        AttributeBinding(
                            label=f"feature.Height.managed.{au_token}",
                            curve_idref=ct_height_curve_ref,
                        )
                    )
                if qmd_enabled:
                    ct_qmd_curve_ref = f"au_{au_token}_managed_{state_slug}_qmd"
                    curves[ct_qmd_curve_ref] = _build_qmd_curve_points(
                        source_curve_points=managed_total_curve.points,
                        si_level=au.si_level,
                        site_index=(
                            float(qmd_support.site_index)
                            if qmd_support is not None
                            and qmd_support.site_index is not None
                            else None
                        ),
                        height_curve_points=(
                            tuple(qmd_support.managed_height_points)
                            if qmd_support is not None
                            else ()
                        ),
                        tph_curve_points=(
                            tuple(qmd_support.managed_tph_points)
                            if qmd_support is not None
                            else ()
                        ),
                        stems_per_ha=(
                            float(qmd_support.managed_stems_per_ha)
                            if qmd_support is not None
                            and qmd_support.managed_stems_per_ha is not None
                            else None
                        ),
                        direct_diameter_curve_points=managed_native_qmd_curve_points,
                        basal_area_curve_points=(
                            managed_native_basal_area_curve_points
                        ),
                        stand_structure_stems_curve_points=(
                            managed_native_stems_curve_points
                        ),
                        response_age=ct_age,
                        response_fraction=float(ct_config["qmd_response_fraction"]),
                    )
                    ct_residual_attrs.append(
                        AttributeBinding(
                            label=f"feature.QMD.managed.{au_token}",
                            curve_idref=ct_qmd_curve_ref,
                        )
                    )
                    if qmd_harvested_product_accounts_enabled:
                        ct_product_attrs.append(
                            AttributeBinding(
                                label=_harvested_treated_area_product_label(
                                    au_token=au_token,
                                    treatment_label="CT",
                                ),
                                curve_idref="unity",
                            )
                        )
                        ct_product_attrs.append(
                            AttributeBinding(
                                label=_harvested_qmd_numerator_product_label(
                                    au_token=au_token,
                                    treatment_label="CT",
                                ),
                                curve_idref=managed_qmd_curve_ref,
                            )
                        )
                        ct_cc_product_attrs.append(
                            AttributeBinding(
                                label=_harvested_treated_area_product_label(
                                    au_token=au_token,
                                    treatment_label="CC",
                                ),
                                curve_idref="unity",
                            )
                        )
                        ct_cc_product_attrs.append(
                            AttributeBinding(
                                label=_harvested_qmd_numerator_product_label(
                                    au_token=au_token,
                                    treatment_label="CC",
                                ),
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
                if "log-grades" in btc_indicator_bank_names:
                    _append_species_log_grade_product_attrs(
                        product_attrs=ct_product_attrs,
                        curves=curves,
                        total_curve_points=curves[ct_product_curve_ref],
                        species_total_curve_points_by_species=ct_species_product_curves,
                        grade_curve_points_by_indicator=ct_log_grade_curves,
                        au_token=au_token,
                        origin="planted",
                        treatment_label="CT",
                        curve_ref_prefix=(
                            f"au_{au_token}_{state_slug}_ct_log_grade_species"
                        ),
                        compile_recipe=btc_indicator_bank_compile_recipes.get(
                            "log-grades"
                        ),
                        log_grade_price_matrices=log_grade_price_matrices,
                    )
                    _append_species_log_grade_product_attrs(
                        product_attrs=ct_cc_product_attrs,
                        curves=curves,
                        total_curve_points=curves[ct_residual_curve_ref],
                        species_total_curve_points_by_species=ct_species_residual_curves,
                        grade_curve_points_by_indicator=ct_cc_log_grade_curves,
                        au_token=au_token,
                        origin="planted",
                        treatment_label="CC",
                        curve_ref_prefix=(
                            f"au_{au_token}_{state_slug}_cc_log_grade_species"
                        ),
                        compile_recipe=btc_indicator_bank_compile_recipes.get(
                            "log-grades"
                        ),
                        log_grade_price_matrices=log_grade_price_matrices,
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
                current_stems_points = ct_stems_curve_points
                current_height_points = managed_height_curve_points
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
                    if current_stems_points:
                        fert_stems_curve_ref = (
                            f"au_{au_token}_managed_"
                            f"{_sanitize_id_component(str(fert_config['to_state']))}_stems_per_ha"
                        )
                        curves[fert_stems_curve_ref] = tuple(current_stems_points)
                        fert_feature_attrs.append(
                            AttributeBinding(
                                label=f"feature.StemsPerHa.managed.{au_token}",
                                curve_idref=fert_stems_curve_ref,
                            )
                        )
                    if height_enabled and current_height_points:
                        fert_height_curve_ref = (
                            f"au_{au_token}_managed_"
                            f"{_sanitize_id_component(str(fert_config['to_state']))}_height"
                        )
                        curves[fert_height_curve_ref] = tuple(current_height_points)
                        fert_feature_attrs.append(
                            AttributeBinding(
                                label=f"feature.Height.managed.{au_token}",
                                curve_idref=fert_height_curve_ref,
                            )
                        )
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
                    fert_log_grade_curves: dict[str, tuple[CurvePoint, ...]] = {}
                    if "log-grades" in btc_indicator_bank_names:
                        fert_log_grade_curves = _append_log_grade_product_attrs(
                            product_attrs=fert_cc_product_attrs,
                            curves=curves,
                            managed_indicator_curves=managed_indicator_curves,
                            source_curve_points=curves[fert_curve_ref],
                            au_token=au_token,
                            treatment_label="CC",
                            silv_state=str(fert_config["to_state"]),
                            curve_ref_prefix=(
                                "au_"
                                f"{au_token}_{_sanitize_id_component(str(fert_config['to_state']))}"
                                "_cc_log_grade"
                            ),
                            compile_recipe=btc_indicator_bank_compile_recipes.get(
                                "log-grades"
                            ),
                        )
                    if qmd_enabled:
                        fert_qmd_curve_ref = f"au_{au_token}_managed_{_sanitize_id_component(str(fert_config['to_state']))}_qmd"
                        curves[fert_qmd_curve_ref] = _build_qmd_curve_points(
                            source_curve_points=current_source_points,
                            si_level=au.si_level,
                            site_index=(
                                float(qmd_support.site_index)
                                if qmd_support is not None
                                and qmd_support.site_index is not None
                                else None
                            ),
                            height_curve_points=(
                                tuple(qmd_support.managed_height_points)
                                if qmd_support is not None
                                else ()
                            ),
                            tph_curve_points=(
                                tuple(qmd_support.managed_tph_points)
                                if qmd_support is not None
                                else ()
                            ),
                            stems_per_ha=(
                                float(qmd_support.managed_stems_per_ha)
                                if qmd_support is not None
                                and qmd_support.managed_stems_per_ha is not None
                                else None
                            ),
                            direct_diameter_curve_points=(
                                managed_native_qmd_curve_points
                            ),
                            basal_area_curve_points=(
                                managed_native_basal_area_curve_points
                            ),
                            stand_structure_stems_curve_points=(
                                managed_native_stems_curve_points
                            ),
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
                        if qmd_harvested_product_accounts_enabled:
                            fert_cc_product_attrs.append(
                                AttributeBinding(
                                    label=_harvested_treated_area_product_label(
                                        au_token=au_token,
                                        treatment_label="CC",
                                    ),
                                    curve_idref="unity",
                                )
                            )
                            fert_cc_product_attrs.append(
                                AttributeBinding(
                                    label=_harvested_qmd_numerator_product_label(
                                        au_token=au_token,
                                        treatment_label="CC",
                                    ),
                                    curve_idref=fert_qmd_curve_ref,
                                )
                            )
                    fert_species_curves = _build_species_yield_curves(
                        total_points=curves[fert_curve_ref],
                        species_prop_points_by_species=ct_species_prop_points,
                    )
                    if "log-grades" in btc_indicator_bank_names:
                        _append_species_log_grade_product_attrs(
                            product_attrs=fert_cc_product_attrs,
                            curves=curves,
                            total_curve_points=curves[fert_curve_ref],
                            species_total_curve_points_by_species=fert_species_curves,
                            grade_curve_points_by_indicator=fert_log_grade_curves,
                            au_token=au_token,
                            origin="planted",
                            treatment_label="CC",
                            curve_ref_prefix=(
                                "au_"
                                f"{au_token}_{_sanitize_id_component(str(fert_config['to_state']))}"
                                "_cc_log_grade_species"
                            ),
                            compile_recipe=btc_indicator_bank_compile_recipes.get(
                                "log-grades"
                            ),
                            log_grade_price_matrices=log_grade_price_matrices,
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

    resolved_input_attributes = {
        "block": DEFAULT_INPUT_ATTRIBUTE_BLOCK,
        "area": DEFAULT_INPUT_ATTRIBUTE_AREA,
        "age": DEFAULT_INPUT_ATTRIBUTE_AGE,
        "exclude": DEFAULT_INPUT_ATTRIBUTE_EXCLUDE,
    }
    if input_attributes:
        resolved_input_attributes.update(
            {
                str(key): str(value)
                for key, value in input_attributes.items()
                if value is not None and str(value).strip()
            }
        )

    return ForestModelDefinition(
        description=str(forestmodel_description),
        horizon=int(horizon_years),
        year=int(start_year),
        match="multi",
        input_attributes=resolved_input_attributes,
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
        selects=_apply_default_pass_through_successions(selects=selects),
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


def _append_succession_definitions(
    *,
    parent: et.Element,
    succession_definitions: tuple[SuccessionDefinition, ...],
) -> None:
    for succession_definition in succession_definitions:
        attrs = {
            "breakup": succession_definition.breakup,
            "renew": succession_definition.renew,
        }
        if succession_definition.initial_age_limit is not None:
            attrs["initialagelimit"] = succession_definition.initial_age_limit
        succession = et.SubElement(parent, "succession", attrs)
        for assignment in succession_definition.assignments:
            et.SubElement(
                succession,
                "assign",
                {"field": assignment.field, "value": assignment.value},
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


def _default_pass_through_succession_definition() -> SuccessionDefinition:
    return SuccessionDefinition(
        breakup=DEFAULT_PASS_THROUGH_SUCCESSION_BREAKUP,
        renew=DEFAULT_PASS_THROUGH_SUCCESSION_RENEW,
    )


def _apply_default_pass_through_successions(
    *,
    selects: list[SelectDefinition],
) -> tuple[SelectDefinition, ...]:
    default_succession = (_default_pass_through_succession_definition(),)
    return tuple(
        replace(
            select,
            succession_definitions=default_succession,
        )
        if select.include_track and not select.succession_definitions
        else select
        for select in selects
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
        if select.retention_definitions:
            _append_retention_definitions(
                parent=select_node,
                retention_definitions=select.retention_definitions,
            )
        if select.succession_definitions:
            _append_succession_definitions(
                parent=select_node,
                succession_definitions=select.succession_definitions,
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


def validate_forestmodel_xml_tree(
    *,
    root: et.Element,
    required_define_fields: Iterable[str] | None = None,
    required_curve_ids: Iterable[str] | None = ("unity",),
    require_cc_treatment: bool = True,
) -> None:
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
    resolved_required_define_fields = tuple(
        required_define_fields
        if required_define_fields is not None
        else ("AU", "IFM", "ORIGIN", "SILV_STATE", "RETENTION", "treatment")
    )
    for field in resolved_required_define_fields:
        if field not in define_fields:
            issues.append(f"missing define field: {field}")

    curve_ids = {
        curve_id
        for node in root.findall(".//curve")
        for curve_id in [node.get("id")]
        if isinstance(curve_id, str)
    }
    resolved_required_curve_ids = tuple(required_curve_ids or ())
    for curve_id in resolved_required_curve_ids:
        if curve_id not in curve_ids:
            issues.append(f"missing required curve id {curve_id!r}")
        elif not root.findall(f"./curve[@id='{curve_id}']/point"):
            issues.append(f"required curve {curve_id!r} missing point(s)")

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

    if require_cc_treatment and not root.findall(".//treatment[@label='CC']"):
        issues.append("missing required CC treatment definition")

    if issues:
        raise ValueError("invalid ForestModel XML tree: " + "; ".join(issues))


def build_fragments_geodataframe(
    *,
    checkpoint_path: Path,
    au_table: pd.DataFrame,
    tsa_list: Iterable[str],
    fragments_crs: str = DEFAULT_FRAGMENTS_CRS,
    ifm_mode: str = DEFAULT_IFM_MODE,
    ifm_source_col: str | None = DEFAULT_IFM_SOURCE_COL,
    ifm_threshold: float | None = DEFAULT_IFM_THRESHOLD,
    ifm_target_managed_share: float | None = DEFAULT_IFM_TARGET_MANAGED_SHARE,
    silviculture_config: dict[str, Any] | None = None,
    legacy_input_variables_config: dict[str, Any] | None = None,
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

    live_input_attributes, required_live_source_columns = (
        _build_live_legacy_input_attribute_contract(
            legacy_input_variables_config=legacy_input_variables_config
        )
    )
    (
        live_additional_stratification_columns,
        required_live_additional_source_columns,
    ) = _build_live_legacy_additional_stratification_contract(
        legacy_input_variables_config=legacy_input_variables_config
    )
    legacy_constants = _build_live_legacy_constants_contract(
        legacy_input_variables_config=legacy_input_variables_config
    )
    live_treatment_eligibility_expression = _normalize_optional_expression(
        _legacy_input_variables_staged_mapping(legacy_input_variables_config).get(
            "treatment_eligibility_expression"
        )
    )
    required_legacy_source_columns: list[str] = []
    for column_name in (
        *required_live_source_columns,
        *required_live_additional_source_columns,
    ):
        if column_name not in required_legacy_source_columns:
            required_legacy_source_columns.append(column_name)
    missing_live_source_columns = sorted(
        column_name
        for column_name in required_legacy_source_columns
        if column_name not in scoped.columns
    )
    if missing_live_source_columns:
        raise ValueError(
            "required legacy export source columns missing from checkpoint: "
            + ", ".join(missing_live_source_columns)
        )

    if "FEMIC_EFFECTIVE_AREA_SQM" in scoped.columns:
        total_area_ha = (
            pd.to_numeric(scoped["FEMIC_EFFECTIVE_AREA_SQM"], errors="coerce") * 0.0001
        )
    elif "FEATURE_AREA_SQM" in scoped.columns:
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
    block_values = pd.Series(
        np.arange(1, len(scoped) + 1, dtype=int), index=scoped.index, dtype="int64"
    )
    if live_input_attributes.get("block") != DEFAULT_INPUT_ATTRIBUTE_BLOCK:
        block_candidate = _evaluate_legacy_export_expression(
            expression=live_input_attributes["block"],
            scoped=scoped,
            area_ha=total_area_ha,
        )
        if pd.to_numeric(block_candidate, errors="coerce").isna().any():
            raise ValueError(
                "legacy block expression must resolve to numeric values for fragments export"
            )
        block_values = (
            pd.to_numeric(block_candidate, errors="coerce").fillna(0).astype(int)
        )
    area_values = (
        pd.to_numeric(total_area_ha, errors="coerce").fillna(0.0).astype(float)
    )
    if live_input_attributes.get("area") != DEFAULT_INPUT_ATTRIBUTE_AREA:
        area_candidate = _evaluate_legacy_export_expression(
            expression=live_input_attributes["area"],
            scoped=scoped,
            area_ha=total_area_ha,
        )
        area_values = (
            pd.to_numeric(area_candidate, errors="coerce").fillna(0.0).clip(lower=0.0)
        )
    positive_area_mask = area_values.gt(MIN_FRAGMENT_EXPORT_AREA_HA)
    if not positive_area_mask.any():
        raise ValueError(
            "no positive-area checkpoint rows matched selected TSA/AU export filters"
        )
    if not positive_area_mask.all():
        scoped = scoped.loc[positive_area_mask].copy().reset_index(drop=True)
        total_area_ha = (
            total_area_ha.loc[positive_area_mask].copy().reset_index(drop=True)
        )
        block_values = (
            block_values.loc[positive_area_mask].copy().reset_index(drop=True)
        )
        area_values = area_values.loc[positive_area_mask].copy().reset_index(drop=True)
    age_values = (
        pd.to_numeric(scoped["PROJ_AGE_1"], errors="coerce").fillna(0).astype(int)
    )
    if live_input_attributes.get("age") != DEFAULT_INPUT_ATTRIBUTE_AGE:
        age_candidate = _evaluate_legacy_export_expression(
            expression=live_input_attributes["age"],
            scoped=scoped,
            area_ha=total_area_ha,
        )
        if pd.to_numeric(age_candidate, errors="coerce").isna().any():
            raise ValueError(
                "legacy age expression must resolve to numeric values for fragments export"
            )
        age_values = pd.to_numeric(age_candidate, errors="coerce").fillna(0).astype(int)
    au_values = scoped["au"].astype(int)
    fragment_ids = np.arange(1, len(scoped) + 1, dtype=int)
    retention_overrides = _resolve_retention_overrides_by_au(
        au_table=au_table,
        silviculture_config=silviculture_config,
    )
    retention_values = np.full(len(scoped), DEFAULT_RETENTION_VALUE, dtype=float)
    for au_id, factor in retention_overrides.items():
        retention_values[au_values == int(au_id)] = float(factor)
    ifm_values, final_retention_values = _resolve_ifm_and_retention(
        scoped=scoped,
        total_area_ha=total_area_ha,
        ifm_mode=ifm_mode,
        ifm_source_col=ifm_source_col,
        ifm_threshold=ifm_threshold,
        ifm_target_managed_share=ifm_target_managed_share,
        retention_values=retention_values,
    )
    out = pd.DataFrame(
        {
            FRAGMENT_ID_COLUMN: fragment_ids,
            "BLOCK": block_values.astype(int),
            "AREA_HA": area_values.astype(float),
            "F_AGE": age_values.astype(int),
            "AU": au_values,
            "IFM": ifm_values.to_numpy(),
            "ORIGIN": np.where(
                age_values <= ORIGIN_PLANTED_MAX_AGE, "planted", "natural"
            ),
            "SILV_STATE": np.where(
                age_values <= ORIGIN_PLANTED_MAX_AGE,
                DEFAULT_SILV_STATE_PLANTED,
                DEFAULT_SILV_STATE_NATURAL,
            ),
            "RETENTION": final_retention_values,
            "TSA": scoped["tsa_code"].astype(str),
            "geometry": scoped["geometry"],
        }
    )
    for column_name in required_live_source_columns:
        out[column_name] = scoped[column_name]
    used_fragment_field_names = {
        str(column_name).casefold() for column_name in out.columns
    }
    for key, source_expression in live_additional_stratification_columns:
        export_field_name = _resolve_legacy_additional_export_field_name(
            requested_key=key,
            used_names=used_fragment_field_names,
        )
        out[export_field_name] = _evaluate_legacy_export_expression(
            expression=source_expression,
            scoped=scoped,
            area_ha=total_area_ha,
        )
    if live_treatment_eligibility_expression is not None:
        treatment_ineligible = _evaluate_legacy_treatment_eligibility_expression(
            expression=live_treatment_eligibility_expression,
            scoped=scoped,
            exported=out,
            legacy_constants=legacy_constants,
        )
        out[DEFAULT_LEGACY_TREATMENT_ELIGIBILITY_FIELD] = np.where(
            treatment_ineligible.to_numpy(),
            "Y",
            "N",
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
    *, scoped: pd.DataFrame, ifm_source_col: str | None, ifm_mode: str
) -> str | None:
    normalized_mode = str(ifm_mode).strip().lower()
    if ifm_source_col is not None and ifm_source_col.strip():
        candidate = ifm_source_col.strip()
        if candidate not in scoped.columns:
            raise ValueError(
                f"ifm_source_col {candidate!r} was requested but not found in checkpoint"
            )
        return candidate
    if normalized_mode == "legacy_binary":
        candidates = IFM_SIGNAL_PRIORITY
    elif normalized_mode == "proportional":
        candidates = IFM_PROPORTIONAL_SIGNAL_PRIORITY
    else:
        raise ValueError(
            f"Unsupported ifm_mode {ifm_mode!r}; expected one of "
            f"{sorted(VALID_IFM_MODES)}"
        )
    for candidate in candidates:
        if candidate in scoped.columns:
            return candidate
    return None


def _resolve_ifm_managed_share(
    *,
    scoped: pd.DataFrame,
    signal_col: str | None,
    total_area_ha: pd.Series,
) -> pd.Series:
    if signal_col is None:
        return pd.Series(1.0, index=scoped.index, dtype=float)

    signal = pd.to_numeric(scoped[signal_col], errors="coerce").fillna(0.0)
    if signal_col == "thlb_area":
        denominator = pd.to_numeric(total_area_ha, errors="coerce").replace(0.0, np.nan)
        managed_share = signal.div(denominator).fillna(0.0)
    else:
        max_signal = float(signal.max()) if not signal.empty else 0.0
        managed_share = signal / 100.0 if max_signal > 1.0 else signal
    return managed_share.clip(lower=0.0, upper=1.0)


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
    signal_col = _resolve_ifm_signal_col(
        scoped=scoped,
        ifm_source_col=ifm_source_col,
        ifm_mode="legacy_binary",
    )
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


def _resolve_ifm_and_retention(
    *,
    scoped: pd.DataFrame,
    total_area_ha: pd.Series,
    ifm_mode: str,
    ifm_source_col: str | None,
    ifm_threshold: float | None,
    ifm_target_managed_share: float | None,
    retention_values: np.ndarray,
) -> tuple[pd.Series, np.ndarray]:
    normalized_mode = str(ifm_mode).strip().lower()
    if normalized_mode not in VALID_IFM_MODES:
        raise ValueError(
            f"Unsupported ifm_mode {ifm_mode!r}; expected one of "
            f"{sorted(VALID_IFM_MODES)}"
        )

    if normalized_mode == "legacy_binary":
        managed_flag = _resolve_managed_flag(
            scoped=scoped,
            ifm_source_col=ifm_source_col,
            ifm_threshold=ifm_threshold,
            ifm_target_managed_share=ifm_target_managed_share,
        )
        return (
            pd.Series(
                np.where(managed_flag.to_numpy(dtype=bool), "managed", "unmanaged"),
                index=scoped.index,
            ),
            retention_values,
        )

    if ifm_threshold is not None or ifm_target_managed_share is not None:
        raise ValueError(
            "ifm_threshold and ifm_target_managed_share are only supported when "
            "ifm_mode='legacy_binary'"
        )

    signal_col = _resolve_ifm_signal_col(
        scoped=scoped,
        ifm_source_col=ifm_source_col,
        ifm_mode=normalized_mode,
    )
    managed_share = _resolve_ifm_managed_share(
        scoped=scoped,
        signal_col=signal_col,
        total_area_ha=total_area_ha,
    )
    retention_overlay = np.clip(
        pd.to_numeric(pd.Series(retention_values), errors="coerce")
        .fillna(0.0)
        .to_numpy(dtype=float),
        0.0,
        1.0,
    )
    final_managed_share = (
        managed_share.to_numpy(dtype=float) * (1.0 - retention_overlay)
    ).clip(0.0, 1.0)
    ifm_values = pd.Series(
        np.where(final_managed_share > 0.0, "managed", "unmanaged"),
        index=scoped.index,
    )
    final_retention = np.where(
        final_managed_share > 0.0,
        1.0 - final_managed_share,
        0.0,
    ).astype(float)
    return _collapse_subprecision_retention_splits(
        area_ha=total_area_ha,
        ifm_values=ifm_values,
        final_retention=final_retention,
    )


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
    forestmodel_description: str = DEFAULT_FORESTMODEL_DESCRIPTION,
    start_year: int = DEFAULT_START_YEAR,
    horizon_years: int = DEFAULT_HORIZON_YEARS,
    cc_min_age: int = DEFAULT_CC_MIN_AGE,
    cc_max_age: int = DEFAULT_CC_MAX_AGE,
    cc_transition_ifm: str | None = DEFAULT_CC_TRANSITION_IFM,
    fragments_crs: str = DEFAULT_FRAGMENTS_CRS,
    ifm_mode: str = DEFAULT_IFM_MODE,
    ifm_source_col: str | None = DEFAULT_IFM_SOURCE_COL,
    ifm_threshold: float | None = DEFAULT_IFM_THRESHOLD,
    ifm_target_managed_share: float | None = DEFAULT_IFM_TARGET_MANAGED_SHARE,
    seral_stage_config_path: Path | None = DEFAULT_SERAL_STAGE_CONFIG_PATH,
    silviculture_config_path: Path | None = DEFAULT_SILVICULTURE_CONFIG_PATH,
    legacy_input_variables_config_path: Path | None = (
        DEFAULT_LEGACY_INPUT_VARIABLES_CONFIG_PATH
    ),
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
    legacy_input_variables_config = _load_legacy_input_variables_config(
        legacy_input_variables_config_path=legacy_input_variables_config_path,
    )
    resolved_description = (
        str(legacy_input_variables_config.get("description", forestmodel_description))
        if legacy_input_variables_config is not None
        else str(forestmodel_description)
    )
    resolved_start_year = (
        int(legacy_input_variables_config.get("start_year", start_year))
        if legacy_input_variables_config is not None
        else int(start_year)
    )
    resolved_horizon_years = (
        int(legacy_input_variables_config.get("horizon_years", horizon_years))
        if legacy_input_variables_config is not None
        else int(horizon_years)
    )
    resolved_input_attributes, _required_live_source_columns = (
        _build_live_legacy_input_attribute_contract(
            legacy_input_variables_config=legacy_input_variables_config
        )
    )

    root = build_forestmodel_xml_tree_from_context(
        context=context,
        forestmodel_description=resolved_description,
        input_attributes=resolved_input_attributes,
        start_year=resolved_start_year,
        horizon_years=resolved_horizon_years,
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
        ifm_mode=ifm_mode,
        ifm_source_col=ifm_source_col,
        ifm_threshold=ifm_threshold,
        ifm_target_managed_share=ifm_target_managed_share,
        silviculture_config=silviculture_config,
        legacy_input_variables_config=legacy_input_variables_config,
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
