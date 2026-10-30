Inventory ALS Predictions
=========================

This guide runs the INV-01 contract: apply a fitted area-based model to one
pinned FEMIC LiDAR product bundle and write the long ``inventory.als`` table.

The model card is external.  FEMIC does not invent coefficients or fit an ABA
model in this step.

Prerequisites
-------------

1. A validated FEMIC LiDAR bundle with a ``canopy`` table product or a ``chm``
   raster that can supply the grid feature table.
2. A JSON model card matching ``femic.inventory.als.model.v1``.
3. Optional plot/observation CSV for validation.

Run
---

.. code-block:: bash

   femic lidar inventory \
     --bundle data/lidar/product_bundle \
     --model metadata/inventory/my-aba-model.json \
     --output-dir data/lidar/inventory \
     --plots data/plots/p48_p49_validation.csv

To derive a 25 m CHM grid feature table from the bundle:

.. code-block:: bash

   femic lidar inventory-features \
     --bundle data/lidar/product_bundle \
     --output data/lidar/inventory/features_25m.csv \
     --grid-size-m 25

Then apply one model card to that table:

.. code-block:: bash

   femic lidar inventory \
     --bundle data/lidar/product_bundle \
     --features data/lidar/inventory/features_25m.csv \
     --model config/inventory/models/als_boreal_lorey_height_2012.json \
     --output-dir data/lidar/inventory/lorey_height \
     --fragment-id-field fragment_id

The command writes:

- ``inventory_als.csv`` — one row per fragment and attribute;
- ``inventory_als.json`` — bundle/model provenance, warnings, and caveats;
- ``inventory_als_validation.csv`` — only when ``--plots`` matches predictions.

The CLI prints the row count, model id, and validation RMSE when available.

Point-cloud grid features
-------------------------

For a first-return model, derive metrics directly from LAS/LAZ tiles instead of
using CHM proxies:

.. code-block:: bash

   femic lidar inventory-pointcloud-features \
     --pointcloud tile_a.laz \
     --pointcloud tile_b.laz \
     --dem dem.tif \
     --output features_25m.csv \
     --grid-size-m 25

The point clouds and DEM must share a CRS. The command needs the optional
``laspy[lazrs]`` dependency. It samples the DEM, normalizes first returns, and
writes ``Lhmean``, ``Lhcv``, ``Lhp95``, ``CC2m``, and return counts. Tiles must
not overlap; overlapping tiles would double-count cells.

Local CWH pilot
---------------

The local cards under ``config/inventory/models/als_cwh_*_2026.json`` were fit
to 14 public FAIB PSP plots with LidarBC 2023/2024 CHMs.  They are CWH northern
Vancouver Island pilots, not TSA 23 operational models.  Apply them only inside
the card's predictor ranges; for the TFL 6 pilot the forest mask used
``--min-cover-pct 34.5``.

.. code-block:: bash

   femic lidar inventory-features \
     --bundle <tfl6-bundle> \
     --output /tmp/inv01/features_25m_cwh.csv \
     --grid-size-m 25 \
     --min-cover-pct 34.5

   femic lidar inventory \
     --bundle <tfl6-bundle> \
     --features /tmp/inv01/features_25m_cwh.csv \
     --model config/inventory/models/als_cwh_lorey_height_2026.json \
     --output-dir /tmp/inv01/cwh_lorey_height \
     --fragment-id-field fragment_id

See ``notes/reports/inv01-cwh-local-model-tfl6.md`` for the fit diagnostics and
the VRI comparison, and :doc:`inv01-tsa23-full-run` for the full TSA 23
Globus/Sockeye runbook.

Published transfer benchmark
-----------------------------

The cards under ``config/inventory/models/`` encode the published Wulder et
al. (2012) boreal equations.  They are useful for exercising the contract and
for measuring transfer failure, not for an operational CWH inventory.  The
current TFL 6 pilot is CWH; the cards therefore emit an applicability warning.

Fixture
-------

Use the synthetic fixture only to test the contract:

.. code-block:: bash

   femic lidar inventory \
     --bundle tests/fixtures/lidar/bundle \
     --model tests/fixtures/lidar/inventory_model.json \
     --output-dir /tmp/lidar-inventory

That model is an identity ``lorey_height_m`` model, not an area-based inventory
estimate.  The unit tests build the bundle from
``tests/fixtures/lidar/product_plan.json``.

Validation
----------

The optional plot table must contain ``fragment_id``, ``attribute``, and
``observed``.  Predictions with no matching observation remain in the inventory
table but are excluded from the validation statistics.  No match is a warning,
not a pass.

Limits
------

- The default reader consumes the bundle's ``canopy`` table; ``--features``
  accepts an explicit fragment table.
- ``inventory-features`` derives CHM proxies, not first-return point-cloud
  metrics; use ``inventory-pointcloud-features`` for first-return metrics.
- ``--min-cover-pct`` filters non-forest grid cells before model application.
- The model card must carry its own training scope, RMSE, and predictor ranges.
- The reader refuses out-of-range predictors.
- The TSA/WS4 P48/P49 validation tables are not bundled in this repository.
- Point-cloud tiles must be non-overlapping; the extractor aggregates by grid
  cell and does not deduplicate overlapping acquisitions.
