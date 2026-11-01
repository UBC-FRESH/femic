# INV-01 independent BC IDF validation

## Why this exists

The earlier INVENTORY-01 evidence called four TSA 23 plots the external check.
Those four plots are the high-biomass external tile.  They are not the available
validation set.

The full PSP archive contains **969 latest IDF plots** across BC.  Matching each
plot to the LidarBC point-cloud and DEM index gives:

- **573** plots with both point-cloud and DEM coverage
- **151** of those in TSA 23
- **111** plots with the latest ground measurement within five years of the
  selected LiDAR
- **88** plots with usable first-return metrics after DEM nodata screening
- **70** of those stayed within five years; **18** used fallback tiles at 6-11
  years
- **38** strict independent plots after removing training, high-biomass, and
  external plots
- **56** recent independent plots including the 18 fallback tiles
- **25** TSA 23 plots are within five years; **7** are independent

The remaining 462 covered plots have ground measurements 6-55 years away from
the available LiDAR.  They are recorded as coverage, but are not used as
current-condition validation.

## Method

- Fixed experimental cards; no refit on the validation plots.
- First-return point-cloud metrics above 2 m, plot radius from the FAIB plot
  header.
- 1 m LidarBC DEM, with DEM nodata sentinels removed before height calculation.
- Candidate point clouds are tested closest-year first; a later tile is used
  only when the first has no usable returns in the plot.
- Predictions are evaluated only inside each card's `predictor_ranges`.

## Results

### Strict independent plots (0-5 years)

| Card | Attribute | In-range plots | Bias | MAE | RMSE |
| --- | --- | ---: | ---: | ---: | ---: |
| Experimental hybrid | BA | 36 | 2.69 m2/ha | 6.78 | **8.86** |
| Experimental hybrid | Volume | 28 | -2.20 m3/ha | 53.26 | **67.02** |
| Published TSA 23 | BA | 10 | 3.62 m2/ha | 8.28 | 9.89 |
| Published TSA 23 | Volume | 10 | 33.48 m3/ha | 60.61 | 74.74 |

### Recent expanded (56 plots, includes 6-11 year fallback)

| Card | Attribute | In-range plots | RMSE |
| --- | --- | ---: | ---: |
| Experimental hybrid | BA | 54 | 8.02 |
| Experimental hybrid | Volume | 44 | 62.93 |

The original four-plot external check was BA RMSE 6.67 and volume RMSE 42.09.
The strict set is worse than the expanded set, and both are worse than the four
external plots.

### Independent errors by TSA

| TSA | Plots | BA in-range | BA RMSE | Volume in-range | Volume RMSE |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 2 | 11 | 11 | 6.18 | 10 | 57.18 |
| 5 | 20 | 20 | 7.05 | 20 | 64.15 |
| 9 | 3 | 3 | 1.96 | 3 | 72.28 |
| 18 | 3 | 2 | 10.91 | 3 | 73.53 |
| 22 | 1 | 1 | 0.99 | 1 | 22.83 |
| 29 | 8 | 7 | 4.37 | 7 | 61.90 |

TSA 23 independent plots: 7; hybrid BA RMSE **15.02 m2/ha**; no independent TSA
23 volume plot falls inside the volume card's predictor range.  This is a
failure of applicability, not a successful external check.

### TSA 23 descriptive set

The 25 TSA 23 plots within five years, including training and external plots:

- Experimental hybrid: BA RMSE 9.44 (24 in range), volume RMSE 23.74 (17 in range)
- Published cards: BA RMSE 2.82 (11 in range), volume RMSE 22.76 (11 in range)

The published cards look better on the small in-range TSA 23 subset.  The hybrid
does not justify replacing them.  The strict 0-5 year set is 38 plots; the
56-plot expanded set and the 435-plot lag sensitivity are not current-condition
validation.

## Decision

- Do **not** promote the hybrid to operational inventory.
- Keep the hybrid as an experimental research bundle, not an operational
  default.
- Keep the published TSA 23 cards unchanged.
- Replace the "four-plot external" claim with this 56-plot independent result in
  the model cards and instance documentation.
- Report in-range counts alongside every RMSE; wide BC IDF plots frequently fall
  outside the current cards' predictor ranges.

## Artifacts

- `psp/bc_validation/bc_idf_features_111.csv`
- `psp/bc_validation/bc_idf_validation_predictions.csv`
- `psp/bc_validation/bc_idf_validation.json`
- `psp/bc_idf_plot_lidar_matches.csv`
- `psp/lidarbc_bc_index.json`
- `psp/compute_bc_validation_metrics_parallel.py`
- `psp/evaluate_bc_validation.py`
