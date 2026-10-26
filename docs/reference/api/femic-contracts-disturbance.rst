``femic.contracts.disturbance`` Module
======================================

The :mod:`femic.contracts.disturbance` module owns the
``femic.disturbance.v1`` event contract. It validates event records, their
spatial references, their severity representation, and their provenance without
importing FEMIC's modelling or runtime stack.

Use this page when you are producing, reading, or validating disturbance events
for a FEMIC instance, a ws4 scenario, or an FHOPS salvage plan.

Start Here If...
----------------

Use this page first if you are trying to:

- define a shared fire, insect, drought, wind, mortality, harvest, or salvage
  event;
- check a detector's output before a model consumes it;
- debug a type, severity, confidence, spatial-reference, or timestamp failure;
- produce a flat row for a ws4 consumer; or
- report which source and attribution method produced an event.

Typical Usage
-------------

.. code-block:: python

   from pathlib import Path
   from femic.contracts.disturbance import (
       consumer_rows,
       events_for_block,
       read_disturbance_table,
       summarize_disturbance_table,
       write_disturbance_table,
   )

   events = read_disturbance_table(Path("data/disturbance/fire_2023.json"))
   summary = summarize_disturbance_table(events)
   block_events = events_for_block(events, 101)
   rows = consumer_rows(events)
   write_disturbance_table(Path("data/disturbance/table.json"), events)

Key Entry Surfaces
------------------

- :func:`validate_disturbance_event`
  Validate one event and its cross-field rules.
- :class:`DisturbanceEvent`
  Typed event with canonical ``to_dict``, ``from_dict``, and
  ``to_consumer_row``.
- :func:`read_disturbance_table`
  Read and validate a JSON table, an ``events`` object, or a single event.
- :func:`write_disturbance_table`
  Write a validated table with unique event ids.
- :func:`summarize_disturbance_table`
  Return counts, types, severity classes, year and area ranges, sources,
  attributions, and spatial-reference counts.
- :func:`consumer_rows`
  Return the flat ws4-facing rows.
- :func:`events_for_block`
  Select events that name a block directly.
- :func:`disturbance_schema`
  Return a defensive copy of the JSON Schema document.

Cross-References
----------------

- :doc:`../contracts/disturbance-contract`
- :doc:`../contracts/index`

.. automodule:: femic.contracts.disturbance
   :members:
   :show-inheritance:
