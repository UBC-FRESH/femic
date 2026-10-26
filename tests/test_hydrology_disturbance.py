from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from femic.hydrology.disturbance import (
    DisturbanceLedger,
    DisturbanceUnit,
    HarvestEvent,
    HydrologyDisturbanceError,
    RoadEvent,
    build_disturbance_ledger,
    load_disturbance_ledger,
    load_disturbance_units_csv,
    load_harvest_events_csv,
    load_road_events_csv,
    validate_disturbance_ledger,
    write_disturbance_ledger,
    write_disturbance_ledger_csv,
)

GENERATED_UTC = "2026-10-25T00:00:00+00:00"


def _units() -> tuple[DisturbanceUnit, ...]:
    return (
        DisturbanceUnit("u1", 10.0, "w1", "h1"),
        DisturbanceUnit("u2", 20.0, "w1", "h2"),
    )


def _harvest() -> tuple[HarvestEvent, ...]:
    return (
        HarvestEvent("h1", "u1", 2020, 4.0, 1.0, "partial", "ws4"),
        HarvestEvent("h2", "u2", 2021, 5.0, 0.0, "clearcut", "ws4"),
    )


def _roads() -> tuple[RoadEvent, ...]:
    return (
        RoadEvent("r1b", "r1", "u1", 2020, "build", 1000.0, True, 1, "fhops"),
        RoadEvent("r2b", "r2", "u1", 2020, "build", 500.0, False, 0, "fhops"),
        RoadEvent("r2d", "r2", "u1", 2021, "decommission", 500.0, False, 0, "fhops"),
        RoadEvent("r1u", "r1", "u1", 2021, "use", 0.0, True, 0, "fhops"),
        RoadEvent("r1d", "r1", "u1", 2022, "decommission", 1000.0, True, 1, "fhops"),
    )


def _ledger() -> DisturbanceLedger:
    return build_disturbance_ledger(
        domain_id="domain-1",
        units=_units(),
        harvest_events=_harvest(),
        road_events=_roads(),
        years=(2020, 2021, 2022),
        generated_utc=GENERATED_UTC,
    )


def test_build_ledger_is_complete_and_tracks_road_state() -> None:
    ledger = _ledger()

    assert ledger.row_count == 6
    assert ledger.ledger_id.startswith("hydro-dist-")
    assert validate_disturbance_ledger(ledger).is_valid
    rows = {(row.year, row.unit_id): row for row in ledger.rows}
    first = rows[(2020, "u1")]
    assert first.harvest_area_ha == 4.0
    assert first.retention_area_ha == 1.0
    assert first.effective_harvest_area_ha == 3.0
    assert first.road_active_length_m == 1500.0
    assert first.road_connected_length_m == 1000.0
    assert first.road_built_length_m == 1500.0
    assert first.road_crossing_count == 1
    assert first.years_since_harvest == 0
    assert first.years_since_road_build == 0
    assert first.source_event_ids == ("h1", "r1b", "r2b")

    second = rows[(2021, "u1")]
    assert second.road_active_length_m == 1000.0
    assert second.road_decommissioned_length_m == 500.0
    assert second.years_since_harvest == 1
    assert second.years_since_road_build == 1

    third = rows[(2022, "u1")]
    assert third.road_active_length_m == 0.0
    assert third.road_connected_length_m == 0.0
    assert third.road_crossing_count == 0
    assert third.years_since_harvest == 2

    u2 = rows[(2020, "u2")]
    assert u2.years_since_harvest is None
    assert u2.years_since_road_build is None
    assert u2.harvest_area_ha == 0.0
    assert ledger.to_dict()["summary"]["row_count"] == 6


def test_ledger_id_is_deterministic() -> None:
    first = _ledger()
    second = _ledger()
    assert first.ledger_id == second.ledger_id


def test_write_load_and_csv_round_trip(tmp_path: Path) -> None:
    ledger = _ledger()
    json_path = write_disturbance_ledger(ledger, tmp_path / "ledger.json")
    csv_path = write_disturbance_ledger_csv(ledger, tmp_path / "ledger.csv")
    loaded = load_disturbance_ledger(json_path)

    assert loaded.to_dict() == ledger.to_dict()
    assert csv_path.read_text().startswith("year,unit_id,watershed_id")
    assert len(csv_path.read_text().splitlines()) == 7

    path = tmp_path / "bad.json"
    path.write_text('{"schema_version": "bad"}')
    with pytest.raises(HydrologyDisturbanceError, match="Unsupported"):
        load_disturbance_ledger(path)
    path.write_text("not-json")
    with pytest.raises(HydrologyDisturbanceError, match="Invalid JSON"):
        load_disturbance_ledger(path)
    path.write_text("[]")
    with pytest.raises(HydrologyDisturbanceError, match="JSON object"):
        load_disturbance_ledger(path)


