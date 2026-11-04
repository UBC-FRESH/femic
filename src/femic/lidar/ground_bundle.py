"""Read-only validation for the optional ground-classification sidecar bundle.

The bundle is produced by ``fresh-urban-forest-lab`` and is intentionally
independent of FEMIC. This module validates the versioned manifest, the QA
summary, and the file hashes. It optionally inspects the LAZ extra dimensions
when ``laspy`` is installed; ``laspy`` is not a hard FEMIC dependency.

Contract:
- ``ground.laz`` — LAZ copy with ``is_ground``, ``hag``, ``is_low``, and ``ref_class``;
- ``manifest.json`` — ``femic.ground-bundle.v1``;
- ``qa.json`` — ``femic.ground-qa.v1``.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

GROUND_BUNDLE_SCHEMA_VERSION = "femic.ground-bundle.v1"
GROUND_QA_SCHEMA_VERSION = "femic.ground-qa.v1"
GROUND_LAZ_NAME = "ground.laz"
GROUND_MANIFEST_NAME = "manifest.json"
GROUND_QA_NAME = "qa.json"
GROUND_EXTRA_DIMENSIONS: tuple[str, ...] = (
    "is_ground",
    "hag",
    "is_low",
    "ref_class",
)
GROUND_REQUIRED_QA_FIELDS: tuple[str, ...] = (
    "point_count",
    "ground_count",
    "low_point_count",
    "sor_removed",
    "seed_count",
    "iterations",
    "hag_percentiles_m",
    "warnings",
)


class GroundBundleError(RuntimeError):
    """Raised when a ground bundle is missing, malformed, or inconsistent."""


@dataclass(frozen=True)
class GroundBundlePointInspection:
    """Optional low-level LAZ inspection.

    Attributes
    ----------
    point_count : int
        Point count reported by the LAZ header.
    dimensions : tuple of str
        Dimension names in the LAZ point format.
    crs : str or None
        CRS reported by the header, or ``None``.
    """

    point_count: int
    dimensions: tuple[str, ...]
    crs: str | None


@dataclass(frozen=True)
class GroundBundle:
    """Validated ground-bundle metadata.

    Attributes
    ----------
    root : Path
        Bundle directory.
    ground_laz : Path
        Ground LAZ path.
    manifest_path : Path
        Manifest path.
    qa_path : Path
        QA summary path.
    manifest : dict
        Parsed manifest.
    qa : dict
        Parsed QA summary.
    point_count : int
        Validated point count.
    ground_count : int
        Predicted-ground count.
    low_point_count : int
        Low-point count.
    point_inspection : GroundBundlePointInspection or None
        Optional LAZ inspection. ``None`` when inspection is disabled or ``laspy`` is
        unavailable.
    warnings : tuple of str
        Non-fatal validation warnings.
    """

    root: Path
    ground_laz: Path
    manifest_path: Path
    qa_path: Path
    manifest: dict[str, object]
    qa: dict[str, object]
    point_count: int
    ground_count: int
    low_point_count: int
    point_inspection: GroundBundlePointInspection | None
    warnings: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-friendly summary.

        Returns
        -------
        dict
            Paths, schemas, counts, optional inspection, and warnings.
        """
        return {
            "root": str(self.root),
            "ground_laz": str(self.ground_laz),
            "manifest_path": str(self.manifest_path),
            "qa_path": str(self.qa_path),
            "bundle_schema_version": self.manifest.get("schema_version"),
            "qa_schema_version": self.qa.get("schema_version"),
            "point_count": self.point_count,
            "ground_count": self.ground_count,
            "low_point_count": self.low_point_count,
            "point_inspection": (
                {
                    "point_count": self.point_inspection.point_count,
                    "dimensions": list(self.point_inspection.dimensions),
                    "crs": self.point_inspection.crs,
                }
                if self.point_inspection is not None
                else None
            ),
            "warnings": list(self.warnings),
        }


