Disturbance Contract (``femic.disturbance.v1``)
================================================

Purpose
-------

This page is the source-of-truth contract for the disturbance event record that
FEMIC, ws4, and FHOPS exchange. It defines what happened, where, when, how
severe it was, how confident the attribution is, and which source produced it.

The contract does not detect or attribute disturbances. It consumes events from
an existing detector, inventory, expert record, or disturbance layer.

Quick Contract
--------------

- Event schema: ``femic.disturbance.v1``.
- Table file: JSON, containing a list of events, an object with an ``events``
  list, or a single event object.
- Spatial reference: a shallow-validated GeoJSON geometry, positive
  ``fragment_ids``, positive ``block_ids``, or a combination.
- Severity: a required categorical ``severity_class`` and an optional
  continuous ``severity_value`` in [0, 1].
- Confidence: a required probability in [0, 1].
- Event ids are unique within a table.

Event Fields
------------

.. list-table::
   :header-rows: 1
   :widths: 24 16 60

   * - Field
     - Type
     - Meaning
   * - ``schema_version``
     - string
     - Must be ``femic.disturbance.v1``.
   * - ``event_id``
     - string
     - Stable identifier, unique within the table.
   * - ``event_type``
     - string
     - One of the canonical types below.
   * - ``year``
     - integer
     - Calendar year the event began, 1900-2300.
   * - ``severity_class``
     - string
     - ``low``, ``moderate``, ``high``, ``very_high``, or ``unknown``.
   * - ``severity_value``
     - number or null
     - Optional continuous severity in [0, 1].
   * - ``severity_basis``
     - string or null
     - Required when ``severity_value`` is present; for example ``dNBR`` or
       ``mortality_fraction``.
   * - ``confidence``
     - number
     - Attribution or detection confidence in [0, 1].
   * - ``attribution``
     - string
     - Cause or attribution label, for example ``wildfire`` or ``drought``.
   * - ``attribution_method``
     - string or null
     - Method or product used for attribution.
   * - ``geometry``
     - object or null
     - Shallow-validated GeoJSON geometry.
   * - ``fragment_ids``
     - array or null
     - Positive, unique FEMIC fragment ids.
   * - ``block_ids``
     - array or null
     - Positive, unique ws4 block ids.
   * - ``area_ha``
     - number or null
     - Event area in hectares.
   * - ``source_id``
     - string
     - Upstream source identifier.
   * - ``source_version``
     - string
     - Upstream source version.
   * - ``retrieved_utc``
     - string
     - Timezone-aware ISO-8601 retrieval timestamp.
   * - ``notes``
     - string or null
     - Optional free-text note.

Event Types
-----------

``fire``, ``insect``, ``disease``, ``drought``, ``wind``, ``flood``,
``partial_mortality``, ``harvest``, ``salvage``, and ``other``.

``partial_mortality`` is the non-stand-replacing lane used by NSR detections.
``harvest`` and ``salvage`` are operational events; they can share an area with
a fire or insect event without being merged.

Severity
--------

The categorical ``severity_class`` is required because it is the common field a
manager can read. The continuous ``severity_value`` is optional because
different detectors produce different scales (dNBR, mortality fraction,
defoliation percent). When a value is present, ``severity_basis`` names the
scale. Do not compare values with different bases without a conversion.

Spatial Reference
-----------------

An event must carry at least one of:

- a GeoJSON ``geometry``;
- ``fragment_ids``;
- ``block_ids``.

The geometry validator checks the GeoJSON type and the presence of coordinates
or geometries; it does not validate topology or CRS. A consumer is responsible
for the CRS and for resolving fragments to blocks. The direct selection helper
:func:`events_for_block` only matches ``block_ids``; fragment-to-block
resolution belongs to the consumer.

Table Format
------------

A table is a JSON list of events::

   [
     {"schema_version": "femic.disturbance.v1", "event_id": "fire-2023-001", ...},
     {"schema_version": "femic.disturbance.v1", "event_id": "nsr-2022-001", ...}
   ]

An object with an ``events`` list is also accepted. A single event object is
accepted as a one-event table, which is useful for examples and tests.

Consumer Rows
-------------

:meth:`femic.contracts.disturbance.DisturbanceEvent.to_consumer_row` returns the
minimal ws4-facing shape:

``event_id``, ``event_type``, ``year``, ``severity_class``, ``severity_value``,
``confidence``, ``fragment_ids``, ``block_ids``, ``area_ha``, ``source_id``.

That row is deliberately smaller than the full record. A consumer can report
the event without importing the contract package; the full record remains the
source of provenance.

Validation Rules
----------------

- Unknown and missing required fields are errors.
- ``schema_version`` is exact.
- ``event_type`` and ``severity_class`` are controlled vocabularies.
- ``year`` is an integer in 1900-2300.
- ``confidence`` and ``severity_value`` are in [0, 1].
- ``severity_value`` requires ``severity_basis``.
- At least one spatial reference is required.
- Ids are positive and unique within their list; event ids are unique within a
  table.
- ``retrieved_utc`` is ISO-8601 and timezone-aware.
- An empty table is an error.

Example
-------

.. code-block:: python

   from pathlib import Path
   from femic.contracts.disturbance import (
       consumer_rows,
       read_disturbance_table,
       summarize_disturbance_table,
   )

   events = read_disturbance_table(Path("data/disturbance/fire_2023.json"))
   summary = summarize_disturbance_table(events)
   rows = consumer_rows(events)

Out of Scope
------------

- A disturbance detection or attribution algorithm.
- A fire-spread or insect-spread simulator.
- A full hazard model or expected-loss calculation.
- A GIS topology or CRS validator.
- A database or data portal.

Cross-References
----------------

- :doc:`../api/femic-contracts-disturbance`
- :doc:`climate-contract`
- :doc:`index`

.. toctree::
   :hidden:

   ../api/femic-contracts-disturbance