def test_csv_loaders_build_same_ledger(tmp_path: Path) -> None:
    units = tmp_path / "units.csv"
    units.write_text("unit_id,area_ha,watershed_id,hru_id\nu1,10,w1,h1\nu2,20,w1,h2\n")
    harvest = tmp_path / "harvest.csv"
    harvest.write_text(
        "event_id,unit_id,year,area_ha,retention_area_ha,treatment,source\n"
        "h1,u1,2020,4,1,partial,ws4\n"
        "h2,u2,2021,5,0,clearcut,ws4\n"
    )
    roads = tmp_path / "roads.csv"
    roads.write_text(
        "event_id,road_id,unit_id,year,action,length_m,connected_to_stream,"
        "crossing_count,source\n"
        "r1b,r1,u1,2020,build,1000,true,1,fhops\n"
        "r2b,r2,u1,2020,build,500,false,0,fhops\n"
        "r2d,r2,u1,2021,decommission,500,false,0,fhops\n"
        "r1u,r1,u1,2021,use,0,true,0,fhops\n"
        "r1d,r1,u1,2022,decommission,1000,true,1,fhops\n"
    )

    ledger = build_disturbance_ledger(
        domain_id="domain-1",
        units=load_disturbance_units_csv(units),
        harvest_events=load_harvest_events_csv(harvest),
        road_events=load_road_events_csv(roads),
        years=(2020, 2021, 2022),
        generated_utc=GENERATED_UTC,
    )

    assert ledger.to_dict() == _ledger().to_dict()


def test_csv_bool_and_missing_file_errors(tmp_path: Path) -> None:
    bad = tmp_path / "bad.csv"
    bad.write_text(
        "event_id,road_id,unit_id,year,action,length_m,connected_to_stream\n"
        "e,r,u,2020,build,10,maybe\n"
    )
    with pytest.raises(HydrologyDisturbanceError, match="boolean"):
        load_road_events_csv(bad)
    with pytest.raises(HydrologyDisturbanceError, match="Unable to read CSV"):
        load_disturbance_units_csv(tmp_path / "missing.csv")


def test_unit_and_event_conservation_errors() -> None:
    with pytest.raises(HydrologyDisturbanceError, match="At least one"):
        build_disturbance_ledger(
            domain_id="d",
            units=(),
            harvest_events=(),
            road_events=(),
            years=(2020,),
        )
    with pytest.raises(HydrologyDisturbanceError, match="Duplicate unit"):
        build_disturbance_ledger(
            domain_id="d",
            units=(_units()[0], _units()[0]),
            harvest_events=(),
            road_events=(),
            years=(2020,),
        )
    with pytest.raises(HydrologyDisturbanceError, match="positive area"):
        build_disturbance_ledger(
            domain_id="d",
            units=(DisturbanceUnit("u", 0.0, "w"),),
            harvest_events=(),
            road_events=(),
            years=(2020,),
        )
    with pytest.raises(HydrologyDisturbanceError, match="watershed"):
        build_disturbance_ledger(
            domain_id="d",
            units=(DisturbanceUnit("u", 1.0, ""),),
            harvest_events=(),
            road_events=(),
            years=(2020,),
        )
    with pytest.raises(HydrologyDisturbanceError, match="unknown unit"):
        build_disturbance_ledger(
            domain_id="d",
            units=_units(),
            harvest_events=(HarvestEvent("h", "missing", 2020, 1.0),),
            road_events=(),
            years=(2020,),
        )
    with pytest.raises(HydrologyDisturbanceError, match="outside the ledger"):
        build_disturbance_ledger(
            domain_id="d",
            units=_units(),
            harvest_events=(HarvestEvent("h", "u1", 2019, 1.0),),
            road_events=(),
            years=(2020,),
        )
    with pytest.raises(HydrologyDisturbanceError, match="positive area"):
        build_disturbance_ledger(
            domain_id="d",
            units=_units(),
            harvest_events=(HarvestEvent("h", "u1", 2020, 0.0),),
            road_events=(),
            years=(2020,),
        )
    with pytest.raises(HydrologyDisturbanceError, match="retention"):
        build_disturbance_ledger(
            domain_id="d",
            units=_units(),
            harvest_events=(HarvestEvent("h", "u1", 2020, 1.0, 2.0),),
            road_events=(),
            years=(2020,),
        )
    with pytest.raises(HydrologyDisturbanceError, match="exceeds unit area"):
        build_disturbance_ledger(
            domain_id="d",
            units=_units(),
            harvest_events=(HarvestEvent("h", "u1", 2020, 11.0),),
            road_events=(),
            years=(2020,),
        )


def test_year_and_road_conservation_errors() -> None:
    with pytest.raises(HydrologyDisturbanceError, match="At least one ledger year"):
        build_disturbance_ledger(
            domain_id="d",
            units=_units(),
            harvest_events=(),
            road_events=(),
            years=(),
        )
    with pytest.raises(HydrologyDisturbanceError, match="Duplicate ledger year"):
        build_disturbance_ledger(
            domain_id="d",
            units=_units(),
            harvest_events=(),
            road_events=(),
            years=(2020, 2020),
        )
    with pytest.raises(HydrologyDisturbanceError, match="positive"):
        build_disturbance_ledger(
            domain_id="d",
            units=_units(),
            harvest_events=(),
            road_events=(),
            years=(0,),
        )
    with pytest.raises(HydrologyDisturbanceError, match="unsupported action"):
        build_disturbance_ledger(
            domain_id="d",
            units=_units(),
            harvest_events=(),
            road_events=(RoadEvent("e", "r", "u1", 2020, "bad"),),
            years=(2020,),
        )
    with pytest.raises(HydrologyDisturbanceError, match="positive length"):
        build_disturbance_ledger(
            domain_id="d",
            units=_units(),
            harvest_events=(),
            road_events=(RoadEvent("e", "r", "u1", 2020, "build", 0.0),),
            years=(2020,),
        )
    with pytest.raises(HydrologyDisturbanceError, match="spans multiple units"):
        build_disturbance_ledger(
            domain_id="d",
            units=_units(),
            harvest_events=(),
            road_events=(
                RoadEvent("e1", "r", "u1", 2020, "build", 1.0),
                RoadEvent("e2", "r", "u2", 2020, "decommission", 1.0),
            ),
            years=(2020,),
        )
    with pytest.raises(HydrologyDisturbanceError, match="already active"):
        build_disturbance_ledger(
            domain_id="d",
            units=_units(),
            harvest_events=(),
            road_events=(
                RoadEvent("e1", "r", "u1", 2020, "build", 1.0),
                RoadEvent("e2", "r", "u1", 2020, "build", 1.0),
            ),
            years=(2020,),
        )
    with pytest.raises(HydrologyDisturbanceError, match="exceeds active length"):
        build_disturbance_ledger(
            domain_id="d",
            units=_units(),
            harvest_events=(),
            road_events=(RoadEvent("e", "r", "u1", 2020, "decommission", 1.0),),
            years=(2020,),
        )
    with pytest.raises(HydrologyDisturbanceError, match="exceeds active crossings"):
        build_disturbance_ledger(
            domain_id="d",
            units=_units(),
            harvest_events=(),
            road_events=(
                RoadEvent("e1", "r", "u1", 2020, "build", 1.0),
                RoadEvent("e2", "r", "u1", 2020, "decommission", 1.0, False, 1),
            ),
            years=(2020,),
        )


def test_validation_catches_row_errors() -> None:
    ledger = _ledger()
    row = ledger.rows[0]
    broken_rows = (
        replace(row, harvest_area_ha=-1.0),
        replace(row, retention_area_ha=row.harvest_area_ha + 1.0),
        replace(row, harvest_area_ha=row.unit_area_ha + 1.0),
        replace(row, effective_harvest_area_ha=999.0),
        replace(row, road_active_length_m=-1.0),
        replace(row, road_connected_length_m=row.road_active_length_m + 1.0),
        replace(row, road_crossing_count=-1),
        replace(row, years_since_harvest=-1),
        replace(row, years_since_road_build=-1),
        replace(row, unit_id="missing"),
    )
    for broken_row in broken_rows:
        broken = replace(
            ledger,
            rows=(broken_row, *ledger.rows[1:]),
        )
        assert not validate_disturbance_ledger(broken).is_valid

    duplicate = replace(ledger, rows=(ledger.rows[0], *ledger.rows))
    assert any(
        "Duplicate ledger row" in error
        for error in validate_disturbance_ledger(duplicate).errors
    )
    missing = replace(ledger, rows=ledger.rows[:-1])
    assert any(
        "missing unit/year rows" in error
        for error in validate_disturbance_ledger(missing).errors
    )
    bad_ids = replace(ledger, ledger_id="", domain_id="", schema_version="bad")
    errors = validate_disturbance_ledger(bad_ids).errors
    assert any("Unsupported" in error for error in errors)
    assert any("Ledger ID" in error for error in errors)
    assert any("Domain ID" in error for error in errors)
    empty = replace(ledger, years=(), units=(), rows=())
    assert not validate_disturbance_ledger(empty).is_valid


