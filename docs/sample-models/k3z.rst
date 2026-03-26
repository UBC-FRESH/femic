K3Z Example Instance (Pointer)
==============================

Purpose
-------

FEMIC keeps this page as a short pointer for K3Z. The canonical student-facing
documentation now lives in the standalone K3Z instance repository.

Canonical Student Docs
----------------------

- Public repository: ``https://github.com/UBC-FRESH/femic-k3z-instance``
- Published docs: ``https://ubc-fresh.github.io/femic-k3z-instance/``
- Linked submodule path in FEMIC: ``external/femic-k3z-instance``

Use the standalone docs as source of truth for:

- land base, THLB assumptions, and AU accounting,
- analysis-area map and figure appendix,
- base-case interpretation and troubleshooting playbooks,
- operator runbook and rebuild/release checklists.

Standalone K3Z Coverage Map
---------------------------

Use the standalone K3Z docs for:

- variant selection across ``base``, ``ctfert``, ``ctfert_l15h5``,
  ``ctfert_l20h0``, ``pct_light``, ``pct_moderate``, and ``pct_heavy``,
- baseline-derived overlay subvariants
  (``basecase_riparian``, ``basecase_sum``, ``scenario1_sum``,
  ``scenario2_sum``),
- treatment sequencing and parameter logic for the intensive silviculture
  variants, and
- ``og1`` / ``og2`` old-growth semantics.

Submodule Sync Commands
-----------------------

From the FEMIC workspace top-level directory:

.. code-block:: bash

   git submodule update --init --recursive
   git submodule update --remote external/femic-k3z-instance

FEMIC-Local Integration Notes
-----------------------------

- K3Z instance runtime root in this repository:
  ``external/femic-k3z-instance``
- Rebuild contract files:
  ``external/femic-k3z-instance/config/rebuild.spec.yaml`` and
  ``external/femic-k3z-instance/config/rebuild.allowlist.yaml``
- Rebuild runbook:
  ``external/femic-k3z-instance/runbooks/REBUILD_RUNBOOK.md``

For provenance and source lineage context retained in FEMIC docs, see
``docs/sample-models/k3z-metadata-lineage.rst``.
