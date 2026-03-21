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

1. Run upstream compilation:

   .. code-block:: bash

      femic run --run-config config/run_profile.<case>.yaml

2. Execute manual BatchTIPSY handoff using generated ``02_input-*.dat``.
3. Upload ``04_output-*.out`` back into ``data/``.
4. Run downstream post-TIPSY stages:

   .. code-block:: bash

      femic tsa post-tipsy --run-config config/run_profile.<case>.yaml --tsa <code> -v

For the known-good K3Z Windows path from the parent FEMIC checkout, the
practical boundary is:

.. code-block:: powershell

   $env:FEMIC_EXTERNAL_DATA_ROOT='C:\Users\gep\projects\femic\external\femic-public-data\data'
   python -m femic run --instance-root external/femic-k3z-instance --run-config config/run_profile.k3z.yaml --run-id k3z_windows_cleanstart
   # manual BatchTIPSY step happens here
   python -m femic tsa post-tipsy --instance-root external/femic-k3z-instance --run-config config/run_profile.k3z.yaml --tsa k3z --run-id k3z_windows_cleanstart

5. Export planning-system packages:

   .. code-block:: bash

      femic export patchworks --tsa <code>
      femic export woodstock --tsa <code>
      femic export dual --tsa <code> --with-ws3-smoke --ws3-command "<ws3 smoke command>"

Stage Boundaries
----------------

- **Stage 00 (data prep):** ingest/filter inventory, derive strata inputs,
  compile stand attributes and checkpoints.
- **Stage 01a (per TSA):** build strata/AUs, run VDYP, smooth curves,
  generate BatchTIPSY input tables.
- **Stage 01b (post-TIPSY):** parse TIPSY outputs, compare against VDYP,
  publish bundle tables and diagnostics.

Key Assumptions
---------------

- Inventory and growth model inputs are local and version-controlled by path,
  not fetched dynamically at runtime.
- TIPSY is a manual Windows GUI boundary (human in the loop).
- ``02_input-*.dat`` is the canonical BatchTIPSY handoff input; XLSX companions
  are readability aids generated from the same payload.
- Diagnostic plots are required QA artifacts, not optional cosmetics.

Operator Interpretation Callouts
--------------------------------

- ``strata-*.png`` should show interpretable abundance and SI distributions
  before curve fitting is trusted.
- ``vdyp_fitdiag_*.png`` should track binned medians; large early-age spikes
  or inverted SI ordering are red flags.
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
