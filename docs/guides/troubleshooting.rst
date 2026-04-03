Troubleshooting and Recovery Cookbook
=====================================

Common Issues
-------------

BatchTIPSY input parsing errors
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Likely causes:

- Fixed-width DAT misalignment
- Column-wizard mismatch versus previously validated settings
- Unsupported species/FIZ pairings

Recovery:

1. Keep wizard column mapping constant across runs.
2. Regenerate DAT from FEMIC with unchanged schema.
3. Apply species-code overrides in case/FMU TIPSY YAML config where needed.

Sparse/unstable VDYP fits
^^^^^^^^^^^^^^^^^^^^^^^^^

Likely causes:

- Over-fragmented strata/SI bins
- Too-few stands in fit bins
- Outlier points driving NLLS behavior
- Sampled VDYP polygon/layer temp files drifting out of feature alignment

Recovery:

1. Reduce stratification complexity for small areas.
2. Increase SI-bin collapse aggressiveness or merge bins.
3. Inspect the sampled VDYP temp CSVs and confirm polygon rows and layer rows
   still share the same ``FEATURE_ID`` set before VDYP launch.
4. Apply targeted fit overrides and compare diagnostics only after the batch
   handoff itself looks sane.

VDYP fit-policy config surface
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- FEMIC-level default per-case/per-FMU smoothing exceptions live in
  ``config/vdyp_fit_policy.yaml``.
- Case-specific overrides can live beside the instance in
  ``<instance_root>/config/vdyp_fit_policy.yaml``.
- Normal precedence is:
  explicit runtime override map -> instance-local YAML -> FEMIC default YAML ->
  code fallback for missing/malformed shared defaults.
- Use the instance-local overlay only for bounded, reviewable exceptions such
  as accepted K3Z curve-specific tail handling. Do not treat it as a shortcut
  for broad global smoothing-policy experiments.

Unexpected cache/resume behavior
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Likely causes:

- Resume with stale checkpoints under changed run profile
- Debug-row mode interacting with cached artifacts

Recovery:

1. Use explicit run IDs per experiment.
2. Disable/clear relevant caches when run semantics changed.
3. Confirm manifest provenance and runtime parameters.

Docs/Pages visibility confusion
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Likely causes:

- GitHub Pages source set to branch/Jekyll instead of Actions artifact
- Deploy job skipped by workflow ``if`` guard

Recovery:

1. Set Pages source to **GitHub Actions**.
2. Ensure deploy guard matches intended trigger (push/manual).
3. Re-run workflow and validate guide URLs directly.

Total Managed OK, Species-wise Managed Empty
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Failure signature:

- ``product.Yield.managed.Total`` reports nonzero behavior in Patchworks.
- Species-wise managed accounts are empty/near-zero unexpectedly.

Deterministic troubleshooting flow:

1. Run account-surface diagnostics and capture JSON evidence:

   .. code-block:: bash

      python -m femic instance account-surface \
        --config config/patchworks.runtime.windows.yaml \
        --output runtime/logs/account_surface-<run_id>.json \
        --instance-root <instance-root>

2. If diagnostics prints ``total OK, species-wise empty``:

   - Inspect ``tracks/products.csv`` and ``tracks/curves.csv`` for missing or
     zero-signal species labels.
   - Inspect matrix manifest ``accounts_sync.excluded_patterns`` for
     over-broad regex exclusions.
3. Re-run deterministic rebuild with Patchworks:

   .. code-block:: bash

      python -m femic instance rebuild \
        --spec config/rebuild.spec.yaml \
        --with-patchworks \
        --instance-root <instance-root>

4. Confirm fatal species policy invariants pass:
   ``required_present``, ``expected_absent``, ``required_nonzero``,
   ``expected_zero``.
5. If still failing, compare against baseline/allowlist diff output in
   ``instance_rebuild_report-<run_id>.json`` and only allowlist intentional
   deltas.
