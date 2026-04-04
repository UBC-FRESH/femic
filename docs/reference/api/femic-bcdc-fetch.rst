``femic.bcdc_fetch`` Module
===========================

The :mod:`femic.bcdc_fetch` module owns FEMIC's first AOI-scoped geographic
acquisition path for BCDC layers that expose WFS-queryable OpenMaps services.
It sits one layer downstream of :mod:`femic.bcdc_catalog`: resolve first,
then fetch through WFS when the top match advertises
``suggested_fetch_strategy=wfs_getfeature_bbox``.

Use this page when you are debugging the actual WFS fetch path, Geomark AOI
normalization, or the GeoJSON/GeoPackage write behavior rather than the
catalogue search/ranking logic.

Start Here If...
----------------

Use this page first if you are trying to:

- inspect how FEMIC turns a Geomark reference into an EPSG:3005 bbox;
- debug the exact WFS ``GetFeature`` URL FEMIC builds for OpenMaps-backed
  layers;
- understand why a ``bcdc-fetch`` call wrote GeoJSON vs GeoPackage; or
- inspect why a resolved dataset was rejected as non-WFS-queryable and pushed
  back to ``femic data bcdc-resolve --download-direct`` or manual follow-up.

Typical Usage
-------------

The common operator-facing entrypoint is:

.. code-block:: bash

   femic data bcdc-fetch WHSE_FOREST_VEGETATION.F_OWN --bbox 1170000,450000,1180000,460000

The matching Python entrypoints are:

.. code-block:: python

   from pathlib import Path
   from femic.bcdc_fetch import (
       build_bbox_3005,
       fetch_bcdc_wfs_data,
       resolve_geomark_bbox_3005,
       write_bcdc_fetch_manifest,
   )

   bbox = build_bbox_3005("1170000,450000,1180000,460000")
   result = fetch_bcdc_wfs_data(
       "WHSE_FOREST_VEGETATION.F_OWN",
       destination_root=Path("downloads/bcdc"),
       bbox_epsg3005=bbox,
   )
   write_bcdc_fetch_manifest(result, Path("runtime/logs/f_own_fetch_manifest.json"))

Key Entry Surfaces
------------------

- :func:`build_bbox_3005`
  Parse and validate explicit AOI bboxes from the CLI.
- :func:`resolve_geomark_bbox_3005`
  Normalize a Geomark reference into an EPSG:3005 bbox for v1 WFS fetches.
- :func:`fetch_bcdc_wfs_data`
  Resolve a query, require a WFS-queryable service resource, request
  GeoJSON via WFS ``GetFeature``, and save local vector output.
- :func:`write_bcdc_fetch_manifest`
  Persist one WFS fetch result as JSON for later review or promotion.

Cross-References
----------------

- :doc:`../../guides/bc-data-catalogue-discovery`
- :doc:`../../guides/data-access-inventory`
- :doc:`../cli`

.. toctree::
   :hidden:

   generated/femic.bcdc_fetch

.. automodule:: femic.bcdc_fetch
   :members:
   :undoc-members:
   :show-inheritance:
   :noindex:
