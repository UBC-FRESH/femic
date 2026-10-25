Hydrology Disturbance Ledger Contract
=====================================

Purpose
-------

This page is the short source-of-truth contract for FEMIC P114.3 annual
disturbance ledgers. It defines the schema, unit/year completeness, harvest and
retention accounting, road state rules, conservation checks, CSV handoff, and
recovery semantics.

The ledger is an accounting bridge from WS4/FHOPS schedules to hydrologic
response. It is not a flood response or operational decision.

Quick Contract
--------------

- Schema: ``femic.hydrology.disturbance.v1``.
- Grain: one row per spatial unit per year.
- Required row completeness: every unit × every year.
- Harvest: gross area and retention area; effective = gross - retention.
- Roads: active, connected, built, decommissioned length and active crossings.
- Recovery: time since last event only; no recovery curve.
- Road actions: ``build``, ``use``, ``maintain``, ``decommission``.
- Every row carries source event IDs.
- No private data in tracked ledgers or fixtures.

Manifest Fields
---------------

The ledger records:

- ``ledger_id``, ``generated_utc``, ``domain_id``, ``years``, and ``units``;
- a summary of unit, year, and row counts;
- rows, caveats, and provenance.

Each unit records ``unit_id``, ``area_ha``, ``watershed_id``, and optional
``hru_id``.

Each row records:

- ``year``, ``unit_id``, ``watershed_id``, ``hru_id``, ``unit_area_ha``;
- ``harvest_area_ha``, ``retention_area_ha``, ``effective_harvest_area_ha``;
- ``road_active_length_m``, ``road_connected_length_m``,
  ``road_built_length_m``, ``road_decommissioned_length_m``;
- ``road_crossing_count``;
- ``years_since_harvest`` and ``years_since_road_build``;
- ``source_event_ids``.

Road State Rules
----------------

- A ``build`` event adds active length, connected length when the road is
  connected, and crossings.
- A ``decommission`` event subtracts the same quantities.
- ``use`` and ``maintain`` are lineage-only; they do not change state.
- A road cannot be built while already active.
- Decommissioning cannot exceed active length, connected length, or active
  crossings.
- A road ID cannot span spatial units.

Conservation Rules
------------------

The build rejects:

- duplicate unit, year, harvest-event, or road-event IDs;
- unknown units;
- event years outside the ledger;
- non-positive harvest area or build/decommission length;
- retention greater than harvest area;
- total harvest greater than unit area;
- invalid road actions and negative crossings;
- road decommissioning beyond active state.

The validation rejects missing or duplicate unit/year rows, inconsistent
effective area, negative areas or lengths, connected length above active
length, and negative ages.

CSV Handoff
-----------

- Units: ``unit_id, area_ha, watershed_id, hru_id``.
- Harvest: ``event_id, unit_id, year, area_ha, retention_area_ha, treatment, source``.
- Roads: ``event_id, road_id, unit_id, year, action, length_m, connected_to_stream, crossing_count, source``.

The CSV loaders are the supported first handoff from WS4/FHOPS. Unknown or
extra columns are ignored by the loader but should be reconciled in the source
schedule.

Recovery Semantics
------------------

``years_since_harvest`` and ``years_since_road_build`` are time counters. They
do not encode hydrologic recovery, species regeneration, canopy closure, or a
response curve. Those belong to P114.5/P114.7.

Cross-References
----------------

- :doc:`../../guides/hydrology-disturbance-ledger`
- :doc:`hydrology-domain`
- :doc:`hydrology-data-bundle`
- :doc:`../api/femic-hydrology-disturbance`
