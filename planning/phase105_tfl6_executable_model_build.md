# Phase 105: TFL6 Executable FreshForge Model-Build Acceptance

## Purpose

P105 promotes the existing TFL6 FreshForge model-build workflow from a
validate/inspect/plan contract into the first executable parent-checkout model
build acceptance lane. The acceptance target is a full `freshforge run` through
the generic FEMIC provider stages and Patchworks Matrix Builder.

## Boundary

- The workflow document remains owned by the TFL6 instance repository.
- FEMIC core keeps only generic `femic.*` FreshForge provider stages.
- No `tfl6.*` provider is added in this phase.
- FreshForge schema and execution semantics are unchanged.
- Materialization remains a prerequisite workflow family; P105 assumes the TFL6
  submodule has already been materialized enough to run model-build commands.

## Execution Shape

The workflow should be run from the parent FEMIC checkout:

```powershell
freshforge run external/femic-tfl6-instance/workflows/freshforge/tfl6_model_build_workflow.yaml --workdir runtime/freshforge --namespace tfl6/model-build --json
```

The workflow nodes continue to use generic provider references:

- `femic.validate_case`
- `femic.geospatial_preflight`
- `femic.accepted_btc_handoff`
- `femic.btc_post_tipsy`
- `femic.export_patchworks`
- `femic.patchworks_preflight`
- `femic.matrix_build`

The TFL6 workflow must use `instance_root: external/femic-tfl6-instance` so the
same document works from the parent checkout. Run config, Patchworks config,
bundle, checkpoint, output, log, and artifact paths stay instance-relative
because the FEMIC CLI resolves them against `instance_root`.

P105 uses the accepted TFL6 BTC handoff artifacts recorded in the instance
run profile and planning surfaces. It does not regenerate production TIPSY
parameter rules from raw upstream inputs. The accepted-handoff node checks the
declared BTC input/output and treated-curve artifacts before the workflow
continues to `femic.btc_post_tipsy`.

## Pre-Run Checks

Before the executable run, operators should use P104 workflow discovery and
non-mutating FreshForge checks:

```powershell
python -m femic freshforge workflows list
python -m femic freshforge workflows commands external/femic-tfl6-instance/workflows/freshforge/tfl6_model_build_workflow.yaml
freshforge validate external/femic-tfl6-instance/workflows/freshforge/tfl6_model_build_workflow.yaml
freshforge inspect external/femic-tfl6-instance/workflows/freshforge/tfl6_model_build_workflow.yaml
freshforge plan external/femic-tfl6-instance/workflows/freshforge/tfl6_model_build_workflow.yaml
```

Rebuild-spec validation remains a separate pre-run FEMIC check:

```powershell
python -m femic instance validate-spec --instance-root external/femic-tfl6-instance --spec config/rebuild.spec.yaml
```

## Acceptance Evidence

P105 is complete only after the executable run finishes and the rebuilt output
surface is inspected directly:

- FreshForge run record under parent `runtime/freshforge/`.
- FEMIC runtime manifests under
  `external/femic-tfl6-instance/runtime/logs/`.
- Exported Patchworks package under
  `external/femic-tfl6-instance/output/patchworks_tfl6_mp11_harvest_system_candidate/`.
- Matrix Builder manifest.
- Compiled tracks under
  `external/femic-tfl6-instance/models/tfl6_patchworks_model_mp11_harvest_system_candidate/tracks`.
- TFL6 Git status after execution.

Tracked model-output changes are reviewable rebuild output. They should be
committed only when expected and validated.

## Acceptance Result

The parent-checkout acceptance run completed on 2026-07-02 with:

- `freshforge run ... --workdir runtime/freshforge --namespace tfl6/model-build --json`
  returning `ok: true`;
- all seven workflow nodes succeeding;
- BTC sub-run id `tfl6_freshforge_model_build_tfl6`;
- Matrix Builder manifest `returncode: 0`;
- `accounts_sync.status: synced`;
- Patchworks export rebuilt under
  `external/femic-tfl6-instance/output/patchworks_tfl6_mp11_harvest_system_candidate/`;
- compiled tracks rebuilt under
  `external/femic-tfl6-instance/models/tfl6_patchworks_model_mp11_harvest_system_candidate/tracks`;
- no invalid combined TSA/TFL matches remaining in the source/test/TFL6
  workspace search.

The run intentionally uses the accepted BTC input CSV and accepted BatchTIPSY
output. It does not require or regenerate the legacy TIPSY parameter
spreadsheet.
