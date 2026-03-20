Stage 01a: Strata, VDYP Curves, and TIPSY Input Generation
==========================================================

Scope
-----

Stage 01a is the per-management-unit compile phase. It builds top strata,
creates SI-level AU splits, runs VDYP sampling/fits, and emits BatchTIPSY input
parameter files.

Key Workflow Steps
------------------

1. Select top strata by cumulative area coverage / target-N strategy.
2. Alias sparse strata to dominant strata where configured.
3. Define SI bins (L/M/H) and collapse sparse bins when thresholds demand it.
4. Run VDYP (sampling mode: ``auto``/``all``/fixed-N).
5. Smooth fitted curves and publish fit diagnostics.
6. Generate ``02_input-*.dat`` + spreadsheet handoff for BatchTIPSY.

VDYP Fitting and SI Splits
--------------------------

- SI split definitions are policy-driven and can vary by case.
- For small management units, bin-collapse thresholds are required to avoid
  unstable regressions.
- Tail handling and outlier controls are needed when right-tail flattening or
  early-age anomalies appear in binned medians.

TIPSY Input Boundary
--------------------

- FEMIC writes fixed-schema DAT/XLSX handoff files.
- ``02_input-*.dat`` is the canonical BatchTIPSY input artifact used by the
  GUI run; ``tipsy_params_tsa*.xlsx`` is a human-readable mirror generated from
  the same table payload.
- BatchTIPSY field maps are GUI-configured and brittle; avoid changing column
  wizard mappings run-to-run.
- Species code mapping and SI fallback behavior should be explicit in
  ``config/tipsy/tsa*.yaml``.

Operator QA Checklist
---------------------

- Confirm non-empty top strata with expected abundance coverage.
- Confirm SI distribution plots are plausible before VDYP fitting.
- Confirm AU count and labels are stable and interpretable.
- Confirm ``02_input-*.dat`` aligns with known-good fixed-width schema before
  exporting across systems.

Known Failure Signatures
------------------------

- Empty SI bins despite adequate stand counts: inspect quantile logic and
  collapse thresholds.
- Flat/degenerate or wildly oscillating VDYP curves: inspect bin medians,
  sample size, and fit overrides.
- BatchTIPSY parse failures: usually fixed-width misalignment or unsupported
  species/FIZ combinations.

Primary Legacy Notebook Coverage
--------------------------------

See traceability mapping for markdown cells in ``01a_run-tsa.ipynb`` and
cross-referenced driver cells in ``00_data-prep.ipynb``.
