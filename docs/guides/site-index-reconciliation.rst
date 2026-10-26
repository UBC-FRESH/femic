Site-Index Reconciliation Workflow
===================================

This guide runs the ``femic.site_index`` reconciliation on an existing FEMIC
instance. It consumes VRI, VDYP, and SIBEC; it does not build a new
site-index model.

When to Use It
--------------

Use this workflow when you need to:

- see whether VRI, VDYP, and SIBEC site-index values disagree before a growth
  or yield review;
- record which source supplied the reference value;
- produce a feature-level CSV for a forester or modeller to review; or
- audit BEC-unit/species gaps before changing a curve assignment.

Do not use it to overwrite a curve input. The output is a review table.

Inputs
------

- **VRI** — a Feather, Parquet, or CSV checkpoint with ``FEATURE_ID``,
  ``BEC_ZONE_CODE``, ``BEC_SUBZONE``, ``BEC_VARIANT``, ``SPECIES_CD_1``,
  ``SITE_INDEX``, and ``EST_SITE_INDEX``.
- **VDYP** — a VDYP layer Feather/Parquet/CSV with ``FEATURE_ID``,
  ``LAYER_LEVEL_CODE``, ``EST_SITE_INDEX_SPECIES_CD``, and
  ``ESTIMATED_SITE_INDEX``. The reader keeps the primary layer.
- **SIBEC** — the public 2013 approximation XLSX (header on the third row) or
  a CSV export.

Run It
------

.. code-block:: bash

   python -m femic.site_index \
     --vri external/femic-tsa46-instance/data/vri_vclr1p_checkpoint8.feather \
     --vdyp external/femic-tsa46-instance/data/vdyp_lyr-tsa46.feather \
     --sibec /path/to/sibec2013approx_final.xlsx \
     --out-csv /tmp/si-reconcile/tsa46_si_reconciliation.csv \
     --out-json /tmp/si-reconcile/tsa46_si_summary.json \
     --delta-threshold 2.0

The JSON summary is also printed to standard output. ``--delta-threshold``
controls the conflict flag. ``--min-sibec-plot-count`` controls when SIBEC may
become the reference value for a feature with no VRI field site index.

Read the Summary
----------------

The summary reports coverage separately for each source. Check the following
before reading a conflict count:

- ``coverage.si_vdyp``: if this is small, the three-way comparison is sparse.
  A large ``partial`` count is expected.
- ``coverage.si_sibec_vri``: missing values usually mean the BEC unit or
  species is absent from SIBEC.
- ``status_counts.conflict``: rows where a comparable difference exceeds the
  threshold or a source is outside the SIBEC range.
- ``species_mismatch_count``: VRI and VDYP name different species, so their
  direct delta is intentionally suppressed.
- ``reference_sources``: which source supplied the documented reference.

For each conflict, inspect the CSV columns:

- ``si_vri``, ``si_vdyp``, ``si_sibec_vri``;
- ``si_sibec_vri_min`` and ``si_sibec_vri_max``;
- ``delta_vri_vdyp``, ``delta_vri_sibec_range``, ``delta_vdyp_sibec_range``;
- ``species_vri``, ``species_vdyp``, ``species_match``; and
- ``si_reference``, ``si_reference_source``, ``delta_reference_curve``.

Interpretation Rules
--------------------

1. A VRI-versus-VDYP delta is only calculated when the species match.
2. SIBEC is aggregated to BEC unit + species because VRI has no site series.
   Use the SIBEC range for the consistency check, not the mean as a polygon
   estimate.
3. A conflict is a review flag, not proof that VRI or VDYP is wrong.
4. ``si_reference`` is a comparison value. It does not change the VDYP curve
   input.
5. Do not translate a reconciliation result directly into an AAC change.

TSA46 Pilot
-----------

The first TSA46 run used 171,826 VRI features and the public SIBEC 2013
approximation. VRI had a site index for every feature; VDYP primary layers had
one for 3,384 features; SIBEC matched 136,807 features. Only 2,285 features had
all three sources. At a 2.0 m threshold, 25,643 features were flagged for
review. See :doc:`../reference/contracts/site-index-reconciliation` for the
full contract and the known limits.

Next Checks
-----------

- Merge the SIBEC 2014 addendum when its merged-cell layout is handled.
- Reconcile the AU-level ``03_input`` SI separately from the polygon/layer
  table.
- Review the top conflict BEC units/species with a forester before changing a
  curve assignment.
