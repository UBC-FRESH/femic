# Rebuild Runbook (Instance Placeholder)

Use this file as the operator-facing rebuild procedure for this instance.

## Required Inputs
- `config/run_profile.<case>.yaml`
- `config/rebuild.spec.yaml`
- `config/rebuild.allowlist.yaml`
- Any case-specific runtime prerequisites (for example Patchworks licensing/runtime).

## Standard Rebuild Commands
```bash
femic instance validate-spec --spec config/rebuild.spec.yaml
femic instance rebuild \
  --spec config/rebuild.spec.yaml \
  --baseline config/rebuild.baseline.json \
  --allowlist config/rebuild.allowlist.yaml
```

## Evidence to Archive
- `runtime/logs/instance_rebuild_report-<run_id>.json`
- Referenced manifests/logs listed under `artifact_references`.

## Evidence Refresh Step (Release Prep)
```bash
femic instance refresh-reference-evidence --reference-root .
```
After refresh, verify:
- `evidence/reference_rebuild_report.latest.json` exists,
- `status` is `ok`,
- `regression_gate` booleans are all false.

## Local Notes
- Document case-specific overrides, expected warnings, and accepted deltas here.

## Species-Surface Diagnostics (When Total Looks OK but Species Look Empty)
```bash
  femic instance account-surface \
  --config config/patchworks.runtime.windows.yaml \
  --output runtime/logs/account_surface-<run_id>.json
```
After running, verify in the JSON/report:
- `diagnosis.total_ok_species_empty_signature` is `false`.
- If `true`, follow `diagnosis.recommended_next_checks` before changing allowlists.
