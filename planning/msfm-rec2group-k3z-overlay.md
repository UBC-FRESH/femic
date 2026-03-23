# MSFM Rec2Group K3Z Overlay Plan

## Purpose

Define a clean, auditable workflow for importing a student-prepared GIS overlay
into the canonical K3Z instance and compiling four baseline-derived Patchworks
subvariants whose only intended change is fragment-level `RETENTION`.

This task is scoped only to the K3Z overlay work on branch
`feature/k3z-student-overlay`.

## Desired Outcome

Starting from the current K3Z baseline variant, produce four overlay
subvariants:

1. `basecase_riparian`
2. `basecase_sum`
3. `scenario1_sum`
4. `scenario2_sum`

Each subvariant should:

- use the same canonical K3Z fragments surface and baseline modeling inputs;
- differ only in the fragment `RETENTION` values imported from the student GIS
  layer;
- therefore change only the managed-vs-unmanaged area balance implied by those
  `RETENTION` values.

## Source Inputs

Canonical FEMIC repo root:

- `C:\Users\gep\projects\femic`

Known local planning input already available:

- `tmp/Fragments_Retention_HSmith.xls`

Canonical K3Z target surface to join against:

- `external/femic-k3z-instance`
- current K3Z instance fragments shapefile
- join key: `FEATURE_ID` on student layer -> `FEATURE_ID` on K3Z fragments

Student retention fields requested for import:

- `basecase_riparian`
- `basecase_sum`
- `scenario1_sum`
- `scenario2_sum`

## Working Assumptions

- The student GitHub fork is being abandoned, so runtime workflows should not
  depend on that fork remaining available.
- The uploaded `.xls` export is sufficient to validate field names and key
  presence even before the full GIS inventory copy is materialized in `tmp/`.
- The four requested retention columns are intended to replace or override the
  baseline fragment `RETENTION` field for four separate baseline-derived
  subvariants.
- No other baseline K3Z inputs should change for this task unless join-quality
  issues force a corrective follow-up.

## Immediate Constraint

The current repo venv does not have `xlrd`, so direct schema inspection of the
uploaded `tmp/Fragments_Retention_HSmith.xls` file is currently blocked from the
existing Python environment. That means workbook verification is the first
execution step once we either:

- install `.xls` reader support in the active environment, or
- receive/save the same export as `.xlsx` or CSV.

This does not block planning, but it does block claiming the field contract is
already verified.

## Observed Findings

- `xlrd` has now been installed in the repo venv, so the uploaded workbook is
  readable from the current environment.
- The uploaded workbook contains one sheet, `Fragment_Retention_HSmith`, with
  218 rows.
- The student export does not use the exact expected field names. The observed
  field mapping is:
  - `FEATURE_ID1` -> canonical `FEATURE_ID`
  - `Basecase_Riparian` -> `basecase_riparian`
  - `BaseCase_Sum` -> `basecase_sum`
  - `Scenario1_Sum` -> `scenario1_sum`
  - `Scenario2_Sum` -> `scenario2_sum`
- The four requested retention fields are present and complete (no nulls in the
  uploaded workbook/export).
- The published baseline Patchworks fragments shapefile does not carry
  `FEATURE_ID` directly. The practical join bridge is:
  - student workbook `FEATURE_ID1`
  - -> `models/k3z_patchworks_model/blocks/blocks.shp` `FEATURE_ID`
  - -> shared `BLOCK`
  - -> `output/patchworks_k3z_validated/fragments/fragments.shp`
- Join coverage is complete:
  - 218 student rows
  - 218 K3Z blocks rows
  - 218 baseline fragments rows
  - zero unmatched `FEATURE_ID`
  - zero unmatched `BLOCK`
  - zero nulls across the four target retention columns after normalization
- Repo-local normalized artifacts now exist at:
  - `tmp/k3z_student_overlay_retention_join.csv`
  - `tmp/k3z_student_overlay_retention_join.feather`
