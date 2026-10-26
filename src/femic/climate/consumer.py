"""Join validated climate records to FEMIC attribute rows.

This is the first consumer of the ``femic.climate.v1`` contract. It selects a
climate context for an AOI, scenario, year, and variable set, then attaches the
values and their provenance to attribute rows. It does not implement a
climate-growth response; that is a later model layer.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from femic.contracts.climate import ClimateRecord


class ClimateConsumerError(ValueError):
    """Raised when a climate table cannot be resolved or attached."""


@dataclass(frozen=True)
class ClimateContext:
    """A resolved climate context for one AOI, scenario, and year.

    Attributes
    ----------
    aoi_id : str
        Area-of-interest identifier.
    scenario : str
        Scenario label.
    year : int
        Calendar year or period label.
    gcm : str
        GCM or ensemble label.
    values : dict[str, float]
        Variable to value.
    units : dict[str, str]
        Variable to canonical unit.
    source_id : str
        Upstream source identifier.
    source_version : str
        Source release or version.
    downscaling_method : str
        Downscaling or processing method.
    retrieved_utc : str
        Latest retrieval timestamp in the context.
    """

    aoi_id: str
    scenario: str
    year: int
    gcm: str
    values: dict[str, float]
    units: dict[str, str]
    source_id: str
    source_version: str
    downscaling_method: str
    retrieved_utc: str

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable context."""
        return {
            "aoi_id": self.aoi_id,
            "scenario": self.scenario,
            "year": self.year,
            "gcm": self.gcm,
            "values": dict(self.values),
            "units": dict(self.units),
            "source_id": self.source_id,
            "source_version": self.source_version,
            "downscaling_method": self.downscaling_method,
            "retrieved_utc": self.retrieved_utc,
        }


def _require_text(value: object, field: str) -> str:
    """Return a non-empty string."""
    if not isinstance(value, str) or not value.strip():
        raise ClimateConsumerError(f"{field} must be a non-empty string")
    return value.strip()


def select_climate_context(
    records: Sequence[ClimateRecord],
    *,
    aoi_id: str,
    scenario: str,
    year: int,
    variables: Sequence[str],
    gcm: str | None = None,
) -> ClimateContext:
    """Select one climate context from a validated table.

    Parameters
    ----------
    records : sequence[ClimateRecord]
        Validated climate records.
    aoi_id : str
        AOI to select.
    scenario : str
        Scenario to select.
    year : int
        Year to select.
    variables : sequence[str]
        Variables to include. Duplicates are collapsed in order.
    gcm : str | None, optional
        GCM to select. Required when the table has more than one GCM for the
        same AOI, scenario, year, and variable.

    Returns
    -------
    ClimateContext
        The resolved values, units, and provenance.

    Raises
    ------
    ClimateConsumerError
        If the selection is empty, a variable is missing, multiple GCMs or
        sources are ambiguous, or a variable has more than one record.
    """
    aoi = _require_text(aoi_id, "aoi_id")
    scenario_text = _require_text(scenario, "scenario")
    requested = tuple(dict.fromkeys(variables))
    if not requested:
        raise ClimateConsumerError("variables must not be empty")

    candidates = [
        record
        for record in records
        if record.aoi_id == aoi
        and record.scenario == scenario_text
        and record.year == year
        and record.variable in requested
    ]
    if gcm is not None:
        gcm_text = _require_text(gcm, "gcm")
        candidates = [record for record in candidates if record.gcm == gcm_text]
    if not candidates:
        raise ClimateConsumerError(
            f"no climate records for aoi={aoi!r}, scenario={scenario_text!r}, "
            f"year={year}, variables={list(requested)!r}"
        )

    gcms = sorted({record.gcm for record in candidates})
    if gcm is None and len(gcms) > 1:
        raise ClimateConsumerError(
            f"climate selection is ambiguous across GCMs: {gcms}; pass gcm"
        )
    selected: list[ClimateRecord] = []
    for variable in requested:
        matches = [record for record in candidates if record.variable == variable]
        if not matches:
            raise ClimateConsumerError(f"missing variable {variable!r}")
        if len(matches) > 1:
            raise ClimateConsumerError(
                f"variable {variable!r} has {len(matches)} records; "
                "select a single GCM or source"
            )
        selected.append(matches[0])

    sources = {
        (record.source_id, record.source_version, record.downscaling_method)
        for record in selected
    }
    if len(sources) > 1:
        raise ClimateConsumerError(
            "climate selection mixes sources: "
            + ", ".join(
                sorted(
                    f"{source}@{version}/{method}"
                    for source, version, method in sources
                )
            )
        )
    source_id, source_version, downscaling_method = next(iter(sources))
    return ClimateContext(
        aoi_id=aoi,
        scenario=scenario_text,
        year=year,
        gcm=gcms[0],
        values={record.variable: record.value for record in selected},
        units={record.variable: record.unit for record in selected},
        source_id=source_id,
        source_version=source_version,
        downscaling_method=downscaling_method,
        retrieved_utc=max(record.retrieved_utc for record in selected),
    )


def attach_climate_context(
    rows: Sequence[Mapping[str, object]],
    context: ClimateContext,
    *,
    prefix: str = "climate_",
) -> list[dict[str, object]]:
    """Attach a climate context to copies of attribute rows.

    Parameters
    ----------
    rows : sequence[mapping[str, object]]
        Attribute rows. They are copied, not mutated.
    context : ClimateContext
        Resolved climate context.
    prefix : str, optional
        Field prefix. Defaults to ``"climate_"``.

    Returns
    -------
    list[dict[str, object]]
        Copies with ``<prefix><variable>``, ``<prefix><variable>_unit``, and
        context provenance fields.

    Raises
    ------
    ClimateConsumerError
        If the prefix is empty or a row is not a mapping.
    """
    prefix_text = _require_text(prefix, "prefix")
    metadata: dict[str, object] = {
        f"{prefix_text}aoi_id": context.aoi_id,
        f"{prefix_text}scenario": context.scenario,
        f"{prefix_text}year": context.year,
        f"{prefix_text}gcm": context.gcm,
        f"{prefix_text}source_id": context.source_id,
        f"{prefix_text}source_version": context.source_version,
        f"{prefix_text}downscaling_method": context.downscaling_method,
        f"{prefix_text}retrieved_utc": context.retrieved_utc,
    }
    for variable, value in context.values.items():
        metadata[f"{prefix_text}{variable}"] = value
        metadata[f"{prefix_text}{variable}_unit"] = context.units[variable]

    attached: list[dict[str, object]] = []
    for row_number, row in enumerate(rows, start=1):
        if not isinstance(row, Mapping):
            raise ClimateConsumerError(f"row {row_number} must be a mapping")
        output = dict(row)
        output.update(metadata)
        attached.append(output)
    return attached


def attach_climate_to_rows(
    rows: Sequence[Mapping[str, object]],
    records: Sequence[ClimateRecord],
    *,
    scenario: str,
    year: int,
    variables: Sequence[str],
    gcm: str | None = None,
    aoi_field: str = "aoi_id",
    default_aoi_id: str | None = None,
    prefix: str = "climate_",
) -> list[dict[str, object]]:
    """Resolve a context per row and attach its climate values.

    Parameters
    ----------
    rows : sequence[mapping[str, object]]
        Attribute rows with an AOI field, or a default AOI id.
    records : sequence[ClimateRecord]
        Validated climate records.
    scenario : str
        Scenario to select.
    year : int
        Year to select.
    variables : sequence[str]
        Variables to include.
    gcm : str | None, optional
        GCM to select when the table is ambiguous.
    aoi_field : str, optional
        Row field naming the AOI. Defaults to ``"aoi_id"``.
    default_aoi_id : str | None, optional
        AOI to use when a row omits the field.
    prefix : str, optional
        Field prefix. Defaults to ``"climate_"``.

    Returns
    -------
    list[dict[str, object]]
        Copies of the rows with climate values and provenance.

    Raises
    ------
    ClimateConsumerError
        If a row has no AOI and no default, or a context cannot be resolved.
    """
    field = _require_text(aoi_field, "aoi_field")
    contexts: dict[str, ClimateContext] = {}
    attached: list[dict[str, object]] = []
    for row_number, row in enumerate(rows, start=1):
        if not isinstance(row, Mapping):
            raise ClimateConsumerError(f"row {row_number} must be a mapping")
        raw_aoi = row.get(field, default_aoi_id)
        if raw_aoi is None:
            raise ClimateConsumerError(
                f"row {row_number} has no {field!r} and no default_aoi_id"
            )
        aoi = _require_text(raw_aoi, f"row {row_number} {field}")
        if aoi not in contexts:
            contexts[aoi] = select_climate_context(
                records,
                aoi_id=aoi,
                scenario=scenario,
                year=year,
                variables=variables,
                gcm=gcm,
            )
        attached.extend(attach_climate_context([row], contexts[aoi], prefix=prefix))
    return attached
