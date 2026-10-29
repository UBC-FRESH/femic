# INV-01 local CWH model pilot: TFL 6

## Scope

This is the first local CWH fit, not an operational inventory.  It uses public
FAIB ground plots and LidarBC 1 m DEM/DSM CHMs.  The target is the FEMIC
`inventory.als` contract; the model cards are under
`config/inventory/models/`.

- Ground data: public FAIB PSP tree detail and plot headers.
- LiDAR: LidarBC 2023/2024 DEM and DSM, 1 m, EPSG:3005.
- Plot support: 11.28 m circular CHM metrics.
- Training: 14 plots with a plot-visit/LiDAR offset of 0-2 years.
- Temporal holdout: 9 plots with a 4-6 year offset.
- Response: live trees, DBH >= 9.1 cm, expanded by `PHF_TREE`.
- Ground attributes: Lorey height, basal area, whole-stem volume.
- Predictors: CHM mean, CV, p95, and cover above 2 m.

The predictor set is a CHM proxy for first-return point-cloud metrics.  The
ground/LiDAR offset and small sample are explicit limitations.

## Fitted cards

| Attribute | Form | Predictors | LOOCV RMSE | Temporal holdout RMSE |
| --- | --- | --- | ---: | ---: |
| Lorey height (m) | identity | `Lhp95` | 2.14 | 2.07 |
| Basal area (m2/ha) | log | `Lhmean`, `CC2m` | 9.27 | 11.56 |
| Gross volume (m3/ha) | log | `Lhmean`, `CC2m` | 62.22 | 114.60 |

Training coefficients:

- `cwh-lorey-height-psp-lidarbc-2026`: `1.78345 + 0.97258 * Lhp95`.
- `cwh-basal-area-psp-lidarbc-2026`: `exp(-2.64411 + 0.66320 ln(Lhmean) + 1.03354 ln(CC2m)) * 1.01081`.
- `cwh-gross-volume-psp-lidarbc-2026`: `exp(-1.34517 + 1.33511 ln(Lhmean) + 0.83886 ln(CC2m)) * 1.00745`.

The `output_scale` values are Duan smearing corrections for the log models.
Training and holdout rows are in `notes/reports/inv01-cwh-training-plots.csv`.

## TFL 6 application

The CWH cards were applied to the TFL 6 25 m grid after dropping cells below
the training cover range (`CC2m < 34.5%`).  That leaves 1,289 forested cells.

| Attribute | Mean | Median | Min | Max |
| --- | ---: | ---: | ---: | ---: |
| Lorey height (m) | 22.08 | 21.43 | 11.84 | 47.76 |
| Basal area (m2/ha) | 37.27 | 37.27 | 10.07 | 78.49 |
| Gross volume (m3/ha) | 309.08 | 286.73 | 67.26 | 1130.08 |

Conventional VRI-2025 comparison over seven overlapping polygons (six with
attributes; means of polygon values):

| Attribute | Local ALS | VRI-2025 | Difference |
| --- | ---: | ---: | ---: |
| Lorey height (m) | 25.36 | 28.25 | -2.89 |
| Basal area (m2/ha) | 39.87 | 66.89 | -27.02 |
| Gross volume (m3/ha) | 379.69 | 397.30 | -17.61 |

Volume is close at the pilot scale, height is moderately low, and basal area is
strongly low.  The VRI is a conventional inventory, not an independent field
validation, and the model has only 14 training plots.  This is evidence that
the local fit is more credible than the boreal transfer, but it is not a
production model.

## Why this is not operational

- 14 training plots are too few for a stable local ABA model.
- Nine temporal holdout plots are a stress test, not a design-based validation.
- The predictors are CHM proxies, not first-return point-cloud metrics.
- The VRI comparison is not an independent P48/P49 plot reconciliation.
- The model is fitted to CWH northern Vancouver Island, not TSA 23.
- Basal area remains materially biased low.

## Reproduction

```bash
femic lidar inventory-features \
  --bundle <tfl6-bundle> \
  --output /tmp/inv01/features_25m_cwh.csv \
  --grid-size-m 25 \
  --min-cover-pct 34.5

for attr in cwh_lorey_height cwh_basal_area cwh_gross_volume; do
  femic lidar inventory \
    --bundle <tfl6-bundle> \
    --features /tmp/inv01/features_25m_cwh.csv \
    --model config/inventory/models/als_${attr}_2026.json \
    --output-dir /tmp/inv01/${attr} \
    --fragment-id-field fragment_id
 done
```

## Next

Acquire additional co-located CWH plots and, if possible, first-return point
cloud metrics for the training plots.  Then refit with a held-out design and
run the P48/P49 reconciliation before any WS4/FHOPS use.
