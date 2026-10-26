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
  a CSV export. The 2014 addendum XLSX (``ciReportByUnit`` sheet) can be added
  separately.
- **AU input** — optional ``03_input-<tsa>.csv`` for a separate analysis-unit
  report. Do not join it to the polygon table.

Run It
------

.. code-block:: bash

   python -m femic.site_index \
     --vri external/femic-tsa46-instance/data/vri_vclr1p_checkpoint8.feather \
     --vdyp external/femic-tsa46-instance/data/vdyp_lyr-tsa46.feather \
     --sibec /path/to/sibec2013approx_final.xlsx \
     --sibec-addendum /path/to/2013sisuaddendum_jul2014.xlsx \
     --au-input external/femic-tsa46-instance/data/03_input-tsa46.csv \
     --out-csv /tmp/si-reconcile/tsa46_si_reconciliation.csv \
     --out-json /tmp/si-reconcile/tsa46_si_summary.json \
     --out-au-csv /tmp/si-reconcile/tsa46_au_site_index.csv \
     --out-au-json /tmp/si-reconcile/tsa46_au_summary.json \
     --delta-threshold 2.0

The polygon JSON summary is printed to standard output. The AU report is
written separately and its grain is stated as ``analysis_unit_species``.
``--delta-threshold`` controls the conflict flag. ``--min-sibec-plot-count``
controls when SIBEC may become the reference value for a feature with no VRI
field site index.

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
- ``sibec_sources``: how many rows selected the 2013 approximation, the 2014
  addendum, or no SIBEC source.

For each conflict, inspect the CSV columns:

- ``si_vri``, ``si_vdyp``, ``si_sibec_vri``;
- ``si_sibec_vri_min`` and ``si_sibec_vri_max``;
- ``si_sibec_vri_source`` and ``si_sibec_vdyp_source``;
- ``delta_vri_vdyp``, ``delta_vri_sibec_range``, ``delta_vdyp_sibec_range``;
- ``species_vri``, ``species_vdyp``, ``species_match``; and
- ``si_reference``, ``si_reference_source``, ``delta_reference_curve``.

Interpretation Rules
--------------------

1. A VRI-versus-VDYP delta is only calculated when the species match.
2. SIBEC is aggregated to BEC unit + species because VRI has no site series.
   Use the SIBEC range for the consistency check, not the mean as a polygon
   estimate. The addendum is preferred for duplicate keys, and the selected
   source is explicit in the output.
3. A conflict is a review flag, not proof that VRI or VDYP is wrong.
4. ``si_reference`` is a comparison value. It does not change the VDYP curve
   input.
5. The AU-level report is a separate grain. Do not join it to VRI polygons or
   treat it as polygon evidence.
6. Do not translate a reconciliation result directly into an AAC change.

TSA46 Pilot
-----------

The TSA46 run used 171,826 VRI features, the public SIBEC 2013
approximation, and the 2014 addendum. VRI had a site index for every feature;
VDYP primary layers had one for 3,384 features; SIBEC matched 136,807 features
(136,659 from 2013, 148 from the addendum). Only 2,285 features had all three
sources. At a 2.0 m threshold, 25,559 features were flagged for review.

The separate AU-level report covered 21 analysis units and 462 AU/species rows
across 22 species columns. The leading-species SI ranged from 6.3 to 22.5 m.
See :doc:`../reference/contracts/site-index-reconciliation` for the full
contract and the known limits.

Next Checks
-----------

- Review the top conflict BEC units/species with a forester before changing a
  curve assignment.
- Check the 148 addendum-selected polygon rows and the 21 AU rows against the
  source workbooks before using them in a curve review.
- Keep the AU-level report separate from the polygon reconciliation; the AU
  table has no BEC variant.
