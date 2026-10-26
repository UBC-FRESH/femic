``femic.hydrology.surrogate`` Module
=====================================

The :mod:`femic.hydrology.surrogate` module owns P114.7 surrogate work. It
builds Latin-hypercube designs, trains ridge-linear and RBF Gaussian-process
surrogates, validates them on held-out or k-fold data, and refuses queries
outside a validated applicability domain.

Use this page when you are turning process-model scenarios into a fast,
bounded response surrogate for optimization.

Start Here If...
----------------

Use this page first if you are trying to:

- design process-model scenarios over harvest/road/climate factors;
- train a linear or Gaussian-process surrogate;
- validate error and interval coverage on held-out scenarios;
- save/load a surrogate model; or
- understand when a surrogate query must be refused.

Typical Usage
-------------

.. code-block:: python

   from pathlib import Path
   from femic.hydrology.surrogate import (
       DesignFactor,
       attach_targets,
       build_latin_hypercube_design,
       cross_validate_surrogate,
       fit_surrogate,
       save_surrogate,
   )

   design = build_latin_hypercube_design(
       (
           DesignFactor("harvest_fraction", 0.0, 0.6),
           DesignFactor("road_density", 0.0, 2.0),
       ),
       n_samples=200,
       seed=42,
   )
   dataset = attach_targets(design, targets)
   model = fit_surrogate(dataset, family="gp")
   report = cross_validate_surrogate(dataset, family="gp", folds=5)
   save_surrogate(model, Path("models/hydrology/peak_ratio_gp.json"))

Key Entry Surfaces
------------------

- :func:`build_latin_hypercube_design`
- :func:`attach_targets`
- :func:`train_validation_split`
  Build and split surrogate datasets.
- :func:`fit_surrogate`
  Fit a linear or Gaussian-process surrogate.
- :func:`evaluate_surrogate`
  Validate on held-out samples with applicability refusal.
- :func:`cross_validate_surrogate`
  Run deterministic k-fold validation.
- :func:`save_surrogate`
- :func:`load_surrogate`
  Persist and load model state.
- :class:`ApplicabilityDomain`
  Bounded envelope and distance guard.
- :class:`SurrogateValidation`
  Error, coverage, refusal, and fold metrics.

Cross-References
----------------

- :doc:`../../guides/hydrology-surrogate-models`
- :doc:`../contracts/hydrology-surrogate-models`
- :doc:`femic-hydrology-process-models`
- :doc:`femic-hydrology-flood`

.. toctree::
   :hidden:

   generated/femic.hydrology.surrogate

.. automodule:: femic.hydrology.surrogate
   :members:
   :undoc-members:
   :show-inheritance:
