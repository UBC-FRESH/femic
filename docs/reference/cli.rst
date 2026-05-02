CLI Reference
=============

Top-Level Command
-----------------

.. code-block:: text

   python -m femic [OPTIONS] COMMAND [ARGS]...

Options
-------

- ``--version``: Show version and exit.
- ``--debug``: Enable rich tracebacks.
- ``--help``: Show help and exit.

Commands
--------

- ``run``
- ``prep``
- ``vdyp``
- ``tsa``
- ``tipsy``
- ``fansier``
- ``data``
- ``pipelines``
- ``tsr``
- ``export``
- ``patchworks``
- ``instance``

Run
---

.. code-block:: text

   python -m femic run [OPTIONS]

- ``--data-root PATH`` (default: ``data``)
- ``--output-root PATH`` (default: ``outputs``)
- ``--tsa TEXT`` (repeatable; legacy FMU/code selector name)
- ``--resume``
- ``--dry-run``
- ``--verbose`` / ``-v``
- ``--skip-checks``
- ``--debug-rows INTEGER``
- ``--run-id TEXT``
- ``--log-dir PATH`` (default: ``runtime/logs``)
- ``--run-config PATH`` (YAML/JSON run profile)
- ``--instance-root PATH`` (optional; defaults to CWD or ``FEMIC_INSTANCE_ROOT`` env)

Pipelines
---------

.. code-block:: text

   python -m femic pipelines [OPTIONS] COMMAND [ARGS]...

Subcommands

- ``run``: ``python -m femic pipelines run --runbook PATH [--instance-root PATH]``

``pipelines run`` resolves one machine-readable runbook, loads the built-in +
optional user + optional instance-local named-pipeline registries, and runs
the first proof-oriented named pipeline surface.

Current proof-runner scope:

- primary product pipeline id: ``tsr.thlb_strict``
- legacy scaffold pipeline id: ``tsr.thlb_reviewed``
- seams: ``scratch``, ``aflb``, ``aflb_yield_ready``, and ``lhlb_curve_ready``
- delegation into the existing strict reconstructed TSR THLB lane rather than a new
  execution engine

``pipelines run`` options

- ``--runbook PATH`` (required; typically under ``runbooks/pipelines/``)
- ``--instance-root PATH`` (optional; defaults to CWD or ``FEMIC_INSTANCE_ROOT`` env)

Example proof-runner invocation

.. code-block:: text

   python -m femic pipelines run ^
     --runbook runbooks/pipelines/tsa29.tsr.thlb_strict.aflb_yield_ready.yaml ^
     --instance-root external/femic-tsa29-instance

Prep
----

.. code-block:: text

   python -m femic prep [OPTIONS] COMMAND [ARGS]...

Subcommands

- ``run``: ``python -m femic prep run [OPTIONS]``
- ``arbutus-auth-status``: ``python -m femic prep arbutus-auth-status [OPTIONS]``
- ``arbutus-auth-init``: ``python -m femic prep arbutus-auth-init [OPTIONS]``
- ``validate-case``: ``python -m femic prep validate-case [OPTIONS]``
- ``geospatial-preflight``: ``python -m femic prep geospatial-preflight [OPTIONS]``
- ``glb-build``: ``python -m femic prep glb-build [OPTIONS]``
- ``arcgis-review-project``: ``python -m femic prep arcgis-review-project [OPTIONS]``

``prep run`` options

- ``--data-root PATH`` (default: ``data``)
- ``--output-root PATH`` (default: ``outputs``)
- ``--tsa TEXT`` (repeatable; legacy FMU/code selector name)
- ``--resume``
- ``--dry-run``
- ``--verbose`` / ``-v``

``prep arbutus-auth-status`` options

- ``--profile TEXT`` (optional named Arbutus profile)
- ``--dataset PATH`` (optional dataset path for ``git annex enableremote`` validation)
- ``--remote TEXT`` (optional remote override)

Use ``prep arbutus-auth-status`` as the non-mutating Windows auth/profile/marker
probe. It reports:

- whether the user-local auth files exist;
- whether the current shell is loaded with the shared Arbutus env values;
- whether the selected bucket passes ``HeadBucket``; and
- whether the saved non-secret known-working marker is current or stale.

When ``--dataset`` is supplied, the command can also validate
``git annex enableremote <remote>`` for that dataset.

``prep arbutus-auth-init`` options

- ``--profile TEXT`` (optional named profile to create or refresh)
- ``--bucket TEXT`` (optional bucket name for the selected profile)
- ``--dataset PATH`` (optional dataset path for ``git annex enableremote`` validation)
- ``--remote TEXT`` (default: ``arbutus-s3``)
- ``--force-refresh-loaders``

Use ``prep arbutus-auth-init`` to scaffold and validate the Windows local
workflow under ``%USERPROFILE%\.config\femic``. The command:

- creates missing local auth/profile/status files;
- prompts interactively for missing shared values when the session allows it;
- validates ``HeadBucket`` for the selected profile; and
- writes a non-secret known-working marker only after validation succeeds.

``prep validate-case`` options

- ``--run-config PATH`` (default: ``config/run_profile.case_template.yaml``)
- ``--tipsy-config-dir PATH`` (default: ``config/tipsy``)
- ``--strict-warnings``
- ``--instance-root PATH``

On Windows, ``prep validate-case`` now also performs the low-noise
annex/Arbutus checks needed for FEMIC's Arbutus-backed public-data workflow
when that mirror is in play. It can fail fast on:

- unusable ``git-annex`` / DataLad runtime;
- quoted credential values in ``%USERPROFILE%\.config\femic\arbutus.env``;
- missing loaded Arbutus auth vars when a local Arbutus env-file workflow is
  already in use; and
- failed visibility probes for the known public-data Arbutus bucket; and
- unreadable canonical ``data/bc/tsa/FADM_TSA.gdb`` inputs that are more likely
  annex materialization/unlock problems than generic Windows GDAL ghosts.

``prep validate-case`` is no longer the primary auth/bootstrap workflow.
Use:

- ``prep arbutus-auth-status`` for current-vs-stale Windows auth state; and
- ``prep arbutus-auth-init`` to scaffold or refresh the local workflow.

For the canonical Windows auth/bootstrap runbook and publication sequence, see
``docs/guides/windows-arbutus-auth-workflow.rst`` and
``docs/guides/public-data-mirror-runbook.rst``.

``prep geospatial-preflight`` remains the generic Fiona/GDAL/shapefile smoke
check. On Windows, use ``prep validate-case`` to prove that the active FEMIC
case can actually read the annex-backed canonical TSA/FileGDB inputs.

``prep geospatial-preflight`` options

- ``--strict-warnings``
- ``--skip-shapefile-smoke``

``prep glb-build`` options

- ``--tsa TEXT`` (required; TSA code, ``tsa_<code>``, or TSA name)
- ``--instance-root PATH``
- ``--output-dir PATH`` (optional explicit output directory for the GLB bundle)
- ``--source-zip-path PATH`` (optional explicit raw VRI zip override)
- ``--boundary-path PATH`` (optional explicit TSA boundary layer override)
- ``--force-rebuild-glb`` (ignore an existing local stashed GLB and rebuild)
- ``--no-stash-public-data-glb`` (disable the default local public-data stash)
- ``--force-update-public-data-glb`` (overwrite an existing local stashed GLB)

``prep glb-build`` is the clean raw-source GLB workflow for one named TSA. It
uses the canonical 2024 provincial VRI zip by default, clips it with the
active TSA boundary row, writes a clipped GLB artifact plus JSON/Markdown
summary, and reports the clipped stand geometry area directly. Checkpoints are
not accepted as the source baseline for this command.

By default, successful runs also stash a reusable zipped GLB snapshot plus
summary JSON into the local ``external/femic-public-data`` DataLad repo under a
deterministic TSA/VRI path. That stash is local only in v1:

- no auto-commit;
- no auto-push; and
- no Arbutus/GitHub publication.

Use ``--no-stash-public-data-glb`` to disable the default stash or
``--force-update-public-data-glb`` to replace an existing stored snapshot.
When a local stashed GLB already exists, ``prep glb-build`` now reuses that
confirmed-valid snapshot by default instead of rebuilding from raw source; use
``--force-rebuild-glb`` to bypass the stash and run the raw clip again.

``prep arcgis-review-project`` options

- ``--instance-root PATH``
- ``--output-dir PATH`` (optional; defaults to ``workbench/arcgis_review`` under the instance root)
- ``--project-name TEXT`` (optional explicit `.aprx` name stem)

``prep arcgis-review-project`` is a Windows/ArcGIS Pro inspection aid, not a
new FEMIC GIS-processing backend. It discovers instance-local vector layers
already on disk (for example downloaded BCDC GeoPackages plus local shapefile
context layers such as stands or fragments), emits a ready-to-open `.aprx`,
writes a manifest JSON, and keeps all loaded layers off by default at launch.
When GeoPackage layers need ArcGIS-friendly staging, the emitted bundle also
includes helper shapefile copies under the chosen output directory.

Use it when a human needs to inspect an instance visually in ArcGIS Pro
without hand-loading dozens of layers. It depends on a local ArcGIS Pro
installation and the same path-resolved ``propy.bat`` / ArcGIS Pro Python seam
already used by the Windows SiteProd fallback.

VDYP
----

.. code-block:: text

   python -m femic vdyp [OPTIONS] COMMAND [ARGS]...

Subcommands

- ``run``: ``python -m femic vdyp run [OPTIONS]``
- ``report``: ``python -m femic vdyp report [OPTIONS]``

``vdyp run`` options

- ``--data-root PATH`` (default: ``data``)
- ``--output-root PATH`` (default: ``outputs``)
- ``--tsa TEXT`` (repeatable; legacy FMU/code selector name)
- ``--resume``
- ``--dry-run``
- ``--verbose`` / ``-v``

``vdyp report`` options

- ``--curve-log PATH`` (default: ``vdyp_io/logs/vdyp_curve_events.jsonl``)
- ``--run-log PATH`` (default: ``vdyp_io/logs/vdyp_runs.jsonl``)
- ``--expected-first-age FLOAT`` (default: ``1.0``)
- ``--expected-first-volume FLOAT`` (default: ``1e-06``)
- ``--tolerance FLOAT`` (default: ``1e-12``)
- ``--mismatch-limit INTEGER`` (default: ``10``)
- ``--max-curve-warnings INTEGER``
- ``--max-first-point-mismatches INTEGER``
- ``--max-curve-parse-errors INTEGER``
- ``--max-run-parse-errors INTEGER``
- ``--min-curve-events INTEGER``
- ``--min-run-events INTEGER``

TSA
---

.. code-block:: text

   python -m femic tsa [OPTIONS] COMMAND [ARGS]...

Compatibility note:

- ``tsa`` remains the command-group name for historical/runtime compatibility.
  In generic FEMIC usage, read it as "FMU/code-targeted legacy pipeline
  commands" unless the case is literally a BC Timber Supply Area.

Subcommands

- ``run``: ``python -m femic tsa run [OPTIONS]``
- ``post-tipsy``: ``python -m femic tsa post-tipsy [OPTIONS]``
- ``btc-post-tipsy``: ``python -m femic tsa btc-post-tipsy [OPTIONS]``

``tsa run`` options

- ``--data-root PATH`` (default: ``data``)
- ``--output-root PATH`` (default: ``outputs``)
- ``--tsa TEXT`` (repeatable; selected FMU/code values)
- ``--resume``
- ``--dry-run``
- ``--verbose`` / ``-v``

``tsa post-tipsy`` options

- ``--tsa TEXT`` (repeatable, required; selected FMU/code values)
- ``--verbose`` / ``-v``
- ``--run-id TEXT``
- ``--log-dir PATH`` (default: ``runtime/logs``)
- ``--run-config PATH`` (optional; load FMU/code selection and managed-curve mode defaults)
- ``--yield-assumptions-path PATH`` (optional instance-local post-TIPSY yield assumptions YAML)
- ``--instance-root PATH``

``tsa btc-post-tipsy`` options

- ``--tsa TEXT`` (repeatable, required; selected FMU/code values)
- ``--verbose`` / ``-v``
- ``--run-id TEXT``
- ``--log-dir PATH`` (default: ``runtime/logs``)
- ``--run-config PATH`` (optional; load FMU/code selection and managed-curve mode defaults)
- ``--yield-assumptions-path PATH`` (optional instance-local post-TIPSY yield assumptions YAML)
- ``--btc-exe PATH`` (optional explicit ``TIPSYbtc.exe`` override)
- ``--scratch-dir PATH`` (optional scratch root for copied BTC installs and staged run files)
- ``--report-preset TEXT`` (default: ``tsr-unattended-default``)
- ``--instance-root PATH``

TIPSY
-----

.. code-block:: text

   python -m femic tipsy [OPTIONS] COMMAND [ARGS]...

Use this command group when you want direct control of the BTC/TIPSY runtime
boundary rather than the broader Stage 01a/01b orchestration. The current
operator-facing default is the unattended BTC `/TSR` seam through the live
user-overlay ``TimberSupply.rpt`` path.

Data
----

.. code-block:: text

   python -m femic data [OPTIONS] COMMAND [ARGS]...

Subcommands

- ``bcdc-resolve``: ``python -m femic data bcdc-resolve [OPTIONS] [QUERY]...``
- ``bcdc-fetch``: ``python -m femic data bcdc-fetch [OPTIONS] [QUERY]...``
- ``bcdc-order``: ``python -m femic data bcdc-order [OPTIONS] [QUERY]...``
- ``bcdc-order-followup``: ``python -m femic data bcdc-order-followup [OPTIONS] ORDER_MANIFEST``

``data bcdc-resolve`` options

- ``QUERY`` argument (repeatable; BC Data Catalogue layer names or keywords)
- ``--query-file PATH`` (optional one-query-per-line text file; blank lines and ``#`` comments ignored)
- ``--summary-csv PATH`` (optional one-row-per-query CSV review export)
- ``--manifest-path PATH`` (optional JSON manifest output path)
- ``--download-direct / --no-download-direct`` (opt-in direct-downloads from the top-ranked package only)
- ``--download-root PATH`` (optional destination root for direct downloads)
- ``--limit INTEGER`` (default: ``5``)
- ``--instance-root PATH`` (optional instance root used to resolve default output paths)
- ``--plan-only`` (preview deduplicated direct-download activity without executing it)
- ``--allow-bulk / --no-allow-bulk`` (explicitly allow larger direct-download bursts that exceed FEMIC's default public-service threshold)

For working Windows examples, including quoted multi-word queries and
``--query-file`` batch usage, see
``docs/guides/bc-data-catalogue-discovery.rst``.

``data bcdc-fetch`` options

- ``QUERY`` argument (repeatable; BC Data Catalogue layer names or keywords)
- ``--query-file PATH`` (optional one-query-per-line text file; blank lines and ``#`` comments ignored)
- ``--manifest-path PATH`` (optional JSON manifest output path)
- ``--download-root PATH`` (optional destination root; defaults under ``data/downloads/bcdc``)
- ``--limit INTEGER`` (default: ``5``)
- ``--instance-root PATH`` (optional instance root used to resolve default output paths)
- ``--bbox minx,miny,maxx,maxy`` (required unless ``--geomark`` is supplied; interpreted in ``EPSG:3005``)
- ``--geomark TEXT`` (required unless ``--bbox`` is supplied; accepts a full Geomark URL or bare Geomark ID)
- ``--output-format [gpkg|geojson]`` (default: ``gpkg``)
- ``--plan-only`` (preview deduplicated WFS activity without executing it)
- ``--allow-bulk / --no-allow-bulk`` (explicitly allow larger WFS bursts that exceed FEMIC's default public-service threshold)

``data bcdc-fetch`` is the first automated geographic acquisition lane built on
top of the WFS service hints from ``bcdc-resolve``. Use it when the resolved
dataset exposes ``wfs_queryable`` and
``suggested_fetch_strategy=wfs_getfeature_bbox``. If a dataset exposes only
direct-download resources, use ``femic data bcdc-resolve --download-direct``
instead.

``data bcdc-order`` options

- ``QUERY`` argument (repeatable; BC Data Catalogue layer names or keywords)
- ``--query-file PATH`` (optional one-query-per-line text file; blank lines and ``#`` comments ignored)
- ``--manifest-path PATH`` (optional JSON manifest output path)
- ``--limit INTEGER`` (default: ``5``)
- ``--instance-root PATH`` (optional instance root used to resolve relative manifest paths)
- ``--bbox minx,miny,maxx,maxy`` (required unless ``--geomark`` is supplied; interpreted in ``EPSG:3005``)
- ``--geomark TEXT`` (required unless ``--bbox`` is supplied; accepts a full Geomark URL or bare Geomark ID)
- ``--output-format [fgdb|gpkg|geojson|shp]`` (default: ``fgdb``)
- ``--email TEXT`` (optional DWDS notification email; defaults to ``FEMIC_BCDC_DWDS_EMAIL`` when set, otherwise ``git config user.email``)
- ``--clip / --no-clip`` (default: ``--clip``)
- ``--plan-only`` (preview deduplicated DWDS order activity without executing it)
- ``--allow-bulk / --no-allow-bulk`` (explicitly allow larger DWDS order bursts that exceed FEMIC's default public-service threshold)

``data bcdc-order`` is the heavier BCGW fallback lane. Use it when a dataset
needs a DWDS order for richer outputs such as File Geodatabase or GeoPackage
instead of a simple direct file download or a WFS-backed subset fetch. The
current public DWDS seam can submit orders successfully, but the public
``/order/{id}`` status lookup may still report successful live orders as
missing, so FEMIC records that caveat in the manifest instead of pretending
the full end-to-end download path is already solved.

``data bcdc-order-followup`` options

- ``ORDER_MANIFEST`` argument (required; manifest written by ``data bcdc-order``)
- ``--manifest-path PATH`` (optional output manifest path; defaults to updating the input manifest in place)
- ``--download-root PATH`` (optional destination root for downloaded DWDS artifacts)
- ``--instance-root PATH`` (optional instance root used to resolve relative output paths)
- ``--download / --no-download`` (default: ``--download``; materialize the artifact when a follow-up probe exposes a download URL)
- ``--poll-status / --no-poll-status`` (default: ``--poll-status``; re-probe the public DWDS order seam before materialization)

``data bcdc-order-followup`` is FEMIC's recovery lane for orders that were
submitted successfully but did not immediately expose a downloadable artifact.
It reloads an existing DWDS manifest, retries the public status seam, and
downloads the artifact into the selected root if DWDS finally returns a
download URL. When the public ``/order/{id}`` seam still returns the known
false negative, FEMIC now also uses the saved ``order_guid`` to try the DWDS
``pickupByGUID`` launcher page and extract the real
``distribution.data.gov.bc.ca`` package URL.

All three BCDC acquisition commands now apply soft good-citizen guardrails:
duplicate queries are collapsed automatically, ``--plan-only`` previews the
deduplicated public-service activity, and larger batch runs require an
explicit ``--allow-bulk`` acknowledgement before FEMIC will execute them.

Subcommands

- ``validate``: ``python -m femic tipsy validate [OPTIONS]``
- ``write-btc-report-template``: ``python -m femic tipsy write-btc-report-template [OPTIONS]``
- ``run-btc``: ``python -m femic tipsy run-btc [OPTIONS]``

``tipsy validate`` options

- ``--config-dir PATH`` (default: ``config/tipsy``)
- ``--tsa TEXT`` (repeatable; selected FMU/code values)
- ``--instance-root PATH``

``tipsy write-btc-report-template`` options

- ``--preset TEXT`` (required; built-in report-template preset)
- ``OUTPUT`` argument (required)
- ``--source-rpt PATH`` (optional existing ``.rpt`` template to clone/adapt)
- ``--column TEXT`` (repeatable additional BTC output column token)
- ``--instance-root PATH``

``tipsy run-btc`` options

- ``INPUT_CSV`` argument (required)
- ``--output-csv PATH`` (optional; defaults beside input)
- ``--error-csv PATH`` (optional; defaults beside input)
- ``--btc-exe PATH`` (optional explicit ``TIPSYbtc.exe`` override)
- ``--mode TEXT`` (default: ``TSR``)
- ``--report-template PATH`` (optional vetted ``TimberSupply.rpt`` override)
- ``--report-preset TEXT`` (default: ``tsr-unattended-default`` for ``TSR``)
- ``--copy-install`` / ``--use-installed-btc``
- ``--scratch-dir PATH`` (optional writable scratch directory; defaults under ``tipsy_io/scratch``)
- ``--log-dir PATH`` (default: ``tipsy_io/logs``)
- ``--run-id TEXT``
- ``--instance-root PATH``

Operational note:

- runtime artifacts now default under ``tipsy_io/logs`` and
  ``tipsy_io/scratch`` so BTC supervision is visually separate from the VDYP
  runtime namespace.

FAN$IER
-------

.. code-block:: text

   python -m femic fansier [OPTIONS] COMMAND [ARGS]...

Use this command group when you want FEMIC to drive the tracked Windows
FAN$IER batch-extraction seam and optionally normalize the resulting long-report
text files into FEMIC-owned tables.

Subcommands

- ``run-batch``: ``python -m femic fansier run-batch [OPTIONS] RGM_PATH``
- ``parse-batch-output``:
  ``python -m femic fansier parse-batch-output [OPTIONS] REPORT_DIR``
- ``run-and-parse``:
  ``python -m femic fansier run-and-parse [OPTIONS] RGM_PATH``

``fansier run-batch`` options

- ``RGM_PATH`` argument (required)
- ``--out-dir PATH`` (default: ``tipsy_io/logs/fansier_batch``)
- ``--log-dir PATH`` (default: ``tipsy_io/logs``)
- ``--run-id TEXT`` (default: ``fansier_batch``)
- ``--fansier-exe PATH`` (default: installed ``Fansier.exe`` path)
- ``--discount-name TEXT`` (default: ``FEMIC Raw 0%``)
- ``--discount-dis-path PATH`` (optional; load `.dis` before selection)
- ``--report-type TEXT`` (default: ``txt``)
- ``--long-report`` / ``--short-report`` (default: short)
- ``--product-cols`` / ``--no-product-cols``
- ``--activity-cols`` / ``--no-activity-cols`` (default: off)
- ``--select-all-products``
- ``--select-all-ages``
- ``--product-name TEXT`` (used when not selecting all products)
- ``--age-name TEXT`` (used when not selecting all ages)

``fansier parse-batch-output`` options

- ``REPORT_DIR`` argument (required directory of FAN$IER ``.txt`` outputs)
- ``--out-dir PATH`` (default: ``tipsy_io/logs/fansier_parsed``)
- ``--report-glob TEXT`` (default: ``*.txt``)

``fansier run-and-parse`` options

- ``RGM_PATH`` argument (required)
- ``--out-dir PATH`` (default: ``tipsy_io/logs/fansier_batch``)
- ``--parsed-out-dir PATH`` (default: ``tipsy_io/logs/fansier_parsed``)
- ``--log-dir PATH`` (default: ``tipsy_io/logs``)
- ``--run-id TEXT`` (default: ``fansier_batch``)
- ``--fansier-exe PATH`` (default: installed ``Fansier.exe`` path)
- ``--discount-name TEXT`` (default: ``FEMIC Raw 0%``)
- ``--discount-dis-path PATH`` (optional; load `.dis` before selection)
- ``--report-type TEXT`` (currently must be ``txt`` for parsing)
- ``--long-report`` / ``--short-report`` (default: long)
- ``--product-cols`` / ``--no-product-cols``
- ``--activity-cols`` / ``--no-activity-cols`` (default: off)
- ``--select-all-products`` / ``--single-product`` (default: all)
- ``--select-all-ages`` / ``--single-age`` (default: all)
- ``--product-name TEXT`` (used when broad product selection is off)
- ``--age-name TEXT`` (used when broad age selection is off)

Operational notes:

- the parsing seam currently expects ``txt`` reports;
- the practical machine-ingest default is `0%` discount posture with product
  columns on and activity columns off.

Data
----

.. code-block:: text

   python -m femic data [OPTIONS] COMMAND [ARGS]...

Use this command group when you want FEMIC to help resolve BC Data Catalogue
records from explicit layer names or keywords copied from TSR source-data
lists.

Subcommands

- ``bcdc-resolve``: ``python -m femic data bcdc-resolve [OPTIONS] QUERY...``

``data bcdc-resolve`` options

- ``QUERY`` argument (repeatable; one or more layer names or keywords)
- ``--manifest-path PATH`` (optional JSON candidate-manifest output path)
- ``--download-direct / --no-download-direct`` (default: ``--no-download-direct``)
- ``--download-root PATH`` (optional; defaults under ``data/downloads/bcdc``
  for ``--instance-root`` workflows, otherwise ``./downloads/bcdc``)
- ``--limit INTEGER`` (default: ``5``)
- ``--instance-root PATH``

Operational notes:

- v1 resolves and classifies catalogue resources first; it does **not**
  automate indirect/custom-download BCGW flows;
- service-backed OpenMaps resources can now surface machine-readable WFS hints
  such as ``wfs_queryable``, ``wfs_typename``, and
  ``suggested_fetch_strategy`` in the manifest/summary outputs;
- ``--download-direct`` only downloads stable direct-access data resources from
  the top-ranked package match; and
- the intended promotion path is candidate manifest first, then manual review,
  then optional updates to ``metadata/required_datasets.yaml``.

TSR
---

.. code-block:: text

   python -m femic tsr [OPTIONS] COMMAND [ARGS]...

Subcommands

- ``index``: ``python -m femic tsr index [OPTIONS]``
- ``fetch``: ``python -m femic tsr fetch [OPTIONS]``
- ``extract``: ``python -m femic tsr extract [OPTIONS]``
- ``facts-report``: ``python -m femic tsr facts-report [OPTIONS]``
- ``recipe-init``: ``python -m femic tsr recipe-init [OPTIONS]``
- ``source-layers-build``: ``python -m femic tsr source-layers-build [OPTIONS]``
- ``source-layers-run``: ``python -m femic tsr source-layers-run [OPTIONS]``
- ``overlay-init``: ``python -m femic tsr overlay-init [OPTIONS]``
- ``overlay-report``: ``python -m femic tsr overlay-report [OPTIONS]``
- ``override-init``: ``python -m femic tsr override-init [OPTIONS]``
- ``override-report``: ``python -m femic tsr override-report [OPTIONS]``
- ``thlb-netdown-warmstart-build``: ``python -m femic tsr thlb-netdown-warmstart-build [OPTIONS]``
- ``thlb-reconstruction-compare``: ``python -m femic tsr thlb-reconstruction-compare [OPTIONS]``

``tsr index`` options

- ``--output-root PATH`` (optional; defaults to ``metadata/tsr`` under the
  active FEMIC checkout)

``tsr index`` crawls the public BC Timber Supply Review TSA document surfaces
and writes the canonical repo-tracked registry outputs:

- ``metadata/tsr/tsa_registry.json``
- ``metadata/tsr/tsa_documents.json``

This first slice indexes TSA folders, cycles, and linked document metadata
only. It does not download PDFs or extract candidate facts yet.

``tsr fetch`` options

- ``--documents-path PATH`` (optional; defaults to
  ``metadata/tsr/tsa_documents.json`` under the active FEMIC checkout)
- ``--corpus-root PATH`` (optional; defaults to the user-local
  ``~/.femic/tsr/corpus`` and can later be redirected to a separate
  DataLad-managed corpus root)
- ``--manifest-path PATH`` (optional; defaults to the user-local
  ``~/.femic/tsr/tsa_pdf_cache_manifest.json``)
- ``--tsa TEXT`` (repeatable optional TSA filter)
- ``--max-documents INTEGER`` (optional bounded smoke-test/fetch limit)

``tsr fetch`` downloads the indexed TSA PDF corpus into the chosen corpus root
and writes a canonical provenance manifest that stores repo-relative corpus
paths or stable user-local placeholders, checksums, fetch status, and source
URLs without requiring the PDFs themselves to live in the main FEMIC Git
history.

``tsr extract`` options

- ``--documents-path PATH`` (optional; defaults to
  ``metadata/tsr/tsa_documents.json`` under the active FEMIC checkout)
- ``--corpus-root PATH`` (optional; defaults to the user-local
  ``~/.femic/tsr/corpus``)
- ``--output-path PATH`` (optional; defaults to
  ``metadata/tsr/tsa_candidate_facts.json`` under the active FEMIC checkout)
- ``--tsa TEXT`` (repeatable optional TSA filter)
- ``--max-documents INTEGER`` (optional bounded smoke-test/extract limit)

``tsr extract`` reads cached TSR PDFs from the chosen corpus root and emits a
canonical candidate-fact JSON artifact:

- ``metadata/tsr/tsa_candidate_facts.json``

The extraction slice is intentionally review-oriented. It produces candidate
facts for source-layer tokens, AU snippets, THLB references, and TIPSY
assumption snippets with page/snippet provenance, but it does not adopt those
facts into live instance overlays yet.

``tsr facts-report`` options

- ``--tsa TEXT`` (required TSA code, ``tsa_<code>``, or TSA name)
- ``--fact-family TEXT`` (required, repeatable; currently supports at least
  ``source_layer_candidate`` and ``thlb_reference``)
- ``--fact-family [source_layer_candidate|thlb_reference]`` is the most useful
  current review slice for TSR netdown/THLB work
- ``--candidate-facts-path PATH`` (optional; defaults to
  ``metadata/tsr/tsa_candidate_facts.json``)
- ``--output-csv PATH`` (optional review CSV output path)
- ``--limit INTEGER`` (optional cap on sorted review rows)

``tsr facts-report`` renders a review-friendly table over the canonical TSR
candidate-fact pool. It does not mutate the canonical fact artifact or the
instance-local overlay. The first guided-review slice:

- filters by TSA and fact family;
- adds lightweight quality labels:
  - ``likely_useful``
  - ``needs_review``
  - ``likely_noise``;
- preserves provenance and source URLs; and
- can write a CSV that is easier to sort/filter than the raw JSON fact pool.

``tsr recipe-init`` options

- ``--tsa TEXT`` (required TSA code, ``tsa_<code>``, or TSA name)
- ``--instance-root PATH`` (instance root containing ``config/`` and ``data/``)
- ``--registry-path PATH`` (optional; defaults to
  ``metadata/tsr/tsa_registry.json``)
- ``--documents-path PATH`` (optional; defaults to
  ``metadata/tsr/tsa_documents.json``)
- ``--candidate-facts-path PATH`` (optional; defaults to
  ``metadata/tsr/tsa_candidate_facts.json``)
- ``--overlay-path PATH`` (optional; defaults to
  ``config/tsr/overlay.yaml`` under the instance root)
- ``--overrides-path PATH`` (optional; defaults to
  ``config/tsr/source_layer_overrides.yaml`` under the instance root)
- ``--source-layers-recipe-path PATH`` (optional; defaults to
  ``config/tsr/source_layers.recipe.yaml`` under the instance root)
- ``--thlb-netdown-recipe-path PATH`` (optional; defaults to
  ``config/tsr/thlb_netdown.recipe.yaml`` under the instance root)
- ``--overwrite`` (optional; replace existing recipe scaffold files)

``tsr recipe-init`` initializes the two instance-local reviewed working
recipes that later recipe build/run slices will own:

- ``config/tsr/source_layers.recipe.yaml``
- ``config/tsr/thlb_netdown.recipe.yaml``

These recipe files are intentionally distinct from:

- canonical shared TSR discovery JSON under ``metadata/tsr``;
- the reviewed/adopted overlay at ``config/tsr/overlay.yaml``; and
- the wall-moving escape hatch file at
  ``config/tsr/source_layer_overrides.yaml``.

``tsr source-layers-build`` options

- ``--instance-root PATH`` (instance root containing ``config/`` and ``data/``)
- ``--source-layers-recipe-path PATH`` (optional; defaults to
  ``config/tsr/source_layers.recipe.yaml`` under the instance root)
- ``--limit INTEGER`` (optional BCDC package-match cap; defaults to ``5``)

``tsr source-layers-build`` refreshes the reviewed source-layer recipe from:

- canonical TSR source-layer candidate facts;
- the existing guided review heuristics behind ``femic tsr facts-report``; and
- current BCDC resolution metadata.

The command records a deterministic reviewed acquisition plan instead of making
the user re-run the TSA29-style discovery sequence manually every time.

``tsr source-layers-run`` options

- ``--instance-root PATH`` (instance root containing ``config/`` and ``data/``)
- ``--source-layers-recipe-path PATH`` (optional; defaults to
  ``config/tsr/source_layers.recipe.yaml`` under the instance root)
- exactly one AOI input:
  - ``--bbox minx,miny,maxx,maxy`` in ``EPSG:3005``
  - ``--geomark TEXT``
- ``--limit INTEGER`` (optional BCDC package-match cap; defaults to ``5``)
- ``--allow-order`` (optional; permit **new** DWDS order submission for recipe
  entries that still require ``dwds_order``)

``tsr source-layers-run`` executes only the safe acquisition paths already
trusted elsewhere in FEMIC:

- WFS fetch via ``femic data bcdc-fetch``-equivalent logic;
- direct-download reuse via ``femic data bcdc-resolve --download-direct``-equivalent
  logic; and
- automatic DWDS manifest follow-up/materialization for ``dwds_order`` entries
  that already carry a saved ``order_manifest_path``; and
- explicit reviewed override mappings from
  ``config/tsr/source_layer_overrides.yaml``.

``tsr thlb-netdown-build`` options

- ``--instance-root PATH`` (instance root containing ``config/`` and ``data/``)
- ``--thlb-netdown-recipe-path PATH`` (optional; defaults to
  ``config/tsr/thlb_netdown.recipe.yaml`` under the instance root)

``tsr thlb-netdown-build`` refreshes the reviewed THLB netdown recipe from:

- canonical TSR ``thlb_reference`` facts;
- the current source-layer recipe so THLB steps can link to stable logical
  source ids instead of ad hoc filenames; and
- the latest preferred TSR data-package document for the target TSA when
  multiple cycles are present.

The command is intentionally about **what the TSR says to do**, not about
executing the netdown. It writes an ordered, reviewable
``config/tsr/thlb_netdown.recipe.yaml`` that preserves:

- raw TSR wording;
- explicit land-base stage semantics:
  - ``glb_to_aflb``
  - ``aflb_to_lhlb``
  - ``lhlb_to_thlb``
  - ``reference_target``
  - ``context``
- normalized action/subject/predicate hints where the extraction is confident;
- linked source-layer recipe entry ids when they can be derived conservatively;
- per-step readiness/blocking state; and
- the selected source TSR document paths used for the build.

The stage model is the guardrail that keeps the THLB recipe from confusing
universe definition, legal exclusions, projected operational deductions,
benchmark rows, and pure context.

For the full reconstruction-ladder and benchmark-comparison contract behind
those stage labels, see
:doc:`../guides/tsr-thlb-reconstruction-ladder`.

``tsr thlb-netdown-warmstart-build`` options

- ``--instance-root PATH`` (instance root containing ``config/`` and ``data/``)
- ``--thlb-netdown-recipe-path PATH`` (optional; defaults to
  ``config/tsr/thlb_netdown.recipe.yaml`` under the instance root)
- ``--output-markdown PATH`` (optional; defaults to
  ``workbench/tsr/thlb_netdown.warmstart.md`` under the instance root)
- ``--output-yaml PATH`` (optional; defaults to
  ``config/tsr/thlb_warmstart.yaml`` under the instance root)

``tsr thlb-netdown-warmstart-build`` generates a non-canonical no-LLM review
aid from the current reviewed THLB recipe:

- ``workbench/tsr/thlb_netdown.warmstart.md``
- ``config/tsr/thlb_warmstart.yaml``

The artifact is intentionally a warm-start checklist/template, not executable
THLB logic. Its job is to help a human analyst see:

- what FEMIC already knows about each parent step;
- which recurring THLB motif best matches the current row, if any; and
- which likely layers, fields, values, and review questions should be checked
  next.

The canonical executable surface remains:

- ``config/tsr/thlb_netdown.recipe.yaml``

``tsr thlb-reconstruction-compare`` options

- ``--instance-root PATH`` (instance root containing ``config/`` and ``data/``)
- ``--thlb-netdown-recipe-path PATH`` (optional; defaults to
  ``config/tsr/thlb_netdown.recipe.yaml`` under the instance root)
- ``--reconstructed-audit-path PATH`` (optional; defaults to
  ``config/tsr/thlb_reconstructed.audit.json`` under the instance root)
- ``--reviewed-status-path PATH`` (optional; defaults to
  ``config/tsr/thlb_netdown.status.md`` under the instance root)
- ``--output-markdown PATH`` (optional; defaults to
  ``config/tsr/thlb_reconstruction_comparison.md`` under the instance root)
- ``--output-json PATH`` (optional; defaults to
  ``config/tsr/thlb_reconstruction_comparison.json`` under the instance root)

``tsr thlb-reconstruction-compare`` is the explain-first comparison surface
for the still-open strict-reconstruction gap under ``#128``. It reads the
existing reviewed and reconstructed TSA29 artifacts and emits:

- ``config/tsr/thlb_reconstruction_comparison.md``
- ``config/tsr/thlb_reconstruction_comparison.json``

The command does **not** rerun THLB execution. Its job is to show, in plain
language:

- strict reconstructed THLB vs TSR-reported THLB as the primary benchmark;
- reviewed bridge THLB vs TSR-reported THLB as context for why the reviewed
  lane was accepted for practical exploratory use;
- strict reconstructed vs reviewed bridge deltas as explanatory context rather
  than the main score; and
- which parent steps should be treated as:
  - close enough to TSR;
  - real strict overcut/undercut seams;
  - missing-data seams;
  - or accepted reviewed bridges / aspatial fallback territory.

``tsr thlb-netdown-workbench-build`` options

- ``--instance-root PATH`` (instance root containing ``config/`` and ``data/``)
- ``--thlb-netdown-recipe-path PATH`` (optional; defaults to
  ``config/tsr/thlb_netdown.recipe.yaml`` under the instance root)
- ``--workbench-path PATH`` (optional; defaults to
  ``workbench/tsr/thlb_netdown.workbench.ipynb`` under the instance root)

``tsr thlb-netdown-workbench-build`` generates a Jupyter notebook bridge
artifact from the current reviewed THLB recipe. The notebook is intentionally
**not** the canonical source of truth. Instead it is a structured work surface
for:

- LLM-assisted piloting of the THLB review/execution process; and
- no-LLM human review when users need a warm-start workbench instead of raw
  YAML or JSON.

The notebook is generated from the same parent-step + draft-subrule structure
already captured in ``config/tsr/thlb_netdown.recipe.yaml`` and organizes the
workflow into a text -> code -> output -> interpretation ladder grouped by:

- ``GLB -> AFLB``
- ``AFLB -> LHLB``
- ``LHLB -> THLB``

The generated cells also respect the stage boundary in the underlying FEMIC
pipeline, but current TSA29 strict validation must stay on validated
``data/tsr/*.feather`` seam checkpoints rather than legacy
``ria_vri_vclr1p_checkpoint*.feather`` fallbacks.

``tsr thlb-netdown-workbench-lock`` options

- ``--instance-root PATH`` (instance root containing ``config/`` and ``data/``)
- ``--thlb-netdown-recipe-path PATH`` (optional; defaults to
  ``config/tsr/thlb_netdown.recipe.yaml`` under the instance root)
- ``--workbench-path PATH`` (optional; defaults to
  ``workbench/tsr/thlb_netdown.workbench.ipynb`` under the instance root)
- ``--lock-scope [aflb|thlb|all]`` (optional; defaults to ``all``)

``tsr thlb-netdown-workbench-lock`` freezes the current reviewed state into a
deterministic reproducibility bundle:

- ``workbench/tsr/thlb_netdown.locked.py``
- a frozen recipe copy
- a frozen Markdown status report copy
- a frozen audit JSON copy when one exists

Important lock contract:

- AFLB lock freezes the modeled universe definition
- THLB lock freezes the downstream harvest-eligibility logic
- THLB cannot lock unless AFLB is already locked or locked in the same pass
- cutting AFLB invalidates THLB because THLB is downstream from the AFLB
  universe definition

``tsr thlb-netdown-step-run`` options

- ``PARENT_STEP_ID`` (required parent-step id from
  ``config/tsr/thlb_netdown.recipe.yaml``)
- ``--instance-root PATH`` (instance root containing ``config/`` and ``data/``)
- ``--thlb-netdown-recipe-path PATH`` (optional; defaults to
  ``config/tsr/thlb_netdown.recipe.yaml`` under the instance root)
- ``--checkpoint-path PATH`` (optional; current TSA29 strict validation should
  pass an explicit validated checkpoint path under ``data/tsr/``)
- ``--map-id TEXT`` (repeatable; optional explicit ``MAP_ID`` subset)
- ``--auto-map-id-smoke-subset / --no-auto-map-id-smoke-subset`` (default:
  ``--auto-map-id-smoke-subset``)

``tsr thlb-netdown-step-run`` executes one parent step cumulatively on the
small smoke subset and writes working artifacts under:

- ``runtime/logs/tsr/notebook_runs/``

This helper is the command-line twin of the generated notebook cells and keeps
the small-area proving-ground discipline explicit while the recipe shape is
still being refined.

``tsr thlb-netdown-run`` options

- ``--instance-root PATH`` (instance root containing ``config/`` and ``data/``)
- ``--thlb-netdown-recipe-path PATH`` (optional; defaults to
  ``config/tsr/thlb_netdown.recipe.yaml`` under the instance root)
- ``--checkpoint-path PATH`` (optional; current TSA29 strict validation should
  pass an explicit validated checkpoint path under ``data/tsr/``)
- ``--output-path PATH`` (optional; defaults to
  ``data/tsr/thlb_netdown_checkpoint.feather`` under the instance root)
- ``--audit-path PATH`` (optional; defaults to
  ``config/tsr/thlb_netdown.audit.json`` under the instance root)
- ``--execution-mode [hybrid|reconstructed]`` (optional; defaults to
  ``hybrid``)
- ``--map-id TEXT`` (repeatable optional VRI mapsheet smoke subset)
- ``--auto-map-id-smoke-subset`` (optional bounded reconstructed smoke helper)
- ``--allow-stand-binary-fallback`` (optional non-default debug fallback for
  reconstructed mode only)
- ``--no-aflb-gpkg`` (optional; suppress the default
  ``data/tsr/aflb_checkpoint.gpkg`` companion export when a reconstructed run
  reaches the AFLB milestone)
- ``--no-lhlb-gpkg`` (optional; suppress the default
  ``data/tsr/lhlb_checkpoint.gpkg`` companion export when a reconstructed run
  reaches the LHLB milestone)
- ``--no-lhlb-curve-ready-gpkg`` (optional; suppress the default
  ``data/tsr/lhlb_curve_ready_checkpoint.gpkg`` companion export when a
  reconstructed run promotes the official LHLB checkpoint into the late-stage
  curve-ready restart surface)

``tsr thlb-netdown-run`` executes a bounded subset of the reviewed THLB recipe
into a stand-level checkpoint that carries ``thlb_fact`` for downstream export
and simulation flows.

Current v1 execution contract:

- ``use_land_base`` and ``no_deduction`` become explicit no-op audit rows;
- ``exclude`` steps with fetched polygon sources are applied as stand-level
  overlap deductions in ``EPSG:3005``;
- unsupported or low-confidence actions remain explicit as
  ``needs_review`` / ``unsupported`` / ``blocked_missing_source`` instead of
  being guessed silently; and
- the run writes both:
  - ``data/tsr/thlb_netdown_checkpoint.feather``
  - ``config/tsr/thlb_netdown.audit.json``
  - ``config/tsr/thlb_netdown.status.md``
  - plus a timestamped history copy under ``runtime/logs/tsr/``
- reconstructed runs that genuinely reach the AFLB milestone now also write:
  ``data/tsr/aflb_checkpoint.feather`` as the canonical downstream restart
  artifact, and ``data/tsr/aflb_checkpoint.gpkg`` by default as the GIS-facing
  companion export
- reconstructed runs that genuinely reach the LHLB milestone now also write:
  ``data/tsr/lhlb_checkpoint.feather`` as the canonical raw post-step-12
  restart artifact, and ``data/tsr/lhlb_checkpoint.gpkg`` by default as the
  GIS-facing companion export
- reconstructed runs that need strict ``LHLB -> THLB`` execution now also
  promote that raw LHLB restart into
  ``data/tsr/lhlb_curve_ready_checkpoint.feather`` as the canonical late-stage
  restart artifact for steps ``13+``, with
  ``data/tsr/lhlb_curve_ready_checkpoint.gpkg`` written by default as the
  GIS-facing companion export unless the caller disables it explicitly

This command is intentionally partial-success friendly: it should move the
recipe forward where FEMIC has enough trustworthy information while keeping the
remaining wall visible and reproducible.

The generated status report keeps benchmark ratios visible while the THLB logic
converges:

- a GLB/AFLB/LHLB/THLB backbone summary;
- input checkpoint area;
- AFLB / baseline managed area;
- final THLB area;
- current executable ratios such as the GLB:AFLB proxy and ``AFLB:THLB``; and
- TSR AFLB / THLB benchmark values when they can be parsed from the selected
  data package PDF.

It also groups the reviewed steps by:

- ``GLB -> AFLB``
- ``AFLB -> LHLB``
- ``LHLB -> THLB``
- ``Reference targets``
- ``Context / interpretation``

Important current boundary:

- ``--execution-mode hybrid`` is still the reviewed stand-level bridge from
  issue ``#126``;
- ``--execution-mode reconstructed`` is now the promoted fragment-first lane:
  for current TSA29 strict validation it must start from an explicit validated
  ``data/tsr/*.feather`` seam checkpoint, fragment the working land base where
  reviewed spatial exclusions intersect, and assign binary fragment-level THLB
  membership ``{0,1}``;
- reconstructed exact spatial steps now run LU-wise by default:
  FEMIC cuts one Landscape Unit chunk at a time instead of trying to build one
  full-TSA exact-overlay workload;
- reconstructed mode now supports two honest deduction types: exact fragment
  overlay where FEMIC has a reviewed spatial implementation, and explicit
  recipe-driven aspatial fallback where the reviewed recipe already carries a
  TSR target-area deduction;
- ``--checkpoint-path data/tsr/aflb_checkpoint.feather`` is now the supported
  downstream restart seam when analysts want to explore ``AFLB -> LHLB ->
  THLB`` logic without rebuilding the settled ``GLB -> AFLB`` ladder;
- ``--checkpoint-path data/tsr/lhlb_checkpoint.feather`` is now the supported
  raw post-step-12 restart seam when analysts want to inspect or rebuild the
  stage boundary itself;
- ``--checkpoint-path data/tsr/lhlb_curve_ready_checkpoint.feather`` is now the
  supported downstream restart seam when analysts want to explore only
  strict ``LHLB -> THLB`` logic without rebuilding the settled upstream ladder;
- this is an explicit recipe-driven aspatial fallback, not a silent substitute
  for blocked spatial logic;
- blocked exact-overlay rows still remain explicit instead of being silently
  converted into fallback; and
- the old coarse stand-binary approximation remains available only behind the
  explicit ``--allow-stand-binary-fallback`` debug flag.

For the conceptual distinction between those two modes, plus the comparison
contract against TSR-reported THLB, see
:doc:`../guides/tsr-thlb-reconstruction-ladder`.

``tsr overlay-init`` options

- ``--tsa TEXT`` (required TSA code, ``tsa_<code>``, or TSA name)
- ``--instance-root PATH`` (instance root containing ``config/`` and ``data/``)
- ``--registry-path PATH`` (optional; defaults to
  ``metadata/tsr/tsa_registry.json``)
- ``--documents-path PATH`` (optional; defaults to
  ``metadata/tsr/tsa_documents.json``)
- ``--candidate-facts-path PATH`` (optional; defaults to
  ``metadata/tsr/tsa_candidate_facts.json`` for canonical candidate facts)
- ``--overlay-path PATH`` (optional; defaults to
  ``config/tsr/overlay.yaml`` under the instance root)
- ``--overwrite`` (optional; replace an existing overlay)

``tsr overlay-init`` initializes the instance-local reviewed/adopted overlay:

- ``config/tsr/overlay.yaml``

The initialized overlay stores only TSA identity, canonical provenance
references, candidate-summary counts, and empty adopted sections. It does not
auto-promote unresolved candidate facts into live instance truth.

``tsr overlay-report`` options

- ``--instance-root PATH`` (instance root containing ``config/`` and ``data/``)
- ``--overlay-path PATH`` (optional; defaults to
  ``config/tsr/overlay.yaml`` under the instance root)

``tsr overlay-report`` compares the local reviewed overlay against the canonical
candidate summary already stored inside the overlay and reports adopted counts
per section without mutating the file.

``tsr override-init`` options

- ``--instance-root PATH`` (instance root containing ``config/`` and ``data/``)
- ``--overlay-path PATH`` (optional; defaults to
  ``config/tsr/overlay.yaml`` under the instance root)
- ``--overrides-path PATH`` (optional; defaults to
  ``config/tsr/source_layer_overrides.yaml`` under the instance root)
- ``--overwrite`` (optional; replace an existing override file)

``tsr override-init`` initializes an instance-local source-layer override file
from unresolved TSA rows already captured in the reviewed TSR overlay:

- ``config/tsr/source_layer_overrides.yaml``

Use it when the public BCDC resolver has hit an honest wall and you need to
record a reviewed escape hatch such as:

- a local filesystem path;
- a bespoke dataset URL;
- a FEMIC/DataLad-managed mirror path;
- a reviewed replacement layer; or
- an explicit ``private`` / ``unavailable`` marker with notes.

``tsr override-report`` options

- ``--instance-root PATH`` (instance root containing ``config/`` and ``data/``)
- ``--overlay-path PATH`` (optional; defaults to
  ``config/tsr/overlay.yaml`` under the instance root)
- ``--overrides-path PATH`` (optional; defaults to
  ``config/tsr/source_layer_overrides.yaml`` under the instance root)

The override workflow is for reviewed escape hatches only. ``override-init``
can now pre-populate ``replacement_family_candidates`` for a small number of
stale/public-facing wall cases, but those suggestions are not automatic
replacements and are never auto-fetched or auto-adopted.

``tsr override-report`` compares the override file against the unresolved rows
still present in the TSR overlay and reports:

- total override entries;
- how many are already resolved vs still pending; and
- which override kinds are currently in use.

For the full operator/agent workflow from TSR page to cached PDFs to reviewed
instance overlay, see ``docs/guides/tsr-intelligence-workflow.rst``.

Export
------

.. code-block:: text

   python -m femic export [OPTIONS] COMMAND [ARGS]...

Subcommands

- ``patchworks``: ``python -m femic export patchworks [OPTIONS]``
- ``woodstock``: ``python -m femic export woodstock [OPTIONS]``
- ``dual``: ``python -m femic export dual [OPTIONS]``
- ``release``: ``python -m femic export release [OPTIONS]``

``export patchworks`` options

- ``--tsa TEXT`` (repeatable, required; selected FMU/code values)
- ``--bundle-dir PATH`` (default: ``data/model_input_bundle``)
- ``--checkpoint PATH`` (default: ``data/ria_vri_vclr1p_checkpoint7.feather``)
- ``--output-dir PATH`` (default: ``output/patchworks``)
- ``--start-year INTEGER`` (default: ``2026``)
- ``--horizon-years INTEGER`` (default: ``300``)
- ``--cc-min-age INTEGER`` (default: ``0``)
- ``--cc-max-age INTEGER`` (default: ``1000``)
- ``--cc-transition-ifm TEXT`` (default: unset; no IFM transition assign)
- ``--fragments-crs TEXT`` (default: ``EPSG:3005``)
- ``--ifm-mode TEXT`` (default: ``proportional``; ``proportional`` keeps
  continuous THLB share via ``RETENTION``, ``legacy_binary`` preserves the
  older threshold/share-based stand snap)
- ``--ifm-source-col TEXT`` (optional; explicit checkpoint THLB signal column)
- ``--ifm-threshold FLOAT`` (optional; legacy-binary mode only; managed when
  source value > threshold)
- ``--ifm-target-managed-share FLOAT`` (optional; legacy-binary mode only;
  top-N managed by source value)
- ``--seral-stage-config PATH`` (optional; YAML per-AU seral-stage boundaries)
- ``--instance-root PATH``

``export woodstock`` options

- ``--tsa TEXT`` (repeatable, required; selected FMU/code values)
- ``--bundle-dir PATH`` (default: ``data/model_input_bundle``)
- ``--checkpoint PATH`` (default: ``data/ria_vri_vclr1p_checkpoint7.feather``)
- ``--output-dir PATH`` (default: ``output/woodstock``)
- ``--cc-min-age INTEGER`` (default: ``0``)
- ``--cc-max-age INTEGER`` (default: ``1000``)
- ``--fragments-crs TEXT`` (default: ``EPSG:3005``)
- ``--instance-root PATH``

``export dual`` options

- ``--tsa TEXT`` (repeatable, required; selected FMU/code values)
- ``--bundle-dir PATH`` (default: ``data/model_input_bundle``)
- ``--checkpoint PATH`` (default: ``data/ria_vri_vclr1p_checkpoint7.feather``)
- ``--patchworks-output-dir PATH`` (default: ``output/patchworks``)
- ``--woodstock-output-dir PATH`` (default: ``output/woodstock``)
- ``--with-ws3-smoke / --no-ws3-smoke`` (default: ``--no-ws3-smoke``)
- ``--ws3-command TEXT`` (optional shell command for ws3 simulation smoke)
- ``--ws3-workdir PATH`` (optional command working directory)
- ``--ws3-report PATH`` (default: ``evidence/ws3_smoke_report.latest.json``)
- ``--ws3-require-command / --ws3-allow-no-command`` (default: allow no command)
- ``--ws3-timeout-seconds INTEGER`` (default: ``600``)
- ``--ws3-repo-path PATH`` (optional local ws3 checkout path for builtin smoke)
- ``--ws3-builtin-smoke / --no-ws3-builtin-smoke`` (default: ``--no-ws3-builtin-smoke``)
- ``--ws3-bridge-dir PATH`` (optional output directory for generated ws3 section files)
- ``--instance-root PATH``

``export release`` options

- ``--case-id TEXT`` (default: ``case``)
- ``--output-root PATH`` (default: ``releases``)
- ``--bundle-dir PATH`` (default: ``data/model_input_bundle``)
- ``--patchworks-dir PATH`` (default: ``output/patchworks_k3z_validated``)
- ``--woodstock-dir PATH`` (optional)
- ``--logs-dir PATH`` (default: ``runtime/logs``)
- ``--run-id TEXT`` (optional)
- ``--strict / --no-strict`` (default: ``--strict``)
- ``--instance-root PATH``

Patchworks Runtime
------------------

.. code-block:: text

   python -m femic patchworks [OPTIONS] COMMAND [ARGS]...

Use this command group when you want FEMIC to inspect or launch registry-backed
Patchworks variants, scenarios, and scenario sets, while still preserving the
lower-level ``run-headless <pin>`` primitive seam.

Subcommands

- ``preflight``: ``python -m femic patchworks preflight [OPTIONS]``
- ``instances list``: ``python -m femic patchworks instances list [OPTIONS]``
- ``build-blocks``: ``python -m femic patchworks build-blocks [OPTIONS]``
- ``matrix-build``: ``python -m femic patchworks matrix-build [OPTIONS]``
- ``run-headless``: ``python -m femic patchworks run-headless [OPTIONS] PIN``
- ``run-default-scenario``: ``python -m femic patchworks run-default-scenario [OPTIONS] VARIANT_ID``
- ``run-default-scenario-set``: ``python -m femic patchworks run-default-scenario-set [OPTIONS] INSTANCE_ID``
- ``run-scenario``: ``python -m femic patchworks run-scenario [OPTIONS] VARIANT_ID SCENARIO_ID``
- ``run-variant``: ``python -m femic patchworks run-variant [OPTIONS] VARIANT_ID``
- ``scenarios list``: ``python -m femic patchworks scenarios list [OPTIONS] VARIANT_ID``
- ``scenario-sets list``: ``python -m femic patchworks scenario-sets list [OPTIONS]``
- ``scenario-sets show``: ``python -m femic patchworks scenario-sets show [OPTIONS] SCENARIO_SET_ID``
- ``variants list``: ``python -m femic patchworks variants list [OPTIONS]``
- ``variants register``: ``python -m femic patchworks variants register [OPTIONS] VARIANT_ID``
- ``variants remove``: ``python -m femic patchworks variants remove [OPTIONS] VARIANT_ID``
- ``variants show``: ``python -m femic patchworks variants show [OPTIONS] VARIANT_ID``
- ``variants update``: ``python -m femic patchworks variants update [OPTIONS] VARIANT_ID``

``patchworks preflight`` options

- ``--config PATH`` (default: ``config/patchworks.runtime.yaml``)

``patchworks instances list`` options

- ``--registry PATH`` (default: ``~/.femic/variants.yaml``; built-ins always loaded)

``patchworks matrix-build`` options

- ``--config PATH`` (default: ``config/patchworks.runtime.yaml``)
- ``--instance-root PATH``
- ``--log-dir PATH`` (default: ``runtime/logs``)
- ``--run-id TEXT``
- ``--interactive``
- ``--instance-root PATH``

``patchworks build-blocks`` options

- ``--config PATH`` (default: ``config/patchworks.runtime.yaml``)
- ``--model-dir PATH`` (optional; inferred from runtime config when omitted)
- ``--fragments-shp PATH`` (optional; defaults to runtime fragments ``.shp``)
- ``--topology-radius FLOAT`` (default: ``200.0``)
- ``--with-topology / --no-topology`` (default: ``--with-topology``)
- ``--instance-root PATH``

``patchworks run-headless`` options

- ``PIN`` argument (required)
- ``--config PATH`` (default: ``config/patchworks.runtime.yaml``)
- ``--log-dir PATH`` (default: ``runtime/logs``)
- ``--run-id TEXT`` (optional)
- ``--stage-label TEXT`` (optional)
- ``--iterations INTEGER`` (default: ``1``)
- ``--improvement FLOAT`` (default: ``0.0``)
- ``--scenario-mode TEXT`` (default: ``none``)
- ``--scenario-target TEXT`` (optional)
- ``--scenario-min-annual FLOAT`` (optional)
- ``--instance-root PATH``

``patchworks run-variant`` options

- ``VARIANT_ID`` argument (required)
- ``--registry PATH`` (default: ``~/.femic/variants.yaml``; built-ins always loaded)
- ``--log-dir PATH`` (default: ``runtime/logs``)
- ``--run-id TEXT`` (optional)
- ``--stage-label TEXT`` (optional)
- ``--iterations INTEGER`` (default: ``1``)
- ``--improvement FLOAT`` (default: ``0.0``)
- ``--scenario-mode TEXT`` (default: ``none``)
- ``--scenario-target TEXT`` (optional)
- ``--scenario-min-annual FLOAT`` (optional)
- ``--allow-large-download`` (skip the materialization confirmation prompt when
  known estimated downloads exceed the threshold)
- ``--materialization-threshold-mib INTEGER`` (default: ``100``)

``patchworks scenarios list`` options

- ``VARIANT_ID`` argument (required)
- ``--registry PATH`` (default: ``~/.femic/variants.yaml``; built-ins always loaded)

``patchworks scenario-sets list`` options

- ``--registry PATH`` (default: ``~/.femic/variants.yaml``; built-ins always loaded)
- ``--instance-id TEXT`` (optional instance id filter)

``patchworks scenario-sets show`` options

- ``SCENARIO_SET_ID`` argument (required)
- ``--registry PATH`` (default: ``~/.femic/variants.yaml``; built-ins always loaded)

``patchworks run-scenario`` options

- ``VARIANT_ID`` argument (required)
- ``SCENARIO_ID`` argument (required)
- ``--registry PATH`` (default: ``~/.femic/variants.yaml``; built-ins always loaded)
- ``--log-dir PATH`` (default: ``runtime/logs``)
- ``--run-id TEXT`` (optional)
- ``--stage-label TEXT`` (optional override; falls back to the registry scenario when set there)
- ``--allow-large-download`` (skip the materialization confirmation prompt when
  known estimated downloads exceed the threshold)
- ``--materialization-threshold-mib INTEGER`` (default: ``100``)

``patchworks run-default-scenario`` options

- ``VARIANT_ID`` argument (required)
- ``--registry PATH`` (default: ``~/.femic/variants.yaml``; built-ins always loaded)
- ``--log-dir PATH`` (default: ``runtime/logs``)
- ``--run-id TEXT`` (optional)
- ``--stage-label TEXT`` (optional override; falls back to the registry default scenario when set there)
- ``--allow-large-download`` (skip the materialization confirmation prompt when
  known estimated downloads exceed the threshold)
- ``--materialization-threshold-mib INTEGER`` (default: ``100``)

``patchworks run-default-scenario-set`` options

- ``INSTANCE_ID`` argument (required)
- ``--registry PATH`` (default: ``~/.femic/variants.yaml``; built-ins always loaded)
- ``--log-dir PATH`` (default: ``runtime/logs``)
- ``--run-id TEXT`` (optional; step runs derive ``_01``, ``_02``, ...)
- ``--stage-label TEXT`` (optional; per-step stage labels derive ``_01``,
  ``_02``, ...)
- ``--allow-large-download`` (skip the materialization confirmation prompt when
  known estimated downloads exceed the threshold)
- ``--materialization-threshold-mib INTEGER`` (default: ``100``)

``patchworks run-scenario-set`` options

- ``SCENARIO_SET_ID`` argument (required)
- ``--registry PATH`` (default: ``~/.femic/variants.yaml``; built-ins always loaded)
- ``--log-dir PATH`` (default: ``runtime/logs``)
- ``--run-id TEXT`` (optional; step runs derive ``_01``, ``_02``, ...)
- ``--stage-label TEXT`` (optional; per-step stage labels derive ``_01``,
  ``_02``, ...)
- ``--allow-large-download`` (skip the materialization confirmation prompt when
  known estimated downloads exceed the threshold)
- ``--materialization-threshold-mib INTEGER`` (default: ``100``)

``patchworks variants list`` options

- ``--registry PATH`` (default: ``~/.femic/variants.yaml``; built-ins always loaded)
- ``--instance-id TEXT`` (optional filter)

``patchworks variants register`` options

- ``VARIANT_ID`` argument (required)
- ``--label TEXT`` (required)
- ``--instance-id TEXT`` (required)
- ``--instance-label TEXT`` (optional)
- ``--instance-root PATH`` (required)
- ``--analysis-pin PATH`` (required)
- ``--runtime-config PATH`` (required)
- ``--variant-family TEXT`` (default: ``default``)
- ``--kind TEXT`` (default: ``patchworks``)
- ``--default / --no-default`` (default: ``--no-default``)
- ``--registry PATH`` (default: ``~/.femic/variants.yaml``; writes the user overlay)

``patchworks variants update`` options

- ``VARIANT_ID`` argument (required)
- ``--label TEXT`` (optional)
- ``--instance-id TEXT`` (optional)
- ``--instance-label TEXT`` (optional)
- ``--instance-root PATH`` (optional)
- ``--analysis-pin PATH`` (optional)
- ``--runtime-config PATH`` (optional)
- ``--variant-family TEXT`` (optional)
- ``--kind TEXT`` (optional)
- ``--default BOOL`` (optional explicit override: ``true`` or ``false``)
- ``--registry PATH`` (default: ``~/.femic/variants.yaml``; writes the user overlay)

``patchworks variants remove`` options

- ``VARIANT_ID`` argument (required)
- ``--registry PATH`` (default: ``~/.femic/variants.yaml``; removes only user-overlay entries)

``patchworks variants show`` options

- ``VARIANT_ID`` argument (required)
- ``--registry PATH`` (default: ``~/.femic/variants.yaml``; built-ins always loaded)
- ``--materialization-threshold-mib INTEGER`` (default: ``100``; used when
  summarizing registry-declared materialization)

``patchworks variants materialization-plan`` options

- ``VARIANT_ID`` argument (required)
- ``--registry PATH`` (default: ``~/.femic/variants.yaml``; built-ins always loaded)
- ``--materialization-threshold-mib INTEGER`` (default: ``100``; used when
  deciding whether the current plan would require confirmation)

Both ``patchworks variants show`` and
``patchworks variants materialization-plan`` now print:

- one aggregate materialization summary;
- one dataset-root grouped summary per touched dataset; and
- the supporting raw per-action detail lines.

Operational notes:

- built-ins are always loaded from FEMIC's packaged registry;
- ``~/.femic/variants.yaml`` is a writable user overlay, not the only source
  of truth;
- launch-time materialization consent is driven by the grouped dataset summary
  before the raw per-action detail lines.

Instance Workspace
------------------

.. code-block:: text

   python -m femic instance [OPTIONS] COMMAND [ARGS]...

Subcommands

- ``init``: ``python -m femic instance init [OPTIONS]``
- ``config show``: ``python -m femic instance config show``
- ``config set-managed-external-root``:
  ``python -m femic instance config set-managed-external-root <path>``
- ``config set-user-instance-root``:
  ``python -m femic instance config set-user-instance-root <path>``
- ``builtins list``: ``python -m femic instance builtins list``
- ``builtins install``: ``python -m femic instance builtins install <builtin-id|all>``
- ``rebuild``: ``python -m femic instance rebuild [OPTIONS]``
- ``validate-spec``: ``python -m femic instance validate-spec [OPTIONS]``
- ``promote-evidence``: ``python -m femic instance promote-evidence [OPTIONS]``
- ``refresh-reference-evidence``: ``python -m femic instance refresh-reference-evidence [OPTIONS]``
- ``account-surface``: ``python -m femic instance account-surface [OPTIONS]``
- ``ws3-smoke``: ``python -m femic instance ws3-smoke [OPTIONS]``

``instance init`` options

- ``--instance-root PATH`` (optional; defaults to CWD)
- ``--instance-name TEXT`` (optional; create under configured visible user
  instance root; mutually exclusive with ``--instance-root``)
- ``--overwrite`` (overwrite existing scaffold template files)
- ``--download-bc-vri / --no-download-bc-vri`` (default: ``--download-bc-vri``)
- ``--yes`` / ``-y`` (assume yes for prompts)

``instance config show`` output

- current config path
- whether ``user.yaml`` exists yet
- resolved managed built-in root
- resolved visible user-instance root
- the default values FEMIC would use if the config file is absent

``instance builtins list`` output

- builtin id and label
- install status
- resolved install path
- standalone repo URL
- declared support-repo dependencies/notes

``instance builtins install`` behavior

- clones missing built-in repos into the configured managed built-in root
- clones declared support repos if missing
- skips already-installed git worktrees
- does **not** run ``datalad get`` automatically
- prints next-step guidance for payload materialization instead

Operational notes:

- packaged-install config now lives at ``~/.femic/user.yaml`` (or the Windows
  equivalent);
- FEMIC uses that config for managed built-ins and the visible user workspace
  root;
- normal operational runtime precedence is still
  ``--instance-root`` -> ``FEMIC_INSTANCE_ROOT`` -> current working directory.

``instance rebuild`` options

- ``--spec PATH`` (default: ``config/rebuild.spec.yaml``)
- ``--run-config PATH`` (default: ``config/run_profile.case_template.yaml``)
- ``--tipsy-config-dir PATH`` (default: ``config/tipsy``)
- ``--log-dir PATH`` (default: ``runtime/logs``)
- ``--run-id TEXT`` (optional; defaults to UTC timestamp)
- ``--with-patchworks / --no-patchworks`` (default: ``--no-patchworks``)
- ``--dry-run`` (print planned step sequence without execution)
- ``--patchworks-config PATH`` (default: ``config/patchworks.runtime.yaml``)
- ``--baseline PATH`` (default: ``config/rebuild.baseline.json``)
- ``--write-baseline`` (write/update baseline snapshot before diff evaluation)
- ``--allowlist PATH`` (default: ``config/rebuild.allowlist.yaml``)
- ``--instance-root PATH``

``instance rebuild`` writes a machine-readable report to
``runtime/logs/instance_rebuild_report-<run_id>.json`` and records discovered
manifest/log artifact references under ``artifact_references``.
It also writes ``diagnostics.account_surface`` when ``tracks/accounts.csv`` is
available, including a deterministic
``total_ok_species_empty_signature`` flag and recommended next checks.
It also evaluates configured rebuild-spec invariants and appends measured
``metrics`` plus ``invariant_results`` to the report. Any invariant with
``severity: fatal`` that evaluates false causes command failure with a
remediation summary.
When a baseline snapshot is available, the report also includes a ``baseline``
section with table/XML structural diffs and aggregate ``baseline_match`` /
``baseline_diff_count`` metrics. If an allowlist file is present, rebuild also
computes ``baseline_allowlist_match`` and ``baseline_unexpected_diff_count``
for explicit intentional-delta tracking.
Rebuild exits non-zero when unexpected baseline diffs exceed
``runtime.baseline_unexpected_diff_threshold`` from ``rebuild.spec.yaml``
(default ``0``), and writes ``regression_gate`` details into the report.

``instance validate-spec`` options

- ``--spec PATH`` (default: ``config/rebuild.spec.yaml``)
- ``--instance-root PATH``

``instance promote-evidence`` options

- ``--report PATH`` (optional; defaults to latest rebuild report in ``--log-dir``)
- ``--output PATH`` (default: ``evidence/reference_rebuild_report.latest.json``)
- ``--log-dir PATH`` (default: ``runtime/logs``)
- ``--max-warn-increase INT`` (optional drift warning threshold)
- ``--max-baseline-diff-increase INT`` (optional drift warning threshold)
- ``--instance-root PATH``

Promoted evidence summary also includes:

- ``summary.account_surface_total_ok_species_empty_signature``
- ``summary.account_surface_species_count``

``instance refresh-reference-evidence`` options

- ``--report PATH`` (optional; defaults to latest report in reference ``runtime/logs``)
- ``--reference-root PATH`` (default: ``instances/reference``)
- ``--max-warn-increase INT`` (optional drift warning threshold)
- ``--max-baseline-diff-increase INT`` (optional drift warning threshold)

``instance account-surface`` options

- ``--config PATH`` (default: ``config/patchworks.runtime.yaml``)
- ``--output PATH`` (optional JSON output path for diagnostics summary)
- ``--instance-root PATH``

``instance account-surface`` reads ``tracks/accounts.csv`` from the configured
Patchworks matrix output folder and summarizes species-level account coverage
(``product.Yield.managed.*`` and ``product.HarvestedVolume.managed.*.CC``)
plus AU-level seral account coverage.
When ``tracks/products.csv`` and ``tracks/curves.csv`` are available it also
computes a deterministic diagnosis for the
``total OK, species-wise empty`` failure signature and prints recommended
next-check steps.

``instance ws3-smoke`` options

- ``--woodstock-dir PATH`` (default: ``output/woodstock``)
- ``--output PATH`` (default: ``evidence/ws3_smoke_report.latest.json``)
- ``--ws3-command TEXT`` (optional shell command for ws3 simulation smoke)
- ``--ws3-workdir PATH`` (optional command working directory)
- ``--require-command / --allow-no-command`` (default: allow no command)
- ``--timeout-seconds INTEGER`` (default: ``600``)
- ``--ws3-repo-path PATH`` (optional local ws3 checkout path for builtin smoke)
- ``--builtin-model-smoke / --no-builtin-model-smoke`` (default: ``--builtin-model-smoke``)
- ``--ws3-bridge-dir PATH`` (optional output directory for generated ws3 section files)
- ``--instance-root PATH``
