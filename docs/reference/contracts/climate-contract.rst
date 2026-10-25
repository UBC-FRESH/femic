Climate Contract (``femic.climate.v1``)
========================================

Purpose
-------

This page is the source-of-truth contract for the climate table that FEMIC,
ws3, ws4, and Nemora exchange. It defines one validated record, the canonical
units and scenario labels, the table formats, and the provenance a consumer can
report.

The contract does not download ClimateNA data, choose a GCM ensemble, or model
climate. An adapter is responsible for converting a source to this table.

Quick Contract
--------------

- Record schema: ``femic.climate.v1``.
- Canonical table files: ``.csv`` with one record per row, or ``.json`` with a
  list of records (or an object with a ``records`` list).
- Required timezone: ISO-8601 with an explicit offset.
- Canonical scenarios: ``historical``, ``rcp26``, ``rcp45``, ``rcp60``,
  ``rcp85``, ``ssp126``, ``ssp245``, ``ssp370``, ``ssp585``.
- Canonical units are fixed per variable; adapters convert before writing.
- The validator rejects unknown fields, missing fields, unsupported variables,
  mismatched units, out-of-range years, non-finite values, negative variance,
  and timestamps without a timezone.

Record Fields
-------------

.. list-table::
   :header-rows: 1
   :widths: 22 14 64

   * - Field
     - Type
     - Meaning
   * - ``schema_version``
     - string
     - Must be ``femic.climate.v1``.
   * - ``aoi_id``
     - string
     - Area-of-interest identifier the value applies to.
   * - ``variable``
     - string
     - Canonical variable, one of the table below.
   * - ``unit``
     - string
     - Canonical unit for the variable.
   * - ``year``
     - integer
     - Calendar year, 1900-2300.
   * - ``scenario``
     - string
     - Scenario label from the canonical list.
   * - ``gcm``
     - string
     - GCM, ensemble, or ``observed`` label.
   * - ``value``
     - number
     - Finite climate value in ``unit``.
   * - ``variance``
     - number or null
     - Optional variance. Must be finite and non-negative.
   * - ``source_id``
     - string
     - Upstream source identifier.
   * - ``source_version``
     - string
     - Source release or version.
   * - ``downscaling_method``
     - string
     - Downscaling or processing method, or ``none``.
   * - ``retrieved_utc``
     - string
     - ISO-8601 retrieval timestamp with a timezone.
   * - ``notes``
     - string or null
     - Optional free-text note.

Variables and Units
-------------------

.. list-table::
   :header-rows: 1
   :widths: 25 25 50

   * - Variable
     - Unit
     - Meaning
   * - ``tavg``
     - ``degC``
     - Mean temperature.
   * - ``tmax``
     - ``degC``
     - Maximum temperature.
   * - ``tmin``
     - ``degC``
     - Minimum temperature.
   * - ``mat``
     - ``degC``
     - Mean annual temperature.
   * - ``ppt``
     - ``mm``
     - Total precipitation.
   * - ``prcp``
     - ``mm``
     - Precipitation (source-compatible alias).
   * - ``map``
     - ``mm``
     - Mean annual precipitation.
   * - ``snow``
     - ``mm``
     - Snowfall or snow water equivalent.
   * - ``cwd``
     - ``mm``
     - Climatic water deficit.
   * - ``pet``
     - ``mm``
     - Potential evapotranspiration.
   * - ``rh``
     - ``percent``
     - Relative humidity.
   * - ``vpd``
     - ``kPa``
     - Vapour pressure deficit.
   * - ``gdd``
     - ``degree_days``
     - Growing degree days.

Scenarios
---------

``historical`` is the observed or baseline lane. ``rcp*`` labels are retained
for ClimateNA v6/v7 outputs; ``ssp*`` labels are the CMIP6 generation. A single
GCM is not a scenario: record the ensemble or model label in ``gcm`` and the
selection rule in the adapter documentation.

Table Formats
-------------

CSV files carry one record per row with the header fields in this order::

   schema_version,aoi_id,variable,unit,year,scenario,gcm,value,variance,
   source_id,source_version,downscaling_method,retrieved_utc,notes

JSON files carry a list of record objects, or an object with a ``records``
list. Empty tables are rejected: a consumer should fail on an empty table
rather than silently report zero records.

Validation Rules
----------------

- Unknown fields and missing required fields are errors.
- ``schema_version`` is exact; a new shape needs a new version.
- ``variable`` must be in the canonical set, and ``unit`` must match it.
- ``year`` must be an integer in 1900-2300; booleans are not integers here.
- ``value`` and ``variance`` must be finite; ``variance`` is non-negative.
- ``retrieved_utc`` must be ISO-8601 and timezone-aware.
- The table must contain at least one record.

Provenance Summary
------------------

:func:`femic.contracts.climate.summarize_climate_table` returns counts, AOIs,
variables, units, scenarios, the year range, deduplicated source tuples, and
the retrieval-time range. A consumer should report this summary with any
derived product so a reader can see which source and downscaling method were
used.

Example
-------

.. code-block:: python

   from pathlib import Path
   from femic.contracts.climate import (
       read_climate_table,
       summarize_climate_table,
       write_climate_table,
   )

   table = read_climate_table(Path("data/climate/north-island.csv"))
   summary = summarize_climate_table(table)
   write_climate_table(Path("data/climate/north-island.json"), table)

Out of Scope
------------

- A ClimateNA/SilvR21 adapter or a GCM ensemble selector.
- A climate model, downscaling algorithm, or gap-filling method.
- A climate-growth response function or yield modifier.
- A database or data portal.

Cross-References
----------------

- :doc:`../api/femic-contracts-climate`
- :doc:`index`

.. toctree::
   :hidden:

   ../api/femic-contracts-climate
