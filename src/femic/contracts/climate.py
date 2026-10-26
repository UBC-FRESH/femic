"""Versioned climate-table contract for the FRESH modelling ecosystem.

This module owns the ``femic.climate.v1`` record contract: the canonical
climate table that FEMIC, ws3, ws4, and Nemora exchange. It validates units,
scenarios, timestamps, and provenance before a consumer can use a value.

The contract is deliberately narrow. It does not download ClimateNA data,
select a GCM ensemble, or model climate. The adapter that produces a table is a
separate concern; this module defines what a valid table is.
"""

from __future__ import annotations

import copy
import csv
import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

CLIMATE_SCHEMA_VERSION = "femic.climate.v1"

#: Canonical variable names and their required units. Adapters convert source
#: units to these before writing a table.
CLIMATE_VARIABLES: dict[str, str] = {
    "tavg": "degC",
    "tmax": "degC",
    "tmin": "degC",
    "mat": "degC",
    "mwmt": "degC",
    "mcmt": "degC",
    "ppt": "mm",
    "prcp": "mm",
    "map": "mm",
    "snow": "mm",
    "cwd": "mm",
    "pet": "mm",
    "rh": "percent",
    "vpd": "kPa",
    "gdd": "degree_days",
    "nffd": "days",
}

#: Accepted scenario labels. ``rcp*`` labels are retained for ClimateNA v6/v7
#: outputs; ``ssp*`` labels are the CMIP6 generation.
CLIMATE_SCENARIOS: frozenset[str] = frozenset(
    {
        "historical",
        "rcp26",
        "rcp45",
        "rcp60",
        "rcp85",
        "ssp126",
        "ssp245",
        "ssp370",
        "ssp585",
    }
)

CLIMATE_MIN_YEAR = 1900
CLIMATE_MAX_YEAR = 2300

CLIMATE_REQUIRED_FIELDS: tuple[str, ...] = (
    "schema_version",
    "aoi_id",
    "variable",
    "unit",
    "year",
    "scenario",
    "gcm",
    "value",
    "source_id",
    "source_version",
    "downscaling_method",
    "retrieved_utc",
)
CLIMATE_OPTIONAL_FIELDS: tuple[str, ...] = ("variance", "notes")
CLIMATE_ALLOWED_FIELDS: frozenset[str] = frozenset(
    CLIMATE_REQUIRED_FIELDS + CLIMATE_OPTIONAL_FIELDS
)
CLIMATE_CSV_FIELDS: tuple[str, ...] = CLIMATE_REQUIRED_FIELDS + CLIMATE_OPTIONAL_FIELDS


class ClimateContractError(ValueError):
    """Raised when a climate record or table violates ``femic.climate.v1``."""


def _require_text(value: object, field: str) -> str:
    """Return a non-empty string, or raise a contract error."""
    if not isinstance(value, str) or not value.strip():
        raise ClimateContractError(f"{field} must be a non-empty string")
    return value.strip()


def _require_int(value: object, field: str) -> int:
    """Return an integer, rejecting booleans and non-integers."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ClimateContractError(f"{field} must be an integer")
    return value


def _require_number(value: object, field: str) -> float:
    """Return a finite number, rejecting booleans, NaN, and infinity."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ClimateContractError(f"{field} must be a number")
    number = float(value)
    if not math.isfinite(number):
        raise ClimateContractError(f"{field} must be finite")
    return number


def _require_timestamp(value: object, field: str) -> datetime:
    """Return a timezone-aware ISO-8601 timestamp."""
    text = _require_text(value, field)
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ClimateContractError(f"{field} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise ClimateContractError(f"{field} must include a timezone")
    return parsed


def _build_schema() -> dict[str, object]:
    """Build the JSON Schema document for a climate record."""
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://femic.ubc.ca/schemas/climate.v1.json",
        "title": "FEMIC climate.v1 record",
        "type": "object",
        "additionalProperties": False,
        "required": list(CLIMATE_REQUIRED_FIELDS),
        "properties": {
            "schema_version": {"const": CLIMATE_SCHEMA_VERSION},
            "aoi_id": {"type": "string", "minLength": 1},
            "variable": {"type": "string", "enum": sorted(CLIMATE_VARIABLES)},
            "unit": {"type": "string", "enum": sorted(set(CLIMATE_VARIABLES.values()))},
            "year": {
                "type": "integer",
                "minimum": CLIMATE_MIN_YEAR,
                "maximum": CLIMATE_MAX_YEAR,
            },
            "scenario": {"type": "string", "enum": sorted(CLIMATE_SCENARIOS)},
            "gcm": {"type": "string", "minLength": 1},
            "value": {"type": "number"},
            "variance": {"type": ["number", "null"], "minimum": 0},
            "source_id": {"type": "string", "minLength": 1},
            "source_version": {"type": "string", "minLength": 1},
            "downscaling_method": {"type": "string", "minLength": 1},
            "retrieved_utc": {"type": "string", "format": "date-time"},
            "notes": {"type": ["string", "null"]},
        },
    }


#: JSON Schema for one ``femic.climate.v1`` record. Call :func:`climate_schema`
#: for a defensive copy.
CLIMATE_SCHEMA: dict[str, object] = _build_schema()


def climate_schema() -> dict[str, object]:
    """Return a defensive copy of the ``femic.climate.v1`` JSON Schema.

    Returns
    -------
    dict[str, object]
        A copy of the schema document, safe for a caller to mutate.
    """
    return copy.deepcopy(CLIMATE_SCHEMA)


def validate_climate_record(record: Mapping[str, object]) -> None:
    """Validate one climate record against ``femic.climate.v1``.

    Parameters
    ----------
    record : mapping[str, object]
        Candidate record.

    Raises
    ------
    ClimateContractError
        If the record is not a mapping, has unknown or missing fields, carries
        an unsupported variable or scenario, has a unit that does not match the
        variable, has an out-of-range year, or has an invalid value, variance,
        or timestamp.
    """
    if not isinstance(record, Mapping):
        raise ClimateContractError("climate record must be a mapping")

    unknown = set(record) - CLIMATE_ALLOWED_FIELDS
    if unknown:
        names = ", ".join(sorted(str(name) for name in unknown))
        raise ClimateContractError(f"unknown climate fields: {names}")

    missing = [field for field in CLIMATE_REQUIRED_FIELDS if field not in record]
    if missing:
        raise ClimateContractError(f"missing climate fields: {', '.join(missing)}")

    schema_version = _require_text(record["schema_version"], "schema_version")
    if schema_version != CLIMATE_SCHEMA_VERSION:
        raise ClimateContractError(f"schema_version must be {CLIMATE_SCHEMA_VERSION!r}")

    _require_text(record["aoi_id"], "aoi_id")
    variable = _require_text(record["variable"], "variable")
    if variable not in CLIMATE_VARIABLES:
        supported = ", ".join(sorted(CLIMATE_VARIABLES))
        raise ClimateContractError(
            f"variable must be one of: {supported}; got {variable!r}"
        )

    unit = _require_text(record["unit"], "unit")
    expected_unit = CLIMATE_VARIABLES[variable]
    if unit != expected_unit:
        raise ClimateContractError(
            f"unit for {variable!r} must be {expected_unit!r}; got {unit!r}"
        )

    year = _require_int(record["year"], "year")
    if year < CLIMATE_MIN_YEAR or year > CLIMATE_MAX_YEAR:
        raise ClimateContractError(
            f"year must be between {CLIMATE_MIN_YEAR} and {CLIMATE_MAX_YEAR}"
        )

    scenario = _require_text(record["scenario"], "scenario")
    if scenario not in CLIMATE_SCENARIOS:
        supported = ", ".join(sorted(CLIMATE_SCENARIOS))
        raise ClimateContractError(
            f"scenario must be one of: {supported}; got {scenario!r}"
        )

    _require_text(record["gcm"], "gcm")
    _require_number(record["value"], "value")

    variance = record.get("variance")
    if variance is not None:
        value = _require_number(variance, "variance")
        if value < 0:
            raise ClimateContractError("variance must be non-negative")

    _require_text(record["source_id"], "source_id")
    _require_text(record["source_version"], "source_version")
    _require_text(record["downscaling_method"], "downscaling_method")
    _require_timestamp(record["retrieved_utc"], "retrieved_utc")

    notes = record.get("notes")
    if notes is not None and not isinstance(notes, str):
        raise ClimateContractError("notes must be a string or null")


