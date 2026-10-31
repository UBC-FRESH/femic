# INV-01 hybrid regional model bundle

Experimental TSA 23 IDF bundle:

- BA: linear regional card (`models/als_tsa23_idf_basal_area_regional_2026c.json`)
- Volume: second-order polynomial log-volume spec (`nonlinear/MODEL_SPEC.json`)
- Height: current published card, unchanged

The bundle is experimental.  The BA card loads through the standard FEMIC model
reader; the nonlinear volume model is applied by `nonlinear/apply.py` because
the current reader only supports linear predictors.

`hybrid_cv.json` contains the paired external and leave-one-TSA-out results.
