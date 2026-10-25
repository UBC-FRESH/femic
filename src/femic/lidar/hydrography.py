"""Terrain-derived stream candidates with explicit review caveats.

P79.4 derives screening-level D8 flow paths from a native DEM, compares them
with an aligned public-hydrography reference, and writes a review manifest and
caveat report. Candidates are not authoritative streams.
"""

from __future__ import annotations

import heapq
import json
import math
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import geopandas as gpd  # type: ignore[import-untyped]
import numpy as np
import rasterio  # type: ignore[import-untyped]  # rasterio ships without PEP 561 stubs
import rasterio.features  # type: ignore[import-untyped]

from femic.lidar.terrain import (
    TerrainRasterMetadata,
    read_terrain_grid,
    require_projected_metre_grid,
)

STREAM_CANDIDATE_SCHEMA_VERSION = "femic.lidar.stream_candidates.v1"
STREAM_CANDIDATE_MANIFEST_NAME = "stream_candidates_manifest.json"
STREAM_CANDIDATE_REVIEW_NAME = "stream_candidates_review.md"
STREAM_CANDIDATE_RASTER_NAME = "stream_candidates.tif"
STREAM_ACCUMULATION_RASTER_NAME = "flow_accumulation.tif"
DEFAULT_DEPRESSION_EPSILON = 1e-6
DEFAULT_ACCUMULATION_THRESHOLD = 100
DEFAULT_STREAM_NODATA = 255
DEFAULT_ACCUMULATION_NODATA = -9999.0

D8_NEIGHBOURS: tuple[tuple[int, int, int, str], ...] = (
    (0, 1, 1, "E"),
    (1, 1, 2, "SE"),
    (1, 0, 3, "S"),
    (1, -1, 4, "SW"),
    (0, -1, 5, "W"),
    (-1, -1, 6, "NW"),
    (-1, 0, 7, "N"),
    (-1, 1, 8, "NE"),
)
STREAM_CAVEATS: tuple[str, ...] = (
    (
        "Terrain-derived candidates are a screening aid, not an authoritative "
        "stream layer."
    ),
    (
        "D8 routing is sensitive to DEM artefacts, culverts, bridges, and source "
        "resolution."
    ),
    ("Depression filling changes local flow paths and may create synthetic channels."),
    (
        "Candidates require field or public-hydrography review before riparian, "
        "operability, or legal use."
    ),
    "No reprojection or resampling was performed.",
)


class StreamCandidateError(RuntimeError):
    """Raised when stream-candidate inputs or outputs are invalid."""


@dataclass(frozen=True)
class StreamComparison:
    """Overlap metrics between candidate and reference stream masks."""

    candidate_cells: int
    reference_cells: int
    true_positive: int
    false_positive: int
    false_negative: int
    precision: float | None
    recall: float | None
    f1: float | None
    jaccard: float | None
    candidate_area_ha: float | None = None
    reference_area_ha: float | None = None
    overlap_area_ha: float | None = None

    def to_dict(self) -> dict[str, object]:
        """Return the comparison as a JSON-serializable mapping."""

        return {
            "candidate_cells": self.candidate_cells,
            "reference_cells": self.reference_cells,
            "true_positive": self.true_positive,
            "false_positive": self.false_positive,
            "false_negative": self.false_negative,
            "precision": self.precision,
            "recall": self.recall,
            "f1": self.f1,
            "jaccard": self.jaccard,
            "candidate_area_ha": self.candidate_area_ha,
            "reference_area_ha": self.reference_area_ha,
            "overlap_area_ha": self.overlap_area_ha,
        }


