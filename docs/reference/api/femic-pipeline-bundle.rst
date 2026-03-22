``femic.pipeline.bundle`` Module
================================

The :mod:`femic.pipeline.bundle` module owns FEMIC's canonical
``data/model_input_bundle`` table surface. It resolves the three bundle table
paths, loads and writes them, constructs AU/curve tables from per-TSA VDYP and
TIPSY outputs, and provides compatibility helpers for downstream consumers that
need stable AU-to-curve mapping behavior.

If you are debugging why bundle tables were written to the wrong place, why a
post-TIPSY rebuild produced missing AU mappings, or how downstream exporters
decide which treated and untreated curve IDs to use, this is the first module
to read. In practice it owns:

- canonical bundle table paths and readiness checks
- assembly of AU, curve, and curve-points tables from per-TSA curve surfaces
- species-proportion curve emission for ordered species universes
- compatibility helpers for AU mapping backfill and curve-id assignment

Start Here If...
----------------

Use this page first if you are trying to:

- understand what lives under ``data/model_input_bundle/``
- inspect how Stage 01b outputs become export-ready bundle tables
- debug missing AU/curve mappings during bundle assembly
- trace how treated versus untreated curve IDs are assigned downstream

Typical maintenance path:

1. Start with :func:`resolve_bundle_paths` and :func:`bundle_tables_ready` for
   basic path-contract questions.
2. Read :func:`build_bundle_tables_from_curves` when the issue is in bundle
   assembly from per-TSA VDYP and TIPSY outputs.
3. Inspect :func:`assign_curve_ids_from_au_table` when downstream consumers are
   attaching curve IDs back onto stand tables.

Typical Usage
-------------

The common maintenance pattern is to resolve canonical bundle paths first and
then load the three-table surface as one unit:

.. code-block:: python

   import pandas as pd
   from femic.pipeline.bundle import load_bundle_tables, resolve_bundle_paths

   paths = resolve_bundle_paths(base_dir="data/model_input_bundle")
   au_table, curve_table, curve_points_table = load_bundle_tables(
       paths=paths,
       pd_module=pd,
   )

How This Fits Into The Pipeline
-------------------------------

This module sits at the seam between post-TIPSY assembly and model export:

1. upstream code produces per-TSA untreated VDYP curves and optional treated
   TIPSY curves
2. this module compiles those surfaces into canonical bundle tables
3. export/runtime layers such as :mod:`femic.fmg.patchworks` and related tools
   consume the bundle tables instead of rebuilding upstream curve logic

That makes this module the source-of-truth for the *bundle table contract*,
even though it does not own the upstream curve generation algorithms.

Key Entry Surfaces
------------------

The highest-value entrypoints in this module are:

- :func:`resolve_bundle_paths`
  Resolve canonical AU/curve/curve-points bundle table locations.
- :func:`load_bundle_tables`
  Load bundle tables from CSV and optionally normalize TSA codes.
- :func:`write_bundle_tables`
  Persist bundle tables to the canonical CSV surface.
- :func:`build_bundle_tables_from_curves`
  Assemble the three canonical bundle tables from per-TSA VDYP and TIPSY
  outputs.
- :func:`assign_curve_ids_from_au_table`
  Attach treated/untreated curve IDs back onto stand-like tables.

The main dataclasses are also important because they make the table/path
contracts explicit:

- :class:`BundlePaths`
- :class:`BundleAssemblyResult`

Core Contracts
--------------

The most important runtime contracts in this module are:

- the canonical bundle directory defaults to ``data/model_input_bundle``
- the required tables are ``au_table.csv``, ``curve_table.csv``, and
  ``curve_points_table.csv``
- AU identifiers are deterministically namespaced by TSA through
  :func:`tsa_curve_id_prefix`
- managed and unmanaged curve IDs are emitted together so downstream export
  layers can choose the right curve family without recomputing upstream logic
- optional ordered-species support emits extra species-proportion curves for
  both untreated and treated surfaces

Failure Seams To Watch
----------------------

The common failure boundaries in this module are:

- missing AU mappings
  per-TSA curve combinations can be skipped if ``scsi_au`` lacks a required
  mapping
- bundle-table naming drift
  downstream tools assume the canonical three-table contract and can break if
  filenames or key columns drift
- treated/unmanaged compatibility confusion
  this module intentionally carries both current and backward-compatible column
  names so older exporters/checkpoints do not break

Cross-References
----------------

Guides and references that pair especially closely with this module:

- :doc:`../../guides/model-input-bundle-and-export`
- :doc:`../../guides/stage-01b-post-tipsy`
- :doc:`../../guides/pipeline-overview`
- :doc:`../patchworks-export`
- :doc:`../woodstock-export`

Related API pages:

- :doc:`femic-workflows-legacy`
- :doc:`femic-fmg-patchworks`

.. toctree::
   :hidden:

   generated/femic.pipeline.bundle

.. automodule:: femic.pipeline.bundle
   :members:
   :undoc-members:
   :show-inheritance:
   :noindex:
