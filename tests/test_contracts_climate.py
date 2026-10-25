"""Tests for the ``femic.climate.v1`` contract."""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import pytest

from femic.contracts.climate import (
    CLIMATE_SCHEMA_VERSION,
    ClimateContractError,
    ClimateRecord,
    climate_schema,
    read_climate_table,
    summarize_climate_table,
    validate_climate_record,
    write_climate_table,
)

FIXTURE = Path(__file__).parent / "fixtures" / "contracts" / "climate_v1_sample.csv"


def _sample_records() -> tuple[ClimateRecord, ...]:
    return read_climate_table(FIXTURE)


def _record_dict() -> dict[str, object]:
    return _sample_records()[0].to_dict()


def test_sample_table_reads_and_summarizes() -> None:
    records = _sample_records()

    assert len(records) == 4
    assert records[0].aoi_id == "north-island"
    assert records[0].variable == "tavg"
    assert records[0].unit == "degC"
    assert records[0].scenario == "historical"
    assert records[0].variance == pytest.approx(0.12)

    summary = summarize_climate_table(records)
    assert summary["schema_version"] == CLIMATE_SCHEMA_VERSION
    assert summary["record_count"] == 4
    assert summary["aoi_ids"] == ["north-island"]
    assert summary["variables"] == ["ppt", "tavg", "tmin"]
    assert summary["scenarios"] == ["historical", "ssp245"]
    assert summary["year_min"] == 2020
    assert summary["year_max"] == 2050
    assert summary["sources"] == [
        {
            "source_id": "contract-fixture",
            "source_version": "1.0",
            "downscaling_method": "none",
        }
    ]
    assert summary["retrieved_utc_min"] == "2026-10-25T00:00:00+00:00"


def test_csv_round_trip_is_identical(tmp_path: Path) -> None:
    records = _sample_records()
    target = tmp_path / "climate.csv"

    write_climate_table(target, records)

    assert read_climate_table(target) == records


def test_json_round_trip_is_identical(tmp_path: Path) -> None:
    records = _sample_records()
    target = tmp_path / "climate.json"

    write_climate_table(target, records)

    assert read_climate_table(target) == records


def test_json_object_with_records_is_accepted(tmp_path: Path) -> None:
    records = _sample_records()
    target = tmp_path / "climate.json"
    target.write_text(
        json.dumps({"records": [record.to_dict() for record in records]}),
        encoding="utf-8",
    )

    assert read_climate_table(target) == records


def test_missing_scenario_is_rejected() -> None:
    record = _record_dict()
    record.pop("scenario")

    with pytest.raises(ClimateContractError, match="missing climate fields: scenario"):
        validate_climate_record(record)


def test_unknown_unit_is_rejected() -> None:
    record = _record_dict()
    record["unit"] = "K"

    with pytest.raises(ClimateContractError, match="unit for 'tavg'"):
        validate_climate_record(record)


def test_unknown_variable_is_rejected() -> None:
    record = _record_dict()
    record["variable"] = "not-a-variable"

    with pytest.raises(ClimateContractError, match="variable must be one of"):
        validate_climate_record(record)


def test_negative_variance_is_rejected() -> None:
    record = _record_dict()
    record["variance"] = -0.1

    with pytest.raises(ClimateContractError, match="variance must be non-negative"):
        validate_climate_record(record)


def test_non_finite_value_is_rejected() -> None:
    record = _record_dict()
    record["value"] = math.nan

    with pytest.raises(ClimateContractError, match="value must be finite"):
        validate_climate_record(record)


def test_year_out_of_range_is_rejected() -> None:
    record = _record_dict()
    record["year"] = 1800

    with pytest.raises(ClimateContractError, match="year must be between"):
        validate_climate_record(record)


def test_timestamp_requires_timezone() -> None:
    record = _record_dict()
    record["retrieved_utc"] = "2026-10-25T00:00:00"

    with pytest.raises(ClimateContractError, match="must include a timezone"):
        validate_climate_record(record)


def test_schema_version_is_exact() -> None:
    record = _record_dict()
    record["schema_version"] = "femic.climate.v2"

    with pytest.raises(ClimateContractError, match="schema_version must be"):
        validate_climate_record(record)


def test_unknown_field_is_rejected() -> None:
    record = _record_dict()
    record["extra"] = "nope"

    with pytest.raises(ClimateContractError, match="unknown climate fields: extra"):
        validate_climate_record(record)


def test_csv_missing_column_is_rejected(tmp_path: Path) -> None:
    target = tmp_path / "broken.csv"
    with target.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["schema_version", "aoi_id"])
        writer.writeheader()
        writer.writerow(
            {"schema_version": CLIMATE_SCHEMA_VERSION, "aoi_id": "north-island"}
        )

    with pytest.raises(ClimateContractError, match="missing columns"):
        read_climate_table(target)


def test_empty_table_is_rejected(tmp_path: Path) -> None:
    target = tmp_path / "empty.json"
    target.write_text("[]", encoding="utf-8")

    with pytest.raises(ClimateContractError, match="contains no climate records"):
        read_climate_table(target)


def test_schema_is_a_defensive_copy() -> None:
    first = climate_schema()
    first["title"] = "mutated"

    assert climate_schema()["title"] == "FEMIC climate.v1 record"
    required = climate_schema()["required"]
    assert isinstance(required, list)
    assert "scenario" in required
    assert "retrieved_utc" in required
