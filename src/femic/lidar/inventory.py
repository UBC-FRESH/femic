"""Area-based inventory predictions from a pinned FEMIC LiDAR bundle.

The module is the INV-01 consumer seam, not a new ABA fitting algorithm.  It
reads a versioned model card, applies that model to a table product in a FEMIC
LiDAR product bundle, and writes the long ``inventory.als`` table.  A model card
must identify its coefficients, training scope, and error; FEMIC does not invent
them.

The first supported product is the tabular ``canopy`` artifact (one row per
LiDAR tile).  The output is intentionally a *fragment* table: a real application
can substitute fragment polygons and zonal metrics without changing the output
contract, but that join is not done here.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import numpy as np  # type: ignore[import-untyped]
import pandas as pd  # type: ignore[import-untyped]
import rasterio  # type: ignore[import-untyped]
from pyproj import CRS  # type: ignore[import-untyped]

from femic.lidar.products import (
    LIDAR_PRODUCT_MANIFEST_NAME,
    validate_lidar_product_bundle,
)

INVENTORY_ALS_SCHEMA_VERSION = "femic.inventory.als.v1"
INVENTORY_ALS_MODEL_SCHEMA_VERSION = "femic.inventory.als.model.v1"
DEFAULT_FRAGMENT_ID_FIELD = "tile_id"
DEFAULT_FEATURE_ID_FIELD = "fragment_id"
INVENTORY_ALS_MODEL_LINKS: tuple[str, ...] = ("identity", "log")
INVENTORY_ALS_CAVEATS: tuple[str, ...] = (
    "Area-based inventory predictions are model outputs, not field measurements.",
    "Model transferability and extrapolation are the caller's responsibility.",
    "The output table is long: one row per fragment and attribute.",
    "No reprojection, resampling, or source-product rewrite is performed.",
)


class LidarInventoryError(RuntimeError):
    """Raised when a model card, bundle, or inventory prediction is invalid."""


@dataclass(frozen=True)
class InventoryAlsModel:
    """A validated, pinned area-based model card."""

    path: Path
    model_id: str
    model_version: str
    attribute: str
    unit: str
    intercept: float
    coefficients: Mapping[str, float]
    rmse: float
    sample_count: int | None
    training_scope: str
    source: str
    caveats: tuple[str, ...]
    link: str = "identity"
    output_scale: float = 1.0
    applicability: Mapping[str, object] = field(default_factory=dict)
    predictor_ranges: Mapping[str, tuple[float, float]] = field(default_factory=dict)
    sha256: str = ""
    schema_version: str = INVENTORY_ALS_MODEL_SCHEMA_VERSION

    @property
    def features(self) -> tuple[str, ...]:
        """Return the predictor names in stable model-card order."""
        return tuple(self.coefficients)

    def to_dict(self) -> dict[str, object]:
        """Return the model card summary as a JSON-serializable mapping."""
        return {
            "schema_version": self.schema_version,
            "model_id": self.model_id,
            "model_version": self.model_version,
            "attribute": self.attribute,
            "unit": self.unit,
            "intercept": self.intercept,
            "coefficients": dict(self.coefficients),
            "rmse": self.rmse,
            "link": self.link,
            "output_scale": self.output_scale,
            "sample_count": self.sample_count,
            "training_scope": self.training_scope,
            "source": self.source,
            "applicability": dict(self.applicability),
            "predictor_ranges": {
                name: list(bounds) for name, bounds in self.predictor_ranges.items()
            },
            "caveats": list(self.caveats),
            "sha256": self.sha256,
        }


@dataclass(frozen=True)
class InventoryAlsRow:
    """One predicted inventory attribute for one fragment."""

    fragment_id: str
    attribute: str
    value: float
    model_id: str
    rmse: float
    model_version: str
    unit: str
    source: str

    def to_dict(self) -> dict[str, object]:
        """Return the row as a JSON-serializable mapping."""
        return {
            "fragment_id": self.fragment_id,
            "attribute": self.attribute,
            "value": self.value,
            "model_id": self.model_id,
            "rmse": self.rmse,
            "model_version": self.model_version,
            "unit": self.unit,
            "source": self.source,
        }


@dataclass(frozen=True)
class InventoryAlsValidationRow:
    """One predicted-versus-observed comparison row."""

    fragment_id: str
    attribute: str
    predicted: float
    observed: float
    residual: float

    def to_dict(self) -> dict[str, object]:
        """Return the row as a JSON-serializable mapping."""
        return {
            "fragment_id": self.fragment_id,
            "attribute": self.attribute,
            "predicted": self.predicted,
            "observed": self.observed,
            "residual": self.residual,
        }


@dataclass(frozen=True)
class InventoryAlsValidation:
    """Summary of an optional plot/observation comparison."""

    plots_path: Path
    matched_rows: int
    missing_observations: int
    bias: float | None
    mae: float | None
    rmse: float | None
    rows: tuple[InventoryAlsValidationRow, ...]

    def to_dict(self) -> dict[str, object]:
        """Return the validation summary as a JSON-serializable mapping."""
        return {
            "plots_path": str(self.plots_path),
            "matched_rows": self.matched_rows,
            "missing_observations": self.missing_observations,
            "bias": self.bias,
            "mae": self.mae,
            "rmse": self.rmse,
            "rows": [row.to_dict() for row in self.rows],
        }


@dataclass(frozen=True)
class InventoryAlsResult:
    """The complete ``inventory.als`` output contract."""

    bundle_dir: Path
    manifest_path: Path
    bundle_id: str
    bundle_version: str
    model: InventoryAlsModel
    rows: tuple[InventoryAlsRow, ...]
    generated_utc: str
    features_path: Path | None = None
    features_sha256: str = ""
    validation: InventoryAlsValidation | None = None
    warnings: tuple[str, ...] = ()
    caveats: tuple[str, ...] = INVENTORY_ALS_CAVEATS
    schema_version: str = INVENTORY_ALS_SCHEMA_VERSION

    def to_dict(self) -> dict[str, object]:
        """Return the output manifest as a JSON-serializable mapping."""
        return {
            "schema_version": self.schema_version,
            "bundle_dir": str(self.bundle_dir),
            "manifest_path": str(self.manifest_path),
            "bundle_id": self.bundle_id,
            "bundle_version": self.bundle_version,
            "generated_utc": self.generated_utc,
            "features_path": str(self.features_path) if self.features_path else None,
            "features_sha256": self.features_sha256,
            "model": self.model.to_dict(),
            "row_count": len(self.rows),
            "rows": [row.to_dict() for row in self.rows],
            "validation": self.validation.to_dict() if self.validation is not None else None,
            "warnings": list(self.warnings),
            "caveats": list(self.caveats),
        }


def load_inventory_als_model(path: Path) -> InventoryAlsModel:
    """Load and validate a fitted ABA model card.

    The model card is JSON.  Coefficients are explicit; this function never
    estimates or imputes them.  The card must identify its training scope and
    prediction error.
    """
    resolved = path.expanduser().resolve()
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except OSError as exc:
        raise LidarInventoryError(f"Unable to read model card: {resolved}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise LidarInventoryError(f"Invalid model-card JSON: {resolved}: {exc}") from exc
    if not isinstance(payload, Mapping):
        raise LidarInventoryError("Model card must be a JSON object.")

    schema_version = _required_text(payload, "schema_version")
    if schema_version != INVENTORY_ALS_MODEL_SCHEMA_VERSION:
        raise LidarInventoryError(
            f"Unsupported model schema {schema_version!r}; expected "
            f"{INVENTORY_ALS_MODEL_SCHEMA_VERSION!r}."
        )
    coefficients_raw = payload.get("coefficients")
    if not isinstance(coefficients_raw, Mapping) or not coefficients_raw:
        raise LidarInventoryError("Model card `coefficients` must be a non-empty object.")
    coefficients: dict[str, float] = {}
    for key, value in coefficients_raw.items():
        name = str(key).strip()
        if not name:
            raise LidarInventoryError("Model card coefficient names must be non-empty.")
        coefficients[name] = _finite_float(value, f"coefficient {name!r}")
    predictor_ranges: dict[str, tuple[float, float]] = {}
    ranges_raw = payload.get("predictor_ranges", {})
    if ranges_raw is not None and not isinstance(ranges_raw, Mapping):
        raise LidarInventoryError("Model card `predictor_ranges` must be an object.")
    if isinstance(ranges_raw, Mapping):
        for key, bounds in ranges_raw.items():
            name = str(key).strip()
            if name not in coefficients:
                raise LidarInventoryError(
                    f"Predictor range {name!r} has no matching coefficient."
                )
            if not isinstance(bounds, list | tuple) or len(bounds) != 2:
                raise LidarInventoryError(
                    f"Predictor range {name!r} must be [minimum, maximum]."
                )
            low = _finite_float(bounds[0], f"predictor range {name!r} minimum")
            high = _finite_float(bounds[1], f"predictor range {name!r} maximum")
            if low > high:
                raise LidarInventoryError(
                    f"Predictor range {name!r} minimum exceeds maximum."
                )
            predictor_ranges[name] = (low, high)

    rmse = _finite_float(payload.get("rmse"), "rmse")
    if rmse < 0:
        raise LidarInventoryError("Model card `rmse` must be non-negative.")
    sample_count_raw = payload.get("sample_count")
    sample_count: int | None = None
    if sample_count_raw is not None:
        if isinstance(sample_count_raw, bool) or not isinstance(sample_count_raw, int):
            raise LidarInventoryError("Model card `sample_count` must be an integer.")
        if sample_count_raw < 0:
            raise LidarInventoryError("Model card `sample_count` must be non-negative.")
        sample_count = sample_count_raw
    caveats_raw = payload.get("caveats", [])
    if not isinstance(caveats_raw, list) or not all(
        isinstance(item, str) and item.strip() for item in caveats_raw
    ):
        raise LidarInventoryError("Model card `caveats` must be a list of non-empty strings.")
    link = _required_text(payload, "link") if "link" in payload else "identity"
    if link not in INVENTORY_ALS_MODEL_LINKS:
        raise LidarInventoryError(
            f"Model card `link` must be one of {', '.join(INVENTORY_ALS_MODEL_LINKS)}."
        )
    output_scale = _finite_float(payload.get("output_scale", 1.0), "output_scale")
    if output_scale <= 0:
        raise LidarInventoryError("Model card `output_scale` must be positive.")
    applicability_raw = payload.get("applicability", {})
    if applicability_raw is not None and not isinstance(applicability_raw, Mapping):
        raise LidarInventoryError("Model card `applicability` must be an object.")
    applicability = dict(applicability_raw) if isinstance(applicability_raw, Mapping) else {}

    return InventoryAlsModel(
        path=resolved,
        model_id=_required_text(payload, "model_id"),
        model_version=_required_text(payload, "model_version"),
        attribute=_required_text(payload, "attribute"),
        unit=_required_text(payload, "unit"),
        intercept=_finite_float(payload.get("intercept", 0.0), "intercept"),
        coefficients=coefficients,
        rmse=rmse,
        sample_count=sample_count,
        training_scope=_required_text(payload, "training_scope"),
        source=_required_text(payload, "source"),
        caveats=tuple(caveats_raw),
        link=link,
        output_scale=output_scale,
        applicability=applicability,
        predictor_ranges=predictor_ranges,
        sha256=hashlib.sha256(resolved.read_bytes()).hexdigest(),
    )


def build_inventory_als(
    bundle_dir: Path,
    model_path: Path,
    *,
    features_path: Path | None = None,
    fragment_id_field: str | None = None,
    plots_path: Path | None = None,
    generated_utc: str | None = None,
) -> InventoryAlsResult:
    """Apply a fitted ABA model to one pinned FEMIC LiDAR bundle.

    The default source is the bundle's tabular ``canopy`` product.  A caller may
    instead pass ``features_path``, a CSV with ``fragment_id`` and the model's
    predictor columns; this is the seam for fragment or grid metrics computed
    from the bundle without pretending that the join happened here.
    """
    root = bundle_dir.expanduser().resolve()
    manifest_path = root / LIDAR_PRODUCT_MANIFEST_NAME
    validation = validate_lidar_product_bundle(root)
    if not validation.is_valid:
        raise LidarInventoryError(
            "LiDAR bundle failed validation: " + "; ".join(validation.errors)
        )
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LidarInventoryError(f"Unable to read bundle manifest: {exc}") from exc
    if not isinstance(manifest, Mapping):
        raise LidarInventoryError("Bundle manifest must be a JSON object.")
    bundle_id = _required_text(manifest, "bundle_id")
    bundle_version = _required_text(manifest, "bundle_version")

    if features_path is not None:
        table_path = features_path.expanduser().resolve()
        context = "Feature table"
        field = fragment_id_field or DEFAULT_FEATURE_ID_FIELD
    else:
        products = manifest.get("products")
        if not isinstance(products, list):
            raise LidarInventoryError("Bundle manifest has no product list.")
        canopy_record = next(
            (
                item
                for item in products
                if isinstance(item, Mapping) and item.get("product") == "canopy"
            ),
            None,
        )
        if canopy_record is None:
            raise LidarInventoryError(
                "Bundle has no `canopy` table product; pass `--features` with an "
                "explicit fragment feature table."
            )
        relative_path = canopy_record.get("relative_path")
        if not isinstance(relative_path, str):
            raise LidarInventoryError("Canopy product has no relative_path.")
        table_path = (root / relative_path).resolve()
        context = "Canopy product"
        field = fragment_id_field or DEFAULT_FRAGMENT_ID_FIELD

    try:
        table = pd.read_csv(table_path)
    except (OSError, ValueError) as exc:
        raise LidarInventoryError(f"Unable to read {context.lower()}: {table_path}: {exc}") from exc
    if table.empty:
        raise LidarInventoryError(f"{context} contains no rows.")
    if field not in table.columns:
        raise LidarInventoryError(
            f"{context} is missing fragment identifier {field!r}."
        )
    model = load_inventory_als_model(model_path)
    missing = [name for name in model.features if name not in table.columns]
    if missing:
        raise LidarInventoryError(
            f"{context} is missing model predictor(s): " + ", ".join(missing)
        )
    for name, (low, high) in model.predictor_ranges.items():
        values = pd.to_numeric(table[name], errors="coerce")
        if values.isna().any():
            raise LidarInventoryError(f"Predictor {name!r} contains non-numeric values.")
        if ((values < low) | (values > high)).any():
            raise LidarInventoryError(
                f"Predictor {name!r} is outside the model-card range [{low}, {high}]."
            )
    fragment_ids = table[field].astype(str)
    if fragment_ids.duplicated().any():
        duplicate = fragment_ids[fragment_ids.duplicated()].iloc[0]
        raise LidarInventoryError(
            f"{context} has duplicate fragment identifier {duplicate!r}."
        )
    rows: list[InventoryAlsRow] = []
    for record in table.itertuples(index=False):
        predictors = {name: float(getattr(record, name)) for name in model.features}
        if model.link == "log":
            non_positive = [name for name, value in predictors.items() if value <= 0]
            if non_positive:
                raise LidarInventoryError(
                    "Log-link predictor(s) must be positive: " + ", ".join(non_positive)
                )
            linear = model.intercept + sum(
                model.coefficients[name] * math.log(predictors[name])
                for name in model.features
            )
            value = math.exp(linear) * model.output_scale
        else:
            value = (
                model.intercept
                + sum(
                    model.coefficients[name] * predictors[name]
                    for name in model.features
                )
            ) * model.output_scale
        if not math.isfinite(value):
            raise LidarInventoryError(
                f"Model produced a non-finite value for fragment "
                f"{getattr(record, field)!r}."
            )
        rows.append(
            InventoryAlsRow(
                fragment_id=str(getattr(record, field)),
                attribute=model.attribute,
                value=value,
                model_id=model.model_id,
                rmse=model.rmse,
                model_version=model.model_version,
                unit=model.unit,
                source=model.source,
            )
        )
    validation_report = (
        _validate_against_plots(tuple(rows), plots_path) if plots_path is not None else None
    )
    warnings: list[str] = []
    regions = model.applicability.get("regions")
    if isinstance(regions, list) and regions:
        warnings.append(
            "Model applicability regions: "
            + ", ".join(str(region) for region in regions)
            + "; bundle region was not verified."
        )
    if validation_report is None:
        warnings.append("No plot/observation validation file was supplied.")
    elif validation_report.matched_rows == 0:
        warnings.append("Validation file matched no rows.")
    return InventoryAlsResult(
        bundle_dir=root,
        manifest_path=manifest_path,
        bundle_id=bundle_id,
        bundle_version=bundle_version,
        model=model,
        rows=tuple(rows),
        generated_utc=generated_utc or datetime.now(UTC).isoformat(),
        features_path=table_path if features_path is not None else None,
        features_sha256=(
            hashlib.sha256(table_path.read_bytes()).hexdigest()
            if features_path is not None
            else ""
        ),
        validation=validation_report,
        warnings=tuple(warnings),
    )


def build_chm_grid_features(
    bundle_dir: Path,
    output_path: Path,
    *,
    grid_size_m: float = 25.0,
    chm_product: str = "chm",
    min_cover_pct: float = 0.0,
) -> dict[str, object]:
    """Derive a 25 m grid feature table from a bundle CHM.

    Metrics are CHM proxies for the first-return metrics used by many published
    ABA models: mean height, coefficient of variation, p95, and percent cover
    above 2 m.  Cells with fewer than three above-2 m pixels are omitted.  This
    is a wall-to-wall feature seam, not a point-cloud metric replacement.
    """
    root = bundle_dir.expanduser().resolve()
    validation = validate_lidar_product_bundle(root)
    if not validation.is_valid:
        raise LidarInventoryError(
            "LiDAR bundle failed validation: " + "; ".join(validation.errors)
        )
    manifest_path = root / LIDAR_PRODUCT_MANIFEST_NAME
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, Mapping):
        raise LidarInventoryError("Bundle manifest must be a JSON object.")
    bundle_id = _required_text(manifest, "bundle_id")
    products = manifest.get("products")
    if not isinstance(products, list):
        raise LidarInventoryError("Bundle manifest has no product list.")
    record = next(
        (
            item
            for item in products
            if isinstance(item, Mapping) and item.get("product") == chm_product
        ),
        None,
    )
    if record is None:
        raise LidarInventoryError(f"Bundle has no {chm_product!r} raster product.")
    relative_path = record.get("relative_path")
    if not isinstance(relative_path, str):
        raise LidarInventoryError(f"{chm_product!r} product has no relative_path.")
    chm_path = (root / relative_path).resolve()
    if grid_size_m <= 0:
        raise LidarInventoryError("grid_size_m must be positive.")
    if not 0.0 <= min_cover_pct <= 100.0:
        raise LidarInventoryError("min_cover_pct must be between 0 and 100.")

    rows: list[dict[str, object]] = []
    try:
        with rasterio.open(chm_path) as dataset:
            data = (
                dataset.read(1, masked=True)
                .astype("float64")
                .filled(float("nan"))
            )
            transform = dataset.transform
            resolution = abs(transform.a)
            if resolution <= 0:
                raise LidarInventoryError("CHM raster has an invalid resolution.")
            block = max(1, round(grid_size_m / resolution))
            height, width = data.shape
            cell = 0
            for row_start in range(0, height, block):
                for col_start in range(0, width, block):
                    values = np.asarray(
                        data[
                            row_start : min(row_start + block, height),
                            col_start : min(col_start + block, width),
                        ]
                    )
                    valid = values[np.isfinite(values)]
                    if valid.size == 0:
                        continue
                    above = valid[valid > 2.0]
                    if above.size < 3:
                        continue
                    mean = float(above.mean())
                    std = float(above.std())
                    cv = std / mean if mean > 0 else float("nan")
                    p95 = float(np.percentile(above, 95))
                    cover = 100.0 * above.size / valid.size
                    if cover < min_cover_pct:
                        continue
                    center_x = float(transform.c + (col_start + block / 2) * resolution)
                    center_y = float(transform.f - (row_start + block / 2) * resolution)
                    rows.append(
                        {
                            "fragment_id": f"{bundle_id}:cell:{cell:05d}",
                            "x_center": center_x,
                            "y_center": center_y,
                            "Lhmean": mean,
                            "Lhcv": cv,
                            "Lhp95": p95,
                            "CC2m": cover,
                            "valid_pixels": int(valid.size),
                            "above2m_pixels": int(above.size),
                            "grid_size_m": grid_size_m,
                        }
                    )
                    cell += 1
    except OSError as exc:
        raise LidarInventoryError(f"Unable to read CHM raster: {chm_path}: {exc}") from exc
    if not rows:
        raise LidarInventoryError("No grid cells had enough above-2 m CHM pixels.")
    output = output_path.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(rows)
    frame.to_csv(output, index=False)
    return {
        "bundle_id": bundle_id,
        "chm_path": chm_path,
        "output_path": output,
        "grid_size_m": grid_size_m,
        "min_cover_pct": min_cover_pct,
        "row_count": len(rows),
        "columns": list(frame.columns),
    }



def _horizontal_epsg(crs: object) -> int | None:
    """Return the horizontal EPSG code from a 2D or compound CRS."""
    try:
        parsed = CRS.from_user_input(crs)
    except Exception:
        return None
    if parsed.is_compound and parsed.sub_crs_list:
        parsed = parsed.sub_crs_list[0]
    return parsed.to_epsg()

def build_pointcloud_grid_features(
    pointcloud_paths: Sequence[Path],
    dem_path: Path,
    output_path: Path,
    *,
    grid_size_m: float = 25.0,
    height_threshold_m: float = 2.0,
    min_returns: int = 10,
    min_cover_pct: float = 0.0,
    batch_size: int = 5_000_000,
) -> dict[str, object]:
    """Derive first-return point-cloud metrics on a regular grid.

    The point clouds and the DEM must share a CRS.  The function samples the
    DEM, normalizes first returns to height above ground, and aggregates by
    grid cell.  It is the point-cloud counterpart to
    :func:`build_chm_grid_features`; it does not fit an ABA model.

    The optional ``laspy[lazrs]`` dependency is imported lazily because FEMIC
    does not make point-cloud processing mandatory for every installation.
    """
    try:
        import laspy  # type: ignore[import-untyped]
    except ImportError as exc:
        raise LidarInventoryError(
            "Point-cloud grid features require the optional `laspy[lazrs]` "
            "dependency; install `femic[lidar]`."
        ) from exc

    paths = [path.expanduser().resolve() for path in pointcloud_paths]
    if not paths:
        raise LidarInventoryError("At least one point-cloud path is required.")
    for path in paths:
        if not path.is_file():
            raise LidarInventoryError(f"Point-cloud file does not exist: {path}")
    dem = dem_path.expanduser().resolve()
    if not dem.is_file():
        raise LidarInventoryError(f"DEM file does not exist: {dem}")
    if grid_size_m <= 0:
        raise LidarInventoryError("grid_size_m must be positive.")
    if height_threshold_m <= 0:
        raise LidarInventoryError("height_threshold_m must be positive.")
    if min_returns < 0:
        raise LidarInventoryError("min_returns must be non-negative.")
    if not 0.0 <= min_cover_pct <= 100.0:
        raise LidarInventoryError("min_cover_pct must be between 0 and 100.")

    try:
        with rasterio.open(dem) as dataset:
            dem_data = dataset.read(1, masked=True).astype("float64")
            dem_array = dem_data.filled(float("nan"))
            transform = dataset.transform
            dem_crs = dataset.crs
            width = dataset.width
            height = dataset.height
            nodata = dataset.nodata
    except OSError as exc:
        raise LidarInventoryError(f"Unable to read DEM: {dem}: {exc}") from exc
    resolution = abs(transform.a)
    if resolution <= 0 or abs(transform.e) <= 0:
        raise LidarInventoryError("DEM has an invalid pixel size.")

    ncols = math.ceil(width * resolution / grid_size_m)
    nrows = math.ceil(height * resolution / grid_size_m)
    n_cells = nrows * ncols
    if n_cells <= 0:
        raise LidarInventoryError("DEM does not define any grid cells.")
    all_count = np.zeros(n_cells, dtype="int64")
    above_count = np.zeros(n_cells, dtype="int64")
    above_sum = np.zeros(n_cells, dtype="float64")
    above_sumsq = np.zeros(n_cells, dtype="float64")
    bin_width = 0.1
    max_height_m = 100.0
    n_bins = int(max_height_m / bin_width) + 1
    hist = np.zeros((n_cells, n_bins), dtype="int64")
    x0 = float(transform.c)
    y0 = float(transform.f)

    for path in paths:
        try:
            with laspy.open(path) as reader:
                las_crs = reader.header.parse_crs()
                if (
                    las_crs is not None
                    and dem_crs is not None
                    and _horizontal_epsg(las_crs) != _horizontal_epsg(dem_crs)
                ):
                    raise LidarInventoryError(
                        f"Point cloud CRS {las_crs.to_string()!r} does not match "
                        f"DEM CRS {dem_crs.to_string()!r}; silent reprojection is "
                        "not allowed."
                    )
                for chunk in reader.chunk_iterator(batch_size):
                    x = np.asarray(chunk.x, dtype="float64")
                    y = np.asarray(chunk.y, dtype="float64")
                    z = np.asarray(chunk.z, dtype="float64")
                    first = np.asarray(chunk.return_number) == 1
                    if not first.any():
                        continue
                    x = x[first]
                    y = y[first]
                    z = z[first]
                    pixel_col = np.floor((x - x0) / resolution).astype("int64")
                    pixel_row = np.floor((y0 - y) / resolution).astype("int64")
                    inside = (
                        (pixel_col >= 0)
                        & (pixel_col < width)
                        & (pixel_row >= 0)
                        & (pixel_row < height)
                    )
                    if not inside.any():
                        continue
                    x = x[inside]
                    y = y[inside]
                    z = z[inside]
                    pixel_col = pixel_col[inside]
                    pixel_row = pixel_row[inside]
                    ground = dem_array[pixel_row, pixel_col]
                    valid = np.isfinite(ground)
                    if nodata is not None:
                        valid &= ground != nodata
                    if not valid.any():
                        continue
                    x = x[valid]
                    y = y[valid]
                    z = z[valid]
                    ground = ground[valid]
                    cell_col = np.floor((x - x0) / grid_size_m).astype("int64")
                    cell_row = np.floor((y0 - y) / grid_size_m).astype("int64")
                    cells = (
                        (cell_col >= 0)
                        & (cell_col < ncols)
                        & (cell_row >= 0)
                        & (cell_row < nrows)
                    )
                    if not cells.any():
                        continue
                    cell_idx = cell_row[cells] * ncols + cell_col[cells]
                    heights = z[cells] - ground[cells]
                    valid_height = np.isfinite(heights) & (heights >= 0.0)
                    if not valid_height.any():
                        continue
                    cell_idx = cell_idx[valid_height]
                    heights = heights[valid_height]
                    all_count += np.bincount(cell_idx, minlength=n_cells)
                    above = heights > height_threshold_m
                    if not above.any():
                        continue
                    above_cells = cell_idx[above]
                    above_heights = heights[above]
                    above_count += np.bincount(above_cells, minlength=n_cells)
                    above_sum += np.bincount(
                        above_cells, weights=above_heights, minlength=n_cells
                    )
                    above_sumsq += np.bincount(
                        above_cells, weights=above_heights * above_heights, minlength=n_cells
                    )
                    bins = np.clip(
                        np.floor(above_heights / bin_width).astype("int64"),
                        0,
                        n_bins - 1,
                    )
                    flat = above_cells * n_bins + bins
                    hist += np.bincount(
                        flat, minlength=n_cells * n_bins
                    ).reshape(n_cells, n_bins)
        except OSError as exc:
            raise LidarInventoryError(f"Unable to read point cloud: {path}: {exc}") from exc

    rows: list[dict[str, object]] = []
    cumulative = np.cumsum(hist, axis=1)
    for cell in np.flatnonzero(above_count >= min_returns):
        total = int(all_count[cell])
        above = int(above_count[cell])
        if total == 0:
            continue
        cover = 100.0 * above / total
        if cover < min_cover_pct:
            continue
        mean = float(above_sum[cell] / above)
        variance = max(0.0, float(above_sumsq[cell] / above - mean * mean))
        cv = math.sqrt(variance) / mean if mean > 0 else float("nan")
        target = 0.95 * above
        p95_bin = int(np.searchsorted(cumulative[cell], target, side="left"))
        p95 = min(max_height_m, (p95_bin + 0.5) * bin_width)
        row = cell // ncols
        col = cell % ncols
        rows.append(
            {
                "fragment_id": f"cell_{row:05d}_{col:05d}",
                "x_center": x0 + (col + 0.5) * grid_size_m,
                "y_center": y0 - (row + 0.5) * grid_size_m,
                "Lhmean": mean,
                "Lhcv": cv,
                "Lhp95": p95,
                "CC2m": cover,
                "all_first_returns": total,
                "above2m_returns": above,
                "grid_size_m": grid_size_m,
            }
        )
    if not rows:
        raise LidarInventoryError("No grid cells had enough first returns.")
    output = output_path.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(rows)
    frame.to_csv(output, index=False)
    return {
        "dem_path": dem,
        "pointcloud_paths": [str(path) for path in paths],
        "output_path": output,
        "grid_size_m": grid_size_m,
        "height_threshold_m": height_threshold_m,
        "min_returns": min_returns,
        "min_cover_pct": min_cover_pct,
        "row_count": len(rows),
        "columns": list(frame.columns),
    }


def write_inventory_als(result: InventoryAlsResult, out_dir: Path) -> dict[str, Path]:
    """Write the long inventory table and its provenance manifest."""
    output = out_dir.expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    table_path = output / "inventory_als.csv"
    columns = (
        "fragment_id",
        "attribute",
        "value",
        "model_id",
        "rmse",
        "model_version",
        "unit",
        "source",
    )
    with table_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(row.to_dict() for row in result.rows)
    manifest_path = output / "inventory_als.json"
    manifest_path.write_text(
        json.dumps(result.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    paths: dict[str, Path] = {"table": table_path, "manifest": manifest_path}
    if result.validation is not None:
        validation_path = output / "inventory_als_validation.csv"
        with validation_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=("fragment_id", "attribute", "predicted", "observed", "residual"),
            )
            writer.writeheader()
            writer.writerows(row.to_dict() for row in result.validation.rows)
        paths["validation"] = validation_path
    return paths


def _validate_against_plots(
    rows: tuple[InventoryAlsRow, ...],
    plots_path: Path,
) -> InventoryAlsValidation:
    resolved = plots_path.expanduser().resolve()
    try:
        plots = pd.read_csv(resolved)
    except (OSError, ValueError) as exc:
        raise LidarInventoryError(f"Unable to read plot table: {resolved}: {exc}") from exc
    required = {"fragment_id", "attribute", "observed"}
    missing = required - set(plots.columns)
    if missing:
        raise LidarInventoryError(
            "Plot table is missing required columns: " + ", ".join(sorted(missing))
        )
    observations = {
        (str(row.fragment_id), str(row.attribute)): _finite_float(row.observed, "observed")
        for row in plots.itertuples(index=False)
    }
    validation_rows: list[InventoryAlsValidationRow] = []
    missing_observations = 0
    for row in rows:
        observed = observations.get((row.fragment_id, row.attribute))
        if observed is None:
            missing_observations += 1
            continue
        validation_rows.append(
            InventoryAlsValidationRow(
                fragment_id=row.fragment_id,
                attribute=row.attribute,
                predicted=row.value,
                observed=observed,
                residual=row.value - observed,
            )
        )
    residuals = [row.residual for row in validation_rows]
    return InventoryAlsValidation(
        plots_path=resolved,
        matched_rows=len(validation_rows),
        missing_observations=missing_observations,
        bias=sum(residuals) / len(residuals) if residuals else None,
        mae=sum(abs(value) for value in residuals) / len(residuals) if residuals else None,
        rmse=math.sqrt(sum(value * value for value in residuals) / len(residuals))
        if residuals
        else None,
        rows=tuple(validation_rows),
    )


def _required_text(payload: Mapping[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise LidarInventoryError(f"Model field {key!r} must be a non-empty string.")
    return value.strip()


def _finite_float(value: object, name: str) -> float:
    if isinstance(value, bool):
        raise LidarInventoryError(f"Model field {name!r} must be a finite number.")
    try:
        result = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise LidarInventoryError(f"Model field {name!r} must be a finite number.") from exc
    if not math.isfinite(result):
        raise LidarInventoryError(f"Model field {name!r} must be a finite number.")
    return result
