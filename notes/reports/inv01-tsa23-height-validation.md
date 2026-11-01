# INV-01 TSA 23 height validation

## Purpose

The default product included height and BA.  Height had only the 14-plot LOOCV
from the pilot cards, so it was tested on the same strict and lag-aware sets used
for BA and volume.

## Method

- Published height card: identity link, `Lhp95` predictor, range 9.508–24.07 m.
- Ground observation: FAIB Lorey height from the latest PSP visit.
- Predictions outside the card range are abstained, not extrapolated.
- Strict set: independent plots within five years.
- Time-lag set: all independent plots with usable features.

## Strict result

| Set | Plots in range | Bias | MAE | RMSE |
| --- | ---: | ---: | ---: | ---: |
| Strict independent | 19 | 0.33 m | 1.38 m | **2.54 m** |
| TSA 23 strict independent | 6 | 0.61 m | 1.30 m | **4.18 m** |

The pilot-card LOOCV RMSE was **0.688 m**.  The independent height error is much
larger and fails the same standard applied to BA and volume.

## Time-lag sensitivity

Independent plots only, in-range rows:

| Lag | Plots | RMSE |
| --- | ---: | ---: |
| 0-5 years | 19 | 2.54 m |
| 6-10 years | 27 | 1.17 m |
| 11-20 years | 128 | 2.33 m |
| 21-30 years | 107 | 3.45 m |
| >30 years | 3 | 4.20 m |

## Decision

- Height is **not** supported as a default product attribute by independent
  validation.
- Remove height from the default config.
- Keep the published height card available only through an explicit card path
  or a research config.
- Default product is **BA only**.
- Volume remains research-only and withheld.

## Artifacts

- `psp/bc_validation/bc_idf_height_predictions.csv`
- `psp/bc_validation/bc_idf_time_lag_predictions.csv`
- `psp/evaluate_time_lag.py`
