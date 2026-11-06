# P139 close-out: candidate PTD settings on TFL6 and Golden terrain

Phase: P139 Candidate PTD settings on TFL6 and Golden terrain
Parent issue: #593
Branch: `feature/p139-candidate-settings`
Pull request: the P139 PR
Date: 2026-11-06
Status: complete; candidate rejected as a default change

> **P141 update:** the TFL6 class-2 recall below uses all class-2 points as the denominator.
> SOR removes 7,516 of 77,461 class-2 points on `T6_23339461`; the kept-point recall is
> 0.9049, not 0.8171. See `p141-tfl6-false-negative-audit.md`.

## Question

P138 found a strong Squamish setting: SOR on, 2 m cells, 30 degree maximum angle, 0.3 m
maximum distance. Does that setting hold on the real TFL6 crop and the steep Golden-area
tile, or is it a small-patch overfit?

## Inputs

- TFL6 `T6_23339461`: steep cable block, 4.81M points, 77,461 class-2 points.
- TFL6 `T6_23339462`: mostly open block, 11.16M points, 524,332 class-2 points.
- Golden 2021: `bc_082n025_4_2_1_xyes_8_utm11_2021.laz`, 113,775 points, 15,353 class-2
  points.

The TFL6 blocks were cropped from `runtime/p135/tfl6_blocks_crop.laz` with a 10 m margin.
Raw LAZ data stays under `runtime/` and is not tracked.

Reference method is the P14 class-2 nearest-surface reference:

- positive ground: `classification == 2`;
- reference surface: nearest published class-2 point in XY;
- high-confidence non-ground: non-class-2 points with reference HAG > 2 m;
- ambiguous 0–2 m band excluded.

This is reproducible but not a manual label set.

## Settings

| Name | SOR | Cell m | Angle deg | Distance m |
| --- | --- | ---: | ---: | ---: |
| P135 default | on | 1.0 | 15 | 0.5 |
| P138 candidate | on | 2.0 | 30 | 0.3 |

Both use 8 iterations and a 10-neighbour, 2.0-multiplier SOR.

## Results

| Case | Setting | Ground | Ground fraction | Class-2 recall | High-conf false ground | HAG p95 | Class-2 HAG p99 | Runtime |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| T6_23339461 | default | 489,745 | 10.64% | 0.8171 | 1.54% | 28.16 m | 0.065 m | 268 s |
| T6_23339461 | candidate | 479,842 | 10.43% | 0.8477 | 0.29% | 30.44 m | 0.069 m | 198 s |
| T6_23339462 | default | 4,015,938 | 37.58% | 0.9636 | 0.42% | 19.11 m | 0.115 m | 603 s |
| T6_23339462 | candidate | 4,281,047 | 40.06% | 0.9794 | 0.03% | 19.48 m | 0.105 m | 562 s |
| Golden 2021 | default | 82,530 | 76.12% | 0.9590 | 3.72% | — | 0.044 m | 4.4 s |
| Golden 2021 | candidate | 82,387 | 75.99% | 0.9564 | 1.80% | — | 0.340 m | 4.3 s |

TFL6 default/candidate agreement:

- `T6_23339461`: Jaccard 0.682; 182,977 points changed.
- `T6_23339462`: Jaccard 0.890; 481,739 points changed.
- Golden 2021: Jaccard 0.895; 9,165 points changed.

## Golden ablations

Two extra Golden-only runs isolate the two changed parameters:

| Setting | Cell m | Angle deg | Class-2 recall | High-conf false ground | Class-2 HAG p99 |
| --- | ---: | ---: | ---: | ---: | ---: |
| cell 2.0, angle 15 | 2.0 | 15 | 0.9479 | 1.26% | 0.260 m |
| cell 1.0, angle 30 | 1.0 | 30 | 0.9867 | 6.61% | 0.0475 m |

The 2 m cell is the main cause of the class-2 HAG degradation. The 30 degree angle raises
recall but also raises high-confidence false ground when the cell is 1 m.

## Decision

**Reject the P138 candidate as a default change. Keep the P135 defaults.**

The candidate does reduce high-confidence false ground on TFL6 and Golden, and it is
faster on the TFL6 blocks. But:

- Golden class-2 HAG p99 degrades from 0.044 m to 0.340 m (about 8x worse);
- the candidate changes 10–32% of TFL6 ground points, so the result is not a small
  refinement;
- TFL6 class-2 recall remains low (0.82 on the steep block) even after the candidate;
- one Golden tile and two TFL6 blocks are not enough to justify a default change.

If tuning continues, the next candidates should keep the 1 m cell and test intermediate
angles (20–25 degrees), or use a 1.0–1.5 m cell with the current 15 degree angle. Any such
change needs more tiles and manual labels.

## Limits

- Class-2 reference is incomplete, especially on TFL6; recall is not an accuracy estimate.
- The high-confidence false-ground set excludes the ambiguous 0–2 m band.
- No manual labels; P137 only covers open mudflat and canopy first returns.
- One Golden tile and two TFL6 blocks.
- Runtime is workstation-only; no CI claim.
- No default parameter, product, tag, or release change.

## Artifacts

- `notes/reports/p139-candidate-settings.csv`
- `notes/reports/p139-candidate-settings.json`
- Raw block crops and results under `runtime/p139/`, not tracked.
