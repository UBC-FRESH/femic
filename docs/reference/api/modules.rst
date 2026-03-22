FEMIC Modules
=============

The pages below are grouped by the way FEMIC is actually maintained, not just by
package namespace.

High-priority operational modules
---------------------------------

These are the first pages to consult for real runtime/debugging work and the
first targets in the Phase 24 API-docs rebuild.

Current curated pages in this section include ``femic.cli.main``,
``femic.pipeline.vdyp_stage``, ``femic.pipeline.io``, and
``femic.pipeline.tipsy``.

.. toctree::
   :maxdepth: 1

   femic-cli-main
   femic-pipeline-vdyp-stage
   femic-pipeline-io
   femic-pipeline-tipsy

.. autosummary::
   :toctree: generated

   femic.pipeline.siteprod
   femic.fmg.patchworks
   femic.patchworks_runtime
   femic.workflows.legacy

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
   femic.geospatial_preflight
   femic.instance_bootstrap
   femic.instance_context
   femic.pipeline
   femic.pipeline.bundle
   femic.pipeline.diagnostics
   femic.pipeline.legacy_context
   femic.pipeline.legacy_runtime
   femic.pipeline.managed_curves
   femic.pipeline.manifest
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
   femic.rebuild_baseline
   femic.rebuild_invariants
   femic.rebuild_runner
   femic.rebuild_spec
   femic.release_packaging
   femic.vdyp
   femic.vdyp.reporting
   femic.workflows.legacy_resources
   femic.ws3_bridge
   femic.ws3_smoke
