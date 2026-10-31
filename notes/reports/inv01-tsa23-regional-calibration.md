# INV-01 regional IDF calibration using all open PSP + LidarBC data

## What changed

The previous experiment stopped at TSA 23/29.  Using the full open-data stack,
I found **46 high-biomass IDF PSP plots across BC with matching LidarBC point
clouds** (TSAs 2, 5, 9, 18, 22, 23, 29).  Of those, 24 produced usable
first-return features; 19 non-TSA-23 plots supplement the 14 TSA 23 training
plots.  The four TSA 23 high-biomass plots remain the external check.

Uses the existing open PSP and LidarBC data.

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
| Basal area | 8.351 | 6.670 | +0.931 | -3.807 |
| Gross volume | 118.207 | 42.484 | +89.267 | -3.370 |

The regional high-biomass data **fixes the volume extrapolation** on the four
TSA 23 plots: bias drops from +89 to -3 m3/ha and RMSE from 118 to 42.  The BA
candidate also improves: RMSE 8.351 to 6.670 and bias +0.93 to -3.81, using
`Lhmean` and `Lhp95` instead of `Lhmean` and `CC2m`.  Height does not improve and
keeps the current card.

## Candidate coefficients

Experimental only; not published as model cards.

| Attribute | Intercept | `Lhp95` | `Lhmean` | `CC2m` |
| --- | ---: | ---: | ---: | ---: |
| Height (identity) | 1.633212 | 0.859860 | — | — |
| BA (log link) | 2.059838 | — | 0.747222 | — |
| Volume (log link) | -1.081158 | — | 1.183467 | 0.768613 |

The volume candidate is the first version that covers the high-biomass test
without the old +90 m3/ha bias.  It still needs a larger TSA 23 spatial holdout
before becoming a published card.

## Cross-region holdout

Leave-one-TSA-out CV on the 24 regional high-biomass plots (fit 14 TSA 23 +
all other regional high plots):

| Held-out region | BA RMSE | BA bias | Volume RMSE | Volume bias |
| --- | ---: | ---: | ---: | ---: |
| TSA 2 (n=9) | 9.42 | +6.92 | 100.61 | +74.58 |
| TSA 5 (n=1) | 2.14 | +2.14 | 16.11 | -16.11 |
| TSA 18 (n=3) | 5.69 | +4.72 | 62.15 | +12.10 |
| TSA 22 (n=1) | 12.29 | -12.29 | 32.66 | -32.66 |
| TSA 29 (n=5) | 7.61 | -6.35 | 46.95 | -36.46 |

The regional cards are not uniformly transferable; volume is especially
region-sensitive.  The four-plot TSA 23 check is better than the TSA 2/18
regions, so the candidate is a real step, not a finished operational model.

## Model bundle

The experimental cards are packaged at
``experiments/inv01-regional-calibration/model_bundle/`` with a manifest,
checksums, candidate metrics, and the cross-region CV.  They load through
``femic.lidar.inventory.load_inventory_als_model``.  The full-grid application is
in ``examples/inv01_tsa23_validation/apply_regional_inventory.py``.

## Decision

- Keep the current height card; the regional height fit is worse.
- Treat the regional **BA and volume** candidates as experimental; both improve
the four-plot external check but are selected on a small clustered test.
- The data support continued model development.
- Next: refit/evaluate BA and volume on more TSA 23 high-biomass tiles and publish
  the candidate cards as experimental, not operational.

## Files

- `notes/reports/inv01-tsa23-regional-calibration.md`
- `notes/reports/inv01-tsa23-regional-features.csv`
- `notes/reports/inv01-tsa23-regional-refit.json`
- data root: `/srv/shared-data/gep/ws4/tmp/inv01-data/psp/`
