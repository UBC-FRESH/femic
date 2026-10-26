# P79.7 TFL 6 Canopy Pilot

Phase: P79.7 / `#348`
Status: complete
Parent: P79 / `#211`
Branch: `feature/p79-lidar-pipeline`
Instance context: `external/femic-tfl6-instance`

## Purpose

Pilot native CHM/canopy products and optional individual-tree ingestion on the
same bounded TFL 6 AOI used by P79.6. Compare CHM evidence with VRI height and
cover and record uncertainty.

This is not a field-accuracy claim and it does not promote canopy products into
TFL 6 model inputs.

## AOI And Sources

- AOI: `881700,627500,882700,628500` in EPSG:3005 (100 ha).
- LidarBC DEM: 2 layer-5 1 m tiles from P79.6.
- LidarBC DSM: 2 layer-1 1 m tiles, materialized in 6.39 s (13.6 MiB).
- Vertical datum: Canadian Geodetic Vertical Datum of 2013.
- VRI: `data/input/tfl_6/vri_2025_r1_poly_tfl6.gpkg`, clipped to the AOI
  (7 polygons with CHM coverage).

## LidarBC Product Inventory

The feature service exposes only DEM, DSM, and point-cloud indexes. It has:

- no CHM or canopy-metric layer;
- no individual-tree layer.

CHM and canopy structure are therefore FEMIC-derived from DSM/DEM. Individual-
tree ingestion remains optional and is tested with a public-safe fixture; no
LidarBC tree product was available to ingest at this AOI.

## CHM Results

Outputs:

- `runtime/dem/p79_7_canopy_pilot/canopy/chm.tif`
- `canopy_structure.json`
- `canopy_qa.json` / `canopy_qa.csv`
- `vri_canopy_comparison.csv`

CHM QA:

- valid pixels: `1,000,000` (100.0 ha);
- nodata pixels: `0`;
- negative `DSM-DEM` pixels: `95` (clamped to zero);
- mean height: `8.62 m`;
- median height: `7.71 m`;
- p90 height: `18.96 m`;
- p95 height: `21.78 m`;
- p99 height: `28.01 m`;
- max height: `55.42 m`.

Canopy cover:

| Threshold | Cover |
| --- | ---: |
| >=2 m | 70.94% |
| >=5 m | 60.09% |
| >=10 m | 41.03% |
| >=20 m | 7.84% |

Runtime for mosaic, CHM, structure, and VRI comparison: `4.10 s`.
Canopy outputs: `3.28 MiB`.

## VRI Comparison

Seven VRI polygons had enough valid CHM pixels. Summary:

- height bias (CHM p95 minus VRI height): `-2.93 m`;
- height MAE: `4.08 m`;
- height RMSE: `6.16 m`;
- cover bias (CHM >=2 m minus VRI crown closure): `+23.87` percentage points;
- cover MAE: `39.47` percentage points.

Polygon-level examples:

- polygon `23339461`: VRI height `37.0 m`, CHM p95 `37.10 m`;
- polygon `23339458`: VRI height `22.7 m`, CHM p95 `20.49 m`;
- polygon `16624698`: VRI height `30.5 m`, CHM p95 `16.35 m`;
- polygon `23339462`: missing VRI height/cover, but CHM p95 `8.24 m`.

The height comparison is usable as uncertainty evidence but is variable. CHM
cover at >=2 m is systematically much higher than VRI crown closure and must
not be treated as crown-closure equivalence.

## Individual-Tree Contract

Added optional point-product ingestion:

- required `tree_id`, `height_m`;
- optional `crown_radius_m`, `species`;
- duplicate/missing-field checks;
- height/crown distributions and species counts;
- optional block summaries with matching-CRS points and polygons.

No new segmentation algorithm was added. No LidarBC individual-tree product was
available in the current public index.

## Findings Against TFL 6 Needs

1. Native 1 m CHM is technically viable from LidarBC DSM/DEM.
2. CHM p95 is reasonably comparable to VRI height overall but has large
   polygon-level variance.
3. CHM cover at 2 m is not VRI crown closure; a higher threshold or explicit
   calibration is required before operational use.
4. No LidarBC individual-tree product is available; tree ingestion remains an
   optional contract for future sources.
5. The CHM workflow is fast and small at AOI scale, but full-TFL6 canopy work
   inherits the multi-GiB DSM annex requirement.

## Follow-Up List

1. TFL 6: test CHM cover thresholds (5/10/20 m) against VRI closure and decide
   whether a calibrated cover product is useful for operability or riparian
   screening.
2. TFL 6: if a public individual-tree product becomes available, ingest and
   summarize it by block; do not synthesize trees.
3. FEMIC: include CHM/canopy products in the P79.8 product plan when a consumer
   needs them.
4. FEMIC: keep canopy products out of model-input promotion until TFL 6
   review explicitly accepts a threshold/calibration.

## Caveats

- Single 1 km AOI, not TFL 6-wide.
- CHM depends on DSM/DEM vintage, grid alignment, and vertical-datum agreement.
- VRI height/cover are inventory estimates, not field truth.
- No field-accuracy claim is made.
- No private WFP LiDAR, DTSM, ITI, or LEFI data was used.
