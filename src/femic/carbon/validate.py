"""Validation for FEMIC static carbon packages.

The validator is deliberately producer-side: it checks the package contract,
table hashes, manifest totals, classifier coverage, yield grid, and crosswalk
consistency before a package is handed to WS4 or WS3.
"""

from __future__ import annotations

import hashlib
import itertools
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from .package import SCHEMA_VERSION, TABLE_FILES, UNITS

REQUIRED_COLUMNS: dict[str, set[str]] = {
    "classifiers": {"classifier_id", "classifier", "value", "description"},
    "disturbance_types": {
        "user_dist_type",
        "default_dist_type",
        "removes_biomass",
        "transition_reset_age",
        "regen_delay",
    },
    "age_classes": {"name", "class_size"},
    "inventory": {
        "track_name",
        "age",
        "area_ha",
        "delay",
        "landclass",
        "historic_disturbance",
        "last_pass_disturbance",
    },
    "yield": {"track_name", "species", "leading_species", "age", "volume_m3_ha"},
    "track_carbon_map": {
        "track_name",
        "classifier_set",
        "leading_species",
        "softwood_share",
        "hardwood_share",
        "landclass",
        "last_disturbance",
        "eco_boundary",
        "volume_feature_label",
    },
    "curve_carbon_map": {"track_name", "feature_label", "species", "share"},
    "species_map": {"bc_species", "cbm_species", "wood_type", "confidence"},
    "boundaries": {"admin_boundary", "eco_boundary"},
}
MANIFEST_KEYS = {
    "schema_version",
    "package_id",
    "producer",
    "sources",
    "cbm_defaults",
    "units",
    "boundaries",
    "mapping",
    "table_files",
    "table_hashes",
}


@dataclass(frozen=True)
class CarbonValidationResult:
    """The result of a successful package validation.

    Attributes
    ----------
    package_dir : Path
        Validated package directory.
    package_id : str
        Manifest package id.
    track_count : int
        Number of tracks.
    inventory_area_ha : float
        Total inventory area.
    yield_rows : int
        Number of yield rows.
    """

    package_dir: Path
    package_id: str
    track_count: int
    inventory_area_ha: float
    yield_rows: int


class CarbonValidationError(ValueError):
    """Raised when a carbon package violates the contract.

    Attributes
    ----------
    issues : tuple of str
        One or more human-readable validation failures.
    """

    def __init__(self, issues: list[str]) -> None:
        self.issues = tuple(issues)
        detail = "\n".join(f"- {issue}" for issue in self.issues)
        super().__init__(f"carbon package validation failed:\n{detail}")


def validate_carbon_package(
    package_dir: Path,
    *,
    expected_area_ha: float | None = None,
    expected_track_count: int | None = None,
) -> CarbonValidationResult:
    """Validate a package against the FEMIC carbon contract.

    Parameters
    ----------
    package_dir : Path
        Package directory containing ``manifest.json`` and the nine CSVs.
    expected_area_ha : float or None, optional
        Require a total inventory area within ``max(0.5 ha, 1e-6 relative)``.
    expected_track_count : int or None, optional
        Require an exact track count.

    Returns
    -------
    CarbonValidationResult
        Summary totals for a valid package.

    Raises
    ------
    CarbonValidationError
        When one or more contract checks fail.
    FileNotFoundError
        When the package directory or manifest is missing.
    """
    root = Path(package_dir)
    if not root.is_dir():
        raise FileNotFoundError(f"carbon package directory not found: {root}")
    manifest_path = root / "manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"carbon package manifest not found: {manifest_path}")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CarbonValidationError(
            [f"manifest.json is not valid JSON: {exc}"]
        ) from exc
    if not isinstance(manifest, dict):
        raise CarbonValidationError(["manifest.json must be a JSON object"])
    issues: list[str] = []
    _check_manifest(root, manifest, issues)
    tables = _read_tables(root, manifest, issues)
    if issues:
        raise CarbonValidationError(issues)
    _check_tables(manifest, tables, issues)
    area = float(pd.to_numeric(tables["inventory"]["area_ha"]).sum())
    tracks = int(tables["track_carbon_map"]["track_name"].nunique())
    yield_rows = int(tables["yield"].shape[0])
    if expected_area_ha is not None:
        tolerance = max(0.5, float(expected_area_ha) * 1e-6)
        if abs(area - float(expected_area_ha)) > tolerance:
            issues.append(
                f"inventory area {area:.6f} ha does not match expected "
                f"{float(expected_area_ha):.6f} ha"
            )
    if expected_track_count is not None and tracks != int(expected_track_count):
        issues.append(
            f"track count {tracks} does not match expected {int(expected_track_count)}"
        )
    if issues:
        raise CarbonValidationError(issues)
    return CarbonValidationResult(
        package_dir=root,
        package_id=str(manifest["package_id"]),
        track_count=tracks,
        inventory_area_ha=area,
        yield_rows=yield_rows,
    )


def _check_manifest(root: Path, manifest: dict[str, Any], issues: list[str]) -> None:
    """Check the manifest shape, file hashes, and fingerprint."""
    missing = sorted(MANIFEST_KEYS.difference(manifest))
    if missing:
        issues.append(f"manifest is missing keys: {missing}")
        return
    if manifest["schema_version"] != SCHEMA_VERSION:
        issues.append(
            f"manifest schema_version {manifest['schema_version']!r} != {SCHEMA_VERSION!r}"
        )
    if manifest["units"] != UNITS:
        issues.append(f"manifest units {manifest['units']!r} != {UNITS!r}")
    table_files = manifest["table_files"]
    if not isinstance(table_files, dict):
        issues.append("manifest table_files must be a mapping")
        return
    missing_tables = sorted(set(TABLE_FILES).difference(table_files))
    if missing_tables:
        issues.append(f"manifest table_files is missing: {missing_tables}")
    hashes = manifest["table_hashes"]
    if not isinstance(hashes, dict):
        issues.append("manifest table_hashes must be a mapping")
        return
    for name in TABLE_FILES:
        file_name = table_files.get(name)
        if not isinstance(file_name, str) or not file_name:
            issues.append(f"manifest table_files[{name!r}] must name a file")
            continue
        path = root / file_name
        if not path.is_file():
            issues.append(f"table {name!r} file is missing: {file_name}")
            continue
        digest = _sha256(path)
        expected = hashes.get(name)
        if expected != digest:
            issues.append(
                f"table {name!r} hash mismatch: manifest {expected!r}, actual {digest!r}"
            )
    fingerprint = _fingerprint(manifest)
    package_id = str(manifest.get("package_id", ""))
    if fingerprint and not package_id.endswith(fingerprint[:12]):
        issues.append(
            f"package_id {package_id!r} does not carry fingerprint {fingerprint[:12]!r}"
        )


def _read_tables(
    root: Path, manifest: dict[str, Any], issues: list[str]
) -> dict[str, pd.DataFrame]:
    """Read every table named by the manifest."""
    table_files = manifest.get("table_files")
    if not isinstance(table_files, dict):
        return {}
    tables: dict[str, pd.DataFrame] = {}
    for name in TABLE_FILES:
        file_name = table_files.get(name)
        if not isinstance(file_name, str):
            continue
        path = root / file_name
        if not path.is_file():
            continue
        try:
            table = pd.read_csv(path, dtype=str, keep_default_na=False)
        except (pd.errors.ParserError, OSError) as exc:
            issues.append(f"table {name!r} cannot be read: {exc}")
            continue
        tables[name] = table
        missing = sorted(REQUIRED_COLUMNS[name].difference(table.columns))
        if missing:
            issues.append(f"table {name!r} is missing columns: {missing}")
    return tables


def _check_tables(
    manifest: dict[str, Any], tables: dict[str, pd.DataFrame], issues: list[str]
) -> None:
    """Check table-level contract rules."""
    if set(tables) != set(TABLE_FILES):
        return
    boundaries = tables["boundaries"]
    if boundaries.empty:
        issues.append("boundaries.csv must contain at least one row")
    admin = str(manifest["boundaries"].get("admin", ""))
    eco = str(manifest["boundaries"].get("eco", ""))
    declared_boundaries = {
        (str(row["admin_boundary"]).strip(), str(row["eco_boundary"]).strip())
        for row in boundaries.to_dict("records")
    }
    if (admin, eco) not in declared_boundaries:
        issues.append("boundaries.csv does not declare the manifest boundary")

    age_classes = _integers(tables["age_classes"], "class_size", issues)
    grid: list[int] = []
    if age_classes:
        if age_classes[0] != 0:
            issues.append("age_classes.csv must start with a zero-width class")
        widths = set(age_classes[1:])
        if len(widths) > 1 or (widths and min(widths) <= 0):
            issues.append("age_classes.csv must use one positive class width")

    track_map = tables["track_carbon_map"]
    if track_map["track_name"].duplicated().any():
        issues.append("track_carbon_map.csv has duplicate track_name values")
    track_names = set(track_map["track_name"])
    species_classifier = set(
        tables["classifiers"].loc[
            tables["classifiers"]["classifier"] == "species", "value"
        ]
    )
    track_classifier = set(
        tables["classifiers"].loc[
            tables["classifiers"]["classifier"] == "track", "value"
        ]
    )
    if track_classifier != track_names:
        missing = sorted(track_names.difference(track_classifier))[:5]
        extra = sorted(track_classifier.difference(track_names))[:5]
        issues.append(f"track classifier mismatch; missing={missing}, extra={extra}")
    leading_species = set(track_map["leading_species"])
    if not leading_species.issubset(species_classifier):
        issues.append(
            "leading species missing from the species classifier: "
            f"{sorted(leading_species.difference(species_classifier))[:5]}"
        )
    for track_row in track_map.to_dict("records"):
        track = str(track_row["track_name"])
        parts = str(track_row["classifier_set"]).split(";")
        if (
            len(parts) != 2
            or parts[0] != track
            or parts[1] != track_row["leading_species"]
        ):
            issues.append(f"track {track!r} has an invalid classifier_set")
        try:
            shares = float(track_row["softwood_share"]) + float(
                track_row["hardwood_share"]
            )
        except ValueError:
            issues.append(f"track {track!r} has non-numeric species shares")
        else:
            if abs(shares - 1.0) > 1e-6:
                issues.append(f"track {track!r} species shares sum to {shares}")
        if str(track_row["eco_boundary"]).strip() not in {
            eco for _admin, eco in declared_boundaries
        }:
            issues.append(f"track {track!r} eco boundary is not declared in boundaries.csv")
        if not str(track_row["volume_feature_label"]).strip():
            issues.append(f"track {track!r} has an empty volume feature label")

    inventory = tables["inventory"]
    inventory_tracks = set(inventory["track_name"])
    if inventory_tracks != track_names:
        missing = sorted(track_names.difference(inventory_tracks))[:5]
        extra = sorted(inventory_tracks.difference(track_names))[:5]
        issues.append(f"inventory track mismatch; missing={missing}, extra={extra}")
    _positive_numbers(inventory, "area_ha", issues, label="inventory area")
    _non_negative_integers(inventory, "age", issues)
    _non_negative_integers(inventory, "delay", issues)
    _land_classes(inventory, issues)

    yields = tables["yield"]
    yield_tracks = set(yields["track_name"])
    if yield_tracks != track_names:
        missing = sorted(track_names.difference(yield_tracks))[:5]
        extra = sorted(yield_tracks.difference(track_names))[:5]
        issues.append(f"yield track mismatch; missing={missing}, extra={extra}")
    _non_negative_numbers(yields, "volume_m3_ha", issues, label="yield volume")
    age_values = _integers(yields, "age", issues)
    grid = sorted(set(age_values))
    if grid:
        if grid[0] != 0:
            issues.append("yield.csv must start at age 0")
        steps = {b - a for a, b in itertools.pairwise(grid)}
        if len(steps) > 1 or (steps and min(steps) <= 0):
            issues.append("yield.csv must use one positive age interval")
    ages_by_track = yields.groupby("track_name")["age"].apply(
        lambda values: sorted({int(value) for value in values})
    )
    for track_name_value, ages in ages_by_track.items():
        if grid and ages != grid:
            issues.append(f"track {track_name_value!r} does not cover the age grid")
            break
    if ages_by_track.empty and track_names:
        issues.append("yield.csv has no rows")
    if age_values and any(age < 0 for age in age_values):
        issues.append("yield.csv has negative ages")
    for track_name_value, group in yields.groupby("track_name"):
        species_values = set(group["species"])
        leading_values = set(group["leading_species"])
        if len(species_values) != 1 or species_values != leading_values:
            issues.append(
                f"track {track_name_value!r} yield species does not match leading species"
            )
            break

    curve_map = tables["curve_carbon_map"]
    curve_tracks = set(curve_map["track_name"])
    if curve_tracks != track_names:
        issues.append("curve_carbon_map.csv tracks do not match track_carbon_map.csv")
    shares_by_track = curve_map.groupby("track_name")["share"].apply(
        lambda values: sum(float(value) for value in values)
    )
    if any(abs(value - 1.0) > 1e-6 for value in shares_by_track):
        issues.append("curve_carbon_map.csv shares do not sum to one")
    for curve_row in curve_map.to_dict("records"):
        if not str(curve_row["feature_label"]).strip():
            issues.append(
                f"curve map track {curve_row['track_name']!r} has no feature label"
            )
            break

    disturbance = tables["disturbance_types"]
    if disturbance["user_dist_type"].duplicated().any():
        issues.append("disturbance_types.csv has duplicate user_dist_type values")
    types = set(disturbance["user_dist_type"].str.strip().str.lower())
    for inventory_row in inventory.to_dict("records"):
        for field in ("historic_disturbance", "last_pass_disturbance"):
            value = str(inventory_row[field]).strip().lower()
            if value and value not in types:
                issues.append(f"inventory {field} {value!r} has no disturbance type")
                return

    species_table = tables["species_map"]
    if species_table["bc_species"].duplicated().any():
        issues.append("species_map.csv has duplicate bc_species values")
    for species_row in species_table.to_dict("records"):
        if not str(species_row["cbm_species"]).strip():
            issues.append(f"species {species_row['bc_species']!r} has no CBM species")
            break
        if species_row["wood_type"] not in {"softwood", "hardwood"}:
            issues.append(
                f"species {species_row['bc_species']!r} has an invalid wood type"
            )
            break


