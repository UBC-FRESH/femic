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
- **56** of those are independent of the 14 TSA 23 training plots, the 24
  regional high-biomass plots, and the four original external plots
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

### Independent plots

| Card | Attribute | In-range plots | Bias | MAE | RMSE | R2 |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Experimental hybrid | BA | 54 | 1.29 m2/ha | 6.23 | **8.02** | 0.57 |
| Experimental hybrid | Volume | 44 | -10.35 m3/ha | 50.81 | **62.93** | 0.58 |
| Published TSA 23 | BA | 10 | 3.62 m2/ha | 8.28 | 9.89 | |
| Published TSA 23 | Volume | 10 | 33.48 m3/ha | 60.61 | 74.74 | |

The original four-plot external check was BA RMSE 6.67 and volume RMSE 42.09.
The larger independent set is materially worse, especially for volume.

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
does not justify replacing them.

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
