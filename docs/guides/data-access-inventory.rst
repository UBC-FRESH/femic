Data Access Inventory
=====================

This page is the operator-facing companion to
``metadata/required_datasets.yaml`` and records external dataset requirements
for FEMIC deployment instances.

Authoritative Registry
----------------------

- Machine-readable source of truth:
  ``metadata/required_datasets.yaml``
- Current DataLad include list snapshot:
  ``metadata/datalad_mirror_seed.csv``
- Scope:
  required provincial base layers, optional support assets, and case-specific
  geometry dependencies.
- Intent:
  drive Phase 10 DataLad mirror work (``P10.6``), especially for datasets that
  are public but not reliably one-click downloadable.

Key Dataset Families
--------------------

- Provincial VRI (preferred 2024, fallback 2019):
  - ``VEG_COMP_LYR_R1_POLY_2024.gdb``
  - ``VEG_COMP_VDYP7_INPUT_POLY_AND_LAYER_2024.gdb``
- Provincial boundaries and productivity:
  - ``FADM_TSA.gdb``
  - ``Site_Prod_BC.gdb``
- THLB signal:
  - ``misc.thlb.tif`` (archived HectaresBC source; primary mirror target)
- Case-specific boundary geometry:
  - operator-supplied ``selection.boundary_path`` assets.

Checksum Policy
---------------

Each dataset entry in ``metadata/required_datasets.yaml`` includes a checksum
block:

- ``algorithm``: currently ``sha256``
- ``value``: expected digest value (or ``null`` until captured)
- ``status``: workflow state (for example ``pending`` or
  ``required_before_publish``)
- ``target_artifact``: the file that digest applies to.

Before publishing mirrored artifacts, populate all checksum values for mirrored
datasets.

DataLad Mirror Scope
--------------------

The registry includes ``datalad_mirror.include`` and rationale fields per
dataset.

Current inclusion priority:

1. ``hectaresbc_misc_thlb_tif`` (source is decommissioned).
2. Historical/manual-access provincial fallbacks and base layers where
   operator access is inconsistent (2019 VRI/VDYP inputs, FMU boundary layers
   including TSA boundaries, Site_Prod_BC).

Directly downloadable datasets (for example 2024 VRI endpoints) remain outside
the mirror by default unless reliability policy changes.
