``femic.bcdc_dwds`` Module
==========================

The :mod:`femic.bcdc_dwds` module owns FEMIC's heavier BCGW fallback lane for
BCDC datasets that need a DWDS order instead of a direct download or a
WFS-backed subset fetch. It sits beside :mod:`femic.bcdc_fetch`: resolve and
prefer WFS first, then use DWDS when the dataset needs a warehouse order and a
richer output format such as File Geodatabase or GeoPackage.

Use this page when you are debugging the public DWDS order payload, FGDB/GPKG
format selection, or the status/manifest caveats of the current public seam.
In particular, this is where to start if you need to understand why the public
`/order/{id}` seam did not return a clean live status after a successful order
submission.

Start Here If...
----------------

Use this page first if you are trying to:

- inspect how FEMIC builds a custom GML AOI from a bbox or Geomark-derived
  bbox;
- debug the public ``createOrderFiltered`` payload for a BCGW feature type;
- understand why a ``bcdc-order`` call chose FGDB vs GeoPackage output; or
- inspect the current caveat that the public `/order/{id}` seam may not
  resolve successful live orders cleanly.

Typical Usage
-------------

The common operator-facing entrypoint is:

.. code-block:: bash

   femic data bcdc-order WHSE_FOREST_VEGETATION.F_OWN --bbox 1170000,450000,1180000,460000

The matching Python entrypoints are:

.. code-block:: python

   from pathlib import Path
   from femic.bcdc_dwds import submit_bcdc_dwds_order, write_bcdc_dwds_manifest

   result = submit_bcdc_dwds_order(
       "WHSE_FOREST_VEGETATION.F_OWN",
       bbox_epsg3005=(1170000.0, 450000.0, 1180000.0, 460000.0),
       output_format="fgdb",
   )
   write_bcdc_dwds_manifest(result, Path("runtime/logs/f_own_dwds_manifest.json"))

Key Entry Surfaces
------------------

- :func:`submit_bcdc_dwds_order`
  Resolve a BCDC query, choose a BCGW feature type, and submit a public DWDS
  order for FGDB/GPKG/GeoJSON/shapefile output.
- :func:`write_bcdc_dwds_manifest`
  Persist one DWDS order result as JSON for later review or manual follow-up.

Cross-References
----------------

- :doc:`../../guides/bc-data-catalogue-discovery`
- :doc:`../../guides/data-access-inventory`
- :doc:`femic-bcdc-catalog`
- :doc:`femic-bcdc-fetch`
- :doc:`../cli`

.. toctree::
   :hidden:

   generated/femic.bcdc_dwds

.. automodule:: femic.bcdc_dwds
   :members:
   :undoc-members:
   :show-inheritance:
   :noindex:
