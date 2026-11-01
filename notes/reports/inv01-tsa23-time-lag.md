# INV-01 time-lag sensitivity and strict validation correction

## Why this exists

The earlier BC IDF validation labeled 56 independent plots.  Checking the
candidate fallback exposed a stricter issue: **18 of those 56** used a fallback
LiDAR tile 6-11 years from the ground measurement.  The strict current-condition
set is **38 independent plots**, not 56.

The time-lag extraction adds the older covered plots so the full population can
be checked without treating it as current-condition validation.

## Coverage

- 969 latest IDF PSP plots across BC
- 573 with LidarBC point-cloud and DEM coverage
- 111 candidate plots within five years
- 88 of those produced usable features
- **70** stayed within ±5 years
- **18** used fallback tiles at 6-11 years
- **38** strict independent plots remain after removing training, high-biomass,
  and external plots
- 462 older covered plots
- 381 older plots produced usable features
- 469 total usable features; 435 independent in the lag sensitivity

## Strict current-condition result

| Model | Attribute | In-range | Bias | MAE | RMSE |
| --- | --- | ---: | ---: | ---: | ---: |
| Hybrid | BA | 36 | 2.69 m2/ha | 6.78 | **8.86** |
| Hybrid | Volume | 28 | -2.20 m3/ha | 53.26 | **67.02** |
| Published | BA | 10 | 3.62 m2/ha | 8.28 | 9.89 |
| Published | Volume | 10 | 33.48 m3/ha | 60.61 | 74.74 |

The earlier 56-plot expanded result was BA 8.02 and volume 62.93; the strict
0-5 year result is worse.  Both are reported, but 38 plots is the defensible
current-condition comparison.

## Time-lag sensitivity

Independent plots only, fixed cards, in-range rows:

| Lag | Plots | Hybrid BA RMSE | Hybrid volume RMSE | Published BA RMSE | Published volume RMSE |
| --- | ---: | ---: | ---: | ---: | ---: |
| 0-5 | 38 | 8.86 | 67.02 | 9.89 | 74.74 |
| 6-10 | 58 | 8.06 | 53.20 | 5.22 | 62.72 |
| 11-20 | 184 | 8.41 | 71.97 | 8.38 | 59.42 |
| 21-30 | 147 | 9.74 | 99.06 | 9.45 | 89.45 |
| >30 | 8 | 13.06 | 116.44 | 15.22 | 82.47 |

The older plots do not provide a hidden large validation set.  The volume error
grows strongly with lag, and both cards are erratic across TSAs.  This is a
sensitivity result, not a current-condition validation.

## Decision

- Use **38 strict independent plots** for current-condition validation.
- Keep the 56-row expanded and 435-row lag results as sensitivity tables.
- Do not promote the hybrid, the refit, or a time-lag model.
- Keep the published TSA 23 pilot cards as the default, with abstention outside
  predictor ranges.
- Update public text that previously called 56 plots independent without noting
  the fallback lag.

## Artifacts

- `psp/bc_validation/bc_idf_features_time_lag.csv`
- `psp/bc_validation/bc_idf_time_lag_predictions.csv`
- `psp/bc_validation/bc_idf_time_lag.json`
- `psp/compute_bc_time_lag_metrics.py`
- `psp/evaluate_time_lag.py`
