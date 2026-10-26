``femic.contracts.efi`` Module
==============================

The :mod:`femic.contracts.efi` module owns the ``femic.efi.model.v1`` model-card
contract. It records the target, predictors, training data, validation,
applicability domain, and licence for an ALS-derived inventory model.

Use this page when you are producing, reading, validating, or attaching an EFI
model card to attribute rows for a FEMIC instance or a Nemora workflow.

Start Here If...
----------------

Use this page first if you are trying to:

- describe an area-based or tree-level EFI model;
- check a card's unit, accuracy, applicability, or licence before a consumer
  uses it;
- attach model metadata to an ALS-derived attribute table;
- decide whether an attribute is inside the model's applicability domain; or
- report which model version and validation produced an attribute.

Typical Usage
-------------

.. code-block:: python

   from pathlib import Path
   from femic.contracts.efi import (
       annotate_attribute_rows,
       read_efi_model_card,
       summarize_efi_model_card,
       write_efi_model_card,
   )

   card = read_efi_model_card(Path("data/efi/als-height-cwh-v1.json"))
   summary = summarize_efi_model_card(card)
   rows = annotate_attribute_rows(
       [{"fragment_id": 1001, "height_m": 24.5}], card
   )
   write_efi_model_card(Path("data/efi/copy.json"), card)

Key Entry Surfaces
------------------

- :func:`validate_efi_model_card`
  Validate one card and its cross-field rules.
- :class:`EFIModelCard`
  Typed card with canonical ``to_dict``, ``from_dict``, and ``applies_to``.
- :class:`EFITrainingData`
  Training source, region, plot count, species, and period.
- :class:`EFIValidation`
  Validation design, sample size, RMSE, bias, unit, and R-squared.
- :class:`EFIApplicability`
  Regions, species, age and height bounds, and notes.
- :func:`read_efi_model_card`
  Read and validate one JSON model card.
- :func:`write_efi_model_card`
  Write one validated model card.
- :func:`summarize_efi_model_card`
  Return a compact, provenance-bearing summary.
- :func:`annotate_attribute_rows`
  Attach model metadata to copies of attribute rows.
- :func:`efi_model_schema`
  Return a defensive copy of the JSON Schema document.

Cross-References
----------------

- :doc:`../contracts/efi-model-card`
- :doc:`femic-efi-pipeline`
- :doc:`../contracts/index`

.. automodule:: femic.contracts.efi
   :members:
   :show-inheritance:
