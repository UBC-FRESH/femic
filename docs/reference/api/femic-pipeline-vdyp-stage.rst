``femic.pipeline.vdyp_stage`` Module
====================================

The :mod:`femic.pipeline.vdyp_stage` module owns the heaviest part of FEMIC's
Stage 01a compile path. It is the seam that turns prepared strata/sample-table
inputs into external VDYP batch runs, per-stratum bootstrap results, smoothed
yield curves, and the diagnostic artifacts operators inspect before handing the
workflow off to BatchTIPSY.

If you are tracing why Stage 01a produced the wrong VDYP curves, why a host
cannot launch the legacy VDYP runtime, or why curve-smoothing diagnostics look
wrong, this is the first module to read. In practice it owns:

- loading or caching the VDYP polygon/layer tables used as runtime input
- launching the external VDYP console binary with local temp files
- handling per-stratum sampling, cache reuse, and bootstrap orchestration
- translating raw VDYP tables into smoothed L/M/H curve results
- emitting the JSONL/text log artifacts that make Stage 01a debuggable

Start Here If...
----------------

Use this page first if you are trying to:

- debug a Stage 01a failure before the BTC/BatchTIPSY boundary
- understand why a host cannot find ``VDYP7Console.exe``, ``vdyp_params-landp``,
  ``wine``, or the local ``vdyp_io/VDYP_CFG`` runtime assets
- trace how FEMIC maps sample-table feature IDs to VDYP polygon output tables
- investigate suspicious ``vdyp_fitdiag_*.png`` or ``tipsy_vdyp_*.png`` plots
- work out whether a bug belongs in this module versus
  :mod:`femic.pipeline.vdyp_io`, :mod:`femic.pipeline.vdyp_logging`, or
  :mod:`femic.pipeline.vdyp_sampling`

Typical maintenance path:

1. Start with :func:`run_vdyp_for_stratum` to see the single-stratum execution
   contract.
2. Drop into :func:`execute_vdyp_batch` if the issue looks like external
   process launch, temp-file handling, or output import.
3. Jump to :func:`execute_bootstrap_vdyp_runs` and
   :func:`load_or_build_vdyp_results_tsa` if the issue is about multi-stratum
   orchestration or cache reuse.
4. Finish with :func:`execute_curve_smoothing_runs` and
   :func:`fit_stratum_curves` if the failure is visible in smoothed curves or
   downstream TIPSY overlays.

Typical Usage
-------------

The common call pattern is to let higher-level orchestration prepare the inputs
and then pass one FMU/code runtime payload into the Stage 01a seam through the
legacy ``tsa`` contract:

.. code-block:: python

   from femic.pipeline.legacy_runtime import build_legacy_01a_runtime_config
   from femic.pipeline.vdyp_stage import load_or_build_vdyp_results_tsa

   runtime_config = build_legacy_01a_runtime_config(
       tsa_code="08",
       resume_effective=True,
       force_run_vdyp=False,
       kwarg_overrides_for_tsa=None,
       vdyp_results_pickle_path="data/vdyp_results.pkl",
       vdyp_input_pandl_path="data/vdyp_input_pandl.feather",
       vdyp_ply_feather_path="data/vdyp_ply.feather",
       vdyp_lyr_feather_path="data/vdyp_lyr.feather",
       tipsy_params_columns=[],
       tipsy_params_path_prefix="data/tipsy_params_tsa",
       vdyp_results_tsa_pickle_path_prefix="data/vdyp_prep-tsa",
       vdyp_curves_smooth_tsa_feather_path_prefix="data/vdyp_curves_smooth-tsa",
   )

   # Higher-level callers then dispatch the selected FMU/code run through the
   # Stage 01a seam. The payload still uses legacy ``tsa`` field names.

How This Fits Into The Pipeline
-------------------------------

This module sits inside the Stage 01a compile flow described in
:doc:`../../guides/stage-01a-vdyp-tipsy-input`.

At a high level, the owning sequence is:

1. load prepared VDYP polygon/layer inputs and optional feather caches
2. run external VDYP batches for one stratum or a sampled subset
3. persist run logs and optional cached results for later reuse
4. smooth and quality-gate the resulting curves into the surfaces consumed by
   downstream managed-curve/TIPSY steps

That means this module is a boundary layer, not just a math helper. It owns the
handoff between FEMIC's Python orchestration and the external proprietary VDYP
runtime, then bridges the raw outputs back into FEMIC's internal curve-fitting
and diagnostics flow.

Main Sub-Flows
--------------

The most important sub-flows in this module are:

- **Input loading and cache hydration**
  :func:`load_vdyp_input_tables` reads the PandL source plus feather caches and
  normalizes the polygon/layer tables used for later batch runs.
- **Single-batch execution**
  :func:`execute_vdyp_batch` writes temp ``ply``/``lyr`` CSVs plus raw
  ``.out``/``.err`` spill under ``vdyp_io/scratch/``, builds the external
  command line, captures stdout/stderr, and imports the resulting VDYP tables.
- **Per-stratum orchestration**
  :func:`run_vdyp_for_stratum` resolves runtime assets, log paths, sampling
  behavior, and feature-ID mapping before dispatching one or more batches.
- **Bootstrap execution and cache reuse**
  :func:`execute_bootstrap_vdyp_runs`,
  :func:`build_bootstrap_vdyp_results_runner`, and
  :func:`load_or_build_vdyp_results_tsa` control the per-stratum/per-SI
  execution loop and pickle-backed reuse of previously computed results.
- **Curve fitting and smoothing**
  :func:`fit_stratum_curves`, :func:`execute_curve_smoothing_runs`, and
  :func:`build_smoothed_curve_table` turn raw VDYP output tables into the
  smoothed curves and diagnostics the rest of Stage 01a expects.

Key Entry Surfaces
------------------

The highest-value entrypoints in this module are:

- :func:`load_vdyp_input_tables`
  Read or rebuild the polygon/layer tables that seed all later VDYP work.
- :func:`run_vdyp_for_stratum`
  The best single entrypoint for understanding one stratum's runtime contract.
- :func:`execute_vdyp_batch`
  The external process seam where temp files, subprocess launch, and parse
  failures become visible.
- :func:`execute_bootstrap_vdyp_runs`
  Multi-stratum orchestration across L/M/H site-index buckets.
- :func:`load_or_build_vdyp_results_tsa`
  Reuse or rebuild pickled per-FMU/code VDYP results through the legacy
  ``tsa`` cache naming seam.
- :func:`execute_curve_smoothing_runs`
  Convert raw batch outputs into smoothed curve products and fit diagnostics.

The small dataclasses near the top of the module are also worth reading because
they make the main payload contracts explicit:

- :class:`VdypBatchExecutionDependencies`
- :class:`VdypBatchTempArtifacts`
- :class:`VdypRunEventCounts`
- :class:`StratumFitRunConfig`
- :class:`CurveSmoothingPlotConfig`
- :class:`SmoothedCurveResult`

Runtime Contracts And Artifacts
-------------------------------

The most important runtime assumptions in this module are:

- the external VDYP executable must be available, usually at
  ``VDYP7/VDYP7/VDYP7Console.exe`` relative to ``FEMIC_SOURCE_ROOT`` unless the
  caller passes an explicit path
- the VDYP params file must exist, usually ``vdyp_params-landp``
- non-Windows hosts need ``wine`` available in ``PATH`` before VDYP execution
- local runtime assets under ``vdyp_io/VDYP_CFG`` and ``vdyp_io/VDYP.INI`` must
  exist or be copyable from ``FEMIC_SOURCE_ROOT``
- optional environment overrides include ``FEMIC_SOURCE_ROOT``,
  ``FEMIC_VDYP_CFG_DIR``, and ``FEMIC_SAMPLING_SEED``

The main artifacts this module writes or updates are:

- temp batch inputs/outputs under ``vdyp_io/scratch/`` for each subprocess run
- per-run JSONL/text logs via :mod:`femic.pipeline.vdyp_logging`
- stdout/stderr capture files for the external VDYP runtime
- pickle caches for combined or per-FMU/code VDYP results
- smoothed-curve tables and the diagnostic plots reviewed during Stage 01a

Failure Seams To Watch
----------------------

The common failure boundaries in this module are:

- missing host prerequisites
  ``wine`` absent on Linux/macOS, missing VDYP executable, or missing params
  file will fail before any batch run starts.
- runtime asset drift
  If ``vdyp_io/VDYP_CFG`` or ``VDYP.INI`` is absent and ``FEMIC_SOURCE_ROOT``
  does not point to a valid source tree, the external run will be misconfigured.
- output parse failures
  :func:`execute_vdyp_batch` records parse-error events when the subprocess runs
  but the imported tables are missing, malformed, or empty.
- feature-ID reconciliation issues
  :func:`run_vdyp_for_stratum` contains non-trivial mapping logic from source
  feature IDs to VDYP output tables using ``MAP_ID`` and polygon identifiers;
  this is a common place for edge-case mismatches.
- sampling and fit-quality surprises
  ``auto`` sampling, cache reuse, or later fit-quality gates can produce
  unexpected partial results even when the external batch run itself succeeds.

Cross-References
----------------

Guides and references that pair especially closely with this module:

- :doc:`../../guides/pipeline-overview`
- :doc:`../../guides/stage-01a-vdyp-tipsy-input`
- :doc:`../../guides/diagnostics-playbook`
- :doc:`../../guides/geospatial-runtime-bootstrap`
- :doc:`../../guides/cross-platform-runtime-smoke`
- :doc:`../run-config`

Related API pages:

- :doc:`generated/femic.pipeline.vdyp_io`
- :doc:`generated/femic.pipeline.vdyp_logging`
- :doc:`generated/femic.pipeline.vdyp_sampling`
- :doc:`generated/femic.pipeline.vdyp_curves`
- :doc:`generated/femic.pipeline.tipsy`

.. toctree::
   :hidden:

   generated/femic.pipeline.vdyp_stage

.. automodule:: femic.pipeline.vdyp_stage
   :members:
   :undoc-members:
   :show-inheritance:
   :noindex:
