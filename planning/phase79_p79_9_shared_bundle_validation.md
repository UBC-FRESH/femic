# P79.9 Shared Product Bundle Validation

Phase: P79.9 / `#350`
Status: complete; P79 close-out queued
Parent: P79 / `#211`
Branch: `feature/p79-lidar-pipeline`
Bundle: `lidarbc-995fb1f771f4d7fe`
Bundle version: `2026.10.0-tfl6-pilot`

## Purpose

Build a shared TFL 6 product bundle end to end, validate its native-resolution
and licence contract, and attempt cross-repo parity with WS4 P43 and FHOPS P13.

## End-To-End Build

1. **Discovery:** `femic lidar discover` on the 1 km TFL 6 AOI
   `881700,627500,882700,628500` for DEM and DSM.
2. **Materialization:** reused the verified P79.6 DEM tiles and P79.7 DSM
   tiles.
3. **Terrain:** reused the 1 m LidarBC DEM/DSM mosaics and the Horn percent
   slope raster.
4. **Canopy:** reused the 1 m CHM and canopy structure report.
5. **Packaging:** `femic lidar bundle` with five products:
   - `dem`
   - `dsm`
   - `slope`
   - `chm`
   - `canopy`

Bundle path:

```text
external/femic-tfl6-instance/runtime/dem/p79_9_shared/bundle/
```

Selection and plan:

```text
external/femic-tfl6-instance/runtime/dem/p79_9_shared/selection.json
external/femic-tfl6-instance/runtime/dem/p79_9_shared/product_plan.json
```

Validation: `femic lidar inspect --json` returned valid, with no errors or
warnings.

## Native Contract Checks

All checks passed:

| Check | Result |
| --- | --- |
| Product count | 5 |
| Bundle bytes | 13,390,216 |
| Manifest schema | `femic.lidar.product.v1` |
| Layout | `femic.lidar.bundle.v1` |
| Per-product SHA-256 | all match |
| Per-product size | all match |
| Bundle file vs source file SHA-256 | all match |
| CRS | `EPSG:3005` for all products |
| Resolution | 1.0 m for all products |
| Vertical datum | CGVD2013 for all products |
| Licence | OGL-BC for all products |
| Source tiles | all subset of the selection |
| Canopy structure schema | `femic.lidar.canopy_structure.v1` |

Bundle build runtime: 3.24 s; about 191 MB peak RSS.

## Shared-AOI Reference Aggregations

The bundle was read back and slope/CHM values were recomputed over seven VRI
polygons in the AOI. Bundle values were compared with the pre-bundle source
rasters:

- 7/7 polygons matched exactly for slope;
- 7/7 polygons matched exactly for CHM;
- bundle/source equality tolerance: exact byte/value equality;
- aggregate tolerance: 0.0 (same bundle raster).

Examples:

| Polygon | Valid px | Slope mean | Slope p95 | CHM mean | CHM p95 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 23339458 | 731,180 | 22.59% | 49.08% | 8.70 m | 20.49 m |
| 23339461 | 22,372 | 51.55% | 146.55% | 19.20 m | 37.10 m |
| 16624698 | 66,306 | 22.01% | 43.12% | 1.99 m | 16.35 m |
| 19212607 | 12,342 | 27.32% | 68.29% | 16.54 m | 30.03 m |

These are reference support aggregations for WS4-style fragment/block means and
FHOPS-style block p95 values. They are not results from WS4 or FHOPS consumer
code.

## Consumer Parity

WS4 P52.1 (`UBC-FRESH/ws4#318`, branch `feature/p52-lidar-products`, commit
`8f4feb0`) and FHOPS P14.1 (`UBC-FRESH/fhops#189`, branch
`feature/phase14-lidar-products`, commit `8b6adb6c`) now implement the consumer
contract.

Both consumers:

- pinned bundle `lidarbc-995fb1f771f4d7fe` / `2026.10.0-tfl6-pilot`;
- validated schema, OGL-BC licence, checksums, CRS, 1 m resolution, CGVD2013,
  and source-tile membership;
- read `slope` and `chm` through the bundle manifest;
- summarized seven shared TFL 6 polygons with mean and p95.

Results:

- WS4 and FHOPS matched exactly on every value;
- maximum absolute difference: `0.0`;
- both also matched the FEMIC producer-side reference rows exactly;
- documented tolerance: `1e-9`; result is within tolerance.

This is actual independent consumer code, not a simulated check.

## Recommended Consumer Contract

Both consumers should:

1. pin `bundle_id` and `bundle_version`;
2. verify every product `sha256` and size;
3. require `EPSG:3005`, 1.0 m, CGVD2013, and OGL-BC for this bundle;
4. read `dem`, `dsm`, `slope`, `chm`, and `canopy` by `relative_path`;
5. map support explicitly:
   - WS4 fragment/block mean and p95 slope;
   - FHOPS block/landing p95 slope and CHM;
6. reject silent reprojection/resampling;
7. compare against
   `planning/phase79_p79_9_shared_parity_rows.csv` with a documented tolerance
   (recommended: 1e-9 for identical raster reads).

## Performance And Storage

- Shared bundle: 12.8 MiB, 5 products.
- Bundle build: 3.24 s.
- Materialization evidence (P79.6): 60.0 MiB, 3 tiles, 7.18 s.
- Canopy build (P79.7): 3.28 MiB output, 4.10 s analysis.
- Full TFL 6 DEM estimate remains roughly 13 GiB before point clouds.

## P79.9 Status

Complete:

- bounded AOI product build;
- native-resolution, CRS, vertical-datum, licence, checksum, and source-tile
  checks;
- performance and storage evidence;
- shared-AOI reference aggregation fixture;
- actual WS4 P52.1 and FHOPS P14.1 consumer parity with max difference `0.0`;
- docs, roadmap, changelog updates.

P79 close-out is queued for maintainer approval.

## Next Steps

1. Review and merge WS4 P52.1 (`8f4feb0`) and FHOPS P14.1 (`8b6adb6c`).
2. Continue WS4 P52.2/P52.3 and FHOPS P14.2/P14.3 for compiled-dataset and
   scenario integration.
3. Close P79 after maintainer approval of this validation report.

## Caveats

- Single 1 km TFL 6 AOI, not a provincial release.
- The shared AOI is one 1 km TFL 6 pilot, not a provincial release.
- No model-input or production data switch was made.
