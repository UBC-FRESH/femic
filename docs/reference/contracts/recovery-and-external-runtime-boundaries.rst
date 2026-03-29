Recovery and External Runtime Boundaries
========================================

Purpose
-------

This page is the compact source of truth for restart paths, recovery workflow,
and the runtime assumptions FEMIC makes about external tools.

External Runtime Boundaries
---------------------------

.. list-table::
   :header-rows: 1
   :widths: 28 72

   * - Runtime seam
     - Contract
   * - BatchTIPSY
     - Default unattended BTC runtime boundary. FEMIC writes the canonical
       ``03_input-*.csv`` handoff, runs ``TIPSYbtc.exe /TSR`` on Windows, and
       resumes from returned ``04_output-*.csv`` / ``04_error-*.csv`` files.
   * - Patchworks
     - Proprietary runtime boundary. FEMIC can export packages, run preflight,
       and launch commands, but users must supply the local Patchworks install,
       license wiring, and host-ready runtime.
   * - ArcRasterRescue
     - Treat as an explicit external executable; if auto-discovery fails, set
       ``FEMIC_ARC_RASTER_RESCUE_EXE`` to the compiled path.
   * - ArcGIS Pro fallback
     - Windows-only fallback path for SiteProd geoprocessing when canonical
       SiteProd artifacts are unavailable.

Critical BTC `/TSR` Runtime Note
--------------------------------

The unattended BTC seam has one especially important hidden rule:

- plain installed ``TIPSYbtc.exe /TSR`` consults the per-user overlay report
  under the current user's Windows Documents folder:
  - ``<Documents>\BatchTIPSY Composer\TimberSupply.rpt``
  before falling back to the stock installed report under
  ``C:\Program Files\TIPSY 4.7\BTC``

Operational consequences:

- a broken user-overlay ``TimberSupply.rpt`` can make apparently normal stock
  ``/TSR`` runs fail
- moving the overlay out of the way restores stock fallback behavior
- the safest unattended customization path is to preserve the stock TSR report
  structure and extend it conservatively through that overlay seam
- do not assume that replacing ``TimberSupply.rpt`` wholesale with a
  clean-room generated template is equivalent to the stock report contract
- FEMIC should resolve the overlay path from the current user's Windows
  Documents directory, not from any machine-specific OneDrive naming pattern

This is now a critical FEMIC development invariant for BTC reverse-engineering
and unattended report-template probing.

Recovery Workflows
------------------

When a run stops at a known boundary, prefer the narrow restart path instead of
rerunning the entire pipeline.

After Stage 01a / before BTC:

1. confirm ``03_input-*.csv`` exists and is the intended handoff payload
2. run ``femic tsa btc-post-tipsy ...`` to launch unattended BTC and resume
3. inspect ``04_output-*.csv`` / ``04_error-*.csv`` if the run fails

After BTC output refresh:

.. code-block:: powershell

   $env:FEMIC_EXTERNAL_DATA_ROOT="$PWD\external\femic-public-data\data"
   python -m femic tsa btc-post-tipsy --instance-root external/femic-k3z-instance --run-config config/run_profile.k3z.yaml --tsa k3z --run-id k3z_resume

Before Patchworks runtime launch:

1. run ``femic patchworks preflight ...``
2. confirm Java or Wine + Java is available for the host mode
3. confirm ``patchworks.jar``, ``SPSHOME``, and license values are wired
4. launch ``build-blocks`` or ``matrix-build`` only after preflight is clean

Host Assumptions
----------------

- Windows is the authoritative host for native Patchworks launch, native VDYP,
  and ArcGIS Pro fallback workflows.
- Linux is a supported development host and can run the non-proprietary FEMIC
  path plus Wine-based Patchworks runtime where configured.
- ``patchworks.use_xvfb: true`` requires ``xvfb-run`` on non-Windows hosts.
- A successful FEMIC preflight validates config and environment shape, not the
  entire proprietary runtime behavior of third-party tools.

If Something Looks Wrong
------------------------

- Wrong files or configs resolved:
  check :doc:`instance-and-data-roots`.
- BTC / BatchTIPSY resume blocked unexpectedly:
  check :doc:`stage-boundaries-and-canonical-artifacts`.
- Patchworks launch fails after a correct export:
  check Patchworks runtime prerequisites and host mode before changing export
  logic.
- Public-data fallback missing:
  confirm ``datalad get`` completed and ``FEMIC_EXTERNAL_DATA_ROOT`` points at
  real payloads.

See Also
--------

- :doc:`../../guides/stage-01b-post-tipsy`
- :doc:`../../guides/patchworks-wine-runtime`
- :doc:`../../guides/geospatial-runtime-bootstrap`
- :doc:`../../guides/cross-platform-runtime-smoke`
- :doc:`../api/femic-pipeline-tipsy`
- :doc:`../api/femic-patchworks-runtime`
- :doc:`../api/femic-pipeline-siteprod`
