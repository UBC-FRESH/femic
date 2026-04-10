Stage Boundaries and Canonical Artifacts
========================================

Purpose
-------

This page is the source of truth for the main pipeline boundaries and which
artifacts are authoritative at each step.

Pipeline Boundary Map
---------------------

.. list-table::
   :header-rows: 1
   :widths: 14 28 28 30

   * - Stage
     - FEMIC owns
     - Canonical artifacts
     - Boundary notes
   * - Stage 00
     - inventory prep, stratification inputs, geospatial support artifacts
     - instance ``data/`` inputs, checkpoints, and generated prep outputs
     - Can depend on canonical public-data fallback when instance-local copies
       are absent.
   * - Stage 01a
     - top strata, SI splits, VDYP fitting, BTC/BatchTIPSY handoff generation
     - ``03_input-<unit>.csv`` and the related Stage 01a outputs
     - Stops intentionally at the BTC runtime boundary.
   * - BTC / BatchTIPSY
     - external Windows runtime step launched unattended by FEMIC
     - returned ``04_output-<unit>.csv`` and ``04_error-<unit>.csv``
     - FEMIC owns the handoff/output contract and validates
       freshness/coherence on resume.
   * - Stage 01b
     - post-TIPSY parsing, managed-vs-untreated comparison, bundle tables
     - bundle tables, QA plots, refreshed downstream tables
     - Resumes only after canonical BatchTIPSY output is available.
   * - Export
     - Patchworks/Woodstock package synthesis
     - ``forestmodel.xml``, fragments shapefile/DBF, Woodstock outputs
     - Export correctness is separate from runtime launch success.
   * - Runtime
     - preflight, build-blocks, Matrix Builder / Beanshell launch
     - runtime logs, manifests, tracks, blocks/topology outputs
     - Depends on proprietary Patchworks tooling and host-specific runtime
       assumptions.

Canonical Artifact Rules
------------------------

- ``03_input-*.csv`` is the canonical BTC/BatchTIPSY input artifact.
- ``tipsy_params_tsa*.xlsx`` is a human-readable mirror only, not the
  authoritative freshness artifact.
- ``04_output-*.csv`` is the required returned BTC output for Stage 01b, paired
  with ``04_error-*.csv``.
- Legacy ``02_input-*.dat`` / ``04_output-*.out`` files remain compatibility
  artifacts only and are no longer the default supported seam.
- Canonical SiteProd mode prefers a paired ``siteprod.tif`` +
  ``siteprod.bandmap.json``.
- Export-time Patchworks artifacts prove package synthesis, not runtime
  readiness.
- ``tracks/*/groups.csv`` should be treated as a post-matrix-builder
  user-overlay surface unless a specific instance explicitly documents
  otherwise. Editing group assignments in that file does not, by itself,
  imply that ``forestmodel.xml`` or the other compiled track tables need to be
  regenerated.
- AOI-scoped TSR GIS acquisitions are only canonical for the extent they were
  fetched for. A clipped smoke/test overlay is not automatically a valid
  production/full-TSA source layer just because it lives under the instance
  ``data/`` tree.

TSR AOI Acquisition Contract
----------------------------

For TSR source-layer workflows that acquire public GIS data by bbox/order:

- record the requested AOI with the acquired artifact;
- distinguish reviewed production/full-TSA acquisitions from smoke-scale or
  otherwise AOI-scoped exploratory downloads;
- keep smoke-scale downloads segregated under a smoke-specific subtree such as
  ``data/downloads/bcdc/smoke/`` instead of mixing them into the production GIS
  library; and
- treat obvious bbox-coverage mismatches against the active checkpoint extent
  as blockers for full-TSA netdown execution rather than as silent no-op or
  generic missing-source conditions.

Operational rule:

- do not promote a smoke-clipped overlay into later full-TSA THLB validation
  without reacquiring or otherwise reviewing a production-valid extent.

Minimal Functional Patchworks Instance
--------------------------------------

When FEMIC or an instance doc says "functional Patchworks instance", be
explicit about *which* readiness tier you mean.

Matrix-Builder-ready minimum:

- Patchworks runtime config for the target instance (for example
  ``config/patchworks.runtime.windows.yaml``)
- compiled ``forestmodel.xml``
- full fragments shapefile sidecar set:
  ``fragments.shp``, ``fragments.dbf``, ``fragments.shx``,
  ``fragments.prj``, and ``fragments.cpg``
- host/runtime prerequisites that let ``femic patchworks preflight`` pass

Post-matrix-build compiled minimum:

- everything in the Matrix-Builder-ready tier
- compiled track tables under ``tracks/`` including at least:
  ``curves.csv``, ``features.csv``, ``products.csv``, ``treatments.csv``,
  ``protoaccounts.csv``, and ``accounts.csv``

Standalone launch-ready published minimum:

- everything in the post-matrix-build compiled tier
- ``blocks/blocks.shp`` plus the full shapefile sidecar set used by the
  shipped runtime surface
- the topology CSV used by the shipped analysis surface
- the analysis/PIN launch surfaces required to open the compiled model

Editable anti-lock-in publication tier:

- the standalone launch-ready published minimum
- the validated ``forestmodel.xml`` plus validated ``fragments`` sidecar set
  preserved as the user-visible rebuild/overlay starting point even when the
  compiled model could technically launch without revisiting them

If you are rebuilding ``forestmodel.xml`` from FEMIC bundle outputs, the
minimum upstream compile inputs are also:

- ``data/model_input_bundle/au_table.csv``
- ``data/model_input_bundle/curve_table.csv``
- ``data/model_input_bundle/curve_points_table.csv``

Operational rule:

- do not treat a thin instance that only contains ``forestmodel.xml`` plus a
  placeholder ``fragments/README.md`` as Patchworks-functional;
- restore or regenerate the actual fragments sidecar set before preflight or
  Matrix Builder work;
- do not treat a compiled model surface with tracks but no shipped
  ``blocks/blocks.shp`` payload as standalone launch-ready;
- if an instance is published as a runnable standalone Patchworks model, make
  the shipped blocks/topology/analysis surfaces explicit alongside the editable
  XML/fragments escape hatch;
- do not claim a rebuilt Patchworks input layer is sane until you have
  inspected the concrete compiled track outputs directly.

VDYP Runtime Layout Note
------------------------

Treat the local ``vdyp_io/`` tree as three different contracts, not one pile:

- ``vdyp_io/VDYP.INI`` and ``vdyp_io/VDYP_CFG/**`` are durable local runtime
  prerequisites;
- ``vdyp_io/logs/`` is for VDYP-specific event/stdout/stderr evidence;
- ``vdyp_io/scratch/`` is cleanup-safe raw per-batch spill
  (``vdyp_ply_*.csv``, ``vdyp_lyr_*.csv``, ``vdyp_out_*.out``,
  ``vdyp_err_*.err``).

Operational rule:

- do not treat raw per-batch scratch under ``vdyp_io/scratch/`` as canonical
  evidence or durable runtime input;
- do not delete ``VDYP.INI`` or ``VDYP_CFG/**`` when cleaning runtime spill.

Canonical-source note:

- FEMIC-level VDYP runtime assets are the preferred canonical shared source
  during ordinary source-checkout development;
- instance-local copies of ``VDYP.INI`` / ``VDYP_CFG/**`` are mainly justified
  when an instance is being frozen or published as a more standalone runtime
  package that should not depend on the parent FEMIC checkout being present;
- if both surfaces exist, treat unnecessary duplication as a maintenance risk
  and keep the intended source of truth explicit in the instance/operator docs.

Patchworks Track Overlay Note
-----------------------------

Not every file under a compiled ``tracks/`` directory has the same rebuild
contract.

- ``curves.csv``, ``features.csv``, ``products.csv``, ``treatments.csv``,
  ``protoaccounts.csv``, and ``accounts.csv`` are compiled outputs and should
  normally be refreshed through the normal export / matrix-build path.
- ``groups.csv`` may be a deliberate user-edited overlay applied *after*
  Matrix Builder has generated the main track package.

Agent/developer consequence:

- if a request is specifically about swapping or editing ``groups.csv`` in an
  already-built Patchworks surface, do not assume the right next step is a
  rebuild;
- first verify the runtime contract for how that instance consumes the groups
  overlay;
- do not invent BeanShell ``calculateGroups("GROUP")``-style fixes unless the
  instance docs or runtime contract explicitly say that is required.

Freshness and Resume Rules
--------------------------

- Stage 01b treats canonical BTC input CSV content as authoritative when
  deciding whether returned BTC output is stale.
- If CSV content has not changed and the output remains coherent, FEMIC can
  resume without regenerating Stage 01a inputs.
- If CSV content has changed, refresh the BTC output before rerunning
  post-TIPSY stages.
- Use ``FEMIC_STRICT_TIPSY_TIMESTAMP_MISMATCH=1`` only when you want coherent
  timestamp mismatch to fail hard.
- Use ``FEMIC_ALLOW_STALE_TIPSY_OUTPUT=1`` only for explicit debugging on the
  legacy DAT/OUT seam.

Quick Decision Table
--------------------

.. list-table::
   :header-rows: 1
   :widths: 42 58

   * - Question
     - Answer
   * - Which file is authoritative for the BTC/BatchTIPSY input boundary?
     - ``03_input-*.csv``
   * - Does changing the XLSX mirror alone require a rerun?
     - No. The XLSX is not the authoritative freshness contract.
   * - Can FEMIC continue into Stage 01b without ``04_output-*.csv``?
     - No.
   * - Does a successful Patchworks export mean Matrix Builder will run?
     - No. Runtime prerequisites are a separate boundary.

See Also
--------

- :doc:`../../guides/pipeline-overview`
- :doc:`../../guides/stage-01a-vdyp-tipsy-input`
- :doc:`../../guides/stage-01b-post-tipsy`
- :doc:`../../guides/model-input-bundle-and-export`
- :doc:`../../guides/tsr-thlb-reconstruction-ladder`
- :doc:`../api/femic-pipeline-vdyp-stage`
- :doc:`../api/femic-pipeline-tipsy`
- :doc:`../api/femic-fmg-patchworks`
- :doc:`../api/femic-patchworks-runtime`
