Geospatial and Runtime Bootstrap
================================

Why This Matters
----------------

FEMIC depends on more than Python packages. A usable workstation needs a
combination of:

- geospatial Python libraries (Fiona/GDAL)
- Git + git-annex + DataLad for annex-backed public-data payloads
- platform-specific external tools such as VDYP, Patchworks, Java, ArcGIS Pro,
  and Wine where applicable

This guide records the currently known-good bootstrap rituals for both Windows
and Linux, with Windows treated as the active reference host for end-to-end
Patchworks validation.

For the canonical source-checkout developer ritual, see
``docs/guides/developer-environment-bootstrap.rst``.

Authoritative Platform Runtime Surfaces
---------------------------------------

Windows
^^^^^^^

Treat Windows as authoritative for:

- native Patchworks launch and Matrix Builder
- native Java runtime for Patchworks
- native VDYP (`VDYP7Console.exe`)
- ArcGIS Pro fallback for SiteProd geoprocessing
- Git + git-annex + DataLad access to `external/femic-public-data`

Linux
^^^^^

Treat Linux as authoritative for:

- normal Python/FEMIC development workflow
- upstream FEMIC stages that do not require native Patchworks
- Wine-wrapped VDYP execution where native Windows VDYP is unavailable

Core Executables and Services
-----------------------------

Windows workstation checklist:

- `python`
- `git`
- `git annex`
- `.venv\Scripts\datalad.exe`
- Java for Patchworks
- Patchworks installation / `patchworks.jar`
- native `VDYP7Console.exe`
- ArcGIS Pro Python (`propy.bat`) available by explicit path if not on `PATH`

Linux workstation checklist:

- `python`
- `git`
- `git annex`
- `datalad`
- `java`
- `wine` / `wine64`
- Linux geospatial runtime (`gdal-bin`, `libgdal-dev`, Fiona-compatible stack)

Windows Bootstrap Ritual
------------------------

1. Upgrade packaging tools:

   .. code-block:: powershell

      python -m pip install --upgrade pip setuptools wheel

2. Install/refresh the local virtual environment dependencies:

   .. code-block:: powershell

      python -m venv .venv
      .venv\Scripts\Activate.ps1
      python -m pip install -r requirements-dev.txt

3. Confirm the Windows runtime baseline:

   .. code-block:: powershell

      git --version
      git annex version
      .venv\Scripts\datalad.exe --version
      java --version

4. Materialize the annex-backed public data you need:

   .. code-block:: powershell

      git submodule update --init --recursive
      git -C external/femic-public-data annex enableremote arbutus-s3
      .venv\Scripts\datalad.exe get -r external/femic-public-data/data

5. Validate the case before long runs:

   .. code-block:: powershell

      femic prep validate-case --instance-root external/femic-k3z-instance --run-config config/run_profile.k3z.yaml
      femic prep geospatial-preflight

6. For the known-good K3Z Windows path, expect the following runtime pattern:

- native VDYP
- ArcGIS Pro fallback for SiteProd when needed
- manual BatchTIPSY handoff at the `02_input-*.dat` / `04_output-*.out` boundary
- native Patchworks / Matrix Builder after post-TIPSY

Linux Bootstrap Ritual
----------------------

1. Install system geospatial dependencies first:

   .. code-block:: bash

      sudo apt-get update
      sudo apt-get install -y gdal-bin libgdal-dev

2. Install/refresh the virtual environment:

   .. code-block:: bash

      python -m venv .venv
      . .venv/bin/activate
      python -m pip install --upgrade pip setuptools wheel
      python -m pip install -r requirements-dev.txt

3. Confirm the Linux runtime baseline:

   .. code-block:: bash

      git --version
      git annex version
      datalad --version
      java --version
      wine --version

4. Materialize the annex-backed public data you need:

   .. code-block:: bash

      git submodule update --init --recursive
      git -C external/femic-public-data annex enableremote arbutus-s3
      datalad get -r external/femic-public-data/data

5. Validate the case before long runs:

   .. code-block:: bash

      export FEMIC_EXTERNAL_DATA_ROOT=$PWD/external/femic-public-data/data
      femic prep validate-case --instance-root external/femic-k3z-instance --run-config config/run_profile.k3z.yaml
      femic prep geospatial-preflight

DataLad / git-annex Smoke Checks
--------------------------------

These checks are lightweight and worth running before a clean-start pipeline rerun:

.. code-block:: powershell

   .venv\Scripts\datalad.exe get external/femic-public-data/data/misc.thlb.tif
   Test-Path external\femic-public-data\data\misc.thlb.tif

A healthy Windows checkout should also report:

.. code-block:: powershell

   git -C external/femic-public-data annex version
   .venv\Scripts\datalad.exe status external/femic-public-data

If the payload is present and the repo responds normally, the Windows public-data
bootstrap is good enough for FEMIC pipeline runs.

Verify Runtime Readiness
------------------------

Run FEMIC geospatial preflight after install:

.. code-block:: bash

   femic prep geospatial-preflight

This checks:

- Fiona import
- GDAL version visibility
- basic shapefile write/read smoke test

Troubleshooting
---------------

- If `git` or `git annex` is missing on Windows, fix the user `PATH` first and
  restart the shell.
- If `datalad` is available only in `.venv`, use `.venv\Scripts\datalad.exe`
  explicitly instead of relying on `PATH`.
- If annex-backed payloads show only pointer files, run
  `git -C external/femic-public-data annex enableremote arbutus-s3` and then
  `datalad get -r external/femic-public-data/data` before rerunning FEMIC.
- If Fiona imports but shapefile smoke fails, verify GDAL shared-library
  resolution and recreate the virtual environment.
- If ArcGIS Pro fallback is required, treat `propy.bat` as a path-resolved tool,
  not something guaranteed to be on `PATH`.
- If Linux VDYP runs but Windows does not, check the Windows-native VDYP config
  directory and parameter-file resolution before rerunning the full pipeline.
