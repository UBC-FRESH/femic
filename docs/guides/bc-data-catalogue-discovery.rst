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

Manifest Output
---------------

The candidate manifest is the durable output of this first slice. It records:

- the original query string;
- the BC Data Catalogue API URLs used;
- ranked package matches;
- normalized resource classifications;
- the chosen top match; and
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
