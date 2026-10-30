# INV-01 TSA 23 point-cloud grid pilot

## Scope

This is the first wall-to-wall-style feature grid for the TSA 23 IDF pilot.
It uses one LidarBC 2024 point-cloud tile and its matching 1 m DEM, both in
EPSG:3157.

- Point cloud: `bc_092p063_3_4_3_xyes_8_utm10_20240719_20240720.laz`
- DEM: `bc_092p063_3_4_3_xyes_8_utm10_20240719_20240720.tif`
- Grid: 25 m
- First-return height threshold: 2 m
- Minimum 50 above-threshold returns and 10% cover per cell

The extractor writes `Lhmean`, `Lhcv`, `Lhp95`, `CC2m`, and return counts. It
does not fit a model.

## Feature result

- 3,857 grid cells with sufficient first returns
- 3,328 cells inside the TSA 23 IDF height-card predictor range
- 2,196 cells inside the basal-area/volume-card `Lhmean + CC2m` ranges

Applying the TSA 23 IDF cards only inside their declared ranges:

| Attribute | Cells | Mean | Median | Min | Max |
| --- | ---: | ---: | ---: | ---: | ---: |
| Lorey height (m) | 3,328 | 18.13 | 18.27 | 10.09 | 22.03 |
| Basal area (m2/ha) | 2,196 | 30.83 | 31.55 | 12.14 | 41.71 |
| Gross volume (m3/ha) | 2,196 | 201.50 | 203.25 | 46.68 | 309.87 |

Rows are in `/tmp/opencode/inv01_tsa23/inventory_als_bc092p063_3_4_3.csv`
(not tracked).

## Limits

- One point-cloud tile, not the full TSA 23.
- The cards are 14-plot pilot fits; this is not an operational inventory.
- Predictor ranges exclude a large fraction of the tile; the map is partial by
  design.
- No independent P48/P49 validation or VRI comparison has been completed for
  this grid.
- Point-cloud tiles must be non-overlapping; the extractor aggregates by cell
  and does not deduplicate overlaps.
- The ground attributes used to fit the cards still need reconciliation with
  the official FAIB compiled attributes.

## Reproduction

```bash
femic lidar inventory-pointcloud-features \
  --pointcloud bc_092p063_3_4_3_xyes_8_utm10_20240719_20240720.laz \
  --dem bc_092p063_3_4_3_xyes_8_utm10_20240719_20240720.tif \
  --output features_25m.csv \
  --grid-size-m 25 \
  --min-returns 50 \
  --min-cover-pct 10
```
