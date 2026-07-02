# P100 TFL6 FreshForge materialization overlay

P100 is the first real instance materialization workflow that uses the generic
FEMIC `femic.materialization` FreshForge provider. The acceptance case is the
parent FEMIC checkout with TFL6 mounted as `external/femic-tfl6-instance`,
because that is the workflow that has been failing for new users.

The TFL6 repository owns the overlay and workflow documents. FEMIC owns the
generic provider only. The workflow should initialize the TFL6 submodule,
validate the parent `.venv` and editable FEMIC/FreshForge install, enable the
TFL6 `arbutus-s3` annex remote, materialize the tracked model/config/workflow
payloads, audit `models/` remote coverage, and write a local FreshForge report.

The first overlay is intentionally parent-checkout oriented, not a standalone
TFL6-only clone contract. Standalone instance materialization can be added
later once this parent-submodule workflow is stable.

Validation surfaces:

- `freshforge providers --json`
- `freshforge validate external/femic-tfl6-instance/workflows/freshforge/tfl6_materialization_workflow.yaml --json`
- `freshforge inspect external/femic-tfl6-instance/workflows/freshforge/tfl6_materialization_workflow.yaml --json`
- `freshforge plan external/femic-tfl6-instance/workflows/freshforge/tfl6_materialization_workflow.yaml --json`
- `freshforge run external/femic-tfl6-instance/workflows/freshforge/tfl6_materialization_workflow.yaml --workdir runtime/freshforge --namespace tfl6/materialization --json`

Runtime reports remain local/generated under `runtime/freshforge/` and must not
be tracked.
