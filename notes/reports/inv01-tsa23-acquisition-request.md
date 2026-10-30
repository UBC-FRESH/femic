# INV-01 TSA 23 high-biomass acquisition request

## Ask

Acquire current field measurements and co-located LidarBC point clouds for
high-biomass TSA 23 IDF permanent sample plots, sufficient to extend and
independently validate the current inventory cards.

Target: **20–30 high-biomass TSA 23 IDF plots**, with current remeasurement and
lidar.  The existing archive has only four such plots with usable point clouds.

## Priority sites

Nearest recent target:

- `4033798` — IDF mw, 2022; 19.17 m Lorey height, 33.12 m2/ha BA, 238.80 m3/ha
  volume; no selected LidarBC point-cloud tile.

Older high-biomass sites requiring remeasurement plus lidar:

| Site | Last measurement | Volume m3/ha |
| --- | ---: | ---: |
| 4024694 | 2012 | 441.1 |
| 4024445 | 2003 | 406.2 |
| 4024439 | 2003 | 365.2 |
| 4025001 | 1999 | 362.5 |
| 4025098 | 1997 | 344.7 |
| 4024440 | 2003 | 305.8 |
| 4024627 | 2002 | 305.5 |
| 4024695 | 2012 | 299.2 |
| 4025376 | 1994 | 256.5 |
| 4025377 | 1994 | 250.4 |

These older measurements are not calibration data for 2019/2024 lidar.  They
identify where new measurements should be taken.

## Required fields

For each plot:

- `SITE_IDENTIFIER`, `CLSTR_ID`, `VISIT_NUMBER`, `PLOT`
- plot centre in BC Albers (EPSG:3005), latitude/longitude
- plot shape, `PLOT_AREA_MAIN`, `F_RAD`, `PLOT_WL/PLOT_LENGTH` where applicable
- measurement date and visit number
- tree detail: species, DBH, height, live/dead status, `PHF_TREE`, `BA_TREE`,
  `VOL_WSV`
- BAF/expansion method and DBH limit
- BEC zone/subzone/variant and leading species

For the lidar:

- raw point cloud or 1 m DEM/DSM at the plot support
- acquisition date and CRS
- point format/classes and first-return availability
- exact tile footprint and any edge effects

## Acceptance criteria

- At least 20 TSA 23 IDF plots with current measurement within ±2 years of lidar.
- At least half above the current BA/volume range (`Lhmean` > 14.1882 m) or
  observed volume > 220 m3/ha.
- A tile-level spatial holdout independent of the existing 14 training plots.
- No transfer from TSA 22 (Okanagan); TSA 29 can remain an external comparison
  only.

## Why this is the blocker

The current map has BA/volume predictions on only **14.9%** of TSA 23.  The
four external high-biomass plots are outside the card range, and the archive
contains no additional TSA 23 high-biomass plots with LidarBC support.  More
refitting of the same rows cannot solve that; new co-located field/lidar data
can.

## Status

Requested, not yet acquired.  Do not represent the current surface as an
operational inventory in the meantime.
