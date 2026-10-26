"""Optional individual-tree product ingestion and block summaries.

P79.7 consumes existing LidarBC or external individual-tree products. It does
not implement a new tree-segmentation algorithm. Tree products are optional and
are summarized with explicit completeness and uncertainty fields.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import geopandas as gpd  # type: ignore[import-untyped]
import numpy as np

TREE_PRODUCT_SCHEMA_VERSION = "femic.lidar.individual_tree.v1"
DEFAULT_TREE_ID_FIELD = "tree_id"
DEFAULT_TREE_HEIGHT_FIELD = "height_m"
DEFAULT_TREE_CROWN_FIELD = "crown_radius_m"
DEFAULT_TREE_SPECIES_FIELD = "species"
DEFAULT_BLOCK_ID_FIELD = "block_id"
TREE_PRODUCT_CAVEATS: tuple[str, ...] = (
    "Individual-tree products are optional and source-dependent.",
    (
        "FEMIC does not implement a new tree-segmentation algorithm; ingest a "
        "suitable existing public product."
    ),
    "Tree heights and crowns are not a field-accuracy claim without validation.",
)


class TreeProductError(RuntimeError):
    """Raised when an individual-tree product or block summary is invalid."""


@dataclass(frozen=True)
class IndividualTreeSummary:
    """Completeness and distribution summary for one tree product."""

    path: Path
    crs: str
    feature_count: int
    unique_tree_count: int
    duplicate_tree_count: int
    missing_height_count: int
    height_metrics: dict[str, object]
    crown_metrics: dict[str, object]
    species_counts: dict[str, int]
    geometry_types: tuple[str, ...]
    generated_utc: str
    warnings: tuple[str, ...] = ()
    schema_version: str = TREE_PRODUCT_SCHEMA_VERSION

    def to_dict(self) -> dict[str, object]:
        """Return the summary as a JSON-serializable mapping."""

        return {
            "schema_version": self.schema_version,
            "path": str(self.path),
            "crs": self.crs,
            "feature_count": self.feature_count,
            "unique_tree_count": self.unique_tree_count,
            "duplicate_tree_count": self.duplicate_tree_count,
            "missing_height_count": self.missing_height_count,
            "height_metrics": self.height_metrics,
            "crown_metrics": self.crown_metrics,
            "species_counts": self.species_counts,
            "geometry_types": list(self.geometry_types),
            "generated_utc": self.generated_utc,
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class TreeBlockRow:
    """Tree summary for one block or polygon."""

    block_id: str
    tree_count: int
    mean_height_m: float | None
    p95_height_m: float | None
    max_height_m: float | None
    species_counts: dict[str, int]

    def to_dict(self) -> dict[str, object]:
        """Return the block row as a JSON-serializable mapping."""

        return {
            "block_id": self.block_id,
            "tree_count": self.tree_count,
            "mean_height_m": self.mean_height_m,
            "p95_height_m": self.p95_height_m,
            "max_height_m": self.max_height_m,
            "species_counts": self.species_counts,
        }


@dataclass(frozen=True)
class TreeBlockSummary:
    """Block-level summary for an individual-tree product."""

    trees_path: Path
    blocks_path: Path
    block_id_field: str
    rows: tuple[TreeBlockRow, ...]
    generated_utc: str
    warnings: tuple[str, ...] = ()
    schema_version: str = TREE_PRODUCT_SCHEMA_VERSION

    def to_dict(self) -> dict[str, object]:
        """Return the block summary as a JSON-serializable mapping."""

        return {
            "schema_version": self.schema_version,
            "trees_path": str(self.trees_path),
            "blocks_path": str(self.blocks_path),
            "block_id_field": self.block_id_field,
            "rows": [row.to_dict() for row in self.rows],
            "generated_utc": self.generated_utc,
            "warnings": list(self.warnings),
        }


def inspect_individual_tree_product(
    path: Path,
    *,
    id_field: str = DEFAULT_TREE_ID_FIELD,
    height_field: str = DEFAULT_TREE_HEIGHT_FIELD,
    crown_field: str | None = DEFAULT_TREE_CROWN_FIELD,
    species_field: str | None = DEFAULT_TREE_SPECIES_FIELD,
    generated_utc: str | None = None,
) -> IndividualTreeSummary:
    """Inspect an existing point-based individual-tree product."""

    resolved = path.expanduser().resolve()
    try:
        frame = gpd.read_file(resolved)
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        raise TreeProductError(
            f"Unable to read individual-tree product: {resolved}: {exc}"
        ) from exc
    if frame.empty:
        raise TreeProductError("Individual-tree product contains no features.")
    if frame.crs is None:
        raise TreeProductError("Individual-tree product has no CRS.")
    for field in (id_field, height_field):
        if field not in frame.columns:
            raise TreeProductError(
                f"Individual-tree product is missing required field {field!r}."
            )
    geometry_types = tuple(
        sorted({str(value) for value in frame.geometry.geom_type.dropna().unique()})
    )
    unsupported = [
        value for value in geometry_types if value not in {"Point", "MultiPoint"}
    ]
    if unsupported:
        raise TreeProductError(
            "Individual-tree geometry must be point-based; found: "
            + ", ".join(unsupported)
        )
    warnings: list[str] = [
        "No reprojection or resampling was performed.",
        "Tree products are optional and source-dependent.",
    ]
    if not frame.crs.is_projected:
        warnings.append(
            "Tree product CRS is not projected; block summaries may be unreliable."
        )
    if crown_field is not None and crown_field not in frame.columns:
        warnings.append(f"Optional crown field {crown_field!r} is missing.")
    if species_field is not None and species_field not in frame.columns:
        warnings.append(f"Optional species field {species_field!r} is missing.")
    ids = frame[id_field].dropna().astype(str)
    duplicate_tree_count = int(ids.duplicated(keep=False).sum())
    heights = _numeric_values(frame[height_field])
    missing_height_count = int(frame[height_field].isna().sum())
    crowns = (
        _numeric_values(frame[crown_field])
        if crown_field is not None and crown_field in frame.columns
        else np.asarray([], dtype=float)
    )
    species_counts: dict[str, int] = {}
    if species_field is not None and species_field in frame.columns:
        species_counts = {
            str(key): int(value)
            for key, value in frame[species_field]
            .fillna("unknown")
            .value_counts()
            .items()
        }
    return IndividualTreeSummary(
        path=resolved,
        crs=frame.crs.to_string(),
        feature_count=len(frame),
        unique_tree_count=int(ids.nunique()),
        duplicate_tree_count=duplicate_tree_count,
        missing_height_count=missing_height_count,
        height_metrics=_distribution(heights),
        crown_metrics=_distribution(crowns),
        species_counts=species_counts,
        geometry_types=geometry_types,
        generated_utc=generated_utc or _now(),
        warnings=tuple(warnings),
    )


def summarize_individual_trees_by_block(
    trees_path: Path,
    blocks_path: Path,
    *,
    block_id_field: str = DEFAULT_BLOCK_ID_FIELD,
    id_field: str = DEFAULT_TREE_ID_FIELD,
    height_field: str = DEFAULT_TREE_HEIGHT_FIELD,
    species_field: str | None = DEFAULT_TREE_SPECIES_FIELD,
    generated_utc: str | None = None,
) -> TreeBlockSummary:
    """Join tree points to blocks and summarize tree counts and heights."""

    resolved_trees = trees_path.expanduser().resolve()
    resolved_blocks = blocks_path.expanduser().resolve()
    try:
        trees = gpd.read_file(resolved_trees)
        blocks = gpd.read_file(resolved_blocks)
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        raise TreeProductError(f"Unable to read tree/block inputs: {exc}") from exc
    if trees.empty or blocks.empty:
        raise TreeProductError("Tree and block inputs must both contain features.")
    if trees.crs is None or blocks.crs is None:
        raise TreeProductError("Tree and block inputs must both have a CRS.")
    if trees.crs.to_string() != blocks.crs.to_string():
        raise TreeProductError(
            "Tree and block CRS do not match; reprojection is not allowed."
        )
    for field in (id_field, height_field):
        if field not in trees.columns:
            raise TreeProductError(f"Tree product is missing required field {field!r}.")
    if block_id_field not in blocks.columns:
        raise TreeProductError(
            f"Block product is missing required field {block_id_field!r}."
        )
    joined = gpd.sjoin(
        trees,
        blocks[[block_id_field, "geometry"]],
        how="inner",
        predicate="within",
    )
    warnings: list[str] = [
        "No reprojection or resampling was performed.",
    ]
    if len(joined) < len(trees):
        warnings.append(
            f"{len(trees) - len(joined)} trees were outside all blocks and "
            "were excluded from block summaries."
        )
    rows: list[TreeBlockRow] = []
    for block_id, group in joined.groupby(block_id_field):
        heights = _numeric_values(group[height_field])
        species_counts: dict[str, int] = {}
        if species_field is not None and species_field in group.columns:
            species_counts = {
                str(key): int(value)
                for key, value in group[species_field]
                .fillna("unknown")
                .value_counts()
                .items()
            }
        rows.append(
            TreeBlockRow(
                block_id=str(block_id),
                tree_count=len(group),
                mean_height_m=(float(np.mean(heights)) if heights.size else None),
                p95_height_m=(
                    float(np.percentile(heights, 95)) if heights.size else None
                ),
                max_height_m=(float(np.max(heights)) if heights.size else None),
                species_counts=species_counts,
            )
        )
    rows.sort(key=lambda row: row.block_id)
    return TreeBlockSummary(
        trees_path=resolved_trees,
        blocks_path=resolved_blocks,
        block_id_field=block_id_field,
        rows=tuple(rows),
        generated_utc=generated_utc or _now(),
        warnings=tuple(warnings),
    )


def write_individual_tree_summary(
    summary: IndividualTreeSummary,
    path: Path,
) -> Path:
    """Write a tree-product summary as JSON."""

    resolved = path.expanduser().resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(
        json.dumps(summary.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return resolved


def write_tree_block_summary_csv(summary: TreeBlockSummary, path: Path) -> Path:
    """Write block-level tree summaries as CSV."""

    resolved = path.expanduser().resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    with resolved.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "block_id",
                "tree_count",
                "mean_height_m",
                "p95_height_m",
                "max_height_m",
                "species_counts",
            ]
        )
        for row in summary.rows:
            writer.writerow(
                [
                    row.block_id,
                    row.tree_count,
                    row.mean_height_m,
                    row.p95_height_m,
                    row.max_height_m,
                    json.dumps(row.species_counts, sort_keys=True),
                ]
            )
    return resolved


def _numeric_values(series: object) -> np.ndarray:
    try:
        values = np.asarray(series, dtype=float)
    except (TypeError, ValueError):
        return np.asarray([], dtype=float)
    return values[np.isfinite(values)]


def _distribution(values: np.ndarray) -> dict[str, object]:
    if values.size == 0:
        return {
            "count": 0,
            "min": None,
            "mean": None,
            "median": None,
            "p95": None,
            "max": None,
        }
    return {
        "count": int(values.size),
        "min": float(np.min(values)),
        "mean": float(np.mean(values)),
        "median": float(np.median(values)),
        "p95": float(np.percentile(values, 95)),
        "max": float(np.max(values)),
    }


def _now() -> str:
    return datetime.now(UTC).isoformat()
