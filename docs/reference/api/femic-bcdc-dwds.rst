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
submission, or how FEMIC follows up on an existing DWDS manifest to retry the
status probe and materialize the artifact when a download URL appears. This
now also covers the stronger retrieval seam discovered in live TSA29 use:

- DWDS may email an ``pickupByGUID`` launcher URL rather than exposing a clean
  public ``/order/{id}`` download URL;
- that launcher page is HTML, not the final package; and
- FEMIC can now follow the launcher to the real
  ``distribution.data.gov.bc.ca`` zip when the order has been assembled.

Start Here If...
----------------

Use this page first if you are trying to:

- inspect how FEMIC builds a custom GML AOI from a bbox or Geomark-derived
  bbox;
- debug the public ``createOrderFiltered`` payload for a BCGW feature type;
- understand why a ``bcdc-order`` call chose FGDB vs GeoPackage output; or
- inspect the current caveat that the public `/order/{id}` seam may not
  resolve successful live orders cleanly, even though ``bcdc-order-followup``
  can now retry that seam later and, when necessary, pivot through the
  emailed ``pickupByGUID`` launcher page to materialize the artifact.
- understand how FEMIC resolves the DWDS notification email when ``--email``
  is omitted (explicit flag first, then ``FEMIC_BCDC_DWDS_EMAIL``, then
  ``git config user.email``).

Typical Usage
-------------

The common operator-facing entrypoint is:

.. code-block:: bash

   femic data bcdc-order WHSE_FOREST_VEGETATION.F_OWN --bbox 1170000,450000,1180000,460000

The matching Python entrypoints are:

.. code-block:: python

   from pathlib import Path
   from femic.bcdc_dwds import (
       follow_up_bcdc_dwds_order,
       load_bcdc_dwds_manifest,
       submit_bcdc_dwds_order,
       write_bcdc_dwds_manifest,
   )

   result = submit_bcdc_dwds_order(
       "WHSE_FOREST_VEGETATION.F_OWN",
       bbox_epsg3005=(1170000.0, 450000.0, 1180000.0, 460000.0),
       output_format="fgdb",
   )
   write_bcdc_dwds_manifest(result, Path("runtime/logs/f_own_dwds_manifest.json"))

   saved = follow_up_bcdc_dwds_order(
       load_bcdc_dwds_manifest(Path("runtime/logs/f_own_dwds_manifest.json"))[0],
       download_root=Path("downloads/bcdc"),
   )
   write_bcdc_dwds_manifest(saved, Path("runtime/logs/f_own_dwds_manifest.json"))

Key Entry Surfaces
------------------

- :func:`submit_bcdc_dwds_order`
  Resolve a BCDC query, choose a BCGW feature type, and submit a public DWDS
  order for FGDB/GPKG/GeoJSON/shapefile output.
- :func:`load_bcdc_dwds_manifest`
  Reload one or more previously submitted DWDS orders from a FEMIC manifest.
- :func:`follow_up_bcdc_dwds_order`
  Re-probe one submitted DWDS order and materialize its artifact when DWDS
  exposes a download URL, or when the saved ``order_guid`` can be used to
  resolve the emailed ``pickupByGUID`` launcher page into the real
  distribution zip URL.
- :func:`write_bcdc_dwds_manifest`
  Persist one DWDS order result as JSON for later review or follow-up retries.

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
