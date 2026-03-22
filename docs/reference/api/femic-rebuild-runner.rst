``femic.rebuild_runner`` Module
===============================

The :mod:`femic.rebuild_runner` module owns FEMIC's deterministic rebuild-step
execution skeleton. It defines typed rebuild steps and outcomes, resolves a
stable topological execution order, runs step actions with shared context, and
can persist a machine-readable rebuild execution report through a pluggable sink.

If you are debugging why rebuild steps executed in a certain order, why a run
stopped after a failure, or how step metadata/error payloads become the stored
execution report, this is the first module to read. In practice it owns:

- typed rebuild step/outcome/report payloads
- deterministic topological ordering
- stop-on-failure behavior
- JSON report-sink persistence

Start Here If...
----------------

Use this page first if you are trying to:

- understand the execution skeleton under ``femic instance rebuild``
- inspect dependency ordering or cycle detection behavior
- debug report content independent of the higher-level CLI wrapper

Typical maintenance path:

1. Start with :class:`RebuildRunner` for execution-order and failure-flow
   questions.
2. Read :class:`RebuildStep`, :class:`StepOutcome`, and
   :class:`RebuildExecutionReport` for payload semantics.
3. Inspect :class:`JsonRebuildReportSink` if the issue is in report persistence.

How This Fits Into The Pipeline
-------------------------------

This module sits beneath rebuild orchestration but above individual step
actions:

1. higher-level code converts a rebuild spec into concrete step actions
2. this module resolves execution order and runs them deterministically
3. downstream report consumers read the resulting execution report

That means this module owns the *generic rebuild runner contract*, not the
meaning of specific rebuild steps or invariants.

Key Entry Surfaces
------------------

The highest-value entrypoints in this module are:

- :class:`RebuildRunner`
- :class:`RebuildStep`
- :class:`StepOutcome`
- :class:`RebuildExecutionReport`
- :class:`JsonRebuildReportSink`

Core Contracts
--------------

The most important runtime contracts in this module are:

- step IDs must be unique and dependency edges must resolve
- execution order is deterministic and topological
- step metadata can augment shared runtime context for downstream steps
- failures are captured as text payloads in outcomes and can optionally stop the
  run immediately
- report sinks receive one normalized run-level report payload

Failure Seams To Watch
----------------------

The common failure boundaries in this module are:

- dependency graph mistakes
  duplicate IDs, unknown dependencies, or cycles fail before execution begins
- context propagation surprises
  step metadata is merged into shared runtime context, so collisions can change
  downstream behavior
- stop-on-failure expectations
  caller assumptions about continued execution after a failed step must match
  the configured runner mode

Cross-References
----------------

Guides and references that pair especially closely with this module:

- :doc:`../../guides/rebuild-repro-contract`
- :doc:`../../guides/interpret-rebuild-reports`

Related API pages:

- :doc:`femic-rebuild-spec`
- :doc:`femic-rebuild-invariants`

.. toctree::
   :hidden:

   generated/femic.rebuild_runner

.. automodule:: femic.rebuild_runner
   :members:
   :undoc-members:
   :show-inheritance:
   :noindex:
