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
5. reviewed instance-local working recipe scaffolds under:
   - ``config/tsr/source_layers.recipe.yaml``
   - ``config/tsr/thlb_netdown.recipe.yaml``
   - ``config/tsr/thlb_netdown.audit.json``
   - ``data/tsr/thlb_netdown_checkpoint.feather``

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
- ``config/tsr/source_layers.recipe.yaml``
- ``config/tsr/thlb_netdown.recipe.yaml``
- ``config/tsr/thlb_netdown.audit.json``
- ``data/tsr/thlb_netdown_checkpoint.feather``

Treat the canonical JSON artifacts as the shared discovery surface, and treat
the overlay YAML plus recipe YAMLs as the reviewed/adopted per-instance
surface.

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

Initialize the reviewed recipe scaffolds and overlay inside the target
instance:

.. code-block:: bash

   python -m femic tsr recipe-init \
     --instance-root external/femic-tsa29-instance \
     --tsa 29

   python -m femic tsr source-layers-build \
     --instance-root external/femic-tsa29-instance

   python -m femic tsr thlb-netdown-build \
     --instance-root external/femic-tsa29-instance

   python -m femic tsr thlb-netdown-workbench-build \
     --instance-root external/femic-tsa29-instance

   python -m femic tsr thlb-netdown-run \
     --instance-root external/femic-tsa29-instance

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

For the deeper conceptual contract behind the ladder itself, including
hybrid-vs-reconstructed semantics, the raw-GLB reconstructed start contract,
and benchmark comparison rules, see
:doc:`tsr-thlb-reconstruction-ladder`.

For THLB reporting specifically, the governing accounting rule is now:

- stepwise marginal deduction means **true net active-area change at that
  step**;
- milestone rows are cumulative checkpoints, not deductions; and
- gross matched/candidate/touched areas are diagnostics only, not the primary
  reconciliation numbers.

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

6a. once the reviewed source-layer recipe exists, you can rerun the same
   acquisition story through the instance-local recipe surface instead of
   rebuilding the logic manually:

   .. code-block:: bash

      python -m femic tsr source-layers-build \
        --instance-root external/femic-tsa29-instance

      python -m femic tsr source-layers-run \
        --instance-root external/femic-tsa29-instance \
        --bbox 1015173.8086,653963.4944,1393139.0550,901924.5102

   The build step refreshes ``config/tsr/source_layers.recipe.yaml`` from:

   - TSR source-layer candidate facts;
   - current BCDC public-resolution metadata; and
   - reviewed override context from
     ``config/tsr/source_layer_overrides.yaml`` when present.

   The run step then executes only the safe acquisition paths already trusted
   elsewhere in FEMIC and writes the resulting artifact paths back into the
   recipe.

6b. once the source-layer recipe is in a good state, build the reviewed THLB
   netdown recipe:

   .. code-block:: bash

      python -m femic tsr thlb-netdown-build \
        --instance-root external/femic-tsa29-instance

   This refreshes ``config/tsr/thlb_netdown.recipe.yaml`` from the canonical
   ``thlb_reference`` fact pool while preserving:

   - raw TSR wording and provenance;
   - explicit land-base stage semantics:
     - ``glb_to_aflb``
     - ``aflb_to_lhlb``
     - ``lhlb_to_thlb``
     - ``reference_target``
     - ``context``
   - normalized action hints such as ``exclude``, ``defer``,
     ``aspatial_reduction``, and ``reference_target`` when the builder is
     confident enough;
   - linked source-layer recipe entry ids when the THLB text can be connected
     conservatively to a logical source; and
   - explicit ``ready`` / ``needs_review`` / ``blocked_missing_source`` step
     status so the later execution slice has a stable contract to work from.

   The THLB recipe build step is intentionally about extracting
   **what the TSR says to do**, not applying the netdown yet.

The current goal is no longer a flat wall of THLB snippets. FEMIC now
treats the TSA land-base ladder itself as the organizing grammar:

When comparing the strict reconstructed lane to the accepted reviewed TSA29
lane, keep the benchmark order straight:

- primary benchmark: strict reconstructed vs TSR;
- secondary context: strict reconstructed vs reviewed; and
- practical interpretation: reviewed was accepted because cumulative THLB was
  close enough for exploratory use, not because every reviewed step is
  automatically the gold standard for strict reconstruction.

   - ``Gross Land Base (GLB) -> Analysis Forest Land Base (AFLB)``
   - ``AFLB -> Legally Harvestable Land Base (LHLB)``
   - ``LHLB -> Timber Harvesting Land Base (THLB)``

   That staged backbone is the guardrail that helps the recipe stop confusing
   headings, context, benchmark rows, legal exclusions, and projected
   operational deductions.

6c. execute the bounded supported subset of the THLB recipe into a stand-level
   checkpoint:

   .. code-block:: bash

      python -m femic tsr thlb-netdown-run \
        --instance-root external/femic-tsa29-instance

   This writes:

   - ``config/tsr/thlb_netdown.audit.json``
   - ``config/tsr/thlb_netdown.status.md``
   - ``data/tsr/thlb_netdown_checkpoint.feather``
   - a versioned Markdown history copy under ``runtime/logs/tsr/``

   The output checkpoint carries ``thlb_fact`` for downstream export logic.
   The audit JSON records which THLB recipe steps were:

   - ``applied``;
   - ``applied_noop``;
   - ``unsupported``; or
   - ``blocked_missing_source``.

   This keeps the run convergent and reproducible: supported steps move the
   instance forward, and unsupported steps remain explicit instead of forcing
   the user to rediscover what FEMIC did or did not apply.

   The status report Markdown is the user-facing convergence surface for this
   lane. It records, for each run:

   - a backbone summary for GLB/AFLB/LHLB/THLB;
   - input checkpoint area;
   - AFLB / baseline managed area;
   - final THLB area;
   - the current executable ratios (currently a GLB/AFLB proxy plus
     ``AFLB:THLB``);
   - TSR benchmark AFLB and THLB values when FEMIC can parse them from the
     selected TSR data package; and
   - stage-grouped step ledgers for:
     - ``GLB -> AFLB``
     - ``AFLB -> LHLB``
     - ``LHLB -> THLB``
     - ``Reference targets``
     - ``Context / interpretation``
   - a stable latest report plus a timestamped runtime-history copy so users
     and helper agents can compare successive runs while the recipe converges.

   Important current boundary:

   - this is the **hybrid THLB bridge** landed in issue ``#126``;
   - FEMIC currently seeds ``thlb_fact`` from the existing checkpoint THLB
     signal (``thlb_fact`` -> ``thlb_raw`` -> ``thlb_area`` -> ``thlb``) and
     then applies the supported reviewed TSR exclusions on top;
   - that is internally consistent and reproducible, but it is **not** yet the
     full production-grade reconstruction target.

   The promoted next target is issue ``#128``:

   - start from the raw/resultant VRI land base;
   - overlay the reviewed exclusion layers and fragment the geometry; and
   - assign binary fragment-level THLB membership ``{0,1}`` the way BC
     analysts commonly do when building a resultant/fragments surface.

   Until that lane lands, treat ``thlb-netdown-run`` as the current approved
   milestone, not as the final reconstructed land-base engine.

