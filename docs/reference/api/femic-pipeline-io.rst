``femic.pipeline.io`` Module
============================

The :mod:`femic.pipeline.io` module is FEMIC's main path-resolution and
run-configuration seam. It turns CLI/profile inputs into normalized run
options, resolves which instance-root and external-data artifacts should be
used, and assembles the environment payload that the legacy subprocess wrapper
needs to execute Stage 00/01a/01b work consistently.

If you are debugging why FEMIC picked the wrong instance root, log directory,
run profile, SiteProd artifact, THLB raster, or external data root, this is
the first module to read. In practice it owns:

- loading and validating YAML/JSON run profiles
- normalizing TSA lists and other CLI/profile option surfaces
- building the dataclass payloads that carry resolved path contracts
- resolving canonical external-data, SiteProd, and THLB artifact locations
- constructing the environment and command payload for legacy-script execution

Start Here If...
----------------

Use this page first if you are trying to:

- understand how ``--instance-root`` and ``FEMIC_INSTANCE_ROOT`` affect runtime
  path resolution
- trace how ``config/run_profile.*.yaml`` becomes effective FEMIC run options
- debug whether FEMIC should use instance-local artifacts or published
  canonical assets from ``FEMIC_EXTERNAL_DATA_ROOT``
- inspect which environment variables the CLI passes into the legacy stage
  scripts
- decide whether a path/bootstrap bug belongs here or in a lower-level stage
  helper such as :mod:`femic.pipeline.siteprod` or
  :mod:`femic.workflows.legacy`

Typical maintenance path:

1. Start with :func:`load_pipeline_run_profile` and
   :func:`resolve_effective_run_options` if the issue begins with CLI/profile
   behavior.
2. Move to :func:`resolve_run_paths` and :func:`build_pipeline_run_config` if
   the problem is about instance-root/log-dir/output-root resolution.
3. Read :func:`resolve_legacy_external_data_paths`,
   :func:`resolve_legacy_siteprod_artifacts`, and
   :func:`resolve_legacy_thlb_raster_path` when artifact selection or public
   data fallback is the concern.
4. Finish with :func:`build_legacy_execution_plan` if the failure is visible in
   subprocess env vars, working directory, manifest paths, or legacy command
   handoff.

How This Fits Into The Pipeline
-------------------------------

This module sits between the CLI layer and the legacy workflow/runtime layer.
It does not perform the heavy geospatial, VDYP, TIPSY, or Patchworks work
itself. Instead, it defines which files, paths, and environment contracts those
stages will see.

That makes it a high-leverage debugging seam. If FEMIC is using the wrong data
root, missing a required config path, writing logs to the wrong place, or
pointing a stage at the wrong canonical artifact, the problem usually starts
here before the downstream runtime ever begins.

Main Sub-Flows
--------------

The most important sub-flows in this module are:

- **Profile loading and normalization**
  :func:`load_pipeline_run_profile`, :func:`normalize_tsa_list`, and
  :func:`resolve_effective_run_options` turn CLI/profile inputs into normalized
  execution options.
- **Dataclass payload construction**
  :func:`build_pipeline_run_config` and the module-level dataclasses make the
  run/profile/path contracts explicit instead of passing unstructured path bags
  around the pipeline.
- **External-data and artifact resolution**
  :func:`resolve_legacy_external_data_paths`,
  :func:`build_legacy_data_artifact_paths`,
  :func:`resolve_legacy_siteprod_artifacts`, and
  :func:`resolve_legacy_thlb_raster_path` decide which real source artifacts a
  stage should consume.
- **Legacy execution planning**
  :func:`resolve_run_paths` and :func:`build_legacy_execution_plan` assemble the
  working directory, manifest/log locations, env vars, and command payload used
  to launch the legacy stage script.

Key Entry Surfaces
------------------

The highest-value entrypoints in this module are:

- :func:`load_pipeline_run_profile`
  Load and validate YAML/JSON run-profile files.
- :func:`resolve_effective_run_options`
  Merge explicit CLI values with profile defaults.
- :func:`resolve_legacy_external_data_paths`
  Pick the effective external data root and the main VRI/VDYP/TSA/SiteProd
  source paths.
- :func:`resolve_legacy_siteprod_artifacts`
  Prefer instance-local or canonical pre-stacked SiteProd assets when both TIFF
  and band-map sidecar are available.
- :func:`resolve_legacy_thlb_raster_path`
  Fall back from instance-local ``data/misc.thlb.tif`` to the canonical public
  mirror when needed.
- :func:`build_legacy_execution_plan`
  Build the final subprocess-ready payload for legacy stage execution.

The small dataclasses in this module are also important because they define the
main path and config contracts explicitly:

- :class:`PipelineRunConfig`
- :class:`PipelineRunProfile`
- :class:`EffectiveRunOptions`
- :class:`RunPaths`
- :class:`LegacyExecutionPlan`
- :class:`LegacyDataArtifactPaths`
- :class:`LegacyExternalDataPaths`
- :class:`LegacySiteProdArtifacts`

Artifact Resolution Rules
-------------------------

The most important path/artifact resolution behavior in this module is:

- run profiles are loaded from YAML or JSON and must have mapping-shaped root,
  ``selection``, ``modes``, and ``run`` sections when present
- TSA lists are normalized to zero-padded string codes
- instance-root-aware paths are built under the active runtime root instead of
  assuming one hard-coded workspace layout
- external data is resolved from the first viable candidate among:
  caller/env override, repo-local ``data``, sibling ``../data``, and
  ``~/data``
- canonical SiteProd behavior prefers a paired TIFF + band-map sidecar before
  falling back to the old export-and-stack path
- THLB raster behavior prefers instance-local ``data/misc.thlb.tif`` first and
  then falls back to ``FEMIC_EXTERNAL_DATA_ROOT/misc.thlb.tif``

Those rules are why this module matters for fresh clones, tmp-clone reruns, and
the bundled ``external/*`` example instances. It is the place where FEMIC
decides whether a stripped instance copy can still borrow canonical public
artifacts from the mirrored data root.

Environment And Legacy Handoff
------------------------------

When FEMIC launches the legacy stage script, this module is responsible for the
main env contract, including:

- ``FEMIC_TSA_LIST``
- ``FEMIC_RESUME`` and ``FEMIC_NO_CACHE``
- ``FEMIC_RUN_ID`` and ``FEMIC_RUN_UUID``
- ``FEMIC_LOG_DIR`` and ``FEMIC_OUTPUT_ROOT``
- ``FEMIC_INSTANCE_ROOT`` and ``FEMIC_SOURCE_ROOT``
- ``FEMIC_VDYP_CFG_DIR``
- ``FEMIC_RUN_CONFIG_PATH`` / ``FEMIC_RUN_CONFIG_SHA256``
- optional boundary/stratification/managed-curve overrides

If the legacy script sees the wrong config, wrong working directory, or wrong
artifact root, the bug often traces back to how :func:`build_legacy_execution_plan`
assembled this environment.

Failure Seams To Watch
----------------------

The common failure boundaries in this module are:

- invalid run-profile structure
  malformed or incorrectly typed YAML/JSON fields raise early normalization
  errors here rather than later in the pipeline
- wrong instance-root assumptions
  if the caller expects repo-coupled behavior but passes a different
  ``--instance-root``, downstream stages may appear to "lose" files when the
  real problem is path resolution
- incomplete public-data materialization
  canonical fallback paths only help if ``external/femic-public-data`` has been
  materialized with DataLad and ``FEMIC_EXTERNAL_DATA_ROOT`` points at real
  payloads
- SiteProd/THLB mismatch confusion
  a missing paired SiteProd TIFF + bandmap or a missing THLB raster can cause
  FEMIC to switch from canonical-artifact mode back to a legacy fallback path
- env drift into legacy scripts
  if log-dir, config, or VDYP-related env vars look wrong in downstream runs,
  this module is usually where to inspect first

Cross-References
----------------

Guides and references that pair especially closely with this module:

- :doc:`../../guides/developer-environment-bootstrap`
- :doc:`../../guides/deployment-instances`
- :doc:`../../guides/public-data-mirror-runbook`
- :doc:`../../guides/stage-00-data-prep`
- :doc:`../../guides/geospatial-runtime-bootstrap`
- :doc:`../run-config`

Related API pages:

- :doc:`femic-cli-main`
- :doc:`generated/femic.pipeline.siteprod`
- :doc:`generated/femic.pipeline.tipsy`
- :doc:`generated/femic.workflows.legacy`

.. toctree::
   :hidden:

   generated/femic.pipeline.io

.. automodule:: femic.pipeline.io
   :members:
   :undoc-members:
   :show-inheritance:
   :noindex:
