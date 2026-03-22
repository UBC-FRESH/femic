``femic.rebuild_invariants`` Module
===================================

The :mod:`femic.rebuild_invariants` module owns FEMIC's invariant metric
collection and evaluation surface for instance rebuild runs. It measures key
runtime outputs, expands species-account policy into concrete invariant entries,
and evaluates configured invariants into pass/warn/fail results with
remediation context.

If you are debugging why a rebuild report failed its regression gate, which
metrics were actually measured from a run, or how species-account policy is
translated into fatal invariants automatically, this is the first module to
read. In practice it owns:

- metric collection from runtime outputs and Patchworks artifacts
- expansion of species-account policy into invariant entries
- invariant comparator evaluation and result payloads

Start Here If...
----------------

Use this page first if you are trying to:

- understand the metrics behind ``instance_rebuild_report-<run_id>.json``
- debug a fatal invariant failure during instance rebuild
- inspect how required/absent/nonzero/zero species-account policy rules become
  concrete invariant checks

Typical maintenance path:

1. Start with :func:`collect_rebuild_metrics` for measured-value questions.
2. Read :func:`build_species_account_policy_invariants` for automatic policy
   expansion behavior.
3. Move to :func:`evaluate_invariants` when the question is about result status
   rather than raw metrics.

Typical Usage
-------------

The common pattern is to measure runtime outputs first and then evaluate the
configured invariant list against those metrics:

.. code-block:: python

   from pathlib import Path
   from femic.rebuild_invariants import collect_rebuild_metrics, evaluate_invariants

   metrics = collect_rebuild_metrics(
       instance_root=Path("."),
       log_dir=Path("vdyp_io/logs"),
       run_id="docs_example",
       patchworks_config_path=Path("config/patchworks.runtime.windows.yaml"),
   )
   results = evaluate_invariants(invariants=spec_payload["invariants"], metrics=metrics)

How This Fits Into The Pipeline
-------------------------------

This module sits after rebuild execution but before final regression gating:

1. rebuild steps produce logs, Patchworks outputs, and other runtime artifacts
2. this module measures selected metrics from those artifacts
3. configured invariants are evaluated against those metrics
4. the resulting statuses feed the final rebuild report and regression gate

That means this module owns the *invariant-evaluation contract*, not step
execution or baseline snapshotting.

Key Entry Surfaces
------------------

The highest-value entrypoints in this module are:

- :func:`collect_rebuild_metrics`
- :func:`build_species_account_policy_invariants`
- :func:`evaluate_invariants`
- :class:`InvariantResult`

Core Contracts
--------------

The most important runtime contracts in this module are:

- metrics are gathered from real runtime outputs such as tracks tables, logs,
  and Patchworks config/model locations
- species-account policy can generate fatal invariants automatically rather than
  forcing each rule to be hand-authored in the spec
- invariant outcomes preserve both measured values and remediation text so
  rebuild reports remain actionable

Failure Seams To Watch
----------------------

The common failure boundaries in this module are:

- missing runtime artifacts
  metric collection can degrade or fail if Patchworks outputs or logs are
  absent
- comparator mismatch
  a valid metric can still produce confusing output if the configured
  comparator/target pair does not match the metric's real type
- policy drift
  species-account policy changes can alter the generated invariant set even when
  the hand-authored spec itself did not change

Cross-References
----------------

Guides and references that pair especially closely with this module:

- :doc:`../../guides/rebuild-repro-contract`
- :doc:`../../guides/interpret-rebuild-reports`
- :doc:`../../guides/author-instance-rebuild-spec`

Related API pages:

- :doc:`femic-rebuild-baseline`
- :doc:`femic-rebuild-spec`
- :doc:`femic-rebuild-runner`

.. toctree::
   :hidden:

   generated/femic.rebuild_invariants

.. automodule:: femic.rebuild_invariants
   :members:
   :undoc-members:
   :show-inheritance:
   :noindex:
