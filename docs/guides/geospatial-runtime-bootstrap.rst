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
- ArcGIS Pro fallback for SiteProd geoprocessing when canonical ``siteprod.tif`` + ``siteprod.bandmap.json`` are unavailable
- Git + git-annex + DataLad access to `external/femic-public-data`

Linux
^^^^^

Treat Linux as authoritative for:

- normal Python/FEMIC development workflow
- upstream FEMIC stages that do not require native Patchworks
- Wine-wrapped VDYP execution where native Windows VDYP is unavailable
- ArcRasterRescue executable invocation via the documented patched fork build
  (or explicit ``FEMIC_ARC_RASTER_RESCUE_EXE`` override)

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

Linux VDYP runtime note:

- When running with ``--instance-root`` (including temporary `/tmp` clones),
  FEMIC now stages missing legacy VDYP runtime assets
  (``vdyp_io/VDYP_CFG`` and ``vdyp_io/VDYP.INI``) from ``FEMIC_SOURCE_ROOT``
  before Wine dispatch.
- Keep the source checkout runtime payloads intact under
  ``$FEMIC_SOURCE_ROOT/vdyp_io`` (or ``$FEMIC_SOURCE_ROOT/VDYP7/VDYP7``).

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
- canonical pre-stacked SiteProd TIFF + band-map by default, with ArcGIS Pro fallback only when those artifacts are unavailable
- default unattended BTC handoff at the `03_input-*.csv` / `04_output-*.csv`
  boundary
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

Native Windows clones may still materialize some annexed raster worktree paths
as tiny pointer stubs instead of ordinary TIFF files. FEMIC now resolves those
pointer-style paths at the direct THLB/SiteProd raster-open seams before calling
``rasterio.open(...)``, so Linux behavior stays unchanged while Windows clones
remain usable without extra manual checkout-mode tweaking.

Verify Runtime Readiness
------------------------

Run FEMIC geospatial preflight after install:

.. code-block:: bash

   femic prep geospatial-preflight

This checks:

- Fiona import
- GDAL version visibility
- basic shapefile write/read smoke test

This is intentionally a **generic** runtime smoke, not a case-aware annex or
FileGDB materialization check. On Windows, passing
``femic prep geospatial-preflight`` does **not** prove that the canonical
annex-backed TSA boundary geodatabase is readable in the active FEMIC case.
Use ``femic prep validate-case`` for that.

Troubleshooting
---------------

- If `git` or `git annex` is missing on Windows, fix the user `PATH` first and
  restart the shell.
- If `datalad` is available only in `.venv`, use `.venv\Scripts\datalad.exe`
  explicitly instead of relying on `PATH`.
- If annex-backed payloads show only pointer files, run
  `git -C external/femic-public-data annex enableremote arbutus-s3` and then
  `datalad get -r external/femic-public-data/data` before rerunning FEMIC.
- If ``femic prep validate-case`` fails on
  ``external/femic-public-data/data/bc/tsa/FADM_TSA.gdb``, do **not** jump
  straight to reinstalling GDAL. First treat it as a likely public-data
  materialization seam and run the canonical open-source recovery sequence:

  .. code-block:: powershell

     git -C external/femic-public-data annex enableremote arbutus-s3
     .venv\Scripts\datalad.exe get -r external/femic-public-data/data
     git -C external/femic-public-data annex unlock data/bc/tsa/FADM_TSA.gdb
     python -m femic prep validate-case --instance-root external/femic-k3z-instance --run-config config/run_profile.k3z.yaml

  A successful open-source recovery should end with the canonical layer
  ``WHSE_ADMIN_BOUNDARIES_FADM_TSA`` becoming readable again through the same
  ``validate-case`` seam.
- If Fiona imports but shapefile smoke fails, verify GDAL shared-library
  resolution and recreate the virtual environment.
- If the open-source recovery path is still blocked but ArcGIS Pro is available,
  treat ``arcpy`` as a fallback recovery leg for exporting the TSA boundary to
  a GeoPandas-friendly artifact. It is a fallback, not a required primary FEMIC
  runtime dependency.
- If ArcGIS Pro fallback is required, treat `propy.bat` as a path-resolved tool,
  not something guaranteed to be on `PATH`.
- For manual GIS review on Windows, ``femic prep arcgis-review-project`` can
  emit a ready-to-open ArcGIS Pro project from the instance's local ``.shp``
  and ``.gpkg`` layers. This is an inspection aid only: it does not replace
  FEMIC's canonical geoprocessing/runtime pipeline, all emitted layers default
  to ``visible = off`` so the review project opens as a quiet workspace, and
  GeoPackage-backed layers can be staged as helper shapefiles under the chosen
  output directory when ArcGIS compatibility requires it.
- If Linux VDYP runs but Windows does not, check the Windows-native VDYP config
  directory and parameter-file resolution before rerunning the full pipeline.
- If Stage 00 cannot find ArcRasterRescue, set
  ``FEMIC_ARC_RASTER_RESCUE_EXE`` explicitly (or restore the documented
  sibling-checkout layout) rather than changing SiteProd extraction design.

