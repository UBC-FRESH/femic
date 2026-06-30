FreshForge Provider Integration
===============================

Purpose
-------

FEMIC exposes a plan-only FreshForge provider for model-build workflow stages.
FreshForge owns declarative graph validation, provider discovery,
inspection, and deterministic non-executing planning. FEMIC still owns actual
execution through existing commands such as ``femic run``,
``femic tsa btc-post-tipsy``, ``femic export patchworks``,
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

FEMIC registers a provider entry point in the ``freshforge.providers`` group.
When FEMIC is installed with the optional FreshForge dependency, FreshForge can
discover provider id ``femic``:

.. code-block:: bash

   freshforge providers

The provider references currently exposed for model-build planning are:

- ``femic.validate_case``
- ``femic.geospatial_preflight``
- ``femic.compile_upstream``
- ``femic.btc_post_tipsy``
- ``femic.export_patchworks``
- ``femic.patchworks_preflight``
- ``femic.matrix_build``

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

FreshForge graph planning is not the same surface as FEMIC rebuild execution.
Use the FreshForge workflow to make the model-build graph explicit and
checkable before execution. Use ``config/rebuild.spec.yaml`` and
``femic instance rebuild`` for the current deterministic execution and
invariant-checking path.

Named pipelines remain a narrower TSR/THLB recipe and runbook lane. The
FreshForge integration is the cross-package workflow graph surface intended to
describe broader model-building pipelines.

Instance Workflow Ownership
---------------------------

``femic.freshforge`` owns only the reusable FEMIC provider vocabulary. It does
not ship K3Z-specific workflow builders or default paths. Instance-specific
FreshForge documents should live in the instance repository that owns the
model-build contract. For example, a K3Z workflow document should live in the
K3Z instance repository, while FEMIC core supplies reusable provider references
such as ``femic.validate_case`` and ``femic.matrix_build``.

Boundaries
----------

The FEMIC provider validates broad node shape only. It does not:

- execute FreshForge nodes;
- add ``freshforge run``;
- launch FEMIC stage commands;
- read model inputs or declared artifact files;
- launch BTC or Patchworks;
- replace ``femic instance rebuild``; or
- change FEMIC scientific stage logic.

API
---

Use :func:`femic.freshforge.provider_factory` when a caller needs explicit
registry control. Concrete workflow assembly is intentionally left to instance
repositories or caller-owned workflow documents.
