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

For development, ``requirements-dev.txt`` installs the FreshForge integration
through FEMIC's ``dev`` extra. For a smaller runtime install, use:

.. code-block:: bash

   python -m pip install "femic[freshforge]"

Provider Discovery
------------------

FEMIC registers provider entry points in the ``freshforge.providers`` group.
When FEMIC is installed with the optional FreshForge dependency, FreshForge can
discover provider IDs ``femic`` and ``femic.mkrf``:

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

The MKRF-specific provider references exposed for the first executable MKRF
workflow are:

- ``femic.mkrf.build_au_inputs``
- ``femic.mkrf.select_aus``
- ``femic.mkrf.build_managed_au_inputs``
- ``femic.mkrf.build_managed_au_curves``
- ``femic.mkrf.init_runtime_package``

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
   freshforge run examples/freshforge/model_build_workflow.yaml --run-id smoke --dry-run

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
surface.

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
``femic.matrix_build`` plus the MKRF command namespace ``femic.mkrf``.

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
registry control for the generic FEMIC provider. Use
:func:`femic.freshforge.mkrf_provider_factory` for the MKRF-specific provider.
Concrete workflow assembly is intentionally left to instance repositories or
caller-owned workflow documents.
