``femic.workflows.legacy`` Module
=================================

The :mod:`femic.workflows.legacy` module is FEMIC's orchestration seam for the
still-active legacy stage scripts. It does not implement the Stage 00, 01a, or
01b scientific logic itself. Instead, it resolves the packaged legacy script
bundle, prepares the env/cwd contract those scripts expect, launches them
safely, and records the manifests/artifacts that let newer FEMIC code audit the
results.

If you are debugging why ``00_data-prep.py`` launched with the wrong run
configuration, why a post-TIPSY bundle rebuild cannot find cached 01a assets,
or why a manifest/log file was not produced around a legacy execution path,
this is the first module to read. In practice it owns:

- Stage 00 subprocess execution through the normalized
  :class:`femic.pipeline.io.PipelineRunConfig` contract
- post-TIPSY orchestration that reuses cached 01a artifacts plus returned
  BTC/TIPSY output to rebuild bundle tables
- packaged legacy-script bundle resolution for repo-root and installed-package
  contexts
- temporary env and working-directory overrides around legacy execution
- manifest writing and summary payloads for both subprocess and post-TIPSY
  assembly flows

Start Here If...
----------------

Use this page first if you are trying to:

- understand which layer actually launches the legacy ``00_data-prep.py``
  script after the CLI resolves run options
- trace how cached ``vdyp_prep-tsa*.pkl`` and
  ``vdyp_curves_smooth-tsa*.feather`` artifacts are reused during a
  post-TIPSY-only rebuild for a selected FMU/code target
- debug why FEMIC cannot find the packaged legacy scripts in a fresh clone or
  installed-package workflow
- inspect where run manifests are written for Stage 00 or post-TIPSY bundle
  assembly
- determine whether a failure belongs here, in :mod:`femic.pipeline.io`, or in
  lower-level pipeline helpers such as :mod:`femic.pipeline.tipsy` or
  :mod:`femic.pipeline.bundle`

Typical maintenance path:

1. Start with :func:`run_data_prep` if the failure begins with CLI-driven Stage
   00 execution or manifest capture around the legacy subprocess.
2. Move to :func:`run_post_tipsy_bundle_with_manifest` if the problem is in the
   Stage 01b-plus-bundle path and you need a manifest-wrapped rerun.
3. Read :func:`run_post_tipsy_bundle` directly if the issue is about cached
   artifact loading, 01b callback behavior, or bundle-table assembly rather
   than manifest bookkeeping.
4. Inspect :func:`_managed_curve_env_overrides` and the temporary env/cwd
   helpers when behavior differs between direct notebook-era expectations and
   the modern packaged runtime.

Typical Usage
-------------

The most common high-level use is to let the CLI drive the subprocess path:

.. code-block:: bash

   femic run --instance-root external/femic-k3z-instance --run-config config/run_profile.k3z.yaml --run-id k3z_docs_example
   femic tsa btc-post-tipsy --instance-root external/femic-k3z-instance --run-config config/run_profile.k3z.yaml --tsa k3z --run-id k3z_docs_example

When calling directly from Python, the manifest-wrapped post-TIPSY path is the
safer maintenance seam:

.. code-block:: python

   from pathlib import Path
   from femic.workflows.legacy import run_post_tipsy_bundle_with_manifest

   result = run_post_tipsy_bundle_with_manifest(
       tsa_list=["08"],
       data_root=Path("data"),
       log_dir=Path("vdyp_io/logs"),
   )

How This Fits Into The Pipeline
-------------------------------

This module sits between FEMIC's newer orchestration surfaces and the remaining
legacy execution assets:

1. :mod:`femic.cli.main` and :mod:`femic.pipeline.io` normalize runtime inputs
   into a :class:`~femic.pipeline.io.PipelineRunConfig` or equivalent path
   payload
2. :func:`run_data_prep` launches the packaged legacy Stage 00 workflow with
   that normalized execution plan and writes its manifest
3. Stage 01a outputs and returned BTC/TIPSY output accumulate under the active
   data root
4. :func:`run_post_tipsy_bundle` or
   :func:`run_post_tipsy_bundle_with_manifest` reload those cached artifacts,
   call the legacy 01b ``run_tsa`` surface, and rebuild the canonical
   ``model_input_bundle`` tables

That makes this module an orchestration boundary, not the owner of the lower
level data transforms. If path resolution, env wiring, or manifest behavior is
wrong, the bug is often here. If the scientific content of Stage 01a/01b
artifacts is wrong, the root cause usually belongs in a lower-level pipeline
module or in the legacy scripts themselves.

Key Entry Surfaces
------------------

The highest-value entrypoints in this module are:

- :func:`run_data_prep`
  Launch the legacy ``00_data-prep.py`` script using the normalized execution
  plan from :mod:`femic.pipeline.io`.
- :func:`run_post_tipsy_bundle`
  Reload cached Stage 01a artifacts, invoke the legacy 01b ``run_tsa`` path,
  and rebuild the bundle tables without rerunning the full front half of the
  pipeline.
- :func:`run_post_tipsy_bundle_with_manifest`
  Wrap the post-TIPSY rebuild path with explicit manifest lifecycle tracking.

The small result dataclasses are also important because they define the main
post-TIPSY output contract explicitly:

- :class:`PostTipsyBundleResult`
- :class:`PostTipsyBundleRunResult`

Main Runtime Contracts
----------------------

The most important contracts in this module are:

- ``run_data_prep`` expects a fully resolved
  :class:`~femic.pipeline.io.PipelineRunConfig`, not raw CLI fragments
- packaged legacy script resolution must succeed either from the active
  instance root or from package-owned resources exposed through
  :func:`femic.workflows.legacy_resources.resolve_legacy_script_bundle`
- post-TIPSY rebuilds require cached ``vdyp_prep-tsa*.pkl`` and
  ``vdyp_curves_smooth-tsa*.feather`` inputs for every selected FMU/code
  target through the legacy ``tsa`` cache naming seam
- the post-TIPSY path expects returned BTC/TIPSY outputs under the active data
  root through :mod:`femic.pipeline.legacy_runtime` configuration
- bundle rebuild outputs are written into the resolved ``model_input_bundle``
  directory through :mod:`femic.pipeline.bundle`
- both major execution paths are expected to write machine-readable manifest
  files even when the underlying run fails

Those rules are why this module is the right debugging stop when a modern FEMIC
run "looks" like a legacy-script problem. It is the layer that translates from
explicit FEMIC runtime contracts back into the older script expectations.

Cached Post-TIPSY Rebuild Flow
------------------------------

The post-TIPSY path is the main behavior in this module that is easy to miss.
It is designed for the workflow where Stage 01a has already completed,
unattended BTC or legacy manual BatchTIPSY has returned output, and FEMIC
needs to rebuild the
downstream bundle tables without rerunning the whole pipeline.

That flow:

- loads per-FMU/code 01a checkpoints and smoothed curves from the active data
  root
- reconstructs AU/stratum/SI lookup maps needed by the legacy 01b code
- calls the legacy 01b ``run_tsa`` function inside a temporary working
  directory rooted at the selected repo/package script location
- applies optional managed-curve env overrides before invoking 01b
- collects ``tipsy_curves`` and ``tipsy_sppcomp`` outputs when they exist
- derives species-universe support and writes the canonical bundle tables

This is the bridge between the Stage 01b guide and the exported model-input
bundle tables described in the bundle/export guide.

Failure Seams To Watch
----------------------

The common failure boundaries in this module are:

- mis-resolved legacy script roots
  repo-root versus packaged-resource execution can diverge if FEMIC cannot find
  the expected ``00_data-prep.py`` / ``01b_run-tsa.py`` bundle
- missing cached 01a artifacts
  post-TIPSY reruns fail fast when ``vdyp_prep-tsa*.pkl`` or
  ``vdyp_curves_smooth-tsa*.feather`` are absent for a selected FMU/code
  target
- manifest/log expectation drift
  callers rely on this module to emit manifest files even for failed runs, so
  any early exception before manifest update is important
- managed-curve override confusion
  ``FEMIC_MANAGED_CURVE_*`` env overrides are applied here before the legacy
  01b call, so mismatched settings can look like a lower-level TIPSY or curve
  bug
- subprocess exit-code wrapping
  ``run_data_prep`` converts non-zero legacy subprocess exits into
  ``RuntimeError`` after manifest capture, which can hide the real failure if
  the stage logs are ignored

Cross-References
----------------

Guides and references that pair especially closely with this module:

- :doc:`../../guides/stage-00-data-prep`
- :doc:`../../guides/stage-01a-vdyp-tipsy-input`
- :doc:`../../guides/stage-01b-post-tipsy`
- :doc:`../../guides/model-input-bundle-and-export`
- :doc:`../../guides/pipeline-overview`
- :doc:`../run-config`

Related API pages:

- :doc:`femic-cli-main`
- :doc:`femic-pipeline-io`
- :doc:`femic-pipeline-tipsy`
- :doc:`generated/femic.pipeline.bundle`
- :doc:`generated/femic.pipeline.legacy_runtime`

.. toctree::
   :hidden:

   generated/femic.workflows.legacy

.. automodule:: femic.workflows.legacy
   :members:
   :undoc-members:
   :show-inheritance:
   :noindex:
