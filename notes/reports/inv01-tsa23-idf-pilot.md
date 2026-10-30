# INV-01 TSA 23 IDF pilot

## Feasibility result

The public FAIB PSP plots are usable for TSA 23.

- 190 FAIB plots in the 100 Mile House TSA
- 25 measured since 2018
- 22/25 have LidarBC point-cloud coverage within +/-2 years
- 19 of those are IDF
- 14 IDF plots have downloadable LidarBC point clouds and can be matched to
  their plot visit

The earlier 1 m CHM route only gave 7 contemporaneous IDF plots because the
2019 acquisitions do not have a matching public 1 m DEM/DSM tile.  Switching to
first-return point-cloud metrics removed that blocker.

## Fit

Data:

- 14 public FAIB PSP plots, IDF, 100 Mile House TSA
- LidarBC 2019/2024 point clouds, first returns, heights above 2 m
- Plot support matched to the FAIB plot header (`PLOT_AREA_MAIN`, `F_RAD`;
  equivalent radius for square plots, 11.28-17.98 m)
- Ground attributes from live trees DBH >= 9.1 cm and `PHF_TREE`
- Predictors: first-return mean, CV, p95, and cover above 2 m

Models (LOOCV, leave-one-plot-out):

| Attribute | Form | Predictors | LOOCV RMSE | R2 |
| --- | --- | --- | ---: | ---: |
| Lorey height (m) | identity | `Lhp95` | 0.688 | 0.952 |
| Basal area (m2/ha) | log | `Lhmean`, `CC2m` | 4.414 | 0.581 |
| Gross volume (m3/ha) | log | `Lhmean`, `CC2m` | 20.666 | 0.834 |

Cards:

- `config/inventory/models/als_tsa23_idf_lorey_height_2026.json`
- `config/inventory/models/als_tsa23_idf_basal_area_2026.json`
- `config/inventory/models/als_tsa23_idf_gross_volume_2026.json`

Training rows: `notes/reports/inv01-tsa23-training-plots.csv`.

## What changed from the CWH pilot

The CWH pilot used CHM proxies and an 11.28 m window.  This TSA 23 pilot uses:

- first-return point-cloud metrics
- the actual FAIB plot area/radius
- local IDF plots
- plots that are contemporaneous with the point-cloud acquisition

That is why the height and volume errors are much lower.  The basal-area model
is still the weak one; BA is harder to recover from canopy structure alone.

## Limits

- 14 plots is a pilot sample, not an operational calibration.
- LOOCV is not a spatial holdout; several plots are clustered.
- No independent P48/P49 field-plot validation.
- No wall-to-wall TSA 23 feature grid or map has been produced yet.
- The cards require a first-return point-cloud feature table; the existing
  `inventory-features` helper produces CHM proxies and is not a substitute.
- Ground attributes were reconstructed from tree detail; reconcile with the
  official FAIB compiled attributes before operational use.

## Next

1. Build a first-return point-cloud grid feature extractor for one TSA 23
   LidarBC block.
2. Apply the three cards and compare with VRI at the same support.
3. Add more IDF plots, preferably a spatial holdout, before claiming operational
   accuracy.
4. Run P48/P49 reconciliation when the plot tables are available.