@dataclass(frozen=True)
class StreamCandidateManifest:
    """Review manifest for one terrain-derived stream-candidate build."""

    generated_utc: str
    source: TerrainRasterMetadata
    parameters: dict[str, object]
    outputs: dict[str, str]
    qa: dict[str, object]
    comparison: StreamComparison | None
    caveats: tuple[str, ...] = STREAM_CAVEATS
    warnings: tuple[str, ...] = ()
    schema_version: str = STREAM_CANDIDATE_SCHEMA_VERSION

    def to_dict(self) -> dict[str, object]:
        """Return the manifest as a JSON-serializable mapping."""

        return {
            "schema_version": self.schema_version,
            "generated_utc": self.generated_utc,
            "source": self.source.to_dict(),
            "parameters": self.parameters,
            "outputs": self.outputs,
            "qa": self.qa,
            "comparison": self.comparison.to_dict() if self.comparison else None,
            "caveats": list(self.caveats),
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class StreamCandidateResult:
    """Paths and manifest returned by a stream-candidate build."""

    manifest: StreamCandidateManifest
    output_dir: Path
    stream_path: Path
    accumulation_path: Path
    manifest_path: Path
    review_path: Path

    def to_dict(self) -> dict[str, object]:
        """Return the result as a JSON-serializable mapping."""

        return {
            "output_dir": str(self.output_dir),
            "stream_path": str(self.stream_path),
            "accumulation_path": str(self.accumulation_path),
            "manifest_path": str(self.manifest_path),
            "review_path": str(self.review_path),
            "manifest": self.manifest.to_dict(),
        }


def fill_dem_depressions(
    elevation: np.ndarray,
    valid: np.ndarray,
    *,
    epsilon: float = DEFAULT_DEPRESSION_EPSILON,
) -> tuple[np.ndarray, int]:
    """Fill depressions with a priority-flood pass.

    Returns the filled elevation grid and the count of valid cells that were
    not connected to the outer boundary and therefore were left unfilled.
    """

    if epsilon <= 0 or not math.isfinite(epsilon):
        raise StreamCandidateError("Depression-fill epsilon must be positive.")
    values = np.asarray(elevation, dtype=np.float64)
    mask = np.asarray(valid, dtype=bool)
    if values.shape != mask.shape:
        raise StreamCandidateError("Elevation and validity arrays must match.")
    filled = values.copy()
    visited = np.zeros(mask.shape, dtype=bool)
    height, width = mask.shape
    heap: list[tuple[float, int, int]] = []
    for row in range(height):
        for column in (0, width - 1):
            if mask[row, column] and not visited[row, column]:
                visited[row, column] = True
                heapq.heappush(heap, (filled[row, column], row, column))
    for column in range(width):
        for row in (0, height - 1):
            if mask[row, column] and not visited[row, column]:
                visited[row, column] = True
                heapq.heappush(heap, (filled[row, column], row, column))
    while heap:
        current, row, column = heapq.heappop(heap)
        for delta_row, delta_column, _, _ in D8_NEIGHBOURS:
            neighbour_row = row + delta_row
            neighbour_column = column + delta_column
            if not (0 <= neighbour_row < height and 0 <= neighbour_column < width):
                continue
            if not mask[neighbour_row, neighbour_column]:
                continue
            if visited[neighbour_row, neighbour_column]:
                continue
            visited[neighbour_row, neighbour_column] = True
            raised = max(filled[neighbour_row, neighbour_column], current + epsilon)
            filled[neighbour_row, neighbour_column] = raised
            heapq.heappush(heap, (raised, neighbour_row, neighbour_column))
    unfilled_isolated = int(mask.sum() - visited.sum())
    return filled, unfilled_isolated


def derive_d8_flow_direction(
    elevation: np.ndarray,
    valid: np.ndarray,
    *,
    resolution_x: float,
    resolution_y: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Derive D8 flow directions and downstream flat indices.

    Codes are 1=E, 2=SE, 3=S, 4=SW, 5=W, 6=NW, 7=N, 8=NE. Sinks and invalid
    cells receive ``-1``.
    """

    if resolution_x <= 0 or resolution_y <= 0:
        raise StreamCandidateError("Flow routing requires positive resolution.")
    values = np.asarray(elevation, dtype=np.float64)
    mask = np.asarray(valid, dtype=bool)
    if values.shape != mask.shape:
        raise StreamCandidateError("Elevation and validity arrays must match.")
    direction = np.full(values.shape, -1, dtype=np.int8)
    downstream = np.full(values.shape, -1, dtype=np.int64)
    height, width = values.shape
    for row, column in zip(*np.nonzero(mask), strict=False):
        current = values[row, column]
        best_drop = 0.0
        best_code = -1
        best_target = -1
        for delta_row, delta_column, code, _ in D8_NEIGHBOURS:
            neighbour_row = row + delta_row
            neighbour_column = column + delta_column
            if not (0 <= neighbour_row < height and 0 <= neighbour_column < width):
                continue
            if not mask[neighbour_row, neighbour_column]:
                continue
            distance = math.hypot(
                delta_row * resolution_x,
                delta_column * resolution_y,
            )
            drop = (current - values[neighbour_row, neighbour_column]) / distance
            if drop > best_drop + 1e-15:
                best_drop = drop
                best_code = code
                best_target = neighbour_row * width + neighbour_column
        direction[row, column] = best_code
        downstream[row, column] = best_target
    return direction, downstream


def accumulate_d8_flow(
    elevation: np.ndarray,
    downstream: np.ndarray,
    valid: np.ndarray,
) -> np.ndarray:
    """Accumulate one cell of area downstream over a D8 network."""

    values = np.asarray(elevation, dtype=np.float64)
    targets = np.asarray(downstream, dtype=np.int64)
    mask = np.asarray(valid, dtype=bool)
    if values.shape != targets.shape or values.shape != mask.shape:
        raise StreamCandidateError("Flow arrays must share one shape.")
    accumulation = np.zeros(values.size, dtype=np.float64)
    valid_flat = np.flatnonzero(mask.ravel())
    accumulation[valid_flat] = 1.0
    order = valid_flat[np.argsort(values.ravel()[valid_flat], kind="stable")[::-1]]
    targets_flat = targets.ravel()
    for index in order:
        target = targets_flat[index]
        if target >= 0:
            accumulation[target] += accumulation[index]
    return accumulation.reshape(values.shape)


def compare_stream_candidates(
    candidate_mask: np.ndarray,
    reference_mask: np.ndarray,
    *,
    pixel_area_m2: float | None = None,
) -> StreamComparison:
    """Compare candidate and reference stream masks."""

    candidate = np.asarray(candidate_mask, dtype=bool)
    reference = np.asarray(reference_mask, dtype=bool)
    if candidate.shape != reference.shape:
        raise StreamCandidateError("Candidate and reference masks must match.")
    true_positive = int(np.count_nonzero(candidate & reference))
    false_positive = int(np.count_nonzero(candidate & ~reference))
    false_negative = int(np.count_nonzero(~candidate & reference))
    candidate_cells = int(np.count_nonzero(candidate))
    reference_cells = int(np.count_nonzero(reference))
    precision = _safe_ratio(true_positive, true_positive + false_positive)
    recall = _safe_ratio(true_positive, true_positive + false_negative)
    f1 = (
        _safe_ratio(2.0 * precision * recall, precision + recall)
        if precision is not None and recall is not None
        else None
    )
    jaccard = _safe_ratio(
        true_positive, candidate_cells + reference_cells - true_positive
    )
    area_factor = (
        pixel_area_m2 / 10_000.0
        if pixel_area_m2 is not None and pixel_area_m2 > 0
        else None
    )
    return StreamComparison(
        candidate_cells=candidate_cells,
        reference_cells=reference_cells,
        true_positive=true_positive,
        false_positive=false_positive,
        false_negative=false_negative,
        precision=precision,
        recall=recall,
        f1=f1,
        jaccard=jaccard,
        candidate_area_ha=(
            candidate_cells * area_factor if area_factor is not None else None
        ),
        reference_area_ha=(
            reference_cells * area_factor if area_factor is not None else None
        ),
        overlap_area_ha=(
            true_positive * area_factor if area_factor is not None else None
        ),
    )


def derive_stream_candidates(
    source_dem_path: Path,
    output_dir: Path,
    *,
    accumulation_threshold: int = DEFAULT_ACCUMULATION_THRESHOLD,
    fill_depressions: bool = True,
    reference_path: Path | None = None,
    reference_all_touched: bool = False,
    generated_utc: str | None = None,
) -> StreamCandidateResult:
    """Derive screening stream candidates from a native DEM.

    The workflow fills depressions (optional), routes D8 flow, thresholds flow
    accumulation, writes candidate and accumulation rasters, and emits a JSON
    review manifest plus a Markdown caveat report. It never reprojects or
    resamples the DEM.
    """

    if accumulation_threshold < 1:
        raise StreamCandidateError("Accumulation threshold must be at least 1.")
    grid = read_terrain_grid(source_dem_path)
    require_projected_metre_grid(grid.metadata)
    warnings: list[str] = []
    if fill_depressions:
        filled, isolated = fill_dem_depressions(grid.values, grid.valid)
        if isolated:
            warnings.append(
                f"{isolated} valid cells were not connected to the outer boundary "
                "and were left unfilled."
            )
    else:
        filled = grid.values.copy()
        warnings.append(
            "Depression filling was disabled; sinks remain as local minima."
        )
    _, downstream = derive_d8_flow_direction(
        filled,
        grid.valid,
        resolution_x=grid.metadata.resolution_x,
        resolution_y=grid.metadata.resolution_y,
    )
    accumulation = accumulate_d8_flow(filled, downstream, grid.valid)
    candidates = grid.valid & (accumulation >= accumulation_threshold)
    if not np.any(candidates):
        warnings.append(
            "No cells met the accumulation threshold; the candidate raster is empty."
        )
    pixel_area = abs(
        grid.metadata.transform[0] * grid.metadata.transform[4]
        - grid.metadata.transform[1] * grid.metadata.transform[3]
    )
    comparison: StreamComparison | None = None
    if reference_path is not None:
        reference_mask, reference_warnings = _load_reference_mask(
            reference_path,
            grid.metadata,
            all_touched=reference_all_touched,
        )
        warnings.extend(reference_warnings)
        comparison = compare_stream_candidates(
            candidates,
            reference_mask,
            pixel_area_m2=pixel_area,
        )
    resolved_output = output_dir.expanduser().resolve()
    resolved_output.mkdir(parents=True, exist_ok=True)
    stream_path = resolved_output / STREAM_CANDIDATE_RASTER_NAME
    accumulation_path = resolved_output / STREAM_ACCUMULATION_RASTER_NAME
    stream_values = np.full(candidates.shape, DEFAULT_STREAM_NODATA, dtype=np.uint8)
    stream_values[grid.valid] = 0
    stream_values[candidates] = 1
    _write_uint8_raster(
        stream_values,
        stream_path,
        grid.metadata,
        nodata=DEFAULT_STREAM_NODATA,
    )
    accumulation_values = np.where(
        grid.valid,
        accumulation,
        DEFAULT_ACCUMULATION_NODATA,
    ).astype(np.float32)
    _write_float32_raster(
        accumulation_values,
        accumulation_path,
        grid.metadata,
        nodata=DEFAULT_ACCUMULATION_NODATA,
    )
    candidate_accumulation = accumulation[candidates]
    qa: dict[str, object] = {
        "valid_cells": int(grid.valid.sum()),
        "candidate_cells": int(candidates.sum()),
        "candidate_area_ha": float(candidates.sum() * pixel_area / 10_000.0),
        "accumulation_min": (
            float(np.min(candidate_accumulation))
            if candidate_accumulation.size
            else None
        ),
        "accumulation_max": (
            float(np.max(candidate_accumulation))
            if candidate_accumulation.size
            else None
        ),
        "accumulation_mean": (
            float(np.mean(candidate_accumulation))
            if candidate_accumulation.size
            else None
        ),
    }
    manifest = StreamCandidateManifest(
        generated_utc=generated_utc or _now(),
        source=grid.metadata,
        parameters={
            "accumulation_threshold": accumulation_threshold,
            "fill_depressions": fill_depressions,
            "depression_epsilon": DEFAULT_DEPRESSION_EPSILON,
            "flow_routing": "d8",
            "d8_codes": {code: label for _, _, code, label in D8_NEIGHBOURS},
            "reference_path": str(reference_path) if reference_path else None,
            "reference_all_touched": reference_all_touched,
            "resampling": "none",
        },
        outputs={
            "stream_candidates": STREAM_CANDIDATE_RASTER_NAME,
            "flow_accumulation": STREAM_ACCUMULATION_RASTER_NAME,
        },
        qa=qa,
        comparison=comparison,
        warnings=tuple(warnings),
    )
    manifest_path = write_stream_candidate_manifest(
        manifest,
        resolved_output / STREAM_CANDIDATE_MANIFEST_NAME,
    )
    review_path = write_stream_candidate_review(
        manifest,
        resolved_output / STREAM_CANDIDATE_REVIEW_NAME,
    )
    return StreamCandidateResult(
        manifest=manifest,
        output_dir=resolved_output,
        stream_path=stream_path,
        accumulation_path=accumulation_path,
        manifest_path=manifest_path,
        review_path=review_path,
    )


def write_stream_candidate_manifest(
    manifest: StreamCandidateManifest,
    path: Path,
) -> Path:
    """Write the stream-candidate review manifest as JSON."""

    resolved = path.expanduser().resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(
        json.dumps(manifest.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return resolved


def write_stream_candidate_review(
    manifest: StreamCandidateManifest,
    path: Path,
) -> Path:
    """Write a human-readable caveat and review report."""

    resolved = path.expanduser().resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Terrain-derived stream candidates",
        "",
        f"Generated: {manifest.generated_utc}",
        "",
        "## Inputs",
        "",
        f"- DEM: `{manifest.source.path}`",
        f"- CRS: `{manifest.source.crs}`",
        f"- Resolution: {manifest.source.resolution_x} x {manifest.source.resolution_y} m",
        "",
        "## Parameters",
        "",
    ]
    for key, value in manifest.parameters.items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(
        [
            "",
            "## Outputs",
            "",
        ]
    )
    for key, value in manifest.outputs.items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(
        [
            "",
            "## QA",
            "",
        ]
    )
    for key, value in manifest.qa.items():
        lines.append(f"- {key}: {value}")
    if manifest.comparison is not None:
        lines.extend(["", "## Comparison", ""])
        for key, value in manifest.comparison.to_dict().items():
            lines.append(f"- {key}: {value}")
    lines.extend(["", "## Caveats", ""])
    for caveat in manifest.caveats:
        lines.append(f"- {caveat}")
    if manifest.warnings:
        lines.extend(["", "## Warnings", ""])
        for warning in manifest.warnings:
            lines.append(f"- {warning}")
    lines.extend(
        [
            "",
            "## Review checklist",
            "",
            "- [ ] Compare candidates against current public hydrography.",
            "- [ ] Check DEM artefacts, culverts, bridges, and cutblocks.",
            "- [ ] Confirm the accumulation threshold is appropriate for the AOI.",
            "- [ ] Record the reviewer and decision before operational use.",
            "",
        ]
    )
    resolved.write_text("\n".join(lines), encoding="utf-8")
    return resolved


def _load_reference_mask(
    reference_path: Path,
    metadata: TerrainRasterMetadata,
    *,
    all_touched: bool,
) -> tuple[np.ndarray, tuple[str, ...]]:
    resolved = reference_path.expanduser().resolve()
    if resolved.suffix.lower() in {".tif", ".tiff"}:
        reference = read_terrain_grid(resolved)
        if (
            reference.metadata.width != metadata.width
            or reference.metadata.height != metadata.height
            or reference.metadata.crs != metadata.crs
            or reference.metadata.transform != metadata.transform
        ):
            raise StreamCandidateError(
                "Reference hydrography raster must share the DEM grid and CRS; "
                "resampling is not allowed."
            )
        return reference.valid & (reference.values > 0), ()
    try:
        frame = gpd.read_file(resolved)
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        raise StreamCandidateError(
            f"Unable to read reference hydrography: {resolved}: {exc}"
        ) from exc
    if frame.crs is None:
        raise StreamCandidateError("Reference hydrography vector has no CRS.")
    if frame.crs.to_string() != metadata.crs:
        raise StreamCandidateError(
            f"Reference hydrography CRS {frame.crs.to_string()!r} does not match "
            f"DEM CRS {metadata.crs!r}; reprojection is not allowed."
        )
    if frame.empty:
        return np.zeros((metadata.height, metadata.width), dtype=bool), (
            "Reference hydrography vector contains no features.",
        )
    mask = rasterio.features.rasterize(
        list(frame.geometry),
        out_shape=(metadata.height, metadata.width),
        transform=rasterio.transform.Affine(*metadata.transform),
        fill=0,
        default_value=1,
        all_touched=all_touched,
        dtype="uint8",
    )
    return mask.astype(bool), ()


def _write_uint8_raster(
    values: np.ndarray,
    path: Path,
    metadata: TerrainRasterMetadata,
    *,
    nodata: int,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    profile = {
        "driver": "GTiff",
        "dtype": "uint8",
        "count": 1,
        "width": metadata.width,
        "height": metadata.height,
        "crs": metadata.crs,
        "transform": rasterio.transform.Affine(*metadata.transform),
        "nodata": nodata,
        "compress": "deflate",
    }
    with rasterio.open(path, "w", **profile) as destination:
        destination.write(values.astype(np.uint8), 1)


def _write_float32_raster(
    values: np.ndarray,
    path: Path,
    metadata: TerrainRasterMetadata,
    *,
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


def _safe_ratio(numerator: float, denominator: float) -> float | None:
    if denominator <= 0:
        return None
    return float(numerator / denominator)


def _now() -> str:
    return datetime.now(UTC).isoformat()
