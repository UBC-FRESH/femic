# Phase 104: FreshForge Workflow Discovery

P104 adds a small generic discovery layer for FreshForge workflow documents
that already live in the FEMIC checkout or checked-out instance submodules.
The goal is user entry, not new execution semantics.

The discovery helper scans workflow documents:

- `examples/freshforge/*workflow.yaml`
- `external/*/workflows/freshforge/*workflow.yaml`

Overlay/config YAML files in the same directories are intentionally not listed
as workflows.

The implementation must stay generic. It must not hardcode example instance
names or require MKRF, TFL6, K3Z, TSA29, or any future instance to exist.
Instance-specific workflow documents remain owned by instance repositories.

The CLI entry point is:

```powershell
python -m femic freshforge workflows list
python -m femic freshforge workflows list --json
python -m femic freshforge workflows commands PATH
```

The `commands` helper prints released FreshForge CLI commands:

```powershell
freshforge validate PATH
freshforge inspect PATH
freshforge plan PATH
freshforge run PATH --workdir runtime/freshforge --namespace NAME --json
```

The suggested namespace is derived from the workflow file name. For example,
`foo_model_build_workflow.yaml` becomes `foo/model-build`, and
`foo_materialization_workflow.yaml` becomes `foo/materialization`.

P104 does not add new providers, change workflow YAML schemas, run workflows,
or route command outputs differently. P105 should use this discovery surface as
the user entry point before promoting the TFL6 model-build workflow into a full
executable acceptance lane.
