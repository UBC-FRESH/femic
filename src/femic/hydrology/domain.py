"""Hydrologic domain and receptor contracts for forest flood-risk work.

P114.1 defines the public spatial domain, layer roles, watersheds, receptors,
gauges, and provenance. It does not download data or run a hydrology model.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

HYDROLOGY_DOMAIN_SCHEMA_VERSION = "femic.hydrology.domain.v1"
HYDROLOGY_SOURCE_REGISTRY_VERSION = "femic.hydrology.sources.v1"
HYDROLOGY_LAYER_ROLES: tuple[str, ...] = (
    "watershed",
    "stream",
    "road",
    "dem",
    "land_cover",
    "soil",
    "climate",
    "gauge",
    "receptor",
    "hru",
)
HYDROLOGY_REQUIRED_LAYER_ROLES: tuple[str, ...] = (
    "watershed",
    "stream",
    "road",
    "dem",
)
HYDROLOGY_RECEPTOR_TYPES: tuple[str, ...] = (
    "community",
    "infrastructure",
    "channel_capacity",
    "ecological",
)
DEFAULT_HYDROLOGY_CRS = "EPSG:3005"
DEFAULT_HYDROLOGY_RESOLUTION_M = 25.0
SHA256_PATTERN = re.compile(r"^[0-9a-fA-F]{64}$")


class HydrologyDomainError(RuntimeError):
    """Raised when a hydrologic domain or source contract is invalid."""


@dataclass(frozen=True)
class HydrologySourceSpec:
    """One public source family available to a hydrology domain."""

    source_id: str
    title: str
    role: str
    catalogue_url: str | None
    service_url: str | None
    licence_id: str
    native_crs: str
    required_fields: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        """Return the source spec as a JSON-serializable mapping."""

        return {
            "source_id": self.source_id,
            "title": self.title,
            "role": self.role,
            "catalogue_url": self.catalogue_url,
            "service_url": self.service_url,
            "licence_id": self.licence_id,
            "native_crs": self.native_crs,
            "required_fields": list(self.required_fields),
            "notes": list(self.notes),
        }


HYDROLOGY_SOURCE_REGISTRY: tuple[HydrologySourceSpec, ...] = (
    HydrologySourceSpec(
        source_id="fwa_watersheds",
        title="Freshwater Atlas watersheds",
        role="watershed",
        catalogue_url=(
            "https://catalogue.data.gov.bc.ca/dataset?q="
            "WHSE_BASEMAPPING.FWA_WATERSHEDS_POLY"
        ),
        service_url=(
            "https://openmaps.gov.bc.ca/geo/pub/"
            "WHSE_BASEMAPPING.FWA_WATERSHEDS_POLY/ows"
        ),
        licence_id="OGL-BC",
        native_crs="EPSG:3005",
        required_fields=("WATERSHED_KEY", "WATERSHED_GROUP_CODE"),
    ),
    HydrologySourceSpec(
        source_id="fwa_streams",
        title="Freshwater Atlas stream networks",
        role="stream",
        catalogue_url=(
            "https://catalogue.data.gov.bc.ca/dataset?q="
            "WHSE_BASEMAPPING.FWA_STREAM_NETWORKS_SP"
        ),
        service_url=(
            "https://openmaps.gov.bc.ca/geo/pub/"
            "WHSE_BASEMAPPING.FWA_STREAM_NETWORKS_SP/ows"
        ),
        licence_id="OGL-BC",
        native_crs="EPSG:3005",
        required_fields=("LINEAR_FEATURE_ID", "STREAM_ORDER"),
    ),
    HydrologySourceSpec(
        source_id="road_atlas",
        title="Digital Road Atlas",
        role="road",
        catalogue_url=(
            "https://catalogue.data.gov.bc.ca/dataset?q="
            "WHSE_BASEMAPPING.DRA_DGTL_ROAD_ATLAS_MPAR_SP"
        ),
        service_url=(
            "https://openmaps.gov.bc.ca/geo/pub/"
            "WHSE_BASEMAPPING.DRA_DGTL_ROAD_ATLAS_MPAR_SP/ows"
        ),
        licence_id="OGL-BC",
        native_crs="EPSG:3005",
        required_fields=("ROAD_SECTION_ID", "ROAD_CLASS"),
    ),
    HydrologySourceSpec(
        source_id="ften_roads",
        title="Forest tenure road sections",
        role="road",
        catalogue_url=(
            "https://catalogue.data.gov.bc.ca/dataset?q="
            "WHSE_FOREST_TENURE.FTEN_ROAD_SECTION_LINES_SVW"
        ),
        service_url=(
            "https://openmaps.gov.bc.ca/geo/pub/"
            "WHSE_FOREST_TENURE.FTEN_ROAD_SECTION_LINES_SVW/ows"
        ),
        licence_id="OGL-BC",
        native_crs="EPSG:3005",
        required_fields=("ROAD_SECTION_ID", "ROAD_STATUS_CODE"),
        notes=("Preferred where forest-road tenure and status are required.",),
    ),
    HydrologySourceSpec(
        source_id="lidarbc_dem",
        title="LidarBC DEM/DSM products",
        role="dem",
        catalogue_url=(
            "https://catalogue.data.gov.bc.ca/dataset/lidarbc-open-lidar-data-portal"
        ),
        service_url="https://lidar.gov.bc.ca/pages/download-discovery",
        licence_id="OGL-BC",
        native_crs="EPSG:3005",
        notes=("Use the FEMIC P79 product bundle where available.",),
    ),
    HydrologySourceSpec(
        source_id="vri_land_cover",
        title="Vegetation Resources Inventory",
        role="land_cover",
        catalogue_url=(
            "https://catalogue.data.gov.bc.ca/dataset?q="
            "WHSE_FOREST_VEGETATION.VEG_COMP_LYR_R1_POLY"
        ),
        service_url=(
            "https://openmaps.gov.bc.ca/geo/pub/"
            "WHSE_FOREST_VEGETATION.VEG_COMP_LYR_R1_POLY/ows"
        ),
        licence_id="OGL-BC",
        native_crs="EPSG:3005",
        required_fields=("POLYGON_ID", "SPECIES_CD_1", "PROJ_HEIGHT_1"),
    ),
    HydrologySourceSpec(
        source_id="bc_soil_landscapes",
        title="BC soil landscapes",
        role="soil",
        catalogue_url="https://catalogue.data.gov.bc.ca/dataset?q=soil+landscape",
        service_url=None,
        licence_id="OGL-BC",
        native_crs="EPSG:3005",
        notes=("Resolve the exact reviewed soil layer through BCDC.",),
    ),
    HydrologySourceSpec(
        source_id="pcic_climate",
        title="Pacific Climate Impacts Consortium data",
        role="climate",
        catalogue_url="https://www.pacificclimate.org/data",
        service_url=None,
        licence_id="PCIC data terms",
        native_crs="various",
        notes=("Climate grids may be non-3005; record the native grid explicitly.",),
    ),
    HydrologySourceSpec(
        source_id="wsc_gauges",
        title="Water Survey of Canada hydrometric stations",
        role="gauge",
        catalogue_url="https://wateroffice.ec.gc.ca/",
        service_url=None,
        licence_id="OGL-Canada",
        native_crs="EPSG:4326",
        notes=("Gauge records require a reviewed link to a watershed and period.",),
    ),
    HydrologySourceSpec(
        source_id="receptor_inventory",
        title="Downstream receptor inventory",
        role="receptor",
        catalogue_url=None,
        service_url=None,
        licence_id="reviewed source required",
        native_crs="EPSG:3005",
        notes=(
            (
                "Communities, infrastructure, channel-capacity points, and "
                "ecological receptors must carry a reviewed source and licence."
            ),
        ),
    ),
)


@dataclass(frozen=True)
class HydrologyLayerSpec:
    """One spatial or tabular source layer in a hydrology domain."""

    layer_id: str
    role: str
    path: str
    format: str
    crs: str
    geometry_type: str | None = None
    source_id: str | None = None
    required_fields: tuple[str, ...] = ()
    description: str = ""
    licence_id: str = "OGL-BC"
    checksum_sha256: str | None = None
    size_bytes: int | None = None
    resolution_m: float | None = None

    def to_dict(self) -> dict[str, object]:
        """Return the layer spec as a JSON-serializable mapping."""

        return {
            "layer_id": self.layer_id,
            "role": self.role,
            "path": self.path,
            "format": self.format,
            "crs": self.crs,
            "geometry_type": self.geometry_type,
            "source_id": self.source_id,
            "required_fields": list(self.required_fields),
            "description": self.description,
            "licence_id": self.licence_id,
            "checksum_sha256": self.checksum_sha256,
            "size_bytes": self.size_bytes,
            "resolution_m": self.resolution_m,
        }


@dataclass(frozen=True)
class HydrologyWatershed:
    """One watershed or nested sub-watershed in the domain."""

    watershed_id: str
    name: str
    area_km2: float
    layer_id: str
    feature_id: str | None = None

    def to_dict(self) -> dict[str, object]:
        """Return the watershed as a JSON-serializable mapping."""

        return {
            "watershed_id": self.watershed_id,
            "name": self.name,
            "area_km2": self.area_km2,
            "layer_id": self.layer_id,
            "feature_id": self.feature_id,
        }


@dataclass(frozen=True)
class HydrologyReceptor:
    """One downstream flood-risk receptor."""

    receptor_id: str
    name: str
    receptor_type: str
    watershed_id: str
    layer_id: str
    feature_id: str | None = None
    capacity_m3s: float | None = None
    damage_curve_id: str | None = None
    notes: str = ""

    def to_dict(self) -> dict[str, object]:
        """Return the receptor as a JSON-serializable mapping."""

        return {
            "receptor_id": self.receptor_id,
            "name": self.name,
            "receptor_type": self.receptor_type,
            "watershed_id": self.watershed_id,
            "layer_id": self.layer_id,
            "feature_id": self.feature_id,
            "capacity_m3s": self.capacity_m3s,
            "damage_curve_id": self.damage_curve_id,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class HydrologyGauge:
    """One hydrometric gauge linked to a watershed."""

    gauge_id: str
    station_name: str
    watershed_id: str
    layer_id: str | None = None
    drainage_area_km2: float | None = None
    period_start: str | None = None
    period_end: str | None = None
    record_url: str | None = None

    def to_dict(self) -> dict[str, object]:
        """Return the gauge as a JSON-serializable mapping."""

        return {
            "gauge_id": self.gauge_id,
            "station_name": self.station_name,
            "watershed_id": self.watershed_id,
            "layer_id": self.layer_id,
            "drainage_area_km2": self.drainage_area_km2,
            "period_start": self.period_start,
            "period_end": self.period_end,
            "record_url": self.record_url,
        }


@dataclass(frozen=True)
class HydrologyDomainManifest:
    """A versioned public hydrology domain and receptor contract."""

    domain_id: str
    name: str
    created_utc: str
    crs: str
    resolution_m: float
    layers: tuple[HydrologyLayerSpec, ...]
    watersheds: tuple[HydrologyWatershed, ...]
    receptors: tuple[HydrologyReceptor, ...]
    gauges: tuple[HydrologyGauge, ...]
    caveats: tuple[str, ...] = ()
    provenance: dict[str, object] = field(default_factory=dict)
    schema_version: str = HYDROLOGY_DOMAIN_SCHEMA_VERSION

    def to_dict(self) -> dict[str, object]:
        """Return the domain manifest as a JSON-serializable mapping."""

        return {
            "schema_version": self.schema_version,
            "domain_id": self.domain_id,
            "name": self.name,
            "created_utc": self.created_utc,
            "crs": self.crs,
            "resolution_m": self.resolution_m,
            "layers": [layer.to_dict() for layer in self.layers],
            "watersheds": [watershed.to_dict() for watershed in self.watersheds],
            "receptors": [receptor.to_dict() for receptor in self.receptors],
            "gauges": [gauge.to_dict() for gauge in self.gauges],
            "caveats": list(self.caveats),
            "provenance": self.provenance,
        }


@dataclass(frozen=True)
class HydrologyDomainValidation:
    """Structural validation outcome for a hydrology domain."""

    is_valid: bool
    errors: tuple[str, ...]
    warnings: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        """Return the validation as a JSON-serializable mapping."""

        return {
            "is_valid": self.is_valid,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class HydrologyLayerAudit:
    """Local file audit for one domain layer."""

    layer_id: str
    role: str
    path: str
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
            "path": self.path,
            "exists": self.exists,
            "size_bytes": self.size_bytes,
            "expected_size_bytes": self.expected_size_bytes,
            "checksum_ok": self.checksum_ok,
            "issues": list(self.issues),
        }


@dataclass(frozen=True)
class HydrologyDomainAudit:
    """Validation and local-file audit for a hydrology domain."""

    domain_id: str
    manifest_path: Path | None
    is_valid: bool
    checked_utc: str
    layers: tuple[HydrologyLayerAudit, ...]
    errors: tuple[str, ...]
    warnings: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        """Return the audit as a JSON-serializable mapping."""

        return {
            "domain_id": self.domain_id,
            "manifest_path": str(self.manifest_path) if self.manifest_path else None,
            "is_valid": self.is_valid,
            "checked_utc": self.checked_utc,
            "layers": [layer.to_dict() for layer in self.layers],
            "errors": list(self.errors),
            "warnings": list(self.warnings),
        }


def hydrology_source_registry() -> tuple[HydrologySourceSpec, ...]:
    """Return the default public hydrology source registry."""

    return HYDROLOGY_SOURCE_REGISTRY


def find_hydrology_source(source_id: str) -> HydrologySourceSpec | None:
    """Resolve one source ID from the default registry."""

    return next(
        (
            source
            for source in HYDROLOGY_SOURCE_REGISTRY
            if source.source_id == source_id
        ),
        None,
    )


def build_hydrology_domain(
    *,
    domain_id: str,
    name: str,
    layers: Sequence[HydrologyLayerSpec],
    watersheds: Sequence[HydrologyWatershed],
    receptors: Sequence[HydrologyReceptor],
    gauges: Sequence[HydrologyGauge],
    crs: str = DEFAULT_HYDROLOGY_CRS,
    resolution_m: float = DEFAULT_HYDROLOGY_RESOLUTION_M,
    caveats: Sequence[str] = (),
    provenance: Mapping[str, object] | None = None,
    created_utc: str | None = None,
) -> HydrologyDomainManifest:
    """Build and validate one hydrology domain manifest.

    Raises
    ------
    HydrologyDomainError
        If the domain is structurally invalid.
    """

    manifest = HydrologyDomainManifest(
        domain_id=domain_id,
        name=name,
        created_utc=created_utc or _now(),
        crs=crs,
        resolution_m=resolution_m,
        layers=tuple(layers),
        watersheds=tuple(watersheds),
        receptors=tuple(receptors),
        gauges=tuple(gauges),
        caveats=tuple(caveats),
        provenance={
            "producer": "femic.hydrology",
            "source_registry_version": HYDROLOGY_SOURCE_REGISTRY_VERSION,
            **dict(provenance or {}),
        },
    )
    validation = validate_hydrology_domain(manifest)
    if not validation.is_valid:
        raise HydrologyDomainError("; ".join(validation.errors))
    return manifest


def validate_hydrology_domain(
    manifest: HydrologyDomainManifest,
) -> HydrologyDomainValidation:
    """Validate structural, identification, and cross-reference rules."""

    errors: list[str] = []
    warnings: list[str] = []
    if manifest.schema_version != HYDROLOGY_DOMAIN_SCHEMA_VERSION:
        errors.append(
            f"Unsupported hydrology domain schema {manifest.schema_version!r}; "
            f"expected {HYDROLOGY_DOMAIN_SCHEMA_VERSION!r}."
        )
    if not manifest.domain_id.strip():
        errors.append("Domain ID must be non-empty.")
    if not manifest.name.strip():
        errors.append("Domain name must be non-empty.")
    if not manifest.created_utc.strip():
        errors.append("Domain created_utc must be non-empty.")
    if not manifest.crs.strip():
        errors.append("Domain CRS must be non-empty.")
    if manifest.resolution_m <= 0 or not math.isfinite(manifest.resolution_m):
        errors.append("Domain resolution_m must be positive and finite.")
    if not manifest.layers:
        errors.append("Domain must contain at least one layer.")
    layer_ids: set[str] = set()
    roles: set[str] = set()
    for layer in manifest.layers:
        if not layer.layer_id.strip():
            errors.append("Layer ID must be non-empty.")
        if layer.layer_id in layer_ids:
            errors.append(f"Duplicate layer ID {layer.layer_id!r}.")
        layer_ids.add(layer.layer_id)
        if layer.role not in HYDROLOGY_LAYER_ROLES:
            errors.append(
                f"Layer {layer.layer_id!r} has unsupported role {layer.role!r}."
            )
        roles.add(layer.role)
        if not layer.path.strip():
            errors.append(f"Layer {layer.layer_id!r} has no path.")
        if not layer.format.strip():
            errors.append(f"Layer {layer.layer_id!r} has no format.")
        if not layer.licence_id.strip():
            errors.append(f"Layer {layer.layer_id!r} has no licence.")
        if not layer.crs.strip():
            errors.append(f"Layer {layer.layer_id!r} has no CRS.")
        elif layer.crs != manifest.crs:
            errors.append(
                f"Layer {layer.layer_id!r} CRS {layer.crs!r} does not match "
                f"domain CRS {manifest.crs!r}."
            )
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
            errors.append(f"Layer {layer.layer_id!r} has an invalid SHA-256 checksum.")
        if layer.size_bytes is not None and layer.size_bytes < 0:
            errors.append(f"Layer {layer.layer_id!r} has a negative size.")
        if layer.resolution_m is not None and layer.resolution_m <= 0:
            errors.append(f"Layer {layer.layer_id!r} has a non-positive resolution.")
    missing_roles = [
        role for role in HYDROLOGY_REQUIRED_LAYER_ROLES if role not in roles
    ]
    if missing_roles:
        errors.append(
            "Domain is missing required layer roles: " + ", ".join(missing_roles) + "."
        )
    watershed_ids: set[str] = set()
    if not manifest.watersheds:
        errors.append("Domain must contain at least one watershed.")
    for watershed in manifest.watersheds:
        if not watershed.watershed_id.strip():
            errors.append("Watershed ID must be non-empty.")
        if not watershed.name.strip():
            errors.append(f"Watershed {watershed.watershed_id!r} has no name.")
        if watershed.watershed_id in watershed_ids:
            errors.append(f"Duplicate watershed ID {watershed.watershed_id!r}.")
        watershed_ids.add(watershed.watershed_id)
        if watershed.area_km2 <= 0 or not math.isfinite(watershed.area_km2):
            errors.append(
                f"Watershed {watershed.watershed_id!r} must have positive area."
            )
        if watershed.layer_id not in layer_ids:
            errors.append(
                f"Watershed {watershed.watershed_id!r} references unknown layer "
                f"{watershed.layer_id!r}."
            )
    receptor_ids: set[str] = set()
    if not manifest.receptors:
        errors.append("Domain must contain at least one flood-risk receptor.")
    for receptor in manifest.receptors:
        if not receptor.receptor_id.strip():
            errors.append("Receptor ID must be non-empty.")
        if not receptor.name.strip():
            errors.append(f"Receptor {receptor.receptor_id!r} has no name.")
        if receptor.receptor_id in receptor_ids:
            errors.append(f"Duplicate receptor ID {receptor.receptor_id!r}.")
        receptor_ids.add(receptor.receptor_id)
        if receptor.receptor_type not in HYDROLOGY_RECEPTOR_TYPES:
            errors.append(
                f"Receptor {receptor.receptor_id!r} has unsupported type "
                f"{receptor.receptor_type!r}."
            )
        if receptor.watershed_id not in watershed_ids:
            errors.append(
                f"Receptor {receptor.receptor_id!r} references unknown watershed "
                f"{receptor.watershed_id!r}."
            )
        if receptor.layer_id not in layer_ids:
            errors.append(
                f"Receptor {receptor.receptor_id!r} references unknown layer "
                f"{receptor.layer_id!r}."
            )
        if receptor.capacity_m3s is not None and receptor.capacity_m3s <= 0:
            errors.append(
                f"Receptor {receptor.receptor_id!r} must have positive capacity."
            )
    gauge_ids: set[str] = set()
    if not manifest.gauges:
        warnings.append(
            "Domain has no linked hydrometric gauge; calibration will be weaker."
        )
    for gauge in manifest.gauges:
        if not gauge.gauge_id.strip():
            errors.append("Gauge ID must be non-empty.")
        if not gauge.station_name.strip():
            errors.append(f"Gauge {gauge.gauge_id!r} has no station name.")
        if gauge.gauge_id in gauge_ids:
            errors.append(f"Duplicate gauge ID {gauge.gauge_id!r}.")
        gauge_ids.add(gauge.gauge_id)
        if gauge.watershed_id not in watershed_ids:
            errors.append(
                f"Gauge {gauge.gauge_id!r} references unknown watershed "
                f"{gauge.watershed_id!r}."
            )
        if gauge.layer_id is not None and gauge.layer_id not in layer_ids:
            errors.append(
                f"Gauge {gauge.gauge_id!r} references unknown layer {gauge.layer_id!r}."
            )
        if gauge.drainage_area_km2 is not None and gauge.drainage_area_km2 <= 0:
            errors.append(f"Gauge {gauge.gauge_id!r} must have positive drainage area.")
        if (
            gauge.period_start is not None
            and gauge.period_end is not None
            and gauge.period_start > gauge.period_end
        ):
            errors.append(f"Gauge {gauge.gauge_id!r} period start is after its end.")
    return HydrologyDomainValidation(
        is_valid=not errors,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def write_hydrology_domain_manifest(
    manifest: HydrologyDomainManifest,
    path: Path,
) -> Path:
    """Write a hydrology domain manifest as pretty-printed JSON."""

    resolved = path.expanduser().resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(
        json.dumps(manifest.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return resolved


def load_hydrology_domain_manifest(path: Path) -> HydrologyDomainManifest:
    """Load a hydrology domain manifest from JSON."""

    resolved = path.expanduser().resolve()
    payload = _read_json_object(resolved, context="hydrology domain manifest")
    schema_version = _required_str(
        payload,
        "schema_version",
        context="hydrology domain manifest",
    )
    if schema_version != HYDROLOGY_DOMAIN_SCHEMA_VERSION:
        raise HydrologyDomainError(
            f"Unsupported hydrology domain schema {schema_version!r}; expected "
            f"{HYDROLOGY_DOMAIN_SCHEMA_VERSION!r}."
        )
    layers = tuple(
        _layer_from_payload(item, index=index)
        for index, item in enumerate(
            _required_list(payload, "layers", context="hydrology domain"),
            start=1,
        )
    )
    watersheds = tuple(
        _watershed_from_payload(item, index=index)
        for index, item in enumerate(
            _required_list(payload, "watersheds", context="hydrology domain"),
            start=1,
        )
    )
    receptors = tuple(
        _receptor_from_payload(item, index=index)
        for index, item in enumerate(
            _required_list(payload, "receptors", context="hydrology domain"),
            start=1,
        )
    )
    gauges = tuple(
        _gauge_from_payload(item, index=index)
        for index, item in enumerate(
            _required_list(payload, "gauges", context="hydrology domain"),
            start=1,
        )
    )
    return HydrologyDomainManifest(
        domain_id=_required_str(payload, "domain_id", context="hydrology domain"),
        name=_required_str(payload, "name", context="hydrology domain"),
        created_utc=_optional_str(payload.get("created_utc")) or "",
        crs=_required_str(payload, "crs", context="hydrology domain"),
        resolution_m=_required_float(
            payload,
            "resolution_m",
            context="hydrology domain",
        ),
        layers=layers,
        watersheds=watersheds,
        receptors=receptors,
        gauges=gauges,
        caveats=_optional_str_list(payload.get("caveats"), context="caveats"),
        provenance=_optional_mapping(payload.get("provenance"), context="provenance"),
        schema_version=schema_version,
    )


def audit_hydrology_domain(
    manifest: HydrologyDomainManifest | Path,
    *,
    data_root: Path | None = None,
    checked_utc: str | None = None,
) -> HydrologyDomainAudit:
    """Validate a domain and audit its local layer files.

    Relative layer paths are resolved against ``data_root`` when provided,
    otherwise against the manifest directory (or the current directory for an
    in-memory manifest).
    """

    manifest_path: Path | None
    if isinstance(manifest, Path):
        manifest_path = manifest.expanduser().resolve()
        domain = load_hydrology_domain_manifest(manifest_path)
        base = data_root.expanduser().resolve() if data_root else manifest_path.parent
    else:
        domain = manifest
        manifest_path = None
        base = data_root.expanduser().resolve() if data_root else Path.cwd()
    validation = validate_hydrology_domain(domain)
    errors = list(validation.errors)
    warnings = list(validation.warnings)
    layer_audits: list[HydrologyLayerAudit] = []
    for layer in domain.layers:
        path = _resolve_layer_path(layer.path, base)
        issues: list[str] = []
        exists = path.is_file()
        size_bytes: int | None = None
        checksum_ok: bool | None = None
        if not exists:
            issues.append("missing file")
            errors.append(f"Layer {layer.layer_id!r} file is missing: {path}")
        else:
            size_bytes = path.stat().st_size
            if layer.size_bytes is not None and size_bytes != layer.size_bytes:
                issues.append("size mismatch")
                errors.append(
                    f"Layer {layer.layer_id!r} size mismatch: {size_bytes} != "
                    f"{layer.size_bytes}."
                )
            if layer.checksum_sha256 is not None:
                checksum_ok = _sha256_file(path) == layer.checksum_sha256.lower()
                if not checksum_ok:
                    issues.append("checksum mismatch")
                    errors.append(f"Layer {layer.layer_id!r} checksum mismatch.")
        layer_audits.append(
            HydrologyLayerAudit(
                layer_id=layer.layer_id,
                role=layer.role,
                path=str(path),
                exists=exists,
                size_bytes=size_bytes,
                expected_size_bytes=layer.size_bytes,
                checksum_ok=checksum_ok,
                issues=tuple(issues),
            )
        )
    return HydrologyDomainAudit(
        domain_id=domain.domain_id,
        manifest_path=manifest_path,
        is_valid=not errors,
        checked_utc=checked_utc or _now(),
        layers=tuple(layer_audits),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def _layer_from_payload(item: object, *, index: int) -> HydrologyLayerSpec:
    payload = _mapping_from_object(item, context=f"layer {index}")
    return HydrologyLayerSpec(
        layer_id=_required_str(payload, "layer_id", context=f"layer {index}"),
        role=_required_str(payload, "role", context=f"layer {index}"),
        path=_required_str(payload, "path", context=f"layer {index}"),
        format=_required_str(payload, "format", context=f"layer {index}"),
        crs=_required_str(payload, "crs", context=f"layer {index}"),
        geometry_type=_optional_str(payload.get("geometry_type")),
        source_id=_optional_str(payload.get("source_id")),
        required_fields=_optional_str_list(
            payload.get("required_fields"),
            context=f"layer {index} required_fields",
        ),
        description=_optional_str(payload.get("description")) or "",
        licence_id=_optional_str(payload.get("licence_id")) or "",
        checksum_sha256=_optional_str(payload.get("checksum_sha256")),
        size_bytes=_optional_int(payload.get("size_bytes")),
        resolution_m=_optional_float(payload.get("resolution_m")),
    )


def _watershed_from_payload(item: object, *, index: int) -> HydrologyWatershed:
    payload = _mapping_from_object(item, context=f"watershed {index}")
    return HydrologyWatershed(
        watershed_id=_required_str(
            payload,
            "watershed_id",
            context=f"watershed {index}",
        ),
        name=_required_str(payload, "name", context=f"watershed {index}"),
        area_km2=_required_float(payload, "area_km2", context=f"watershed {index}"),
        layer_id=_required_str(payload, "layer_id", context=f"watershed {index}"),
        feature_id=_optional_str(payload.get("feature_id")),
    )


def _receptor_from_payload(item: object, *, index: int) -> HydrologyReceptor:
    payload = _mapping_from_object(item, context=f"receptor {index}")
    return HydrologyReceptor(
        receptor_id=_required_str(
            payload,
            "receptor_id",
            context=f"receptor {index}",
        ),
        name=_required_str(payload, "name", context=f"receptor {index}"),
        receptor_type=_required_str(
            payload,
            "receptor_type",
            context=f"receptor {index}",
        ),
        watershed_id=_required_str(
            payload,
            "watershed_id",
            context=f"receptor {index}",
        ),
        layer_id=_required_str(payload, "layer_id", context=f"receptor {index}"),
        feature_id=_optional_str(payload.get("feature_id")),
        capacity_m3s=_optional_float(payload.get("capacity_m3s")),
        damage_curve_id=_optional_str(payload.get("damage_curve_id")),
        notes=_optional_str(payload.get("notes")) or "",
    )


def _gauge_from_payload(item: object, *, index: int) -> HydrologyGauge:
    payload = _mapping_from_object(item, context=f"gauge {index}")
    return HydrologyGauge(
        gauge_id=_required_str(payload, "gauge_id", context=f"gauge {index}"),
        station_name=_required_str(
            payload,
            "station_name",
            context=f"gauge {index}",
        ),
        watershed_id=_required_str(
            payload,
            "watershed_id",
            context=f"gauge {index}",
        ),
        layer_id=_optional_str(payload.get("layer_id")),
        drainage_area_km2=_optional_float(payload.get("drainage_area_km2")),
        period_start=_optional_str(payload.get("period_start")),
        period_end=_optional_str(payload.get("period_end")),
        record_url=_optional_str(payload.get("record_url")),
    )


def _resolve_layer_path(value: str, base: Path) -> Path:
    candidate = Path(value).expanduser()
    if candidate.is_absolute():
        return candidate.resolve()
    return (base / candidate).resolve()


def _read_json_object(path: Path, *, context: str) -> dict[str, object]:
    try:
        payload: object = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise HydrologyDomainError(f"Unable to read {context}: {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise HydrologyDomainError(f"Invalid JSON in {context}: {path}: {exc}") from exc
    if not isinstance(payload, Mapping):
        raise HydrologyDomainError(f"{context} must be a JSON object: {path}")
    return {str(key): value for key, value in payload.items()}


def _mapping_from_object(value: object, *, context: str) -> dict[str, object]:
    if not isinstance(value, Mapping):
        raise HydrologyDomainError(f"{context} must be an object.")
    return {str(key): item for key, item in value.items()}


def _required_list(
    mapping: Mapping[str, object],
    key: str,
    *,
    context: str,
) -> list[object]:
    value = mapping.get(key)
    if not isinstance(value, list):
        raise HydrologyDomainError(f"{context} field {key!r} must be a list.")
    return value


def _required_str(
    mapping: Mapping[str, object],
    key: str,
    *,
    context: str,
) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        raise HydrologyDomainError(
            f"{context} field {key!r} must be a non-empty string."
        )
    return value.strip()


def _required_float(
    mapping: Mapping[str, object],
    key: str,
    *,
    context: str,
) -> float:
    value = mapping.get(key)
    parsed = _optional_float(value)
    if parsed is None:
        raise HydrologyDomainError(f"{context} field {key!r} must be numeric.")
    return parsed


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


def _optional_float(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        parsed = float(value)
    elif isinstance(value, str):
        try:
            parsed = float(value)
        except ValueError:
            return None
    else:
        return None
    return parsed if math.isfinite(parsed) else None


def _optional_str_list(value: object, *, context: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise HydrologyDomainError(f"{context} must be a list.")
    items: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise HydrologyDomainError(f"{context} entries must be strings.")
        text = item.strip()
        if text:
            items.append(text)
    return tuple(items)


def _optional_mapping(value: object, *, context: str) -> dict[str, object]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise HydrologyDomainError(f"{context} must be an object.")
    return {str(key): item for key, item in value.items()}


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _now() -> str:
    return datetime.now(UTC).isoformat()
