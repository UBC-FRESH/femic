# INV-01 time-aware refit

## Design

The full covered PSP population was used to test whether the older plots can
improve the model when the LiDAR-ground time offset is explicit.

- Development: all usable plots except the strict 0-5 year independent test set
  (**431 plots**)
- Strict test: **38 independent plots** within five years
- Candidate forms: log-log models with and without `Lhmean`, `CC2m`, `Lhp95`,
  and a time-lag term (`dy`, `dy^2`)
- Selection: leave-one-TSA-out CV on development rows; the strict test was
  scored once

This is a temporal-correction experiment.  It does not turn old ground
measurements into current-condition validation.

## Results

| Model | Features | Development CV | Strict test | TSA 23 strict |
| --- | --- | ---: | ---: | ---: |
| Time-aware BA | Lhmean, CC2m | 9.91 | **7.92** | 11.50 |
| Time-aware volume | Lhmean, CC2m, lag | 89.96 | **62.67** | 93.86 |
| Fixed hybrid, strict | — | — | 8.86 | 15.02 |
| Fixed hybrid, expanded 56 | — | — | 8.02 | 15.02 |

The time-aware model improves the pooled strict-test error, but it is worse on
TSA 23: BA RMSE 11.50 and volume RMSE 93.86.  The pooled improvement comes from
other TSAs and is not a TSA 23 result.

`vol_cc_lag` also cannot be applied wall-to-wall without a defined lag.  A
current LiDAR run would use `dy=0`, but that is not the same model that was
selected on the mixed-lag data.

## Decision

- Do not promote the time-aware refit.
- Keep the strict 38-plot result as the current-condition evidence.
- Keep the published TSA 23 cards as the default; the hybrid and time-aware
  models remain research-only.
- The 435-plot time-lag result is still sensitivity evidence, not validation.

The old archive is useful for understanding how error grows with time, but it
does not solve the small recent TSA 23 high-biomass validation population.

## Artifacts

- `psp/bc_validation/bc_idf_time_aware_refit.json`
- `psp/refit_time_aware.py`
