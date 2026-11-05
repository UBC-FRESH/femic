# P138 close-out: PTD parameter sensitivity on the Squamish control zones

Phase: P138 PTD parameter sensitivity on the Squamish control zones
Parent issue: #591
Branch: `feature/p138-ptd-sensitivity`
Pull request: the P138 PR
Date: 2026-11-05
Status: complete; analysis only, no default change

## Question

The P137 public control patch used the P135 operational PTD parameters: SOR on, 1 m
seed cells, 15 degree maximum angle, 0.5 m maximum distance, 8 iterations. Is that choice
robust, and would another setting materially improve the ground/canopy separation?

## Control zones

The analysis reuses the P137 labels:

- 5,461 open estuarine mudflat points labelled ground.
- 9,284 closed-canopy first-return points labelled non-ground.

The classifier runs on the surrounding P137 patches so the spatial context and TIN seeds
remain intact. Raw data stays under `runtime/p137/` and is not tracked.

## Grid

- SOR: on / off
- Cell size: 0.5 / 1.0 / 2.0 m
- Maximum angle: 10 / 15 / 30 degrees
- Maximum distance: 0.3 / 0.5 / 1.0 m
- Maximum iterations: 8

That is 54 settings. The full grid is in `notes/reports/p138-ptd-sensitivity.csv` and the
machine-readable summary is `notes/reports/p138-ptd-sensitivity.json`.

## Main result

| Setting | Ground recall | Canopy false ground | Balanced accuracy |
| --- | ---: | ---: | ---: |
| P135 default (SOR, 1 m, 15 deg, 0.5 m) | 0.9742 | 0.00141 | 0.9864 |
| Best balanced (SOR, 2 m, 30 deg, 0.3 m) | 0.9998 | 0.00011 | 0.9999 |

The best setting raises ground recall by about 2.6 percentage points and lowers the
canopy false-ground rate by an order of magnitude **on this patch**. It is not a general
recommendation: the patch is small, coastal, and open-ground/canopy-only.

## Top settings

| SOR | Cell m | Angle deg | Distance m | Ground recall | Canopy false ground | Balanced |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| on | 2.0 | 30 | 0.3 | 0.99982 | 0.00011 | 0.99985 |
| off | 2.0 | 30 | 0.3 | 0.99945 | 0.00000 | 0.99973 |
| on | 2.0 | 30 | 0.5 | 0.99908 | 0.00043 | 0.99933 |
| off | 2.0 | 30 | 0.5 | 0.99890 | 0.00054 | 0.99918 |
| on | 2.0 | 30 | 1.0 | 1.00000 | 0.00184 | 0.99908 |
| off | 2.0 | 30 | 1.0 | 1.00000 | 0.00194 | 0.99903 |
| off | 1.0 | 30 | 0.3 | 0.99707 | 0.00022 | 0.99843 |
| off | 1.0 | 30 | 1.0 | 0.99835 | 0.00162 | 0.99837 |
| off | 1.0 | 30 | 0.5 | 0.99725 | 0.00054 | 0.99836 |
| on | 1.0 | 30 | 0.3 | 0.99744 | 0.00152 | 0.99796 |

## Parameter sensitivity

Mean metrics over the 54 settings:

- **Angle is the dominant parameter.** Mean ground recall is 0.911 at 10 degrees, 0.973 at
  15 degrees, and 0.999 at 30 degrees. The canopy false-ground rate stays below 0.6% on
  average, so the higher angle mostly recovers missed ground.
- **Cell size matters less.** Mean ground recall is 0.958 at 0.5 m, 0.960 at 1.0 m, and
  0.964 at 2.0 m; mean canopy false ground is 1.11%, 0.12%, and 0.03% respectively.
- **Distance is a weak lever here.** Mean ground recall is 0.960–0.962 across 0.3–1.0 m;
  canopy false ground rises from 0.32% to 0.57% as distance increases.
- **SOR is mixed.** Averaged over all settings, SOR on is slightly worse than SOR off
  (balanced 0.9773 vs 0.9795). SOR removes 491 of the 9,284 canopy labels and some ground
  labels; it helps some high-angle settings and hurts others. It is not a free win.

## Interpretation

The P135 defaults are conservative and perform well: 97.4% ground recall with 0.14%
canopy false ground. The data do not justify changing the defaults from one small coastal
patch. The strongest candidate for a future TFL6/steep-terrain test is:

- SOR on
- cell size 2.0 m
- maximum angle 30 degrees
- maximum distance 0.3 m

That setting should be tested on the TFL6 blocks and a steep Golden-area tile before it is
considered for an operational default. A 30 degree angle is permissive; on steep terrain
it may pull low vegetation into the ground surface.

## Limits

- One small coastal control patch; not a general tuning set.
- Open mudflat ground plus canopy first returns; no ground under closed canopy.
- 2019 LiDAR and 2024 orthophoto differ by five years.
- No field labels and no TFL6-specific labels.
- No default parameter change, tag, release, or product change in this phase.

## Verification

- 54 settings completed over the P137 ground and canopy patches.
- Full grid: `notes/reports/p138-ptd-sensitivity.csv`.
- Summary: `notes/reports/p138-ptd-sensitivity.json`.
- Raw patches and labels stay under `runtime/p137/`.
