EFI Model Application (``femic.efi.coefficients.v1``)
=====================================================

Purpose
-------

This page defines the execution layer above the ``femic.efi.model.v1`` card. A
card describes the claim; a coefficients document supplies a linear predictor;
FEMIC applies the predictor, checks the card's applicability domain, and
backtests the result against observed values.

The linear form is a transport for published or project coefficients. It is not
a new statistical method and it does not make a model valid.

Coefficients Document
---------------------

.. code-block:: json

   {
     "schema_version": "femic.efi.coefficients.v1",
     "model_id": "als-site-index-cwh-v1",
     "model_version": "0.1.0-pilot",
     "attribute": "site_index",
     "unit": "m",
     "intercept": 5.0,
     "coefficients": {
       "chm_p95": 0.7,
       "canopy_cover_2m": -5.0
     }
   }

The document must match the card's ``model_id``, ``model_version``,
``attribute``, and ``unit``. The coefficient keys must exactly match the card's
``predictors``. Values are finite numbers.

Prediction
----------

For a row with predictor values ``x``:

``prediction = intercept + sum(coefficient * x)``

The predictor names are row column names by default. A caller can map them with
``predictor_columns`` when the attribute table uses different column names.

Applicability
-------------

The engine checks the card's applicability domain using row fields ``region``,
``species``, ``age``, and ``height`` (or ``height_m``) when present. Restricted
dimensions are conservative: a missing query dimension is out of domain.

- ``out_of_domain="flag"`` keeps the row with ``model_in_domain=false`` and
  ``model_domain_reasons``.
- ``out_of_domain="drop"`` omits the row.
- ``require_domain=True`` raises instead of flagging.

Backtest
--------

``backtest_linear_model`` computes, for in-domain rows with an observed value:

- sample size and out-of-domain count,
- bias, RMSE, MAE, and R-squared when defined,
- observed and predicted ranges.

Out-of-domain rows are counted but excluded from the metrics. A backtest with no
in-domain observed rows is an error.

Example
-------

.. code-block:: python

   from pathlib import Path
   from femic.efi.application import (
       apply_linear_model,
       backtest_linear_model,
       load_linear_efi_model,
   )

   model = load_linear_efi_model(
       Path("data/efi/site_index_card.json"),
       Path("data/efi/site_index_coefficients.json"),
   )
   predictions = apply_linear_model(rows, model, out_of_domain="flag")
   report = backtest_linear_model(
       rows, model, observed_column="observed_site_index"
   )

Out of Scope
------------

- Fitting or calibrating coefficients.
- A non-linear or mixed-effects model.
- A universal site-index equation.
- The final ``si_als`` fragment attribute and instance backtest. Those remain
  P117.1 work.
- A replacement for the P48/P49 validation surfaces.

Cross-References
----------------

- :doc:`efi-model-card`
- :doc:`../api/femic-efi-application`
- :doc:`index`