def _integers(frame: pd.DataFrame, column: str, issues: list[str]) -> list[int]:
    """Return integer values, recording a parse failure."""
    try:
        return [int(value) for value in frame[column]]
    except (TypeError, ValueError):
        issues.append(f"{column} contains a non-integer value")
        return []


def _positive_numbers(
    frame: pd.DataFrame, column: str, issues: list[str], *, label: str
) -> None:
    """Require finite positive numbers."""
    try:
        values = [float(value) for value in frame[column]]
    except (TypeError, ValueError):
        issues.append(f"{label} contains a non-numeric value")
        return
    if any(value <= 0 for value in values):
        issues.append(f"{label} must be positive")


def _non_negative_numbers(
    frame: pd.DataFrame, column: str, issues: list[str], *, label: str
) -> None:
    """Require finite non-negative numbers."""
    try:
        values = [float(value) for value in frame[column]]
    except (TypeError, ValueError):
        issues.append(f"{label} contains a non-numeric value")
        return
    if any(value < 0 for value in values):
        issues.append(f"{label} must be non-negative")


def _non_negative_integers(frame: pd.DataFrame, column: str, issues: list[str]) -> None:
    """Require non-negative integer values."""
    values = _integers(frame, column, issues)
    if any(value < 0 for value in values):
        issues.append(f"{column} must be non-negative")


def _land_classes(frame: pd.DataFrame, issues: list[str]) -> None:
    """Require CBM land classes in the documented range."""
    values = _integers(frame, "landclass", issues)
    if any(value < 0 or value > 22 for value in values):
        issues.append("landclass must be between 0 and 22")


def _sha256(path: Path) -> str:
    """Return the SHA-256 digest of a file."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fingerprint(manifest: dict[str, Any]) -> str:
    """Recompute the package fingerprint from manifest fields."""
    table_hashes = manifest.get("table_hashes")
    sources = manifest.get("sources")
    boundaries = manifest.get("boundaries")
    defaults = manifest.get("cbm_defaults")
    if (
        not isinstance(table_hashes, dict)
        or not isinstance(sources, list)
        or not isinstance(boundaries, dict)
        or not isinstance(defaults, dict)
    ):
        return ""
    digest = hashlib.sha256()
    for name in sorted(table_hashes):
        digest.update(name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(table_hashes[name]).encode("ascii"))
        digest.update(b"\0")
    for source in sources:
        if not isinstance(source, dict):
            return ""
        digest.update(str(source.get("path", "")).encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(source.get("sha256", "")).encode("ascii"))
        digest.update(b"\0")
    digest.update(str(boundaries.get("admin", "")).encode("utf-8"))
    digest.update(b"\0")
    digest.update(str(boundaries.get("eco", "")).encode("utf-8"))
    digest.update(b"\0")
    digest.update(str(defaults.get("sha256", "")).encode("ascii"))
    return digest.hexdigest()
