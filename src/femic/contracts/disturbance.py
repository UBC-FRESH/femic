"""Versioned disturbance-event contract for the FRESH modelling ecosystem.

This module owns the ``femic.disturbance.v1`` event record: the shared language
for fire, insect, drought, wind, partial mortality, harvest, and salvage events.
It validates the event, its spatial reference, its severity representation, and
its provenance before a consumer can use it.

The contract does not detect or attribute disturbances. It consumes events from
an existing detector, inventory, or expert record.
"""

from __future__ import annotations

import copy
import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

DISTURBANCE_SCHEMA_VERSION = "femic.disturbance.v1"

DISTURBANCE_TYPES: frozenset[str] = frozenset(
    {
        "fire",
        "insect",
        "disease",
        "drought",
        "wind",
        "flood",
        "partial_mortality",
        "harvest",
        "salvage",
        "other",
    }
)
SEVERITY_CLASSES: frozenset[str] = frozenset(
    {"low", "moderate", "high", "very_high", "unknown"}
)
GEOMETRY_TYPES: frozenset[str] = frozenset(
    {
        "Point",
        "LineString",
        "Polygon",
        "MultiPoint",
        "MultiLineString",
        "MultiPolygon",
        "GeometryCollection",
    }
)

DISTURBANCE_MIN_YEAR = 1900
DISTURBANCE_MAX_YEAR = 2300

DISTURBANCE_REQUIRED_FIELDS: tuple[str, ...] = (
    "schema_version",
    "event_id",
    "event_type",
    "year",
    "severity_class",
    "confidence",
    "attribution",
    "source_id",
    "source_version",
    "retrieved_utc",
)
DISTURBANCE_OPTIONAL_FIELDS: tuple[str, ...] = (
    "severity_value",
    "severity_basis",
    "attribution_method",
    "geometry",
    "fragment_ids",
    "block_ids",
    "area_ha",
    "notes",
)
DISTURBANCE_ALLOWED_FIELDS: frozenset[str] = frozenset(
    DISTURBANCE_REQUIRED_FIELDS + DISTURBANCE_OPTIONAL_FIELDS
)


class DisturbanceContractError(ValueError):
    """Raised when an event or table violates ``femic.disturbance.v1``."""


def _require_text(value: object, field: str) -> str:
    """Return a non-empty string, or raise a contract error."""
    if not isinstance(value, str) or not value.strip():
        raise DisturbanceContractError(f"{field} must be a non-empty string")
    return value.strip()


def _require_int(value: object, field: str) -> int:
    """Return an integer, rejecting booleans and non-integers."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise DisturbanceContractError(f"{field} must be an integer")
    return value


def _require_number(value: object, field: str) -> float:
    """Return a finite number, rejecting booleans, NaN, and infinity."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise DisturbanceContractError(f"{field} must be a number")
    number = float(value)
    if not math.isfinite(number):
        raise DisturbanceContractError(f"{field} must be finite")
    return number


def _require_probability(value: object, field: str) -> float:
    """Return a number in the closed interval [0, 1]."""
    number = _require_number(value, field)
    if number < 0 or number > 1:
        raise DisturbanceContractError(f"{field} must be between 0 and 1")
    return number


def _require_timestamp(value: object, field: str) -> datetime:
    """Return a timezone-aware ISO-8601 timestamp."""
    text = _require_text(value, field)
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise DisturbanceContractError(
            f"{field} must be an ISO-8601 timestamp"
        ) from exc
    if parsed.tzinfo is None:
        raise DisturbanceContractError(f"{field} must include a timezone")
    return parsed


def _optional_ids(value: object, field: str) -> tuple[int, ...]:
    """Validate an optional list of positive integer ids."""
    if value is None:
        return ()
    if not isinstance(value, list) or not value:
        raise DisturbanceContractError(f"{field} must be a non-empty list or null")
    ids: list[int] = []
    for item in value:
        identifier = _require_int(item, field)
        if identifier <= 0:
            raise DisturbanceContractError(f"{field} ids must be positive")
        ids.append(identifier)
    if len(set(ids)) != len(ids):
        raise DisturbanceContractError(f"{field} ids must be unique")
    return tuple(ids)


