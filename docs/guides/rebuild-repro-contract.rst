Rebuild Repro Contract
======================

Purpose
-------

The FEMIC rebuild reproducibility contract defines the minimum operational
standard for rebuilding a deployment instance in a deterministic way.

It exists to prevent silent regressions and to make every rebuild auditable
through machine-readable evidence.

Contract Sources
----------------

- Human-readable contract:
  ``planning/femic_instance_rebuild_contract.md``
- Machine-readable contract:
  ``planning/femic_instance_rebuild_contract.v1.yaml``
- Rebuild-spec schema:
  ``planning/femic_instance_rebuild_spec_schema.v1.yaml``

Expected Operator Workflow
--------------------------

1. Validate and customize instance config:
   ``config/run_profile.<case>.yaml``,
   ``config/rebuild.spec.yaml``,
   ``config/rebuild.allowlist.yaml``.
2. Run deterministic rebuild orchestration:

   .. code-block:: bash

      python -m femic instance rebuild \
        --instance-root . \
        --spec config/rebuild.spec.yaml \
        --baseline config/rebuild.baseline.json \
        --allowlist config/rebuild.allowlist.yaml \
        --with-patchworks

3. Review rebuild report:
   ``runtime/logs/instance_rebuild_report-<run_id>.json``.
4. If baseline drift is intentional:
   update ``config/rebuild.allowlist.yaml`` (or regenerate baseline with
   ``--write-baseline`` when appropriate).
5. If regression gate fails:
   follow remediation hints emitted by CLI and recorded in the report.

Required Evidence Artifacts
---------------------------

Every rebuild run should produce:

- Step outcomes and timings in
  ``instance_rebuild_report-<run_id>.json``.
- Referenced manifests/logs under ``artifact_references``.
- Invariant measurements under ``metrics`` and ``invariant_results``.
- Baseline/allowlist structural diff results under ``baseline``.
- Gate summary under ``regression_gate``.

Failure Classes
---------------

- ``fatal``: hard stop (missing prerequisites, step failure, fatal invariant
  regression, or unexpected baseline drift above threshold).
- ``warn``: non-fatal issue requiring follow-up (for example, non-fatal
  invariant drift or optional artifact warning).

Contributor Policy (Mandatory for New Instance Repos)
-----------------------------------------------------

For every new FEMIC deployment-instance repository, the following are required:

- Track ``config/rebuild.spec.yaml`` in git.
- Track ``config/rebuild.allowlist.yaml`` in git.
- Run ``femic instance validate-spec`` as part of contributor QA.
- Run ``femic instance rebuild`` (at least dry-run; full run when dependencies
  are available) before milestone closure.
- Preserve rebuild evidence artifacts (report + manifests/log references) for
  review and audit trails.

No new instance phase should be considered complete without reproducible
rebuild evidence and a passing regression gate.

Next Guides
-----------

- ``How to author a new instance rebuild spec``:
  ``docs/guides/author-instance-rebuild-spec.rst`` (P13.5b)
- ``How to interpret rebuild reports and regressions``:
  ``docs/guides/interpret-rebuild-reports.rst`` (P13.5c)
