Hydrology Disturbance Ledger
============================

Purpose
-------

P114.3 converts harvest, road, retention, and recovery schedules into a
complete annual ledger by spatial unit and year. It is the bridge between
WS4/FHOPS schedules and later hydrologic response work.

The ledger is accounting. It is not a flood response, a recovery curve, or an
operability decision.

Ledger Contract
---------------

The ledger uses schema ``femic.hydrology.disturbance.v1``. It contains:

- one record for every spatial unit and every year, including years with no
  event;
- ``harvest_area_ha`` and ``retention_area_ha``;
- ``effective_harvest_area_ha``;
- ``road_active_length_m``, ``road_connected_length_m``,
  ``road_built_length_m``, and ``road_decommissioned_length_m``;
- ``road_crossing_count``;
- ``years_since_harvest`` and ``years_since_road_build``;
- ``source_event_ids``.

Inputs
------

Units:

.. code-block:: python

   from femic.hydrology.disturbance import DisturbanceUnit

   units = (
       DisturbanceUnit("u1", area_ha=10.0, watershed_id="w1", hru_id="h1"),
       DisturbanceUnit("u2", area_ha=20.0, watershed_id="w1", hru_id="h2"),
   )

Harvest events:

.. code-block:: python

   from femic.hydrology.disturbance import HarvestEvent

   harvest_events = (
       HarvestEvent(
           event_id="h1",
           unit_id="u1",
           year=2020,
           area_ha=4.0,
           retention_area_ha=1.0,
           treatment="partial",
           source="ws4",
       ),
   )

Road events:

.. code-block:: python

   from femic.hydrology.disturbance import RoadEvent

   road_events = (
       RoadEvent(
           event_id="r1b",
           road_id="r1",
           unit_id="u1",
           year=2020,
           action="build",
           length_m=1000.0,
           connected_to_stream=True,
           crossing_count=1,
           source="fhops",
       ),
   )

Build the ledger:

.. code-block:: python

   from pathlib import Path
   from femic.hydrology.disturbance import (
       build_disturbance_ledger,
       write_disturbance_ledger,
       write_disturbance_ledger_csv,
   )

   ledger = build_disturbance_ledger(
       domain_id="example-domain",
       units=units,
       harvest_events=harvest_events,
       road_events=road_events,
       years=(2020, 2021, 2022),
   )
   write_disturbance_ledger(ledger, Path("metadata/hydrology/disturbance.json"))
   write_disturbance_ledger_csv(ledger, Path("metadata/hydrology/disturbance.csv"))

CSV Handoff
-----------

Three simple CSV surfaces support WS4/FHOPS handoff:

- units: ``unit_id, area_ha, watershed_id, hru_id``
- harvest: ``event_id, unit_id, year, area_ha, retention_area_ha, treatment, source``
- roads: ``event_id, road_id, unit_id, year, action, length_m, connected_to_stream, crossing_count, source``

Load them with ``load_disturbance_units_csv``, ``load_harvest_events_csv``, and
``load_road_events_csv``.

Road State
----------

- ``build`` adds active length, connected length when applicable, and crossings.
- ``decommission`` subtracts the same quantities.
- ``use`` and ``maintain`` do not change the state.
- A road may not be built while already active.
- Decommissioning cannot exceed active length, connected length, or active
  crossings.
- A road ID may not span units.

Conservation
------------

The build rejects:

- duplicate unit, year, harvest-event, or road-event IDs;
- unknown units;
- event years outside the ledger;
- non-positive harvest area or build/decommission length;
- retention greater than harvest area;
- total harvest greater than unit area;
- invalid road actions;
- road decommissioning that exceeds active state.

Every unit/year row must exist. The validation also checks row area, road, age,
and effective-area consistency.

Recovery Semantics
------------------

``years_since_harvest`` and ``years_since_road_build`` record time since the
last event. They do not imply a recovery curve. Hydrologic recovery belongs to
P114.5/P114.7.

Limits
------

- Unit geometry is not dissolved or recalculated; units carry their source
  identifiers.
- Road length is event-level accounting, not a survey-grade road inventory.
- Crossings are counted from road events, not inferred from stream crossings.
- Retention is recorded as area within harvest, not as a spatial polygon.
- The ledger is not a flood-risk product.
- No private data belongs in a tracked ledger or fixture.

See Also
--------

- :doc:`hydrology-domain-contract`
- :doc:`hydrology-data-bundle`
- :doc:`../reference/contracts/hydrology-disturbance-ledger`
- :doc:`../reference/api/femic-hydrology-disturbance`
