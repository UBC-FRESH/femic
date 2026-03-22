``femic.pipeline.legacy_runtime`` Module
========================================

The :mod:`femic.pipeline.legacy_runtime` module defines the typed runtime
payloads passed from modern FEMIC orchestration into the still-active legacy
``00_data-prep.py`` / ``01a_run-tsa.py`` / ``01b_run-tsa.py`` surfaces. It is
small, but it captures the boundary contract that keeps newer code from passing
anonymous path bags and option blobs into legacy execution.

If you are debugging which arguments the legacy 01a or 01b code actually
receives, why a cached artifact path was or was not present in the payload, or
how parallel worker and sampling settings move across the Stage 00/01a/01b
boundary, this is the first module to read. In practice it owns:

- typed dataclasses for legacy 01a and 01b runtime payloads
- deterministic cache-path bundling for 01a TSA runs
- the explicit contract between modern orchestration code and legacy stage
  entrypoints

Start Here If...
----------------

Use this page first if you are trying to:

- inspect what a single 01a TSA run receives from the Stage 00 orchestrator
- understand the small runtime contract passed into legacy 01b post-TIPSY work
- debug why a legacy call saw the wrong cache paths, worker count, or TIPSY
  output root

Typical maintenance path:

1. Start with :func:`build_legacy_01a_runtime_config` for Stage 00 -> 01a
   wiring questions.
2. Read :func:`build_legacy_01b_runtime_config` for post-TIPSY 01b contract
   questions.
3. Inspect the dataclasses directly when the issue is about field semantics or
   test fixtures rather than builder behavior.

Typical Usage
-------------

The normal pattern is for orchestration code to build one typed payload per
stage boundary instead of passing anonymous dictionaries into legacy code:

.. code-block:: python

   from femic.pipeline.legacy_runtime import build_legacy_01b_runtime_config

   runtime_config = build_legacy_01b_runtime_config(
       tipsy_params_path_prefix="data/tipsy_params_tsa",
       tipsy_output_root="data",
       tipsy_output_filename_template="04_output-tsa{tsa}.out",
   )

How This Fits Into The Pipeline
-------------------------------

This module sits between orchestration code and legacy stage functions:

1. modern FEMIC orchestration resolves paths, options, and cache locations
2. this module packages those resolved values into typed 01a or 01b runtime
   payloads
3. legacy stage code consumes those payloads instead of reconstructing the
   runtime context itself

That means this module owns the *typed handoff contract* for legacy stage
execution, not the higher-level path resolution or the lower-level stage logic.

Key Entry Surfaces
------------------

The highest-value entrypoints in this module are:

- :func:`build_legacy_01a_runtime_config`
  Build the typed runtime payload for one 01a TSA run, including VDYP cache
  path resolution.
- :func:`build_legacy_01b_runtime_config`
  Build the typed runtime payload for one 01b post-TIPSY TSA run.
- :class:`Legacy01ARuntimeConfig`
- :class:`Legacy01BRuntimeConfig`

Core Contracts
--------------

The most important runtime contracts in this module are:

- 01a payloads carry resolved checkpoint paths, TIPSY export prefixes, cache
  paths, sampling settings, and worker-count settings
- 01b payloads intentionally stay smaller and focus on TIPSY params and output
  location semantics
- 01a cache paths are derived through :func:`femic.pipeline.vdyp.build_vdyp_cache_paths`
  so the naming contract stays aligned with the VDYP stage

Failure Seams To Watch
----------------------

The common failure boundaries in this module are:

- stale anonymous-parameter assumptions
  if callers bypass these typed builders and pass ad hoc dictionaries, runtime
  drift becomes much harder to debug
- cache-path mismatch
  01a behavior depends on builder-aligned cache paths matching the VDYP stage's
  expectations
- field drift across stage boundaries
  because the legacy stage functions are still active, mismatched field meaning
  here can look like a failure in lower-level notebook-era code

Cross-References
----------------

Guides and references that pair especially closely with this module:

- :doc:`../../guides/stage-01a-vdyp-tipsy-input`
- :doc:`../../guides/stage-01b-post-tipsy`
- :doc:`../../guides/pipeline-overview`

Related API pages:

- :doc:`femic-workflows-legacy`
- :doc:`femic-pipeline-vdyp-stage`
- :doc:`femic-pipeline-tipsy`

.. toctree::
   :hidden:

   generated/femic.pipeline.legacy_runtime

.. automodule:: femic.pipeline.legacy_runtime
   :members:
   :undoc-members:
   :show-inheritance:
   :noindex:
