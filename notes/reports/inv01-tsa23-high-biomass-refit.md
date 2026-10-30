# INV-01 TSA 23 high-biomass refit experiment

## Purpose

The four TSA 23 PSP holdout plots are mostly outside the published BA/volume
range.  This experiment adds high-biomass IDF plots from TSA 29 to see whether
the cards can be extended without sacrificing the TSA 23 held-out performance.

This is a domain-extension experiment, not an operational validation.  TSA 29 is
a different TSA; the four TSA 23 plots are clustered in one tile.  Do not replace
the published cards from this result.

## Data

- TSA 23 training: 14 IDF plots
- TSA 23 external holdout: 4 IDF plots, one 2019 tile
- TSA 29 high-biomass increment: 10 selected, 8 usable
  - 4024191, 4024279, 4024285, 4024299, 4024429, 4024835, 4024836, 4026687
  - 4024194 excluded: downloaded LAZ fails `lazrs` at read time
  - 4024290 excluded: published tile is 113 KB / 18,949 points and has no
    first returns in the plot support
- TSA 22 high-biomass candidates are Okanagan TSA, not adjacent to TSA 23;
  they are excluded from training and would be a separate transfer test only.

All data and outputs are under
`/srv/shared-data/gep/ws4/tmp/inv01-data` on the data drive.

The TSA 29 point clouds are 2019/2023/2024; the ground visits are 2018/2022.
The TSA 23 holdout remains 2018 plots against 2019 lidar.  Exact plot support is
used, with the 1 m DEM matched to the point-cloud map tile.  The 4026687 DEM was
corrected to `bc_093b029_4_3_1_xli1m...` after an adjacent tile produced
impossible heights.

## Candidate form

The candidate keeps the published forms:

- height: identity on `Lhp95`
- BA: log link on `Lhmean`, `CC2m`
- volume: log link on `Lhmean`, `CC2m`

The candidate is fitted on the 14 TSA 23 training plots plus the 8 TSA 29
high-biomass plots, then tested on the four TSA 23 holdout plots.

## Results

| Attribute | Current holdout RMSE | Candidate holdout RMSE | Current bias | Candidate bias |
| --- | ---: | ---: | ---: | ---: |
| Lorey height | 1.462 | 2.032 | +0.997 | +1.637 |
| Basal area | 8.351 | 7.823 | +0.931 | -3.062 |
| Gross volume | 118.207 | 79.984 | +89.267 | +53.365 |

The high-biomass increment materially improves BA and volume on the four TSA 23
plots, but **height gets worse**.  The volume bias is still +53 m3/ha and the
volume RMSE remains far above the pilot LOOCV (20.666 m3/ha).

This is not enough to replace the cards.  It does show that the high-biomass
domain extension is the right direction.

## Candidate coefficients

These are experimental only; they are not published model cards.

| Attribute | Intercept | `Lhp95` | `Lhmean` | `CC2m` |
| --- | ---: | ---: | ---: | ---: |
| Height (identity) | 1.094285 | 0.885092 | — | — |
| BA (log link) | -3.377564 | — | 0.743383 | 1.129363 |
| Volume (log link) | -2.028867 | — | 1.416963 | 0.861132 |

No output scale was refitted in this experiment; the current BA/volume scale
factors were not applied to the candidate.  A production refit should fit scale
and intercept together and use a proper spatial holdout.

## Decision

- Keep the published height card; the candidate degrades height.
- Do not replace the published BA/volume cards yet.
- The volume improvement is promising but still fails the external cluster.
- Add TSA 22 high-biomass plots (UTM 11) and, more importantly, acquire
  high-biomass **TSA 23** plots before publishing.
- Then refit with a tile-level spatial holdout and a wider range; do not wait for
  new validation data.

## Files

- `notes/reports/inv01-tsa23-high-biomass-targets.md`
- `notes/reports/inv01-tsa23-high-biomass-candidates.csv`
- `notes/reports/inv01-tsa23-high-biomass-download.csv`
- `notes/reports/inv01-tsa23-high-biomass-features.csv`
- `notes/reports/inv01-tsa23-high-biomass-refit.json`
- `notes/reports/inv01-tsa23-high-biomass-acquisition-targets.md`
