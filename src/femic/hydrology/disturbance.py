"""Annual harvest/road/retention disturbance ledgers.

P114.3 converts spatial harvest and road schedules into a complete annual
ledger by unit and year. It is an accounting layer, not a hydrologic response.
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

HYDROLOGY_DISTURBANCE_SCHEMA_VERSION = "femic.hydrology.disturbance.v1"
HYDROLOGY_DISTURBANCE_ACTIONS: tuple[str, ...] = (
    "build",
    "use",
    "maintain",
    "decommission",
)


class HydrologyDisturbanceError(RuntimeError):
    """Raised when a disturbance schedule or ledger is invalid."""


@dataclass(frozen=True)
class DisturbanceUnit:
    """One spatial unit in the disturbance ledger."""

    unit_id: str
    area_ha: float
    watershed_id: str
    hru_id: str | None = None

    def to_dict(self) -> dict[str, object]:
        """Return the unit as a JSON-serializable mapping."""

        return {
            "unit_id": self.unit_id,
            "area_ha": self.area_ha,
            "watershed_id": self.watershed_id,
            "hru_id": self.hru_id,
        }


@dataclass(frozen=True)
class HarvestEvent:
    """One harvest or retention event on a spatial unit."""

    event_id: str
    unit_id: str
    year: int
    area_ha: float
    retention_area_ha: float = 0.0
    treatment: str = "clearcut"
    source: str = ""

    def to_dict(self) -> dict[str, object]:
        """Return the event as a JSON-serializable mapping."""

        return {
            "event_id": self.event_id,
            "unit_id": self.unit_id,
            "year": self.year,
            "area_ha": self.area_ha,
            "retention_area_ha": self.retention_area_ha,
            "treatment": self.treatment,
            "source": self.source,
        }


@dataclass(frozen=True)
class RoadEvent:
    """One road build, use, maintenance, or decommission event."""

    event_id: str
    road_id: str
    unit_id: str
    year: int
    action: str
    length_m: float = 0.0
    connected_to_stream: bool = False
    crossing_count: int = 0
    source: str = ""

    def to_dict(self) -> dict[str, object]:
        """Return the event as a JSON-serializable mapping."""

        return {
            "event_id": self.event_id,
            "road_id": self.road_id,
            "unit_id": self.unit_id,
            "year": self.year,
            "action": self.action,
            "length_m": self.length_m,
            "connected_to_stream": self.connected_to_stream,
            "crossing_count": self.crossing_count,
            "source": self.source,
        }


@dataclass(frozen=True)
class DisturbanceLedgerRow:
    """One unit/year disturbance state."""

    year: int
    unit_id: str
    watershed_id: str
    hru_id: str | None
    unit_area_ha: float
    harvest_area_ha: float
    retention_area_ha: float
    effective_harvest_area_ha: float
    road_active_length_m: float
    road_connected_length_m: float
    road_built_length_m: float
    road_decommissioned_length_m: float
    road_crossing_count: int
    years_since_harvest: int | None
    years_since_road_build: int | None
    source_event_ids: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        """Return the row as a JSON-serializable mapping."""

        return {
            "year": self.year,
            "unit_id": self.unit_id,
            "watershed_id": self.watershed_id,
            "hru_id": self.hru_id,
            "unit_area_ha": self.unit_area_ha,
            "harvest_area_ha": self.harvest_area_ha,
            "retention_area_ha": self.retention_area_ha,
            "effective_harvest_area_ha": self.effective_harvest_area_ha,
            "road_active_length_m": self.road_active_length_m,
            "road_connected_length_m": self.road_connected_length_m,
            "road_built_length_m": self.road_built_length_m,
            "road_decommissioned_length_m": self.road_decommissioned_length_m,
            "road_crossing_count": self.road_crossing_count,
            "years_since_harvest": self.years_since_harvest,
            "years_since_road_build": self.years_since_road_build,
            "source_event_ids": list(self.source_event_ids),
        }


@dataclass(frozen=True)
class DisturbanceLedger:
    """Complete annual disturbance ledger for a hydrology domain."""

    ledger_id: str
    generated_utc: str
    domain_id: str
    years: tuple[int, ...]
    units: tuple[DisturbanceUnit, ...]
    rows: tuple[DisturbanceLedgerRow, ...]
    caveats: tuple[str, ...] = ()
    provenance: dict[str, object] = field(default_factory=dict)
    schema_version: str = HYDROLOGY_DISTURBANCE_SCHEMA_VERSION

    @property
    def row_count(self) -> int:
        """Return the number of unit/year rows."""

        return len(self.rows)

    def to_dict(self) -> dict[str, object]:
        """Return the ledger as a JSON-serializable mapping."""

        return {
            "schema_version": self.schema_version,
            "ledger_id": self.ledger_id,
            "generated_utc": self.generated_utc,
            "domain_id": self.domain_id,
            "years": list(self.years),
            "units": [unit.to_dict() for unit in self.units],
            "summary": {
                "unit_count": len(self.units),
                "year_count": len(self.years),
                "row_count": self.row_count,
            },
            "rows": [row.to_dict() for row in self.rows],
            "caveats": list(self.caveats),
            "provenance": self.provenance,
        }


@dataclass(frozen=True)
class DisturbanceLedgerValidation:
    """Validation outcome for a disturbance ledger."""

    is_valid: bool
    errors: tuple[str, ...]
    warnings: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        """Return the validation as a JSON-serializable mapping."""

        return {
            "is_valid": self.is_valid,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
        }


def build_disturbance_ledger(
    *,
    domain_id: str,
    units: Sequence[DisturbanceUnit],
    harvest_events: Sequence[HarvestEvent],
    road_events: Sequence[RoadEvent],
    years: Sequence[int],
    generated_utc: str | None = None,
) -> DisturbanceLedger:
    """Build a complete annual unit/year disturbance ledger.

    Every unit receives one row for every year, even when no event occurs.
    Harvest area and retention are gross annual flows; road lengths are active
    state plus gross annual build/decommission flows.
    """

    if not domain_id.strip():
        raise HydrologyDisturbanceError("Domain ID must be non-empty.")
    sorted_years = _normalize_years(years)
    unit_map = _normalize_units(units)
    _validate_events(harvest_events, road_events, unit_map=unit_map, years=sorted_years)
    harvest_by_unit_year = _group_harvest(harvest_events)
    for (unit_id, year), (harvest_area, _) in harvest_by_unit_year.items():
        if harvest_area > unit_map[unit_id].area_ha + 1e-9:
            raise HydrologyDisturbanceError(
                f"Harvest area for {unit_id!r} in {year} exceeds unit area."
            )
    road_state_by_event = _build_road_state(
        road_events,
        unit_map=unit_map,
        years=sorted_years,
    )
    last_harvest_year: dict[str, int] = {}
    last_road_build_year: dict[str, int] = {}
    rows: list[DisturbanceLedgerRow] = []
    for year in sorted_years:
        for unit in sorted(unit_map.values(), key=lambda item: item.unit_id):
            harvest_key = (unit.unit_id, year)
            harvest_area, retention_area = harvest_by_unit_year.get(
                harvest_key,
                (0.0, 0.0),
            )
            if harvest_area > 0:
                last_harvest_year[unit.unit_id] = year
            active, connected, crossing, built, decommissioned = (
                road_state_by_event.get((unit.unit_id, year), (0.0, 0.0, 0, 0.0, 0.0))
            )
            event_ids = sorted(
                {
                    event.event_id
                    for event in harvest_events
                    if event.unit_id == unit.unit_id and event.year == year
                }
                | {
                    event.event_id
                    for event in road_events
                    if event.unit_id == unit.unit_id and event.year == year
                }
            )
            build_year = _road_build_year_for_unit(
                road_events,
                unit_id=unit.unit_id,
                year=year,
                last_road_build_year=last_road_build_year,
            )
            rows.append(
                DisturbanceLedgerRow(
                    year=year,
                    unit_id=unit.unit_id,
                    watershed_id=unit.watershed_id,
                    hru_id=unit.hru_id,
                    unit_area_ha=unit.area_ha,
                    harvest_area_ha=harvest_area,
                    retention_area_ha=retention_area,
                    effective_harvest_area_ha=harvest_area - retention_area,
                    road_active_length_m=active,
                    road_connected_length_m=connected,
                    road_built_length_m=built,
                    road_decommissioned_length_m=decommissioned,
                    road_crossing_count=crossing,
                    years_since_harvest=(
                        year - last_harvest_year[unit.unit_id]
                        if unit.unit_id in last_harvest_year
                        else None
                    ),
                    years_since_road_build=(
                        year - build_year if build_year is not None else None
                    ),
                    source_event_ids=tuple(event_ids),
                )
            )
    records = tuple(rows)
    provenance = {
        "producer": "femic.hydrology.disturbance",
        "harvest_event_count": len(harvest_events),
        "road_event_count": len(road_events),
    }
    ledger_id = _ledger_id(
        domain_id=domain_id,
        years=sorted_years,
        units=tuple(unit_map.values()),
        rows=records,
    )
    return DisturbanceLedger(
        ledger_id=ledger_id,
        generated_utc=generated_utc or _now(),
        domain_id=domain_id,
        years=sorted_years,
        units=tuple(sorted(unit_map.values(), key=lambda item: item.unit_id)),
        rows=records,
        caveats=(
            "The disturbance ledger is accounting, not a hydrologic response.",
            "Road active length assumes event-level build/decommission conservation.",
            "Recovery is represented by time since disturbance, not a recovery curve.",
        ),
        provenance=provenance,
    )


def validate_disturbance_ledger(
    ledger: DisturbanceLedger,
) -> DisturbanceLedgerValidation:
    """Validate ledger structure, completeness, and row conservation."""

    errors: list[str] = []
    warnings: list[str] = []
    if ledger.schema_version != HYDROLOGY_DISTURBANCE_SCHEMA_VERSION:
        errors.append(
            f"Unsupported disturbance ledger schema {ledger.schema_version!r}; "
            f"expected {HYDROLOGY_DISTURBANCE_SCHEMA_VERSION!r}."
        )
    if not ledger.ledger_id.strip():
        errors.append("Ledger ID must be non-empty.")
    if not ledger.domain_id.strip():
        errors.append("Domain ID must be non-empty.")
    if not ledger.years:
        errors.append("Ledger must contain at least one year.")
    if not ledger.units:
        errors.append("Ledger must contain at least one unit.")
    unit_ids = {unit.unit_id for unit in ledger.units}
    if len(unit_ids) != len(ledger.units):
        errors.append("Ledger contains duplicate unit IDs.")
    row_keys: set[tuple[int, str]] = set()
    for row in ledger.rows:
        key = (row.year, row.unit_id)
        if key in row_keys:
            errors.append(f"Duplicate ledger row for {row.year}/{row.unit_id}.")
        row_keys.add(key)
        if row.unit_id not in unit_ids:
            errors.append(f"Row references unknown unit {row.unit_id!r}.")
        if row.harvest_area_ha < 0 or row.retention_area_ha < 0:
            errors.append(f"Row {row.year}/{row.unit_id} has negative harvest area.")
        if row.retention_area_ha > row.harvest_area_ha:
            errors.append(
                f"Row {row.year}/{row.unit_id} retention exceeds harvest area."
            )
        if row.harvest_area_ha > row.unit_area_ha:
            errors.append(f"Row {row.year}/{row.unit_id} harvest exceeds unit area.")
        if not math.isclose(
            row.effective_harvest_area_ha,
            row.harvest_area_ha - row.retention_area_ha,
        ):
            errors.append(
                f"Row {row.year}/{row.unit_id} has inconsistent effective area."
            )
        if row.road_active_length_m < 0 or row.road_connected_length_m < 0:
            errors.append(f"Row {row.year}/{row.unit_id} has negative road length.")
        if row.road_connected_length_m > row.road_active_length_m:
            errors.append(
                f"Row {row.year}/{row.unit_id} connected road exceeds active road."
            )
        if row.road_crossing_count < 0:
            errors.append(f"Row {row.year}/{row.unit_id} has negative crossings.")
        if row.years_since_harvest is not None and row.years_since_harvest < 0:
            errors.append(f"Row {row.year}/{row.unit_id} has negative harvest age.")
        if row.years_since_road_build is not None and row.years_since_road_build < 0:
            errors.append(f"Row {row.year}/{row.unit_id} has negative road age.")
    expected_rows = len(ledger.years) * len(ledger.units)
    if len(ledger.rows) != expected_rows:
        errors.append(f"Ledger has {len(ledger.rows)} rows; expected {expected_rows}.")
    expected_keys = {
        (year, unit.unit_id) for year in ledger.years for unit in ledger.units
    }
    missing_keys = expected_keys - row_keys
    if missing_keys:
        errors.append(
            "Ledger is missing unit/year rows: "
            + ", ".join(f"{year}/{unit}" for year, unit in sorted(missing_keys))
            + "."
        )
    if not ledger.rows:
        warnings.append("Ledger contains no disturbance rows.")
    return DisturbanceLedgerValidation(
        is_valid=not errors,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def write_disturbance_ledger(ledger: DisturbanceLedger, path: Path) -> Path:
    """Write a disturbance ledger as pretty-printed JSON."""

    resolved = path.expanduser().resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(_pretty_json(ledger.to_dict()), encoding="utf-8")
    return resolved


def write_disturbance_ledger_csv(ledger: DisturbanceLedger, path: Path) -> Path:
    """Write one CSV row per unit/year for review and downstream joins."""

    resolved = path.expanduser().resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    with resolved.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "year",
                "unit_id",
                "watershed_id",
                "hru_id",
                "unit_area_ha",
                "harvest_area_ha",
                "retention_area_ha",
                "effective_harvest_area_ha",
                "road_active_length_m",
                "road_connected_length_m",
                "road_built_length_m",
                "road_decommissioned_length_m",
                "road_crossing_count",
                "years_since_harvest",
                "years_since_road_build",
                "source_event_ids",
            ]
        )
        for row in ledger.rows:
            writer.writerow(
                [
                    row.year,
                    row.unit_id,
                    row.watershed_id,
                    row.hru_id,
                    row.unit_area_ha,
                    row.harvest_area_ha,
                    row.retention_area_ha,
                    row.effective_harvest_area_ha,
                    row.road_active_length_m,
                    row.road_connected_length_m,
                    row.road_built_length_m,
                    row.road_decommissioned_length_m,
                    row.road_crossing_count,
                    row.years_since_harvest,
                    row.years_since_road_build,
                    ";".join(row.source_event_ids),
                ]
            )
    return resolved


def load_disturbance_ledger(path: Path) -> DisturbanceLedger:
    """Load a disturbance ledger from JSON."""

    resolved = path.expanduser().resolve()
    payload = _read_json_object(resolved, context="disturbance ledger")
    schema_version = _required_str(
        payload,
        "schema_version",
        context="disturbance ledger",
    )
    if schema_version != HYDROLOGY_DISTURBANCE_SCHEMA_VERSION:
        raise HydrologyDisturbanceError(
            f"Unsupported disturbance ledger schema {schema_version!r}; expected "
            f"{HYDROLOGY_DISTURBANCE_SCHEMA_VERSION!r}."
        )
    years = tuple(
        _required_int_value(item, context="disturbance years")
        for item in _required_list(payload, "years", context="disturbance ledger")
    )
    units = tuple(
        _unit_from_payload(item, index=index)
        for index, item in enumerate(
            _required_list(payload, "units", context="disturbance ledger"),
            start=1,
        )
    )
    rows = tuple(
        _row_from_payload(item, index=index)
        for index, item in enumerate(
            _required_list(payload, "rows", context="disturbance ledger"),
            start=1,
        )
    )
    return DisturbanceLedger(
        ledger_id=_required_str(payload, "ledger_id", context="disturbance ledger"),
        generated_utc=_optional_str(payload.get("generated_utc")) or "",
        domain_id=_required_str(payload, "domain_id", context="disturbance ledger"),
        years=years,
        units=units,
        rows=rows,
        caveats=_optional_str_list(payload.get("caveats"), context="caveats"),
        provenance=_optional_mapping(payload.get("provenance"), context="provenance"),
        schema_version=schema_version,
    )


def load_disturbance_units_csv(path: Path) -> tuple[DisturbanceUnit, ...]:
    """Load units from a CSV with unit_id, area_ha, watershed_id, hru_id."""

    rows = _read_csv_rows(path)
    units: list[DisturbanceUnit] = []
    for row in rows:
        units.append(
            DisturbanceUnit(
                unit_id=_required_str(row, "unit_id", context="unit CSV"),
                area_ha=_required_float(row, "area_ha", context="unit CSV"),
                watershed_id=_required_str(
                    row,
                    "watershed_id",
                    context="unit CSV",
                ),
                hru_id=_optional_str(row.get("hru_id")),
            )
        )
    return tuple(units)


def load_harvest_events_csv(path: Path) -> tuple[HarvestEvent, ...]:
    """Load harvest events from a CSV schedule."""

    events: list[HarvestEvent] = []
    for row in _read_csv_rows(path):
        events.append(
            HarvestEvent(
                event_id=_required_str(row, "event_id", context="harvest CSV"),
                unit_id=_required_str(row, "unit_id", context="harvest CSV"),
                year=_required_int(row, "year", context="harvest CSV"),
                area_ha=_required_float(row, "area_ha", context="harvest CSV"),
                retention_area_ha=_optional_float(row.get("retention_area_ha")) or 0.0,
                treatment=_optional_str(row.get("treatment")) or "clearcut",
                source=_optional_str(row.get("source")) or "",
            )
        )
    return tuple(events)


def load_road_events_csv(path: Path) -> tuple[RoadEvent, ...]:
    """Load road events from a CSV schedule."""

    events: list[RoadEvent] = []
    for row in _read_csv_rows(path):
        events.append(
            RoadEvent(
                event_id=_required_str(row, "event_id", context="road CSV"),
                road_id=_required_str(row, "road_id", context="road CSV"),
                unit_id=_required_str(row, "unit_id", context="road CSV"),
                year=_required_int(row, "year", context="road CSV"),
                action=_required_str(row, "action", context="road CSV"),
                length_m=_optional_float(row.get("length_m")) or 0.0,
                connected_to_stream=_parse_bool(
                    row.get("connected_to_stream"),
                    context="road CSV connected_to_stream",
                ),
                crossing_count=_optional_int(row.get("crossing_count")) or 0,
                source=_optional_str(row.get("source")) or "",
            )
        )
    return tuple(events)


def _normalize_years(years: Sequence[int]) -> tuple[int, ...]:
    if not years:
        raise HydrologyDisturbanceError("At least one ledger year is required.")
    normalized: list[int] = []
    for year in years:
        if isinstance(year, bool) or not isinstance(year, int):
            raise HydrologyDisturbanceError("Ledger years must be integers.")
        if year < 1:
            raise HydrologyDisturbanceError("Ledger years must be positive.")
        if year in normalized:
            raise HydrologyDisturbanceError(f"Duplicate ledger year {year}.")
        normalized.append(year)
    return tuple(sorted(normalized))


def _normalize_units(
    units: Sequence[DisturbanceUnit],
) -> dict[str, DisturbanceUnit]:
    if not units:
        raise HydrologyDisturbanceError("At least one disturbance unit is required.")
    unit_map: dict[str, DisturbanceUnit] = {}
    for unit in units:
        if not unit.unit_id.strip():
            raise HydrologyDisturbanceError("Unit ID must be non-empty.")
        if unit.unit_id in unit_map:
            raise HydrologyDisturbanceError(f"Duplicate unit ID {unit.unit_id!r}.")
        if unit.area_ha <= 0 or not math.isfinite(unit.area_ha):
            raise HydrologyDisturbanceError(
                f"Unit {unit.unit_id!r} must have positive area."
            )
        if not unit.watershed_id.strip():
            raise HydrologyDisturbanceError(
                f"Unit {unit.unit_id!r} must have a watershed ID."
            )
        unit_map[unit.unit_id] = unit
    return unit_map


def _validate_events(
    harvest_events: Sequence[HarvestEvent],
    road_events: Sequence[RoadEvent],
    *,
    unit_map: Mapping[str, DisturbanceUnit],
    years: tuple[int, ...],
) -> None:
    year_set = set(years)
    harvest_ids: set[str] = set()
    for harvest_event in harvest_events:
        if not harvest_event.event_id.strip():
            raise HydrologyDisturbanceError("Harvest event ID must be non-empty.")
        if harvest_event.event_id in harvest_ids:
            raise HydrologyDisturbanceError(
                f"Duplicate harvest event ID {harvest_event.event_id!r}."
            )
        harvest_ids.add(harvest_event.event_id)
        if harvest_event.unit_id not in unit_map:
            raise HydrologyDisturbanceError(
                f"Harvest event {harvest_event.event_id!r} references unknown unit "
                f"{harvest_event.unit_id!r}."
            )
        if harvest_event.year not in year_set:
            raise HydrologyDisturbanceError(
                f"Harvest event {harvest_event.event_id!r} year is outside the ledger."
            )
        if harvest_event.area_ha <= 0 or not math.isfinite(harvest_event.area_ha):
            raise HydrologyDisturbanceError(
                f"Harvest event {harvest_event.event_id!r} must have positive area."
            )
        if harvest_event.retention_area_ha < 0:
            raise HydrologyDisturbanceError(
                f"Harvest event {harvest_event.event_id!r} has negative retention."
            )
        if harvest_event.retention_area_ha > harvest_event.area_ha:
            raise HydrologyDisturbanceError(
                f"Harvest event {harvest_event.event_id!r} retention exceeds area."
            )
    road_ids: set[str] = set()
    road_units: dict[str, str] = {}
    for road_event in road_events:
        if not road_event.event_id.strip():
            raise HydrologyDisturbanceError("Road event ID must be non-empty.")
        if road_event.event_id in road_ids:
            raise HydrologyDisturbanceError(
                f"Duplicate road event ID {road_event.event_id!r}."
            )
        road_ids.add(road_event.event_id)
        if road_event.unit_id not in unit_map:
            raise HydrologyDisturbanceError(
                f"Road event {road_event.event_id!r} references unknown unit "
                f"{road_event.unit_id!r}."
            )
        if road_event.year not in year_set:
            raise HydrologyDisturbanceError(
                f"Road event {road_event.event_id!r} year is outside the ledger."
            )
        if road_event.action not in HYDROLOGY_DISTURBANCE_ACTIONS:
            raise HydrologyDisturbanceError(
                f"Road event {road_event.event_id!r} has unsupported action "
                f"{road_event.action!r}."
            )
        if road_event.length_m < 0 or not math.isfinite(road_event.length_m):
            raise HydrologyDisturbanceError(
                f"Road event {road_event.event_id!r} has invalid length."
            )
        if road_event.action in {"build", "decommission"} and road_event.length_m <= 0:
            raise HydrologyDisturbanceError(
                f"Road event {road_event.event_id!r} requires positive length."
            )
        if road_event.crossing_count < 0:
            raise HydrologyDisturbanceError(
                f"Road event {road_event.event_id!r} has negative crossings."
            )
        if (
            road_event.road_id in road_units
            and road_units[road_event.road_id] != road_event.unit_id
        ):
            raise HydrologyDisturbanceError(
                f"Road {road_event.road_id!r} spans multiple units."
            )
        road_units[road_event.road_id] = road_event.unit_id


def _group_harvest(
    events: Sequence[HarvestEvent],
) -> dict[tuple[str, int], tuple[float, float]]:
    grouped: dict[tuple[str, int], tuple[float, float]] = {}
    for event in events:
        key = (event.unit_id, event.year)
        area, retention = grouped.get(key, (0.0, 0.0))
        grouped[key] = (area + event.area_ha, retention + event.retention_area_ha)
    return grouped


@dataclass
class _RoadState:
    unit_id: str
    active_m: float = 0.0
    connected_m: float = 0.0
    crossings: int = 0


def _build_road_state(
    events: Sequence[RoadEvent],
    *,
    unit_map: Mapping[str, DisturbanceUnit],
    years: tuple[int, ...],
) -> dict[tuple[str, int], tuple[float, float, int, float, float]]:
    road_state: dict[str, _RoadState] = {}
    result: dict[tuple[str, int], tuple[float, float, int, float, float]] = {}
    for year in years:
        for event in sorted(
            (item for item in events if item.year == year),
            key=lambda item: item.event_id,
        ):
            state = road_state.setdefault(
                event.road_id,
                _RoadState(unit_id=event.unit_id),
            )
            if event.action == "build":
                if state.active_m > 0:
                    raise HydrologyDisturbanceError(
                        f"Road {event.road_id!r} is already active in {year}."
                    )
                state.active_m += event.length_m
                if event.connected_to_stream:
                    state.connected_m += event.length_m
                state.crossings += event.crossing_count
            elif event.action == "decommission":
                if event.length_m > state.active_m + 1e-9:
                    raise HydrologyDisturbanceError(
                        f"Road {event.road_id!r} decommission exceeds active length."
                    )
                if (
                    event.connected_to_stream
                    and event.length_m > state.connected_m + 1e-9
                ):
                    raise HydrologyDisturbanceError(
                        f"Road {event.road_id!r} decommission exceeds connected length."
                    )
                if event.crossing_count > state.crossings:
                    raise HydrologyDisturbanceError(
                        f"Road {event.road_id!r} decommission exceeds active crossings."
                    )
                state.active_m -= event.length_m
                if event.connected_to_stream:
                    state.connected_m -= event.length_m
                state.crossings -= event.crossing_count
        for unit in unit_map.values():
            active = 0.0
            connected = 0.0
            crossings = 0
            built = 0.0
            decommissioned = 0.0
            for state in road_state.values():
                if state.unit_id != unit.unit_id:
                    continue
                active += state.active_m
                connected += state.connected_m
                crossings += state.crossings
            for event in events:
                if event.unit_id == unit.unit_id and event.year == year:
                    if event.action == "build":
                        built += event.length_m
                    elif event.action == "decommission":
                        decommissioned += event.length_m
            result[(unit.unit_id, year)] = (
                active,
                connected,
                crossings,
                built,
                decommissioned,
            )
    return result


def _road_build_year_for_unit(
    events: Sequence[RoadEvent],
    *,
    unit_id: str,
    year: int,
    last_road_build_year: dict[str, int],
) -> int | None:
    for event in events:
        if event.unit_id == unit_id and event.action == "build" and event.year <= year:
            last_road_build_year[unit_id] = max(
                last_road_build_year.get(unit_id, event.year),
                event.year,
            )
    return last_road_build_year.get(unit_id)


def _ledger_id(
    *,
    domain_id: str,
    years: tuple[int, ...],
    units: tuple[DisturbanceUnit, ...],
    rows: tuple[DisturbanceLedgerRow, ...],
) -> str:
    material = {
        "domain_id": domain_id,
        "years": list(years),
        "units": [unit.to_dict() for unit in units],
        "rows": [row.to_dict() for row in rows],
    }
    digest = hashlib.sha256(_canonical_json_bytes(material)).hexdigest()
    return f"hydro-dist-{digest[:16]}"


def _unit_from_payload(item: object, *, index: int) -> DisturbanceUnit:
    payload = _mapping_from_object(item, context=f"unit {index}")
    return DisturbanceUnit(
        unit_id=_required_str(payload, "unit_id", context=f"unit {index}"),
        area_ha=_required_float(payload, "area_ha", context=f"unit {index}"),
        watershed_id=_required_str(
            payload,
            "watershed_id",
            context=f"unit {index}",
        ),
        hru_id=_optional_str(payload.get("hru_id")),
    )


def _row_from_payload(item: object, *, index: int) -> DisturbanceLedgerRow:
    payload = _mapping_from_object(item, context=f"row {index}")
    return DisturbanceLedgerRow(
        year=_required_int(payload, "year", context=f"row {index}"),
        unit_id=_required_str(payload, "unit_id", context=f"row {index}"),
        watershed_id=_required_str(
            payload,
            "watershed_id",
            context=f"row {index}",
        ),
        hru_id=_optional_str(payload.get("hru_id")),
        unit_area_ha=_required_float(
            payload,
            "unit_area_ha",
            context=f"row {index}",
        ),
        harvest_area_ha=_required_float(
            payload,
            "harvest_area_ha",
            context=f"row {index}",
        ),
        retention_area_ha=_required_float(
            payload,
            "retention_area_ha",
            context=f"row {index}",
        ),
        effective_harvest_area_ha=_required_float(
            payload,
            "effective_harvest_area_ha",
            context=f"row {index}",
        ),
        road_active_length_m=_required_float(
            payload,
            "road_active_length_m",
            context=f"row {index}",
        ),
        road_connected_length_m=_required_float(
            payload,
            "road_connected_length_m",
            context=f"row {index}",
        ),
        road_built_length_m=_required_float(
            payload,
            "road_built_length_m",
            context=f"row {index}",
        ),
        road_decommissioned_length_m=_required_float(
            payload,
            "road_decommissioned_length_m",
            context=f"row {index}",
        ),
        road_crossing_count=_required_int(
            payload,
            "road_crossing_count",
            context=f"row {index}",
        ),
        years_since_harvest=_optional_int(payload.get("years_since_harvest")),
        years_since_road_build=_optional_int(payload.get("years_since_road_build")),
        source_event_ids=_optional_str_list(
            payload.get("source_event_ids"),
            context=f"row {index} source_event_ids",
        ),
    )


def _parse_bool(value: object, *, context: str) -> bool:
    if value is None or value == "":
        return False
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y"}:
        return True
    if text in {"0", "false", "no", "n"}:
        return False
    raise HydrologyDisturbanceError(f"{context} must be a boolean value.")


def _read_csv_rows(path: Path) -> tuple[dict[str, str], ...]:
    resolved = path.expanduser().resolve()
    try:
        with resolved.open(newline="", encoding="utf-8") as handle:
            return tuple(dict(row) for row in csv.DictReader(handle))
    except OSError as exc:
        raise HydrologyDisturbanceError(
            f"Unable to read CSV {resolved}: {exc}"
        ) from exc


def _read_json_object(path: Path, *, context: str) -> dict[str, object]:
    try:
        payload: object = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise HydrologyDisturbanceError(
            f"Unable to read {context}: {path}: {exc}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise HydrologyDisturbanceError(
            f"Invalid JSON in {context}: {path}: {exc}"
        ) from exc
    if not isinstance(payload, Mapping):
        raise HydrologyDisturbanceError(f"{context} must be a JSON object: {path}")
    return {str(key): value for key, value in payload.items()}


def _mapping_from_object(value: object, *, context: str) -> dict[str, object]:
    if not isinstance(value, Mapping):
        raise HydrologyDisturbanceError(f"{context} must be an object.")
    return {str(key): item for key, item in value.items()}


def _required_list(
    mapping: Mapping[str, object],
    key: str,
    *,
    context: str,
) -> list[object]:
    value = mapping.get(key)
    if not isinstance(value, list):
        raise HydrologyDisturbanceError(f"{context} field {key!r} must be a list.")
    return value


def _required_str(
    mapping: Mapping[str, object],
    key: str,
    *,
    context: str,
) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        raise HydrologyDisturbanceError(
            f"{context} field {key!r} must be a non-empty string."
        )
    return value.strip()


def _required_float(
    mapping: Mapping[str, object],
    key: str,
    *,
    context: str,
) -> float:
    value = mapping.get(key)
    parsed = _optional_float(value)
    if parsed is None:
        raise HydrologyDisturbanceError(f"{context} field {key!r} must be numeric.")
    return parsed


def _required_int(
    mapping: Mapping[str, object],
    key: str,
    *,
    context: str,
) -> int:
    value = mapping.get(key)
    parsed = _optional_int(value)
    if parsed is None:
        raise HydrologyDisturbanceError(f"{context} field {key!r} must be an integer.")
    return parsed


def _required_int_value(value: object, *, context: str) -> int:
    parsed = _optional_int(value)
    if parsed is None:
        raise HydrologyDisturbanceError(f"{context} entries must be integers.")
    return parsed


def _optional_str(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text or None


def _optional_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return None


def _optional_float(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        parsed = float(value)
    elif isinstance(value, str):
        try:
            parsed = float(value)
        except ValueError:
            return None
    else:
        return None
    return parsed if math.isfinite(parsed) else None


def _optional_str_list(value: object, *, context: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise HydrologyDisturbanceError(f"{context} must be a list.")
    items: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise HydrologyDisturbanceError(f"{context} entries must be strings.")
        text = item.strip()
        if text:
            items.append(text)
    return tuple(items)


def _optional_mapping(value: object, *, context: str) -> dict[str, object]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise HydrologyDisturbanceError(f"{context} must be an object.")
    return {str(key): item for key, item in value.items()}


def _canonical_json_bytes(payload: object) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _pretty_json(payload: object) -> str:
    return (
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n"
    )


def _now() -> str:
    return datetime.now(UTC).isoformat()
