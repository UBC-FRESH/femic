"""Optional sidecar ground bundle for one ALS tile.

This module implements the P15 design: one LAZ, one manifest, and one QA file. It is an
opt-in adapter, not a default dataset path. The bundle is self-contained and does not import
or depend on FEMIC.

The ground labels come from :mod:`femic.lidar.ground_classification`. The adapter adds
``is_ground``, ``hag``, ``is_low``, and ``ref_class`` dimensions to a copy of the input
LAS/LAZ, then writes a versioned manifest and QA summary.

This is the canonical FEMIC writer. The earlier `fresh-urban-forest-lab` prototype proved
the same contract; FEMIC now owns the producer side.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from femic.lidar.ground_classification import (
    classify_ground_ptd,
    low_point_mask,
    statistical_outlier_mask,
)


class GroundAdapterError(RuntimeError):
    """Raised when a ground bundle cannot be written."""


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


BUNDLE_SCHEMA_VERSION = "femic.ground-bundle.v1"
QA_SCHEMA_VERSION = "femic.ground-qa.v1"
HAG_PERCENTILES: tuple[float, ...] = (0, 1, 5, 25, 50, 75, 90, 95, 99, 100)


@dataclass(frozen=True, slots=True)
class GroundAdapterParameters:
    """Parameters recorded in a ground bundle.

    Attributes
    ----------
    sor_enabled : bool
        Whether to run statistical outlier removal before PTD.
    sor_k : int
        Neighbour count for SOR.
    sor_multiplier : float
        Standard-deviation multiplier for SOR.
    cell_size_m : float
        PTD seed grid cell size in metres.
    max_angle_deg : float
        Maximum point-to-vertex angle in degrees.
    max_distance_m : float
        Maximum vertical residual in metres.
    max_iterations : int
        Maximum PTD densification iterations.
    low_point_cut_m : float
        Height-above-ground cut for the low-point flag.
    """

    sor_enabled: bool = True
    sor_k: int = 10
    sor_multiplier: float = 2.0
    cell_size_m: float = 1.0
    max_angle_deg: float = 15.0
    max_distance_m: float = 0.5
    max_iterations: int = 8
    low_point_cut_m: float = 0.15

    def to_dict(self) -> dict[str, object]:
        """Return the parameter block as a JSON-serializable mapping.

        Returns
        -------
        dict
            Parameter names and values.
        """
        return dict(asdict(self))

    def sha256(self) -> str:
        """Return a canonical parameter hash.

        Returns
        -------
        str
            Lower-case SHA-256 digest of the canonical JSON parameter block.
        """
        payload = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class GroundBundleResult:
    """Paths and counts produced by a ground-bundle write.

    Attributes
    ----------
    ground_laz : Path
        Written LAZ copy with extra dimensions.
    manifest_path : Path
        Written manifest JSON.
    qa_path : Path
        Written QA JSON.
    point_count : int
        Number of input points.
    ground_count : int
        Number of predicted ground points.
    low_point_count : int
        Number of points below the low-point cut.
    warnings : tuple of str
        Non-fatal warnings recorded in the bundle.
    """

    ground_laz: Path
    manifest_path: Path
    qa_path: Path
    point_count: int
    ground_count: int
    low_point_count: int
    warnings: tuple[str, ...]


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


def _percentiles(values: NDArray[np.float64]) -> dict[str, float | None]:
    """Return HAG percentiles as a JSON-friendly mapping.

    Parameters
    ----------
    values : ndarray
        HAG values. NaN entries are ignored.

    Returns
    -------
    dict
        Percentile label to value, or ``None`` when no finite value exists.
    """
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return {str(int(q)): None for q in HAG_PERCENTILES}
    return {
        str(int(q)): round(float(np.percentile(finite, q)), 4) for q in HAG_PERCENTILES
    }


def _class_counts(classes: NDArray[np.uint8]) -> dict[str, int]:
    """Return a JSON-friendly class count mapping.

    Parameters
    ----------
    classes : ndarray
        LAS classification values.

    Returns
    -------
    dict
        String class code to count.
    """
    values, counts = np.unique(classes, return_counts=True)
    return {
        str(int(value)): int(count) for value, count in zip(values, counts, strict=True)
    }


def _predicted_by_class(
    classes: NDArray[np.uint8],
    is_ground: NDArray[np.bool_],
) -> dict[str, dict[str, int | float]]:
    """Summarize predicted ground by original class.

    Parameters
    ----------
    classes : ndarray
        LAS classification values.
    is_ground : ndarray
        Predicted ground mask.

    Returns
    -------
    dict
        Per-class point count, predicted-ground count, and fraction.
    """
    result: dict[str, dict[str, int | float]] = {}
    for code in np.unique(classes):
        mask = classes == code
        total = int(np.count_nonzero(mask))
        ground = int(np.count_nonzero(is_ground & mask))
        result[str(int(code))] = {
            "points": total,
            "predicted_ground": ground,
            "fraction": round(ground / total, 6) if total else 0.0,
        }
    return result


def _resolve_crs(las: Any, explicit: str | None) -> tuple[str | None, list[str]]:
    """Resolve a CRS label and return warnings for a missing value.

    Parameters
    ----------
    las : Any
        Input ``laspy.LasData`` point cloud.
    explicit : str or None
        Caller-supplied CRS label.

    Returns
    -------
    tuple
        ``(crs_label, warnings)``.
    """
    warnings: list[str] = []
    if explicit:
        return explicit, warnings
    parsed = las.header.parse_crs()
    if parsed is not None:
        return str(parsed), warnings
    warnings.append("CRS is missing; manifest records null")
    return None, warnings


def write_ground_bundle(
    laz_path: Path,
    out_dir: Path,
    *,
    crs: str | None = None,
    vertical_datum: str | None = None,
    parameters: GroundAdapterParameters | None = None,
    overwrite: bool = False,
) -> GroundBundleResult:
    """Write a sidecar ground bundle for one LAS/LAZ tile.

    Parameters
    ----------
    laz_path : Path
        Input LAS or LAZ file.
    out_dir : Path
        Output directory. Created when missing.
    crs : str or None
        Explicit CRS label. When omitted, the file header is used.
    vertical_datum : str or None
        Explicit vertical-datum label. When omitted, a warning is recorded.
    parameters : GroundAdapterParameters or None
        Processing parameters. Defaults are used when omitted.
    overwrite : bool
        Replace an existing bundle when ``True``.

    Returns
    -------
    GroundBundleResult
        Paths, counts, and warnings.

    Raises
    ------
    FileNotFoundError
        When the input file does not exist.
    FileExistsError
        When a bundle file exists and ``overwrite`` is false.
    ValueError
        When the input cloud is empty or a parameter is invalid.
    """
    source = Path(laz_path)
    if not source.is_file():
        raise FileNotFoundError(f"input LAZ does not exist: {source}")
    active = parameters or GroundAdapterParameters()
    if active.sor_k < 2:
        raise ValueError("sor_k must be at least 2")
    if active.sor_multiplier <= 0:
        raise ValueError("sor_multiplier must be positive")
    if active.low_point_cut_m < 0:
        raise ValueError("low_point_cut_m must be non-negative")

    target = Path(out_dir)
    ground_path = target / "ground.laz"
    manifest_path = target / "manifest.json"
    qa_path = target / "qa.json"
    if not overwrite:
        for path in (ground_path, manifest_path, qa_path):
            if path.exists():
                raise FileExistsError(f"output exists: {path}")
    target.mkdir(parents=True, exist_ok=True)

    try:
        import laspy  # type: ignore[import-untyped]
        from laspy import ExtraBytesParams  # type: ignore[import-untyped]
    except ImportError as exc:
        raise GroundAdapterError(
            "laspy is required for the ground writer; install femic[lidar]"
        ) from exc

    start = time.perf_counter()
    las = laspy.read(source)
    point_count = len(las)
    if point_count == 0:
        raise ValueError("input LAZ has no points")
    points = np.column_stack(
        [np.asarray(las.x), np.asarray(las.y), np.asarray(las.z)]
    ).astype(np.float64)
    classes = np.asarray(las.classification, dtype=np.uint8)

    warnings: list[str] = []
    resolved_crs, crs_warnings = _resolve_crs(las, crs)
    warnings.extend(crs_warnings)
    if vertical_datum is None:
        warnings.append("vertical datum is missing; manifest records null")
    if np.count_nonzero(classes == 2) < 100:
        warnings.append("fewer than 100 class-2 points; reference QA is weak")

    keep = np.ones(point_count, dtype=np.bool_)
    if active.sor_enabled:
        outlier = statistical_outlier_mask(
            points,
            k=active.sor_k,
            multiplier=active.sor_multiplier,
        )
        keep = ~outlier
        removed_fraction = float(np.mean(outlier))
        if removed_fraction > 0.10:
            warnings.append(
                f"SOR removed {removed_fraction:.1%} of points; review the input"
            )
    else:
        removed_fraction = 0.0

    ptd = classify_ground_ptd(
        points[keep],
        cell_size_m=active.cell_size_m,
        max_angle_deg=active.max_angle_deg,
        max_distance_m=active.max_distance_m,
        max_iterations=active.max_iterations,
    )
    if ptd.warning:
        warnings.append(ptd.warning)

    is_ground = np.zeros(point_count, dtype=np.bool_)
    is_ground[keep] = ptd.is_ground
    hag = np.full(point_count, np.nan, dtype=np.float64)
    hag[keep] = ptd.height_above_ground
    is_low = np.zeros(point_count, dtype=np.bool_)
    is_low[keep] = low_point_mask(ptd.height_above_ground, cut_m=active.low_point_cut_m)

    las.add_extra_dim(ExtraBytesParams(name="is_ground", type=np.uint8))
    las.add_extra_dim(ExtraBytesParams(name="hag", type=np.float32))
    las.add_extra_dim(ExtraBytesParams(name="is_low", type=np.uint8))
    las.add_extra_dim(ExtraBytesParams(name="ref_class", type=np.uint8))
    las.is_ground = is_ground.astype(np.uint8)
    las.hag = hag.astype(np.float32)
    las.is_low = is_low.astype(np.uint8)
    las.ref_class = classes
    las.write(ground_path)

    qa: dict[str, Any] = {
        "schema_version": QA_SCHEMA_VERSION,
        "created_utc": _utc_now(),
        "point_count": point_count,
        "ground_count": int(np.count_nonzero(is_ground)),
        "low_point_count": int(np.count_nonzero(is_low)),
        "sor_removed": int(np.count_nonzero(~keep)),
        "sor_removed_fraction": round(removed_fraction, 6),
        "seed_count": int(ptd.seed_count),
        "iterations": int(ptd.iterations),
        "tin_warning": ptd.warning,
        "hag_percentiles_m": _percentiles(hag),
        "class_counts": _class_counts(classes),
        "predicted_ground_by_class": _predicted_by_class(classes, is_ground),
        "runtime_seconds": round(time.perf_counter() - start, 3),
        "parameter_sha256": active.sha256(),
        "ground_truth_used": False,
        "note": (
            "No accuracy claim is attached. Class 1 and class 7 are not exhaustive "
            "negatives; use a separate reference patch for accuracy."
        ),
        "warnings": warnings,
    }
    qa_path.write_text(json.dumps(qa, indent=2) + "\n", encoding="utf-8")

    manifest: dict[str, Any] = {
        "schema_version": BUNDLE_SCHEMA_VERSION,
        "created_utc": qa["created_utc"],
        "source": {
            "path": source.name,
            "sha256": _sha256_file(source),
            "crs": resolved_crs,
            "vertical_datum": vertical_datum,
            "point_count": point_count,
        },
        "output": {
            "path": ground_path.name,
            "sha256": _sha256_file(ground_path),
            "point_count": point_count,
        },
        "parameters": active.to_dict(),
        "parameter_sha256": active.sha256(),
        "method": {
            "name": "ptd-inspired-ground",
            "version": "fresh-urban-forest-lab ground lane",
            "reference": "Axelsson 2000; Arbor book chapter 4",
            "clean_room": (
                "independent Python implementation; no Arbor or lidR code copied"
            ),
        },
        "qa": {
            "path": qa_path.name,
            "sha256": _sha256_file(qa_path),
        },
        "warnings": warnings,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    return GroundBundleResult(
        ground_laz=ground_path,
        manifest_path=manifest_path,
        qa_path=qa_path,
        point_count=point_count,
        ground_count=int(np.count_nonzero(is_ground)),
        low_point_count=int(np.count_nonzero(is_low)),
        warnings=tuple(warnings),
    )
