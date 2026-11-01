# INV-01 hybrid regional model bundle

Experimental TSA 23 IDF bundle:

- BA: linear regional card (`models/als_tsa23_idf_basal_area_regional_2026c.json`)
- Volume: second-order polynomial log-volume model (`nonlinear/model.json`)
- Height: current published card, unchanged

The bundle is experimental.  Both cards load through the standard FEMIC model
reader; the volume card uses the `log_terms` model type (constant, log,
log-square, and log-product terms).

`hybrid_cv.json` contains the paired external and leave-one-TSA-out results.

Independent BC IDF validation (2026-11-01): 56 independent plots, BA RMSE
8.02 m2/ha (54 in range), volume RMSE 62.93 m3/ha (44 in range).  The seven
independent TSA 23 plots give BA RMSE 15.02; no independent TSA 23 volume plot
is inside the predictor range.  The four-plot external check was not
representative.  See `notes/reports/inv01-tsa23-bc-validation.md`.
