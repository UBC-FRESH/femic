# P118.8 Chapman domain defensibility decision

Date: 2026-10-26
Status: **blocked for hydrologic elevation and flood use**
Parent issue: #383

## Decision

The current public Chapman DEM mosaic is **not defensible as a hydrologic
elevation surface or flood-model input**.

It may support a limited terrain/slope review only after seam inspection,
because it is a horizontal 1 m EPSG:3157 mosaic clipped to the FWA watershed.
It must not be used to claim a flood response, design flood, or regulatory
result.

## Vertical coverage

The mosaic has 4,985.9 ha of valid pixels inside the 6,917.1 ha watershed.
Vertical metadata coverage is uneven:

| Class | Area (ha) | Share of valid |
| --- | ---: | ---: |
| CGVD2013 compound tiles | 1,621.6 | 32.5% |
| 2D-only tiles, vertical unknown | 3,347.5 | 67.1% |
| Valid outside both tile footprints | 16.7 | 0.3% |
| Unfilled watershed gap | 1,931.2 | — |

- 81 tiles are EPSG:6653 compound with CGVD2013 heights.
- 9 older 2019/2020 tiles are EPSG:3157 2D with no vertical metadata.
- The 2D-only footprint dominates the valid mosaic. The vertical datum cannot be
  inferred or silently assumed.

## Why this blocks the pilot

- A flood-response model needs consistent vertical elevation and channel
  geometry; mixed/unknown vertical metadata is not acceptable.
- The unfilled 1,931.2 ha gap is large enough to affect watershed response.
- No reviewed Chapman receptor geometry or capacity/damage assumption exists.
- No current public daily gauge series is confirmed; the historical WSC record
  ends in 2003.
- No culvert/road-crossing inventory, hydrologist review, or reviewed WS4
  crosswalk exists.

## Unblock requirements

1. Obtain LidarBC project metadata or a reviewed vertical-control check for the
   9 older 2D tiles, or replace them with a consistent CGVD2013 DEM.
2. Close or explicitly bound the 1,931.2 ha coverage gap.
3. Select and source a reviewed Chapman intake/WTP receptor geometry and
   capacity/damage assumption.
4. Obtain a current public or governed gauge series.
5. Assemble the culvert/road-crossing inventory.
6. Complete hydrologist review and the reviewed WS4 crosswalk.

Until then, the Chapman phase stays data-blocked. No flood model or claim was
produced.
