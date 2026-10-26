"""Climate consumer helpers for FEMIC attribute rows."""

from femic.climate.consumer import (
    ClimateConsumerError,
    ClimateContext,
    attach_climate_context,
    attach_climate_to_rows,
    select_climate_context,
)

__all__ = [
    "ClimateConsumerError",
    "ClimateContext",
    "attach_climate_context",
    "attach_climate_to_rows",
    "select_climate_context",
]
