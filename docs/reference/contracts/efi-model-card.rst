EFI Model Card (``femic.efi.model.v1``)
========================================

Purpose
-------

This page is the source-of-truth contract for the EFI model card that travels
with ALS-derived inventory attributes. It records what the model predicts, what
it was trained on, how accurate it is, where it applies, and what licence
governs it.

The card complements, rather than replaces, the LiDAR product bundle manifest
(``femic.lidar.product.v1``). The bundle describes the sensor product; the card
describes the inventory model.

Quick Contract
--------------

- Card schema: ``femic.efi.model.v1``.
- File: one JSON model-card object.
- Target attribute and unit are a canonical pair.
- Predictors are a non-empty, unique list.
- Training and validation are nested objects.
- Applicability is a nested object naming at least one region or species.
- Validation unit must match the card unit.
- Training region must be in the applicability regions when those are present.
- Created timestamp must be ISO-8601 and timezone-aware.

Card Fields
-----------

.. list-table::
   :header-rows: 1
   :widths: 24 16 60

   * - Field
     - Type
     - Meaning
   * - ``schema_version``
     - string
     - Must be ``femic.efi.model.v1``.
   * - ``model_id``
     - string
     - Stable model identifier.
   * - ``model_version``
     - string
     - Model artifact version.
   * - ``attribute``
     - string
     - Target attribute from the canonical list below.
   * - ``unit``
     - string
     - Canonical unit for the attribute.
   * - ``predictors``
     - array
     - Non-empty, unique predictor names.
   * - ``training``
     - object
     - Training provenance; see below.
   * - ``validation``
     - object
     - Validation evidence; see below.
   * - ``applicability``
     - object
     - Domain; see below.
   * - ``licence_id``
     - string
     - Licence identifier, for example ``OGL-BC``.
   * - ``created_utc``
     - string
     - Timezone-aware ISO-8601 creation timestamp.
   * - ``notes``
     - string or null
     - Optional free-text note.

Attributes and Units
--------------------

.. list-table::
   :header-rows: 1
   :widths: 35 25 40

   * - Attribute
     - Unit
     - Meaning
   * - ``height``
     - ``m``
     - Height.
   * - ``volume``
     - ``m3_ha``
     - Volume per hectare.
   * - ``basal_area``
     - ``m2_ha``
     - Basal area per hectare.
   * - ``density``
     - ``stems_ha``
     - Stems per hectare.
   * - ``canopy_cover``
     - ``fraction``
     - Fractional cover in [0, 1].
   * - ``species_fraction``
     - ``fraction``
     - Species fraction in [0, 1].
   * - ``site_index``
     - ``m``
     - Site index.
   * - ``biomass``
     - ``t_ha``
     - Biomass per hectare.
   * - ``carbon``
     - ``tC_ha``
     - Carbon per hectare.
   * - ``other``
     - free text
     - A declared non-empty unit for an unlisted attribute.

Training Object
---------------

Required: ``source_id``, ``source_version``, ``region``, ``plot_count``.
Optional: ``species`` (unique list), ``period``, ``notes``.

Validation Object
-----------------

Required: ``design``, ``n``, ``rmse``, ``bias``, ``unit``. Optional: ``r2`` in
[0, 1], ``notes``. ``n`` is at least 1; ``rmse`` is non-negative. The validation
unit must equal the card unit.

Applicability Object
--------------------

Required: ``regions`` and ``species``. At least one of the two must be non-empty.
Optional: ``age_min``, ``age_max``, ``height_min``, ``height_max``, ``notes``.
Minimums must not exceed maximums.

A restricted dimension is conservative: if the card restricts region, species,
age, or height and the query does not provide that dimension, the query is
**out of domain**. This prevents a consumer from silently applying a model
without the information needed to establish applicability.

Attaching to Attribute Rows
---------------------------

:func:`femic.contracts.efi.annotate_attribute_rows` copies each row and adds:

``model_id``, ``model_version``, ``model_attribute``, ``model_unit``,
``model_rmse``, ``model_bias``, ``model_licence_id``, ``model_applicability``.

The input rows are not mutated.

Validation Rules
----------------

- Unknown and missing required fields are errors.
- ``schema_version`` is exact.
- ``attribute`` is a controlled vocabulary; ``unit`` must match it.
- ``predictors`` are non-empty and unique.
- Nested training, validation, and applicability objects are validated.
- Validation unit must match the card unit.
- Training region must be in the applicability regions when present.
- ``created_utc`` is ISO-8601 and timezone-aware.
- A card is not a validation certificate; it makes the claim inspectable.

Example
-------

.. code-block:: python

   from pathlib import Path
   from femic.contracts.efi import (
       annotate_attribute_rows,
       read_efi_model_card,
       summarize_efi_model_card,
   )

   card = read_efi_model_card(Path("data/efi/als-height-cwh-v1.json"))
   summary = summarize_efi_model_card(card)
   rows = annotate_attribute_rows(
       [{"fragment_id": 1001, "height_m": 24.5}], card
   )

Out of Scope
------------

- Training or retraining an EFI model.
- A model registry, database, or serving layer.
- Rebuilding the LiDAR product bundle or its sensor manifest.
- A claim of field accuracy beyond the recorded validation.
- A universal or global model card.

Cross-References
----------------

- :doc:`../api/femic-contracts-efi`
- :doc:`climate-contract`
- :doc:`disturbance-contract`
- :doc:`index`

.. toctree::
   :hidden:

   ../api/femic-contracts-efi
