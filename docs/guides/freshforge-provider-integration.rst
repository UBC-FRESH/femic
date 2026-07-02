FreshForge Provider Integration
===============================

Purpose
-------

FEMIC exposes FreshForge providers for model-build workflow stages. FreshForge
owns declarative graph validation, provider discovery, inspection,
deterministic planning, and explicit ``freshforge run`` orchestration. FEMIC
still owns the actual stage behavior through existing commands such as
``femic run``, ``femic tsa btc-post-tipsy``, ``femic export patchworks``,
``femic patchworks matrix-build``, and ``femic instance rebuild``.

The provider is intentionally instance-neutral. Concrete workflow documents
for K3Z or other FEMIC instances belong in the corresponding instance
repositories, where the instance root, run profile, TSA code, Patchworks
runtime configuration, and artifact names are owned.

Install
-------

FreshForge is optional. Install FEMIC with the FreshForge extra when you need
workflow orchestration:

.. code-block:: bash

   python -m pip install "femic[freshforge]"

For local development, install the editable checkout with:

.. code-block:: bash

   python -m pip install -e ".[freshforge]"

The extra currently pins ``freshforge==0.1.0a5``.

Provider Discovery
------------------

FEMIC registers provider entry points in the ``freshforge.providers`` group.
When FreshForge is installed alongside FEMIC, FreshForge can discover provider
IDs ``femic`` and ``femic.materialization``:

.. code-block:: bash

   freshforge providers

The generic provider references currently exposed for model-build workflows are:

- ``femic.validate_case``
- ``femic.geospatial_preflight``
- ``femic.compile_upstream``
- ``femic.btc_post_tipsy``
- ``femic.export_patchworks``
- ``femic.patchworks_preflight``
- ``femic.matrix_build``

Instance-specific provider references are not shipped by FEMIC core. For
example, the MKRF instance owns its executable adapter package and exposes
provider references such as ``mkrf.build_au_inputs`` only when that instance
adapter is installed.

Materialization Provider
------------------------

The ``femic.materialization`` provider is the generic FreshForge surface for
model-instance bootstrap and DataLad/git-annex materialization workflows. It is
config-driven: model instances supply small overlay YAML files, while FEMIC
owns reusable node implementations for toolchain checks, Python environment
setup, package installation, submodule setup, git-annex initialization,
special-remote enablement, required path materialization, annex availability
audits, and report generation.

The public-safe smoke workflow writes only a report and does not run
``datalad get``, package installs, submodule updates, or git-annex commands:

.. code-block:: bash

   freshforge validate examples/freshforge/materialization_smoke_workflow.yaml
   freshforge inspect examples/freshforge/materialization_smoke_workflow.yaml
   freshforge plan examples/freshforge/materialization_smoke_workflow.yaml
   freshforge run examples/freshforge/materialization_smoke_workflow.yaml --workdir runtime/freshforge --namespace smoke --json

Real MKRF, TFL6, K3Z, and TSA29 materialization overlays are later instance
phases. They should use the same provider and overlay contract rather than
adding instance names to FEMIC core.

Generic Workflow Example
------------------------

The public-safe provider example workflow lives at:

.. code-block:: text

   examples/freshforge/model_build_workflow.yaml

Validate and plan it with:

.. code-block:: bash

   freshforge validate examples/freshforge/model_build_workflow.yaml
   freshforge inspect examples/freshforge/model_build_workflow.yaml
   freshforge plan examples/freshforge/model_build_workflow.yaml
   freshforge run examples/freshforge/model_build_workflow.yaml --workdir runtime/freshforge --namespace smoke

FreshForge also exposes workflow matrix commands through
``freshforge matrix``. Matrix examples and command-output namespace routing
are planned as later compatibility phases; this guide keeps the first
released-tag example focused on direct provider discovery, validation,
inspection, planning, explicit serial runs, and report-only artifact metadata.

Namespace-Aware Artifacts
-------------------------

When ``freshforge run`` is called with ``--workdir`` and ``--namespace``,
FEMIC resolves workflow-declared artifact paths in the returned FreshForge run
record. For example, a declared artifact such as
``runtime/logs/run_manifest.json`` is reported under
``runtime/freshforge/smoke/runtime/logs/run_manifest.json`` when the command
uses ``--workdir runtime/freshforge --namespace smoke``.

This is currently report-only metadata. FEMIC does not automatically pass the
resolved paths into command options such as ``--log-dir`` or ``--output-dir``,
does not move existing runtime outputs, and does not claim that resolved
artifact paths exist unless the provider-owned command actually creates them.
Collision-safe command-output routing is a later phase.

The graph declares this order:

1. validate case
2. geospatial preflight
3. compile upstream Stage 00 / Stage 01a inputs
4. BTC and post-TIPSY bundle
5. export Patchworks package
6. Patchworks preflight
7. matrix build

Relationship To FEMIC Execution
-------------------------------

FreshForge validation, inspection, and planning are non-mutating. ``freshforge
run`` launches provider-owned FEMIC commands in deterministic plan order only
when called explicitly. Use ``config/rebuild.spec.yaml`` and
``femic instance rebuild --dry-run`` as the legacy execution dry-run comparison
surface. The generic example workflow is public-safe for validation,
inspection, and planning, but an actual run requires a real instance root and
matching configuration.

Named pipelines remain a narrower TSR/THLB recipe and runbook lane. The
FreshForge integration is the cross-package workflow graph surface intended to
describe broader model-building pipelines.

Instance Workflow Ownership
---------------------------

``femic.freshforge`` owns only the reusable FEMIC provider vocabulary and
provider execution hooks. It does not ship K3Z-specific or MKRF-specific
workflow builders. Instance-specific FreshForge documents should live in the
instance repository that owns the model-build contract. For example, the MKRF
workflow document lives in the MKRF instance repository, while FEMIC core
supplies reusable provider references such as ``femic.validate_case`` and
``femic.matrix_build``. The MKRF instance supplies its own provider namespace
``mkrf`` through its adapter package.

Boundaries
----------

The FEMIC providers validate broad node shape and can execute existing FEMIC CLI
commands when ``freshforge run`` is called. They do not:

- run during ``freshforge validate``, ``inspect``, or ``plan``;
- materialize DataLad content;
- read model inputs or declared artifact files outside the launched FEMIC
  command;
- replace ``femic instance rebuild``; or
- change FEMIC scientific stage logic.

API
---

Use :func:`femic.freshforge.provider_factory` when a caller needs explicit
registry control for the generic FEMIC provider. Concrete workflow assembly and
instance-specific providers are intentionally left to instance repositories or
caller-owned workflow documents.
