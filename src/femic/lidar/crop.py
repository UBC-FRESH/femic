"""Local bounding-box crop for large LAZ tiles.

LidarBC distributes LAZ tiles that can be much larger than a block AOI.
LAZ is not COPC, so a range read does not avoid the full download. This
module is the one-time local step: read the tile in chunks, keep the points
inside a bbox, and write a small LAZ plus a manifest.

It is opt-in and does not change any default FEMIC product.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

LAZ_CROP_SCHEMA_VERSION = "femic.laz_crop.v1"
DEFAULT_CROP_CHUNK_SIZE = 1_000_000


class LazCropError(RuntimeError):
    """Raised when a LAZ crop is invalid or empty."""


@dataclass(frozen=True)
class LazCropResult:
    """Result of a LAZ bounding-box crop.

    Attributes
    ----------
    output_path : Path
        Written LAZ.
    manifest_path : Path
        Written manifest.
    input_point_count : int
        Points in the input tile.
    output_point_count : int
        Points written.
    bbox : tuple of float
        ``(minx, miny, maxx, maxy)`` in the source CRS.
    warnings : tuple of str
        Non-fatal warnings.
    """

    output_path: Path
    manifest_path: Path
    input_point_count: int
    output_point_count: int
    bbox: tuple[float, float, float, float]
    warnings: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-friendly summary.

        Returns
        -------
        dict
            Paths, counts, bbox, and warnings.
        """
        return {
            "output_path": str(self.output_path),
            "manifest_path": str(self.manifest_path),
            "input_point_count": self.input_point_count,
            "output_point_count": self.output_point_count,
            "bbox": list(self.bbox),
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


def _validate_bbox(bbox: tuple[float, float, float, float]) -> None:
    """Validate a crop bbox.

    Parameters
    ----------
    bbox : tuple of float
        ``(minx, miny, maxx, maxy)``.

    Raises
    ------
    LazCropError
        When the bbox is reversed or non-finite.
    """
    minx, miny, maxx, maxy = bbox
    if not all(isinstance(value, (int, float)) for value in bbox):
        raise LazCropError("bbox must contain four numbers")
    if minx >= maxx or miny >= maxy:
        raise LazCropError("bbox must satisfy minx < maxx and miny < maxy")


def crop_laz_by_bbox(
    laz_path: Path,
    out_path: Path,
    bbox: tuple[float, float, float, float],
    *,
    overwrite: bool = False,
) -> LazCropResult:
    """Crop a local LAZ to a bounding box.

    Parameters
    ----------
    laz_path : Path
        Input LAZ.
    out_path : Path
        Output LAZ.
    bbox : tuple of float
        ``(minx, miny, maxx, maxy)`` in the source CRS.
    overwrite : bool
        Replace an existing output and manifest.

    Returns
    -------
    LazCropResult
        Paths, counts, bbox, and warnings.

    Raises
    ------
    LazCropError
        When the input is missing, the bbox is invalid, the crop is empty, or
        ``laspy`` is unavailable.
    """
    _validate_bbox(bbox)
    source = Path(laz_path)
    target = Path(out_path)
    manifest_path = target.with_suffix(".manifest.json")
    if not source.is_file():
        raise LazCropError(f"input LAZ does not exist: {source}")
    if not overwrite and (target.exists() or manifest_path.exists()):
        raise LazCropError(f"output exists: {target} or {manifest_path}")
    try:
        import laspy  # type: ignore[import-untyped]
        from laspy.point.record import ScaleAwarePointRecord  # type: ignore[import-untyped]
    except ImportError as exc:
        raise LazCropError(
            "laspy is required for LAZ cropping; install femic[lidar]"
        ) from exc

    minx, miny, maxx, maxy = bbox
    chunks: list[Any] = []
    input_count = 0
    with laspy.open(source) as reader:
        header = reader.header
        for points in reader.chunk_iterator(DEFAULT_CROP_CHUNK_SIZE):
            input_count += len(points)
            x = points.x
            y = points.y
            inside = (x >= minx) & (x <= maxx) & (y >= miny) & (y <= maxy)
            if bool(inside.any()):
                chunks.append(points[inside])
    output_count = sum(len(chunk) for chunk in chunks)
    if output_count == 0:
        raise LazCropError("bbox contains no points")
    array = np.concatenate([chunk.array for chunk in chunks])
    record = ScaleAwarePointRecord(
        array,
        header.point_format,
        header.scales,
        header.offsets,
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and overwrite:
        target.unlink()
    out = laspy.LasData(header, points=record)
    out.write(target)
    parsed_crs = header.parse_crs()
    warnings: list[str] = []
    if parsed_crs is None:
        warnings.append("source CRS is missing; bbox is interpreted as unknown units")
    manifest = {
        "schema_version": LAZ_CROP_SCHEMA_VERSION,
        "created_utc": _utc_now(),
        "source": {
            "path": source.name,
            "sha256": _sha256_file(source),
            "point_count": input_count,
            "crs": str(parsed_crs) if parsed_crs is not None else None,
        },
        "output": {
            "path": target.name,
            "sha256": _sha256_file(target),
            "point_count": output_count,
        },
        "bbox": list(bbox),
        "warnings": warnings,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return LazCropResult(
        output_path=target,
        manifest_path=manifest_path,
        input_point_count=input_count,
        output_point_count=output_count,
        bbox=bbox,
        warnings=tuple(warnings),
    )
