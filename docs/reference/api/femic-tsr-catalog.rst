``femic.tsr_catalog`` Module
============================

The :mod:`femic.tsr_catalog` module owns FEMIC's first BC Timber Supply Review
intelligence slice. It crawls the public TSA-oriented TSR document surfaces,
normalizes TSA/cycle/document metadata, writes the canonical JSON registry
artifacts under ``metadata/tsr``, and fetches/caches TSR PDFs into a
configurable corpus root with provenance manifests.

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
  a later DataLad-managed corpus split.

Typical Usage
-------------

The common operator-facing entrypoint is:

.. code-block:: bash

   femic tsr index
   femic tsr fetch

The matching Python entrypoints are:

.. code-block:: python

   from pathlib import Path
   from femic.tsr_catalog import fetch_tsr_pdfs, index_tsr_tsa_surfaces, write_tsr_index

   result = index_tsr_tsa_surfaces()
   write_tsr_index(result, Path("metadata/tsr"))
   fetch_tsr_pdfs(
       documents_path=Path("metadata/tsr/tsa_documents.json"),
       corpus_root=Path.home() / ".femic" / "tsr" / "corpus",
       manifest_path=Path.home() / ".femic" / "tsr" / "tsa_pdf_cache_manifest.json",
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
