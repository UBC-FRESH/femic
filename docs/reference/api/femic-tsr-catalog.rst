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
``config/tsr/overlay.yaml`` without auto-promoting unresolved candidate facts.

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
   femic tsr overlay-init --instance-root external/femic-tsa29-instance --tsa 29
   femic tsr overlay-report --instance-root external/femic-tsa29-instance

The matching Python entrypoints are:

.. code-block:: python

   from pathlib import Path
   from femic.tsr_catalog import (
       build_tsr_overlay_report,
       extract_tsr_candidate_facts,
       fetch_tsr_pdfs,
       init_tsr_overlay,
       index_tsr_tsa_surfaces,
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
   init_tsr_overlay(
       instance_root=Path("external/femic-tsa29-instance"),
       overlay_path=Path("external/femic-tsa29-instance/config/tsr/overlay.yaml"),
       tsa="29",
       registry_path=Path("metadata/tsr/tsa_registry.json"),
       documents_path=Path("metadata/tsr/tsa_documents.json"),
       candidate_facts_path=Path("metadata/tsr/tsa_candidate_facts.json"),
       source_root=Path.cwd(),
   )
   build_tsr_overlay_report(
       overlay_path=Path("external/femic-tsa29-instance/config/tsr/overlay.yaml"),
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
- :func:`init_tsr_overlay`
  Initialize the reviewed/adopted instance-local TSR overlay YAML without
  auto-adopting candidate facts.
- :func:`build_tsr_overlay_report`
  Summarize one reviewed overlay against the canonical candidate-fact pool it
  references.

Cross-References
----------------

- :doc:`../cli`
- :doc:`../../guides/data-access-inventory`

.. toctree::
   :hidden:

   generated/femic.tsr_catalog

.. automodule:: femic.tsr_catalog
   :members:
   :undoc-members:
   :show-inheritance:
   :noindex:
