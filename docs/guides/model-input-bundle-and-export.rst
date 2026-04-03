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

The export flag remains ``--tsa`` for compatibility, but it should be read
generically as the selected FMU/code target.

Outputs:

- ``forestmodel.xml``
- ``fragments`` shapefile package
  (``fragments.{shp,dbf,shx,prj,cpg}``)

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

Strict release packaging treats the Patchworks package as incomplete unless it
includes:

- ``patchworks/forestmodel.xml``
- the full ``patchworks/fragments/`` sidecar set:
  ``fragments.shp``, ``fragments.dbf``, ``fragments.shx``,
  ``fragments.prj``, and ``fragments.cpg``

This strict release-packaging check only enforces the **export-bundle**
Patchworks minimum. It does **not** mean the package is a fully launch-ready
standalone Patchworks instance.

For a published standalone instance that users can open directly in Patchworks,
the shipped asset set must additionally include:

- compiled ``tracks/`` tables
- ``blocks/blocks.shp`` plus sidecars
- the topology CSV used by the shipped analysis surface
- the analysis/PIN launch surfaces used to open the model
- and the validated ``forestmodel.xml`` + ``fragments`` pair kept as the
  editable rebuild/overlay escape hatch

Assumptions
-----------

- Export steps consume validated bundle tables; they do not re-run upstream
  yield compilation.
- Export naming semantics (for example managed/unmanaged IFM in Patchworks)
  follow downstream system contracts, not legacy notebook naming conventions.
- Shipping ``forestmodel.xml`` plus ``fragments`` in a standalone instance is
  about preserving manual overlay/rebuild freedom, not about satisfying the
  already-compiled Patchworks launch seam alone.
