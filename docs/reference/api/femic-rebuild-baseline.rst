``femic.rebuild_baseline`` Module
=================================

The :mod:`femic.rebuild_baseline` module owns FEMIC's structural baseline
snapshot and diff contract for instance rebuild runs. It resolves where the
baseline snapshot should live, captures the current normalized Patchworks/XML
and tracks-table state, loads and saves baseline JSON payloads, and computes
the structural diff summary later used by regression gating.

If you are debugging why a rebuild baseline did or did not match, what FEMIC
actually snapshots for comparison, or how baseline/allowlist drift is turned
into machine-readable evidence, this is the first module to read. In practice
it owns:

- baseline snapshot path resolution
- normalized current-state snapshot building
- JSON load/save for baseline payloads
- structural diff summaries between baseline and current state

Start Here If...
----------------

Use this page first if you are trying to:

- understand what ``config/rebuild.baseline.json`` is meant to contain
- inspect why a rebuild report shows baseline drift
- trace which Patchworks/XML and track-table structures are compared

Typical maintenance path:

1. Start with :func:`resolve_baseline_path` for path/instance-root questions.
2. Read :func:`build_current_snapshot` for snapshot content questions.
3. Move to :func:`diff_snapshots` when debugging baseline mismatch output.

Typical Usage
-------------

The common baseline workflow is:

.. code-block:: python

   from pathlib import Path
   from femic.rebuild_baseline import build_current_snapshot, diff_snapshots, load_snapshot

   baseline = load_snapshot(Path("config/rebuild.baseline.json"))
   current = build_current_snapshot(
       patchworks_config_path=Path("config/patchworks.runtime.windows.yaml"),
   )
   diff = diff_snapshots(baseline=baseline, current=current)

How This Fits Into The Pipeline
-------------------------------

This module sits beside rebuild execution and invariant evaluation:

1. rebuild workflows resolve the baseline path for the active instance
2. this module builds the current normalized snapshot
3. baseline and current snapshots are compared and folded into the rebuild
   evidence/report flow

That makes this module the source-of-truth for *baseline structural comparison*,
not the broader rebuild-step orchestration.

Key Entry Surfaces
------------------

The highest-value entrypoints in this module are:

- :func:`resolve_baseline_path`
- :func:`build_current_snapshot`
- :func:`load_snapshot`
- :func:`save_snapshot`
- :func:`diff_snapshots`
- :func:`load_diff_allowlist`

Core Contracts
--------------

The most important runtime contracts in this module are:

- the default baseline path is ``config/rebuild.baseline.json`` relative to the
  active instance root
- snapshots normalize the key Patchworks XML summary and track-table hash/row
  count surfaces rather than storing arbitrary raw files
- diffs are structural summaries intended for regression gating, not full file
  patches
- allowlists can be layered on top of diff results to accept intentional drift

Failure Seams To Watch
----------------------

The common failure boundaries in this module are:

- wrong baseline path assumptions
  relative baseline paths are resolved against the instance root, not the repo
  root by default
- incomplete runtime outputs
  snapshot building depends on Patchworks config/model outputs being present
- false-positive drift
  baseline mismatch can come from stale baselines or allowlists rather than
  true regressions in the current run

Cross-References
----------------

Guides and references that pair especially closely with this module:

- :doc:`../../guides/rebuild-repro-contract`
- :doc:`../../guides/interpret-rebuild-reports`
- :doc:`../../guides/deployment-instances`

Related API pages:

- :doc:`femic-rebuild-invariants`
- :doc:`femic-rebuild-spec`

.. toctree::
   :hidden:

   generated/femic.rebuild_baseline

.. automodule:: femic.rebuild_baseline
   :members:
   :undoc-members:
   :show-inheritance:
   :noindex:
