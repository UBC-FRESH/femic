"""Dependency-light cross-repo contracts.

The contracts package is intentionally small. It defines shared record shapes
and validators without importing FEMIC's modelling or runtime stack.
"""

from femic.contracts.climate import (
    CLIMATE_CSV_FIELDS,
    CLIMATE_MAX_YEAR,
    CLIMATE_MIN_YEAR,
    CLIMATE_SCENARIOS,
    CLIMATE_SCHEMA,
    CLIMATE_SCHEMA_VERSION,
    CLIMATE_VARIABLES,
    ClimateContractError,
    ClimateRecord,
    climate_schema,
    read_climate_table,
    summarize_climate_table,
    validate_climate_record,
    write_climate_table,
)

__all__ = [
    "CLIMATE_CSV_FIELDS",
    "CLIMATE_MAX_YEAR",
    "CLIMATE_MIN_YEAR",
    "CLIMATE_SCENARIOS",
    "CLIMATE_SCHEMA",
    "CLIMATE_SCHEMA_VERSION",
    "CLIMATE_VARIABLES",
    "ClimateContractError",
    "ClimateRecord",
    "climate_schema",
    "read_climate_table",
    "summarize_climate_table",
    "validate_climate_record",
    "write_climate_table",
]
