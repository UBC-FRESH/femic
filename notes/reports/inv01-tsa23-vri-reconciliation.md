# INV-01 TSA 23 VRI reconciliation

## Purpose

This report tests whether the full TSA 23 pilot surface is consistent with the
public BC Vegetation Resources Inventory (VRI).  It is a **screening check**, not
independent validation: VRI polygons are interpreted estimates, often older than
the point clouds, and several VRI attributes have different definitions from the
FEMIC model outputs.

The operational conclusion is negative: the current 14-plot IDF cards disagree
with VRI far more than their LOOCV errors suggest.  The surface remains a pilot
and must not be used for operational TSA 23 decisions.  A later four-plot PSP
holdout (see ``inv01-tsa23-psp-holdout.md``) is mostly outside the current
BA/volume card range; it confirms that the high-biomass domain is not covered,
not merely that the volume card is noisy.

## Inputs

| Input | Value |
| --- | --- |
| Features | `features_full.parquet`, 9,523,476 cells, SHA-256 `296c31f6...` |
| Inventory | `inventory_full.parquet`, 12,458,706 rows, SHA-256 `19be051c...` |
| VRI | `ria_vri_vclr1p_checkpoint8.feather`, 102,132 polygons, EPSG:3005, SHA-256 `9cc1c493...` |
| Model cards | TSA 23 IDF cards, model version `2026.1` |
| Code | `main` at `6dd15f1` plus this validation branch |

VRI polygons are all `BCLCS_LEVEL_1 = V`, `FOR_MGMT_LAND_BASE_IND = Y`; 102,081
have positive polygon area.  The file is the TSA 23 checkpoint used by the
instance, not a new download.

## Method

- Cell centres were transformed from `EPSG:3157` to `EPSG:3005`.
- Cell centres were joined to VRI polygons by point-in-polygon.
- Overlapping VRI polygons were deduplicated per cell by retaining the smallest
  polygon.
- Only cells with a model prediction and a positive VRI value were compared.
- Metrics were computed at both cell level and VRI-polygon level.  The polygon
  level uses the mean of cell predictions within each `FEATURE_ID`; it reduces
  pseudo-replication but remains spatially autocorrelated.
- Error is `prediction - VRI`.  Negative bias means underprediction.
- No outlier trimming or calibration was applied.

Attribute definitions are not identical:

- `PROJ_HEIGHT_1` is VRI projected/top height; the model predicts Lorey height.
- `BASAL_AREA` is VRI basal area; the model predicts live-tree basal area for
  DBH >= 9.1 cm.
- `LIVE_STAND_VOLUME_125` is VRI live volume for trees >= 12.5 cm; the model
  predicts gross volume.  A positive volume bias is therefore partly definitional.

## Join coverage

| Item | Cells |
| --- | ---: |
| Full feature grid | 9,523,476 |
| Joined to a VRI polygon | 8,187,067 (86.0%) |
| Height-card cells, total | 6,573,196 |
| Height-card cells with VRI height | 5,670,064 |
| BA/volume-card cells, total | 2,942,755 |
| BA-card cells with VRI BA | 2,745,339 |
| Volume-card cells with VRI volume | 2,711,451 |

The 1.3 M cells not joined to VRI are mostly non-vegetated, non-productive, or
outside the VRI forest polygon layer.  They are not evidence of point-cloud gaps.

## Results

### Cell level

| Attribute | n | Model mean | VRI mean | Bias | MAE | RMSE | r | Slope |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Lorey height (m) | 5,670,064 | 16.18 | 18.66 | -2.48 | 6.18 | 7.65 | 0.398 | 0.169 |
| Basal area (m2/ha) | 2,745,339 | 24.07 | 19.46 | +4.61 | 9.50 | 11.49 | 0.364 | 0.220 |
| Gross volume (m3/ha) | 2,711,451 | 141.57 | 112.11 | +29.46 | 74.92 | 92.83 | 0.397 | 0.262 |

### VRI-polygon level

