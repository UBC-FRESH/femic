"""Native-grid terrain raster, slope, and zonal-statistic helpers.

P79.3 accepts existing DTM/DEM/DSM rasters and provides a small point-cloud
cell-aggregation API for callers that already hold sample points. It does not
read LAZ/COPC files, classify ground returns, reproject, or resample silently.
"""

from __future__ import annotations

import csv
import json
import math
from collections.abc import Sequence
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import rasterio  # type: ignore[import-untyped]  # rasterio ships without PEP 561 stubs

from femic.lidar.catalog import (
    LIDARBC_NATIVE_CRS,
    LidarCatalogError,
    normalize_bbox_epsg3005,
)

LIDAR_TERRAIN_QA_SCHEMA_VERSION = "femic.lidar.terrain_qa.v1"
DEFAULT_TERRAIN_NODATA = -9999.0
TERRAIN_SLOPE_METHODS: tuple[str, ...] = ("horn",)
TERRAIN_POINT_CLOUD_AGGREGATIONS: tuple[str, ...] = ("min", "max", "mean", "count")
TERRAIN_ZONAL_STATISTICS: tuple[str, ...] = (
    "count",
    "mean",
    "median",
    "min",
    "max",
    "std",
    "sum",
)
TERRAIN_DEPENDENCY_STACK: tuple[str, ...] = (
    "numpy",
    "rasterio",
)
METRE_UNITS = frozenset({"m", "metre", "metres", "meter", "meters"})


class TerrainProcessingError(RuntimeError):
    """Raised when a terrain raster, slope, or zonal operation is invalid."""


@dataclass(frozen=True)
class TerrainRasterMetadata:
    """Normalized metadata for one terrain raster."""

    path: Path
    crs: str
    transform: tuple[float, float, float, float, float, float]
    width: int
    height: int
    resolution_x: float
    resolution_y: float
    nodata: float | None
    dtype: str
    band_count: int
    bounds: tuple[float, float, float, float]

    def to_dict(self) -> dict[str, object]:
        """Return the metadata as a JSON-serializable mapping."""

        return {
            "path": str(self.path),
            "crs": self.crs,
            "transform": list(self.transform),
            "width": self.width,
            "height": self.height,
            "resolution_x": self.resolution_x,
            "resolution_y": self.resolution_y,
            "nodata": self.nodata,
            "dtype": self.dtype,
            "band_count": self.band_count,
            "bounds": list(self.bounds),
        }


@dataclass(frozen=True)
class TerrainRasterResult:
    """One derived terrain raster and its QA summary."""

    product: str
    path: Path
    source_path: Path | None
    metadata: TerrainRasterMetadata
    algorithm: str
    parameters: dict[str, object]
    generated_utc: str
    valid_pixels: int
    nodata_pixels: int
    min_value: float | None
    max_value: float | None
    mean_value: float | None
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        """Return the product result as a JSON-serializable mapping."""

        return {
            "product": self.product,
            "path": str(self.path),
            "source_path": str(self.source_path) if self.source_path else None,
            "metadata": self.metadata.to_dict(),
            "algorithm": self.algorithm,
            "parameters": self.parameters,
            "generated_utc": self.generated_utc,
            "valid_pixels": self.valid_pixels,
            "nodata_pixels": self.nodata_pixels,
            "min_value": self.min_value,
            "max_value": self.max_value,
            "mean_value": self.mean_value,
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class TerrainQaReport:
    """QA report for a terrain-product build."""

    generated_utc: str
    source: TerrainRasterMetadata
    products: tuple[TerrainRasterResult, ...]
    dependency_stack: tuple[str, ...] = TERRAIN_DEPENDENCY_STACK
    warnings: tuple[str, ...] = ()
    schema_version: str = LIDAR_TERRAIN_QA_SCHEMA_VERSION

    @property
    def product_count(self) -> int:
        """Return the number of derived products."""

        return len(self.products)

    def to_dict(self) -> dict[str, object]:
        """Return the QA report as a JSON-serializable mapping."""

        return {
            "schema_version": self.schema_version,
            "generated_utc": self.generated_utc,
            "source": self.source.to_dict(),
            "dependency_stack": list(self.dependency_stack),
            "warnings": list(self.warnings),
            "summary": {"product_count": self.product_count},
            "products": [product.to_dict() for product in self.products],
        }


@dataclass(frozen=True)
class ZonalStatisticRow:
    """Statistics for one positive zone ID."""

    zone_id: int
    count: int
    mean: float | None = None
    median: float | None = None
    minimum: float | None = None
    maximum: float | None = None
    stddev: float | None = None
    total: float | None = None
    area_ha: float | None = None

    def to_dict(self) -> dict[str, object]:
        """Return the zone row as a JSON-serializable mapping."""

        return {
            "zone_id": self.zone_id,
            "count": self.count,
            "mean": self.mean,
            "median": self.median,
            "min": self.minimum,
            "max": self.maximum,
            "std": self.stddev,
            "sum": self.total,
            "area_ha": self.area_ha,
        }


@dataclass(frozen=True)
class ZonalStatisticsResult:
    """Zonal-statistic outcome for one zones/values raster pair."""

    zones_path: Path
    values_path: Path
    crs: str
    resolution_x: float
    resolution_y: float
    statistics: tuple[str, ...]
    rows: tuple[ZonalStatisticRow, ...]
    generated_utc: str
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        """Return the result as a JSON-serializable mapping."""

        return {
            "zones_path": str(self.zones_path),
            "values_path": str(self.values_path),
            "crs": self.crs,
            "resolution_x": self.resolution_x,
            "resolution_y": self.resolution_y,
            "statistics": list(self.statistics),
            "rows": [row.to_dict() for row in self.rows],
            "generated_utc": self.generated_utc,
            "warnings": list(self.warnings),
        }


def inspect_terrain_raster(path: Path) -> TerrainRasterMetadata:
    """Read normalized metadata for one terrain raster without loading values."""

    resolved = path.expanduser().resolve()
    try:
        with rasterio.open(resolved) as source:
            return _metadata_from_dataset(source, resolved)
    except (OSError, rasterio.errors.RasterioIOError) as exc:
        raise TerrainProcessingError(
            f"Unable to read raster {resolved}: {exc}"
        ) from exc


def derive_slope_percent(
    source_path: Path,
    output_path: Path,
    *,
    nodata: float | None = None,
    generated_utc: str | None = None,
) -> TerrainRasterResult:
    """Derive percent slope from a single-band elevation raster.

    The operation preserves the source grid, CRS, and resolution. It requires a
    projected CRS in metres, a north-up transform, and no resampling.
    """

    data, valid, metadata = _read_single_band(source_path)
    _require_projected_metre_grid(metadata)
    elevation = np.where(valid, data, 0.0)
    slope = _horn_slope(
        elevation,
        valid,
        resolution_x=metadata.resolution_x,
        resolution_y=metadata.resolution_y,
    )
    slope_valid = np.isfinite(slope)
    output_nodata = (
        float(nodata)
        if nodata is not None
        else (
            metadata.nodata if metadata.nodata is not None else DEFAULT_TERRAIN_NODATA
        )
    )
    output = np.where(slope_valid, slope, output_nodata).astype(np.float32)
    resolved_output = output_path.expanduser().resolve()
    _write_float_raster(output, resolved_output, metadata, output_nodata)
    stats = _raster_statistics(output, slope_valid)
    return TerrainRasterResult(
        product="slope_percent",
        path=resolved_output,
        source_path=source_path.expanduser().resolve(),
        metadata=inspect_terrain_raster(resolved_output),
        algorithm="horn_3x3",
        parameters={
            "resolution_x": metadata.resolution_x,
            "resolution_y": metadata.resolution_y,
            "edge_handling": "edge_replication",
            "units": "percent_rise",
            "resampling": "none",
        },
        generated_utc=generated_utc or _now(),
        valid_pixels=stats.valid_pixels,
        nodata_pixels=stats.nodata_pixels,
        min_value=stats.minimum,
        max_value=stats.maximum,
        mean_value=stats.mean,
        warnings=(
            "No reprojection or resampling was performed.",
            "Edge pixels use replicated neighbours.",
            "Slope is percent rise (100 * vertical/horizontal).",
        ),
    )


def build_terrain_products(
    source_path: Path,
    output_dir: Path,
    *,
    products: Sequence[str] = ("slope_percent",),
    qa_json_path: Path | None = None,
    qa_csv_path: Path | None = None,
    nodata: float | None = None,
    generated_utc: str | None = None,
) -> TerrainQaReport:
    """Build terrain products and write JSON/CSV QA reports.

    Only ``slope_percent`` is implemented in P79.3. Additional terrain products
    should extend this function rather than creating a parallel pipeline.
    """

    requested = tuple(product.strip() for product in products if product.strip())
    if not requested:
        raise TerrainProcessingError("At least one terrain product must be requested.")
    unsupported = [product for product in requested if product != "slope_percent"]
    if unsupported:
        raise TerrainProcessingError(
            "Unsupported terrain products: " + ", ".join(sorted(unsupported))
        )
    resolved_output = output_dir.expanduser().resolve()
    resolved_output.mkdir(parents=True, exist_ok=True)
    timestamp = generated_utc or _now()
    result = derive_slope_percent(
        source_path,
        resolved_output / "slope_percent.tif",
        nodata=nodata,
        generated_utc=timestamp,
    )
    report = TerrainQaReport(
        generated_utc=timestamp,
        source=inspect_terrain_raster(source_path),
        products=(result,),
        warnings=result.warnings,
    )
    write_terrain_qa_report(
        report,
        qa_json_path or resolved_output / "terrain_qa.json",
    )
    write_terrain_qa_summary_csv(
        report,
        qa_csv_path or resolved_output / "terrain_qa.csv",
    )
    return report


def rasterize_point_cloud(
    points_xyz: Sequence[tuple[float, float, float]],
    *,
    output_path: Path,
    bbox_epsg3005: Sequence[object],
    resolution_m: float,
    crs: str = LIDARBC_NATIVE_CRS,
    aggregation: str = "min",
    nodata: float = DEFAULT_TERRAIN_NODATA,
    generated_utc: str | None = None,
) -> TerrainRasterResult:
    """Rasterize points into a native-grid DTM/DSM-like surface.

    This is a reusable cell-aggregation core, not a ground-classification
    workflow. Use ``min`` for a DTM-like surface, ``max`` for a DSM-like
    surface, or ``mean``/``count`` for diagnostics.
    """

    if aggregation not in TERRAIN_POINT_CLOUD_AGGREGATIONS:
        raise TerrainProcessingError(
            "Unsupported point-cloud aggregation "
            f"{aggregation!r}; expected one of: "
            + ", ".join(TERRAIN_POINT_CLOUD_AGGREGATIONS)
        )
    if crs != LIDARBC_NATIVE_CRS:
        raise TerrainProcessingError(
            f"Point-cloud gridding requires native CRS {LIDARBC_NATIVE_CRS}; "
            f"got {crs!r}."
        )
    if not math.isfinite(resolution_m) or resolution_m <= 0:
        raise TerrainProcessingError("Point-cloud resolution_m must be positive.")
    try:
        minx, miny, maxx, maxy = normalize_bbox_epsg3005(bbox_epsg3005)
    except LidarCatalogError as exc:
        raise TerrainProcessingError(f"Invalid point-cloud AOI: {exc}") from exc
    width = max(1, math.ceil((maxx - minx) / resolution_m))
    height = max(1, math.ceil((maxy - miny) / resolution_m))
    output = np.full((height, width), nodata, dtype=np.float32)
    x_indices: list[int] = []
    y_indices: list[int] = []
    z_values: list[float] = []
    for point in points_xyz:
        if len(point) != 3:
            raise TerrainProcessingError(
                "Each point must contain exactly three values: x, y, z."
            )
        x, y, z = (float(value) for value in point)
        if not all(math.isfinite(value) for value in (x, y, z)):
            continue
        if not (minx <= x < maxx and miny <= y < maxy):
            continue
        column = math.floor((x - minx) / resolution_m)
        row = math.floor((maxy - y) / resolution_m)
        x_indices.append(column)
        y_indices.append(row)
        z_values.append(z)
    if not z_values:
        raise TerrainProcessingError("No finite points fall inside the requested AOI.")
    columns = np.asarray(x_indices, dtype=np.int64)
    rows = np.asarray(y_indices, dtype=np.int64)
    values = np.asarray(z_values, dtype=np.float64)
    if aggregation == "min":
        grid = np.full((height, width), np.inf, dtype=np.float64)
        np.minimum.at(grid, (rows, columns), values)
        output = np.where(np.isfinite(grid), grid, nodata).astype(np.float32)
    elif aggregation == "max":
        grid = np.full((height, width), -np.inf, dtype=np.float64)
        np.maximum.at(grid, (rows, columns), values)
        output = np.where(np.isfinite(grid), grid, nodata).astype(np.float32)
    elif aggregation == "mean":
        totals = np.zeros((height, width), dtype=np.float64)
        counts = np.zeros((height, width), dtype=np.int64)
        np.add.at(totals, (rows, columns), values)
        np.add.at(counts, (rows, columns), 1)
        mean_grid = np.divide(
            totals,
            counts,
            out=np.full_like(totals, nodata),
            where=counts > 0,
        )
        output = mean_grid.astype(np.float32)
    else:
        counts = np.zeros((height, width), dtype=np.int64)
        np.add.at(counts, (rows, columns), 1)
        output = np.where(counts > 0, counts, nodata).astype(np.float32)
    transform = rasterio.transform.from_origin(minx, maxy, resolution_m, resolution_m)
    metadata = TerrainRasterMetadata(
        path=output_path.expanduser().resolve(),
        crs=crs,
        transform=(
            float(transform.a),
            float(transform.b),
            float(transform.c),
            float(transform.d),
            float(transform.e),
            float(transform.f),
        ),
        width=width,
        height=height,
        resolution_x=resolution_m,
        resolution_y=resolution_m,
        nodata=nodata,
        dtype="float32",
        band_count=1,
        bounds=(minx, miny, maxx, maxy),
    )
    resolved_output = output_path.expanduser().resolve()
    _write_float_raster(output, resolved_output, metadata, nodata)
    stats = _raster_statistics(output, output != nodata)
    return TerrainRasterResult(
        product=f"point_cloud_{aggregation}",
        path=resolved_output,
        source_path=None,
        metadata=inspect_terrain_raster(resolved_output),
        algorithm=f"point_cloud_cell_{aggregation}",
        parameters={
            "aggregation": aggregation,
            "resolution_m": resolution_m,
            "bbox_epsg3005": [minx, miny, maxx, maxy],
            "point_count": len(points_xyz),
            "rasterized_point_count": len(z_values),
            "resampling": "none",
        },
        generated_utc=generated_utc or _now(),
        valid_pixels=stats.valid_pixels,
        nodata_pixels=stats.nodata_pixels,
        min_value=stats.minimum,
        max_value=stats.maximum,
        mean_value=stats.mean,
        warnings=(
            "Cell aggregation only; no ground classification or interpolation.",
            "No reprojection or resampling was performed.",
        ),
    )


def compute_zonal_statistics(
    zones_path: Path,
    values_path: Path,
    *,
    statistics: Sequence[str] = ("count", "mean", "median", "min", "max", "std"),
    generated_utc: str | None = None,
) -> ZonalStatisticsResult:
    """Compute zonal statistics over aligned zones and values rasters.

    Zones must be positive integer IDs on exactly the same grid as values. The
    helper never resamples or reprojects either input.
    """

    requested = tuple(stat.strip() for stat in statistics if stat.strip())
    if not requested:
        raise TerrainProcessingError("At least one zonal statistic must be requested.")
    unsupported = [stat for stat in requested if stat not in TERRAIN_ZONAL_STATISTICS]
    if unsupported:
        raise TerrainProcessingError(
            "Unsupported zonal statistics: " + ", ".join(sorted(unsupported))
        )
    zones_data, zones_valid, zones_meta = _read_single_band(zones_path)
    values_data, values_valid, values_meta = _read_single_band(values_path)
    _require_aligned_grids(zones_meta, values_meta)
    if not np.allclose(zones_data[zones_valid], np.rint(zones_data[zones_valid])):
        raise TerrainProcessingError("Zones raster must contain integer zone IDs.")
    zone_values = np.where(zones_valid, np.rint(zones_data), 0).astype(np.int64)
    valid_zone_mask = zones_valid & (zone_values > 0)
    zone_ids = sorted(int(value) for value in np.unique(zone_values[valid_zone_mask]))
    projected_metres = _is_projected_metres(zones_meta)
    pixel_area = abs(
        zones_meta.transform[0] * zones_meta.transform[4]
        - zones_meta.transform[1] * zones_meta.transform[3]
    )
    warnings: list[str] = [
        "No reprojection or resampling was performed.",
    ]
    if not projected_metres:
        warnings.append(
            "Area hectares are omitted because the CRS is not projected metres."
        )
    rows: list[ZonalStatisticRow] = []
    for zone_id in zone_ids:
        mask = valid_zone_mask & (zone_values == zone_id) & values_valid
        values = values_data[mask]
        row = ZonalStatisticRow(zone_id=zone_id, count=int(values.size))
        if values.size:
            if "mean" in requested:
                row = replace(row, mean=float(np.mean(values)))
            if "median" in requested:
                row = replace(row, median=float(np.median(values)))
            if "min" in requested:
                row = replace(row, minimum=float(np.min(values)))
            if "max" in requested:
                row = replace(row, maximum=float(np.max(values)))
            if "std" in requested:
                row = replace(row, stddev=float(np.std(values)))
            if "sum" in requested:
                row = replace(row, total=float(np.sum(values)))
        if projected_metres and values.size:
            row = replace(row, area_ha=float(values.size * pixel_area / 10_000.0))
        rows.append(row)
    return ZonalStatisticsResult(
        zones_path=zones_path.expanduser().resolve(),
        values_path=values_path.expanduser().resolve(),
        crs=zones_meta.crs,
        resolution_x=zones_meta.resolution_x,
        resolution_y=zones_meta.resolution_y,
        statistics=requested,
        rows=tuple(rows),
        generated_utc=generated_utc or _now(),
        warnings=tuple(warnings),
    )


def write_terrain_qa_report(report: TerrainQaReport, path: Path) -> Path:
    """Write a terrain QA report as pretty-printed JSON."""

    resolved = path.expanduser().resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(
        json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return resolved


def write_terrain_qa_summary_csv(report: TerrainQaReport, path: Path) -> Path:
    """Write a one-row-per-product terrain QA summary CSV."""

    resolved = path.expanduser().resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    with resolved.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "product",
                "path",
                "algorithm",
                "crs",
                "resolution_x",
                "resolution_y",
                "valid_pixels",
                "nodata_pixels",
                "min_value",
                "max_value",
                "mean_value",
            ]
        )
        for product in report.products:
            writer.writerow(
                [
                    product.product,
                    product.path,
                    product.algorithm,
                    product.metadata.crs,
                    product.metadata.resolution_x,
                    product.metadata.resolution_y,
                    product.valid_pixels,
                    product.nodata_pixels,
                    product.min_value,
                    product.max_value,
                    product.mean_value,
                ]
            )
    return resolved


