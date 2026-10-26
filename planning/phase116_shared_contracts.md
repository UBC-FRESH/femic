# Phase 116: Shared Environmental Contracts

Parent issue: `#369`
Branch: `feature/p116-shared-contracts`
Status: active (P116.1 complete; P116.2 and P116.3 pending)

## Purpose

Give FEMIC, ws3, ws4, FHOPS, and Nemora one shared vocabulary for climate,
disturbance, and EFI-model metadata. The contracts are dependency-light schemas
plus one real consumer each.

## Contract home

`femic/contracts` for this wave. Keep the package free of the FEMIC modelling
stack so the other repos can import it without the full dependency tree. A
separate `fresh-contracts` repository remains the longer-term option.

## P116.1 climate contract

Implemented:

- `femic.contracts.climate`: `femic.climate.v1` schema, validator, CSV/JSON
  reader and writer, provenance summary, and a public-safe sample table.
- `femic.contracts.climate_na`: annual ClimateNA/SilvR21 CSV adapter with a
  default column map and explicit override.
- `femic.climate.consumer`: context selection and provenance-bearing attachment
  to attribute rows. This is the first climate consumer.
- Contract, API, and consumer docs; 40 focused tests across the three suites.

## P116.2 disturbance contract

Implemented:

- `femic.contracts.disturbance`: `femic.disturbance.v1` event record,
  controlled types, severity model, spatial references, JSON reader/writer,
  provenance summary, and ws4-facing consumer rows.
- Fire and NSR examples, contract/API docs, and 18 focused tests.
- The ws4 consumer is merged: `UBC-FRESH/ws4#398` (`5ea4a05`).

## P116.3 EFI model cards

Implemented contract:

- `femic.contracts.efi`: `femic.efi.model.v1` card with training, validation,
  applicability, and licence metadata; domain checks and row annotation.
- Two public-safe synthetic cards, contract/API docs, and 22 focused tests.

Open: real project/published cards and the FEMIC attribute-pipeline wiring.

## Out of scope

- A new climate, disturbance, or EFI model.
- A climate-growth response or yield modifier.
- Rebuilding the P79 LiDAR pipeline.
- The P114 hydrology lane.
- A fire-spread simulator or a new data portal.
