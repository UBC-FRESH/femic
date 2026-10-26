Site-Index Reconciliation (``femic.site-index.reconciliation.v1``)
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
estimate.

Quick Contract
--------------

- Reconciliation schema: ``femic.site-index.reconciliation.v1``.
- SIBEC tidy schema: ``femic.sibec.v1``.
- VRI reader schema: ``femic.vri.site-index.v1``.
- VDYP reader schema: ``femic.vdyp.site-index.v1``.
- Grain: one output row per VRI feature.
- Join keys: ``feature_id``; BEC unit key; canonical species key.
- Default conflict threshold: ``2.0`` m.
- Default SIBEC reference minimum: ``7`` plots.
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

- ``region``, ``bgc_unit``, ``site_series``, ``site_association``;
- ``species``;
- ``plot_count``, ``mean_site_index``, ``standard_error``; and
- ``schema_version = femic.sibec.v1``.

``aggregate_sibec_by_bgc_unit`` then groups site-series rows to BEC unit +
species and reports:

- ``si_sibec_mean`` (weighted by plot count when counts are available,
  otherwise unweighted);
- ``si_sibec_min`` and ``si_sibec_max``;
- mean standard error;
- total plot count; and
- the number of contributing site series.

The mean is **not** a polygon-level SIBEC estimate. VRI does not carry a site
series, so SIBEC site-series rows cannot be joined directly to a polygon. The
SIBEC **range** is used to test whether a VRI or VDYP value is outside the
BEC-unit/species envelope; the mean is retained as descriptive provenance.

The 2013 approximation is the first supported table. The 2014 addendum is not
merged yet; it has a different merged-cell layout and is an explicit follow-up.

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
   * - ``si_sibec_vdyp`` / ``..._min`` / ``..._max``
     - SIBEC values for the VDYP species.
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
     --out-csv out/tsa46_si_reconciliation.csv \
     --out-json out/tsa46_si_summary.json \
     --delta-threshold 2.0

Use ``--sibec-sheet`` to select a non-default worksheet. The command prints a
JSON summary and writes the feature-level CSV and summary when paths are
provided.

TSA46 Pilot (26 October 2026)
-----------------------------

Inputs:

- VRI checkpoint 8, 171,826 features;
- VDYP layer table, primary layer only; and
- SIBEC 2013 approximation, 4,023 source rows.

Results:

- ``si_vri`` present: 171,826 (100%);
- ``si_vri_est`` present: 5,966 (3.5%);
- ``si_vdyp`` present: 3,384 (2.0%);
- ``si_sibec_vri`` present: 136,807 (79.6%);
- complete triple: 2,285 (1.3%);
- conflicts at 2.0 m: 25,643 (14.9%);
- partial: 143,898 (83.8%); and
- missing: 0.

The high partial count is driven by sparse VDYP layer site index, not by a
missing VRI value. The SIBEC range test is the main polygon-level consistency
check in this pilot. The VDYP layer field is too sparse to support a complete
three-way comparison; AU-level TSA SI is a separate grain and is not forced
into this table.

Known Limits
------------

- SIBEC 2013 approximation only; the 2014 addendum is not yet merged.
- SIBEC is aggregated to BEC unit + species because VRI has no site series.
  The range check is a screening test, not a site-series assignment.
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
