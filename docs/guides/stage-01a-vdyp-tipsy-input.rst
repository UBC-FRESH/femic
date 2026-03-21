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

K3Z Teaching Baseline Notes
---------------------------

- K3Z baseline managed curves now come from real BatchTIPSY output driven by
  VDYP-derived SI.
- The low-yield ``CWHvm_CW+YC`` and ``CWHvm_CW+PLC`` strata are intentionally
  excluded from the treated/TIPSY pathway and retained out of THLB via
  ``RETENTION = 1.0``.
- Remaining treated AUs use the simplified teaching planting logic:
  - FD-pair AUs: ``900 FD + 3100 HW``
  - CW-pair AUs: ``900 CW + 3100 HW``
  - all other remaining treated AUs: ``600 CW + 300 FD + 3100 HW``

Known-Good Windows K3Z Hand-Off
-------------------------------

On the validated Patchworks workstation, the intended K3Z Stage 01a path is:

.. code-block:: powershell

   $env:FEMIC_EXTERNAL_DATA_ROOT='C:\Users\gep\projects\femic\external\femic-public-data\data'
   python -m femic prep validate-case --instance-root external/femic-k3z-instance --run-config config/run_profile.k3z.yaml
   python -m femic run --instance-root external/femic-k3z-instance --run-config config/run_profile.k3z.yaml --run-id k3z_windows_cleanstart

Expected outcome:

- native Windows VDYP runs using the bundled ``VDYP7Console.exe``
- SiteProd geoprocessing can fall back through ArcGIS Pro when needed
- FEMIC stops intentionally at the BatchTIPSY freshness boundary after writing:
  - ``external/femic-k3z-instance/data/02_input-tsak3z.dat``
  - ``external/femic-k3z-instance/data/tipsy_params_tsak3z.xlsx`` or a timestamped fallback workbook

At that point, do **not** rerun Stage 01a unless the TIPSY handoff really needs
to be regenerated, because doing so will make the previous ``04_output`` stale.

