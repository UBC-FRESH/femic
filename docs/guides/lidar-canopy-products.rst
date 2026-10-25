Native Canopy And Precision-Forestry Products
=============================================

Purpose
-------

This guide explains P79.7: how FEMIC derives a native-resolution canopy height
model (CHM) from aligned DSM/DEM rasters, summarizes canopy height and cover,
compares CHM evidence with VRI inventory fields, and ingests optional
individual-tree products.

FEMIC does not implement a new individual-tree segmentation algorithm. Tree
products are consumed from existing public sources where coverage and quality
permit.

CHM From DSM And DEM
--------------------

.. code-block:: bash

   femic lidar canopy \
     --dem data/lidar/lidarbc/dem/layer_5/2024/dem.tif \
     --dsm data/lidar/lidarbc/dsm/layer_1/2024/dsm.tif \
     --output-dir data/lidar/canopy \
     --vertical-datum "Canadian Geodetic Vertical Datum of 2013"

The DSM and DEM must share exactly the same grid, CRS, transform, resolution,
and vertical datum. FEMIC rejects misaligned or different-CRS inputs rather
than resampling them.

The CHM is ``DSM - DEM``. Negative heights are clamped to zero by default and
counted in QA. Use ``--no-clamp-negative`` only for diagnostics.

Outputs:

.. code-block:: text

   <output-dir>/
     chm.tif
     canopy_structure.json
     canopy_qa.json
     canopy_qa.csv
     vri_canopy_comparison.csv   # when --vri is supplied

Canopy Structure
----------------

The canopy QA report uses schema ``femic.lidar.canopy_qa.v1``.
``canopy_structure.json`` records:

- valid/nodata pixels and area;
- min, mean, median, p90, p95, p99, and max height;
- cover percentages at 2, 5, 10, and 20 m.

The CHM and structure are native-grid products. No reprojection, resampling,
smoothing, or threshold promotion occurs.

VRI Comparison And Uncertainty
------------------------------

Use ``--vri`` to compare polygon-level CHM evidence with VRI height and cover:

.. code-block:: bash

   femic lidar canopy \
     --dem data/lidar/dem.tif \
     --dsm data/lidar/dsm.tif \
     --output-dir data/lidar/canopy \
     --vri data/input/tfl_6/vri_2025_r1_poly_tfl6.gpkg \
     --vri-height-field proj_height_1 \
     --vri-cover-field crown_closure \
     --vri-id-field feature_id

The comparison uses CHM p95 as the height metric and CHM cover at ``>=2 m`` as
the cover metric. It records per-polygon rows, bias, MAE, and RMSE.

This is uncertainty evidence, not a field-accuracy claim. VRI height and crown
closure are inventory estimates, and CHM cover at a 2 m threshold is not
equivalent to VRI crown closure.

Individual Tree Products
------------------------

Ingest an existing point product:

.. code-block:: bash

   femic lidar trees \
     --product data/lidar/trees/lidarbc_trees.gpkg \
     --output-dir data/lidar/trees

Required fields are ``tree_id`` and ``height_m``. Optional fields are
``crown_radius_m`` and ``species``. The command writes a JSON completeness
summary using schema ``femic.lidar.individual_tree.v1`` with duplicate IDs,
missing heights, height/crown distributions, and species counts.

Block summaries:

.. code-block:: bash

   femic lidar trees \
     --product data/lidar/trees/lidarbc_trees.gpkg \
     --blocks data/input/analysis_blocks.gpkg \
     --block-id-field block_id \
     --output-dir data/lidar/trees

Tree points outside all blocks are excluded and reported. Tree and block CRS
must already match.

TFL 6 Pilot Evidence
--------------------

A 1 km TFL 6 AOI used LidarBC 1 m DSM/DEM tiles:

- CHM mean 8.62 m, median 7.71 m, p90 18.96 m, p95 21.78 m, max 55.42 m.
- Cover: 70.94% at >=2 m, 60.09% at >=5 m, 41.03% at >=10 m, 7.84% at >=20 m.
- 95 negative pixels were clamped to zero.
- VRI comparison across 7 polygons: height bias -2.93 m, MAE 4.08 m, RMSE
  6.16 m; cover bias +23.87 percentage points, MAE 39.47 points.
- The LidarBC feature service has no CHM/canopy layer and no individual-tree
  layer. CHM was derived; individual-tree ingestion remains optional.

The cover disagreement is large enough that CHM cover at 2 m must not be
treated as VRI crown-closure equivalence. Height p95 is more comparable but
still variable.

Limitations
-----------

- No field-accuracy claim is made.
- CHM depends on DSM/DEM vintage and vertical-datum agreement.
- The feature service does not currently publish an individual-tree layer.
- No new segmentation algorithm is implemented.
- Point-cloud processing is optional and GPU is not required.

See Also
--------

- :doc:`lidar-terrain-products`
- :doc:`lidar-materialization`
- :doc:`../reference/contracts/lidar-canopy-products`
- :doc:`../reference/api/femic-lidar-canopy`
- :doc:`../reference/api/femic-lidar-trees`
