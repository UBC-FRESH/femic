"""Native-resolution CHM, canopy structure, and VRI uncertainty helpers.

P79.7 derives a canopy height model from aligned DSM/DEM rasters, summarizes
canopy height and cover, and compares CHM evidence with VRI inventory fields.
It does not reproject, resample, segment individual trees, or claim field-level
inventory accuracy.
"""

from __future__ import annotations

import csv
import json
import math
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import geopandas as gpd  # type: ignore[import-untyped]
import numpy as np
import rasterio  # type: ignore[import-untyped]  # rasterio ships without PEP 561 stubs
import rasterio.mask  # type: ignore[import-untyped]

from femic.lidar.terrain import (
    DEFAULT_TERRAIN_NODATA,
    TerrainRasterMetadata,
    read_terrain_grid,
    require_projected_metre_grid,
)

CANOPY_QA_SCHEMA_VERSION = "femic.lidar.canopy_qa.v1"
CANOPY_STRUCTURE_SCHEMA_VERSION = "femic.lidar.canopy_structure.v1"
DEFAULT_CANOPY_THRESHOLDS: tuple[float, ...] = (2.0, 5.0, 10.0, 20.0)
DEFAULT_CANOPY_COVER_THRESHOLD_M = 2.0
DEFAULT_VRI_HEIGHT_FIELD = "proj_height_1"
DEFAULT_VRI_COVER_FIELD = "crown_closure"
DEFAULT_VRI_ID_FIELD = "feature_id"
CANOPY_CAVEATS: tuple[str, ...] = (
    (
        "CHM is DSM minus DEM on exactly aligned native grids. It is not a "
        "field inventory."
    ),
    ("DSM and DEM must share the same CRS, transform, resolution, and vertical datum."),
    "No reprojection or resampling is performed.",
    ("VRI comparisons are uncertainty evidence, not a field-accuracy claim."),
)


class CanopyProcessingError(RuntimeError):
    """Raised when canopy inputs, grids, or VRI comparisons are invalid."""


@dataclass(frozen=True)
class CanopyHeightResult:
    """Derived CHM raster and its QA summary."""

    path: Path
    dsm_path: Path
    dem_path: Path
    metadata: TerrainRasterMetadata
    dsm_metadata: TerrainRasterMetadata
    dem_metadata: TerrainRasterMetadata
    vertical_datum: str | None
    generated_utc: str
    valid_pixels: int
    nodata_pixels: int
    negative_pixels: int
    clamped_negative: bool
    height_metrics: dict[str, object]
    cover_fractions: dict[str, float]
    valid_area_ha: float
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        """Return the CHM result as a JSON-serializable mapping."""

        return {
            "path": str(self.path),
            "dsm_path": str(self.dsm_path),
            "dem_path": str(self.dem_path),
            "metadata": self.metadata.to_dict(),
            "dsm_metadata": self.dsm_metadata.to_dict(),
            "dem_metadata": self.dem_metadata.to_dict(),
            "vertical_datum": self.vertical_datum,
            "generated_utc": self.generated_utc,
            "valid_pixels": self.valid_pixels,
            "nodata_pixels": self.nodata_pixels,
            "negative_pixels": self.negative_pixels,
            "clamped_negative": self.clamped_negative,
            "height_metrics": self.height_metrics,
            "cover_fractions": self.cover_fractions,
            "valid_area_ha": self.valid_area_ha,
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class CanopyStructureResult:
    """Canopy height and cover summary for one CHM raster."""

    path: Path
    metadata: TerrainRasterMetadata
    thresholds_m: tuple[float, ...]
    generated_utc: str
    valid_pixels: int
    nodata_pixels: int
    valid_area_ha: float
    height_metrics: dict[str, object]
    cover_fractions: dict[str, float]
    warnings: tuple[str, ...] = ()
    schema_version: str = CANOPY_STRUCTURE_SCHEMA_VERSION

    def to_dict(self) -> dict[str, object]:
        """Return the canopy structure result as a JSON-serializable mapping."""

        return {
            "schema_version": self.schema_version,
            "path": str(self.path),
            "metadata": self.metadata.to_dict(),
            "thresholds_m": list(self.thresholds_m),
            "generated_utc": self.generated_utc,
            "valid_pixels": self.valid_pixels,
            "nodata_pixels": self.nodata_pixels,
            "valid_area_ha": self.valid_area_ha,
            "height_metrics": self.height_metrics,
            "cover_fractions": self.cover_fractions,
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class VriComparisonRow:
    """One polygon-level CHM versus VRI comparison."""

    polygon_id: str
    vri_height_m: float | None
    chm_p95_m: float | None
    chm_mean_m: float | None
    height_delta_m: float | None
    vri_cover_pct: float | None
    chm_cover_pct: float | None
    cover_delta_pct: float | None
    valid_pixels: int

    def to_dict(self) -> dict[str, object]:
        """Return the row as a JSON-serializable mapping."""

        return {
            "polygon_id": self.polygon_id,
            "vri_height_m": self.vri_height_m,
            "chm_p95_m": self.chm_p95_m,
            "chm_mean_m": self.chm_mean_m,
            "height_delta_m": self.height_delta_m,
            "vri_cover_pct": self.vri_cover_pct,
            "chm_cover_pct": self.chm_cover_pct,
            "cover_delta_pct": self.cover_delta_pct,
            "valid_pixels": self.valid_pixels,
        }


@dataclass(frozen=True)
class VriComparison:
    """Summary uncertainty comparison between CHM and VRI polygons."""

    vri_path: Path
    height_field: str
    cover_field: str | None
    chm_height_metric: str
    polygon_count: int
    matched_count: int
    skipped_count: int
    height_bias_m: float | None
    height_mae_m: float | None
    height_rmse_m: float | None
    cover_bias_pct: float | None
    cover_mae_pct: float | None
    rows: tuple[VriComparisonRow, ...]
    generated_utc: str
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        """Return the comparison as a JSON-serializable mapping."""

        return {
            "vri_path": str(self.vri_path),
            "height_field": self.height_field,
            "cover_field": self.cover_field,
            "chm_height_metric": self.chm_height_metric,
            "polygon_count": self.polygon_count,
            "matched_count": self.matched_count,
            "skipped_count": self.skipped_count,
            "height_bias_m": self.height_bias_m,
            "height_mae_m": self.height_mae_m,
            "height_rmse_m": self.height_rmse_m,
            "cover_bias_pct": self.cover_bias_pct,
            "cover_mae_pct": self.cover_mae_pct,
            "rows": [row.to_dict() for row in self.rows],
            "generated_utc": self.generated_utc,
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class CanopyQaReport:
    """QA report for one CHM/canopy build."""

    generated_utc: str
    dsm: TerrainRasterMetadata
    dem: TerrainRasterMetadata
    chm: CanopyHeightResult
    structure: CanopyStructureResult
    vri_comparison: VriComparison | None = None
    caveats: tuple[str, ...] = CANOPY_CAVEATS
    warnings: tuple[str, ...] = ()
    schema_version: str = CANOPY_QA_SCHEMA_VERSION

    def to_dict(self) -> dict[str, object]:
        """Return the canopy QA report as a JSON-serializable mapping."""

        return {
            "schema_version": self.schema_version,
            "generated_utc": self.generated_utc,
            "dsm": self.dsm.to_dict(),
            "dem": self.dem.to_dict(),
            "chm": self.chm.to_dict(),
            "structure": self.structure.to_dict(),
            "vri_comparison": (
                self.vri_comparison.to_dict() if self.vri_comparison else None
            ),
            "caveats": list(self.caveats),
            "warnings": list(self.warnings),
        }


def derive_canopy_height_model(
    dsm_path: Path,
    dem_path: Path,
    output_path: Path,
    *,
    clamp_negative: bool = True,
    nodata: float | None = None,
    vertical_datum: str | None = None,
    thresholds_m: Sequence[float] = DEFAULT_CANOPY_THRESHOLDS,
    generated_utc: str | None = None,
) -> CanopyHeightResult:
    """Derive CHM = DSM - DEM on exactly aligned native grids."""

    dsm_grid = read_terrain_grid(dsm_path)
    dem_grid = read_terrain_grid(dem_path)
    _require_aligned(dsm_grid.metadata, dem_grid.metadata)
    require_projected_metre_grid(dsm_grid.metadata)
    require_projected_metre_grid(dem_grid.metadata)
    valid = dsm_grid.valid & dem_grid.valid
    raw = np.zeros(dsm_grid.values.shape, dtype=np.float64)
    raw[valid] = dsm_grid.values[valid] - dem_grid.values[valid]
    negative_pixels = int(np.count_nonzero(valid & (raw < 0.0)))
    chm = raw.copy()
    if clamp_negative:
        chm = np.maximum(chm, 0.0)
    thresholds = _normalize_thresholds(thresholds_m)
    output_nodata = (
        float(nodata)
        if nodata is not None
        else (
            dsm_grid.metadata.nodata
            if dsm_grid.metadata.nodata is not None
            else DEFAULT_TERRAIN_NODATA
        )
    )
    output = np.where(valid, chm, output_nodata).astype(np.float32)
    resolved_output = output_path.expanduser().resolve()
    _write_float_raster(output, resolved_output, dsm_grid.metadata, output_nodata)
    values = chm[valid]
    pixel_area = dsm_grid.metadata.resolution_x * dsm_grid.metadata.resolution_y
    warnings: list[str] = [
        "No reprojection or resampling was performed.",
    ]
    if vertical_datum is None:
        warnings.append(
            "Vertical datum was not supplied; confirm DSM and DEM use the same datum."
        )
    if negative_pixels:
        warnings.append(
            f"{negative_pixels} negative DSM-DEM pixels were "
            + (
                "clamped to zero."
                if clamp_negative
                else "retained as negative heights."
            )
        )
    return CanopyHeightResult(
        path=resolved_output,
        dsm_path=dsm_path.expanduser().resolve(),
        dem_path=dem_path.expanduser().resolve(),
        metadata=read_terrain_grid(resolved_output).metadata,
        dsm_metadata=dsm_grid.metadata,
        dem_metadata=dem_grid.metadata,
        vertical_datum=vertical_datum,
        generated_utc=generated_utc or _now(),
        valid_pixels=int(values.size),
        nodata_pixels=int(valid.size - values.size),
        negative_pixels=negative_pixels,
        clamped_negative=clamp_negative,
        height_metrics=_height_metrics(values),
        cover_fractions=_cover_fractions(values, thresholds),
        valid_area_ha=float(values.size * pixel_area / 10_000.0),
        warnings=tuple(warnings),
    )


def derive_canopy_structure(
    chm_path: Path,
    *,
    thresholds_m: Sequence[float] = DEFAULT_CANOPY_THRESHOLDS,
    generated_utc: str | None = None,
) -> CanopyStructureResult:
    """Summarize canopy height and cover from a CHM raster."""

    grid = read_terrain_grid(chm_path)
    require_projected_metre_grid(grid.metadata)
    thresholds = _normalize_thresholds(thresholds_m)
    values = grid.values[grid.valid]
    pixel_area = grid.metadata.resolution_x * grid.metadata.resolution_y
    return CanopyStructureResult(
        path=chm_path.expanduser().resolve(),
        metadata=grid.metadata,
        thresholds_m=thresholds,
        generated_utc=generated_utc or _now(),
        valid_pixels=int(values.size),
        nodata_pixels=int(grid.valid.size - values.size),
        valid_area_ha=float(values.size * pixel_area / 10_000.0),
        height_metrics=_height_metrics(values),
        cover_fractions=_cover_fractions(values, thresholds),
        warnings=(
            "No reprojection or resampling was performed.",
            "Canopy structure is derived from the CHM, not a field inventory.",
        ),
    )


def compare_canopy_to_vri(
    chm_path: Path,
    vri_path: Path,
    *,
    height_field: str = DEFAULT_VRI_HEIGHT_FIELD,
    cover_field: str | None = DEFAULT_VRI_COVER_FIELD,
    id_field: str = DEFAULT_VRI_ID_FIELD,
    min_valid_pixels: int = 10,
    cover_threshold_m: float = DEFAULT_CANOPY_COVER_THRESHOLD_M,
    generated_utc: str | None = None,
) -> VriComparison:
    """Compare polygon-level CHM p95/cover with VRI height/cover fields."""

    if min_valid_pixels < 1:
        raise CanopyProcessingError("min_valid_pixels must be positive.")
    grid = read_terrain_grid(chm_path)
    require_projected_metre_grid(grid.metadata)
    resolved_vri = vri_path.expanduser().resolve()
    try:
        frame = gpd.read_file(resolved_vri)
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        raise CanopyProcessingError(
            f"Unable to read VRI polygons: {resolved_vri}: {exc}"
        ) from exc
    if frame.crs is None:
        raise CanopyProcessingError("VRI polygons have no CRS.")
    if frame.crs.to_string() != grid.metadata.crs:
        raise CanopyProcessingError(
            f"VRI CRS {frame.crs.to_string()!r} does not match CHM CRS "
            f"{grid.metadata.crs!r}; reprojection is not allowed."
        )
    if height_field not in frame.columns:
        raise CanopyProcessingError(
            f"VRI is missing required height field {height_field!r}."
        )
    if id_field not in frame.columns:
        raise CanopyProcessingError(
            f"VRI is missing required identifier field {id_field!r}."
        )
    if cover_field is not None and cover_field not in frame.columns:
        raise CanopyProcessingError(f"VRI is missing cover field {cover_field!r}.")
    warnings: list[str] = [
        "No reprojection or resampling was performed.",
        "VRI comparisons are uncertainty evidence, not field-accuracy claims.",
    ]
    rows: list[VriComparisonRow] = []
    skipped = 0
    with rasterio.open(grid.metadata.path) as source:
        for _, record in frame.iterrows():
            geometry = record.geometry
            if geometry is None or geometry.is_empty:
                skipped += 1
                continue
            try:
                masked, _ = rasterio.mask.mask(
                    source,
                    [geometry],
                    crop=True,
                    filled=False,
                )
            except ValueError:
                skipped += 1
                continue
            values = np.asarray(masked[0].compressed(), dtype=float)
            if values.size < min_valid_pixels:
                skipped += 1
                continue
            vri_height = _optional_float(record.get(height_field))
            vri_cover = (
                _optional_float(record.get(cover_field))
                if cover_field is not None
                else None
            )
            chm_p95 = float(np.percentile(values, 95))
            chm_mean = float(np.mean(values))
            chm_cover = float(np.mean(values >= cover_threshold_m) * 100.0)
            height_delta = chm_p95 - vri_height if vri_height is not None else None
            cover_delta = chm_cover - vri_cover if vri_cover is not None else None
            rows.append(
                VriComparisonRow(
                    polygon_id=str(record.get(id_field)),
                    vri_height_m=vri_height,
                    chm_p95_m=chm_p95,
                    chm_mean_m=chm_mean,
                    height_delta_m=height_delta,
                    vri_cover_pct=vri_cover,
                    chm_cover_pct=chm_cover,
                    cover_delta_pct=cover_delta,
                    valid_pixels=int(values.size),
                )
            )
    if not rows:
        warnings.append("No VRI polygons had enough valid CHM pixels.")
    height_deltas = [
        row.height_delta_m for row in rows if row.height_delta_m is not None
    ]
    cover_deltas = [
        row.cover_delta_pct for row in rows if row.cover_delta_pct is not None
    ]
    return VriComparison(
        vri_path=resolved_vri,
        height_field=height_field,
        cover_field=cover_field,
        chm_height_metric="p95",
        polygon_count=len(frame),
        matched_count=len(rows),
        skipped_count=skipped,
        height_bias_m=_mean(height_deltas),
        height_mae_m=_mean([abs(value) for value in height_deltas]),
        height_rmse_m=(
            float(math.sqrt(np.mean(np.square(height_deltas))))
            if height_deltas
            else None
        ),
        cover_bias_pct=_mean(cover_deltas),
        cover_mae_pct=_mean([abs(value) for value in cover_deltas]),
        rows=tuple(rows),
        generated_utc=generated_utc or _now(),
        warnings=tuple(warnings),
    )


def build_canopy_products(
    dsm_path: Path,
    dem_path: Path,
    output_dir: Path,
    *,
    clamp_negative: bool = True,
    nodata: float | None = None,
    vertical_datum: str | None = None,
    thresholds_m: Sequence[float] = DEFAULT_CANOPY_THRESHOLDS,
    vri_path: Path | None = None,
    vri_height_field: str = DEFAULT_VRI_HEIGHT_FIELD,
    vri_cover_field: str | None = DEFAULT_VRI_COVER_FIELD,
    vri_id_field: str = DEFAULT_VRI_ID_FIELD,
    generated_utc: str | None = None,
) -> CanopyQaReport:
    """Build CHM/canopy products, optional VRI comparison, and QA reports."""

    resolved_output = output_dir.expanduser().resolve()
    resolved_output.mkdir(parents=True, exist_ok=True)
    timestamp = generated_utc or _now()
    chm = derive_canopy_height_model(
        dsm_path,
        dem_path,
        resolved_output / "chm.tif",
        clamp_negative=clamp_negative,
        nodata=nodata,
        vertical_datum=vertical_datum,
        thresholds_m=thresholds_m,
        generated_utc=timestamp,
    )
    structure = derive_canopy_structure(
        chm.path,
        thresholds_m=thresholds_m,
        generated_utc=timestamp,
    )
    (resolved_output / "canopy_structure.json").write_text(
        json.dumps(structure.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    vri_comparison: VriComparison | None = None
    if vri_path is not None:
        vri_comparison = compare_canopy_to_vri(
            chm.path,
            vri_path,
            height_field=vri_height_field,
            cover_field=vri_cover_field,
            id_field=vri_id_field,
            generated_utc=timestamp,
        )
        write_vri_comparison_csv(
            vri_comparison,
            resolved_output / "vri_canopy_comparison.csv",
        )
    report = CanopyQaReport(
        generated_utc=timestamp,
        dsm=chm.dsm_metadata,
        dem=chm.dem_metadata,
        chm=chm,
        structure=structure,
        vri_comparison=vri_comparison,
        warnings=tuple(dict.fromkeys(chm.warnings + structure.warnings)),
    )
    write_canopy_qa_report(report, resolved_output / "canopy_qa.json")
    write_canopy_qa_summary_csv(report, resolved_output / "canopy_qa.csv")
    return report


def write_canopy_qa_report(report: CanopyQaReport, path: Path) -> Path:
    """Write the canopy QA report as pretty-printed JSON."""

    resolved = path.expanduser().resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(
        json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return resolved


def write_canopy_qa_summary_csv(report: CanopyQaReport, path: Path) -> Path:
    """Write a one-row-per-product canopy QA summary CSV."""

    resolved = path.expanduser().resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    with resolved.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "product",
                "path",
                "crs",
                "resolution_m",
                "valid_pixels",
                "nodata_pixels",
                "valid_area_ha",
                "mean_height_m",
                "p95_height_m",
                "cover_ge_2m_pct",
            ]
        )
        for product, result in (
            ("chm", report.chm),
            ("canopy_structure", report.structure),
        ):
            writer.writerow(
                [
                    product,
                    result.path,
                    result.metadata.crs,
                    result.metadata.resolution_x,
                    result.valid_pixels,
                    result.nodata_pixels,
                    result.valid_area_ha,
                    result.height_metrics.get("mean_m"),
                    result.height_metrics.get("p95_m"),
                    result.cover_fractions.get("ge_2m"),
                ]
            )
    return resolved


def write_vri_comparison_csv(comparison: VriComparison, path: Path) -> Path:
    """Write polygon-level VRI comparison rows as CSV."""

    resolved = path.expanduser().resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    with resolved.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "polygon_id",
                "vri_height_m",
                "chm_p95_m",
                "chm_mean_m",
                "height_delta_m",
                "vri_cover_pct",
                "chm_cover_pct",
                "cover_delta_pct",
                "valid_pixels",
            ]
        )
        for row in comparison.rows:
            writer.writerow(
                [
                    row.polygon_id,
                    row.vri_height_m,
                    row.chm_p95_m,
                    row.chm_mean_m,
                    row.height_delta_m,
                    row.vri_cover_pct,
                    row.chm_cover_pct,
                    row.cover_delta_pct,
                    row.valid_pixels,
                ]
            )
    return resolved


def _require_aligned(
    first: TerrainRasterMetadata,
    second: TerrainRasterMetadata,
) -> None:
    if (
        first.width != second.width
        or first.height != second.height
        or first.crs != second.crs
        or first.transform != second.transform
    ):
        raise CanopyProcessingError(
            "DSM and DEM must share exactly the same grid and CRS; "
            "resampling is not allowed."
        )


def _normalize_thresholds(thresholds: Sequence[float]) -> tuple[float, ...]:
    normalized: list[float] = []
    for threshold in thresholds:
        value = float(threshold)
        if not math.isfinite(value) or value < 0:
            raise CanopyProcessingError(
                "Canopy height thresholds must be finite and non-negative."
            )
        if value not in normalized:
            normalized.append(value)
    if not normalized:
        raise CanopyProcessingError("At least one canopy threshold is required.")
    return tuple(sorted(normalized))


def _height_metrics(values: np.ndarray) -> dict[str, object]:
    if values.size == 0:
        return {
            "count": 0,
            "min_m": None,
            "mean_m": None,
            "median_m": None,
            "p90_m": None,
            "p95_m": None,
            "p99_m": None,
            "max_m": None,
        }
    return {
        "count": int(values.size),
        "min_m": float(np.min(values)),
        "mean_m": float(np.mean(values)),
        "median_m": float(np.median(values)),
        "p90_m": float(np.percentile(values, 90)),
        "p95_m": float(np.percentile(values, 95)),
        "p99_m": float(np.percentile(values, 99)),
        "max_m": float(np.max(values)),
    }


def _cover_fractions(
    values: np.ndarray,
    thresholds: tuple[float, ...],
) -> dict[str, float]:
    if values.size == 0:
        return {f"ge_{threshold:g}m": 0.0 for threshold in thresholds}
    return {
        f"ge_{threshold:g}m": float(np.mean(values >= threshold) * 100.0)
        for threshold in thresholds
    }


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


def _optional_float(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float, np.integer, np.floating)):
        parsed = float(value)
    elif isinstance(value, str):
        try:
            parsed = float(value.strip())
        except ValueError:
            return None
    else:
        return None
    return parsed if math.isfinite(parsed) else None


def _mean(values: list[float]) -> float | None:
    return float(np.mean(values)) if values else None


def _now() -> str:
    return datetime.now(UTC).isoformat()
