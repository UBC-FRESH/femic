# INV-01 regional candidate applied to the full grid

## What was run

The experimental regional BA and volume candidates were applied to the full
9,523,476-cell TSA 23 feature grid.  Height still uses the published current
card.

## Coverage

| Surface | Current cells | Candidate cells | Current TSA share | Candidate TSA share |
| --- | ---: | ---: | ---: | ---: |
| Height | 6,573,196 | 6,573,196 | 33.3% | 33.3% |
| BA | 2,942,755 | 7,479,672 | 14.9% | 37.9% |
| Volume | 2,942,755 | 4,745,557 | 14.9% | 24.0% |
| BA and volume | 2,942,755 | 4,660,847 | 14.9% | 23.6% |

The regional candidates increase the joint BA/volume surface from 1,839 km2 to
2,913 km2, a 58% increase in covered area.  Twelve percent of the TSA is newly
covered; the remaining gaps are still no-point-cloud and no-DEM areas.

## Candidate statistics

| Attribute | Cells | Mean | Median | Min | Max |
| --- | ---: | ---: | ---: | ---: | ---: |
| BA (m2/ha) | 7,479,672 | 23.83 | 23.25 | 13.45 | 44.30 |
| Volume (m3/ha) | 4,745,557 | 167.81 | 153.44 | 56.66 | 511.54 |

These are candidate model outputs, not observations.  The four-plot external
check is the evidence for the candidate; it is clustered in one TSA 23 tile.

## Status consequences

- Current model-status: BA/volume 14.9%, height 33.3%.
- Regional candidate status: BA/volume 23.6%, height 33.3%.
- Processed/no-model drops from 29.5% to 26.0%; height-only drops from 20.0% to
  14.8%.
- No point cloud and omitted/no-DEM remain 20.0% and 15.7%.

## Decision

Use this as an experimental open-data bundle, not a published operational card.
The candidate is materially better than the current volume extrapolation and
also improves BA, but it still has a narrow spatial holdout.

## Files

- `notes/reports/inv01-tsa23-regional-inventory.md`
- `notes/reports/inv01-tsa23-model-status.md`
- `notes/reports/inv01-tsa23-regional-calibration.md`
- `experiments/inv01-regional-calibration/candidate_cards.json`
- data root: `inventory_regional_full.parquet`,
  `tsa23_model_status_regional_25m.tif`
