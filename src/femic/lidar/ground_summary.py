"""Optional block-level summaries for a validated ground bundle.

This consumer reads a ground bundle, joins the HAG values to planning polygons,
and writes a small CSV plus a manifest. It is opt-in and does not change any
default FEMIC product. Polygons and points must share a CRS; there is no silent
reprojection.
"""

from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import geopandas as gpd  # type: ignore[import-untyped]
import numpy as np
from pyproj import CRS
from shapely import contains_xy  # type: ignore[import-untyped]

from femic.lidar.ground_bundle import GroundBundleError, read_ground_bundle

GROUND_SUMMARY_SCHEMA_VERSION = "femic.ground-summary.v1"


class GroundSummaryError(RuntimeError):
    """Raised when a ground-bundle summary input or output is invalid."""


@dataclass(frozen=True)
class GroundSummaryRow:
    """One polygon summary.

    Attributes
    ----------
    polygon_id : str
        Polygon identifier.
    point_count : int
        Points inside the polygon.
    ground_count : int
        Predicted-ground points inside the polygon.
    ground_fraction : float
        Ground count divided by point count.
    low_count : int
        Low-point-flagged points inside the polygon.
    low_fraction : float
        Low count divided by point count.
    hag_mean : float or None
        Mean finite HAG, in metres.
    hag_p50 : float or None
        Median finite HAG.
    hag_p95 : float or None
        95th percentile finite HAG.
    hag_max : float or None
        Maximum finite HAG.
    """

    polygon_id: str
    point_count: int
    ground_count: int
    ground_fraction: float
    low_count: int
    low_fraction: float
    hag_mean: float | None
    hag_p50: float | None
    hag_p95: float | None
    hag_max: float | None

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-friendly row.

        Returns
        -------
        dict
            Row fields.
        """
        return {
            "polygon_id": self.polygon_id,
            "point_count": self.point_count,
            "ground_count": self.ground_count,
            "ground_fraction": self.ground_fraction,
            "low_count": self.low_count,
            "low_fraction": self.low_fraction,
            "hag_mean": self.hag_mean,
            "hag_p50": self.hag_p50,
            "hag_p95": self.hag_p95,
            "hag_max": self.hag_max,
        }


@dataclass(frozen=True)
class GroundSummaryResult:
    """Result of a ground-bundle summary.

    Attributes
    ----------
    csv_path : Path
        Written CSV.
    manifest_path : Path
        Written manifest.
    rows : tuple of GroundSummaryRow
        One row per polygon.
    warnings : tuple of str
        Non-fatal warnings.
    """

    csv_path: Path
    manifest_path: Path
    rows: tuple[GroundSummaryRow, ...]
    warnings: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-friendly summary.

        Returns
        -------
        dict
            Paths, row count, rows, and warnings.
        """
        return {
            "csv_path": str(self.csv_path),
            "manifest_path": str(self.manifest_path),
            "row_count": len(self.rows),
            "rows": [row.to_dict() for row in self.rows],
            "warnings": list(self.warnings),
        }


def _sha256_file(path: Path) -> str:
    """Compute a file SHA-256.

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


def _utc_now() -> str:
    """Return an ISO UTC timestamp.

    Returns
    -------
    str
        Timestamp with a trailing ``Z``.
    """
    return (
        dt.datetime.now(dt.UTC)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _read_points(
    path: Path,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Read the arrays needed for a polygon summary.

    Parameters
    ----------
    path : Path
        Ground LAZ path.

    Returns
    -------
    tuple
        ``(x, y, hag, is_ground, is_low)`` arrays.

    Raises
    ------
    GroundSummaryError
        When ``laspy`` is unavailable or the dimensions are missing.
    """
    try:
        import laspy  # type: ignore[import-untyped]
    except ImportError as exc:
        raise GroundSummaryError(
            "laspy is required for ground summaries; install femic[lidar]"
        ) from exc
    try:
        las = laspy.read(path)
    except Exception as exc:
        raise GroundSummaryError(f"cannot read ground LAZ: {path}: {exc}") from exc
    missing = [
        name
        for name in ("hag", "is_ground", "is_low")
        if name not in las.point_format.dimension_names
    ]
    if missing:
        raise GroundSummaryError(
            "ground LAZ is missing required dimensions: " + ", ".join(missing)
        )
    return (
        np.asarray(las.x, dtype=np.float64),
        np.asarray(las.y, dtype=np.float64),
        np.asarray(las.hag, dtype=np.float64),
        np.asarray(las.is_ground, dtype=np.bool_),
        np.asarray(las.is_low, dtype=np.bool_),
    )


def _summary_row(
    polygon_id: str,
    x: np.ndarray,
    y: np.ndarray,
    hag: np.ndarray,
    is_ground: np.ndarray,
    is_low: np.ndarray,
    polygon: object,
) -> GroundSummaryRow:
    """Summarize one polygon.

    Parameters
    ----------
    polygon_id : str
        Polygon identifier.
    x, y, hag : numpy.ndarray
        Point arrays.
    is_ground, is_low : numpy.ndarray
        Boolean point flags.
    polygon : object
        Shapely polygon.

    Returns
    -------
    GroundSummaryRow
        Polygon summary.
    """
    inside = contains_xy(polygon, x, y)  # type: ignore[arg-type]
    count = int(np.count_nonzero(inside))
    if count == 0:
        return GroundSummaryRow(
            polygon_id=polygon_id,
            point_count=0,
            ground_count=0,
            ground_fraction=0.0,
            low_count=0,
            low_fraction=0.0,
            hag_mean=None,
            hag_p50=None,
            hag_p95=None,
            hag_max=None,
        )
    ground_count = int(np.count_nonzero(is_ground[inside]))
    low_count = int(np.count_nonzero(is_low[inside]))
    values = hag[inside]
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        mean = p50 = p95 = maximum = None
    else:
        mean = round(float(np.mean(finite)), 4)
        p50 = round(float(np.percentile(finite, 50)), 4)
        p95 = round(float(np.percentile(finite, 95)), 4)
        maximum = round(float(np.max(finite)), 4)
    return GroundSummaryRow(
        polygon_id=polygon_id,
        point_count=count,
        ground_count=ground_count,
        ground_fraction=round(ground_count / count, 6),
        low_count=low_count,
        low_fraction=round(low_count / count, 6),
        hag_mean=mean,
        hag_p50=p50,
        hag_p95=p95,
        hag_max=maximum,
    )


def _horizontal_crs(value: str) -> CRS:
    """Return the horizontal component of a CRS.

    Parameters
    ----------
    value : str
        CRS string or authority code.

    Returns
    -------
    pyproj.CRS
        Horizontal CRS, with any vertical component removed.
    """
    crs = CRS.from_user_input(value)
    return crs.sub_crs_list[0] if crs.is_compound else crs


def summarize_ground_bundle(
    bundle_dir: Path,
    polygons_path: Path,
    out_csv: Path,
    *,
    id_field: str,
    overwrite: bool = False,
) -> GroundSummaryResult:
    """Summarize a validated ground bundle over polygons.

    Parameters
    ----------
    bundle_dir : Path
        Ground-bundle directory.
    polygons_path : Path
        Polygon layer readable by geopandas.
    out_csv : Path
        Destination CSV.
    id_field : str
        Polygon identifier field.
    overwrite : bool
        Replace an existing CSV and manifest.

    Returns
    -------
    GroundSummaryResult
        CSV/manifest paths, rows, and warnings.

    Raises
    ------
    GroundSummaryError
        When the bundle, polygons, CRS, or output are invalid.
    """
    manifest_path = out_csv.with_suffix(".manifest.json")
    if not overwrite and (out_csv.exists() or manifest_path.exists()):
        raise GroundSummaryError(f"output exists: {out_csv} or {manifest_path}")
    try:
        bundle = read_ground_bundle(bundle_dir, inspect_points=True)
    except GroundBundleError as exc:
        raise GroundSummaryError(str(exc)) from exc
    if bundle.point_inspection is None:
        raise GroundSummaryError(
            "LAZ point inspection is required; install femic[lidar]"
        )
    polygons = gpd.read_file(polygons_path)
    if id_field not in polygons.columns:
        raise GroundSummaryError(f"polygon layer is missing id field '{id_field}'")
    if polygons.crs is None:
        raise GroundSummaryError("polygon layer has no CRS")
    if bundle.point_inspection.crs is not None:
        point_crs = _horizontal_crs(bundle.point_inspection.crs)
        polygon_crs = _horizontal_crs(polygons.crs)
        if not point_crs.equals(polygon_crs):
            raise GroundSummaryError(
                "point and polygon CRS differ; reproject explicitly before summarizing"
            )

    x, y, hag, is_ground, is_low = _read_points(bundle.ground_laz)
    rows: list[GroundSummaryRow] = []
    warnings: list[str] = []
    for record in polygons.itertuples(index=False):
        polygon_id = str(getattr(record, id_field))
        geometry = getattr(record, "geometry")
        row = _summary_row(polygon_id, x, y, hag, is_ground, is_low, geometry)
        rows.append(row)
        if row.point_count == 0:
            warnings.append(f"polygon '{polygon_id}' has no points")

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=list(rows[0].to_dict()) if rows else []
        )
        if rows:
            writer.writeheader()
            writer.writerows(row.to_dict() for row in rows)

    output_manifest = bundle.manifest.get("output")
    ground_sha256 = (
        output_manifest.get("sha256") if isinstance(output_manifest, dict) else None
    )
    manifest: dict[str, object] = {
        "schema_version": GROUND_SUMMARY_SCHEMA_VERSION,
        "created_utc": _utc_now(),
        "bundle": {
            "root": str(bundle.root),
            "manifest_schema_version": bundle.manifest.get("schema_version"),
            "qa_schema_version": bundle.qa.get("schema_version"),
            "parameter_sha256": bundle.manifest.get("parameter_sha256"),
            "ground_sha256": ground_sha256,
        },
        "polygons": {
            "path": polygons_path.name,
            "sha256": _sha256_file(polygons_path),
            "id_field": id_field,
            "feature_count": len(polygons),
        },
        "output_csv": {"path": out_csv.name, "sha256": _sha256_file(out_csv)},
        "row_count": len(rows),
        "warnings": warnings,
        "crs": str(polygons.crs),
        "note": (
            "HAG statistics describe the predicted surface, not field-validated ground "
            "accuracy."
        ),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return GroundSummaryResult(
        csv_path=out_csv,
        manifest_path=manifest_path,
        rows=tuple(rows),
        warnings=tuple(warnings),
    )
