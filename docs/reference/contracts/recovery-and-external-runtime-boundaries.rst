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
       license wiring, and host-ready runtime. The current proving-ground
       headless seam is now real on native Windows:
       FEMIC can launch a `.pin` without `classic_GUI(control)`, wait one
       unattended iteration, save a stage, and return control cleanly.
   * - FAN$IER
     - Windows-only proprietary runtime boundary. FEMIC now owns a tracked
       unattended batch seam around ``Fansier.exe``: it can launch a clean
       session, load one `.rgm` plus optional `.dis`, run Batch mode,
       harvest deterministic report outputs, and parse those reports through
       FEMIC-owned reporting/workflow surfaces.
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

For unattended FEMIC BTC ``/TSR`` work, this live user-overlay path is the
**only known-valid runtime seam**.

Operational consequences:

- a broken user-overlay ``TimberSupply.rpt`` can make apparently normal stock
  ``/TSR`` runs fail
- moving the overlay out of the way restores stock fallback behavior
- the safest unattended customization path is to preserve the stock TSR report
  structure and extend it conservatively through that overlay seam
- copied-install-local ``TimberSupply.rpt`` overrides and stock-report-only
  ``/TSR`` probes are useful clue-gathering at best; they are not equivalent
  validation of the live unattended FEMIC seam
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

Before FAN$IER unattended extraction:

1. confirm you are on a Windows host with ``Fansier.exe`` available
2. confirm the target `.rgm` exists
3. optionally confirm a `.dis` file exists if you want to load discount
   assumptions instead of creating/selecting them in-session
4. choose the intended output lane:
   - lean ingest: short `txt`, product columns on, activity columns off
   - archive/discovery: long `txt`, broad products/ages

Patchworks Headless Runtime Note
--------------------------------

The first successful FEMIC-controlled no-GUI Patchworks seam now has one
critical scheduler rule:

- in the proving-ground BeanShell helper, let
  ``Control.waitForIterations(...)`` own scheduler startup
- do **not** call ``control.resume()`` immediately before the wait in this
  headless path

In the current native-Windows proving ground, the explicit ``resume()`` caused
the old ``java.lang.IllegalStateException: Not suspended`` failure. Removing
that pre-resume step allows the headless helper to:

1. load the proving-ground ``.pin``
2. reach ``PatchWorks_Init`` completion
3. wait one unattended iteration
4. suspend after the wait
5. call ``saveStage(...)``
6. return control cleanly while FEMIC tears down the Patchworks Java tree

FEMIC now also supervises these Windows headless runs directly:

- success and failure are detected from explicit headless trace/log markers
- failed runs no longer leave dead console shells for the human to close
- successful runs are also terminated cleanly after the success marker and
  saved-stage verification

The proving-ground seam has now advanced one step further:

- a minimal headless scenario mode can activate
  ``product.Yield.managed.Total`` with a modest annual minimum before the
  bounded wait/save cycle;
- the saved proving-ground stage now records that target as active in
  ``scenario/targetStatus.csv``;
- ``scenario/targetSummary.csv`` contains non-zero managed-yield currents and
  derived ``flow.even.product.Yield.managed.Total`` values; and
- ``scenario/schedule.csv`` is non-empty and contains real managed treatments.

One useful reverse-engineering nuance is now established too:

- directly activating ``flow.even.product.Yield.managed.Total`` changed target
  state but still left the saved schedule empty;
- activating the underlying ``product.Yield.managed.Total`` target produced
  the first useful saved headless schedule on the K3Z proving ground.

The next proving-ground refinement is now also established:

- a real ``flow.even.*`` headless smoke works when FEMIC treats it as a
  two-phase scheduler problem instead of a one-shot target toggle;
- the helper must first seed the underlying
  ``product.Yield.managed.Total`` target so there is harvest pressure in the
  final period, then suspend, then activate the companion
  ``flow.even.product.Yield.managed.Total`` target for the second wait phase;
- proving-ground smoke ``p49_smoke_20260328q`` saved a stage where both the
  underlying harvest target and the even-flow companion were active in
  ``scenario/targetStatus.csv``, both had non-zero currents in
  ``scenario/targetSummary.csv``, and ``scenario/schedule.csv`` remained
  non-empty with real managed treatments.
- the normal CLI/default-target path now proves the same seam too:
  ``p49_smoke_20260328r`` omitted an explicit scenario target and relied on
  FEMIC's default ``product.Yield.managed.Total`` resolution; the saved stage
  still recorded both targets as active, and ``scenario/schedule.csv``
  remained non-empty.

The current closeout-level proving-ground contract is now anchored on the real
base K3Z variant:

- FEMIC's ``max-even-flow-smoke`` mode now defaults to a useful K3Z recipe:
  default target ``product.Yield.managed.Total``, default iteration budget
  ``100000``, seed harvest first on the underlying target, force that base
  target into linear penalty mode, set its maximum to ``200000`` in every
  period at default weight, seed its minimum to ``10000`` per period, then
  activate ``flow.even.product.Yield.managed.Total`` with minimum = maximum =
  ``0`` and minimum = maximum weight = ``100`` across periods.
- proving-ground smoke ``p49_base_closeout_20260328b`` ran against
  ``analysis/base.pin`` and saved a stage where both the underlying harvest
  target and the even-flow companion were active, the base target stabilized at
  roughly ``122200`` per period inside the ``100000..200000`` band, the
  even-flow summary values stayed tightly clustered near zero, and
  ``scenario/schedule.csv`` remained non-empty with real treatments.

Patchworks Registry Operator Note
---------------------------------

The current preferred operator surface for shipped Patchworks examples is now
registry-backed, not raw-path-first:

- inspect with ``instances list`` / ``variants list`` / ``variants show``;
- inspect grouped download/materialization work with
  ``variants materialization-plan``;
- launch with ``run-variant``, ``run-scenario``, or the scenario-set helpers.

Use raw `.pin` paths only when you are intentionally bypassing the FEMIC
registry/operator layer.

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
- :doc:`../../guides/btc-fansier-runtime-and-extraction`
- :doc:`../../guides/patchworks-variant-and-scenario-management`
- :doc:`../../guides/patchworks-wine-runtime`
- :doc:`../../guides/geospatial-runtime-bootstrap`
- :doc:`../../guides/cross-platform-runtime-smoke`
- :doc:`../api/femic-pipeline-tipsy`
- :doc:`../api/femic-fansier-runtime`
- :doc:`../api/femic-fansier-workflow`
- :doc:`../api/femic-patchworks-variants`
- :doc:`../api/femic-patchworks-runtime`
- :doc:`../api/femic-pipeline-siteprod`