| Attribute | Polygons | Bias | MAE | RMSE | r | Slope | Spearman |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Lorey height (m) | 67,150 | -2.94 | 6.56 | 7.86 | 0.525 | 0.165 | 0.565 |
| Basal area (m2/ha) | 48,757 | +5.29 | 9.34 | 10.98 | 0.523 | 0.229 | 0.545 |
| Gross volume (m3/ha) | 48,039 | +28.90 | 70.33 | 85.12 | 0.507 | 0.257 | 0.568 |

The polygon-level correlation is higher than the cell-level correlation, as
expected when many cells share one VRI polygon, but the bias and RMSE remain large.

### By BEC zone

| Zone | Height n | Height bias / RMSE | BA n | BA bias / RMSE | Volume n | Volume bias / RMSE |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| IDF | 4,019,392 | -2.21 / 7.39 | 1,950,516 | +5.70 / 11.12 | 1,924,722 | +42.97 / 86.11 |
| SBS | 731,776 | -3.30 / 8.13 | 389,342 | +2.72 / 12.29 | 386,183 | +5.42 / 107.43 |
| SBPS | 636,587 | -2.54 / 8.35 | 266,638 | +2.66 / 12.21 | 262,567 | +6.95 / 96.06 |
| MS | 163,213 | -2.55 / 7.89 | 50,197 | +1.37 / 12.95 | 49,835 | -23.86 / 123.92 |
| ESSF | 119,096 | -5.93 / 9.01 | 88,646 | -3.31 / 12.75 | 88,144 | -63.04 / 128.23 |

The IDF is the largest zone and the one where the BA and volume cards were
fitted.  It still shows strong volume overprediction (+43 m3/ha).  ESSF shows the
opposite pattern, with underprediction of all three attributes.

### By VRI value class

| VRI class | Height bias / RMSE | BA bias / RMSE | Volume bias / RMSE |
| --- | ---: | ---: | ---: |
| Lowest class | +9.16 / 10.45 (<10 m) | +14.55 / 15.61 (<10 m2/ha) | +84.34 / 96.06 (<50 m3/ha) |
| Middle class | -2.07 to +1.41 / 3.4-3.7 | +1.28 / 7.02 (20-30) | -4.80 / 60.93 (150-200) |
| Highest class | -9.97 / 10.63 (25+ m) | -9.25 / 12.36 (30+ m2/ha) | -97.99 / 128.90 (200+ m3/ha) |

This is the classic compression pattern: the model overpredicts low-biomass
stands and underpredicts high-biomass stands.  It is consistent with a 14-plot
fit and with the narrow predictor ranges in the cards, not with a transferable
TSA-wide model.

## Interpretation

- The VRI comparison does **not** establish field accuracy.  It does establish
  that the current surface is not consistent with an independent public
  inventory layer at a scale that would support operational use.
- The height card has a LOOCV RMSE of 0.688 m but a VRI disagreement RMSE of
  7.65 m.  Definition differences (Lorey vs projected height, VRI vintage) explain
  some of this, but not the compression and the ESSF/IDF pattern.
- The BA and volume cards were fitted to only 14 IDF plots and cover only
  2.94 M of 9.52 M cells.  Their VRI disagreement is much larger than their
  LOOCV errors.
- Volume has an additional definitional mismatch: VRI `LIVE_STAND_VOLUME_125`
  is not FEMIC gross volume.  The +29 m3/ha mean bias should not be interpreted
  as a pure model error.  The rank correlation and the low/high-class pattern
  are still diagnostic.

## Decision

Do not use this surface as an operational TSA 23 inventory.  The next model step
is independent field validation and a spatial holdout, followed by a refit or
stratified model if the validation confirms these patterns.  VRI can support
screening, stratification, and sampling design; it cannot replace field plots.

## Files

- `notes/reports/inv01-tsa23-vri-reconciliation.json` — machine-readable metrics.
- `notes/reports/figures/inv01-tsa23-vri-reconciliation.png` — model-vs-VRI density.
- `examples/inv01_tsa23_validation/vri_reconcile.py` — reproducible join/metrics.
- `examples/inv01_tsa23_validation/make_validation_figures.py` — figure generation.
