"""Instance-level carbon configuration.

The ``carbon:`` block names the crosswalk files, CBM defaults provenance, and the
review state for one FEMIC instance. It is the supported way to select an instance default
without repeating a long command line.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from .package import (
    DEFAULT_AGE_INTERVAL,
    DEFAULT_MAX_AGE,
    DEFAULT_VOLUME_FEATURE_LABEL,
    CarbonExportConfig,
    load_carbon_export_config,
)

CONFIG_SCHEMA_VERSION = "0.1"
CBM_ECO_BOUNDARIES = {
    "Atlantic Maritime",
    "Boreal Cordillera",
    "Boreal Plains",
    "Boreal Shield East",
    "Boreal Shield West",
    "Hudson Plains",
    "Mixedwood Plains",
    "Montane Cordillera",
    "Pacific Maritime",
    "Semiarid Prairies",
    "Subhumid Prairies",
    "Taiga Cordillera",
    "Taiga Plains",
    "Taiga Shield East",
    "Taiga Shield West",
}
REQUIRED_MAPS = (
    "species_map",
    "eco_boundary_map",
    "disturbance_map",
    "land_class_map",
)


@dataclass(frozen=True)
class CarbonInstanceConfig:
    """A validated ``carbon:`` configuration.

    Attributes
    ----------
    config_path : Path
        Source YAML file.
    schema_version : str
        Carbon config schema version.
    tsa_codes : tuple of str
        TSA/FMU codes covered by the configuration.
    admin_boundary : str
        CBM administrative boundary.
    eco_boundary : str
        CBM eco boundary.
    crosswalk_dir : Path
        Directory holding the four crosswalk CSVs.
    cbm_defaults_version : str
        CBM defaults version.
    cbm_defaults_sha256 : str or None
        CBM defaults digest, when pinned.
    cbm_defaults_source : str
        CBM defaults source label.
    fallback_softwood : str
        Explicit softwood fallback CBM species.
    fallback_hardwood : str
        Explicit hardwood fallback CBM species.
    fallback_wood_type : {"softwood", "hardwood"}
        Fallback wood type for an unmapped species.
    age_interval : int
        Yield grid width.
    max_age : int
        Maximum yield age.
    volume_feature_label : str
        WS4 merchantable-volume feature label.
    review_status : str
        Crosswalk review status.
    reviewer : str
        Crosswalk reviewer.
    reviewed_utc : str
        Review timestamp.
    expected_area_ha : float or None
        Optional expected inventory area for validation.
    expected_track_count : int or None
        Optional expected track count for validation.
    """

    config_path: Path
    schema_version: str
    tsa_codes: tuple[str, ...]
    admin_boundary: str
    eco_boundary: str
    crosswalk_dir: Path
    cbm_defaults_version: str
    cbm_defaults_sha256: str | None
    cbm_defaults_source: str
    fallback_softwood: str
    fallback_hardwood: str
    fallback_wood_type: str
    age_interval: int
    max_age: int
    volume_feature_label: str
    review_status: str
    reviewer: str
    reviewed_utc: str
    expected_area_ha: float | None
    expected_track_count: int | None


def load_carbon_instance_config(path: Path) -> CarbonInstanceConfig:
    """Load and validate one ``carbon:`` configuration.

    Parameters
    ----------
    path : Path
        YAML file with a top-level ``carbon:`` mapping.

    Returns
    -------
    CarbonInstanceConfig
        The resolved configuration.

    Raises
    ------
    FileNotFoundError
        When the YAML file or a crosswalk is missing.
    ValueError
        When the block is malformed, references an unknown TSA, or names a
        boundary that does not match the eco-boundary map.
    """
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(f"carbon config not found: {source}")
    payload = yaml.safe_load(source.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise TypeError(f"{source} must contain a YAML mapping")
    carbon = payload.get("carbon")
    if not isinstance(carbon, dict):
        raise TypeError(f"{source} must contain a 'carbon:' mapping")
    schema = str(carbon.get("schema_version", "")).strip()
    if schema != CONFIG_SCHEMA_VERSION:
        raise ValueError(
            f"{source}: schema_version must be {CONFIG_SCHEMA_VERSION!r}, got {schema!r}"
        )
    admin = _required_text(carbon, "admin_boundary", source)
    eco = _required_text(carbon, "eco_boundary", source)
    if eco not in CBM_ECO_BOUNDARIES:
        raise ValueError(f"{source}: unknown CBM eco boundary {eco!r}")
    maps = {
        name: _resolve_crosswalk(source, _required_text(carbon, name, source))
        for name in REQUIRED_MAPS
    }
    crosswalk_dir = _single_parent(maps, source)
    tsa_codes = _tsa_codes(carbon.get("tsa_codes"), source)
    _validate_eco_rows(maps["eco_boundary_map"], tsa_codes, admin, eco, source)
    defaults = carbon.get("cbm_defaults")
    if not isinstance(defaults, dict):
        raise TypeError(f"{source}: cbm_defaults must be a mapping")
    defaults_version = _required_text(defaults, "version", source)
    defaults_sha = _optional_text(defaults.get("sha256"))
    defaults_source = _optional_text(defaults.get("source")) or "libcbm"
    fallback = carbon.get("fallback") or {}
    if not isinstance(fallback, dict):
        raise TypeError(f"{source}: fallback must be a mapping")
    review = carbon.get("review") or {}
    if not isinstance(review, dict):
        raise TypeError(f"{source}: review must be a mapping")
    validation = carbon.get("validation") or {}
    if not isinstance(validation, dict):
        raise TypeError(f"{source}: validation must be a mapping")
    age_interval = int(carbon.get("age_interval", DEFAULT_AGE_INTERVAL))
    max_age = int(carbon.get("max_age", DEFAULT_MAX_AGE))
    if age_interval <= 0 or max_age < age_interval:
        raise ValueError(f"{source}: age_interval and max_age must define a grid")
    return CarbonInstanceConfig(
        config_path=source,
        schema_version=schema,
        tsa_codes=tsa_codes,
        admin_boundary=admin,
        eco_boundary=eco,
        crosswalk_dir=crosswalk_dir,
        cbm_defaults_version=defaults_version,
        cbm_defaults_sha256=defaults_sha,
        cbm_defaults_source=defaults_source,
        fallback_softwood=_optional_text(fallback.get("softwood_species"))
        or "Unspecified softwood species",
        fallback_hardwood=_optional_text(fallback.get("hardwood_species"))
        or "Unspecified hardwood species",
        fallback_wood_type=_optional_text(fallback.get("wood_type")) or "softwood",
        age_interval=age_interval,
        max_age=max_age,
        volume_feature_label=(
            _optional_text(carbon.get("volume_feature_label"))
            or DEFAULT_VOLUME_FEATURE_LABEL
        ),
        review_status=_optional_text(review.get("status")) or "draft",
        reviewer=_optional_text(review.get("reviewer")) or "",
        reviewed_utc=_optional_text(review.get("reviewed_utc")) or "",
        expected_area_ha=_optional_float(validation.get("expected_area_ha"), source),
        expected_track_count=_optional_int(
            validation.get("expected_track_count"), source
        ),
    )


def to_export_config(config: CarbonInstanceConfig) -> CarbonExportConfig:
    """Resolve an instance config into the package exporter config.

    Parameters
    ----------
    config : CarbonInstanceConfig
        The instance configuration.

    Returns
    -------
    CarbonExportConfig
        The crosswalks and provenance used by the exporter.
    """
    if config.fallback_wood_type not in {"softwood", "hardwood"}:
        raise ValueError("fallback.wood_type must be 'softwood' or 'hardwood'")
    return load_carbon_export_config(
        config.crosswalk_dir,
        admin_boundary=config.admin_boundary,
        eco_boundary=config.eco_boundary,
        cbm_defaults_version=config.cbm_defaults_version,
        cbm_defaults_sha256=config.cbm_defaults_sha256,
        cbm_defaults_source=config.cbm_defaults_source,
        age_interval=config.age_interval,
        max_age=config.max_age,
        volume_feature_label=config.volume_feature_label,
        fallback_softwood=config.fallback_softwood,
        fallback_hardwood=config.fallback_hardwood,
        fallback_wood_type=config.fallback_wood_type,
        review_status=config.review_status,
        reviewer=config.reviewer,
        reviewed_utc=config.reviewed_utc,
    )


def _required_text(mapping: dict[str, Any], key: str, source: Path) -> str:
    """Return a non-empty string field."""
    value = _optional_text(mapping.get(key))
    if not value:
        raise ValueError(f"{source}: missing required field {key!r}")
    return value


def _optional_text(value: object) -> str:
    """Normalize a scalar to a stripped string."""
    if value is None:
        return ""
    return str(value).strip()


def _resolve_crosswalk(source: Path, name: str) -> Path:
    """Resolve a crosswalk path relative to the config, then the cwd."""
    path = Path(name).expanduser()
    candidates = (
        [path] if path.is_absolute() else [source.parent / path, Path.cwd() / path]
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    raise FileNotFoundError(f"{source}: crosswalk not found: {name}")


def _single_parent(maps: dict[str, Path], source: Path) -> Path:
    """Return the common parent directory of the four crosswalk files."""
    parents = {path.parent for path in maps.values()}
    if len(parents) != 1:
        raise ValueError(
            f"{source}: all crosswalk files must share one directory, got {sorted(map(str, parents))}"
        )
    return parents.pop()


def _tsa_codes(value: object, source: Path) -> tuple[str, ...]:
    """Normalize an optional TSA/FMU code sequence."""
    if value is None:
        return ()
    if isinstance(value, str):
        items = [value]
    elif isinstance(value, (list, tuple)):
        items = list(value)
    else:
        raise TypeError(f"{source}: tsa_codes must be a string or list")
    codes = tuple(str(item).strip().lower() for item in items if str(item).strip())
    if not codes:
        raise ValueError(f"{source}: tsa_codes must not be empty when supplied")
    return codes


def _validate_eco_rows(
    path: Path,
    tsa_codes: tuple[str, ...],
    admin: str,
    eco: str,
    source: Path,
) -> None:
    """Check the configured TSA rows against the requested boundary."""
    frame = pd.read_csv(path, dtype=str, keep_default_na=False)
    required = {"tsa_code", "admin_boundary", "eco_boundary"}
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise ValueError(f"{path}: missing required columns {missing}")
    frame["tsa_code"] = frame["tsa_code"].str.strip().str.lower()
    for code in tsa_codes:
        rows = frame.loc[frame["tsa_code"] == code]
        if rows.empty:
            raise ValueError(f"{path}: no eco-boundary row for TSA/FMU {code!r}")
        for row in rows.to_dict("records"):
            if row["admin_boundary"] != admin or row["eco_boundary"] != eco:
                raise ValueError(
                    f"{source}: TSA/FMU {code!r} maps to "
                    f"{row['admin_boundary']!r}/{row['eco_boundary']!r}, not "
                    f"{admin!r}/{eco!r}"
                )


def _optional_float(value: object, source: Path) -> float | None:
    """Parse an optional non-negative float."""
    if value is None or str(value).strip() == "":
        return None
    number = float(str(value))
    if number <= 0:
        raise ValueError(f"{source}: expected_area_ha must be positive")
    return number


def _optional_int(value: object, source: Path) -> int | None:
    """Parse an optional positive integer."""
    if value is None or str(value).strip() == "":
        return None
    number = int(str(value))
    if number <= 0:
        raise ValueError(f"{source}: expected_track_count must be positive")
    return number
