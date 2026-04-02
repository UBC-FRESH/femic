K3Z Metadata and Lineage
========================

Scope
-----

This page documents the current metadata inventory, build lineage, and
provenance policy for the tracked K3Z sample model package at
``models/k3z_patchworks_model`` plus the validated export mirrors under
``output/patchworks_k3z*_validated``.

Machine-readable companion registry:

- ``models/k3z_patchworks_model/metadata/lineage_registry.yaml``

Inventory: Upstream Sources -> Model Artifacts
----------------------------------------------

The key dataset families feeding ``output/``, ``tracks/``, and ``blocks/`` are:

.. list-table::
   :header-rows: 1

   * - Target artifact family
     - Current in-repo path
     - Upstream source datasets
     - Primary compiler step
   * - Fragments shapefile
     - ``output/patchworks_k3z_validated/fragments/fragments.*``
     - ``data/model_input_bundle/au_table.csv`` plus stand checkpoint
       ``data/ria_vri_vclr1p_checkpoint7.feather`` (or explicit ``--checkpoint``)
     - ``femic export patchworks``
   * - ForestModel XML
     - ``output/patchworks_k3z_validated/forestmodel.xml``
     - ``data/model_input_bundle/{au_table,curve_table,curve_points_table}.csv``
       plus optional seral config
     - ``femic export patchworks``
   * - Blocks shapefile
     - ``models/k3z_patchworks_model/blocks/blocks.*``
     - ``models/k3z_patchworks_model/data/fragments.shp``
     - ``femic patchworks build-blocks``
   * - Block topology CSV
     - ``models/k3z_patchworks_model/blocks/topology_blocks_200r.csv``
     - ``models/k3z_patchworks_model/blocks/blocks.shp`` geometry adjacency
     - ``femic patchworks build-blocks --topology-radius 200``

Build-Lineage Chain
-------------------

Current canonical lineage for the tracked K3Z model:

1. Bundle/checkpoint stage (FEMIC pipeline output):
   ``data/model_input_bundle/*.csv`` + checkpoint feather.
2. Patchworks export stage:
   ``femic export patchworks --tsa k3z --seral-stage-config config/seral.k3z.yaml``.
   This produces ``output/patchworks/forestmodel.xml`` and
   ``output/patchworks/fragments/fragments.*``.
3. Validated-export stage:
   ``output/patchworks/forestmodel.xml`` ->
   ``output/patchworks_k3z_validated/forestmodel.xml`` and
   ``output/patchworks/fragments/*`` ->
   ``output/patchworks_k3z_validated/fragments/*``.
4. Blocks stage:
   ``femic patchworks build-blocks --config config/patchworks.runtime.windows.yaml``.
5. Matrix stage:
   ``femic patchworks matrix-build --config config/patchworks.runtime.windows.yaml``.
   Tracks CSVs are rebuilt in ``models/k3z_patchworks_model/tracks``.
6. Account-promotion stage (automatic in matrix-build):
   ``tracks/protoaccounts.csv`` -> ``tracks/accounts.csv`` with timestamped backup.

Component-Level Notes
---------------------

- Fragments compiler semantics:
  ``build_fragments_geodataframe(...)`` scopes checkpoint rows by the legacy
  case/FMU code field and AU,
  computes area/age fields, and resolves IFM assignment from THLB signal
  columns (or explicit IFM options).
- ForestModel compiler semantics:
  built from normalized AU/curve context derived from bundle tables; optional
  seral-stage boundaries are loaded from YAML.
- Blocks compiler semantics:
  strict stand:block identity mode; ``BLOCK`` is copied from stand identifier
  field (`FEATURE_ID`/`FRAGS_ID`) in fragments.
- Matrix compiler semantics:
  Matrix Builder consumes ``fragments.dbf`` + ``forestmodel.xml`` and writes
  ``tracks/*.csv``; FEMIC evaluates completion by artifact readiness and fatal
  log signatures.

Provenance Versioning Policy
----------------------------

Use this policy for each rebuild intended for teaching/collaboration release:

1. Treat these as authoritative source inputs:
   run-profile/config values, bundle tables, checkpoint feather, and seral
   config YAML.
2. Rebuild in deterministic order:
   export patchworks -> sync model inputs -> build blocks -> matrix-build.
3. Preserve run evidence:
   keep run-scoped manifests/logs under ``vdyp_io/logs`` for rebuild events.
4. Commit artifact + metadata updates together:
   model artifacts changed by rebuild, updates to this page and
   ``lineage_registry.yaml``, `ROADMAP.md` Detailed Next Steps note, and
   matching `CHANGE_LOG.md` entry.
5. Never hand-edit generated families in release prep:
   ``tracks/*.csv``, ``blocks/blocks.*``, and generated topology CSV.
   Regenerate instead.

Acceptance Checklist for Lineage Updates
----------------------------------------

- Source inventory still maps all current ``output/``, ``tracks/``, and
  ``blocks/`` artifacts.
- Command chain and runtime config references remain accurate.
- Registry file is updated for any path/command/schema changes.
- Related roadmap/changelog notes are appended in the same milestone.
