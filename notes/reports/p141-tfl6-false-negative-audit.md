# P141 close-out: TFL6 steep-block false-negative audit

Phase: P141 TFL6 steep-block false-negative audit
Parent issue: #597
Branch: `feature/p141-tfl6-false-negatives`
Pull request: the P141 PR
Date: 2026-11-06
Status: complete; audit only, no default change

## Question

P139 reported class-2 recall 0.8171 on TFL6 `T6_23339461`, yet class-2 HAG p99 was only
0.065 m. Why are class-2 points missed if the final surface passes through them?

## Finding 1: half the false negatives are SOR-removed

The P139 recall used all 77,461 class-2 points as the denominator. But SOR removed 7,516 of
them (9.7% of class 2), while removing 4.2% of non-class-2 points. A point removed before
PTD cannot be predicted ground.

| Quantity | Count |
| --- | ---: |
| Class-2 points | 77,461 |
| SOR-removed class-2 | 7,516 |
| Class-2 kept | 69,945 |
| Class-2 true positives | 63,290 |
| Class-2 false negatives, all points | 14,171 |
| Class-2 false negatives, kept points | 6,655 |
| Recall, all class-2 | 0.8171 |
| Recall, kept class-2 | **0.9049** |

SOR is preferentially removing ground returns on this steep block. That is a real issue
separate from the PTD angle/distance test.

## Finding 2: kept false negatives lie on the final surface

Of the 6,655 kept false negatives:

- 99.4% have HAG <= 0.15 m;
- 99.95% have HAG <= 0.5 m;
- 99.99% are last returns (ground returns);
- 99.4% are low-point flagged;
- none are high-confidence non-ground (HAG > 2 m).

`is_ground` and HAG are therefore inconsistent: the final PTD surface passes through these
points, but the label mask does not include them. The gap is not primarily a surface error;
it is a conservative final-mask decision plus SOR removal.

Edge distance does not explain the gap: 20.1% of kept false negatives are within 10 m of the
block edge, versus 21.0% of true positives.

## Finding 3: SOR-off plus a final-surface pass is promising

Diagnostic runs on the same block:

| Setting | Ground count | Class-2 recall | High-conf false ground | Class-2 HAG p99 |
| --- | ---: | ---: | ---: | ---: |
| P135 default, SOR on | 489,745 | 0.8171 all / 0.9049 kept | 1.54% | 0.065 m |
| SOR off | 451,424 | 0.9343 | 0.54% | 0.082 m |
| SOR off + final low-HAG pass | 485,532 | **0.9990** | 0.63% | 0.082 m |

The final pass is a **diagnostic definition**, not implemented code:
`is_ground OR (kept AND HAG <= 0.15 m)`.

Golden 2021 shows the same direction:

| Setting | Class-2 recall | High-conf false ground | Class-2 HAG p99 |
| --- | ---: | ---: | ---: |
| P135 default, SOR on | 0.9590 | 3.72% | 0.044 m |
| SOR off | 0.9624 | 3.09% | 0.050 m |
| SOR off + final pass | **0.9995** | 3.31% | 0.050 m |

The final pass adds low-HAG points, including low vegetation; it is not semantically free.
The low-point mask already flags those points. A future design needs to decide whether the
ground label should mean “terrain surface” or “mineral ground only”.

## Recommendation

**No default change in P141.** Keep the P135 defaults.

Open a follow-up phase to:

1. make SOR optional for ground classification and report both modes;
2. add an **opt-in** final-surface consistency pass (or a separate `is_near_surface` flag
   rather than changing `is_ground`);
3. validate on the Squamish CI guard, Golden, and TFL6;
4. decide whether the ground label is terrain-surface or mineral-ground semantics.

This is more promising than the P138 angle/cell candidate, which was rejected in P139. The
remaining TFL6 recall gap is mostly SOR removal and a conservative final mask, not a bad
TIN surface.

## Limits

- Class-2 reference is incomplete, especially on TFL6.
- The all-point denominator includes SOR-removed points; P139 recall should be read with
  the kept denominator when discussing the classifier.
- The final-surface pass is simulated, not implemented.
- The 0.15 m pass threshold is a diagnostic, not a validated default.
- No manual labels for TFL6.
- No default parameter, product, tag, or release change.
