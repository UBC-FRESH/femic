# Phase 116: Shared Environmental Contracts

Parent issue: `#369`
Branch: `feature/p116-shared-contracts`
Status: planned (2026-10-25)

## Purpose

Give FEMIC, ws3, ws4, FHOPS, and Nemora one shared vocabulary for climate,
disturbance, and EFI-model metadata. The contracts are dependency-light schemas
plus one real consumer each; they are not a new modelling stack.

## Contract home

`femic/contracts` for this wave. Keep the package free of the FEMIC modelling
stack so the other repos can import it without pulling the full dependency
tree. A separate `fresh-contracts` repository remains the long-term option.

## Implemented (2026-10-25)

- `femic.contracts.climate`: `femic.climate.v1` schema, validator, CSV/JSON
  reader and writer, provenance summary, and a public-safe sample table.
- Contract page `docs/reference/contracts/climate-contract.rst` and API page
  `docs/reference/api/femic-contracts-climate.rst`.
- The ClimateNA/SilvR21 adapter and first consumer remain open in `#370`.

## Children

- `P116.1` (`#370`): `climate.v1` and a ClimateNA/SilvR21 adapter.
- `P116.2` (`#371`): `disturbance.v1` and a ws4 consumer.
- `P116.3` (`#372`): `efi.model.v1` model cards.

## Out of scope

- A new climate model, downscaling pipeline, or GCM selector.
- A new disturbance detection or attribution algorithm.
- Rebuilding the P79 LiDAR pipeline.
- The P114 hydrology lane.
- A fire-spread simulator or a new data portal.

## Acceptance

- Each schema has a validator, an example, and a failure test.
- Each contract has one downstream consumer reading real data.
- Provenance survives the round-trip.
- No parallel LiDAR, hydrology, or fire-simulation lane is introduced.

## Risks

- Contract sprawl.
- Repo coupling through a heavy shared package.
- Schema overreach in climate and disturbance vocabularies.
- False confidence: a valid schema does not make the data correct.
