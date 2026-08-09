BTC and FAN$IER Runtime and Extraction
======================================

Purpose
-------

This guide explains the current FEMIC-owned runtime seams for unattended BTC
and FAN$IER work on Windows.

Use this page when you want to:

- understand the supported unattended BTC `/TSR` path;
- choose between BTC indicator-bank extraction and the downstream FAN$IER
  economics lane;
- run the shipped FAN$IER batch commands without reverse-engineering the GUI
  contract again; or
- explain the current seams to another maintainer or coding agent.

BTC: Supported Unattended Runtime Seam
--------------------------------------

FEMIC's supported unattended BTC seam is:

- canonical handoff input written as ``03_input-*.csv``;
- plain installed ``TIPSYbtc.exe /TSR`` on Windows; and
- the live per-user overlay report at:
  ``<Documents>\BatchTIPSY Composer\TimberSupply.rpt``.

One rule matters more than any other:

- on Windows-native hosts, the live user-overlay ``TimberSupply.rpt`` path is
  the **only known-valid** unattended FEMIC `/TSR` seam.

On Linux+Wine and WSL-interop hosts, the launcher integration is now the
first-class supported path: ``femic tipsy run-btc`` and
``femic tsa btc-post-tipsy`` accept the BTC runtime config
(`config/tipsy.btc.runtime.yaml` or environment variables), provide a
built-in headless wrap (``--use-xvfb``), and are verified with
``femic tipsy preflight-btc``. See `docs/guides/tipsy-btc-wine-runtime.rst`
for the full cross-platform guide. A real WSL-interop run and Windows-native
CI remain the environments where those legs are executed; copied-install
staging remains the validated unattended `/TSR` seam for the Wine path.

That means:

- safe unattended BTC customization should extend the stock TSR report
  structure through that overlay seam;
- copied-install or stock-report-only `/TSR` probes are clue-gathering aids,
  not equivalent validation; and
- BTC `/No_GUI` is not part of the recommended FEMIC runtime workflow.

BTC `/No_GUI` Status
--------------------

FEMIC now treats BTC ``/No_GUI`` as a documented dead end for unattended work.

Current conclusion:

- ``/No_GUI`` changes visibility;
- it does not provide a proven useful execution seam for `.btc` project runs;
- `/TSR` and `/FLP` remain the only proven useful BTC command-line execution
  triggers for FEMIC.

For the deeper module-level explanation, see
``docs/reference/api/femic-pipeline-tipsy.rst``.

BTC Indicator Banks
-------------------

FEMIC can now extend the unattended BTC `/TSR` output surface through shipped
optional indicator banks.

Use these when you want richer BTC-native surfaces than the conservative
default TSR bundle, for example:

- stand structure;
- grades and industrial/residual products;
- mortality and crop quality;
- crown/fire, biomass, carbon, and CO2e; or
- diameter-class families.

Example:

.. code-block:: powershell

   python -m femic tipsy run-btc `
     external/femic-k3z-instance/data/03_input-tsak3z.csv `
     --indicator-bank stand-structure-threshold-raw `
     --run-id btc_threshold_smoke

Runtime defaults that matter operationally:

- logs now default under ``tipsy_io/logs``;
- scratch now defaults under ``tipsy_io/scratch``;
- live unattended `/TSR` overlay smokes should be run sequentially, not in
  parallel, because they share the same user-overlay report seam.

See also:

- ``docs/guides/stage-01b-post-tipsy.rst``
- ``docs/reference/api/femic-pipeline-tipsy.rst``

FAN$IER: Tracked FEMIC Surfaces
-------------------------------

FEMIC now owns three tracked FAN$IER command surfaces:

- ``femic fansier run-batch``
- ``femic fansier parse-batch-output``
- ``femic fansier run-and-parse``

These are Windows-only GUI-automation seams around ``Fansier.exe``. They are
not native FAN$IER CLI contracts.

FEMIC's tracked runtime now handles:

- clean-session launch;
- loading `.rgm` and optional `.dis` files;
- broad product/age selection using FAN$IER's own checked-list context menus;
- batch export to deterministic output folders; and
- parsing long-report text outputs into normalized FEMIC-owned tables.

Practical FAN$IER Lanes
-----------------------

Use the lean ingest lane when you want a cleaner machine-ingest surface:

- ``txt``
- short report
- product columns on
- activity columns off
- raw `0%` discount posture

Use the archive/discovery lane when you want broader economic harvest:

- ``txt``
- long report
- broad product and age fan-out
- the same raw `0%` discount posture unless you are explicitly modeling
  discount assumptions inside FAN$IER.

Recommended one-command lean example:

.. code-block:: powershell

   python -m femic fansier run-and-parse `
     "<path-to-regime.rgm>" `
     --discount-name "FEMIC Raw 0%" `
     --report-type txt `
     --short-report `
     --product-cols `
     --no-activity-cols `
     --single-product `
     --single-age `
     --product-name "Lumber & Mill Residues (All Grades)" `
     --age-name "Current" `
     --run-id fansier_lean_smoke

Broad archive example:

.. code-block:: powershell

   python -m femic fansier run-and-parse `
     "<path-to-regime.rgm>" `
     --discount-dis-path "<path-to-discount-profile.dis>" `
     --report-type txt `
     --long-report `
     --product-cols `
     --no-activity-cols `
     --select-all-products `
     --select-all-ages `
     --run-id fansier_archive_smoke

Related References
------------------

- ``docs/reference/cli.rst``
- ``docs/reference/api/femic-fansier-runtime.rst``
- ``docs/reference/api/femic-fansier-reporting.rst``
- ``docs/reference/api/femic-fansier-workflow.rst``
- ``planning/fansier_linkage_investigation.md``
