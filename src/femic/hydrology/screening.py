"""Tier 0 hydrology screening metrics and caveats.

These metrics describe harvest and road exposure. They are diagnostics, not a
hydrologic response model.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

HYDROLOGY_SCREENING_SCHEMA_VERSION = "femic.hydrology.screening.v1"
HYDROLOGY_SCREENING_REGIMES: tuple[str, ...] = (
    "rain",
    "rain_on_snow",
    "snowmelt",
    "snow_transient",
    "unknown",
)


class HydrologyScreeningError(RuntimeError):
    """Raised when Tier 0 screening inputs or outputs are invalid."""


@dataclass(frozen=True)
class WatershedRegime:
    """Hydrologic regime metadata for one watershed."""

    watershed_id: str
    regime: str = "unknown"
    notes: str = ""

    def to_dict(self) -> dict[str, object]:
        """Return the regime as a JSON-serializable mapping."""

        return {
            "watershed_id": self.watershed_id,
            "regime": self.regime,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class UnitExposureContext:
    """Reviewed per-unit fractions used for screening exposure metrics."""

    unit_id: str
    riparian_fraction: float = 0.0
    snow_transient_fraction: float = 0.0
    high_elevation_fraction: float = 0.0

    def to_dict(self) -> dict[str, object]:
        """Return the context as a JSON-serializable mapping."""

        return {
            "unit_id": self.unit_id,
            "riparian_fraction": self.riparian_fraction,
            "snow_transient_fraction": self.snow_transient_fraction,
            "high_elevation_fraction": self.high_elevation_fraction,
        }


@dataclass(frozen=True)
class Tier0ScreeningRow:
    """One watershed/year Tier 0 screening row."""

    year: int
    watershed_id: str
    regime: str
    watershed_area_ha: float
    harvest_area_ha: float
    retention_area_ha: float
    effective_harvest_area_ha: float
    harvest_fraction: float
    eca_area_ha: float
    eca_fraction: float
    road_active_km: float
    road_connected_km: float
    road_density_km_per_km2: float
    connected_road_density_km_per_km2: float
    road_connected_fraction: float | None
    crossing_count: int
    crossing_density_per_km2: float
    riparian_effective_harvest_ha: float
    snow_transient_effective_harvest_ha: float
    high_elevation_effective_harvest_ha: float

    def to_dict(self) -> dict[str, object]:
        """Return the row as a JSON-serializable mapping."""

        return {
            "year": self.year,
            "watershed_id": self.watershed_id,
            "regime": self.regime,
            "watershed_area_ha": self.watershed_area_ha,
            "harvest_area_ha": self.harvest_area_ha,
            "retention_area_ha": self.retention_area_ha,
            "effective_harvest_area_ha": self.effective_harvest_area_ha,
            "harvest_fraction": self.harvest_fraction,
            "eca_area_ha": self.eca_area_ha,
            "eca_fraction": self.eca_fraction,
            "road_active_km": self.road_active_km,
            "road_connected_km": self.road_connected_km,
            "road_density_km_per_km2": self.road_density_km_per_km2,
            "connected_road_density_km_per_km2": (
                self.connected_road_density_km_per_km2
            ),
            "road_connected_fraction": self.road_connected_fraction,
            "crossing_count": self.crossing_count,
            "crossing_density_per_km2": self.crossing_density_per_km2,
            "riparian_effective_harvest_ha": self.riparian_effective_harvest_ha,
            "snow_transient_effective_harvest_ha": (
                self.snow_transient_effective_harvest_ha
            ),
            "high_elevation_effective_harvest_ha": (
                self.high_elevation_effective_harvest_ha
            ),
        }


@dataclass(frozen=True)
class Tier0ScreeningReport:
    """Tier 0 screening report for one disturbance ledger and domain."""

    screening_id: str
    generated_utc: str
    ledger_id: str
    domain_id: str
    recovery_years: int | None
    rows: tuple[Tier0ScreeningRow, ...]
    caveats: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    provenance: dict[str, object] = field(default_factory=dict)
    schema_version: str = HYDROLOGY_SCREENING_SCHEMA_VERSION

    def to_dict(self) -> dict[str, object]:
        """Return the screening report as a JSON-serializable mapping."""

        return {
            "schema_version": self.schema_version,
            "screening_id": self.screening_id,
            "generated_utc": self.generated_utc,
            "ledger_id": self.ledger_id,
            "domain_id": self.domain_id,
            "recovery_years": self.recovery_years,
            "summary": {"row_count": len(self.rows)},
            "rows": [row.to_dict() for row in self.rows],
            "caveats": list(self.caveats),
            "warnings": list(self.warnings),
            "provenance": self.provenance,
        }


def compute_tier0_screening(
    ledger: object,
    domain: object,
    *,
    regimes: Sequence[WatershedRegime] = (),
    unit_contexts: Sequence[UnitExposureContext] = (),
    recovery_years: int | None = None,
    generated_utc: str | None = None,
) -> Tier0ScreeningReport:
    """Compute watershed/year Tier 0 screening metrics.

    The metrics are:
    - gross/effective harvest and harvest fraction;
    - a configurable, optionally recovery-discounted ECA diagnostic;
    - road density, connected-road density, and crossing density;
    - context-weighted riparian, snow-transient, and high-elevation exposure.

    The context fractions are supplied by a reviewed spatial analysis; this
    function does not intersect geometries or resample rasters.
    """

    from femic.hydrology.disturbance import (
        DisturbanceLedger,
        validate_disturbance_ledger,
    )
    from femic.hydrology.domain import (
        HydrologyDomainManifest,
        validate_hydrology_domain,
    )

    if not isinstance(ledger, DisturbanceLedger):
        raise HydrologyScreeningError("ledger must be a DisturbanceLedger.")
    if not isinstance(domain, HydrologyDomainManifest):
        raise HydrologyScreeningError("domain must be a HydrologyDomainManifest.")
    ledger_validation = validate_disturbance_ledger(ledger)
    if not ledger_validation.is_valid:
        raise HydrologyScreeningError("; ".join(ledger_validation.errors))
    domain_validation = validate_hydrology_domain(domain)
    if not domain_validation.is_valid:
        raise HydrologyScreeningError("; ".join(domain_validation.errors))
    if ledger.domain_id != domain.domain_id:
        raise HydrologyScreeningError(
            "Disturbance ledger and hydrology domain IDs do not match."
        )
    if recovery_years is not None and recovery_years <= 0:
        raise HydrologyScreeningError("recovery_years must be positive when supplied.")

    watershed_area_ha = {
        watershed.watershed_id: watershed.area_km2 * 100.0
        for watershed in domain.watersheds
    }
    unit_map = {unit.unit_id: unit for unit in ledger.units}
    for unit in ledger.units:
        if unit.watershed_id not in watershed_area_ha:
            raise HydrologyScreeningError(
                f"Disturbance unit {unit.unit_id!r} references unknown watershed "
                f"{unit.watershed_id!r}."
            )
    regime_map = _normalize_regimes(regimes, watershed_ids=set(watershed_area_ha))
    context_map = _normalize_contexts(unit_contexts, unit_ids=set(unit_map))
    warnings: list[str] = []
    if recovery_years is None:
        warnings.append("ECA is undiscounted because recovery_years was not supplied.")
    if not regime_map:
        warnings.append("No watershed regime was supplied; regime is `unknown`.")
    if not context_map:
        warnings.append(
            "No unit exposure context was supplied; riparian, snow-transient, and "
            "high-elevation exposure metrics are zero."
        )
    elif len(context_map) != len(unit_map):
        warnings.append(
            "Some units have no exposure context; their context-weighted exposure "
            "is zero."
        )
    row_map = {(row.year, row.unit_id): row for row in ledger.rows}
    eca_by_watershed_year: dict[tuple[str, int], float] = {}
    last_effective_by_unit: dict[str, float] = {}
    for year in ledger.years:
        for unit in ledger.units:
            row = row_map[(year, unit.unit_id)]
            if row.harvest_area_ha > 0:
                last_effective_by_unit[unit.unit_id] = row.effective_harvest_area_ha
            last_effective = last_effective_by_unit.get(unit.unit_id, 0.0)
            contribution = _recovery_adjusted_area(
                last_effective,
                years_since_harvest=row.years_since_harvest,
                recovery_years=recovery_years,
            )
            key = (unit.watershed_id, year)
            eca_by_watershed_year[key] = (
                eca_by_watershed_year.get(key, 0.0) + contribution
            )
    rows: list[Tier0ScreeningRow] = []
    for year in ledger.years:
        for watershed in sorted(domain.watersheds, key=lambda item: item.watershed_id):
            units = [
                unit
                for unit in ledger.units
                if unit.watershed_id == watershed.watershed_id
            ]
            unit_rows = [row_map[(year, unit.unit_id)] for unit in units]
            harvest_area = sum(row.harvest_area_ha for row in unit_rows)
            retention_area = sum(row.retention_area_ha for row in unit_rows)
            effective_area = sum(row.effective_harvest_area_ha for row in unit_rows)
            active_m = sum(row.road_active_length_m for row in unit_rows)
            connected_m = sum(row.road_connected_length_m for row in unit_rows)
            crossing_count = sum(row.road_crossing_count for row in unit_rows)
            area_ha = watershed_area_ha[watershed.watershed_id]
            area_km2 = area_ha / 100.0
            eca_area = eca_by_watershed_year.get((watershed.watershed_id, year), 0.0)
            active_km = active_m / 1000.0
            connected_km = connected_m / 1000.0
            riparian = sum(
                row.effective_harvest_area_ha
                * context_map.get(
                    unit.unit_id, UnitExposureContext(unit.unit_id)
                ).riparian_fraction
                for unit, row in zip(units, unit_rows, strict=False)
            )
            snow_transient = sum(
                row.effective_harvest_area_ha
                * context_map.get(
                    unit.unit_id,
                    UnitExposureContext(unit.unit_id),
                ).snow_transient_fraction
                for unit, row in zip(units, unit_rows, strict=False)
            )
            high_elevation = sum(
                row.effective_harvest_area_ha
                * context_map.get(
                    unit.unit_id,
                    UnitExposureContext(unit.unit_id),
                ).high_elevation_fraction
                for unit, row in zip(units, unit_rows, strict=False)
            )
            rows.append(
                Tier0ScreeningRow(
                    year=year,
                    watershed_id=watershed.watershed_id,
                    regime=regime_map.get(watershed.watershed_id, "unknown"),
                    watershed_area_ha=area_ha,
                    harvest_area_ha=harvest_area,
                    retention_area_ha=retention_area,
                    effective_harvest_area_ha=effective_area,
                    harvest_fraction=harvest_area / area_ha,
                    eca_area_ha=eca_area,
                    eca_fraction=eca_area / area_ha,
                    road_active_km=active_km,
                    road_connected_km=connected_km,
                    road_density_km_per_km2=active_km / area_km2,
                    connected_road_density_km_per_km2=connected_km / area_km2,
                    road_connected_fraction=(
                        connected_km / active_km if active_km > 0 else None
                    ),
                    crossing_count=crossing_count,
                    crossing_density_per_km2=crossing_count / area_km2,
                    riparian_effective_harvest_ha=riparian,
                    snow_transient_effective_harvest_ha=snow_transient,
                    high_elevation_effective_harvest_ha=high_elevation,
                )
            )
    record_rows = tuple(rows)
    screening_id = _screening_id(
        ledger_id=ledger.ledger_id,
        domain_id=domain.domain_id,
        recovery_years=recovery_years,
        rows=record_rows,
    )
    return Tier0ScreeningReport(
        screening_id=screening_id,
        generated_utc=generated_utc or _now(),
        ledger_id=ledger.ledger_id,
        domain_id=domain.domain_id,
        recovery_years=recovery_years,
        rows=record_rows,
        caveats=(
            "Tier 0 metrics are screening diagnostics, not a flood response.",
            "ECA is not a substitute for frequency-based hydrologic analysis.",
            (
                "Context-weighted exposure uses reviewed unit fractions; it is not "
                "a geometry intersection."
            ),
            "No instance-specific threshold or operational decision is applied.",
        ),
        warnings=tuple(warnings),
        provenance={
            "producer": "femic.hydrology.screening",
            "ledger_id": ledger.ledger_id,
            "domain_id": domain.domain_id,
        },
    )


def write_tier0_screening_report(
    report: Tier0ScreeningReport,
    path: Path,
) -> Path:
    """Write a Tier 0 screening report as pretty-printed JSON."""

    resolved = path.expanduser().resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(
        json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return resolved


def _normalize_regimes(
    regimes: Sequence[WatershedRegime],
    *,
    watershed_ids: set[str],
) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for regime in regimes:
        if regime.watershed_id not in watershed_ids:
            raise HydrologyScreeningError(
                f"Regime references unknown watershed {regime.watershed_id!r}."
            )
        if regime.watershed_id in normalized:
            raise HydrologyScreeningError(
                f"Duplicate regime for watershed {regime.watershed_id!r}."
            )
        if regime.regime not in HYDROLOGY_SCREENING_REGIMES:
            raise HydrologyScreeningError(
                f"Unsupported regime {regime.regime!r} for watershed "
                f"{regime.watershed_id!r}."
            )
        normalized[regime.watershed_id] = regime.regime
    return normalized


def _normalize_contexts(
    contexts: Sequence[UnitExposureContext],
    *,
    unit_ids: set[str],
) -> dict[str, UnitExposureContext]:
    normalized: dict[str, UnitExposureContext] = {}
    for context in contexts:
        if context.unit_id not in unit_ids:
            raise HydrologyScreeningError(
                f"Exposure context references unknown unit {context.unit_id!r}."
            )
        if context.unit_id in normalized:
            raise HydrologyScreeningError(
                f"Duplicate exposure context for unit {context.unit_id!r}."
            )
        for name, value in (
            ("riparian_fraction", context.riparian_fraction),
            ("snow_transient_fraction", context.snow_transient_fraction),
            ("high_elevation_fraction", context.high_elevation_fraction),
        ):
            if value < 0 or value > 1 or not math.isfinite(value):
                raise HydrologyScreeningError(
                    f"{name} for unit {context.unit_id!r} must be between 0 and 1."
                )
        normalized[context.unit_id] = context
    return normalized


def _recovery_adjusted_area(
    effective_area_ha: float,
    *,
    years_since_harvest: int | None,
    recovery_years: int | None,
) -> float:
    if effective_area_ha <= 0 or years_since_harvest is None:
        return 0.0
    if recovery_years is None:
        return effective_area_ha
    remaining = max(0.0, 1.0 - years_since_harvest / recovery_years)
    return effective_area_ha * remaining


def _screening_id(
    *,
    ledger_id: str,
    domain_id: str,
    recovery_years: int | None,
    rows: Sequence[Tier0ScreeningRow],
) -> str:
    material = {
        "ledger_id": ledger_id,
        "domain_id": domain_id,
        "recovery_years": recovery_years,
        "rows": [row.to_dict() for row in rows],
    }
    digest = hashlib.sha256(_canonical_json_bytes(material)).hexdigest()
    return f"hydro-screen-{digest[:16]}"


def _canonical_json_bytes(payload: object) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _now() -> str:
    return datetime.now(UTC).isoformat()
