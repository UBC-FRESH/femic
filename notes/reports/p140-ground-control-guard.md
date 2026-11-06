# P140 close-out: ground-classifier public-control guard

Phase: P140 Ground-classifier public-control guard
Parent issue: #595
Branch: `feature/p140-ground-control-guard`
Pull request: the P140 PR
Date: 2026-11-06
Status: complete

## Purpose

P137-P139 produced a useful public control patch but left the evidence in untracked runtime
files. This phase turns the control into compact fixtures and a CI guard so a future
classifier change cannot silently lose open-ground recall or start calling canopy first
returns ground.

## Fixtures

Tracked under `tests/fixtures/lidar/ground_control/`:

| Fixture | Points | Labels | Size |
| --- | ---: | ---: | ---: |
| `squamish_ground_patch.npz` | 30,932 | 5,461 ground | 172 KB |
| `squamish_canopy_patch.npz` | 113,389 | 9,284 non-ground | 772 KB |

Each NPZ stores `x`, `y`, `z` in EPSG:3157, `label` (`1` ground, `0` non-ground,
`-1` context), plus source and licence strings. `README.md` and `metadata.json` record the
provenance, checksums, thresholds, and limits.

## Guard

The test runs the canonical P135 settings:

- SOR `k=10`, `multiplier=2.0`;
- PTD cell 1.0 m, angle 15 degrees, distance 0.5 m, 8 iterations.

Assertions:

- ground recall >= 0.95 (current 0.9742);
- canopy false-ground <= 0.005 (current 0.0014).

The test is `tests/test_lidar_ground_control_fixture.py`. A lightweight workflow,
`.github/workflows/ground-classifier-guard.yml`, runs only this test on pull requests and
`main`.

## Result

- Ground fixture: 5,461 labelled points, 97.42% predicted ground.
- Canopy fixture: 9,234 retained labelled points, 0.14% predicted ground.
- Local run: 2 passed in 4.47 s.

## Limits

- Photointerpreted and return-type labels, not field labels.
- Open mudflat ground plus canopy first returns; no ground under closed canopy.
- 2019 LiDAR and 2024 orthophoto are five years apart.
- The guard protects the current public-control behaviour; it is not a general accuracy
  claim.

## Artifacts

- `tests/fixtures/lidar/ground_control/README.md`
- `tests/fixtures/lidar/ground_control/metadata.json`
- `tests/fixtures/lidar/ground_control/squamish_ground_patch.npz`
- `tests/fixtures/lidar/ground_control/squamish_canopy_patch.npz`
- `tests/test_lidar_ground_control_fixture.py`
- `.github/workflows/ground-classifier-guard.yml`

Raw orthophoto and LAZ bytes remain under `runtime/p137/` and are not tracked.
