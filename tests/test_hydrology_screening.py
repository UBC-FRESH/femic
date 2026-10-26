from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from femic.hydrology.disturbance import (
    DisturbanceUnit,
    HarvestEvent,
    RoadEvent,
    build_disturbance_ledger,
)
from femic.hydrology.domain import (
    HydrologyGauge,
    HydrologyLayerSpec,
    HydrologyReceptor,
    HydrologyWatershed,
    build_hydrology_domain,
)
from femic.hydrology.screening import (
    HydrologyScreeningError,
    UnitExposureContext,
    WatershedRegime,
    compute_tier0_screening,
    write_tier0_screening_report,
)

GENERATED_UTC = "2026-10-25T00:00:00+00:00"


def _domain():
    layers = (
        HydrologyLayerSpec("watersheds", "watershed", "w.gpkg", "gpkg", "EPSG:3005"),
        HydrologyLayerSpec("streams", "stream", "s.gpkg", "gpkg", "EPSG:3005"),
        HydrologyLayerSpec("roads", "road", "r.gpkg", "gpkg", "EPSG:3005"),
        HydrologyLayerSpec("dem", "dem", "d.tif", "tif", "EPSG:3005"),
        HydrologyLayerSpec("receptors", "receptor", "x.gpkg", "gpkg", "EPSG:3005"),
    )
    return build_hydrology_domain(
        domain_id="screen-domain",
        name="Screen domain",
        layers=layers,
        watersheds=(HydrologyWatershed("w1", "Watershed 1", 10.0, "watersheds"),),
        receptors=(HydrologyReceptor("r1", "Town", "community", "w1", "receptors"),),
        gauges=(HydrologyGauge("g1", "Gauge", "w1"),),
        created_utc=GENERATED_UTC,
    )


def _ledger():
    units = (
        DisturbanceUnit("u1", 10.0, "w1", "h1"),
        DisturbanceUnit("u2", 20.0, "w1", "h2"),
    )
    return build_disturbance_ledger(
        domain_id="screen-domain",
        units=units,
        harvest_events=(
            HarvestEvent("h1", "u1", 2020, 4.0, 1.0, "partial", "ws4"),
            HarvestEvent("h2", "u2", 2021, 5.0, 0.0, "clearcut", "ws4"),
        ),
        road_events=(
            RoadEvent("r1b", "r1", "u1", 2020, "build", 1000.0, True, 1, "fhops"),
            RoadEvent("r2b", "r2", "u1", 2020, "build", 500.0, False, 0, "fhops"),
            RoadEvent(
                "r2d", "r2", "u1", 2021, "decommission", 500.0, False, 0, "fhops"
            ),
        ),
        years=(2020, 2021, 2022),
        generated_utc=GENERATED_UTC,
    )


def _contexts():
    return (
        UnitExposureContext("u1", 0.25, 0.5, 0.1),
        UnitExposureContext("u2", 0.0, 0.0, 0.0),
    )


def test_compute_screening_without_recovery() -> None:
    report = compute_tier0_screening(
        _ledger(),
        _domain(),
        regimes=(WatershedRegime("w1", "snow_transient"),),
        unit_contexts=_contexts(),
        generated_utc=GENERATED_UTC,
    )

    assert len(report.rows) == 3
    assert report.screening_id.startswith("hydro-screen-")
    rows = {row.year: row for row in report.rows}
    first = rows[2020]
    assert first.regime == "snow_transient"
    assert first.watershed_area_ha == 1000.0
    assert first.harvest_area_ha == 4.0
    assert first.retention_area_ha == 1.0
    assert first.effective_harvest_area_ha == 3.0
    assert first.harvest_fraction == pytest.approx(0.004)
    assert first.eca_area_ha == 3.0
    assert first.eca_fraction == pytest.approx(0.003)
    assert first.road_active_km == 1.5
    assert first.road_connected_km == 1.0
    assert first.road_density_km_per_km2 == pytest.approx(0.15)
    assert first.connected_road_density_km_per_km2 == pytest.approx(0.1)
    assert first.road_connected_fraction == pytest.approx(2 / 3)
    assert first.crossing_count == 1
    assert first.crossing_density_per_km2 == pytest.approx(0.1)
    assert first.riparian_effective_harvest_ha == pytest.approx(0.75)
    assert first.snow_transient_effective_harvest_ha == pytest.approx(1.5)
    assert first.high_elevation_effective_harvest_ha == pytest.approx(0.3)

    second = rows[2021]
    assert second.eca_area_ha == 8.0
    assert second.road_active_km == 1.0
    assert second.riparian_effective_harvest_ha == 0.0
    assert any("undiscounted" in warning for warning in report.warnings)

    third = rows[2022]
    assert third.eca_area_ha == 8.0
    assert third.road_active_km == 1.0
    assert third.road_connected_km == 1.0
    assert third.road_connected_fraction == pytest.approx(1.0)
    assert report.to_dict()["summary"]["row_count"] == 3
    assert report.to_dict()["caveats"]


def test_compute_screening_with_recovery() -> None:
    report = compute_tier0_screening(
        _ledger(),
        _domain(),
        regimes=(WatershedRegime("w1", "rain_on_snow"),),
        unit_contexts=_contexts(),
        recovery_years=2,
    )

    rows = {row.year: row for row in report.rows}
    assert rows[2020].eca_area_ha == pytest.approx(3.0)
    assert rows[2021].eca_area_ha == pytest.approx(6.5)
    assert rows[2022].eca_area_ha == pytest.approx(2.5)
    assert rows[2021].regime == "rain_on_snow"


