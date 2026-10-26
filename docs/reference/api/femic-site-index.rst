``femic.site_index`` Package
============================

The :mod:`femic.site_index` package owns the provenance and reconciliation
surface for existing British Columbia site-index products. It reads VRI,
VDYP primary-layer, and SIBEC values, joins them at feature/BEC/species grain,
and reports differences without fitting a model or changing a curve.

Start Here If...
----------------

Use this page first if you are trying to:

- load the public SIBEC 2013 workbook into a tidy table;
- read VRI ``SITE_INDEX``/``EST_SITE_INDEX``;
- read VDYP primary-layer site index;
- run or extend the ``femic.site-index.reconciliation.v1`` report; or
- understand why VRI and VDYP values are suppressed when species differ.

Typical Usage
-------------

.. code-block:: python

   from pathlib import Path
   from femic.site_index import (
       aggregate_sibec_by_bgc_unit,
       load_sibec_table,
       load_vdyp_site_index,
       load_vri_site_index,
       reconcile_site_index,
       summarize_reconciliation,
   )

   vri = load_vri_site_index(Path("data/vri_vclr1p_checkpoint8.feather"))
   vdyp = load_vdyp_site_index(Path("data/vdyp_lyr-tsa46.feather"))
   sibec = aggregate_sibec_by_bgc_unit(
       load_sibec_table(Path("data/sibec2013approx_final.xlsx"))
   )
   frame = reconcile_site_index(vri, vdyp, sibec, delta_threshold=2.0)
   summary = summarize_reconciliation(frame, delta_threshold=2.0)

Key Entry Surfaces
------------------

- :func:`femic.site_index.sibec.load_sibec_table`
  Load the public workbook or a CSV into ``femic.sibec.v1``.
- :func:`femic.site_index.sibec.aggregate_sibec_by_bgc_unit`
  Aggregate site-series rows to BEC unit + species with mean, range, plot
  count, and standard error.
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

.. automodule:: femic.site_index.vri
   :members:
   :show-inheritance:

.. automodule:: femic.site_index.vdyp
   :members:
   :show-inheritance:

.. automodule:: femic.site_index.reconcile
   :members:
   :show-inheritance:
