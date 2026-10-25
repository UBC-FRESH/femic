Native Canopy And Tree Product Contract
=======================================

Purpose
-------

This page is the short source-of-truth contract for FEMIC's native CHM, canopy
structure, VRI uncertainty comparison, and optional individual-tree products.

Quick Contract
--------------

- Canopy QA schema: ``femic.lidar.canopy_qa.v1``.
- Individual-tree schema: ``femic.lidar.individual_tree.v1``.
- CHM: `DSM - DEM` on exactly aligned native grids.
- CHM negative heights: clamped by default and counted.
- CHM cover thresholds: 2, 5, 10, and 20 m.
- VRI height metric: CHM p95.
- VRI cover metric: CHM cover at >=2 m.
- No reprojection or resampling.
- No new individual-tree segmentation algorithm.
- No field-accuracy claim.

CHM Contract
------------

DSM and DEM must share:

- width and height;
- CRS;
- transform and native resolution;
- projected metre units;
- vertical datum.

Misaligned or geographic inputs are rejected. The CHM preserves the DSM grid
and writes float32 values with a recorded nodata value. Negative ``DSM-DEM``
pixels are clamped to zero by default, counted, and warned about.

Canopy Structure Contract
-------------------------

The canopy structure report records:

- valid and nodata pixels;
- valid area hectares;
- min, mean, median, p90, p95, p99, and max height;
- percent cover at the configured thresholds.

The report is derived from the CHM, not a field inventory.

VRI Comparison Contract
-----------------------

VRI polygons must already match the CHM CRS. FEMIC clips each polygon to the
CHM, requires a minimum valid-pixel count, and records:

- polygon ID, VRI height, CHM p95, CHM mean, and height delta;
- VRI cover, CHM cover at >=2 m, and cover delta;
- valid-pixel count;
- height bias, MAE, and RMSE;
- cover bias and MAE.

Polygons outside the CHM or with too few valid pixels are skipped and counted.
The comparison is uncertainty evidence, not proof of field accuracy.

Individual Tree Contract
------------------------

An individual-tree product is optional. It must be point-based, have a CRS, and
carry:

- required ``tree_id`` and ``height_m``;
- optional ``crown_radius_m`` and ``species``.

The summary records feature count, unique tree count, duplicate IDs, missing
heights, height/crown distributions, species counts, geometry types, and
warnings. Block summaries require tree and block CRS to match; trees outside all
blocks are excluded and reported.

FEMIC does not implement tree segmentation. A source without a suitable public
tree product is not given a synthetic one.

No-Resampling Rule
------------------

The canopy and tree workflows reject:

- DSM/DEM grid or CRS mismatch;
- geographic or non-metre CHM inputs;
- VRI polygons in a different CRS;
- tree/block CRS mismatch.

Consumer-side reprojection, if needed, is an explicit separate decision.

See Also
--------

- :doc:`../../guides/lidar-canopy-products`
- :doc:`lidar-terrain-products`
- :doc:`../api/femic-lidar-canopy`
- :doc:`../api/femic-lidar-trees`
- :doc:`stage-boundaries-and-canonical-artifacts`
