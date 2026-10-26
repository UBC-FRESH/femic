# Phase 117: EFI Inventory Attributes and Biomass Curves

Parent issue: `#374`
Branch: `feature/p117-efi-attributes`
Status: planned (2026-10-25)

## Purpose

Turn FEMIC's existing LiDAR product bundle into inventory attributes and a
biomass curve family the estate models can consume. P79 owns the sensor
pipeline; this phase owns the inventory model and the curve family.

## Implemented (2026-10-26)

- `femic.efi.application`: `femic.efi.coefficients.v1` contract, linear
  prediction, applicability checks, domain flagging/dropping, and a
  bias/RMSE/MAE/R-squared backtest.
- Synthetic site-index pilot card and coefficients, with 13 focused tests and
  contract/API docs.
- Real coefficients, the instance backtest, and the `si_als` pipeline remain
  open in `#375`.

## Children

- `P117.1` (`#375`): ALS site-index / potential-height layer.
- `P117.2` (`#376`): biomass curve family and carbon conversion.

## Dependencies

- `P116.3` (`#372`) for the EFI model card.
- `P79` (`#211`) for the LiDAR product bundle.
- `P115` (`#361`) for the carbon package; this phase does not duplicate it.
- ws4 `P48`/`P49` for the ground-plot validation surfaces.

## Out of scope

- Rebuilding the P79 LiDAR pipeline.
- The carbon package or CBM runtime.
- The P114 hydrology lane.
- A universal site-index equation or a new remote-sensing study.
- An estate-model objective change.

## Acceptance

- The site-index layer covers the pilot AOI and reports its gaps.
- A backtest reports bias, RMSE, and the fragments whose curve assignment
  changes.
- Species outside the calibrated set are rejected or flagged.
- The biomass curve is independently selectable and carries its source,
  species, and conversion.
- No P79 or P115 code is duplicated.

## Risks

- Model transferability across species and regions.
- Young-stand height bias.
- Allometry and belowground assumptions.
- Double counting if volume and biomass are summed into one account.
