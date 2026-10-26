Surrogate Model Contract
========================

Purpose
-------

This page is the short source-of-truth contract for FEMIC P114.7 surrogate
models. It defines the design, dataset, model families, applicability domain,
validation metrics, persistence, and refusal rules.

Quick Contract
--------------

- Design schema: ``femic.hydrology.surrogate_design.v1``.
- Model schema: ``femic.hydrology.surrogate_model.v1``.
- Families: ``linear`` and ``gp``.
- Design: Latin hypercube over continuous factors.
- Validation: held-out or k-fold RMSE, MAE, R2, 95% coverage, interval width.
- Applicability: feature min/max envelope plus standardized-distance guard.
- Default behavior: refuse out-of-domain queries.
- No silent extrapolation.

Design And Dataset
------------------

A design records factors, bounds, seed, points, and a deterministic design ID.
A dataset records feature order, target name, source, and samples. Every sample
must contain exactly the dataset features and finite target/feature values.

The design does not choose targets. Targets come from process-model runs or a
reviewed scenario library.

Surrogate Families
------------------

Linear:

- standardized ridge-linear regression;
- residual-sigma interval;
- warning when there are too few samples for a residual estimate.

Gaussian process:

- RBF kernel on standardized features;
- heuristic length scale unless supplied;
- predictive variance interval;
- Cholesky solve with bounded jitter and a warning when jitter is required.

Applicability And Refusal
-------------------------

A query is inside the domain when:

- every required feature is present;
- every feature is within its training min/max;
- the standardized distance from the training mean is within the guard.

An out-of-domain query raises ``HydrologySurrogateError`` unless the caller
explicitly sets ``allow_extrapolation=True``. The default refusal is the
contract used by optimization.

Validation Metrics
------------------

``evaluate_surrogate`` records:

- evaluation and accepted/refused counts;
- RMSE, MAE, and R2;
- 95% interval coverage;
- mean interval width;
- fold count;
- warnings for refusals, no accepted samples, and low coverage.

``cross_validate_surrogate`` applies the same metrics across deterministic
folds.

Persistence
-----------

Saved models include family, feature order, scaler, coefficients or kernel
state, hyperparameters, applicability domain, and warnings. Loading rejects an
unknown family or malformed JSON.

Limits
------

- Surrogate validity is bounded by training coverage.
- Validation error is not hydrologic validation.
- Categorical scenarios need explicit encoding.
- No public-gauge or process-model benchmark is implied by a good CV score.
- P114.9 owns the final benchmark and pilot validation.

Cross-References
----------------

- :doc:`../../guides/hydrology-surrogate-models`
- :doc:`hydrology-process-models`
- :doc:`hydrology-flood-frequency`
- :doc:`../api/femic-hydrology-surrogate`
