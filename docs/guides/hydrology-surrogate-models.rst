Surrogate Models For Hydrologic Response
========================================

Purpose
-------

P114.7 provides fast surrogate models for hydrologic response queries. The
surrogate is trained on process-model scenarios or a reviewed scenario library
and refuses queries outside a validated applicability domain.

It is a fast approximation, not a substitute for the process model or
hydrologist review. The design schema is
``femic.hydrology.surrogate_design.v1`` and the model schema is
``femic.hydrology.surrogate_model.v1``.

Design Of Experiments
---------------------

Continuous factors are sampled with a Latin-hypercube design:

.. code-block:: python

   from femic.hydrology.surrogate import DesignFactor, build_latin_hypercube_design

   design = build_latin_hypercube_design(
       (
           DesignFactor("harvest_fraction", 0.0, 0.6),
           DesignFactor("road_density", 0.0, 2.0),
           DesignFactor("climate_index", 0.8, 1.2),
       ),
       n_samples=200,
       seed=42,
   )

Attach process-model targets with ``attach_targets``. Categorical climate
scenarios should be encoded by a reviewed numeric covariate or handled as
separate surrogates.

Surrogate Families
------------------

Two dependency-free families are implemented:

- ``linear``: standardized ridge-linear regression with a residual interval.
- ``gp``: RBF-kernel Gaussian process with a predictive variance.

Additional families can be added behind the ``SurrogateModel`` protocol.

Training And Validation
-----------------------

.. code-block:: python

   from femic.hydrology.surrogate import (
       attach_targets,
       cross_validate_surrogate,
       evaluate_surrogate,
       fit_surrogate,
       train_validation_split,
   )

   dataset = attach_targets(design, targets, target_name="peak_flow_ratio")
   train, validation = train_validation_split(dataset, validation_fraction=0.2, seed=42)
   model = fit_surrogate(train, family="gp")
   report = evaluate_surrogate(model, validation)
   cv = cross_validate_surrogate(dataset, family="gp", folds=5, seed=42)

Validation records RMSE, MAE, R2, 95% interval coverage, mean interval width,
accepted/refused counts, and fold count.

Applicability Domain And Refusal
--------------------------------

The applicability domain combines:

- a per-feature training min/max envelope;
- a standardized-distance guard around the training mean.

Queries outside the domain raise by default:

.. code-block:: python

   model.predict({"harvest_fraction": 0.9, "road_density": 5.0})
   # HydrologySurrogateError: Query is outside the applicability domain...

Use ``allow_extrapolation=True`` only for an explicitly reviewed extrapolation
test. Do not silently feed extrapolated queries into optimization.

Persistence
-----------

.. code-block:: python

   from femic.hydrology.surrogate import load_surrogate, save_surrogate

   save_surrogate(model, Path("models/hydrology/peak_ratio_gp.json"))
   loaded = load_surrogate(Path("models/hydrology/peak_ratio_gp.json"))

The saved model includes the feature order, scaler, coefficients or kernel
state, hyperparameters, and applicability domain.

Limits
------

- The surrogate is only valid inside its training coverage.
- Validation error is not a hydrologic validation.
- The GP length scale is heuristic unless supplied.
- Categorical scenarios need explicit encoding.
- Process-model calibration and benchmark validation remain P114.9.
- Hydrologist review is required before operational use.
- No silent extrapolation: out-of-domain queries are refused by default.

See Also
--------

- :doc:`hydrology-process-models`
- :doc:`hydrology-flood-frequency`
- :doc:`../reference/contracts/hydrology-surrogate-models`
- :doc:`../reference/api/femic-hydrology-surrogate`
