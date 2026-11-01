# INV-01 TSA 23 BA-only pilot acceptance

## Decision

**Accept as experimental; reject for operational use.**

The BA-only product is internally consistent and consumer-readable.  It remains
a 14.9% coverage pilot with an 8.86 m2/ha strict independent error and only seven
independent TSA 23 plots.

## Consumer checks

| Check | Result |
| --- | --- |
| BA table | 2,942,755 rows, 8 columns |
| Attribute | `ba_m2_ha` only |
| BA raster | 1 band, `basal_area_m2_ha`, EPSG:3157, 25 m |
| Nodata | `-9999` |
| Raster valid pixels | 2,942,755 |
| Row/pixel identity | equal |
| Table mean | 23.87 m2/ha |
| Raster mean | 23.87 m2/ha |
| Value range | 10.73–42.01 m2/ha |
| Manifest hashes | match |

## Consumer rules

- Use only valid raster pixels or BA table rows.
- Treat `-9999` as abstention, not zero.
- Do not use height or volume from this product.
- Do not extrapolate outside the BA card range.
- Keep the native 25 m EPSG:3157 grid.
- Do not use for operational decisions.

## Validation

- Strict independent set: 38 plots; 36 BA in range; RMSE 8.86 m2/ha.
- Independent TSA 23 subset: 7 plots; BA RMSE 15.02 m2/ha.
- Coverage: 14.9% of TSA area; 9.35% of the full raster because the raster
  extends outside the TSA.

## VRI/THLB

VRI/THLB geometry is not materialized in the instance annex checkout.  The
acceptance record says **not computed**; it does not infer forest/THLB coverage.

## Evidence

- `metadata/inv01/tsa23_ba_pilot_acceptance.json`
- `metadata/inv01/tsa23_ba_pilot_manifest.json`
- `notes/reports/inv01-tsa23-ba-pilot-release.md`
- Data archive: `inventory_ba_pilot.parquet`, `tsa23_ba_pilot_25m.tif`

## What was not verified

- No WS4 or FHOPS end-to-end consumer run was executed.
- No VRI/THLB cross-tab was computed.
- No operational fitness-for-use test was possible.