def test_screening_id_is_deterministic_and_report_writes(tmp_path: Path) -> None:
    first = compute_tier0_screening(
        _ledger(),
        _domain(),
        regimes=(WatershedRegime("w1", "snow_transient"),),
        unit_contexts=_contexts(),
        generated_utc=GENERATED_UTC,
    )
    second = compute_tier0_screening(
        _ledger(),
        _domain(),
        regimes=(WatershedRegime("w1", "snow_transient"),),
        unit_contexts=_contexts(),
        generated_utc=GENERATED_UTC,
    )
    assert first.screening_id == second.screening_id

    path = write_tier0_screening_report(first, tmp_path / "screening.json")
    payload = json.loads(path.read_text())
    assert payload["schema_version"] == "femic.hydrology.screening.v1"
    assert payload["ledger_id"] == _ledger().ledger_id
    assert payload["rows"][0]["year"] == 2020
    assert payload["rows"][0]["regime"] == "snow_transient"


def test_missing_regime_and_context_warnings() -> None:
    report = compute_tier0_screening(_ledger(), _domain(), recovery_years=10)

    assert all(row.regime == "unknown" for row in report.rows)
    assert all(row.riparian_effective_harvest_ha == 0 for row in report.rows)
    assert any("No watershed regime" in warning for warning in report.warnings)
    assert any("No unit exposure context" in warning for warning in report.warnings)
    assert all(row.snow_transient_effective_harvest_ha == 0 for row in report.rows)


def test_screening_rejects_bad_inputs() -> None:
    ledger = _ledger()
    domain = _domain()
    with pytest.raises(HydrologyScreeningError, match="ledger must be"):
        compute_tier0_screening(object(), domain)
    with pytest.raises(HydrologyScreeningError, match="domain must be"):
        compute_tier0_screening(ledger, object())
    with pytest.raises(HydrologyScreeningError, match="IDs do not match"):
        compute_tier0_screening(replace(ledger, domain_id="other"), domain)
    with pytest.raises(HydrologyScreeningError, match="recovery_years"):
        compute_tier0_screening(ledger, domain, recovery_years=0)
    with pytest.raises(HydrologyScreeningError, match="unknown watershed"):
        compute_tier0_screening(
            ledger,
            domain,
            regimes=(WatershedRegime("missing", "rain"),),
        )
    with pytest.raises(HydrologyScreeningError, match="Duplicate regime"):
        compute_tier0_screening(
            ledger,
            domain,
            regimes=(
                WatershedRegime("w1", "rain"),
                WatershedRegime("w1", "snowmelt"),
            ),
        )
    with pytest.raises(HydrologyScreeningError, match="Unsupported regime"):
        compute_tier0_screening(
            ledger,
            domain,
            regimes=(WatershedRegime("w1", "bad"),),
        )
    with pytest.raises(HydrologyScreeningError, match="unknown unit"):
        compute_tier0_screening(
            ledger,
            domain,
            unit_contexts=(UnitExposureContext("missing"),),
        )
    with pytest.raises(HydrologyScreeningError, match="Duplicate exposure"):
        compute_tier0_screening(
            ledger,
            domain,
            unit_contexts=(
                UnitExposureContext("u1"),
                UnitExposureContext("u1"),
            ),
        )
    with pytest.raises(HydrologyScreeningError, match="between 0 and 1"):
        compute_tier0_screening(
            ledger,
            domain,
            unit_contexts=(UnitExposureContext("u1", 1.1),),
        )
    with pytest.raises(HydrologyScreeningError, match="between 0 and 1"):
        compute_tier0_screening(
            ledger,
            domain,
            unit_contexts=(UnitExposureContext("u1", 0.0, -0.1),),
        )
    with pytest.raises(HydrologyScreeningError, match="between 0 and 1"):
        compute_tier0_screening(
            ledger,
            domain,
            unit_contexts=(UnitExposureContext("u1", 0.0, 0.0, 2.0),),
        )


def test_invalid_ledger_and_domain_are_rejected() -> None:
    ledger = _ledger()
    domain = _domain()
    bad_ledger = replace(ledger, ledger_id="")
    with pytest.raises(HydrologyScreeningError, match="Ledger ID"):
        compute_tier0_screening(bad_ledger, domain)
    bad_domain = replace(domain, domain_id="")
    with pytest.raises(HydrologyScreeningError, match="Domain ID"):
        compute_tier0_screening(ledger, bad_domain)
    no_units = replace(
        ledger,
        units=(),
        rows=(),
        years=(),
    )
    with pytest.raises(HydrologyScreeningError, match="at least one year"):
        compute_tier0_screening(no_units, domain)


def test_rows_and_context_payloads() -> None:
    report = compute_tier0_screening(
        _ledger(),
        _domain(),
        regimes=(WatershedRegime("w1", "snow_transient"),),
        unit_contexts=_contexts(),
    )
    row = report.rows[0]
    assert row.to_dict()["watershed_id"] == "w1"
    assert WatershedRegime("w1", "rain").to_dict()["regime"] == "rain"
    assert UnitExposureContext("u1").to_dict()["unit_id"] == "u1"
    assert report.to_dict()["rows"][0]["eca_area_ha"] >= 0


def test_unknown_unit_watershed_and_partial_context_warning() -> None:
    ledger = _ledger()
    bad_units = (
        replace(ledger.units[0], watershed_id="missing"),
        ledger.units[1],
    )
    bad = replace(ledger, units=bad_units)
    with pytest.raises(HydrologyScreeningError, match="unknown watershed"):
        compute_tier0_screening(bad, _domain())

    report = compute_tier0_screening(
        ledger,
        _domain(),
        unit_contexts=(UnitExposureContext("u1", 0.25),),
    )
    assert any(
        "Some units have no exposure context" in warning for warning in report.warnings
    )
