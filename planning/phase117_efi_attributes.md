# Phase 117: EFI Inventory Attributes and Biomass Curves

Parent issue: `#374`
Branch: `feature/p117-efi-attributes`; P117.1 split PR:
`feature/p117.1-efi-application`
Status: active (P117.1 application engine; real coefficients/backtest pending)

## Purpose

Turn the P79 LiDAR product bundle into inventory attributes and a biomass curve
family the estate models can consume. P79 owns the sensor pipeline; this phase
owns the inventory model and the curve family.

## P117.1 application engine

Implemented:

- `femic.efi.coefficients.v1` coefficients contract.
- `femic.efi.application` linear prediction, applicability checks, domain
  flagging/dropping, and bias/RMSE/MAE/R-squared backtest.
- Synthetic site-index pilot card and coefficients.
- Contract/API docs and 13 focused tests.

Open:

- a published or project site-index coefficient set;
- mapping the selected FEMIC LiDAR metrics;
- adding `si_als` to the fragment attribute pipeline;
- running the instance backtest with the P48/P49 ground-plot surfaces.

## P117.2 biomass curves

Planned: a biomass curve family and carbon conversion, independent of the
volume curve.

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
