``femic.pdf_metadata_summary`` Module
====================================

The :mod:`femic.pdf_metadata_summary` module produces deterministic,
machine-searchable JSON metadata summaries for one cached PDF per run. The
summary combines document-level metadata (title, author, page count,
SHA-256, source URL, fetch timestamp) with figrecover-aware figure
candidates and per-page text snippets so downstream automation can search,
filter, and cross-reference TSR PDFs without assembling a full document-
figure corpus first.

Responsibilities
----------------

- Compute SHA-256 checksums, byte sizes, and timestamps for cached PDFs.
- Coalesce PyMuPDF and pypdf document metadata into a single canonical set
  with ``schema_version = 1``.
- Render selected PDF pages through ``figrecover.documents.render_pdf_pages``
  and detect PyMuPDF image-block figure candidates through
  ``figrecover.adapters.extract_pymupdf_image_candidates`` (when the
  optional stack is available).
- Capture per-page text snippets suitable for planning and content
  cross-referencing.
- Cross-reference FAMIC's TSA inventory (TSA code, name, cycle label,
  document type, inventory-relative path) when supplied.
- Resolve provenance for ``figrecover``, ``pymupdf``, ``pypdf``, and the
  originating FEMIC command label.

The helper intentionally mirrors the pattern used by ``femic.document_figures``:
``figrecover`` is loaded lazily, the helper falls back gracefully when
optional extras are missing, and rendered pages stay under ignored runtime
paths while the JSON summary itself remains small.

Optional chart-digitisation sections
------------------------------------

The PDF metadata summary is the canonical landing place for two optional
sections that appear once a chart-digitisation pipeline has run on the
extracted figures:

- ``figure_datasets`` records every figrecover image-block plus its logical
  figure mapping, dataset path / SHA-256, calibrated-extraction counts,
  curated-row counts, and rendered-crop paths / checksums.
- ``tsr_facts`` captures structured numeric TSR-specific figures (current
  vs proposed AAC, AFLB / THLB area declarations, harvest-schedule
  shelves, sensitivity-analysis rows, growth/yield assumptions) with
  per-fact page citations and verbatim quotes from the document body.
- ``ws3_links`` is the read-only cross-reference between TSR-published
  facts and the actual Patchworks strata / tracks inventory that a
  FEMIC TSA instance already ships; the section carries
  ``modifies_model_inventory = False`` plus an
  ``inventory_index`` listing every AU code recognised by the model.

The Williams Lake TSA 2026 PDP shipped under
``external/femic-tsa29-instance/reference/tsa/tsa_29/TSR_2026/Public_Discussion_Paper/``
is the production end-to-end example: see
``scripts/tsa29/digitise_tsr_2026_pdp_figures.py`` and
``external/femic-tsa29-instance/evidence/TSR_2026_pdp_extraction_decisions.md``
for the dataset inventory, skip rules, and regression-test pointers.

API
---

.. automodule:: femic.pdf_metadata_summary
   :members:
   :undoc-members:
   :show-inheritance:
