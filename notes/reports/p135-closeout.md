# P135 close-out: TFL6 ground-bundle end-to-end

Phase: P135 TFL6 Ground-Bundle End-to-End
Parent issue: #581
Pull request: the P135 PR, `feature/p135-tfl6-ground-e2e` into `main`
Evidence head: the P135.1 commit
Report commit: the commit that adds this report
Date: 2026-11-04
Status: complete; workstation validation

## Summary

The full lane ran on a real TFL6 LidarBC tile and the seven FHOPS blocks:

1. materialize the 1.53 GB tile once;
2. reproject the blocks to the tile CRS;
3. crop to the block AOI with a 50 m margin;
4. run the `fresh-urban-forest-lab` ground adapter;
5. run the FEMIC seven-block summary.

## Evidence

- Input: 246,658,211 points, 1.5 GB, EPSG:3156 + CGVD2013.
- Crop: 137,428,675 points, 815 MB.
- Bundle: 36,662,162 predicted ground, 27,880,539 low-point flags, 6,025,777 SOR removals,
  HAG p95 21.4207 m, 1,821.9 s, no warnings.
- Summary: seven rows, one per block.
- Report: `notes/reports/p135-tfl6-ground-e2e.md`.
- Evidence: `notes/reports/p135-tfl6-ground-e2e.json`.

## Limits

- No field or manual ground labels; the ground fractions are not accuracy estimates.
- Workstation-only; the tile and bundle are not tracked.
- Per-block ground fraction is point composition, not ground-area fraction.
- No default FEMIC product changed.

## Verification

- Targeted tests: `tests/test_lidar_crop.py`, `tests/test_lidar_ground_bundle.py`,
  `tests/test_lidar_ground_summary.py`.
- `sphinx-build -b html docs _build/html -W`.
- The large run is local and not a CI network job.

## Next

- A manual ground-label patch remains the evidence gap.
- Alternatively, feed the seven-block summary into WS4/FHOPS as an optional support layer.
