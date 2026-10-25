from __future__ import annotations

import json
import math
from datetime import date
from pathlib import Path

import numpy as np
import pytest
from scipy import stats

from femic.hydrology.flood import (
    FloodBenchmark,
    FloodEvent,
    FloodSample,
    FloodScenario,
    HydrologyFloodError,
    build_response_surface,
    evaluate_frequency_benchmark,
    extract_annual_maxima,
    extract_peaks_over_threshold,
    fit_flood_frequency,
    fit_nonstationary_gev,
    fit_pot_frequency,
    paired_frequency_response,
    predict_nonstationary_quantiles,
    write_flood_frequency_report,
    write_response_surface,
)

PERIODS = (2.0, 5.0, 10.0, 25.0, 50.0, 100.0)


def _sample(values: np.ndarray, *, station: str = "station-1") -> FloodSample:
    years = tuple(range(1900, 1900 + len(values)))
    return FloodSample(station, years, tuple(float(value) for value in values))


def _gev_sample(seed: int = 42, size: int = 100) -> FloodSample:
    rng = np.random.default_rng(seed)
    values = stats.genextreme.rvs(
        0.1, loc=100.0, scale=20.0, size=size, random_state=rng
    )
    return _sample(values)


def test_sample_validation_and_payloads() -> None:
    sample = _sample(np.array([1.0, 2.0, 3.0]))
    assert sample.to_dict()["station_id"] == "station-1"
    assert FloodEvent(date(2020, 1, 1), 10.0).to_dict()["value"] == 10.0
    with pytest.raises(HydrologyFloodError, match="equal length"):
        FloodSample("s", (2020,), (1.0, 2.0))
    with pytest.raises(HydrologyFloodError, match="at least one"):
        FloodSample("s", (), ())
    with pytest.raises(HydrologyFloodError, match="unique"):
        FloodSample("s", (2020, 2020), (1.0, 2.0))
    with pytest.raises(HydrologyFloodError, match="positive"):
        FloodSample("s", (2020,), (0.0,))


def test_extract_annual_maxima() -> None:
    events = (
        FloodEvent(date(2020, 1, 1), 10.0),
        FloodEvent(date(2020, 6, 1), 20.0),
        FloodEvent(date(2021, 1, 1), 15.0),
    )
    sample = extract_annual_maxima(events, station_id="s", regime="rain")
    assert sample.years == (2020, 2021)
    assert sample.values == (20.0, 15.0)
    assert sample.regime == "rain"
    with pytest.raises(HydrologyFloodError, match="At least one"):
        extract_annual_maxima((), station_id="s")
    with pytest.raises(HydrologyFloodError, match="positive"):
        extract_annual_maxima(
            (FloodEvent(date(2020, 1, 1), 0.0),),
            station_id="s",
        )


def test_extract_peaks_over_threshold_declusters() -> None:
    events = (
        FloodEvent(date(2020, 1, 1), 150.0),
        FloodEvent(date(2020, 1, 3), 140.0),
        FloodEvent(date(2020, 2, 1), 130.0),
        FloodEvent(date(2021, 1, 1), 90.0),
    )
    sample = extract_peaks_over_threshold(
        events,
        threshold=100.0,
        min_separation_days=10,
        station_id="s",
        regime="rain",
    )
    assert sample.values == (150.0, 130.0)
    assert sample.annual_rate == pytest.approx(1.0)
    assert sample.to_dict()["threshold"] == 100.0
    with pytest.raises(HydrologyFloodError, match="At least one"):
        extract_peaks_over_threshold(
            (),
            threshold=100.0,
            min_separation_days=10,
            station_id="s",
        )
    with pytest.raises(HydrologyFloodError, match="finite"):
        extract_peaks_over_threshold(
            events,
            threshold=float("nan"),
            min_separation_days=10,
            station_id="s",
        )
    with pytest.raises(HydrologyFloodError, match="non-negative"):
        extract_peaks_over_threshold(
            events,
            threshold=100.0,
            min_separation_days=-1,
            station_id="s",
        )
    with pytest.raises(HydrologyFloodError, match="positive"):
        extract_peaks_over_threshold(
            (FloodEvent(date(2020, 1, 1), 0.0),),
            threshold=100.0,
            min_separation_days=10,
            station_id="s",
        )


def test_fit_gev_and_lp3() -> None:
    gev = fit_flood_frequency(
        _gev_sample(),
        method="gev",
        return_periods=PERIODS,
        bootstrap_samples=30,
        seed=1,
    )
    assert gev.method == "gev"
    assert gev.sample_size == 100
    assert list(gev.quantiles) == sorted(gev.quantiles)
    assert all(
        lower <= value <= upper
        for lower, value, upper in zip(
            gev.lower_bounds, gev.quantiles, gev.upper_bounds, strict=False
        )
    )
    assert math.isfinite(gev.aic)
    assert gev.to_dict()["parameters"]["shape_scipy"] == pytest.approx(
        gev.parameters["shape_scipy"]
    )

    rng = np.random.default_rng(7)
    lp3_values = 10 ** rng.normal(2.0, 0.25, 100)
    lp3 = fit_flood_frequency(
        _sample(lp3_values),
        method="lp3",
        return_periods=PERIODS,
        bootstrap_samples=20,
        seed=2,
    )
    assert lp3.method == "lp3"
    assert list(lp3.quantiles) == sorted(lp3.quantiles)
    assert "log10_skew" in lp3.parameters


def test_frequency_fit_warnings_and_errors() -> None:
    short = fit_flood_frequency(
        _sample(np.array([10.0, 11.0, 12.0, 13.0, 14.0, 15.0])),
        bootstrap_samples=0,
    )
    assert any("recommended" in warning for warning in short.warnings)
    assert short.lower_bounds == (None,) * len(short.return_periods)
    with pytest.raises(HydrologyFloodError, match="method"):
        fit_flood_frequency(_gev_sample(), method="bad")
    with pytest.raises(HydrologyFloodError, match="Return periods"):
        fit_flood_frequency(_gev_sample(), return_periods=(1.0,))
    with pytest.raises(HydrologyFloodError, match="At least 5"):
        fit_flood_frequency(_sample(np.array([1.0, 2.0, 3.0, 4.0])))


