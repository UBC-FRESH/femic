TSR Intelligence Workflow
=========================

Purpose
-------

Use the ``femic tsr`` workflow when you want to turn public BC Timber Supply
Review document surfaces into three separate layers of knowledge:

1. canonical repo-tracked TSR discovery artifacts under ``metadata/tsr``;
2. user-local cached PDFs under ``~/.femic/tsr/corpus`` by default; and
3. reviewed/adopted instance-local notes under ``config/tsr/overlay.yaml``.
4. reviewed instance-local source-layer escape hatches under
   ``config/tsr/source_layer_overrides.yaml`` when the public catalogue cannot
   finish the job safely.

This guide is intentionally about workflow and promotion discipline. It does
**not** make FEMIC auto-adopt extracted candidate facts into a live instance.

Canonical vs Local Outputs
--------------------------

The TSR intelligence lane separates shared discovery artifacts from
instance-local reviewed metadata.

Canonical repo-tracked outputs:

- ``metadata/tsr/tsa_registry.json``
- ``metadata/tsr/tsa_documents.json``
- ``metadata/tsr/tsa_candidate_facts.json``

User-local cache outputs by default:

- ``~/.femic/tsr/corpus``
- ``~/.femic/tsr/tsa_pdf_cache_manifest.json``

Instance-local reviewed overlay:

- ``config/tsr/overlay.yaml``
- ``config/tsr/source_layer_overrides.yaml`` (when explicit source-layer
  overrides are needed)

Treat the canonical JSON artifacts as the shared discovery surface, and treat
the overlay YAML as the reviewed/adopted per-instance surface.

Minimal One-TSA Workflow
------------------------

Refresh the canonical TSA registry and document inventory:

.. code-block:: bash

   python -m femic tsr index

Fetch only the TSA you are actively working on. For example, TSA 29:

.. code-block:: bash

   python -m femic tsr fetch --tsa 29

Extract candidate facts only for that TSA:

.. code-block:: bash

   python -m femic tsr extract --tsa 29

Initialize the reviewed overlay inside the target instance:

.. code-block:: bash

   python -m femic tsr overlay-init \
     --instance-root external/femic-tsa29-instance \
     --tsa 29

Inspect the local adopted-vs-canonical state:

.. code-block:: bash

   python -m femic tsr overlay-report \
     --instance-root external/femic-tsa29-instance

This is the recommended default path for most users. Few workflows need a
full-corpus fetch or extraction run across every indexed TSA.

Reviewed Adoption Workflow
--------------------------

``femic tsr extract`` writes candidate facts, not final truth. The expected
promotion path is:

1. run ``femic tsr extract`` for the target TSA;
2. inspect the relevant candidate facts in
   ``metadata/tsr/tsa_candidate_facts.json``;
3. initialize ``config/tsr/overlay.yaml`` for the target instance;
4. copy only reviewed/adopted facts into the overlay YAML, preserving
   provenance back to the source document/page/snippet IDs;
5. use ``femic tsr overlay-report`` to confirm what remains canonical-only vs
   what is now adopted locally.
6. when the public BCDC lane hits a real wall, initialize
   ``config/tsr/source_layer_overrides.yaml`` and record reviewed local/URL/
   mirror/replacement/unavailable decisions there instead of rediscovering
   them repeatedly.

Candidate facts are **not auto-adopted** into the overlay. In other words,
candidate facts are **not auto-adopted** into live instance truth, and the
overlay is the only place where reviewed instance-local TSR interpretation
should live.

Worked Example: TSA29 Source Layers and THLB
--------------------------------------------

The cleanest current end-to-end use case is TSA29 netdown/source-layer review.

1. refresh the canonical TSR surfaces:

   .. code-block:: bash

      python -m femic tsr index
      python -m femic tsr fetch --tsa 29
      python -m femic tsr extract --tsa 29

2. render a review CSV for source-layer candidates:

   .. code-block:: bash

      python -m femic tsr facts-report \
        --tsa 29 \
        --fact-family source_layer_candidate \
        --output-csv runtime/logs/tsa29_tsr_source_layers_review.csv

3. render a separate THLB review CSV:

   .. code-block:: bash

      python -m femic tsr facts-report \
        --tsa 29 \
        --fact-family thlb_reference \
        --output-csv runtime/logs/tsa29_tsr_thlb_review.csv

4. review the CSVs:

   - reject rows marked ``likely_noise``;
   - keep rows marked ``likely_useful``;
   - inspect ``needs_review`` rows manually using the snippet, page number,
     title, and provenance ID columns.
   - copy the approved ``recommended_query`` values into
     ``runtime/logs/tsa29_tsr_source_layers.txt`` so the next BCDC step uses a
     clean query file instead of raw JSON.

5. turn the approved source-layer queries into BCDC follow-on resolution:

   .. code-block:: bash

      python -m femic data bcdc-resolve \
        --query-file runtime/logs/tsa29_tsr_source_layers.txt \
        --summary-csv runtime/logs/tsa29_tsr_source_layers_summary.csv \
        --manifest-path runtime/logs/tsa29_tsr_source_layers_manifest.json

6. for WFS-queryable rows such as ``WHSE_FOREST_VEGETATION.F_OWN``, fetch a
   usable local subset instead of stopping at the manifest:

   .. code-block:: bash

      python -m femic data bcdc-fetch \
        WHSE_FOREST_VEGETATION.F_OWN \
        --bbox 1170000,450000,1180000,460000 \
        --output-format gpkg \
        --download-root data/downloads/bcdc \
        --manifest-path runtime/logs/tsa29_f_own_fetch_manifest.json

   For direct-download-only rows such as ``SITE_PROD_BC``, stay on the
   ``femic data bcdc-resolve --download-direct`` path instead of forcing
   ``bcdc-fetch``.

7. initialize or refresh the reviewed overlay:

   .. code-block:: bash

      python -m femic tsr overlay-init \
        --instance-root external/femic-tsa29-instance \
        --tsa 29 \
        --overwrite

8. manually copy only approved facts into:

   - ``external/femic-tsa29-instance/config/tsr/overlay.yaml``
   - ``external/femic-tsa29-instance/config/tsr/source_layer_overrides.yaml``
     for unresolved public-catalogue rows that need a reviewed escape hatch

The current intended human loop is:

- review CSV
- reject noise
- keep good candidates
- curate approved ``recommended_query`` values into a query file
- resolve source layers through BCDC
- fetch WFS-queryable reviewed layers through ``femic data bcdc-fetch`` where
  that is the cleanest path
- adopt only reviewed facts into the overlay
- record any remaining wall cases in ``source_layer_overrides.yaml`` rather
  than hoping the same public query will behave differently later

You should not need to hand-scrub ``metadata/tsr/tsa_candidate_facts.json`` for
this workflow. The intended review surface is the CSV produced by
``femic tsr facts-report``.

When the wall is real rather than accidental, initialize the reviewed
source-layer override file:

.. code-block:: bash

   python -m femic tsr override-init \
     --instance-root external/femic-tsa29-instance

Then inspect current coverage:

.. code-block:: bash

   python -m femic tsr override-report \
     --instance-root external/femic-tsa29-instance

The override file is where you can record reviewed escape hatches such as:

- ``local_path`` to a local copy you obtained outside FEMIC;
- ``dataset_url`` for a bespoke download seam;
- ``datalad_path`` for a FEMIC/DataLad-managed mirror;
- ``replacement_layer`` for a reviewed current public substitute; or
- ``private`` / ``unavailable`` when the wall is real and should stop repeated
  public inference attempts.

Windows PowerShell Notes
------------------------

On Windows, prefer:

- one command per line or a saved script file;
- query files instead of giant interactive pastes; and
- CSV outputs for review instead of trying to inspect raw JSON in the shell.

If interactive PowerShell pastes keep breaking, the friendliest path is
usually:

1. run the ``femic tsr facts-report`` command once;
2. open the review CSV in VS Code or Excel;
3. curate approved layer names into a query file; and
4. pass that query file to ``femic data bcdc-resolve``.

If you already know you need a WFS-backed layer like ``F_OWN``, the next
Windows-friendly step is still file-based and explicit:

1. keep the approved layer token in a query file or single command;
2. use ``--bbox`` or ``--geomark`` rather than pasting large AOI definitions;
3. write a manifest and local file output in one shot with
   ``femic data bcdc-fetch``.

Using Extracted Source Layers with BCDC Discovery
-------------------------------------------------

One important use of TSR candidate facts is to drive the existing BC Data
Catalogue resolver.

Typical pattern:

1. find source-layer candidates in ``metadata/tsr/tsa_candidate_facts.json``;
2. copy the promising BCGW/BCDC-style layer tokens into a query file;
3. resolve them with ``femic data bcdc-resolve``.

Example follow-on command:

.. code-block:: bash

   python -m femic data bcdc-resolve \
     --query-file runtime/logs/tsa29_tsr_source_layers.txt \
     --summary-csv runtime/logs/tsa29_tsr_source_layers_summary.csv \
     --manifest-path runtime/logs/tsa29_tsr_source_layers_manifest.json

Example WFS fetch after reviewing the BCDC manifest:

.. code-block:: bash

   python -m femic data bcdc-fetch \
     WHSE_FOREST_VEGETATION.F_OWN \
     --bbox 1170000,450000,1180000,460000 \
     --output-format gpkg \
     --manifest-path runtime/logs/tsa29_f_own_fetch_manifest.json

This keeps TSR extraction and BCDC promotion loosely coupled:

- TSR docs produce candidate tokens and provenance; then
- BCDC discovery resolves which of those tokens correspond to public catalogue
  packages and direct-download/custom-download seams; and then
- the new WFS-first fetch path can pull usable local vector subsets for the
  reviewed rows that expose queryable OpenMaps services.

Agent Workflow Notes
--------------------

For coding agents and maintainers, the key boundary is:

- canonical JSON under ``metadata/tsr`` is safe to regenerate and compare; but
- ``config/tsr/overlay.yaml`` is reviewed instance-local metadata and should
  not be overwritten casually.

When helping a user with one TSA at a time:

- prefer ``--tsa <code>`` for ``fetch`` and ``extract``;
- prefer the default user-local corpus root instead of inventing a repo-local
  PDF cache;
- prefer promoting only reviewed facts into the overlay rather than editing
  other instance contracts directly.

Current Boundaries
------------------

The current TSR intelligence workflow is intentionally bounded:

- TSAs only in v1
- no automatic promotion into ``metadata/required_datasets.yaml``
- no automatic mutation of rebuild specs
- no arbitrary full-document semantic search workflow embedded in FEMIC
- no OCR-heavy recovery path for image-only PDFs

If you need deeper interpretation, use the canonical JSON artifacts and cached
PDF corpus as the structured substrate for additional human or LLM-assisted
review.

Related References
------------------

- :doc:`bc-data-catalogue-discovery`
- :doc:`data-access-inventory`
- :doc:`../reference/cli`
- :doc:`../reference/api/femic-tsr-catalog`
