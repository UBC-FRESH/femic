# INV-01 TSA 23 spatial holdout

## Method

Leave-one-25 m-tile-out across the 18 TSA 23 plots, training on the other TSA 23
tiles plus the 19 non-TSA-23 high-biomass plots.  This is a broader spatial
check than the four-plot external tile.

Models:

- BA: linear regional card (`Lhmean`, `Lhp95`)
- Volume: second-order polynomial log-volume card
- Height: current card, unchanged

## Result

- 13 tiles, 18 plots
- BA aggregate RMSE: **6.188 m2/ha**
- Volume aggregate RMSE: **25.473 m3/ha**

The hardest fold is still `lidarbc:4:117213` (the four external high-biomass
plots): BA 6.670 and volume 42.092 m3/ha.  Most other tiles are much better;
volume RMSE ranges from 3.5 to 37.1 across single-plot folds.

## Comparison

| Check | BA RMSE | Volume RMSE |
| --- | ---: | ---: |
| Current 14-plot LOOCV | 4.414 | 20.666 |
| Hybrid TSA 23 tile CV | 6.188 | 25.473 |
| Hybrid four-plot external | 6.670 | 42.092 |

The hybrid is not worse than the published cards in a way that justifies
blocking it, but it is still a small plot set and the four high-biomass plots
remain the hardest case.  The hybrid remains the default **experimental**
inventory, not an operational one.

## Decision

Keep the hybrid as the instance experimental root.  Do not relabel it
operational.  The next evidence needed is an independent multi-tile high-biomass
set, not more refitting of the same 18 plots.
