# TSA29 Dataset Compile Plan (Dual Fork: Patchworks + Woodstock/ws3)

## Objective

Compile and validate a TSA29 instance that serves two downstream targets from a
single FEMIC pipeline run:

1. Patchworks-formatted outputs (teaching/training support).
2. Woodstock-formatted outputs for ws3 model ingestion and simulation smoke
   testing (research-critical path).

## Scope Lock

- Primary success path: Woodstock/ws3 branch must run to a smoke-tested ws3
  simulation without errors and with sane outputs.
- Patchworks branch remains required, but secondary.
- Validation does not stop at "Woodstock files emitted"; it extends to "ws3
  model instance runs".

## Current State

- Standalone instance repo exists: `https://github.com/UBC-FRESH/femic-tsa29-instance`.
- FEMIC parent repo links it as submodule:
  `external/femic-tsa29-instance`.
- Snapshot baseline is published (`v0.1.0`) for immediate student use.
- Full rebuild remains open due to known Linux-side TSA index mismatch in 01a;
  Patchworks-enabled host validation remains required.

## End-to-End Pipeline Contract

### Stage A: Upstream FEMIC compile

Required:

- `femic prep validate-case --run-config config/run_profile.tsa29.yaml --tipsy-config-dir config/tipsy`
- `femic run --run-config config/run_profile.tsa29.yaml`
- `femic tsa post-tipsy --run-config config/run_profile.tsa29.yaml --tsa 29`

Expected core artifacts:

- `data/model_input_bundle/{au_table,curve_table,curve_points_table}.csv`
- run manifests in `vdyp_io/logs/`

### Stage B: Pipeline fork outputs

#### Branch B1 (Patchworks)

Required:

- `femic patchworks preflight --config config/patchworks.runtime.windows.yaml`
- `femic patchworks build-blocks --config config/patchworks.runtime.windows.yaml --with-topology`
- `femic patchworks matrix-build --config config/patchworks.runtime.windows.yaml`

Expected artifacts:

- `output/patchworks_tsa29_validated/forestmodel.xml`
- fragment bundle (`fragments.*`, or externalized thin-instance equivalent +
  checksums)
- matrix builder manifest in `vdyp_io/logs/`

#### Branch B2 (Woodstock -> ws3)

Required:

- `femic export woodstock --bundle-dir data/model_input_bundle --output-dir output/woodstock_tsa29`

Expected artifacts:

- complete Woodstock-formatted dataset under `output/woodstock_tsa29/`
- export manifest and checksums

## ws3 Integration and Smoke-Test Contract

### ws3 target repository

- `https://github.com/UBC-FRESH/ws3`

### Required smoke-test path

1. Create or reuse a TSA29 ws3 model instance scaffold.
2. Link FEMIC Woodstock outputs into ws3 input ports.
3. Run a minimal ws3 simulation.
4. Capture run log and summary outputs.

### Smoke-test acceptance criteria

- ws3 run exits successfully (no parser/runtime errors).
- input mappings resolve (no missing Woodstock tables/keys).
- at least one planning result table/report is emitted.
- sanity checks pass (non-empty schedules/volumes/areas; no all-zero collapse
  unless explicitly expected and documented).

### Evidence artifacts

- `evidence/ws3_smoke_report.latest.json`
- `evidence/ws3_smoke_logs/` (or referenced external log path with checksums)
- mapping manifest documenting FEMIC Woodstock outputs -> ws3 inputs.

## Risks and controls

1. FEMIC upstream compile regression (current 01a TSA index issue):
- Control: preserve snapshot baseline for immediate use; track full rebuild
  blocker and fix before phase closure.

2. Woodstock export appears valid but ws3 fails:
- Control: ws3 smoke test is mandatory gate, not optional.

3. Drift between Patchworks and Woodstock branches:
- Control: add shared invariant checks at fork point and branch-specific
  contract checks.

## Open Investigation: Site Productivity (siteprod) Dependency and Failure Policy

Question to resolve in Phase 19 execution hardening:

- Does FEMIC materially use siteprod raster SI values in any critical compile
  path, specifically for:
  - strata construction,
  - AU assignment,
  - VDYP curve generation,
  - TIPSY curve generation,
  - or another downstream component?

Decision gate:

1. If siteprod is not required for current default outputs:
- disable siteprod compile/sampling steps in the default code path.
- move siteprod work behind an explicit optional flag/path used only by
  workflows that truly require it.

2. If siteprod is required:
- keep it enabled, but harden logic so sparse/no-data stands do not crash
  full runs.
- enforce robust no-data handling (row-level fallback/NA policy) and clear
  diagnostics instead of runtime-warning storms or hard failures.

## Deferred Follow-On: VDYP Parallelization (Separate Non-Blocking Phase)

This work is intentionally split from TSA29 compile delivery so we do not delay
student-usable instance publication while pursuing concurrency tuning.

Scope for follow-on phase:

1. Add AU-level (or stratum-bucket) parallel VDYP execution as an opt-in path.
2. Preserve deterministic outputs versus serial baseline (contract tests
   required before any default switch).
3. Improve runtime observability for long runs (chunk/AU progress heartbeat,
   elapsed timing, and completion summary in logs/manifests).
4. Publish benchmark results comparing serial vs parallel wall-clock/runtime
   resource use on at least one large TSA workload.

Non-blocking rule:

- TSA29 Phase 19 completion is not gated on this optimization phase.
- Parallel mode can ship as experimental behind a feature flag first.

### P20.1 Acceptance Checklist (Contract + Non-Regression Invariants)

Parallelization work can proceed only after this checklist is locked:

1. Scope boundary:
- Parallel target is VDYP processing only (no behavior changes in strata, AU,
  TIPSY, Patchworks, or Woodstock stages).
- Initial granularity target is AU-level task partitioning; finer partitioning
  is optional and must preserve deterministic merge order.

2. Parity invariants (serial vs parallel):
- For the same run config/seed/input bundle, serialized outputs must match on:
  - `vdyp_curves_smooth-tsaXX.feather` row set and key columns,
  - generated model input bundle tables used downstream,
  - final export row counts for Patchworks/Woodstock.
- Numeric tolerance policy:
  - exact match for IDs/categorical fields,
  - floating values within configured tolerance (`abs <= 1e-6`) unless a
    tighter threshold is demonstrated stable.

3. Determinism invariants:
- Re-running parallel mode twice with identical inputs must produce equivalent
  hashes for normalized VDYP-stage outputs.
- Merge/reduction order must be explicit and stable (no nondeterministic
  concatenate/group-by output ordering).

4. Failure and fallback policy:
- Any worker failure must be surfaced with AU context and full traceback.
- Pipeline must support automatic fallback to serial mode (or explicit hard
  fail) based on one documented switch; no silent partial-success behavior.

5. Observability minimums:
- Long-running VDYP stages must emit periodic progress heartbeats including:
  - completed units / total units,
  - elapsed wall time,
  - current AU (or chunk identifier),
  - failure count.
- Manifest/log summary must include timing breakdown for serial vs parallel.

6. Performance gate:
- Demonstrate at least one meaningful speedup benchmark on a large TSA case
  without violating parity invariants.
- If speedup is negligible or unstable, keep feature opt-in and do not change
  default mode.

7. Rollout gate:
- Ship behind a feature flag first.
- Promote to default only after parity suite, benchmark evidence, and one full
  clean-slate TSA instance compile pass in production-like conditions.

## Completion criteria

Phase closes only when all are true:

- Snapshot baseline remains student-usable.
- Full compile + Patchworks branch validation is green in supported runtime.
- Woodstock export is generated from same compile and validated.
- ws3 smoke-test run is green with recorded evidence and sane output summary.

## Active Run Follow-Up Notes (Do Not Interrupt Current Run)

- Current monitored clean run reports stratum coverage near `0.656` with
  approximately 10 strata in the active cutoff.
- For the next TSA29 run, increase strata inclusion target to aim for coverage
  near `0.8` (preferred operational target), then compare downstream output
  sanity and runtime impact.
- This is queued as a next-run tuning change only; do not mutate parameters or
  restart the in-flight monitoring run.
- Phase 20 work remains explicitly deferred until TSA29 is stable enough for
  graduate-student handoff.
