"""Tests for the ``femic.disturbance.v1`` contract."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from femic.contracts.disturbance import (
    DISTURBANCE_SCHEMA_VERSION,
    DisturbanceContractError,
    DisturbanceEvent,
    consumer_rows,
    disturbance_schema,
    events_for_block,
    read_disturbance_table,
    summarize_disturbance_table,
    validate_disturbance_event,
    write_disturbance_table,
)

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "contracts"
FIRE_FIXTURE = FIXTURE_ROOT / "disturbance_v1_fire.json"
NSR_FIXTURE = FIXTURE_ROOT / "disturbance_v1_nsr.json"


def _fire() -> DisturbanceEvent:
    return read_disturbance_table(FIRE_FIXTURE)[0]


def _nsr() -> DisturbanceEvent:
    return read_disturbance_table(NSR_FIXTURE)[0]


def _event_dict() -> dict[str, object]:
    return _fire().to_dict()


def test_fire_example_reads() -> None:
    event = _fire()

    assert event.event_id == "fire-2023-001"
    assert event.event_type == "fire"
    assert event.year == 2023
    assert event.severity_class == "high"
    assert event.severity_value == pytest.approx(0.82)
    assert event.severity_basis == "dNBR"
    assert event.confidence == pytest.approx(0.95)
    assert event.fragment_ids == (1001, 1002)
    assert event.block_ids == (101,)
    assert event.area_ha == pytest.approx(1200.0)
    assert event.geometry is not None
    assert event.geometry["type"] == "Polygon"


def test_nsr_example_reads_with_fragment_reference() -> None:
    event = _nsr()

    assert event.event_type == "partial_mortality"
    assert event.geometry is None
    assert event.fragment_ids == (2001,)
    assert event.block_ids == (201,)
    assert event.severity_value == pytest.approx(0.35)


def test_json_round_trip_is_identical(tmp_path: Path) -> None:
    events = (_fire(), _nsr())
    target = tmp_path / "disturbance.json"

    write_disturbance_table(target, events)

    assert read_disturbance_table(target) == events


def test_json_object_with_events_is_accepted(tmp_path: Path) -> None:
    events = (_fire(), _nsr())
    target = tmp_path / "disturbance.json"
    target.write_text(
        json.dumps({"events": [event.to_dict() for event in events]}),
        encoding="utf-8",
    )

    assert read_disturbance_table(target) == events


def test_summary_reports_provenance() -> None:
    summary = summarize_disturbance_table((_fire(), _nsr()))

    assert summary["schema_version"] == DISTURBANCE_SCHEMA_VERSION
    assert summary["event_count"] == 2
    assert summary["event_types"] == ["fire", "partial_mortality"]
    assert summary["severity_classes"] == ["high", "moderate"]
    assert summary["year_min"] == 2022
    assert summary["year_max"] == 2023
    assert summary["total_area_ha"] == pytest.approx(1245.5)
    assert summary["attributions"] == ["drought", "wildfire"]
    assert summary["events_with_geometry"] == 1
    assert summary["events_with_fragment_ids"] == 2
    assert summary["events_with_block_ids"] == 2


def test_consumer_rows_are_flat_and_include_year_and_type() -> None:
    rows = consumer_rows((_fire(), _nsr()))

    assert rows[0]["event_id"] == "fire-2023-001"
    assert rows[0]["event_type"] == "fire"
    assert rows[0]["year"] == 2023
    assert rows[0]["block_ids"] == [101]
    assert rows[1]["event_type"] == "partial_mortality"
    assert rows[1]["year"] == 2022


def test_events_for_block_selects_direct_block_ids() -> None:
    selected = events_for_block((_fire(), _nsr()), 201)

    assert selected == (_nsr(),)


def test_missing_event_type_is_rejected() -> None:
    event = _event_dict()
    event.pop("event_type")

    with pytest.raises(
        DisturbanceContractError, match="missing disturbance fields: event_type"
    ):
        validate_disturbance_event(event)


def test_unknown_event_type_is_rejected() -> None:
    event = _event_dict()
    event["event_type"] = "meteor"

    with pytest.raises(DisturbanceContractError, match="event_type must be one of"):
        validate_disturbance_event(event)


def test_probability_fields_are_bounded() -> None:
    event = _event_dict()
    event["confidence"] = 1.2

    with pytest.raises(DisturbanceContractError, match="confidence must be between"):
        validate_disturbance_event(event)


def test_severity_value_requires_a_basis() -> None:
    event = _event_dict()
    event["severity_basis"] = None

    with pytest.raises(DisturbanceContractError, match="severity_basis is required"):
        validate_disturbance_event(event)


def test_negative_area_is_rejected() -> None:
    event = _event_dict()
    event["area_ha"] = -1.0

    with pytest.raises(DisturbanceContractError, match="area_ha must be non-negative"):
        validate_disturbance_event(event)


def test_event_needs_a_spatial_reference() -> None:
    event = _event_dict()
    event["geometry"] = None
    event["fragment_ids"] = None
    event["block_ids"] = None

    with pytest.raises(
        DisturbanceContractError, match="geometry, fragment_ids, or block_ids"
    ):
        validate_disturbance_event(event)


def test_geometry_requires_coordinates() -> None:
    event = _event_dict()
    event["geometry"] = {"type": "Polygon"}

    with pytest.raises(DisturbanceContractError, match="geometry.coordinates"):
        validate_disturbance_event(event)


def test_timestamp_requires_timezone() -> None:
    event = _event_dict()
    event["retrieved_utc"] = "2026-10-25T00:00:00"

    with pytest.raises(DisturbanceContractError, match="must include a timezone"):
        validate_disturbance_event(event)


def test_duplicate_event_ids_are_rejected(tmp_path: Path) -> None:
    target = tmp_path / "duplicate.json"
    payload = [_fire().to_dict(), _fire().to_dict()]
    target.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(DisturbanceContractError, match="duplicate event ids"):
        read_disturbance_table(target)


def test_unknown_field_is_rejected() -> None:
    event = _event_dict()
    event["extra"] = "nope"

    with pytest.raises(
        DisturbanceContractError, match="unknown disturbance fields: extra"
    ):
        validate_disturbance_event(event)


def test_schema_is_a_defensive_copy() -> None:
    first = disturbance_schema()
    first["title"] = "mutated"

    assert disturbance_schema()["title"] == "FEMIC disturbance.v1 event"
    required = disturbance_schema()["required"]
    assert isinstance(required, list)
    assert "event_type" in required
    assert "retrieved_utc" in required
