``femic.site_index`` Package
============================

The :mod:`femic.site_index` package owns the provenance and reconciliation
surface for existing British Columbia site-index products. It reads VRI,
VDYP primary-layer, and SIBEC values, joins them at feature/BEC/species grain,
and reports differences without fitting a model or changing a curve.

Start Here If...
----------------

Use this page first if you are trying to:

- load the public SIBEC 2013 workbook and 2014 addendum into a tidy table;
- read VRI ``SITE_INDEX``/``EST_SITE_INDEX``;
- read VDYP primary-layer site index;
- run or extend the ``femic.site-index.reconciliation.v2`` report;
- report the AU-level TSA SI separately; or
- understand why VRI and VDYP values are suppressed when species differ.

Typical Usage
-------------

.. code-block:: python

   from pathlib import Path
   from femic.site_index import (
       aggregate_sibec_by_bgc_unit,
       combine_sibec_tables,
       load_sibec_addendum,
       load_sibec_table,
       load_vdyp_site_index,
       load_vri_site_index,
       reconcile_site_index,
       select_sibec_source,
       summarize_reconciliation,
   )

   vri = load_vri_site_index(Path("data/vri_vclr1p_checkpoint8.feather"))
   vdyp = load_vdyp_site_index(Path("data/vdyp_lyr-tsa46.feather"))
   sibec_table = combine_sibec_tables(
       load_sibec_table(Path("data/sibec2013approx_final.xlsx")),
       load_sibec_addendum(Path("data/2013sisuaddendum_jul2014.xlsx")),
   )
   sibec = select_sibec_source(aggregate_sibec_by_bgc_unit(sibec_table))
   frame = reconcile_site_index(vri, vdyp, sibec, delta_threshold=2.0)
   summary = summarize_reconciliation(frame, delta_threshold=2.0)

Key Entry Surfaces
------------------

- :func:`femic.site_index.sibec.load_sibec_table`
  Load the public workbook or a CSV into ``femic.sibec.v2``.
- :func:`femic.site_index.sibec.load_sibec_addendum`
  Load the 2014 addendum and preserve ``source_table``.
- :func:`femic.site_index.sibec.combine_sibec_tables`
  Concatenate SIBEC sources without collapsing their provenance.
- :func:`femic.site_index.sibec.aggregate_sibec_by_bgc_unit`
  Aggregate site-series rows by source, BEC unit, and species.
- :func:`femic.site_index.sibec.select_sibec_source`
  Choose one explicit source per key with the addendum-first preference.
- :func:`femic.site_index.au.load_au_site_index`
  Read ``03_input`` at the analysis-unit/species grain.
- :func:`femic.site_index.au.summarize_au_site_index`
  Summarize the AU-level report without joining it to polygons.
- :func:`femic.site_index.vri.load_vri_site_index`
  Select VRI site-index fields and build BEC/species keys.
- :func:`femic.site_index.vdyp.load_vdyp_site_index`
  Select primary-layer VDYP site index.
- :func:`femic.site_index.reconcile.reconcile_site_index`
  Produce the feature-level reconciliation table.
- :func:`femic.site_index.reconcile.summarize_reconciliation`
  Produce the JSON-serializable coverage and conflict summary.
- ``python -m femic.site_index``
  Command-line entry point.

Cross-References
----------------

- :doc:`../contracts/site-index-reconciliation`
- :doc:`../../guides/site-index-reconciliation`
- :doc:`../contracts/climate-contract`
- :doc:`../contracts/disturbance-contract`

.. automodule:: femic.site_index
   :members:
   :show-inheritance:

.. automodule:: femic.site_index.sibec
   :members:
   :show-inheritance:

.. automodule:: femic.site_index.au
   :members:
   :show-inheritance:

.. automodule:: femic.site_index.vri
   :members:
   :show-inheritance:

.. automodule:: femic.site_index.vdyp
   :members:
   :show-inheritance:

.. automodule:: femic.site_index.reconcile
   :members:
   :show-inheritance:
