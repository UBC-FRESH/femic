Document Figure Recovery
========================

FEMIC can wrap the UBC-FRESH ``figrecover`` package for document-ingestion
workflows where published figures contain useful evidence but the source data
tables were not released.

This workflow is optional. Normal FEMIC installation, THLB reconstruction,
VDYP, TIPSY, BatchTIPSY, Patchworks, and instance-scaffold workflows do not
require ``figrecover``.

Install
-------

Install figrecover from its source repository only on workstations that will
prepare or review document figures:

.. code-block:: bash

   python -m pip install "figrecover[pdf,cv,vlm] @ git+https://github.com/UBC-FRESH/figrecover.git@v0.1.0a1"

The ``femic[figures]`` extra is retained as a PyPI-safe compatibility marker,
but it does not install figrecover while figrecover has no PyPI distribution.

Then verify the optional stack:

.. code-block:: bash

   femic doc figures preflight

The preflight command reports whether ``figrecover`` plus its PDF/image
dependencies are importable. It does not download or process documents.

Corpus Layout
-------------

FEMIC writes generated document-ingestion artifacts under ignored runtime
paths:

.. code-block:: text

   runtime/document_ingestion/<corpus_id>/
     source_manifest.yaml
     pages/
     figure_candidates.csv
     crops/
     calibration/
     recovered/
     overlays/
     review_manifest.jsonl
     accepted/

Rendered pages, crops, overlays, prompt logs, raw recovered tables, and review
bundles should stay under ignored runtime paths unless a maintainer explicitly
approves a sanitized public artifact.

Prepare A Corpus
----------------

Use ``prepare-corpus`` to initialize the corpus layout and render selected
public PDF pages through ``figrecover``:

.. code-block:: bash

   femic doc figures prepare-corpus tfl6-mp11-pilot \
     --pdf /path/to/TFL6_MP_11_202606_w_Appendices_Web-compressed.pdf \
     --pages 82-86,91,98-100,103,116,123 \
     --dpi 150 \
     --output-root runtime/document_ingestion/tfl6-mp11-pilot

The command writes ``source_manifest.yaml`` with source checksums, render
metadata, and artifact paths. If supplied with a figrecover JSONL figure
manifest, it also writes a compact ``figure_candidates.csv`` summary for FEMIC
planning and review.

Register A Recovered Table
--------------------------

FEMIC does not treat recovered values as accepted model inputs by default.
After a user has recovered and reviewed a table, register the table with
explicit provenance:

.. code-block:: bash

   femic doc figures register-table tfl6-mp11-pilot recovered.csv \
     --document-title "TFL 6 Management Plan 11" \
     --page 82 \
     --figure-id "Figure 2" \
     --series-name "base case" \
     --visual-selection-rule "blue harvest-flow line" \
     --calibration-spec calibration/figure-2.json \
     --extraction-method deterministic_line_mask \
     --extraction-parameters recovered/figure-2-params.json \
     --source-url https://www.westernforest.com/wp-content/uploads/2026/06/TFL6_MP_11_202606_w_Appendices_Web-compressed.pdf \
     --review-status accepted_for_comparison \
     --downstream-use comparison_evidence \
     --reviewer "Reviewer Name" \
     --output-root runtime/document_ingestion/tfl6-mp11-pilot

The command appends a JSONL record to ``review_manifest.jsonl`` and writes a
formatted JSON sidecar under ``recovered/``. It computes checksums for the
registered table and, when supplied, local source and crop artifacts.

Review Gates
------------

FEMIC review statuses are deliberately conservative:

- ``raw_extraction``
- ``needs_calibration_review``
- ``needs_value_review``
- ``reviewed_for_planning``
- ``accepted_for_comparison``
- ``accepted_for_model_input``
- ``rejected``
- ``superseded``

Reviewed or accepted statuses require a reviewer and review timestamp. Raw
figure-recovery outputs cannot silently become accepted model inputs.

TFL 6 MP11 Pilot
----------------

The first pilot manifest is tracked as public-safe planning material:

- ``planning/phase78_tfl6_mp11_pilot_notes.md``
- ``planning/phase78_tfl6_mp11_pilot_figure_manifest.csv``

The pilot aligns with the TFL 6 instance Phase 6 issue tree:

- ``UBC-FRESH/femic-tfl6-instance#42``
- ``UBC-FRESH/femic-tfl6-instance#43``
- ``UBC-FRESH/femic-tfl6-instance#44``

The pilot manifest is not a recovered data product. It only records selected
figure candidates, page anchors, chart families, recovery objectives, and
review expectations.
