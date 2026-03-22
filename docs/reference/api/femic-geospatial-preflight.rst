``femic.geospatial_preflight`` Module
=====================================

The :mod:`femic.geospatial_preflight` module is FEMIC's lightweight readiness
check for Fiona/GDAL-dependent workflows. It normalizes host OS families,
returns platform-specific installation hints, verifies that Fiona can import,
and can run a small shapefile write/read smoke test before longer geospatial
stages begin.

If you are debugging why ``femic prep geospatial-preflight`` fails on a fresh
clone, why a host reports Fiona but still cannot do shapefile I/O, or what
bootstrap ritual FEMIC expects on Windows, Linux, or macOS, this is the first
module to read. In practice it owns:

- host OS normalization for bootstrap guidance
- Fiona import and GDAL-version visibility checks
- optional shapefile read/write smoke validation
- typed preflight results used by CLI messaging

Start Here If...
----------------

Use this page first if you are trying to:

- confirm whether a workstation is ready for FEMIC geospatial stages
- debug a failed ``prep geospatial-preflight`` command
- inspect which install hint FEMIC shows for a given host OS
- decide whether a geospatial bootstrap issue belongs here or in the broader
  platform/runtime guides

Typical maintenance path:

1. Start with :func:`run_geospatial_preflight` for the overall readiness flow.
2. Read :func:`detect_os_family` and :func:`geospatial_install_hint` when the
   issue is about platform-specific guidance rather than importability.
3. Inspect the shapefile smoke helper when Fiona imports but real shapefile I/O
   still fails.

How This Fits Into The Pipeline
-------------------------------

This module sits before the heavier geospatial stages begin:

1. bootstrap or onboarding guidance tells the operator to install Fiona/GDAL
2. ``femic prep geospatial-preflight`` calls this module
3. if the checks pass, FEMIC can continue into Stage 00 and other geospatial
   workflows with higher confidence

That means this module owns the *readiness gate*, not the downstream geospatial
logic itself.

Key Entry Surfaces
------------------

The highest-value entrypoints in this module are:

- :func:`run_geospatial_preflight`
  Run the full Fiona/GDAL import and optional shapefile smoke test.
- :class:`GeospatialPreflightResult`
  Typed result payload recording OS family, install hint, GDAL version,
  warnings, and errors.
- :func:`detect_os_family`
  Normalize host platform names into the small set FEMIC uses for guidance.
- :func:`geospatial_install_hint`
  Return the OS-specific install ritual shown to users.

Core Contracts
--------------

The most important runtime contracts in this module are:

- Fiona must import successfully for FEMIC geospatial stages to proceed
- GDAL version visibility is desirable but not always fatal
- the shapefile smoke test is optional but valuable when validating a fresh
  environment
- preflight success is simply ``not result.errors``, exposed through
  :attr:`GeospatialPreflightResult.ok`

Failure Seams To Watch
----------------------

The common failure boundaries in this module are:

- missing Fiona install
  FEMIC cannot proceed with geospatial stages until Fiona/GDAL is installable
- import-time shared-library failures
  Fiona may be installed but unusable if GDAL libraries are mismatched
- shapefile smoke failures
  read/write smoke can catch deeper I/O issues that a plain import check misses

Cross-References
----------------

Guides and references that pair especially closely with this module:

- :doc:`../../guides/geospatial-runtime-bootstrap`
- :doc:`../../guides/developer-environment-bootstrap`
- :doc:`../../guides/deployment-instances`
- :doc:`../cli`

Related API pages:

- :doc:`femic-pipeline-siteprod`
- :doc:`femic-pipeline-vdyp-stage`

.. toctree::
   :hidden:

   generated/femic.geospatial_preflight

.. automodule:: femic.geospatial_preflight
   :members:
   :undoc-members:
   :show-inheritance:
   :noindex:
