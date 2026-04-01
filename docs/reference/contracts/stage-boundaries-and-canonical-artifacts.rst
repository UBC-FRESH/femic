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
- :doc:`../api/femic-pipeline-vdyp-stage`
- :doc:`../api/femic-pipeline-tipsy`
- :doc:`../api/femic-fmg-patchworks`
- :doc:`../api/femic-patchworks-runtime`
