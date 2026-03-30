FEMIC Modules
=============

The pages below are grouped by the way FEMIC is actually maintained, not just by
package namespace.

High-priority operational modules
---------------------------------

These are the first pages to consult for real runtime/debugging work and the
first targets in the Phase 24 API-docs rebuild.

Current curated pages in this section include ``femic.cli.main``,
``femic.pipeline.vdyp_stage``, ``femic.pipeline.io``,
``femic.pipeline.tipsy``, ``femic.fansier_runtime``,
``femic.fansier_reporting``, ``femic.fansier_workflow``,
``femic.fmg.patchworks``,
``femic.patchworks_runtime``, ``femic.workflows.legacy``, and
``femic.pipeline.siteprod``.

.. toctree::
   :maxdepth: 1

   femic-cli-main
   femic-pipeline-vdyp-stage
   femic-pipeline-io
   femic-pipeline-tipsy
   femic-fansier-runtime
   femic-fansier-reporting
   femic-fansier-workflow
   femic-fmg-patchworks
   femic-patchworks-runtime
   femic-workflows-legacy
   femic-pipeline-siteprod

Curated support-contract modules
--------------------------------

These smaller modules are not the first pages most users need, but they still
own real runtime contracts that are easy to miss when left as generated-only
stubs.

Current curated pages in this section include ``femic.instance_context``,
``femic.instance_bootstrap``, ``femic.geospatial_preflight``,
``femic.pipeline.bundle``, ``femic.pipeline.legacy_runtime``, and
``femic.pipeline.manifest``.

.. toctree::
   :maxdepth: 1

   femic-instance-context
   femic-instance-bootstrap
   femic-geospatial-preflight
   femic-pipeline-bundle
   femic-pipeline-legacy-runtime
   femic-pipeline-manifest

Curated rebuild and release modules
-----------------------------------

These modules support deterministic rebuild evidence, regression gating, and
student-facing release packaging. They are not first-stop runtime pages, but
they do carry enough policy and artifact-contract weight to justify curated
introductions.

Current curated pages in this section include ``femic.rebuild_spec``,
``femic.rebuild_baseline``, ``femic.rebuild_invariants``,
``femic.rebuild_runner``, and ``femic.release_packaging``.

.. toctree::
   :maxdepth: 1

   femic-rebuild-spec
   femic-rebuild-baseline
   femic-rebuild-invariants
   femic-rebuild-runner
   femic-release-packaging

Package and support modules
---------------------------

.. autosummary::
   :toctree: generated

   femic
   femic.account_surface
   femic.cli
   femic.fmg
   femic.fmg.adapters
   femic.fmg.core
   femic.fmg.woodstock
   femic.pipeline
   femic.pipeline.diagnostics
   femic.pipeline.legacy_context
   femic.pipeline.managed_curves
   femic.pipeline.plots
   femic.pipeline.pre_vdyp
   femic.pipeline.species_volume
   femic.pipeline.stages
   femic.pipeline.stands
   femic.pipeline.tipsy_config
   femic.pipeline.tipsy_legacy
   femic.pipeline.tsa
   femic.pipeline.vdyp
   femic.pipeline.vdyp_curves
   femic.pipeline.vdyp_io
   femic.pipeline.vdyp_logging
   femic.pipeline.vdyp_overrides
   femic.pipeline.vdyp_sampling
   femic.pipeline.vri
   femic.vdyp
   femic.vdyp.reporting
   femic.workflows.legacy_resources
   femic.ws3_bridge
   femic.ws3_smoke
