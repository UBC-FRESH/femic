# femic

[![DOI](https://zenodo.org/badge/430531073.svg)](https://zenodo.org/badge/latestdoi/430531073)

Hello!

## Documentation

Published docs (target URL): `https://ubc-fresh.github.io/femic/`

The docs are now split into:

- `Guides`: end-to-end workflow narrative recovered from legacy notebook text,
  with stage assumptions, QA interpretation, and troubleshooting playbooks.
- `Reference`: compact technical contracts plus CLI, API, and export/run-profile
  contracts.

If you want the shortest source-of-truth pages for repo invariants, instance
roots, external data, stage boundaries, and restart behavior, start with:

- `docs/reference/contracts/index.rst`

Legacy notebook narrative provenance is preserved in:

- `docs/guides/legacy-traceability.rst`
- `docs/guides/legacy_notebook_coverage.csv`

New case onboarding starters:

- `docs/guides/case-onboarding.rst`
- `instances/reference/config/run_profile.case_template.yaml`
- `instances/reference/config/tipsy/template.case.yaml`

## Developer Bootstrap (Fresh Clone)

For source-checkout development, use a repo-local virtual environment and
editable install:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements-dev.txt
```

This installs FEMIC in editable mode (`-e .`) plus development tools and
DataLad (`datalad[full]`).

The development extra also installs the optional FreshForge integration used
to validate and plan FEMIC model-build workflow graphs without executing FEMIC
stages. For a runtime install that only needs that integration, use
`femic[freshforge]`.

Then bootstrap annex-backed submodules and materialize real file content:

```bash
git submodule update --init --recursive
git annex version
datalad --version
git -C external/femic-public-data annex enableremote arbutus-s3
datalad get -r external/femic-public-data/data
```

Set the external data root for case preflight/runs:

```bash
export FEMIC_EXTERNAL_DATA_ROOT=$PWD/external/femic-public-data/data
```

Preflight before long runs:

```bash
femic prep validate-case --instance-root external/femic-k3z-instance --run-config config/run_profile.k3z.yaml
femic prep geospatial-preflight
```

FreshForge can inspect the plan-only K3Z model-build graph when FEMIC is
installed with the optional integration:

```bash
freshforge providers
freshforge validate examples/freshforge/k3z_model_build_workflow.yaml
freshforge plan examples/freshforge/k3z_model_build_workflow.yaml
```

FreshForge validation and planning do not run FEMIC stages, launch BTC,
launch Patchworks, read declared artifacts, or replace `femic instance rebuild`.

If `git annex version` fails, install `git-annex` at the OS level and re-open
the shell before retrying.

### Full Scripted Bootstrap

Linux/macOS:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements-dev.txt
python -m femic --help
ruff --version
mypy --version
pytest --version
pre-commit --version
sphinx-build --version
git annex version
datalad --version
git submodule update --init --recursive
git -C external/femic-public-data annex enableremote arbutus-s3
datalad get -r external/femic-public-data/data
export FEMIC_EXTERNAL_DATA_ROOT=$PWD/external/femic-public-data/data
femic prep validate-case --instance-root external/femic-k3z-instance --run-config config/run_profile.k3z.yaml
femic prep geospatial-preflight
```

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements-dev.txt
python -m femic --help
ruff --version
mypy --version
pytest --version
pre-commit --version
sphinx-build --version
git annex version
.venv\Scripts\datalad.exe --version
git submodule update --init --recursive
git -C external/femic-public-data annex enableremote arbutus-s3
.venv\Scripts\datalad.exe get -r external/femic-public-data/data
$env:FEMIC_EXTERNAL_DATA_ROOT="$PWD\external\femic-public-data\data"
femic prep validate-case --instance-root external/femic-k3z-instance --run-config config/run_profile.k3z.yaml
femic prep geospatial-preflight
```

If you are doing FEMIC work from VS Code/Cursor on Windows with a local Codex
agent and assistant-rendered file links are opening in the browser instead of
the editor, use the lab-maintained patch utility before fighting the IDE:

- `https://github.com/UBC-FRESH/codex-local-file-link-patch`

That repo includes agent-facing bootstrap notes plus a PowerShell patcher for
the recurring Windows `openai.chatgpt` local-file-link regression.

The canonical guide version of this bootstrap ritual lives in
`docs/guides/developer-environment-bootstrap.rst`.
The compact companion contract page is
`docs/reference/contracts/repo-runtime-invariants.rst`.
For local VS Code/Codex workflow guidance, including this Windows recovery
seam, see `docs/guides/vscode-coding-agent-onboarding.rst`.
If you are creating or publishing a new DataLad-managed FEMIC instance dataset
with an Arbutus special remote, use
`docs/guides/public-data-mirror-runbook.rst` as the canonical maintainer
runbook, especially on Windows.

## Bundled Example Instances Under `external/`

This checkout carries the published example instances as git submodules:

- `external/femic-k3z-instance`
- `external/femic-tsa29-instance`

Use them as the bundled runtime roots when you want to run, amend, or rebuild
the example cases from this FEMIC checkout.

Important rule of thumb:

- change FEMIC code/docs/tests in the parent repo;
- change example-instance configs, runbooks, and tracked case artifacts inside
  the submodule repo;
- if the bundled submodule should move to a new upstream commit, commit inside
  the submodule first, then commit the updated submodule pointer in FEMIC.

Typical amend/rebuild loop for K3Z from the FEMIC checkout:

Linux/macOS:

```bash
export FEMIC_EXTERNAL_DATA_ROOT=$PWD/external/femic-public-data/data
femic prep validate-case --instance-root external/femic-k3z-instance --run-config config/run_profile.k3z.yaml
femic prep geospatial-preflight
femic instance validate-spec --instance-root external/femic-k3z-instance --spec config/rebuild.spec.yaml
femic instance rebuild --instance-root external/femic-k3z-instance --spec config/rebuild.spec.yaml --baseline config/rebuild.baseline.json --allowlist config/rebuild.allowlist.yaml --run-config config/run_profile.k3z.yaml --run-id <run-id>
```

Windows PowerShell:

```powershell
$env:FEMIC_EXTERNAL_DATA_ROOT="$PWD\external\femic-public-data\data"
femic prep validate-case --instance-root external/femic-k3z-instance --run-config config/run_profile.k3z.yaml
femic prep geospatial-preflight
femic instance validate-spec --instance-root external/femic-k3z-instance --spec config/rebuild.spec.yaml
femic instance rebuild --instance-root external/femic-k3z-instance --spec config/rebuild.spec.yaml --baseline config/rebuild.baseline.json --allowlist config/rebuild.allowlist.yaml --run-config config/run_profile.k3z.yaml --run-id <run-id>
```

Review the rebuild report at:

- `external/femic-k3z-instance/vdyp_io/logs/instance_rebuild_report-<run-id>.json`

Then commit in the correct repository:

- local experiment only: leave the submodule working tree dirty;
- persistent instance change: commit inside `external/femic-k3z-instance` or
  `external/femic-tsa29-instance`;
- parent FEMIC update to a new bundled instance revision: commit the submodule
  pointer change in FEMIC after the submodule commit exists.

The source-of-truth guide for this workflow is
`docs/guides/deployment-instances.rst`.

## BC Data Catalogue Discovery

FEMIC now includes a first-pass BC Data Catalogue resolver for turning likely
TSR source-layer names into ranked catalogue matches, resource classifications,
and optional direct downloads.

Resolve a likely BCDC object name:

```powershell
& .\.venv\Scripts\python.exe -m femic data bcdc-resolve WHSE_FOREST_VEGETATION.F_OWN
```

Exercise the direct-download path when the top match exposes stable file
resources:

```powershell
& .\.venv\Scripts\python.exe -m femic data bcdc-resolve SITE_PROD_BC --download-direct --download-root data\downloads\bcdc --manifest-path runtime\logs\bcdc_site_prod_bc_manifest.json
```

For the fuller guide, classification buckets, and PowerShell quoting notes for
multi-word queries, see `docs/guides/bc-data-catalogue-discovery.rst`.

## CLI

Run the legacy pipeline through the FEMIC CLI: 

```bash
femic run --tsa 08 --resume
```

`femic run` executes the legacy script in an isolated subprocess and filters known
non-fatal shutdown noise lines from legacy stderr output.
Each run writes a manifest at `vdyp_io/logs/run_manifest-<run_id>.json` and uses
run-scoped VDYP log files (per TSA + run id).
For each TSA, raw VDYP process streams are also captured to:
`vdyp_io/logs/vdyp_stdout-tsa<tsa>-<run_id>.log` and
`vdyp_io/logs/vdyp_stderr-tsa<tsa>-<run_id>.log`.

### Quickstart (End-to-End)

1. Install package and initialize a deployment instance workspace:

```bash
python -m pip install femic
mkdir -p ~/femic-instance
cd ~/femic-instance
femic instance init
```

This scaffolds `config/`, `data/`, `output/`, and `vdyp_io/logs/` under the
current directory, and prompts to download standard BC VRI 2024 datasets.
Use `--no-download-bc-vri` to skip dataset download during bootstrap.

2. Validate base install:

```bash
femic --help
```

3. Validate TIPSY config handoff files:

```bash
femic tipsy validate --config-dir config/tipsy --tsa 08
```

4. Run one TSA with resume enabled:

```bash
femic run --tsa 08 --resume
```

5. Summarize VDYP diagnostics:

```bash
femic vdyp report
```

6. After manual BatchTIPSY output is uploaded, run downstream stages only (01b + bundle):

```bash
femic tsa post-tipsy --tsa 29 -v
```

This command writes a run manifest to ``vdyp_io/logs/`` (override with ``--log-dir`` and
``--run-id``).
When `data/ria_vri_vclr1p_checkpoint8.feather` is available, post-TIPSY bundle assembly also
adds species-proportion curves for all top-6 VRI species present in the selected TSA(s):
`untreated_species_prop_<SPP>` and `treated_species_prop_<SPP>` (single-point curves at `x=1`).

7. Export Patchworks starter package (ForestModel XML + fragments shapefile):

```bash
femic export patchworks --tsa k3z
```

By default this command reads bundle tables from `data/model_input_bundle/` and stand
geometry from `data/ria_vri_vclr1p_checkpoint7.feather`, then writes:
- `output/patchworks/forestmodel.xml`
- `output/patchworks/fragments/fragments.shp`

In the fragments shapefile, each row is one stand-fragment record. In the current
exporter, `BLOCK` is one-to-one with these fragment rows.

Patchworks XML now includes species-wise yield attributes derived as
`TotalVolume(age) * SpeciesProportion(age)` for unmanaged and managed tracks.
CC treatment minimum age is now resolved per AU as
`CMAI(managed_total_curve)-20` (clamped to `0..--cc-max-age`).
ForestModel feature attributes also include old-growth indicators for each AU
and totals:
- `feature.Area.og1.<au_id>` and `feature.Area.og1.total`
- `feature.Area.og2.<au_id>` and `feature.Area.og2.total`

`og1` ramps linearly from `0` at unmanaged-curve CMAI age to `1` at unmanaged
peak-yield age. `og2` is a policy-step indicator that snaps from `0` at age
`249` to `1` at age `250`.

If your checkpoint carries continuous THLB signal values (for example `thlb_raw`
in `[0, 1]`), you can tune managed/unmanaged assignment at export time:

```bash
femic export patchworks --tsa k3z --ifm-source-col thlb_raw --ifm-target-managed-share 0.8
```

To include seral-stage attributes in ForestModel output, provide a YAML config:

```bash
femic export patchworks --tsa k3z --seral-stage-config config/seral.k3z.yaml
```

With seral config enabled, export writes inventory-state accounts
(`feature.Seral.*`) plus CC-treatment consequence area accounts with AU/stage
specific labels (`product.Seral.area.<stage>.<au_id>.CC`).

8. (Optional) Run proprietary Patchworks Matrix Builder under Wine:

```bash
femic patchworks preflight --config config/patchworks.runtime.yaml
femic patchworks build-blocks --config config/patchworks.runtime.yaml
femic patchworks matrix-build --config config/patchworks.runtime.yaml
```

Runtime logs/manifests are written to `vdyp_io/logs/` with run-scoped names:
`patchworks_matrixbuilder_stdout-<run_id>.log`,
`patchworks_matrixbuilder_stderr-<run_id>.log`, and
`patchworks_matrixbuilder_manifest-<run_id>.json`.
Set both `SPS_LICENSE_SERVER` and `SPSHOME` (or define `patchworks.license_value`
and `patchworks.spshome` in `config/patchworks.runtime.yaml`). FEMIC preflight
validates runtime/config state only; Patchworks performs license-server checks
during launch.
On native Windows hosts, `femic patchworks` launches Patchworks directly via the
local `java` runtime (no Wine). Matrix-build completion is validated by expected
tracks output artifacts and fatal-log signatures rather than JVM exit code alone.
`femic patchworks build-blocks` creates a 1:1 stand:block dataset at
`<model>/blocks/blocks.shp` (with `BLOCK` copied from `FEATURE_ID`/`FRAGS_ID`)
and, by default, writes `<model>/blocks/topology_blocks_200r.csv` for PIN wiring.
The tracked teaching prototype model now lives in-repo at
`models/k3z_patchworks_model/`, and `config/patchworks.runtime.windows.yaml`
points to this location.

9. Export Woodstock compatibility CSV package:

```bash
femic export woodstock --tsa k3z
```

This currently writes:
- `output/woodstock/woodstock_yields.csv`
- `output/woodstock/woodstock_areas.csv`
- `output/woodstock/woodstock_actions.csv`
- `output/woodstock/woodstock_transitions.csv`

Developer note: the preferred source-checkout path is editable install
(`python -m pip install -r requirements-dev.txt`) so `femic` and
`python -m femic` work without `PYTHONPATH` hacks. If you intentionally skip
editable install, use `PYTHONPATH=src python -m femic ...`.

### Config-Driven Runs

Use a YAML/JSON profile to seed TSA selection and run modes:

```bash
PYTHONPATH=src python -m femic run --run-config instances/reference/config/run_profile.case_template.yaml
```

Profile schema and precedence are documented at `docs/reference/run-config.rst`.
`--run-config` values are merged with CLI options; explicit CLI values still win
for `--tsa`, `--debug-rows`, and `--run-id`.

Custom management-unit runs are also supported via run profile fields:
`selection.boundary_path`, `selection.boundary_layer`, and
`selection.boundary_code`. Example profile:
`config/run_profile.k3z.yaml` (North Island Community Forest test case).

Validate case prerequisites before long runs:

```bash
PYTHONPATH=src python -m femic prep validate-case --run-config instances/reference/config/run_profile.<case>.yaml
```

### Package Release Checks

Run package build/release-readiness checks locally:

```bash
python -m pip install build twine
scripts/release_package_checks.sh
```

For staged publication (TestPyPI then PyPI), use:
`docs/guides/pypi-release-runbook.rst`.

### Reproducibility Controls

Set deterministic VDYP sampling with:

```bash
export FEMIC_SAMPLING_SEED=42
```

Run manifests include:

- `runtime_versions` (tool/package versions)
- `runtime_parameters` (effective FEMIC env/runtime settings)
- `config_provenance` (`run_config_path`, `run_config_sha256`)
- `outputs` (`output_root`, `version_tag`, `versioned_output_dir`)

For faster debugging, limit the number of VRI rows processed (this disables cached checkpoints
and output reuse):

```bash
femic run --tsa 08 --resume --debug-rows 1000
```

You can override run metadata/log routing:

```bash
femic run --tsa 08 --resume --run-id mytest01 --log-dir vdyp_io/logs
```

If `--tsa` is omitted, defaults are loaded from `config/dev.toml` (`[run].default_tsa_list`).

Note: In debug mode, some strata may lack VDYP curves. These are skipped with a warning.
Rows whose strata do not map to an AU/curve (missing VDYP curves) are dropped with a warning
summary.
Debug mode also skips final TSA stand shapefile export by default; set
`FEMIC_SKIP_STANDS_SHP=0` to force shapefile output while debugging.
`ipyparallel` is disabled by default (`FEMIC_DISABLE_IPP=1`) for stability;
set `FEMIC_DISABLE_IPP=0` to re-enable controller-backed execution.
Row-wise operations default to pandas `.apply(...)`; set `FEMIC_USE_SWIFTER=1`
to opt back into swifter acceleration.

VDYP diagnostics are written to `vdyp_io/logs/` as JSONL files (e.g.,
`vdyp_runs.jsonl`, `vdyp_curve_events.jsonl`) to capture run status and curve-fit
warnings.
Summarize these logs with:

```bash
femic vdyp report
```

For regression checks in CI, apply warning-budget thresholds (command exits non-zero on breach):

```bash
femic vdyp report --max-curve-warnings 2 --max-first-point-mismatches 0 --min-curve-events 5 --min-run-events 6
```

Yield curves are anchored to a quasi-origin point `(1, 1e-6)` so downstream positive-value
filters can remain unchanged while avoiding zero-age intercept issues.

Raw BC datasets are expected under `../data` relative to your instance root
(for example, if you run from `instances/reference`, this resolves to
`data/bc/vri/2019/VEG_COMP_LYR_R1_POLY.gdb` at the workspace level). You can
override this by setting `FEMIC_EXTERNAL_DATA_ROOT` to a different base path.

## TIPSY Handoff Boundary

The TIPSY stage is currently a human-in-the-loop boundary:

1. Expert modeller derives TSA/AU-specific TIPSY parameter logic from TSR data packages.
2. FEMIC generates batch TIPSY input tables from that logic.
3. Batch TIPSY is run manually in Windows GUI.
4. Raw TIPSY output is copied back to Linux for automated downstream stages.

Draft config scaffolding for this handoff now lives in `config/tipsy/`:

- `config/tipsy/README.md`
- `config/tipsy/template.tsa.yaml`
- `config/tipsy/tsa08.yaml` and `config/tipsy/tsa16.yaml` (concrete TSA configs migrated from
  legacy logic)
- `config/tipsy/tsa24.yaml` (BEC-dependent branching migration from legacy logic)
- `config/tipsy/tsa40.yaml` and `config/tipsy/tsa41.yaml` (dynamic species-rank and
  forest-type-driven migrations)

If a TSA config file exists at `config/tipsy/tsaXX.yaml` (or `.yml`), the legacy
run path now prefers that config for TIPSY parameter generation for that TSA.
Override the config directory with `FEMIC_TIPSY_CONFIG_DIR`.
If no config exists for a requested TSA, the run now fails fast unless
`FEMIC_TIPSY_USE_LEGACY=1` is set.

Validate TIPSY config handoff files before running:

```bash
femic tipsy validate --config-dir config/tipsy --tsa 08 --tsa 16
```

Config-driven TIPSY rules now also support deterministic weak-mapping controls:

- `species_code_overrides` (for example `DR: FD`, `SX: SW`)
- `siteprod_si_fallback_by_species` (species-specific SI fallback values when siteprod
  values are missing/invalid)

## Patchworks Runtime Boundary

Patchworks software binaries are proprietary and must be supplied locally by users;
the repository ignores `reference/Patchworks/` by default and does not publish these
runtime assets.

VDYP fit diagnostics also emit per-stratum L/M/H comparison overlays at:
`plots/vdyp_lmh_tsa<tsa>-<stratum>-<stratum_code>.png`.
