Pipeline Walkthrough
====================

Purpose
-------

FEMIC compiles forest-estate model inputs from BC inventory and growth/yield tools.
The working pipeline keeps legacy scientific logic but exposes repeatable runtime
interfaces through ``femic`` CLI commands.

End-to-End Flow
---------------

Run from your active instance root (maintainers can use
``instances/reference/``):

.. code-block:: bash

   cd instances/reference

For deterministic orchestration using the new rebuild runner abstraction, use:

.. code-block:: bash

   femic instance rebuild --run-config config/run_profile.<case>.yaml --run-id <id>

For fresh-clone source-checkout runs, bootstrap dependencies and annex payloads
first:

.. code-block:: bash

   python -m pip install -r requirements-dev.txt
   git submodule update --init --recursive
   git -C external/femic-public-data annex enableremote arbutus-s3
   datalad get -r external/femic-public-data/data
   export FEMIC_EXTERNAL_DATA_ROOT=$PWD/external/femic-public-data/data

1. Run upstream compilation:

   .. code-block:: bash

      femic run --run-config config/run_profile.<case>.yaml

2. Let FEMIC launch unattended BTC using generated ``03_input-*.csv``.
3. FEMIC captures ``04_output-*.csv`` / ``04_error-*.csv`` back into ``data/``.
4. Run downstream post-TIPSY stages:

   .. code-block:: bash

      femic tsa btc-post-tipsy --run-config config/run_profile.<case>.yaml --tsa <code> -v

   The command group and flag still use the legacy ``tsa`` naming seam for
   compatibility. Read them generically as the selected FMU/code target.

For the known-good K3Z Windows path from the parent FEMIC checkout, the
practical boundary is:

.. code-block:: powershell

   $env:FEMIC_EXTERNAL_DATA_ROOT="$PWD\external\femic-public-data\data"
   python -m femic run --instance-root external/femic-k3z-instance --run-config config/run_profile.k3z.yaml --run-id k3z_windows_cleanstart
   python -m femic tsa btc-post-tipsy --instance-root external/femic-k3z-instance --run-config config/run_profile.k3z.yaml --tsa k3z --run-id k3z_windows_cleanstart

Tracked downstream economics extraction is now available too:

.. code-block:: powershell

   python -m femic fansier run-and-parse "<regime.rgm>" --discount-name "FEMIC Raw 0%" --report-type txt --run-id fansier_smoke

5. Export planning-system packages:

   .. code-block:: bash

      femic export patchworks --tsa <code>
      femic export woodstock --tsa <code>
      femic export dual --tsa <code> --with-ws3-smoke --ws3-command "<ws3 smoke command>"

   The export flag remains ``--tsa`` for compatibility, but it should be read
   generically as the selected FMU/code target.

For Patchworks runtime launch, prefer the registry-backed operator surfaces
(``run-variant``, ``run-scenario``, ``run-scenario-set``) over raw `.pin`
paths when you are using shipped or user-registered FEMIC variants.

Stage Boundaries
----------------

- **Stage 00 (data prep):** ingest/filter inventory, derive strata inputs,
  compile stand attributes and checkpoints.
- **Stage 01a (per FMU/code target):** build strata/AUs, run VDYP, smooth
  curves, generate canonical BTC ``MSYT.csv`` input tables.
- **Stage 01b (post-TIPSY):** parse returned BTC/TIPSY outputs, compare
  against VDYP, publish bundle tables and diagnostics.

For TSR-style named pipelines, the AFLB/CMFLB resultant checkpoint is the
yield-ready model universe. The THLB checkpoint is a managed-area state surface
assigned to those resultant fragments, not a separate stand table. The
complement ``NTHLB = AFLB - THLB`` remains inside the model as
unmanaged/full-retention forest and still requires an untreated growth curve.
Do not start Patchworks bundle/export work from THLB area alone unless a
case-specific roadmap explicitly narrows the model universe.

Key Assumptions
---------------

- Inventory and growth model inputs are local and version-controlled by path,
  not fetched dynamically at runtime.
- BTC is the default unattended Windows BatchTIPSY seam.
- FAN$IER is now a tracked downstream Windows batch-extraction seam through
  FEMIC-owned runtime and parsing commands.
- ``03_input-*.csv`` is the canonical BTC/BatchTIPSY handoff input; XLSX
  companions are readability aids generated from the same payload.
- AFLB/CMFLB resultant fragments outside THLB remain in the model as retained
  unmanaged area; THLB is treatment eligibility, not the complete growth
  universe.
- Legacy ``02_input-*.dat`` / ``04_output-*.out`` remain compatibility
  artifacts only.
- Diagnostic plots are required QA artifacts, not optional cosmetics.

Operator Interpretation Callouts
--------------------------------

- ``strata-*.png`` should show interpretable abundance and SI distributions
  before curve fitting is trusted.
- ``vdyp_fitdiag_*.png`` should track binned medians; large early-age spikes
  or inverted SI ordering are red flags.
- AU-level first-growth synthesis should default to the smoothed observed-bin
  PCHIP family (``smoothed_bin_pchip``); treat older NLLS-oriented fits as
  legacy/fallback behavior rather than the default story.
- ``tipsy_vdyp_*.png`` should be coherent with intended untreated/treated story;
  if not, tune TIPSY config or use configured managed-curve transform mode.

Primary Sources
---------------

- ``00_data-prep.ipynb``
- ``01a_run-tsa.ipynb``
- ``01b_run-tsa.ipynb``
- ``planning/femic_instance_rebuild_contract.md``
- ``docs/reference/run-config.rst``
- ``docs/reference/patchworks-export.rst``
- ``docs/guides/btc-fansier-runtime-and-extraction.rst``
- ``docs/guides/patchworks-variant-and-scenario-management.rst``
