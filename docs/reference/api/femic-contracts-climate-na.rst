``femic.contracts.climate_na`` Module
=====================================

The :mod:`femic.contracts.climate_na` module adapts an annual ClimateNA-style
CSV to the ``femic.climate.v1`` contract. It maps source columns to canonical
variables, converts nothing silently, and preserves the source column in the
record notes.

Use this page when you have a ClimateNA or SilvR21 annual export and need a
validated climate table for FEMIC, ws4, or Nemora.

Start Here If...
----------------

Use this page first if you are trying to:

- load an annual ClimateNA CSV without hand-building a table;
- map a release with non-standard column names;
- preserve scenario, GCM, source version, and retrieval provenance; or
- debug a non-numeric value or a missing mapped column.

Typical Usage
-------------

.. code-block:: python

   from pathlib import Path
   from femic.contracts.climate_na import read_climate_na_csv

   records = read_climate_na_csv(
       Path("data/climate/climate-na-2050.csv"),
       aoi_id="north-island",
       year=2050,
       scenario="ssp245",
       gcm="ensemble",
       source_version="ClimateNA v7.40",
       retrieved_utc="2026-10-25T00:00:00+00:00",
   )

Key Entry Surfaces
------------------

- :func:`read_climate_na_csv`
  Read an annual ClimateNA-style CSV and emit validated records.
- :func:`climate_na_columns`
  Return a defensive copy of the default annual column map.
- :data:`DEFAULT_CLIMATE_NA_COLUMNS`
  The default source column to ``(variable, unit)`` map.

Cross-References
----------------

- :doc:`../contracts/climate-contract`
- :doc:`femic-contracts-climate`
- :doc:`../contracts/index`

.. automodule:: femic.contracts.climate_na
   :members:
   :show-inheritance:
