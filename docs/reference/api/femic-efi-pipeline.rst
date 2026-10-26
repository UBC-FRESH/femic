``femic.efi.pipeline`` Module
=============================

The :mod:`femic.efi.pipeline` module is the file-level seam between
``femic.efi.model.v1`` and attribute tables. It attaches model-card provenance
and an explicit applicability decision to every row of a CSV, Parquet, or
Feather table. It does not predict, fit, or change a curve.

Start Here If...
----------------

Use this page first if you are trying to:

- attach an EFI model card to an ALS-derived attribute table;
- flag or drop rows outside the card's region/species/age/height domain;
- write a reproducible annotation summary; or
- inspect the published cards checked into ``config/efi/models/``.

Typical Usage
-------------

.. code-block:: python

   from pathlib import Path

   from femic.efi.pipeline import annotate_attribute_table

   result = annotate_attribute_table(
       Path("attributes.csv"),
       Path("config/efi/models/als_loreys_height_cwh_2015.json"),
       Path("attributes_annotated.parquet"),
       summary_path=Path("attributes_annotation_summary.json"),
       domain_policy="flag",
   )
   print(result.in_domain_count, result.out_of_domain_count)

Key Entry Surfaces
------------------

- :func:`femic.efi.pipeline.annotate_attribute_table`
  Read, annotate, domain-check, and write an attribute table.
- :class:`femic.efi.pipeline.EFIAttributeAnnotationResult`
  Paths, model identity, row counts, and domain-policy counts.
- :data:`femic.efi.pipeline.EFI_ATTRIBUTE_TABLE_SCHEMA_VERSION`
  ``femic.efi.attribute_table.v1`` summary schema.

The output table adds:

- ``model_card_schema_version``;
- ``model_id``, ``model_version``, ``model_attribute``, ``model_unit``;
- ``model_rmse``, ``model_bias``, ``model_licence_id``;
- ``model_applicability`` (JSON string);
- ``model_in_domain``; and
- ``model_domain_reasons`` (JSON list).

Domain Policies
---------------

- ``flag`` keeps every row and writes the domain decision.
- ``drop`` omits out-of-domain rows.
- ``require`` raises :class:`femic.efi.application.EFIApplicationError` on the
  first out-of-domain row.

A restricted card dimension is conservative: if the card restricts region,
species, age, or height and the table does not provide that column, the row is
out of domain.

Published Cards
---------------

The two cards under ``config/efi/models/`` are metadata-only published cards:

- ``als_loreys_height_cwh_2015.json`` (CWH, Cw/Hw/Hm)
- ``als_site_index_loblolly_seus_2019.json`` (southeastern USA, *Pinus taeda*)

They are not linear models and do not carry the authors' coefficients or
forest objects. See :doc:`../contracts/efi-model-card` for the citations and
limits.

Cross-References
----------------

- :doc:`../contracts/efi-model-card`
- :doc:`femic-efi-application`
- :doc:`femic-contracts-efi`
- :doc:`../contracts/index`

.. automodule:: femic.efi.pipeline
   :members:
   :show-inheritance:
