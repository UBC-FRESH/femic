``femic.hydrology.screening`` Module
=====================================

The :mod:`femic.hydrology.screening` module computes Tier 0 watershed/year
screening metrics from a disturbance ledger and hydrology domain. It reports
harvest, ECA, road density, crossing density, and context-weighted riparian,
snow-transient, and high-elevation exposure.

It is a screening diagnostic, not a hydrologic response model or flood-risk
product.

Start Here If...
----------------

Use this page first if you are trying to:

- summarize harvest and road exposure by watershed/year;
- inspect an ECA diagnostic with or without a recovery period;
- compare active, connected, and crossing road density;
- attach reviewed riparian/snow/elevation context fractions; or
- produce a reviewable Tier 0 report before P114.5.

Typical Usage
-------------

.. code-block:: python

   from pathlib import Path
   from femic.hydrology.screening import (
       UnitExposureContext,
       WatershedRegime,
       compute_tier0_screening,
       write_tier0_screening_report,
   )

   report = compute_tier0_screening(
       ledger,
       domain,
       regimes=(WatershedRegime("w1", "snow_transient"),),
       unit_contexts=(
           UnitExposureContext("u1", 0.25, 0.5, 0.1),
       ),
       recovery_years=60,
   )
   write_tier0_screening_report(
       report,
       Path("metadata/hydrology/tier0_screening.json"),
   )

Key Entry Surfaces
------------------

- :func:`compute_tier0_screening`
  Compute watershed/year Tier 0 screening rows.
- :func:`write_tier0_screening_report`
  Persist the report as JSON.
- :class:`WatershedRegime`
  Regime metadata for one watershed.
- :class:`UnitExposureContext`
  Reviewed per-unit riparian, snow-transient, and high-elevation fractions.
- :class:`Tier0ScreeningReport`
  Versioned report with rows, caveats, warnings, and deterministic identity.

Cross-References
----------------

- :doc:`../../guides/hydrology-tier0-screening`
- :doc:`../contracts/hydrology-tier0-screening`
- :doc:`femic-hydrology-disturbance`
- :doc:`femic-hydrology-domain`

.. toctree::
   :hidden:

   generated/femic.hydrology.screening

.. automodule:: femic.hydrology.screening
   :members:
   :undoc-members:
   :show-inheritance:
