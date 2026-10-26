``femic.efi.application`` Module
================================

The :mod:`femic.efi.application` module applies a linear EFI model card and
coefficients document to row-wise metrics, checks the applicability domain, and
backtests against observed values.

Use this page when you are applying a published or project EFI model, checking
where it applies, or producing a backtest report.

Start Here If...
----------------

Use this page first if you are trying to:

- apply an EFI model to an attribute table;
- verify that a coefficients document matches its model card;
- flag or reject rows outside the model's applicability domain; or
- compute bias, RMSE, MAE, and R-squared against observed values.

Typical Usage
-------------

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

Key Entry Surfaces
------------------

- :func:`load_linear_efi_model`
  Load and cross-check a model card and its coefficients.
- :class:`LinearEFIModel`
  Typed linear model with ``predict``.
- :func:`apply_linear_model`
  Predict, attach provenance, and flag or drop out-of-domain rows.
- :func:`backtest_linear_model`
  Compute bias, RMSE, MAE, R-squared, and ranges on in-domain rows.

Cross-References
----------------

- :doc:`../contracts/efi-application`
- :doc:`../contracts/efi-model-card`
- :doc:`femic-efi-pipeline`
- :doc:`../contracts/index`

.. automodule:: femic.efi.application
   :members:
   :show-inheritance:
