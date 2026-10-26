Climate Consumer
================

Purpose
-------

This page defines the first consumer of the ``femic.climate.v1`` contract. It
resolves a climate context for an AOI, scenario, year, and variable set, then
attaches the values and their provenance to attribute rows.

The consumer does not implement a climate-growth response. It gives a curve or
attribute stage a documented, provenance-bearing interface.

Context Selection
-----------------

``select_climate_context`` filters a validated table by:

- ``aoi_id``,
- ``scenario``,
- ``year``,
- ``variables``,
- ``gcm`` when supplied.

A selection is an error when:

- no record matches;
- a requested variable is missing;
- more than one GCM matches and no ``gcm`` is supplied;
- a requested variable has more than one record; or
- the selected variables mix sources.

The context carries values, canonical units, source id, source version,
downscaling method, GCM, scenario, year, and the latest retrieval timestamp.

Attached Fields
---------------

With the default ``prefix="climate_"``, each row receives:

- ``climate_<variable>`` — value;
- ``climate_<variable>_unit`` — canonical unit;
- ``climate_aoi_id``;
- ``climate_scenario``;
- ``climate_year``;
- ``climate_gcm``;
- ``climate_source_id``;
- ``climate_source_version``;
- ``climate_downscaling_method``;
- ``climate_retrieved_utc``.

Rows are copied, not mutated. A custom prefix is allowed.

Per-Row AOI
-----------

``attach_climate_to_rows`` resolves the AOI from each row's ``aoi_id`` field by
default, or from ``default_aoi_id`` when the field is absent. This lets one
fragment or attribute table carry rows from more than one AOI.

Example
-------

.. code-block:: python

   from pathlib import Path
   from femic.climate.consumer import attach_climate_to_rows
   from femic.contracts.climate import read_climate_table

   table = read_climate_table(Path("data/climate/north-island.csv"))
   rows = [
       {"fragment_id": 1, "aoi_id": "north-island"},
       {"fragment_id": 2, "aoi_id": "south-island"},
   ]
   attached = attach_climate_to_rows(
       rows,
       table,
       scenario="ssp245",
       year=2050,
       variables=["tavg", "ppt"],
   )

Out of Scope
------------

- A climate-growth response, yield modifier, or species suitability model.
- A climate scenario or GCM selector UI.
- Fetching or downloading ClimateNA data.
- A database or a data portal.

Cross-References
----------------

- :doc:`climate-contract`
- :doc:`../api/femic-climate-consumer`
- :doc:`index`
