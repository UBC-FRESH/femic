``femic.climate.consumer`` Module
=================================

The :mod:`femic.climate.consumer` module resolves a validated climate table into
an AOI/scenario/year context and attaches the values and provenance to
attribute rows.

Use this page when you are wiring climate values into a curve or attribute stage
for the first time.

Start Here If...
----------------

Use this page first if you are trying to:

- select one climate context for an AOI, scenario, and year;
- detect an ambiguous GCM or mixed-source selection;
- attach climate values to fragment or attribute rows; or
- carry climate provenance into a downstream report.

Typical Usage
-------------

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

Key Entry Surfaces
------------------

- :func:`select_climate_context`
  Resolve values, units, and provenance for one AOI/scenario/year.
- :class:`ClimateContext`
  Typed context with a JSON-serializable ``to_dict``.
- :func:`attach_climate_context`
  Attach one context to copies of rows.
- :func:`attach_climate_to_rows`
  Resolve a context per row and attach it, with a default-AOI fallback.

Cross-References
----------------

- :doc:`../contracts/climate-consumer`
- :doc:`../contracts/climate-contract`
- :doc:`../contracts/index`

.. automodule:: femic.climate.consumer
   :members:
   :show-inheritance:
