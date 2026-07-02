GitHub + DataLad + Arbutus Pattern
==================================

This guide explains the split-repo pattern FEMIC currently uses for large
datasets:

- the main FEMIC GitHub repo holds code, docs, config, and lightweight
  metadata;
- large GIS/model inputs and outputs live in a separate DataLad + git-annex
  dataset repo; and
- Arbutus S3 holds the heavy annexed payload objects.

That split keeps the codebase reviewable on GitHub while still giving FEMIC a
reproducible way to publish and materialize large datasets.

Short Version
-------------

FEMIC does **not** try to hide DataLad, git-annex, and Arbutus behind fake
magic.

Instead it splits responsibilities cleanly:

- repo creation and special-remote publishing stay in a documented maintainer
  runbook;
- clone, install, path-resolution, and preflight checks are wrapped in code
  and CLI guardrails; and
- normal runtime commands resolve external data roots explicitly instead of
  hard-coding workstation paths.

What FEMIC Wraps Today
----------------------

Registered repo install / clone
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

FEMIC has a generic catalog loader for known support repos and example instance
repos. Catalog entries come from installed instance packages or explicit
catalog YAML, not from hardcoded example metadata in FEMIC core:

- ``src/femic/builtin_instances.py``
- installed providers exposed through ``femic.instance_catalogs``

This layer wraps practical repo-install behavior:

- clone known support repos and instance repos with normal Git;
- install them into a managed external root; and
- let FEMIC resolve those locations consistently later.

Important boundary:

- this layer does **not** automatically run ``datalad get``;
- FEMIC intentionally separates **repo install** from **payload
  materialization**.

User-scoped managed roots
^^^^^^^^^^^^^^^^^^^^^^^^^

FEMIC keeps machine-specific install roots in user config instead of scattering
hard-coded paths through the codebase:

- ``src/femic/user_config.py``

Key ideas there:

- ``managed_external_root``
- ``user_instance_root``

That lets FEMIC install or resolve external support repos in stable locations
without baking a personal workstation path into project logic.

Instance-root and data-root resolution
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

FEMIC separates **instance root** from **external data root**.

Relevant code:

- ``src/femic/instance_context.py``
- ``src/femic/pipeline/io.py``

This is the bridge from:

- “we have a separate DataLad dataset repo somewhere”

to:

- “normal FEMIC runtime commands can find and trust the data they need.”

The most important operational seam is the explicit external-data root:

- ``FEMIC_EXTERNAL_DATA_ROOT``

CLI guardrails and preflight
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The operational wrapper layer lives mostly in:

- ``src/femic/cli/main.py``

This is where FEMIC starts behaving like a guarded front-end instead of just a
pile of instructions:

- checking that ``git-annex`` is present;
- checking that DataLad is usable;
- checking Arbutus environment setup on Windows; and
- warning early when the runtime environment is obviously not ready.

The practical wrapper commands contributors are expected to use include:

- ``git submodule update --init --recursive``
- ``git -C external/femic-public-data annex enableremote arbutus-s3``
- ``datalad get -r external/femic-public-data/data``
- export/set ``FEMIC_EXTERNAL_DATA_ROOT``
- ``femic prep validate-case``
- ``femic prep geospatial-preflight``

What Stays in Runbooks on Purpose
---------------------------------

The **repo-creation / publish** side is still intentionally documented as a
maintainer workflow, not an all-in-one FEMIC CLI feature.

That includes:

- creating a new DataLad dataset from scratch;
- initializing the Arbutus S3 special remote from scratch;
- wiring GitHub sibling publication dependency from scratch; and
- doing the first publish of ``main`` and ``git-annex``.

That flow is documented here:

- :doc:`public-data-mirror-runbook`

Why FEMIC stops there:

- these steps are stateful;
- they depend on account/project/bucket authority outside the repo; and
- they are exactly the kind of bootstrap/admin seam where fake automation tends
  to create harder-to-debug failures later.

How Collaborators Normally Consume the Data
-------------------------------------------

