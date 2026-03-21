Cross-Platform Runtime Smoke and Acceptance
===========================================

Purpose
-------

This guide defines the minimum operator-visible smoke workflows for claiming
that FEMIC runs cleanly on both Windows and Linux.

It does **not** require the two platforms to use identical runtime rituals.
Instead, it defines what should be equivalent in outcome while allowing the
platform-specific boundaries that currently exist:

- Windows is authoritative for native Patchworks and native VDYP.
- Linux is authoritative for the normal Python development workflow and the
  Wine-wrapped VDYP path when Windows-only tools are unavailable.
- BatchTIPSY remains a manual GUI boundary in both cases.

Platform-Specific Runtime Rituals
---------------------------------

Windows
^^^^^^^

Expected runtime shape:

- native Python environment
- native `git`, `git-annex`, and DataLad
- native `VDYP7Console.exe`
- ArcGIS Pro fallback for SiteProd geoprocessing when required
- native Java + Patchworks
- manual BatchTIPSY handoff between Stage 01a and Stage 01b

Linux
^^^^^

Expected runtime shape:

- native Python environment
- native `git`, `git-annex`, and DataLad
- Wine-wrapped VDYP
- no expectation of native Patchworks execution
- manual BatchTIPSY handoff between Stage 01a and Stage 01b

Windows Smoke Workflow
----------------------

Use K3Z as the reference case.

1. Validate prerequisites:

   .. code-block:: powershell

      $env:FEMIC_EXTERNAL_DATA_ROOT='C:\Users\gep\projects\femic\external\femic-public-data\data'
      .venv\Scripts\datalad.exe get -r external/femic-public-data/data
      python -m femic prep validate-case --instance-root external/femic-k3z-instance --run-config config/run_profile.k3z.yaml
      python -m femic prep geospatial-preflight

2. Run Stage 01a / upstream compile through the BatchTIPSY boundary:

   .. code-block:: powershell

      python -m femic run --instance-root external/femic-k3z-instance --run-config config/run_profile.k3z.yaml --run-id k3z_windows_cleanstart

3. Confirm FEMIC produced fresh TIPSY handoff files:

- `external/femic-k3z-instance/data/02_input-tsak3z.dat`
- `external/femic-k3z-instance/data/tipsy_params_tsak3z.xlsx`
  or the latest timestamped fallback workbook

4. Run BatchTIPSY manually and refresh:

- `external/femic-k3z-instance/data/04_output-tsak3z.out`

5. Resume only downstream work:

   .. code-block:: powershell

      python -m femic tsa post-tipsy --instance-root external/femic-k3z-instance --run-config config/run_profile.k3z.yaml --tsa k3z --run-id k3z_windows_cleanstart
      python -m femic patchworks build-blocks --instance-root external/femic-k3z-instance --config config/patchworks.runtime.windows.yaml
      python -m femic patchworks matrix-build --instance-root external/femic-k3z-instance --config config/patchworks.runtime.windows.yaml --run-id k3z_windows_cleanstart

6. Optional but recommended final smoke:

- launch `external/femic-k3z-instance/models/k3z_patchworks_model/analysis/base.pin`
- confirm the baseline model opens cleanly in Patchworks

Linux Parity Workflow
---------------------

Use the same K3Z case where practical, but accept that Patchworks validation is
not native on Linux.

1. Validate prerequisites:

   .. code-block:: bash

      export FEMIC_EXTERNAL_DATA_ROOT=$PWD/external/femic-public-data/data
      git -C external/femic-public-data annex enableremote arbutus-s3
      datalad get -r external/femic-public-data/data
      femic prep validate-case --instance-root external/femic-k3z-instance --run-config config/run_profile.k3z.yaml
      femic prep geospatial-preflight

2. Run Stage 01a / upstream compile through the BatchTIPSY boundary:

   .. code-block:: bash

      femic run --instance-root external/femic-k3z-instance --run-config config/run_profile.k3z.yaml --run-id k3z_linux_parity

3. Confirm fresh TIPSY handoff files exist:

- `external/femic-k3z-instance/data/02_input-tsak3z.dat`
- `external/femic-k3z-instance/data/tipsy_params_tsak3z.xlsx`
  or the current timestamped fallback workbook

4. Run BatchTIPSY manually on a suitable Windows host and copy back:

- `external/femic-k3z-instance/data/04_output-tsak3z.out`

5. Resume downstream work on Linux:

   .. code-block:: bash

      femic tsa post-tipsy --instance-root external/femic-k3z-instance --run-config config/run_profile.k3z.yaml --tsa k3z --run-id k3z_linux_parity

6. Verify downstream artifacts match the expected contract:

- bundle tables regenerated
- comparison plots regenerated
- no stale-TIPSY freshness failure

Acceptance Criteria
-------------------

FEMIC can be considered cross-platform operational when all of the following are
true:

1. Windows preflight passes on the validated workstation.
2. Linux preflight passes on the maintained Linux environment.
3. Both platforms can produce a fresh K3Z Stage 01a handoff:
   - `02_input-tsak3z.dat`
   - workbook companion
4. Both platforms can resume Stage 01b/post-TIPSY cleanly from a fresh
   `04_output-tsak3z.out`.
5. Windows can continue through Patchworks block build + Matrix Builder.
6. The documented runtime rituals are platform-appropriate and explicit, rather
   than assuming Windows and Linux use the same tool chain.
7. Public-data annex/DataLad payload checks pass before the run starts.

What Should Match Across Platforms
----------------------------------

Even though the runtime rituals differ, the following should remain equivalent:

- selected case boundary and stratification policy
- TIPSY handoff schema
- managed/unmanaged curve bundle contract
- K3Z low-yield treated-strata exclusion policy
- K3Z treated species-mix teaching logic
- downstream bundle/export structure

What May Differ Across Platforms
--------------------------------

These differences are currently expected and acceptable:

- native Windows VDYP vs Wine-wrapped Linux VDYP
- ArcGIS Pro fallback availability on Windows only
- Patchworks validation on Windows only
- exact operator steps around manual BatchTIPSY execution
- ArcRasterRescue executable path resolution details (use
  ``FEMIC_ARC_RASTER_RESCUE_EXE`` if the default sibling layout is absent)

Evidence to Keep
----------------

At minimum, retain or inspect:

- `vdyp_io/logs/run_manifest-*.json`
- `vdyp_io/logs/patchworks_matrixbuilder_manifest-*.json` on Windows
- refreshed `tipsy_vdyp_*.png` plots
- regenerated bundle tables under `data/model_input_bundle/`

Related Guides
--------------

- `docs/guides/geospatial-runtime-bootstrap.rst`
- `docs/guides/public-data-mirror-runbook.rst`
- `docs/guides/stage-01a-vdyp-tipsy-input.rst`
- `docs/guides/stage-01b-post-tipsy.rst`
