# INV-01 refit and applicability experiment

## Design

- Development rows: the 14 TSA 23 training plots plus regional high-biomass
  plots that have extracted features.  This yields **31 development plots** in
  TSAs 2, 5, 18, 23, and 29.
- Independent rows: **56 plots** in TSAs 2, 5, 9, 11, 18, 22, 23, and 29.
- Candidate forms were selected by leave-one-TSA-out CV on development rows.
  The independent rows were not used for selection.
- Predictions were also evaluated inside the development predictor ranges.
- No candidate is promoted automatically.

## Candidate results

### Basal area

| Candidate | Features | TSA CV RMSE | Independent all RMSE | In-domain n | In-domain RMSE |
| --- | --- | ---: | ---: | ---: | ---: |
| `ba_cc` | Lhmean, CC2m | 7.76 | 9.19 | 42 | 7.28 |
| `ba_hp95` | Lhmean, Lhp95 | 7.75 | 7.69 | 54 | 7.77 |
| `ba_full` | Lhmean, CC2m, Lhp95 | 8.57 | 8.99 | 41 | 7.06 |
| `ba_lh` | Lhmean | **7.29** | 8.05 | 55 | 8.10 |

CV selected `ba_lh`.  It does not beat the fixed hybrid on the independent set
(8.05 vs 7.93 all rows; 8.10 vs 8.02 in-domain).  `ba_hp95` has a better
independent result but a worse CV result; choosing it after seeing the
independent set would be test leakage.

### Volume

| Candidate | Features | TSA CV RMSE | Independent all RMSE | In-domain n | In-domain RMSE |
| --- | --- | ---: | ---: | ---: | ---: |
| `vol_cc` | Lhmean, CC2m | **59.48** | 71.75 | 42 | **52.06** |
| `vol_hp95` | Lhmean, Lhp95 | 61.23 | 53.61 | 54 | 54.48 |
| `vol_full` | Lhmean, CC2m, Lhp95 | 60.41 | 73.90 | 41 | 55.43 |
| `vol_poly2` | Lhmean, CC2m polynomial | 59.56 | 81.99 | 42 | 62.60 |
| `vol_poly2_hp95` | Lhmean, CC2m, Lhp95 | 59.80 | 82.14 | 41 | 63.57 |

CV selected `vol_cc`.  It improves the independent in-domain volume RMSE from
the fixed hybrid's **62.93** to **52.06**, and the all-row RMSE from 80.95 to
71.75.  This is a real improvement, but 52 m3/ha is still too large for an
operational volume product.

## Comparison

| Model | BA all | BA in-domain | Volume all | Volume in-domain |
| --- | ---: | ---: | ---: | ---: |
| Published TSA 23 | 9.89 (10) | 9.89 | 74.74 (10) | 74.74 |
| Fixed hybrid | 7.93 (56) | 8.02 (54) | 80.95 (56) | 62.93 (44) |
| Refit selected | 8.05 (56) | 8.10 (55) | 71.75 (56) | 52.06 (42) |

TSA 23 independent subset:

- Fixed hybrid BA: 15.02; refit selected BA: 15.12
- Neither model has an independent TSA 23 volume plot inside its predictor range

## Decision

- Do **not** promote either refit as operational.
- Do **not** replace the published default cards.
- Keep the refit volume candidate as **research-only**; it improves the
  independent BC IDF in-domain error but has no independent TSA 23 volume
  coverage and remains far from operational accuracy.
- Keep the applicability/abstention rule: do not emit outside development
  predictor ranges.
- The next model improvement needs a larger, temporally aligned high-biomass
  training set, not another refit on the same 31 development plots.

## Artifacts

- `psp/bc_validation/bc_idf_refit_candidates.json`
- `psp/bc_validation/bc_idf_refit_predictions.csv`
- `psp/refit_bc_validation.py`
