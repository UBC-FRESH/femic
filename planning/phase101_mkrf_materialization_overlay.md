# P101 MKRF FreshForge Materialization Overlay

P101 adds the second real model-instance materialization workflow using the
generic `femic.materialization` FreshForge provider. TFL6 proved the parent
checkout pattern first; MKRF proves the same provider contract can bootstrap an
instance that also owns an editable FreshForge adapter package.

The workflow targets commands run from the parent FEMIC checkout with MKRF at
`external/femic-mkrf-instance`. MKRF supplies only overlay values and workflow
composition. FEMIC core still owns the generic materialization provider, and
MKRF-specific model-build orchestration remains in the MKRF instance package.

The MKRF overlay materializes `models`, `config`, `workflows`, and
`data/source`, then audits `models` and `data/source` against `arbutus-s3`.
The package install step installs `.[dev,freshforge]` from the parent checkout
and installs `external/femic-mkrf-instance` editable so later FreshForge
commands can discover the `mkrf` provider.

Validation targets:

- `freshforge providers --json`
- `freshforge validate external/femic-mkrf-instance/workflows/freshforge/mkrf_materialization_workflow.yaml --json`
- `freshforge inspect external/femic-mkrf-instance/workflows/freshforge/mkrf_materialization_workflow.yaml --json`
- `freshforge plan external/femic-mkrf-instance/workflows/freshforge/mkrf_materialization_workflow.yaml --json`
- `freshforge run external/femic-mkrf-instance/workflows/freshforge/mkrf_materialization_workflow.yaml --workdir runtime/freshforge --namespace mkrf/materialization --json`
- `git -C external/femic-mkrf-instance annex find --not --in arbutus-s3 -- models data/source`

P101 also corrects stale MKRF FreshForge model-build examples that still used
branch-era `--run-id` and `--report` flags. Released FreshForge uses
`--workdir`, `--namespace`, and `--json`; `freshforge plan` is the non-mutating
preview.
