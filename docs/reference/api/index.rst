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

Much of the API reference is still autosummary-driven and too terse for heavy
maintenance work. Phase 24 is rebuilding the highest-value pages first by
adding hand-authored module introductions, contracts, examples, and cross-links
to the relevant Guides.

.. toctree::
   :maxdepth: 2

   modules
