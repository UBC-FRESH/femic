# P118.9 FEMIC-native terrain and stream audit

Date: 2026-10-26
Status: audit complete; Chapman remains data-blocked
Parent issue: #383

## What was used

This audit used the established FEMIC stack, not a new terrain pipeline:

- `femic.lidar.terrain.inspect_terrain_raster`
- `femic.lidar.terrain.read_terrain_grid`
- `femic.lidar.terrain.build_terrain_products` / `derive_slope_percent` (Horn 3x3)
- `femic.lidar.hydrography.derive_stream_candidates` (D8, optional depression fill)
- `femic.lidar.hydrography.derive_d8_flow_direction`
- `femic.lidar.hydrography.accumulate_d8_flow`
- the terrain and stream-candidate QA/manifest contracts.

The existing tests pass: `pytest tests/test_lidar_terrain.py
tests/test_lidar_hydrography.py` -> 31 passed.

## CDED versus LidarBC

FEMIC's BCDC resolver maps the generic `DEM` / `digital elevation model` query
to **Digital Elevation Model for British Columbia - CDED - 1:250,000**
(`src/femic/bcdc_catalog.py`). That is a small-scale provincial DEM, not a 1 m
channel/road-crossing surface. It could be a coverage fallback, but it is not a
substitute for LidarBC 1 m for this pilot.

LidarBC 1 m is the correct source for terrain/stream screening. The problem is
the mixed vertical metadata and coverage, not the choice of LidarBC.

## Mixed-mosaic terrain

A bounded 3,000 x 3,000 pixel AOI from the mixed mosaic was processed with
`build_terrain_products`:

- valid slope pixels: 5,062,894
- slope min/mean/max: 0.0 / 39.08 / **45,466.8%**

The extreme slope is a seam/vertical artefact signal, not real terrain. The
full mixed mosaic terrain attempt exceeded a 10-minute local timeout; the AOI
was used to bound the audit.

## CGVD2013-only terrain

The 81 compound tiles were rebuilt into a CGVD2013-only mosaic:

- valid area: 1,620.6 ha
- vertical status: resolved (CGVD2013, EPSG:6647)
- slope valid pixels: 16,172,577
- slope min/mean/max: 0.0 / 31.31 / 838.8%

This is much more stable than the mixed mosaic, but the 838.8% maximum still
needs review. The 1,620.6 ha subset is only part of the 6,917.1 ha watershed.

## Stream candidates

`derive_stream_candidates` on the CGVD2013-only mosaic, threshold 500, no
depression fill:

- valid cells: 16,206,182
- candidate cells: 211,734
- candidate area: 21.17 ha
- accumulation max/mean: 136,251 / 3,612

FWA streams were reprojected explicitly from EPSG:3005 to EPSG:3157 for
comparison. The overlap was poor:

- reference cells: 40,277
- true positive: 117
- false positive: 211,617
- false negative: 40,160
- precision 0.00055, recall 0.0029, F1 0.00093, Jaccard 0.00046
- overlap area: 0.0117 ha

This is not evidence that the FEMIC functions are wrong. It is evidence that the
current DEM/mosaic/reference alignment is not usable for a hydrologic stream
product. Candidate threshold, DEM artefacts, mixed/vertical issues, and FWA
positional/generalisation differences all need review.

## Decision

The FEMIC-native terrain/hydrography stack is the right implementation surface.
The limiting factor is the Chapman data: mixed vertical metadata, a 1,931.2 ha
valid-coverage gap, and poor stream alignment. Do not build a flood response
surface from this DEM.

Any future Chapman rebuild should call these functions directly; do not add a
parallel ad hoc terrain pipeline.
