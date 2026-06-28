``femic.document_figures`` Module
=================================

The :mod:`femic.document_figures` module owns FEMIC-side artifact and
provenance conventions for optional document-figure recovery workflows.

It intentionally does not import ``figrecover``. This keeps the normal FEMIC
runtime independent of optional PDF, computer-vision, and VLM dependencies.

Responsibilities
----------------

- resolve the ignored ``runtime/document_ingestion/<corpus_id>/`` layout;
- create document-ingestion artifact directories;
- compute SHA256 checksums for source, crop, and recovered-table artifacts;
- validate provenance records before recovered values can be referenced;
- encode review-status and downstream-use vocabularies; and
- write JSON sidecars and JSONL review manifests.

Review Gate
-----------

Reviewed or accepted statuses require reviewer and timestamp provenance. This
prevents raw recovered values from silently entering planning or model-input
contracts.

API
---

.. automodule:: femic.document_figures
   :members:
   :undoc-members:
   :show-inheritance:
