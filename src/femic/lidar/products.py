"""Versioned LidarBC product bundles and consumer manifest contracts.

The P79.8 slice packages already-compiled products; it does not compile
terrain or canopy rasters. A bundle is reproducible from a P79.1 selection
manifest, a product plan, and the product bytes.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import shutil
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from femic import __version__
from femic.lidar.catalog import (
    LIDAR_SELECTION_SCHEMA_VERSION,
    LIDARBC_LICENCE_ID,
    LIDARBC_NATIVE_CRS,
    LIDARBC_SOURCE_ID,
    LidarCatalogError,
    normalize_bbox_epsg3005,
)

LIDAR_PRODUCT_SCHEMA_VERSION = "femic.lidar.product.v1"
LIDAR_PRODUCT_PLAN_SCHEMA_VERSION = "femic.lidar.product_plan.v1"
LIDAR_PRODUCT_BUNDLE_LAYOUT_VERSION = "femic.lidar.bundle.v1"
LIDAR_PRODUCT_MANIFEST_NAME = "manifest.json"
LIDAR_PRODUCTS_DIR = "products"
LIDAR_SELECTION_PROVENANCE_PATH = "provenance/selection.json"
LIDAR_PRODUCT_KINDS: tuple[str, ...] = (
    "point_cloud",
    "dem",
    "dsm",
    "chm",
    "canopy",
    "individual_tree",
    "slope",
)
LIDAR_RASTER_PRODUCT_KINDS = frozenset({"dem", "dsm", "chm", "canopy", "slope"})
LIDAR_DERIVED_PRODUCT_KINDS = frozenset({"chm", "canopy", "slope"})
LIDAR_CONSUMER_PHASES: dict[str, str] = {"ws4": "P43", "fhops": "P13"}


class LidarProductError(RuntimeError):
    """Raised when a product plan, selection, or bundle contract is invalid."""


@dataclass(frozen=True)
class LidarProductSpec:
    """One planned product artifact before checksumming and packaging."""

    product: str
    source_path: Path
    media_type: str
    crs: str
    resolution_m: float | None
    vertical_datum: str
    retrieved_utc: str
    source_tile_ids: tuple[str, ...]
    source_layer_ids: tuple[int, ...]
    derived: bool = False
    lineage: tuple[str, ...] = ()


@dataclass(frozen=True)
class LidarProductPlan:
    """A reproducible product-build plan."""

    bundle_version: str
    processing_version: str
    products: tuple[LidarProductSpec, ...]
    processing_lineage: tuple[str, ...] = ()
    parameters: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        """Return the plan as a JSON-serializable mapping."""

        return {
            "schema_version": LIDAR_PRODUCT_PLAN_SCHEMA_VERSION,
            "bundle_version": self.bundle_version,
            "processing_version": self.processing_version,
            "processing_lineage": list(self.processing_lineage),
            "parameters": self.parameters,
            "products": [
                {
                    "product": spec.product,
                    "path": str(spec.source_path),
                    "media_type": spec.media_type,
                    "crs": spec.crs,
                    "resolution_m": spec.resolution_m,
                    "vertical_datum": spec.vertical_datum,
                    "retrieved_utc": spec.retrieved_utc,
                    "source_tile_ids": list(spec.source_tile_ids),
                    "source_layer_ids": list(spec.source_layer_ids),
                    "derived": spec.derived,
                    "lineage": list(spec.lineage),
                }
                for spec in self.products
            ],
        }


@dataclass(frozen=True)
class LidarProductRecord:
    """One packaged product artifact recorded in the bundle manifest."""

    product_id: str
    product: str
    relative_path: str
    media_type: str
    size_bytes: int
    sha256: str
    crs: str
    resolution_m: float | None
    vertical_datum: str
    retrieved_utc: str
    source_tile_ids: tuple[str, ...]
    source_layer_ids: tuple[int, ...]
    licence_id: str
    derived: bool
    lineage: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        """Return the product record as a JSON-serializable mapping."""

        return {
            "product_id": self.product_id,
            "product": self.product,
            "relative_path": self.relative_path,
            "media_type": self.media_type,
            "size_bytes": self.size_bytes,
            "sha256": self.sha256,
            "crs": self.crs,
            "resolution_m": self.resolution_m,
            "vertical_datum": self.vertical_datum,
            "retrieved_utc": self.retrieved_utc,
            "source_tile_ids": list(self.source_tile_ids),
            "source_layer_ids": list(self.source_layer_ids),
            "licence_id": self.licence_id,
            "derived": self.derived,
            "lineage": list(self.lineage),
        }


@dataclass(frozen=True)
class LidarProductManifest:
    """The versioned, consumer-facing product manifest."""

    bundle_id: str
    bundle_name: str
    bundle_version: str
    created_utc: str
    producer: dict[str, object]
    source: dict[str, object]
    selection: dict[str, object]
    processing: dict[str, object]
    products: tuple[LidarProductRecord, ...]
    consumer_contract: dict[str, object]
    schema_version: str = LIDAR_PRODUCT_SCHEMA_VERSION
    layout_version: str = LIDAR_PRODUCT_BUNDLE_LAYOUT_VERSION

    @property
    def product_count(self) -> int:
        """Return the number of packaged product artifacts."""

        return len(self.products)

    @property
    def total_bytes(self) -> int:
        """Return the total packaged product size in bytes."""

        return sum(product.size_bytes for product in self.products)

    def to_dict(self) -> dict[str, object]:
        """Return the manifest as a JSON-serializable mapping."""

        return {
            "schema_version": self.schema_version,
            "layout_version": self.layout_version,
            "bundle_id": self.bundle_id,
            "bundle_name": self.bundle_name,
            "bundle_version": self.bundle_version,
            "created_utc": self.created_utc,
            "producer": self.producer,
            "source": self.source,
            "selection": self.selection,
            "processing": self.processing,
            "summary": {
                "product_count": self.product_count,
                "total_bytes": self.total_bytes,
            },
            "products": [product.to_dict() for product in self.products],
            "consumer_contract": self.consumer_contract,
        }


@dataclass(frozen=True)
class LidarProductBuildResult:
    """Paths and manifest returned by a successful bundle build."""

    bundle_dir: Path
    manifest_path: Path
    selection_path: Path
    manifest: LidarProductManifest

    def to_dict(self) -> dict[str, object]:
        """Return the build result as a JSON-serializable mapping."""

        return {
            "bundle_dir": str(self.bundle_dir),
            "manifest_path": str(self.manifest_path),
            "selection_path": str(self.selection_path),
            "manifest": self.manifest.to_dict(),
        }


@dataclass(frozen=True)
class LidarProductValidation:
    """Validation outcome for one product bundle."""

    bundle_dir: Path
    manifest_path: Path
    is_valid: bool
    checked_utc: str
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    bundle_id: str | None
    bundle_version: str | None
    product_count: int
    total_bytes: int

    def to_dict(self) -> dict[str, object]:
        """Return the validation report as a JSON-serializable mapping."""

        return {
            "bundle_dir": str(self.bundle_dir),
            "manifest_path": str(self.manifest_path),
            "is_valid": self.is_valid,
            "checked_utc": self.checked_utc,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
            "bundle_id": self.bundle_id,
            "bundle_version": self.bundle_version,
            "product_count": self.product_count,
            "total_bytes": self.total_bytes,
        }


@dataclass(frozen=True)
class _SelectionFacts:
    schema_version: str
    generated_utc: str
    source_id: str
    licence_id: str
    native_crs: str
    aoi_bbox_epsg3005: tuple[float, float, float, float]
    products: tuple[str, ...]
    tile_ids: tuple[str, ...]
    source_layer_ids: tuple[int, ...]
    sha256: str


def load_lidar_product_plan(path: Path) -> LidarProductPlan:
    """Load and validate a product plan, resolving product paths beside it.

    Raises
    ------
    LidarProductError
        If the plan schema, fields, or product entries are invalid.
    """

    resolved = path.expanduser().resolve()
    payload = _read_json_object(resolved, context="LiDAR product plan")
    schema_version = _required_str(payload, "schema_version", context="product plan")
    if schema_version != LIDAR_PRODUCT_PLAN_SCHEMA_VERSION:
        raise LidarProductError(
            f"Unsupported LiDAR product plan schema {schema_version!r}; expected "
            f"{LIDAR_PRODUCT_PLAN_SCHEMA_VERSION!r}."
        )
    bundle_version = _required_str(payload, "bundle_version", context="product plan")
    processing_version = _required_str(
        payload,
        "processing_version",
        context="product plan",
    )
    lineage = _optional_str_list(payload.get("processing_lineage"), context="lineage")
    parameters = _optional_mapping(payload.get("parameters"), context="parameters")
    raw_products = _required_list(payload, "products", context="product plan")
    plan_root = resolved.parent
    specs = tuple(
        _product_spec_from_payload(item, plan_root=plan_root, index=index)
        for index, item in enumerate(raw_products, start=1)
    )
    return LidarProductPlan(
        bundle_version=bundle_version,
        processing_version=processing_version,
        products=specs,
        processing_lineage=lineage,
        parameters=parameters,
    )


def build_lidar_product_bundle(
    *,
    selection_manifest_path: Path,
    product_plan_path: Path,
    output_dir: Path,
    overwrite: bool = False,
    generated_utc: str | None = None,
) -> LidarProductBuildResult:
    """Build a reproducible product bundle from a selection and product plan.

    The bundle layout is::

        manifest.json
        provenance/selection.json
        products/<product>__<index>__<filename>

    The selection digest and every product checksum are recorded in the
    manifest. Rebuilding with the same inputs and ``generated_utc`` produces
    the same manifest bytes.

    Raises
    ------
    LidarProductError
        If the selection, plan, output directory, or safety checks fail.
    OSError
        If a product or bundle file cannot be copied or written.
    """

    selection_path = selection_manifest_path.expanduser().resolve()
    selection_payload = _read_json_object(selection_path, context="LiDAR selection")
    selection_facts = _selection_facts(selection_payload)
    plan = load_lidar_product_plan(product_plan_path)
    _validate_plan(plan, selection_facts)

    output = output_dir.expanduser().resolve()
    _prepare_output(output, overwrite=overwrite)
    output.parent.mkdir(parents=True, exist_ok=True)
    temp_dir = Path(tempfile.mkdtemp(prefix=f".{output.name}.", dir=output.parent))
    try:
        products_dir = temp_dir / LIDAR_PRODUCTS_DIR
        provenance_dir = temp_dir / "provenance"
        products_dir.mkdir(parents=True)
        provenance_dir.mkdir(parents=True)
        (provenance_dir / "selection.json").write_text(
            _pretty_json(selection_payload),
            encoding="utf-8",
        )

        records: list[LidarProductRecord] = []
        for index, spec in enumerate(plan.products, start=1):
            relative_path = _artifact_relative_path(
                spec.product,
                spec.source_path,
                index,
            )
            destination = temp_dir / relative_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(spec.source_path, destination)
            digest = _sha256_file(destination)
            records.append(
                LidarProductRecord(
                    product_id=f"{spec.product}:{index:02d}:{digest[:12]}",
                    product=spec.product,
                    relative_path=relative_path,
                    media_type=spec.media_type,
                    size_bytes=destination.stat().st_size,
                    sha256=digest,
                    crs=spec.crs,
                    resolution_m=spec.resolution_m,
                    vertical_datum=spec.vertical_datum,
                    retrieved_utc=spec.retrieved_utc,
                    source_tile_ids=spec.source_tile_ids,
                    source_layer_ids=spec.source_layer_ids,
                    licence_id=selection_facts.licence_id,
                    derived=spec.derived,
                    lineage=spec.lineage,
                )
            )

        bundle_material = {
            "selection_sha256": selection_facts.sha256,
            "bundle_version": plan.bundle_version,
            "processing_version": plan.processing_version,
            "products": [
                {
                    "product": record.product,
                    "relative_path": record.relative_path,
                    "sha256": record.sha256,
                    "crs": record.crs,
                    "resolution_m": record.resolution_m,
                    "vertical_datum": record.vertical_datum,
                    "retrieved_utc": record.retrieved_utc,
                    "source_tile_ids": list(record.source_tile_ids),
                    "source_layer_ids": list(record.source_layer_ids),
                    "derived": record.derived,
                    "lineage": list(record.lineage),
                }
                for record in records
            ],
        }
        bundle_digest = hashlib.sha256(
            _canonical_json_bytes(bundle_material)
        ).hexdigest()
        bundle_id = f"lidarbc-{bundle_digest[:16]}"
        manifest = LidarProductManifest(
            bundle_id=bundle_id,
            bundle_name=f"{bundle_id}-{plan.bundle_version}",
            bundle_version=plan.bundle_version,
            created_utc=generated_utc or datetime.now(UTC).isoformat(),
            producer={"tool": "femic", "version": __version__},
            source=_required_mapping(
                selection_payload,
                "source",
                context="selection manifest",
            ),
            selection={
                "schema_version": selection_facts.schema_version,
                "generated_utc": selection_facts.generated_utc,
                "sha256": selection_facts.sha256,
                "aoi_bbox_epsg3005": list(selection_facts.aoi_bbox_epsg3005),
                "requested_products": list(selection_facts.products),
                "tile_ids": list(selection_facts.tile_ids),
                "source_layer_ids": list(selection_facts.source_layer_ids),
                "tile_count": len(selection_facts.tile_ids),
            },
            processing={
                "version": plan.processing_version,
                "lineage": list(plan.processing_lineage),
                "parameters": plan.parameters,
            },
            products=tuple(records),
            consumer_contract=_consumer_contract(),
        )
        manifest_path = temp_dir / LIDAR_PRODUCT_MANIFEST_NAME
        manifest_path.write_text(_pretty_json(manifest.to_dict()), encoding="utf-8")
        if output.exists():
            if any(output.iterdir()):
                _assert_replaceable_bundle(output)
                shutil.rmtree(output)
            else:
                output.rmdir()
        temp_dir.replace(output)
        return LidarProductBuildResult(
            bundle_dir=output,
            manifest_path=output / LIDAR_PRODUCT_MANIFEST_NAME,
            selection_path=output / LIDAR_SELECTION_PROVENANCE_PATH,
            manifest=manifest,
        )
    except Exception:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise


def validate_lidar_product_bundle(
    bundle_dir: Path,
    *,
    checked_utc: str | None = None,
) -> LidarProductValidation:
    """Validate a product bundle against its manifest and provenance.

    The check covers manifest structure, selection digest, product existence and
    checksums, native CRS, resolution and vertical-datum fields, licence,
    derived-product labelling, and selected-tile lineage. It does not parse
    raster or point-cloud payloads.
    """

    root = bundle_dir.expanduser().resolve()
    manifest_path = root / LIDAR_PRODUCT_MANIFEST_NAME
    errors: list[str] = []
    warnings: list[str] = []
    bundle_id: str | None = None
    bundle_version: str | None = None
    product_count = 0
    total_bytes = 0
    selection_facts: _SelectionFacts | None = None

    try:
        manifest = _read_json_object(manifest_path, context="LiDAR product manifest")
    except LidarProductError as exc:
        errors.append(str(exc))
        manifest = None
    if manifest is None:
        return _validation_result(
            root,
            manifest_path,
            errors,
            warnings,
            checked_utc,
            bundle_id,
            bundle_version,
            product_count,
            total_bytes,
        )

    try:
        schema_version = _required_str(
            manifest,
            "schema_version",
            context="product manifest",
        )
        if schema_version != LIDAR_PRODUCT_SCHEMA_VERSION:
            errors.append(
                f"Unsupported product manifest schema {schema_version!r}; expected "
                f"{LIDAR_PRODUCT_SCHEMA_VERSION!r}."
            )
        bundle_id = _optional_str(manifest.get("bundle_id"))
        bundle_version = _optional_str(manifest.get("bundle_version"))
        if not bundle_id:
            errors.append("Product manifest is missing `bundle_id`.")
        if not bundle_version:
            errors.append("Product manifest is missing `bundle_version`.")

        source = _optional_mapping(manifest.get("source"), context="manifest source")
        selection = _required_mapping(
            manifest,
            "selection",
            context="product manifest",
        )
        selection_digest = _required_str(
            selection,
            "sha256",
            context="manifest selection",
        )
        selection_path = root / LIDAR_SELECTION_PROVENANCE_PATH
        if not selection_path.is_file():
            errors.append(
                f"Missing selection provenance: {LIDAR_SELECTION_PROVENANCE_PATH}"
            )
        else:
            provenance = _read_json_object(
                selection_path,
                context="selection provenance",
            )
            actual_digest = hashlib.sha256(
                _canonical_json_bytes(provenance)
            ).hexdigest()
            if actual_digest != selection_digest:
                errors.append(
                    "Selection provenance digest does not match the manifest."
                )
            try:
                selection_facts = _selection_facts(provenance)
            except LidarProductError as exc:
                errors.append(f"Invalid selection provenance: {exc}")
        if selection_facts is not None:
            if _optional_str(source.get("source_id")) != selection_facts.source_id:
                errors.append("Manifest source_id does not match selection provenance.")
            if _optional_str(source.get("licence_id")) != selection_facts.licence_id:
                errors.append(
                    "Manifest licence_id does not match selection provenance."
                )
            if _optional_str(source.get("native_crs")) != selection_facts.native_crs:
                errors.append(
                    "Manifest native_crs does not match selection provenance."
                )

        processing = _optional_mapping(
            manifest.get("processing"),
            context="manifest processing",
        )
        if not _optional_str(processing.get("version")):
            errors.append("Product manifest is missing `processing.version`.")

        consumer_contract = _optional_mapping(
            manifest.get("consumer_contract"),
            context="consumer contract",
        )
        for key in (
            "manifest_path",
            "selection_provenance_path",
            "products_dir",
            "pin_rule",
            "native_resolution_rule",
            "consumer_phases",
        ):
            if key not in consumer_contract:
                errors.append(f"Consumer contract is missing {key!r}.")

        raw_products = manifest.get("products")
        if not isinstance(raw_products, list) or not raw_products:
            errors.append("Product manifest must contain a non-empty `products` list.")
            raw_products = []
        seen_product_ids: set[str] = set()
        seen_relative_paths: set[str] = set()
        recorded_products: set[str] = set()
        for index, item in enumerate(raw_products, start=1):
            if not isinstance(item, Mapping):
                errors.append(f"Product entry {index} is not an object.")
                continue
            product = {str(key): value for key, value in item.items()}
            try:
                record = _record_from_manifest(
                    product, context=f"product entry {index}"
                )
            except LidarProductError as exc:
                errors.append(str(exc))
                continue
            product_count += 1
            total_bytes += record.size_bytes
            recorded_products.add(record.product)
            if record.product_id in seen_product_ids:
                errors.append(f"Duplicate product_id {record.product_id!r}.")
            seen_product_ids.add(record.product_id)
            if record.relative_path in seen_relative_paths:
                errors.append(f"Duplicate product path {record.relative_path!r}.")
            seen_relative_paths.add(record.relative_path)
            if record.product not in LIDAR_PRODUCT_KINDS:
                errors.append(
                    f"Unsupported product kind {record.product!r} in "
                    f"{record.relative_path}."
                )
            if (
                record.product in LIDAR_RASTER_PRODUCT_KINDS
                and record.resolution_m is None
            ):
                errors.append(
                    f"Raster product {record.relative_path} is missing resolution_m."
                )
            if record.resolution_m is not None and record.resolution_m <= 0:
                errors.append(
                    f"Product {record.relative_path} has non-positive resolution_m."
                )
            if record.derived != (record.product in LIDAR_DERIVED_PRODUCT_KINDS):
                errors.append(
                    f"Product {record.relative_path} has inconsistent derived flag."
                )
            if record.product in LIDAR_DERIVED_PRODUCT_KINDS and not record.lineage:
                warnings.append(
                    f"Derived product {record.relative_path} has no lineage notes."
                )
            if selection_facts is not None:
                if record.crs != selection_facts.native_crs:
                    errors.append(
                        f"Product {record.relative_path} CRS {record.crs!r} does not "
                        f"match native CRS {selection_facts.native_crs!r}."
                    )
                if record.licence_id != selection_facts.licence_id:
                    errors.append(
                        f"Product {record.relative_path} licence "
                        f"{record.licence_id!r} does not match source licence "
                        f"{selection_facts.licence_id!r}."
                    )
                unknown_tiles = set(record.source_tile_ids) - set(
                    selection_facts.tile_ids
                )
                if unknown_tiles:
                    errors.append(
                        f"Product {record.relative_path} references unknown source "
                        f"tiles: {', '.join(sorted(unknown_tiles))}."
                    )
            artifact_path = _resolve_bundle_member(root, record.relative_path)
            if artifact_path is None:
                errors.append(
                    f"Product path escapes the bundle: {record.relative_path!r}."
                )
            elif not artifact_path.is_file():
                errors.append(f"Missing product artifact: {record.relative_path}")
            else:
                if artifact_path.stat().st_size != record.size_bytes:
                    errors.append(
                        f"Product size mismatch for {record.relative_path}: "
                        f"{artifact_path.stat().st_size} != {record.size_bytes}."
                    )
                if _sha256_file(artifact_path) != record.sha256:
                    errors.append(
                        f"Product checksum mismatch for {record.relative_path}."
                    )
        if selection_facts is not None:
            missing_products = set(selection_facts.products) - recorded_products
            if missing_products:
                warnings.append(
                    "Selection requested products not present in this bundle: "
                    + ", ".join(sorted(missing_products))
                    + "."
                )
        summary = _optional_mapping(manifest.get("summary"), context="summary")
        if summary.get("product_count") != product_count:
            errors.append("Manifest summary product_count does not match products.")
        if summary.get("total_bytes") != total_bytes:
            errors.append("Manifest summary total_bytes does not match products.")
    except LidarProductError as exc:
        errors.append(str(exc))

    return _validation_result(
        root,
        manifest_path,
        errors,
        warnings,
        checked_utc,
        bundle_id,
        bundle_version,
        product_count,
        total_bytes,
    )


def _validation_result(
    root: Path,
    manifest_path: Path,
    errors: list[str],
    warnings: list[str],
    checked_utc: str | None,
    bundle_id: str | None,
    bundle_version: str | None,
    product_count: int,
    total_bytes: int,
) -> LidarProductValidation:
    return LidarProductValidation(
        bundle_dir=root,
        manifest_path=manifest_path,
        is_valid=not errors,
        checked_utc=checked_utc or datetime.now(UTC).isoformat(),
        errors=tuple(errors),
        warnings=tuple(warnings),
        bundle_id=bundle_id,
        bundle_version=bundle_version,
        product_count=product_count,
        total_bytes=total_bytes,
    )


def _product_spec_from_payload(
    item: object,
    *,
    plan_root: Path,
    index: int,
) -> LidarProductSpec:
    product = _optional_mapping(item, context=f"product entry {index}")
    product_kind = _required_str(
        product,
        "product",
        context=f"product entry {index}",
    )
    raw_path = _required_str(product, "path", context=f"product entry {index}")
    source_path = Path(raw_path).expanduser()
    if not source_path.is_absolute():
        source_path = plan_root / source_path
    return LidarProductSpec(
        product=product_kind,
        source_path=source_path.resolve(),
        media_type=_required_str(
            product,
            "media_type",
            context=f"product entry {index}",
        ),
        crs=_required_str(product, "crs", context=f"product entry {index}"),
        resolution_m=_optional_float(product.get("resolution_m")),
        vertical_datum=_required_str(
            product,
            "vertical_datum",
            context=f"product entry {index}",
        ),
        retrieved_utc=_required_str(
            product,
            "retrieved_utc",
            context=f"product entry {index}",
        ),
        source_tile_ids=_required_str_list(
            product.get("source_tile_ids"),
            context=f"product entry {index} source_tile_ids",
        ),
        source_layer_ids=_required_int_list(
            product.get("source_layer_ids"),
            context=f"product entry {index} source_layer_ids",
        ),
        derived=_optional_bool(product.get("derived")),
        lineage=_optional_str_list(
            product.get("lineage"),
            context=f"product entry {index} lineage",
        ),
    )


def _validate_plan(plan: LidarProductPlan, selection: _SelectionFacts) -> None:
    if not plan.products:
        raise LidarProductError("Product plan must contain at least one product.")
    seen_paths: set[Path] = set()
    for spec in plan.products:
        if spec.product not in LIDAR_PRODUCT_KINDS:
            raise LidarProductError(
                f"Unsupported product kind {spec.product!r}; expected one of: "
                + ", ".join(LIDAR_PRODUCT_KINDS)
                + "."
            )
        if not spec.source_path.is_file():
            raise LidarProductError(
                f"Product source does not exist: {spec.source_path}"
            )
        if spec.source_path in seen_paths:
            raise LidarProductError(
                f"Product source is reused in the plan: {spec.source_path}"
            )
        seen_paths.add(spec.source_path)
        if spec.crs != selection.native_crs:
            raise LidarProductError(
                f"Product {spec.product!r} CRS {spec.crs!r} does not match native "
                f"CRS {selection.native_crs!r}; silent reprojection is not allowed."
            )
        if spec.product in LIDAR_RASTER_PRODUCT_KINDS and spec.resolution_m is None:
            raise LidarProductError(
                f"Raster product {spec.product!r} must declare resolution_m."
            )
        if spec.resolution_m is not None and spec.resolution_m <= 0:
            raise LidarProductError(
                f"Product {spec.product!r} must declare positive resolution_m."
            )
        if spec.derived != (spec.product in LIDAR_DERIVED_PRODUCT_KINDS):
            raise LidarProductError(
                f"Product {spec.product!r} has an inconsistent `derived` flag."
            )
        unknown_tiles = set(spec.source_tile_ids) - set(selection.tile_ids)
        if unknown_tiles:
            raise LidarProductError(
                f"Product {spec.product!r} references tiles outside the selection: "
                + ", ".join(sorted(unknown_tiles))
                + "."
            )


def _selection_facts(payload: Mapping[str, object]) -> _SelectionFacts:
    schema_version = _required_str(
        payload,
        "schema_version",
        context="selection manifest",
    )
    if schema_version != LIDAR_SELECTION_SCHEMA_VERSION:
        raise LidarProductError(
            f"Unsupported selection manifest schema {schema_version!r}; expected "
            f"{LIDAR_SELECTION_SCHEMA_VERSION!r}."
        )
    source = _required_mapping(payload, "source", context="selection manifest")
    source_id = _required_str(source, "source_id", context="selection source")
    licence_id = _required_str(source, "licence_id", context="selection source")
    native_crs = _required_str(source, "native_crs", context="selection source")
    if source_id != LIDARBC_SOURCE_ID:
        raise LidarProductError(
            f"Product bundles currently support only {LIDARBC_SOURCE_ID!r}; "
            f"selection uses {source_id!r}."
        )
    if licence_id != LIDARBC_LICENCE_ID:
        raise LidarProductError(
            f"Product bundles require the {LIDARBC_LICENCE_ID} source licence; "
            f"selection uses {licence_id!r}."
        )
    if native_crs != LIDARBC_NATIVE_CRS:
        raise LidarProductError(
            f"Product bundles require native CRS {LIDARBC_NATIVE_CRS}; "
            f"selection uses {native_crs!r}."
        )
    aoi = _required_mapping(payload, "aoi", context="selection manifest")
    raw_bbox = _required_list(aoi, "bbox_epsg3005", context="selection AOI")
    try:
        bbox = normalize_bbox_epsg3005(raw_bbox)
    except LidarCatalogError as exc:
        raise LidarProductError(f"Invalid selection AOI: {exc}") from exc
    products = _required_str_list(
        payload.get("products"),
        context="selection products",
    )
    raw_tiles = _required_list(payload, "tiles", context="selection manifest")
    tile_ids: list[str] = []
    source_layer_ids: set[int] = set()
    for index, item in enumerate(raw_tiles, start=1):
        tile = _optional_mapping(item, context=f"selection tile {index}")
        tile_ids.append(
            _required_str(tile, "tile_id", context=f"selection tile {index}")
        )
        source_layer_ids.add(
            _required_int(tile, "layer_id", context=f"selection tile {index}")
        )
    if not tile_ids:
        raise LidarProductError("Selection manifest contains no tiles.")
    if len(set(tile_ids)) != len(tile_ids):
        raise LidarProductError("Selection manifest contains duplicate tile IDs.")
    return _SelectionFacts(
        schema_version=schema_version,
        generated_utc=_optional_str(payload.get("generated_utc")) or "",
        source_id=source_id,
        licence_id=licence_id,
        native_crs=native_crs,
        aoi_bbox_epsg3005=bbox,
        products=products,
        tile_ids=tuple(sorted(tile_ids)),
        source_layer_ids=tuple(sorted(source_layer_ids)),
        sha256=hashlib.sha256(_canonical_json_bytes(payload)).hexdigest(),
    )


def _consumer_contract() -> dict[str, object]:
    return {
        "manifest_path": LIDAR_PRODUCT_MANIFEST_NAME,
        "selection_provenance_path": LIDAR_SELECTION_PROVENANCE_PATH,
        "products_dir": LIDAR_PRODUCTS_DIR,
        "pin_rule": (
            "Pin `bundle_id` and `bundle_version`, then verify each product "
            "`sha256` before use."
        ),
        "native_resolution_rule": (
            "Consume the recorded CRS, resolution, and vertical datum. Do not "
            "reproject or resample silently."
        ),
        "consumer_phases": dict(LIDAR_CONSUMER_PHASES),
        "required_product_fields": [
            "product_id",
            "product",
            "relative_path",
            "sha256",
            "crs",
            "resolution_m",
            "vertical_datum",
            "retrieved_utc",
            "source_tile_ids",
            "licence_id",
        ],
    }


def _record_from_manifest(
    payload: Mapping[str, object],
    *,
    context: str,
) -> LidarProductRecord:
    return LidarProductRecord(
        product_id=_required_str(payload, "product_id", context=context),
        product=_required_str(payload, "product", context=context),
        relative_path=_required_str(payload, "relative_path", context=context),
        media_type=_required_str(payload, "media_type", context=context),
        size_bytes=_required_int(payload, "size_bytes", context=context),
        sha256=_required_str(payload, "sha256", context=context),
        crs=_required_str(payload, "crs", context=context),
        resolution_m=_optional_float(payload.get("resolution_m")),
        vertical_datum=_required_str(payload, "vertical_datum", context=context),
        retrieved_utc=_required_str(payload, "retrieved_utc", context=context),
        source_tile_ids=_required_str_list(
            payload.get("source_tile_ids"),
            context=f"{context} source_tile_ids",
        ),
        source_layer_ids=_required_int_list(
            payload.get("source_layer_ids"),
            context=f"{context} source_layer_ids",
        ),
        licence_id=_required_str(payload, "licence_id", context=context),
        derived=_optional_bool(payload.get("derived")),
        lineage=_optional_str_list(
            payload.get("lineage"),
            context=f"{context} lineage",
        ),
    )


def _prepare_output(output: Path, *, overwrite: bool) -> None:
    if not output.exists():
        return
    if not output.is_dir():
        raise LidarProductError(f"Output path is not a directory: {output}")
    if not any(output.iterdir()):
        return
    if not overwrite:
        raise LidarProductError(
            f"Output directory is not empty: {output}. Use `--overwrite` to "
            "replace a FEMIC product bundle."
        )
    _assert_replaceable_bundle(output)


def _assert_replaceable_bundle(output: Path) -> None:
    manifest_path = output / LIDAR_PRODUCT_MANIFEST_NAME
    if not manifest_path.is_file():
        raise LidarProductError(f"Refusing to overwrite non-bundle directory: {output}")
    try:
        manifest = _read_json_object(manifest_path, context="existing manifest")
    except LidarProductError as exc:
        raise LidarProductError(
            f"Refusing to overwrite unreadable bundle: {output}"
        ) from exc
    if manifest.get("schema_version") != LIDAR_PRODUCT_SCHEMA_VERSION:
        raise LidarProductError(
            f"Refusing to overwrite a non-FEMIC-LiDAR bundle: {output}"
        )


def _resolve_bundle_member(root: Path, relative_path: str) -> Path | None:
    candidate = (root / relative_path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    return candidate


def _artifact_relative_path(product: str, source_path: Path, index: int) -> str:
    safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", source_path.name).strip("._-")
    if not safe_name:
        safe_name = "artifact"
    return f"{LIDAR_PRODUCTS_DIR}/{product}__{index:02d}__{safe_name}"


def _read_json_object(path: Path, *, context: str) -> dict[str, object]:
    try:
        payload: object = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise LidarProductError(f"Unable to read {context}: {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise LidarProductError(f"Invalid JSON in {context}: {path}: {exc}") from exc
    if not isinstance(payload, Mapping):
        raise LidarProductError(f"{context} must be a JSON object: {path}")
    return {str(key): value for key, value in payload.items()}


def _required_mapping(
    mapping: Mapping[str, object],
    key: str,
    *,
    context: str,
) -> dict[str, object]:
    value = mapping.get(key)
    if not isinstance(value, Mapping):
        raise LidarProductError(f"{context} field {key!r} must be an object.")
    return {str(item_key): item for item_key, item in value.items()}


def _optional_mapping(value: object, *, context: str) -> dict[str, object]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise LidarProductError(f"{context} must be an object.")
    return {str(key): item for key, item in value.items()}


def _required_list(
    mapping: Mapping[str, object],
    key: str,
    *,
    context: str,
) -> list[object]:
    value = mapping.get(key)
    if not isinstance(value, list):
        raise LidarProductError(f"{context} field {key!r} must be a list.")
    return value


def _required_str(
    mapping: Mapping[str, object],
    key: str,
    *,
    context: str,
) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        raise LidarProductError(f"{context} field {key!r} must be a non-empty string.")
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
    if isinstance(value, bool):
        raise LidarProductError(f"{context} field {key!r} must be an integer.")
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError as exc:
            raise LidarProductError(
                f"{context} field {key!r} must be an integer."
            ) from exc
    raise LidarProductError(f"{context} field {key!r} must be an integer.")


def _required_str_list(value: object, *, context: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise LidarProductError(f"{context} must be a list.")
    items: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise LidarProductError(f"{context} entries must be non-empty strings.")
        items.append(item.strip())
    if not items:
        raise LidarProductError(f"{context} must not be empty.")
    return tuple(items)


def _required_int_list(value: object, *, context: str) -> tuple[int, ...]:
    if not isinstance(value, list):
        raise LidarProductError(f"{context} must be a list.")
    items: list[int] = []
    for item in value:
        if isinstance(item, bool):
            raise LidarProductError(f"{context} entries must be integers.")
        if isinstance(item, int):
            items.append(item)
        elif isinstance(item, str):
            try:
                items.append(int(item))
            except ValueError as exc:
                raise LidarProductError(f"{context} entries must be integers.") from exc
        else:
            raise LidarProductError(f"{context} entries must be integers.")
    if not items:
        raise LidarProductError(f"{context} must not be empty.")
    return tuple(items)


def _optional_str_list(value: object, *, context: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise LidarProductError(f"{context} must be a list.")
    items: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise LidarProductError(f"{context} entries must be strings.")
        text = item.strip()
        if text:
            items.append(text)
    return tuple(items)


def _optional_float(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise LidarProductError("Numeric field cannot be a boolean.")
    if isinstance(value, (int, float)):
        number = float(value)
    elif isinstance(value, str):
        try:
            number = float(value)
        except ValueError as exc:
            raise LidarProductError(f"Invalid numeric value: {value!r}") from exc
    else:
        raise LidarProductError(f"Invalid numeric value: {value!r}")
    if not math.isfinite(number):
        raise LidarProductError("Numeric values must be finite.")
    return number


def _optional_bool(value: object) -> bool:
    if value is None:
        return False
    if not isinstance(value, bool):
        raise LidarProductError(f"Boolean field must be true or false: {value!r}")
    return value


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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
