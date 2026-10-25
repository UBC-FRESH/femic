"""Versioned public hydrology data bundles.

P114.2 packages an already-reviewed hydrology domain into a portable bundle.
It does not download public layers itself; callers provide local source paths
from BCDC, WFS, DataLad, or a reviewed project mirror.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import shutil
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from pathlib import Path

from femic.hydrology.domain import (
    HYDROLOGY_REQUIRED_LAYER_ROLES,
    HYDROLOGY_SOURCE_REGISTRY_VERSION,
    HydrologyDomainManifest,
    HydrologyLayerSpec,
    find_hydrology_source,
    load_hydrology_domain_manifest,
    validate_hydrology_domain,
)

HYDROLOGY_BUNDLE_SCHEMA_VERSION = "femic.hydrology.bundle.v1"
HYDROLOGY_BUNDLE_MANIFEST_NAME = "bundle.json"
HYDROLOGY_BUNDLE_LAYERS_DIR = "layers"
HYDROLOGY_BUNDLE_STATUSES: tuple[str, ...] = (
    "planned",
    "materialized",
    "missing",
)
DEFAULT_HYDROLOGY_BUNDLE_VERSION = "0.1.0"
SHA256_PATTERN = re.compile(r"^[0-9a-fA-F]{64}$")


class HydrologyBundleError(RuntimeError):
    """Raised when a hydrology bundle plan, build, or manifest is invalid."""


@dataclass(frozen=True)
class HydrologyBundleLayer:
    """One layer record in a hydrology data bundle."""

    layer_id: str
    role: str
    source_id: str | None
    relative_path: str
    format: str
    crs: str
    licence_id: str
    status: str
    checksum_sha256: str | None = None
    size_bytes: int | None = None
    source_url: str | None = None
    retrieval_utc: str | None = None
    notes: str = ""

    def to_dict(self) -> dict[str, object]:
        """Return the layer record as a JSON-serializable mapping."""

        return {
            "layer_id": self.layer_id,
            "role": self.role,
            "source_id": self.source_id,
            "relative_path": self.relative_path,
            "format": self.format,
            "crs": self.crs,
            "licence_id": self.licence_id,
            "status": self.status,
            "checksum_sha256": self.checksum_sha256,
            "size_bytes": self.size_bytes,
            "source_url": self.source_url,
            "retrieval_utc": self.retrieval_utc,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class HydrologyBundleGap:
    """One missing or unresolved bundle layer."""

    layer_id: str
    role: str
    reason: str

    def to_dict(self) -> dict[str, object]:
        """Return the gap as a JSON-serializable mapping."""

        return {
            "layer_id": self.layer_id,
            "role": self.role,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class HydrologyBundleManifest:
    """Versioned public hydrology data bundle manifest."""

    bundle_id: str
    bundle_version: str
    generated_utc: str
    domain_id: str
    domain_sha256: str
    aoi_bbox_epsg3005: tuple[float, float, float, float]
    layers: tuple[HydrologyBundleLayer, ...]
    gaps: tuple[HydrologyBundleGap, ...] = ()
    caveats: tuple[str, ...] = ()
    provenance: dict[str, object] = field(default_factory=dict)
    schema_version: str = HYDROLOGY_BUNDLE_SCHEMA_VERSION

    @property
    def layer_count(self) -> int:
        """Return the number of layer records."""

        return len(self.layers)

    @property
    def materialized_count(self) -> int:
        """Return the number of materialized layers."""

        return sum(layer.status == "materialized" for layer in self.layers)

    @property
    def is_complete(self) -> bool:
        """Return whether every layer is materialized and no gaps remain."""

        return (
            self.layer_count > 0
            and not self.gaps
            and self.materialized_count == self.layer_count
        )

    def to_dict(self) -> dict[str, object]:
        """Return the bundle manifest as a JSON-serializable mapping."""

        return {
            "schema_version": self.schema_version,
            "bundle_id": self.bundle_id,
            "bundle_version": self.bundle_version,
            "generated_utc": self.generated_utc,
            "domain_id": self.domain_id,
            "domain_sha256": self.domain_sha256,
            "aoi_bbox_epsg3005": list(self.aoi_bbox_epsg3005),
            "summary": {
                "layer_count": self.layer_count,
                "materialized_count": self.materialized_count,
                "gap_count": len(self.gaps),
                "is_complete": self.is_complete,
            },
            "layers": [layer.to_dict() for layer in self.layers],
            "gaps": [gap.to_dict() for gap in self.gaps],
            "caveats": list(self.caveats),
            "provenance": self.provenance,
        }


@dataclass(frozen=True)
class HydrologyBundleBuildResult:
    """Paths and manifest returned by a successful bundle build."""

    bundle_dir: Path
    manifest_path: Path
    manifest: HydrologyBundleManifest

    def to_dict(self) -> dict[str, object]:
        """Return the build result as a JSON-serializable mapping."""

        return {
            "bundle_dir": str(self.bundle_dir),
            "manifest_path": str(self.manifest_path),
            "manifest": self.manifest.to_dict(),
        }


@dataclass(frozen=True)
class HydrologyBundleLayerAudit:
    """Local file audit for one bundle layer."""

    layer_id: str
    role: str
    relative_path: str
    status: str
    exists: bool
    size_bytes: int | None
    expected_size_bytes: int | None
    checksum_ok: bool | None
    issues: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        """Return the layer audit as a JSON-serializable mapping."""

        return {
            "layer_id": self.layer_id,
            "role": self.role,
            "relative_path": self.relative_path,
            "status": self.status,
            "exists": self.exists,
            "size_bytes": self.size_bytes,
            "expected_size_bytes": self.expected_size_bytes,
            "checksum_ok": self.checksum_ok,
            "issues": list(self.issues),
        }


@dataclass(frozen=True)
class HydrologyBundleAudit:
    """Validation and local-file audit for one hydrology bundle."""

    bundle_id: str
    bundle_dir: Path
    manifest_path: Path
    is_valid: bool
    is_complete: bool
    checked_utc: str
    layers: tuple[HydrologyBundleLayerAudit, ...]
    errors: tuple[str, ...]
    warnings: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        """Return the audit as a JSON-serializable mapping."""

        return {
            "bundle_id": self.bundle_id,
            "bundle_dir": str(self.bundle_dir),
            "manifest_path": str(self.manifest_path),
            "is_valid": self.is_valid,
            "is_complete": self.is_complete,
            "checked_utc": self.checked_utc,
            "layers": [layer.to_dict() for layer in self.layers],
            "errors": list(self.errors),
            "warnings": list(self.warnings),
        }


def plan_hydrology_bundle(
    domain: HydrologyDomainManifest,
    *,
    bundle_dir: Path,
    aoi_bbox_epsg3005: Sequence[object],
    sources: Mapping[str, Path] | None = None,
    bundle_version: str = DEFAULT_HYDROLOGY_BUNDLE_VERSION,
    generated_utc: str | None = None,
) -> HydrologyBundleManifest:
    """Plan a hydrology bundle and report missing source layers.

    ``sources`` maps domain layer IDs to local files. Planning never copies
    files; it records planned paths, checksums, sizes, and gaps.
    """

    validation = validate_hydrology_domain(domain)
    if not validation.is_valid:
        raise HydrologyBundleError("; ".join(validation.errors))
    if not bundle_version.strip():
        raise HydrologyBundleError("Bundle version must be non-empty.")
    bbox = _normalize_bbox(aoi_bbox_epsg3005)
    source_map = _normalize_sources(sources)
    known_layer_ids = {layer.layer_id for layer in domain.layers}
    unknown_sources = set(source_map) - known_layer_ids
    if unknown_sources:
        raise HydrologyBundleError(
            "Sources reference unknown layer IDs: "
            + ", ".join(sorted(unknown_sources))
            + "."
        )
    timestamp = generated_utc or _now()
    layers: list[HydrologyBundleLayer] = []
    gaps: list[HydrologyBundleGap] = []
    for layer in sorted(domain.layers, key=lambda item: item.layer_id):
        source_path = source_map.get(layer.layer_id)
        source_spec = (
            find_hydrology_source(layer.source_id) if layer.source_id else None
        )
        relative_path = _bundle_layer_path(layer)
        source_url = (
            (source_spec.service_url or source_spec.catalogue_url)
            if source_spec is not None
            else None
        )
        if source_path is None:
            status = "missing"
            checksum = None
            size = None
            gaps.append(
                HydrologyBundleGap(
                    layer_id=layer.layer_id,
                    role=layer.role,
                    reason="No local source path was supplied.",
                )
            )
        elif not source_path.is_file():
            status = "missing"
            checksum = None
            size = None
            gaps.append(
                HydrologyBundleGap(
                    layer_id=layer.layer_id,
                    role=layer.role,
                    reason=f"Source file is missing: {source_path}",
                )
            )
        else:
            status = "planned"
            checksum = _sha256_file(source_path)
            size = source_path.stat().st_size
        layers.append(
            HydrologyBundleLayer(
                layer_id=layer.layer_id,
                role=layer.role,
                source_id=layer.source_id,
                relative_path=relative_path,
                format=layer.format,
                crs=layer.crs,
                licence_id=layer.licence_id,
                status=status,
                checksum_sha256=checksum,
                size_bytes=size,
                source_url=source_url,
                retrieval_utc=timestamp if source_path is not None else None,
                notes=layer.description,
            )
        )
    provenance: dict[str, object] = {
        "producer": "femic.hydrology.bundle",
        "source_registry_version": HYDROLOGY_SOURCE_REGISTRY_VERSION,
        "domain_schema_version": domain.schema_version,
        "bundle_dir_name": bundle_dir.expanduser().resolve().name,
    }
    records = tuple(layers)
    bundle_id = _bundle_id(
        domain_id=domain.domain_id,
        domain_sha256=_sha256_json(domain.to_dict()),
        aoi_bbox=bbox,
        bundle_version=bundle_version,
        layers=records,
    )
    return HydrologyBundleManifest(
        bundle_id=bundle_id,
        bundle_version=bundle_version,
        generated_utc=timestamp,
        domain_id=domain.domain_id,
        domain_sha256=_sha256_json(domain.to_dict()),
        aoi_bbox_epsg3005=bbox,
        layers=records,
        gaps=tuple(gaps),
        caveats=(
            "Bundle layers are reviewed public or approved inputs.",
            (
                "Large layer payloads may be DataLad annex objects; materialize "
                "them before audit or use."
            ),
            "No reprojection or resampling is performed while bundling.",
        ),
        provenance=provenance,
    )


def build_hydrology_bundle(
    domain_manifest_path: Path,
    bundle_dir: Path,
    *,
    aoi_bbox_epsg3005: Sequence[object],
    sources: Mapping[str, Path],
    bundle_version: str = DEFAULT_HYDROLOGY_BUNDLE_VERSION,
    generated_utc: str | None = None,
    overwrite: bool = False,
) -> HydrologyBundleBuildResult:
    """Copy local source layers into a versioned hydrology bundle.

    All domain layers must have a local source file. The build is atomic and
    writes ``bundle.json`` at the bundle root.
    """

    domain = load_hydrology_domain_manifest(domain_manifest_path)
    output = bundle_dir.expanduser().resolve()
    _prepare_output(output, overwrite=overwrite)
    plan = plan_hydrology_bundle(
        domain,
        bundle_dir=output,
        aoi_bbox_epsg3005=aoi_bbox_epsg3005,
        sources=sources,
        bundle_version=bundle_version,
        generated_utc=generated_utc,
    )
    if plan.gaps:
        raise HydrologyBundleError(
            "Cannot build an incomplete bundle: "
            + "; ".join(gap.reason for gap in plan.gaps)
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    temp_dir = Path(tempfile.mkdtemp(prefix=f".{output.name}.", dir=output.parent))
    try:
        layer_records: list[HydrologyBundleLayer] = []
        for layer in plan.layers:
            source_path = sources[layer.layer_id].expanduser().resolve()
            destination = temp_dir / layer.relative_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source_path, destination)
            layer_records.append(
                replace(
                    layer,
                    status="materialized",
                    checksum_sha256=_sha256_file(destination),
                    size_bytes=destination.stat().st_size,
                )
            )
        records = tuple(layer_records)
        domain_sha256 = _sha256_json(domain.to_dict())
        manifest = replace(
            plan,
            bundle_id=_bundle_id(
                domain_id=domain.domain_id,
                domain_sha256=domain_sha256,
                aoi_bbox=plan.aoi_bbox_epsg3005,
                bundle_version=bundle_version,
                layers=records,
            ),
            layers=records,
            gaps=(),
            generated_utc=plan.generated_utc,
            provenance={
                **plan.provenance,
                "materialized_utc": _now(),
            },
        )
        manifest_path = temp_dir / HYDROLOGY_BUNDLE_MANIFEST_NAME
        manifest_path.write_text(_pretty_json(manifest.to_dict()), encoding="utf-8")
        if output.exists():
            if any(output.iterdir()):
                _assert_replaceable_bundle(output)
                shutil.rmtree(output)
            else:
                output.rmdir()
        temp_dir.replace(output)
        return HydrologyBundleBuildResult(
            bundle_dir=output,
            manifest_path=output / HYDROLOGY_BUNDLE_MANIFEST_NAME,
            manifest=manifest,
        )
    except Exception:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise


def validate_hydrology_bundle_manifest(
    manifest: HydrologyBundleManifest,
) -> tuple[str, ...]:
    """Validate the structural contract of a hydrology bundle manifest."""

    errors: list[str] = []
    if manifest.schema_version != HYDROLOGY_BUNDLE_SCHEMA_VERSION:
        errors.append(
            f"Unsupported hydrology bundle schema {manifest.schema_version!r}; "
            f"expected {HYDROLOGY_BUNDLE_SCHEMA_VERSION!r}."
        )
    if not manifest.bundle_id.strip():
        errors.append("Bundle ID must be non-empty.")
    if not manifest.bundle_version.strip():
        errors.append("Bundle version must be non-empty.")
    if not manifest.domain_id.strip():
        errors.append("Domain ID must be non-empty.")
    if not SHA256_PATTERN.match(manifest.domain_sha256):
        errors.append("Domain SHA-256 is invalid.")
    if len(manifest.aoi_bbox_epsg3005) != 4:
        errors.append("AOI bbox must contain four numbers.")
    else:
        minx, miny, maxx, maxy = manifest.aoi_bbox_epsg3005
        if not all(math.isfinite(value) for value in (minx, miny, maxx, maxy)):
            errors.append("AOI bbox must be finite.")
        elif minx >= maxx or miny >= maxy:
            errors.append("AOI bbox requires minx < maxx and miny < maxy.")
    if not manifest.layers:
        errors.append("Bundle must contain at least one layer.")
    layer_ids: set[str] = set()
    roles: set[str] = set()
    for layer in manifest.layers:
        if layer.layer_id in layer_ids:
            errors.append(f"Duplicate bundle layer ID {layer.layer_id!r}.")
        layer_ids.add(layer.layer_id)
        roles.add(layer.role)
        if layer.status not in HYDROLOGY_BUNDLE_STATUSES:
            errors.append(
                f"Layer {layer.layer_id!r} has unsupported status {layer.status!r}."
            )
        if not layer.licence_id.strip():
            errors.append(f"Layer {layer.layer_id!r} has no licence.")
        if not layer.relative_path.strip():
            errors.append(f"Layer {layer.layer_id!r} has no relative path.")
        if (
            layer.source_id is not None
            and find_hydrology_source(layer.source_id) is None
        ):
            errors.append(
                f"Layer {layer.layer_id!r} references unknown source "
                f"{layer.source_id!r}."
            )
        if layer.checksum_sha256 is not None and not SHA256_PATTERN.match(
            layer.checksum_sha256
        ):
            errors.append(f"Layer {layer.layer_id!r} has an invalid SHA-256.")
        if layer.size_bytes is not None and layer.size_bytes < 0:
            errors.append(f"Layer {layer.layer_id!r} has a negative size.")
    missing_roles = [
        role for role in HYDROLOGY_REQUIRED_LAYER_ROLES if role not in roles
    ]
    if missing_roles:
        errors.append(
            "Bundle is missing required layer roles: " + ", ".join(missing_roles) + "."
        )
    return tuple(errors)


def write_hydrology_bundle_manifest(
    manifest: HydrologyBundleManifest,
    path: Path,
) -> Path:
    """Write a hydrology bundle manifest as pretty-printed JSON."""

    resolved = path.expanduser().resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(_pretty_json(manifest.to_dict()), encoding="utf-8")
    return resolved


def load_hydrology_bundle_manifest(path: Path) -> HydrologyBundleManifest:
    """Load a hydrology bundle manifest from JSON."""

    resolved = _resolve_manifest_path(path)
    payload = _read_json_object(resolved, context="hydrology bundle manifest")
    schema_version = _required_str(
        payload,
        "schema_version",
        context="hydrology bundle manifest",
    )
    if schema_version != HYDROLOGY_BUNDLE_SCHEMA_VERSION:
        raise HydrologyBundleError(
            f"Unsupported hydrology bundle schema {schema_version!r}; expected "
            f"{HYDROLOGY_BUNDLE_SCHEMA_VERSION!r}."
        )
    layers = tuple(
        _layer_from_payload(item, index=index)
        for index, item in enumerate(
            _required_list(payload, "layers", context="hydrology bundle"),
            start=1,
        )
    )
    gaps = tuple(
        _gap_from_payload(item, index=index)
        for index, item in enumerate(
            _required_list(payload, "gaps", context="hydrology bundle"),
            start=1,
        )
    )
    return HydrologyBundleManifest(
        bundle_id=_required_str(payload, "bundle_id", context="hydrology bundle"),
        bundle_version=_required_str(
            payload,
            "bundle_version",
            context="hydrology bundle",
        ),
        generated_utc=_optional_str(payload.get("generated_utc")) or "",
        domain_id=_required_str(payload, "domain_id", context="hydrology bundle"),
        domain_sha256=_required_str(
            payload,
            "domain_sha256",
            context="hydrology bundle",
        ),
        aoi_bbox_epsg3005=_required_bbox(payload, context="hydrology bundle"),
        layers=layers,
        gaps=gaps,
        caveats=_optional_str_list(payload.get("caveats"), context="caveats"),
        provenance=_optional_mapping(payload.get("provenance"), context="provenance"),
        schema_version=schema_version,
    )


def audit_hydrology_bundle(
    path: Path,
    *,
    data_root: Path | None = None,
    checked_utc: str | None = None,
) -> HydrologyBundleAudit:
    """Validate a bundle manifest and audit its local layer files."""

    manifest_path = _resolve_manifest_path(path)
    bundle_dir = manifest_path.parent
    base = data_root.expanduser().resolve() if data_root else bundle_dir
    errors: list[str] = []
    warnings: list[str] = []
    try:
        manifest = load_hydrology_bundle_manifest(manifest_path)
    except HydrologyBundleError as exc:
        return HydrologyBundleAudit(
            bundle_id="",
            bundle_dir=bundle_dir,
            manifest_path=manifest_path,
            is_valid=False,
            is_complete=False,
            checked_utc=checked_utc or _now(),
            layers=(),
            errors=(str(exc),),
            warnings=(),
        )
    errors.extend(validate_hydrology_bundle_manifest(manifest))
    for gap in manifest.gaps:
        warnings.append(f"Gap: {gap.layer_id} ({gap.role}): {gap.reason}")
    layer_audits: list[HydrologyBundleLayerAudit] = []
    verified_layers = 0
    for layer in manifest.layers:
        relative = _resolve_member(base, layer.relative_path)
        issues: list[str] = []
        if relative is None:
            errors.append(
                f"Layer {layer.layer_id!r} path escapes the bundle: "
                f"{layer.relative_path!r}."
            )
            layer_audits.append(
                HydrologyBundleLayerAudit(
                    layer_id=layer.layer_id,
                    role=layer.role,
                    relative_path=layer.relative_path,
                    status=layer.status,
                    exists=False,
                    size_bytes=None,
                    expected_size_bytes=layer.size_bytes,
                    checksum_ok=None,
                    issues=("path escape",),
                )
            )
            continue
        exists = relative.is_file()
        size_bytes = relative.stat().st_size if exists else None
        checksum_ok: bool | None = None
        if layer.status == "materialized":
            if not exists:
                issues.append("missing file")
                errors.append(f"Materialized layer is missing: {layer.relative_path}")
            else:
                verified_layers += 1
                if layer.size_bytes is None or size_bytes != layer.size_bytes:
                    issues.append("size mismatch")
                    errors.append(
                        f"Layer {layer.layer_id!r} size mismatch: {size_bytes} != "
                        f"{layer.size_bytes}."
                    )
                if not layer.checksum_sha256:
                    issues.append("missing checksum")
                    errors.append(f"Layer {layer.layer_id!r} has no checksum.")
                else:
                    checksum_ok = (
                        _sha256_file(relative) == layer.checksum_sha256.lower()
                    )
                    if not checksum_ok:
                        issues.append("checksum mismatch")
                        errors.append(f"Layer {layer.layer_id!r} checksum mismatch.")
        elif exists:
            warnings.append(
                f"Layer {layer.layer_id!r} is {layer.status} but a local file exists."
            )
        layer_audits.append(
            HydrologyBundleLayerAudit(
                layer_id=layer.layer_id,
                role=layer.role,
                relative_path=layer.relative_path,
                status=layer.status,
                exists=exists,
                size_bytes=size_bytes,
                expected_size_bytes=layer.size_bytes,
                checksum_ok=checksum_ok,
                issues=tuple(issues),
            )
        )
    is_complete = (
        manifest.is_complete and verified_layers == manifest.layer_count and not errors
    )
    return HydrologyBundleAudit(
        bundle_id=manifest.bundle_id,
        bundle_dir=bundle_dir,
        manifest_path=manifest_path,
        is_valid=not errors,
        is_complete=is_complete,
        checked_utc=checked_utc or _now(),
        layers=tuple(layer_audits),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def _normalize_sources(
    sources: Mapping[str, Path] | None,
) -> dict[str, Path]:
    if sources is None:
        return {}
    normalized: dict[str, Path] = {}
    for layer_id, value in sources.items():
        if not isinstance(layer_id, str) or not layer_id.strip():
            raise HydrologyBundleError("Source layer IDs must be non-empty strings.")
        if not isinstance(value, Path):
            raise HydrologyBundleError(f"Source for layer {layer_id!r} must be a Path.")
        normalized[layer_id.strip()] = value.expanduser().resolve()
    return normalized


def _bundle_layer_path(layer: HydrologyLayerSpec) -> str:
    filename = _safe_filename(layer.path)
    return f"{HYDROLOGY_BUNDLE_LAYERS_DIR}/{layer.layer_id}/{filename}"


def _safe_filename(value: str) -> str:
    text = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(value).name).strip("._-")
    return text or "artifact"


def _normalize_bbox(
    value: Sequence[object],
) -> tuple[float, float, float, float]:
    if len(value) != 4:
        raise HydrologyBundleError(
            "AOI bbox must contain four values in minx,miny,maxx,maxy order."
        )
    try:
        coordinates = tuple(float(str(item)) for item in value)
    except (TypeError, ValueError) as exc:
        raise HydrologyBundleError("AOI bbox values must be numeric.") from exc
    if not all(math.isfinite(item) for item in coordinates):
        raise HydrologyBundleError("AOI bbox values must be finite.")
    minx, miny, maxx, maxy = coordinates
    if minx >= maxx or miny >= maxy:
        raise HydrologyBundleError("AOI bbox requires minx < maxx and miny < maxy.")
    return (minx, miny, maxx, maxy)


def _bundle_id(
    *,
    domain_id: str,
    domain_sha256: str,
    aoi_bbox: tuple[float, float, float, float],
    bundle_version: str,
    layers: Sequence[HydrologyBundleLayer],
) -> str:
    material = {
        "domain_id": domain_id,
        "domain_sha256": domain_sha256,
        "aoi_bbox_epsg3005": list(aoi_bbox),
        "bundle_version": bundle_version,
        "layers": [
            {
                "layer_id": layer.layer_id,
                "relative_path": layer.relative_path,
                "checksum_sha256": layer.checksum_sha256,
                "size_bytes": layer.size_bytes,
                "licence_id": layer.licence_id,
                "source_id": layer.source_id,
            }
            for layer in layers
        ],
    }
    digest = hashlib.sha256(_canonical_json_bytes(material)).hexdigest()
    return f"hydro-{digest[:16]}"


def _prepare_output(output: Path, *, overwrite: bool) -> None:
    if not output.exists():
        return
    if not output.is_dir():
        raise HydrologyBundleError(f"Output path is not a directory: {output}")
    if not any(output.iterdir()):
        return
    if not overwrite:
        raise HydrologyBundleError(
            f"Output directory is not empty: {output}. Use `overwrite=True` to "
            "replace a FEMIC hydrology bundle."
        )
    manifest_path = output / HYDROLOGY_BUNDLE_MANIFEST_NAME
    if not manifest_path.is_file():
        raise HydrologyBundleError(
            f"Refusing to overwrite non-bundle directory: {output}"
        )
    try:
        load_hydrology_bundle_manifest(manifest_path)
    except HydrologyBundleError as exc:
        raise HydrologyBundleError(
            f"Refusing to overwrite unreadable bundle: {output}"
        ) from exc


def _assert_replaceable_bundle(output: Path) -> None:
    manifest_path = output / HYDROLOGY_BUNDLE_MANIFEST_NAME
    if not manifest_path.is_file():
        raise HydrologyBundleError(
            f"Refusing to overwrite non-bundle directory: {output}"
        )
    load_hydrology_bundle_manifest(manifest_path)


def _resolve_manifest_path(path: Path) -> Path:
    resolved = path.expanduser().resolve()
    if resolved.is_dir():
        return resolved / HYDROLOGY_BUNDLE_MANIFEST_NAME
    return resolved


def _resolve_member(root: Path, relative_path: str) -> Path | None:
    candidate = (root / relative_path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    return candidate


def _layer_from_payload(item: object, *, index: int) -> HydrologyBundleLayer:
    payload = _mapping_from_object(item, context=f"bundle layer {index}")
    return HydrologyBundleLayer(
        layer_id=_required_str(payload, "layer_id", context=f"bundle layer {index}"),
        role=_required_str(payload, "role", context=f"bundle layer {index}"),
        source_id=_optional_str(payload.get("source_id")),
        relative_path=_required_str(
            payload,
            "relative_path",
            context=f"bundle layer {index}",
        ),
        format=_required_str(payload, "format", context=f"bundle layer {index}"),
        crs=_required_str(payload, "crs", context=f"bundle layer {index}"),
        licence_id=_required_str(
            payload,
            "licence_id",
            context=f"bundle layer {index}",
        ),
        status=_required_str(payload, "status", context=f"bundle layer {index}"),
        checksum_sha256=_optional_str(payload.get("checksum_sha256")),
        size_bytes=_optional_int(payload.get("size_bytes")),
        source_url=_optional_str(payload.get("source_url")),
        retrieval_utc=_optional_str(payload.get("retrieval_utc")),
        notes=_optional_str(payload.get("notes")) or "",
    )


def _gap_from_payload(item: object, *, index: int) -> HydrologyBundleGap:
    payload = _mapping_from_object(item, context=f"gap {index}")
    return HydrologyBundleGap(
        layer_id=_required_str(payload, "layer_id", context=f"gap {index}"),
        role=_required_str(payload, "role", context=f"gap {index}"),
        reason=_required_str(payload, "reason", context=f"gap {index}"),
    )


def _required_bbox(
    mapping: Mapping[str, object],
    *,
    context: str,
) -> tuple[float, float, float, float]:
    value = mapping.get("aoi_bbox_epsg3005")
    if not isinstance(value, list):
        raise HydrologyBundleError(
            f"{context} field 'aoi_bbox_epsg3005' must be a list."
        )
    return _normalize_bbox(value)


def _read_json_object(path: Path, *, context: str) -> dict[str, object]:
    try:
        payload: object = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise HydrologyBundleError(f"Unable to read {context}: {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise HydrologyBundleError(f"Invalid JSON in {context}: {path}: {exc}") from exc
    if not isinstance(payload, Mapping):
        raise HydrologyBundleError(f"{context} must be a JSON object: {path}")
    return {str(key): value for key, value in payload.items()}


def _mapping_from_object(value: object, *, context: str) -> dict[str, object]:
    if not isinstance(value, Mapping):
        raise HydrologyBundleError(f"{context} must be an object.")
    return {str(key): item for key, item in value.items()}


def _required_list(
    mapping: Mapping[str, object],
    key: str,
    *,
    context: str,
) -> list[object]:
    value = mapping.get(key)
    if not isinstance(value, list):
        raise HydrologyBundleError(f"{context} field {key!r} must be a list.")
    return value


def _required_str(
    mapping: Mapping[str, object],
    key: str,
    *,
    context: str,
) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        raise HydrologyBundleError(
            f"{context} field {key!r} must be a non-empty string."
        )
    return value.strip()


def _optional_str(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text or None


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


def _optional_str_list(value: object, *, context: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise HydrologyBundleError(f"{context} must be a list.")
    items: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise HydrologyBundleError(f"{context} entries must be strings.")
        text = item.strip()
        if text:
            items.append(text)
    return tuple(items)


def _optional_mapping(value: object, *, context: str) -> dict[str, object]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise HydrologyBundleError(f"{context} must be an object.")
    return {str(key): item for key, item in value.items()}


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_json(payload: object) -> str:
    return hashlib.sha256(_canonical_json_bytes(payload)).hexdigest()


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
