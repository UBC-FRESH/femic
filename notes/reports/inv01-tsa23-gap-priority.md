# INV-01 TSA 23 omitted-tile gap priority

## Headline

Of 6,806 LidarBC point-cloud tiles that intersect TSA 23, 5,899 were processed
and 907 were omitted from the full-run manifest.  The 907 omitted tiles are not
random edge slivers:

- 2,139.5 km2 of tile footprint
- 1,962.0 km2 inside the TSA boundary (15.9% of TSA 23)
- 1,778.0 km2 of VRI forest
- 861.2 km2 of VRI THLB
- 182 high-priority (A) tiles containing 49,249.6 ha of VRI forest and
  30,333.1 ha of THLB

This is a material coverage gap, but it is not the only one: 2,466.5 km2
(20.0%) of TSA 23 has no public point-cloud tile at all in the current LidarBC
selection.

## Why the 907 were omitted

The full-run manifest paired point clouds with the fine (1:2500 / 2.5 km) layer
5 DEM.  All 907 omitted tiles have at least one DEM candidate, but none has the
same fine 2.5 km 1 m DEM tile.  Their candidates are older or larger:

- 64 unique layer 6 DEM tiles (`1:20000`, 1 m, roughly 14 km)
- 19 unique layer 5 DEM tiles, mostly adjacent
- 907 tiles have a DEM candidate; 0 have the same fine maptile

So “907 no-DEM tiles” should be read as **907 tiles without the fine 1 m DEM
used by the run**, not as tiles with no elevation data whatsoever.  A 2019
layer 6 DEM exists for many of them.  Using it would be a methodological change,
not a rerun of the original pairing.

## Coverage arithmetic

| Item | Area |
| --- | ---: |
| TSA 23 | 12,353.2 km2 |
| Processed tile footprint inside TSA | 7,949.0 km2 (64.3%) |
| All selected point-cloud tiles inside TSA | 9,886.7 km2 (80.0%) |
| No public point cloud in selection | 2,466.5 km2 (20.0%) |
| No processed point cloud | 4,404.2 km2 (35.7%) |
| Omitted 907 tiles inside TSA | 1,962.0 km2 (15.9%) |

Filling every omitted tile would raise the tile-footprint ceiling from 64.3% to
80.0%, but would still leave the 2,466.5 km2 no-point-cloud gap.  Cell-area
coverage would rise less than the footprint figure because the existing 25 m
model has empty cells inside tile footprints and because the model-card ranges
restrict BA/volume.

## Priority method

Each omitted tile is represented by its EPSG:3005 point-cloud footprint.  For
each tile:

- `forest_vri_ha` — area of intersection with VRI forest polygons;
- `thlb_vri_ha` — the same intersection restricted to `thlb = 1`;
- `road_distance_km` — straight-line distance from the tile centroid to the
  nearest vertex in the TSA 23 c5 network;
- `mill_*_km` — straight-line distance to each of the three TSA 23 mill
  destinations;
- `priority_score` — a heuristic, not an economic ranking:

```text
score = forest_ha
        * (1 - 0.5 * min(road_distance_km / 20, 1))
        * (1 - 0.25 * min(nearest_mill_km / 150, 1))
```

Tiers are rank-based: A = top 20% (182), B = next 30% (272), C = remaining 50%
(453).  The score does not include haul cost, road build cost, tenure, operability,
or stand age; it only answers “where is the largest accessible forest gap?”

## Top ten omitted tiles

| Rank | Tile | Year | Forest ha | THLB ha | Road km | Nearest mill | Score |
| ---: | --- | ---: | ---: | ---: | ---: | --- | ---: |
| 1 | `lidarbc:4:119519` | 2019 | 266.4 | 257.2 | 0.11 | MILL_694_LGH | 262.1 |
| 2 | `lidarbc:4:119742` | 2019 | 269.4 | 213.4 | 0.01 | MILL_694_LGH | 261.7 |
| 3 | `lidarbc:4:119717` | 2019 | 270.4 | 77.3 | 0.20 | MILL_694_LGH | 260.9 |
| 4 | `lidarbc:4:119695` | 2019 | 268.8 | 31.5 | 0.26 | MILL_694_LGH | 259.5 |
| 5 | `lidarbc:4:119740` | 2019 | 263.2 | 250.4 | 0.26 | MILL_694_LGH | 255.5 |
| 6 | `lidarbc:4:120021` | 2021 | 277.0 | 277.0 | 0.14 | MILL_733_LGH | 255.1 |
| 7 | `lidarbc:4:120015` | 2021 | 273.4 | 272.9 | 0.08 | MILL_733_LGH | 253.9 |
| 8 | `lidarbc:4:120020` | 2021 | 274.1 | 258.8 | 0.13 | MILL_733_LGH | 252.2 |
| 9 | `lidarbc:4:119893` | 2020 | 275.3 | 231.6 | 0.21 | MILL_694_LGH | 251.1 |
| 10 | `lidarbc:4:120044` | 2021 | 274.1 | 139.7 | 0.29 | MILL_733_LGH | 250.8 |

The full 907-row ranking is in `inv01-tsa23-gap-priority.csv`; the same rows with
geometry are in `inv01-tsa23-gap-priority.gpkg`.

## By acquisition year and tier

| Group | Tiles | VRI forest ha | THLB ha |
| --- | ---: | ---: | ---: |
| 2017 | 14 | 3,465.1 | 1,416.5 |
| 2018 | 22 | 229.1 | 38.8 |
| 2019 | 605 | 111,720.0 | 41,514.8 |
| 2020 | 51 | 12,981.0 | 11,263.4 |
| 2021 | 215 | 49,402.2 | 31,887.3 |
| Priority A | 182 | 49,249.6 | 30,333.1 |
| Priority B | 272 | 68,878.3 | 34,731.0 |
| Priority C | 453 | 59,669.7 | 21,056.6 |

Nearest-mill split: 332 tiles are closest to `MILL_733_LGH`, 297 to
`MILL_694_LGH`, and 278 to `MILL_95_LBR`.

## Recommendation

A four-plot PSP holdout now exists.  It is mostly outside the current BA/volume
card range, so it is an extrapolation stress test rather than an in-domain
validation; volume overprediction is severe (RMSE 118.21 m3/ha).  Do not spend
the full download/compute budget on all 907 until the model domain is expanded
and refit.  This is not a reason to wait: use the full PSP archive to find
high-biomass IDF plots with LidarBC support and widen the cards now.

If a coverage expansion is required, the defensible next increment is:

1. Process priority A (182 tiles) first, using the 2019/2020/2021 point clouds and
   the appropriate layer 6 DEMs, after documenting the DEM change.
2. Keep the original 5,899-tile run unchanged as the reference.
3. Add A tiles as a separate experiment, not by silently merging them into the
   current 48%-coverage map.
4. Do not claim wall-to-wall TSA 23 coverage: 2,466.5 km2 still has no selected
   public point cloud and requires new acquisition.

Approximate raw volume for all 907 point clouds is 0.3 TB at the observed
~366 MB/tile average; the 64 unique layer 6 DEMs are much smaller.  That is
feasible, but the model-validity question comes first.

## Files

- `notes/reports/inv01-tsa23-gap-priority.csv` — 907 rows, no geometry.
- `notes/reports/inv01-tsa23-gap-priority.gpkg` — 907 EPSG:3005 polygons.
- `notes/reports/inv01-tsa23-gap-priority.json` — coverage and tier summary.
- `notes/reports/figures/inv01-tsa23-gap-priority.png` — map.
- `examples/inv01_tsa23_validation/gap_priority.py` — reproducible ranking.
