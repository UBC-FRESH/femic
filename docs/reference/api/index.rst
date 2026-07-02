API Reference
=============

Developer-facing API documentation for the public Python module surface.

Use this section when you already know you need to work in FEMIC's Python
modules and you want to understand module responsibilities, callable surfaces,
and package boundaries.

This section is not meant to replace the Guides. The Guides explain workflows
and operator sequences. The API reference should explain what the code owns,
how the main modules fit together, and where to start when you need to extend
or debug a specific runtime seam.

If you need the shortest source-of-truth answers for repo/runtime contracts
rather than module ownership, start with :doc:`../contracts/index`.

API contract
------------

The API reference is generated from ``src/femic`` modules using
``sphinx.ext.autodoc`` and ``sphinx.ext.autosummary`` with Google-style
docstrings.

Default policy:

- Include public FEMIC modules under ``src/femic``.
- Exclude resource-only payload modules under ``femic.resources``.
- Exclude private members by default (names prefixed with ``_``).
- Keep narrative workflow guidance in Guides and Sample Models; keep API pages
  focused on callable/module reference behavior.

How to use this reference
-------------------------

If you are orienting yourself in the codebase, start with the package or module
that matches the job you are trying to do:

- ``femic.cli.main``: CLI entrypoints and command wiring.
- ``femic.pipeline.vdyp_stage``: VDYP orchestration, smoothing, and runtime
  boundary logic.
- ``femic.pipeline.io``: runtime path resolution, external-data discovery, and
  canonical artifact selection.
- ``femic.pipeline.tipsy``: BatchTIPSY handoff generation and related
  fixed-width export logic.
- ``femic.fansier_runtime``: FAN$IER clean-session launch, batch automation,
  and unattended runtime seam helpers.
- ``femic.fansier_reporting``: FAN$IER long-report text parsing and normalized
  table extraction for downstream FEMIC use.
- ``femic.fansier_workflow``: higher-level FAN$IER workflows that chain tracked
  extraction and parsing seams into one FEMIC-owned operation.
- ``femic.patchworks_variants``: registry-backed Patchworks variant resolution
  for installed providers, user overlays, and named launch surfaces.
- ``femic.pipeline.siteprod``: SiteProd artifact resolution, band mapping, and
  raster assignment helpers.
- ``femic.fmg.patchworks``: Patchworks export synthesis, fragments wiring, and
  ForestModel generation.
- ``femic.patchworks_runtime``: Patchworks preflight, launch, and matrix-build
  runtime helpers.
- ``femic.workflows.legacy``: orchestration layer around the still-active
  legacy stage scripts.

Current limitation
------------------

Phase 24 has now curated the highest-value operational, support-contract, and
rebuild/release pages. The remaining generated-only pages are intended to be
leaf helpers, package namespace surfaces, or narrower integration modules
unless the closure-sweep artifact identifies them as still needing promotion.

For the explicit generated-only classification used to close the main rewrite
pass, see ``planning/phase24_api_docs_closure_sweep.md``.

The API reference is therefore mixed by design:

- curated pages for the modules that own major runtime, contract, or
  maintenance seams
- generated pages for narrower helper/package surfaces where autodoc
  completeness is enough

.. toctree::
   :maxdepth: 2

   modules
