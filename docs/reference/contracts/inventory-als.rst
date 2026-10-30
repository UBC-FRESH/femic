Inventory ALS Contract
======================

Purpose
-------

This page defines the INV-01 area-based inventory prediction boundary.  FEMIC
does not fit an ABA model in this layer.  It consumes a pinned model card,
applies it to one pinned FEMIC LiDAR product bundle, and emits a long
``inventory.als`` table with provenance and model error.

The reader accepts the bundle's ``canopy`` table product or an explicit feature
CSV (``--features``).  The ``inventory-features`` helper can derive a 25 m CHM
grid feature table from a bundle ``chm`` product.  The spatial join is
deliberately explicit: the reader does not silently invent fragments.

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
long table can be joined without guessing provenance.  When ``--features`` is
used, the output manifest records the feature-table path and SHA-256.

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
     "link": "log",
     "output_scale": 16.0,
     "intercept": -2.7,
     "coefficients": {"chm_p95_m": 1.4, "canopy_cover_pct": 0.29},
     "rmse": 31.4,
     "sample_count": 120,
     "training_scope": "BEC and acquisition range you fitted for",
     "source": "publication or calibration report",
     "applicability": {
       "regions": ["BEC zone or training domain"],
       "species": ["species group"],
       "notes": "Do not apply outside this domain without a transfer test."
     },
     "predictor_ranges": {
       "chm_p95_m": [2.0, 45.0],
       "canopy_cover_pct": [0.0, 100.0]
     },
     "caveats": ["Not validated outside the training range."]
   }

``link`` is ``identity`` by default or ``log`` for equations of the form
``exp(intercept + sum(coefficient * ln(predictor)))``.  ``output_scale``
converts the published plot total to the declared attribute unit; it defaults
to ``1.0``.  For example, the published boreal Wulder et al. (2012) basal-area
and volume equations predict 25 x 25 m plot totals, so their cards use
``output_scale: 16.0`` to report per hectare.

``predictor_ranges`` is optional but strongly recommended.  Predictions outside
a declared range are refused rather than silently extrapolated.  An
``applicability`` block is metadata only; the reader records a warning that the
bundle region was not verified.

The fixture model in ``tests/fixtures/lidar/inventory_model.json`` is a
synthetic identity model used only to test the contract.  It is not an ABA
model and must not be used for inventory.

Published cards live under ``config/inventory/models/``.  The current boreal
cards are a transfer benchmark, not a CWH/TSA 23 operational model:

- ``als_boreal_lorey_height_2012.json``
- ``als_boreal_basal_area_2012.json``
- ``als_boreal_gross_volume_2012.json``

They use the published equations in Wulder et al. (2012), *Canadian Journal of
Remote Sensing* 38(5): 600-618, https://doi.org/10.5589/m12-049.  Their
applicability domain is boreal Canada; applying them to the CWH TFL 6 pilot is
a transfer test.  The CHM grid helper is also a proxy for the published
first-return metrics, not an exact reconstruction.

The local CWH pilot cards are also metadata-complete cards, but they are
FEMIC fits rather than published models:

- ``als_cwh_lorey_height_2026.json``
- ``als_cwh_basal_area_2026.json``
- ``als_cwh_gross_volume_2026.json``

They use 14 public FAIB PSP plots and LidarBC CHMs, with a 0-2 year offset.
They are CWH northern Vancouver Island pilots, not TSA 23 operational models.
See ``notes/reports/inv01-cwh-local-model-tfl6.md`` and
``notes/reports/inv01-als-transfer-tfl6.md``.

The TSA 23 IDF pilot cards use 14 public FAIB plots, LidarBC 2019/2024
first-return point clouds, and exact FAIB plot support:

- ``als_tsa23_idf_lorey_height_2026.json``
- ``als_tsa23_idf_basal_area_2026.json``
- ``als_tsa23_idf_gross_volume_2026.json``

They are still pilot cards: LOOCV only, no spatial holdout, and no P48/P49
validation.  See ``notes/reports/inv01-tsa23-idf-pilot.md``.

Bundle Prerequisite
-------------------

The bundle must validate against the LiDAR product-bundle contract.  Without
``--features`` it must contain a table product named ``canopy``.  With
``--features`` the CSV supplies ``fragment_id`` and the model predictor columns;
the bundle still supplies the pinned ``bundle_id`` and ``bundle_version``.
The reader uses the manifest's ``relative_path``; it does not discover products
or re-run materialization.

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
- The CHM grid helper is a proxy for first-return point-cloud metrics.
- No reprojection, resampling, or source-product rewrite is implicit.
- A model card is only as credible as its documented training scope and error.
- No WS4/FHOPS objective, constraint, growth, or solver code is changed.

See Also
--------

- :doc:`lidar-product-bundle`
- :doc:`../../guides/lidar-inventory`
- :doc:`../api/femic-lidar-inventory`
