TIPSY BTC Runtime — Cross-Platform Operation
============================================

Purpose
-------

FEMIC's TIPSY yield-curve chain — Stage 01a compiles the MSYT-style input,
the unattended BTC ``/TSR`` seam runs TIPSY 4.7, Stage 01b resumes
post-TIPSY work, and the bundle assembles the managed curves — can now run
on Windows native, Linux through Wine, and WSL interop to a Windows-native
TIPSY install. The runtime is configured through environment variables, an
optional YAML file (``config/tipsy.btc.runtime.yaml``), and CLI options, in
that order of precedence.

Supported Host Matrix
---------------------

.. list-table::
   :header-rows: 1
   :widths: 18 22 60

   * - Host
     - host_mode
     - Runtime seam
   * - Windows (native)
     - ``windows``
     - Live-overlay seam: the installed ``TIPSYbtc.exe /TSR`` writes through
       the live per-user overlay report
       (``<Documents>\BatchTIPSY Composer\TimberSupply.rpt``). No FEMIC
       runtime configuration is required.
   * - Linux
     - ``wine``
     - Copied-install staging seam: FEMIC stages a writable copied TIPSY
       install under scratch and launches it through Wine
       (``wine TIPSYbtc.exe /TSR``), optionally wrapped in ``xvfb-run`` on
       headless hosts.
   * - WSL
     - ``wsl-interop``
     - Interop to a Windows-native TIPSY install: FEMIC launches the
       Windows-visible ``TIPSYbtc.exe`` through ``powershell.exe`` or
       ``cmd.exe``. Falls back to Wine-in-WSL when no interop carrier is
       reachable.

Windows-native operation requires no FEMIC runtime configuration. Linux and
WSL hosts need a Wine prefix containing a Windows TIPSY 4.7 install; see the
next section.

Wine Prefix Setup
-----------------

Linux and WSL hosts need a dedicated Wine prefix before FEMIC can run the
BTC seam. The recipe below is adapted from the TIPSY-under-Wine handoff
(``plan-tipsy-wine-btc.md``); it creates the 64-bit prefix
``~/.wine-tipsy64`` that FEMIC discovers by default.

1. Create the prefix:

   .. code-block:: bash

      WINEARCH=win64 WINEPREFIX=$HOME/.wine-tipsy64 wineboot -u

2. Install .NET Framework 4.8 (the TIPSY 4.7 MSI requires it):

   .. code-block:: bash

      WINEARCH=win64 WINEPREFIX=$HOME/.wine-tipsy64 xvfb-run -a winetricks --force --unattended dotnet48

   The ``--unattended`` flag is essential: without it the .NET installer
   opens its GUI on the virtual display and waits forever for a click.

3. Install the TIPSY 4.7 MSI into the prefix:

   .. code-block:: bash

      WINEARCH=win64 WINEPREFIX=$HOME/.wine-tipsy64 xvfb-run -a wine msiexec /i /tmp/tipsy47.msi

   The installer should exit ``0`` and place the executable at
   ``$HOME/.wine-tipsy64/drive_c/Program Files/TIPSY 4.7/BTC/TIPSYbtc.exe``.

4. Confirm the executable exists:

   .. code-block:: bash

      ls "$HOME/.wine-tipsy64/drive_c/Program Files/TIPSY 4.7/BTC/TIPSYbtc.exe"

5. Verify the resolved FEMIC runtime:

   .. code-block:: bash

      femic tipsy preflight-btc

   A ``0`` exit confirms that host mode, Wine executable and prefix,
   BatchTIPSY executable, and ``xvfb-run`` all resolve.

FEMIC prefix discovery checks ``~/.wine-tipsy64`` then ``~/.wine-tipsy47``,
so using this exact prefix name means no per-host configuration is needed
after the install exists.

Environment Variables
---------------------