def test_fit_pot_frequency() -> None:
    rng = np.random.default_rng(5)
    excesses = stats.genpareto.rvs(0.1, loc=0.0, scale=10.0, size=60, random_state=rng)
    events = tuple(
        FloodEvent(date(1990 + index // 2, 1 + index % 2, 1), 100.0 + float(value))
        for index, value in enumerate(excesses)
    )
    sample = extract_peaks_over_threshold(
        events,
        threshold=100.0,
        min_separation_days=1,
        station_id="pot",
    )
    fit = fit_pot_frequency(
        sample,
        return_periods=(2.0, 5.0, 10.0),
        bootstrap_samples=15,
        seed=3,
    )
    assert fit.method == "gpd"
    assert fit.parameters["annual_rate"] > 0
    assert all(value > sample.threshold for value in fit.quantiles)
    with pytest.raises(HydrologyFloodError, match="At least 5"):
        fit_pot_frequency(
            extract_peaks_over_threshold(
                events[:2],
                threshold=100.0,
                min_separation_days=1,
                station_id="pot",
            )
        )


def test_paired_frequency_response_and_benchmark() -> None:
    rng = np.random.default_rng(11)
    baseline_values = stats.genextreme.rvs(
        0.1, loc=80.0, scale=20.0, size=200, random_state=rng
    )
    baseline = _sample(baseline_values)
    rng = np.random.default_rng(12)
    treatment_values = stats.genextreme.rvs(
        0.1, loc=140.0, scale=20.0, size=200, random_state=rng
    )
    treatment = _sample(treatment_values, station="treatment")
    pairing = paired_frequency_response(
        baseline,
        treatment,
        method="gev",
        return_periods=PERIODS,
        bootstrap_samples=15,
        seed=4,
    )
    assert all(ratio > 1 for ratio in pairing.ratios)
    assert len(pairing.ratio_lower) == len(PERIODS)
    assert pairing.to_dict()["ratios"] == list(pairing.ratios)

    benchmark = FloodBenchmark(
        name="synthetic",
        return_periods=PERIODS,
        lower_ratio=tuple(0.5 for _ in PERIODS),
        upper_ratio=tuple(3.0 for _ in PERIODS),
        source="unit test",
    )
    check = evaluate_frequency_benchmark(pairing, benchmark)
    assert check.is_pass
    assert check.to_dict()["benchmark_name"] == "synthetic"

    strict = FloodBenchmark(
        name="strict",
        return_periods=(2.0,),
        lower_ratio=(2.0,),
        upper_ratio=(3.0,),
    )
    assert not evaluate_frequency_benchmark(pairing, strict).is_pass
    with pytest.raises(HydrologyFloodError, match="differ"):
        evaluate_frequency_benchmark(
            pairing,
            FloodBenchmark("bad", (2.0,), (1.0,), ()),
        )
    with pytest.raises(HydrologyFloodError, match="missing"):
        evaluate_frequency_benchmark(
            pairing,
            FloodBenchmark("bad", (999.0,), (1.0,), (2.0,)),
        )


def test_nonstationary_gev_and_response_surface(tmp_path: Path) -> None:
    rng = np.random.default_rng(21)
    years = tuple(range(1900, 2100))
    covariate = np.linspace(0.0, 1.0, len(years))
    values = stats.genextreme.rvs(
        0.1,
        loc=100.0 + 80.0 * covariate,
        scale=20.0,
        size=len(years),
        random_state=rng,
    )
    sample = FloodSample("nonstationary", years, tuple(float(v) for v in values))
    fit = fit_nonstationary_gev(
        sample,
        {"harvest_fraction": covariate},
        return_periods=(2.0, 10.0, 100.0),
        baseline_covariates={"harvest_fraction": 0.0},
    )
    assert fit.coefficients["harvest_fraction"] > 0
    assert fit.to_dict()["sample_size"] == 200
    predicted = predict_nonstationary_quantiles(
        fit,
        {"harvest_fraction": 1.0},
        return_periods=(2.0, 10.0, 100.0),
    )
    assert all(
        high > baseline
        for high, baseline in zip(predicted, fit.baseline_quantiles, strict=False)
    )

    surface = build_response_surface(
        fit,
        (
            FloodScenario("baseline", {"harvest_fraction": 0.0}),
            FloodScenario("high", {"harvest_fraction": 1.0}),
        ),
        generated_utc="2026-10-25T00:00:00+00:00",
    )
    assert surface.surface_id.startswith("hydro-flood-")
    assert len(surface.rows) == 6
    assert all(row.ratio > 1 for row in surface.rows if row.scenario == "high")
    assert surface.to_dict()["summary"]["row_count"] == 6

    path = write_response_surface(surface, tmp_path / "surface.json")
    assert json.loads(path.read_text())["surface_id"] == surface.surface_id


def test_nonstationary_errors() -> None:
    sample = _gev_sample(size=100)
    with pytest.raises(HydrologyFloodError, match="At least one covariate"):
        fit_nonstationary_gev(sample, {})
    with pytest.raises(HydrologyFloodError, match="length"):
        fit_nonstationary_gev(sample, {"x": [1.0, 2.0]})
    with pytest.raises(HydrologyFloodError, match="finite"):
        fit_nonstationary_gev(sample, {"x": [float("nan")] * 100})
    fit = fit_nonstationary_gev(sample, {"x": [0.0] * 100})
    with pytest.raises(HydrologyFloodError, match="not in the model"):
        predict_nonstationary_quantiles(fit, {"missing": 1.0})
    with pytest.raises(HydrologyFloodError, match="not in the model"):
        fit_nonstationary_gev(
            sample,
            {"x": [0.0] * 100},
            baseline_covariates={"missing": 1.0},
        )
    with pytest.raises(HydrologyFloodError, match="At least one response"):
        build_response_surface(fit, ())
    with pytest.raises(HydrologyFloodError, match="unique"):
        build_response_surface(
            fit,
            (FloodScenario("a", {"x": 0.0}), FloodScenario("a", {"x": 1.0})),
        )
    with pytest.raises(HydrologyFloodError, match="Baseline scenario"):
        build_response_surface(
            fit,
            (FloodScenario("a", {"x": 0.0}),),
            baseline_name="missing",
        )


def test_frequency_report_writer(tmp_path: Path) -> None:
    fit = fit_flood_frequency(_gev_sample(size=20), bootstrap_samples=0)
    path = write_flood_frequency_report(fit, tmp_path / "frequency.json")
    payload = json.loads(path.read_text())
    assert payload["schema_version"] == "femic.hydrology.flood_frequency.v1"
    assert payload["method"] == "gev"
    assert len(payload["quantiles"]) == len(fit.return_periods)
