``femic.lidar.terrain`` Module
===============================

The :mod:`femic.lidar.terrain` module owns FEMIC's native-grid terrain raster
APIs. It derives percent slope, rasterizes in-memory sample points into
DTM/DSM-like surfaces, computes aligned zonal statistics, and writes JSON/CSV
QA reports. It does not reproject, resample, read LAZ/COPC, or apply
instance-specific thresholds.

Use this page when you are deriving or validating terrain products rather than
discovering, materializing, or packaging LiDAR inputs.

Start Here If...
----------------

Use this page first if you are trying to:

- derive slope from a native DTM/DEM;
- grid sample points into a DTM/DSM-like surface;
- compute zonal summaries over slope or elevation;
- inspect the QA report for a terrain build; or
- debug a rejected geographic, rotated, misaligned, or multiband input.

Typical Usage
-------------

.. code-block:: python

   from pathlib import Path
   from femic.lidar.terrain import (
       build_terrain_products,
       compute_zonal_statistics,
       derive_slope_percent,
       rasterize_point_cloud,
   )

   result = derive_slope_percent(
       Path("data/lidar/dem.tif"),
       Path("data/lidar/slope_percent.tif"),
   )
   report = build_terrain_products(
       Path("data/lidar/dem.tif"),
       Path("data/lidar/terrain"),
   )
   stats = compute_zonal_statistics(
       Path("data/zones.tif"),
       Path("data/lidar/slope_percent.tif"),
   )
   grid = rasterize_point_cloud(
       [(1148000.5, 391900.5, 812.3)],
       output_path=Path("data/lidar/dtm_candidate.tif"),
       bbox_epsg3005=(1148000, 391900, 1148100, 392000),
       resolution_m=1.0,
   )

Key Entry Surfaces
------------------

- :func:`inspect_terrain_raster`
  Read normalized CRS, transform, resolution, nodata, bounds, dtype, and band
  metadata.
- :func:`derive_slope_percent`
  Derive Horn 3x3 percent slope on the native grid.
- :func:`rasterize_point_cloud`
  Aggregate in-memory points into ``min``/``max``/``mean``/``count`` cells.
- :func:`compute_zonal_statistics`
  Compute aligned positive-zone statistics without resampling.
- :func:`build_terrain_products`
  Build the named terrain product set and write JSON/CSV QA reports.
- :class:`TerrainQaReport`
  Review artifact with source metadata, products, parameters, counts, and
  warnings.

Cross-References
----------------

- :doc:`../../guides/lidar-terrain-products`
- :doc:`../contracts/lidar-terrain-products`
- :doc:`femic-lidar`
- :doc:`femic-lidar-materialization`
- :doc:`femic-lidar-products`

.. toctree::
   :hidden:

   generated/femic.lidar.terrain

.. automodule:: femic.lidar.terrain
   :members:
   :undoc-members:
   :show-inheritance:
