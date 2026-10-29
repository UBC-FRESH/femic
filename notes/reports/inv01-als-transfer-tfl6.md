# INV-01 ALS transfer benchmark: TFL 6 pilot

## Scope

This is a contract and transfer benchmark, not an operational inventory.
The model cards are the published Wulder et al. (2012) boreal equations.  The
bundle is the FEMIC TFL 6 pilot LiDAR bundle; its CHM is 1 m, EPSG:3005, and
100 ha.

- Bundle: `lidarbc-995fb1f771f4d7fe` / `2026.10.0-tfl6-pilot`
- CHM: `runtime/dem/p79_9_shared/bundle/products/chm__04__chm.tif`
- Grid: 25 m x 25 m; 1,459 cells with at least three above-2 m CHM pixels
- Predictors: CHM mean, CV, p95, and percent cover above 2 m
- Model cards: `config/inventory/models/als_boreal_*_2012.json`

The predictors are CHM proxies for the published first-return metrics.  The
TFL 6 pilot is CWH; the model cards are boreal.  Both are deliberate transfer
stressors, not claims that the model is locally calibrated.

## Result

| Attribute | Cells | Mean | Median | Min | Max |
| --- | ---: | ---: | ---: | ---: | ---: |
| Lorey's height (m) | 1,459 | 18.14 | 18.07 | 3.56 | 33.65 |
| Basal area (m2/ha) | 1,459 | 18.92 | 18.57 | 0.37 | 54.82 |
| Gross volume (m3/ha) | 1,459 | 85.39 | 81.79 | 0.46 | 315.22 |

Predicted rows are in `/tmp/opencode/inv01_tfl6/` (not tracked).  Each run
also writes a manifest with the bundle pin, model hash, applicability warning,
and the caveat that no plot validation table was supplied.

## Conventional-inventory comparison

Six VRI-2025 polygons in the CHM footprint have non-null volume/BA/height.
This is a **conventional inventory comparison**, not independent field
validation.  Mean values over the six polygons are:

| Attribute | ALS transfer | VRI-2025 | Difference |
| --- | ---: | ---: | ---: |
| Lorey's height (m) | 19.91 | 28.25 | -8.34 |
| Basal area (m2/ha) | 22.24 | 66.89 | -44.65 |
| Gross volume (m3/ha) | 106.21 | 397.30 | -291.09 |

Per-polygon values are in `/tmp/opencode/inv01_tfl6/vri_comparison.csv`.

The transfer underpredicts strongly.  That is expected from a boreal model
applied to CWH, a CHM proxy standing in for first-return metrics, and a VRI
comparison rather than an independent plot check.  The run is evidence against
promoting these cards to an operational CWH/TSA 23 model.

## Reproduction

```bash
femic lidar inventory-features \
  --bundle <tfl6-bundle> \
  --output /tmp/inv01/features_25m.csv \
  --grid-size-m 25

for attr in lorey_height basal_area gross_volume; do
  femic lidar inventory \
    --bundle <tfl6-bundle> \
    --features /tmp/inv01/features_25m.csv \
    --model config/inventory/models/als_boreal_${attr}_2012.json \
    --output-dir /tmp/inv01/${attr} \
    --fragment-id-field fragment_id
 done
```

## Next

Do not use these values in WS4/FHOPS planning.  A defensible CWH/TSA 23
inventory needs co-located field plots, a locally fitted model card, and an
independent P48/P49-style validation table.  The `inventory-features` CHM
helper can be replaced by first-return point-cloud metrics without changing
the output contract.
