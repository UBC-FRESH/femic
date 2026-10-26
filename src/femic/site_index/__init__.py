"""Site-index provenance and reconciliation helpers.

This package consumes existing BC site-index products:

- VRI ``SITE_INDEX`` and ``EST_SITE_INDEX`` per polygon;
- VDYP primary-layer ``ESTIMATED_SITE_INDEX``; and
- SIBEC BEC-unit/species estimates.

It does not derive a new site-index model.
"""

from femic.site_index.reconcile import (
    DEFAULT_DELTA_THRESHOLD,
    DEFAULT_MIN_SIBEC_PLOT_COUNT,
    RECONCILIATION_SCHEMA_VERSION,
    SiteIndexReconciliationError,
    reconcile_site_index,
    summarize_reconciliation,
)
from femic.site_index.sibec import (
    SIBEC_SCHEMA_VERSION,
    SibecError,
    aggregate_sibec_by_bgc_unit,
    load_sibec_table,
)
from femic.site_index.vdyp import (
    VDYP_SCHEMA_VERSION,
    VdypError,
    load_vdyp_site_index,
)
from femic.site_index.vri import (
    VRI_SCHEMA_VERSION,
    VriError,
    compose_bec_unit,
    load_vri_site_index,
    normalise_species,
)

__all__ = [
    "DEFAULT_DELTA_THRESHOLD",
    "DEFAULT_MIN_SIBEC_PLOT_COUNT",
    "RECONCILIATION_SCHEMA_VERSION",
    "SIBEC_SCHEMA_VERSION",
    "VDYP_SCHEMA_VERSION",
    "VRI_SCHEMA_VERSION",
    "SibecError",
    "SiteIndexReconciliationError",
    "VdypError",
    "VriError",
    "aggregate_sibec_by_bgc_unit",
    "compose_bec_unit",
    "load_sibec_table",
    "load_vdyp_site_index",
    "load_vri_site_index",
    "normalise_species",
    "reconcile_site_index",
    "summarize_reconciliation",
]
