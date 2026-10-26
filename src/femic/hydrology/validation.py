"""P114.9 validation, public-gauge pilot, model card, and close-out.

This module does not add a new hydrologic model. It records published benchmark
expectations, runs bounded public-gauge frequency backcasts, audits full-pilot
readiness, and emits the validation report and model card that accompany a
FEMIC response bundle.
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

from femic.hydrology.flood import (
    MIN_RECOMMENDED_SAMPLES,
    FloodFrequencyFit,
    FloodSample,
    fit_flood_frequency,
)

HYDROLOGY_VALIDATION_SCHEMA_VERSION = "femic.hydrology.validation.v1"
HYDROLOGY_MODEL_CARD_SCHEMA_VERSION = "femic.hydrology.model_card.v1"
HYDROLOGY_PILOT_RUN_SCHEMA_VERSION = "femic.hydrology.pilot.v1"
HYDROLOGY_BENCHMARK_EVIDENCE_VERSION = "femic.hydrology.benchmark_evidence.2026-10"
HYDROLOGY_PILOT_RETURN_PERIODS: tuple[float, ...] = (2.0, 10.0, 100.0)
BENCHMARK_DIRECTIONS: tuple[str, ...] = (
    "increase",
    "decrease",
    "frequency_dependent",
    "no_change",
)
PILOT_REGIMES: tuple[str, ...] = ("rain", "rain_on_snow", "snow_transient", "snowmelt")
MODEL_CARD_REVIEW_STATUSES: tuple[str, ...] = (
    "not_reviewed",
    "review_pending",
    "reviewed",
    "reviewed_with_conditions",
)


class HydrologyValidationError(RuntimeError):
    """Raised when pilot or validation evidence is invalid."""


@dataclass(frozen=True)
class PublishedBenchmark:
    """One directional/order-of-magnitude expectation from published work."""

    case_id: str
    regime: str
    hypothesis: str
    expected_direction: str
    sources: tuple[str, ...]
    log10_tolerance: float = 0.5
    notes: str = ""

    def __post_init__(self) -> None:
        if not self.case_id.strip():
            raise HydrologyValidationError("Benchmark case ID must be non-empty.")
        if self.regime not in PILOT_REGIMES:
            raise HydrologyValidationError(
                f"Unsupported benchmark regime {self.regime!r}."
            )
        if self.expected_direction not in BENCHMARK_DIRECTIONS:
            raise HydrologyValidationError(
                f"Unsupported expected direction {self.expected_direction!r}."
            )
        if self.log10_tolerance <= 0 or not math.isfinite(self.log10_tolerance):
            raise HydrologyValidationError(
                "Benchmark log10 tolerance must be positive and finite."
            )
        if not self.sources:
            raise HydrologyValidationError("Benchmark case must cite a source.")

    def to_dict(self) -> dict[str, object]:
        """Return the benchmark case as a JSON-serializable mapping."""

        return {
            "case_id": self.case_id,
            "regime": self.regime,
            "hypothesis": self.hypothesis,
            "expected_direction": self.expected_direction,
            "sources": list(self.sources),
            "log10_tolerance": self.log10_tolerance,
            "notes": self.notes,
        }


def published_benchmarks() -> tuple[PublishedBenchmark, ...]:
    """Return the reviewed directional benchmark catalogue.

    These are deliberately directional and order-of-magnitude checks, not
    point estimates copied from any one watershed.
    """

    return (
        PublishedBenchmark(
            case_id="snow-transient-high-return-period-increase",
            regime="snow_transient",
            hypothesis=(
                "Cumulative harvest in snow-transient terrain increases "
                "high-return-period peak flows more than low-return-period flows."
            ),
            expected_direction="increase",
            sources=(
                "Rong, Bishop & Alila (2026), doi:10.1016/j.advwatres.2026.105432",
                "Green & Alila (2012), doi:10.1029/2012WR012449",
                "Schnorbus & Alila (2013), doi:10.1029/2012WR011901",
            ),
            notes=(
                "Planning screen only. The expected magnitude is watershed- and "
                "event-specific; the tolerance is a factor of about three."
            ),
        ),
        PublishedBenchmark(
            case_id="rain-high-return-period-increase",
            regime="rain",
            hypothesis=(
                "Harvest effects on rain-generated peak flows are "
                "return-period-dependent and can increase at longer return periods."
            ),
            expected_direction="increase",
            sources=(
                "Pham, Alila & Caldwell (2025), Journal of Hydrology 661:133704",
                ("Alila, Kuras, Schnorbus & Hudson (2009), doi:10.1029/2008WR007207"),
            ),
            notes=(
                "The direction is the benchmark; the published magnitude varies "
                "with harvest pattern, connectivity, and record length."
            ),
        ),
        PublishedBenchmark(
            case_id="frequency-dependence-high-vs-low",
            regime="rain",
            hypothesis=(
                "Peak-flow response at a long return period exceeds the response "
                "at a short return period for the same treatment."
            ),
            expected_direction="frequency_dependent",
            sources=(
                "Kuras, Alila & Weiler (2012), doi:10.1029/2011WR010705",
                ("Alila, Kuras, Schnorbus & Hudson (2009), doi:10.1029/2008WR007207"),
            ),
            notes=(
                "This case compares high- and low-return-period ratios rather "
                "than requiring a fixed ratio at every return period."
            ),
        ),
        PublishedBenchmark(
            case_id="snowmelt-high-return-period-increase",
            regime="snowmelt",
            hypothesis=(
                "Harvest in snow-dominated terrain can increase snowmelt peak "
                "flows, with the strongest evidence at larger return periods."
            ),
            expected_direction="increase",
            sources=(
                "Green & Alila (2012), doi:10.1029/2012WR012449",
                "Schnorbus & Alila (2013), doi:10.1029/2012WR011901",
            ),
            notes=(
                "Directional screen only; snow regime and elevation-band "
                "representation must be reviewed before application."
            ),
        ),
        PublishedBenchmark(
            case_id="paired-control-no-change",
            regime="rain",
            hypothesis=(
                "An untreated paired control watershed should not show a "
                "treatment-scale change in peak-flow frequency."
            ),
            expected_direction="no_change",
            sources=(
                ("Alila, Kuras, Schnorbus & Hudson (2009), doi:10.1029/2008WR007207"),
                "Kuras, Alila & Weiler (2012), doi:10.1029/2011WR010705",
            ),
            log10_tolerance=0.1,
            notes=(
                "This is a falsification check for confounding, not proof that "
                "the control is hydrologically stationary."
            ),
        ),
    )


@dataclass(frozen=True)
class BenchmarkRow:
    """One return-period comparison against a published expectation."""

    return_period: float
    observed_ratio: float
    direction_ok: bool
    scale_ok: bool

    def to_dict(self) -> dict[str, object]:
        """Return the benchmark row as a JSON-serializable mapping."""

        return {
            "return_period": self.return_period,
            "observed_ratio": self.observed_ratio,
            "direction_ok": self.direction_ok,
            "scale_ok": self.scale_ok,
        }


@dataclass(frozen=True)
class BenchmarkAssessment:
    """Directional/order-of-magnitude assessment of one paired response."""

    case_id: str
    is_consistent: bool
    rows: tuple[BenchmarkRow, ...]
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        """Return the assessment as a JSON-serializable mapping."""

        return {
            "case_id": self.case_id,
            "is_consistent": self.is_consistent,
            "rows": [row.to_dict() for row in self.rows],
            "warnings": list(self.warnings),
        }


def assess_return_period_ratios(
    benchmark: PublishedBenchmark,
    return_periods: Sequence[float],
    ratios: Sequence[float],
) -> BenchmarkAssessment:
    """Compare return-period ratios with one published expectation."""

    periods = tuple(float(period) for period in return_periods)
    values = tuple(float(ratio) for ratio in ratios)
    if not periods or len(periods) != len(values):
        raise HydrologyValidationError(
            "Benchmark return periods and ratios must be non-empty and equal in length."
        )
    if any(period <= 1 or not math.isfinite(period) for period in periods):
        raise HydrologyValidationError("Benchmark return periods must be > 1.")
    if any(value <= 0 or not math.isfinite(value) for value in values):
        raise HydrologyValidationError("Benchmark ratios must be positive and finite.")
    if len(set(periods)) != len(periods):
        raise HydrologyValidationError("Benchmark return periods must be unique.")

    rows: list[BenchmarkRow] = []
    if benchmark.expected_direction == "frequency_dependent":
        low_index = min(range(len(periods)), key=periods.__getitem__)
        high_index = max(range(len(periods)), key=periods.__getitem__)
        high_ratio = values[high_index]
        low_ratio = values[low_index]
        direction_ok = high_ratio > low_ratio
        scale_ok = abs(math.log10(high_ratio / low_ratio)) <= benchmark.log10_tolerance
        for period, value in zip(periods, values, strict=True):
            rows.append(
                BenchmarkRow(
                    return_period=period,
                    observed_ratio=value,
                    direction_ok=direction_ok,
                    scale_ok=scale_ok,
                )
            )
    else:
        for period, value in zip(periods, values, strict=True):
            if benchmark.expected_direction == "increase":
                direction_ok = value > 1.0
            elif benchmark.expected_direction == "decrease":
                direction_ok = value < 1.0
            else:
                direction_ok = abs(math.log10(value)) <= benchmark.log10_tolerance
            scale_ok = abs(math.log10(value)) <= benchmark.log10_tolerance
            rows.append(
                BenchmarkRow(
                    return_period=period,
                    observed_ratio=value,
                    direction_ok=direction_ok,
                    scale_ok=scale_ok,
                )
            )
    warnings: list[str] = []
    if not all(row.direction_ok and row.scale_ok for row in rows):
        warnings.append(
            "Observed ratios are not consistent with the directional planning "
            "screen. This is not proof of hydrologic failure."
        )
    return BenchmarkAssessment(
        case_id=benchmark.case_id,
        is_consistent=all(row.direction_ok and row.scale_ok for row in rows),
        rows=tuple(rows),
        warnings=tuple(warnings),
    )


@dataclass(frozen=True)
class BenchmarkCaseReview:
    """Review status for one published benchmark case."""

    case: PublishedBenchmark
    assessment: BenchmarkAssessment | None
    status: str
    reason: str

    def __post_init__(self) -> None:
        if self.status not in ("passed", "failed", "not_evaluated"):
            raise HydrologyValidationError(
                f"Unsupported benchmark review status {self.status!r}."
            )

    def to_dict(self) -> dict[str, object]:
        """Return the benchmark review as a JSON-serializable mapping."""

        return {
            "case": self.case.to_dict(),
            "assessment": self.assessment.to_dict() if self.assessment else None,
            "status": self.status,
            "reason": self.reason,
        }


def build_benchmark_reviews(
    assessments: Sequence[BenchmarkAssessment] = (),
) -> tuple[BenchmarkCaseReview, ...]:
    """Attach available assessments to the published benchmark catalogue."""

    by_case = {assessment.case_id: assessment for assessment in assessments}
    reviews: list[BenchmarkCaseReview] = []
    for case in published_benchmarks():
        assessment = by_case.get(case.case_id)
        if assessment is None:
            reviews.append(
                BenchmarkCaseReview(
                    case=case,
                    assessment=None,
                    status="not_evaluated",
                    reason=(
                        "No paired baseline/treatment frequency result was "
                        "available in the bounded P114.9 pilot."
                    ),
                )
            )
            continue
        reviews.append(
            BenchmarkCaseReview(
                case=case,
                assessment=assessment,
                status="passed" if assessment.is_consistent else "failed",
                reason=(
                    "Observed paired ratios matched the directional planning screen."
                    if assessment.is_consistent
                    else "Observed paired ratios did not match the planning screen."
                ),
            )
        )
    return tuple(reviews)


@dataclass(frozen=True)
class PilotGauge:
    """Public gauge metadata for the bounded P114.9 pilot."""

    station_number: str
    station_name: str
    province: str
    regime: str
    drainage_area_km2: float
    status: str
    contributor: str
    vertical_datum: str
    source_url: str
    station_url: str
    licence: str
    retrieved_utc: str
    notes: str = ""

    def __post_init__(self) -> None:
        if not self.station_number.strip():
            raise HydrologyValidationError("Pilot station number must be non-empty.")
        if self.regime not in PILOT_REGIMES:
            raise HydrologyValidationError(f"Unsupported pilot regime {self.regime!r}.")
        if self.drainage_area_km2 <= 0 or not math.isfinite(self.drainage_area_km2):
            raise HydrologyValidationError("Pilot drainage area must be positive.")

    def to_dict(self) -> dict[str, object]:
        """Return the gauge metadata as a JSON-serializable mapping."""

        return {
            "station_number": self.station_number,
            "station_name": self.station_name,
            "province": self.province,
            "regime": self.regime,
            "drainage_area_km2": self.drainage_area_km2,
            "status": self.status,
            "contributor": self.contributor,
            "vertical_datum": self.vertical_datum,
            "source_url": self.source_url,
            "station_url": self.station_url,
            "licence": self.licence,
            "retrieved_utc": self.retrieved_utc,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class PilotAnnualMaximum:
    """One public annual maximum daily discharge value."""

    station_number: str
    year: int
    max_date: str
    max_value_m3s: float
    symbol: str = ""

    def __post_init__(self) -> None:
        if not self.station_number.strip():
            raise HydrologyValidationError("Annual-maximum station is required.")
        if self.year < 1800 or self.year > 2200:
            raise HydrologyValidationError("Annual-maximum year is outside range.")
        if not self.max_date.strip():
            raise HydrologyValidationError("Annual-maximum date is required.")
        if self.max_value_m3s <= 0 or not math.isfinite(self.max_value_m3s):
            raise HydrologyValidationError("Annual-maximum discharge must be positive.")

    def to_dict(self) -> dict[str, object]:
        """Return the annual maximum as a JSON-serializable mapping."""

        return {
            "station_number": self.station_number,
            "year": self.year,
            "max_date": self.max_date,
            "max_value_m3s": self.max_value_m3s,
            "symbol": self.symbol,
        }


def load_pilot_gauges(path: Path) -> tuple[PilotGauge, ...]:
    """Load the bounded pilot gauge metadata fixture."""

    payload = _read_json_object(path, context="pilot gauges")
    gauges = payload.get("gauges")
    if not isinstance(gauges, list) or not gauges:
        raise HydrologyValidationError("Pilot gauge file must contain gauges.")
    parsed = tuple(
        _pilot_gauge_from_payload(item, index=index)
        for index, item in enumerate(gauges, start=1)
    )
    numbers = {gauge.station_number for gauge in parsed}
    if len(numbers) != len(parsed):
        raise HydrologyValidationError("Pilot gauge station numbers must be unique.")
    return parsed


def load_pilot_annual_maxima(path: Path) -> tuple[PilotAnnualMaximum, ...]:
    """Load annual maxima from the bounded pilot CSV."""

    resolved = path.expanduser().resolve()
    try:
        with resolved.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            expected = {
                "station_number",
                "year",
                "max_date",
                "max_value_m3s",
                "symbol",
            }
            if reader.fieldnames is None or not expected.issubset(reader.fieldnames):
                raise HydrologyValidationError(
                    f"Pilot CSV is missing required columns: {resolved}"
                )
            rows = tuple(
                PilotAnnualMaximum(
                    station_number=_required_text(row.get("station_number"), "station"),
                    year=_required_int(row.get("year"), "year"),
                    max_date=_required_text(row.get("max_date"), "max_date"),
                    max_value_m3s=_required_float(
                        row.get("max_value_m3s"),
                        "max_value_m3s",
                    ),
                    symbol=(row.get("symbol") or "").strip(),
                )
                for row in reader
            )
    except OSError as exc:
        raise HydrologyValidationError(
            f"Unable to read pilot CSV: {resolved}: {exc}"
        ) from exc
    if not rows:
        raise HydrologyValidationError("Pilot CSV contains no annual maxima.")
    return rows


def build_pilot_sample(
    gauge: PilotGauge,
    rows: Sequence[PilotAnnualMaximum],
) -> FloodSample:
    """Build a validated flood sample for one pilot gauge."""

    selected = sorted(
        (row for row in rows if row.station_number == gauge.station_number),
        key=lambda row: row.year,
    )
    if not selected:
        raise HydrologyValidationError(
            f"No annual maxima found for station {gauge.station_number}."
        )
    years = tuple(row.year for row in selected)
    if len(set(years)) != len(years):
        raise HydrologyValidationError(
            f"Duplicate annual maxima for station {gauge.station_number}."
        )
    return FloodSample(
        station_id=gauge.station_number,
        years=years,
        values=tuple(row.max_value_m3s for row in selected),
        regime=gauge.regime,
    )


@dataclass(frozen=True)
class SplitSampleBackcast:
    """Early/late split-sample frequency stability check."""

    split_year: int
    early_sample_size: int
    late_sample_size: int
    early_fit: FloodFrequencyFit
    late_fit: FloodFrequencyFit
    ratios: tuple[float, ...]
    usable: bool = True
    reasons: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        """Return the split-sample result as a JSON-serializable mapping."""

        return {
            "split_year": self.split_year,
            "early_sample_size": self.early_sample_size,
            "late_sample_size": self.late_sample_size,
            "early_fit": self.early_fit.to_dict(),
            "late_fit": self.late_fit.to_dict(),
            "ratios": list(self.ratios),
            "usable": self.usable,
            "reasons": list(self.reasons),
        }


@dataclass(frozen=True)
class TailCheck:
    """Screening plausibility check for one fitted tail."""

    method: str
    shape: float | None
    q100: float | None
    observed_max: float
    q100_to_observed_max: float | None
    is_plausible: bool
    reasons: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        """Return the tail check as a JSON-serializable mapping."""

        return {
            "method": self.method,
            "shape": self.shape,
            "q100": self.q100,
            "observed_max": self.observed_max,
            "q100_to_observed_max": self.q100_to_observed_max,
            "is_plausible": self.is_plausible,
            "reasons": list(self.reasons),
        }


@dataclass(frozen=True)
class PilotGaugeBackcast:
    """Public-gauge frequency backcast and data-quality record."""

    gauge: PilotGauge
    generated_utc: str
    record_start_year: int
    record_end_year: int
    year_count: int
    missing_years: tuple[int, ...]
    estimated_years: tuple[int, ...]
    flagged_years: tuple[int, ...]
    fits: dict[str, FloodFrequencyFit]
    tail_checks: tuple[TailCheck, ...]
    usable_fits: tuple[str, ...]
    split_sample: SplitSampleBackcast | None
    warnings: tuple[str, ...] = ()
    caveats: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        """Return the gauge backcast as a JSON-serializable mapping."""

        return {
            "gauge": self.gauge.to_dict(),
            "generated_utc": self.generated_utc,
            "record_start_year": self.record_start_year,
            "record_end_year": self.record_end_year,
            "year_count": self.year_count,
            "missing_years": list(self.missing_years),
            "estimated_years": list(self.estimated_years),
            "flagged_years": list(self.flagged_years),
            "fits": {method: fit.to_dict() for method, fit in self.fits.items()},
            "tail_checks": [check.to_dict() for check in self.tail_checks],
            "usable_fits": list(self.usable_fits),
            "split_sample": (
                self.split_sample.to_dict() if self.split_sample else None
            ),
            "warnings": list(self.warnings),
            "caveats": list(self.caveats),
        }


def run_gauge_backcast(
    gauge: PilotGauge,
    rows: Sequence[PilotAnnualMaximum],
    *,
    return_periods: Sequence[float] = HYDROLOGY_PILOT_RETURN_PERIODS,
    bootstrap_samples: int = 200,
    seed: int = 42,
    generated_utc: str | None = None,
) -> PilotGaugeBackcast:
    """Fit GEV and LP3 to one public gauge and run a split-sample check."""

    sample = build_pilot_sample(gauge, rows)
    if len(sample.values) < MIN_RECOMMENDED_SAMPLES:
        raise HydrologyValidationError(
            f"Station {gauge.station_number} has fewer than "
            f"{MIN_RECOMMENDED_SAMPLES} annual maxima."
        )
    selected = sorted(
        (row for row in rows if row.station_number == gauge.station_number),
        key=lambda row: row.year,
    )
    first_year = sample.years[0]
    last_year = sample.years[-1]
    observed_years = set(sample.years)
    missing_years = tuple(
        year for year in range(first_year, last_year + 1) if year not in observed_years
    )
    estimated_years = tuple(
        row.year for row in selected if row.symbol.strip().lower() == "estimated"
    )
    flagged_years = tuple(row.year for row in selected if row.symbol.strip())
    warnings: list[str] = []
    if missing_years:
        warnings.append(
            "Missing annual maxima in the nominal record: "
            + ", ".join(str(year) for year in missing_years)
            + "."
        )
    if estimated_years:
        warnings.append(
            "Annual maxima marked estimated: "
            + ", ".join(str(year) for year in estimated_years)
            + "."
        )
    if flagged_years:
        warnings.append(
            "Annual maxima with source quality symbols: "
            + ", ".join(str(year) for year in flagged_years)
            + "."
        )
    if len(sample.values) < 30:
        warnings.append("Fewer than 30 annual maxima; tail estimates are fragile.")
    fits = {
        method: fit_flood_frequency(
            sample,
            method=method,
            return_periods=return_periods,
            bootstrap_samples=bootstrap_samples,
            seed=seed,
        )
        for method in ("gev", "lp3")
    }
    observed_max = max(sample.values)
    tail_checks = tuple(
        _tail_check(
            method,
            fit,
            observed_max=observed_max,
            return_periods=return_periods,
        )
        for method, fit in fits.items()
    )
    usable_fits = tuple(check.method for check in tail_checks if check.is_plausible)
    for check in tail_checks:
        if not check.is_plausible:
            warnings.append(
                f"{check.method.upper()} tail check failed: " + "; ".join(check.reasons)
            )
    split_sample = _split_sample_backcast(
        sample,
        return_periods=return_periods,
        bootstrap_samples=bootstrap_samples,
        seed=seed,
    )
    if split_sample is not None:
        if not split_sample.usable:
            warnings.append(
                "Split-sample tail check failed: " + "; ".join(split_sample.reasons)
            )
        else:
            for period, ratio in zip(
                return_periods,
                split_sample.ratios,
                strict=True,
            ):
                if ratio < 0.5 or ratio > 2.0:
                    warnings.append(
                        f"Early/late {period:g}-year quantile ratio is {ratio:.2f}; "
                        "tail stability should be reviewed."
                    )
    return PilotGaugeBackcast(
        gauge=gauge,
        generated_utc=generated_utc or _now(),
        record_start_year=first_year,
        record_end_year=last_year,
        year_count=len(sample.values),
        missing_years=missing_years,
        estimated_years=estimated_years,
        flagged_years=flagged_years,
        fits=fits,
        tail_checks=tail_checks,
        usable_fits=usable_fits,
        split_sample=split_sample,
        warnings=tuple(warnings),
        caveats=(
            (
                "Gauge backcast only; no harvest/road treatment or process-model "
                "calibration was applied."
            ),
            (
                "Return-level intervals are bootstrap percentile intervals and are "
                "not a Bayesian posterior."
            ),
            (
                "Fits that fail the tail plausibility screen remain in the record "
                "but must not be used for risk reporting."
            ),
            "This is not a regulatory flood-frequency product.",
        ),
    )


def run_public_gauge_pilot(
    gauges_path: Path,
    annual_maxima_path: Path,
    *,
    return_periods: Sequence[float] = HYDROLOGY_PILOT_RETURN_PERIODS,
    bootstrap_samples: int = 200,
    seed: int = 42,
    generated_utc: str | None = None,
) -> PilotRun:
    """Run the bounded P114.9 public-gauge pilot."""

    gauges = load_pilot_gauges(gauges_path)
    rows = load_pilot_annual_maxima(annual_maxima_path)
    backcasts = tuple(
        run_gauge_backcast(
            gauge,
            rows,
            return_periods=return_periods,
            bootstrap_samples=bootstrap_samples,
            seed=seed,
            generated_utc=generated_utc,
        )
        for gauge in gauges
    )
    return _build_pilot_run(
        gauges=gauges,
        rows=rows,
        backcasts=backcasts,
        return_periods=return_periods,
        bootstrap_samples=bootstrap_samples,
        seed=seed,
        generated_utc=generated_utc or _now(),
    )


@dataclass(frozen=True)
class PilotRun:
    """Serialized bounded public-gauge pilot."""

    run_id: str
    generated_utc: str
    gauges: tuple[PilotGauge, ...]
    backcasts: tuple[PilotGaugeBackcast, ...]
    return_periods: tuple[float, ...]
    bootstrap_samples: int
    seed: int
    caveats: tuple[str, ...] = ()
    provenance: dict[str, object] = field(default_factory=dict)
    schema_version: str = HYDROLOGY_PILOT_RUN_SCHEMA_VERSION

    def to_dict(self) -> dict[str, object]:
        """Return the pilot run as a JSON-serializable mapping."""

        return {
            "schema_version": self.schema_version,
            "run_id": self.run_id,
            "generated_utc": self.generated_utc,
            "gauges": [gauge.to_dict() for gauge in self.gauges],
            "backcasts": [backcast.to_dict() for backcast in self.backcasts],
            "return_periods": list(self.return_periods),
            "bootstrap_samples": self.bootstrap_samples,
            "seed": self.seed,
            "caveats": list(self.caveats),
            "provenance": self.provenance,
        }


@dataclass(frozen=True)
class PilotReadiness:
    """Full-pilot readiness and data-gap audit."""

    domain_available: bool
    lidar_available: bool
    stream_available: bool
    road_available: bool
    disturbance_available: bool
    receptor_available: bool
    process_model_available: bool
    hydrologist_review_recorded: bool
    gaps: tuple[str, ...] = ()

    @property
    def ready_for_full_process_pilot(self) -> bool:
        """Return whether all full-pilot prerequisites are present."""

        return all(
            (
                self.domain_available,
                self.lidar_available,
                self.stream_available,
                self.road_available,
                self.disturbance_available,
                self.receptor_available,
                self.process_model_available,
                self.hydrologist_review_recorded,
            )
        )

    def to_dict(self) -> dict[str, object]:
        """Return the readiness audit as a JSON-serializable mapping."""

        return {
            "domain_available": self.domain_available,
            "lidar_available": self.lidar_available,
            "stream_available": self.stream_available,
            "road_available": self.road_available,
            "disturbance_available": self.disturbance_available,
            "receptor_available": self.receptor_available,
            "process_model_available": self.process_model_available,
            "hydrologist_review_recorded": self.hydrologist_review_recorded,
            "ready_for_full_process_pilot": self.ready_for_full_process_pilot,
            "gaps": list(self.gaps),
        }


def audit_pilot_readiness(
    *,
    domain_manifest_path: Path | None = None,
    disturbance_ledger_path: Path | None = None,
    process_model_available: bool = False,
    hydrologist_review_recorded: bool = False,
) -> PilotReadiness:
    """Audit whether a full two-watershed process pilot can be run."""

    domain_available = (
        domain_manifest_path is not None and domain_manifest_path.is_file()
    )
    lidar_available = False
    stream_available = False
    road_available = False
    receptor_available = False
    disturbance_available = (
        disturbance_ledger_path is not None and disturbance_ledger_path.is_file()
    )
    gaps: list[str] = []
    if not domain_available:
        gaps.append("No public hydrology domain manifest was supplied.")
    else:
        from femic.hydrology.domain import (
            HYDROLOGY_REQUIRED_LAYER_ROLES,
            load_hydrology_domain_manifest,
        )

        assert domain_manifest_path is not None
        try:
            manifest = load_hydrology_domain_manifest(domain_manifest_path)
            roles = {layer.role for layer in manifest.layers}
            lidar_available = "dem" in roles
            stream_available = "stream" in roles
            road_available = "road" in roles
            receptor_available = bool(manifest.receptors)
            missing = [
                role for role in HYDROLOGY_REQUIRED_LAYER_ROLES if role not in roles
            ]
            if missing:
                gaps.append(
                    "Domain is missing required layers: " + ", ".join(missing) + "."
                )
        except Exception as exc:  # noqa: BLE001 - reported as a pilot gap
            gaps.append(f"Domain manifest could not be audited: {exc}")
    if not disturbance_available:
        gaps.append("No annual harvest/road disturbance ledger was supplied.")
    if not process_model_available:
        gaps.append("No executable process model was available for the pilot.")
    if not hydrologist_review_recorded:
        gaps.append("No hydrologist review record was supplied.")
    if not receptor_available:
        gaps.append("No downstream receptor was available for risk evaluation.")
    return PilotReadiness(
        domain_available=domain_available,
        lidar_available=lidar_available,
        stream_available=stream_available,
        road_available=road_available,
        disturbance_available=disturbance_available,
        receptor_available=receptor_available,
        process_model_available=process_model_available,
        hydrologist_review_recorded=hydrologist_review_recorded,
        gaps=tuple(gaps),
    )


@dataclass(frozen=True)
class ModelCard:
    """Versioned model card for the P114 response layer."""

    model_card_id: str
    model_id: str
    model_version: str
    title: str
    intended_use: tuple[str, ...]
    out_of_scope: tuple[str, ...]
    regimes: tuple[str, ...]
    validation_report_id: str
    pilot_run_id: str
    validation_summary: dict[str, object]
    uncertainty: tuple[str, ...]
    limitations: tuple[str, ...]
    review_status: str
    review_checklist: tuple[str, ...]
    consumer_handoff: tuple[str, ...]
    sources: tuple[str, ...]
    generated_utc: str
    caveats: tuple[str, ...] = ()
    schema_version: str = HYDROLOGY_MODEL_CARD_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.review_status not in MODEL_CARD_REVIEW_STATUSES:
            raise HydrologyValidationError(
                f"Unsupported model-card review status {self.review_status!r}."
            )

    def to_dict(self) -> dict[str, object]:
        """Return the model card as a JSON-serializable mapping."""

        return {
            "schema_version": self.schema_version,
            "model_card_id": self.model_card_id,
            "model_id": self.model_id,
            "model_version": self.model_version,
            "title": self.title,
            "intended_use": list(self.intended_use),
            "out_of_scope": list(self.out_of_scope),
            "regimes": list(self.regimes),
            "validation_report_id": self.validation_report_id,
            "pilot_run_id": self.pilot_run_id,
            "validation_summary": self.validation_summary,
            "uncertainty": list(self.uncertainty),
            "limitations": list(self.limitations),
            "review_status": self.review_status,
            "review_checklist": list(self.review_checklist),
            "consumer_handoff": list(self.consumer_handoff),
            "sources": list(self.sources),
            "generated_utc": self.generated_utc,
            "caveats": list(self.caveats),
        }


@dataclass(frozen=True)
class ValidationReport:
    """P114.9 validation report and consumer handoff."""

    validation_id: str
    generated_utc: str
    pilot_run_id: str
    benchmark_evidence_version: str
    benchmark_reviews: tuple[BenchmarkCaseReview, ...]
    readiness: PilotReadiness
    model_card_id: str
    summary: dict[str, object]
    deviations: tuple[str, ...]
    uncertainty: tuple[str, ...]
    caveats: tuple[str, ...]
    consumer_handoff: tuple[str, ...]
    provenance: dict[str, object] = field(default_factory=dict)
    schema_version: str = HYDROLOGY_VALIDATION_SCHEMA_VERSION

    def to_dict(self) -> dict[str, object]:
        """Return the validation report as a JSON-serializable mapping."""

        return {
            "schema_version": self.schema_version,
            "validation_id": self.validation_id,
            "generated_utc": self.generated_utc,
            "pilot_run_id": self.pilot_run_id,
            "benchmark_evidence_version": self.benchmark_evidence_version,
            "benchmark_reviews": [
                review.to_dict() for review in self.benchmark_reviews
            ],
            "readiness": self.readiness.to_dict(),
            "model_card_id": self.model_card_id,
            "summary": self.summary,
            "deviations": list(self.deviations),
            "uncertainty": list(self.uncertainty),
            "caveats": list(self.caveats),
            "consumer_handoff": list(self.consumer_handoff),
            "provenance": self.provenance,
        }


def build_validation_report(
    pilot_run: PilotRun,
    *,
    readiness: PilotReadiness,
    assessments: Sequence[BenchmarkAssessment] = (),
    generated_utc: str | None = None,
) -> tuple[ValidationReport, ModelCard]:
    """Build the deterministic validation report and linked model card."""

    reviews = build_benchmark_reviews(assessments)
    timestamp = generated_utc or _now()
    summary = _validation_summary(pilot_run, reviews, readiness)
    validation_id = _validation_id(pilot_run, reviews, readiness)
    model_card = build_model_card(
        pilot_run=pilot_run,
        validation_report_id=validation_id,
        readiness=readiness,
        generated_utc=timestamp,
    )
    report = ValidationReport(
        validation_id=validation_id,
        generated_utc=timestamp,
        pilot_run_id=pilot_run.run_id,
        benchmark_evidence_version=HYDROLOGY_BENCHMARK_EVIDENCE_VERSION,
        benchmark_reviews=reviews,
        readiness=readiness,
        model_card_id=model_card.model_card_id,
        summary=summary,
        deviations=(
            (
                "The bounded pilot used public gauge annual maxima only; it did not "
                "run a distributed process model or a harvest/road treatment scenario."
            ),
            (
                "No paired baseline/treatment frequency result was available, so the "
                "published benchmark cases remain directional reviews rather than "
                "executed validation cases."
            ),
            (
                "The full two-watershed pilot (snow-transient and coastal rain) was "
                "not completed because public LiDAR, disturbance-ledger, receptor, and "
                "process-model inputs were not assembled in P114.9."
            ),
            "No hydrologist review record was available.",
        ),
        uncertainty=(
            "Annual maxima are a short sample of a nonstationary process.",
            "Bootstrap intervals are percentile intervals, not a Bayesian posterior.",
            (
                "Tail estimates are sensitive to record length, missing years, and "
                "estimated values."
            ),
            "Gauge-frequency behaviour does not identify harvest or road causality.",
            "Regionalization and climate projection are not validated.",
        ),
        caveats=(
            "Screening and decision-support only; not a regulatory flood map.",
            "No design-flood, floodplain, legal, or operational safety determination.",
            (
                "Do not interpret a passed directional benchmark as proof of hydrologic "
                "correctness."
            ),
        ),
        consumer_handoff=(
            (
                "WS4 P49 may use the pinned response bundle for spatial scheduling "
                "screens, subject to the recorded applicability domain and caveats."
            ),
            (
                "FHOPS P14 may use the pinned response bundle for operational road and "
                "harvest tradeoff reporting, subject to the same caveats."
            ),
            "Consumers must verify bundle_id/bundle_version and artifact checksums.",
            (
                "A hydrologist review and a completed process-model pilot are required "
                "before operational use or any regulatory interpretation."
            ),
        ),
        provenance={
            "producer": "femic.hydrology.validation",
            "benchmark_evidence_version": HYDROLOGY_BENCHMARK_EVIDENCE_VERSION,
            "pilot_fixture": "public WSC annual maxima; see pilot README",
            "licence": "Open Government Licence - Canada",
        },
    )
    return report, model_card


def build_model_card(
    *,
    pilot_run: PilotRun,
    validation_report_id: str,
    readiness: PilotReadiness,
    generated_utc: str | None = None,
) -> ModelCard:
    """Build the response-layer model card."""

    summary = {
        "pilot_run_id": pilot_run.run_id,
        "gauge_count": len(pilot_run.gauges),
        "gauges": [gauge.station_number for gauge in pilot_run.gauges],
        "regimes": [gauge.regime for gauge in pilot_run.gauges],
        "record_years": {
            backcast.gauge.station_number: backcast.year_count
            for backcast in pilot_run.backcasts
        },
        "usable_fits": {
            backcast.gauge.station_number: list(backcast.usable_fits)
            for backcast in pilot_run.backcasts
        },
        "full_process_pilot_ready": readiness.ready_for_full_process_pilot,
        "data_gaps": list(readiness.gaps),
    }
    material = {
        "model_id": "femic-hydrology-response",
        "model_version": "2026.10",
        "validation_report_id": validation_report_id,
        "pilot_run_id": pilot_run.run_id,
        "summary": summary,
    }
    digest = hashlib.sha256(_canonical_json_bytes(material)).hexdigest()
    return ModelCard(
        model_card_id=f"hydro-model-card-{digest[:16]}",
        model_id="femic-hydrology-response",
        model_version="2026.10",
        title="FEMIC forest-hydrology response and flood-risk screening layer",
        intended_use=(
            "Landscape-level screening of return-period-specific peak-flow response.",
            "Comparing harvest and road-construction patterns under explicit regimes.",
            "Producing pinned response bundles for WS4 and FHOPS decision support.",
        ),
        out_of_scope=(
            "Regulatory flood mapping, design floods, floodways, or legal determinations.",
            "Operational safety certification without hydrologist review.",
            "Silent extrapolation outside the recorded applicability domain.",
            "Causal attribution of observed floods to forest management.",
        ),
        regimes=tuple(dict.fromkeys(gauge.regime for gauge in pilot_run.gauges)),
        validation_report_id=validation_report_id,
        pilot_run_id=pilot_run.run_id,
        validation_summary=summary,
        uncertainty=(
            "Bootstrap percentile intervals, not a Bayesian posterior.",
            "Short records and nonstationarity limit tail inference.",
            "Structural and climate uncertainty are not fully represented.",
            "Gauge backcasts do not validate treatment effects.",
        ),
        limitations=(
            "No full distributed process-model pilot was completed.",
            "No paired treatment/control response was available for benchmark execution.",
            "Hydrologist review is not recorded.",
            "Damage curves, receptor capacity, and regulatory status remain external.",
        ),
        review_status="not_reviewed",
        review_checklist=(
            "Review gauge selection, regime assignment, missing years, and estimated values.",
            "Review GEV/LP3 fit diagnostics and split-sample tail stability.",
            "Review benchmark directions, tolerances, and deviations.",
            "Review data gaps and the WS4/FHOPS applicability boundary.",
            "Record approval, conditions, or rejection before operational use.",
        ),
        consumer_handoff=(
            "Use only a pinned response bundle that references this model card.",
            "Refuse queries outside the recorded applicability domain.",
            "Carry the screening-only caveat into WS4 and FHOPS outputs.",
            "Require hydrologist review before operational or regulatory use.",
        ),
        sources=tuple(
            source for case in published_benchmarks() for source in case.sources
        ),
        generated_utc=generated_utc or _now(),
        caveats=(
            "Model card is provisional until hydrologist review is recorded.",
            "No regulatory status is claimed.",
        ),
    )


def write_pilot_run(pilot_run: PilotRun, path: Path) -> Path:
    """Write a pilot run as JSON."""

    return _write_json(pilot_run.to_dict(), path)


def write_validation_report(report: ValidationReport, path: Path) -> Path:
    """Write a validation report as JSON."""

    return _write_json(report.to_dict(), path)


def write_model_card(model_card: ModelCard, path: Path) -> Path:
    """Write a model card as JSON."""

    return _write_json(model_card.to_dict(), path)


@dataclass(frozen=True)
class CloseoutResult:
    """Paths and records produced by the P114.9 closeout run."""

    output_dir: Path
    pilot_run: PilotRun
    validation_report: ValidationReport
    model_card: ModelCard
    pilot_path: Path
    validation_path: Path
    model_card_path: Path

    def to_dict(self) -> dict[str, object]:
        """Return the closeout result as a JSON-serializable mapping."""

        return {
            "output_dir": str(self.output_dir),
            "pilot_run": self.pilot_run.to_dict(),
            "validation_report": self.validation_report.to_dict(),
            "model_card": self.model_card.to_dict(),
            "pilot_path": str(self.pilot_path),
            "validation_path": str(self.validation_path),
            "model_card_path": str(self.model_card_path),
        }


def build_p1149_closeout(
    *,
    gauges_path: Path,
    annual_maxima_path: Path,
    output_dir: Path,
    domain_manifest_path: Path | None = None,
    disturbance_ledger_path: Path | None = None,
    process_model_available: bool = False,
    hydrologist_review_recorded: bool = False,
    bootstrap_samples: int = 200,
    seed: int = 42,
    generated_utc: str | None = None,
) -> CloseoutResult:
    """Run the bounded pilot and write the closeout records."""

    pilot = run_public_gauge_pilot(
        gauges_path,
        annual_maxima_path,
        bootstrap_samples=bootstrap_samples,
        seed=seed,
        generated_utc=generated_utc,
    )
    readiness = audit_pilot_readiness(
        domain_manifest_path=domain_manifest_path,
        disturbance_ledger_path=disturbance_ledger_path,
        process_model_available=process_model_available,
        hydrologist_review_recorded=hydrologist_review_recorded,
    )
    report, card = build_validation_report(
        pilot,
        readiness=readiness,
        generated_utc=generated_utc,
    )
    output = output_dir.expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    pilot_path = write_pilot_run(pilot, output / "pilot_run.json")
    validation_path = write_validation_report(report, output / "validation_report.json")
    model_card_path = write_model_card(card, output / "model_card.json")
    return CloseoutResult(
        output_dir=output,
        pilot_run=pilot,
        validation_report=report,
        model_card=card,
        pilot_path=pilot_path,
        validation_path=validation_path,
        model_card_path=model_card_path,
    )


def _tail_check(
    method: str,
    fit: FloodFrequencyFit,
    *,
    observed_max: float,
    return_periods: Sequence[float],
) -> TailCheck:
    reasons: list[str] = []
    shape: float | None = None
    if method == "gev":
        raw_shape = fit.parameters.get("shape_scipy")
        if isinstance(raw_shape, (int, float)) and not isinstance(raw_shape, bool):
            shape = float(raw_shape)
            if shape < -0.5 or shape > 0.5:
                reasons.append(
                    f"GEV shape {shape:.2f} is outside the screening range [-0.5, 0.5]."
                )
    q100 = _fit_quantile(fit, 100.0)
    ratio: float | None = None
    if 100.0 not in return_periods:
        reasons.append("The 100-year return period is missing from the fit.")
    elif q100 is None or not math.isfinite(q100) or q100 <= 0:
        reasons.append("The 100-year quantile is missing or non-physical.")
    else:
        ratio = q100 / observed_max
        if ratio > 10.0:
            reasons.append(
                f"The 100-year quantile is {ratio:.1f} times the observed maximum."
            )
        if ratio < 0.5:
            reasons.append(
                f"The 100-year quantile is only {ratio:.2f} times the observed maximum."
            )
    return TailCheck(
        method=method,
        shape=shape,
        q100=q100,
        observed_max=observed_max,
        q100_to_observed_max=ratio,
        is_plausible=not reasons,
        reasons=tuple(reasons),
    )


def _fit_quantile(fit: FloodFrequencyFit, period: float) -> float | None:
    for candidate, value in zip(
        fit.return_periods,
        fit.quantiles,
        strict=True,
    ):
        if math.isclose(candidate, period, rel_tol=1e-9, abs_tol=1e-9):
            return value
    return None


def _split_sample_backcast(
    sample: FloodSample,
    *,
    return_periods: Sequence[float],
    bootstrap_samples: int,
    seed: int,
) -> SplitSampleBackcast | None:
    if len(sample.values) < MIN_RECOMMENDED_SAMPLES * 2:
        return None
    split_index = max(
        MIN_RECOMMENDED_SAMPLES,
        round(len(sample.values) * 0.7),
    )
    if split_index >= len(sample.values):
        return None
    early = FloodSample(
        station_id=sample.station_id,
        years=sample.years[:split_index],
        values=sample.values[:split_index],
        regime=sample.regime,
    )
    late = FloodSample(
        station_id=sample.station_id,
        years=sample.years[split_index:],
        values=sample.values[split_index:],
        regime=sample.regime,
    )
    if len(late.values) < MIN_RECOMMENDED_SAMPLES:
        return None
    early_fit = fit_flood_frequency(
        early,
        method="gev",
        return_periods=return_periods,
        bootstrap_samples=bootstrap_samples,
        seed=seed,
    )
    late_fit = fit_flood_frequency(
        late,
        method="gev",
        return_periods=return_periods,
        bootstrap_samples=bootstrap_samples,
        seed=seed + 1,
    )
    ratios = tuple(
        late_value / early_value
        for early_value, late_value in zip(
            early_fit.quantiles,
            late_fit.quantiles,
            strict=True,
        )
    )
    early_check = _tail_check(
        "gev",
        early_fit,
        observed_max=max(early.values),
        return_periods=return_periods,
    )
    late_check = _tail_check(
        "gev",
        late_fit,
        observed_max=max(late.values),
        return_periods=return_periods,
    )
    reasons = tuple(f"early {reason}" for reason in early_check.reasons) + tuple(
        f"late {reason}" for reason in late_check.reasons
    )
    return SplitSampleBackcast(
        split_year=sample.years[split_index],
        early_sample_size=len(early.values),
        late_sample_size=len(late.values),
        early_fit=early_fit,
        late_fit=late_fit,
        ratios=ratios,
        usable=not reasons,
        reasons=reasons,
    )


def _build_pilot_run(
    *,
    gauges: Sequence[PilotGauge],
    rows: Sequence[PilotAnnualMaximum],
    backcasts: Sequence[PilotGaugeBackcast],
    return_periods: Sequence[float],
    bootstrap_samples: int,
    seed: int,
    generated_utc: str,
) -> PilotRun:
    material = {
        "gauges": [gauge.to_dict() for gauge in gauges],
        "rows": [row.to_dict() for row in rows],
        "return_periods": list(return_periods),
        "bootstrap_samples": bootstrap_samples,
        "seed": seed,
    }
    digest = hashlib.sha256(_canonical_json_bytes(material)).hexdigest()
    return PilotRun(
        run_id=f"hydro-pilot-{digest[:16]}",
        generated_utc=generated_utc,
        gauges=tuple(gauges),
        backcasts=tuple(backcasts),
        return_periods=tuple(return_periods),
        bootstrap_samples=bootstrap_samples,
        seed=seed,
        caveats=(
            "Public gauge backcast only; no treatment scenario was applied.",
            "Annual maxima are derived from public WSC annual statistics.",
            "No regulatory or design-flood interpretation is permitted.",
        ),
        provenance={
            "producer": "femic.hydrology.validation",
            "source": "Water Survey of Canada hydrometric annual statistics",
            "licence": "Open Government Licence - Canada",
        },
    )


def _validation_summary(
    pilot_run: PilotRun,
    reviews: Sequence[BenchmarkCaseReview],
    readiness: PilotReadiness,
) -> dict[str, object]:
    return {
        "gauge_count": len(pilot_run.gauges),
        "regimes": [gauge.regime for gauge in pilot_run.gauges],
        "backcast_years": {
            backcast.gauge.station_number: backcast.year_count
            for backcast in pilot_run.backcasts
        },
        "usable_fits": {
            backcast.gauge.station_number: list(backcast.usable_fits)
            for backcast in pilot_run.backcasts
        },
        "tail_check_failures": {
            backcast.gauge.station_number: [
                check.method for check in backcast.tail_checks if not check.is_plausible
            ]
            for backcast in pilot_run.backcasts
            if any(not check.is_plausible for check in backcast.tail_checks)
        },
        "benchmark_cases": len(reviews),
        "benchmark_passed": sum(1 for review in reviews if review.status == "passed"),
        "benchmark_failed": sum(1 for review in reviews if review.status == "failed"),
        "benchmark_not_evaluated": sum(
            1 for review in reviews if review.status == "not_evaluated"
        ),
        "full_process_pilot_ready": readiness.ready_for_full_process_pilot,
        "data_gap_count": len(readiness.gaps),
        "hydrologist_review_recorded": readiness.hydrologist_review_recorded,
    }


def _validation_id(
    pilot_run: PilotRun,
    reviews: Sequence[BenchmarkCaseReview],
    readiness: PilotReadiness,
) -> str:
    material = {
        "pilot_run_id": pilot_run.run_id,
        "benchmark_reviews": [review.to_dict() for review in reviews],
        "readiness": readiness.to_dict(),
    }
    digest = hashlib.sha256(_canonical_json_bytes(material)).hexdigest()
    return f"hydro-validation-{digest[:16]}"


def _pilot_gauge_from_payload(item: object, *, index: int) -> PilotGauge:
    payload = _mapping_from_object(item, context=f"pilot gauge {index}")
    return PilotGauge(
        station_number=_required_text(payload.get("station_number"), "station_number"),
        station_name=_required_text(payload.get("station_name"), "station_name"),
        province=_required_text(payload.get("province"), "province"),
        regime=_required_text(payload.get("regime"), "regime"),
        drainage_area_km2=_required_float(
            payload.get("drainage_area_km2"),
            "drainage_area_km2",
        ),
        status=_required_text(payload.get("status"), "status"),
        contributor=_required_text(payload.get("contributor"), "contributor"),
        vertical_datum=_required_text(
            payload.get("vertical_datum"),
            "vertical_datum",
        ),
        source_url=_required_text(payload.get("source_url"), "source_url"),
        station_url=_required_text(payload.get("station_url"), "station_url"),
        licence=_required_text(payload.get("licence"), "licence"),
        retrieved_utc=_required_text(payload.get("retrieved_utc"), "retrieved_utc"),
        notes=_optional_text(payload.get("notes")) or "",
    )


def _read_json_object(path: Path, *, context: str) -> dict[str, object]:
    resolved = path.expanduser().resolve()
    try:
        payload: object = json.loads(resolved.read_text(encoding="utf-8"))
    except OSError as exc:
        raise HydrologyValidationError(
            f"Unable to read {context}: {resolved}: {exc}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise HydrologyValidationError(
            f"Invalid JSON in {context}: {resolved}: {exc}"
        ) from exc
    if not isinstance(payload, Mapping):
        raise HydrologyValidationError(f"{context} must be a JSON object: {resolved}")
    return {str(key): value for key, value in payload.items()}


def _mapping_from_object(value: object, *, context: str) -> dict[str, object]:
    if not isinstance(value, Mapping):
        raise HydrologyValidationError(f"{context} must be an object.")
    return {str(key): item for key, item in value.items()}


def _required_text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise HydrologyValidationError(f"Field {field_name!r} must be non-empty text.")
    return value.strip()


def _optional_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text or None


def _required_float(value: object, field_name: str) -> float:
    if isinstance(value, bool):
        raise HydrologyValidationError(f"Field {field_name!r} must be numeric.")
    try:
        parsed = float(str(value))
    except (TypeError, ValueError) as exc:
        raise HydrologyValidationError(
            f"Field {field_name!r} must be numeric."
        ) from exc
    if not math.isfinite(parsed):
        raise HydrologyValidationError(f"Field {field_name!r} must be finite.")
    return parsed


def _required_int(value: object, field_name: str) -> int:
    if isinstance(value, bool):
        raise HydrologyValidationError(f"Field {field_name!r} must be an integer.")
    try:
        return int(str(value))
    except (TypeError, ValueError) as exc:
        raise HydrologyValidationError(
            f"Field {field_name!r} must be an integer."
        ) from exc


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
