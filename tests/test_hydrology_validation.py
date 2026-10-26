from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from femic.cli.main import app
from femic.hydrology.validation import (
    HydrologyValidationError,
    assess_return_period_ratios,
    audit_pilot_readiness,
    build_benchmark_reviews,
    build_p1149_closeout,
    build_pilot_sample,
    build_validation_report,
    load_pilot_annual_maxima,
    load_pilot_gauges,
    published_benchmarks,
    run_public_gauge_pilot,
)

PILOT_ROOT = Path("tests/fixtures/hydrology/pilot")
RESPONSE_ROOT = Path("tests/fixtures/hydrology/response_bundle")
GENERATED_UTC = "2026-10-26T00:00:00+00:00"
runner = CliRunner()


def _pilot():
    return run_public_gauge_pilot(
        PILOT_ROOT / "gauges.json",
        PILOT_ROOT / "annual_maxima.csv",
        bootstrap_samples=10,
        seed=42,
        generated_utc=GENERATED_UTC,
    )


def test_load_pilot_fixture_and_build_samples() -> None:
    gauges = load_pilot_gauges(PILOT_ROOT / "gauges.json")
    rows = load_pilot_annual_maxima(PILOT_ROOT / "annual_maxima.csv")

    assert len(gauges) == 3
    assert {gauge.regime for gauge in gauges} == {
        "rain",
        "rain_on_snow",
        "snow_transient",
    }
    assert len(rows) == 180
    rain = next(gauge for gauge in gauges if gauge.regime == "rain")
    sample = build_pilot_sample(rain, rows)
    assert sample.station_id == "08HB048"
    assert len(sample.years) == 51
    assert sample.values[0] == pytest.approx(11.0)
    assert sample.years[0] == 1973


def test_public_gauge_pilot_fits_and_split_sample() -> None:
    pilot = _pilot()
    first = _pilot()

    assert pilot.run_id == first.run_id
    assert pilot.run_id.startswith("hydro-pilot-")
    assert len(pilot.backcasts) == 3
    by_station = {item.gauge.station_number: item for item in pilot.backcasts}
    rain = by_station["08HB048"]
    snow = by_station["08LG048"]

    assert rain.gauge.regime == "rain"
    assert rain.year_count == 51
    assert rain.missing_years == (2018,)
    assert rain.estimated_years
    assert set(rain.estimated_years).issubset(rain.flagged_years)
    assert set(rain.fits) == {"gev", "lp3"}
    assert rain.fits["gev"].quantiles[0] < rain.fits["gev"].quantiles[-1]
    assert rain.split_sample is not None
    assert rain.split_sample.early_sample_size > 10
    assert len(rain.split_sample.ratios) == 3
    assert any("estimated" in warning for warning in rain.warnings)

    assert snow.gauge.regime == "snow_transient"
    assert snow.year_count == 58
    assert snow.missing_years == (2021,)
    assert snow.fits["lp3"].quantiles[-1] > snow.fits["lp3"].quantiles[0]
    assert snow.split_sample is not None

    mountain = by_station["08GA022"]
    assert mountain.gauge.regime == "rain_on_snow"
    assert mountain.year_count == 71
    assert "lp3" in mountain.usable_fits
    assert "gev" not in mountain.usable_fits
    assert any("tail check failed" in warning for warning in mountain.warnings)
    assert mountain.split_sample is not None
    assert not mountain.split_sample.usable


def test_pilot_requires_known_station() -> None:
    gauges = load_pilot_gauges(PILOT_ROOT / "gauges.json")
    rows = load_pilot_annual_maxima(PILOT_ROOT / "annual_maxima.csv")
    empty = next(gauge for gauge in gauges if gauge.station_number == "08HB048")

    with pytest.raises(HydrologyValidationError, match="No annual maxima"):
        build_pilot_sample(
            empty, tuple(row for row in rows if row.station_number != "08HB048")
        )


def test_readiness_without_inputs_records_gaps() -> None:
    readiness = audit_pilot_readiness()

    assert not readiness.ready_for_full_process_pilot
    assert not readiness.domain_available
    assert len(readiness.gaps) >= 4


def test_readiness_with_fixture_domain_and_ledger() -> None:
    readiness = audit_pilot_readiness(
        domain_manifest_path=RESPONSE_ROOT / "domain.json",
        disturbance_ledger_path=RESPONSE_ROOT / "disturbance.json",
        process_model_available=True,
        hydrologist_review_recorded=True,
    )

    assert readiness.domain_available
    assert readiness.lidar_available
    assert readiness.stream_available
    assert readiness.road_available
    assert readiness.receptor_available
    assert readiness.ready_for_full_process_pilot
    assert readiness.gaps == ()


def test_benchmark_increase_direction_and_scale() -> None:
    case = next(
        item
        for item in published_benchmarks()
        if item.case_id == "snow-transient-high-return-period-increase"
    )

    passed = assess_return_period_ratios(case, (2.0, 100.0), (1.15, 1.40))
    failed = assess_return_period_ratios(case, (2.0, 100.0), (0.95, 4.0))

    assert passed.is_consistent
    assert all(row.direction_ok for row in passed.rows)
    assert not failed.is_consistent
    assert any("not consistent" in warning for warning in failed.warnings)


