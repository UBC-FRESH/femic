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

AFLB Stand Universe and THLB/NTHLB Semantics
--------------------------------------------

For TSR-style Patchworks bundles, the model stand universe is the accepted
AFLB / forested model universe, not only the final THLB fragments. THLB is a
managed-treatment-eligible subset of that universe. The complement,
``NTHLB = AFLB - THLB``, remains in the model as unmanaged or full-retention
forest.

Bundle builders must therefore:

- build stand or fragment tables from AFLB, CMFLB, or the case-specific
  accepted forested model universe;
- assign every stand in that universe an untreated/natural growth curve, even
  when it is outside THLB;
- overlay the final THLB state back onto the AFLB universe to compute
  ``managed_share``, ``thlb_fact``, ``thlb_area_ha``, ``retention_share``, and
  IFM state;
- compile THLB share as managed/treatment-eligible area subject to the rest of
  the treatment, operability, age, and group gates; and
- compile NTHLB share as unmanaged/full-retention area, preserving growth,
  residual inventory, products/reports, cedar or habitat signals, and group
  memberships.

Do not drop retained forested area from the runtime just because it is outside
the THLB. In Patchworks terms, that area still belongs in the model as
unmanaged or full-retention area. If it has no growth curve, it cannot grow and
cannot support residual-inventory, old-forest, carbon, cedar, habitat, or
teaching KPI reports.

Selected-AU and Remap Semantics
-------------------------------

The bundle tables must preserve the selected-AU curve-family contract created
upstream in Stage 01a:

- ``au_table.csv`` is the Patchworks-facing AU/curve lookup. It should publish
  the accepted curve-family rows, not silently expand sparse non-selected AU
  bins into new curve families.
- ``curve_table.csv`` and ``curve_points_table.csv`` must contain only reviewed
  natural/untreated and treated/managed curve IDs for those accepted curve
  families, plus any explicit species-proportion curves required by the
  exporter.
- Stand or fragment assignment tables may retain both the raw/static AU and
  the selected canonical curve-family target. Non-selected AUs should point at
  the reviewed selected target through the lexicographic remap audit.

In other words, a case can have more static AU bins than curve families. The
static AU surface explains how the source stand was classified; the selected
curve-family surface defines which yield curve the runtime consumes. Do not
infer that every static AU bin needs a distinct VDYP/TIPSY curve.

For the TFL 6 teaching instance, Phase 3 records ``384`` static AU bins and
``77`` selected top-area AU curve families. P4 bundle work must therefore
consume the remap audit rather than compiling or publishing 384 separate
curve-family rows. MKRF carries the same idea through its
``selected_au_table.csv`` and runtime AU remap audit surfaces.

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
