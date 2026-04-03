How to Interpret Rebuild Reports and Regressions
================================================

Report Location
---------------

Each rebuild run writes a machine-readable report:

- ``runtime/logs/instance_rebuild_report-<run_id>.json``

Start with the run summary at top-level keys:

- ``run_id``
- ``failed``
- ``outcomes`` (step execution details)
- ``artifact_references``
- ``metrics``
- ``invariant_results``
- ``baseline``
- ``regression_gate``

Step Outcomes
-------------

Use ``outcomes`` first to confirm command execution order and status.

For each step, review:

- ``step_id``
- ``status`` (``ok`` or ``failed``)
- ``duration_seconds``
- ``error`` (if present)

If any required step failed, treat the run as invalid and resolve that
before interpreting downstream metrics.

Invariant Results
-----------------

``invariant_results`` evaluates spec-defined checks against measured metrics.

Each result includes:

- ``invariant_id``
- ``severity`` (``fatal`` or ``warn``)
- ``metric``
- ``comparator``
- ``target``
- ``measured``
- ``status`` (``pass``, ``warn``, ``fail``)
- ``remediation``

Interpretation rule:

- Any ``fatal`` invariant with ``status=fail`` is a hard regression.
- ``warn`` should be reviewed and either remediated or explicitly accepted.

Baseline and Allowlist Diffs
----------------------------

``baseline`` captures structural drift from snapshot comparisons.

Focus fields:

- ``status``
- ``diff`` (track/XML structural differences)
- ``allowlist``
- ``allowlist_result``

Key metrics:

- ``metrics.baseline_diff_count``
- ``metrics.baseline_unexpected_diff_count``
- ``metrics.baseline_allowlist_match``

If unexpected diffs are intentional, update
``config/rebuild.allowlist.yaml`` and re-run.

Regression Gate
---------------

``regression_gate`` is the final pass/fail policy summary.

Critical fields:

- ``step_failure``
- ``fatal_invariant_failure``
- ``unexpected_diff_regression``
- ``baseline_unexpected_diff_threshold``
- ``baseline_unexpected_diff_count``

The run is blocked when any of these are true:

- ``step_failure``
- ``fatal_invariant_failure``
- ``unexpected_diff_regression``

Evidence Trend Drift Across Releases
------------------------------------

When evidence is promoted with
``femic instance promote-evidence`` (or via
``femic instance refresh-reference-evidence``), the normalized artifact includes
``trend_drift`` for release-over-release interpretation.

Key fields:

- ``trend_drift.previous_summary``
- ``trend_drift.warn_increase``
- ``trend_drift.baseline_diff_increase``
- ``trend_drift.thresholds.max_warn_increase``
- ``trend_drift.thresholds.max_baseline_diff_increase``
- ``trend_drift.warnings``

Interpretation rule:

- Positive ``warn_increase`` means more warning-level invariant results than
  the previously promoted evidence.
- Positive ``baseline_diff_increase`` means additional structural drift versus
  the previously promoted evidence.
- Non-empty ``trend_drift.warnings`` means configured thresholds were exceeded
  and should trigger explicit maintainer review before release.

Recommended release workflow:

1. Refresh evidence with thresholds:
   ``femic instance refresh-reference-evidence --reference-root . --max-warn-increase 0 --max-baseline-diff-increase 0``
2. Inspect ``trend_drift`` deltas and warning messages.
3. If drift is intentional, document rationale in roadmap/changelog and update
   baseline/allowlist artifacts as needed.
4. Re-run rebuild and evidence refresh until drift warnings are either cleared
   or explicitly accepted with documented rationale.

Triage Workflow
---------------

1. Confirm step execution succeeded in ``outcomes``.
2. Resolve any ``fatal`` invariant failures.
3. Review baseline diff scope in ``baseline.diff``.
4. Distinguish intentional vs unintentional drift:
   update allowlist only for intentional changes.
5. Re-run rebuild and confirm ``regression_gate`` is clear.

Common Patterns
---------------

- Block/topology join regressions:
  non-zero ``block_join_mismatch_count`` usually indicates model-side join/key
  inconsistency between ``blocks.shp`` and ``tracks/blocks.csv``.
- Seral-account regressions:
  low/zero ``seral_account_count`` typically indicates XML export or matrix
  build drift.
- Baseline drift regressions:
  ``unexpected_diff_regression=true`` means structural changes exceeded
  accepted allowlist thresholds.
