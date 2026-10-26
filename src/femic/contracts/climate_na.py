"""ClimateNA/SilvR21 CSV adapter for the ``femic.climate.v1`` contract.

The adapter reads an annual ClimateNA-style CSV, maps its columns to canonical
climate variables, and emits validated :class:`~femic.contracts.climate.ClimateRecord`
rows. It does not download data, choose a GCM ensemble, or model climate.

ClimateNA files are wide and their column sets vary by version. The default map
covers the annual columns used most often; a caller can supply an explicit map
when a release uses different names.
"""

from __future__ import annotations

import csv
from collections.abc import Mapping
from pathlib import Path

from femic.contracts.climate import (
    CLIMATE_VARIABLES,
    ClimateContractError,
    ClimateRecord,
)

#: Annual ClimateNA columns and their canonical ``(variable, unit)`` pairs.
DEFAULT_CLIMATE_NA_COLUMNS: dict[str, tuple[str, str]] = {
    "MAT": ("tavg", "degC"),
    "Tave": ("tavg", "degC"),
    "MAP": ("ppt", "mm"),
    "PPT": ("ppt", "mm"),
    "MWMT": ("mwmt", "degC"),
    "MCMT": ("mcmt", "degC"),
    "DD5": ("gdd", "degree_days"),
    "NFFD": ("nffd", "days"),
    "PAS": ("snow", "mm"),
    "CMD": ("cwd", "mm"),
    "Eref": ("pet", "mm"),
    "RH": ("rh", "percent"),
    "VPD": ("vpd", "kPa"),
}

_MISSING_TOKENS: frozenset[str] = frozenset({"", "na", "n/a", "nan", "null", "none"})


def climate_na_columns() -> dict[str, tuple[str, str]]:
    """Return a defensive copy of the default ClimateNA column map."""
    return dict(DEFAULT_CLIMATE_NA_COLUMNS)


def _validate_column_map(
    column_map: Mapping[str, tuple[str, str]],
) -> dict[str, tuple[str, str]]:
    """Validate and normalize a caller-supplied column map."""
    if not isinstance(column_map, Mapping) or not column_map:
        raise ClimateContractError("column_map must be a non-empty mapping")
    normalized: dict[str, tuple[str, str]] = {}
    for column, mapping in column_map.items():
        if not isinstance(column, str) or not column.strip():
            raise ClimateContractError("column_map keys must be non-empty strings")
        if not isinstance(mapping, tuple) or len(mapping) != 2:
            raise ClimateContractError(
                f"column_map[{column!r}] must be a (variable, unit) tuple"
            )
        variable, unit = mapping
        if variable not in CLIMATE_VARIABLES:
            raise ClimateContractError(
                f"column_map[{column!r}] variable {variable!r} is not canonical"
            )
        expected_unit = CLIMATE_VARIABLES[variable]
        if unit != expected_unit:
            raise ClimateContractError(
                f"column_map[{column!r}] unit for {variable!r} must be "
                f"{expected_unit!r}; got {unit!r}"
            )
        normalized[column.strip()] = (variable, unit)
    return normalized


def read_climate_na_csv(
    path: Path,
    *,
    aoi_id: str,
    year: int,
    scenario: str,
    gcm: str,
    source_version: str,
    retrieved_utc: str,
    source_id: str = "climate-na",
    downscaling_method: str = "climate-na",
    column_map: Mapping[str, tuple[str, str]] | None = None,
    row_id_column: str = "ID",
    variance: float | None = None,
    notes: str | None = None,
    require_all_columns: bool = False,
) -> tuple[ClimateRecord, ...]:
    """Read a ClimateNA-style annual CSV and emit climate records.

    Parameters
    ----------
    path : pathlib.Path
        CSV file with one row per location and ClimateNA annual columns.
    aoi_id : str
        Base area-of-interest id. With multiple rows, the record id is
        ``f"{aoi_id}:{row_id}"``; with one row it is ``aoi_id``.
    year : int
        Calendar year or period label for every record in the file.
    scenario : str
        Scenario label from the canonical climate vocabulary.
    gcm : str
        GCM or ensemble label.
    source_version : str
        ClimateNA/SilvR21 release or version.
    retrieved_utc : str
        Timezone-aware ISO-8601 retrieval timestamp.
    source_id : str, optional
        Upstream source id. Defaults to ``"climate-na"``.
    downscaling_method : str, optional
        Downscaling method. Defaults to ``"climate-na"``.
    column_map : mapping[str, tuple[str, str]] | None, optional
        Source column to ``(variable, unit)`` mapping. Defaults to
        :data:`DEFAULT_CLIMATE_NA_COLUMNS`.
    row_id_column : str, optional
        Column used to distinguish locations. Defaults to ``"ID"``.
    variance : float | None, optional
        Optional variance applied to every emitted record.
    notes : str | None, optional
        Optional note; the source column name is appended for provenance.
    require_all_columns : bool, optional
        If true, every mapped column must exist in the CSV. Defaults to false
        so a release with a smaller annual column set still loads.

    Returns
    -------
    tuple[ClimateRecord, ...]
        Validated records in CSV row and column-map order.

    Raises
    ------
    ClimateContractError
        If the file is not a CSV, has no header or rows, a mapped column is
        missing when required, a mapped value is not numeric, no records are
        produced, or a record violates ``femic.climate.v1``.
    """
    if path.suffix.lower() != ".csv":
        raise ClimateContractError("ClimateNA adapter requires a .csv file")
    mapping = _validate_column_map(column_map or DEFAULT_CLIMATE_NA_COLUMNS)

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ClimateContractError(f"{path} has no CSV header")
        fieldnames = list(reader.fieldnames)
        missing = [column for column in mapping if column not in fieldnames]
        if missing and require_all_columns:
            raise ClimateContractError(
                f"{path} is missing mapped columns: {', '.join(missing)}"
            )
        present = [column for column in mapping if column in fieldnames]
        if not present:
            raise ClimateContractError(
                f"{path} has none of the mapped ClimateNA columns"
            )
        rows = list(reader)

    if not rows:
        raise ClimateContractError(f"{path} contains no data rows")

    records: list[ClimateRecord] = []
    for row_number, row in enumerate(rows, start=2):
        row_id = str(row.get(row_id_column, "")).strip()
        if len(rows) > 1:
            aoi = f"{aoi_id}:{row_id or row_number}"
        else:
            aoi = aoi_id
        for column in present:
            raw = str(row.get(column, "")).strip()
            if raw.lower() in _MISSING_TOKENS:
                continue
            try:
                value = float(raw)
            except ValueError as exc:
                raise ClimateContractError(
                    f"{path} row {row_number} column {column!r} is not numeric: {raw!r}"
                ) from exc
            variable, unit = mapping[column]
            record_notes = notes
            column_note = f"source_column={column}"
            if record_notes:
                record_notes = f"{record_notes}; {column_note}"
            else:
                record_notes = column_note
            payload: dict[str, object] = {
                "schema_version": "femic.climate.v1",
                "aoi_id": aoi,
                "variable": variable,
                "unit": unit,
                "year": year,
                "scenario": scenario,
                "gcm": gcm,
                "value": value,
                "variance": variance,
                "source_id": source_id,
                "source_version": source_version,
                "downscaling_method": downscaling_method,
                "retrieved_utc": retrieved_utc,
                "notes": record_notes,
            }
            try:
                records.append(ClimateRecord.from_dict(payload))
            except ClimateContractError as exc:
                raise ClimateContractError(
                    f"{path} row {row_number} column {column!r}: {exc}"
                ) from exc

    if not records:
        raise ClimateContractError(
            f"{path} produced no climate records; every mapped value was missing"
        )
    return tuple(records)
