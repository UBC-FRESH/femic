Tier 0 Hydrology Screening Metrics
==================================

Purpose
-------

P114.4 adds fast watershed/year screening metrics from the disturbance ledger.
They describe harvest and road exposure for review and UI use.

Tier 0 is not a hydrologic response model. It does not estimate peak-flow
frequency, flood probability, or damage. Those begin in P114.5.

Metrics
-------

For each watershed and year:

- gross harvest, retention, and effective harvest area;
- ``harvest_fraction``;
- an equivalent clear-cut area (ECA) diagnostic: ``eca_area_ha`` and
  ``eca_fraction``;
- active and connected road length;
- ``road_density_km_per_km2`` and ``connected_road_density_km_per_km2``;
- active road crossings and ``crossing_density_per_km2``;
- ``riparian_effective_harvest_ha``,
  ``snow_transient_effective_harvest_ha``, and
  ``high_elevation_effective_harvest_ha``.

ECA Semantics
-------------

ECA is an explicitly diagnostic indicator:

- it uses the most recent harvest per unit;
- it can be undiscounted or discounted by a configurable linear recovery period;
- it is not a frequency-based response;
- it is not a substitute for the P114.5 stochastic analysis.

Without ``recovery_years``, ECA is undiscounted and the report warns.
With ``recovery_years``, each unit's last effective harvest area declines
linearly to zero over that period.

Road Metrics
------------

- ``road_active_km`` is the sum of active road length in the watershed.
- ``road_connected_km`` is the active length flagged as connected to streams.
- ``road_density_km_per_km2`` is active km divided by watershed area.
- ``connected_road_density_km_per_km2`` is connected km divided by watershed
  area.
- ``road_connected_fraction`` is connected km divided by active km, or null
  when no road is active.
- ``crossing_density_per_km2`` is active crossings divided by watershed area.

Exposure Context
----------------

Riparian, snow-transient, and high-elevation exposure use reviewed per-unit
fractions:

.. code-block:: python

   from femic.hydrology.screening import UnitExposureContext

   contexts = (
       UnitExposureContext(
           "u1",
           riparian_fraction=0.25,
           snow_transient_fraction=0.5,
           high_elevation_fraction=0.1,
       ),
   )

These are context-weighted fractions, not geometry intersections. The reviewed
spatial analysis that produces them belongs to P114.2 or a later spatial
overlay.

Regimes
-------

A watershed regime can be recorded as ``rain``, ``rain_on_snow``,
``snowmelt``, ``snow_transient``, or ``unknown``. Missing regimes default to
``unknown`` with a warning; this is a metadata flag, not a model.

Example
-------

.. code-block:: python

   from femic.hydrology.screening import (
       WatershedRegime,
       compute_tier0_screening,
       write_tier0_screening_report,
   )

   report = compute_tier0_screening(
       ledger,
       domain,
       regimes=(WatershedRegime("w1", "snow_transient"),),
       unit_contexts=contexts,
       recovery_years=60,
   )
   write_tier0_screening_report(
       report,
       Path("metadata/hydrology/tier0_screening.json"),
   )

Outputs
-------

The report uses schema ``femic.hydrology.screening.v1`` and records:

- screening and ledger/domain identities;
- recovery configuration;
- one row per watershed/year;
- caveats and warnings;
- deterministic ``screening_id``.

Limits
------

- ECA is a screening diagnostic, not a response model.
- Context fractions are supplied inputs, not computed geometry.
- No instance-specific threshold or operational decision is applied.
- Regime flags do not model climate or event frequency.
- The report does not replace field or hydrologist review.

See Also
--------

- :doc:`hydrology-disturbance-ledger`
- :doc:`hydrology-domain-contract`
- :doc:`../reference/contracts/hydrology-tier0-screening`
- :doc:`../reference/api/femic-hydrology-screening`