@dataclass(frozen=True)
class ClimateRecord:
    """One validated ``femic.climate.v1`` record.

    Attributes
    ----------
    aoi_id : str
        Identifier of the area of interest the value applies to.
    variable : str
        Canonical climate variable, one of :data:`CLIMATE_VARIABLES`.
    unit : str
        Canonical unit for the variable.
    year : int
        Calendar year of the value.
    scenario : str
        Scenario label, one of :data:`CLIMATE_SCENARIOS`.
    gcm : str
        General circulation model or ensemble label.
    value : float
        Climate value in ``unit``.
    source_id : str
        Identifier of the upstream data source.
    source_version : str
        Version of the upstream source or release.
    downscaling_method : str
        Downscaling or processing method applied to the source.
    retrieved_utc : str
        Timezone-aware ISO-8601 retrieval timestamp.
    variance : float | None, optional
        Optional variance for the value. Must be non-negative when present.
    notes : str | None, optional
        Optional free-text note.
    schema_version : str, optional
        Contract version. Defaults to :data:`CLIMATE_SCHEMA_VERSION`.
    """

    aoi_id: str
    variable: str
    unit: str
    year: int
    scenario: str
    gcm: str
    value: float
    source_id: str
    source_version: str
    downscaling_method: str
    retrieved_utc: str
    variance: float | None = None
    notes: str | None = None
    schema_version: str = CLIMATE_SCHEMA_VERSION

    def to_dict(self) -> dict[str, object]:
        """Return the canonical dict form, including null optional fields."""
        return {
            "schema_version": self.schema_version,
            "aoi_id": self.aoi_id,
            "variable": self.variable,
            "unit": self.unit,
            "year": self.year,
            "scenario": self.scenario,
            "gcm": self.gcm,
            "value": self.value,
            "variance": self.variance,
            "source_id": self.source_id,
            "source_version": self.source_version,
            "downscaling_method": self.downscaling_method,
            "retrieved_utc": self.retrieved_utc,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, record: Mapping[str, object]) -> ClimateRecord:
        """Validate and construct a record from a mapping.

        Parameters
        ----------
        record : mapping[str, object]
            Candidate record.

        Returns
        -------
        ClimateRecord
            The validated record.

        Raises
        ------
        ClimateContractError
            If the record violates ``femic.climate.v1``.
        """
        validate_climate_record(record)
        variance = record.get("variance")
        notes = record.get("notes")
        return cls(
            aoi_id=_require_text(record["aoi_id"], "aoi_id"),
            variable=_require_text(record["variable"], "variable"),
            unit=_require_text(record["unit"], "unit"),
            year=_require_int(record["year"], "year"),
            scenario=_require_text(record["scenario"], "scenario"),
            gcm=_require_text(record["gcm"], "gcm"),
            value=_require_number(record["value"], "value"),
            source_id=_require_text(record["source_id"], "source_id"),
            source_version=_require_text(record["source_version"], "source_version"),
            downscaling_method=_require_text(
                record["downscaling_method"], "downscaling_method"
            ),
            retrieved_utc=_require_text(record["retrieved_utc"], "retrieved_utc"),
            variance=(
                None if variance is None else _require_number(variance, "variance")
            ),
            notes=None if notes is None else str(notes),
        )


def _record_from_csv_row(row: Mapping[str, str], line_number: int) -> ClimateRecord:
    """Convert one CSV row into a validated climate record."""
    payload: dict[str, object] = dict(row)
    try:
        payload["year"] = int(str(row["year"]).strip())
        payload["value"] = float(str(row["value"]).strip())
        variance_text = str(row.get("variance", "")).strip()
        payload["variance"] = float(variance_text) if variance_text else None
        notes = row.get("notes", "")
        payload["notes"] = notes if notes else None
    except (KeyError, TypeError, ValueError) as exc:
        raise ClimateContractError(
            f"invalid climate CSV row at line {line_number}: {exc}"
        ) from exc
    return ClimateRecord.from_dict(payload)