The following environment variables configure the BTC/Wine runtime.
Precedence per field: CLI argument > environment variable > YAML config >
discovery default.

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Variable
     - Meaning
   * - ``FEMIC_BATCHTIPSY_EXE``
     - Path to the BatchTIPSY executable. On native Windows the default is
       ``C:\Program Files\TIPSY 4.7\BTC\TIPSYbtc.exe``; on Linux/WSL point
       it at the in-prefix executable or let Wine-prefix discovery resolve
       it.
   * - ``FEMIC_WINE_EXE``
     - Wine executable used in ``wine`` mode (``wine``/``wine64`` or an
       absolute path). In ``wsl-interop`` mode this must be
       ``powershell.exe`` or ``cmd.exe``.
   * - ``FEMIC_BTC_WINEPREFIX``
     - Wine prefix hosting the Windows TIPSY 4.7 install. ``WINEPREFIX`` is
       honored as a fallback. Prefix discovery checks ``~/.wine-tipsy64``
       then ``~/.wine-tipsy47``.
   * - ``FEMIC_BTC_USE_XVFB``
     - ``1``/``true``/``yes`` enables and ``0``/``false``/``no`` disables
       ``xvfb-run`` wrapping for headless Wine runs. Any other value is a
       hard config error.
   * - ``FEMIC_BTC_HOST_MODE``
     - ``auto`` (host discovery), ``windows`` (native), ``wine``, or
       ``wsl-interop``.

On WSL hosts, an unresolved ``auto`` mode resolves to ``wsl-interop`` only
when no Wine intent exists; supplying a Wine prefix or Wine executable
(argument, environment, or YAML) resolves ``auto`` to ``wine`` instead.

YAML Configuration
------------------

Runtime defaults can be pinned in ``config/tipsy.btc.runtime.yaml`` at the
repository root, mirroring the conventions of
``config/patchworks.runtime.yaml``. The file is instance-overridable: FEMIC
looks for ``config/tipsy.btc.runtime.yaml`` under the instance root first,
then under the current working directory.

.. code-block:: yaml

   # BTC / BatchTIPSY runtime configuration for the femic launcher.
   # Resolution order per field: CLI option > environment variable > this file > auto-discovery.
   tipsy_btc:
     batch_tipsy_exe: null        # or: /home/you/.wine-tipsy64/drive_c/Program Files/TIPSY 4.7/BTC/TIPSYbtc.exe
     wine_prefix: null            # or: /home/you/.wine-tipsy64
     wine_executable: null        # or: /usr/bin/wine
     use_xvfb: false              # auto-wrap the wine subprocess in xvfb-run when headless
     host_mode: auto              # auto | windows | wine | wsl-interop

All fields are optional; ``null`` means "unset" and defers to discovery.

CLI Usage
---------

Direct single-run control lives under ``femic tipsy``; the orchestrated
Stage 01a to 01b chain lives under ``femic tsa``.

Run one BTC ``/TSR`` job directly through Wine:

.. code-block:: bash

   femic tipsy run-btc external/femic-k3z-instance/data/03_input-tsak3z.csv \
     --wine-prefix $HOME/.wine-tipsy64 \
     --wine-exe wine \
     --use-xvfb \
     --run-id btc_wine_smoke

Run BTC, then resume post-TIPSY bundle assembly for TSA 29 with the
``log-grades`` indicator bank:

.. code-block:: bash

   femic tsa btc-post-tipsy --tsa 29 --indicator-bank log-grades

Both commands accept the cross-platform runtime options:

- ``--wine-prefix PATH``: Wine prefix hosting the Windows TIPSY install;
  resolved under the instance root when relative.
- ``--wine-exe TEXT``: Wine executable override (or ``powershell.exe`` /
  ``cmd.exe`` for ``wsl-interop`` mode).
- ``--use-xvfb`` / ``--no-xvfb``: wrap headless Wine BTC runs in
  ``xvfb-run``.
- ``--host-mode [auto|windows|wine|wsl-interop]``: BTC host mode; defaults
  to host discovery.

These per-field overrides take precedence over the runtime YAML and the
environment.

Preflight:

.. code-block:: bash

   femic tipsy preflight-btc
   femic tipsy preflight-btc --probe

``femic tipsy preflight-btc`` reports the resolved host mode, Wine
executable and prefix, BatchTIPSY executable, ``xvfb-run``, WSL-interop
carriers, and the resolved runtime YAML path without launching BTC. Exit
codes:

- ``0``: runtime OK.
- ``1``: invalid config (unparseable ``tipsy.btc.runtime.yaml``, impossible
  host mode, or a BatchTIPSY executable that cannot be resolved).
- ``2``: optional tool missing (Wine in ``wine`` mode, or ``xvfb-run`` when
  ``--use-xvfb`` is requested on a headless host).

``--probe`` additionally runs a real minimal BTC ``/TSR`` smoke through the
resolved runtime; it launches the executable, so reserve it for operator
verification.

Headless Linux Note
-------------------

On headless Linux hosts with no ``DISPLAY``, Wine needs a virtual display.
Pass ``--use-xvfb`` (or set ``FEMIC_BTC_USE_XVFB=true``) and FEMIC wraps the
Wine subprocess as ``[xvfb-run, -a, wine, ...]``. The wrap only fires when
``DISPLAY`` is unset, so an already-wrapped invocation is never
double-wrapped. If ``--use-xvfb`` is requested on a headless host but
``xvfb-run`` is not installed, FEMIC fails loudly (``femic tipsy
preflight-btc`` exits ``2``).

WSL Interop Requirements
------------------------

On WSL hosts with Windows interop enabled, ``host_mode=wsl-interop`` (or
auto-discovery) launches a Windows-native TIPSY install through
``powershell.exe`` or ``cmd.exe`` instead of Wine:

- Windows-visible scratch: the scratch/work directory must live under
  ``/mnt/<drive>/`` so the Windows TIPSY process can write its staged input,
  scratch, and output files there.
- Path translation: ``/mnt/<drive>/...`` paths are translated to
  ``<DRIVE>:\...`` automatically (for example ``/mnt/c/...`` to ``C:\...``).
- ``WINEPREFIX`` is dropped in interop mode; the prefix only matters for the
  Wine path.
- The carrier (``--wine-exe`` or ``FEMIC_WINE_EXE``) must be
  ``powershell.exe`` or ``cmd.exe``; anything else fails fast.
- In ``auto`` mode, when no interop carrier is reachable, discovery falls
  back to Wine-in-WSL instead of failing. An explicit ``wsl-interop``
  request with no carrier is a hard error.

Pipeline Chain
--------------

The cross-platform runtime plugs into the existing yield-curve chain without
changing the handoff contract:

- Stage 01a compiles the MSYT-style input CSV (``03_input-<tsa>.csv``).
- The BTC ``/TSR`` seam runs TIPSY 4.7 on the selected host shape and
  refreshes ``04_output-<tsa>.csv`` / ``04_error-<tsa>.csv``.
- Stage 01b (post-TIPSY) resumes from the refreshed output and assembles the
  managed/unmanaged curve bundle.

``femic tsa btc-post-tipsy`` drives the whole chain — unattended BTC for
each selected TSA, then post-TIPSY bundle assembly — through
``run_btc_and_post_tipsy_bundle_with_manifest`` in
``femic.workflows.legacy``. The runtime options (``--wine-prefix``,
``--wine-exe``, ``--use-xvfb``/``--no-xvfb``, ``--host-mode``) pass straight
through to the BTC stage.

Sequential Runs and Provenance
------------------------------

BTC runs must be sequential: run one at a time, never in parallel. The
Windows TIPSY GUI front-end does not tolerate concurrent instances, and
unattended ``/TSR`` jobs share the live user-overlay report seam
(``<Documents>\BatchTIPSY Composer\TimberSupply.rpt``) on Windows and the
same Wine prefix on Linux/WSL.

Each supervised run writes a JSON manifest (``btc_manifest-<run-id>.json``
under the resolved log directory — ``tipsy_io/logs`` by default for
``femic tipsy run-btc``, ``runtime/logs`` for the ``tsa btc-post-tipsy``
chain). The manifest records at minimum:

- ``host_mode``: the effective host mode (``windows`` / ``wine`` /
  ``wsl-interop``).
- ``wine_prefix``: the resolved Wine prefix, or ``null`` outside ``wine``
  mode.
- ``wine_executable``: the resolved Wine executable or interop carrier.
- ``use_xvfb``: whether ``xvfb-run`` wrapping was applied.
- ``command``: the executed command line, after path translation and any
  ``xvfb-run`` wrap.

It also records run identity, mode, timestamps, resolved input/output and
staged paths, executable and install roots, copied-install and live-overlay
flags, report template and indicator banks, and exit status.

Related Guides
--------------

- `docs/guides/btc-fansier-runtime-and-extraction.rst`
- `docs/guides/cross-platform-runtime-smoke.rst`
- `docs/guides/patchworks-wine-runtime.rst`
- `docs/guides/stage-01a-vdyp-tipsy-input.rst`
- `docs/guides/stage-01b-post-tipsy.rst`
- `docs/reference/cli.rst`
