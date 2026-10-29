# Inventory ALS model cards

These cards are explicit inputs to `femic lidar inventory`.  They contain
published coefficients and provenance; FEMIC does not refit them in this
layer.

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
to report per hectare; the height card is already a per-plot mean.

These are **boreal Canada** models.  Applying them to the CWH TFL 6 pilot is a
transfer test, not an operational inventory.  The `inventory-features` helper
computes CHM proxies, not first-return point-cloud metrics, so the transfer
test also carries a predictor-definition mismatch.  Do not use the resulting
values for planning without a co-located CWH/TSA plot calibration and an
independent validation table.