- Repo-local summary artifact now exists at:
  - `tmp/k3z_overlay_retention_summary.csv`

## Execution Plan

### 1. Verify student overlay schema and provenance

- Confirm the uploaded export contains `FEATURE_ID` and all four requested
  retention fields.
- Record where the authoritative student inventory copy comes from in the
  abandoned fork, then materialize a repo-local copy under `tmp/`.
- Note any mismatches between workbook/export field names and the names expected
  for the actual GIS layer import.

### 2. Materialize a repo-local overlay artifact

- Copy the relevant student GIS inventory artifact into `tmp/` so the workflow
  can proceed without live dependence on the abandoned fork.
- Prefer a format we can inspect and join reproducibly from the current FEMIC
  environment.
- Preserve enough provenance metadata to trace the import back to the student
  source.

### 3. Join student overlay data to canonical K3Z fragments

- Identify the actual K3Z fragments shapefile used by the current baseline
  Patchworks surface.
- Join the student overlay table/layer to that fragments surface on
  `FEATURE_ID`.
- Audit join coverage:
  - count matched features;
  - count unmatched student rows;
  - count unmatched fragment rows;
  - count null retention values in each of the four requested columns.

### 4. Define overlay subvariant contract

- Treat the current baseline variant as the parent surface.
- Create four subvariants, one per imported retention column.
- Keep all non-RETENTION baseline assumptions fixed:
  - same fragments geometry/set;
  - same baseline non-overlay fields;
  - same baseline tracks/PIN logic except where naming/wiring is required to
    expose the subvariant cleanly.

### 5. Implement baseline-derived overlay subvariants

- Add a clear naming scheme for the four subvariants so students know which
  imported retention field each one represents.
- Wire each subvariant so its fragment `RETENTION` comes from exactly one of:
  - `basecase_riparian`
  - `basecase_sum`
  - `scenario1_sum`
  - `scenario2_sum`
- Ensure the output surfaces remain directly comparable to the current baseline.

### 6. Validate and document

- Confirm the join is complete enough to support the intended teaching use.
- Compare managed/unmanaged area outcomes across the four subvariants.
- Document the import source, join key, subvariant meanings, and any known data
  caveats in the relevant K3Z runbook/docs surfaces.

## Deliverables

- repo-local planning note: `planning/msfm-rec2group-k3z-overlay.md`
- repo-local imported student overlay artifact(s) under `tmp/`
- joined K3Z fragments overlay workflow based on `FEATURE_ID`
- four baseline-derived K3Z overlay subvariants
- validation notes covering join coverage and RETENTION-field completeness
- documentation/runbook updates if the implementation changes student/operator
  workflow

## Risks To Watch

- `FEATURE_ID` coverage may be incomplete between the student layer and current
  canonical K3Z fragments.
- The `.xls` export may not perfectly mirror the real GIS layer schema.
- Some retention columns may contain nulls or values outside the expected
  `RETENTION` domain.
- If the existing baseline/variant wiring is incomplete or inconsistent, we may
  need a small contract cleanup before the overlay subvariants can launch
  cleanly.

## First Execution Step

Unblock schema verification for `tmp/Fragments_Retention_HSmith.xls`, confirm
`FEATURE_ID` plus the four requested retention fields, then pin the exact K3Z
fragments shapefile path that will serve as the canonical join target.

## Current Status

- Completed:
  - schema verification for the uploaded student export
  - normalized repo-local overlay import in `tmp/`
  - full 218/218 join validation via `FEATURE_ID` -> `BLOCK`
  - four overlay-specific fragments datasets
  - four overlay runtime configs
  - four overlay variant specs
  - four overlay PIN launch wrappers
  - four successful Patchworks matrix-builder runs
- Pending:
  - user-facing docs/runbook updates for the new overlay subvariants
  - any follow-up naming/UX cleanup after student review
  - confirm live Patchworks launch behavior after the shared flow-target script
    is switched from baseline-only account discovery to active-overlay account
    discovery

## Current Overlay Outputs

Overlay fragments datasets:

- `external/femic-k3z-instance/output/patchworks_k3z_overlay_basecase_riparian_validated/fragments/fragments.shp`
- `external/femic-k3z-instance/output/patchworks_k3z_overlay_basecase_sum_validated/fragments/fragments.shp`
- `external/femic-k3z-instance/output/patchworks_k3z_overlay_scenario1_sum_validated/fragments/fragments.shp`
- `external/femic-k3z-instance/output/patchworks_k3z_overlay_scenario2_sum_validated/fragments/fragments.shp`

Overlay runtime configs:

- `external/femic-k3z-instance/config/patchworks.runtime.overlay.basecase_riparian.windows.yaml`
- `external/femic-k3z-instance/config/patchworks.runtime.overlay.basecase_sum.windows.yaml`
- `external/femic-k3z-instance/config/patchworks.runtime.overlay.scenario1_sum.windows.yaml`
- `external/femic-k3z-instance/config/patchworks.runtime.overlay.scenario2_sum.windows.yaml`

Overlay Patchworks PIN entrypoints:

- `external/femic-k3z-instance/models/k3z_patchworks_model/analysis/overlay_basecase_riparian.pin`
- `external/femic-k3z-instance/models/k3z_patchworks_model/analysis/overlay_basecase_sum.pin`
- `external/femic-k3z-instance/models/k3z_patchworks_model/analysis/overlay_scenario1_sum.pin`
- `external/femic-k3z-instance/models/k3z_patchworks_model/analysis/overlay_scenario2_sum.pin`

Compiled tracks surfaces:

- `external/femic-k3z-instance/models/k3z_patchworks_model/tracks_overlay_basecase_riparian/`
- `external/femic-k3z-instance/models/k3z_patchworks_model/tracks_overlay_basecase_sum/`
- `external/femic-k3z-instance/models/k3z_patchworks_model/tracks_overlay_scenario1_sum/`
- `external/femic-k3z-instance/models/k3z_patchworks_model/tracks_overlay_scenario2_sum/`

## Validation Snapshot

Area summary relative to baseline (`tmp/k3z_overlay_retention_summary.csv`):

- baseline retained area: `89.065662 ha`
- `basecase_riparian` retained area: `164.305456 ha` (`+75.239794 ha` vs baseline)
- `basecase_sum` retained area: `379.898530 ha` (`+290.832868 ha` vs baseline)
- `scenario1_sum` retained area: `546.841710 ha` (`+457.776048 ha` vs baseline)
- `scenario2_sum` retained area: `622.819694 ha` (`+533.754032 ha` vs baseline)

## Follow-up Bugfix

- Live Patchworks launch confirmed that `overlay_basecase_riparian.pin`
  opens cleanly and respects the requested block-level retention behavior.
- `overlay_basecase_sum.pin` exposed a shared-target wiring bug rather than a
  bad overlay compile: Patchworks failed while defining
  `flow.even.product.Yield.managed.PLC`.
- Root cause:
  - the shared target script
    `models/k3z_patchworks_model/scripts/targets/flowTargets.bsh`
    was still hard-wired to `../tracks/accounts.csv`;
  - overlay wrapper PINs therefore read the baseline account list instead of the
    active overlay tracks account list;
  - `basecase_riparian` still carries managed `PLC`, so it launched by luck;
  - `basecase_sum`, `scenario1_sum`, and `scenario2_sum` legitimately drop
    managed `PLC`, so the stale baseline target list caused launch-time errors.
- Implemented fix:
  - `flowTargets.bsh` now resolves `accounts.csv` from the active
    `tracks_path_prefix` when a wrapper PIN supplies one, and falls back to
    baseline `../tracks/accounts.csv` only when no override is present.
- Expected consequence:
  - baseline and `basecase_riparian` behavior should remain unchanged;
  - `basecase_sum`, `scenario1_sum`, and `scenario2_sum` should now define flow
    targets only for the managed yield accounts that actually exist in their own
    overlay tracks surfaces.
