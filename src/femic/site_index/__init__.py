"""Site-index provenance and reconciliation helpers.

This package consumes existing BC site-index products:

- VRI ``SITE_INDEX`` and ``EST_SITE_INDEX`` per polygon;
- VDYP primary-layer ``ESTIMATED_SITE_INDEX``; and
- SIBEC BEC-unit/species estimates.

It does not derive a new site-index model.
"""

from femic.site_index.au import (
    AU_SCHEMA_VERSION,
    AuSiteIndexError,
    load_au_site_index,
    summarize_au_site_index,
)
from femic.site_index.reconcile import (
    DEFAULT_DELTA_THRESHOLD,
    DEFAULT_MIN_SIBEC_PLOT_COUNT,
    RECONCILIATION_SCHEMA_VERSION,
    SiteIndexReconciliationError,
    reconcile_site_index,
    summarize_reconciliation,
)
from femic.site_index.sibec import (
    DEFAULT_SIBEC_PREFERENCE,
    SIBEC_SCHEMA_VERSION,
    SIBEC_SOURCE_2013,
    SIBEC_SOURCE_2014,
    SibecError,
    aggregate_sibec_by_bgc_unit,
    combine_sibec_tables,
    load_sibec_addendum,
    load_sibec_table,
    select_sibec_source,
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
    "AU_SCHEMA_VERSION",
    "DEFAULT_DELTA_THRESHOLD",
    "DEFAULT_MIN_SIBEC_PLOT_COUNT",
    "DEFAULT_SIBEC_PREFERENCE",
    "RECONCILIATION_SCHEMA_VERSION",
    "SIBEC_SCHEMA_VERSION",
    "SIBEC_SOURCE_2013",
    "SIBEC_SOURCE_2014",
    "VDYP_SCHEMA_VERSION",
    "VRI_SCHEMA_VERSION",
    "AuSiteIndexError",
    "SibecError",
    "SiteIndexReconciliationError",
    "VdypError",
    "VriError",
    "aggregate_sibec_by_bgc_unit",
    "combine_sibec_tables",
    "compose_bec_unit",
    "load_au_site_index",
    "load_sibec_addendum",
    "load_sibec_table",
    "load_vdyp_site_index",
    "load_vri_site_index",
    "normalise_species",
    "reconcile_site_index",
    "select_sibec_source",
    "summarize_au_site_index",
    "summarize_reconciliation",
]
