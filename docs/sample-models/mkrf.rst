MKRF PoC Example Instance (Pointer)
===================================

Purpose
-------

FEMIC keeps this page as a short pointer for the current MKRF PoC instance.
The checked-in MKRF runtime package is benchmark/intermediate evidence, not the
final canonical rebuild.

Canonical PoC Docs
------------------

- Linked submodule path in FEMIC: ``external/femic-mkrf-instance``
- Current instance README:
  ``external/femic-mkrf-instance/README.md``
- Current rebuild runbook:
  ``external/femic-mkrf-instance/runbooks/REBUILD_RUNBOOK.md``

Use the current MKRF instance surfaces as source of truth for:

- the accepted PoC runtime package and rebuild boundary,
- legacy recovery and metadata lineage notes,
- generated XML / tracks / spatial runtime evidence, and
- benchmark-only caveats that remain deferred to the later from-scratch rebuild.

Current Scope Boundary
----------------------

The current MKRF instance in FEMIC is a PoC benchmark surface only. It is
appropriate for:

- reverse-engineering and comparison against the legacy compiled package,
- minimal runnable Patchworks validation,
- accepted benchmark scenario comparison, and
- operator-facing documentation of the current intermediate runtime package.

It is not the source of truth for the later from-scratch MKRF rebuild contract.
That later rebuild remains a separate roadmap phase under issue ``#173``.

Submodule Sync Commands
-----------------------

From the FEMIC workspace top-level directory:

.. code-block:: bash

   git submodule update --init --recursive
   git submodule update --remote external/femic-mkrf-instance

FEMIC-Local Integration Notes
-----------------------------

- MKRF PoC instance runtime root in this repository:
  ``external/femic-mkrf-instance``
- Current PoC runtime package path:
  ``external/femic-mkrf-instance/models/mkrf_patchworks_model``
- Rebuild contract files:
  ``external/femic-mkrf-instance/config/rebuild.spec.yaml`` and
  ``external/femic-mkrf-instance/config/rebuild.allowlist.yaml``
- Rebuild runbook:
  ``external/femic-mkrf-instance/runbooks/REBUILD_RUNBOOK.md``

For retained metadata and lineage context in FEMIC docs, see
``docs/sample-models/mkrf-metadata-lineage.rst``.
