Terrain Raster And Slope Products
=================================

Purpose
-------

This guide explains P79.3: how FEMIC derives native-grid terrain products from
existing DTM/DEM/DSM rasters, rasterizes sample points into DTM/DSM-like
surfaces, computes zonal statistics, and writes QA reports.

P79.3 does not read LAZ/COPC files, classify ground returns, reproject, or
resample silently. P79.2 materializes source tiles; P79.7 owns native canopy
and precision-forestry compilation.

Dependency Stack
----------------

P79.3 uses the existing core stack:

- ``numpy`` for arrays and statistics.
- ``rasterio`` for GeoTIFF I/O and CRS metadata.

No PDAL or laspy dependency is required. Callers that already hold sample
points can use the point-cloud gridder. Reading LAZ/COPC files belongs to a
later point-cloud lane rather than this raster API.

Accepted Inputs
----------------

Raster inputs must be single-band elevation rasters. Slope additionally
requires:

- a projected CRS with metre units;
- a north-up, unrotated transform;
- positive pixel resolution.

LidarBC native DEM/DSM products satisfy this contract. Geographic or rotated
rasters are rejected rather than reprojected silently.

Slope
-----

.. code-block:: python

   from pathlib import Path
   from femic.lidar.terrain import derive_slope_percent

   result = derive_slope_percent(
       Path("data/lidar/lidarbc/dem/layer_5/2023/dem.tif"),
       Path("data/lidar/products/slope_percent.tif"),
   )

The current algorithm is Horn's 3x3 method. Slope is percent rise
(``100 * vertical / horizontal``). Edge pixels use replicated neighbours. The
output preserves the source grid, CRS, transform, extent, and native
resolution.

No reprojection, resampling, smoothing, or thresholding occurs. Any
consumer-side reprojection is an explicit consumer decision.

Point-Cloud Gridding
--------------------

Use the gridder when sample points are already available:

.. code-block:: python

   from pathlib import Path
   from femic.lidar.terrain import rasterize_point_cloud

   result = rasterize_point_cloud(
       [(1148000.5, 391900.5, 812.3), (1148001.5, 391900.5, 809.9)],
       output_path=Path("data/lidar/products/dtm_candidate.tif"),
       bbox_epsg3005=(1148000, 391900, 1148100, 392000),
       resolution_m=1.0,
       aggregation="min",
   )

Aggregations are ``min`` (DTM-like), ``max`` (DSM-like), ``mean``, and
``count``. Empty cells receive the configured nodata value. This is a cell
aggregation core, not a ground-classification or interpolation workflow.

Zonal Statistics
----------------

Zones and values must share exactly the same grid and CRS. The helper rejects
misaligned inputs rather than resampling either raster.

.. code-block:: python

   from pathlib import Path
   from femic.lidar.terrain import compute_zonal_statistics

   result = compute_zonal_statistics(
       Path("data/zones.tif"),
       Path("data/lidar/products/slope_percent.tif"),
       statistics=("count", "mean", "median", "min", "max", "std"),
   )

Positive zone IDs are reported. Zero, negative, and nodata zones are ignored.
Area hectares are included only for projected-metre grids.

QA Reports
----------

``build_terrain_products`` writes the slope raster plus ``terrain_qa.json``
and ``terrain_qa.csv`` QA reports:

.. code-block:: python

   from pathlib import Path
   from femic.lidar.terrain import build_terrain_products

   report = build_terrain_products(
       Path("data/lidar/lidarbc/dem/layer_5/2023/dem.tif"),
       Path("data/lidar/terrain"),
   )

The QA report uses schema ``femic.lidar.terrain_qa.v1`` and records source
metadata, dependency stack, algorithm, parameters, valid/nodata pixel counts,
min/max/mean, warnings, and product paths. It is a review artifact, not a
model input.

Current Limits
--------------

- Only ``slope_percent`` is implemented as a named terrain product.
- Point-cloud gridding accepts in-memory points, not LAZ/COPC files.
- No reprojection, resampling, surface smoothing, or threshold decisions.
- Canopy and precision-forestry products remain P79.7.

See Also
--------

- :doc:`lidar-materialization`
- :doc:`lidar-product-bundles`
- :doc:`../reference/contracts/lidar-terrain-products`
- :doc:`../reference/api/femic-lidar-terrain`
- :doc:`../reference/contracts/lidar-source-and-tile-index`
