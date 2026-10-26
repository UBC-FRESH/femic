"""Resumable LidarBC tile materialization with auditable manifests.

P79.2 downloads selected public tiles into an explicit managed data root. It
keeps large artifacts out of git, resumes partial downloads, verifies SHA-256
and size on completion, and records enough retry state for a later rerun.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from femic.lidar.catalog import (
    LIDAR_SELECTION_SCHEMA_VERSION,
    LIDARBC_LICENCE_ID,
    LIDARBC_NATIVE_CRS,
    LIDARBC_SOURCE_ID,
    LidarCatalogError,
    normalize_bbox_epsg3005,
)

LIDAR_MATERIALIZATION_SCHEMA_VERSION = "femic.lidar.materialization.v1"
LIDAR_MATERIALIZATION_MANIFEST_NAME = "materialization.json"
LIDAR_MATERIALIZATION_STATUSES: tuple[str, ...] = (
    "pending",
    "downloading",
    "partial",
    "verified",
    "failed",
)
LIDAR_MATERIALIZATION_CHUNK_SIZE = 1024 * 1024


class LidarMaterializationError(RuntimeError):
    """Raised when a materialization plan, download, or manifest is invalid."""


@dataclass(frozen=True)
class LidarMaterializationTile:
    """One selected tile and its local materialization state."""

    tile_id: str
    product: str
    layer_id: int
    filename: str
    download_url: str
    relative_path: str
    status: str = "pending"
    attempts: int = 0
    expected_size_bytes: int | None = None
    size_bytes: int | None = None
    sha256: str | None = None
    remote_etag: str | None = None
    last_attempt_utc: str | None = None
    last_error: str | None = None
    resumed_from_bytes: int | None = None

    def to_dict(self) -> dict[str, object]:
        """Return the tile state as a JSON-serializable mapping."""

        return {
            "tile_id": self.tile_id,
            "product": self.product,
            "layer_id": self.layer_id,
            "filename": self.filename,
            "download_url": self.download_url,
            "relative_path": self.relative_path,
            "status": self.status,
            "attempts": self.attempts,
            "expected_size_bytes": self.expected_size_bytes,
            "size_bytes": self.size_bytes,
            "sha256": self.sha256,
            "remote_etag": self.remote_etag,
            "last_attempt_utc": self.last_attempt_utc,
            "last_error": self.last_error,
            "resumed_from_bytes": self.resumed_from_bytes,
        }


@dataclass(frozen=True)
class LidarMaterializationManifest:
    """Auditable manifest for one managed LiDAR materialization root."""

    generated_utc: str
    updated_utc: str
    source: dict[str, object]
    selection: dict[str, object]
    storage: dict[str, object]
    tiles: tuple[LidarMaterializationTile, ...]
    schema_version: str = LIDAR_MATERIALIZATION_SCHEMA_VERSION

    @property
    def tile_count(self) -> int:
        """Return the number of selected tiles."""

        return len(self.tiles)

    @property
    def verified_count(self) -> int:
        """Return the number of verified tiles."""

        return sum(tile.status == "verified" for tile in self.tiles)

    @property
    def pending_count(self) -> int:
        """Return the number of pending tiles."""

        return sum(tile.status == "pending" for tile in self.tiles)

    @property
    def partial_count(self) -> int:
        """Return the number of partial tiles."""

        return sum(tile.status == "partial" for tile in self.tiles)

    @property
    def failed_count(self) -> int:
        """Return the number of failed tiles."""

        return sum(tile.status == "failed" for tile in self.tiles)

    @property
    def downloading_count(self) -> int:
        """Return the number of tiles still marked as downloading."""

        return sum(tile.status == "downloading" for tile in self.tiles)

    @property
    def total_bytes(self) -> int:
        """Return the summed verified or partial byte count."""

        return sum(tile.size_bytes or 0 for tile in self.tiles)

    @property
    def is_complete(self) -> bool:
        """Return whether every tile is verified."""

        return self.tile_count > 0 and self.verified_count == self.tile_count

    def to_dict(self) -> dict[str, object]:
        """Return the materialization manifest as a JSON-serializable mapping."""

        return {
            "schema_version": self.schema_version,
            "generated_utc": self.generated_utc,
            "updated_utc": self.updated_utc,
            "source": self.source,
            "selection": self.selection,
            "storage": self.storage,
            "summary": {
                "tile_count": self.tile_count,
                "verified_count": self.verified_count,
                "pending_count": self.pending_count,
                "partial_count": self.partial_count,
                "failed_count": self.failed_count,
                "downloading_count": self.downloading_count,
                "total_bytes": self.total_bytes,
                "is_complete": self.is_complete,
            },
            "tiles": [tile.to_dict() for tile in self.tiles],
        }


@dataclass(frozen=True)
class LidarMaterializationResult:
    """Outcome of one materialization run."""

    manifest: LidarMaterializationManifest
    manifest_path: Path
    output_root: Path
    downloaded_count: int
    resumed_count: int
    skipped_count: int
    failed_count: int
    pending_count: int

    def to_dict(self) -> dict[str, object]:
        """Return the run result as a JSON-serializable mapping."""

        return {
            "manifest_path": str(self.manifest_path),
            "output_root": str(self.output_root),
            "downloaded_count": self.downloaded_count,
            "resumed_count": self.resumed_count,
            "skipped_count": self.skipped_count,
            "failed_count": self.failed_count,
            "pending_count": self.pending_count,
            "manifest": self.manifest.to_dict(),
        }


@dataclass(frozen=True)
class LidarMaterializationValidation:
    """Validation outcome for one materialization manifest."""

    manifest_path: Path
    is_valid: bool
    is_complete: bool
    checked_utc: str
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    tile_count: int
    verified_count: int
    total_bytes: int

    def to_dict(self) -> dict[str, object]:
        """Return the validation report as a JSON-serializable mapping."""

        return {
            "manifest_path": str(self.manifest_path),
            "is_valid": self.is_valid,
            "is_complete": self.is_complete,
            "checked_utc": self.checked_utc,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
            "tile_count": self.tile_count,
            "verified_count": self.verified_count,
            "total_bytes": self.total_bytes,
        }


@dataclass(frozen=True)
class _SelectionTile:
    tile_id: str
    product: str
    layer_id: int
    filename: str
    download_url: str
    acquisition_year: int | None


@dataclass(frozen=True)
class _SelectionRecord:
    payload: dict[str, object]
    sha256: str
    schema_version: str
    generated_utc: str
    source_id: str
    licence_id: str
    native_crs: str
    aoi_bbox_epsg3005: tuple[float, float, float, float]
    products: tuple[str, ...]
    tiles: tuple[_SelectionTile, ...]


@dataclass(frozen=True)
class _DownloadOutcome:
    resumed_from_bytes: int
    expected_size_bytes: int | None
    remote_etag: str | None


def plan_lidar_materialization(
    selection_manifest_path: Path,
    *,
    generated_utc: str | None = None,
) -> LidarMaterializationManifest:
    """Build a pending materialization manifest from a selection contract.

    The plan records deterministic relative paths and confirmed source URLs but
    does not create the output root or download any tile bytes.
    """

    selection = _load_selection(selection_manifest_path)
    timestamp = generated_utc or _now()
    tiles = tuple(
        LidarMaterializationTile(
            tile_id=tile.tile_id,
            product=tile.product,
            layer_id=tile.layer_id,
            filename=tile.filename,
            download_url=tile.download_url,
            relative_path=_tile_relative_path(selection.source_id, tile),
        )
        for tile in sorted(selection.tiles, key=lambda item: item.tile_id)
    )
    return LidarMaterializationManifest(
        generated_utc=timestamp,
        updated_utc=timestamp,
        source=_required_mapping(
            selection.payload,
            "source",
            context="selection manifest",
        ),
        selection={
            "schema_version": selection.schema_version,
            "sha256": selection.sha256,
            "generated_utc": selection.generated_utc,
            "products": list(selection.products),
            "aoi_bbox_epsg3005": list(selection.aoi_bbox_epsg3005),
            "tile_count": len(selection.tiles),
        },
        storage={
            "layout": "<source_id>/<product>/layer_<layer_id>/<year>/<filename>",
            "manifest_name": LIDAR_MATERIALIZATION_MANIFEST_NAME,
            "partial_suffix": ".part",
            "root_scope": (
                "explicit instance or external-data root; large artifacts stay "
                "out of git and may be annexed through DataLad"
            ),
        },
        tiles=tiles,
    )


def materialize_lidar_selection(
    *,
    selection_manifest_path: Path,
    output_root: Path,
    manifest_path: Path | None = None,
    plan_only: bool = False,
    max_tiles: int | None = None,
    timeout_sec: float = 60.0,
    fail_fast: bool = False,
    generated_utc: str | None = None,
) -> LidarMaterializationResult:
    """Materialize selected tiles into a managed root with resume support.

    Existing verified files are skipped after size and SHA-256 verification.
    Partial files are resumed with HTTP Range requests when supported. The
    manifest is written after each tile so an interrupted run can restart.
    """

    if max_tiles is not None and max_tiles <= 0:
        raise LidarMaterializationError("max_tiles must be positive.")
    if timeout_sec <= 0:
        raise LidarMaterializationError("timeout_sec must be positive.")
    selection = _load_selection(selection_manifest_path)
    root = output_root.expanduser().resolve()
    resolved_manifest_path = resolve_lidar_materialization_manifest_path(
        manifest_path or root / LIDAR_MATERIALIZATION_MANIFEST_NAME
    )
    if resolved_manifest_path.exists():
        manifest = _load_manifest(resolved_manifest_path)
        _assert_same_selection(manifest, selection)
    else:
        manifest = plan_lidar_materialization(
            selection_manifest_path,
            generated_utc=generated_utc,
        )
    if plan_only:
        manifest = replace(manifest, updated_utc=generated_utc or _now())
        _write_manifest(manifest, resolved_manifest_path)
        return _result_from_manifest(
            manifest,
            resolved_manifest_path,
            root,
            downloaded_count=0,
            resumed_count=0,
            skipped_count=0,
            failed_count=manifest.failed_count,
            pending_count=manifest.pending_count,
        )

    records = list(manifest.tiles)
    downloaded_count = 0
    resumed_count = 0
    skipped_count = 0
    failed_count = 0
    processed = 0
    for index, record in enumerate(records):
        if max_tiles is not None and processed >= max_tiles:
            break
        processed += 1
        final_path = _resolve_member(root, record.relative_path)
        if final_path is None:
            raise LidarMaterializationError(
                f"Manifest path escapes the output root: {record.relative_path!r}"
            )
        if (
            record.status == "verified"
            and final_path.is_file()
            and _file_matches(final_path, record)
        ):
            skipped_count += 1
            continue
        if final_path.exists():
            final_path.unlink()
        partial_path = _partial_path(final_path)
        offset = partial_path.stat().st_size if partial_path.is_file() else 0
        attempt_utc = _now()
        attempts = record.attempts + 1
        records[index] = replace(
            record,
            status="downloading",
            attempts=attempts,
            last_attempt_utc=attempt_utc,
            last_error=None,
            resumed_from_bytes=offset,
            size_bytes=None,
            sha256=None,
        )
        _write_manifest(
            replace(manifest, updated_utc=attempt_utc, tiles=tuple(records)),
            resolved_manifest_path,
        )
        try:
            outcome = _download_to_partial(
                record.download_url,
                partial_path,
                timeout_sec=timeout_sec,
            )
        except (LidarMaterializationError, OSError) as exc:
            failed_count += 1
            status = (
                "partial"
                if partial_path.is_file() and partial_path.stat().st_size > 0
                else "failed"
            )
            records[index] = replace(
                records[index],
                status=status,
                last_error=_short_error(exc),
                size_bytes=None,
                sha256=None,
            )
            _write_manifest(
                replace(manifest, updated_utc=_now(), tiles=tuple(records)),
                resolved_manifest_path,
            )
            if fail_fast:
                break
            continue
        final_path.parent.mkdir(parents=True, exist_ok=True)
        partial_path.replace(final_path)
        size_bytes = final_path.stat().st_size
        digest = _sha256_file(final_path)
        if (
            outcome.expected_size_bytes is not None
            and size_bytes != outcome.expected_size_bytes
        ):
            failed_count += 1
            records[index] = replace(
                records[index],
                status="failed",
                expected_size_bytes=outcome.expected_size_bytes,
                size_bytes=size_bytes,
                sha256=digest,
                remote_etag=outcome.remote_etag,
                resumed_from_bytes=outcome.resumed_from_bytes,
                last_error=(
                    f"size mismatch: downloaded {size_bytes} bytes, "
                    f"expected {outcome.expected_size_bytes}"
                ),
            )
        else:
            downloaded_count += 1
            if outcome.resumed_from_bytes > 0:
                resumed_count += 1
            records[index] = replace(
                records[index],
                status="verified",
                expected_size_bytes=outcome.expected_size_bytes,
                size_bytes=size_bytes,
                sha256=digest,
                remote_etag=outcome.remote_etag,
                resumed_from_bytes=outcome.resumed_from_bytes,
                last_error=None,
            )
        _write_manifest(
            replace(manifest, updated_utc=_now(), tiles=tuple(records)),
            resolved_manifest_path,
        )

    final_manifest = replace(
        manifest,
        updated_utc=_now(),
        tiles=tuple(records),
    )
    _write_manifest(final_manifest, resolved_manifest_path)
    return _result_from_manifest(
        final_manifest,
        resolved_manifest_path,
        root,
        downloaded_count=downloaded_count,
        resumed_count=resumed_count,
        skipped_count=skipped_count,
        failed_count=failed_count,
        pending_count=final_manifest.pending_count,
    )


def validate_lidar_materialization(
    manifest_path: Path,
    *,
    checked_utc: str | None = None,
    verify_checksums: bool = True,
) -> LidarMaterializationValidation:
    """Validate a materialization manifest, file sizes, checksums, and status."""

    resolved_manifest_path = resolve_lidar_materialization_manifest_path(manifest_path)
    root = resolved_manifest_path.parent
    errors: list[str] = []
    warnings: list[str] = []
    try:
        manifest = _load_manifest(resolved_manifest_path)
    except LidarMaterializationError as exc:
        return LidarMaterializationValidation(
            manifest_path=resolved_manifest_path,
            is_valid=False,
            is_complete=False,
            checked_utc=checked_utc or _now(),
            errors=(str(exc),),
            warnings=(),
            tile_count=0,
            verified_count=0,
            total_bytes=0,
        )
    for tile in manifest.tiles:
        member = _resolve_member(root, tile.relative_path)
        if member is None:
            errors.append(
                f"Tile {tile.tile_id} path escapes the materialization root: "
                f"{tile.relative_path!r}."
            )
            continue
        if tile.status == "verified":
            if not member.is_file():
                errors.append(f"Verified tile is missing: {tile.relative_path}")
                continue
            if tile.size_bytes is None or member.stat().st_size != tile.size_bytes:
                errors.append(f"Verified tile size mismatch: {tile.relative_path}")
            if not tile.sha256:
                errors.append(f"Verified tile has no SHA-256: {tile.relative_path}")
            elif verify_checksums and _sha256_file(member) != tile.sha256:
                errors.append(f"Verified tile checksum mismatch: {tile.relative_path}")
        else:
            warnings.append(f"Tile {tile.tile_id} is {tile.status} and not verified.")
    if manifest.tile_count == 0:
        errors.append("Materialization manifest contains no tiles.")
    return LidarMaterializationValidation(
        manifest_path=resolved_manifest_path,
        is_valid=not errors,
        is_complete=manifest.is_complete and not errors,
        checked_utc=checked_utc or _now(),
        errors=tuple(errors),
        warnings=tuple(warnings),
        tile_count=manifest.tile_count,
        verified_count=manifest.verified_count,
        total_bytes=manifest.total_bytes,
    )


def resolve_lidar_materialization_manifest_path(path: Path) -> Path:
    """Resolve a manifest file or an output root to its manifest path."""

    resolved = path.expanduser().resolve()
    if resolved.is_dir():
        return resolved / LIDAR_MATERIALIZATION_MANIFEST_NAME
    return resolved


def write_lidar_materialization_manifest(
    manifest: LidarMaterializationManifest,
    path: Path,
) -> Path:
    """Write a materialization manifest atomically and return the path."""

    _write_manifest(manifest, path)
    return path.expanduser().resolve()


def _load_selection(path: Path) -> _SelectionRecord:
    payload = _read_json_object(path, context="LiDAR selection manifest")
    schema_version = _required_str(
        payload,
        "schema_version",
        context="selection manifest",
    )
    if schema_version != LIDAR_SELECTION_SCHEMA_VERSION:
        raise LidarMaterializationError(
            f"Unsupported selection manifest schema {schema_version!r}; expected "
            f"{LIDAR_SELECTION_SCHEMA_VERSION!r}."
        )
    source = _required_mapping(payload, "source", context="selection manifest")
    source_id = _required_str(source, "source_id", context="selection source")
    licence_id = _required_str(source, "licence_id", context="selection source")
    native_crs = _required_str(source, "native_crs", context="selection source")
    if source_id != LIDARBC_SOURCE_ID:
        raise LidarMaterializationError(
            f"Materialization currently supports only {LIDARBC_SOURCE_ID!r}; "
            f"selection uses {source_id!r}."
        )
    if licence_id != LIDARBC_LICENCE_ID:
        raise LidarMaterializationError(
            f"Materialization requires the {LIDARBC_LICENCE_ID} source licence; "
            f"selection uses {licence_id!r}."
        )
    if native_crs != LIDARBC_NATIVE_CRS:
        raise LidarMaterializationError(
            f"Materialization requires native CRS {LIDARBC_NATIVE_CRS}; "
            f"selection uses {native_crs!r}."
        )
    aoi = _required_mapping(payload, "aoi", context="selection manifest")
    raw_bbox = _required_list(aoi, "bbox_epsg3005", context="selection AOI")
    try:
        bbox = normalize_bbox_epsg3005(raw_bbox)
    except LidarCatalogError as exc:
        raise LidarMaterializationError(f"Invalid selection AOI: {exc}") from exc
    products = _required_str_list(
        payload.get("products"),
        context="selection products",
    )
    raw_tiles = _required_list(payload, "tiles", context="selection manifest")
    tiles: list[_SelectionTile] = []
    seen_ids: set[str] = set()
    for index, item in enumerate(raw_tiles, start=1):
        tile = _optional_mapping(item, context=f"selection tile {index}")
        tile_id = _required_str(tile, "tile_id", context=f"selection tile {index}")
        if tile_id in seen_ids:
            raise LidarMaterializationError(
                f"Selection manifest contains duplicate tile ID {tile_id!r}."
            )
        seen_ids.add(tile_id)
        tiles.append(
            _SelectionTile(
                tile_id=tile_id,
                product=_required_str(
                    tile,
                    "product",
                    context=f"selection tile {index}",
                ),
                layer_id=_required_int(
                    tile,
                    "layer_id",
                    context=f"selection tile {index}",
                ),
                filename=_required_str(
                    tile,
                    "filename",
                    context=f"selection tile {index}",
                ),
                download_url=_required_str(
                    tile,
                    "download_url",
                    context=f"selection tile {index}",
                ),
                acquisition_year=_optional_int(tile.get("acquisition_year")),
            )
        )
    if not tiles:
        raise LidarMaterializationError("Selection manifest contains no tiles.")
    return _SelectionRecord(
        payload=payload,
        sha256=_sha256_bytes(_canonical_json_bytes(payload)),
        schema_version=schema_version,
        generated_utc=_optional_str(payload.get("generated_utc")) or "",
        source_id=source_id,
        licence_id=licence_id,
        native_crs=native_crs,
        aoi_bbox_epsg3005=bbox,
        products=products,
        tiles=tuple(tiles),
    )


def _load_manifest(path: Path) -> LidarMaterializationManifest:
    payload = _read_json_object(path, context="LiDAR materialization manifest")
    schema_version = _required_str(
        payload,
        "schema_version",
        context="materialization manifest",
    )
    if schema_version != LIDAR_MATERIALIZATION_SCHEMA_VERSION:
        raise LidarMaterializationError(
            f"Unsupported materialization manifest schema {schema_version!r}; "
            f"expected {LIDAR_MATERIALIZATION_SCHEMA_VERSION!r}."
        )
    raw_tiles = _required_list(payload, "tiles", context="materialization manifest")
    tiles: list[LidarMaterializationTile] = []
    for index, item in enumerate(raw_tiles, start=1):
        tile = _optional_mapping(item, context=f"materialization tile {index}")
        status = _required_str(tile, "status", context=f"materialization tile {index}")
        if status not in LIDAR_MATERIALIZATION_STATUSES:
            raise LidarMaterializationError(
                f"Materialization tile {index} has unsupported status {status!r}."
            )
        tiles.append(
            LidarMaterializationTile(
                tile_id=_required_str(
                    tile,
                    "tile_id",
                    context=f"materialization tile {index}",
                ),
                product=_required_str(
                    tile,
                    "product",
                    context=f"materialization tile {index}",
                ),
                layer_id=_required_int(
                    tile,
                    "layer_id",
                    context=f"materialization tile {index}",
                ),
                filename=_required_str(
                    tile,
                    "filename",
                    context=f"materialization tile {index}",
                ),
                download_url=_required_str(
                    tile,
                    "download_url",
                    context=f"materialization tile {index}",
                ),
                relative_path=_required_str(
                    tile,
                    "relative_path",
                    context=f"materialization tile {index}",
                ),
                status=status,
                attempts=_optional_int(tile.get("attempts")) or 0,
                expected_size_bytes=_optional_int(tile.get("expected_size_bytes")),
                size_bytes=_optional_int(tile.get("size_bytes")),
                sha256=_optional_str(tile.get("sha256")),
                remote_etag=_optional_str(tile.get("remote_etag")),
                last_attempt_utc=_optional_str(tile.get("last_attempt_utc")),
                last_error=_optional_str(tile.get("last_error")),
                resumed_from_bytes=_optional_int(tile.get("resumed_from_bytes")),
            )
        )
    generated_utc = _optional_str(payload.get("generated_utc")) or ""
    return LidarMaterializationManifest(
        generated_utc=generated_utc,
        updated_utc=_optional_str(payload.get("updated_utc")) or generated_utc,
        source=_required_mapping(payload, "source", context="materialization manifest"),
        selection=_required_mapping(
            payload,
            "selection",
            context="materialization manifest",
        ),
        storage=_optional_mapping(payload.get("storage"), context="storage"),
        tiles=tuple(tiles),
    )


def _assert_same_selection(
    manifest: LidarMaterializationManifest,
    selection: _SelectionRecord,
) -> None:
    manifest_sha = _optional_str(manifest.selection.get("sha256"))
    if manifest_sha != selection.sha256:
        raise LidarMaterializationError(
            "Materialization manifest does not match the current selection; "
            "use a new output root or rebuild the manifest."
        )
    manifest_tiles = {tile.tile_id for tile in manifest.tiles}
    selection_tiles = {tile.tile_id for tile in selection.tiles}
    if manifest_tiles != selection_tiles:
        raise LidarMaterializationError(
            "Materialization manifest tile set does not match the current selection."
        )


def _download_to_partial(
    url: str,
    partial_path: Path,
    *,
    timeout_sec: float,
) -> _DownloadOutcome:
    if not url.strip():
        raise LidarMaterializationError("Tile download URL is empty.")
    partial_path.parent.mkdir(parents=True, exist_ok=True)
    offset = partial_path.stat().st_size if partial_path.is_file() else 0
    headers = {"Range": f"bytes={offset}-"} if offset > 0 else {}
    request = Request(url, headers=headers)
    try:
        with urlopen(request, timeout=timeout_sec) as response:
            status = getattr(response, "status", None) or 200
            response_headers = getattr(response, "headers", {})
            expected_size = _expected_size(
                response_headers,
                offset=offset,
                status=status,
            )
            etag = _optional_str(response_headers.get("ETag"))
            mode = "ab" if offset > 0 and status == 206 else "wb"
            resumed_from = offset if mode == "ab" else 0
            with partial_path.open(mode) as handle:
                while True:
                    chunk = response.read(LIDAR_MATERIALIZATION_CHUNK_SIZE)
                    if not chunk:
                        break
                    handle.write(chunk)
    except (HTTPError, URLError, OSError) as exc:
        raise LidarMaterializationError(f"Unable to download {url}: {exc}") from exc
    return _DownloadOutcome(
        resumed_from_bytes=resumed_from,
        expected_size_bytes=expected_size,
        remote_etag=etag,
    )


def _expected_size(
    headers: Mapping[str, str],
    *,
    offset: int,
    status: int,
) -> int | None:
    content_range = headers.get("Content-Range")
    if content_range:
        _, _, total = content_range.rpartition("/")
        if total.strip().isdigit():
            return int(total.strip())
    content_length = headers.get("Content-Length")
    if content_length and content_length.strip().isdigit():
        base = offset if status == 206 else 0
        return base + int(content_length.strip())
    return None


def _file_matches(path: Path, tile: LidarMaterializationTile) -> bool:
    if tile.size_bytes is not None and path.stat().st_size != tile.size_bytes:
        return False
    if not tile.sha256:
        return False
    return _sha256_file(path) == tile.sha256


def _tile_relative_path(source_id: str, tile: _SelectionTile) -> str:
    year = (
        str(tile.acquisition_year) if tile.acquisition_year is not None else "unknown"
    )
    return (
        f"{_safe_component(source_id)}/{_safe_component(tile.product)}/"
        f"layer_{tile.layer_id}/{year}/{_safe_filename(tile.filename)}"
    )


def _safe_component(value: str) -> str:
    text = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip()).strip("._-")
    return text or "unknown"


def _safe_filename(value: str) -> str:
    text = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(value).name).strip("._-")
    return text or "artifact"


def _partial_path(final_path: Path) -> Path:
    return final_path.with_name(f"{final_path.name}.part")


def _resolve_member(root: Path, relative_path: str) -> Path | None:
    candidate = (root / relative_path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    return candidate


def _result_from_manifest(
    manifest: LidarMaterializationManifest,
    manifest_path: Path,
    output_root: Path,
    *,
    downloaded_count: int,
    resumed_count: int,
    skipped_count: int,
    failed_count: int,
    pending_count: int,
) -> LidarMaterializationResult:
    return LidarMaterializationResult(
        manifest=manifest,
        manifest_path=manifest_path,
        output_root=output_root,
        downloaded_count=downloaded_count,
        resumed_count=resumed_count,
        skipped_count=skipped_count,
        failed_count=failed_count,
        pending_count=pending_count,
    )


def _write_manifest(
    manifest: LidarMaterializationManifest,
    path: Path,
) -> None:
    resolved = path.expanduser().resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    temporary = resolved.with_name(f".{resolved.name}.tmp")
    temporary.write_text(_pretty_json(manifest.to_dict()), encoding="utf-8")
    temporary.replace(resolved)


def _read_json_object(path: Path, *, context: str) -> dict[str, object]:
    try:
        payload: object = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise LidarMaterializationError(
            f"Unable to read {context}: {path}: {exc}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise LidarMaterializationError(
            f"Invalid JSON in {context}: {path}: {exc}"
        ) from exc
    if not isinstance(payload, Mapping):
        raise LidarMaterializationError(f"{context} must be a JSON object: {path}")
    return {str(key): value for key, value in payload.items()}


def _required_mapping(
    mapping: Mapping[str, object],
    key: str,
    *,
    context: str,
) -> dict[str, object]:
    value = mapping.get(key)
    if not isinstance(value, Mapping):
        raise LidarMaterializationError(f"{context} field {key!r} must be an object.")
    return {str(item_key): item for item_key, item in value.items()}


def _optional_mapping(value: object, *, context: str) -> dict[str, object]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise LidarMaterializationError(f"{context} must be an object.")
    return {str(key): item for key, item in value.items()}


def _required_list(
    mapping: Mapping[str, object],
    key: str,
    *,
    context: str,
) -> list[object]:
    value = mapping.get(key)
    if not isinstance(value, list):
        raise LidarMaterializationError(f"{context} field {key!r} must be a list.")
    return value


def _required_str(
    mapping: Mapping[str, object],
    key: str,
    *,
    context: str,
) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        raise LidarMaterializationError(
            f"{context} field {key!r} must be a non-empty string."
        )
    return value.strip()


def _optional_str(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text or None


def _required_int(
    mapping: Mapping[str, object],
    key: str,
    *,
    context: str,
) -> int:
    value = mapping.get(key)
    parsed = _optional_int(value)
    if parsed is None:
        raise LidarMaterializationError(f"{context} field {key!r} must be an integer.")
    return parsed


def _optional_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return None


def _required_str_list(value: object, *, context: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise LidarMaterializationError(f"{context} must be a list.")
    items: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise LidarMaterializationError(
                f"{context} entries must be non-empty strings."
            )
        items.append(item.strip())
    if not items:
        raise LidarMaterializationError(f"{context} must not be empty.")
    return tuple(items)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(LIDAR_MATERIALIZATION_CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _canonical_json_bytes(payload: object) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _pretty_json(payload: object) -> str:
    return (
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n"
    )


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _short_error(exc: BaseException) -> str:
    text = str(exc).strip() or type(exc).__name__
    return text[:500]
