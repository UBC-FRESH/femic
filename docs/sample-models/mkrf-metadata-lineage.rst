MKRF PoC Metadata and Lineage
=============================

Scope
-----

This page documents the current metadata inventory and benchmark/runtime
lineage for the tracked MKRF PoC package at
``external/femic-mkrf-instance/models/mkrf_patchworks_model_poc``.

The current MKRF package is a PoC benchmark/intermediate surface. It is not a
source-faithful rebuild and it is not the final canonical instance layout for
the later from-scratch MKRF rebuild.

Machine-readable companion registries:

- ``external/femic-mkrf-instance/metadata/lineage_registry.yaml``
- ``external/femic-mkrf-instance/metadata/legacy_runtime_xml_emission.yaml``
- ``external/femic-mkrf-instance/metadata/legacy_runtime_track_reconciliation.yaml``
- ``external/femic-mkrf-instance/metadata/legacy_source_reproducibility_boundary.yaml``

Current PoC Artifact Families
-----------------------------

The key tracked artifact families in the current MKRF PoC package are:

.. list-table::
   :header-rows: 1

   * - Artifact family
     - Current in-repo path
     - Current status
   * - Runtime model package
     - ``external/femic-mkrf-instance/models/mkrf_patchworks_model_poc``
     - Accepted MKRF PoC intermediate runtime surface
   * - ForestModel XML
     - ``external/femic-mkrf-instance/models/mkrf_patchworks_model_poc/XML/baseMKRF.xml``
     - FEMIC-emitted PoC XML from translated legacy contracts
   * - Generated tracks
     - ``external/femic-mkrf-instance/models/mkrf_patchworks_model_poc/Tracks/*.csv``
     - Matrix-built PoC runtime tables
   * - Accepted spatial runtime lane
     - ``external/femic-mkrf-instance/models/mkrf_patchworks_model_poc/Spatial/*``
     - Accepted compiled runtime inputs, not raw-source reconstruction
   * - Legacy compiled evidence
     - ``external/femic-mkrf-instance/data/legacy_mkrf/*``
     - Archival/reference evidence only
   * - Recovery metadata and runbooks
     - ``external/femic-mkrf-instance/metadata/*`` and
       ``external/femic-mkrf-instance/runbooks/*``
     - Phase 55-58 reverse-engineering and boundary records

Build-Lineage Chain
-------------------

Current accepted lineage for the MKRF PoC package:

1. Legacy recovery lane:
   workbook review extracts, generated XML reconciliation, compiled track
   evidence review, and runtime boundary metadata.
2. Runtime package materialization:
   accepted compiled spatial runtime inputs plus sanitized runtime/control
   scaffold under ``models/mkrf_patchworks_model_poc``.
3. ForestModel XML emission:
   FEMIC-generated ``XML/baseMKRF.xml`` from translated legacy contracts.
4. Matrix stage:
   Patchworks Matrix Builder regenerates ``Tracks/*.csv`` from the emitted XML
   and accepted spatial runtime inputs.
5. Launch / benchmark stage:
   the current PoC lane is accepted after Patchworks launch proof plus one
   representative legacy-vs-PoC benchmark scenario comparison.

Accepted PoC Benchmark Result
-----------------------------

The accepted benchmark comparison for the PoC lane uses one representative
legacy scenario output bundle and one representative PoC headless-run stage.

Compared report pairs:

- ``Forest_Attributes/yield.csv``
- ``Harvest_Attributes/harvestVolumeControls.csv``
- ``Harvest_Attributes/yield_treat.csv``

Accepted interpretation:

- total growing stock is effectively identical at initialization and stays
  within a few percent of legacy in the early periods;
- harvested volume remains somewhat lower than legacy in the same early
  periods, but still tracks the same overall behavior family; and
- longer-horizon divergence is accepted for the PoC lane and deferred to the
  later from-scratch rebuild rather than treated as a PoC blocker.

Current Boundary
----------------

Use the current MKRF PoC package as evidence for:

- reverse-engineering and benchmark comparison,
- accepted runtime XML/track generation,
- accepted compiled spatial runtime usage, and
- operator-facing PoC documentation.

Do not use it as evidence for:

- source-faithful reconstruction from ``03_MappingAnalysisData/*``,
- final canonical MKRF model layout,
- complete recovery of legacy helper/control seams, or
- exact legacy-equivalence across all long-horizon outputs.

Deferred to the Later Rebuild
-----------------------------

The later from-scratch MKRF rebuild phase remains responsible for:

- the canonical FEMIC-native instance layout,
- raw-source geometry-to-runtime reconstruction,
- source-faithful target/control reconstruction,
- any decision about unresolved legacy helper seams such as
  ``THLB4070(...)`` and ``UWR(...)``, and
- final rebuild acceptance gates beyond the current PoC benchmark.
