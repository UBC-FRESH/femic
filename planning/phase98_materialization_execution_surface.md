# P98.3 Materialization Execution Surface

## Decision

P98.4 should implement materialization as a FEMIC-owned optional FreshForge
provider namespace. The first implementation home is FEMIC because the target
workflow is specifically a FEMIC model-instance bootstrap and materialization
ritual: Git submodules, repo-root Python environment, FEMIC/FreshForge
installation, DataLad, git-annex, special remote enablement, targeted payload
materialization, and audit reporting.

The provider must remain generic and config-driven. It must not hardcode MKRF,
TFL6, TSA29, K3Z, or any `external/femic-*-instance` path. Instance repositories
own small overlay YAML files; FEMIC owns the reusable mechanics.

If the provider later proves broadly useful outside FEMIC model instances, the
node vocabulary can be moved upstream into FreshForge. That is an extraction
path, not the P98.4 starting point.

## Planned Provider Shape

Use provider id `femic.materialization`. Implement the provider in
`femic.freshforge_materialization` and expose it through the entry point
`femic.materialization = femic.freshforge_materialization:provider_factory`.
This keeps it separate from `femic.freshforge` model-build stages so
model-build execution and materialization bootstrap do not become one mixed
provider.

FreshForge `validate`, `inspect`, and `plan` remain non-mutating. Only
`freshforge run` performs materialization actions.

Planned node types:

1. `check_toolchain`
2. `check_python_environment`
3. `install_packages`
4. `init_submodules`
5. `init_annex`
6. `enable_special_remote`
7. `materialize_paths`
8. `audit_annex_availability`
9. `write_materialization_report`

## Overlay Contract

Instance overlays should be YAML documents supplied by a workflow node
parameter. The first contract should support:

- `instance_root`: path to the model instance root;
- `submodule_path`: optional path from the parent repo to the instance;
- `venv_path`: repo-root or caller-selected virtual environment path;
- `install`: FEMIC extras, FreshForge requirement, and optional editable
  instance package paths;
- `annex`: special remote name, defaulting to `arbutus-s3`;
- `materialization`: required `datalad get` or `git annex get` paths;
- `audit`: required paths or path families that must be present locally after
  materialization; and
- `report`: output path for the user-facing materialization report.

The overlay can include instance-specific values, but the provider code must
only interpret generic fields.

## Bootstrap Boundary

FreshForge cannot run a workflow until enough Python packaging exists to import
FreshForge and FEMIC. A tiny future bootstrap helper may install the minimum
runner dependencies, but it should not duplicate the deterministic
materialization ritual. The durable procedure belongs in the FreshForge
workflow and the overlay, not in per-instance prose or a bespoke one-off
script.

## P98.4 Handoff

P98.4 should implement:

- the FEMIC materialization provider and entry point;
- overlay parsing and broad validation;
- mocked command execution for each node type;
- deterministic report data;
- fixture workflow tests for `validate`, `inspect`, `plan`, and `run`; and
- clear failure diagnostics for missing tools, missing provider dependencies,
  special remote enablement failures, materialization failures, and failed
  annex availability audits.

The first real instance proof should be a later TFL6 phase with a TFL6-owned
overlay. MKRF and TSA29 overlays should follow once the generic path is proven.
