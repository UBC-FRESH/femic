Patchworks Variant and Scenario Management
==========================================

Purpose
-------

This guide explains FEMIC's registry-backed Patchworks operator surface.

Use this page when you want to:

- launch an installed instance-owned Patchworks variant without passing a raw `.pin`;
- inspect instance-package or user-defined variant metadata;
- run a named scenario or scenario set; or
- understand what FEMIC will materialize before a Patchworks launch.

Registry Shape
--------------

FEMIC merges three registry sources at runtime:

- the generic packaged registry shell shipped with FEMIC;
- installed instance-owned registry providers exposed through
  ``femic.patchworks_variant_registries``; and
- an optional user overlay at ``~/.femic/variants.yaml``.

K3Z and MKRF Patchworks variants are no longer built into FEMIC core. They
appear when the corresponding instance package is installed in the active
environment.

In the parent source checkout, install the example instance packages from their
submodules before using their registry entries:

.. code-block:: powershell

   python -m pip install -e external/femic-k3z-instance
   python -m pip install -e external/femic-mkrf-instance

The registry currently carries:

- instance metadata;
- variant definitions;
- named scenarios attached to variants;
- named scenario sets;
- default scenario per variant when available;
- default scenario set per instance when available; and
- optional materialization actions that FEMIC can execute before launch.

Canonical K3Z provider examples are:

- ``k3z.base``
- ``k3z.intensive_light_standstructure``
- ``k3z.proving_ground``

Canonical MKRF provider examples are:

- ``mkrf.base``
- ``mkrf.poc_base``

Read-Only Inspection Flows
--------------------------

Use these commands first when orienting yourself:

.. code-block:: powershell

   python -m femic patchworks instances list
   python -m femic patchworks variants list --instance-id k3z
   python -m femic patchworks variants show k3z.base
   python -m femic patchworks scenarios list k3z.base
   python -m femic patchworks scenario-sets list --instance-id k3z
   python -m femic patchworks scenario-sets show k3z.proving_ground

Use ``variants show`` when you want the resolved instance root, runtime
config, `.pin`, provider source, and materialization summary for one variant.

Use ``variants materialization-plan`` when you want the richer pre-launch
download/materialization view:

.. code-block:: powershell

   python -m femic patchworks variants materialization-plan k3z.base

Materialization Consent Surface
-------------------------------

When a variant declares materialization work, FEMIC now summarizes it in
operator terms before launch:

- dataset count;
- grouped dataset roots;
- known estimated bytes;
- whether any sizes are still unknown; and
- whether the current plan crosses the default consent threshold.

Current consent rule:

- FEMIC prompts when known estimated downloads exceed ``100 MiB``;
- use ``--allow-large-download`` to skip that prompt deliberately.

The summary is grouped by dataset root first, then backed by raw per-action
detail lines for auditing.

Variant Launch Flows
--------------------

Use ``run-variant`` when you want the default launch surface for a named
variant:

.. code-block:: powershell

   python -m femic patchworks run-variant `
     k3z.base `
     --run-id k3z_variant_smoke `
     --scenario-mode max-even-flow-smoke

If an instance package is not installed, FEMIC reports the variant as unknown.
Install the owning package or provide an explicit user registry overlay before
launching the variant.

Use ``run-scenario`` when the registry already defines a named scenario:

.. code-block:: powershell

   python -m femic patchworks run-scenario `
     k3z.base `
     even_flow_smoke `
     --run-id k3z_scenario_smoke

Use ``run-default-scenario`` when the variant has a registry default:

.. code-block:: powershell

   python -m femic patchworks run-default-scenario `
     k3z.intensive_light_standstructure `
     --run-id k3z_default_scenario_smoke

Scenario Sets
-------------

Scenario sets are named sequential bundles of scenario runs.

Use these commands when you want the registry to drive a proving-ground
multi-step run:

.. code-block:: powershell

   python -m femic patchworks run-scenario-set `
     k3z.proving_ground `
     --run-id k3z_set_smoke

   python -m femic patchworks run-default-scenario-set `
     k3z `
     --run-id k3z_default_set_smoke

Current policy:

- scenario sets run sequentially;
- parallel scenario-set execution remains future work.

User Overlay Management
-----------------------

FEMIC also ships user-overlay mutation commands for the writable registry:

- ``variants register``
- ``variants update``
- ``variants remove``

Use these when you want to add or override local Patchworks variant entries
without mutating instance-package registries.

Example:

.. code-block:: powershell

   python -m femic patchworks variants register `
     demo.base `
     --label "Demo base" `
     --instance-id demo `
     --instance-root C:\path\to\instance `
     --analysis-pin C:\path\to\analysis\base.pin `
     --runtime-config C:\path\to\config\patchworks.runtime.windows.yaml

Related References
------------------

- ``docs/reference/cli.rst``
- ``docs/reference/api/femic-patchworks-variants.rst``
- ``docs/reference/contracts/recovery-and-external-runtime-boundaries.rst``
- ``planning/patchworks_variant_registry_design.md``
