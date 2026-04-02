``femic.pipeline.manifest`` Module
==================================

The :mod:`femic.pipeline.manifest` module owns FEMIC's run-manifest payload
surface for legacy pipeline execution. It writes pretty-printed JSON manifests,
captures runtime/package versions for reproducibility, and builds the canonical
manifest structure that downstream audit, troubleshooting, and rebuild-evidence
flows rely on.

If you are debugging why a run manifest is missing expected provenance, where
runtime versions are captured, or how FEMIC decides which log/checkpoint paths
should appear in a run-scoped manifest, this is the first module to read. In
practice it owns:

- JSON manifest persistence
- runtime/package version capture
- canonical manifest payload assembly from a resolved execution plan

Start Here If...
----------------

Use this page first if you are trying to:

- inspect what should appear in ``vdyp_io/logs/run_manifest-<run_id>.json``
- debug manifest provenance for a completed or failed run
- understand how execution-plan fields become stored audit metadata
- decide whether a manifest bug belongs here or in the code that built the
  execution plan itself

Typical maintenance path:

1. Start with :func:`build_run_manifest_payload` for manifest content questions.
2. Read :func:`collect_runtime_versions` when the issue is about reproducibility
   metadata rather than run-specific payload fields.
3. Finish with :func:`write_manifest` if the problem is in persistence,
   directory creation, or JSON formatting.

Typical Usage
-------------

The common pattern is to build the payload from a resolved execution plan and
then write it at run start or finish:

.. code-block:: python

   from datetime import datetime
   from femic.pipeline.manifest import build_run_manifest_payload, write_manifest

   payload = build_run_manifest_payload(
       execution_plan=execution_plan,
       status="started",
       started_at=datetime.now(),
       finished_at=None,
       duration_sec=None,
       exit_code=None,
   )
   write_manifest(execution_plan.manifest_path, payload)

How This Fits Into The Pipeline
-------------------------------

This module sits alongside workflow orchestration rather than the scientific
pipeline itself:

1. upstream code builds a resolved :class:`femic.pipeline.io.LegacyExecutionPlan`
2. this module turns that plan into a canonical JSON payload
3. orchestration layers write the manifest at run start and update it again
   after completion or failure

That makes this module the source-of-truth for *manifest structure*, even
though it does not decide the underlying runtime behavior.

Key Entry Surfaces
------------------

The highest-value entrypoints in this module are:

- :func:`build_run_manifest_payload`
  Assemble the canonical JSON payload for one pipeline run.
- :func:`collect_runtime_versions`
  Capture Python/platform/package version metadata relevant to reproducibility.
- :func:`write_manifest`
  Persist the JSON payload to disk in a stable pretty-printed form.

Core Contracts
--------------

The most important runtime contracts in this module are:

- manifests are written as UTF-8 pretty-printed JSON with sorted keys
- payloads include run IDs, command/cwd, log dir, selected FMU/code targets
  (via the legacy ``tsa`` selection seam), config provenance, runtime flags,
  output paths, runtime versions, log-path references, and checkpoint presence
- runtime version capture is best-effort and tolerates packages that are not
  installed as distributions
- manifest path creation must succeed even when the parent directories do not
  already exist

Failure Seams To Watch
----------------------

The common failure boundaries in this module are:

- execution-plan drift
  if upstream code changes the meaning of execution-plan fields without
  adjusting manifest payload assembly, audit metadata becomes misleading
- missing distribution metadata
  package version lookup can legitimately return ``None`` for some deps, so
  callers should not assume every version is present
- log/checkpoint reference confusion
  manifest payloads reflect resolved plan state; if the wrong paths appear, the
  root cause may be in plan construction rather than JSON writing itself

Cross-References
----------------

Guides and references that pair especially closely with this module:

- :doc:`../../guides/troubleshooting`
- :doc:`../../guides/rebuild-repro-contract`
- :doc:`../../guides/cross-platform-runtime-smoke`
- :doc:`../run-config`

Related API pages:

- :doc:`femic-pipeline-io`
- :doc:`femic-workflows-legacy`

.. toctree::
   :hidden:

   generated/femic.pipeline.manifest

.. automodule:: femic.pipeline.manifest
   :members:
   :undoc-members:
   :show-inheritance:
   :noindex:
