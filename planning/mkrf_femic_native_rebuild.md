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

## `P60.2b` Rebuild sequencing and validation contract

The canonical MKRF rebuild lane should use the same high-level sequencing
discipline as the standalone K3Z/TSA29 pattern, while keeping the PoC package
and checkpoint-driven surfaces out of the claim boundary.

### Authoritative rebuild sequence

The ordered rebuild sequence for the future canonical MKRF lane is:

1. validate instance case and runtime contracts
   - case/config sanity;
   - required external/runtime prerequisites; and
   - docs/runtime path agreement for the active instance lane.
2. validate geospatial runtime readiness
   - shapefile/GDAL/Fiona I/O;
   - required upstream source surfaces materialized and readable; and
   - no checkpoint-derived substitutes standing in for claimed raw source.
3. compile the upstream source lane
   - source-driven preparation from `03_MappingAnalysisData/*`;
   - reviewed source-input contracts only; and
   - explicit lineage capture for the produced intermediate artifacts.
4. complete the post-yield/model-input bundle lane
   - normalized model-input tables;
   - canonical bundle/config surfaces under `config/`; and
   - explicit publication of the generated inputs that will feed the canonical
     runtime package.
5. run Patchworks preflight against the canonical rebuild package
   - runtime config;
   - XML/track/control prerequisites; and
   - launch/runtime prerequisites such as licensing and JVM wiring.
6. publish the canonical geometry/block/topology runtime surfaces
   - source-faithful runtime spatial handoff under the rebuild package;
   - explicit block/topology generation where required; and
   - separation from accepted PoC compiled-runtime evidence.
7. run Matrix Builder for the canonical rebuild package
   - regenerate runtime tracks from the canonical rebuild package;
   - synchronize XML/tracks/accounts/control surfaces to the same contract; and
   - record runtime manifests/logs as rebuild evidence.
8. run acceptance validation against benchmark/reference surfaces
   - compare selected outputs against the accepted PoC benchmark surfaces;
   - compare legacy evidence where it still matters for acceptance; and
   - record accepted redesign choices versus unresolved regressions.

### Required validation gates

Each phase above must answer a distinct question and emit explicit evidence:

- **contract gate**
  - are the rebuild inputs/config/runtime assumptions explicit and valid?
- **source gate**
  - are the claimed raw-source inputs materialized and actually being used?
- **publication gate**
  - were canonical rebuild artifacts generated into the intended package
    surfaces rather than borrowed from PoC/checkpoint evidence?
- **runtime gate**
  - can the canonical rebuild package pass Patchworks preflight and matrix build?
- **acceptance gate**
  - does the rebuilt package behave acceptably against the benchmark/reference
    surfaces the team still cares about?

### Required evidence surfaces

The rebuild lane should leave behind, at minimum:

- rebuild-spec / allowlist / run-config state under `config/`;
- lineage and evidence ledgers under `metadata/`;
- runtime logs/manifests for preflight, matrix build, and representative runs;
- canonical generated runtime artifacts under the new rebuild package in
  `models/`; and
- benchmark comparison summaries that tie rebuilt outputs back to the accepted
  PoC evidence surface.

### Explicit non-goals for this contract

This sequencing contract does not allow:

- treating `models/mkrf_patchworks_model_poc/` as the canonical rebuild
  package;
- using checkpoint-derived or compiled-runtime artifacts as substitutes for raw
  source while claiming a source-faithful rebuild;
- skipping Patchworks preflight/matrix-build and treating static file presence
  as rebuild validation; or
- treating unexplained legacy seams as required by default just because they
  existed in the PoC lane.

## `P60.2c` Benchmark/reference separation contract

The canonical rebuild lane must keep the accepted PoC evidence surfaces and the
new source-faithful build surfaces distinct in both pathing and claim language.

### Benchmark/reference evidence surface

The following remain benchmark/reference evidence only:

- `models/mkrf_patchworks_model_poc/` and its generated runtime artifacts;
- accepted PoC benchmark saved-stage and report surfaces;
- accepted compiled legacy runtime evidence preserved for comparison;
- reviewed archaeology outputs such as workbook/XML/runtime translations; and
- any checkpoint target-state or helper seams that exist only to preserve PoC
  comparability.

These surfaces may be used for:

- comparison;
- acceptance-gate benchmarking; and
- lineage/documentation.

They may not be used as substitutes for canonical rebuild outputs when making a
source-faithful claim.

### Canonical rebuild surface

The future canonical MKRF rebuild lane must publish its own distinct surfaces:

- source-driven contracts under `config/`;
- source-faithful generated metadata and ledgers under `metadata/`;
- canonical generated runtime artifacts under a rebuild package in `models/`;
- rebuild-owned docs/runbooks under the standalone instance repo; and
- rebuild-owned runtime logs/manifests and acceptance summaries.

The canonical rebuild package must not reuse the PoC package path or hide new
generated artifacts inside PoC evidence directories.

### Required separation rules

- PoC and canonical rebuild runtime packages must remain path-distinct.
- Acceptance summaries must say explicitly whether they describe:
  - PoC benchmark/reference evidence; or
  - canonical rebuild outputs.
- Raw-source publication claims must point back to the upstream source lane,
  not to PoC compiled-runtime or checkpoint artifacts.
- If a PoC artifact is copied or reused for comparison, it must remain labeled
  as benchmark/reference evidence rather than being silently promoted.

### Practical implication for later phases

For `P60.3+`, every new generated artifact should answer one of two questions:

- is this a benchmark/reference surface preserved from the PoC lane? or
- is this a canonical rebuild output generated from the source-faithful lane?

If the answer is unclear, the artifact boundary is wrong and should be fixed
before stronger rebuild claims are made.
