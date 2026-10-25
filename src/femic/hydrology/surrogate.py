"""Surrogate models for fast hydrologic response queries.

P114.7 provides a design-of-experiments surface, two dependency-free surrogate
families (ridge linear and RBF Gaussian process), held-out validation, and an
explicit applicability domain that refuses extrapolation.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

import numpy as np

HYDROLOGY_SURROGATE_DESIGN_SCHEMA_VERSION = "femic.hydrology.surrogate_design.v1"
HYDROLOGY_SURROGATE_MODEL_SCHEMA_VERSION = "femic.hydrology.surrogate_model.v1"
HYDROLOGY_SURROGATE_FAMILIES: tuple[str, ...] = ("linear", "gp")
DEFAULT_SURROGATE_TARGET = "peak_flow_ratio"
DEFAULT_CONFIDENCE_LEVEL = 0.95


class HydrologySurrogateError(RuntimeError):
    """Raised when a surrogate design, model, or query is invalid."""


@dataclass(frozen=True)
class DesignFactor:
    """One continuous factor in a surrogate design."""

    name: str
    low: float
    high: float

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise HydrologySurrogateError("Design factor name must be non-empty.")
        if not math.isfinite(self.low) or not math.isfinite(self.high):
            raise HydrologySurrogateError("Design factor bounds must be finite.")
        if self.low >= self.high:
            raise HydrologySurrogateError(
                f"Design factor {self.name!r} requires low < high."
            )

    def to_dict(self) -> dict[str, object]:
        """Return the factor as a JSON-serializable mapping."""

        return {"name": self.name, "low": self.low, "high": self.high}


@dataclass(frozen=True)
class DesignPoint:
    """One feature vector from a surrogate design."""

    features: dict[str, float]

    def to_dict(self) -> dict[str, object]:
        """Return the point as a JSON-serializable mapping."""

        return {"features": self.features}


@dataclass(frozen=True)
class SurrogateDesign:
    """Latin-hypercube design over continuous hydrologic factors."""

    design_id: str
    generated_utc: str
    factors: tuple[DesignFactor, ...]
    points: tuple[DesignPoint, ...]
    seed: int
    schema_version: str = HYDROLOGY_SURROGATE_DESIGN_SCHEMA_VERSION

    def to_dict(self) -> dict[str, object]:
        """Return the design as a JSON-serializable mapping."""

        return {
            "schema_version": self.schema_version,
            "design_id": self.design_id,
            "generated_utc": self.generated_utc,
            "seed": self.seed,
            "factors": [factor.to_dict() for factor in self.factors],
            "summary": {"point_count": len(self.points)},
            "points": [point.to_dict() for point in self.points],
        }


@dataclass(frozen=True)
class SurrogateSample:
    """One feature/target training or validation sample."""

    features: dict[str, float]
    target: float

    def to_dict(self) -> dict[str, object]:
        """Return the sample as a JSON-serializable mapping."""

        return {"features": self.features, "target": self.target}


@dataclass(frozen=True)
class SurrogateDataset:
    """A validated surrogate training or validation dataset."""

    feature_names: tuple[str, ...]
    target_name: str
    samples: tuple[SurrogateSample, ...]
    source: str = ""
    schema_version: str = "femic.hydrology.surrogate_dataset.v1"

    def __post_init__(self) -> None:
        if not self.feature_names:
            raise HydrologySurrogateError("At least one feature is required.")
        if len(set(self.feature_names)) != len(self.feature_names):
            raise HydrologySurrogateError("Feature names must be unique.")
        if not self.target_name.strip():
            raise HydrologySurrogateError("Target name must be non-empty.")
        if not self.samples:
            raise HydrologySurrogateError("At least one sample is required.")
        for sample in self.samples:
            if set(sample.features) != set(self.feature_names):
                raise HydrologySurrogateError(
                    "Every sample must contain exactly the dataset features."
                )
            if any(
                not math.isfinite(float(value)) for value in sample.features.values()
            ):
                raise HydrologySurrogateError("Feature values must be finite.")
            if not math.isfinite(sample.target):
                raise HydrologySurrogateError("Target values must be finite.")

    def to_dict(self) -> dict[str, object]:
        """Return the dataset as a JSON-serializable mapping."""

        return {
            "schema_version": self.schema_version,
            "feature_names": list(self.feature_names),
            "target_name": self.target_name,
            "source": self.source,
            "sample_count": len(self.samples),
            "samples": [sample.to_dict() for sample in self.samples],
        }


@dataclass(frozen=True)
class ApplicabilityResult:
    """Whether a query lies inside a surrogate's validated domain."""

    inside: bool
    missing_features: tuple[str, ...] = ()
    outside_features: tuple[str, ...] = ()
    distance: float | None = None
    reasons: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        """Return the result as a JSON-serializable mapping."""

        return {
            "inside": self.inside,
            "missing_features": list(self.missing_features),
            "outside_features": list(self.outside_features),
            "distance": self.distance,
            "reasons": list(self.reasons),
        }


@dataclass(frozen=True)
class ApplicabilityDomain:
    """Bounded feature envelope plus standardized-distance guard."""

    feature_names: tuple[str, ...]
    min_values: dict[str, float]
    max_values: dict[str, float]
    mean_values: dict[str, float]
    scale_values: dict[str, float]
    max_distance: float

    def check(self, features: Mapping[str, float]) -> ApplicabilityResult:
        """Check whether one feature vector is inside the domain."""

        missing = tuple(name for name in self.feature_names if name not in features)
        if missing:
            return ApplicabilityResult(
                inside=False,
                missing_features=missing,
                reasons=("Missing required features.",),
            )
        outside: list[str] = []
        reasons: list[str] = []
        for name in self.feature_names:
            value = float(features[name])
            if not math.isfinite(value):
                outside.append(name)
                reasons.append(f"{name} is not finite.")
            elif value < self.min_values[name] or value > self.max_values[name]:
                outside.append(name)
                reasons.append(f"{name} is outside the training range.")
        distance = math.sqrt(
            sum(
                (
                    (float(features[name]) - self.mean_values[name])
                    / self.scale_values[name]
                )
                ** 2
                for name in self.feature_names
            )
        )
        if distance > self.max_distance:
            reasons.append("Feature vector exceeds the standardized distance guard.")
        inside = not outside and distance <= self.max_distance
        return ApplicabilityResult(
            inside=inside,
            missing_features=(),
            outside_features=tuple(outside),
            distance=distance,
            reasons=tuple(reasons),
        )

    def to_dict(self) -> dict[str, object]:
        """Return the domain as a JSON-serializable mapping."""

        return {
            "feature_names": list(self.feature_names),
            "min_values": self.min_values,
            "max_values": self.max_values,
            "mean_values": self.mean_values,
            "scale_values": self.scale_values,
            "max_distance": self.max_distance,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> ApplicabilityDomain:
        """Load an applicability domain from a mapping."""

        return cls(
            feature_names=tuple(
                _strings(payload.get("feature_names"), "feature_names")
            ),
            min_values=_float_mapping(payload.get("min_values"), "min_values"),
            max_values=_float_mapping(payload.get("max_values"), "max_values"),
            mean_values=_float_mapping(payload.get("mean_values"), "mean_values"),
            scale_values=_float_mapping(payload.get("scale_values"), "scale_values"),
            max_distance=float(str(payload.get("max_distance", 0.0))),
        )


class SurrogateModel(Protocol):
    """Protocol for a validated surrogate model."""

    @property
    def family(self) -> str:
        """Return the surrogate family name."""

    @property
    def feature_names(self) -> tuple[str, ...]:
        """Return the model feature order."""

    @property
    def applicability_domain(self) -> ApplicabilityDomain:
        """Return the validated applicability domain."""

    @property
    def warnings(self) -> tuple[str, ...]:
        """Return model warnings."""

    def predict(
        self,
        features: Mapping[str, float],
        *,
        allow_extrapolation: bool = False,
    ) -> float:
        """Predict one target value."""

    def predict_interval(
        self,
        features: Mapping[str, float],
        *,
        allow_extrapolation: bool = False,
    ) -> tuple[float, float]:
        """Predict an interval for one target value."""

    def to_dict(self) -> dict[str, object]:
        """Serialize the model."""


@dataclass(frozen=True)
class LinearSurrogate:
    """Standardized ridge-linear surrogate."""

    feature_names: tuple[str, ...]
    mean_values: dict[str, float]
    scale_values: dict[str, float]
    coefficients: tuple[float, ...]
    residual_sigma: float
    applicability_domain: ApplicabilityDomain
    warnings: tuple[str, ...] = ()
    family: str = "linear"

    def predict(
        self,
        features: Mapping[str, float],
        *,
        allow_extrapolation: bool = False,
    ) -> float:
        """Predict one target value."""

        self._require_domain(features, allow_extrapolation=allow_extrapolation)
        return self._predict_raw(features)

    def predict_interval(
        self,
        features: Mapping[str, float],
        *,
        allow_extrapolation: bool = False,
    ) -> tuple[float, float]:
        """Predict one target interval."""

        prediction = self.predict(
            features,
            allow_extrapolation=allow_extrapolation,
        )
        half_width = 1.96 * self.residual_sigma
        return prediction - half_width, prediction + half_width

    def _predict_raw(self, features: Mapping[str, float]) -> float:
        vector = _feature_vector(features, self.feature_names)
        standardized = [
            (vector[name] - self.mean_values[name]) / self.scale_values[name]
            for name in self.feature_names
        ]
        return float(
            self.coefficients[0]
            + sum(
                coefficient * value
                for coefficient, value in zip(
                    self.coefficients[1:],
                    standardized,
                    strict=False,
                )
            )
        )

    def _require_domain(
        self,
        features: Mapping[str, float],
        *,
        allow_extrapolation: bool,
    ) -> None:
        if allow_extrapolation:
            _feature_vector(features, self.feature_names)
            return
        result = self.applicability_domain.check(features)
        if not result.inside:
            raise HydrologySurrogateError(
                "Query is outside the applicability domain: "
                + "; ".join(result.reasons)
            )

    def to_dict(self) -> dict[str, object]:
        """Return the model as a JSON-serializable mapping."""

        return {
            "schema_version": HYDROLOGY_SURROGATE_MODEL_SCHEMA_VERSION,
            "family": self.family,
            "feature_names": list(self.feature_names),
            "mean_values": self.mean_values,
            "scale_values": self.scale_values,
            "coefficients": list(self.coefficients),
            "residual_sigma": self.residual_sigma,
            "applicability_domain": self.applicability_domain.to_dict(),
            "warnings": list(self.warnings),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> LinearSurrogate:
        """Load a linear surrogate from a mapping."""

        return cls(
            feature_names=tuple(
                _strings(payload.get("feature_names"), "feature_names")
            ),
            mean_values=_float_mapping(payload.get("mean_values"), "mean_values"),
            scale_values=_float_mapping(payload.get("scale_values"), "scale_values"),
            coefficients=tuple(
                float(str(value))
                for value in _list(payload.get("coefficients"), "coefficients")
            ),
            residual_sigma=float(str(payload.get("residual_sigma", 0.0))),
            applicability_domain=ApplicabilityDomain.from_dict(
                _mapping(payload.get("applicability_domain"), "applicability_domain")
            ),
            warnings=_strings(payload.get("warnings"), "warnings")
            if payload.get("warnings") is not None
            else (),
            family=str(payload.get("family", "linear")),
        )


@dataclass(frozen=True)
class GaussianProcessSurrogate:
    """RBF-kernel Gaussian-process surrogate."""

    feature_names: tuple[str, ...]
    mean_values: dict[str, float]
    scale_values: dict[str, float]
    train_standardized: tuple[tuple[float, ...], ...]
    alpha: tuple[float, ...]
    kernel_inverse: tuple[tuple[float, ...], ...]
    y_mean: float
    y_scale: float
    length_scale: float
    noise: float
    applicability_domain: ApplicabilityDomain
    warnings: tuple[str, ...] = ()
    family: str = "gp"

    def predict(
        self,
        features: Mapping[str, float],
        *,
        allow_extrapolation: bool = False,
    ) -> float:
        """Predict one target value."""

        self._require_domain(features, allow_extrapolation=allow_extrapolation)
        mean, _ = self._predict_raw(features)
        return mean

    def predict_interval(
        self,
        features: Mapping[str, float],
        *,
        allow_extrapolation: bool = False,
    ) -> tuple[float, float]:
        """Predict one target interval."""

        self._require_domain(features, allow_extrapolation=allow_extrapolation)
        mean, variance = self._predict_raw(features)
        half_width = 1.96 * math.sqrt(max(0.0, variance))
        return mean - half_width, mean + half_width

    def _predict_raw(self, features: Mapping[str, float]) -> tuple[float, float]:
        vector = _feature_vector(features, self.feature_names)
        standardized = np.asarray(
            [
                (vector[name] - self.mean_values[name]) / self.scale_values[name]
                for name in self.feature_names
            ],
            dtype=float,
        )
        train = np.asarray(self.train_standardized, dtype=float)
        squared = np.sum((train - standardized) ** 2, axis=1)
        kernel = np.exp(-0.5 * squared / (self.length_scale**2))
        mean_standardized = float(kernel @ np.asarray(self.alpha, dtype=float))
        inverse = np.asarray(self.kernel_inverse, dtype=float)
        variance_standardized = float(1.0 - kernel @ inverse @ kernel)
        mean = self.y_mean + self.y_scale * mean_standardized
        variance = self.y_scale**2 * max(0.0, variance_standardized)
        return mean, variance

    def _require_domain(
        self,
        features: Mapping[str, float],
        *,
        allow_extrapolation: bool,
    ) -> None:
        if allow_extrapolation:
            _feature_vector(features, self.feature_names)
            return
        result = self.applicability_domain.check(features)
        if not result.inside:
            raise HydrologySurrogateError(
                "Query is outside the applicability domain: "
                + "; ".join(result.reasons)
            )

    def to_dict(self) -> dict[str, object]:
        """Return the model as a JSON-serializable mapping."""

        return {
            "schema_version": HYDROLOGY_SURROGATE_MODEL_SCHEMA_VERSION,
            "family": self.family,
            "feature_names": list(self.feature_names),
            "mean_values": self.mean_values,
            "scale_values": self.scale_values,
            "train_standardized": [list(row) for row in self.train_standardized],
            "alpha": list(self.alpha),
            "kernel_inverse": [list(row) for row in self.kernel_inverse],
            "y_mean": self.y_mean,
            "y_scale": self.y_scale,
            "length_scale": self.length_scale,
            "noise": self.noise,
            "applicability_domain": self.applicability_domain.to_dict(),
            "warnings": list(self.warnings),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> GaussianProcessSurrogate:
        """Load a Gaussian-process surrogate from a mapping."""

        return cls(
            feature_names=tuple(
                _strings(payload.get("feature_names"), "feature_names")
            ),
            mean_values=_float_mapping(payload.get("mean_values"), "mean_values"),
            scale_values=_float_mapping(payload.get("scale_values"), "scale_values"),
            train_standardized=_matrix(
                payload.get("train_standardized"),
                "train_standardized",
            ),
            alpha=tuple(
                float(str(value)) for value in _list(payload.get("alpha"), "alpha")
            ),
            kernel_inverse=_matrix(
                payload.get("kernel_inverse"),
                "kernel_inverse",
            ),
            y_mean=float(str(payload.get("y_mean", 0.0))),
            y_scale=float(str(payload.get("y_scale", 1.0))),
            length_scale=float(str(payload.get("length_scale", 1.0))),
            noise=float(str(payload.get("noise", 1e-6))),
            applicability_domain=ApplicabilityDomain.from_dict(
                _mapping(payload.get("applicability_domain"), "applicability_domain")
            ),
            warnings=_strings(payload.get("warnings"), "warnings")
            if payload.get("warnings") is not None
            else (),
            family=str(payload.get("family", "gp")),
        )


@dataclass(frozen=True)
class SurrogateValidation:
    """Validation metrics for a surrogate against held-out targets."""

    model_family: str
    evaluation_size: int
    accepted_count: int
    refused_count: int
    rmse: float | None
    mae: float | None
    r2: float | None
    coverage_95: float | None
    mean_interval_width: float | None
    fold_count: int
    is_valid: bool
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        """Return the validation as a JSON-serializable mapping."""

        return {
            "model_family": self.model_family,
            "evaluation_size": self.evaluation_size,
            "accepted_count": self.accepted_count,
            "refused_count": self.refused_count,
            "rmse": self.rmse,
            "mae": self.mae,
            "r2": self.r2,
            "coverage_95": self.coverage_95,
            "mean_interval_width": self.mean_interval_width,
            "fold_count": self.fold_count,
            "is_valid": self.is_valid,
            "warnings": list(self.warnings),
        }


def build_latin_hypercube_design(
    factors: Sequence[DesignFactor],
    *,
    n_samples: int,
    seed: int = 0,
    generated_utc: str | None = None,
) -> SurrogateDesign:
    """Build a Latin-hypercube design over continuous factors."""

    if not factors:
        raise HydrologySurrogateError("At least one design factor is required.")
    if n_samples <= 0:
        raise HydrologySurrogateError("n_samples must be positive.")
    names = [factor.name for factor in factors]
    if len(set(names)) != len(names):
        raise HydrologySurrogateError("Design factor names must be unique.")
    rng = np.random.default_rng(seed)
    strata = np.arange(n_samples)
    columns: dict[str, np.ndarray] = {}
    for factor in factors:
        shuffled = rng.permutation(strata)
        unit = (shuffled + rng.random(n_samples)) / n_samples
        columns[factor.name] = factor.low + unit * (factor.high - factor.low)
    points = tuple(
        DesignPoint(
            features={
                factor.name: float(columns[factor.name][index]) for factor in factors
            }
        )
        for index in range(n_samples)
    )
    timestamp = generated_utc or _now()
    design_id = _design_id(factors, points, seed)
    return SurrogateDesign(
        design_id=design_id,
        generated_utc=timestamp,
        factors=tuple(factors),
        points=points,
        seed=seed,
    )


def attach_targets(
    design: SurrogateDesign,
    targets: Sequence[float],
    *,
    target_name: str = DEFAULT_SURROGATE_TARGET,
    source: str = "",
) -> SurrogateDataset:
    """Attach process-model targets to a design."""

    if len(targets) != len(design.points):
        raise HydrologySurrogateError("Targets must match the number of design points.")
    feature_names = tuple(factor.name for factor in design.factors)
    samples = tuple(
        SurrogateSample(features=point.features, target=float(target))
        for point, target in zip(design.points, targets, strict=False)
    )
    return SurrogateDataset(
        feature_names=feature_names,
        target_name=target_name,
        samples=samples,
        source=source,
    )


def train_validation_split(
    dataset: SurrogateDataset,
    *,
    validation_fraction: float = 0.2,
    seed: int = 0,
) -> tuple[SurrogateDataset, SurrogateDataset]:
    """Split a dataset into deterministic train/validation subsets."""

    if not 0 < validation_fraction < 1:
        raise HydrologySurrogateError("validation_fraction must be between 0 and 1.")
    if len(dataset.samples) < 3:
        raise HydrologySurrogateError(
            "At least three samples are required for a split."
        )
    rng = np.random.default_rng(seed)
    indices = rng.permutation(len(dataset.samples))
    validation_count = max(1, round(len(dataset.samples) * validation_fraction))
    validation_indices = {int(index) for index in indices[:validation_count]}
    train = tuple(
        sample
        for index, sample in enumerate(dataset.samples)
        if index not in validation_indices
    )
    validation = tuple(
        sample
        for index, sample in enumerate(dataset.samples)
        if index in validation_indices
    )
    if not train or not validation:
        raise HydrologySurrogateError("Split must leave both subsets non-empty.")
    return (
        SurrogateDataset(
            feature_names=dataset.feature_names,
            target_name=dataset.target_name,
            samples=train,
            source=dataset.source,
        ),
        SurrogateDataset(
            feature_names=dataset.feature_names,
            target_name=dataset.target_name,
            samples=validation,
            source=dataset.source,
        ),
    )


def fit_surrogate(
    dataset: SurrogateDataset,
    *,
    family: str = "linear",
    ridge: float = 1e-6,
    length_scale: float | None = None,
    noise: float = 1e-6,
) -> SurrogateModel:
    """Fit one of the dependency-free surrogate families."""

    if family not in HYDROLOGY_SURROGATE_FAMILIES:
        raise HydrologySurrogateError(
            f"Unsupported surrogate family {family!r}; expected "
            + ", ".join(HYDROLOGY_SURROGATE_FAMILIES)
            + "."
        )
    matrix, targets, mean, scale, domain = _prepare_training(dataset)
    if family == "linear":
        return _fit_linear(dataset, matrix, targets, mean, scale, domain, ridge=ridge)
    return _fit_gp(
        dataset,
        matrix,
        targets,
        mean,
        scale,
        domain,
        length_scale=length_scale,
        noise=noise,
    )


def evaluate_surrogate(
    model: SurrogateModel,
    dataset: SurrogateDataset,
    *,
    refuse_out_of_domain: bool = True,
) -> SurrogateValidation:
    """Evaluate a surrogate against held-out samples."""

    errors: list[float] = []
    absolute_errors: list[float] = []
    covered = 0
    widths: list[float] = []
    refused = 0
    targets: list[float] = []
    for sample in dataset.samples:
        applicability = model.applicability_domain.check(sample.features)
        if not applicability.inside:
            refused += 1
            if refuse_out_of_domain:
                continue
        prediction = model.predict(
            sample.features,
            allow_extrapolation=not refuse_out_of_domain,
        )
        lower, upper = model.predict_interval(
            sample.features,
            allow_extrapolation=not refuse_out_of_domain,
        )
        errors.append(prediction - sample.target)
        absolute_errors.append(abs(prediction - sample.target))
        widths.append(upper - lower)
        targets.append(sample.target)
        if lower <= sample.target <= upper:
            covered += 1
    accepted = len(errors)
    warnings: list[str] = []
    if refused:
        warnings.append(
            f"{refused} evaluation samples were refused by the applicability domain."
        )
    if accepted == 0:
        warnings.append("No evaluation samples were accepted.")
    rmse = (
        math.sqrt(sum(error * error for error in errors) / accepted)
        if accepted
        else None
    )
    mae = sum(absolute_errors) / accepted if accepted else None
    r2 = _r2(targets, errors) if accepted else None
    coverage = covered / accepted if accepted else None
    mean_width = sum(widths) / accepted if accepted else None
    if coverage is not None and coverage < 0.8:
        warnings.append(
            f"95% interval coverage is only {coverage:.2f}; review uncertainty."
        )
    return SurrogateValidation(
        model_family=model.family,
        evaluation_size=len(dataset.samples),
        accepted_count=accepted,
        refused_count=refused,
        rmse=rmse,
        mae=mae,
        r2=r2,
        coverage_95=coverage,
        mean_interval_width=mean_width,
        fold_count=1,
        is_valid=accepted > 0 and rmse is not None,
        warnings=tuple(warnings),
    )


def cross_validate_surrogate(
    dataset: SurrogateDataset,
    *,
    family: str = "linear",
    folds: int = 5,
    seed: int = 0,
    ridge: float = 1e-6,
    length_scale: float | None = None,
    noise: float = 1e-6,
) -> SurrogateValidation:
    """Run deterministic k-fold cross-validation for one surrogate family."""

    if folds < 2 or folds > len(dataset.samples):
        raise HydrologySurrogateError("folds must be between 2 and sample count.")
    rng = np.random.default_rng(seed)
    indices = rng.permutation(len(dataset.samples))
    fold_indices = np.array_split(indices, folds)
    errors: list[float] = []
    absolute_errors: list[float] = []
    covered = 0
    widths: list[float] = []
    targets: list[float] = []
    refused = 0
    for fold in fold_indices:
        validation_set = {int(index) for index in fold}
        train_samples = tuple(
            sample
            for index, sample in enumerate(dataset.samples)
            if index not in validation_set
        )
        validation_samples = tuple(
            sample
            for index, sample in enumerate(dataset.samples)
            if index in validation_set
        )
        train_dataset = SurrogateDataset(
            feature_names=dataset.feature_names,
            target_name=dataset.target_name,
            samples=train_samples,
            source=dataset.source,
        )
        model = fit_surrogate(
            train_dataset,
            family=family,
            ridge=ridge,
            length_scale=length_scale,
            noise=noise,
        )
        for sample in validation_samples:
            applicability = model.applicability_domain.check(sample.features)
            if not applicability.inside:
                refused += 1
                continue
            prediction = model.predict(sample.features)
            lower, upper = model.predict_interval(sample.features)
            errors.append(prediction - sample.target)
            absolute_errors.append(abs(prediction - sample.target))
            widths.append(upper - lower)
            targets.append(sample.target)
            if lower <= sample.target <= upper:
                covered += 1
    accepted = len(errors)
    warnings: list[str] = []
    if refused:
        warnings.append(
            f"{refused} held-out samples were refused by the applicability domain."
        )
    if accepted == 0:
        warnings.append("No held-out samples were accepted.")
    return SurrogateValidation(
        model_family=family,
        evaluation_size=len(dataset.samples),
        accepted_count=accepted,
        refused_count=refused,
        rmse=(
            math.sqrt(sum(error * error for error in errors) / accepted)
            if accepted
            else None
        ),
        mae=(sum(absolute_errors) / accepted if accepted else None),
        r2=_r2(targets, errors) if accepted else None,
        coverage_95=(covered / accepted if accepted else None),
        mean_interval_width=(sum(widths) / accepted if accepted else None),
        fold_count=folds,
        is_valid=accepted > 0,
        warnings=tuple(warnings),
    )


def save_surrogate(model: SurrogateModel, path: Path) -> Path:
    """Save a surrogate model as JSON."""

    resolved = path.expanduser().resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(
        json.dumps(model.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return resolved


def load_surrogate(path: Path) -> SurrogateModel:
    """Load a surrogate model from JSON."""

    resolved = path.expanduser().resolve()
    payload = _read_json_object(resolved, context="surrogate model")
    family = str(payload.get("family", ""))
    if family == "linear":
        return LinearSurrogate.from_dict(payload)
    if family == "gp":
        return GaussianProcessSurrogate.from_dict(payload)
    raise HydrologySurrogateError(f"Unsupported surrogate family {family!r}.")


def _prepare_training(
    dataset: SurrogateDataset,
) -> tuple[
    np.ndarray, np.ndarray, dict[str, float], dict[str, float], ApplicabilityDomain
]:
    matrix = np.asarray(
        [
            [sample.features[name] for name in dataset.feature_names]
            for sample in dataset.samples
        ],
        dtype=float,
    )
    targets = np.asarray([sample.target for sample in dataset.samples], dtype=float)
    mean = np.mean(matrix, axis=0)
    scale = np.std(matrix, axis=0)
    scale = np.where(scale > 0, scale, 1.0)
    mean_values = {
        name: float(value)
        for name, value in zip(dataset.feature_names, mean, strict=False)
    }
    scale_values = {
        name: float(value)
        for name, value in zip(dataset.feature_names, scale, strict=False)
    }
    standardized = (matrix - mean) / scale
    distances = np.sqrt(np.sum(standardized**2, axis=1))
    domain = ApplicabilityDomain(
        feature_names=dataset.feature_names,
        min_values={
            name: float(value)
            for name, value in zip(
                dataset.feature_names, np.min(matrix, axis=0), strict=False
            )
        },
        max_values={
            name: float(value)
            for name, value in zip(
                dataset.feature_names, np.max(matrix, axis=0), strict=False
            )
        },
        mean_values=mean_values,
        scale_values=scale_values,
        max_distance=float(np.max(distances) * 1.25),
    )
    return matrix, targets, mean_values, scale_values, domain


def _fit_linear(
    dataset: SurrogateDataset,
    matrix: np.ndarray,
    targets: np.ndarray,
    mean: dict[str, float],
    scale: dict[str, float],
    domain: ApplicabilityDomain,
    *,
    ridge: float,
) -> LinearSurrogate:
    standardized = np.column_stack(
        [
            (matrix[:, index] - mean[name]) / scale[name]
            for index, name in enumerate(dataset.feature_names)
        ]
    )
    design = np.column_stack([np.ones(len(standardized)), standardized])
    penalty = ridge * np.eye(design.shape[1])
    penalty[0, 0] = 0.0
    coefficients = np.linalg.solve(
        design.T @ design + penalty,
        design.T @ targets,
    )
    residuals = targets - design @ coefficients
    degrees = len(targets) - design.shape[1]
    warnings: list[str] = []
    if degrees > 0:
        residual_sigma = float(math.sqrt(float(np.sum(residuals**2)) / degrees))
    else:
        residual_sigma = 0.0
        warnings.append("Too few samples for a residual uncertainty estimate.")
    return LinearSurrogate(
        feature_names=dataset.feature_names,
        mean_values=mean,
        scale_values=scale,
        coefficients=tuple(float(value) for value in coefficients),
        residual_sigma=residual_sigma,
        applicability_domain=domain,
        warnings=tuple(warnings),
    )


def _fit_gp(
    dataset: SurrogateDataset,
    matrix: np.ndarray,
    targets: np.ndarray,
    mean: dict[str, float],
    scale: dict[str, float],
    domain: ApplicabilityDomain,
    *,
    length_scale: float | None,
    noise: float,
) -> GaussianProcessSurrogate:
    standardized = np.column_stack(
        [
            (matrix[:, index] - mean[name]) / scale[name]
            for index, name in enumerate(dataset.feature_names)
        ]
    )
    y_mean = float(np.mean(targets))
    y_scale = float(np.std(targets))
    if y_scale <= 0:
        y_scale = 1.0
    centered = (targets - y_mean) / y_scale
    if length_scale is None:
        squared = _squared_distances(standardized)
        off_diagonal = squared[~np.eye(len(standardized), dtype=bool)]
        length_scale = (
            float(math.sqrt(float(np.median(off_diagonal))))
            if off_diagonal.size
            else 1.0
        )
        if not math.isfinite(length_scale) or length_scale <= 0:
            length_scale = 1.0
    kernel = np.exp(
        -0.5 * _squared_distances(standardized) / (length_scale**2)
    ) + noise * np.eye(len(standardized))
    jitter = 0.0
    warnings: list[str] = []
    for _ in range(8):
        try:
            cholesky = np.linalg.cholesky(kernel + jitter * np.eye(len(kernel)))
            alpha = np.linalg.solve(
                cholesky.T,
                np.linalg.solve(cholesky, centered),
            )
            inverse = np.linalg.inv(kernel + jitter * np.eye(len(kernel)))
            break
        except np.linalg.LinAlgError:
            jitter = max(1e-8, jitter * 10 if jitter else 1e-8)
    else:
        raise HydrologySurrogateError(
            "Gaussian-process kernel is not positive definite."
        )
    if jitter:
        warnings.append(f"Kernel jitter {jitter:g} was required for stability.")
    return GaussianProcessSurrogate(
        feature_names=dataset.feature_names,
        mean_values=mean,
        scale_values=scale,
        train_standardized=tuple(
            tuple(float(value) for value in row) for row in standardized
        ),
        alpha=tuple(float(value) for value in alpha),
        kernel_inverse=tuple(tuple(float(value) for value in row) for row in inverse),
        y_mean=y_mean,
        y_scale=y_scale,
        length_scale=float(length_scale),
        noise=float(noise),
        applicability_domain=domain,
        warnings=tuple(warnings),
    )


def _squared_distances(matrix: np.ndarray) -> np.ndarray:
    squared = (
        np.sum(matrix**2, axis=1)[:, None]
        + np.sum(matrix**2, axis=1)[None, :]
        - 2.0 * matrix @ matrix.T
    )
    return np.maximum(squared, 0.0)


def _feature_vector(
    features: Mapping[str, float],
    feature_names: tuple[str, ...],
) -> dict[str, float]:
    missing = [name for name in feature_names if name not in features]
    if missing:
        raise HydrologySurrogateError("Missing features: " + ", ".join(sorted(missing)))
    vector = {name: float(features[name]) for name in feature_names}
    if any(not math.isfinite(value) for value in vector.values()):
        raise HydrologySurrogateError("Feature values must be finite.")
    return vector


def _r2(targets: Sequence[float], errors: Sequence[float]) -> float | None:
    if not targets:
        return None
    mean = sum(targets) / len(targets)
    total = sum((target - mean) ** 2 for target in targets)
    if total <= 0:
        return None
    residual = sum(error * error for error in errors)
    return 1.0 - residual / total


def _design_id(
    factors: Sequence[DesignFactor],
    points: Sequence[DesignPoint],
    seed: int,
) -> str:
    material = {
        "factors": [factor.to_dict() for factor in factors],
        "points": [point.to_dict() for point in points],
        "seed": seed,
    }
    digest = hashlib.sha256(_canonical_json_bytes(material)).hexdigest()
    return f"hydro-design-{digest[:16]}"


def _strings(value: object, name: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise HydrologySurrogateError(f"{name} must be a list.")
    return tuple(str(item) for item in value)


def _list(value: object, name: str) -> list[object]:
    if not isinstance(value, list):
        raise HydrologySurrogateError(f"{name} must be a list.")
    return value


def _matrix(value: object, name: str) -> tuple[tuple[float, ...], ...]:
    if not isinstance(value, list):
        raise HydrologySurrogateError(f"{name} must be a list.")
    rows: list[tuple[float, ...]] = []
    for row in value:
        if not isinstance(row, list):
            raise HydrologySurrogateError(f"{name} rows must be lists.")
        rows.append(tuple(float(item) for item in row))
    return tuple(rows)


def _float_mapping(value: object, name: str) -> dict[str, float]:
    if not isinstance(value, Mapping):
        raise HydrologySurrogateError(f"{name} must be an object.")
    return {str(key): float(item) for key, item in value.items()}


def _mapping(value: object, name: str) -> dict[str, object]:
    if not isinstance(value, Mapping):
        raise HydrologySurrogateError(f"{name} must be an object.")
    return {str(key): item for key, item in value.items()}


def _read_json_object(path: Path, *, context: str) -> dict[str, object]:
    try:
        payload: object = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise HydrologySurrogateError(
            f"Unable to read {context}: {path}: {exc}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise HydrologySurrogateError(
            f"Invalid JSON in {context}: {path}: {exc}"
        ) from exc
    if not isinstance(payload, Mapping):
        raise HydrologySurrogateError(f"{context} must be a JSON object: {path}")
    return {str(key): value for key, value in payload.items()}


def _canonical_json_bytes(payload: object) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _now() -> str:
    return datetime.now(UTC).isoformat()
