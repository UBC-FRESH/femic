``femic.contracts.climate`` Module
==================================

The :mod:`femic.contracts.climate` module owns the ``femic.climate.v1`` record
contract. It validates climate tables and reports their provenance without
importing FEMIC's modelling or runtime stack.

Use this page when you are producing, reading, or validating a climate table
for a FEMIC instance, a ws4 scenario, or a Nemora workflow.

Start Here If...
----------------

Use this page first if you are trying to:

- define a canonical climate table for a new AOI;
- check a ClimateNA/SilvR21 adapter's output before a model consumes it;
- debug a unit, scenario, year, or timestamp failure; or
- report which source and downscaling method produced a climate value.

Typical Usage
-------------

.. code-block:: python

   from pathlib import Path
   from femic.contracts.climate import (
       read_climate_table,
       summarize_climate_table,
       validate_climate_record,
       write_climate_table,
   )

   table = read_climate_table(Path("data/climate/north-island.csv"))
   summary = summarize_climate_table(table)
   write_climate_table(Path("data/climate/north-island.json"), table)

Key Entry Surfaces
------------------

- :func:`validate_climate_record`
  Validate one record against the schema and the variable/unit rules.
- :class:`ClimateRecord`
  Typed record with canonical ``to_dict`` and ``from_dict``.
- :func:`read_climate_table`
  Read and validate a CSV or JSON table in file order.
- :func:`write_climate_table`
  Write a validated table to CSV or JSON.
- :func:`summarize_climate_table`
  Return the provenance-bearing summary a consumer can report.
- :func:`climate_schema`
  Return a defensive copy of the JSON Schema document.

Cross-References
----------------

- :doc:`../contracts/climate-contract`
- :doc:`../contracts/index`

.. automodule:: femic.contracts.climate
   :members:
   :show-inheritance:
