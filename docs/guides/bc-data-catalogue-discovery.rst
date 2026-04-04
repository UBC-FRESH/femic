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
