# Squamish ground-control fixtures

Compact regression fixtures derived from the P137/P138 public control patch.

## Source

- Orthophoto: District of Squamish **Aerial Photo 2024**, 7.5 cm composite,
  **Open Government Licence - Squamish**.
  - https://www.arcgis.com/home/item.html?id=e86a2b42f49046918c0c0c1d13f000a2
- Point cloud: LidarBC **2019**, 8 points/m², tile
  `bc_092g065_3_3_3_xyes_8_utm10_2019.laz`, **Open Government Licence - British Columbia**.
  - https://nrs.objectstore.gov.bc.ca/gdwuts/092/092g/2019/pointcloud/bc_092g065_3_3_3_xyes_8_utm10_2019.laz

Raw orthophoto and LAZ bytes stay under `runtime/p137/` and are not tracked.

## Files

- `squamish_ground_patch.npz` — 30,932 points from the open-mudflat subpatch;
  5,461 labelled ground, the rest unlabelled context.
- `squamish_canopy_patch.npz` — 113,389 points from the closed-canopy subpatch;
  9,284 labelled canopy first returns, the rest unlabelled context.

Each NPZ contains `x`, `y`, `z` (EPSG:3157), `label` (`1` ground, `0` non-ground,
`-1` context), `source`, and `licence`.

## Labels

- Ground: points inside the open-mudflat pixel box on the 2024 orthophoto.
- Non-ground: first returns of multiple-return pulses inside the closed-canopy pixel box.

The labels are photointerpreted and return-type based, not field labels. They do not
validate ground under a closed canopy.

## Thresholds

The test asserts:

- ground recall >= 0.95 (current 0.9742);
- canopy false-ground <= 0.005 (current 0.0014).

These guard against regressions in the canonical P135 settings; they are not a general
accuracy claim.
