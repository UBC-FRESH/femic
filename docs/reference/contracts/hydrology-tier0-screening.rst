Tier 0 Hydrology Screening Contract
===================================

Purpose
-------

This page is the short source-of-truth contract for FEMIC P114.4 Tier 0
screening metrics. It defines the metric grain, ECA semantics, road/crossing
metrics, exposure context, regime flags, caveats, and output schema.

Tier 0 is a screening diagnostic, not a hydrologic response model.

Quick Contract
--------------

- Schema: ``femic.hydrology.screening.v1``.
- Grain: one row per watershed per year.
- Inputs: disturbance ledger, hydrology domain, optional regimes, optional unit
  exposure contexts, optional recovery period.
- ECA is diagnostic and may be undiscounted or linearly discounted.
- Road metrics are active-state density metrics.
- Exposure metrics are context-weighted fractions, not geometry intersections.
- No instance-specific threshold or operational decision.

Metric Definitions
------------------

Per watershed/year:

- ``harvest_area_ha``, ``retention_area_ha``, ``effective_harvest_area_ha``;
- ``harvest_fraction``;
- ``eca_area_ha`` and ``eca_fraction``;
- ``road_active_km`` and ``road_connected_km``;
- ``road_density_km_per_km2`` and ``connected_road_density_km_per_km2``;
- ``road_connected_fraction``;
- ``crossing_count`` and ``crossing_density_per_km2``;
- ``riparian_effective_harvest_ha``;
- ``snow_transient_effective_harvest_ha``;
- ``high_elevation_effective_harvest_ha``.

ECA Semantics
-------------

ECA uses the most recent harvest per unit. Without ``recovery_years`` it is
undiscounted and the report carries a warning. With ``recovery_years`` the last
effective harvest area declines linearly to zero over that period.

ECA is explicitly not a frequency-based peak-flow response and not a substitute
for P114.5.

Road And Crossing Metrics
-------------------------

- Active road length is the disturbance-ledger active length sum.
- Connected road length is the active length flagged connected to streams.
- Road density uses watershed area in km².
- Crossing density uses active crossings and watershed area in km².
- A zero active road length produces a null ``road_connected_fraction``.

Exposure Context
----------------

``UnitExposureContext`` carries reviewed fractions in ``[0, 1]``:

- ``riparian_fraction``;
- ``snow_transient_fraction``;
- ``high_elevation_fraction``.

The metrics multiply current-year effective harvest area by these fractions.
They are not geometry intersections and do not imply a spatial buffer or
elevation model.

Regimes
-------

Allowed regimes are ``rain``, ``rain_on_snow``, ``snowmelt``,
``snow_transient``, and ``unknown``. Missing regimes default to ``unknown`` and
produce a warning. Regime is a metadata flag, not a model.

Caveats
-------

- Tier 0 metrics are screening diagnostics, not a flood response.
- ECA is not a substitute for frequency-based hydrologic analysis.
- Context-weighted exposure is not a geometry intersection.
- No instance-specific threshold or operational decision is applied.
- The report does not replace hydrologist or field review.

Cross-References
----------------

- :doc:`../../guides/hydrology-tier0-screening`
- :doc:`hydrology-disturbance-ledger`
- :doc:`hydrology-domain`
- :doc:`../api/femic-hydrology-screening`