@dataclass(frozen=True)
class _RasterStatistics:
    valid_pixels: int
    nodata_pixels: int
    minimum: float | None
    maximum: float | None
    mean: float | None


def _read_single_band(
    path: Path,
) -> tuple[np.ndarray, np.ndarray, TerrainRasterMetadata]:
    resolved = path.expanduser().resolve()
    try:
        with rasterio.open(resolved) as source:
            metadata = _metadata_from_dataset(source, resolved)
            if metadata.band_count != 1:
                raise TerrainProcessingError(
                    f"Terrain raster must have exactly one band: {resolved}"
                )
            masked = source.read(1, masked=True)
    except (OSError, rasterio.errors.RasterioIOError) as exc:
        raise TerrainProcessingError(
            f"Unable to read raster {resolved}: {exc}"
        ) from exc
    values = np.asarray(masked.filled(np.nan), dtype=np.float64)
    mask = np.ma.getmaskarray(masked)
    valid = ~mask & np.isfinite(values)
    return values, valid, metadata


def _metadata_from_dataset(source: Any, path: Path) -> TerrainRasterMetadata:
    # rasterio dataset readers are untyped; Any is confined to this adapter.
    crs = source.crs
    transform = source.transform
    bounds = source.bounds
    resolution = source.res
    dtype = str(source.dtypes[0])
    return TerrainRasterMetadata(
        path=path,
        crs=crs.to_string() if crs is not None else "",
        transform=(
            float(transform.a),
            float(transform.b),
            float(transform.c),
            float(transform.d),
            float(transform.e),
            float(transform.f),
        ),
        width=int(source.width),
        height=int(source.height),
        resolution_x=float(resolution[0]),
        resolution_y=float(resolution[1]),
        nodata=(float(source.nodata) if source.nodata is not None else None),
        dtype=dtype,
        band_count=int(source.count),
        bounds=(
            float(bounds.left),
            float(bounds.bottom),
            float(bounds.right),
            float(bounds.top),
        ),
    )


def _require_projected_metre_grid(metadata: TerrainRasterMetadata) -> None:
    if not metadata.crs:
        raise TerrainProcessingError("Terrain raster has no CRS.")
    if not _is_projected_metres(metadata):
        raise TerrainProcessingError(
            f"Slope requires a projected CRS with metre units; got {metadata.crs!r}."
        )
    if abs(metadata.transform[1]) > 1e-12 or abs(metadata.transform[3]) > 1e-12:
        raise TerrainProcessingError("Slope requires a north-up, unrotated raster.")
    if metadata.resolution_x <= 0 or metadata.resolution_y <= 0:
        raise TerrainProcessingError("Slope requires positive pixel resolution.")


def _is_projected_metres(metadata: TerrainRasterMetadata) -> bool:
    if not metadata.crs:
        return False
    try:
        crs = rasterio.crs.CRS.from_user_input(metadata.crs)
    except (rasterio.errors.CRSError, TypeError, ValueError):
        return False
    if not crs.is_projected:
        return False
    units = (crs.linear_units or "").lower()
    return units in METRE_UNITS


def _require_aligned_grids(
    zones: TerrainRasterMetadata,
    values: TerrainRasterMetadata,
) -> None:
    if (
        zones.width != values.width
        or zones.height != values.height
        or zones.crs != values.crs
        or zones.transform != values.transform
    ):
        raise TerrainProcessingError(
            "Zones and values rasters must share exactly the same grid and CRS; "
            "resampling is not allowed."
        )


def _horn_slope(
    elevation: np.ndarray,
    valid: np.ndarray,
    *,
    resolution_x: float,
    resolution_y: float,
) -> np.ndarray:
    padded = np.pad(elevation, 1, mode="edge")
    padded_valid = np.pad(valid, 1, mode="edge")
    z1 = padded[:-2, :-2]
    z2 = padded[:-2, 1:-1]
    z3 = padded[:-2, 2:]
    z4 = padded[1:-1, :-2]
    z6 = padded[1:-1, 2:]
    z7 = padded[2:, :-2]
    z8 = padded[2:, 1:-1]
    z9 = padded[2:, 2:]
    neighbour_valid = (
        padded_valid[:-2, :-2]
        & padded_valid[:-2, 1:-1]
        & padded_valid[:-2, 2:]
        & padded_valid[1:-1, :-2]
        & padded_valid[1:-1, 2:]
        & padded_valid[2:, :-2]
        & padded_valid[2:, 1:-1]
        & padded_valid[2:, 2:]
    )
    dzdx = ((z3 + 2.0 * z6 + z9) - (z1 + 2.0 * z4 + z7)) / (8.0 * resolution_x)
    dzdy = ((z7 + 2.0 * z8 + z9) - (z1 + 2.0 * z2 + z3)) / (8.0 * resolution_y)
    slope = 100.0 * np.sqrt(dzdx * dzdx + dzdy * dzdy)
    result = np.full(elevation.shape, np.nan, dtype=np.float64)
    result[valid & neighbour_valid] = slope[valid & neighbour_valid]
    return result


def _raster_statistics(values: np.ndarray, valid: np.ndarray) -> _RasterStatistics:
    selected = values[valid]
    if selected.size == 0:
        return _RasterStatistics(
            valid_pixels=0,
            nodata_pixels=int(values.size),
            minimum=None,
            maximum=None,
            mean=None,
        )
    return _RasterStatistics(
        valid_pixels=int(selected.size),
        nodata_pixels=int(values.size - selected.size),
        minimum=float(np.min(selected)),
        maximum=float(np.max(selected)),
        mean=float(np.mean(selected)),
    )


def _write_float_raster(
    values: np.ndarray,
    path: Path,
    metadata: TerrainRasterMetadata,
    nodata: float,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    profile = {
        "driver": "GTiff",
        "dtype": "float32",
        "count": 1,
        "width": metadata.width,
        "height": metadata.height,
        "crs": metadata.crs,
        "transform": rasterio.transform.Affine(*metadata.transform),
        "nodata": nodata,
        "compress": "deflate",
    }
    with rasterio.open(path, "w", **profile) as destination:
        destination.write(values.astype(np.float32), 1)


def _now() -> str:
    return datetime.now(UTC).isoformat()
