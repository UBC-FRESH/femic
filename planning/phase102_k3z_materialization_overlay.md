# Phase 102: K3Z FreshForge Materialization Overlay

## Purpose

P102 adds K3Z as the third acceptance case for the reusable
`femic.materialization` FreshForge provider. The goal is to prove that the
provider can cover both DataLad/git-annex model instances and plain-git
teaching snapshots without instance-specific code in FEMIC core.

## Storage Mode

K3Z is currently a plain-git snapshot. It does not carry a DataLad dataset
configuration, an annex special remote, or annex-backed payloads. Its README
explicitly treats the current payload size as suitable for plain git, with
future LFS/DataLad migration left as a separate decision.

P102 therefore adds a generic overlay field:

```yaml
annex:
  enabled: false
```

When annex is disabled, the shared materialization provider keeps the workflow
shape stable but changes behavior:

- `init_annex`, `enable_special_remote`, and `audit_annex_availability` return
  deterministic no-op success results explaining that annex is disabled.
- `materialize_paths` verifies that configured paths exist in the working tree
  instead of running `datalad get`.
- The behavior remains generic; FEMIC core does not name K3Z or any
  `external/femic-*-instance` path in provider code.

## K3Z Overlay Scope

The K3Z workflow targets the parent FEMIC checkout with K3Z mounted as
`external/femic-k3z-instance`.

Initial overlay values:

- `instance.root`: `external/femic-k3z-instance`
- `instance.submodule_path`: `external/femic-k3z-instance`
- `environment.venv_path`: `.venv`
- install extras: `dev`, `freshforge`
- install editable paths: `external/femic-k3z-instance`
- `annex.enabled`: `false`
- materialization paths: `models`, `config`, `data`, `docs`, `workflows`
- audit paths: same as materialization paths
- report path: `runtime/freshforge/k3z_materialization_report.json`

## Validation

P102 is accepted when:

- the parent provider tests cover both annex-enabled and annex-disabled
  overlays;
- K3Z `freshforge validate`, `inspect`, and `plan` succeed from the parent
  checkout;
- K3Z `freshforge run --workdir runtime/freshforge --namespace
  k3z/materialization --json` succeeds and writes only ignored runtime output;
- the K3Z docs describe that plain-git materialization does not enable
  `arbutus-s3` or run `datalad get`.
