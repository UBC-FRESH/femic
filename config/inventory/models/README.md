# Inventory ALS model cards

These cards are explicit inputs to `femic lidar inventory`.  They contain the
coefficients and provenance used by the reader; FEMIC does not invent
coefficients at prediction time.

## Published transfer cards

| Card | Attribute | Link | Output | Source |
| --- | --- | --- | --- | --- |
| `als_boreal_lorey_height_2012.json` | Lorey's mean height | log | m | Wulder et al. (2012) |
| `als_boreal_basal_area_2012.json` | Basal area | log | m2/ha | Wulder et al. (2012) |
| `als_boreal_gross_volume_2012.json` | Gross stem volume | log | m3/ha | Wulder et al. (2012) |

Source: Wulder, M.A., White, J.C., Bater, C.W., Coops, N.C., Hopkinson, C., and
Chen, G. (2012). Lidar plots - a new large-area data collection option:
context, concepts, and case study. *Canadian Journal of Remote Sensing*
38(5): 600-618. https://doi.org/10.5589/m12-049.

The published equations predict 25 m x 25 m lidar-plot totals from first
returns above 2 m.  The basal-area and volume cards use `output_scale: 16.0`
to report per hectare.  These are **boreal Canada** models; applying them to
CWH is a transfer test, not an operational inventory.

## Local CWH pilot cards

| Card | Attribute | Link | Output | Fit |
| --- | --- | --- | --- | --- |
| `als_cwh_lorey_height_2026.json` | Lorey height | identity | m | 14 FAIB PSP plots, CWH northern Vancouver Island |
| `als_cwh_basal_area_2026.json` | Basal area | log | m2/ha | same |
| `als_cwh_gross_volume_2026.json` | Gross volume | log | m3/ha | same |

These are FEMIC pilot fits, not published models.  Training used public FAIB
PSP ground plots and LidarBC 2023/2024 1 m CHMs, with a 0-2 year plot/LiDAR
offset and 11.28 m circular CHM metrics.  Nine additional plots with a 4-6 year
offset were held out as a temporal stress test.

The CWH cards are **CWH northern Vancouver Island** only.  They have 14
training plots and CHM proxies; they are not TSA 23 operational models.  See
`notes/reports/inv01-cwh-local-model-tfl6.md`.

## TSA 23 IDF pilot cards

| Card | Attribute | Link | Output | Fit |
| --- | --- | --- | --- | --- |
| `als_tsa23_idf_lorey_height_2026.json` | Lorey height | identity | m | 14 FAIB PSP plots, 100 Mile House IDF |
| `als_tsa23_idf_basal_area_2026.json` | Basal area | log | m2/ha | same |
| `als_tsa23_idf_gross_volume_2026.json` | Gross volume | log | m3/ha | same |

These use first-return point-cloud metrics and the actual FAIB plot support,
not CHM proxies.  LOOCV RMSE is 0.688 m height, 4.414 m2/ha basal area, and
20.666 m3/ha volume.  They are pilot cards: 14 plots, no spatial holdout, and
no P48/P49 validation.  See `notes/reports/inv01-tsa23-idf-pilot.md`.
