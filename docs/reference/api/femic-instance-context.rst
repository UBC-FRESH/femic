``femic.instance_context`` Module
=================================

The :mod:`femic.instance_context` module is FEMIC's source-of-truth seam for
resolving the active deployment instance root. It is small, but it owns one of
the most important path contracts in the entire system: whether runtime paths
should be resolved from an explicit ``--instance-root``, the
``FEMIC_INSTANCE_ROOT`` environment variable, the current working directory, or
the legacy repo-root fallback path used for backward compatibility.

If you are debugging why FEMIC read config or data files from the wrong place,
why a command worked from the repo root but not from a deployment instance, or
why tests and direct command-function calls behave differently from the CLI,
this is the first module to read. In practice it owns:

- precedence rules for instance-root resolution
- the typed :class:`InstanceContext` payload used by downstream path logic
- compatibility fallback to the legacy repository-root layout
- normalization of relative paths against the resolved instance root

Start Here If...
----------------

Use this page first if you are trying to:

- understand the precedence between ``--instance-root``,
  ``FEMIC_INSTANCE_ROOT``, and the current working directory
- debug why FEMIC unexpectedly fell back to the legacy repository root
- inspect how a relative ``Path`` option becomes an absolute runtime path
- decide whether an instance-path bug belongs here or in
  :mod:`femic.pipeline.io`

Typical maintenance path:

1. Start with :func:`resolve_instance_context` for any question about which
   root FEMIC chose.
2. Read :class:`InstanceContext.resolve_path` when the issue is about how
   relative config/data/log paths are normalized.
3. Inspect the legacy workspace marker helpers if behavior differs between
   deployment-instance and source-checkout workflows.

Typical Usage
-------------

The common pattern is to resolve the context once and then normalize all
instance-relative paths through it:

.. code-block:: python

   from pathlib import Path
   from femic.instance_context import resolve_instance_context

   context = resolve_instance_context(instance_root=Path("external/femic-k3z-instance"))
   run_config_path = context.resolve_path(Path("config/run_profile.k3z.yaml"))

How This Fits Into The Pipeline
-------------------------------

This module sits below the CLI and above nearly every runtime path decision:

1. command-layer inputs decide whether an explicit instance root was supplied
2. :func:`resolve_instance_context` chooses the active root using CLI, env,
   current working directory, and optional legacy fallback rules
3. downstream modules such as :mod:`femic.pipeline.io` use that resolved root
   to derive config, data, output, and log paths

That means this module owns *where* FEMIC thinks the instance begins. It does
not decide which specific artifacts inside that root should be used. Once the
root is chosen, artifact selection moves into higher-level modules.

Key Entry Surfaces
------------------

The highest-value entrypoints in this module are:

- :func:`resolve_instance_context`
  Resolve the active instance root with CLI > env > cwd precedence and
  optional legacy fallback behavior.
- :class:`InstanceContext`
  Small typed payload that records the chosen root, its source, and any
  compatibility warnings.
- :meth:`InstanceContext.resolve_path`
  Normalize a user-facing path relative to the resolved instance root.

Core Contracts
--------------

The most important runtime contracts in this module are:

- explicit CLI ``instance_root`` wins over everything else
- ``FEMIC_INSTANCE_ROOT`` wins when CLI input is absent
- otherwise FEMIC uses the current working directory
- optional legacy fallback is only used when the caller provides a legacy repo
  root, the current working directory does not already look like an instance
  root, and the legacy root still matches the older workspace markers
- relative paths are always resolved beneath the chosen instance root

Those rules are why this module matters so much for tmp clones, bundled
``external/*`` instances, and tests that call command functions directly.

Failure Seams To Watch
----------------------

The common failure boundaries in this module are:

- wrong precedence assumptions
  callers sometimes expect current working directory behavior even when
  ``FEMIC_INSTANCE_ROOT`` is set
- silent legacy fallback surprise
  compatibility fallback can make FEMIC appear to "find" files unexpectedly if
  the repo root still looks like an old-style workspace
- non-``Path`` option objects
  direct test invocation can surface Typer ``OptionInfo``-like objects, which
  this module explicitly normalizes away

Cross-References
----------------

Guides and references that pair especially closely with this module:

- :doc:`../../guides/deployment-instances`
- :doc:`../../guides/developer-environment-bootstrap`
- :doc:`../../guides/pipeline-overview`
- :doc:`../cli`

Related API pages:

- :doc:`femic-pipeline-io`
- :doc:`femic-instance-bootstrap`

.. toctree::
   :hidden:

   generated/femic.instance_context

.. automodule:: femic.instance_context
   :members:
   :undoc-members:
   :show-inheritance:
   :noindex:
