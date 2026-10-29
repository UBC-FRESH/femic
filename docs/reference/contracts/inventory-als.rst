Inventory ALS Contract
======================

Purpose
-------

This page defines the INV-01 area-based inventory prediction boundary.  FEMIC
does not fit an ABA model in this layer.  It consumes a pinned model card,
applies it to one pinned FEMIC LiDAR product bundle, and emits a long
``inventory.als`` table with provenance and model error.

The first implementation uses the bundle's ``canopy`` table product.  A future
producer can replace that table with fragment-level zonal statistics without
changing the output contract; that spatial join is deliberately not hidden in
this reader.

Schemas
-------

- Output table: ``femic.inventory.als.v1``
- Model card: ``femic.inventory.als.model.v1``
- Input bundle: ``femic.lidar.product.v1`` / ``femic.lidar.bundle.v1``

Output Table
------------

``inventory_als.csv`` has these required columns:

- ``fragment_id``
- ``attribute``
- ``value``
- ``model_id``
- ``rmse``

The writer also carries ``model_version``, ``unit``, and ``source`` so the
long table can be joined without guessing provenance.

Model Card
----------

A model card is JSON.  Coefficients are explicit; FEMIC never estimates them
from the bundle being predicted.

.. code-block:: json

   {
     "schema_version": "femic.inventory.als.model.v1",
     "model_id": "example-aba-volume",
     "model_version": "1.0.0",
     "attribute": "gross_volume_m3_per_ha",
     "unit": "m3/ha",
     "intercept": 0.0,
     "coefficients": {"chm_p95_m": 2.1, "canopy_cover_pct": 0.3},
     "rmse": 31.4,
     "sample_count": 120,
     "training_scope": "BEC and acquisition range you fitted for",
     "source": "publication or calibration report",
     "predictor_ranges": {
       "chm_p95_m": [2.0, 45.0],
       "canopy_cover_pct": [0.0, 100.0]
     },
     "caveats": ["Not validated outside the training range."]
   }

``predictor_ranges`` is optional but strongly recommended.  Predictions outside
a declared range are refused rather than silently extrapolated.

The fixture model in ``tests/fixtures/lidar/inventory_model.json`` is a
synthetic identity model used only to test the contract.  It is not an ABA
model and must not be used for inventory.

Bundle Prerequisite
-------------------

The bundle must validate against the LiDAR product-bundle contract and contain
a table product named ``canopy``.  The reader uses the manifest's
``relative_path``; it does not discover products or re-run materialization.
The manifest's ``bundle_id`` and ``bundle_version`` are recorded in the output.

Plot Validation
---------------

The optional validation lane accepts a CSV with:

- ``fragment_id``
- ``attribute``
- ``observed``

It writes predicted/observed/residual rows and bias, MAE, and RMSE.  The TSA/WS4
P48/P49 plot tables are the intended external validation source; no plot data
are bundled here.  A validation table with no matching rows is reported as a
warning, not treated as a successful validation.

Limits
------

- This is a **consumer** of a fitted model, not an ABA fitting implementation.
- The fixture canopy table is one row per LiDAR tile, not a real fragment map.
- No reprojection, resampling, or zonal-statistics step is implicit.
- A model card is only as credible as its documented training scope and error.
- No WS4/FHOPS objective, constraint, growth, or solver code is changed.

See Also
--------

- :doc:`lidar-product-bundle`
- :doc:`../../guides/lidar-inventory`
- :doc:`../api/femic-lidar-inventory`
