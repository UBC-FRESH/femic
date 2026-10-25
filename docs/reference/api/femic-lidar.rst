``femic.lidar.catalog`` Module
===============================

The :mod:`femic.lidar.catalog` module owns FEMIC's LidarBC discovery contract.
It describes the public source family, maps FEMIC products to direct tile
layers, normalizes tile-index records, selects tiles for a BC Albers AOI,
records every paginated request, and writes a provenance-carrying selection
manifest. It does not download tile bytes or process rasters.

Use this page when you are debugging LidarBC selection or the provenance
fields that later product packaging depends on.

Start Here If...
----------------

Use this page first if you are trying to:

- understand which LidarBC layers feed ``point_cloud``, ``dem``, and ``dsm``;
- debug an AOI that returns no tiles or too many tiles;
- inspect the licence, CRS, vertical datum, and accuracy metadata that travel
  with a selected tile; or
- extend the selection manifest before P79.8 packages a product bundle.

Typical Usage
-------------

.. code-block:: python

   from pathlib import Path
   from femic.lidar import discover_lidarbc_tiles, write_lidar_selection_manifest

   selection = discover_lidarbc_tiles(
       (1148000, 391900, 1149900, 393500),
       ("point_cloud", "dem", "dsm"),
   )
   write_lidar_selection_manifest(
       selection,
       Path("metadata/lidar/lidarbc_selection.json"),
   )

Key Entry Surfaces
------------------

- :data:`LIDARBC_SOURCE`
  Frozen source-family descriptor with portal, catalogue, index, licence,
  native CRS, supported/derived products, and storage boundary.
- :func:`lidarbc_layers_for_product`
  Map a direct FEMIC product to its LidarBC tile-index layers.
- :func:`normalize_bbox_epsg3005`
  Validate a BC Albers AOI bounding box.
- :func:`bbox_intersects`
  Test positive-area overlap, excluding edge-touching tiles.
- :func:`tile_from_arcgis_feature`
  Normalize one feature-service record into a :class:`LidarTile`.
- :func:`discover_lidarbc_tiles`
  Discover all selected tiles for an AOI and product set.
- :func:`write_lidar_selection_manifest`
  Persist the selection as reviewed JSON.

Cross-References
----------------

- :doc:`../../guides/lidar-data-products`
- :doc:`../contracts/lidar-source-and-tile-index`
- :doc:`../cli`

.. toctree::
   :hidden:

   generated/femic.lidar.catalog

.. automodule:: femic.lidar.catalog
   :members:
   :undoc-members:
   :show-inheritance:
