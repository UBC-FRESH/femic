LiDAR Terrain Product Contract
==============================

Purpose
-------

This page is the short source-of-truth contract for FEMIC's native-grid terrain
and slope APIs. It defines the accepted raster inputs, slope semantics,
point-cloud gridder, zonal-statistics alignment rule, QA report fields, and the
no-silent-resampling boundary for P79.3.

Quick Contract
--------------

- QA schema: ``femic.lidar.terrain_qa.v1``.
- Dependency stack: ``numpy`` and ``rasterio`` from the core environment.
- Slope algorithm: Horn 3x3.
- Slope units: percent rise.
- Input CRS: projected metres, north-up, unrotated.
- Native resolution, CRS, transform, and extent are preserved.
- No reprojection, resampling, smoothing, or threshold decisions.
- Canopy and precision-forestry products are P79.7, not P79.3.

Input Contract
--------------

Terrain rasters must be single-band elevation surfaces. Slope inputs must also
have:

- a projected CRS whose linear units are metres;
- transform rotation terms ``b`` and ``d`` at zero;
- positive pixel resolution.

Inputs that fail these checks are rejected. FEMIC does not silently
reproject, resample, or rotate a terrain raster.

Slope Contract
--------------

``derive_slope_percent`` computes:

- ``dz/dx`` and ``dz/dy`` with the Horn 3x3 weights;
- ``slope_percent = 100 * sqrt((dz/dx)^2 + (dz/dy)^2)``.

Edge pixels use replicated neighbours. A pixel with any invalid neighbour is
nodata. The output profile preserves the source grid, CRS, transform, extent,
and native resolution, with float32 values and a recorded nodata value.

Point-Cloud Gridding
--------------------

``rasterize_point_cloud`` is a cell-aggregation core for points already held in
memory. Supported aggregations are ``min`` (DTM-like), ``max`` (DSM-like),
``mean``, and ``count``. Points outside the AOI or non-finite points are
ignored. Empty cells receive nodata.

This API does not read LAZ/COPC, classify ground returns, interpolate a
surface, or reproject points. Those are separate point-cloud concerns.

Zonal Statistics
----------------

``compute_zonal_statistics`` requires zones and values to share exactly the
same width, height, CRS, and transform. Misalignment is an error, never an
implicit resample.

Positive integer zone IDs are reported. Zero, negative, and nodata zones are
ignored. Supported statistics are ``count``, ``mean``, ``median``, ``min``,
``max``, ``std``, and ``sum``. Area hectares are included only for
projected-metre grids.

QA Report
---------

``build_terrain_products`` writes ``terrain_qa.json`` and
``terrain_qa.csv``. The JSON report records:

- schema version and generation time;
- source raster metadata;
- dependency stack;
- product paths and algorithms;
- slope parameters and edge handling;
- valid and nodata pixel counts;
- min, max, and mean values;
- warnings, including the no-reprojection and edge-replication notices.

The report is a review artifact. It does not apply instance-specific slope
thresholds or operability decisions.

No-Resampling Rule
------------------

A terrain product is rejected rather than normalized when:

- the CRS is geographic or not in metres;
- the raster is rotated;
- the resolution is not positive;
- zones and values are not exactly aligned.

Consumer-side reprojection, if required, is an explicit consumer decision with
its own lineage. The delivered terrain product keeps the source grid.

See Also
--------

- :doc:`../../guides/lidar-terrain-products`
- :doc:`lidar-source-and-tile-index`
- :doc:`../api/femic-lidar-terrain`
- :doc:`stage-boundaries-and-canonical-artifacts`
