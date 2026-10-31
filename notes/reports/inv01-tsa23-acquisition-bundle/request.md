# Request: TSA 23 IDF high-biomass PSP remeasurement and co-located LidarBC

**Subject:** TSA 23 high-biomass permanent sample plots — remeasurement and co-located lidar request

**Request date:** 2026-10-31

**Request ID:** `inv01-tsa23-high-biomass-20261031`

## Request

Please provide current remeasurement and co-located LidarBC point clouds for the
TSA 23 (100 Mile House) IDF high-biomass permanent sample plots listed in
`targets.csv`.  The immediate priority is site `4033798`; the remaining ten are
historical high-biomass locations that need a current visit plus lidar.

The current archive has only four TSA 23 IDF high-biomass plots with usable
LidarBC support.  That is not enough to extend the published inventory cards or
to validate the volume model outside its current low/mid-biomass range.

## Requested data

For each plot:

- `SITE_IDENTIFIER`, `CLSTR_ID`, `VISIT_NUMBER`, `PLOT`
- current measurement date and visit number
- plot centre in EPSG:3005 plus latitude/longitude
- plot shape, area, radius/width/length, and BAF/expansion method
- live/dead tree detail with species, DBH, height, `PHF_TREE`, `BA_TREE`, and
  `VOL_WSV`
- BEC zone/subzone/variant and leading species

For the lidar:

- raw point cloud, or at least 1 m DEM/DSM, covering the full plot support
- acquisition date, CRS, point format/classes, first-return availability
- exact tile footprint and any edge issues

## Acceptance

- At least 20 TSA 23 IDF plots with measurement within ±2 years of lidar.
- At least half above `Lhmean` 14.1882 m or observed volume >220 m3/ha.
- A tile-level spatial holdout independent of the existing 14 training plots.

## Exclusions

- TSA 22 (Okanagan) is not TSA 23 training; it is transfer-test-only.
- TSA 29 (Williams Lake) is an exploratory comparison, not TSA 23 calibration.

## Files

- `targets.csv` — priority sites and last known attributes
- `targets.geojson` — EPSG:3005 plot locations
- `targets_map.png` — overview map
- `request.json` — machine-readable request
- `MANIFEST.sha256` — integrity check
