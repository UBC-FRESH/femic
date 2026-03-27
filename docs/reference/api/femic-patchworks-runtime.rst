``femic.patchworks_runtime`` Module
===================================

The :mod:`femic.patchworks_runtime` module is FEMIC's Patchworks launch and
runtime-preparation seam. It takes an already exported Patchworks package and
handles the operational work needed to run Matrix Builder or related helper
commands: load runtime config, validate host prerequisites, choose the correct
launcher mode, capture logs/manifests, and prepare the 1:1 stand/block dataset
used by the model runtime.

If you are debugging why Patchworks preflight fails, why Matrix Builder will
not launch on Windows or under Wine, or why the runtime package produced the
wrong ``tracks``/``blocks`` side effects, this is the first module to read. In
practice it owns:

- Patchworks runtime config loading and validation
- host-mode detection for native Windows versus Wine/Linux execution
- preflight checks for Java, Wine, licensing, and exported input artifacts
- command construction, launch, and manifest/log capture
- block/topology preparation from exported fragments shapefiles

Start Here If...
----------------

Use this page first if you are trying to:

- understand the boundary between Patchworks export synthesis and actual
  runtime execution
- debug `patchworks preflight`, `patchworks matrix-build`, or
  `patchworks build-blocks`
- inspect why FEMIC chose native Windows Java versus Wine launch mode
- trace where stdout/stderr/manifests are written for runtime launches
- understand what runtime config fields are required before Matrix Builder can
  run

Typical maintenance path:

1. Start with :func:`load_patchworks_runtime_config` if the issue begins with a
   runtime YAML/JSON config file.
2. Move to :func:`run_patchworks_preflight` if the problem is about missing
   Java, Wine, `patchworks.jar`, license values, or runtime inputs.
3. Read :func:`run_patchworks_command` or
   :func:`run_patchworks_beanshell_script` if the failure happens during
   command launch or manifest capture.
4. Read :func:`build_patchworks_blocks_dataset` if the problem is in
   ``blocks.shp`` / topology generation rather than Matrix Builder launch.

Typical Usage
-------------

The common operator-facing path is:

.. code-block:: bash

   femic patchworks preflight --instance-root external/femic-k3z-instance --config config/patchworks.runtime.windows.yaml
   femic patchworks build-blocks --instance-root external/femic-k3z-instance --config config/patchworks.runtime.windows.yaml
   femic patchworks matrix-build --instance-root external/femic-k3z-instance --config config/patchworks.runtime.windows.yaml --run-id k3z_docs_example

At the Python level, maintainers usually call preflight before launch:

.. code-block:: python

   from pathlib import Path
   from femic.patchworks_runtime import load_patchworks_runtime_config, run_patchworks_preflight

   config = load_patchworks_runtime_config(Path("config/patchworks.runtime.windows.yaml"))
   result = run_patchworks_preflight(config)

On native Windows, FEMIC can also supervise noninteractive Matrix Builder runs
and close the spawned Matrix Builder GUI window automatically once fresh output
activity has stabilized. On hosts like the current FEMIC dev environment, the
same supervised cleanup also tears down the matching Patchworks launcher
``cmd.exe`` shell tree when it lingers after the Java process is done. This
behavior is controlled through the runtime config surface:

- ``matrix_builder.auto_close_window_on_success``
- ``matrix_builder.auto_close_settle_seconds``
- ``matrix_builder.auto_close_timeout_seconds``

This automation is intended for the local rebuild workflow and does not replace
manifest/log review when something looks wrong.

How This Fits Into The Pipeline
-------------------------------

This module sits after :mod:`femic.fmg.patchworks`. The export layer writes the
package content. This runtime layer decides whether that package is runnable on
the current host and then launches the proprietary runtime tools.

At a high level, the owning sequence is:

1. load and validate runtime config
2. verify host/runtime prerequisites with preflight
3. build and launch the correct command for the current host mode
4. capture stdout/stderr/manifests and detect fatal runtime signatures
5. optionally prepare ``blocks.shp`` and topology CSV inputs expected by the
   model runtime

That means this module is the operational boundary, not the content-synthesis
boundary. If ``forestmodel.xml`` or fragments semantics are already wrong, the
bug usually belongs in :mod:`femic.fmg.patchworks`. If the package is correct
but runtime tooling still fails, this module is the likely owner.

Key Entry Surfaces
------------------

The highest-value entrypoints in this module are:

- :func:`load_patchworks_runtime_config`
  Load and validate the Patchworks runtime config file.
- :func:`run_patchworks_preflight`
  Verify that the host, license, Java/Wine, and input artifacts are ready.
- :func:`run_patchworks_command`
  Launch Matrix Builder or the app chooser and capture logs/manifests.
- :func:`run_patchworks_beanshell_script`
  Launch Beanshell-based helper scripts through the same runtime shell.
- :func:`build_patchworks_blocks_dataset`
  Prepare ``blocks.shp`` and optional topology CSV from the fragments dataset.
- :func:`build_matrix_builder_command_string`
- :func:`build_appchooser_command_string`
- :func:`build_beanshell_command_string`
  Build the command text that the runtime layer will execute.

The main runtime payload classes are also useful because they define the core
contracts explicitly:

- :class:`PatchworksRuntimeConfig`
- :class:`PatchworksPreflightResult`
- :class:`PatchworksExecutionResult`
- :class:`PatchworksBlocksBuildResult`
- :class:`PatchworksConfigError`

Runtime Contract Surfaces
-------------------------

The most important runtime contracts in this module are:

- runtime config must contain valid `patchworks` and `matrix_builder` sections
- the runtime must have a usable Java surface on Windows or a usable Wine +
  Java surface on non-Windows hosts
- licensing must resolve through `patchworks.license_value` or the configured
  env var, usually `SPS_LICENSE_SERVER`
- `SPSHOME` must point to the Patchworks install root visible to the chosen
  launcher mode
- Matrix Builder requires a valid fragments dataset, output tracks directory,
  and ForestModel XML path before launch
- runtime launches must emit logs/manifests even when the proprietary tool
  exits badly

This is the code-level owner of the runtime behavior documented in:

- :doc:`../../guides/patchworks-wine-runtime`
- :doc:`../../guides/ubc-vpn-license-connectivity`

Host Modes And Launch Paths
---------------------------

One of the most important behaviors in this module is the host split:

- on native Windows, FEMIC launches Java directly
- on non-Windows hosts, FEMIC prefers Wine (`wine64` or `wine`)
- when `patchworks.use_xvfb` is enabled, non-Windows launches can be wrapped in
  `xvfb-run -a`

That host-mode split affects:

- which executable FEMIC searches for
- how paths are converted into Windows-visible arguments
- where `SPSHOME` and license values must be visible
- which failure signatures are expected during preflight versus runtime launch

If a command works on one host family but not the other, this module is where
the behavior diverges intentionally.

Artifacts And Failure Seams
---------------------------

The most important runtime artifacts this module produces are:

- `patchworks_matrixbuilder_stdout-<run_id>.log`
- `patchworks_matrixbuilder_stderr-<run_id>.log`
- `patchworks_matrixbuilder_manifest-<run_id>.json`
- `patchworks_beanshell_*` logs/manifests for Beanshell runs
- `blocks/blocks.shp` and optional `topology_blocks_*r.csv`

The common failure boundaries in this module are:

- invalid runtime config
  missing required sections or malformed fields fail fast here
- missing launcher/runtime prerequisites
  Java, Wine, `patchworks.jar`, `SPSHOME`, or license wiring may be absent even
  when the exported package itself is valid
- fatal runtime stderr signatures
  Matrix Builder can "run" but still report fatal conditions only through
  stderr patterns that this module scans for explicitly
- output-not-ready conditions
  a zero/empty tracks output directory after launch is treated as a runtime
  failure even if the JVM exit code is not obviously fatal
- block/topology preparation problems
  missing fragments geometry, no usable stand/block id field, or backend misuse
  can break the `build-blocks` path before Matrix Builder ever runs

Cross-References
----------------

Guides and references that pair especially closely with this module:

- :doc:`../../guides/patchworks-wine-runtime`
- :doc:`../../guides/ubc-vpn-license-connectivity`
- :doc:`../../guides/cross-platform-runtime-smoke`
- :doc:`../../guides/geospatial-runtime-bootstrap`
- :doc:`../cli`

Related API pages:

- :doc:`femic-fmg-patchworks`
- :doc:`femic-cli-main`
- :doc:`generated/femic.workflows.legacy`

.. toctree::
   :hidden:

   generated/femic.patchworks_runtime

.. automodule:: femic.patchworks_runtime
   :members:
   :undoc-members:
   :show-inheritance:
   :noindex:
