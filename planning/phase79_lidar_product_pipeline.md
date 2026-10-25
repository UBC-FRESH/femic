# Phase 79 LidarBC Product Pipeline Notes

Phase: P79 / `#211`
Branch: `feature/p79-lidar-pipeline`
Status: active
Owner: FEMIC (producer); WS4 P43 (`#317`) and FHOPS P13 (`#188`) are consumers.

## Ownership boundary

FEMIC owns:

- LidarBC project and tile discovery.
- AOI selection and selection manifests.
- Reproducible DataLad/Arbutus materialization and partial fetch.
- Native-resolution terrain, canopy, and precision-forestry compilation.
- Versioned product manifests and delivery bundles.

WS4 and FHOPS own only consumer-side schema, spatial, scenario, and cost
integration. They must pin a FEMIC product version instead of re-running
discovery or materialization.

## Source contract (P79.1)

Public source surfaces:

- Portal: <https://lidar.gov.bc.ca/pages/download-discovery>
- Catalogue record:
  <https://catalogue.data.gov.bc.ca/dataset/lidarbc-open-lidar-data-portal>
- Licence: OGL-BC,
  <https://www2.gov.bc.ca/gov/content/data/open-data/open-government-licence-bc>
- Index item:
  <https://www.arcgis.com/home/item.html?id=5f6a1f31212a4cb2826743d2e52ef02a>
- Feature service:
  <https://services6.arcgis.com/ubm4tcTYICKBpist/arcgis/rest/services/LiDAR_BC_S3_Public/FeatureServer>

The catalogue record's package metadata uses an `Access Only` wrapper because
the dataset record fronts an ArcGIS application. The portal, the index item,
and the province's open-data listing identify the data products themselves as
OGL-BC. FEMIC records `OGL-BC` as the product licence and keeps the catalogue
metadata caveat in the source contract.

Observed service layers:

| Layer | Name | FEMIC product |
| --- | --- | --- |
| 0 | LiDAR project data extent | `project_extent` metadata |
| 1 | LiDAR DSM index 1:2,500 | `dsm` |
| 2 | LiDAR DSM index 1:10,000 | `dsm` |
| 3 | LiDAR DSM index 1:20,000 | `dsm` |
| 4 | LiDAR point cloud index | `point_cloud` |
| 5 | LiDAR DEM index 1:2,500 | `dem` |
| 6 | LiDAR DEM index 1:20,000 | `dem` |

Tile records carry, where populated: filename, BCGS map tile, storage path,
grid scale, acquisition year, projection token, spacing, contract, operator,
point density, vertical datum, point format/classes, S3 download URL, accuracy
report URL, and geometry in BC Albers (`EPSG:3005`).

CHM, canopy structure metrics, and individual-tree products are not separate
layers in this feature service. CHM and canopy metrics are FEMIC-derived
products (P79.7); individual-tree products are consumed from LidarBC where a
suitable public product exists.

Not supported by this phase:

- Private or restricted LiDAR.
- A full provincial download mirror.
- Silent reprojection, resampling, or vertical-datum transformation.
- Treating the catalogue wrapper licence field as the product licence.

## P79.1 implementation

Add `femic.lidar.catalog` with:

- A frozen source-family descriptor.
- Product-to-layer mapping for point cloud, DEM, and DSM.
- Frozen tile, AOI, and selection-manifest records.
- Pure parsing and bbox-intersection helpers.
- A paginated discovery helper over the public feature service.
- A JSON selection-manifest writer.

Storage boundary for P79.1: discovery metadata only. Tile bytes are not
downloaded. P79.2 adds resumable materialization under an explicit instance or
external-data root.

Dependency boundary: discovery uses the Python standard library. Terrain and
canopy processing dependencies are selected in P79.3/P79.7.

## P79.2 implementation

Add `femic.lidar.materialization` with:

- `femic.lidar.materialization.v1` manifests under an explicit output root.
- Managed layout:
  `<root>/lidarbc/<product>/layer_<id>/<year>/<filename>`.
- `.part` files and HTTP Range resume; a ranged `200` response restarts the
  tile from zero.
- Per-tile status (`pending`, `downloading`, `partial`, `verified`, `failed`),
  attempts, last attempt time, last error, resumed byte offset, expected size,
  observed ETag, local size, and SHA-256.
- Manifest writes before a download and after every tile, so interrupted runs
  resume from the last successful state.
- `femic lidar materialize` and `femic lidar materialization-status`, including
  `--plan-only`, `--max-tiles`, `--timeout-sec`, `--fail-fast`, and
  `--require-complete`.
- Selection digest and tile-set pinning so one manifest cannot mix AOIs or
  catalog snapshots.

P79.2 downloads selected public tiles only. It does not compile terrain or
canopy products and does not create a provincial mirror.

## P79.8 implementation

Add `femic.lidar.products` with:

- `femic.lidar.product_plan.v1` input plans.
- `femic.lidar.product.v1` manifests and `femic.lidar.bundle.v1` layout.
- Deterministic `bundle_id` from selection digest, bundle/processing versions,
  and packaged product metadata/checksums.
- Per-product SHA-256, size, CRS, native resolution, vertical datum, licence,
  source tiles/layers, derived flag, and lineage.
- `femic lidar bundle` and `femic lidar inspect` CLI surfaces.
- `validate_lidar_product_bundle` with checksum, licence, CRS, resolution,
  derived-labelling, provenance, and source-tile checks.
- A public-safe bounded AOI fixture with DEM, DSM, CHM, and canopy artifacts.

Bundle layout:

```text
<bundle>/
  manifest.json
  provenance/selection.json
  products/<product>__<index>__<filename>
```

P79.8 packages compiled products only. It does not download tiles or compile
rasters. P79.2 and P79.3/P79.7 remain the materialization and compilation
phases.

The consumer pin rule is: pin `bundle_id` and `bundle_version`, then verify
each product `sha256`. WS4 P43 and FHOPS P13 must honor the recorded CRS,
resolution, and vertical datum and must not re-run discovery or
materialization.

## Current edge

1. P79.1 source/tile-index contract and tests (complete).
2. P79.2 resumable materialization and status surfaces (complete).
3. P79.8 product manifest, bundle, CLI, and fixture (complete).
4. P79.3/P79.7 terrain and canopy products.
5. P79.9 cross-repo validation with WS4/FHOPS.

Do not start consumer integration in WS4/FHOPS until a real shared bundle
passes both consumer contracts.
