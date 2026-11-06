# P142 close-out: opt-in near-surface ground labels

Phase: P142 Opt-in near-surface ground labels
Parent issue: #599
Branch: `feature/p142-near-surface-ground`
Pull request: the P142 PR
Date: 2026-11-06
Status: complete; opt-in only, default unchanged

## What changed

Added an opt-in final-surface consistency pass to the ground bundle.

- New helper: `femic.lidar.ground_classification.near_surface_mask`.
- New `GroundAdapterParameters` fields:
  - `include_near_surface` (default `False`);
  - `near_surface_tolerance_m` (default `0.15`).
- New CLI options:
  - `--include-near-surface/--strict-ground`;
  - `--near-surface-tolerance-m`.
- When enabled, points within tolerance of the final PTD surface are added to `is_ground`.
  `hag` and `is_low` are unchanged.
- Manifest parameters and QA fields record the option:
  - `strict_ground_count`;
  - `near_surface_added`;
  - `include_near_surface`;
  - `near_surface_tolerance_m`.

The default is still strict ground.

## Validation

Squamish public control:

| Mode | Ground recall | Canopy false ground |
| --- | ---: | ---: |
| Strict | 0.9742 | 0.00141 |
| Near-surface 0.15 m | **0.9903** | 0.00173 |

The canopy false-ground rate remains below the P140 guard threshold of 0.005.

Golden 2021:

| Mode | SOR | Class-2 recall | High-conf false ground |
| --- | --- | ---: | ---: |
| Strict | on | 0.9590 | 3.72% |
| Near-surface | on | **0.9950** | 4.08% |
| Strict | off | 0.9624 | 3.09% |
| Near-surface | off | **0.9995** | 3.31% |

TFL6 steep `T6_23339461`:

| Mode | Class-2 recall | High-conf false ground |
| --- | ---: | ---: |
| Strict, SOR off | 0.9343 | 0.54% |
| Near-surface, SOR off | **0.9990** | 0.63% |

End-to-end Golden bundle with `--no-sor --include-near-surface`:

- points: 113,775;
- strict ground: 82,240;
- final ground: 84,047;
- near-surface added: 1,807;
- SOR removed: 0;
- the bundle reader validated the manifest, QA, hashes, and extra dimensions.

## Semantics

This is **terrain-surface ground**, not mineral-ground-only. Near-surface mode can include
low vegetation close to the surface. The low-point flag is unchanged, so consumers can still
separate that band.

Do not change the default to near-surface mode without a semantic decision. The P141 audit
showed the recall gain, but `is_ground` and `is_low` now describe different things in this
mode.

## Verification

- Targeted tests: 40 passed across classifier, adapter, and public-control guard.
- `ruff check` passed on the changed classifier, adapter, and tests.
- `ruff format` clean for changed files.
- Sphinx build with warnings as errors.
- End-to-end Golden bundle and reader validation passed.

## Artifacts

- `notes/reports/p142-near-surface-ground.json`
- Guide: `docs/guides/lidar-ground-bundle.rst`
- Contract: `docs/reference/contracts/lidar-ground-bundle.rst`
- Raw Golden bundle under `runtime/p142/`, not tracked.
