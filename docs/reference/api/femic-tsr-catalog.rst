``femic.tsr_catalog`` Module
============================

The :mod:`femic.tsr_catalog` module owns FEMIC's first BC Timber Supply Review
intelligence slice. It crawls the public TSA-oriented TSR document surfaces,
normalizes TSA/cycle/document metadata, and writes the canonical JSON registry
artifacts under ``metadata/tsr``.

Use this page when you are debugging the TSR indexing logic itself rather than
the higher-level CLI surface.

Start Here If...
----------------

Use this page first if you are trying to:

- understand how FEMIC crawls the BC TSR landing surface and TSA publish tree;
- inspect how TSA identity, cycle labels, and document types are normalized; or
- debug the canonical JSON outputs written to ``metadata/tsr``.

Typical Usage
-------------

The common operator-facing entrypoint is:

.. code-block:: bash

   femic tsr index

The matching Python entrypoints are:

.. code-block:: python

   from pathlib import Path
   from femic.tsr_catalog import index_tsr_tsa_surfaces, write_tsr_index

   result = index_tsr_tsa_surfaces()
   write_tsr_index(result, Path("metadata/tsr"))

Key Entry Surfaces
------------------

- :func:`index_tsr_tsa_surfaces`
  Crawl the public TSR TSA surfaces and build the canonical in-memory index.
- :func:`write_tsr_index`
  Persist the canonical registry and document inventory JSON artifacts.

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
