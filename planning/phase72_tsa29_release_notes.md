# Phase 72: Publish the TSA29 `v1.0.0-alpha1` Release

## Governing Issue

- Instance issue: `UBC-FRESH/femic-tsa29-instance#8`

## Release Intent

Cut `v1.0.0-alpha1` for `femic-tsa29-instance` as the first standalone TSA29
release where the rebuilt Patchworks package:

- uses the locked row-23 THLB surface;
- uses the accepted smoothed VDYP plus refreshed TIPSY yield surfaces;
- rebuilds cleanly through export, block build, and Matrix Builder;
- launches successfully; and
- produces a representative smoke scenario with sane output.

## Current Gate

Do not cut the release from an unmerged feature branch. The release boundary is:

1. merge the TSA29 Phase 71 review PRs:
   - `UBC-FRESH/femic-tsa29-instance#7`
   - `UBC-FRESH/femic#195`
2. refresh the local TSA29 instance checkout to merged `main`
3. verify the merged release-candidate surfaces directly
4. publish `v1.0.0-alpha1` as a GitHub pre-release

Current status:

- `#7` merged
- `#195` merged
- parent `main` now pins the merged TSA29 instance `main` commit

## Evidence Basis

Current evidence supporting the release idea:

- rebuilt TSA29 Patchworks package on the locked row-23 THLB surface
- successful Matrix Builder run on the rebuilt package
- successful headless launch smoke on `analysis/base.pin`
- accepted interactive scenario evidence in:
  - `external/femic-tsa29-instance/evidence/patchworks_test01_scenario_20260606.md`

The accepted `test01` evidence note records a managed harvest band of roughly
`1.4` to `1.6 million m3/year`, which is close to the published Williams Lake
TSA public-discussion mid-term reference values.

## Planned Execution Shape

### P72.1

- merge the active TSA29 Phase 71 review PRs
- refresh the release-facing wording in the TSA29 docs/notes
- keep the alpha boundary explicit

Current progress:

- merged:
  - `UBC-FRESH/femic-tsa29-instance#7`
  - `UBC-FRESH/femic#195`
- re-anchored both repos on `main`
- updated the parent `main` submodule pointer so the parent now pins the
  merged TSA29 instance `main` commit
- refreshed the TSA29 release-facing wording so the docs now treat
  `v1.0.0-alpha1` as the active intended milestone and explicitly frame it as
  an alpha-quality research/prototype release

### P72.2

- verify the merged release-candidate instance state on `main`
- confirm the intended DataLad/annex publication state for launch-critical
  payloads
- create the `v1.0.0-alpha1` tag and GitHub pre-release
- record the release in the parent planning/changelog surfaces
