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
     - top strata, SI splits, VDYP fitting, BatchTIPSY handoff generation
     - ``02_input-<unit>.dat`` and the related Stage 01a outputs
     - Stops intentionally at the manual BatchTIPSY boundary.
   * - BatchTIPSY
     - external manual GUI/runtime step
     - returned ``04_output-<unit>.out``
     - FEMIC does not run BatchTIPSY; it defines the handoff contract and
       validates freshness/coherence on resume.
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

- ``02_input-*.dat`` is the canonical BatchTIPSY input artifact.
- ``tipsy_params_tsa*.xlsx`` is a human-readable mirror only, not the
  authoritative freshness artifact.
- ``04_output-*.out`` is the required returned BatchTIPSY output for Stage 01b.
- Canonical SiteProd mode prefers a paired ``siteprod.tif`` +
  ``siteprod.bandmap.json``.
- Export-time Patchworks artifacts prove package synthesis, not runtime
  readiness.

Freshness and Resume Rules
--------------------------

- Stage 01b treats DAT content as authoritative when deciding whether returned
  BatchTIPSY output is stale.
- If DAT content has not changed and the output remains coherent, FEMIC can
  resume without regenerating Stage 01a inputs.
- If DAT content has changed, refresh the BatchTIPSY output before rerunning
  post-TIPSY stages.
- Use ``FEMIC_STRICT_TIPSY_TIMESTAMP_MISMATCH=1`` only when you want coherent
  timestamp mismatch to fail hard.
- Use ``FEMIC_ALLOW_STALE_TIPSY_OUTPUT=1`` only for explicit debugging.

Quick Decision Table
--------------------

.. list-table::
   :header-rows: 1
   :widths: 42 58

   * - Question
     - Answer
   * - Which file is authoritative for the BatchTIPSY input boundary?
     - ``02_input-*.dat``
   * - Does changing the XLSX mirror alone require a rerun?
     - No. The XLSX is not the authoritative freshness contract.
   * - Can FEMIC continue into Stage 01b without ``04_output-*.out``?
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
