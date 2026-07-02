# Phase 103: TSA29 FreshForge Materialization Overlay

## Purpose

P103 adds TSA29 as the fourth real acceptance case for the reusable
`femic.materialization` FreshForge provider. Unlike K3Z, TSA29 is a
DataLad/git-annex dataset with an `arbutus-s3` special remote, so the workflow
uses the annex-enabled materialization path.

## Scope

The first TSA29 overlay targets the parent FEMIC checkout with TSA29 mounted at
`external/femic-tsa29-instance`.

It materializes the launch-critical and rebuild-facing published package
surfaces needed for the current TSA29 alpha snapshot:

- `models/tsa29_patchworks_model/blocks`
- `models/tsa29_patchworks_model/tracks`
- `models/tsa29_patchworks_model/analysis`
- `output/patchworks_tsa29_validated`
- `config`
- `workflows`

The overlay installs the parent FEMIC package with `dev` and `freshforge`
extras, then installs the TSA29 instance package editable so TSA29-owned FEMIC
extension entry points are available after bootstrap.

## Non-Goals

P103 does not materialize the whole TSR/THLB reconstruction stack, run the
strict locked-chain pipeline, rerun THLB recipes, regenerate model inputs, or
change TSA29 scientific/runtime behavior. Those are separate analytical
workflow phases.

## Acceptance

P103 is accepted when:

- the TSA29 overlay and workflow are tracked under
  `external/femic-tsa29-instance/workflows/freshforge/`;
- parent-checkout `freshforge validate`, `inspect`, and `plan` pass;
- a bounded parent-checkout `freshforge run --workdir runtime/freshforge
  --namespace tsa29/materialization --json` succeeds;
- `git annex find --not --in arbutus-s3 -- <audit paths>` reports no required
  payload gaps; and
- run reports remain ignored under `runtime/freshforge/`.
