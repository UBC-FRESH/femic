# MKRF FEMIC-Native Rebuild Notes

Issue: `#173`

## Summary

This note is the active planning surface for the from-scratch MKRF rebuild
lane.

It starts after the legacy archaeology / PoC benchmark program recorded in:

- `planning/mkrf_legacy_decompile.md`

The governing posture for this lane is:

- use the standalone K3Z/TSA29 FEMIC instance pattern as the default
  architecture;
- treat the current MKRF PoC package and benchmark surfaces as comparison
  evidence only;
- carry forward legacy behavior only when it is justified by reviewed source
  evidence or benchmark necessity.

## Current rebuild contract

### Governing architecture defaults

- standalone instance repo remains the canonical owner of runtime/config/docs;
- parent FEMIC repo remains a pointer/lineage and integration surface;
- canonical rebuild contracts live under `config/`;
- canonical user-facing/operator docs live under `docs/`;
- the future canonical runtime package lives under `models/` as a rebuild
  surface distinct from the current PoC package:
  `models/mkrf_patchworks_model_poc/`.

### What is benchmark/reference evidence only

- the current PoC runtime package;
- PoC benchmark saved-stage and report surfaces;
- accepted legacy compiled-runtime evidence;
- reviewed workbook/XML/runtime translations recovered during the archaeology
  lane.

These are acceptance/comparison surfaces, not automatic architecture contracts.

### Carry-forward gate

Any legacy behavior carried into the new rebuild must satisfy at least one of:

- justified by reviewed source evidence from the upstream legacy corpus; or
- justified by benchmark necessity because dropping it would break an accepted
  comparison surface the team still cares about.

Anything satisfying neither test should be treated as removable PoC/legacy
residue.

## Active phase map

### `P60.1` Define the target instance contract and acceptance gates

Completed:

- `P60.1a`
  set the governing standalone-instance pattern using K3Z/TSA29 conventions;
- `P60.1b`
  fixed the PoC package as benchmark/reference evidence only; and
- `P60.1c`
  required explicit evidence or benchmark necessity for any legacy behavior
  carried forward.

This phase starts from the closed PoC handoff already established in the
legacy note:

- the current PoC runtime package under
  `models/mkrf_patchworks_model_poc/` is benchmark/intermediate evidence only;
- the Phase 59 standalone docs lane is complete enough that the benchmark lane
  no longer needs to be treated as under-documented; and
- the rebuild lane is free to move forward without reopening PoC archaeology
  unless a later acceptance gate requires it.

### `P60.2` Define the canonical FEMIC-native MKRF instance layout

Completed:

- `P60.2a`
  fixed the canonical top-level layout contract:
  `.github/`, `config/`, `data/`, `docs/`, `models/`, `metadata/`,
  `runbooks/`, plus root repo docs.

Active next bounded move:

- `P60.2b`
  define the authoritative rebuild sequencing and validation contract for the
  canonical MKRF rebuild lane.

Planned immediately after:

- `P60.2c`
  keep benchmark/reference artifacts clearly separated from the new
  source-faithful build surfaces.

### Downstream phases

- `P60.3`
  reconstruct the raw-source geometry-to-runtime pipeline from
  `03_MappingAnalysisData/*`;
- `P60.4`
  rebuild the target/control lane from reviewed source contracts instead of
  checkpoint loading;
- `P60.5`
  rebuild the full MKRF runtime package from source-faithful inputs;
- `P60.6`
  validate the rebuilt model against the accepted PoC benchmark and relevant
  legacy evidence; and
- `P60.7`
  publish closeout docs and decide whether umbrella issue `#172` can close.

In shorthand:

- `P60.3`
  rebuild the raw-source geometry-to-runtime pipeline from
  `03_MappingAnalysisData/*` as a source-faithful lane, not by reusing PoC
  runtime/checkpoint substitutes;
- `P60.4`
  rebuild the target/control lane from reviewed source contracts instead of
  legacy checkpoint loading or unexplained compiled helper seams;
- `P60.5`
  rebuild the full MKRF runtime package from source-faithful inputs and publish
  the new canonical runtime outputs;
- `P60.6`
  validate the rebuilt model against the accepted PoC benchmark surfaces and
  the legacy evidence that still matters for acceptance; and
- `P60.7`
  publish closeout docs and decide whether umbrella legacy-recovery issue
  `#172` can close once the from-scratch rebuild is complete.

## Immediate working rules for `P60.2+`

- Do not let the current PoC package path become the canonical rebuild path.
- Do not use checkpoint-derived or compiled-runtime artifacts as substitutes
  for raw-source rebuild claims.
- Prefer K3Z/TSA29 sequencing and validation structure unless MKRF-specific
  source evidence requires a different contract.
- When a later task needs an explicit acceptance gate, define it in terms of:
  - source evidence,
  - canonical generated outputs, and
  - benchmark comparison surfaces,
  not ad hoc convenience artifacts.
