# INV-01 TSA 23 model-status mask

## Purpose

The current 25 m surface is a pilot, not a wall-to-wall inventory.  The status
mask separates coverage gaps from model-domain gaps.

## Current cards

| Code | Class | Area km2 | Share of TSA |
| ---: | --- | ---: | ---: |
| 0 | No public point cloud | 2,465.7 | 20.0% |
| 1 | Omitted / no fine 1 m DEM | 1,936.7 | 15.7% |
| 2 | Processed, but no model cell | 3,643.0 | 29.5% |
| 3 | Height only | 2,463.5 | 20.0% |
| 4 | BA/volume valid | 1,839.2 | 14.9% |

The rasterized TSA area is 12,348.0 km2; the vector TSA area is 12,353.2 km2.
The difference is the 25 m edge approximation.

Height predictions cover **33.3%** of the TSA (6,573,196 cells); BA/volume cover
**14.9%**.  The other 51.8% has no height/BA/volume surface: 20.0% no public
point cloud, 15.7% omitted/no-DEM, and 29.5% processed but with no usable model
cell (including cells outside the card ranges).

## Regional candidate cards

Applying the experimental regional BA/volume cards to the full feature grid:

| Code | Class | Area km2 | Share of TSA |
| ---: | --- | ---: | ---: |
| 0 | No public point cloud | 2,465.7 | 20.0% |
| 1 | Omitted / no fine 1 m DEM | 1,936.7 | 15.7% |
| 2 | Processed, but no model cell | 3,207.1 | 26.0% |
| 3 | Height only | 1,825.5 | 14.8% |
| 4 | BA/volume valid | 2,913.0 | 23.6% |

The regional candidates increase BA/volume coverage from 14.9% to **23.6%** of
TSA 23, while height coverage is unchanged.  This is still an experimental
surface; the four-plot external check is clustered and the candidate cards are
not published operational cards.

## Rasters

`tsa23_model_status_25m.tif` for the current cards:

1. `model_status` — 0 no point cloud, 1 omitted/no fine DEM, 2 processed/no model
   cell, 3 height only, 4 BA/volume valid.
2. `ba_vol_predictor_outside` — 1 where a feature cell is outside the published
   BA/volume predictor range.
3. `height_predictor_outside` — 1 where a feature cell is outside the published
   height predictor range.

`tsa23_model_status_regional_25m.tif` is the same three bands for the regional
candidate cards.

## Interpretation

- Do not treat classes 2-4 as “valid everywhere”.
- Class 3 is height-only; BA/volume are unsupported.
- Classes 0 and 1 are coverage gaps, not zero biomass.
- The regional candidates do not improve height; height keeps the current card.
- The high-biomass regional cards are experimental and must not be published as
  operational cards without a larger spatial holdout.

## Reproduce

Builders:

- `examples/inv01_tsa23_validation/build_status_mask.py` — current cards
- `examples/inv01_tsa23_validation/build_status_mask_regional.py` — regional
  candidate cards

Data root, never `/tmp`:

```text
/srv/shared-data/gep/ws4/tmp/inv01-data
```