def _sha256_file(path: Path) -> str:
    """Compute the SHA-256 digest of a file.

    Parameters
    ----------
    path : Path
        File to hash.

    Returns
    -------
    str
        Lower-case hexadecimal digest.
    """
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_mapping(path: Path, label: str) -> dict[str, object]:
    """Read a JSON object.

    Parameters
    ----------
    path : Path
        JSON path.
    label : str
        Human-readable label for errors.

    Returns
    -------
    dict
        Parsed object.

    Raises
    ------
    GroundBundleError
        When the file is missing, invalid JSON, or not an object.
    """
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise GroundBundleError(f"{label} does not exist: {path}") from exc
    except json.JSONDecodeError as exc:
        raise GroundBundleError(f"{label} is not valid JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise GroundBundleError(f"{label} must be a JSON object: {path}")
    return payload


def _mapping(parent: Mapping[str, object], key: str) -> dict[str, object]:
    """Return a required child object.

    Parameters
    ----------
    parent : mapping
        Parent object.
    key : str
        Child key.

    Returns
    -------
    dict
        Child object.

    Raises
    ------
    GroundBundleError
        When the child is missing or not an object.
    """
    value = parent.get(key)
    if not isinstance(value, dict):
        raise GroundBundleError(f"manifest field '{key}' must be an object")
    return value


def _string(parent: Mapping[str, object], key: str) -> str:
    """Return a required string field.

    Parameters
    ----------
    parent : mapping
        Parent object.
    key : str
        Field key.

    Returns
    -------
    str
        Field value.

    Raises
    ------
    GroundBundleError
        When the field is missing or not a string.
    """
    value = parent.get(key)
    if not isinstance(value, str) or not value:
        raise GroundBundleError(f"manifest field '{key}' must be a non-empty string")
    return value


def _integer(parent: Mapping[str, object], key: str) -> int:
    """Return a required integer field.

    Parameters
    ----------
    parent : mapping
        Parent object.
    key : str
        Field key.

    Returns
    -------
    int
        Field value.

    Raises
    ------
    GroundBundleError
        When the field is missing or not an integer.
    """
    value = parent.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise GroundBundleError(f"QA field '{key}' must be an integer")
    return value


def _inspect_points(
    path: Path,
    expected_count: int,
) -> tuple[GroundBundlePointInspection | None, list[str]]:
    """Inspect the LAZ header and extra dimensions.

    Parameters
    ----------
    path : Path
        Ground LAZ path.
    expected_count : int
        Expected point count from the QA summary.

    Returns
    -------
    tuple
        ``(inspection, warnings)``.

    Raises
    ------
    GroundBundleError
        When the LAZ cannot be opened or is missing required dimensions.
    """
    warnings: list[str] = []
    try:
        import laspy  # type: ignore[import-untyped]
    except ImportError:
        warnings.append("laspy is not installed; LAZ point inspection skipped")
        return None, warnings
    try:
        with laspy.open(path) as reader:
            header = reader.header
            dimensions = tuple(
                str(name) for name in header.point_format.dimension_names
            )
            parsed_crs = header.parse_crs()
            crs = str(parsed_crs) if parsed_crs is not None else None
            point_count = int(header.point_count)
    except Exception as exc:
        raise GroundBundleError(f"cannot read ground LAZ: {path}: {exc}") from exc
    missing = [name for name in GROUND_EXTRA_DIMENSIONS if name not in dimensions]
    if missing:
        raise GroundBundleError(
            "ground LAZ is missing required dimensions: " + ", ".join(missing)
        )
    if point_count != expected_count:
        raise GroundBundleError(
            f"ground LAZ point count {point_count} does not match QA {expected_count}"
        )
    return GroundBundlePointInspection(
        point_count=point_count,
        dimensions=dimensions,
        crs=crs,
    ), warnings


def read_ground_bundle(
    path: Path,
    *,
    inspect_points: bool = True,
) -> GroundBundle:
    """Validate and read a sidecar ground bundle.

    Parameters
    ----------
    path : Path
        Bundle directory or manifest path.
    inspect_points : bool
        Inspect the LAZ header and extra dimensions when ``laspy`` is available.

    Returns
    -------
    GroundBundle
        Validated bundle metadata.

    Raises
    ------
    GroundBundleError
        When required files, schema versions, hashes, counts, or dimensions are invalid.
    """
    root = path if path.is_dir() else path.parent
    manifest_path = root / GROUND_MANIFEST_NAME
    qa_path = root / GROUND_QA_NAME
    ground_laz = root / GROUND_LAZ_NAME
    manifest = _read_mapping(manifest_path, "ground manifest")
    qa = _read_mapping(qa_path, "ground QA")

    if manifest.get("schema_version") != GROUND_BUNDLE_SCHEMA_VERSION:
        raise GroundBundleError(
            f"unsupported bundle schema: {manifest.get('schema_version')!r}"
        )
    if qa.get("schema_version") != GROUND_QA_SCHEMA_VERSION:
        raise GroundBundleError(f"unsupported QA schema: {qa.get('schema_version')!r}")

    output = _mapping(manifest, "output")
    qa_ref = _mapping(manifest, "qa")
    if _string(output, "path") != GROUND_LAZ_NAME:
        raise GroundBundleError(f"output.path must be '{GROUND_LAZ_NAME}'")
    if _string(qa_ref, "path") != GROUND_QA_NAME:
        raise GroundBundleError(f"qa.path must be '{GROUND_QA_NAME}'")
    if not ground_laz.is_file():
        raise GroundBundleError(f"ground LAZ does not exist: {ground_laz}")

    output_hash = _string(output, "sha256")
    if _sha256_file(ground_laz) != output_hash.lower():
        raise GroundBundleError("ground LAZ SHA-256 does not match the manifest")
    qa_hash = _string(qa_ref, "sha256")
    if _sha256_file(qa_path) != qa_hash.lower():
        raise GroundBundleError("QA SHA-256 does not match the manifest")
    if _string(manifest, "parameter_sha256") != _string(qa, "parameter_sha256"):
        raise GroundBundleError("parameter SHA-256 differs between manifest and QA")

    source = _mapping(manifest, "source")
    source_count = _integer(source, "point_count")
    output_count = _integer(output, "point_count")
    qa_count = _integer(qa, "point_count")
    if not (source_count == output_count == qa_count):
        raise GroundBundleError(
            "point counts differ: "
            f"source={source_count}, output={output_count}, qa={qa_count}"
        )
    for field in GROUND_REQUIRED_QA_FIELDS:
        if field not in qa:
            raise GroundBundleError(f"QA is missing required field '{field}'")

    ground_count = _integer(qa, "ground_count")
    low_point_count = _integer(qa, "low_point_count")
    warnings: list[str] = []
    point_inspection: GroundBundlePointInspection | None = None
    if inspect_points:
        point_inspection, inspection_warnings = _inspect_points(ground_laz, qa_count)
        warnings.extend(inspection_warnings)

    return GroundBundle(
        root=root,
        ground_laz=ground_laz,
        manifest_path=manifest_path,
        qa_path=qa_path,
        manifest=manifest,
        qa=qa,
        point_count=qa_count,
        ground_count=ground_count,
        low_point_count=low_point_count,
        point_inspection=point_inspection,
        warnings=tuple(warnings),
    )
