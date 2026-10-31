# INV-01 regional IDF calibration using all open PSP + LidarBC data

## What changed

The previous experiment stopped at TSA 23/29.  Using the full open-data stack,
I found **46 high-biomass IDF PSP plots across BC with matching LidarBC point
clouds** (TSAs 2, 5, 9, 18, 22, 23, 29).  Of those, 24 produced usable
first-return features; 19 non-TSA-23 plots supplement the 14 TSA 23 training
plots.  The four TSA 23 high-biomass plots remain the external check.

No new field data and no acquisition gate were used.

## Data

- PSP: full FAIB archive; 969 BC IDF sites with reconstructed latest attributes
- High-biomass candidate set: 104 recent IDF sites (>=2017, volume >=200 m3/ha)
- LidarBC: province-wide point-cloud/DEM tile selection; 46 candidates matched
- Usable regional high-biomass features: 24 plots
- Training rows: 14 TSA 23 + 19 non-TSA-23 = 33
- External holdout: 4 TSA 23 plots (one 2019 tile)

Some candidates had no first returns in the actual point-cloud footprint or a
bad LAZ payload; they were excluded rather than filled with an empty sample.

## Results

| Attribute | Current holdout RMSE | Regional candidate RMSE | Current bias | Regional bias |
| --- | ---: | ---: | ---: | ---: |
| Lorey height | 1.462 | 1.659 | +0.997 | +1.247 |
| Basal area | 8.351 | 10.029 | +0.931 | -7.920 |
| Gross volume | 118.207 | 42.484 | +89.267 | -3.370 |

The regional high-biomass data **fixes the volume extrapolation** on the four
TSA 23 plots: bias drops from +89 to -3 m3/ha and RMSE from 118 to 42.  It does
not improve height or BA; those should keep the current cards or be refit
separately.

## Candidate coefficients

Experimental only; not published as model cards.

| Attribute | Intercept | `Lhp95` | `Lhmean` | `CC2m` |
| --- | ---: | ---: | ---: | ---: |
| Height (identity) | 1.633212 | 0.859860 | — | — |
| BA (log link) | -2.526970 | — | 0.386795 | 1.124657 |
| Volume (log link) | -1.081158 | — | 1.183467 | 0.768613 |

The volume candidate is the first version that covers the high-biomass test
without the old +90 m3/ha bias.  It still needs a larger TSA 23 spatial holdout
before becoming a published card.

## Decision

- Keep current height and BA cards.
- Treat the regional **volume** candidate as an experimental candidate, not a
  replacement card.
- The data are sufficient to continue model development now; no acquisition gate.
- Next: improve BA with the regional high set and test the volume candidate on
  more than one TSA 23 tile.

## Files

- `notes/reports/inv01-tsa23-regional-calibration.md`
- `notes/reports/inv01-tsa23-regional-features.csv`
- `notes/reports/inv01-tsa23-regional-refit.json`
- data root: `/srv/shared-data/gep/ws4/tmp/inv01-data/psp/`