def test_benchmark_frequency_dependence() -> None:
    case = next(
        item
        for item in published_benchmarks()
        if item.case_id == "frequency-dependence-high-vs-low"
    )

    passed = assess_return_period_ratios(case, (2.0, 100.0), (1.05, 1.35))
    failed = assess_return_period_ratios(case, (2.0, 100.0), (1.35, 1.05))

    assert passed.is_consistent
    assert not failed.is_consistent


def test_benchmark_no_change_and_validation() -> None:
    case = next(
        item
        for item in published_benchmarks()
        if item.case_id == "paired-control-no-change"
    )

    assert assess_return_period_ratios(case, (2.0, 100.0), (0.98, 1.02)).is_consistent
    assert not assess_return_period_ratios(case, (2.0, 100.0), (1.5, 1.5)).is_consistent

    with pytest.raises(HydrologyValidationError, match="equal in length"):
        assess_return_period_ratios(case, (2.0,), (1.0, 1.0))
    with pytest.raises(HydrologyValidationError, match="positive"):
        assess_return_period_ratios(case, (2.0,), (0.0,))
    with pytest.raises(HydrologyValidationError, match="unique"):
        assess_return_period_ratios(case, (2.0, 2.0), (1.0, 1.0))


def test_benchmark_reviews_mark_executed_cases() -> None:
    case = published_benchmarks()[0]
    assessment = assess_return_period_ratios(case, (2.0, 100.0), (1.2, 1.4))
    reviews = build_benchmark_reviews((assessment,))
    executed = next(review for review in reviews if review.case.case_id == case.case_id)

    assert executed.status == "passed"
    assert executed.assessment is not None
    assert executed.assessment.is_consistent
    assert sum(review.status == "passed" for review in reviews) == 1


def test_benchmark_reviews_keep_unexecuted_cases_explicit() -> None:
    reviews = build_benchmark_reviews()

    assert len(reviews) == len(published_benchmarks())
    assert all(review.status == "not_evaluated" for review in reviews)
    assert all(review.assessment is None for review in reviews)
    assert all("No paired" in review.reason for review in reviews)


def test_validation_report_and_model_card_are_deterministic() -> None:
    pilot = _pilot()
    readiness = audit_pilot_readiness()
    report, card = build_validation_report(
        pilot,
        readiness=readiness,
        generated_utc=GENERATED_UTC,
    )
    second_report, second_card = build_validation_report(
        pilot,
        readiness=readiness,
        generated_utc=GENERATED_UTC,
    )

    assert report.validation_id == second_report.validation_id
    assert report.validation_id.startswith("hydro-validation-")
    assert report.pilot_run_id == pilot.run_id
    assert report.model_card_id == card.model_card_id
    assert report.summary["gauge_count"] == 3
    assert report.summary["benchmark_not_evaluated"] == len(published_benchmarks())
    assert report.summary["tail_check_failures"] == {"08GA022": ["gev"]}
    assert report.readiness.gaps
    assert any("not a regulatory flood map" in caveat for caveat in report.caveats)
    assert card.model_card_id == second_card.model_card_id
    assert card.validation_report_id == report.validation_id
    assert card.review_status == "not_reviewed"


def test_closeout_writes_machine_readable_records(tmp_path: Path) -> None:
    result = build_p1149_closeout(
        gauges_path=PILOT_ROOT / "gauges.json",
        annual_maxima_path=PILOT_ROOT / "annual_maxima.csv",
        output_dir=tmp_path / "closeout",
        bootstrap_samples=10,
        seed=42,
        generated_utc=GENERATED_UTC,
    )

    assert result.pilot_path.is_file()
    assert result.validation_path.is_file()
    assert result.model_card_path.is_file()
    pilot_payload = json.loads(result.pilot_path.read_text(encoding="utf-8"))
    report_payload = json.loads(result.validation_path.read_text(encoding="utf-8"))
    card_payload = json.loads(result.model_card_path.read_text(encoding="utf-8"))
    assert pilot_payload["schema_version"] == "femic.hydrology.pilot.v1"
    assert report_payload["schema_version"] == "femic.hydrology.validation.v1"
    assert card_payload["schema_version"] == "femic.hydrology.model_card.v1"
    assert report_payload["model_card_id"] == card_payload["model_card_id"]


def test_cli_pilot_writes_closeout(tmp_path: Path) -> None:
    output = tmp_path / "cli-closeout"

    result = runner.invoke(
        app,
        [
            "hydrology",
            "pilot",
            "--gauges",
            str(PILOT_ROOT / "gauges.json"),
            "--annual-maxima",
            str(PILOT_ROOT / "annual_maxima.csv"),
            "--output-dir",
            str(output),
            "--bootstrap-samples",
            "20",
            "--generated-utc",
            GENERATED_UTC,
        ],
    )

    assert result.exit_code == 0, result.output
    assert "pilot_run_id: hydro-pilot-" in result.stdout
    assert "validation_id: hydro-validation-" in result.stdout
    assert (output / "validation_report.json").is_file()