def _validate_geometry(value: object) -> None:
    """Validate the shallow GeoJSON shape without a geometry dependency."""
    if not isinstance(value, Mapping):
        raise DisturbanceContractError("geometry must be a GeoJSON mapping")
    geometry_type = _require_text(value.get("type"), "geometry.type")
    if geometry_type not in GEOMETRY_TYPES:
        supported = ", ".join(sorted(GEOMETRY_TYPES))
        raise DisturbanceContractError(
            f"geometry.type must be one of: {supported}; got {geometry_type!r}"
        )
    if geometry_type == "GeometryCollection":
        geometries = value.get("geometries")
        if not isinstance(geometries, list) or not geometries:
            raise DisturbanceContractError(
                "geometry.geometries must be a non-empty list"
            )
        return
    coordinates = value.get("coordinates")
    if not isinstance(coordinates, list) or not coordinates:
        raise DisturbanceContractError("geometry.coordinates must be a non-empty list")


def _build_schema() -> dict[str, object]:
    """Build the JSON Schema document for a disturbance event."""
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://femic.ubc.ca/schemas/disturbance.v1.json",
        "title": "FEMIC disturbance.v1 event",
        "type": "object",
        "additionalProperties": False,
        "required": list(DISTURBANCE_REQUIRED_FIELDS),
        "properties": {
            "schema_version": {"const": DISTURBANCE_SCHEMA_VERSION},
            "event_id": {"type": "string", "minLength": 1},
            "event_type": {"type": "string", "enum": sorted(DISTURBANCE_TYPES)},
            "year": {
                "type": "integer",
                "minimum": DISTURBANCE_MIN_YEAR,
                "maximum": DISTURBANCE_MAX_YEAR,
            },
            "severity_class": {"type": "string", "enum": sorted(SEVERITY_CLASSES)},
            "severity_value": {"type": ["number", "null"], "minimum": 0, "maximum": 1},
            "severity_basis": {"type": ["string", "null"], "minLength": 1},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "attribution": {"type": "string", "minLength": 1},
            "attribution_method": {"type": ["string", "null"], "minLength": 1},
            "geometry": {"type": ["object", "null"]},
            "fragment_ids": {
                "type": ["array", "null"],
                "items": {"type": "integer", "minimum": 1},
                "uniqueItems": True,
            },
            "block_ids": {
                "type": ["array", "null"],
                "items": {"type": "integer", "minimum": 1},
                "uniqueItems": True,
            },
            "area_ha": {"type": ["number", "null"], "minimum": 0},
            "source_id": {"type": "string", "minLength": 1},
            "source_version": {"type": "string", "minLength": 1},
            "retrieved_utc": {"type": "string", "format": "date-time"},
            "notes": {"type": ["string", "null"]},
        },
    }


#: JSON Schema for one ``femic.disturbance.v1`` event. Call
#: :func:`disturbance_schema` for a defensive copy.
DISTURBANCE_SCHEMA: dict[str, object] = _build_schema()


def disturbance_schema() -> dict[str, object]:
    """Return a defensive copy of the ``femic.disturbance.v1`` JSON Schema.

    Returns
    -------
    dict[str, object]
        A copy of the schema document, safe for a caller to mutate.
    """
    return copy.deepcopy(DISTURBANCE_SCHEMA)


def validate_disturbance_event(event: Mapping[str, object]) -> None:
    """Validate one event against ``femic.disturbance.v1``.

    Parameters
    ----------
    event : mapping[str, object]
        Candidate event.

    Raises
    ------
    DisturbanceContractError
        If the event is not a mapping, has unknown or missing fields, carries an
        unsupported type or severity class, has an out-of-range year or
        probability, has no spatial reference, or has an invalid geometry,
        timestamp, or id list.
    """
    if not isinstance(event, Mapping):
        raise DisturbanceContractError("disturbance event must be a mapping")

    unknown = set(event) - DISTURBANCE_ALLOWED_FIELDS
    if unknown:
        names = ", ".join(sorted(str(name) for name in unknown))
        raise DisturbanceContractError(f"unknown disturbance fields: {names}")

    missing = [field for field in DISTURBANCE_REQUIRED_FIELDS if field not in event]
    if missing:
        raise DisturbanceContractError(
            f"missing disturbance fields: {', '.join(missing)}"
        )

    schema_version = _require_text(event["schema_version"], "schema_version")
    if schema_version != DISTURBANCE_SCHEMA_VERSION:
        raise DisturbanceContractError(
            f"schema_version must be {DISTURBANCE_SCHEMA_VERSION!r}"
        )

    _require_text(event["event_id"], "event_id")
    event_type = _require_text(event["event_type"], "event_type")
    if event_type not in DISTURBANCE_TYPES:
        supported = ", ".join(sorted(DISTURBANCE_TYPES))
        raise DisturbanceContractError(
            f"event_type must be one of: {supported}; got {event_type!r}"
        )

    year = _require_int(event["year"], "year")
    if year < DISTURBANCE_MIN_YEAR or year > DISTURBANCE_MAX_YEAR:
        raise DisturbanceContractError(
            f"year must be between {DISTURBANCE_MIN_YEAR} and {DISTURBANCE_MAX_YEAR}"
        )

    severity_class = _require_text(event["severity_class"], "severity_class")
    if severity_class not in SEVERITY_CLASSES:
        supported = ", ".join(sorted(SEVERITY_CLASSES))
        raise DisturbanceContractError(
            f"severity_class must be one of: {supported}; got {severity_class!r}"
        )

    severity_value = event.get("severity_value")
    if severity_value is not None:
        _require_probability(severity_value, "severity_value")
        if event.get("severity_basis") is None:
            raise DisturbanceContractError(
                "severity_basis is required when severity_value is present"
            )
    severity_basis = event.get("severity_basis")
    if severity_basis is not None:
        _require_text(severity_basis, "severity_basis")

    _require_probability(event["confidence"], "confidence")
    _require_text(event["attribution"], "attribution")
    attribution_method = event.get("attribution_method")
    if attribution_method is not None:
        _require_text(attribution_method, "attribution_method")

    geometry = event.get("geometry")
    if geometry is not None:
        _validate_geometry(geometry)
    fragment_ids = _optional_ids(event.get("fragment_ids"), "fragment_ids")
    block_ids = _optional_ids(event.get("block_ids"), "block_ids")
    if geometry is None and not fragment_ids and not block_ids:
        raise DisturbanceContractError(
            "event must carry geometry, fragment_ids, or block_ids"
        )

    area_ha = event.get("area_ha")
    if area_ha is not None:
        area = _require_number(area_ha, "area_ha")
        if area < 0:
            raise DisturbanceContractError("area_ha must be non-negative")

    _require_text(event["source_id"], "source_id")
    _require_text(event["source_version"], "source_version")
    _require_timestamp(event["retrieved_utc"], "retrieved_utc")

    notes = event.get("notes")
    if notes is not None and not isinstance(notes, str):
        raise DisturbanceContractError("notes must be a string or null")


@dataclass(frozen=True)
class DisturbanceEvent:
    """One validated ``femic.disturbance.v1`` event.

    Attributes
    ----------
    event_id : str
        Stable identifier, unique within a table.
    event_type : str
        One of :data:`DISTURBANCE_TYPES`.
    year : int
        Calendar year the event began.
    severity_class : str
        One of :data:`SEVERITY_CLASSES`.
    confidence : float
        Attribution or detection confidence in [0, 1].
    attribution : str
        Cause or attribution label (for example ``wildfire`` or ``drought``).
    source_id : str
        Upstream source identifier.
    source_version : str
        Upstream source version.
    retrieved_utc : str
        Timezone-aware ISO-8601 retrieval timestamp.
    severity_value : float | None, optional
        Optional continuous severity in [0, 1]. Requires ``severity_basis``.
    severity_basis : str | None, optional
        What the continuous severity measures (for example ``dNBR``).
    attribution_method : str | None, optional
        Method or product used for attribution.
    geometry : dict[str, object] | None, optional
        Shallow-validated GeoJSON geometry.
    fragment_ids : tuple[int, ...], optional
        Positive fragment ids touched by the event.
    block_ids : tuple[int, ...], optional
        Positive block ids touched by the event.
    area_ha : float | None, optional
        Event area in hectares.
    notes : str | None, optional
        Optional free-text note.
    schema_version : str, optional
        Contract version. Defaults to :data:`DISTURBANCE_SCHEMA_VERSION`.
    """

    event_id: str
    event_type: str
    year: int
    severity_class: str
    confidence: float
    attribution: str
    source_id: str
    source_version: str
    retrieved_utc: str
    severity_value: float | None = None
    severity_basis: str | None = None
    attribution_method: str | None = None
    geometry: dict[str, object] | None = None
    fragment_ids: tuple[int, ...] = ()
    block_ids: tuple[int, ...] = ()
    area_ha: float | None = None
    notes: str | None = None
    schema_version: str = DISTURBANCE_SCHEMA_VERSION

    def to_dict(self) -> dict[str, object]:
        """Return the canonical dict form, including null optional fields."""
        return {
            "schema_version": self.schema_version,
            "event_id": self.event_id,
            "event_type": self.event_type,
            "year": self.year,
            "severity_class": self.severity_class,
            "severity_value": self.severity_value,
            "severity_basis": self.severity_basis,
            "confidence": self.confidence,
            "attribution": self.attribution,
            "attribution_method": self.attribution_method,
            "geometry": self.geometry,
            "fragment_ids": list(self.fragment_ids),
            "block_ids": list(self.block_ids),
            "area_ha": self.area_ha,
            "source_id": self.source_id,
            "source_version": self.source_version,
            "retrieved_utc": self.retrieved_utc,
            "notes": self.notes,
        }

    def to_consumer_row(self) -> dict[str, object]:
        """Return the minimal ws4-facing row for this event.

        Returns
        -------
        dict[str, object]
            A flat row with the event identity, year, type, severity,
            confidence, spatial ids, area, and source. It is deliberately
            smaller than the full record so a consumer does not need the
            contract package to report an event.
        """
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "year": self.year,
            "severity_class": self.severity_class,
            "severity_value": self.severity_value,
            "confidence": self.confidence,
            "fragment_ids": list(self.fragment_ids),
            "block_ids": list(self.block_ids),
            "area_ha": self.area_ha,
            "source_id": self.source_id,
        }

    @classmethod
    def from_dict(cls, event: Mapping[str, object]) -> DisturbanceEvent:
        """Validate and construct an event from a mapping.

        Parameters
        ----------
        event : mapping[str, object]
            Candidate event.

        Returns
        -------
        DisturbanceEvent
            The validated event.

        Raises
        ------
        DisturbanceContractError
            If the event violates ``femic.disturbance.v1``.
        """
        validate_disturbance_event(event)
        geometry = event.get("geometry")
        return cls(
            event_id=_require_text(event["event_id"], "event_id"),
            event_type=_require_text(event["event_type"], "event_type"),
            year=_require_int(event["year"], "year"),
            severity_class=_require_text(event["severity_class"], "severity_class"),
            confidence=_require_probability(event["confidence"], "confidence"),
            attribution=_require_text(event["attribution"], "attribution"),
            source_id=_require_text(event["source_id"], "source_id"),
            source_version=_require_text(event["source_version"], "source_version"),
            retrieved_utc=_require_text(event["retrieved_utc"], "retrieved_utc"),
            severity_value=(
                None
                if event.get("severity_value") is None
                else _require_probability(event["severity_value"], "severity_value")
            ),
            severity_basis=(
                None
                if event.get("severity_basis") is None
                else _require_text(event["severity_basis"], "severity_basis")
            ),
            attribution_method=(
                None
                if event.get("attribution_method") is None
                else _require_text(event["attribution_method"], "attribution_method")
            ),
            geometry=dict(geometry) if isinstance(geometry, Mapping) else None,
            fragment_ids=_optional_ids(event.get("fragment_ids"), "fragment_ids"),
            block_ids=_optional_ids(event.get("block_ids"), "block_ids"),
            area_ha=(
                None
                if event.get("area_ha") is None
                else _require_number(event["area_ha"], "area_ha")
            ),
            notes=None if event.get("notes") is None else str(event["notes"]),
        )


def _validate_unique_events(events: Sequence[DisturbanceEvent]) -> None:
    """Reject duplicate event ids in a table."""
    ids = [event.event_id for event in events]
    if len(set(ids)) != len(ids):
        duplicates = sorted({event_id for event_id in ids if ids.count(event_id) > 1})
        raise DisturbanceContractError(f"duplicate event ids: {', '.join(duplicates)}")


def read_disturbance_table(path: Path) -> tuple[DisturbanceEvent, ...]:
    """Read and validate a disturbance table from JSON.

    Parameters
    ----------
    path : pathlib.Path
        ``.json`` file containing a list of events or an object with an
        ``events`` list.

    Returns
    -------
    tuple[DisturbanceEvent, ...]
        The validated events in file order.

    Raises
    ------
    DisturbanceContractError
        If the suffix is unsupported, the file is empty, a record is invalid, or
        two events share an id.
    """
    if path.suffix.lower() != ".json":
        raise DisturbanceContractError("disturbance tables must be JSON")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        events_payload = payload.get("events")
        if events_payload is None and "event_id" in payload:
            events_payload = [payload]
        payload = events_payload
    if not isinstance(payload, list):
        raise DisturbanceContractError(
            f"{path} must contain a list of events or an object with 'events'"
        )
    events = tuple(
        DisturbanceEvent.from_dict(event)
        for event in payload
        if isinstance(event, Mapping)
    )
    if len(events) != len(payload):
        raise DisturbanceContractError(f"{path} contains a non-mapping event")
    if not events:
        raise DisturbanceContractError(f"{path} contains no disturbance events")
    _validate_unique_events(events)
    return events


def write_disturbance_table(path: Path, events: Sequence[DisturbanceEvent]) -> None:
    """Write a validated disturbance table to JSON.

    Parameters
    ----------
    path : pathlib.Path
        Destination ``.json`` path.
    events : sequence[DisturbanceEvent]
        Events to write. Each is validated before writing.

    Raises
    ------
    DisturbanceContractError
        If the suffix is unsupported, the table is empty, an event is invalid,
        or two events share an id.
    """
    if path.suffix.lower() != ".json":
        raise DisturbanceContractError("disturbance tables must be JSON")
    if not events:
        raise DisturbanceContractError(
            "disturbance table must contain at least one event"
        )
    for event in events:
        validate_disturbance_event(event.to_dict())
    _validate_unique_events(events)
    path.write_text(
        json.dumps([event.to_dict() for event in events], indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )


def summarize_disturbance_table(
    events: Sequence[DisturbanceEvent],
) -> dict[str, object]:
    """Return a provenance-bearing summary of a disturbance table.

    Parameters
    ----------
    events : sequence[DisturbanceEvent]
        Validated events.

    Returns
    -------
    dict[str, object]
        Counts, event types, severity classes, year range, total area, sources,
        attribution labels, confidence range, and spatial-reference counts.

    Raises
    ------
    DisturbanceContractError
        If the table is empty or an event is invalid.
    """
    if not events:
        raise DisturbanceContractError(
            "disturbance table must contain at least one event"
        )
    for event in events:
        validate_disturbance_event(event.to_dict())
    _validate_unique_events(events)

    sources = sorted({(event.source_id, event.source_version) for event in events})
    return {
        "schema_version": DISTURBANCE_SCHEMA_VERSION,
        "event_count": len(events),
        "event_types": sorted({event.event_type for event in events}),
        "severity_classes": sorted({event.severity_class for event in events}),
        "year_min": min(event.year for event in events),
        "year_max": max(event.year for event in events),
        "total_area_ha": sum(
            event.area_ha for event in events if event.area_ha is not None
        ),
        "sources": [
            {"source_id": source_id, "source_version": source_version}
            for source_id, source_version in sources
        ],
        "attributions": sorted({event.attribution for event in events}),
        "confidence_min": min(event.confidence for event in events),
        "confidence_max": max(event.confidence for event in events),
        "events_with_geometry": sum(
            1 for event in events if event.geometry is not None
        ),
        "events_with_fragment_ids": sum(1 for event in events if event.fragment_ids),
        "events_with_block_ids": sum(1 for event in events if event.block_ids),
    }


def consumer_rows(events: Sequence[DisturbanceEvent]) -> list[dict[str, object]]:
    """Return ws4-facing rows for a sequence of events.

    Parameters
    ----------
    events : sequence[DisturbanceEvent]
        Validated events.

    Returns
    -------
    list[dict[str, object]]
        Flat rows from :meth:`DisturbanceEvent.to_consumer_row`, in input order.
    """
    return [event.to_consumer_row() for event in events]


def events_for_block(
    events: Sequence[DisturbanceEvent], block_id: int
) -> tuple[DisturbanceEvent, ...]:
    """Return events that name a block, optionally through fragment ids.

    Parameters
    ----------
    events : sequence[DisturbanceEvent]
        Validated events.
    block_id : int
        Block id to select.

    Returns
    -------
    tuple[DisturbanceEvent, ...]
        Events whose ``block_ids`` contains ``block_id``. This is a direct
        selection only; fragment-to-block resolution belongs to the consumer.
    """
    if block_id <= 0:
        raise DisturbanceContractError("block_id must be positive")
    return tuple(event for event in events if block_id in event.block_ids)