def test_private_parsers_and_payload_helpers(tmp_path: Path) -> None:
    from femic.hydrology.disturbance import (
        _optional_float,
        _optional_int,
        _optional_mapping,
        _optional_str_list,
        _parse_bool,
        _read_csv_rows,
        _read_json_object,
        _required_float,
        _required_int,
        _required_int_value,
        _required_list,
        _required_str,
    )

    assert _optional_int(True) is None
    assert _optional_int("2") == 2
    assert _optional_int("x") is None
    assert _optional_int(object()) is None
    assert _optional_float(True) is None
    assert _optional_float("2.5") == 2.5
    assert _optional_float("x") is None
    assert _optional_float(object()) is None
    assert _optional_float(float("inf")) is None
    assert _optional_str_list(None, context="test") == ()
    with pytest.raises(HydrologyDisturbanceError, match="must be a list"):
        _optional_str_list("x", context="test")
    with pytest.raises(HydrologyDisturbanceError, match="must be strings"):
        _optional_str_list([1], context="test")
    assert _optional_mapping(None, context="test") == {}
    with pytest.raises(HydrologyDisturbanceError, match="must be an object"):
        _optional_mapping("x", context="test")
    assert _parse_bool(None, context="test") is False
    assert _parse_bool("yes", context="test") is True
    assert _parse_bool("0", context="test") is False
    with pytest.raises(HydrologyDisturbanceError, match="must be a list"):
        _required_list({"v": "x"}, "v", context="test")
    with pytest.raises(HydrologyDisturbanceError, match="non-empty string"):
        _required_str({"v": " "}, "v", context="test")
    with pytest.raises(HydrologyDisturbanceError, match="must be numeric"):
        _required_float({"v": "x"}, "v", context="test")
    with pytest.raises(HydrologyDisturbanceError, match="must be an integer"):
        _required_int({"v": "x"}, "v", context="test")
    with pytest.raises(HydrologyDisturbanceError, match="must be integers"):
        _required_int_value("x", context="test")
    with pytest.raises(HydrologyDisturbanceError, match="Unable to read"):
        _read_json_object(tmp_path / "missing.json", context="test")
    invalid = tmp_path / "invalid.json"
    invalid.write_text("not-json")
    with pytest.raises(HydrologyDisturbanceError, match="Invalid JSON"):
        _read_json_object(invalid, context="test")
    array = tmp_path / "array.json"
    array.write_text("[]")
    with pytest.raises(HydrologyDisturbanceError, match="JSON object"):
        _read_json_object(array, context="test")
    empty_csv = tmp_path / "empty.csv"
    empty_csv.write_text("")
    assert _read_csv_rows(empty_csv) == ()


def test_csv_loader_validation_errors(tmp_path: Path) -> None:
    with pytest.raises(HydrologyDisturbanceError, match="non-empty string"):
        load_disturbance_units_csv(
            _csv(tmp_path / "bad_units.csv", "unit_id,area_ha,watershed_id\n,10,w1\n")
        )
    harvest = _csv(
        tmp_path / "harvest.csv",
        "event_id,unit_id,year,area_ha\nh1,u1,x,1\n",
    )
    with pytest.raises(HydrologyDisturbanceError, match="integer"):
        load_harvest_events_csv(harvest)


def _csv(path: Path, text: str) -> Path:
    path.write_text(text)
    return path


def test_payload_helpers_and_more_conservation_errors() -> None:
    from femic.hydrology.disturbance import (
        _mapping_from_object,
        _optional_str,
        _optional_str_list,
        _parse_bool,
    )

    assert HarvestEvent("h", "u", 2020, 1.0).to_dict()["event_id"] == "h"
    assert (
        RoadEvent("r", "road", "u", 2020, "build", 1.0).to_dict()["road_id"] == "road"
    )
    assert validate_disturbance_ledger(_ledger()).to_dict()["is_valid"] is True
    with pytest.raises(HydrologyDisturbanceError, match="Domain ID"):
        build_disturbance_ledger(
            domain_id=" ",
            units=_units(),
            harvest_events=(),
            road_events=(),
            years=(2020,),
        )
    ledger = _ledger()
    duplicate_units = replace(ledger, units=(ledger.units[0], ledger.units[0]))
    assert any(
        "duplicate unit ids" in error.lower()
        for error in validate_disturbance_ledger(duplicate_units).errors
    )
    with pytest.raises(HydrologyDisturbanceError, match="integers"):
        build_disturbance_ledger(
            domain_id="d",
            units=_units(),
            harvest_events=(),
            road_events=(),
            years=(True,),
        )
    with pytest.raises(HydrologyDisturbanceError, match="Unit ID"):
        build_disturbance_ledger(
            domain_id="d",
            units=(DisturbanceUnit(" ", 1.0, "w"),),
            harvest_events=(),
            road_events=(),
            years=(2020,),
        )
    with pytest.raises(HydrologyDisturbanceError, match="Harvest event ID"):
        build_disturbance_ledger(
            domain_id="d",
            units=_units(),
            harvest_events=(HarvestEvent(" ", "u1", 2020, 1.0),),
            road_events=(),
            years=(2020,),
        )
    with pytest.raises(HydrologyDisturbanceError, match="Duplicate harvest"):
        build_disturbance_ledger(
            domain_id="d",
            units=_units(),
            harvest_events=(
                HarvestEvent("h", "u1", 2020, 1.0),
                HarvestEvent("h", "u1", 2020, 1.0),
            ),
            road_events=(),
            years=(2020,),
        )
    with pytest.raises(HydrologyDisturbanceError, match="negative retention"):
        build_disturbance_ledger(
            domain_id="d",
            units=_units(),
            harvest_events=(HarvestEvent("h", "u1", 2020, 1.0, -1.0),),
            road_events=(),
            years=(2020,),
        )
    with pytest.raises(HydrologyDisturbanceError, match="Road event ID"):
        build_disturbance_ledger(
            domain_id="d",
            units=_units(),
            harvest_events=(),
            road_events=(RoadEvent(" ", "r", "u1", 2020, "build", 1.0),),
            years=(2020,),
        )
    with pytest.raises(HydrologyDisturbanceError, match="Duplicate road"):
        build_disturbance_ledger(
            domain_id="d",
            units=_units(),
            harvest_events=(),
            road_events=(
                RoadEvent("e", "r", "u1", 2020, "build", 1.0),
                RoadEvent("e", "r", "u1", 2020, "build", 1.0),
            ),
            years=(2020,),
        )
    with pytest.raises(HydrologyDisturbanceError, match="unknown unit"):
        build_disturbance_ledger(
            domain_id="d",
            units=_units(),
            harvest_events=(),
            road_events=(RoadEvent("e", "r", "missing", 2020, "build", 1.0),),
            years=(2020,),
        )
    with pytest.raises(HydrologyDisturbanceError, match="outside the ledger"):
        build_disturbance_ledger(
            domain_id="d",
            units=_units(),
            harvest_events=(),
            road_events=(RoadEvent("e", "r", "u1", 2019, "build", 1.0),),
            years=(2020,),
        )
    with pytest.raises(HydrologyDisturbanceError, match="connected length"):
        build_disturbance_ledger(
            domain_id="d",
            units=_units(),
            harvest_events=(),
            road_events=(
                RoadEvent("e1", "r", "u1", 2020, "build", 1.0, False),
                RoadEvent("e2", "r", "u1", 2020, "decommission", 1.0, True),
            ),
            years=(2020,),
        )
    assert _parse_bool(True, context="test") is True
    with pytest.raises(HydrologyDisturbanceError, match="must be an object"):
        _mapping_from_object("x", context="test")
    assert _optional_str(1) is None
    assert _optional_str_list(["a", "b"], context="test") == ("a", "b")
    assert build_disturbance_ledger(
        domain_id="d",
        units=_units(),
        harvest_events=(),
        road_events=(),
        years=(2020,),
    ).generated_utc


def test_negative_road_length_and_crossings_are_rejected() -> None:
    with pytest.raises(HydrologyDisturbanceError, match="invalid length"):
        build_disturbance_ledger(
            domain_id="d",
            units=_units(),
            harvest_events=(),
            road_events=(RoadEvent("e", "r", "u1", 2020, "use", -1.0),),
            years=(2020,),
        )
    with pytest.raises(HydrologyDisturbanceError, match="negative crossings"):
        build_disturbance_ledger(
            domain_id="d",
            units=_units(),
            harvest_events=(),
            road_events=(RoadEvent("e", "r", "u1", 2020, "use", 0.0, False, -1),),
            years=(2020,),
        )
