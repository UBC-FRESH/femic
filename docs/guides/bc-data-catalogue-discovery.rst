BC Data Catalogue Discovery
===========================

Purpose
-------

Use ``femic data bcdc-resolve`` when a TSR data-package source list gives you
one or more likely BC Data Catalogue / BCGW layer names and you want FEMIC to:

- find the best matching catalogue package;
- classify the package resources into direct downloads, services, indirect
  custom-download surfaces, or supporting documents; and
- optionally download only the stable direct-access data resources.

This guide is intentionally about discovery and first-pass collection only. It
does **not** parse PDF source lists automatically, and it does **not** promote
discovered results directly into ``metadata/required_datasets.yaml``.

Minimal Workflow
----------------

Start from explicit layer names or keywords copied from a TSR source-data
section, for example ``WHSE_FOREST_VEGETATION.F_OWN`` from a BC forestry source
list.

Resolve candidates only:

.. code-block:: bash

   femic data bcdc-resolve WHSE_FOREST_VEGETATION.F_OWN

Write a machine-readable candidate manifest for later review:

.. code-block:: bash

   femic data bcdc-resolve \
     WHSE_FOREST_VEGETATION.F_OWN \
     --manifest-path runtime/logs/bcdc_f_own_manifest.json

Opt into the easy direct-download subset only:

.. code-block:: bash

   femic data bcdc-resolve \
     WHSE_FOREST_VEGETATION.F_OWN \
     --download-direct \
     --download-root data/downloads/bcdc \
     --manifest-path runtime/logs/bcdc_f_own_manifest.json

When ``--instance-root`` is supplied, FEMIC resolves relative paths against the
instance workspace and defaults direct downloads under ``data/downloads/bcdc``.

Concrete Examples
-----------------

Resolve-only example with a clean exact object-name hit:

.. code-block:: text

   & .\.venv\Scripts\python.exe -m femic data bcdc-resolve WHSE_FOREST_VEGETATION.F_OWN

Typical outcome:

- top match resolves to ``Generalized Forest Cover Ownership``;
- service resources are listed;
- WFS-capable OpenMaps services are now surfaced with a suggested fetch
  strategy when FEMIC can probe them successfully;
- the BCGW custom-download seam is identified as
  ``indirect_custom_download``; and
- supporting PDF documentation is surfaced for manual review.

Direct-download-capable example:

.. code-block:: text

   & .\.venv\Scripts\python.exe -m femic data bcdc-resolve SITE_PROD_BC

That query currently exposes direct-download candidates for the provincial site
productivity package. To actually exercise the v1 download capability, follow
up with:

.. code-block:: text

   & .\.venv\Scripts\python.exe -m femic data bcdc-resolve SITE_PROD_BC `
     --download-direct `
     --download-root data\downloads\bcdc `
     --manifest-path runtime\logs\bcdc_site_prod_bc_manifest.json

Another direct-download-capable example is the VRI R1 layer:

.. code-block:: text

   & .\.venv\Scripts\python.exe -m femic data bcdc-resolve `
     WHSE_FOREST_VEGETATION.VEG_COMP_LYR_R1_POLY `
     --download-direct `
     --download-root data\downloads\bcdc `
     --manifest-path runtime\logs\bcdc_vri_r1_manifest.json

WFS-backed acquisition example using the new ``bcdc-fetch`` path:

.. code-block:: text

   & .\.venv\Scripts\python.exe -m femic data bcdc-fetch `
     WHSE_FOREST_VEGETATION.F_OWN `
     --bbox 1170000,450000,1180000,460000 `
     --output-format gpkg `
     --download-root data\downloads\bcdc `
     --manifest-path runtime\logs\bcdc_f_own_fetch_manifest.json

That path is intended for datasets that do **not** expose a simple direct file
download, but *do* expose a WFS-queryable OpenMaps service. For F_OWN, FEMIC
can now resolve the catalogue package, detect that the OpenMaps ``ows`` service
is WFS-queryable, normalize the AOI from ``--bbox`` or ``--geomark``, and save
a local GeoPackage or GeoJSON subset instead of dropping you directly into the
manual BCGW UI.

Worked Example: F_OWN to a Local GeoPackage
-------------------------------------------

This is the cleanest current example of the full WFS-first path.

1. resolve the layer and inspect the service hints:

   .. code-block:: text

      & .\.venv\Scripts\python.exe -m femic data bcdc-resolve `
        WHSE_FOREST_VEGETATION.F_OWN `
        --manifest-path runtime\logs\bcdc_f_own_manifest.json

2. confirm the top match reports:

   - ``service_type=openmaps_ows``
   - ``wfs_queryable=True``
   - ``wfs_typename=pub:WHSE_FOREST_VEGETATION.F_OWN``
   - ``suggested_fetch_strategy=wfs_getfeature_bbox``

3. fetch a local subset using an explicit BC Albers bbox:

   .. code-block:: text

      & .\.venv\Scripts\python.exe -m femic data bcdc-fetch `
        WHSE_FOREST_VEGETATION.F_OWN `
        --bbox 1170000,450000,1180000,460000 `
        --output-format gpkg `
        --download-root data\downloads\bcdc `
        --manifest-path runtime\logs\bcdc_f_own_fetch_manifest.json

4. inspect the outputs:

   - local vector file under ``data/downloads/bcdc/WHSE_FOREST_VEGETATION_F_OWN/``
   - JSON manifest at ``runtime/logs/bcdc_f_own_fetch_manifest.json``

This is the intended path when a dataset has no clean direct-download URL but
does expose a WFS-queryable OpenMaps service.

Batch Input from a Query File
-----------------------------

When working through a TSR source list on Windows, a query file is usually more
reliable than a large interactive paste.

Create a text file with one query per line. Blank lines and ``#`` comments are
ignored.

Example ``runtime/logs/williams_lake_table2_queries.txt``:

.. code-block:: text

   # Williams Lake Table 2 sample
   WHSE_FOREST_VEGETATION.F_OWN
   WHSE_ADMIN_BOUNDARIES.FADM_TSA
   CONSOLIDATED_CUTBLOCKS_2011

Then run:

.. code-block:: text

   & .\.venv\Scripts\python.exe -m femic data bcdc-resolve `
     --query-file runtime\logs\williams_lake_table2_queries.txt `
     --manifest-path runtime\logs\williams_lake_table2_manifest.json

If you want a quick review surface before opening the full JSON manifest, also
write a one-row-per-query CSV summary:

.. code-block:: text

   & .\.venv\Scripts\python.exe -m femic data bcdc-resolve `
     --query-file runtime\logs\williams_lake_table2_queries.txt `
     --summary-csv runtime\logs\williams_lake_table2_summary.csv `
     --manifest-path runtime\logs\williams_lake_table2_manifest.json

The CSV summary is intended for fast triage of larger source lists. It records
the original query, top match title, dataset page URL, whether an alias was
used, whether direct-download candidates exist, and whether the top match is
mostly service/custom-download/document driven.

The first follow-on slice after issue `#98` also adds a small curated alias
path for known forestry naming drift. For example,
``CONSOLIDATED_CUTBLOCKS_2011`` now retries through the cleaner
``CONSOLIDATED_CUTBLOCKS`` query variant before giving up.

PowerShell Notes
----------------

Quote multi-word free-text queries so PowerShell passes them as one query
instead of splitting them into multiple positional arguments:

.. code-block:: text

   & .\.venv\Scripts\python.exe -m femic data bcdc-resolve "Silviculture Activities History"

Prefer one query per command or use a script file when working through large
TSR source lists. Large multiline interactive pastes can trigger noisy
``PSReadLine`` rendering failures that are unrelated to FEMIC itself.

Classification Buckets
----------------------

The v1 resolver classifies discovered resources into one of these buckets:

