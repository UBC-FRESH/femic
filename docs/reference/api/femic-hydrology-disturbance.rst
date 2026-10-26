``femic.hydrology.disturbance`` Module
=======================================

The :mod:`femic.hydrology.disturbance` module converts harvest, road,
retention, and recovery schedules into a complete annual unit/year disturbance
ledger. It records active road state, source event lineage, and time since
disturbance for later hydrologic response work.

It is an accounting layer, not a hydrology model or a flood-risk product.

Start Here If...
----------------

Use this page first if you are trying to:

- convert WS4/FHOPS schedules into annual unit/year rows;
- reconcile harvest area, retention, and unit area;
- track road build, use, maintenance, and decommissioning;
- preserve source event lineage; or
- hand a disturbance ledger to Tier 0 or response modelling.

Typical Usage
-------------

.. code-block:: python

   from pathlib import Path
   from femic.hydrology.disturbance import (
       DisturbanceUnit,
       HarvestEvent,
       RoadEvent,
       build_disturbance_ledger,
       write_disturbance_ledger,
       write_disturbance_ledger_csv,
   )

   ledger = build_disturbance_ledger(
       domain_id="example-domain",
       units=(
           DisturbanceUnit("u1", 10.0, "w1", "h1"),
       ),
       harvest_events=(
           HarvestEvent("h1", "u1", 2020, 4.0, 1.0),
       ),
       road_events=(
           RoadEvent("r1b", "r1", "u1", 2020, "build", 1000.0, True, 1),
       ),
       years=(2020, 2021, 2022),
   )
   write_disturbance_ledger(ledger, Path("metadata/hydrology/disturbance.json"))
   write_disturbance_ledger_csv(ledger, Path("metadata/hydrology/disturbance.csv"))

Key Entry Surfaces
------------------

- :func:`build_disturbance_ledger`
  Build a complete annual unit/year ledger with conservation checks.
- :func:`validate_disturbance_ledger`
  Check row completeness, area, road state, and age consistency.
- :func:`load_disturbance_units_csv`
- :func:`load_harvest_events_csv`
- :func:`load_road_events_csv`
  Load the first WS4/FHOPS handoff surfaces.
- :func:`write_disturbance_ledger`
- :func:`write_disturbance_ledger_csv`
  Persist JSON and one-row-per-unit/year CSV.
- :class:`DisturbanceLedger`
  Annual ledger with units, rows, caveats, and provenance.

Cross-References
----------------

- :doc:`../../guides/hydrology-disturbance-ledger`
- :doc:`../contracts/hydrology-disturbance-ledger`
- :doc:`femic-hydrology-domain`
- :doc:`femic-hydrology-bundle`
- :doc:`../cli`

.. toctree::
   :hidden:

   generated/femic.hydrology.disturbance

.. automodule:: femic.hydrology.disturbance
   :members:
   :undoc-members:
   :show-inheritance:
