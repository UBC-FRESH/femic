# P135 TFL6 ground-bundle end-to-end

Date: 2026-11-04
Phase: P135
Parent issue: #581
Task: #582
Status: real-tile run complete; no field validation

## Input

- Tile: `bc_092l062_4_1_2_xyes_8_utm9_20240316_20240317.laz`
- URL: https://nrs.objectstore.gov.bc.ca/gdwuts/092/092l/2024/pointcloud/bc_092l062_4_1_2_xyes_8_utm9_20240316_20240317.laz
- Licence: OGL-BC.
- Acquisition: 2024-03-16/17.
- CRS: NAD83(CSRS) / UTM zone 9N + CGVD2013, EPSG:3156 compound.
- Input points: 246,658,211.
- Input size: 1.5 GB.
- SHA-256: `0d45310118cf7d02d9e2c5cec1c8229ee098733a2a7316163db74aadfaa58b6e`.

The tile was materialized once into `runtime/p135/` and is not tracked.

## Blocks and crop

- Seven FHOPS TFL6 blocks, 100 ha total, source CRS EPSG:3005.
- Blocks were reprojected to the tile CRS for the crop only.
- Crop bbox with a 50 m margin: `[593648.98, 5611680.89, 594790.07, 5612820.53]`.
- Crop points: 137,428,675.
- Crop size: 815 MB.
- Crop SHA-256: `7391a3f7680118f57cb4b494f62df8225bf2761ae96a387b6290ba926db9a807`.

## Ground bundle

- Points: 137,428,675.
- Predicted ground: 36,662,162 (26.68%).
- Low-point flags: 27,880,539 (20.29%).
- SOR removed: 6,025,777 (4.39%).
- Seed points: 1,207,358.
- PTD iterations: 8.
- HAG p50: 6.7494 m.
- HAG p75: 13.9346 m.
- HAG p90: 18.793 m.
- HAG p95: 21.4207 m.
- HAG p99: 26.6657 m.
- HAG max: 54.2834 m.
- Runtime: 1,821.9 s (30.4 min).
- Warnings: none.
- Bundle schemas: `femic.ground-bundle.v1`, `femic.ground-qa.v1`.

## Block summary

| Block | Points | Ground | Ground fraction | Low fraction | HAG mean | HAG p95 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| T6_23339490 | 6,355,770 | 1,352,820 | 21.28% | 15.30% | 8.17 m | 20.20 m |
| T6_23339461 | 3,052,389 | 411,237 | 13.47% | 10.56% | 14.49 m | 31.95 m |
| T6_23339462 | 3,553,655 | 2,776,908 | 78.14% | 65.74% | 1.72 m | 13.66 m |
| T6_23339458 | 86,743,659 | 21,454,139 | 24.73% | 18.45% | 7.95 m | 20.68 m |
| T6_16625195 | 7,975,110 | 1,316,030 | 16.50% | 11.93% | 11.07 m | 24.97 m |
| T6_16624698 | 4,967,140 | 3,578,509 | 72.04% | 60.13% | 3.80 m | 23.45 m |
| T6_19212607 | 1,296,633 | 171,426 | 13.22% | 9.84% | 13.29 m | 28.20 m |

The 73 ha block `T6_23339458` dominates the crop with 86.7M points. The per-block ground
fraction is a point-composition metric, not a ground-area fraction.

## What this shows

- The full lane runs on a real 246M-point LidarBC tile:
  materialize once -> crop to the block AOI -> ground bundle -> seven-block summary.
- The local crop reduces 1.5 GB / 246M points to 815 MB / 137M points.
- The ground adapter handles the 137M-point crop in about 30 minutes.
- The summary writes one row per block with ground/low fractions and HAG statistics.
- The reader/summary accepts the compound tile CRS and the block polygons after explicit
  reprojection.

## What this does not show

- No field or manual ground labels. The ground fractions are not accuracy estimates.
- No independent validation of the ground labels.
- The crop is still large; this is a workstation run, not a CI job.
- The tile and bundle bytes are not tracked.
- The per-block HAG distribution is a point statistic, not a stand-level inventory attribute.

## Reproduction

1. Materialize the tile into `runtime/p135/`.
2. Run the P134 crop with the block bbox in the tile CRS.
3. Run `fresh-urban-forest-lab` `write_ground_bundle` on the crop.
4. Run `femic lidar ground-summary` on the bundle and the reprojected blocks.

The local runner is `runtime/p135/run_e2e.py` and is not tracked.
