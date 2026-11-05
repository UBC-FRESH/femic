# P137 close-out: Squamish orthophoto control patch

Phase: P137 Squamish orthophoto control patch
Parent issue: #589
Branch: `feature/p137-squamish-control-patch`
Pull request: the P137 PR
Date: 2026-11-05
Status: complete; public-data validation, no field data

## Why this patch

TFL6 has a 2012 0.5 m provincial orthophoto, but it is **Access Only** in the BC Data
Catalogue and sold per BCGS tile. The free thumbnail is 1/16 scale (about 8 m pixels), too
coarse for point-level ground labels. That path needs funding or a data request.

The District of Squamish publishes its orthophoto under the Open Government Licence -
Squamish, and LidarBC publishes the matching point cloud under OGL-BC. This gives a
zero-cost control patch with public provenance.

## Sources

- Orthophoto: District of Squamish, **Aerial Photo 2024**, 7.5 cm composite, OGL-Squamish.
  - Item: https://www.arcgis.com/home/item.html?id=e86a2b42f49046918c0c0c1d13f000a2
  - Image service: https://portal.squamish.ca/server/rest/services/Orthophoto_2024/ImageServer
- Point cloud: LidarBC, **2019**, 8 points/m2, OGL-BC.
  - Tile: `bc_092g065_3_3_3_xyes_8_utm10_2019.laz`
  - Object-store URL:
    https://nrs.objectstore.gov.bc.ca/gdwuts/092/092g/2019/pointcloud/bc_092g065_3_3_3_xyes_8_utm10_2019.laz
  - Classes present: 1, 2, 7.

Raw bytes remain under `runtime/p137/` and are not tracked. The tracked report records the
source URLs, checksums, patch boxes, parameters, and metrics.

## Patch design

The patch uses two independent, clearly visible zones in the same 2019 LidarBC tile:

1. **Ground zone**: open estuarine mudflat with no canopy above it. The 2024 orthophoto
   shows the mineral surface; 2019 LiDAR returns are terrain.
2. **Non-ground zone**: closed forest canopy. Only **first returns of multiple returns**
   are labelled non-ground. A first return in a multi-return pulse is a canopy hit, not a
   ground hit, independent of the classifier.

The ground zone is a 100 m UTM box at `x=486430..486530`, `y=5504560..5504660`
(EPSG:3157). The canopy zone is a 100 m UTM box at `x=486300..486400`,
`y=5504520..5504620`.

The orthophoto crops were exported from the 2024 image service:

- Ground crop, EPSG:3857:
  `-13713244.901985273,6393348.354335499,-13713089.7305535,6393503.525767272`
- Canopy crop, EPSG:3857:
  `-13713444.795561131,6393285.934704034,-13713290.835651558,6393441.108679998`

Within the 1333 x 1333 ground crop, the ground labels use pixel box
`(933, 1133)..(1133, 1266)`. Within the canopy crop, the canopy labels use pixel box
`(200, 300)..(450, 600)`.

## Classifier

The canonical FEMIC classifier ran with the P135 TFL6 parameters:

- SOR: `k=10`, `multiplier=2.0`
- PTD: `cell_size_m=1.0`, `max_angle_deg=15.0`, `max_distance_m=0.5`,
  `max_iterations=8`
- Low-point cut: `0.15 m`

The point cloud was cropped to each 100 m box before classification. No orthophoto
information was used by the classifier.

## Result

| Label | Points | Predicted ground | Class-2 fraction | HAG p50 / p95 |
| --- | ---: | ---: | ---: | --- |
| Ground (open mudflat) | 5,461 | 5,391 (98.72%) | 13.24% | 0.000 / 0.087 m |
| Non-ground (canopy first returns) | 9,284 | 16 (0.17%) | 0.00% | 17.981 / 27.747 m |

Confusion matrix:

|  | Predicted ground | Predicted non-ground |
| --- | ---: | ---: |
| Ground | 5,391 | 70 |
| Non-ground | 16 | 9,268 |

- Precision: **0.9970**
- Recall: **0.9872**
- False-positive ground: **16 / 9,284 = 0.17%**
- False-negative ground: **70 / 5,461 = 1.28%**

The 16 false-positive ground points are canopy first returns. They are a small residual
compared with the 9,284 canopy labels; the classifier is not systematically calling canopy
ground at this site.

## Limits

- This is **not** TFL6-specific and not a forest-floor accuracy estimate. The orthophoto
  cannot see ground under a closed canopy, so ground-under-canopy remains unvalidated.
- The ground zone is open estuarine mudflat, not a harvested or upland forest floor.
- The 2019 LiDAR and 2024 orthophoto are five years apart. The selected mudflat and mature
  canopy zones are visually stable, but this is not a same-day acquisition.
- LidarBC class 2 is incomplete in the ground zone (13.24%), so class-2 recall alone would
  understate the classifier. The labels here are orthophoto/return-type labels, not field
  labels.
- No field data, paid TFL6 tile, tag, release, or default product change was used.

## Verification

- Ground crop and canopy crop exported successfully from the public image service.
- 2019 LAZ tile downloaded from the LidarBC object store.
- Labels generated from the two zones and saved to
  `runtime/p137/squamish_manual_control_labels.csv`.
- PTD run used the canonical FEMIC implementation and P135 parameters.
- Raw data checksums are recorded in `runtime/p137/checksums.txt`; the raw files are not
  tracked.

## Next

- A TFL6-specific control patch still needs either the paid 2012 0.5 m tile or a GeoBC
  research/data request.
- A true forest-floor control patch needs a source that can see under canopy, such as
  stereo imagery, a manually interpreted side view, or field labels.
