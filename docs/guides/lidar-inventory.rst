Inventory ALS Predictions
=========================

This guide runs the INV-01 contract: apply a fitted area-based model to one
pinned FEMIC LiDAR product bundle and write the long ``inventory.als`` table.

The model card is external.  FEMIC does not invent coefficients or fit an ABA
model in this step.

Prerequisites
-------------

1. A validated FEMIC LiDAR bundle with a ``canopy`` table product.
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

The command writes:

- ``inventory_als.csv`` — one row per fragment and attribute;
- ``inventory_als.json`` — bundle/model provenance, warnings, and caveats;
- ``inventory_als_validation.csv`` — only when ``--plots`` matches predictions.

The CLI prints the row count, model id, and validation RMSE when available.

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

- The current reader consumes the bundle's ``canopy`` table; it does not compute
  fragment zonal statistics.
- The model card must carry its own training scope, RMSE, and predictor ranges.
- The reader refuses out-of-range predictors.
- The TSA/WS4 P48/P49 validation tables are not bundled in this repository.
