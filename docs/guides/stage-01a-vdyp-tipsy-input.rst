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
6. Generate ``03_input-*.csv`` + workbook handoff for unattended BTC/BatchTIPSY.

VDYP Fitting and SI Splits
--------------------------

- SI split definitions are policy-driven and can vary by case.
- For small management units, bin-collapse thresholds are required to avoid
  unstable regressions.
- Tail handling and outlier controls are needed when right-tail flattening or
  early-age anomalies appear in binned medians.
- Before each VDYP batch is launched, FEMIC now drops sampled polygon rows
  that lack matching layer rows so the polygon/layer CSV pair stays strictly
  feature-aligned at the external handoff seam.
- Default per-case/per-FMU smoothing exceptions now live in
  ``config/vdyp_fit_policy.yaml``.
- Instance-specific overlays can add or adjust those rules with
  ``config/vdyp_fit_policy.yaml`` inside the active ``--instance-root``
  checkout.
- Override precedence is:
  ``runtime kwarg_overrides_for_tsa`` -> instance-local YAML overlay ->
  FEMIC-level YAML defaults -> narrow code fallback if the shared default YAML
  is missing or malformed.

TIPSY Input Boundary
--------------------

- FEMIC writes canonical BTC ``MSYT.csv`` handoff files plus workbook mirrors.
- ``03_input-*.csv`` is the canonical BTC/BatchTIPSY input artifact used by
  the unattended ``/TSR`` seam; ``tipsy_params_tsa*.xlsx`` is a human-readable
  mirror generated from the same table payload.
- When FEMIC emits BTC rows with ``planted_percent < 100``, the same canonical
  handoff must also carry explicit ``natural_species*`` and
  ``natural_density*`` payload; mixed-share rows with blank natural-ingress
  fields are now treated as a FEMIC contract error before BTC launch.
- Legacy ``02_input-*.dat`` remains a compatibility artifact only.
- Species code mapping and SI fallback behavior should be explicit in
  ``config/tipsy/tsa*.yaml`` (legacy filename pattern retained for
  compatibility).

Operator QA Checklist
---------------------

- Confirm non-empty top strata with expected abundance coverage.
- Confirm SI distribution plots are plausible before VDYP fitting.
- Confirm AU count and labels are stable and interpretable.
- Confirm ``03_input-*.csv`` aligns with the expected BTC ``MSYT.csv`` schema
  before exporting across systems.

Known Failure Signatures
------------------------

- Empty SI bins despite adequate stand counts: inspect quantile logic and
  collapse thresholds.
- Flat/degenerate or wildly oscillating VDYP curves: inspect bin medians,
  sample size, fit overrides, and whether the sampled polygon/layer batch lost
  feature alignment before VDYP.
- BTC / BatchTIPSY parse failures: usually input-schema mismatch, unsupported
  species/FIZ combinations, or incompatible report-template seams.

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

Linux Source-Checkout Prerequisites
-----------------------------------

Before running Stage 01a from a fresh Linux source checkout, ensure:

.. code-block:: bash

   python -m pip install -r requirements-dev.txt
   git submodule update --init --recursive
   git -C external/femic-public-data annex enableremote arbutus-s3
   datalad get -r external/femic-public-data/data
   export FEMIC_EXTERNAL_DATA_ROOT=$PWD/external/femic-public-data/data

For isolated ``--instance-root`` clones, FEMIC falls back to source-root
runtime assets when local copies are missing (for example
``data/tipsy_params_columns``, ``vdyp_io/VDYP_CFG``, and ``vdyp_io/VDYP.INI``).

Known-Good Windows K3Z Hand-Off
-------------------------------

On the validated Patchworks workstation, the intended K3Z Stage 01a path is:

.. code-block:: powershell

   $env:FEMIC_EXTERNAL_DATA_ROOT="$PWD\external\femic-public-data\data"
   python -m femic prep validate-case --instance-root external/femic-k3z-instance --run-config config/run_profile.k3z.yaml
   python -m femic run --instance-root external/femic-k3z-instance --run-config config/run_profile.k3z.yaml --run-id k3z_windows_cleanstart

Expected outcome:

- native Windows VDYP runs using the bundled ``VDYP7Console.exe``
- SiteProd geoprocessing can fall back through ArcGIS Pro when needed
- FEMIC stops intentionally at the BTC freshness boundary after writing:
  - ``external/femic-k3z-instance/data/03_input-tsak3z.csv``
  - ``external/femic-k3z-instance/data/tipsy_params_tsak3z.xlsx`` or a timestamped fallback workbook
  - optionally ``external/femic-k3z-instance/data/02_input-tsak3z.dat`` as a legacy mirror

At that point, do **not** rerun Stage 01a unless the TIPSY handoff really needs
to be regenerated. Stage 01b freshness is BTC-CSV-content based, so unchanged
``03_input`` content can reuse existing BTC output, but real canonical input
changes require a refreshed ``04_output``.
