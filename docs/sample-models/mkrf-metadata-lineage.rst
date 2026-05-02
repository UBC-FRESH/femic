MKRF Metadata and Lineage
=========================

Scope
-----

This page documents the current metadata inventory and runtime/benchmark
lineage for the MKRF instance surfaces.

The active canonical rebuild package now lives at:

- ``external/femic-mkrf-instance/models/mkrf_patchworks_model``

The retained benchmark/reference PoC package remains at:

- ``external/femic-mkrf-instance/models/mkrf_patchworks_model_poc``

Machine-readable companion registries:

- ``external/femic-mkrf-instance/metadata/lineage_registry.yaml``
- ``external/femic-mkrf-instance/metadata/legacy_runtime_xml_emission.yaml``
- ``external/femic-mkrf-instance/metadata/legacy_runtime_track_reconciliation.yaml``
- ``external/femic-mkrf-instance/metadata/legacy_source_reproducibility_boundary.yaml``

Current Artifact Families
-------------------------

The key tracked artifact families in the current MKRF instance are:

.. list-table::
   :header-rows: 1

   * - Artifact family
     - Current in-repo path
     - Current status
   * - Runtime model package
     - ``external/femic-mkrf-instance/models/mkrf_patchworks_model``
     - Canonical FEMIC-native rebuild runtime surface
   * - PoC benchmark package
     - ``external/femic-mkrf-instance/models/mkrf_patchworks_model_poc``
     - Accepted MKRF benchmark/intermediate reference surface
   * - Canonical rebuild XML / tracks / spatial
     - ``external/femic-mkrf-instance/models/mkrf_patchworks_model/{xml,tracks,spatial}/*``
     - Source-faithful canonical rebuild runtime artifacts
   * - PoC XML / tracks / spatial
     - ``external/femic-mkrf-instance/models/mkrf_patchworks_model_poc/{XML,Tracks,Spatial}/*``
     - Benchmark/reference runtime artifacts
   * - Legacy compiled evidence
     - ``external/femic-mkrf-instance/data/legacy_mkrf/*``
     - Archival/reference evidence only
   * - Recovery metadata and runbooks
     - ``external/femic-mkrf-instance/metadata/*`` and
       ``external/femic-mkrf-instance/runbooks/*``
     - Phase 55-58 reverse-engineering and boundary records

Canonical Build-Lineage Chain
-----------------------------

Current accepted lineage for the canonical rebuild package:

1. Raw-source geometry lane:
   source-faithful publication from ``03_MappingAnalysisData/*`` into the
   canonical runtime spatial surface.
2. Canonical runtime package materialization:
   FEMIC emits the rebuild-owned XML, analysis, lineage, and control metadata
   under ``models/mkrf_patchworks_model``.
3. Matrix stage:
   Patchworks Matrix Builder regenerates ``tracks/*.csv`` from the emitted XML
   and canonical runtime spatial inputs.
4. Benchmark-validation stage:
   the canonical runtime surface is compared back to the accepted PoC package
   by family presence and accepted-difference classification.
5. Runtime-sanity stage:
   the canonical even-flow saved stage is audited against the published
   species-share surface so emitted ``indsp.*`` signals are explained by source
   inputs rather than hidden runtime heuristics.

Retained PoC / Legacy Reference Chain
-------------------------------------

The retained PoC/legacy evidence chain still matters for benchmark/reference
only:

1. legacy compiled-package evidence under ``data/legacy_mkrf/*``;
2. PoC package materialization under
   ``models/mkrf_patchworks_model_poc``; and
3. accepted benchmark/control surfaces such as the PoC
   ``analysis/base.pin`` / ``ScenarioSet.bsh`` lane.

Accepted Benchmark Result
-------------------------

The accepted benchmark comparison for the rebuild lane uses the retained PoC
runtime package as the comparison target for runtime-surface parity and keeps
the older legacy scenario/control lane only as benchmark/reference evidence.

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

Use the current canonical rebuild package as evidence for:

- source-faithful runtime spatial publication,
- accepted canonical runtime XML/track/product/account generation, and
- accepted PoC-parity runtime-surface comparison; and
- explicit IFM/origin semantics where:
  - ``managed`` / ``unmanaged`` means treatment eligibility; and
  - ``natural`` / ``treated`` means curve provenance.

Use the retained PoC / legacy surfaces as evidence for:

- benchmark/reference comparison,
- legacy control-lane context, and
- accepted legacy-only helper/control seams that remain outside the canonical
  claim boundary.

Do not use the canonical rebuild package as evidence for:

- a rebuilt source-faithful control/entrypoint lane,
- complete recovery of legacy helper/control seams, or
- exact legacy-equivalence across all long-horizon outputs.

Current validation evidence added in the closeout slice:

- ``external/femic-mkrf-instance/models/mkrf_patchworks_model/analysis/runtime_species_share_audit.csv``
- canonical even-flow saved stage under
  ``runtime/logs/headless_stage/mkrf_canonical_evenflow_semantic_smoke_20260502b/``
- saved-stage sanity outputs under that stage's ``sanity/`` directory

Those surfaces are now part of the accepted ``v0`` runtime sanity evidence for
the canonical rebuild lane.

Accepted Legacy-Only Seams
--------------------------

The following control-lane seams remain accepted legacy-only benchmark evidence
unless a later task explicitly reopens source-faithful control-lane rebuild:

- ``THLB4070(...)``
- ``UWR(...)``
- ``InitialTargets/00_Target_Descriptions.bsh``
