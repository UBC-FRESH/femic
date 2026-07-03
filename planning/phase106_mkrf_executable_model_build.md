# P106 MKRF Executable FreshForge Model-Build Acceptance

P106 promotes the MKRF model-build workflow into the second executable
FreshForge acceptance lane after TFL6. The workflow runs from the parent FEMIC
checkout and uses generic `femic.*` provider stages plus the instance-owned
`mkrf.*` provider namespace.

The first implementation requirement is compatibility with released FreshForge.
The MKRF adapter still carries the older branch-era execution surface
(`execute_node`, `ProviderExecutionResult`, and tests importing
`ExecutionContext` / `execute_workflow`). P106 refreshes that adapter to
`run_node`, `ProviderRunResult`, `RunStatus`, and
`freshforge.execution.run_workflow`.

The MKRF workflow remains owned by the instance repository:
`external/femic-mkrf-instance/workflows/freshforge/mkrf_model_build_workflow.yaml`.
All `instance_root` parameters should be parent-checkout paths:
`external/femic-mkrf-instance`. Workflow-owned run config, source data,
Patchworks config, model package, runtime, and artifact paths remain
instance-relative.

`rebuild_spec` validation is not embedded in the first FreshForge node.
Operators should run the separate pre-run check:

```powershell
python -m femic instance validate-spec --instance-root external/femic-mkrf-instance --spec config/rebuild.spec.yaml
```

Acceptance requires validation, planning, and a real `freshforge run` from the
parent checkout:

```powershell
freshforge run external/femic-mkrf-instance/workflows/freshforge/mkrf_model_build_workflow.yaml --workdir runtime/freshforge --namespace mkrf/model-build --json
```

Before closeout, inspect the FreshForge record, MKRF runtime manifests,
ForestModel XML, fragments, tracks, Matrix Builder manifest, MKRF Git status,
and the `arbutus-s3` availability audit for required model/source paths.
