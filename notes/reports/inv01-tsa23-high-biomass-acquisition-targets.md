# INV-01 TSA 23 high-biomass acquisition targets

## Result

The complete PSP archive does not contain enough TSA 23 high-biomass plots with
LidarBC support to extend the current cards.  The point-cloud audit found:

- 162 TSA 23 IDF sites
- 24 latest visits since 2014
- 23 of those have a LidarBC point-cloud tile
- 5 have observed volume >= 200 m3/ha with a point-cloud tile
- 1 high-biomass recent plot has no point cloud: `4033798` (2022, 238.8 m3/ha)

The five high-biomass plots with point clouds are:

| Site | Measured | Height m | BA m2/ha | Volume m3/ha | Role |
| --- | ---: | ---: | ---: | ---: | --- |
| 4025091 | 2018 | 19.54 | 44.61 | 305.07 | external holdout |
| 4025090 | 2018 | 23.68 | 34.33 | 302.78 | external holdout |
| 4025094 | 2018 | 20.90 | 36.23 | 273.80 | external holdout |
| 4024520 | 2018 | 22.73 | 27.14 | 217.89 | training |
| 4024958 | 2019 | 17.21 | 36.07 | 214.54 | training |

There are also older TSA 23 IDF plots with high reconstructed volume but no
current point cloud.  They are **not** usable for this fit until they are
remeasured and co-located with a lidar acquisition:

- 4024439 (2003, 365.2 m3/ha)
- 4024440 (2003, 305.8)
- 4024445 (2003, 406.2)
- 4024627 (2002, 305.5)
- 4024694 (2012, 441.1)
- 4024695 (2012, 299.2)
- 4025001 (1999, 362.5)
- 4025098 (1997, 344.7)
- 4025376 (1994, 256.5)
- 4025377 (1994, 250.4)

## Acquisition target

The nearest actionable target is `4033798` (IDF mw, 2022):
19.17 m Lorey height, 33.12 m2/ha BA, 238.80 m3/ha volume.  It has no selected
LidarBC point-cloud tile.

The older plots above define a field-acquisition shortlist, not a calibration
set.  They need current measurement and lidar; using their 1990s/2000s volumes
against 2019/2024 lidar would be a temporal transfer error.

## Decision

- Do not keep refitting the current 18 TSA 23 plots; that is exhausted.
- Do not use TSA 22 (Okanagan) as TSA 23 training.
- Keep TSA 29 as an exploratory transfer test only.
- Acquire/measure high-biomass **TSA 23** plots, prioritizing `4033798` and the
  historical high-biomass sites above.
- Keep the current map explicitly low/mid-biomass until that data exists.

## Files

- `notes/reports/inv01-tsa23-high-biomass-acquisition-targets.csv`
- `notes/reports/inv01-tsa23-high-biomass-targets.md`
- `notes/reports/inv01-tsa23-high-biomass-refit.md`
