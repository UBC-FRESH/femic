# TSA 23 high-biomass acquisition bundle

Sender-ready package for requesting current PSP remeasurement and co-located
LidarBC point clouds for high-biomass TSA 23 IDF plots.

Start with `request.md`.  `targets.csv` and `targets.geojson` are the site list;
`targets_map.png` is a quick overview.  `request.json` carries the same request
for automated handoff.

Priority 1 is `4033798` (2022, 238.8 m3/ha, no selected LidarBC tile).  Priority
2 is the ten historical high-biomass sites that need remeasurement plus lidar.

All source data and outputs remain under the approved data root:

```text
/srv/shared-data/gep/ws4/tmp/inv01-data
```

No project data is stored under `/tmp`.
