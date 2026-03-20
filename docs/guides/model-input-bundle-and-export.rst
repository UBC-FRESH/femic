Model Input Bundle and Export Workflow
======================================

Bundle Artifacts
----------------

FEMIC compiles standardized bundle tables under
``data/model_input_bundle/`` including:

- ``au_table``
- ``curve_table``
- ``curve_points_table``

These feed downstream planning-system exporters.

Patchworks Export
-----------------

Use:

.. code-block:: bash

   PYTHONPATH=src python -m femic export patchworks --tsa <code>

Outputs:

- ``forestmodel.xml``
- ``fragments`` shapefile package

Patchworks-specific schema expectations are documented in
``docs/reference/patchworks-export.rst``.

Woodstock Export
----------------

Use:

.. code-block:: bash

   PYTHONPATH=src python -m femic export woodstock --tsa <code>

Outputs CSV compatibility tables for yield/area/action/transition ingestion.

Dual-Fork Export (Patchworks + Woodstock + Optional ws3 Smoke)
--------------------------------------------------------------

Use:

.. code-block:: bash

   PYTHONPATH=src python -m femic export dual \
     --tsa <code> \
     --with-ws3-smoke \
     --ws3-command "<ws3 smoke command>"

This runs Patchworks and Woodstock exports from the same bundle/checkpoint
inputs, then optionally executes a ws3 smoke command and writes evidence to
``evidence/ws3_smoke_report.latest.json``.

Release Packaging Export
------------------------

Use:

.. code-block:: bash

   PYTHONPATH=src python -m femic export release \
     --case-id <code> \
     --patchworks-dir output/patchworks_<case>_validated \
     --woodstock-dir output/woodstock_<case>_validated

This builds a versioned release folder under ``releases/`` with:

- ``model_input_bundle/``
- ``patchworks/``
- optional ``woodstock/``
- ``logs/`` (selected manifests/runtime logs when present)
- ``release_manifest.json`` (file inventory + SHA256)
- ``HANDOFF.md`` (operator handoff checklist)

Assumptions
-----------

- Export steps consume validated bundle tables; they do not re-run upstream
  yield compilation.
- Export naming semantics (for example managed/unmanaged IFM in Patchworks)
  follow downstream system contracts, not legacy notebook naming conventions.
