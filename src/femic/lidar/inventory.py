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
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import numpy as np  # type: ignore[import-untyped]
import pandas as pd  # type: ignore[import-untyped]
import rasterio  # type: ignore[import-untyped]

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
