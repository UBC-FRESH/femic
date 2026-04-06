``femic.tsr_catalog`` Module
============================

The :mod:`femic.tsr_catalog` module owns FEMIC's first BC Timber Supply Review
intelligence slice. It crawls the public TSA-oriented TSR document surfaces,
normalizes TSA/cycle/document metadata, writes the canonical JSON registry
artifacts under ``metadata/tsr``, and fetches/caches TSR PDFs into a
configurable corpus root with provenance manifests. The current extraction
slice also derives reviewable candidate facts from cached TSR PDFs and writes a
canonical ``metadata/tsr/tsa_candidate_facts.json`` artifact. The current
overlay slice initializes reviewed/adopted per-instance TSR overlays under
``config/tsr/overlay.yaml`` without auto-promoting unresolved candidate facts,
the current reporting slice renders guided review tables over the canonical
fact pool without forcing users to hand-scrub raw JSON, and the current
override slice adds reviewed per-instance source-layer escape hatches under
``config/tsr/source_layer_overrides.yaml`` for tokens that public BCDC
inference cannot resolve safely. The new recipe scaffold slice adds reviewed
working YAML surfaces under:

- ``config/tsr/source_layers.recipe.yaml``
- ``config/tsr/thlb_netdown.recipe.yaml``

Use this page when you are debugging the TSR indexing logic itself rather than
the higher-level CLI surface.

Default user-local cache paths used by the first fetch/cache slice are:

- ``~/.femic/tsr/corpus``
- ``~/.femic/tsr/tsa_pdf_cache_manifest.json``

Start Here If...
----------------

Use this page first if you are trying to:

- understand how FEMIC crawls the BC TSR landing surface and TSA publish tree;
- inspect how TSA identity, cycle labels, and document types are normalized; or
- debug the canonical JSON outputs written to ``metadata/tsr``; or
- inspect how TSR PDF cache manifests and corpus-relative paths are shaped for
  a later DataLad-managed corpus split; or
- inspect how cached TSR PDFs are turned into reviewable source-layer, AU,
  THLB, and TIPSY candidate facts; or
- inspect how reviewed/adopted instance-local TSR overlays are initialized and
  summarized.

Typical Usage
-------------

The common operator-facing entrypoint is:

.. code-block:: bash

   femic tsr index
   femic tsr fetch
   femic tsr extract
   femic tsr facts-report --tsa 29 --fact-family source_layer_candidate
   femic tsr recipe-init --instance-root external/femic-tsa29-instance --tsa 29
   femic tsr source-layers-build --instance-root external/femic-tsa29-instance
   femic tsr source-layers-run --instance-root external/femic-tsa29-instance --bbox ...
   femic tsr thlb-netdown-build --instance-root external/femic-tsa29-instance
   femic tsr thlb-netdown-workbench-build --instance-root external/femic-tsa29-instance
   femic tsr thlb-netdown-run --instance-root external/femic-tsa29-instance
   femic tsr thlb-netdown-workbench-lock --instance-root external/femic-tsa29-instance
   femic tsr overlay-init --instance-root external/femic-tsa29-instance --tsa 29
   femic tsr overlay-report --instance-root external/femic-tsa29-instance
   femic tsr override-init --instance-root external/femic-tsa29-instance
   femic tsr override-report --instance-root external/femic-tsa29-instance

Important instance-local THLB artifacts in this lane include:

- ``config/tsr/thlb_netdown.recipe.yaml``
- ``workbench/tsr/thlb_netdown.workbench.ipynb``
- ``workbench/tsr/thlb_netdown.locked.py``

The matching Python entrypoints are:

.. code-block:: python

   from pathlib import Path
   from femic.tsr_catalog import (
      build_tsr_thlb_netdown_recipe,
      build_tsr_overlay_report,
      build_tsr_source_layers_recipe,
      build_tsr_thlb_workbench,
      extract_tsr_candidate_facts,
      fetch_tsr_pdfs,
      init_tsr_overlay,
      init_tsr_recipe_scaffolds,
      init_tsr_source_layer_overrides,
      index_tsr_tsa_surfaces,
      lock_tsr_thlb_workbench,
      report_tsr_candidate_facts,
      build_tsr_source_layer_override_report,
      run_tsr_source_layers_recipe,
      write_tsr_fact_report_csv,
      write_tsr_index,
   )

   result = index_tsr_tsa_surfaces()
   write_tsr_index(result, Path("metadata/tsr"))
   fetch_tsr_pdfs(
       documents_path=Path("metadata/tsr/tsa_documents.json"),
       corpus_root=Path.home() / ".femic" / "tsr" / "corpus",
       manifest_path=Path.home() / ".femic" / "tsr" / "tsa_pdf_cache_manifest.json",
   )
   extract_tsr_candidate_facts(
       documents_path=Path("metadata/tsr/tsa_documents.json"),
       corpus_root=Path.home() / ".femic" / "tsr" / "corpus",
       output_path=Path("metadata/tsr/tsa_candidate_facts.json"),
   )
   report = report_tsr_candidate_facts(
       candidate_facts_path=Path("metadata/tsr/tsa_candidate_facts.json"),
       tsa="29",
       fact_families=("source_layer_candidate",),
   )
   write_tsr_fact_report_csv(
       report,
       path=Path("runtime/logs/tsa29_tsr_source_layers_review.csv"),
   )
   init_tsr_overlay(
       instance_root=Path("external/femic-tsa29-instance"),
       overlay_path=Path("external/femic-tsa29-instance/config/tsr/overlay.yaml"),
       tsa="29",
       registry_path=Path("metadata/tsr/tsa_registry.json"),
       documents_path=Path("metadata/tsr/tsa_documents.json"),
       candidate_facts_path=Path("metadata/tsr/tsa_candidate_facts.json"),
       source_root=Path.cwd(),
   )
   init_tsr_recipe_scaffolds(
       instance_root=Path("external/femic-tsa29-instance"),
       tsa="29",
       registry_path=Path("metadata/tsr/tsa_registry.json"),
       documents_path=Path("metadata/tsr/tsa_documents.json"),
       candidate_facts_path=Path("metadata/tsr/tsa_candidate_facts.json"),
       source_root=Path.cwd(),
       overlay_path=Path("external/femic-tsa29-instance/config/tsr/overlay.yaml"),
       overrides_path=Path(
           "external/femic-tsa29-instance/config/tsr/source_layer_overrides.yaml"
       ),
       source_layers_recipe_path=Path(
           "external/femic-tsa29-instance/config/tsr/source_layers.recipe.yaml"
       ),
       thlb_netdown_recipe_path=Path(
           "external/femic-tsa29-instance/config/tsr/thlb_netdown.recipe.yaml"
       ),
   )
   build_tsr_source_layers_recipe(
       recipe_path=Path(
           "external/femic-tsa29-instance/config/tsr/source_layers.recipe.yaml"
       ),
       source_root=Path.cwd(),
   )
   run_tsr_source_layers_recipe(
       recipe_path=Path(
           "external/femic-tsa29-instance/config/tsr/source_layers.recipe.yaml"
       ),
       bbox_epsg3005=(1170000.0, 450000.0, 1180000.0, 460000.0),
   )
   build_tsr_thlb_netdown_recipe(
       recipe_path=Path(
           "external/femic-tsa29-instance/config/tsr/thlb_netdown.recipe.yaml"
       ),
       source_root=Path.cwd(),
   )
   run_tsr_thlb_netdown_recipe(
       recipe_path=Path(
           "external/femic-tsa29-instance/config/tsr/thlb_netdown.recipe.yaml"
       ),
   )
   build_tsr_overlay_report(
       overlay_path=Path("external/femic-tsa29-instance/config/tsr/overlay.yaml"),
   )
   init_tsr_source_layer_overrides(
       instance_root=Path("external/femic-tsa29-instance"),
       overlay_path=Path("external/femic-tsa29-instance/config/tsr/overlay.yaml"),
       overrides_path=Path(
           "external/femic-tsa29-instance/config/tsr/source_layer_overrides.yaml"
       ),
   )
   build_tsr_source_layer_override_report(
       overlay_path=Path("external/femic-tsa29-instance/config/tsr/overlay.yaml"),
       overrides_path=Path(
           "external/femic-tsa29-instance/config/tsr/source_layer_overrides.yaml"
       ),
   )

Key Entry Surfaces
------------------

- :func:`index_tsr_tsa_surfaces`
  Crawl the public TSR TSA surfaces and build the canonical in-memory index.
- :func:`write_tsr_index`
  Persist the canonical registry and document inventory JSON artifacts.
- :func:`fetch_tsr_pdfs`
  Download/cache indexed TSR PDFs into a configurable corpus root and write a
  provenance manifest with corpus-relative paths, stable user-local path
  placeholders, and checksums.
- :func:`extract_tsr_candidate_facts`
  Parse cached TSR PDFs into reviewable candidate facts with page/snippet
  provenance for later human or agent adoption.
- :func:`report_tsr_candidate_facts`
  Shape canonical candidate facts into review-friendly rows with lightweight
  quality heuristics for operator review.
- :func:`init_tsr_overlay`
  Initialize the reviewed/adopted instance-local TSR overlay YAML without
  auto-adopting candidate facts.
- :func:`init_tsr_recipe_scaffolds`
  Initialize the reviewed working recipe YAML files that later source-layer
  and THLB recipe build/run slices will own.
- :func:`build_tsr_source_layers_recipe`
  Refresh the reviewed source-layer recipe from TSR facts plus current public
  BCDC resolution metadata.
- :func:`run_tsr_source_layers_recipe`
  Execute safe acquisition steps from the reviewed source-layer recipe while
  reusing already materialized artifacts when available.
- :func:`build_tsr_thlb_netdown_recipe`
  Refresh the reviewed THLB netdown recipe from TSR THLB facts plus the stable
  logical-source ids already captured in the source-layer recipe, while also
  classifying rows into the GLB/AFLB/LHLB/THLB backbone instead of leaving
  every row in one flat semantic bucket.
- :func:`run_tsr_thlb_netdown_recipe`
  Execute the bounded supported subset of the reviewed THLB recipe into a
  stand-level checkpoint carrying ``thlb_fact`` plus a structured audit JSON.
- :func:`build_tsr_overlay_report`
  Summarize one reviewed overlay against the canonical candidate-fact pool it
  references.
- :func:`init_tsr_source_layer_overrides`
  Initialize a reviewed instance-local source-layer override YAML from the
  unresolved rows already captured in the TSR overlay.
- :func:`build_tsr_source_layer_override_report`
  Summarize how many unresolved overlay rows have reviewed escape hatches
  recorded locally.

The override layer can now also carry review-only
``replacement_family_candidates`` for selected stale wildlife/netdown tokens.
These are bounded public shortlists meant to help human review move the wall;
they are not treated as exact replacements or auto-fetch targets.

Current THLB Execution Boundary
-------------------------------

The THLB execution helper shipped in issue ``#126`` is intentionally a
reproducible **hybrid bridge**, not yet the full raw-land-base reconstruction
engine:

- it starts from the existing checkpoint THLB signal when building
  ``thlb_fact``;
- it applies the bounded supported reviewed exclusions on top of that
  baseline; and
- it keeps unsupported or blocked clauses explicit in the audit output.

The promoted next target, tracked in issue ``#128``, is to rebuild THLB from
the raw/resultant land base itself by overlaying the reviewed exclusion layers,
fragmenting the geometry, and assigning binary fragment-level THLB membership
``{0,1}``.

The current recipe/review improvement lane under ``#128`` also teaches FEMIC
the explicit land-base ladder:

- ``GLB -> AFLB``
- ``AFLB -> LHLB``
- ``LHLB -> THLB``

That staged schema is what lets later execution and fallback slices tell the
difference between universe definition, legal exclusions, projected
operational deductions, benchmark targets, and pure context.

Cross-References
----------------

- :doc:`../cli`
- :doc:`../../guides/tsr-intelligence-workflow`
- :doc:`../../guides/data-access-inventory`

.. toctree::
   :hidden:

   generated/femic.tsr_catalog

.. automodule:: femic.tsr_catalog
   :members:
   :undoc-members:
   :show-inheritance:
   :noindex:
