"""Tests for the ClimateNA CSV adapter."""

from __future__ import annotations

import csv
from collections.abc import Mapping
from pathlib import Path

import pytest

from femic.contracts.climate import (
    ClimateContractError,
    read_climate_table,
    write_climate_table,
)
from femic.contracts.climate_na import (
    DEFAULT_CLIMATE_NA_COLUMNS,
    climate_na_columns,
    read_climate_na_csv,
)

FIXTURE = (
    Path(__file__).parent / "fixtures" / "contracts" / "climate_na_annual_sample.csv"
)


def _read(
    path: Path = FIXTURE,
    *,
    aoi_id: str = "north-island",
    year: int = 2050,
    scenario: str = "ssp245",
    gcm: str = "synthetic-ensemble",
    source_version: str = "fixture-1.0",
    retrieved_utc: str = "2026-10-25T00:00:00+00:00",
    notes: str | None = "Synthetic ClimateNA-shaped fixture.",
    column_map: Mapping[str, tuple[str, str]] | None = None,
    require_all_columns: bool = False,
):
    return read_climate_na_csv(
        path,
        aoi_id=aoi_id,
        year=year,
        scenario=scenario,
        gcm=gcm,
        source_version=source_version,
        retrieved_utc=retrieved_utc,
        notes=notes,
        column_map=column_map,
        require_all_columns=require_all_columns,
    )


def test_adapter_emits_one_record_per_mapped_cell() -> None:
    records = _read()

    assert len(records) == 22
    variables = {record.variable for record in records}
    assert "tavg" in variables
    assert "ppt" in variables
    assert "mwmt" in variables
    assert "mcmt" in variables
    assert "gdd" in variables
    assert "nffd" in variables
    assert "snow" in variables
    assert "cwd" in variables
    assert "pet" in variables
    assert "rh" in variables
    assert "vpd" in variables

    first = records[0]
    assert first.aoi_id == "north-island:site-1"
    assert first.variable == "tavg"
    assert first.unit == "degC"
    assert first.value == pytest.approx(8.4)
    assert first.year == 2050
    assert first.scenario == "ssp245"
    assert first.gcm == "synthetic-ensemble"
    assert first.source_id == "climate-na"
    assert first.source_version == "fixture-1.0"
    assert first.downscaling_method == "climate-na"
    assert first.notes is not None
    assert "source_column=MAT" in first.notes


def test_single_row_uses_base_aoi_id(tmp_path: Path) -> None:
    rows = list(csv.DictReader(FIXTURE.open(encoding="utf-8-sig")))
    target = tmp_path / "single.csv"
    with target.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerow(rows[0])

    records = _read(target)

    assert len(records) == 11
    assert all(record.aoi_id == "north-island" for record in records)


def test_custom_column_map_limits_the_output() -> None:
    records = _read(
        column_map={"MAT": ("tavg", "degC"), "MAP": ("ppt", "mm")},
        require_all_columns=True,
    )

    assert len(records) == 4
    assert {record.variable for record in records} == {"tavg", "ppt"}


def test_required_missing_column_is_rejected() -> None:
    with pytest.raises(ClimateContractError, match="missing mapped columns"):
        _read(
            column_map={
                "MAT": ("tavg", "degC"),
                "NOT_A_COLUMN": ("ppt", "mm"),
            },
            require_all_columns=True,
        )


def test_non_numeric_value_is_rejected(tmp_path: Path) -> None:
    target = tmp_path / "bad.csv"
    target.write_text(
        "ID,MAT\nsite-1,not-a-number\n",
        encoding="utf-8",
    )

    with pytest.raises(ClimateContractError, match="not numeric"):
        _read(target)


def test_missing_values_are_skipped(tmp_path: Path) -> None:
    target = tmp_path / "missing.csv"
    target.write_text(
        "ID,MAT,MAP\nsite-1,8.4,NA\n",
        encoding="utf-8",
    )

    records = _read(target)

    assert len(records) == 1
    assert records[0].variable == "tavg"


def test_all_missing_values_are_rejected(tmp_path: Path) -> None:
    target = tmp_path / "missing.csv"
    target.write_text(
        "ID,MAT\nsite-1,NA\n",
        encoding="utf-8",
    )

    with pytest.raises(ClimateContractError, match="produced no climate records"):
        _read(target)


def test_unknown_scenario_is_rejected() -> None:
    with pytest.raises(ClimateContractError, match="scenario must be one of"):
        _read(scenario="not-a-scenario")


def test_adapter_output_round_trips_through_the_table_contract(tmp_path: Path) -> None:
    records = _read()
    target = tmp_path / "climate.csv"

    write_climate_table(target, records)

    assert read_climate_table(target) == records


def test_default_map_is_canonical() -> None:
    for variable, unit in DEFAULT_CLIMATE_NA_COLUMNS.values():
        assert variable in {
            "tavg",
            "ppt",
            "mwmt",
            "mcmt",
            "gdd",
            "nffd",
            "snow",
            "cwd",
            "pet",
            "rh",
            "vpd",
        }
        assert unit


def test_column_map_copy_is_defensive() -> None:
    first = climate_na_columns()
    first["MAT"] = ("ppt", "mm")

    assert climate_na_columns()["MAT"] == ("tavg", "degC")
