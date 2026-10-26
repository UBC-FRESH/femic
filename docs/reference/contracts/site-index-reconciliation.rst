Site-Index Reconciliation (``femic.site-index.reconciliation.v2``)
===================================================================

Purpose
-------

This page is the contract for reporting and reconciling the site-index values
that FEMIC already receives from three British Columbia products:

- VRI polygon ``SITE_INDEX`` and ``EST_SITE_INDEX``;
- VDYP primary-layer ``ESTIMATED_SITE_INDEX``; and
- SIBEC site-series estimates by BEC unit and tree species.

The reconciliation is a **reporting layer**. It does not derive a new
site-index model, refit VDYP/TIPSY curves, change an AAC/THLB calculation, or
silently replace a curve input.

The first pilot is TSA46. Its coverage and limits are recorded below so a
consumer does not mistake a sparse VDYP layer value for a complete polygon
estimate. The AU-level TSA SI is reported separately and is never forced into
the polygon table.

Quick Contract
--------------

- Reconciliation schema: ``femic.site-index.reconciliation.v2``.
- SIBEC tidy schema: ``femic.sibec.v2``.
- AU-level schema: ``femic.site-index.au.v1``.
- VRI reader schema: ``femic.vri.site-index.v1``.
- VDYP reader schema: ``femic.vdyp.site-index.v1``.
- Polygon grain: one output row per VRI feature.
- AU grain: one output row per analysis unit and species.
- Join keys: ``feature_id``; BEC unit key; canonical species key.
- Default conflict threshold: ``2.0`` m.
- Default SIBEC reference minimum: ``7`` plots.
- SIBEC source preference: ``2014_addendum`` first, then
  ``2013_approximation``; the selected source is written explicitly.
- Reference precedence: VRI ``SITE_INDEX`` -> SIBEC (meeting the plot-count
  minimum) -> VDYP -> VRI ``EST_SITE_INDEX``.
- The VDYP value is always retained as the current curve input; the reference
  value is never applied automatically.

Source Inputs
-------------

VRI
~~~

``femic.site_index.vri.load_vri_site_index`` reads a VRI Feather, Parquet, or
CSV table and selects:

- ``FEATURE_ID``;
- ``BEC_ZONE_CODE``, ``BEC_SUBZONE``, ``BEC_VARIANT``;
- ``SPECIES_CD_1`` and ``SPECIES_PCT_1``;
- ``SITE_INDEX`` and ``EST_SITE_INDEX``; and
- ``PROJ_AGE_1`` and ``PROJ_HEIGHT_1``.

The BEC unit is composed as zone + subzone + variant (for example
``CWHvh2``). The lookup key is upper-cased so VRI and SIBEC spelling
differences do not prevent a match.

The VRI reader uses a small alias map for known code variants. ``H`` maps to
``HW``, ``FDC`` maps to ``FD``, and ``AC`` maps to ``AT``. Unknown codes are
kept as-is and simply fail to match SIBEC or VDYP; they are not guessed.

VDYP
~~~~

``femic.site_index.vdyp.load_vdyp_site_index`` reads a VDYP layer table and
keeps the primary layer (``LAYER_LEVEL_CODE == "1"``) with a non-null
``ESTIMATED_SITE_INDEX``. It records the species named by
``EST_SITE_INDEX_SPECIES_CD``.

This is the polygon/layer-level VDYP output. It is **not** the AU-level SI in
the ``03_input`` TSA table. The pilot showed that only a small share of VDYP
primary layers carry a non-null site index, so the reconciliation does not
claim complete VDYP coverage.

SIBEC
~~~~~

``femic.site_index.sibec.load_sibec_table`` reads the public 2013
approximation workbook (header on the third row) or a CSV export. It
normalises the columns to:

- ``source_table`` (source provenance);
- ``region``, ``bgc_unit``, ``site_series``, ``site_association``;
- ``species``;
- ``plot_count``, ``mean_site_index``, ``standard_error``; and
- ``schema_version = femic.sibec.v2``.

``load_sibec_addendum`` reads the 2014 addendum (``ciReportByUnit``). It
removes the repeated page-header blocks and accepts the addendum's
``Sample Size`` / ``Mean Site Index`` / ``Standard Error`` columns. The result
keeps ``source_table = 2014_addendum``; it is never silently merged into the
2013 approximation.

``combine_sibec_tables`` concatenates the two tidy tables while preserving the
``source_table`` labels. ``aggregate_sibec_by_bgc_unit`` groups site-series rows
to BEC unit + species + source and reports:

- ``si_sibec_mean`` (weighted by plot count when counts are available,
  otherwise unweighted);
- ``si_sibec_min`` and ``si_sibec_max``;
- mean standard error;
- total plot count; and
- the number of contributing site series.

