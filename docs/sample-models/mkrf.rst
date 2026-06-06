MKRF Example Instance (Pointer)
===============================

Purpose
-------

FEMIC keeps this page as a short pointer for the current MKRF instance.

The active canonical rebuild runtime package now lives at:

- ``external/femic-mkrf-instance/models/mkrf_patchworks_model``

The retained PoC benchmark package remains alongside it as comparison evidence:

- ``external/femic-mkrf-instance/models/mkrf_patchworks_model_poc``

Canonical MKRF Docs
-------------------

- Linked submodule path in FEMIC: ``external/femic-mkrf-instance``
- Standalone instance docs root:
  ``external/femic-mkrf-instance/docs/index.rst``
- Current instance README:
  ``external/femic-mkrf-instance/README.md``
- Current rebuild runbook:
  ``external/femic-mkrf-instance/runbooks/REBUILD_RUNBOOK.md``

Use the current MKRF instance surfaces as source of truth for:

- the canonical rebuild runtime package and claim boundary,
- retained PoC benchmark/reference evidence,
- generated XML / tracks / spatial runtime evidence, and
- accepted legacy-only helper/control seams that remain outside the canonical
  rebuild claim boundary.

Current Scope Boundary
----------------------

The current MKRF instance in FEMIC now contains two distinct lanes:

- a canonical rebuild runtime package under
  ``external/femic-mkrf-instance/models/mkrf_patchworks_model``; and
- a retained PoC benchmark/intermediate package under
  ``external/femic-mkrf-instance/models/mkrf_patchworks_model_poc``.

The canonical rebuild lane is now the source of truth for:

- source-faithful runtime spatial publication,
- canonical ForestModel / tracks / products / accounts generation, and
- the accepted runtime-surface comparison against the PoC benchmark package.

It now also carries the reviewed Patchworks semantics contract used for the
current ``v0`` checkpoint:

- ``managed`` / ``unmanaged`` means treatment eligibility only;
- ``natural`` / ``treated`` origin means curve provenance only; and
- retention can move area between managed and unmanaged without changing
  origin.

The PoC lane remains appropriate only for:

- benchmark/reference comparison against the older compiled package behavior,
- retained control-lane evidence such as ``analysis/base.pin`` and
  ``ScenarioSet.bsh``, and
- legacy/benchmark-only caveats that are not part of the canonical rebuild
  claim boundary.

The practical handoff is:

- use the canonical rebuild package for current runtime/package reference;
- use the PoC package only for benchmark/reference comparison; and
- use Phase 60 / ``#173`` for the remaining closeout/docs claim-boundary work.

Commercial thinning follow-up
-----------------------------

The completed cedar-pole CT implementation is tracked in
``UBC-FRESH/femic-mkrf-instance#8`` and landed in the canonical runtime after
full Matrix Builder and Patchworks smoke validation. The next CT roadmap phase
is the Anna/Sean follow-up issue set under
``UBC-FRESH/femic-mkrf-instance#15``.

Legacy and PoC CT behavior remains documented as benchmark/reference:

- treatment-year CT extraction = ``0.4 * base curve``; and
- post-thin THN standing yield for later ages = ``0.6 * base curve(x)``.

That is a constant proportional gap model, not the current canonical target.

The active canonical redesign now uses bucketed CT treatments
(``CT35``, ``CT40``, ``CT45``) and bucket-specific thinned lanes so the
canonical runtime can approximate a constant-absolute-gap response legally in
ForestModel XML. The follow-up phase broadens eligibility to
``Cw + Fd >= 50%``, handles Fd-leading plantations explicitly, recalibrates
planted Hw ingrowth to a ``30%`` landscape default, and keeps the full
runtime QA gate: managed/runtime regeneration, Matrix Builder, Patchworks
smoke, saved-stage sanity audit, and targeted pytest.

Use the standalone instance treatment/state page for the exact current
canonical CT wording, bucket layout, and evidence pointers.

Current ``v0`` checkpoint signal
--------------------------------

The canonical rebuild lane has now passed a stronger runtime sanity check than
the earlier short smoke runs:

- Matrix Builder is clean against the canonical package;
- the canonical even-flow harvest-volume smoke is now treated as a
  ``100000``-iteration validation lane rather than a short scheduler sample;
- the saved-stage runtime sanity audit confirms that emitted ``indsp.*``
  species signals agree with the published source-share audit; and
- the active even-flow target ``product.yield.managed.total`` produces a
  numerically stable solution in the saved stage.

This is the current basis for treating the canonical MKRF rebuild as a
defensible ``version 0`` checkpoint.

Submodule Sync Commands
-----------------------

From the FEMIC workspace top-level directory:

.. code-block:: bash

   git submodule update --init --recursive
   git submodule update --remote external/femic-mkrf-instance

FEMIC-Local Integration Notes
-----------------------------

- MKRF instance runtime root in this repository:
  ``external/femic-mkrf-instance``
- Current canonical rebuild runtime package path:
  ``external/femic-mkrf-instance/models/mkrf_patchworks_model``
- Retained PoC benchmark package path:
  ``external/femic-mkrf-instance/models/mkrf_patchworks_model_poc``
- Rebuild contract files:
  ``external/femic-mkrf-instance/config/rebuild.spec.yaml`` and
  ``external/femic-mkrf-instance/config/rebuild.allowlist.yaml``
- Rebuild runbook:
  ``external/femic-mkrf-instance/runbooks/REBUILD_RUNBOOK.md``

For retained metadata and lineage context in FEMIC docs, see
``docs/sample-models/mkrf-metadata-lineage.rst``.
