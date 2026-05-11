# Phase 69: TSA29 Patchworks Rebuild on the New THLB and Yield Surfaces

## Governing Issue and Branches

- Instance issue: `UBC-FRESH/femic-tsa29-instance#6`
- Parent branch: `feature/tsa29-patchworks-rebuild-new-inputs`
- Instance branch: `feature/tsa29-patchworks-rebuild-new-inputs`

## Contract

This lane rebuilds the TSA29 Patchworks-facing model package on top of the
currently accepted upstream inputs:

- the locked TSA29 THLB chain through row 23; and
- the accepted smoothed VDYP plus refreshed TIPSY yield surfaces.

The rebuild must not silently drop surviving AFLB area that falls past the
direct top-N AU selection surface.

## Critical Requirement

Past-top-N strata must still receive deterministic AU assignment. If the direct
selection surface does not cover all surviving AFLB area, use the
lexicographical stratum-matching imputation logic so no remaining modeled area
is left without an AU by accident.

## Planned Execution Shape

### P69.1

Initialization is in progress:
- issue opened;
- parent/instance feature branches created; and
- the remaining initialization task is to keep the lexicographical-imputation
  requirement explicit in the planning and implementation surfaces.

### P69.2

Expected implementation bundle:
- regenerate the TSA29 model-input bundle from the current locked THLB and
  accepted curve surfaces;
- rebuild the TSA29 Patchworks package on that regenerated bundle;
- apply/verify lexicographical AU imputation for past-top-N strata if needed;
- inspect the rebuilt Patchworks-facing outputs directly.

### P69.3

Expected validation/publication bundle:
- run the necessary Patchworks-facing validation checks;
- update docs/evidence only if the rebuilt package is accepted; and
- close the issue and publish the resulting branch/PR state.