``select_sibec_source`` then chooses one row per BEC-unit/species with the
declared preference: the 2014 addendum first, then the 2013 approximation. The
selected label is written to ``si_sibec_source`` and carried into the
reconciliation as ``si_sibec_vri_source`` and ``si_sibec_vdyp_source``.

The mean is **not** a polygon-level SIBEC estimate. VRI does not carry a site
series, so SIBEC site-series rows cannot be joined directly to a polygon. The
SIBEC **range** is used to test whether a VRI or VDYP value is outside the
BEC-unit/species envelope; the mean is retained as descriptive provenance.

The 2013 approximation and 2014 addendum are both supported. The addendum is a
smaller supplement (224 usable rows in the public workbook); the 2013 table is
the broad base.

AU-level TSA SI
~~~~~~~~~~~~~~~

``femic.site_index.au.load_au_site_index`` reads
``03_input-<tsa>.csv`` at the analysis-unit/species grain. It reports:

- ``au_id`` (the ``feature_id`` in the TSA input);
- ``bec_zone`` and ``bec_subzone``;
- ``planted_species``, ``natural_species``, and ``leading_species``;
- ``species`` / ``species_key`` and ``si_au``; and
- ``is_leading`` for the leading species.

``summarize_au_site_index`` states the grain explicitly
(``analysis_unit_species``), counts AUs, rows, species, and BEC zones, and
summarizes the leading-species SI. The AU table has no BEC variant in the TSA
input, so it is **not** joined to the VRI polygon table. It is written as a
separate CSV and JSON summary.

Reconciliation Rules
--------------------

Species matching
~~~~~~~~~~~~~~~~

The VRI leading species and the VDYP site-index species are compared
separately. A VRI-versus-VDYP delta is only calculated when both species keys
are present and equal. When they differ:

- ``species_match`` is ``false``;
- ``delta_vri_vdyp`` is null; and
- the SIBEC values for each species are still reported separately.

This avoids comparing a VRI value for one species with a VDYP value for
another species.

Pairwise deltas
~~~~~~~~~~~~~~~

The following differences are reported:

- ``delta_vri_vdyp`` = VDYP - VRI, only when species match;
- ``delta_vri_sibec`` = SIBEC mean - VRI (descriptive);
- ``delta_vdyp_sibec`` = SIBEC mean - VDYP (descriptive);
- ``delta_vri_sibec_range`` = distance of VRI outside the SIBEC min/max range,
  or ``0`` when VRI is inside the range;
- ``delta_vdyp_sibec_range`` = distance of VDYP outside the SIBEC min/max
  range, or ``0`` when VDYP is inside the range; and
- ``delta_abs_max`` = the largest absolute value among the species-matched
  VRI/VDYP delta and the two SIBEC range exceedances.

``delta_abs_max > delta_threshold`` marks the row as a conflict. The default
threshold is ``2.0`` m. A conflict means "look here"; it does not mean that one
source is wrong.

Status and reference
~~~~~~~~~~~~~~~~~~~~

``si_status`` is one of:

- ``complete``: VRI ``SITE_INDEX``, VDYP, and SIBEC for the VRI species are
  all present, and no comparable difference exceeds the threshold;
- ``conflict``: a comparable difference exceeds the threshold;
- ``partial``: some source values are present but the triple is incomplete; or
- ``missing``: no source value is present.

``si_reference`` and ``si_reference_source`` use the precedence below. The
reference is a comparison value, not an overwrite:

1. VRI ``SITE_INDEX`` when present (source ``vri``);
2. SIBEC mean when the VRI value is absent and the SIBEC plot count meets
   ``min_sibec_plot_count`` (source ``sibec``);
3. VDYP when the first two are absent (source ``vdyp``);
4. VRI ``EST_SITE_INDEX`` as the final fallback (source ``vri_estimate``).

``delta_reference_curve`` is ``si_reference - si_vdyp``. It shows how far the
reference is from the VDYP value the current curve uses.

Output Columns
--------------

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Column
     - Meaning
   * - ``feature_id``
     - VRI feature identifier.
   * - ``bec_unit``
     - Composed BEC unit, such as ``CWHvh2``.
   * - ``species_vri``
     - VRI leading species.
   * - ``species_vdyp``
     - Species named by the VDYP site-index field.
   * - ``species_match``
     - Whether the two species keys are present and equal.
   * - ``si_vri``
     - VRI field site index.
   * - ``si_vri_est``
     - VRI estimated site index.
   * - ``si_vdyp``
     - VDYP primary-layer estimated site index.
   * - ``si_sibec_vri``
     - SIBEC mean for the VRI species and BEC unit.
   * - ``si_sibec_vri_min`` / ``si_sibec_vri_max``
     - SIBEC site-series range for the VRI species.
   * - ``si_sibec_vri_se``
     - Mean SIBEC standard error for the VRI species.
   * - ``si_sibec_vri_plot_count``
     - Total SIBEC plot count for the VRI species; ``0`` means the source
       approximation has no plot count.
   * - ``si_sibec_vri_site_series_count``
     - Number of SIBEC site series behind the VRI-species aggregate.
   * - ``si_sibec_vri_source``
     - Selected SIBEC source for the VRI species (``2013_approximation`` or
       ``2014_addendum``).
   * - ``si_sibec_vdyp`` / ``..._min`` / ``..._max``
     - SIBEC values for the VDYP species.
   * - ``si_sibec_vdyp_source``
     - Selected SIBEC source for the VDYP species.
   * - ``delta_vri_vdyp``
     - VDYP - VRI when species match.
   * - ``delta_vri_sibec`` / ``delta_vdyp_sibec``
     - Descriptive difference from the SIBEC mean.
   * - ``delta_vri_sibec_range`` / ``delta_vdyp_sibec_range``
     - Distance outside the SIBEC range.
   * - ``delta_abs_max``
     - Largest comparable absolute difference.
   * - ``si_source_count``
     - Number of non-null values among VRI, VDYP, and SIBEC/VRI.
   * - ``si_status``
     - ``complete``, ``conflict``, ``partial``, or ``missing``.
   * - ``si_reference`` / ``si_reference_source``
     - Documented comparison value and its source.
   * - ``delta_reference_curve``
     - Reference minus VDYP.
   * - ``proj_age`` / ``proj_height``
     - VRI projection attributes carried for review.

CLI
---

Run the reconciliation after installing FEMIC:

.. code-block:: bash

   python -m femic.site_index \
     --vri data/vri_vclr1p_checkpoint8.feather \
     --vdyp data/vdyp_lyr-tsa46.feather \
     --sibec data/sibec2013approx_final.xlsx \
     --sibec-addendum data/2013sisuaddendum_jul2014.xlsx \
     --au-input data/03_input-tsa46.csv \
     --out-csv out/tsa46_si_reconciliation.csv \
     --out-json out/tsa46_si_summary.json \
     --out-au-csv out/tsa46_au_site_index.csv \
     --out-au-json out/tsa46_au_summary.json \
     --delta-threshold 2.0

Use ``--sibec-sheet`` to select a non-default worksheet. Use
``--sibec-addendum`` to combine the 2014 addendum with the 2013 base; the
addendum is preferred for duplicate BEC-unit/species keys and the selected
source is written to the CSV. Use ``--au-input`` plus the AU output paths for
the separate analysis-unit report. The command prints the polygon JSON summary
and writes the feature-level and AU-level files when paths are provided.

TSA46 Pilot (26 October 2026)
-----------------------------

Inputs:

- VRI checkpoint 8, 171,826 features;
- VDYP layer table, primary layer only;
- SIBEC 2013 approximation, 4,023 source rows; and
- SIBEC 2014 addendum, 224 usable rows.

Polygon results:

- ``si_vri`` present: 171,826 (100%);
- ``si_vri_est`` present: 5,966 (3.5%);
- ``si_vdyp`` present: 3,384 (2.0%);
- ``si_sibec_vri`` present: 136,807 (79.6%);
- SIBEC VRI-species source: 136,659 from 2013 and 148 from the addendum;
- complete triple: 2,285 (1.3%);
- conflicts at 2.0 m: 25,559 (14.9%);
- partial: 143,982 (83.8%); and
- missing: 0.

The high partial count is driven by sparse VDYP layer site index, not by a
missing VRI value. The SIBEC range test is the main polygon-level consistency
check in this pilot. The VDYP layer field is too sparse to support a complete
three-way comparison.

AU-level TSA46 report:

- 21 analysis units;
- 462 AU/species rows;
- 22 species columns;
- BEC zones: CWH and MH;
- leading species: HW 8, CW 3, FD 3, YC 3, BA 3, HM 1; and
- leading-species SI: min 6.3, median 10.9, mean 11.43, max 22.5 m.

The AU table has no BEC variant and is not joined to the polygon table. It is a
separate grain and a separate output.

Known Limits
------------

- SIBEC 2013 is the broad base; the 2014 addendum is a 224-row supplement.
  The addendum is preferred for duplicate BEC-unit/species keys, and the
  selected source is explicit in the output.
- SIBEC is aggregated to BEC unit + species because VRI has no site series.
  The range check is a screening test, not a site-series assignment.
- The AU-level TSA table has no BEC variant and is not joined to the polygon
  table. Treat its summary as the current curve-input grain, not a polygon
  estimate.
- VRI ``SITE_INDEX`` is a provincial inventory value, not a newly measured
  ground plot.
- VDYP layer coverage depends on the instance and layer export; do not assume
  every VRI feature has a VDYP layer value.
- Species aliases are explicit. Unknown species are retained but do not match.
- The reconciliation does not change curves, AAC, THLB, or schedules.

Cross-References
----------------

- :doc:`../../guides/site-index-reconciliation`
- :doc:`../api/femic-site-index`
- :doc:`climate-contract`
- :doc:`disturbance-contract`
