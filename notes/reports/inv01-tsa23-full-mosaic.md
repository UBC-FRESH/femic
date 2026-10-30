# INV-01 TSA 23 full-domain run

## Run identity

| Field | Value |
| --- | --- |
| Run ID | `inv01-tsa23-20261030` |
| Date | 2026-10-30 (PDT/UTC) |
| FEMIC code | `cc3c8ce` (PR #474) |
| TSA 23 IDF cards | `5ea8319` (PR #470) |
| Allocation | Sockeye `st-gep-1`; Chinook `ch-gep-1` |
| Grid | 25 m, UTM zone 10N, `EPSG:3157` |
| Grid origin | `(549275, 5784675)` |
| Model scope | 14-plot TSA 23 IDF pilot cards; **not operational** |

This report is the evidence record for the largest TSA 23 run completed so far.
The executable runbook is in `examples/inv01_tsa23_full/`; the Sphinx guide is
`docs/guides/inv01-tsa23-full-run.rst`.  Machine-readable metadata, including
hashes and failure names, is in `notes/reports/inv01-tsa23-full-mosaic.json`.

## Inputs and grid

The LidarBC selection intersected the TSA 23 boundary in EPSG:3005:

- 9,568 candidate point-cloud tiles
- 4,693 candidate 1 m DEM tiles
- 5,899 point-cloud/DEM tile pairs with a positive-area overlap
- 907 point-cloud tiles had no matching 1 m DEM and were skipped

Each pair was processed independently into a 25 m global grid.  The common
origin was required because per-DEM origins would not align cell IDs across tile
boundaries.  Settings were:

- `grid_size_m = 25`
- `grid_origin_x = 549275`
- `grid_origin_y = 5784675`
- `height_threshold_m = 2.0`
- `min_returns = 10`
- `min_cover_pct = 10`

The run produced 93 batches of 64 tiles (the last batch had 11).  Of 5,899
pairs, 5,875 produced usable cells; 24 produced no cell with enough first
returns.  The 24 names are recorded in the JSON evidence file.

## Processing evidence

### Download

The download helper ran on Sockeye against the public LidarBC object store.  The
run downloaded 5,899 LAZ and 3,167 DEM files.  The last download log update was
`2026-10-30 02:02:21 PDT`.  The auto-submit log first wait was
`2026-10-30 08:57:49 UTC` (`01:57 PDT`), and the compute array was submitted at
`02:28:07 PDT`.  The exact download start was not preserved, so no exact
download wall-time is claimed here.

The old downloader reported 24 failures.  Those were HTTP 416 responses on
already-complete `.part` files; the files were present and the run used them.
The runbook downloader handles that case as success.

### Compute

| Field | Value |
| --- | --- |
| Slurm job | `13794758` |
| Array tasks | 93 |
| Submitted | `2026-10-30 02:28:07 PDT` |
| Last array task ended | `2026-10-30 02:57:52 PDT` |
| Wall time | `29 min 45 s` (1,785 s) |
| Concurrency | 8 tasks |
| Resources | 32 CPUs and 150 GB per task, `skylake`, exclusive |
| Approximate core-hours | 124 |
| Array states | 82 `COMPLETED`, 11 `FAILED` |
| Parts written | 93 `batch_*.parquet` |
| Scratch part bytes | 652,286,074 |
| Batch 0 validation | 64 tiles, 169,286 cells, 0 bad |

The 11 `FAILED` array states are not missing parts: the worker writes its part
before returning nonzero when one tile in the batch is bad.  All 93 parts exist.
The failures correspond to the 24 no-return tiles listed in the JSON evidence.

### Archive

All archival transfers used the Chinook guest collection `UBC FRESH Chinook
Allocation` via Globus.  The S3 endpoint was not used because object reads and
writes return `AccessDenied`.

| Label | Globus task | Files | Bytes | Requested (UTC) | Completed (UTC) |
| --- | --- | ---: | ---: | --- | --- |
| `inv01 raw laz` | `ca0a93ab-d443-11f1-b9dd-0effda64b40f` | 5,899 | 2,162,599,779,082 | 09:25:05 | 10:15:26 |
| `inv01 raw dem` | `d00e29a2-d443-11f1-a172-0effda64b40f` | 3,167 | 20,578,123,602 | 09:25:15 | 09:26:42 |
| `inv01 parts` | `d11f8c73-d443-11f1-b334-0affd629e535` | 94 | 650,187,144 | 09:25:17 | 09:25:31 |
| `inv01 parts final` | `2ed341b0-d44a-11f1-81c3-02ffc7f41b19` | 95 | 652,592,957 | 10:10:51 | 10:11:05 |
| `inv01 products` | `4e94bc74-d44b-11f1-aa21-0effda64b40f` | 4 | 487,626,418 | 10:18:54 | 10:19:08 |

The raw LAZ transfer took 50 min 21 s at about 714 MB/s (2.16 TB).  The DEM and
parts transfers completed in under two minutes.  The final products transfer
took 14 s.

Chinook paths:

- `inv01/raw/laz/`
- `inv01/raw/dem/`
- `inv01/parts2/`
- `inv01/products/`

### Output artifacts

Local reducer output was produced on 2026-10-30 between 10:09 and 10:12 UTC:

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| `features_full.parquet` | 334,514,970 | `296c31f60d51438d459d7f2d4ad7a20796f04e3dd8548260daae543804183a22` |
| `inventory_full.parquet` | 114,518,458 | `19be051c05e839bebca9b252ba733a1300c138452a354e096892cc69182aaf03` |
| `tsa23_idf_full_25m.tif` | 38,592,390 | `0d4dabe9a896cbaffaedfeeb804922150ae9bb6e4a835d673a558c352481512a` |
| `summary_full.json` | 600 | `cd85c850b91834c44764c065c52738381081817aa3075904214b327ad809910c` |

The three-band raster has bands `lorey_height_m`, `ba_m2_ha`, and `vol_m3_ha`,
with `-9999` nodata.  The local copies used for this record were under
`/srv/shared-data/gep/ws4/tmp/inv01-data/inv01_tsa23/`; they are not tracked in git.  The canonical copies
are in `inv01/products/` on Chinook.

## Results

After deduplication by `fragment_id` and clipping cell centres to the TSA 23
polygon:

- 9,523,476 feature cells
- 6,573,196 cells inside the height-card predictor range
- 2,942,755 cells inside the BA/volume predictor ranges

| Attribute | Cells | Mean | Median | Min | Max |
| --- | ---: | ---: | ---: | ---: | ---: |
| Lorey height (m) | 6,573,196 | 16.09 | 16.18 | 9.92 | 22.03 |
| Basal area (m2/ha) | 2,942,755 | 23.87 | 23.12 | 10.73 | 42.01 |
| Gross volume (m3/ha) | 2,942,755 | 139.33 | 129.71 | 40.32 | 312.19 |

The lower modelled counts are the model-card predictor ranges, not processing
failures.

## Coverage

- TSA 23 area: 12,353.18 km2
- union of usable tile footprints intersecting the TSA: 7,949.00 km2
- tile-footprint coverage: 64.35%
- model-domain grid area: 5,952.17 km2
- modelled-cell coverage: 48.18%

This is not full TSA 23 coverage.  In addition to the 907 no-DEM tiles, parts of
the TSA have no suitable public point cloud.  The map must not be described as
wall-to-wall TSA 23 inventory.

## Software environment

Sockeye compute environment:

- Python 3.12.7
- numpy 2.5.4
- pandas 3.1.0
- rasterio 1.5.2
- laspy 2.7.0
- pyarrow 26.0.0
- geopandas 1.2.0
- shapely 2.2.0
- pyproj 3.8.0
- fiona 1.10.1

## Reproduction

1. Build the paired manifest with
   `examples/inv01_tsa23_full/build_manifest.py`.
2. Split it with `split_manifest.py` (2 download shards, 64-tile batches).
3. Download on a Sockeye login/DTN node with `download_tiles.py`.
4. Run `compute_batches.sbatch` (93 tasks, 8 concurrent, 32 CPUs).
5. Transfer raw, parts, and products to Chinook through Globus.
6. Reduce with `reduce_full.py` and the TSA 23 IDF cards.

The full command sequence and environment variables are in
`examples/inv01_tsa23_full/README.md` and the Sphinx guide
`docs/guides/inv01-tsa23-full-run.rst`.

## Limits

- The 14-plot IDF cards are pilot calibrations, not operational models.
- No independent P48/P49 validation or complete VRI reconciliation.
- 64% tile-footprint coverage and 48% modelled-cell coverage.
- 907 no-DEM tiles and 24 no-return tiles were not filled.
- S3 object reads remain blocked by policy; Globus and Sockeye scratch are the
  active path.

## Follow-up checks

A VRI screening comparison and an omitted-tile priority analysis are recorded in
`notes/reports/inv01-tsa23-vri-reconciliation.md` and
`notes/reports/inv01-tsa23-gap-priority.md`.  They show that the current surface
is not operationally validated and that the 907 omitted tiles cover 1,962 km2
inside TSA 23.  A four-plot external PSP holdout is recorded in
`notes/reports/inv01-tsa23-psp-holdout.md`; it confirms that the volume card is
not ready.  The Sphinx guide is `docs/guides/inv01-tsa23-validation.rst`.