6d. generate the notebook bridge artifact when you want a text-code-output
   review surface for either an LLM coding agent or a human analyst:

   .. code-block:: bash

      python -m femic tsr thlb-netdown-workbench-build \
        --instance-root external/femic-tsa29-instance

   This writes:

   - ``workbench/tsr/thlb_netdown.workbench.ipynb``

   The notebook is generated from the current THLB recipe and is intended as
   an interactive bridge medium, not the canonical source of truth. During
   iteration, the authoritative machine-readable state remains:

   - ``config/tsr/thlb_netdown.recipe.yaml``
   - ``config/tsr/thlb_netdown.status.md``
   - ``config/tsr/thlb_netdown.audit.json`` when a runtime pass has been run

   Workbench execution follows the staged FEMIC pipeline boundary, but current
   TSA29 strict validation must stay on validated ``data/tsr/*.feather`` seam
   checkpoints rather than legacy ``ria_vri_vclr1p_checkpoint*.feather``
   fallback files.

   For example, TSA29 step ``014`` (sites with low growing timber potential)
   now uses assigned bundle curves directly in the notebook bridge:

   - the executable threshold logic runs against assigned curve volume at age
     ``160`` when the TSR text defines the rule that way; and
   - the step can still carry other curve-metric modes explicitly when a
     future TSR assumption needs them.

6e. if no LLM is available, generate the explicit warm-start checklist/template
   pair before diving into manual THLB review:

   .. code-block:: bash

      python -m femic tsr thlb-netdown-warmstart-build \
        --instance-root external/femic-tsa29-instance

   This writes:

   - ``workbench/tsr/thlb_netdown.warmstart.md``
   - ``config/tsr/thlb_warmstart.yaml``

   These outputs are **not** canonical THLB logic. They are a bounded review
   aid that turns the current parent-step recipe into a plain-language
   checklist for a human analyst:

   - what the TSR row is doing;
   - what FEMIC already has;
   - which recurring motif best matches the row, if any; and
   - which likely layers, fields, values, and review questions should be
     inspected next.

6f. once the human+agent team agrees the THLB workflow is ready to freeze,
   lock it into deterministic reproducibility artifacts:

   .. code-block:: bash

      python -m femic tsr thlb-netdown-workbench-lock \
        --instance-root external/femic-tsa29-instance \
        --lock-scope all

   This writes:

   - ``workbench/tsr/thlb_netdown.locked.py``
   - a frozen status report copy
   - a frozen audit JSON copy when one exists

   Lock hierarchy is explicit:

   - AFLB lock freezes the modeled universe definition
   - THLB lock freezes downstream harvest-eligibility logic
   - cutting AFLB invalidates THLB

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

Convergence And Reproducibility Contract
----------------------------------------

Phase 52 is being developed as action research on TSA29, but the accepted
result still has to converge toward production-grade reproducibility rather
than remaining clever one-off shell lore.

The current scriptable milestone is:

1. ``femic tsr index``
2. ``femic tsr fetch --tsa 29``
3. ``femic tsr extract --tsa 29``
4. ``femic tsr recipe-init --instance-root ... --tsa 29``
5. ``femic tsr source-layers-build``
6. ``femic tsr source-layers-run``
7. ``femic tsr thlb-netdown-build``
8. ``femic tsr thlb-netdown-workbench-build``
9. ``femic tsr thlb-netdown-run``
10. ``femic tsr thlb-netdown-workbench-lock``
11. ``femic tsr overlay-init`` / ``overlay-report``
12. ``femic tsr thlb-reconstruction-compare`` when you need a plain-language
    strict-vs-reviewed-vs-TSR gap inventory from the current artifacts without
    rerunning THLB execution.

   .. code-block:: bash

      python -m femic tsr thlb-reconstruction-compare \
        --instance-root external/femic-tsa29-instance

That chain is already a valid, reproducible TSA29 runbook.

However, it is important not to blur two different THLB states:

- **Current milestone:** a reproducible hybrid bridge that starts from the
  existing checkpoint THLB signal and applies the supported TSR-derived
  exclusions into ``thlb_fact``.
- **Promoted reconstruction lane (`#128` / `#131`):** a raw-land-base
  reconstructed mode that, for current TSA29 strict validation, must stay on
  explicit validated ``data/tsr/*.feather`` seam checkpoints, fragment the
  land base, and assign binary fragment-level THLB membership ``{0,1}``.

Reconstructed mode can now also apply a **recipe-driven aspatial fallback**
when the reviewed THLB recipe already carries a TSR target-area deduction for a
step that is intentionally not being reproduced as exact spatial geometry in
that lane. That fallback stays explicit in the audit/status output and is not
the same thing as exact spatial overlay.

Coarse approximation is no longer part of the default reconstructed contract.
If a user intentionally enables the non-default stand-binary debug fallback,
FEMIC must say so explicitly in the audit/status surface rather than presenting
that output as normal fragment-first execution.

The exact reconstructed spatial path is now LU-wise by default. In plain
language, FEMIC cuts one Landscape Unit chunk at a time instead of trying to
cut the whole TSA in one giant exact-overlay workload.

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

For a few selected stale wildlife/netdown tokens, ``override-init`` can now
pre-populate ``replacement_family_candidates``. These are intentionally
review-only suggestions, not auto-adopted replacements. Their job is to give
you a bounded shortlist when the old TSR token no longer maps cleanly to one
public BCDC object, but a small current public dataset family looks promising.

For example, a stale mule-deer token can now surface a reviewed public family
including entries such as:

- ``REG_LAND_AND_NATURAL_RESOURCE.WLD_MULE_DEER_RNG_TOPO_CAR_SP``
- ``REG_LAND_AND_NATURAL_RESOURCE.WLD_MULE_DEER_HAB_MG_ZN_CAR_SP``
- ``REG_LAND_AND_NATURAL_RESOURCE.WLD_MULE_DEER_STND_STRC_CAR_SP``

The intended loop is still manual:

1. inspect the suggested family;
2. decide whether one of the candidates is a valid reviewed replacement for
   your project;
3. record that decision under ``override_kind: replacement_layer`` only after
   review.

AOI Scope Guardrail
-------------------

When a TSR source-layer acquisition uses an AOI-bounded fetch strategy such as
WFS bbox or DWDS order, treat the requested extent as part of the data
contract, not as disposable fetch trivia.

- Acquisitions whose AOI matches the reviewed production bbox can live under
  the normal instance download root.
- Acquisitions whose AOI is smaller or otherwise differs from that reviewed
  production bbox are smoke-scale artifacts and should live under
  ``data/downloads/bcdc/smoke/``.
- Do not reuse smoke-scale AOI overlays in full-TSA THLB validation just
  because the file exists. FEMIC now compares obvious source-artifact bbox
  coverage against the current checkpoint extent and blocks clear mismatches as
  extent errors instead of quietly treating them as valid production layers.

Operationally: if a clipped smoke artifact was useful for a bounded proof, keep
it, but reacquire or promote a full-extent production artifact before drawing
full-TSA conclusions from that recipe step.

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
