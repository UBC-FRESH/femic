# Phase 117: EFI Inventory Attributes and Biomass Curves

Parent issue: `#374`
Branch: `feature/p117-efi-attributes`; P117.1 split PR:
`feature/p117.1-efi-application`
Status: active (P117.1 data-blocked; P117.2 remains)

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

Data-blocked close-out:

- no defensible BC CWH/TSA site-index coefficient set is available;
- no plot-level site-index/ALS backtest surface exists in P48/P49;
- `si_als` was not added and no curve assignment changed;
- the application engine and synthetic fixture remain reusable infrastructure.

See `notes/reports/p117.1-site-index-feasibility.md`.

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