def read_climate_table(path: Path) -> tuple[ClimateRecord, ...]:
    """Read and validate a climate table from CSV or JSON.

    Parameters
    ----------
    path : pathlib.Path
        ``.csv`` file with one record per row, or ``.json`` file containing a
        list of records or an object with a ``records`` list.

    Returns
    -------
    tuple[ClimateRecord, ...]
        The validated records in file order.

    Raises
    ------
    ClimateContractError
        If the suffix is unsupported, the file is empty, or any record is
        invalid.
    """
    suffix = path.suffix.lower()
    if suffix == ".csv":
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames is None:
                raise ClimateContractError(f"{path} has no CSV header")
            missing = [
                field for field in CLIMATE_CSV_FIELDS if field not in reader.fieldnames
            ]
            if missing:
                raise ClimateContractError(
                    f"{path} is missing columns: {', '.join(missing)}"
                )
            records = tuple(
                _record_from_csv_row(row, line_number)
                for line_number, row in enumerate(reader, start=2)
            )
    elif suffix == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            payload = payload.get("records")
        if not isinstance(payload, list):
            raise ClimateContractError(
                f"{path} must contain a list of records or an object with 'records'"
            )
        records = tuple(
            ClimateRecord.from_dict(record)
            for record in payload
            if isinstance(record, Mapping)
        )
        if len(records) != len(payload):
            raise ClimateContractError(f"{path} contains a non-mapping record")
    else:
        raise ClimateContractError(f"unsupported climate table suffix: {path.suffix!r}")

    if not records:
        raise ClimateContractError(f"{path} contains no climate records")
    return records


def write_climate_table(path: Path, records: Sequence[ClimateRecord]) -> None:
    """Write a validated climate table to CSV or JSON.

    Parameters
    ----------
    path : pathlib.Path
        Destination ``.csv`` or ``.json`` path.
    records : sequence[ClimateRecord]
        Records to write. Each is validated before writing.

    Raises
    ------
    ClimateContractError
        If the suffix is unsupported or a record is invalid.
    """
    if not records:
        raise ClimateContractError("climate table must contain at least one record")
    for record in records:
        validate_climate_record(record.to_dict())

    if path.suffix.lower() == ".csv":
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=CLIMATE_CSV_FIELDS)
            writer.writeheader()
            writer.writerows(record.to_dict() for record in records)
    elif path.suffix.lower() == ".json":
        path.write_text(
            json.dumps(
                [record.to_dict() for record in records], indent=2, sort_keys=True
            )
            + "\n",
            encoding="utf-8",
        )
    else:
        raise ClimateContractError(f"unsupported climate table suffix: {path.suffix!r}")


def summarize_climate_table(records: Sequence[ClimateRecord]) -> dict[str, object]:
    """Return a provenance-bearing summary of a climate table.

    Parameters
    ----------
    records : sequence[ClimateRecord]
        Validated records.

    Returns
    -------
    dict[str, object]
        Counts, AOIs, variables, units, scenarios, year range, source tuples,
        and the retrieval-time range. This is the shape a consumer can report
        without copying the whole table.

    Raises
    ------
    ClimateContractError
        If the table is empty.
    """
    if not records:
        raise ClimateContractError("climate table must contain at least one record")

    for record in records:
        validate_climate_record(record.to_dict())

    sources = sorted(
        {
            (
                record.source_id,
                record.source_version,
                record.downscaling_method,
            )
            for record in records
        }
    )
    timestamps = [
        _require_timestamp(record.retrieved_utc, "retrieved_utc") for record in records
    ]
    return {
        "schema_version": CLIMATE_SCHEMA_VERSION,
        "record_count": len(records),
        "aoi_ids": sorted({record.aoi_id for record in records}),
        "variables": sorted({record.variable for record in records}),
        "units": sorted({record.unit for record in records}),
        "scenarios": sorted({record.scenario for record in records}),
        "year_min": min(record.year for record in records),
        "year_max": max(record.year for record in records),
        "sources": [
            {
                "source_id": source_id,
                "source_version": source_version,
                "downscaling_method": downscaling_method,
            }
            for source_id, source_version, downscaling_method in sources
        ],
        "retrieved_utc_min": min(timestamps).astimezone(UTC).isoformat(),
        "retrieved_utc_max": max(timestamps).astimezone(UTC).isoformat(),
    }
