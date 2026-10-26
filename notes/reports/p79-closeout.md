# P79 Close-Out: Native LidarBC Data-Product Pipeline

Phase: P79 / `#211`
Branch: `feature/p79-lidar-pipeline`
Status: complete; merged in PR #368 as `65b9057`
Consumers: WS4 P52 (`UBC-FRESH/ws4#317`), FHOPS P14 (`UBC-FRESH/fhops#188`)

## Outcome

P79 makes FEMIC the authoritative upstream producer of LidarBC data products:

- discovery and AOI selection;
- resumable materialization with checksums;
- native-grid terrain, slope, and zonal statistics;
- terrain-derived stream candidates with review caveats;
- native CHM, canopy structure, VRI uncertainty, and optional tree ingestion;
- versioned product bundles with manifest/checksum/licence provenance;
- CLI, docs, and a shared consumer contract.

WS4 and FHOPS consume versioned bundles. Neither reimplements discovery or
materialization.

## Commit Range

`50c856e` through `465a840` on `feature/p79-lidar-pipeline`, covering
P79.1-P79.9.

## Delivered Surface

Package modules:

- `femic.lidar.catalog`
- `femic.lidar.materialization`
- `femic.lidar.terrain`
- `femic.lidar.hydrography`
- `femic.lidar.canopy`
- `femic.lidar.trees`
- `femic.lidar.products`

CLI:

```bash
femic lidar discover
femic lidar materialize
femic lidar materialization-status
femic lidar terrain
femic lidar streams
femic lidar canopy
femic lidar trees
femic lidar bundle
femic lidar inspect
```

Contracts:

- `femic.lidar.selection.v1`
- `femic.lidar.materialization.v1`
- `femic.lidar.terrain_qa.v1`
- `femic.lidar.stream_candidates.v1`
- `femic.lidar.canopy_qa.v1`
- `femic.lidar.canopy_structure.v1`
- `femic.lidar.individual_tree.v1`
- `femic.lidar.product.v1`
- `femic.lidar.bundle.v1`

## Evidence

Contract and CLI:

- `planning/phase79_lidar_product_pipeline.md`
- `docs/guides/lidar-data-products.rst`
- `docs/guides/lidar-materialization.rst`
- `docs/guides/lidar-terrain-products.rst`
- `docs/guides/lidar-stream-candidates.rst`
- `docs/guides/lidar-canopy-products.rst`
- `docs/guides/lidar-product-bundles.rst`
- `docs/guides/lidar-instance-integration.rst`

TFL 6 pilots:

- `planning/phase79_p79_6_tfl6_pilot.md`
- `planning/phase79_p79_6_tfl6_pilot_metrics.json`
- `planning/phase79_p79_6_tfl6_slope_thresholds.csv`
- `planning/phase79_p79_6_tfl6_stream_thresholds.csv`
- `planning/phase79_p79_7_tfl6_canopy_pilot.md`
- `planning/phase79_p79_7_tfl6_canopy_pilot_metrics.json`
- `planning/phase79_p79_7_tfl6_vri_comparison.csv`

Shared bundle and consumer parity:

- `planning/phase79_p79_9_shared_bundle_validation.md`
- `planning/phase79_p79_9_shared_parity_metrics.json`
- `planning/phase79_p79_9_shared_parity_rows.csv`
- `planning/phase79_p79_9_consumer_parity.json`

## Verification

FEMIC:

- 192 LiDAR tests passed.
- 100% branch coverage for `femic.lidar.catalog`,
  `femic.lidar.materialization`, `femic.lidar.products`,
  `femic.lidar.terrain`, `femic.lidar.hydrography`, and
  `femic.lidar.canopy`; 99% for `femic.lidar.trees`.
- `ruff check` passed for all new LiDAR modules and tests.
- `mypy src/femic/lidar` passed.
- `sphinx-build -b html docs _build/html -W` passed.
- Selected docs-contract tests passed.
- Full-repo test/lint/type baseline remains non-green on pre-existing unrelated
  Windows runtime, unmaterialized instance submodule, and docs-contract
  surfaces. PR CI covers docs and package checks.

WS4 P52.1:

- 5 consumer contract tests passed.
- Sphinx `-W` passed.
- `scripts/check_workflow.py` passed.
- Targeted ruff/mypy passed.
- Commit `8f4feb0`.

FHOPS P14.1:

- 5 consumer contract tests passed.
- Sphinx `-W` passed.
- Targeted ruff/mypy passed.
- Commit `8b6adb6c`.

## Consumer Parity

Bundle:

- `bundle_id`: `lidarbc-995fb1f771f4d7fe`
- `bundle_version`: `2026.10.0-tfl6-pilot`
- products: `dem`, `dsm`, `slope`, `chm`, `canopy`
- 13,390,216 bytes.

Both consumers pinned the bundle, validated checksums, licence, CRS, native
resolution, vertical datum, and source tiles, and summarized seven shared TFL 6
polygons. Slope/CHM mean and p95 matched exactly:

- maximum absolute difference: `0.0`
- tolerance: `1e-9`

## Performance And Storage

- P79.6 materialization: 3 tiles, 60.0 MiB, 7.18 s.
- Shared bundle build: 5 products, 12.8 MiB, 3.24 s.
- Canopy build: 3.28 MiB, 4.10 s.
- Full TFL 6 DEM estimate: roughly 13 GiB before point clouds; annex storage
  and bounded AOIs are mandatory.

## Limitations And Deviations

- No provincial mirror or province-wide release.
- One 1 km TFL 6 pilot AOI; not a TFL 6-wide validation.
- LidarBC currently exposes no CHM/canopy or individual-tree layer. CHM is
  derived; tree ingestion is optional.
- Stream candidates remain screening-only; FWA agreement was too low for
  riparian use.
- No field-accuracy claim.
- Consumer phase numbers were corrected from WS4 P43/FHOPS P13 to WS4
  P52/FHOPS P14 because the original numbers collided with existing roadmap
  phases.
- No TFL 6 model-input promotion, production data switch, release, or tag was
  made.

## Merge Record

- PR: #368
- Squash merge: `65b9057`

## Recommendation

Merge P79, close parent `#211`, and continue the consumer phases:

- WS4 P52.2/P52.3;
- FHOPS P14.2/P14.3.

The next producer work is driven by consumer needs, not new P79 scope.