- ``direct_data_download``
  stable direct-access data URL; eligible for opt-in download in v1
- ``service``
  WMS/KML/service surface; inspect manually rather than treating it as a file
  download
- ``indirect_custom_download``
  BC Geographic Warehouse custom-download flow or similar indirect-access seam;
  follow the dataset page manually
- ``supporting_document``
  PDF or documentation-like resource; useful context, but not auto-downloaded
- ``unknown``
  FEMIC could not classify the resource confidently in v1

For many forestry datasets, a package may expose more than one class at the
same time. For example, one package can expose service endpoints, BCGW custom
download surfaces, and supporting PDF documentation together.

Service Automation Hints
------------------------

Some ``service`` resources now carry machine-readable hints for later
automation, especially when they point at an OpenMaps ``.../ows`` endpoint.

When FEMIC can prove that a service resource is WFS-queryable, the resolver
will surface hints such as:

- ``service_type`` (for example ``openmaps_ows``)
- ``wfs_queryable``
- ``wfs_capabilities_url``
- ``wfs_typename``
- ``suggested_fetch_strategy`` (currently
  ``wfs_getfeature_bbox`` when the OpenMaps service advertises a matching
  feature type)

This does not yet replace ``femic data bcdc-resolve`` with a download path by
itself, but it gives the next acquisition layer enough structured information
to automate AOI-scoped fetches without making users rediscover the service seam
manually.

AOI-Scoped WFS Fetch
--------------------

When ``femic data bcdc-resolve`` reports a WFS-capable service hint, follow up
with ``femic data bcdc-fetch``.

The v1 fetch path accepts exactly one AOI input:

- ``--bbox minx,miny,maxx,maxy`` in ``EPSG:3005``; or
- ``--geomark`` as either a full Geomark URL or a bare Geomark ID.

Example with explicit bbox:

.. code-block:: text

   & .\.venv\Scripts\python.exe -m femic data bcdc-fetch `
     WHSE_FOREST_VEGETATION.F_OWN `
     --bbox 1170000,450000,1180000,460000 `
     --output-format gpkg

Example with Geomark:

.. code-block:: text

   & .\.venv\Scripts\python.exe -m femic data bcdc-fetch `
     WHSE_FOREST_VEGETATION.F_OWN `
     --geomark gm-abcdefghijklmnopqrstuvwxyz0000bc `
     --output-format geojson

The intended split is:

- ``bcdc-resolve`` = discovery and classification;
- ``bcdc-fetch`` = automatable WFS subset download; and
- ``bcdc-order`` = DWDS fallback order submission for datasets that need a
  warehouse order and richer outputs such as File Geodatabase or GeoPackage.

DWDS / FGDB Fallback
--------------------

When a dataset cannot be fetched cleanly through WFS, or when you explicitly
want a richer warehouse output such as File Geodatabase, use
``femic data bcdc-order``.

Example ``F_OWN`` fallback order:

.. code-block:: text

   & .\.venv\Scripts\python.exe -m femic data bcdc-order `
     WHSE_FOREST_VEGETATION.F_OWN `
     --bbox 1170000,450000,1180000,460000 `
     --output-format fgdb `
     --manifest-path runtime\logs\bcdc_f_own_dwds_manifest.json

This path currently does three useful things:

- resolves the top BCDC package and BCGW feature type;
- submits a public DWDS order for the requested output format; and
- writes a manifest recording the order id, order guid, AOI, payload, and any
  public-status caveats.

Current caveats of the public fallback seam:

- FEMIC submits the order through the public ``createOrderFiltered`` endpoint
  using a raw JSON body, because that is the live shape that actually worked in
  probes;
- ``--geomark`` is currently normalized to a bbox-derived custom GML AOI for
  reliable order submission rather than being passed through directly to DWDS;
  and
- the public ``/order/{id}`` status lookup may still report successful live
  orders as missing, so the manifest should be treated as the durable record of
  submission until that seam is better behaved.

Worked Example: TSA29 Query File to Local Layers
------------------------------------------------

The TSA29-friendly path starts from a reviewed query file rather than a large
interactive paste.

1. start from a reviewed source-layer query file, for example:

   - ``runtime/logs/tsa29_tsr_source_layers.txt``

2. resolve the reviewed candidates into a triage manifest and summary CSV:

   .. code-block:: text

      & .\.venv\Scripts\python.exe -m femic data bcdc-resolve `
        --query-file runtime\logs\tsa29_tsr_source_layers.txt `
        --summary-csv runtime\logs\tsa29_tsr_source_layers_summary.csv `
        --manifest-path runtime\logs\tsa29_tsr_source_layers_manifest.json

3. from the summary/manifest, identify which approved rows are:

   - ``direct_data_download`` and should use ``--download-direct``; versus
   - WFS-queryable service rows and should use ``bcdc-fetch``.

4. fetch a WFS-queryable reviewed layer directly. For example, if
   ``WHSE_FOREST_VEGETATION.F_OWN`` is on the approved TSA29 list:

   .. code-block:: text

      & .\.venv\Scripts\python.exe -m femic data bcdc-fetch `
        WHSE_FOREST_VEGETATION.F_OWN `
        --bbox 1170000,450000,1180000,460000 `
        --output-format gpkg `
        --download-root data\downloads\bcdc `
        --manifest-path runtime\logs\tsa29_f_own_fetch_manifest.json

5. for reviewed direct-download rows such as ``SITE_PROD_BC``, stay on the
   direct-download path instead:

   .. code-block:: text

      & .\.venv\Scripts\python.exe -m femic data bcdc-resolve `
        SITE_PROD_BC `
        --download-direct `
        --download-root data\downloads\bcdc `
        --manifest-path runtime\logs\bcdc_site_prod_bc_manifest.json

This keeps TSA29 acquisition practical:

- review with query files and CSVs;
- fetch WFS-backed layers through ``bcdc-fetch``; and
- use ``bcdc-order`` when a reviewed layer needs a warehouse order and a
  richer output such as FGDB; and
- use ``--download-direct`` only where the dataset actually exposes a clean
  file-download surface.

Manifest Output
---------------

The candidate manifest is the durable output of this first slice. It records:

- the original query string;
- the BC Data Catalogue API URLs used;
- ranked package matches;
- normalized resource classifications;
- the chosen top match; and
- any WFS/OpenMaps service automation hints discovered during probing; and
- any direct-download attempts and outcomes.

The new ``bcdc-fetch`` manifest records:

- the chosen package and WFS-capable service resource;
- the AOI source (bbox vs Geomark);
- the normalized ``EPSG:3005`` bbox;
- the exact WFS ``GetFeature`` request URL;
- the saved local vector path;
- the output format; and
- the returned feature count.

The new ``bcdc-order`` manifest records:

- the chosen package/resource and BCGW feature type;
- the AOI source (bbox vs geomark-derived bbox);
- the normalized ``EPSG:3005`` bbox;
- the DWDS order payload and ordering application;
- the returned order id and order guid; and
- any warnings from the public status probe.

Use that manifest as a review/promotion artifact before touching
``metadata/required_datasets.yaml`` or copying payloads into
``external/femic-public-data``.

Promotion Path
--------------

The intended v1 workflow is:

1. resolve/query candidate datasets with ``femic data bcdc-resolve``;
2. inspect the manifest and dataset page(s);
3. decide whether the discovered dataset belongs in
   ``metadata/required_datasets.yaml`` or a case-specific contract;
4. stage or archive the approved payload through the normal data-management
   workflow.

This keeps discovery separate from promotion, which is especially important
for indirect/custom-download datasets and ambiguous source-list wording.

Related References
------------------

- :doc:`data-access-inventory`
- :doc:`public-data-mirror-runbook`
- :doc:`../reference/cli`
