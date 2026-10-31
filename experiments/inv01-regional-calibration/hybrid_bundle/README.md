# INV-01 hybrid regional model bundle

Experimental TSA 23 IDF bundle:

- BA: linear regional card (`models/als_tsa23_idf_basal_area_regional_2026c.json`)
- Volume: second-order polynomial log-volume model (`nonlinear/model.json`)
- Height: current published card, unchanged

The bundle is experimental.  Both cards load through the standard FEMIC model
reader; the volume card uses the `log_terms` model type (constant, log,
log-square, and log-product terms).

`hybrid_cv.json` contains the paired external and leave-one-TSA-out results.
