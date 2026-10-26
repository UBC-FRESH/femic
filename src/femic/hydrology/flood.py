"""Stochastic flood-frequency response surfaces.

P114.5 provides screening/decision-support frequency fits, paired-watershed
response ratios, and nonstationary GEV response surfaces. It does not replace
hydrologist review, public-gauge calibration, or regulatory flood analysis.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path

import numpy as np
from scipy import optimize, stats  # type: ignore[import-untyped]

HYDROLOGY_FLOOD_FREQUENCY_SCHEMA_VERSION = "femic.hydrology.flood_frequency.v1"
HYDROLOGY_FLOOD_RESPONSE_SCHEMA_VERSION = "femic.hydrology.flood_response.v1"
DEFAULT_RETURN_PERIODS: tuple[float, ...] = (2.0, 5.0, 10.0, 25.0, 50.0, 100.0)
DEFAULT_BOOTSTRAP_SAMPLES = 200
MIN_FIT_SAMPLES = 5
MIN_RECOMMENDED_SAMPLES = 10
GEV_SHAPE_BOUNDS: tuple[float, float] = (-0.5, 0.5)
GEV_MIN_SCALE = 1e-9


class HydrologyFloodError(RuntimeError):
    """Raised when a flood sample, fit, or response surface is invalid."""


@dataclass(frozen=True)
class FloodEvent:
    """One observed peak-flow event."""

    event_date: date
    value: float

    def to_dict(self) -> dict[str, object]:
        """Return the event as a JSON-serializable mapping."""

        return {"event_date": self.event_date.isoformat(), "value": self.value}


@dataclass(frozen=True)
class FloodSample:
    """Annual-maximum peak-flow sample for one station."""

    station_id: str
    years: tuple[int, ...]
    values: tuple[float, ...]
    regime: str = "unknown"

    def __post_init__(self) -> None:
        if len(self.years) != len(self.values):
            raise HydrologyFloodError("Flood years and values must have equal length.")
        if not self.values:
            raise HydrologyFloodError("Flood sample must contain at least one value.")
        if len(set(self.years)) != len(self.years):
            raise HydrologyFloodError("Flood sample years must be unique.")
        if any(not math.isfinite(value) or value <= 0 for value in self.values):
            raise HydrologyFloodError("Flood values must be positive and finite.")

    def to_dict(self) -> dict[str, object]:
        """Return the sample as a JSON-serializable mapping."""

        return {
            "station_id": self.station_id,
            "years": list(self.years),
            "values": list(self.values),
            "regime": self.regime,
        }


@dataclass(frozen=True)
class PotSample:
    """Declustered peaks-over-threshold sample."""

    station_id: str
    events: tuple[FloodEvent, ...]
    threshold: float
    min_separation_days: int
    record_start_year: int
    record_end_year: int
    regime: str = "unknown"

    @property
    def values(self) -> tuple[float, ...]:
        """Return the declustered peak values."""

        return tuple(event.value for event in self.events)

    @property
    def annual_rate(self) -> float:
        """Return the mean number of selected peaks per year."""

        years = self.record_end_year - self.record_start_year + 1
        return len(self.events) / years

    def to_dict(self) -> dict[str, object]:
        """Return the sample as a JSON-serializable mapping."""

        return {
            "station_id": self.station_id,
            "events": [event.to_dict() for event in self.events],
            "threshold": self.threshold,
            "min_separation_days": self.min_separation_days,
            "record_start_year": self.record_start_year,
            "record_end_year": self.record_end_year,
            "annual_rate": self.annual_rate,
            "regime": self.regime,
        }


@dataclass(frozen=True)
class FloodFrequencyFit:
    """Stationary flood-frequency fit and return-level interval."""

    station_id: str
    method: str
    return_periods: tuple[float, ...]
    quantiles: tuple[float, ...]
    lower_bounds: tuple[float | None, ...]
    upper_bounds: tuple[float | None, ...]
    parameters: dict[str, object]
    log_likelihood: float
    aic: float
    sample_size: int
    bootstrap_samples: int
    warnings: tuple[str, ...] = ()
    caveats: tuple[str, ...] = ()
    schema_version: str = HYDROLOGY_FLOOD_FREQUENCY_SCHEMA_VERSION

    def to_dict(self) -> dict[str, object]:
        """Return the fit as a JSON-serializable mapping."""

        return {
            "schema_version": self.schema_version,
            "station_id": self.station_id,
            "method": self.method,
            "return_periods": list(self.return_periods),
            "quantiles": list(self.quantiles),
            "lower_bounds": list(self.lower_bounds),
            "upper_bounds": list(self.upper_bounds),
            "parameters": self.parameters,
            "log_likelihood": self.log_likelihood,
            "aic": self.aic,
            "sample_size": self.sample_size,
            "bootstrap_samples": self.bootstrap_samples,
            "warnings": list(self.warnings),
            "caveats": list(self.caveats),
        }


@dataclass(frozen=True)
class FrequencyPairingResult:
    """Baseline/treatment frequency pairing and return-period ratios."""

    baseline: FloodFrequencyFit
    treatment: FloodFrequencyFit
    return_periods: tuple[float, ...]
    ratios: tuple[float, ...]
    ratio_lower: tuple[float | None, ...]
    ratio_upper: tuple[float | None, ...]
    differences: tuple[float, ...]
    warnings: tuple[str, ...] = ()
    caveats: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        """Return the pairing as a JSON-serializable mapping."""

        return {
            "baseline": self.baseline.to_dict(),
            "treatment": self.treatment.to_dict(),
            "return_periods": list(self.return_periods),
            "ratios": list(self.ratios),
            "ratio_lower": list(self.ratio_lower),
            "ratio_upper": list(self.ratio_upper),
            "differences": list(self.differences),
            "warnings": list(self.warnings),
            "caveats": list(self.caveats),
        }


@dataclass(frozen=True)
class NonstationaryGevFit:
    """Nonstationary GEV with a linear location model in covariates."""

    station_id: str
    covariate_names: tuple[str, ...]
    coefficients: dict[str, float]
    log_likelihood: float
    aic: float
    sample_size: int
    return_periods: tuple[float, ...]
    baseline_covariates: dict[str, float]
    baseline_quantiles: tuple[float, ...]
    warnings: tuple[str, ...] = ()
    caveats: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        """Return the fit as a JSON-serializable mapping."""

        return {
            "station_id": self.station_id,
            "covariate_names": list(self.covariate_names),
            "coefficients": self.coefficients,
            "log_likelihood": self.log_likelihood,
            "aic": self.aic,
            "sample_size": self.sample_size,
            "return_periods": list(self.return_periods),
            "baseline_covariates": self.baseline_covariates,
            "baseline_quantiles": list(self.baseline_quantiles),
            "warnings": list(self.warnings),
            "caveats": list(self.caveats),
        }


@dataclass(frozen=True)
class FloodScenario:
    """One covariate scenario for a response surface."""

    name: str
    covariates: dict[str, float]

    def to_dict(self) -> dict[str, object]:
        """Return the scenario as a JSON-serializable mapping."""

        return {"name": self.name, "covariates": self.covariates}


@dataclass(frozen=True)
class FloodResponseSurfaceRow:
    """One scenario/return-period response row."""

    scenario: str
    return_period: float
    quantile: float
    baseline_quantile: float
    ratio: float
    difference: float

    def to_dict(self) -> dict[str, object]:
        """Return the row as a JSON-serializable mapping."""

        return {
            "scenario": self.scenario,
            "return_period": self.return_period,
            "quantile": self.quantile,
            "baseline_quantile": self.baseline_quantile,
            "ratio": self.ratio,
            "difference": self.difference,
        }


@dataclass(frozen=True)
class FloodResponseSurface:
    """Return-period-specific response surface."""

    surface_id: str
    generated_utc: str
    station_id: str
    method: str
    baseline_name: str
    return_periods: tuple[float, ...]
    scenarios: tuple[FloodScenario, ...]
    rows: tuple[FloodResponseSurfaceRow, ...]
    diagnostics: dict[str, object] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()
    caveats: tuple[str, ...] = ()
    schema_version: str = HYDROLOGY_FLOOD_RESPONSE_SCHEMA_VERSION

    def to_dict(self) -> dict[str, object]:
        """Return the surface as a JSON-serializable mapping."""

        return {
            "schema_version": self.schema_version,
            "surface_id": self.surface_id,
            "generated_utc": self.generated_utc,
            "station_id": self.station_id,
            "method": self.method,
            "baseline_name": self.baseline_name,
            "return_periods": list(self.return_periods),
            "scenarios": [scenario.to_dict() for scenario in self.scenarios],
            "summary": {"row_count": len(self.rows)},
            "rows": [row.to_dict() for row in self.rows],
            "diagnostics": self.diagnostics,
            "warnings": list(self.warnings),
            "caveats": list(self.caveats),
        }


@dataclass(frozen=True)
class FloodBenchmark:
    """Published or reviewed return-period ratio envelope."""

    name: str
    return_periods: tuple[float, ...]
    lower_ratio: tuple[float, ...]
    upper_ratio: tuple[float, ...]
    source: str = ""
    notes: str = ""

    def to_dict(self) -> dict[str, object]:
        """Return the benchmark as a JSON-serializable mapping."""

        return {
            "name": self.name,
            "return_periods": list(self.return_periods),
            "lower_ratio": list(self.lower_ratio),
            "upper_ratio": list(self.upper_ratio),
            "source": self.source,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class FloodBenchmarkRow:
    """One benchmark comparison row."""

    return_period: float
    observed_ratio: float
    lower_ratio: float
    upper_ratio: float
    within_envelope: bool

    def to_dict(self) -> dict[str, object]:
        """Return the row as a JSON-serializable mapping."""

        return {
            "return_period": self.return_period,
            "observed_ratio": self.observed_ratio,
            "lower_ratio": self.lower_ratio,
            "upper_ratio": self.upper_ratio,
            "within_envelope": self.within_envelope,
        }


@dataclass(frozen=True)
class FloodBenchmarkCheck:
    """Benchmark comparison outcome."""

    benchmark_name: str
    is_pass: bool
    rows: tuple[FloodBenchmarkRow, ...]
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        """Return the check as a JSON-serializable mapping."""

        return {
            "benchmark_name": self.benchmark_name,
            "is_pass": self.is_pass,
            "rows": [row.to_dict() for row in self.rows],
            "warnings": list(self.warnings),
        }


def extract_annual_maxima(
    events: Sequence[FloodEvent],
    *,
    station_id: str,
    regime: str = "unknown",
) -> FloodSample:
    """Extract one annual maximum per calendar year from event records."""

    if not events:
        raise HydrologyFloodError("At least one flood event is required.")
    by_year: dict[int, float] = {}
    for event in events:
        if not math.isfinite(event.value) or event.value <= 0:
            raise HydrologyFloodError("Flood event values must be positive and finite.")
        year = event.event_date.year
        by_year[year] = max(by_year.get(year, 0.0), event.value)
    years = tuple(sorted(by_year))
    return FloodSample(
        station_id=station_id,
        years=years,
        values=tuple(by_year[year] for year in years),
        regime=regime,
    )


def extract_peaks_over_threshold(
    events: Sequence[FloodEvent],
    *,
    threshold: float,
    min_separation_days: int,
    station_id: str,
    regime: str = "unknown",
) -> PotSample:
    """Extract declustered peaks over a threshold.

    Peaks are selected in descending magnitude with a minimum day separation.
    The record start/end years come from all supplied events, not only the
    selected peaks.
    """

    if not events:
        raise HydrologyFloodError("At least one flood event is required.")
    if not math.isfinite(threshold):
        raise HydrologyFloodError("POT threshold must be finite.")
    if min_separation_days < 0:
        raise HydrologyFloodError("POT separation must be non-negative.")
    ordered = sorted(events, key=lambda event: event.event_date)
    for event in ordered:
        if not math.isfinite(event.value) or event.value <= 0:
            raise HydrologyFloodError("Flood event values must be positive and finite.")
    selected: list[FloodEvent] = []
    for event in sorted(
        (event for event in ordered if event.value > threshold),
        key=lambda event: event.value,
        reverse=True,
    ):
        if all(
            abs((event.event_date - kept.event_date).days) >= min_separation_days
            for kept in selected
        ):
            selected.append(event)
    selected.sort(key=lambda event: event.event_date)
    return PotSample(
        station_id=station_id,
        events=tuple(selected),
        threshold=threshold,
        min_separation_days=min_separation_days,
        record_start_year=ordered[0].event_date.year,
        record_end_year=ordered[-1].event_date.year,
        regime=regime,
    )


def fit_flood_frequency(
    sample: FloodSample,
    *,
    method: str = "gev",
    return_periods: Sequence[float] = DEFAULT_RETURN_PERIODS,
    bootstrap_samples: int = DEFAULT_BOOTSTRAP_SAMPLES,
    seed: int = 0,
) -> FloodFrequencyFit:
    """Fit a stationary GEV or LP3 frequency distribution.

    Return periods are in years and use annual-maximum non-exceedance
    probability ``1 - 1/T``. Bootstrap intervals are percentile intervals.
    """

    _validate_method(method)
    periods = _validate_return_periods(return_periods)
    if len(sample.values) < MIN_FIT_SAMPLES:
        raise HydrologyFloodError(
            f"At least {MIN_FIT_SAMPLES} annual maxima are required for a fit."
        )
    warnings: list[str] = []
    if len(sample.values) < MIN_RECOMMENDED_SAMPLES:
        warnings.append(
            f"Only {len(sample.values)} annual maxima are available; "
            f"{MIN_RECOMMENDED_SAMPLES}+ is recommended."
        )
    parameters, quantiles, log_likelihood = _fit_stationary(
        sample.values,
        method=method,
        return_periods=periods,
    )
    if parameters.get("fit_strategy") == "constrained":
        warnings.append(
            "GEV shape was constrained to the screening bounds "
            f"{GEV_SHAPE_BOUNDS}; inspect the fit before tail use."
        )
    lower, upper, effective_bootstrap = _bootstrap_bounds(
        sample.values,
        method=method,
        return_periods=periods,
        bootstrap_samples=bootstrap_samples,
        seed=seed,
    )
    if effective_bootstrap < bootstrap_samples:
        warnings.append(
            f"{bootstrap_samples - effective_bootstrap} bootstrap fits failed and "
            "were skipped."
        )
    return FloodFrequencyFit(
        station_id=sample.station_id,
        method=method,
        return_periods=periods,
        quantiles=quantiles,
        lower_bounds=lower,
        upper_bounds=upper,
        parameters=parameters,
        log_likelihood=log_likelihood,
        aic=2.0 * 3.0 - 2.0 * log_likelihood,
        sample_size=len(sample.values),
        bootstrap_samples=effective_bootstrap,
        warnings=tuple(warnings),
        caveats=_frequency_caveats(),
    )


def fit_pot_frequency(
    sample: PotSample,
    *,
    return_periods: Sequence[float] = DEFAULT_RETURN_PERIODS,
    bootstrap_samples: int = DEFAULT_BOOTSTRAP_SAMPLES,
    seed: int = 0,
) -> FloodFrequencyFit:
    """Fit a Poisson-GPD peaks-over-threshold frequency model."""

    periods = _validate_return_periods(return_periods)
    values = sample.values
    if len(values) < MIN_FIT_SAMPLES:
        raise HydrologyFloodError(
            f"At least {MIN_FIT_SAMPLES} POT peaks are required for a fit."
        )
    annual_rate = sample.annual_rate
    if annual_rate <= 0:
        raise HydrologyFloodError("POT annual rate must be positive.")
    excesses = np.asarray([value - sample.threshold for value in values], dtype=float)
    if np.any(excesses <= 0):
        raise HydrologyFloodError("POT peaks must exceed the threshold.")
    shape, _, scale = stats.genpareto.fit(excesses, floc=0.0)
    parameters: dict[str, object] = {
        "threshold": sample.threshold,
        "annual_rate": annual_rate,
        "gpd_shape": float(shape),
        "gpd_scale": float(scale),
    }
    quantiles = _pot_quantiles(
        sample.threshold,
        annual_rate,
        float(shape),
        float(scale),
        periods,
    )
    log_likelihood = float(
        np.sum(stats.genpareto.logpdf(excesses, shape, loc=0.0, scale=scale))
    )
    lower, upper, effective_bootstrap = _bootstrap_pot_bounds(
        sample,
        return_periods=periods,
        bootstrap_samples=bootstrap_samples,
        seed=seed,
    )
    warnings: list[str] = []
    if effective_bootstrap < bootstrap_samples:
        warnings.append(
            f"{bootstrap_samples - effective_bootstrap} bootstrap fits failed and "
            "were skipped."
        )
    return FloodFrequencyFit(
        station_id=sample.station_id,
        method="gpd",
        return_periods=periods,
        quantiles=quantiles,
        lower_bounds=lower,
        upper_bounds=upper,
        parameters=parameters,
        log_likelihood=log_likelihood,
        aic=2.0 * 2.0 - 2.0 * log_likelihood,
        sample_size=len(values),
        bootstrap_samples=effective_bootstrap,
        warnings=tuple(warnings),
        caveats=_frequency_caveats(),
    )


def paired_frequency_response(
    baseline: FloodSample,
    treatment: FloodSample,
    *,
    method: str = "gev",
    return_periods: Sequence[float] = DEFAULT_RETURN_PERIODS,
    bootstrap_samples: int = DEFAULT_BOOTSTRAP_SAMPLES,
    seed: int = 0,
) -> FrequencyPairingResult:
    """Compare baseline and treatment return levels by return period."""

    _validate_method(method)
    periods = _validate_return_periods(return_periods)
    baseline_fit = fit_flood_frequency(
        baseline,
        method=method,
        return_periods=periods,
        bootstrap_samples=bootstrap_samples,
        seed=seed,
    )
    treatment_fit = fit_flood_frequency(
        treatment,
        method=method,
        return_periods=periods,
        bootstrap_samples=bootstrap_samples,
        seed=seed + 1,
    )
    ratios = tuple(
        treatment_value / baseline_value
        for baseline_value, treatment_value in zip(
            baseline_fit.quantiles,
            treatment_fit.quantiles,
            strict=False,
        )
    )
    differences = tuple(
        treatment_value - baseline_value
        for baseline_value, treatment_value in zip(
            baseline_fit.quantiles,
            treatment_fit.quantiles,
            strict=False,
        )
    )
    ratio_lower, ratio_upper, _ = _bootstrap_ratio_bounds(
        baseline.values,
        treatment.values,
        method=method,
        return_periods=periods,
        bootstrap_samples=bootstrap_samples,
        seed=seed,
    )
    return FrequencyPairingResult(
        baseline=baseline_fit,
        treatment=treatment_fit,
        return_periods=periods,
        ratios=ratios,
        ratio_lower=ratio_lower,
        ratio_upper=ratio_upper,
        differences=differences,
        warnings=tuple(set(baseline_fit.warnings) | set(treatment_fit.warnings)),
        caveats=_frequency_caveats(),
    )


def fit_nonstationary_gev(
    sample: FloodSample,
    covariates: Mapping[str, Sequence[float]],
    *,
    return_periods: Sequence[float] = DEFAULT_RETURN_PERIODS,
    baseline_covariates: Mapping[str, float] | None = None,
) -> NonstationaryGevFit:
    """Fit a GEV whose location is linear in time-varying covariates."""

    periods = _validate_return_periods(return_periods)
    if len(sample.values) < MIN_FIT_SAMPLES:
        raise HydrologyFloodError(
            f"At least {MIN_FIT_SAMPLES} annual maxima are required for a fit."
        )
    names = tuple(covariates)
    if not names:
        raise HydrologyFloodError("At least one covariate is required.")
    matrix = np.column_stack(
        [
            _as_covariate(covariates[name], expected=len(sample.values), name=name)
            for name in names
        ]
    )
    values = np.asarray(sample.values, dtype=float)
    stationary_shape, stationary_loc, stationary_scale = stats.genextreme.fit(values)
    initial = np.concatenate(
        (
            np.asarray([stationary_loc], dtype=float),
            np.zeros(len(names), dtype=float),
            np.asarray([math.log(float(stationary_scale))], dtype=float),
            np.asarray([float(stationary_shape)], dtype=float),
        )
    )
    bounds = [(None, None)] * (1 + len(names)) + [(-20.0, 20.0)] + [(-0.5, 0.5)]

    def negative_log_likelihood(params: np.ndarray) -> float:
        intercept = float(params[0])
        betas = params[1 : 1 + len(names)]
        sigma = math.exp(float(params[1 + len(names)]))
        shape = float(params[2 + len(names)])
        mu = intercept + matrix @ betas
        log_pdf = stats.genextreme.logpdf(values, shape, loc=mu, scale=sigma)
        if not np.all(np.isfinite(log_pdf)):
            return 1e20
        return float(-np.sum(log_pdf))

    result = optimize.minimize(negative_log_likelihood, initial, bounds=bounds)
    if not result.success:
        raise HydrologyFloodError(f"Nonstationary GEV fit failed: {result.message}")
    params = np.asarray(result.x, dtype=float)
    intercept = float(params[0])
    betas = params[1 : 1 + len(names)]
    log_sigma = float(params[1 + len(names)])
    shape = float(params[2 + len(names)])
    sigma = math.exp(log_sigma)
    coefficients = {
        "intercept": intercept,
        **{name: float(beta) for name, beta in zip(names, betas, strict=False)},
        "log_sigma": log_sigma,
        "shape_scipy": shape,
    }
    baseline = {name: 0.0 for name in names}
    if baseline_covariates is not None:
        unknown = set(baseline_covariates) - set(names)
        if unknown:
            raise HydrologyFloodError(
                "Baseline covariates are not in the model: "
                + ", ".join(sorted(unknown))
                + "."
            )
        baseline.update(
            {name: float(value) for name, value in baseline_covariates.items()}
        )
    baseline_quantiles = _nonstationary_quantiles(
        intercept,
        {name: float(beta) for name, beta in zip(names, betas, strict=False)},
        sigma,
        shape,
        baseline,
        periods,
    )
    return NonstationaryGevFit(
        station_id=sample.station_id,
        covariate_names=names,
        coefficients=coefficients,
        log_likelihood=float(-result.fun),
        aic=2.0 * (2.0 + len(names)) - 2.0 * float(-result.fun),
        sample_size=len(values),
        return_periods=periods,
        baseline_covariates=baseline,
        baseline_quantiles=baseline_quantiles,
        warnings=(),
        caveats=(
            *_frequency_caveats(),
            (
                "Nonstationary coefficients are point estimates; use the P114.7 "
                "surrogate/uncertainty layer for propagation."
            ),
        ),
    )


def predict_nonstationary_quantiles(
    fit: NonstationaryGevFit,
    covariates: Mapping[str, float],
    *,
    return_periods: Sequence[float] = DEFAULT_RETURN_PERIODS,
) -> tuple[float, ...]:
    """Predict return levels for one covariate scenario."""

    periods = _validate_return_periods(return_periods)
    unknown = set(covariates) - set(fit.covariate_names)
    if unknown:
        raise HydrologyFloodError(
            "Scenario covariates are not in the model: "
            + ", ".join(sorted(unknown))
            + "."
        )
    betas = {name: fit.coefficients[name] for name in fit.covariate_names}
    return _nonstationary_quantiles(
        fit.coefficients["intercept"],
        betas,
        math.exp(fit.coefficients["log_sigma"]),
        fit.coefficients["shape_scipy"],
        {name: float(value) for name, value in covariates.items()},
        periods,
    )


def build_response_surface(
    fit: NonstationaryGevFit,
    scenarios: Sequence[FloodScenario],
    *,
    baseline_name: str | None = None,
    generated_utc: str | None = None,
) -> FloodResponseSurface:
    """Build a return-period-specific response surface from scenarios."""

    if not scenarios:
        raise HydrologyFloodError("At least one response scenario is required.")
    scenario_names = {scenario.name for scenario in scenarios}
    if len(scenario_names) != len(scenarios):
        raise HydrologyFloodError("Response scenario names must be unique.")
    baseline = baseline_name or scenarios[0].name
    if baseline not in scenario_names:
        raise HydrologyFloodError(
            f"Baseline scenario {baseline!r} is not in the scenario list."
        )
    baseline_quantiles = predict_nonstationary_quantiles(
        fit,
        _scenario_covariates(scenarios, baseline),
        return_periods=fit.return_periods,
    )
    rows: list[FloodResponseSurfaceRow] = []
    for scenario in scenarios:
        quantiles = predict_nonstationary_quantiles(
            fit,
            scenario.covariates,
            return_periods=fit.return_periods,
        )
        for period, quantile, baseline_quantile in zip(
            fit.return_periods,
            quantiles,
            baseline_quantiles,
            strict=False,
        ):
            rows.append(
                FloodResponseSurfaceRow(
                    scenario=scenario.name,
                    return_period=period,
                    quantile=quantile,
                    baseline_quantile=baseline_quantile,
                    ratio=quantile / baseline_quantile,
                    difference=quantile - baseline_quantile,
                )
            )
    record_rows = tuple(rows)
    surface_id = _surface_id(
        station_id=fit.station_id,
        baseline_name=baseline,
        rows=record_rows,
    )
    return FloodResponseSurface(
        surface_id=surface_id,
        generated_utc=generated_utc or _now(),
        station_id=fit.station_id,
        method="nonstationary_gev",
        baseline_name=baseline,
        return_periods=fit.return_periods,
        scenarios=tuple(scenarios),
        rows=record_rows,
        diagnostics={
            "aic": fit.aic,
            "sample_size": fit.sample_size,
            "coefficients": fit.coefficients,
        },
        warnings=fit.warnings,
        caveats=fit.caveats,
    )


def evaluate_frequency_benchmark(
    pairing: FrequencyPairingResult,
    benchmark: FloodBenchmark,
) -> FloodBenchmarkCheck:
    """Compare paired return-period ratios with a benchmark envelope."""

    if len(benchmark.return_periods) != len(benchmark.lower_ratio):
        raise HydrologyFloodError("Benchmark return periods and lower ratios differ.")
    if len(benchmark.return_periods) != len(benchmark.upper_ratio):
        raise HydrologyFloodError("Benchmark return periods and upper ratios differ.")
    ratio_by_period = {
        period: ratio
        for period, ratio in zip(pairing.return_periods, pairing.ratios, strict=False)
    }
    rows: list[FloodBenchmarkRow] = []
    for period, lower, upper in zip(
        benchmark.return_periods,
        benchmark.lower_ratio,
        benchmark.upper_ratio,
        strict=False,
    ):
        if period not in ratio_by_period:
            raise HydrologyFloodError(
                f"Benchmark return period {period} is missing from the pairing."
            )
        observed = ratio_by_period[period]
        rows.append(
            FloodBenchmarkRow(
                return_period=period,
                observed_ratio=observed,
                lower_ratio=lower,
                upper_ratio=upper,
                within_envelope=lower <= observed <= upper,
            )
        )
    return FloodBenchmarkCheck(
        benchmark_name=benchmark.name,
        is_pass=all(row.within_envelope for row in rows),
        rows=tuple(rows),
        warnings=(),
    )


def write_flood_frequency_report(fit: FloodFrequencyFit, path: Path) -> Path:
    """Write a stationary frequency fit as JSON."""

    return _write_json(fit.to_dict(), path)


def write_response_surface(surface: FloodResponseSurface, path: Path) -> Path:
    """Write a flood response surface as JSON."""

    return _write_json(surface.to_dict(), path)


def _fit_gev(
    values: np.ndarray,
) -> tuple[float, float, float, str]:
    """Fit a GEV, falling back to bounded shape when MLE leaves the screen."""
    try:
        shape, loc, scale = stats.genextreme.fit(values)
        if (
            math.isfinite(float(shape))
            and math.isfinite(float(loc))
            and math.isfinite(float(scale))
            and float(scale) > 0
            and GEV_SHAPE_BOUNDS[0] <= float(shape) <= GEV_SHAPE_BOUNDS[1]
        ):
            return float(shape), float(loc), float(scale), "mle"
    except (FloatingPointError, RuntimeError, ValueError):
        shape = 0.1
        loc = float(np.mean(values))
        scale = float(np.std(values, ddof=1))
    initial_shape = min(max(float(shape), GEV_SHAPE_BOUNDS[0]), GEV_SHAPE_BOUNDS[1])
    initial_loc = float(loc) if math.isfinite(float(loc)) else float(np.mean(values))
    initial_scale = (
        float(scale)
        if math.isfinite(float(scale)) and float(scale) > 0
        else max(float(np.std(values, ddof=1)), GEV_MIN_SCALE)
    )

    def negative_log_likelihood(params: np.ndarray) -> float:
        candidate_shape = float(params[0])
        candidate_loc = float(params[1])
        candidate_scale = math.exp(float(params[2]))
        if candidate_scale <= 0 or not math.isfinite(candidate_scale):
            return 1e100
        log_pdf = stats.genextreme.logpdf(
            values,
            candidate_shape,
            loc=candidate_loc,
            scale=candidate_scale,
        )
        if not np.all(np.isfinite(log_pdf)):
            return 1e100
        return float(-np.sum(log_pdf))

    result = optimize.minimize(
        negative_log_likelihood,
        np.asarray(
            [initial_shape, initial_loc, math.log(initial_scale)],
            dtype=float,
        ),
        method="L-BFGS-B",
        bounds=[
            GEV_SHAPE_BOUNDS,
            (None, None),
            (math.log(GEV_MIN_SCALE), None),
        ],
    )
    if not result.success or not np.all(np.isfinite(result.x)):
        raise HydrologyFloodError(
            "GEV fit failed even with shape bounds; review the sample."
        )
    constrained_shape = float(result.x[0])
    constrained_loc = float(result.x[1])
    constrained_scale = math.exp(float(result.x[2]))
    if not GEV_SHAPE_BOUNDS[0] <= constrained_shape <= GEV_SHAPE_BOUNDS[1]:
        raise HydrologyFloodError("Constrained GEV shape escaped its bounds.")
    return constrained_shape, constrained_loc, constrained_scale, "constrained"


def _fit_stationary(
    values: Sequence[float] | np.ndarray,
    *,
    method: str,
    return_periods: tuple[float, ...],
) -> tuple[dict[str, object], tuple[float, ...], float]:
    array = np.asarray(values, dtype=float)
    probabilities = np.asarray([1.0 - 1.0 / period for period in return_periods])
    if method == "gev":
        shape, loc, scale, strategy = _fit_gev(array)
        quantiles = tuple(
            float(stats.genextreme.ppf(probability, shape, loc=loc, scale=scale))
            for probability in probabilities
        )
        log_likelihood = float(
            np.sum(stats.genextreme.logpdf(array, shape, loc=loc, scale=scale))
        )
        parameters: dict[str, object] = {
            "shape_scipy": float(shape),
            "loc": float(loc),
            "scale": float(scale),
            "fit_strategy": strategy,
            "shape_bounds": list(GEV_SHAPE_BOUNDS),
        }
        return parameters, quantiles, log_likelihood
    log_values = np.log10(array)
    skew, loc, scale = stats.pearson3.fit(log_values)
    quantiles = tuple(
        float(10.0 ** stats.pearson3.ppf(probability, skew, loc=loc, scale=scale))
        for probability in probabilities
    )
    log_likelihood = float(
        np.sum(stats.pearson3.logpdf(log_values, skew, loc=loc, scale=scale))
    )
    lp3_parameters: dict[str, object] = {
        "log10_skew": float(skew),
        "log10_loc": float(loc),
        "log10_scale": float(scale),
    }
    return lp3_parameters, quantiles, log_likelihood


def _bootstrap_bounds(
    values: Sequence[float],
    *,
    method: str,
    return_periods: tuple[float, ...],
    bootstrap_samples: int,
    seed: int,
) -> tuple[tuple[float | None, ...], tuple[float | None, ...], int]:
    if bootstrap_samples <= 0:
        return (
            tuple(None for _ in return_periods),
            tuple(None for _ in return_periods),
            0,
        )
    rng = np.random.default_rng(seed)
    samples: list[tuple[float, ...]] = []
    array = np.asarray(values, dtype=float)
    for _ in range(bootstrap_samples):
        resampled = rng.choice(array, size=array.size, replace=True)
        try:
            _, quantiles, _ = _fit_stationary(
                resampled,
                method=method,
                return_periods=return_periods,
            )
        except (FloatingPointError, HydrologyFloodError, RuntimeError, ValueError):
            continue
        samples.append(quantiles)
    if not samples:
        return (
            tuple(None for _ in return_periods),
            tuple(None for _ in return_periods),
            0,
        )
    matrix = np.asarray(samples, dtype=float)
    lower = tuple(float(value) for value in np.percentile(matrix, 2.5, axis=0))
    upper = tuple(float(value) for value in np.percentile(matrix, 97.5, axis=0))
    return lower, upper, len(samples)


def _bootstrap_pot_bounds(
    sample: PotSample,
    *,
    return_periods: tuple[float, ...],
    bootstrap_samples: int,
    seed: int,
) -> tuple[tuple[float | None, ...], tuple[float | None, ...], int]:
    if bootstrap_samples <= 0:
        return (
            tuple(None for _ in return_periods),
            tuple(None for _ in return_periods),
            0,
        )
    values = np.asarray(sample.values, dtype=float)
    rng = np.random.default_rng(seed)
    samples: list[tuple[float, ...]] = []
    for _ in range(bootstrap_samples):
        resampled = rng.choice(values, size=values.size, replace=True)
        excesses = resampled - sample.threshold
        try:
            shape, _, scale = stats.genpareto.fit(excesses, floc=0.0)
            samples.append(
                _pot_quantiles(
                    sample.threshold,
                    sample.annual_rate,
                    float(shape),
                    float(scale),
                    return_periods,
                )
            )
        except (FloatingPointError, HydrologyFloodError, RuntimeError, ValueError):
            continue
    if not samples:
        return (
            tuple(None for _ in return_periods),
            tuple(None for _ in return_periods),
            0,
        )
    matrix = np.asarray(samples, dtype=float)
    lower = tuple(float(value) for value in np.percentile(matrix, 2.5, axis=0))
    upper = tuple(float(value) for value in np.percentile(matrix, 97.5, axis=0))
    return lower, upper, len(samples)


def _bootstrap_ratio_bounds(
    baseline_values: Sequence[float],
    treatment_values: Sequence[float],
    *,
    method: str,
    return_periods: tuple[float, ...],
    bootstrap_samples: int,
    seed: int,
) -> tuple[tuple[float | None, ...], tuple[float | None, ...], int]:
    if bootstrap_samples <= 0:
        return (
            tuple(None for _ in return_periods),
            tuple(None for _ in return_periods),
            0,
        )
    rng = np.random.default_rng(seed)
    baseline = np.asarray(baseline_values, dtype=float)
    treatment = np.asarray(treatment_values, dtype=float)
    ratios: list[tuple[float, ...]] = []
    for _ in range(bootstrap_samples):
        baseline_sample = rng.choice(baseline, size=baseline.size, replace=True)
        treatment_sample = rng.choice(treatment, size=treatment.size, replace=True)
        try:
            _, baseline_quantiles, _ = _fit_stationary(
                baseline_sample,
                method=method,
                return_periods=return_periods,
            )
            _, treatment_quantiles, _ = _fit_stationary(
                treatment_sample,
                method=method,
                return_periods=return_periods,
            )
        except (FloatingPointError, HydrologyFloodError, RuntimeError, ValueError):
            continue
        ratios.append(
            tuple(
                treatment_value / baseline_value
                for baseline_value, treatment_value in zip(
                    baseline_quantiles,
                    treatment_quantiles,
                    strict=False,
                )
            )
        )
    if not ratios:
        return (
            tuple(None for _ in return_periods),
            tuple(None for _ in return_periods),
            0,
        )
    matrix = np.asarray(ratios, dtype=float)
    lower = tuple(float(value) for value in np.percentile(matrix, 2.5, axis=0))
    upper = tuple(float(value) for value in np.percentile(matrix, 97.5, axis=0))
    return lower, upper, len(ratios)


def _pot_quantiles(
    threshold: float,
    annual_rate: float,
    shape: float,
    scale: float,
    return_periods: tuple[float, ...],
) -> tuple[float, ...]:
    quantiles: list[float] = []
    for period in return_periods:
        probability = 1.0 - 1.0 / (annual_rate * period)
        if probability <= 0 or probability >= 1:
            raise HydrologyFloodError(
                f"Return period {period} is not supported by annual rate {annual_rate}."
            )
        quantiles.append(
            float(
                threshold
                + stats.genpareto.ppf(
                    probability,
                    shape,
                    loc=0.0,
                    scale=scale,
                )
            )
        )
    return tuple(quantiles)


def _nonstationary_quantiles(
    intercept: float,
    betas: Mapping[str, float],
    sigma: float,
    shape: float,
    covariates: Mapping[str, float],
    return_periods: tuple[float, ...],
) -> tuple[float, ...]:
    mu = intercept + sum(betas[name] * covariates.get(name, 0.0) for name in betas)
    probabilities = [1.0 - 1.0 / period for period in return_periods]
    return tuple(
        float(stats.genextreme.ppf(probability, shape, loc=mu, scale=sigma))
        for probability in probabilities
    )


def _scenario_covariates(
    scenarios: Sequence[FloodScenario],
    name: str,
) -> dict[str, float]:
    for scenario in scenarios:
        if scenario.name == name:
            return scenario.covariates
    raise HydrologyFloodError(f"Scenario {name!r} was not found.")


def _as_covariate(
    values: Sequence[float],
    *,
    expected: int,
    name: str,
) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    if array.size != expected:
        raise HydrologyFloodError(
            f"Covariate {name!r} length {array.size} does not match sample size "
            f"{expected}."
        )
    if not np.all(np.isfinite(array)):
        raise HydrologyFloodError(f"Covariate {name!r} must be finite.")
    return array


def _validate_method(method: str) -> None:
    if method not in {"gev", "lp3"}:
        raise HydrologyFloodError("method must be `gev` or `lp3`.")


def _validate_return_periods(return_periods: Sequence[float]) -> tuple[float, ...]:
    if not return_periods:
        raise HydrologyFloodError("At least one return period is required.")
    periods: list[float] = []
    for period in return_periods:
        if not math.isfinite(period) or period <= 1:
            raise HydrologyFloodError("Return periods must be finite and > 1 year.")
        periods.append(float(period))
    return tuple(periods)


def _frequency_caveats() -> tuple[str, ...]:
    return (
        "Frequency fits are decision-support tools and require hydrologist review.",
        "Short records and nonstationarity limit inference.",
        "Bootstrap intervals are percentile intervals, not a full Bayesian posterior.",
        "Public-gauge calibration and published-benchmark validation are P114.9.",
    )


def _surface_id(
    *,
    station_id: str,
    baseline_name: str,
    rows: Sequence[FloodResponseSurfaceRow],
) -> str:
    material = {
        "station_id": station_id,
        "baseline_name": baseline_name,
        "rows": [row.to_dict() for row in rows],
    }
    digest = hashlib.sha256(_canonical_json_bytes(material)).hexdigest()
    return f"hydro-flood-{digest[:16]}"


def _write_json(payload: object, path: Path) -> Path:
    resolved = path.expanduser().resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return resolved


def _canonical_json_bytes(payload: object) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _now() -> str:
    return datetime.now(UTC).isoformat()
