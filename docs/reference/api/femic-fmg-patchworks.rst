``femic.fmg.patchworks`` Module
================================

The :mod:`femic.fmg.patchworks` module is FEMIC's Patchworks export synthesis
layer. It takes the compiled bundle/checkpoint surfaces produced upstream and
turns them into a Patchworks package: ``forestmodel.xml`` plus the fragments
shapefile payload that Matrix Builder and the interactive model consume later.

If you are debugging why FEMIC exported the wrong ForestModel curves, why a
fragments dataset fails structural validation, or why retention/seral/silviculture
semantics are not showing up in the Patchworks package, this is the first module
to read. In practice it owns:

- Patchworks ForestModel XML construction from bundle model context
- fragments GeoDataFrame construction and shapefile writing
- managed/unmanaged IFM assignment and origin/silviculture state wiring
- derived yield/species/seral/old-growth curve generation
- export-time validation of XML structure and fragments field/value contracts

Start Here If...
----------------

Use this page first if you are trying to:

- understand how FEMIC bundle tables become ``forestmodel.xml`` and
  ``fragments/fragments.shp``
- inspect how AU-level managed/unmanaged tracks are mapped into Patchworks
  feature attributes and treatments
- debug seral-stage, retention, CT/PCT/fertilization, or origin-state behavior
  in exported models
- work out whether a failure belongs in export synthesis here or later in
  :mod:`femic.patchworks_runtime`
- validate whether a problem is in the source bundle/checkpoint surfaces versus
  the Patchworks-specific export layer

Typical maintenance path:

1. Start with :func:`export_patchworks_package` to understand the top-level
   export contract and artifacts.
2. Move to :func:`build_patchworks_forestmodel_definition` and
   :func:`build_forestmodel_xml_tree_from_context` if the issue is visible in
   ForestModel XML.
3. Read :func:`build_fragments_geodataframe` if the issue is visible in
   fragments field values, IFM assignment, geometry, or retention state.
4. Finish with :func:`validate_forestmodel_xml_tree` and
   :func:`validate_fragments_geodataframe` if the export is failing fast on
   contract checks before runtime launch.

Typical Usage
-------------

The common operator-facing path is to export from already-built bundle tables
rather than rerunning upstream stages from inside the exporter:

.. code-block:: bash

   femic export patchworks --instance-root external/femic-k3z-instance --run-config config/run_profile.k3z.yaml --tsa k3z

At the Python level, maintainers usually enter through the top-level export
helpers after bundle tables already exist under ``data/model_input_bundle/``.

How This Fits Into The Pipeline
-------------------------------

This module sits after Stage 01b and bundle assembly. It does not run
Patchworks itself. Instead, it defines the export-time contract that later
runtime helpers consume.

At a high level, the owning sequence is:

1. read bundle/checkpoint/model-context inputs
2. derive Patchworks curves, attributes, treatments, and selects
3. write ``forestmodel.xml``
4. build and validate the fragments dataset
5. hand the resulting package off to downstream runtime tooling

That distinction matters when debugging. If the package content itself is wrong,
this module is the likely owner. If the package is correct but Patchworks fails
to launch or Matrix Builder fails later, the problem usually belongs in the
runtime layer instead.

Key Entry Surfaces
------------------

The highest-value entrypoints in this module are:

- :func:`export_patchworks_package`
  Top-level package export entrypoint returning the final artifact paths/counts.
- :func:`build_patchworks_forestmodel_definition`
  Build the in-memory Patchworks definition, including selects, treatments, and
  curve bindings.
- :func:`build_forestmodel_xml_tree`
- :func:`build_forestmodel_xml_tree_from_context`
  Build XML output from bundle tables or a prepared model context.
- :func:`build_fragments_geodataframe`
  Build the fragments dataset from FEMIC checkpoint output.
- :func:`validate_forestmodel_xml_tree`
  Enforce Patchworks XML structure expectations before writing.
- :func:`validate_fragments_geodataframe`
  Enforce required fragments field/value/geometry contracts.

The main result payload is also worth reading:

- :class:`PatchworksExportResult`

Main Contract Surfaces
----------------------

The most important export contracts in this module are:

- ``forestmodel.xml`` must contain the expected Patchworks structure, required
  select/input/treatment surfaces, and valid curve references
- fragments must carry the required columns from ``REQUIRED_FRAGMENT_COLUMNS``,
  including ``IFM``, ``ORIGIN``, ``SILV_STATE``, ``RETENTION``, and geometry
- managed/unmanaged assignment can come from explicit IFM signal columns or
  target-share heuristics
- retention is modeled as a separate scalar factor and should stay orthogonal to
  IFM and silviculture state
- optional seral-stage and silviculture configs can change which attributes,
  states, and treatments are emitted
- export-time validation should fail fast before the package reaches the
  proprietary runtime boundary

This is the code-level owner of the Patchworks export contract documented in
:doc:`../patchworks-export`.

Curve And Attribute Synthesis
-----------------------------

One reason this module is large is that it does much more than serialize
existing curves. It also derives export-specific surfaces, including:

- readable deterministic curve ids for source and derived curves
- species-yield curves from total-yield plus species-proportion curves
- seral-stage binary curves
- old-growth indicator curves
- treatment-state variants for CT, PCT, and fertilization paths
- feature/product/account bindings for managed and unmanaged tracks

That means a bug in exported Patchworks semantics often does not come from a
single raw source table. It may come from how this module derives and rebinds
curves during export.

One current high-value example is managed QMD. When the optional BTC
``stand-structure-basic`` bank is present, this module now prefers richer
BTC-native managed diameter evidence in this order:

- direct ``DBHg000`` curve points
- QMD reconstructed from ``BasalArea000`` plus ``SPH000`` / ``StemCount000``
- the older volume/height/stems approximation

That keeps the newer K3Z proving-ground QMD surfaces coherent with the richer
BTC-managed stand-structure outputs without forcing every non-bank surface to
carry the same dependency.

Another current example is the log-grade compile-recipe seam. The shipped
``log-grades`` recipe now treats the explicit grades
``D/F/H/I/J/U/X/Y`` as the additive family and excludes ``Logs_Grade_All`` by
default because that BTC field behaves as a separate scaled-log metric rather
than a true additive parent. At export time this module:

- reads the shipped reference recipe from
  ``src/femic/resources/patchworks/btc_indicator_bank_compile_recipes.yaml``;
- merges optional user overlays from
  ``~/.femic/recipe-overlays/btc_indicator_bank_compile_recipes.yaml``;
- applies optional treatment-specific ratio overrides;
- normalizes the explicit grades against harvested-volume totals so the emitted
  grade family sums to ``product.HarvestedVolume.*`` instead of raw BTC
  merchantable yield.

The current K3Z teaching contract uses that seam to bias ``CT`` harvested
volume toward lower-grade ``J/U/X/Y`` material. This is a deliberate bridge
between upstream forest-growth signals and downstream product-sector teaching
accounts, not a claim that BTC directly observed CT-grade outcomes.

The same recipe seam now also supports a second teaching bridge layer for K3Z:

- additive ``AU x species x grade`` harvested-volume products built from the
  explicit grade family plus AU-level species weights;
- matching value products built from shipped coast-market price matrices; and
- user-owned override seams under ``~/.femic/recipe-overlays`` for both the
  compile recipe and the price matrices/proxy mappings.

This bridge should be read as a modeled classroom surface, not as a claim that
BTC directly observed species-by-grade outturn. FEMIC uses the explicit grade
totals as one margin, combines them with AU/species weights, and emits the
full matrix so students can move between forest-growth accounting and
products-sector accounting inside the same Patchworks model.

Fragments And State Wiring
--------------------------

The fragments path in this module is responsible for:

- coercing geometry out of checkpoint payloads
- assigning deterministic fragment/block ids
- resolving IFM from configured signal columns or managed-share heuristics
- writing ``ORIGIN`` and ``SILV_STATE`` values expected by the XML definition
- applying full-retention overrides where configured
- preserving a valid CRS for geometry-derived area processing

This is also the main seam where exported model semantics become spatial.
If the XML looks reasonable but Patchworks behavior is still wrong, inspect the
fragments dataset generated here before assuming the runtime is at fault.

Failure Seams To Watch
----------------------

The common failure boundaries in this module are:

- invalid fragments payloads
  missing columns, null/empty geometry, invalid CRS, bad value domains, or
  duplicate fragment/block identifiers fail validation here
- XML structure drift
  missing required treatments, invalid define fields, or bad curve references
  fail export before runtime launch
- IFM assignment surprises
  changing signal columns, thresholds, or target-managed-share logic can
  silently reclassify a large portion of the fragments set
- seral/silviculture config misuse
  malformed YAML or invalid config objects can change or block which treatment
  states are emitted
- retention confusion
  retention is intended to be an explicit scalar overlay, not a synonym for IFM
  or unmanaged state, so bugs around that distinction often surface here

Cross-References
----------------

Guides and references that pair especially closely with this module:

- :doc:`../patchworks-export`
- :doc:`../../guides/model-input-bundle-and-export`
- :doc:`../../guides/patchworks-wine-runtime`
- :doc:`../../guides/cross-platform-runtime-smoke`
- :doc:`../../guides/author-instance-rebuild-spec`
- :doc:`../../guides/troubleshooting`

Related API pages:

- :doc:`femic-cli-main`
- :doc:`generated/femic.patchworks_runtime`
- :doc:`generated/femic.workflows.legacy`

.. toctree::
   :hidden:

   generated/femic.fmg.patchworks

.. automodule:: femic.fmg.patchworks
   :members:
   :undoc-members:
   :show-inheritance:
   :noindex:
