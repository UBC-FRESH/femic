"""Tests for the climate consumer that attaches values to attribute rows."""

from __future__ import annotations

from pathlib import Path

import pytest

from femic.climate.consumer import (
    ClimateConsumerError,
    ClimateContext,
    attach_climate_context,
    attach_climate_to_rows,
    select_climate_context,
)
from femic.contracts.climate import (
    ClimateRecord,
    read_climate_table,
    write_climate_table,
)

FIXTURE = (
    Path(__file__).parent / "fixtures" / "contracts" / "climate_consumer_sample.csv"
)


def _records() -> tuple[ClimateRecord, ...]:
    return read_climate_table(FIXTURE)


def _context() -> ClimateContext:
    return select_climate_context(
        _records(),
        aoi_id="north-island",
        scenario="ssp245",
        year=2050,
        variables=["tavg", "ppt"],
    )


def test_select_context_returns_values_and_provenance() -> None:
    context = _context()

    assert context.aoi_id == "north-island"
    assert context.scenario == "ssp245"
    assert context.year == 2050
    assert context.gcm == "synthetic-ensemble"
    assert context.values == {"tavg": pytest.approx(10.1), "ppt": pytest.approx(1420.0)}
    assert context.units == {"tavg": "degC", "ppt": "mm"}
    assert context.source_id == "climate-fixture"
    assert context.source_version == "1.0"
    assert context.downscaling_method == "none"
    assert context.retrieved_utc == "2026-10-26T00:00:00+00:00"
    assert context.to_dict()["values"] == {
        "tavg": pytest.approx(10.1),
        "ppt": pytest.approx(1420.0),
    }


def test_variable_order_and_duplicates_are_preserved_or_collapsed() -> None:
    context = select_climate_context(
        _records(),
        aoi_id="south-island",
        scenario="ssp245",
        year=2050,
        variables=["ppt", "ppt", "tavg"],
    )

    assert list(context.values) == ["ppt", "tavg"]
    assert context.values["tavg"] == pytest.approx(12.3)


def test_missing_variable_is_rejected() -> None:
    with pytest.raises(ClimateConsumerError, match="missing variable"):
        select_climate_context(
            _records(),
            aoi_id="north-island",
            scenario="ssp245",
            year=2050,
            variables=["tavg", "vpd"],
        )


def test_missing_selection_is_rejected() -> None:
    with pytest.raises(ClimateConsumerError, match="no climate records"):
        select_climate_context(
            _records(),
            aoi_id="north-island",
            scenario="historical",
            year=2050,
            variables=["tavg"],
        )


def test_ambiguous_gcm_requires_a_choice(tmp_path: Path) -> None:
    records = list(_records())
    duplicate = records[0].to_dict()
    duplicate["gcm"] = "other-ensemble"
    records.append(ClimateRecord.from_dict(duplicate))
    target = tmp_path / "ambiguous.csv"
    write_climate_table(target, records)
    table = read_climate_table(target)

    with pytest.raises(ClimateConsumerError, match="ambiguous across GCMs"):
        select_climate_context(
            table,
            aoi_id="north-island",
            scenario="ssp245",
            year=2050,
            variables=["tavg"],
        )

    context = select_climate_context(
        table,
        aoi_id="north-island",
        scenario="ssp245",
        year=2050,
        variables=["tavg"],
        gcm="other-ensemble",
    )
    assert context.gcm == "other-ensemble"


def test_multiple_sources_are_rejected(tmp_path: Path) -> None:
    records = [
        record
        for record in _records()
        if not (record.aoi_id == "north-island" and record.variable == "ppt")
    ]
    ppt_record = next(
        record
        for record in _records()
        if record.aoi_id == "north-island" and record.variable == "ppt"
    )
    duplicate = ppt_record.to_dict()
    duplicate["source_id"] = "other-source"
    records.append(ClimateRecord.from_dict(duplicate))
    target = tmp_path / "mixed.csv"
    write_climate_table(target, records)

    with pytest.raises(ClimateConsumerError, match="mixes sources"):
        select_climate_context(
            read_climate_table(target),
            aoi_id="north-island",
            scenario="ssp245",
            year=2050,
            variables=["tavg", "ppt"],
        )


def test_attach_climate_context_adds_values_without_mutating_rows() -> None:
    rows = [{"fragment_id": 1}, {"fragment_id": 2}]

    attached = attach_climate_context(rows, _context())

    assert attached[0]["fragment_id"] == 1
    assert attached[0]["climate_tavg"] == pytest.approx(10.1)
    assert attached[0]["climate_tavg_unit"] == "degC"
    assert attached[0]["climate_ppt"] == pytest.approx(1420.0)
    assert attached[0]["climate_aoi_id"] == "north-island"
    assert attached[0]["climate_source_id"] == "climate-fixture"
    assert rows[0] == {"fragment_id": 1}


def test_attach_climate_context_supports_a_custom_prefix() -> None:
    attached = attach_climate_context(
        [{"fragment_id": 1}], _context(), prefix="future_"
    )

    assert attached[0]["future_tavg"] == pytest.approx(10.1)
    assert attached[0]["future_aoi_id"] == "north-island"


def test_attach_climate_to_rows_resolves_per_row_aoi() -> None:
    rows = [
        {"fragment_id": 1, "aoi_id": "north-island"},
        {"fragment_id": 2, "aoi_id": "south-island"},
    ]

    attached = attach_climate_to_rows(
        rows,
        _records(),
        scenario="ssp245",
        year=2050,
        variables=["tavg"],
    )

    assert attached[0]["climate_tavg"] == pytest.approx(10.1)
    assert attached[1]["climate_tavg"] == pytest.approx(12.3)


def test_attach_climate_to_rows_uses_default_aoi() -> None:
    attached = attach_climate_to_rows(
        [{"fragment_id": 1}],
        _records(),
        scenario="ssp245",
        year=2050,
        variables=["ppt"],
        default_aoi_id="north-island",
    )

    assert attached[0]["climate_ppt"] == pytest.approx(1420.0)


def test_attach_climate_to_rows_requires_an_aoi() -> None:
    with pytest.raises(ClimateConsumerError, match="has no 'aoi_id'"):
        attach_climate_to_rows(
            [{"fragment_id": 1}],
            _records(),
            scenario="ssp245",
            year=2050,
            variables=["tavg"],
        )


def test_attach_climate_to_rows_rejects_empty_variables() -> None:
    with pytest.raises(ClimateConsumerError, match="variables must not be empty"):
        attach_climate_to_rows(
            [{"fragment_id": 1, "aoi_id": "north-island"}],
            _records(),
            scenario="ssp245",
            year=2050,
            variables=[],
        )


def test_attach_climate_context_rejects_a_non_mapping_row() -> None:
    with pytest.raises(ClimateConsumerError, match="must be a mapping"):
        attach_climate_context([object()], _context())  # type: ignore[list-item]