For ordinary developers or students, FEMIC does **not** expect them to recreate
the mirror.

The normal collaborator path is:

1. clone FEMIC with submodules;
2. enable the Arbutus special remote on the linked public-data submodule;
3. materialize only the data they need with ``datalad get``; and
4. point FEMIC at that materialized data root.

The best docs for that workflow are:

- :doc:`developer-environment-bootstrap`
- :doc:`deployment-instances`
- :doc:`../reference/contracts/instance-and-data-roots`
- :doc:`../reference/contracts/repo-runtime-invariants`
- :doc:`../reference/cli`

How the Coding Agent Fits In
----------------------------

The safe pattern is **not** “let the agent improvise raw DataLad and S3
commands from memory.”

The useful FEMIC pattern is:

- write the dangerous/bootstrap pieces down as a runbook;
- put stable clone/install/path-resolution/preflight behavior behind FEMIC
  wrappers and contracts; and
- let the coding agent drive **those wrappers** and **those docs**.

In plain language, the agent is useful for:

- reading the contracts before doing work;
- invoking things like ``femic instance catalog install``,
  ``femic prep validate-case``, and ``femic prep geospatial-preflight``;
- checking whether the public-data repo is installed and materialized; and
- steering the human back to the documented runbook when the task crosses into
  higher-risk DataLad / Arbutus bootstrap territory.

So the useful pattern is:

- **agent pilots the safe wrapper layer**;
- **human supervises the risky bootstrap/publish layer**.

How to Copy This Pattern into Another Project
---------------------------------------------

If you want to reuse this pattern in a non-FEMIC modelling project, copy these
design choices:

1. Keep code and heavy data in separate repos
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Use:

- one normal code repo; and
- one separate DataLad dataset repo for large input/output artifacts.

2. Use git-annex for payloads, not GitHub blobs
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Use GitHub for:

- lightweight metadata;
- issue tracking; and
- normal source control.

Use git-annex + object storage for:

- heavy rasters;
- large model inputs;
- scenario outputs; and
- archived benchmark/reference bundles.

3. Write down the repo-creation/publish flow before over-automating it
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

FEMIC’s current runbook-first approach is a good pattern because the bootstrap
path is fragile and platform-sensitive.

4. Wrap the stable seams in code
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The stable seams worth wrapping are:

- registered repo catalog;
- install/clone helpers;
- user-configured managed roots;
- instance-root resolution;
- external-data-root resolution; and
- preflight checks.

5. Use one explicit external-data environment variable
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

FEMIC uses:

- ``FEMIC_EXTERNAL_DATA_ROOT``

A similar project should likely use something like:

- ``PROJECT_EXTERNAL_DATA_ROOT``

That gives the runtime a single explicit place to look for materialized heavy
data.

6. Let the coding agent drive wrappers, not raw infrastructure bootstrapping
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The agent should mostly be calling:

- project CLI commands;
- preflight checks; and
- documented runbooks.

It should **not** be inventing new ``git annex`` / S3 / GitHub sibling
bootstrap rituals on the fly.

If You Only Read 6 Files
------------------------

If you want the fastest orientation, start here:

1. :doc:`public-data-mirror-runbook`
2. :doc:`deployment-instances`
3. :doc:`../reference/contracts/instance-and-data-roots`
4. ``src/femic/builtin_instances.py``
5. ``src/femic/pipeline/io.py``
6. ``src/femic/cli/main.py``

That set gives you:

- the publication model;
- the install/deployment model;
- the path-resolution contract; and
- the main wrapper code.

Bottom Line
-----------

The simplest honest description is:

- FEMIC does **not** try to hide DataLad/GitHub/Arbutus behind fake magic;
- it treats dataset publication as a documented, reviewable operator workflow;
- it wraps the stable downstream seams in code so normal runtime commands can
  work cleanly; and
- it uses the coding agent mainly to pilot those wrappers and guardrails, not
  to improvise infrastructure behavior.

That is the most reusable part of the design for another large-data modelling
project.
