# INV-01 TSA 23 full-domain pilot

## Scope

This is the largest TSA 23 run completed so far. It uses every published
LidarBC point-cloud tile that intersects the TSA 23 boundary and has a matching
1 m DEM tile.

- 5,899 point-cloud/DEM tile pairs
- 93 compute batches of 64 tiles
- first-return point-cloud metrics
- global 25 m grid in UTM zone 10N (`EPSG:3157`)
- grid origin: `(549275, 5784675)`
- minimum 10 above-2 m first returns per cell
- cells outside the TSA 23 polygon dropped

The raw data is archived in Chinook under `inv01/raw/`; per-batch Parquet parts
are under `inv01/parts2/`.

## Coverage

- TSA 23 area: 12,353 km2
- union of usable point-cloud tiles: 7,949 km2 intersecting the TSA (64%)
- model-domain grid cells: 9,523,476
- cell area represented: 5,952 km2

This is not full TSA 23 coverage. 907 point-cloud tiles had no matched 1 m DEM
and were skipped; additional TSA area has no suitable public point cloud.

## Results

After deduplication and boundary filtering:

- 9,523,476 feature cells
- 6,573,196 cells inside the height-card predictor range
- 2,942,755 cells inside the BA/volume predictor ranges

| Attribute | Cells | Mean | Median | Min | Max |
| --- | ---: | ---: | ---: | ---: | ---: |
| Lorey height (m) | 6,573,196 | 16.09 | 16.18 | 9.92 | 22.03 |
| Basal area (m2/ha) | 2,942,755 | 23.87 | 23.12 | 10.73 | 42.01 |
| Gross volume (m3/ha) | 2,942,755 | 139.33 | 129.71 | 40.32 | 312.19 |

The three-band 25 m GeoTIFF is:
`/tmp/opencode/inv01_tsa23/tsa23_idf_full_25m.tif` (not tracked).

## Processing evidence

- 93 Parquet parts, 0 missing batch parts
- 3 tiles raised “no grid cells had enough first returns”
- raw LAZ transfer: 5,899 files, ~2.0 TB, Chinook task `ca0a93ab-...`
- DEM transfer: 3,167 files, ~20.6 GB, succeeded
- parts transfer: 95 files, ~0.65 GB, succeeded
- batch 0 validation: 64 tiles, 169,286 cells, 0 bad

## Limits

- The 14-plot IDF cards are still pilot calibrations, not operational models.
- No independent P48/P49 validation or full VRI reconciliation.
- Coverage is 64% of TSA 23 by tile footprint and 48% by modelled cell area.
- S3 object reads remain blocked by policy; this run uses Globus and Sockeye
  scratch, not Chinook S3.
