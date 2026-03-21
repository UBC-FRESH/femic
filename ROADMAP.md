# Refactor Roadmap

## Phase 1: Stabilize Runtime + Inputs
- [x] P1.1 Stand up Typer CLI entrypoint (FHOPS-style, nemora-compatible)
  - [x] P1.1a Expose the `femic` console script (Forest Estate Model Input Compiler)
  - [x] P1.1b Create `src/femic/cli/main.py` with `Typer(add_completion=False, no_args_is_help=True)`
  - [x] P1.1c Organize subcommands (prep, vdyp, tsa, run) via `app.add_typer(...)`
  - [x] P1.1d Use module-level constants for defaults + typed `Path` args (avoid B008)
- [x] P1.2 Define a single entrypoint script with explicit CLI args
  - [x] P1.2a Add a `--tsa` filter and `--resume` flag
  - [x] P1.2b Centralize environment checks (VDYP, wine, data paths)
- [x] P1.3 Normalize I/O paths and required files
  - [x] P1.3a Document expected data layout under `data/` and `vdyp_io/`
  - [x] P1.3b Add validation for missing files before processing
- [x] P1.4 Improve logging and error visibility
  - [x] P1.4a Add structured logging with per-TSA context
  - [x] P1.4b Capture external tool stderr/stdout to files
- [x] P1.5 VDYP diagnostics + metadata hardening
  - [x] P1.5a Add VDYP Wine wrapper health checks (config, inputs, tmp outputs,
  exit codes)
  - [x] P1.5b Record VDYP run metadata + failure reasons per TSA and AU
  - [x] P1.5c Add curve-build diagnostics (binning stats, NLLS convergence,
  residuals)
  - [x] P1.5d Add ramp-splice diagnostics and iterative left-point trimming with warnings

## Phase 2: Modularize Pipeline Steps
- [x] P2.1 Extract reusable modules from `00_data-prep.py`
  - [x] P2.1a Split into `io.py`, `vdyp.py`, `tsa.py`, `plots.py`
  - [x] P2.1b Remove global state and pass explicit parameters
    - [x] P2.1b.1 Centralize 01a per-TSA VDYP cache-path templates in shared helper
    - [x] P2.1b.2 Replace residual 01a `os.path` cache checks with `Path(...).is_file()`
    - [x] P2.1b.3 Collapse 00->01a cache-path handoff to one resolved payload
    - [x] P2.1b.4 Reduce 01a `run_tsa(...)` signature by bundling remaining path/runtime args
    - [x] P2.1b.5 Introduce typed 01b runtime payload and explicit 00->01b path handoff
- [x] P2.2 Convert notebook logic into functions
  - [x] P2.2a Wrap major steps with clear inputs/outputs
  - [x] P2.2b Add a small orchestration layer for sequencing
  - [x] P2.2c Move 00_data-prep 01a/01b module-load + call loops behind shared stage helpers
- [x] P2.3 Add minimal tests for core helpers
  - [x] P2.3a Smoke tests for file validation and key transforms
  - [x] P2.3b Deterministic checks for small sample data

## Phase 3: Workflow Hardening
- [x] P3.1 Sphinx docs + GitHub Pages (FHOPS-style)
  - [x] P3.1a Add `docs/conf.py` with `sphinx_rtd_theme`, `nbsphinx`, `autosummary`
  - [x] P3.1b Add `docs/index.rst` + `docs/reference/cli.rst` mirroring CLI help
  - [x] P3.1c Add GitHub Pages workflow to build + publish `docs/_build/html`
- [x] P3.2 Nemora alignment prep
  - [x] P3.2a Map femic CLI commands to nemora task taxonomy
  - [x] P3.2b Identify shared utilities to upstream into nemora later
- [x] P3.3 Add config-driven runs
  - [x] P3.3a YAML/JSON config to select TSA, strata, and modes
  - [x] P3.3b Store run metadata and versioned outputs
- [x] P3.4 Make outputs reproducible
  - [x] P3.4a Seed randomness in bootstrap/sample paths
  - [x] P3.4b Record tool versions and runtime parameters
- [x] P3.5 Documentation + handoff
  - [x] P3.5a Update README with new workflow
  - [x] P3.5b Add a quickstart for running end-to-end

## Phase 4: Patchworks + Woodstock Export (femic.fmg)
- [x] P4.1 Patchworks requirements + source governance
  - [x] P4.1a Parse Patchworks user guide into a concrete implementation checklist
  - [x] P4.1b Add gitignore rules for proprietary reference PDFs (do not republish)
  - [x] P4.1c Document required ForestModel XML elements and fragments schema fields
- [x] P4.2 Port legacy `fmg` core to Python 3 under `src/femic/fmg/`
  - [x] P4.2a Port core model classes (`Curve`, `Treatment`, `ForestModel`, related XML nodes)
  - [x] P4.2b Preserve deterministic XML serialization behavior with fixture-based parity tests
  - [x] P4.2c Port Woodstock import/export helpers as a compatibility module
- [x] P4.3 Build femic-to-fmg adapters from current pipeline outputs
  - [x] P4.3a Map `curve_table`/`curve_points_table` into fmg curve objects
  - [x] P4.3b Map AU-to-stand assignments into feature/treatment strata bindings
  - [x] P4.3c Auto-create baseline CC treatment and default post-treatment transitions
- [x] P4.4 Generate Patchworks ForestModel XML
  - [x] P4.4a Add a writer stage that emits valid ForestModel XML for a compiled run
  - [x] P4.4b Add schema/structure validation checks and fail-fast diagnostics
  - [x] P4.4c Add CLI entrypoint(s) for export (`femic export patchworks ...`)
- [x] P4.5 Generate Patchworks fragments shapefile from BC VRI
  - [x] P4.5a Define canonical fragments field map (IDs/themes/area/treatment linkage)
  - [x] P4.5b Build shapefile writer with robust CRS/field-type/width handling
  - [x] P4.5c Join model themes/curve assignment attributes to stand geometries
- [x] P4.6 End-to-end validation and handoff
  - [x] P4.6a Validate patchworks package build on TSA29 and CFA K3Z test cases
  - [x] P4.6b Add regression tests for XML + fragments outputs
  - [x] P4.6c Update docs with a Patchworks-first workflow (Woodstock noted as secondary)

## Phase 5: Documentation Recovery + Expansion
- [x] P5.1 Inventory legacy notebook knowledge and map coverage gaps
  - [x] P5.1a Extract markdown-cell inventory from `00_data-prep.ipynb`,
    `01a_run-tsa.ipynb`, `01b_run-tsa.ipynb` with cell index + preview text
  - [x] P5.1b Build a coverage matrix: notebook knowledge item -> existing docs
    location (or gap)
  - [x] P5.1c Classify each item as assumptions, step intent, interpretation
    guidance, failure mode, or operator action
- [x] P5.2 Add a Guides documentation section (separate from Reference)
  - [x] P5.2a Create Guides toctree and wire it from docs landing page
  - [x] P5.2b Add pipeline narrative pages by stage and workflow milestone
  - [x] P5.2c Keep Reference pages API/CLI-oriented and move procedural content
    to Guides
- [x] P5.3 Re-author notebook narrative into structured guides (curated rewrite)
  - [x] P5.3a Stage 00 guide: data dependencies, preprocessing assumptions,
    checkpoint semantics
  - [x] P5.3b Stage 01a guide: strata construction, SI splits, VDYP fitting
    logic, TIPSY input boundary
  - [x] P5.3c Stage 01b guide: TIPSY output ingestion, overlays, QA interpretation
  - [x] P5.3d Bundle/export guide: `model_input_bundle` tables and
    Patchworks/Woodstock outputs
- [x] P5.4 Add operator QA and troubleshooting guidance
  - [x] P5.4a Add “what good looks like” checks for strata, fit diagnostics, and
    TIPSY-vs-VDYP overlays
  - [x] P5.4b Document common failure signatures and deterministic remedies
  - [x] P5.4c Add manual BatchTIPSY handoff checklist and fixed-width DAT caveats
- [x] P5.5 Preserve traceability to legacy notebooks
  - [x] P5.5a Add “Legacy Notebook Traceability” docs page with cell-index mapping
  - [x] P5.5b Record source notebook/cell provenance for major guide content
  - [x] P5.5c Mark intentionally retired legacy guidance explicitly
- [x] P5.6 Keep docs current with code and CLI
  - [x] P5.6a Add docs consistency checks for CLI command/options drift
  - [x] P5.6b Add docs acceptance tests for required guide pages and toctree visibility
  - [x] P5.6c Update changelog and roadmap notes for this docs milestone
- [x] P5.7 Publish and validate GitHub Pages output
  - [x] P5.7a Verify Guides navigation renders in published site
  - [x] P5.7b Validate direct URLs for all guide pages in deployed docs
  - [x] P5.7c Confirm docs workflow behavior for push/manual dispatch expectations

## Phase 6: Deployment Readiness and Case Onboarding
- [x] P6.1 Add reusable case onboarding template set
  - [x] P6.1a Add run-profile onboarding template for TSA and custom-boundary modes
  - [x] P6.1b Add TIPSY rule starter template for new case config files
  - [x] P6.1c Publish required-input and acceptance checklist in Guides
- [x] P6.2 Add one-command case preflight validation
  - [x] P6.2a Validate required paths/configs before long compile runs
  - [x] P6.2b Emit clear remediation messages for missing prerequisites
  - [x] P6.2c Add regression tests for success/failure preflight scenarios
- [x] P6.3 Add student-facing release packaging workflow
  - [x] P6.3a Emit versioned output bundle for training deployments
  - [x] P6.3b Add concise handoff notes with commands and QA expectations
  - [x] P6.3c Add acceptance checks for package completeness
- [x] P6.4 Add onboarding regression scenario tests
  - [x] P6.4a Add smoke case for new-case template instantiation
  - [x] P6.4b Validate template-driven run/profile compatibility
  - [x] P6.4c Add docs checks ensuring onboarding guide + templates remain linked

## Phase 7: Patchworks Runtime Integration + UBC VPN Licensing
- [x] P7.1 Protect proprietary Patchworks bundle in git
  - [x] P7.1a Add `.gitignore` entry for `reference/Patchworks/`
  - [x] P7.1b If already tracked, remove from index (`git rm --cached -r reference/Patchworks`)
  - [x] P7.1c Add docs note that users must provide local Patchworks install separately
- [x] P7.2 Add Patchworks runtime preflight checks (CLI)
  - [x] P7.2a Verify `wine64` exists
  - [x] P7.2b Verify `java` is callable inside Wine context
  - [x] P7.2c Verify `patchworks.jar` path and readability
  - [x] P7.2d Verify `SPS_LICENSE_SERVER` is set and parseable
  - [x] P7.2e Verify required model inputs exist (`forestmodel.xml`, `fragments.dbf`)
- [x] P7.3 Add deterministic Matrix Builder runner command
  - [x] P7.3a Add command builder for `ca.spatial.tracks.builder.Process` with 3 args
  - [x] P7.3b Add path translation (`/home/...` -> `Z:\\home\\...`) for Wine CMD
  - [x] P7.3c Capture stdout/stderr logs and return exit code
  - [x] P7.3d Add optional interactive launcher mode (`java -jar patchworks.jar`)
- [x] P7.4 Add UBC VPN connectivity workflow (host-pass-through primary)
  - [x] P7.4a Document host-side `openconnect myvpn.ubc.ca` flow (from uploaded PDF)
  - [x] P7.4b Add preflight checks to test license server reachability before run
  - [x] P7.4c Add troubleshooting for MFA suffixes (`@app`, `@phone`, optional pool)
  - [x] P7.4d Add fallback notes for in-container OpenConnect (only if tun/caps available)
- [x] P7.5 Add docs and operator runbook
  - [x] P7.5a Add step-by-step “Patchworks under Wine” guide
  - [x] P7.5b Add “VPN + licensing diagnostics” guide
  - [x] P7.5c Add known failure signatures and remedies
- [x] P7.6 Add regression and acceptance tests
  - [x] P7.6a Unit-test command assembly and path mapping
  - [x] P7.6b Unit-test env var injection and validation failures
  - [x] P7.6c Integration smoke test with mocked external calls
  - [x] P7.6d Docs contract tests for new guides and CLI docs

## Phase 8: K3Z Metadata + Student-Facing How-To Documentation Program
- [x] P8.1 Build a full metadata inventory and lineage record for K3Z
  - [x] P8.1a Catalog every source dataset feeding `data/`, `yield/`, and `blocks/`
  - [x] P8.1b Record transformation lineage from FEMIC bundle/checkpoints to model artifacts
  - [x] P8.1c Add provenance versioning policy for future model refreshes
- [x] P8.2 Publish a parameter/assumption registry for K3Z
  - [x] P8.2a Enumerate every operational default (IFM, seral, CC age, topology, horizon)
  - [x] P8.2b Map each parameter to its controlling file/CLI flag
  - [x] P8.2c Define acceptable ranges and risk notes for student edits
- [x] P8.3 Document component-to-function mapping for the full model
  - [x] P8.3a Map each directory/file to Patchworks runtime behavior
  - [x] P8.3b Add account/target traceability (`forestmodel.xml` -> tracks -> PIN targets)
  - [x] P8.3c Add map-layer and report-wiring traceability in `analysis/base.pin`
- [x] P8.4 Define a user edit-policy matrix (editable vs generated artifacts)
  - [x] P8.4a Mark "safe to edit", "regenerate", and "do not hand-edit" assets
  - [x] P8.4b Add regeneration runbooks for each generated artifact family
  - [x] P8.4c Add backup/recovery conventions for learner experiments
- [x] P8.5 Add scenario interpretation guidance for teaching use
  - [x] P8.5a Explain seral trajectory interpretation within and across scenarios
  - [x] P8.5b Explain treatment-shift interpretation using `product.Seral.area.*.*.CC`
  - [x] P8.5c Add report/table templates for classroom comparisons
- [x] P8.6 Expand "Sample Models/K3Z" docs to complete user-facing how-to coverage
  - [x] P8.6a Add end-to-end onboarding checklist for first-run users
  - [x] P8.6b Add failure-signature cookbook with deterministic remediation steps
  - [x] P8.6c Add change-management notes for collaborators extending the model
  - [x] P8.6d Roll regenerated strata/AU build plots into user-facing K3Z docs
- [x] P8.7 Add docs QA and acceptance checks for K3Z documentation completeness
  - [x] P8.7a Add contract tests for new Sample Models navigation/pages
  - [x] P8.7b Add required-section checks for K3Z metadata/how-to docs
  - [x] P8.7c Add a release-readiness checklist for student distribution

## Phase 9: Repository + Project Rebrand (`wbi_ria_yield` -> `femic`)
- [x] P9.1 Rebrand canonical project metadata and naming surface
  - [x] P9.1a Update visible project title strings (README/docs/CITATION) to `femic`
  - [x] P9.1b Add explicit transition note ("formerly `wbi_ria_yield`") where needed
  - [x] P9.1c Preserve historical provenance references in roadmap/changelog entries
- [x] P9.2 Update URL and publication endpoints to new repository slug
  - [x] P9.2a Update in-repo GitHub links to `github.com/UBC-FRESH/femic`
  - [x] P9.2b Update published docs URL references to `ubc-fresh.github.io/femic`
  - [x] P9.2c Validate GitHub Pages deployment behavior after rename cutover
- [x] P9.3 Remove hard-coded old-slug local path assumptions from runtime config
  - [x] P9.3a Replace `wbi_ria_yield` absolute path references with config-relative/env-driven paths
  - [x] P9.3b Revalidate Patchworks runtime preflight/build commands using updated paths
  - [x] P9.3c Add/adjust regression checks for path portability expectations
- [x] P9.4 Perform legacy-slug sweep and cleanup policy enforcement
  - [x] P9.4a Clear non-historical `wbi_ria_yield` references from source/docs/config
  - [x] P9.4b Define notebook output cleanup policy for stale absolute-path traces
  - [x] P9.4c Keep historical slug mentions only where audit trail requires them
- [x] P9.5 Execute cutover workflow and release validation
  - [x] P9.5a Start rebrand work on dedicated branch `feature/rebrand-femic`
  - [x] P9.5b Run full validation gates before merge
  - [x] P9.5c Confirm post-rename install/docs/CLI smoke checks

## Phase 10: Instance/Package Decoupling + PyPI Release Readiness
- [x] P10.1 Add first-class instance model + path resolution
  - [x] P10.1a Introduce `InstanceContext`/`instance_root` resolver
    (default: CWD, override via `--instance-root`/env).
  - [x] P10.1b Make CLI commands resolve defaults relative to instance root,
    not repo-root assumptions.
  - [x] P10.1c Keep transition compatibility (legacy root-coupled mode still
    works with warnings).
- [x] P10.2 Add instance bootstrap UX (`femic instance init`)
  - [x] P10.2a Add new CLI namespace `instance` with `init` command.
  - [x] P10.2b Scaffold filesystem-first instance skeleton (config/templates/log/output/data dirs + `.gitignore` + quickstart doc).
  - [x] P10.2c Ship template assets as package resources (not repo-root only files).
- [x] P10.3 Decouple runtime from repo-root legacy scripts
  - [x] P10.3a Move legacy stage scripts to package-owned resources and execute from package runtime.
  - [x] P10.3b Remove hard dependency on `<repo>/00_data-prep.py` style paths.
  - [x] P10.3c Add explicit migration/warning messages for old execution assumptions.
- [x] P10.4 Split case/deployment assets from generic project layout
  - [x] P10.4a Define canonical in-repo reference instance location (for maintainers), separate from package source.
  - [x] P10.4b Repoint docs/tests/examples to instance-based layout.
  - [x] P10.4c Enforce contract tests: no active runtime/docs/config references to repo-specific deployment paths.
- [x] P10.5 Publish-readiness completion criteria (PyPI in scope)
  - [x] P10.5a Add package build/release checks (`build`, `twine check`, wheel install smoke).
  - [x] P10.5b Verify installed-package workflow in clean env (`pip install femic` + `femic instance init` + preflight).
  - [x] P10.5c Final docs updates for “install package + create instance + run”.
- [x] P10.6 Public-data accessibility mirror via DataLad + submodule linkage
  - [x] P10.6a Inventory all "public but not directly downloadable" required layers
    (including archived HectaresBC `misc*.tif` dependencies) with provenance notes.
  - [x] P10.6b Create/publish a dedicated DataLad-backed GitHub dataset repo for
    these layers with remote object storage on Arbutus (special remote).
  - [x] P10.6c Add the published dataset repo as a Git submodule under FEMIC and
    wire docs/instance bootstrap guidance to consume it.
  - [x] P10.6d Add operator runbook for clone/get/update workflows
    (`git submodule` + `datalad get`) for students/collaborators.

## Phase 11: K3Z Example Instance Repository (Standalone + Linked)
- [x] P11.1 Define K3Z example-instance repository contract
- [x] P11.2 Assemble and validate K3Z instance payload
- [x] P11.3 Publish `UBC-FRESH` public K3Z repo
- [x] P11.4 Link K3Z repo into FEMIC as submodule + docs wiring
- [x] P11.5 Add contract checks + acceptance validation

## Phase 12: Relocated K3Z Rebuild Validation + Standalone Docs Program
- [x] P12.1 Revalidate relocated K3Z Patchworks compile flow on Windows
  - [x] P12.1a Add/track an instance-local Patchworks runtime config in
    `external/femic-k3z-instance/config/` with paths resolved to the relocated
    K3Z workspace layout.
  - [x] P12.1b Run `femic patchworks preflight`, `build-blocks`, and
    `matrix-build` against the relocated model instance.
  - [x] P12.1c Capture and archive run evidence (stdout/stderr/manifest plus
    key output artifact timestamps) for reproducibility.
- [x] P12.2 Verify bugfixes and check regressions after rebuilt tracks
  - [x] P12.2a Confirm `FD -> FDC` treated species mapping remains correct in
    rebuilt K3Z outputs (no nonzero-source collapse to zero).
  - [x] P12.2b Compare rebuilt `tracks/*.csv` structural invariants against
    known-good baseline (row counts, account counts, key account names).
  - [x] P12.2c Add regression checks/scripts for K3Z compile invariants so
    future rebuilds fail fast on behavior drift.
  - [x] P12.2d Investigate `PL` vs `PLC` species-account semantics in K3Z;
    if `PL` is not a valid active species in current inputs, trim `PL` from
    generated accounts/targets/docs to prevent student-facing false alarms.
- [x] P12.3 Stand up standalone Sphinx docs in `femic-k3z-instance`
  - [x] P12.3a Add docs scaffold (`docs/`, `conf.py`, `index.rst`,
    docs requirements, `.readthedocs.yaml`, and docs publish workflow).
  - [x] P12.3b Publish docs for `femic-k3z-instance` and verify external URLs.
  - [x] P12.3c Add docs acceptance checks for required sections and navigation.
- [x] P12.4 Expand K3Z user-facing docs to TSR-style data-package depth
  (match structure/depth of BC small-unit timber supply data packages)
  - [x] P12.4a Add full metadata inventory and lineage narratives by artifact
    family (inputs, transforms, outputs, validation evidence).
  - [x] P12.4b Add full operator runbook coverage (fresh setup, rebuild,
    diagnostics, troubleshooting, and release checklist).
  - [x] P12.4c Add user edit-policy matrix and interpretation guidance aligned
    to classroom workflows and scenario comparison needs.
  - [x] P12.4d Build exemplar structure crosswalk from BC reference data
    packages (`TFL26`, `CFA`, `FNWL`) to K3Z standalone docs sections,
    including: Introduction, Land Base Definition, Non-Timber Assumptions,
    Harvesting Assumptions, Growth & Yield, Natural Disturbance, Modeling
    Assumptions, Analysis Report, Discussion, and References.
  - [x] P12.4e Add standalone K3Z data-package page set covering:
    land-base definition + netdown logic, assumptions registry
    (timber/non-timber/model), base-case analysis outputs + interpretation,
    and discussion/limitations/known uncertainty sources.
  - [x] P12.4f Require explicit evidence/provenance tables for each artifact
    family with update date, source path/URL, transform stage, and QA status.
  - [x] P12.4g Add student usability acceptance content across major pages:
    what to edit vs regenerate, and how to validate rebuild/rerun outputs.
  - [x] P12.4h Define publication acceptance criteria before closing `P12.4`:
    standalone docs build `-W`, docs-contract coverage for required sections,
    and published GitHub Pages verification for `femic-k3z-instance`.
- [x] P12.5 Enforce FRESH lab Sphinx template consistency (FHOPS-aligned)
  - [x] P12.5a Define the canonical template baseline using
    `https://github.com/UBC-FRESH/fhops` as the reference implementation.
  - [x] P12.5b Capture required template components and style conventions
    (theme/extensions, navigation structure, build/publish settings, RTD/GitHub
    Pages behavior, and warning-as-error policy).
  - [x] P12.5c Apply the shared template baseline to
    `femic-k3z-instance` docs, then reconcile FEMIC docs where needed so FRESH
    lab docs present a consistent user experience.
  - [x] P12.5d Add a template-compliance checklist in CI/docs-contract tests to
    prevent drift across FRESH lab documentation projects.
  - [x] P12.5e Ensure FHOPS template alignment preserves BC data-package depth
    expectations for K3Z documentation content.
- [x] P12.6 Finalize and operationalize docs ownership
  - [x] P12.6a Define update cadence and ownership for K3Z docs/content refresh.
  - [x] P12.6b Define release tagging/versioning policy for docs alongside model
    snapshots.
  - [x] P12.6c Add contributor onboarding guidance for docs changes and review.
- [x] P12.7 Cross-platform geospatial dependency bootstrap hardening (`fiona`/`GDAL`)
  - [x] P12.7a Define and test known-valid install rituals for Linux and Windows
    (including Windows-specific `fiona`/`GDAL` handling for local `.venv` setup).
  - [x] P12.7b Add runtime/bootstrap OS detection so environment setup applies the
    correct dependency path automatically.
  - [x] P12.7c Add explicit preflight checks for geospatial stack readiness
    (`import fiona`, GDAL version visibility, shapefile I/O smoke).
  - [x] P12.7d Add troubleshooting docs for Windows geospatial dependency install
    failures and deterministic remediation steps.
- [x] P12.8 Terminology normalization: use `untreated/treated` curve-source terms
  - [x] P12.8a Replace legacy terminology in source code, tests, and docstrings.
  - [x] P12.8b Replace legacy terminology in user-facing docs/metadata text.
  - [x] P12.8c Keep IFM semantics unchanged (`managed/unmanaged`) while using
    `untreated/treated` only for curve-source terminology.

## Phase 13: Instance Rebuild Repro Framework (Default for All New Instances)
- [x] P13.1 Define a canonical rebuild contract for FEMIC deployment instances
  - [x] P13.1a Specify required inputs, required config files, and required runtime prerequisites.
  - [x] P13.1b Specify the authoritative rebuild sequence (command order, mutable artifacts, expected outputs).
  - [x] P13.1c Specify required post-rebuild invariants (accounts, targets, managed-area sanity, block joins, seral presence).
  - [x] P13.1d Define failure classes (hard fail vs warning) and required remediation messaging.
- [x] P13.2 Add first-class rebuild orchestration to FEMIC
  - [x] P13.2a Add a reusable rebuild runner abstraction (step graph + deterministic execution + report sink).
  - [x] P13.2b Add CLI support for instance rebuild execution (instance-rooted, run-ided, non-interactive).
  - [x] P13.2c Ensure rebuild execution writes machine-readable reports/manifests and references all generated logs.
  - [x] P13.2d Add dry-run mode showing full planned command sequence without mutation.
- [x] P13.3 Add per-instance rebuild spec/config files as tracked source-of-truth
  - [x] P13.3a Define a standard rebuild spec schema (YAML) for instance command steps and invariants.
  - [x] P13.3b Ship a default template with `femic instance init` so every new instance starts with a rebuild spec.
  - [x] P13.3c Add K3Z as the reference implementation and backfill its current known-valid sequence.
  - [x] P13.3d Add schema validation + clear diagnostics for malformed rebuild specs.
- [x] P13.4 Add regression guardrails for rebuild outputs
  - [x] P13.4a Add invariant checks for known-risk dimensions (managed species yields, seral accounts, topology/block joins).
  - [x] P13.4b Add configurable baseline snapshot/diff support for key track tables and selected XML structures.
  - [x] P13.4c Add explicit allowlist mechanism for intentional output deltas (so accepted changes are tracked in git).
  - [x] P13.4d Fail rebuild with actionable summary when invariants regress or unexpected diffs exceed thresholds.
- [x] P13.5 Add user-facing documentation and operator runbooks
  - [x] P13.5a Add docs page: "Rebuild Repro Contract" (what it is, why it exists, expected workflow).
  - [x] P13.5b Add docs page: "How to author a new instance rebuild spec" with copy-ready examples.
  - [x] P13.5c Add docs page: "How to interpret rebuild reports and regressions".
  - [x] P13.5d Add contributor policy text making rebuild-spec + checks mandatory for new instance repos.
- [x] P13.6 Enforce this as the default norm for all new FEMIC instances
  - [x] P13.6a Extend `femic instance init` scaffolding to always include rebuild spec + runbook placeholders.
  - [x] P13.6b Add docs/contract tests requiring rebuild-spec references in sample/new instance docs.
  - [x] P13.6c Add release-gate checks requiring successful rebuild report for reference instances prior to milestone close.
  - [x] P13.6d Add roadmap/changelog policy note: no new instance phase closes without reproducible rebuild evidence.

Phase 13 Closure Policy (Mandatory)
-----------------------------------

No new instance phase is considered complete unless reproducible rebuild
evidence is present and passing (report + regression-gate status), and that
evidence is tracked or explicitly referenced in roadmap/changelog milestone
notes.

## Phase 14: Evidence Automation + Ongoing Instance Operations
- [x] P14.1 Add CLI support to promote rebuild reports into normalized
  evidence artifacts
  - [x] P14.1a Add `femic instance promote-evidence` command with latest-report
    discovery and explicit `--report` override.
  - [x] P14.1b Emit normalized evidence payload for release-gate consumption
    (`status`, `regression_gate`, summary counts, source report path).
  - [x] P14.1c Add CLI/docs-contract coverage and reference CLI docs updates.
- [x] P14.2 Add reusable evidence-refresh automation for maintainers
  - [x] P14.2a Add script/helper command to refresh
    `instances/reference/evidence/reference_rebuild_report.latest.json` from
    current logs.
  - [x] P14.2b Add contributor runbook step for evidence refresh during release
    preparation.
- [x] P14.3 Add drift-monitoring hooks for long-lived instance repositories
  - [x] P14.3a Add optional warning threshold checks for trend drift in rebuild
    evidence summaries.
  - [x] P14.3b Add docs on interpreting evidence-trend drift across releases.

## Phase 15: K3Z Species-Account Semantics + Output Hygiene
- [x] P15.1 Resolve `PL` vs `PLC` semantics for K3Z species-wise outputs
  - [x] P15.1a Audit `tracks/accounts.csv`, `forestmodel.xml`, and source
    species-code mappings to confirm whether `PL` is a valid modeled species
    for K3Z or a legacy loose-end.
  - [x] P15.1b If `PL` is not valid for K3Z, remove it from generated account
   /target surfaces and keep `PLC` canonical.
  - [x] P15.1c Add explicit docs note so students understand species-code
    expectations and do not interpret empty `PL` as runtime failure.
- [x] P15.2 Add rebuild invariants for species-account completeness
  - [x] P15.2a Add invariant checks for species-wise managed yield and
    harvested-volume account presence/non-null behavior.
  - [x] P15.2b Classify expected-empty vs unexpected-empty species outputs as
    configurable policy in rebuild spec/allowlist.
  - [x] P15.2c Fail rebuild when unexpected species-account null regressions are
    introduced.
- [x] P15.3 Add operator diagnostics for account-surface QA
  - [x] P15.3a Add a CLI/report helper to summarize account/target coverage by
    species and AU from rebuilt tracks.
  - [x] P15.3b Add a deterministic troubleshooting flow for "total OK,
    species-wise empty" failures.
  - [x] P15.3c Wire diagnostics outputs into rebuild evidence/runbook guidance.
- [x] P15.4 Update K3Z standalone docs and FEMIC sample-model docs
  - [x] P15.4a Update k3z guide pages with species-account interpretation and
    PL/PLC decision record.
  - [x] P15.4b Add user-facing "expected empty account" matrix and validation
    checklist.
  - [x] P15.4c Add docs-contract coverage for required species-account
    interpretation sections.

## Phase 16: Full Developer API Documentation Coverage (FEMIC Package)
- [x] P16.1 Define API doc contract and exclusion policy
- [x] P16.2 Systematically inject/normalize Google-style docstrings across
  `src/femic`
- [x] P16.3 Build full Sphinx API reference (public surface only)
- [x] P16.4 Add API-doc coverage guardrails in tests/CI
- [x] P16.5 Validate docs build and cross-link integrity

## Phase 17: K3Z TSR-Style Student Documentation (Submodule-First)
- [x] P17.0 Sync submodule baseline to latest intended
  `femic-k3z-instance` commit
- [x] P17.1 Define K3Z doc information architecture in submodule docs
- [x] P17.2 Add TSR-style core content (area, THLB, AU accounting,
  maps/figures)
- [x] P17.3 Add figure appendix and in-text references
- [x] P17.4 Keep FEMIC docs as pointer page to submodule canonical docs
- [x] P17.5 Add docs contract checks for submodule-first K3Z docs

## Phase 18: Packaging and Publication to PyPI
- [x] P18.1 Packaging metadata and build reproducibility checks
- [x] P18.2 TestPyPI publication and install smoke tests
- [x] P18.3 Production PyPI release
- [x] P18.4 Post-release docs/changelog/version traceability

## Phase 19: TSA29 Example Instance Repository (Standalone + Linked)
- [x] P19.1 Define TSA29 instance contract, scope, and acceptance gates
- [x] P19.2 Bootstrap and structure femic-tsa29-instance repository
- [x] P19.3 Assemble ASAP-usable TSA29 snapshot payload
- [x] P19.4 Add rebuild spec + invariant policy + evidence workflow
- [ ] P19.5 Execute rebuild validation and publish evidence
- [x] P19.6 Build canonical TSA29 student docs in instance repo
- [x] P19.7 Link TSA29 repo back into FEMIC as submodule + pointer docs
- [x] P19.8 Add contract tests and release handoff (v0.1.0)
- [x] P19.9 Add dual-output fork contract (Patchworks + Woodstock)
- [x] P19.10 Add ws3 smoke-test integration and evidence gate
- [x] P19.11 Harden resume checkpoint compatibility for strata-selection changes
- [x] P19.12 Improve stratum SI diagnostic plot readability and interpretability
  - [x] P19.12a Thin/sample SI point overlays and reduce point opacity so violin
    density remains visible.
  - [x] P19.12b Add zoomed SI-axis defaults centered on core distribution
    (quantile-based window + configurable cap), with explicit outlier handling.
  - [x] P19.12c Record and report clipped/out-of-window point counts in plot
    metadata/log output so visual trimming is auditable.
- [x] P19.13 Add VDYP NLLS failure detection and auto-reparameterization fallback
  sequence
  - [x] P19.13a Add fit-quality gate(s) to detect obviously failed or
    biophysically implausible NLLS curves before acceptance.
  - [x] P19.13b Add left-toe outlier censor pass for incoherent early-age points,
    then re-fit on censored vectors.
  - [x] P19.13c Add optional merchantable-volume floor constraint
    (default zero through age 20) via toe-shift/parameterized fit mode.
  - [x] P19.13d Implement ordered fallback policy (primary NLLS ->
    reparameterized NLLS -> censored re-fit -> constrained fallback) with
    per-stratum event logging.
  - [x] P19.13e Move body NLLS fit substrate from annual-age medians to
    5-year binned medians for smoother/less noisy stratum fits.
  - [x] P19.13f Enforce layered left-toe censor application for structural
    early-age discontinuities before downstream fit-path processing.
- [x] P19.14 Revisit VDYP tail-blend heuristic and curve-selection policy
  - [x] P19.14a Relax/update tail-linearity definition and threshold parameters
    (config-driven, TSA-overridable).
  - [x] P19.14b Rework tail-blend vs straight-NLLS selection criteria using
    explicit objective metrics and deterministic tie-breaks.
  - [x] P19.14c Add regression diagnostics/plots that expose selected fit path,
    blend window, and residual behavior per stratum/SI level.
  - [x] P19.14d Rework right-tail detection to right-to-left contiguous
    break finding on 5-year bins with flat-slope + span guards so long
    straight-ish tails are detected ahead of tiny end segments.
- [x] P19.15 Re-run TSA29 curve QA and publish curve-stability evidence
  - [x] P19.15a Rebuild TSA29 diagnostics with updated plotting and fitting
    policies.
    - [x] P19.15a.1 Guard THLB raster mean for empty valid-cell slices to avoid
      NumPy warning floods during post-TIPSY bundle assembly.
  - [x] P19.15b Produce reviewer-facing summary table of strata/SI fit status
    (accepted/fallback path/constraints applied).
  - [x] P19.15c Update TSA29 instance docs/evidence with before/after curve
    comparisons and acceptance sign-off notes.
  - [x] P19.15d Harden curve-path branching so censoring is composable and
    selected-curve gate failures auto-rescue to best available candidates.
- [x] P19.16 Fix degenerate best-fit selection behavior for catastrophic
  primary-NLLS cases
  - [x] P19.16a Redefine candidate selection to allow "dominant recovery"
    candidates (for example, censored refit) when baseline primary metrics are
    catastrophic, even if a single guard metric (for example, early overshoot)
    regresses.
  - [x] P19.16b Add explicit hard-fail quality gates for selected curves
    (catastrophic error envelope), and require fallback to best available
    non-catastrophic candidate when triggered.
  - [x] P19.16c Add deterministic decision-event telemetry that records
    rejection reasons and veto priorities so reviewer-visible failures are
    explainable from logs without plot inspection.
  - [x] P19.16d Add targeted regression fixtures/tests for known TSA29 failure
    strata (`MS_PLI H`, `IDF_FDI L`, `MS_PL M`, `IDF_FD H/M`) and assert
    selected-path outcomes plus quality metric improvements.
  - [x] P19.16e Re-run cached TSA29 smoothing + fitdiag regeneration and
    publish before/after reviewer summary evidence.
- [ ] P19.17 Execute TSA29 instance Sphinx docs deep-dive and augmentation pass
  - [ ] P19.17a Audit TSA29 instance Sphinx pages for thin/missing sections
    (workflow steps, assumptions, artifact references, troubleshooting detail).
  - [ ] P19.17b Expand weak sections with concrete procedural guidance and
    explicit cross-links to current TSA29 compile/smoke evidence artifacts.
  - [ ] P19.17c Rebuild docs with warnings-as-errors and publish a short
    documentation-gap closure summary in roadmap/changelog notes.

## Phase 20: VDYP Parallelization and Runtime Observability (Non-Blocking)
- [ ] P20.1 Define VDYP parallelization contract and non-regression invariants
- [ ] P20.2 Profile baseline serial VDYP runtime by TSA/AU workload shape
- [ ] P20.3 Implement optional AU-level parallel execution path behind a feature flag
- [ ] P20.4 Add deterministic merge/reduction logic and reproducibility checks
- [ ] P20.5 Expand runtime progress logging/heartbeat for long VDYP stages
- [ ] P20.6 Validate parity and performance; decide default enablement policy

## Phase 21: K3Z Old-Growth Attribute Rollout (`og1`/`og2`)
- [x] P21.1 Define OG attribute/curve contract for Patchworks export
  - [x] P21.1a Add per-AU feature attributes:
    `feature.Area.og1.<au_id>`, `feature.Area.og2.<au_id>`.
  - [x] P21.1b Add cross-AU total feature attributes:
    `feature.Area.og1.total`, `feature.Area.og2.total`.
  - [x] P21.1c Scope OG1 to unmanaged (untreated/VDYP) yield dynamics.
- [x] P21.2 Implement OG curve synthesis in FEMIC Patchworks exporter
  - [x] P21.2a OG1: linear ramp from CMAI age (`0.0`) to peak-yield age (`1.0`),
    computed from unmanaged total-yield curve.
  - [x] P21.2b OG2: policy-step curve (`0.0` at age 249, `1.0` at age 250).
  - [x] P21.2c Bind OG attributes to both managed/unmanaged feature selects.
- [x] P21.3 Add regression coverage and refresh XML fixtures
  - [x] P21.3a Assert OG labels and OG curve point vectors in
    `tests/test_fmg_patchworks.py`.
  - [x] P21.3b Update ForestModel XML fixtures for deterministic output parity.
- [x] P21.4 Regenerate K3Z instance ForestModel XML with OG attributes
  - [x] P21.4a Rebuild
    `external/femic-k3z-instance/models/k3z_patchworks_model/yield/forestmodel.xml`
    from K3Z bundle tables using current exporter logic.
  - [x] P21.4b Verify emitted OG labels and curve IDs in generated XML.


## Phase 22: K3Z CT + Fert Treatment Scaffolding and Optional Instance Variant
- [x] P22.1 Define YAML-facing treatment scaffold contract for CT + fertilization
  - [x] P22.1a Add K3Z model-input schema for one CT treatment plus optional
    `fert1` / `fert2` / `fert3` treatment chain.
  - [x] P22.1b Add per-AU treatment parameter support for:
    CT age, CT basal-area removal fraction, BA:volume conversion ratio,
    fertilization speedup fraction, fertilization response duration,
    and fert spacing offsets.
  - [x] P22.1c Limit the initial CT/fert scaffold to K3Z AUs
    `FDC+HW-M` and `CW+HW-M`, while keeping the YAML structure extensible to
    additional AUs later.
- [x] P22.2 Add explicit treatment-path state handling in Patchworks export
  - [x] P22.2a Introduce a new stand-state field for treatment-path gating
    (for example `SILV_STATE`) instead of overloading `ORIGIN`, so
    `ORIGIN` retains its natural/planted semantics.
  - [x] P22.2b Define initial treatment-path state and XML `<assign>`
    transitions for `CT`, `fert1`, `fert2`, and `fert3` eligibility gates.
  - [x] P22.2c Keep CT/fert eligibility constrained to `ORIGIN='planted'`
    where required while preserving current unmanaged/managed/origin logic.
- [x] P22.3 Add provisional QMD curve support to the K3Z model scaffold
  - [x] P22.3a Add AU-wise QMD curves/attributes to the Patchworks exporter.
  - [x] P22.3b Synthesize placeholder but plausible K3Z QMD curves for the
    initial rollout, with a documented replacement path for future nemora-based
    or externally supplied QMD curves.
  - [x] P22.3c Expose QMD curve assumptions/parameters in YAML so later
    real-curve replacement does not require exporter redesign.
- [x] P22.4 Implement commercial thinning (CT) treatment logic
  - [x] P22.4a Add a single CT treatment available only in planted stands and
    only in the initial target AUs (`FDC+HW-M`, `CW+HW-M`).
  - [x] P22.4b Parameterize CT age per AU (default age 40) and CT removal
    intensity (default 30% basal area removed from below).
  - [x] P22.4c Add temporary BA:volume conversion parameter (default 1.0) and
    use it to estimate CT harvested volume until a better DBH-distribution-based
    treatment response path is available.
  - [x] P22.4d Define post-CT total-volume trajectory so CT-harvested volume plus
    final-harvest volume approximately conserves the no-CT total-yield endpoint.
- [x] P22.5 Implement fertilization treatment-chain logic (`fert1`/`fert2`/`fert3`)
  - [x] P22.5a Make `fert1` available only after CT, using the treatment-path
    state gate rather than `ORIGIN` mutation.
  - [x] P22.5b Schedule `fert1` at the age of maximal CAI on the planted total
    yield curve (argmax of first derivative), with YAML override support if we
    later need AU-specific exceptions.
  - [x] P22.5c Make `fert2` available only after `fert1` and schedule it 10
    years later by default; make `fert3` available only after `fert2` and
    schedule it another 10 years later by default.
  - [x] P22.5d Parameterize fertilization response as a growth-speedup fraction
    (default 10%) for a finite response window (default 10 years).
- [x] P22.6 Add curve-synthesis rules for CT/fert treatment responses
  - [x] P22.6a Build post-CT treated total-yield curves by subtracting CT
    harvested volume at treatment age from the planted baseline curve.
  - [x] P22.6b Build fertilization-response curves by temporarily compressing the
    planted post-treatment growth path over the configured response window.
  - [x] P22.6c Preserve transparent, auditable curve-generation logic in docs
    and tests so these provisional treatment-response heuristics can be swapped
    out later without changing the external YAML contract.
- [x] P22.7 Roll CT/fert scaffolding into an optional K3Z instance variant branch
  - [x] P22.7a Keep parent-repo implementation work on branch
    `feature/k3z-ct-fert-treatment-scaffold`.
  - [x] P22.7b Land generated K3Z instance outputs on submodule branch
    `feature/k3z-ct-fert-treatment-option`, so only student groups that want
    CT/fert can pull that variant into their forks.
  - [x] P22.7c Rebuild K3Z Patchworks XML/tracks on the variant branch and run
    Windows Patchworks smoke validation before any merge discussion.
- [x] P22.8 Add docs, evidence, and acceptance checks
  - [x] P22.8a Update FEMIC docs and standalone `femic-k3z-instance` Sphinx docs
    to cover the optional CT/fert variant end-to-end: YAML parameters,
    treatment-path state semantics, provisional QMD/curve assumptions, and the
    student-facing pull/use workflow for the optional instance branch.
  - [x] P22.8b Add regression tests for YAML parsing, treatment-state gating,
    CT/fert XML emission, QMD attribute export, and treatment-response curves.
  - [x] P22.8c Capture Patchworks smoke evidence showing CT/fert treatments,
    accounts, and targets appear correctly in the optional K3Z variant.
  - [x] P22.8d Backfill standalone `femic-k3z-instance` docs with the earlier
    Phase 21 old-growth rollout details (`og1`/`og2` area attributes, curve
    semantics, compiled-account expectations) so the K3Z docs reflect the full
    current model surface before or alongside CT/fert variant guidance.
- [ ] P22.9 Co-locate baseline and CT/fert variants inside one K3Z instance on main
  - [x] P22.9a Define the coexistence pattern: variant selection happens by
    config/PIN/runtime target, not by Git branch.
  - [x] P22.9b Add distinct K3Z variant config YAMLs documenting baseline and
    CT/fert build instructions plus their variant-specific runtime targets.
  - [x] P22.9c Add distinct CT/fert runtime/build surfaces (`tracks_ctfert`,
    `forestmodel_ctfert.xml`, `output/patchworks_k3z_ctfert_validated/`,
    `analysis/ctfert.pin`) so baseline and variant can coexist in one instance.
  - [x] P22.9d Fix shared target-script path assumptions so each PIN resolves
    accounts/validation against its own active tracks folder.
  - [ ] P22.9e Rebuild the CT/fert variant from canonical K3Z inputs while
    preserving the current teaching-baseline footprint (`THLB=1`, 218
    fragments, 14 AUs), then verify the resulting tracks surface is an additive
    extension of the baseline rather than a stale copied artifact.
  - [x] P22.9f Update standalone K3Z docs and runbooks to teach variant
    selection by config/PIN instead of by Git branch.
  - [x] P22.9g Merge the coexistence layout to `main` in both repos only after
    baseline and CT/fert variants launch cleanly side-by-side from one branch.

- [x] P22.10 Add a third coexisting K3Z silviculture variant for PCT -> CT
  - [x] P22.10a Extend the Phase 22 variant contract so K3Z supports three
    coexisting upstream-from-Matrix-Builder variants on one branch:
    baseline, ctfert, and pctct.
  - [x] P22.10b Add a dedicated variant YAML/runtime/PIN/output surface for the
    new pctct path:
    config/patchworks.variant.pctct.yaml,
    config/patchworks.runtime.pctct.windows.yaml,
    models/k3z_patchworks_model/analysis/pctct.pin,
    models/k3z_patchworks_model/tracks_pctct/,
    models/k3z_patchworks_model/yield/forestmodel_pctct.xml,
    and output/patchworks_k3z_pctct_validated/.
  - [x] P22.10c Add a pre-commercial thinning (PCT) treatment option that is
    available on the planted pathway before CT and removes hardwood ingress
    while retaining only the planted conifer component at a residual
    900 stems/ha target.
  - [x] P22.10d Parameterize PCT by AU in silviculture YAML, including at
    default treatment age (10), eligible AU set, and the planted-species retention
    rule so the current K3Z heuristic can be revised later without redesigning
    the external config contract.
  - [x] P22.10e Add treatment-path gating so CT is only available after
    PCT in the new pctct variant, while preserving the existing ctfert
    branch semantics unchanged.
  - [x] P22.10f Synthesize post-PCT curves/products/accounts so the pctct
    variant behaves as an additive extension of the baseline model rather than a
    separate ad hoc compile, and verify that the residual conifer-only treated
    state is reflected consistently in XML, tracks, and Patchworks accounts.
  - [x] P22.10g Update standalone K3Z docs, runbooks, and student-facing
    variant guidance so the three-way coexistence model is explicit:
    baseline (base.pin), ctfert (ctfert.pin), and pctct
    (pctct.pin), including what each variant changes upstream from Matrix
    Builder and when students should choose one over another.
  - [x] P22.10h Run Windows Patchworks smoke checks on the pctct variant and
    only then consider merging the three-variant coexistence layout back to
    main.

## Phase 23: Cross-Platform Runtime Parity (Linux + Windows)
- [x] P23.1 Inventory platform-specific runtime dependencies and current gaps
  - [x] P23.1a Enumerate required local executables/services for full FEMIC runs on Linux and Windows (`python`, `git`, `git-annex`, `datalad`, `VDYP`, `Patchworks`, Java, Wine where applicable).
  - [x] P23.1b Record which runtime surfaces are authoritative per platform (for example: native Patchworks on Windows, Wine-wrapped VDYP on Linux, native VDYP on Windows).
  - [x] P23.1c Add deterministic environment-detection/preflight checks so FEMIC can report missing platform prerequisites clearly before long runs start.
- [x] P23.2 Make Windows a first-class full-pipeline execution environment
  - [x] P23.2a Validate native Windows VDYP invocation using the bundled local `VDYP7Console.exe` path instead of Linux/Wine assumptions.
  - [x] P23.2b Add/verify Windows run-profile and helper wiring so `femic run` can execute end-to-end from a clean start in the Patchworks workstation environment.
  - [x] P23.2c Document the known-good Windows bootstrap sequence for local `.venv`, native VDYP, Patchworks, and Java.
  - [x] P23.2d Apply the K3Z low-yield treated-strata simplification cleanly in the canonical pipeline: exclude `CWHvm_CW+YC` and `CWHvm_CW+PLC` from BatchTIPSY generation, keep their unmanaged VDYP side, and force `RETENTION = 1.0` for matching fragments so they are fully netted out of THLB in the baseline model.
  - [x] P23.2e Replace the remaining K3Z TIPSY species-mix rules with the simplified teaching logic: FD-pair AUs -> `900 FD + 3100 HW`; CW-pair AUs -> `900 CW + 3100 HW`; all other remaining treated AUs -> `600 CW + 300 FD + 3100 HW`.
- [x] P23.3 Preserve and harden Linux execution parity
  - [x] P23.3a Keep Linux VDYP execution working via Wine and document the exact wrapper/runtime expectations. Verified on Linux 2026-03-21 with clean-start run `k3z_linux_p233a_20260321_r16_full` against `/tmp/femic_p23a_finalrun_rC45UW`: ArcRasterRescue completed all layers, Stage 00 checkpoints regenerated, VDYP bootstrap/two-pass SI rebin completed (`mapped VDYP SI for 38/46 rows`), and run reached the expected Stage 01a BatchTIPSY freshness boundary (`Stale BatchTIPSY output detected: data/04_output-tsak3z.out is older than data/02_input-tsak3z.dat`).
  - [x] P23.3b Verify Linux guidance still covers the full FEMIC pipeline when Patchworks is unavailable natively. Verified on Linux 2026-03-21 with `femic tsa post-tipsy --instance-root /tmp/femic_p23b_r5_dC7Rio --run-config config/run_profile.k3z.yaml --tsa k3z --run-id k3z_linux_p233b_20260321_r8` (`status=ok`), after hardening 01b plotting to tolerate missing comparison keys.
  - [x] P23.3c Add parity notes explaining what is expected to differ between Linux and Windows and what should remain identical. Linux-side sign-off complete (2026-03-21) using real `P23.3a` and `P23.3b` execution evidence; docs now reflect that both platforms converge to the same Stage 01a->BatchTIPSY boundary and Stage 01b resume contract, with platform differences isolated to runtime/tool wrapper surfaces.
- [x] P23.4 Stabilize DataLad / git-annex bootstrap on Windows
  - [x] P23.4a Document a known-good Windows install/bootstrap pattern for `git`, `git-annex`, and DataLad.
  - [x] P23.4b Ensure FEMIC operator docs explain how annex-backed payloads are materialized on Windows (including pointer-file behavior and recovery steps).
  - [x] P23.4c Add validation/smoke checks that confirm annex-backed public-data payloads are usable from Windows pipeline runs.
- [x] P23.5 Add cross-platform docs, smoke tests, and acceptance gates
  - [x] P23.5a Add a user-facing guide describing how to run FEMIC cleanly in both Linux and Windows environments.
  - [x] P23.5b Add smoke workflows for a clean-start rerun on Windows and a parity rerun on Linux.
  - [x] P23.5c Define acceptance as: FEMIC can rerun a full canonical pipeline from a clean start on both platforms with documented, platform-appropriate runtime rituals.
  - [x] P23.5d Update user-facing K3Z docs and operator runbooks to explain the low-yield treated-strata netdown decision (`CWHvm_CW+YC`, `CWHvm_CW+PLC`), the resulting full-retention behavior, and the simplified TIPSY species-mix logic used for the remaining treated AUs.
- [x] P23.6 Harden fresh-clone developer bootstrap and DataLad materialization rituals
  - [x] P23.6a Add an explicit agent-facing "first steps in a fresh clone" checklist (venv activation, editable install, and required runtime smoke checks).
  - [x] P23.6b Add a user-facing development-environment bootstrap path that standardizes `.venv` setup and `pip install -e .[dev]`.
  - [x] P23.6c Make DataLad/git-annex/arbutus-s3 bootstrap and `datalad get` materialization expectations unambiguous for `external/femic-public-data`.
  - [x] P23.6d Add packaging affordances (`requirements-dev.txt`, optional dependency extras) so fresh-clone setup is one command and reproducible.

### Phase 23 Windows Closeout Status
- Windows-side Phase 23 closeout is complete on branch feature/phase23-windows-runtime-parity.
- The remaining open work in Phase 23 is Linux-specific parity verification under P23.3.
- Treat the following tasks as **Linux dev environment required** before Phase 23 can be called fully closed:
  - P23.3a
  - P23.3b
  - Linux sign-off portion of P23.3c
- Once those Linux tasks are completed and documented, mark top-level P23.3 and P23 complete.
  - 2026-03-21 update: Linux tasks (`P23.3a`, `P23.3b`, `P23.3c`) are now completed and documented; Phase 23 parity closeout criteria are satisfied.
## Detailed Next Steps Notes
- 2026-03-21 (Phase 23 Linux parity full clean-start convergence): obtained the first uninterrupted Linux `P23.3a` terminal outcome and closed parity sign-off items.
  - Run details:
    - tmp instance: `/tmp/femic_p23a_finalrun_rC45UW`
    - run id: `k3z_linux_p233a_20260321_r16_full`
    - log: `/tmp/femic_p23a_r16_full.log`
    - manifest: `/tmp/femic_p23a_finalrun_rC45UW/vdyp_io/logs/run_manifest-k3z_linux_p233a_20260321_r16_full.json`
  - Observed terminal behavior:
    - ArcRasterRescue exported all 22 species layers with per-layer completion timings,
    - Stage 00 completed through stacked `siteprod.tif` and regenerated checkpoints (`checkpoint2`, `checkpoint3`, `checkpoint4`, `vdyp_prep-tsak3z.pkl`),
    - VDYP bootstrap ran across all strata/SI bins and two-pass SI rebin completed (`mapped VDYP SI for 38/46 rows`, rebuilt bins with `missing=0 of 114`),
    - run then stopped at expected Stage 01a->BatchTIPSY freshness boundary:
      `RuntimeError: Stale BatchTIPSY output detected: data/04_output-tsak3z.out is older than data/02_input-tsak3z.dat`.
  - Outcome:
    - this is the expected Linux Stage 01a handoff boundary behavior, not a runtime crash regression;
    - with `P23.3b` already passing on Linux, parity sign-off (`P23.3c`) is now complete.

- 2026-03-21 (Phase 23 Linux parity fail-fast diagnostic plan for Stage 00): convert the ArcRasterRescue export seam from silent long-running behavior to explicit bounded failures.
  - Add per-layer ArcRasterRescue instrumentation in `src/femic/pipeline/siteprod.py`:
    - emit start/completion timing messages for each species/layer export,
    - enforce timeout-bounded subprocess behavior (configurable),
    - raise explicit `RuntimeError` on timeout/non-zero return with layer/species context and stderr summary.
  - Add regression coverage in `tests/test_siteprod.py` for:
    - timeout path emits a deterministic failure instead of indefinite wait,
    - non-zero returncode path includes diagnostics.
  - Re-run a Linux `P23.3a` clean-start check after instrumentation to capture the first concrete failing ArcRasterRescue layer or prove progression beyond Stage 00.
- 2026-03-21 (Phase 23 Linux parity diagnostic outcome after Stage 00 instrumentation): prior "species SW stall" interpretation was corrected.
  - Implemented fail-fast diagnostics in `src/femic/pipeline/siteprod.py`:
    - per-layer ArcRasterRescue launch/completion messages with timing,
    - timeout-bound execution via `FEMIC_ARC_RASTER_RESCUE_TIMEOUT_SEC` (default 900s),
    - explicit `RuntimeError` on timeout/non-zero returncode with species/layer context and stderr summary.
  - Added execution-stream visibility hardening:
    - `build_legacy_execution_plan(...)` now sets `PYTHONUNBUFFERED=1` by default so long Stage 00 progress is not hidden by Python buffering.
  - Added regression coverage:
    - `tests/test_siteprod.py`: timeout and non-zero returncode diagnostics.
    - `tests/test_pipeline_helpers.py`: asserts `PYTHONUNBUFFERED=1` in legacy execution env.
  - Linux rerun evidence (`run-id: k3z_linux_p233a_20260321_r15_diag_unbuffered`, tmp `/tmp/femic_p23a_diag2_P0qEiG`):
    - Stage 00 progressed beyond ArcRasterRescue export despite sparse streamed output:
      - temp `site_prod_bc_*.tif` count dropped to zero,
      - stacked `data/siteprod.tif` grew to full-size write,
      - `data/ria_vri_vclr1p_checkpoint2.feather` and `data/ria_vri_vclr1p_checkpoint3.feather` were created.
    - Run was manually interrupted before reaching VDYP/TIPSY boundary to keep iteration time bounded, so `P23.3a` remains open.

- 2026-03-21 (Phase 23 Linux parity clean-start rerun, post runtime-asset staging): `P23.3a` remains open after a reproducible Stage 00 stall before VDYP boundary.
  - Clean rerun context:
    - tmp instance: `/tmp/femic_p23a_final_bF2EN4`
    - run id: `k3z_linux_p233a_20260321_r13_final`
    - shell log: `/tmp/femic_p23a_r13_final.log`
    - manifest: `/tmp/femic_p23a_final_bF2EN4/vdyp_io/logs/run_manifest-k3z_linux_p233a_20260321_r13_final.json`
  - Observed behavior:
    - preflight passed (`validate-case`, `geospatial-preflight`);
    - run advanced through ArcRasterRescue species extraction logs up to `... processing species SW`;
    - after that point, no new log lines were emitted for multiple minutes, no `vdyp_runs-...jsonl`/`vdyp_stderr-...log` files were created, and no active ArcRasterRescue child process remained;
    - process was interrupted manually to avoid indefinite execution, leaving the run manifest in `status=started`.
  - Interpretation:
    - the prior missing-VDYP-runtime-asset seam is fixed in code, but this run did not reach the VDYP boundary, so `P23.3a` still lacks final Linux handoff confirmation.

- 2026-03-21 (Phase 23 Linux parity root-cause + runtime-asset staging): identified why Linux `P23.3a` reported missing VDYP output even though bootstrap dispatch calls were emitted.
  - Root cause evidence:
    - failing runs reached bootstrap dispatch, but each call logged `FATAL: VDYP7 Configuration Folder ('-c') has not been supplied.` in `vdyp_stderr-*.log`;
    - all generated `vdyp_out_*.out` files were empty (`0` bytes), so two-pass SI rebin mapped `0/46` and downstream strata reported missing VDYP curves;
    - direct replay of a captured VDYP command from `/tmp` instance root failed the same way, while replay from repo source root succeeded and produced non-empty `vdyp_out` output.
  - Root cause interpretation:
    - `vdyp_params-landp` still points to relative legacy paths (`./vdyp_io/VDYP_CFG`, `./vdyp_io/VDYP.INI`);
    - clean `/tmp` instance clones did not carry those runtime assets, so Wine VDYP dispatch executed but produced no usable output.
  - Corrective implementation:
    - added `ensure_local_vdyp_runtime_assets(...)` in `src/femic/pipeline/vdyp_stage.py` and wired it into `run_vdyp_for_stratum(...)` so missing `vdyp_io/VDYP_CFG` and `vdyp_io/VDYP.INI` are staged from `FEMIC_SOURCE_ROOT` runtime assets before VDYP calls.
    - added regression coverage in `tests/test_vdyp_stage.py` (`test_ensure_local_vdyp_runtime_assets_stages_cfg_and_ini`).
  - Current status:
    - targeted regression tests pass for the new staging seam;
    - full clean-start Linux `P23.3a` confirmation to the Stage 01a BatchTIPSY boundary still pending (long Stage 00 extraction runs were interrupted in-session before the VDYP boundary was reached).

- 2026-03-21 (Phase 23 Linux parity corrective rerun after ArcRasterRescue + TIPSY freshness fixes): advanced past prior blockers, but Linux parity is still not fully closed.
  - Implemented and validated in-repo fixes:
    - ArcRasterRescue executable path resolution now supports `FEMIC_ARC_RASTER_RESCUE_EXE` and source-root/instance-root fallback resolution.
    - ArcRasterRescue FileGDB invocation now normalizes `.gdb/` command-path form expected by the patched tool workflow.
    - Stage 01b freshness now treats DAT as canonical and supports DAT-hash sidecars (`04_output-tsaXX.out.input_sha256`) so unchanged DAT content does not repeatedly force manual BatchTIPSY reruns.
    - Stage 01b skips BatchTIPSY freshness gating when `managed_curve_mode != tipsy` (`vdyp_transform` path).
    - `run_vdyp_for_stratum(...)` now resolves relative VDYP executable paths via `FEMIC_SOURCE_ROOT` fallback (matching existing params-path fallback semantics).
  - Linux runtime verification evidence:
    - `P23.3a` rerun (`run-id: k3z_linux_p233a_20260321_r4`) progressed through SiteProd extraction/stacking and pre-VDYP checkpoint generation, then failed at VDYP runtime boundary with:
      `RuntimeError: VDYP executable not found: /tmp/femic_p23a_r4_Ch5Y9R/VDYP7/VDYP7/VDYP7Console.exe`
      (manifest: `/tmp/femic_p23a_r4_Ch5Y9R/vdyp_io/logs/run_manifest-k3z_linux_p233a_20260321_r4.json`, `status=failed`, `exit_code=1`).
    - After adding source-root fallback for VDYP executable resolution, resumed Linux rerun continued past this explicit error but did not yet complete to a clean BatchTIPSY handoff sign-off within this session.
  - `P23.3b` rerun evidence:
    - command:
      `femic tsa post-tipsy --instance-root /tmp/femic_p23b_r5_dC7Rio --run-config config/run_profile.k3z.yaml --tsa k3z --run-id k3z_linux_p233b_20260321_r5_only`
    - freshness guard no longer blocked on DAT/XLSX timestamp mismatch; run advanced into plotting and then failed with:
      `KeyError: 'L'` (from `vdyp_curves_by_scsi.loc[sc, si_level]` in `01b_run-tsa.py`).
    - manifest:
      `/tmp/femic_p23b_r5_dC7Rio/vdyp_io/logs/run_manifest-k3z_linux_p233b_20260321_r5_only.json` (`status=failed`, `exit_code=1`).
  - Phase 23 remains open pending:
    - final Linux run confirmation that Stage 01a reaches the expected BatchTIPSY handoff boundary with the corrected runtime fallbacks, and
    - resolution/characterization of the `KeyError: 'L'` post-TIPSY plotting/indexing failure during Linux resume validation.
- 2026-03-21 (Phase 23 Linux parity follow-up): patch 01b post-TIPSY plotting to tolerate missing `(stratum_code, si_level)` VDYP overlays during resume validation.
  - Scope:
    - keep bundle/table generation behavior unchanged,
    - when a VDYP comparison key is missing, emit a warning and continue plotting TIPSY-managed trajectory rather than raising and aborting.
  - Validation target:
    - rerun `femic tsa post-tipsy` on Linux tmp clone and confirm stale-output guard remains resolved and the previous `KeyError: 'L'` no longer aborts the run.
- 2026-03-21 (Phase 23 Linux parity follow-up outcome): `P23.3b` now passes on Linux; `P23.3a` still pending final clean-start boundary confirmation.
  - Implemented additional 01b resilience fixes after rerun evidence:
    - missing `(stratum_code, si_level)` VDYP comparison keys now emit warnings and continue,
    - missing AU->(stratum, SI) map entries now emit warnings and continue (no hard crash in plotting loop).
  - Linux verification evidence:
    - `P23.3b` pass:
      - command:
        `femic tsa post-tipsy --instance-root /tmp/femic_p23b_r5_dC7Rio --run-config config/run_profile.k3z.yaml --tsa k3z --run-id k3z_linux_p233b_20260321_r8`
      - result:
        downstream bundle tables + plots regenerated; command completed with `status=ok`.
      - manifest:
        `/tmp/femic_p23b_r5_dC7Rio/vdyp_io/logs/run_manifest-k3z_linux_p233b_20260321_r8.json`.
    - `P23.3a` remains open:
      - attempted clean-start rerun (`run-id: k3z_linux_p233a_20260321_r6`) entered full Stage 00 extraction path and was still long-running at session cutoff, so final Stage 01a boundary sign-off remains pending.
  - additional bounded rerun attempt:
    - command:
      `timeout 900 femic run --instance-root /tmp/femic_p23a_r6_KpHxKg --run-config config/run_profile.k3z.yaml --run-id k3z_linux_p233a_20260321_r6_resume --resume`
    - observed behavior:
      entered legacy Stage 00 path (`00_data-prep.py`) and remained long-running without reaching a terminal success/failure boundary within the allotted window; process was terminated to avoid indefinite resource consumption.
- 2026-03-21 (Phase 23 Linux parity corrective implementation scope): execute a targeted parity fix pass before any additional Linux reruns.
  - ArcRasterRescue boundary:
    - Do not treat this as a new runtime design problem.
    - Reuse and codify the existing documented workflow for the patched ArcRasterRescue fork/build used to extract SiteProd rasters from ESRI FileGDB sources.
    - Update runtime path resolution/docs so Linux parity runs point at that existing executable workflow rather than assuming only a local `../ArcRasterRescue/build/arc_raster_rescue.exe` adjacency.
  - BatchTIPSY freshness boundary:
    - Treat `02_input-tsaXX.dat` as the canonical freshness input, not `tipsy_params_tsaXX.xlsx` (human-readable companion only).
    - Replace timestamp-only stale detection with content-aware behavior so unchanged DAT content does not force repeated manual BatchTIPSY reruns.
    - Ensure Stage 01b/post-TIPSY freshness blocking is mode-aware: when managed curves are not `tipsy` (for example `vdyp_transform`), do not require BatchTIPSY output freshness to proceed.
  - Required outputs for this corrective pass:
    - code + tests for ArcRasterRescue executable resolution aligned with documented workflow,
    - code + tests for DAT-authoritative, mode-aware TIPSY freshness behavior,
    - user-facing and agent-facing docs updated to match actual expected operator workflow on Linux and Windows.
- 2026-03-21 (Phase 23 Linux parity rerun after bootstrap hardening): verified Linux runtime bootstrap improvements and re-ran the remaining `P23.3` commands from a Linux host with real annex payload materialization; parity remains blocked by two concrete runtime boundaries.
  - Linux runtime bootstrap recovery completed in-session:
    - installed OS-level `git-annex` (`sudo apt-get install -y git-annex`),
    - enabled DataLad special remote (`git -C external/femic-public-data annex enableremote arbutus-s3`),
    - materialized annex-backed payloads (`datalad get -r external/femic-public-data/data`), including VRI/SiteProd/TSA GDB table files that were missing previously.
  - `P23.3a` rerun evidence:
    - command:
      `femic run --instance-root <tmp_k3z_clone> --run-config config/run_profile.k3z.yaml --run-id k3z_linux_p233a_20260321_r2`
    - preflight passed, but run failed before VDYP execution with:
      `FileNotFoundError: ArcRasterRescue executable not found: ../ArcRasterRescue/build/arc_raster_rescue.exe`
    - manifest:
      `<tmp_k3z_clone>/vdyp_io/logs/run_manifest-k3z_linux_p233a_20260321_r2.json` (`status=failed`, `exit_code=1`).
  - `P23.3b` rerun evidence:
    - command:
      `femic tsa post-tipsy --instance-root <tmp_k3z_clone> --run-config config/run_profile.k3z.yaml --tsa k3z --run-id k3z_linux_p233b_20260321_r2`
    - failed with expected freshness guard:
      `Stale BatchTIPSY output detected: .../04_output-tsak3z.out is older than .../tipsy_params_tsak3z.xlsx`
    - manifest:
      `<tmp_k3z_clone>/vdyp_io/logs/run_manifest-k3z_linux_p233b_20260321_r2.json` (`status=failed`, `exit_code=1`).
  - Phase 23 remains open pending:
    - Linux-accessible SiteProd/ArcRasterRescue path resolution for clean Stage 00->01a execution,
    - fresh BatchTIPSY `04_output-tsak3z.out` regenerated from current handoff before Linux post-TIPSY resume sign-off.
- 2026-03-21 (Phase 23 `P23.6` complete): hardened fresh-clone developer bootstrap and DataLad materialization rituals across agent-facing and user-facing docs.
  - Added explicit agent startup checklist in `AGENTS.md` covering:
    - local `.venv` activation + editable dev install,
    - required runtime smoke commands,
    - DataLad/git-annex + `arbutus-s3` enable + recursive `datalad get`,
    - mandatory `FEMIC_EXTERNAL_DATA_ROOT` export before case preflight/runs.
  - Added a dedicated user-facing guide:
    `docs/guides/developer-environment-bootstrap.rst` and linked it in the guides index.
  - Updated bootstrap/runbook guides to require explicit annex payload materialization:
    - `docs/guides/geospatial-runtime-bootstrap.rst`
    - `docs/guides/public-data-mirror-runbook.rst`
    - `docs/guides/deployment-instances.rst`
    - `docs/guides/cross-platform-runtime-smoke.rst`
    - `docs/guides/stage-01a-vdyp-tipsy-input.rst`
    - `docs/guides/stage-01b-post-tipsy.rst`
    - `docs/guides/pipeline-overview.rst`
  - Added packaging affordances for repeatable setup:
    - new `requirements-dev.txt` (`-e .[dev]`)
    - new `[project.optional-dependencies].dev` in `pyproject.toml`
    - `requirements.txt` now includes `datalad[full]`.
  - Validation passed in local `.venv`:
    - `ruff format src tests`
    - `ruff check src tests`
    - `mypy src`
    - `pytest`
    - `pre-commit run --all-files`
    - `sphinx-build -b html docs _build/html -W`
- 2026-03-20 (Phase 22 kickoff): queued a new optional K3Z treatment-variant workstream for commercial thinning plus 1-3 fertilization treatments.
  - Branches created:
    - parent repo: `feature/k3z-ct-fert-treatment-scaffold`
    - K3Z instance repo: `feature/k3z-ct-fert-treatment-option`
  - Locked planning decision: do not overload `ORIGIN` with CT/fert gating
    states; introduce a separate treatment-path state variable so natural vs
    planted origin semantics remain intact.
  - Initial scope:
    CT only in `FDC+HW-M` and `CW+HW-M` AUs, planted-only eligibility,
    provisional QMD curves, one CT plus optional `fert1`/`fert2`/`fert3`
    treatment chain, all parameterized through K3Z YAML scaffolding.
  - Immediate execution order for this phase:
    YAML contract -> treatment-path state design -> QMD scaffold -> CT curves ->
    fert curves -> K3Z variant rebuild/smoke.
- 2026-03-20 (Phase 21 complete): added generalized K3Z old-growth feature
  attributes and regenerated the tracked instance ForestModel XML.
  - Implemented OG curve generation in `femic.fmg.patchworks`:
    - `og1`: unmanaged-curve-driven linear ramp from CMAI age (`0.0`) to
      peak-yield age (`1.0`).
    - `og2`: fixed policy step at ages `249 -> 0.0`, `250 -> 1.0`.
  - Added per-AU + total feature attributes on both IFM selects:
    `feature.Area.og1.<au_id>`, `feature.Area.og1.total`,
    `feature.Area.og2.<au_id>`, `feature.Area.og2.total`.
  - Added regression test coverage and refreshed XML fixtures to include new
    OG curves/attributes.
  - Rewrote K3Z instance
    `models/k3z_patchworks_model/yield/forestmodel.xml` from current bundle
    tables and confirmed OG labels/curves are present.
- 2026-03-16 (Phase 19 toe-shift correction follow-up): removed the accidental
  second right-shift on toe `c` and confirmed no extended left plateau from
  double-shifting.
  - `fill_curve_left(...)` now treats `toe_shift_years` as inapplicable when
    the toe model already has an explicit location parameter (`popt.size >= 3`,
    as in legacy `fit_func1`); no `c += toe_shift` mutation is performed.
  - Blend-window sizing now keys off the effective shift (zero when location
    already exists), so `toe_shift_years` no longer distorts splice behavior in
    legacy toe fits.
  - Targeted TSA29 `MS_PLI L` rerun still detects the long tail segment and
    selects `tail_blend`, with no `candidate_rejected_non_finite` or
    `non_finite_curve` events.
- 2026-03-16 (Phase 19 toe-shift correction): replaced clamp-based toe shift
  with a location-parameter toe transform so the toe stage no longer injects
  `NaN/Inf` values when `toe_shift_years > 0`.
  - Root cause was `legacy_fit_func2` evaluation on `x=0` values created by
    global age clamping (`x -> max(x-shift, 0)`), yielding `0**(-a)` in toe
    evaluation for early ages.
  - Updated `fill_curve_left(...)` to apply a toe-only location transform
    (softplus shift) before toe fit/eval, and removed global body-age clamping
    from `process_vdyp_out(...)`.
  - Targeted TSA29 `MS_PLI L` rerun now shows no
    `candidate_rejected_non_finite` events; layered candidates are valid and
    fallback selection resolves to `reparameterized_nlls` after fit-gate rescue
    (tail candidate rejected for overshoot, not non-finite values).
- 2026-03-15 (Phase 19 follow-up checkpoint): validated the new 5-year-bin
  substrate + layered tail/toe logic with full QA gates and refreshed the
  TSA29 `MS_PLI L` fit diagnostic artifact.
  - Ran required validation suite successfully:
    `ruff format src tests`, `ruff check src tests`,
    `PYTHONPATH=src python -m mypy src`,
    `PYTHONPATH=src python -m pytest`,
    `python -m pre_commit run --all-files`,
    `sphinx-build -b html docs _build/html -W`.
  - Regenerated `plots/vdyp_fitdiag_tsa29-01-MS_PLI-L.png` from cached
    `vdyp_prep-tsa29.pkl` / `vdyp_results-tsa29.pkl` with current logic.
  - Current rerun telemetry confirms long-tail detection is active
    (`anchor_age=180`, `tail_span_years=120`) but also shows candidate
    validation rejecting tail-blend and left-toe-censor curves for non-finite
    values in this case, leaving `selected_path=primary_nlls`.
  - Next tightening target (without per-case overrides): stabilize toe/candidate
    non-finite handling so layered candidates remain selectable when their
    fitted shapes are structurally valid.
- 2026-03-15 (Phase 19 follow-up complete): switched VDYP fit substrate to
  5-year binned medians and tightened layered censor+tail behavior.
  - Updated `process_vdyp_out(...)` to consume 5-year binned medians for
    body NLLS and tail detection inputs (annual-age medians no longer drive
    fit substrate).
  - Added `build_observed_bins_for_fit(...)` and updated tail detection to
    right-to-left contiguous break scanning with composite straight-ish gate:
    low normalized residual + (high R2 or near-flat slope), plus minimum tail
    span guard.
  - Added new tail defaults/env knobs in stage runtime:
    `FEMIC_TAIL_LINEAR_FLAT_SLOPE_ABS` and
    `FEMIC_TAIL_LINEAR_MIN_SPAN_YEARS`.
  - Updated stage layering policy so structural left-toe discontinuities
    (`skip_delta >= 4`) are accepted and tail blending is selected when a
    valid right-tail segment is detected.
  - Targeted TSA29 `MS_PLI L` rerun now shows:
    `left_toe_censor_selected (skip1_after=6)` and
    `tail_blend_selected` with detected tail anchor near age `180`
    (span `120` years), rather than tiny terminal segments near age `294+`.
- 2026-03-15 (Phase 19 follow-up complete): generalized left-toe discontinuity
  censoring so early low-shoulder/kink failures are handled by fit logic rather
  than per-case smoothing overrides.
  - Updated `_infer_left_toe_censor_skip(...)` in
    `execute_curve_smoothing_runs(...)` to detect:
    - existing early high-spike / sharp-drop outliers, plus
    - symmetric early low-discontinuity outliers (`next_median/current` and
      absolute gap), and
    - local slope-kink discontinuities (initial slope vs following-slope scale).
  - Added a strict non-harm structural acceptance path for left-toe censor
    candidates when inferred censor depth is substantial (default
    `skip_delta >= 4`) and RMSE/tail-RMSE/MAPE remain within tight ratio
    guardrails.
  - Removed the temporary TSA29 `("MS_PLI","L")` tail-shape override so this
    case now relies on generalized fit logic.
  - Targeted rerun for `MS_PLI L` now emits
    `left_toe_censor_selected` (`skip1_after=6`) and selects
    `selected_path=censored_refit` in curve-fit telemetry.
- 2026-03-15 (Phase 19 follow-up complete): corrected TSA29 `MS_PLI L` right-tail
  behavior to enforce a near-linear post-200 shape (not zero-slope clamping).
  - Added TSA29 per-case smoothing override in `vdyp_overrides` for
    `("MS_PLI", "L")`:
    `tail_linear_min_points=20`, `tail_linear_min_r2=0.6`,
    `tail_linear_max_nrmse=0.25`, quantile fallback enabled,
    `tail_anchor_quantile=0.70`, `tail_blend_years=10.0`.
  - Targeted rerun for only `MS_PLI L` confirms `selected_path=tail_blend` with
    effectively linear post-200 tail (very small quadratic term) and refreshed
    fit diagnostic plot `plots/vdyp_fitdiag_tsa29-01-MS_PLI-L.png`.
  - Added regression coverage in `tests/test_vdyp_overrides.py` for the new
    TSA29 case override payload.
- 2026-03-15 (Phase 19 `P19.16` planned): address degenerative selection logic
  that currently preserves catastrophic primary curves in some strata/SI cases.
  - Observed failure pattern from `vdyp_curve_events-tsa29-rerun-20260315T213053Z.jsonl`:
    `MS_PLI H` and `IDF_FDI L` selected `primary_nlls` with catastrophic metrics
    (`MAPE ~= 1.0`, very high RMSE/tail RMSE) while rejecting left-toe-censor
    candidates that drastically improved RMSE/MAPE/tail RMSE.
  - Root-cause hypothesis to validate in code:
    selection applies strict guard-veto precedence (notably early-overshoot)
    without a catastrophic-baseline override, and selected-curve quality gates
    do not currently classify these cases as hard failures.
  - Planned implementation sequence:
    (1) add dominant-recovery override in selection scoring/order,
    (2) add selected-curve catastrophic hard-fail envelope with forced
    re-selection,
    (3) extend decision telemetry with explicit veto/override fields,
    (4) add regression fixtures for reported strata, and
    (5) rerun cached TSA29 + regenerate fit diagnostics + selection summaries.
  - Acceptance evidence for closure:
    reported failure strata must no longer finalize catastrophic primary curves,
    and reviewer-facing logs/summary must explicitly show why the selected path
    won in each case.
- 2026-03-15 (Phase 19 `P19.16a`-`P19.16d` complete): implemented dominant
  recovery selection + catastrophic gate hardening with deterministic telemetry
  and targeted regression coverage.
  - Added `early_underfit` fit metric and catastrophic/underfit gate reasons in
    `execute_curve_smoothing_runs(...)`, including new env knobs:
    `FEMIC_FIT_GATE_CATASTROPHIC_MAPE`,
    `FEMIC_FIT_GATE_MAX_EARLY_UNDERFIT`,
    `FEMIC_DOMINANT_RECOVERY_MAX_METRIC_RATIO`.
  - Added `dominant_recovery` decision logic used by both left-toe-censor and
    tail-blend selection so catastrophic baselines can be replaced when
    candidate RMSE/MAPE/tail-RMSE improvements are decisive.
  - Expanded fit-event telemetry with structured decision payloads and rescue
    audit fields (`rescue_trigger_gate_reasons`, `rescue_order`, `gate_by_path`)
    so veto/override causes are explicit in JSONL logs.
  - Added regression tests:
    - `test_execute_curve_smoothing_runs_selects_dominant_recovery_tail_blend_candidate`
    - `test_summarize_curve_selection_rows_flags_selected_curve_gate_rescue`
  - Targeted TSA29 cached rerun evidence from
    `vdyp_curve_events-tsa29-p1916_rerun_20260315T2212Z.jsonl` shows:
    `MS_PLI H` and `IDF_FDI L` left-toe-censor now selected via
    `dominant_recovery.selected=true` instead of prior catastrophic
    `primary_nlls` retention.
- 2026-03-15 (Phase 19 follow-up complete): moved toe-shift behavior to the
  default fit path so all VDYP smoothing candidates use the same delayed-toe
  shape unless explicitly overridden.
  - `execute_curve_smoothing_runs(...)` now injects `toe_shift_years` into
    baseline/candidate fit kwargs by default (env-backed via
    `FEMIC_VDYP_TOE_SHIFT_YEARS`, default `20.0`).
  - Merchantable-floor candidate generation is now skipped when a positive
    toe-shift is already active, avoiding duplicate post-hoc flattening logic.
  - Added run-profile support for `modes.vdyp_toe_shift_years` so users can set
    per-run defaults in config files; value is exported to runtime env for
    legacy stage execution.
  - Added regression coverage in `tests/test_vdyp_stage.py`,
    `tests/test_vdyp_curves.py`, and `tests/test_pipeline_helpers.py` for
    default/env-config toe-shift behavior and config parsing/env wiring.
- 2026-03-15 (Phase 19 `P19.13c` follow-up complete): corrected merchantable
  floor behavior to preserve smooth toe-ramp shape by shifting the fitted curve
  right (age-delay) instead of hard-clamping the first 20 years to zero.
  - Updated `process_vdyp_out(...)` merchantable-floor path to apply a
    right-shift transform (`x -> x - floor_age`) with floor fill only for
    `x <= floor_age`, preserving the fitted toe curvature after age 20.
  - Added `mode=right_shift` and `shift_years` fields to
    `stage=merchantable_floor` events for explicit audit visibility.
  - Expanded regression coverage in `tests/test_vdyp_curves.py` to assert
    post-floor ages follow the shifted baseline curve rather than flattened
    clamping behavior.
- 2026-03-15 (Phase 19 `P19.15d` complete): tightened curve-path branching and
  selected-curve quality gate behavior.
  - Left-toe censoring now composes with downstream candidates (including
    tail-blend runs) instead of behaving as an exclusive final-path override.
  - Added selected-curve gate rescue logic: if the initial selected curve fails
    fit-quality gate checks, FEMIC now attempts ordered rescue candidates
    (`tail_blend`, `merchantable_floor`, `reparameterized_nlls`,
    `censored_refit`, `primary_nlls`) and emits explicit gate-rescue/unresolved
    warning events.
  - Tail-blend selection thresholds are now env-tunable (`FEMIC_TAIL_SELECT_*`)
    with relaxed defaults so tail blends are admitted more often when primary
    curves are weak but still near non-harm bounds.
  - Added regression coverage in `tests/test_vdyp_stage.py` for composable
    censor+tail behavior and selected-curve gate rescue selection.
- 2026-03-15 (Phase 19 `P19.15` complete): reran TSA29 curve QA with
  updated plotting/fitting policy stack and published curve-stability evidence.
  - Regenerated TSA29 diagnostics with `FEMIC_STRAT_TOP_AREA_COVERAGE=0.80`
    (18 strata; coverage `0.8061826878755755`), including `plots/strata-tsa29.png`
    and all `54` AU overlays (`plots/tipsy_vdyp_tsa29-*.png`).
  - Produced reviewer CSV via `femic vdyp report --selection-summary-out`:
    `vdyp_io/logs/curve_selection_summary-tsa29-20260315T184955Z.csv`
    (`primary_nlls=12`, `tail_blend=19`, `merchantable_floor=22`,
    `censored_refit=1`).
  - Finalized post-TIPSY bundle via
    `vdyp_io/logs/run_manifest-post_tipsy_20260315T190051Z.json`
    and refreshed `data/model_input_bundle/{au_table,curve_table,curve_points_table}.csv`.
  - Published instance evidence in submodule:
    `external/femic-tsa29-instance/evidence/curve_stability_report.20260315.md`
    and
    `external/femic-tsa29-instance/evidence/curve_selection_summary-tsa29-20260315T184955Z.csv`.
- 2026-03-15 (Phase 19 `P19.15a.1` complete): patched THLB raster sampling to
  return fallback values when masked geometries have no valid cells.
  - Updated `mean_thlb_for_geometry(...)` to avoid `np.mean` on empty slices
    and to guard non-finite outputs.
  - Added regression coverage in `tests/test_pipeline_helpers.py` for the
    empty-valid-cell fallback path.
- 2026-03-15 (Phase 19 `P19.15b` complete): added reviewer-facing curve
  selection summary output from VDYP curve-event logs.
  - Added `summarize_curve_selection_rows(...)` in `femic.vdyp.reporting` to
    generate per-stratum/SI rows with selected path plus key fit-path flags
    (fit-quality warning, left-toe, merchantable-floor, tail-blend).
  - Extended `femic vdyp report` with `--selection-summary-out` to emit the
    summary as CSV for reviewer handoff and audit trails.
- 2026-03-15 (Phase 19 `P19.14c` complete): upgraded VDYP fit diagnostics to
  expose selected fit path, blend window context, and residual behavior.
  - Fit diagnostic plot now renders the selected output curve explicitly
    alongside current/candidate curves and prints the selected path in-figure.
  - Added residual subplot (`selected - observed median`) over age bins for
    per-stratum/SI visual QA of systematic fit bias.
  - Added tail-blend window annotation support (anchor/end age estimates) so
    reviewers can see where tail blending is expected to act.
- 2026-03-15 (Phase 19 `P19.14b` complete): added explicit objective selection
  logic for tail-blend vs straight NLLS with deterministic tie-breaks.
  - Added metric-driven tail selection policy requiring strong tail-RMSE
    improvement under non-harm guardrails, with deterministic tie-break when
    tails are near-equal.
  - Added `vdyp_curve_fit` decision events at `stage=tail_blend_selection`
    (selected/rejected) including baseline/candidate metrics and decision
    predicates.
  - Integrated tail selection into fallback output path as `selected_path=tail_blend`
    for non-K3Z when criteria are met; K3Z override behavior remains intact.
- 2026-03-15 (Phase 19 `P19.14a` complete): relaxed tail-linearity defaults and
  moved threshold control to config/env + per-stratum overrides.
  - Tail candidate no longer hard-overwrites threshold values in stage logic;
    it now uses configurable defaults and preserves `kwarg_overrides_for_tsa`
    when provided.
  - Added env-backed defaults for tail thresholds (`FEMIC_TAIL_*`) to enable
    runtime tuning without source edits.
  - Added regression tests verifying both per-stratum override precedence and
    env-default application for tail-blend candidate settings.
- 2026-03-15 (Phase 19 `P19.13d` complete): wired explicit ordered fallback
  selection policy with per-stratum/SI selection events.
  - Selection order now executes as `primary_nlls -> reparameterized_nlls
    (auto-skip) -> censored_refit -> merchantable_floor`, with K3Z-specific
    tail-blend override preserved.
  - Added `vdyp_curve_fit` event `stage=fallback_policy`/`reason=curve_selected`
    for each stratum/SI with selected path, available candidates, and selected
    metrics to make fit-path decisions auditable.
  - Added regression test to verify reparameterized candidate selection and
    fallback-policy event emission.
- 2026-03-15 (Phase 19 `P19.13c` complete): added optional merchantable-volume
  floor candidate (default zero through age 20) with selection diagnostics.
  - `process_vdyp_out(...)` now supports
    `merchantable_floor_enabled/age/value` and logs `merchantable_floor` stage
    events when applied.
  - Stage-level smoothing now evaluates a merchantable-floor candidate when
    baseline pre-merchantable volume is non-trivial, then selects/rejects it
    using pre-age-20 plausibility plus RMSE guardrails.
  - Added regression tests covering both direct floor application in
    `vdyp_curves` and stage-level candidate selection behavior.
- 2026-03-15 (Phase 19 `P19.13b` complete): added left-toe outlier censor
  candidate fit path with deterministic selection logging.
  - Added observed-bin based left-toe outlier detection that proposes
    `skip1` censoring for incoherent early-age points.
  - Added a re-fit candidate using censored vectors and acceptance logic based
    on early-overshoot reduction plus RMSE/MAPE improvement.
  - Added structured `vdyp_curve_fit` events at stage `left_toe_censor`
    indicating selected/rejected decisions with baseline vs candidate metrics.
- 2026-03-15 (Phase 19 `P19.13a` complete): added fit-quality gate warnings for
  implausible VDYP NLLS outputs before downstream acceptance.
  - Added gate checks in curve smoothing for non-finite/negative outputs plus
    metric thresholds (`mape`, `early_overshoot`) and emits structured
    `vdyp_curve_fit` warning events (`stage=fit_quality_gate`) when violated.
  - Added regression coverage that forces an implausible fit and verifies
    `fit_quality_gate_failed` diagnostics are recorded.
- 2026-03-15 (Phase 19 `P19.12` follow-up): fixed strata SI diagnostic x-axis
  floor to `0` so left violin tails are not visually clipped by quantile-based
  windowing.
  - Lower SI bound is now fixed at `site_index_xlim[0]` (default `0`) while
    upper bound remains quantile-focused.
  - Regenerated TSA29 strata diagnostics to confirm rendered SI axis starts at
    `0`.
- 2026-03-15 (Phase 19 `P19.12` follow-up): switched strata diagnostic output
  to PNG-only by default to reduce plot-folder noise.
  - `render_strata_distribution_plot(...)` now writes PDF only when explicitly
    enabled in plot config (`write_pdf=True`).
- 2026-03-15 (Phase 19 `P19.12` complete): improved stratum SI diagnostic
  plotting readability and added auditable clipping metadata.
  - Point overlays now use deterministic thinning and lower default opacity to
    keep violin density visible under heavy sample counts.
  - Plot SI axis now uses quantile-centered windowing with configurable cap and
    padding instead of expanding to extreme outliers.
  - Plot helper now returns clipping/point-count metadata; legacy 01a run logs
    report SI window, total/window/overlay point counts, and low/high clipped
    counts for audit traceability.
- 2026-03-15 (Phase 19 planning note): incorporated TSA29 curve-review feedback
  as new actionable tasks `P19.12`-`P19.15`.
  - Plot readability work (`P19.12`): reduce overplot darkness, thin point
    overlays, and add quantile-focused SI zoom with auditable outlier clipping.
  - NLLS robustness work (`P19.13`): detect failed fits and apply ordered
    auto-reparameterization fallbacks, including left-toe point censoring and
    merchantable-volume floor through age 20.
  - Tail policy work (`P19.14`): relax/redefine tail-linearity and revise
    tail-blend selection criteria against straight NLLS.
  - Validation/evidence work (`P19.15`): rerun TSA29 diagnostics and publish
    fit-path evidence for sign-off before phase closure.
- 2026-03-15 (Phase 19 `P19.11` complete): fixed resume behavior so
  `vdyp_prep-tsaXX.pkl` cannot be reused when pre-VDYP stratification settings
  change (for example `FEMIC_STRAT_TOP_AREA_COVERAGE`).
  - Added signature-aware pre-VDYP checkpoint persistence/validation.
  - Resume now rebuilds pre-VDYP fit payload on signature mismatch instead of
    silently loading stale strata payloads.
- 2026-03-15 (Phase 19 runtime tuning): removed default explicit feature-id
  chunked GDB reads in VDYP source loading to reduce per-query overhead on
  high-memory hosts.
  - New default for explicit feature-id mode is full-layer read + in-memory
    `FEATURE_ID` filter.
  - Chunked `FEATURE_ID IN (...)` reads remain available only when an explicit
    `source_feature_id_chunk_size` is provided.
  - Also removed explicit `driver=\"FileGDB\"` kwargs from these calls to avoid
    `OpenFileGDB ... open option DRIVER` warning spam.
- 2026-03-15 (Phase 19 in-flight run note): current clean TSA29 run is showing
  stratum coverage around `0.656` with ~10 strata (current cutoff), which is
  below preferred operating target.
  - Queue for next run only: tune stratum inclusion/cutoff to target coverage
    near `0.8`.
  - Do not interrupt/restart the currently monitored run; first observe whether
    this run completes with sane output.
  - Keep Phase 20 deferred to a separate feature branch after TSA29 handoff
    readiness is achieved.
- 2026-03-15 (Phase 20 `P20.1` drafted): added execution-ready acceptance
  checklist in `planning/TSA29_dataset_compile_plan.md` covering:
  - scope boundary (VDYP-only),
  - serial/parallel parity invariants + numeric tolerance policy,
  - determinism/hash-repeatability requirements,
  - worker-failure/fallback behavior,
  - observability heartbeat minimums,
  - performance and rollout gates (opt-in first).
- 2026-03-15 (Phase 20 planning note): added a separate, explicitly
  non-blocking phase for VDYP parallelization and long-run observability so
  TSA29 Phase 19 delivery can proceed without waiting on concurrency work.
  - Execution rule: do not block `P19.5`/instance delivery on Phase 20.
  - Phase 20 focuses on opt-in first, with parity checks before any default
    behavior change.
- 2026-03-15 (Phase 19 planning note): added explicit TSA29 investigation task
  on siteprod dependency in compile paths (strata/AU/VDYP/TIPSY/other) with
  decision gate:
  - if not required, disable siteprod in default path and keep it opt-in.
  - if required, harden no-data handling so sparse no-data stands cannot crash
    clean runs.
- 2026-03-14 (Phase 19 `P19.10` complete): executed real TSA29 Woodstock export
  and ws3 smoke gate, then published evidence in the TSA29 instance repo.
  - Generated complete Woodstock package under
    `external/femic-tsa29-instance/output/woodstock_tsa29_validated/`
    (yields/areas/actions/transitions + ws3 bridge `.lan/.are/.yld/.act/.trn`).
  - Executed command:
    `femic instance ws3-smoke --instance-root external/femic-tsa29-instance --woodstock-dir output/woodstock_tsa29_validated --output evidence/ws3_smoke_report.latest.json --ws3-repo-path /home/gep/projects/ws3`.
  - Result: `status=ok`, rows `(y/a/ac/t)=(10050/147959/30/30)`,
    `actions=1`, `inventory_area=2172195.127`.
  - Published TSA29 instance commit with evidence/artifacts:
    `UBC-FRESH/femic-tsa29-instance@afc5f8b`.
- 2026-03-14 (Phase 19 `P19.10` progress): added builtin ws3 model smoke path
  that converts FEMIC Woodstock CSV exports into ws3-ingestible Woodstock
  section files and runs a minimal `ForestModel` compile/schedule check.
  - Added bridge module:
    `src/femic/ws3_bridge.py` with
    `build_ws3_sections_from_femic_woodstock(...)` to generate
    `.lan/.are/.yld/.act/.trn`.
  - Extended ws3 smoke runtime:
    `src/femic/ws3_smoke.py` now supports builtin smoke execution, optional
    `--ws3-repo-path` PYTHONPATH injection, and report fields for bridge output
    location/model name.
  - Extended CLI wiring:
    `femic export dual` now supports
    `--ws3-repo-path`, `--ws3-builtin-smoke`, `--ws3-bridge-dir`;
    `femic instance ws3-smoke` now supports
    `--ws3-repo-path`, `--builtin-model-smoke`, `--ws3-bridge-dir`.
  - Added tests/docs coverage:
    `tests/test_ws3_bridge.py`, updates to
    `tests/test_ws3_smoke.py`, `tests/test_cli_main.py`,
    `tests/test_docs_contract.py`,
    `docs/reference/cli.rst`,
    `docs/reference/api/modules.rst`.
  - Remaining for `P19.10`:
    run this against a real TSA29 Woodstock output + ws3 model workflow and
    publish green ws3 smoke evidence in the TSA29 instance repo.
- 2026-03-14 (Phase 19 `P19.9` complete, `P19.10` in progress):
  implemented dual-output orchestration and ws3 smoke-test command support in
  FEMIC CLI/runtime.
  - Added new export command:
    `femic export dual` to generate Patchworks and Woodstock outputs from the
    same bundle/checkpoint inputs, with optional ws3 smoke execution.
  - Added new instance command:
    `femic instance ws3-smoke` to validate Woodstock datasets and optionally
    execute a ws3 simulation command, emitting JSON evidence.
  - Added `src/femic/ws3_smoke.py` with machine-readable smoke results and
    sanity checks (file presence, row counts, nonzero aggregate volume/area,
    optional command return code and captured logs).
  - Updated docs:
    `docs/reference/cli.rst`,
    `docs/guides/model-input-bundle-and-export.rst`,
    `docs/guides/pipeline-overview.rst`.
  - Added tests:
    `tests/test_ws3_smoke.py` and new CLI wiring checks in
    `tests/test_cli_main.py`.
  - Remaining for `P19.10`:
    execute ws3 smoke against an actual ws3 model instance path and capture
    green evidence in TSA29 instance repository workflows.
- 2026-03-14 (Phase 19 extension - dual-output + ws3 integration):
  extended TSA29 planning so the pipeline must fork to both Patchworks and
  Woodstock outputs, with ws3 simulation smoke tests as required validation.
  - Created feature branch for this workstream firewall:
    `feature/compile-tsa29-instance-ws3-fork`.
  - Rewrote plan doc:
    `planning/TSA29_dataset_compile_plan.md` with explicit:
    - fork-stage contract (`Patchworks` and `Woodstock` outputs),
    - ws3 ingestion and simulation smoke-test workflow,
    - ws3 evidence artifacts and sanity gates.
  - Added new open Phase 19 tasks:
    `P19.9` (dual-output contract) and
    `P19.10` (ws3 smoke-test gate).
- 2026-03-14 (Phase 19 kickoff + initial delivery):
  published initial standalone TSA29 instance repository and linked it back into
  FEMIC.
  - Published repo/tag:
    `https://github.com/UBC-FRESH/femic-tsa29-instance` @ `v0.1.0`.
  - Completed deliverables:
    - authored instance contract in
      `planning/tsa29-instance-contract.md`,
    - bootstrapped TSA29 repo structure/config/rebuild runbook/docs,
    - assembled thin snapshot payload with curated TSA29 artifacts + checksums,
    - added evidence baseline artifact
      `evidence/reference_rebuild_report.latest.json`,
    - added FEMIC submodule link at `external/femic-tsa29-instance`,
    - added FEMIC TSA29 pointer docs and docs-contract tests.
  - Intentional thin-instance policy:
    very large artifacts were externalized and referenced via
    `metadata/large_artifacts.sha256` and output manifest docs.
  - Remaining step for full phase closure (`P19.5`):
    run full Patchworks-enabled rebuild in a validated runtime host and publish
    a green evidence update replacing the current warning-state baseline.
- 2026-03-12 (Phase 18 `P18.3` + `P18.4` complete): published
  `femic==0.1.1a1` to production PyPI via trusted publisher and validated
  post-release smoke install in workflow.
  - Green production run:
    `https://github.com/UBC-FRESH/femic/actions/runs/23024083304`
  - Published artifacts (from PyPI API):
    - `femic-0.1.1a1-py3-none-any.whl`
      `sha256=09c8dfca3539815b149dee77145ba525eae33f239e88a3e3e63879d6fcc0d699`
    - `femic-0.1.1a1.tar.gz`
      `sha256=10fb2e43abdecb0dcee5c40096230462aca9cab5e2cc7c28687a7bd8258154d7`
  - Release summary:
    Phase 18 checklist is now fully complete (`P18.1`–`P18.4`).
- 2026-03-12 (Phase 18 `P18.2` complete): published pre-release
  `femic==0.1.1a1` to TestPyPI with successful end-to-end smoke install in
  GitHub Actions.
  - Version bump:
    `pyproject.toml` from `0.1.0` -> `0.1.1a1` (PEP 440 pre-release).
  - Workflow hardening:
    - aligned `.github/workflows/publish-pypi.yml` with TestPyPI safety
      behavior (`skip-existing: true` + smoke install step),
    - added index-propagation retry loops to both publish workflows to handle
      TestPyPI/PyPI indexing lag after upload.
  - Green TestPyPI run:
    `https://github.com/UBC-FRESH/femic/actions/runs/23023751656`.
  - Prior failed attempt (diagnosed and fixed):
    publish succeeded, smoke install failed due immediate index lag:
    `https://github.com/UBC-FRESH/femic/actions/runs/23023687076`.
  - Next:
    execute `P18.3` production PyPI publish using the now-matched workflow and
    then complete `P18.4` traceability recording.
- 2026-03-12 (Phase 18 `P18.3` execution attempt): production publish workflow
  is blocked by PyPI trusted-publisher configuration (not by workflow/build
  logic).
  - Failing run:
    `https://github.com/UBC-FRESH/femic/actions/runs/23023862800`
  - Failure:
    `invalid-publisher` during OIDC exchange in `Publish to PyPI`.
  - Emitted claims:
    - `sub`: `repo:UBC-FRESH/femic:environment:pypi`
    - `repository`: `UBC-FRESH/femic`
    - `workflow_ref`:
      `UBC-FRESH/femic/.github/workflows/publish-pypi.yml@refs/heads/main`
    - `ref`: `refs/heads/main`
    - `environment`: `pypi`
  - Next unblock action:
    create/update matching trusted publisher on production PyPI, then rerun
    `publish-pypi`; smoke step is already wired and will verify install.
- 2026-03-12 (Phase 18 workflow bugfix): fixed TestPyPI smoke step shell
  parsing error after successful publish.
  - Root cause:
    `publish-testpypi.yml` used brittle nested quoting in the version-detection
    command, producing shell parse error near `tomllib.loads(...)`.
  - Fix:
    simplified version extraction command to a single robust Python `-c`
    invocation in `.github/workflows/publish-testpypi.yml`.
  - Validation gates passed locally:
    `ruff format`, `ruff check`, `mypy`, `pytest`, `pre-commit --all-files`,
    `sphinx-build -W`.
- 2026-03-12 (Phase 18 docs clarification): added validated TestPyPI
  token-free bootstrap path to release runbook to remove ambiguity when no
  project-level "Add project" button is visible.
  - Updated `docs/guides/pypi-release-runbook.rst` with account-level
    TestPyPI pending-publisher flow:
    `https://test.pypi.org/manage/account/publishing/`.
  - Added explicit notes that first successful OIDC publish creates the
    TestPyPI project automatically and attaches the publisher.
  - Kept token upload documented only as fallback, not primary path.
- 2026-03-12 (Phase 18 `P18.2` execution attempt): triggered
  `publish-testpypi` workflow and confirmed current blocker is trusted
  publisher configuration, not packaging artifacts.
  - Workflow run:
    `https://github.com/UBC-FRESH/femic/actions/runs/23022440859`
    failed at `Publish to TestPyPI` with `invalid-publisher`.
  - Claims emitted by GitHub for debugging:
    - `repository`: `UBC-FRESH/femic`
    - `workflow_ref`:
      `UBC-FRESH/femic/.github/workflows/publish-testpypi.yml@refs/heads/main`
    - `environment`: `testpypi`
  - Updated `docs/guides/pypi-release-runbook.rst` with explicit trusted
    publisher setup requirements for TestPyPI/PyPI and troubleshooting steps.
  - Next action for `P18.2`:
    configure matching trusted publisher entries on TestPyPI, then re-run
    `publish-testpypi` and perform install smoke.
- 2026-03-12 (Phase 17 docs refinement): switched K3Z appendix from
  filename-only inventory to inline-rendered figures in the standalone
  instance docs.
  - Updated `external/femic-k3z-instance/docs/figure-appendix.rst` to embed:
    analysis-area map, strata figure, all VDYP LMH envelopes, all VDYP fit
    diagnostics, and all TIPSY-vs-natural overlay plots.
  - Retained filename references in captions for traceability/QA.
  - Updated docs contract checks in `tests/test_docs_contract.py` to require
    new appendix section headings and figure directives.
  - Validation checks passed:
    `pytest tests/test_docs_contract.py`,
    `sphinx-build -b html external/femic-k3z-instance/docs ... -W`,
    `sphinx-build -b html docs _build/html -W`.
- 2026-03-12 (Phase 18 `P18.1` completion + `P18.2/P18.3` automation prep):
  added deterministic packaging runbook + CI/workflow scaffolding for staged
  TestPyPI -> PyPI publication.
  - Added release runbook:
    `docs/guides/pypi-release-runbook.rst` and wired it in
    `docs/guides/index.rst`.
  - Added local helper:
    `scripts/release_package_checks.sh` to run
    `python -m build`, `twine check`, wheel install smoke, and a wheel
    reproducibility check under fixed `SOURCE_DATE_EPOCH`.
  - Updated CI packaging workflow:
    `.github/workflows/package-release-checks.yml` now sets deterministic build
    epoch and enforces wheel reproducibility across consecutive builds.
  - Added staged publish workflows:
    `.github/workflows/publish-testpypi.yml` and
    `.github/workflows/publish-pypi.yml` (OIDC/trusted-publisher ready).
  - Updated user-facing release instructions in `README.md` to point to the
    runbook and helper script.
  - Validation gates passed:
    `ruff format`, `ruff check`, `mypy`, `pytest (491 passed)`,
    `pre-commit --all-files`, `sphinx-build -W`, and
    `scripts/release_package_checks.sh`.
  - Remaining for Phase 18 completion:
    run actual TestPyPI and PyPI publish executions (`P18.2`/`P18.3`) once
    publisher credentials/trust bindings are active; then record final
    artifact/version traceability (`P18.4`).
- 2026-03-12 (Phase 17 `P17.4` completion): converted FEMIC K3Z page to
  pointer/overview model and aligned docs contracts to submodule-first
  ownership.
  - Replaced `docs/sample-models/k3z.rst` with a concise pointer page linking:
    - canonical repo/docs:
      `https://github.com/UBC-FRESH/femic-k3z-instance`,
      `https://ubc-fresh.github.io/femic-k3z-instance/`,
    - submodule sync commands and FEMIC-local integration paths.
  - Updated `tests/test_docs_contract.py` K3Z sample-model assertions to
    enforce pointer-page contract (required sections + canonical links +
    submodule commands), replacing old deep narrative heading checks.
  - Phase 17 checklist now fully complete (`P17.0`–`P17.5`).
  - Validation gates passed:
    `ruff format`, `ruff check`, `mypy`, `pytest (490 passed)`,
    `pre-commit --all-files`,
    `sphinx-build -W` for parent docs and standalone
    `external/femic-k3z-instance/docs`.
- 2026-03-12 (Phase 17 `P17.1/P17.2/P17.3/P17.5` completion): expanded
  standalone K3Z student docs to TSR-style structure with area accounting, map,
  and full figure appendix coverage.
  - Updated standalone guide IA in
    `external/femic-k3z-instance/docs/index.rst` to include
    `figure-appendix.rst` and keep K3Z docs rooted in submodule Sphinx.
  - Extended
    `external/femic-k3z-instance/docs/land-base-and-netdown.rst` with:
    - analysis-area map section using generated
      `docs/_static/k3z_analysis_area_map.png`,
    - total analysis area/THLB summary table,
    - AU-level area accounting table (14 AUs),
    - explicit THLB netdown placeholder table with zeroed reductions.
  - Extended
    `external/femic-k3z-instance/docs/base-case-analysis.rst` with appendix
    linkage so interpretation sections reference canonical figures.
  - Added new
    `external/femic-k3z-instance/docs/figure-appendix.rst` containing:
    - core teaching figure catalog with captions,
    - full inventory list of all current `plots/*tsak3z*` artifacts.
  - Updated
    `external/femic-k3z-instance/docs/data-package-crosswalk.rst` to map TSR
    figure/map exhibits to the new appendix and linked pages.
  - Added/expanded docs contract checks in `tests/test_docs_contract.py` for:
    - required `figure-appendix` navigation entry,
    - required new land-base section headings,
    - required appendix anchor/content and base-case appendix references.
  - Validation gates passed:
    `ruff format`, `ruff check`, `mypy`, `pytest (490 passed)`,
    `pre-commit --all-files`,
    `sphinx-build -W` for both parent docs and standalone
    `external/femic-k3z-instance/docs`.
- 2026-03-12 (Phase 16 `P16.2` completion): finished public-surface docstring
  coverage for FEMIC Python modules and normalized command/helper docstrings.
  - Added/normalized missing public docstrings in:
    `src/femic/__main__.py`,
    `src/femic/cli/main.py`,
    `src/femic/patchworks_runtime.py`,
    `src/femic/pipeline/io.py`,
    `src/femic/pipeline/plots.py`,
    `src/femic/pipeline/tipsy_legacy.py`,
    `src/femic/rebuild_runner.py`,
    `src/femic/vdyp/reporting.py`.
  - Verified public-surface docstring completeness with a static AST scan
    (`missing count: 0` for non-private defs in `src/femic`, excluding
    resources payload modules).
  - Kept behavior unchanged (documentation-only updates in code paths).
- 2026-03-12 (Phase 16/17 execution kick-off): synced K3Z submodule baseline
  and landed initial FEMIC API reference scaffolding with guardrails.
  - Completed `P17.0` by fast-forwarding
    `external/femic-k3z-instance` from `e3285ad` to `9748707`, restoring
    standalone docs scaffold and `config/rebuild.spec.yaml` expected by
    contract tests.
  - Completed `P16.1` by adding API contract policy page:
    `docs/reference/api/index.rst` (public module scope, exclusions, and
    private-member policy).
  - Completed `P16.3` by wiring API docs into Sphinx:
    `docs/index.rst` now links `reference/api/index`;
    `docs/reference/api/modules.rst` enumerates public modules for generated
    API stubs.
  - Completed `P16.4` by extending docs contract tests in
    `tests/test_docs_contract.py` to require API reference pages and expected
    module entries.
  - Updated Sphinx config in `docs/conf.py` to add `src/` import path so
    autodoc/autosummary can resolve `femic` modules during docs build.
  - Validation gates (this checkpoint): `ruff format`, `ruff check`, `mypy`,
    `pytest` (`490 passed`), `pre-commit --all-files`, and
    `sphinx-build -W` all passed.
- 2026-03-12 (Phase 16-18 roadmap extension lock-in): added the
  decision-complete implementation plan for API docs coverage, submodule-first
  K3Z student docs, and staged package publication.
  - Added new roadmap phase checklists:
    - `Phase 16: Full Developer API Documentation Coverage (FEMIC Package)`
    - `Phase 17: K3Z TSR-Style Student Documentation (Submodule-First)`
    - `Phase 18: Packaging and Publication to PyPI`
  - Locked documentation model:
    `external/femic-k3z-instance/docs/` is canonical for student-facing K3Z
    content, while FEMIC docs keep a short pointer/overview page.
  - Locked API docs policy defaults:
    Google-style docstrings, public-surface API publication, and
    autosummary/autodoc Sphinx coverage for `src/femic` public modules.
  - Locked release flow:
    package publication executes via TestPyPI validation first, then PyPI.
  - Implementation reminder:
    current local submodule checkout is behind upstream and lacks a local docs
    tree; `P17.0` must sync `external/femic-k3z-instance` before docs work.
- 2026-03-11 (repo-root cleanup: legacy notebook archive move):
  moved legacy notebook artifacts out of repository root into a dedicated
  archive location.
  - Moved notebook files:
    `00_data-prep.ipynb`, `01a_run-tsa.ipynb`, `01b_run-tsa.ipynb` ->
    `reference/legacy_notebooks/`.
  - Updated docs/test references to the new notebook location:
    `docs/guides/legacy-traceability.rst`,
    `docs/guides/index.rst`,
    `tests/test_docs_contract.py`.
  - Verified contract/tests/docs build remain green after relocation.
- 2026-03-11 (K3Z species-account bugfix: TIPSY `FD` alias to canonical `FDC`):
  fixed treated species-proportion mapping so species-wise accounts no longer
  drop `FDC` to zero when TIPSY outputs `FD`.
  - Updated bundle assembly in `src/femic/pipeline/bundle.py` to normalize
    TIPSY species aliases (`FD -> FDC`) before writing treated species-prop
    curves.
  - Added regression test
    `tests/test_bundle.py::test_build_bundle_tables_from_curves_maps_tipsy_fd_to_fdc`.
  - Re-ran K3Z post-TIPSY bundle + Patchworks export and verified
    `managed_prop_FDC_985521000004` now exports with `y=0.1`, and
    `au_985501000_managed_yield_FDC` is no longer a flat zero curve.
- 2026-03-10 (P8.7 docs QA + acceptance checks): added automated docs
  contract coverage for Sample Models navigation and required K3Z sections,
  and added a release-readiness checklist for student distribution.
  - Extended `tests/test_docs_contract.py` with:
    - Sample Models toctree/page existence checks (`k3z`, `k3z-metadata-lineage`),
    - required heading checks for `docs/sample-models/k3z.rst`,
    - required heading checks for
      `docs/sample-models/k3z-metadata-lineage.rst`.
  - Added `Release Readiness Checklist` section to
    `docs/sample-models/k3z.rst`.
  - Marked `P8.7a/P8.7b/P8.7c` complete.
- 2026-03-11 (Phase 8 `P8.6d` complete: regenerated strata/AU plot rollout):
  integrated regenerated K3Z strata/AU QA plot artifacts into user-facing
  Sample Models documentation.
  - Added new section `Regenerated Strata/AU Build Plots` to
    `docs/sample-models/k3z.rst` with explicit artifact families:
    `plots/strata-tsak3z.png`, `plots/vdyp_lmh_tsak3z-*.png`,
    `plots/tipsy_vdyp_tsak3z-*.png`.
  - Updated K3Z release checklist to require regenerated plot presence prior to
    student distribution.
  - Extended `tests/test_docs_contract.py` K3Z section contract to require the
    new plot section and artifact-pattern references.
  - Marked `P8.6d` complete; with `P8.6a/P8.6b/P8.6c` already complete, parent
    `P8.6` is now complete.
- 2026-03-11 (Phase 8 status normalization): parent `P8.3` marked complete
  because all child items (`P8.3a/P8.3b/P8.3c`) were already completed.
- 2026-03-11 (Phase 10 status normalization): parent `P10.1`, `P10.2`, and
  `P10.3` marked complete because all child items were already completed.
- 2026-03-10 (P8.5 scenario interpretation guidance): completed trajectory
  interpretation guidance for classroom scenario analysis in K3Z docs.
  - Added `Scenario Comparison Guidance` to `docs/sample-models/k3z.rst`
    covering within-scenario and cross-scenario comparison workflow.
  - Added explicit treatment-shift interpretation guidance using
    `product.Seral.area.<stage>.<au_id>.CC` trajectories.
  - Added a minimum report-template matrix mapping analytical questions to
    account sources and aggregation patterns for student exercises.
  - Marked `P8.5a/P8.5b/P8.5c` complete.
- 2026-03-10 (P8.2c + P8.4c completion): expanded K3Z guide with explicit
  student-facing parameter risk ranges and backup/recovery conventions.
  - Added `Parameter Risk and Suggested Ranges` section to
    `docs/sample-models/k3z.rst` covering IFM share/threshold tuning,
    topology radius, seral boundaries, CC min-age behavior, and horizon risk.
  - Added `Backup and Recovery Conventions` section to document run-log
    retention, automatic `accounts.csv` timestamp backups, and regeneration-
    first recovery practices.
  - Marked `P8.2c` and `P8.4c` complete; with this, `P8.2` and `P8.4` are
    now fully complete.
- 2026-03-10 (P8.1 metadata + lineage baseline): completed initial K3Z
  metadata lineage capture for student-facing use and future rebuild governance.
  - Added docs page `docs/sample-models/k3z-metadata-lineage.rst` with:
    source inventory for `data/`, `yield/`, `blocks/`, explicit lineage chain,
    and a provenance versioning policy/checklist.
  - Added machine-readable registry
    `models/k3z_patchworks_model/metadata/lineage_registry.yaml` encoding
    artifact-to-source mappings, builder commands, and provenance rules.
  - Wired metadata page into Sample Models docs navigation
    (`docs/sample-models/index.rst`) and linked from K3Z guide.
  - Marked `P8.1a/P8.1b/P8.1c` complete.
- 2026-03-10 (P6.4 onboarding regression scenarios): completed the queued
  onboarding regression test slice by adding template-driven case preflight and
  docs-linkage contract coverage.
  - Added `tests/test_case_preflight_cli.py` scenarios for:
    - smoke instantiation from `config/run_profile.case_template.yaml` +
      `config/tipsy/template.case.yaml` (new TSA code) passing
      `femic prep validate-case`;
    - boundary-mode compatibility using template-derived profile
      (`selection.boundary_path`/`selection.boundary_code`) with matching
      `tsa<boundary_code>.yaml` config.
  - Added docs contract check in `tests/test_docs_contract.py` requiring
    `docs/guides/case-onboarding.rst` to keep links to both onboarding
    templates plus the `femic prep validate-case` command.
  - Marked `P6.4a/P6.4b/P6.4c` complete.
- 2026-03-10 (Sample Models docs + K3Z deep-dive launch): added a new
  top-level Sphinx "Sample Models" section and published a detailed K3Z guide at
  `docs/sample-models/k3z.rst`, anchored to the in-repo authoritative model
  state at `models/k3z_patchworks_model/`.
  - Documented purpose/scope, provenance, full component mapping, rebuild
    commands, runtime pathing, and matrix-builder artifact expectations.
  - Explicitly documented post-build accounts promotion behavior:
    `tracks/protoaccounts.csv -> tracks/accounts.csv` with timestamped backup.
  - Added user guidance for assumptions/parameters, edit policy, seral account
    semantics, and common troubleshooting signatures.
  - Added new planning phase `Phase 8` to drive full student-facing K3Z
    metadata/how-to documentation to completion.
  - Marked completed Phase 8 starter tasks in checklist form (`P8.2a/P8.2b`,
    `P8.3a/P8.3b/P8.3c`, `P8.4a/P8.4b`, `P8.6a/P8.6b/P8.6c`) so roadmap
    progress reflects delivered docs work.
- 2026-03-09 (THLB/IFM tuning for Patchworks export): confirmed legacy 00 THLB
  assignment logic is still in effect (`assign_thlb_area_and_flag` with fixed
  thresholds 93/69/50 and `thlb_raw` expected on percent-like scale), and added
  explicit export-time IFM tuning controls to avoid guesswork when checkpoints
  carry continuous THLB values (for example `[0,1]`).
  - New `femic export patchworks` options:
    - `--ifm-source-col` (explicit THLB signal column, e.g. `thlb_raw`)
    - `--ifm-threshold` (managed when signal > threshold)
    - `--ifm-target-managed-share` (top-N stands managed by signal rank)
  - `--ifm-threshold` and `--ifm-target-managed-share` are mutually exclusive.
  - This keeps legacy defaults unchanged unless an operator opts into tuning.
- 2026-03-09 (1:1 blocks + topology pipeline step): added
  `femic patchworks build-blocks` to compile a sample-aligned blocks package
  from `data/fragments.shp` with strict stand:block identity (`BLOCK` copied
  from `FEATURE_ID`/`FRAGS_ID`) and optional topology generation.
  - Output contract:
    - `<model>/blocks/blocks.shp`
    - `<model>/blocks/topology_blocks_<radius>r.csv` (default radius `200`)
  - Topology CSV schema matches Patchworks sample usage:
    `BLOCK1,BLOCK2,DISTANCE,LENGTH`, including exterior `-9999` rows for PIN
    `control.inputTopology(...)` wiring.
  - Live validation completed on
    `C:\Users\gep\Documents\msfm\msfm2025\k3z_patchworks_model` with
    `blocks=218` and `edges=928` at `200m` radius.
- 2026-03-09 (Windows runtime config path correction): updated
  `config/patchworks.runtime.windows.yaml` paths from stale Desktop location to
  active model root under
  `C:\Users\gep\Documents\msfm\msfm2025\k3z_patchworks_model`.
- 2026-03-09 (K3Z script adaptation): replaced
  `C:\Users\gep\Desktop\msfm2025\k3z_patchworks_model\scripts\dataPrep\prepareBlocks.bsh`
  with a FEMIC-aligned variant that:
  - targets `data/fragments.*`, `yield/forestmodel.xml`, and `tracks/`,
  - requires `yield/forestmodel.xml` explicitly (no C5 fallback filename),
  - runs Matrix Builder through `new ca.spatial.tracks.builder.Process(...).execute(false)`,
    then waits on the process object for completion,
  - keeps C5-style dissolve/join steps as optional toggles and skips safely when
    lookup inputs are missing.
- 2026-03-09 (K3Z Patchworks model layout reorg): created
  `C:\Users\gep\Desktop\msfm2025\k3z_patchworks_model` with top-level folders
  mirroring Patchworks `sample_2024` structure (`analysis`, `blocks`, `data`,
  `imagery`, `misc`, `roads`, `scenarios`, `scripts`, `tracks`, `yield`).
- Copied K3Z runtime artifacts into sample-aligned locations:
  - fragments shapefile set -> `...\k3z_patchworks_model\data\fragments.*`
  - ForestModel XML -> `...\k3z_patchworks_model\yield\forestmodel.xml`
  - seeded scripts from `reference/Patchworks-202502/sample_2024/scripts/`.
- Updated `config/patchworks.runtime.windows.yaml` matrix builder paths to use
  the new K3Z model root and verified a successful matrix build run
  (`run_id=win_native_k3z_reorg_20260309`, `returncode=0`) writing tracks to
  `...\k3z_patchworks_model\tracks`.
- 2026-03-09 (Windows-first Patchworks runtime): updated
  `femic patchworks` to support native Windows launch (`java -jar ...`) in
  addition to Linux/Wine, instead of hard-requiring Wine on all hosts.
- 2026-03-09 (matrix-build completion semantics): aligned with Patchworks
  `Process.main(argv)` behavior by treating non-interactive run success as
  artifact-driven (tracks output present + no fatal signatures), recording both
  raw JVM return code and effective FEMIC return code in run manifests.
- 2026-03-09 (matrix output precondition): matrix output directory is now
  created automatically before non-interactive launch to satisfy Patchworks
  constructor requirements (`outName` must exist).
- Completed `P6.3`: added `femic export release` for versioned student-facing
  bundle packaging with strict required-artifact checks, release manifest
  (`release_manifest.json`), and operator handoff notes (`HANDOFF.md`).
- Added release packaging tests and CLI/docs wiring; next queued work starts at
  `P6.4` (onboarding regression scenario tests + docs linkage checks).
- Started Phase 7 runtime integration for proprietary Patchworks tooling:
  added `femic patchworks preflight` and `femic patchworks matrix-build` command
  skeletons with config-driven Wine invocation, Matrix Builder command assembly,
  run log capture, and execution manifest output.
- Added a baseline Patchworks runtime config (`config/patchworks.runtime.yaml`)
  for local editing, and gitignored `reference/Patchworks/` to avoid publishing
  proprietary binaries/API docs.
- Added Phase 7 docs/test wiring for Patchworks runtime and VPN diagnostics;
  verified `reference/Patchworks/` is now ignored and not tracked in git index;
  remaining queued Phase 7 work is first live VPN+Wine validation against the
  real license server environment.
- Updated Patchworks runtime licensing behavior to match real Patchworks
  ownership: `femic patchworks preflight` now validates env/config only
  (`SPS_LICENSE_SERVER`, `SPSHOME`, Wine/Java/jar/input paths) and no longer
  performs direct DNS/TCP checks against inferred license ports/hosts.
- Added required `patchworks.spshome` runtime config support and propagated
  `SPSHOME` injection into Wine subprocess env for `matrix-build` runs.
- Live validation (2026-03-09): `patchworks preflight` now passes in-container
  with `SPSHOME` set to the Wine-visible local Patchworks path, but
  `patchworks matrix-build` still fails internally despite shell return code 0.
  Current blockers from stderr are:
  `no mrsidget2_64 in java.library.path`, GUI/X11 peer creation failures
  (`$DISPLAY` missing), and final license message
  `Not licensed or no connection to license server`; no `tracks/` output
  directory is produced.
- Next queued Phase 7 work: harden matrix-build success detection beyond process
  return code (stderr signature + required output artifact checks), then resolve
  runtime prerequisites (headless/GUI mode compatibility and Patchworks native
  library path) before re-testing VPN/license pass-through.
- Completed matrix-build hardening pass:
  - `patchworks.use_xvfb` config support (wraps launch with `xvfb-run -a`);
  - Windows-side `SPSHOME`/`PATH` injection plus `-Djava.library.path` in
    java launch command;
  - deterministic failure promotion when fatal runtime signatures are found in
    process output or when matrix output directory is missing/empty.
- Live rerun now fails deterministically with explicit blockers:
  `Not licensed or no connection to license server`,
  `IP Helper Library GetAdaptersAddresses function failed`, and missing
  matrix output artifacts.
- Matrix Builder validation from user Windows workstation identified a
  ForestModel schema-order issue (`<input>` unexpectedly encountered near top of
  document). Exporter now emits ForestModel child elements in schema-compatible
  order aligned with current Patchworks samples:
  curves -> define -> input/output -> select.
- Regenerated Patchworks fixtures and re-exported
  `output/patchworks_k3z_validated/forestmodel.xml` with corrected ordering for
  external Matrix Builder retest.
- Follow-up Windows Matrix Builder parse error identified select expression type
  mismatch (`AU` integer column compared to string literal). Exporter now emits
  numeric AU predicates (`AU eq 985501000`) while keeping quoted string
  predicates for `IFM`/`treatment`.
- Re-exported K3Z ForestModel XML with numeric AU expressions for immediate
  external retest.
- Additional Windows Matrix Builder validation shows schema engine mismatch with
  legacy DTD header expectations. Exporter now emits Patchworks XSD model hint
  header (`<?xml-model href="https://www.spatial.ca/ForestModel.xsd"?>`) in
  place of the old DOCTYPE line to align with 2024/2025 sample model format.
- Live preflight now resolves local file paths and Java-in-Wine checks in this
  container; remaining blockers are matrix runtime dependencies and effective
  Patchworks licensing at launch time.
- Phase 6 kickoff complete: added reusable onboarding assets for new cases:
  `config/run_profile.case_template.yaml`, `config/tipsy/template.case.yaml`,
  and `docs/guides/case-onboarding.rst`.
- Guides navigation now includes a dedicated onboarding page so new-case setup
  is discoverable in published docs.
- Next queued work starts at `P6.2` (single-command case preflight validation).
- Completed `P6.2`: added `femic prep validate-case` to run profile-aware
  prerequisite checks (boundary/path integrity, TIPSY config presence/validity,
  external dataset presence, log-dir warnings) with remediation messages and
  optional `--strict-warnings` failure mode.
- Added regression coverage in `tests/test_case_preflight_cli.py` for preflight
  success and key failure paths (missing TIPSY config, missing boundary code,
  strict warnings), and extended docs drift checks for the new CLI options.
- Next queued work starts at `P6.3` (student-facing release packaging workflow).
- Phase 5 docs recovery milestone completed locally: added a new Guides section
  (`docs/guides/*`), a notebook-to-guides coverage matrix
  (`docs/guides/legacy_notebook_coverage.csv`), and a legacy traceability page
  (`docs/guides/legacy-traceability.rst`) so notebook narrative knowledge is now
  explicitly preserved in published docs.
- Added docs contract tests in `tests/test_docs_contract.py` to enforce guide
  page presence, toctree wiring, notebook markdown coverage completeness, and
  high-value CLI docs drift checks.
- Completed GitHub Pages deployment validation (`P5.7`) after push to `main`:
  verified Guides nav renders and direct guide URLs return HTTP 200.
- Updated docs workflow deploy guard in `.github/workflows/docs-pages.yml` to
  allow deployment for both push and manual `workflow_dispatch` runs on `main`
  (still excludes pull requests).
- `PYTHONPATH=src python -m femic --help` now works in the venv.
- `pyproject.toml` defines the `femic` console script; install with `pip install -e .` when ready.
- Added a legacy workflow wrapper that runs `00_data-prep.py` and honors `--tsa`/`--resume`.
- `femic run` now performs preflight checks (use `--skip-checks` to bypass).
- Legacy bundle handling now targets `data/model_input_bundle` only (no legacy auto-copy).
- Removed legacy `data/spadescbm_bundle` directory.
- Normalized `tsa_code`/`tsa` to zero-padded strings to prevent resume-time index mismatches.
- Added a guard that fails fast with a summary when AU assignment yields zero rows.
- Rebuilds `scsi_au` from `au_table` when resuming so curve assignment can proceed.
- Added a `--debug-rows` CLI option to downsample VRI rows for faster iteration.
- Debug row limiting now re-applies after checkpoint reloads to avoid full-size fallbacks.
- Fixed debug row helper ordering so checkpoint loads can call it safely.
- Skips strata lacking VDYP curves to avoid debug-run crashes.
- Debug runs now disable cached checkpoint and output reuse.
- External dataset paths now resolve relative to repo root (`../data`).
- Added external data root override via `FEMIC_EXTERNAL_DATA_ROOT`.
- Fixed raster masking calls to wrap geometries in lists (rasterio expects iterables).
- AU/curve assignment now tolerates missing stratum+SI mappings and logs a warning summary before
  dropping unmapped rows.
- Added `planning/VDYP_debug_notes.md` and queued a VDYP diagnostics + metadata
  hardening focus.
- Added VDYP run and curve-fit diagnostics logs plus toe-fit auto-trimming with warnings to keep
  the pipeline moving while recording failures.
- Updated curve anchoring to quasi-origin `(1, 1e-6)` so zero-value filtering can stay strict.
- Added pre-VDYP TSA checkpointing (`data/vdyp_prep-tsa{tsa}.pkl`) for faster warm-starts.
- Pre-VDYP checkpoint payloads now strip non-picklable fit callables for reliable resume loads.
- Added minimal validation scaffolding: `tests/`, `docs/`, and `.pre-commit-config.yaml`.
- Verified TSA 08 rerun writes `vdyp_io/logs/vdyp_curve_events.jsonl` entries with
  `first_age=1.0` and `first_volume=1e-06`.
- Added `femic vdyp report` to summarize `vdyp_runs.jsonl` + `vdyp_curve_events.jsonl`
  (status/stage/phase counts, parse errors, first-point conformance, mismatch samples).
- Added fallback handling for `nsamples="auto"` with small strata so VDYP runs all available
  records instead of raising `AssertionError`.
- Added explicit warnings + JSONL metadata when curve build/tipsy-input stages encounter
  missing VDYP outputs for specific stratum+SI combinations.
- Forced a fresh TSA 08 debug rerun (`--debug-rows 500`) and confirmed non-empty logs:
  `vdyp_runs.jsonl` (77 events) and `vdyp_curve_events.jsonl` (26 events).
- Hardened sparse-curve handling in `process_vdyp_out`: if smoothed body-fit inputs are empty or
  too short, emit a warning event and return a quasi-origin-anchored fallback curve instead of
  crashing on `idxmax()`.
- Moved `scsi_au`/`au_scsi` registration to only occur for stratum+SI combos that pass all
  operability/species filters and have usable VDYP output.
- Hardened AU-table build in `00_data-prep.py` to skip VDYP curve combos that have no AU mapping,
  with a top-10 warning summary instead of raising `KeyError`.
- Re-ran forced TSA 08 debug (`--debug-rows 500`) from fresh VDYP and reached end-to-end completion
  (process exit code `0`) with populated logs:
  `vdyp_runs.jsonl` (77 events) and `vdyp_curve_events.jsonl` (27 events, including 1
  `body_input` sparse-data warning fallback).
- Defaulted row-wise apply paths back to pandas `.apply(...)` (with optional
  `FEMIC_USE_SWIFTER=1` opt-in) to reduce swifter-related instability/noise during debug runs.
- Added `FEMIC_DISABLE_IPP` handling (default `1`) so debug runs use serial execution without
  ipyparallel controller dependencies.
- Added `FEMIC_SKIP_STANDS_SHP` handling (defaults to skip in debug mode) to bypass final
  shapefile export when iterating rapidly.
- The non-fatal shutdown message (`Error in sys.excepthook` / `Original exception was`) still
  appears even on exit code `0`; root cause remains unresolved, but pipeline outputs and VDYP
  diagnostics are now completing reliably in forced TSA08 debug reruns.
- Updated citation metadata repository URL to match the active remote:
  `https://github.com/UBC-FRESH/wbi_ria_yield`.
- Fixed singleton-stratum handling in `fit_stratum` by forcing `f_.loc[[sc]]` DataFrame access
  (avoids accidental Series coercion and `KeyError: np.False_` during boolean filtering).
- Added guards for empty species mixes in TIPSY-input assembly: if a stratum+SI has no species
  candidates after filtering, emit `no_species_candidates` warning metadata and skip that combo
  instead of raising `IndexError`.
- Stopped importing `swifter` unless `FEMIC_USE_SWIFTER=1` is explicitly enabled, removing
  default monkeypatch side effects during normal debug runs.
- Reworked `run_data_prep` to execute `00_data-prep.py` in a subprocess and stream filtered
  output; this removes persistent non-fatal legacy shutdown noise
  (`Error in sys.excepthook` / `Original exception was`) from `femic run` logs.
- Roadmap review checkpoint (2026-03-01): completed the runtime hardening/diagnostics tranche that
  started this refactor; roadmap focus is now Phase 2 extraction and global-state reduction.
- `femic run` now accepts `--run-id` and `--log-dir`; these are passed to the legacy runner and
  exported as `FEMIC_RUN_ID` / `FEMIC_LOG_DIR`.
- Added per-run manifest output (`run_manifest-<run_id>.json`) with command/options, env flags,
  TSA list, checkpoint presence, and resolved run-scoped log paths.
- VDYP logs are now emitted per TSA + run id
  (`vdyp_runs-tsa{tsa}-{run_id}.jsonl`, `vdyp_curve_events-tsa{tsa}-{run_id}.jsonl`).
- Added deterministic TSA08 regression fixtures under `tests/fixtures/vdyp/tsa08_debug/` and
  tests that assert stable `summarize_vdyp_logs` counts.
- Added warning-budget evaluation (`evaluate_warning_budget`) and CLI threshold flags on
  `femic vdyp report` so CI can fail when warnings/parse-errors grow beyond expected bounds.
- Added per-TSA raw VDYP stream artifacts:
  `vdyp_stdout-tsa{tsa}-{run_id}.log` and `vdyp_stderr-tsa{tsa}-{run_id}.log`.
- Expanded run manifest payloads with runtime/package versions, resolved key paths, and per-TSA
  artifact existence inventory for `vdyp_runs`, `vdyp_curve_events`, `vdyp_stdout`, and
  `vdyp_stderr`.
- Phase 1 checklist reconciled with completed runtime hardening deliverables; remaining work now starts at
  Phase 2 modularization tasks (P2.1+).
- Started Phase 2 module extraction with new reusable helpers under `src/femic/pipeline/`:
  `io.py`, `vdyp.py`, `tsa.py`, and `plots.py`.
- Legacy workflow manifest/log path logic now consumes `femic.pipeline` helpers, reducing
  duplicated logic and defining a stable seam for future migration out of notebook-generated code.
- Removed hardcoded multi-TSA defaults from new pipeline helpers; default TSA selection now reads
  from dev config (`config/dev.toml`, `[run].default_tsa_list`) with `["08"]` fallback for local
  testing.
- Introduced explicit `PipelineRunConfig` handoff from CLI to workflow wrapper so run settings
  (`tsa_list`, `resume`, `debug_rows`, `run_id`, `log_dir`) are passed as typed config instead of
  loose parameters; this is the first concrete step toward `P2.1b` global-state reduction.
- Added `LegacyExecutionPlan` builder in pipeline I/O helpers; legacy runner now consumes a fully
  resolved execution plan (command, env, run IDs, paths, checkpoints) instead of constructing this
  state inline.
- `P2.1b` is now partially complete at the CLI/workflow boundary (typed run config + execution
  plan); remaining `P2.1b` work is to eliminate notebook-script globals inside `00_data-prep.py`
  and `01a_run-tsa.py`.
- Extracted subprocess execution into `femic.pipeline.stages.run_legacy_subprocess(...)`, giving a
  reusable stage executor and reducing orchestration logic inside the legacy workflow wrapper.
- Extracted run-manifest assembly into `femic.pipeline.manifest` (`build_run_manifest_payload`,
  `collect_runtime_versions`, `write_manifest`) so workflow wrapper orchestration now calls reusable
  stage + manifest builders instead of maintaining these internals inline.
- Extracted pre-VDYP checkpoint serialization/load/save into `femic.pipeline.pre_vdyp` and wired
  `01a_run-tsa.py` to use these helpers (`load_vdyp_prep_checkpoint`,
  `save_vdyp_prep_checkpoint`), creating the first notebook-derived data-stage seam for `P2.2a`.
- Removed the old `Next Focus` section after merging non-redundant items into phase checklists to
  keep a single source of planning truth.
- Extracted VDYP input/output table I/O helpers into `femic.pipeline.vdyp_io` and refactored
  `01a_run-tsa.py` to call these shared functions (`write_vdyp_infiles_plylyr`,
  `import_vdyp_tables`), extending `P2.2a` modularization with explicit helper seams.
- Extracted VDYP sample-size estimator into `femic.pipeline.vdyp_sampling.nsamples_from_curves`
  and refactored the auto-sampling loop in `01a_run-tsa.py` to consume this helper.
- Extracted run-id/log-path resolution and append helpers into
  `femic.pipeline.vdyp_logging` (`resolve_run_id`, `build_tsa_vdyp_log_paths`,
  `append_jsonl`, `append_text`) and refactored `01a_run-tsa.py` to consume them.
- Rewired manifest-facing VDYP artifact path builder (`femic.pipeline.vdyp.build_vdyp_log_paths`)
  to reuse `build_tsa_vdyp_log_paths`, removing duplicated filename logic between modules.
- Extracted VDYP curve-building helpers into `femic.pipeline.vdyp_curves` and refactored
  `01a_run-tsa.py` to call shared `process_vdyp_out(...)` logic (including toe-fit retry/fallback
  and quasi-origin anchor behavior) through a reusable module seam.
- Extracted shared VDYP-to-TIPSY scalar derivations into `femic.pipeline.tipsy`
  (`compute_vdyp_site_index`, `compute_vdyp_oaf1`) and refactored all TSA-specific TIPSY parameter
  builders in `01a_run-tsa.py` to consume these helpers instead of duplicating inline parsing logic.
- Added reusable TIPSY candidate evaluation + warning payload helpers in `femic.pipeline.tipsy`
  (`evaluate_tipsy_candidate`, `build_tipsy_warning_event`) and rewired the AU-selection loop in
  `01a_run-tsa.py` to use centralized eligibility reasoning + standardized warning metadata.
- Added initial manual-handoff TIPSY config scaffolding under `config/tipsy/` with a draft template
  (`template.tsa.yaml`) and notes capturing cross-TSA variability from the five legacy TSA rule
  dicts (08/16/24/40/41), to guide migration from hard-coded logic to expert-authored config.
- Added `femic.pipeline.tipsy_config` with TSA YAML loader/validator and config-rule evaluation
  (`load_tipsy_tsa_config`, `validate_tipsy_tsa_config`, `build_tipsy_params_from_config`), and
  wired `01a_run-tsa.py` to prefer `config/tipsy/tsa{tsa}.yaml` (or `.yml`) when present, with
  legacy dict-based dispatch as fallback.
- Added first concrete migrated TSA config `config/tipsy/tsa08.yaml` plus tokenized assignment
  support (e.g., `$leading_species_tipsy`) so config rules can preserve legacy species normalization
  behavior (notably `SX -> SW`) while keeping per-TSA rule logic out of Python code.
- Added second migrated TSA config `config/tipsy/tsa16.yaml` (high-variability case with full
  species-mix/GW field coverage), plus tests that load the repo config and verify expected
  config-driven rule selection output.
- Added third migrated TSA config `config/tipsy/tsa24.yaml` capturing BEC-dependent branching
  (`SBS` vs `ESSF`) and species-group-specific assignment blocks; expanded config tests to verify
  both SBS and ESSF rule-path selection from repo-backed YAML.
- Added `config/tipsy/tsa40.yaml` and `config/tipsy/tsa41.yaml`, completing migration of all five
  legacy TSA rule dict examples into YAML. Extended token support for ranked species placeholders
  (`$species_rank_<n>_tipsy`, `$species_pct_<n>`) and added tests covering dynamic species token
  expansion and forest-type-conditioned rule selection.
- Switched legacy runner default to require config-driven TIPSY rules for TSA processing; missing
  config now fails fast with explicit guidance, while `FEMIC_TIPSY_USE_LEGACY=1` preserves an
  opt-in escape hatch to legacy in-code rule dispatch during transition.
- Added `femic tipsy validate` CLI command for preflight validation of TSA YAML handoff files
  (all discovered configs, or explicit `--tsa` subset), including missing-file detection and schema
  checks via shared `tipsy_config` loader/validator helpers.
- Reduced notebook-script global coupling at the 00/01a/01b stage boundary:
  `01a_run-tsa.run_tsa(...)` and `01b_run-tsa.run_tsa(...)` now take explicit runtime arguments
  (`tsa`, and for 01a also `stratum_col`, `f`, `si_levels`, `vdyp_out_cache`, fit/wrap hooks),
  and `00_data-prep.py` now passes these values directly instead of setting module globals.
- Replaced broad `module.__dict__.update(globals())` handoff with explicit, validated context
  binding via `femic.pipeline.legacy_context.bind_legacy_module_context(...)` and scoped symbol
  lists (`RUN_01A_CONTEXT_SYMBOLS`, `RUN_01B_CONTEXT_SYMBOLS`) so 01a/01b receive only required
  shared notebook-state dependencies.
- Extracted VDYP batch prep/run/import orchestration into
  `femic.pipeline.vdyp_stage.execute_vdyp_batch(...)` (input CSV staging, subprocess execution,
  stdout/stderr artifact appends, parse/error/status event logging), and rewired `01a_run-tsa.py`
  `run_vdyp` internals to call this shared stage helper.
- Added focused unit tests for the VDYP stage helper (`tests/test_vdyp_stage.py`) covering success,
  parse-error, and timeout paths with deterministic fake runner/importer hooks.
- Extracted bootstrap-dispatch orchestration from `01a_run-tsa.py` into
  `femic.pipeline.vdyp_stage.execute_bootstrap_vdyp_runs(...)` (per stratum+SI context assembly,
  dispatch/dispatch_error logging, and nested result-table accumulation), and rewired the
  `force_run_vdyp` branch to consume this helper.
- Expanded `tests/test_vdyp_stage.py` with bootstrap orchestration coverage for success and
  dispatch-error logging behavior.
- Extracted curve-smoothing dispatch orchestration from `01a_run-tsa.py` into
  `femic.pipeline.vdyp_stage.execute_curve_smoothing_runs(...)`, centralizing per stratum+SI
  missing-output warnings, `process_vdyp_out(...)` invocation, and curve-context event emission.
- Rewired `01a_run-tsa.py` to consume `execute_curve_smoothing_runs(...)` and build
  `vdyp_smoothxy` tables from returned smoothed-curve records before writing
  `vdyp_curves_smooth-tsa{tsa}.feather`.
- Expanded `tests/test_vdyp_stage.py` with curve-smoothing orchestration coverage, including
  missing-VDYP warning logging and kwarg-override forwarding into `process_vdyp_out(...)`.
- Extracted legacy VDYP overlay plotting into
  `femic.pipeline.vdyp_stage.plot_curve_overlays(...)`, so `01a_run-tsa.py` now delegates the
  per-stratum plotting loop to a shared stage helper while preserving existing plot output shape.
- Reduced required 01a legacy context symbols by removing no-longer-used globals
  (`Path`, `curve_fit`, `shlex`, `subprocess`) from `RUN_01A_CONTEXT_SYMBOLS`.
- Added `tests/test_vdyp_stage.py` coverage for overlay plotting orchestration
  (`plot_curve_overlays`) to assert expected plotting calls and axis/legend handling.
- Extracted the remaining smooth-curve table assembly/write path into
  `femic.pipeline.vdyp_stage.build_smoothed_curve_table(...)`, so `01a_run-tsa.py` now delegates
  smoothed-curve DataFrame construction + optional feather persistence through a shared stage helper.
- Removed additional stale 01a legacy context symbols after extraction (`_curve_fit`, `wraps`)
  from `RUN_01A_CONTEXT_SYMBOLS`.
- Expanded `tests/test_vdyp_stage.py` with `build_smoothed_curve_table(...)` coverage to verify
  row assembly and output-path write invocation behavior.
- Extracted VDYP result-resolution branching (`force_run`, per-TSA cache load, combined-cache
  fallback, bootstrap-and-persist) into
  `femic.pipeline.vdyp_stage.load_or_build_vdyp_results_tsa(...)`, and rewired `01a_run-tsa.py`
  to delegate this cache/bootstrap decision path through the shared stage helper.
- Reduced required 01a legacy context symbols again by removing stale `pickle` dependency from
  `RUN_01A_CONTEXT_SYMBOLS`.
- Expanded `tests/test_vdyp_stage.py` with coverage for `load_or_build_vdyp_results_tsa(...)`
  across force-run, TSA-cache, combined-cache, and compat-loader fallback branches.
- Extracted VDYP polygon/layer table loading into
  `femic.pipeline.vdyp_stage.load_vdyp_input_tables(...)` and rewired `01a_run-tsa.py` to use this
  helper instead of inline source/feather branch code.
- Reduced required 01a legacy context symbols again by removing stale `gpd` dependency from
  `RUN_01A_CONTEXT_SYMBOLS`.
- Expanded `tests/test_vdyp_stage.py` with `load_vdyp_input_tables(...)` coverage for both feather
  cache loads and source-geodatabase load+persist behavior.
- Added `femic.pipeline.vdyp_stage.build_curve_fit_adapter(...)` and rewired `01a_run-tsa.py` to
  construct a local `curve_fit` wrapper from `curve_fit_impl` so legacy `maxfev` kwargs map to
  modern SciPy `max_nfev` without per-call inline wrapper logic.
- Removed obsolete `wraps_impl` plumbing from `01a_run-tsa.run_tsa(...)` and the
  `00_data-prep.py` caller now that curve-fit adaptation is centralized in the stage helper.
- Expanded `tests/test_vdyp_stage.py` with `build_curve_fit_adapter(...)` coverage for both
  `maxfev -> max_nfev` conversion and passthrough when `max_nfev` is already supplied.
- Reduced additional 01a global-state coupling by extending `01a_run-tsa.run_tsa(...)` with
  explicit path/export inputs (`vdyp_results_*`, `vdyp_input_pandl_path`,
  `vdyp_{ply,lyr}_feather_path`, `tipsy_params_columns`, `tipsy_params_path_prefix`) and wiring
  `00_data-prep.py` to pass them directly.
- Trimmed `RUN_01A_CONTEXT_SYMBOLS` after this signature change by removing no-longer-needed path
  and TIPSY-export globals (`vdyp_input_pandl_path`, `vdyp_{ply,lyr}_feather_path`,
  `vdyp_results_*`, `tipsy_params_columns`, `tipsy_params_path_prefix`).
- Extended `01a_run-tsa.run_tsa(...)` again to take the mutable per-run data structures
  (`results`, `vdyp_results`, `vdyp_curves_smooth`, `scsi_au`, `au_scsi`, `tipsy_params`) and
  lookup inputs (`si_levelquants`, `species_list`,
  `vdyp_curves_smooth_tsa_feather_path_prefix`) explicitly from `00_data-prep.py`.
- Trimmed `RUN_01A_CONTEXT_SYMBOLS` further after this handoff update, leaving only baseline
  runtime/module helpers (`np`, `pd`, `plt`, `sns`, `os`, `operator`, `itertools`, `distance`,
  `kwarg_overrides`, `_femic_resume_effective`) instead of dataset/state payload globals.
- Converted `01b_run-tsa.run_tsa(...)` to explicit runtime inputs
  (`results`, `au_scsi`, `tipsy_curves`, `vdyp_curves_smooth`) and updated `00_data-prep.py` to
  pass these directly instead of relying on injected module globals.
- Removed all remaining 01b context injection requirements by setting
  `RUN_01B_CONTEXT_SYMBOLS` to an empty tuple and localizing 01b plotting imports
  (`matplotlib.pyplot`, `seaborn`) inside the function.
- Extracted TIPSY export assembly/writes from `01a_run-tsa.py` into reusable
  `femic.pipeline.tipsy` helpers (`build_tipsy_input_table`, `write_tipsy_input_exports`) and
  rewired the legacy script to delegate xlsx/dat output generation through these helpers.
- Expanded `tests/test_tipsy.py` with coverage for new TIPSY export helpers: row/column assembly,
  empty-input failure behavior, and xlsx/dat artifact writes.
- Extracted config-vs-legacy TIPSY rule-selection into
  `femic.pipeline.tipsy_config.resolve_tipsy_param_builder(...)` and rewired `01a_run-tsa.py` to
  call this helper for builder/message resolution.
- Expanded `tests/test_tipsy_config.py` with resolver coverage for config-preferred, forced-legacy,
  and missing-config error paths.
- Localized remaining non-numeric helper imports used by `01a_run-tsa.py` (`distance`,
  `itertools`, `operator`, `os`) inside `run_tsa(...)`, removing these dependencies on injected
  legacy module globals.
- Trimmed `RUN_01A_CONTEXT_SYMBOLS` again after import localization; 01a context binding now
  requires only `_femic_resume_effective`, `kwarg_overrides`, and plotting/dataframe modules
  (`np`, `pd`, `plt`, `sns`).
- Extracted the TIPSY candidate-selection and AU-assignment loop from `01a_run-tsa.py` into
  `femic.pipeline.tipsy.build_tipsy_params_for_tsa(...)`, including eligibility filtering, warning
  event emission, and final `scsi_au`/`au_scsi`/`tipsy_params` map construction.
- Rewired `01a_run-tsa.run_tsa(...)` to consume `build_tipsy_params_for_tsa(...)` and pass
  explicit runtime flags (`resume_effective`, `force_run_vdyp`, `kwarg_overrides_for_tsa`) from
  `00_data-prep.py` instead of reading injected globals.
- Localized `numpy`/`pandas`/`matplotlib`/`seaborn` imports inside `01a_run-tsa.run_tsa(...)` and
  trimmed `RUN_01A_CONTEXT_SYMBOLS` to an empty tuple; both 01a and 01b now run without required
  legacy context payload injection.
- Expanded `tests/test_tipsy.py` with orchestration coverage for
  `build_tipsy_params_for_tsa(...)` (success mapping, missing-VDYP warning, no-species warning).
- Extracted inline legacy TSA rule builders/exclusion setup from `01a_run-tsa.py` into new
  `femic.pipeline.tipsy_legacy` module (`build_tipsy_exclusion`,
  `get_legacy_tipsy_builders`, `tipsy_params_tsa08/16/24/40/41`) and rewired 01a to consume this
  shared seam.
- Added `tests/test_tipsy_legacy.py` coverage for legacy builder-dispatch keys, exclusion-map keys,
  and baseline TSA08 output fields.
- Added runtime-wiring regression tests in `tests/test_legacy_context.py` asserting
  `RUN_01A_CONTEXT_SYMBOLS == ()` and `RUN_01B_CONTEXT_SYMBOLS == ()`, plus empty-required-symbol
  binding behavior.
- Removed no-op legacy context binding calls from `00_data-prep.py` now that both
  `RUN_01A_CONTEXT_SYMBOLS` and `RUN_01B_CONTEXT_SYMBOLS` are empty; 01a/01b module loading now
  proceeds directly to explicit `run_tsa(...)` invocation.
- Removed the inactive `if 0:` legacy TIPSY export branch from `01a_run-tsa.py` (unused duplicate
  xlsx assembly path) to keep only the active helper-driven export flow.
- Pruned deprecated legacy-context re-exports from `femic.pipeline.__init__` now that context
  injection is no longer part of the runtime orchestration surface.
- Removed additional low-risk inactive `if 0:` debug/reload blocks from `00_data-prep.py`
  (checkpoint rollbacks/manual cache toggles/legacy shp export snippets) to reduce notebook-era
  dead-code noise without altering active runtime branches.
- Added `tests/test_legacy_orchestration_wiring.py` AST regression checks to lock explicit
  `_run01a_module.run_tsa(...)` and `_run01b_module.run_tsa(...)` keyword handoff surfaces and
  assert no `bind_legacy_module_context(...)` call remains in `00_data-prep.py`.
- Removed the final inactive `if 0:` notebook-era debug blocks from `00_data-prep.py` (dormant
  legacy `process_vdyp_out(...)` sandbox and manual TSA smoothing loop), leaving only active
  orchestration code paths.
- Expanded `tests/test_tipsy_legacy.py` with a TSA24 regression case that verifies BEC-dependent
  legacy rule branching (`SBS` vs `ESSF`) for a fir-leading stand.
- Extracted default VDYP curve-smoothing kwarg overrides into
  `femic.pipeline.vdyp_overrides` (`DEFAULT_VDYP_KWARG_OVERRIDES`,
  `vdyp_kwarg_overrides_for_tsa(...)`) to remove hardcoded override dicts from
  `00_data-prep.py` and centralize override defaults in a reusable pipeline seam.
- Updated `01a_run-tsa.run_tsa(...)` to resolve override defaults internally when
  `kwarg_overrides_for_tsa` is not provided; `00_data-prep.py` now passes `None` explicitly.
- Added regression coverage for the new override helper (`tests/test_vdyp_overrides.py`) plus AST
  wiring coverage asserting the 00->01a handoff uses internal defaults
  (`kwarg_overrides_for_tsa=None`).
- Rewired `01a_run-tsa.py` to consume `femic.pipeline.tsa.target_nstrata_for(...)` instead of an
  inline TSA->target-strata dict, reducing notebook-era duplicated constants.
- Added shared `femic.pipeline.tsa.MIN_STANDCOUNT` and updated 01a strata filtering/tests to consume
  this constant instead of hardcoded local values.
- Removed additional inline bootstrap tuning constants from `01a_run-tsa.py` by relying on
  `execute_bootstrap_vdyp_runs(...)` defaults for `half_rel_ci`, `nsamples_c1`, and `ipp_mode`.
- Added `tests/test_legacy_01a_structure.py` AST guardrails that lock 01a structural cleanup:
  `run_tsa(...)` must call `target_nstrata_for(...)`, must not reintroduce an inline
  `target_nstrata` dict assignment, and must not locally reassign `si_levels`.
- Extracted 01a strata summarization logic into `femic.pipeline.tsa.build_strata_summary(...)`
  (target-strata selection, site-index/crown-closure/coverage aggregates, stand-count filtering,
  and `median_si` enrichment), reducing notebook-era inline grouping logic in `run_tsa(...)`.
- Rewired `01a_run-tsa.py` to consume `build_strata_summary(...)` for stratum candidate table
  assembly and IQR reporting.
- Expanded `tests/test_pipeline_helpers.py` with deterministic `build_strata_summary(...)` coverage
  (aggregate outputs + validation error path), and updated `tests/test_legacy_01a_structure.py`
  guardrails to assert `run_tsa(...)` calls the extracted helper seam.
- Extracted 01a lexmatch alias resolution into
  `femic.pipeline.tsa.build_stratum_lexmatch_alias_map(...)`, moving Levenshtein tie-break
  selection logic (distance + relative-area tiebreak) out of inline notebook-era code.
- Rewired `01a_run-tsa.py` to consume `build_stratum_lexmatch_alias_map(...)` when mapping
  non-selected strata onto selected strata for downstream fitting.
- Expanded tests with deterministic alias-map coverage in `tests/test_pipeline_helpers.py`, and
  added AST guardrails in `tests/test_legacy_01a_structure.py` asserting 01a calls the new
  lexmatch helper seam.
- Extracted the inline 01a stratum-fitting block into
  `femic.pipeline.vdyp_stage.fit_stratum_curves(...)`, centralizing per-SI quantile filtering,
  species-share derivation, curve-fit execution/error handling, and optional plot emission in a
  reusable stage seam.
- Rewired `01a_run-tsa.py` to call `fit_stratum_curves(...)` during pre-VDYP stratum compilation,
  removing the nested `fit_stratum(...)` function definition from `run_tsa(...)`.
- Expanded `tests/test_vdyp_stage.py` with focused `fit_stratum_curves(...)` coverage (successful
  species payload output and curve-fit error skip/log behavior), and extended
  `tests/test_legacy_01a_structure.py` guardrails to assert 01a calls the stage helper and no
  longer defines a nested `fit_stratum`.
- Extracted stratum-compilation loop orchestration into
  `femic.pipeline.vdyp_stage.compile_strata_fit_results(...)`, so 01a now delegates per-stratum
  iteration/message/result assembly through a reusable stage helper.
- Rewired `01a_run-tsa.py` pre-VDYP compilation path to call
  `compile_strata_fit_results(...)` with the extracted `fit_stratum_curves(...)` seam.
- Expanded `tests/test_vdyp_stage.py` with deterministic compile-loop helper coverage, and extended
  `tests/test_legacy_01a_structure.py` guardrails to assert 01a calls
  `compile_strata_fit_results(...)`.
- Extracted VDYP sampling-mode orchestration into
  `femic.pipeline.vdyp_stage.run_vdyp_sampling(...)`, centralizing the `auto`/`all`/fixed sample
  flow, cache-hit handling, and gap-fill loop decision logic previously embedded in 01a.
- Rewired `01a_run-tsa.py` `run_vdyp(...)` to delegate sampling decisions through
  `run_vdyp_sampling(...)` while keeping batch execution/logging in its existing `_run_vdyp(...)`
  closure.
- Expanded `tests/test_vdyp_stage.py` with focused `run_vdyp_sampling(...)` coverage
  (auto-small-sample path, auto gap-fill phase path, and invalid-mode assertion), and extended
  `tests/test_legacy_01a_structure.py` guardrails to assert 01a calls
  `run_vdyp_sampling(...)`.
- Extracted the nested 01a `run_vdyp(...)` wrapper into
  `femic.pipeline.vdyp_stage.run_vdyp_for_stratum(...)`, centralizing per-stratum VDYP runtime
  preflight checks (wine/bin/params), default log-path resolution, run-event logging, batch
  execution dispatch, and sampling orchestration handoff.
- Rewired `01a_run-tsa.py` bootstrap execution to call `run_vdyp_for_stratum(...)` directly and
  removed the nested `run_vdyp` and `_tsa_log_path` definitions from `run_tsa(...)`.
- Expanded `tests/test_vdyp_stage.py` with `run_vdyp_for_stratum(...)` coverage and updated
  `tests/test_legacy_01a_structure.py` guardrails to assert 01a no longer calls
  `run_vdyp_sampling(...)` directly and no longer defines a nested `run_vdyp`.
- Queued next extraction slice: move the remaining 01a bootstrap-callable wiring lambda into a
  dedicated stage helper so `run_tsa(...)` only passes explicit orchestration inputs without
  inline closure assembly.
- Added `femic.pipeline.vdyp_stage.build_run_vdyp_for_stratum_runner(...)`, a reusable helper that
  binds per-TSA runtime context (`tsa`, `run_id`, VDYP tables, fit hooks, and run-log paths) into
  a `run_vdyp_fn(sample_table, **kwargs)` callable compatible with
  `execute_bootstrap_vdyp_runs(...)`.
- Rewired `01a_run-tsa.py` bootstrap flow to build `run_vdyp_fn` via
  `build_run_vdyp_for_stratum_runner(...)`, removing the remaining inline lambda that assembled
  `run_vdyp_for_stratum(...)` kwargs inside `run_tsa(...)`.
- Expanded `tests/test_vdyp_stage.py` with binding/forwarding coverage for
  `build_run_vdyp_for_stratum_runner(...)`, and updated
  `tests/test_legacy_01a_structure.py` guardrails to assert 01a calls the builder helper and no
  longer calls `run_vdyp_for_stratum(...)` directly.
- Queued next extraction slice: remove the remaining inline `run_bootstrap_fn=lambda: ...`
  assembly in `01a_run-tsa.py` by introducing a dedicated stage helper for per-TSA bootstrap
  callback construction.
- Added `femic.pipeline.vdyp_stage.build_bootstrap_vdyp_results_runner(...)`, a reusable helper
  that binds per-TSA bootstrap dispatch inputs (`tsa`, `run_id`, results payload, SI levels, log
  sink, `run_vdyp_fn`, and cache map) into a zero-arg callback compatible with
  `load_or_build_vdyp_results_tsa(...)`.
- Rewired `01a_run-tsa.py` to pass `run_bootstrap_fn` built by
  `build_bootstrap_vdyp_results_runner(...)`, removing the remaining inline
  `run_bootstrap_fn=lambda: execute_bootstrap_vdyp_runs(...)` closure assembly.
- Expanded `tests/test_vdyp_stage.py` with binding/forwarding coverage for
  `build_bootstrap_vdyp_results_runner(...)`, and updated
  `tests/test_legacy_01a_structure.py` guardrails to assert 01a calls the builder helper and does
  not pass an inline lambda to `run_bootstrap_fn`.
- Queued next extraction slice: move the remaining inline `compile_one_fn=lambda: ...` assembly in
  pre-VDYP stratum compilation into a dedicated stage helper so 01a no longer builds fit-call
  closures inline.
- Added `femic.pipeline.vdyp_stage.build_fit_stratum_curves_runner(...)`, a reusable helper that
  binds per-TSA stratum-fit context into `compile_one_fn(stratumi, sc)` callbacks for
  `compile_strata_fit_results(...)`.
- Rewired `01a_run-tsa.py` to build and pass `compile_one_fn` via
  `build_fit_stratum_curves_runner(...)`, removing inline fit-call closure assembly in the pre-VDYP
  compilation path.
- Expanded `tests/test_vdyp_stage.py` with fit-runner binding coverage and updated
  `tests/test_legacy_01a_structure.py` guardrails so 01a must call the builder helper and must not
  pass inline lambdas to `compile_one_fn`.
- Extracted legacy notebook fit functions (`fit_func1`, `fit_func1_bounds_func`, `fit_func2`,
  `fit_func2_bounds_func`) from `01a_run-tsa.py` into `femic.pipeline.vdyp_curves`
  (`legacy_fit_func1`, `legacy_fit_func1_bounds_func`, `legacy_fit_func2`,
  `legacy_fit_func2_bounds_func`), and rewired 01a to consume these shared helpers.
- Expanded `tests/test_vdyp_curves.py` with deterministic coverage for legacy fit-function outputs
  and bounds, and added AST guardrails asserting 01a no longer defines nested legacy fit functions.
- Queued next extraction slice: remove the final nested `match_stratum(...)` function definition in
  `01a_run-tsa.py` by moving alias-application logic into a reusable TSA helper.
- Added `femic.pipeline.tsa.apply_stratum_alias_map(...)` to encapsulate selected-strata retention
  plus alias fallback assignment for `*_matched` stratum columns.
- Rewired `01a_run-tsa.py` to call `apply_stratum_alias_map(...)` for stratum matching, removing
  the final nested helper definition (`match_stratum`) from `run_tsa(...)`.
- Expanded `tests/test_pipeline_helpers.py` with deterministic alias-application coverage and added
  AST guardrails in `tests/test_legacy_01a_structure.py` asserting 01a calls the helper and has no
  nested `match_stratum`.
- `01a_run-tsa.run_tsa(...)` now has zero nested function definitions; remaining extraction focus is
  reducing inline notebook-style constant/plot configuration blocks into reusable stage helpers.
- Queued next extraction slice: move curve-smoothing plot setup constants
  (`palette_flavours`/palette/alpha defaults) from `01a_run-tsa.py` into a shared stage helper.
- Added `femic.pipeline.vdyp_stage.CurveSmoothingPlotConfig` and
  `build_curve_smoothing_plot_config(...)` to centralize legacy curve-smoothing plot defaults
  (plot toggle, `figsize`, palette setup, `palette_flavours`, `alphas`) behind a shared stage seam.
- Rewired `01a_run-tsa.py` curve-smoothing overlay path to call
  `build_curve_smoothing_plot_config(...)` and consume the returned config instead of defining
  inline plot/palette constants.
- Expanded `tests/test_vdyp_stage.py` with deterministic defaults coverage for
  `build_curve_smoothing_plot_config(...)`, and added AST guardrails in
  `tests/test_legacy_01a_structure.py` asserting 01a calls this helper and no longer assigns
  inline smoothing `palette_flavours`/`alphas` constants.
- Queued next extraction slice: remove dead legacy `fit_func2`/`fit_func2_bounds_func` local
  bindings from `01a_run-tsa.py` now that these values are no longer consumed by any active stage.
- Removed dead `legacy_fit_func2`/`legacy_fit_func2_bounds_func` imports and local
  `fit_func2`/`fit_func2_bounds_func` assignments from `01a_run-tsa.py`; these values were no
  longer used by any active stage path after prior smoothing-stage extraction.
- Added `tests/test_legacy_01a_structure.py` guardrails asserting `run_tsa(...)` no longer assigns
  local legacy fit2 bindings.
- Queued next extraction slice: move inline TIPSY staging defaults
  (`min_operable_years`, `si_iqrlo_quantile`, local `verbose`) into a shared helper seam so 01a no
  longer embeds these constants directly.
- Removed inline TIPSY staging constant assignments from `01a_run-tsa.py`
  (`min_operable_years`, `si_iqrlo_quantile`, local `verbose`) and now rely on
  `build_tipsy_params_for_tsa(...)` shared default thresholds.
- Expanded `tests/test_legacy_01a_structure.py` with guardrails asserting 01a no longer assigns
  these constants inline and no longer overrides corresponding
  `build_tipsy_params_for_tsa(...)` keyword defaults.
- Queued next extraction slice: move overlay axis-bound constants (`xlim`, `ylim`) passed to
  `plot_curve_overlays(...)` out of `01a_run-tsa.py` into a shared stage/default helper.
- Extended `CurveSmoothingPlotConfig` / `build_curve_smoothing_plot_config(...)` to include overlay
  axis defaults (`xlim`, `ylim`) so smoothing overlay bounds are configured in one shared stage
  seam.
- Rewired `01a_run-tsa.py` `plot_curve_overlays(...)` call to consume
  `smooth_plot_cfg.xlim`/`smooth_plot_cfg.ylim` instead of inline tuple literals.
- Expanded `tests/test_vdyp_stage.py` defaults coverage for new axis config fields and added
  `tests/test_legacy_01a_structure.py` AST guardrails asserting overlay axes are sourced from
  `smooth_plot_cfg`.
- Queued next extraction slice: move stratum-distribution plot constants (`bw`, `linewidth`,
  `inner`, `width`, `cut`, `alpha`) from `01a_run-tsa.py` into a shared plotting helper/config
  seam.
- Added `StrataDistributionPlotConfig` and `build_strata_distribution_plot_config(...)` in
  `femic.pipeline.plots` to centralize default plotting constants for 01a stratum-distribution
  diagnostics.
- Rewired the 01a stratum-distribution plotting block to consume
  `build_strata_distribution_plot_config(...)` values instead of inline constants.
- Expanded `tests/test_pipeline_helpers.py` with defaults coverage for the new plot-config helper,
  and added AST guardrails in `tests/test_legacy_01a_structure.py` asserting 01a calls the helper
  and no longer assigns inline strata-plot constants.
- Queued next extraction slice: replace inline strata plot output path literals in `01a_run-tsa.py`
  with `femic.pipeline.plots.strata_plot_paths(...)` helper output.
- Rewired `01a_run-tsa.py` strata diagnostic plot output writes to call
  `femic.pipeline.plots.strata_plot_paths(...)` and save to returned PDF/PNG paths instead of
  inline `"plots/strata-tsa%s.*"` string literals.
- Added AST guardrails in `tests/test_legacy_01a_structure.py` asserting 01a calls
  `strata_plot_paths(...)` and no longer embeds inline strata plot output path literals.
- Queued next extraction slice: move inline stratum-label ordering toggle (`sort_lex` branch) from
  `01a_run-tsa.py` into a reusable TSA/plot helper seam.
- Added `femic.pipeline.plots.resolve_strata_plot_ordering(...)` to centralize abundance-vs-lexic
  ordering for stratum distribution plots.
- Rewired `01a_run-tsa.py` to call `resolve_strata_plot_ordering(...)` and removed the inline
  `sort_lex` branch and local ordering assembly.
- Expanded `tests/test_pipeline_helpers.py` with deterministic ordering coverage for default
  (abundance) and lexical modes, and added AST guardrails in
  `tests/test_legacy_01a_structure.py` asserting 01a calls the helper and no longer assigns local
  `sort_lex`.
- Queued next extraction slice: remove residual inline notebook-style diagnostic plot calls in early
  01a flow (`site_index_median` histogram + scatter) into a reusable plotting helper.
- Added `femic.pipeline.plots.plot_strata_site_index_diagnostics(...)` to encapsulate early 01a
  stratum diagnostics plotting (`site_index_median` histogram + abundance-vs-SI scatter).
- Rewired `01a_run-tsa.py` to call `plot_strata_site_index_diagnostics(...)` and removed direct
  inline histogram/scatter plotting calls from `run_tsa(...)`.
- Expanded `tests/test_pipeline_helpers.py` with deterministic behavior coverage for the new
  diagnostics helper and added AST guardrails in `tests/test_legacy_01a_structure.py` asserting 01a
  calls the helper and no longer invokes direct `plt.scatter(...)` for this stage.
- Queued next extraction slice: centralize stratum-distribution/ordering plotting orchestration
  (bar+violin block) into a dedicated shared helper to further shrink inline plotting in 01a.
- Added `femic.pipeline.plots.render_strata_distribution_plot(...)` to encapsulate the stratum
  distribution diagnostics rendering workflow (barplot + violinplot + labels + xlim + PDF/PNG
  writes via helper-managed paths).
- Rewired `01a_run-tsa.py` to call `render_strata_distribution_plot(...)`, removing direct inline
  seaborn bar/violin calls and save-path plumbing from `run_tsa(...)`.
- Expanded `tests/test_pipeline_helpers.py` with deterministic rendering-helper coverage and added
  AST guardrails in `tests/test_legacy_01a_structure.py` asserting 01a calls the rendering helper
  and no longer performs direct `sns.barplot(...)`/`sns.violinplot(...)` calls in this stage.
- Queued next extraction slice: trim now-unused local imports from `01a_run-tsa.py` (notably early
  `seaborn` direct plotting dependencies that have moved behind helper seams) and lock with
  guardrails.
- Added `femic.pipeline.tipsy_config.resolve_tipsy_runtime_options(...)` to centralize
  `FEMIC_TIPSY_CONFIG_DIR`/`FEMIC_TIPSY_USE_LEGACY` environment resolution for TIPSY runtime
  behavior.
- Rewired `01a_run-tsa.py` to call `resolve_tipsy_runtime_options(...)` instead of reading
  `os.environ` directly for TIPSY config/legacy flags.
- Expanded `tests/test_tipsy_config.py` with defaults/override coverage for
  `resolve_tipsy_runtime_options(...)` and added AST guardrails in
  `tests/test_legacy_01a_structure.py` asserting 01a no longer reads `os.environ` directly for this
  stage.
- Queued next extraction slice: begin consolidating remaining inline 01a run-stage constants
  (`fit_rawdata`, `min_age`, `agg_type`, `verbose`, `plot`) into dedicated stage/config helpers.
- Added `StratumFitRunConfig` and `build_stratum_fit_run_config(...)` in
  `femic.pipeline.vdyp_stage` to centralize pre-VDYP stratum fit-stage defaults
  (`fit_rawdata`, `min_age`, `agg_type`, `plot`, `verbose`, `figsize`, `xlim`, `ylim`).
- Rewired `01a_run-tsa.py` pre-VDYP fit compilation path to consume
  `build_stratum_fit_run_config(...)` instead of assigning these constants inline.
- Expanded `tests/test_vdyp_stage.py` with defaults coverage for the new fit-stage config helper
  and added AST guardrails in `tests/test_legacy_01a_structure.py` asserting 01a calls the helper
  and no longer assigns inline stratum fit-stage constants.
- Queued next extraction slice: centralize pre-VDYP checkpoint filename construction
  (`"./data/vdyp_prep-tsa%s.pkl"`) into a shared path helper seam.
- Added `femic.pipeline.pre_vdyp.pre_vdyp_checkpoint_path(...)` to centralize per-TSA pre-VDYP
  checkpoint path construction.
- Rewired `01a_run-tsa.py` to call `pre_vdyp_checkpoint_path(...)` instead of constructing
  `"./data/vdyp_prep-tsa%s.pkl"` inline.
- Expanded `tests/test_pre_vdyp.py` with path-helper coverage (default dir + TSA zero-padding) and
  added AST guardrails in `tests/test_legacy_01a_structure.py` asserting 01a calls the helper and
  no longer embeds `vdyp_prep-tsa` literals.
- Queued next extraction slice: centralize remaining inline 01a path templates
  (`vdyp_results_tsa_pickle_path`, `vdyp_curves_smooth_tsa_feather_path`) into dedicated shared
  path helpers.
- Transcript review checkpoint (2026-03-02): the legacy notebook-to-script debugging tranche is
  complete (00/01a/01b script entrypoints, VDYP/Wine diagnostics hardening, config-driven TIPSY
  handoff, and broad 01a helper extraction); active work remains in Phase 2 (`P2.1b`/`P2.2`) to
  remove residual inline globals/path templates and tighten stage orchestration seams.
- Planned execution sequence after transcript review:
  1) extract remaining 01a inline path templates into shared helpers, 2) trim stale 01a imports and
  dependency injection leftovers, 3) finish converting any residual inline stage logic to helper
  calls with AST guardrails, 4) run full validation gate and capture a new end-to-end TSA debug run
  summary in changelog notes.
- Added `femic.pipeline.vdyp.build_vdyp_cache_paths(...)` to centralize per-TSA cache artifact path
  templates for `vdyp_results-tsa*.pkl` and `vdyp_curves_smooth-tsa*.feather`.
- Rewired `01a_run-tsa.py` to call `build_vdyp_cache_paths(...)` instead of constructing per-TSA
  cache paths inline via string templates.
- Expanded tests with helper and guardrail coverage:
  `tests/test_pipeline_helpers.py` now checks `build_vdyp_cache_paths(...)`, and
  `tests/test_legacy_01a_structure.py` now asserts 01a calls the helper and no longer assigns
  inline `%`-formatted cache-path templates.
- Full validation gate passes after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (154 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: trim now-stale local imports and remaining dependency handoff
  plumbing in `01a_run-tsa.py` after path-template helper extraction.
- Removed local `os` dependency from `01a_run-tsa.py` path checks by switching to
  `Path(...).is_file()` for pre-VDYP checkpoint and smoothed-curve cache detection.
- Added AST guardrail coverage in `tests/test_legacy_01a_structure.py` asserting `run_tsa(...)`
  does not import `os` locally for this path-check stage.
- Queued next extraction slice: reduce remaining 00->01a path handoff plumbing by passing a single
  resolved VDYP cache-path payload instead of separate path-prefix arguments.
- Queued execution batch (post-checklist refresh):
  1) implement a `vdyp_cache_paths` payload handoff from `00_data-prep.py` to `01a_run-tsa.py`,
  2) reduce `run_tsa(...)` argument surface by grouping remaining path/runtime plumbing into a
  typed config payload,
  3) extract 00_data-prep 01a/01b module-loader/caller loops into shared orchestration helper(s).
- Added `Legacy01ARuntimeConfig` (`femic.pipeline.legacy_runtime`) and rewired
  `01a_run-tsa.run_tsa(...)` to consume this typed runtime payload instead of discrete
  path/runtime args (`resume_effective`, `force_run_vdyp`, cache path prefixes, tipsy export paths,
  and optional fit/cache hooks).
- Collapsed 00->01a cache-path handoff to one resolved payload (`vdyp_cache_paths`) built in
  `00_data-prep.py` and passed through `Legacy01ARuntimeConfig`.
- Added shared orchestration helpers in `femic.pipeline.stages`:
  `load_legacy_module(...)` and `run_legacy_tsa_loop(...)`.
- Rewired 00_data-prep 01a/01b execution loops to use shared loader/loop helpers (instead of
  inline `importlib.util` plumbing and duplicated loop scaffolding).
- Added script-run fallback in `00_data-prep.py` to prepend `src/` on `ModuleNotFoundError` so
  direct `python 00_data-prep.py` execution can still import `femic.pipeline` helpers.
- Expanded guardrails/tests:
  `tests/test_legacy_orchestration_wiring.py` now validates runtime-config handoff plus shared
  loader/loop helper usage, `tests/test_pipeline_stages.py` now covers
  `load_legacy_module(...)`/`run_legacy_tsa_loop(...)`, and
  `tests/test_legacy_01a_structure.py` asserts 01a reads cache paths from `runtime_config`.
- Queued next extraction slice: continue `P2.2` by moving remaining 00_data-prep orchestration
  logic around stage setup/checkpoints into reusable stage helpers so the top-level script becomes a
  thin workflow shell.
- Added stage setup helpers in `femic.pipeline.stages`:
  `initialize_legacy_tsa_stage_state(...)`, `prepare_tsa_index(...)`, and
  `should_skip_if_outputs_exist(...)`.
- Added `femic.pipeline.legacy_runtime.build_legacy_01a_runtime_config(...)` so 00_data-prep no
  longer assembles the 01a runtime payload inline.
- Rewired `00_data-prep.py` to consume these helpers for state-map initialization, TSA-index
  preparation, resume-skip checks, and 01a runtime-config assembly.
- Expanded tests to cover new setup/runtime helpers and wiring:
  `tests/test_pipeline_stages.py` now covers helper behavior and runtime-config cache path build,
  and `tests/test_legacy_orchestration_wiring.py` asserts 00_data-prep calls the new setup/runtime
  helper seams.
- Queued next extraction slice: continue thinning 00_data-prep by extracting remaining post-01b
  bundle/table orchestration and path wiring into shared helpers under `femic.pipeline`.
- Added new bundle orchestration helpers in `femic.pipeline.bundle`:
  `resolve_bundle_paths(...)`, `bundle_tables_ready(...)`, `load_bundle_tables(...)`,
  `write_bundle_tables(...)`, and `ensure_scsi_au_from_table(...)`.
- Rewired 00_data-prep post-01b bundle block to use shared bundle helpers for path wiring,
  resume-time table loading, CSV persistence, and `scsi_au` backfill.
- Added focused bundle helper tests in `tests/test_bundle.py` and expanded orchestration AST
  guardrails in `tests/test_legacy_orchestration_wiring.py` to assert 00_data-prep calls bundle
  helper seams.
- Queued next extraction slice: move the heavy AU/curve table assembly loop (currently inline in
  00_data-prep) into a reusable pipeline helper with deterministic unit coverage.
- Added `build_bundle_tables_from_curves(...)` and `BundleAssemblyResult` in
  `femic.pipeline.bundle` to extract the heavy AU/curve table assembly loop from 00_data-prep.
- Rewired 00_data-prep to consume `build_bundle_tables_from_curves(...)` and retain warning summary
  behavior for missing AU mappings using returned diagnostics.
- Expanded `tests/test_bundle.py` with deterministic coverage for managed/unmanaged curve assembly
  and missing-mapping diagnostics, and extended orchestration guardrails to assert
  `build_bundle_tables_from_curves(...)` usage.
- Queued next extraction slice: continue P2.2 by moving residual stratum-matching + SI-level
  assignment orchestration (post-bundle stage) into reusable helper seams.
- Added residual post-bundle strata helpers in `femic.pipeline.tsa`:
  `assign_stratum_matches_from_au_table(...)` and
  `assign_si_levels_from_stratum_quantiles(...)`.
- Rewired `00_data-prep.py` post-bundle stage to call these helpers instead of maintaining inline
  stratum-matching and SI-level assignment loops.
- Expanded helper/wiring tests:
  `tests/test_pipeline_helpers.py` now covers both new TSA helpers, and
  `tests/test_legacy_orchestration_wiring.py` guardrails now assert
  `assign_stratum_matches_from_au_table(...)` and
  `assign_si_levels_from_stratum_quantiles(...)` seam usage.
- Queued next extraction slice: continue thinning 00_data-prep by extracting AU assignment + null
  diagnostics (`_lookup_scsi_au`, `au_from_scsi`, missing/null summaries) into reusable helper(s).
- Added AU-assignment helper seams in `femic.pipeline.tsa`:
  `lookup_scsi_au_base(...)`, `assign_au_ids_from_scsi(...)`,
  `summarize_missing_au_mappings(...)`, `build_au_assignment_null_summary(...)`, and
  `validate_nonempty_au_assignment(...)`.
- Rewired 00_data-prep AU assignment + null-diagnostics block to consume these helpers instead of
  inline `_lookup_scsi_au`/`au_from_scsi`/missing-summary logic.
- Expanded tests with deterministic helper coverage in `tests/test_pipeline_helpers.py` and updated
  orchestration guardrails in `tests/test_legacy_orchestration_wiring.py` to assert new AU helper
  seam usage.
- Queued next extraction slice: continue P2.2 by extracting the post-AU curve-ID assignment block
  (`assign_curve1`, `assign_curve2`) into reusable helper(s), then wire through tests/guardrails.
- Added `assign_curve_ids_from_au_table(...)` in `femic.pipeline.bundle` to centralize post-AU
  curve ID assignment logic (managed/unmanaged switch and fallback handling).
- Rewired 00_data-prep to call `assign_curve_ids_from_au_table(...)` in place of inline
  `assign_curve1`/`assign_curve2` functions and row-wise assignment calls.
- Expanded `tests/test_bundle.py` with deterministic coverage for managed/unmanaged curve assignment
  behavior, and updated orchestration guardrails to assert
  `assign_curve_ids_from_au_table(...)` seam usage.
- Queued next extraction slice: continue P2.2 by extracting the remaining post-curve assignment
  THLB/theme orchestration blocks into reusable helper seams.
- Added `assign_thlb_area_and_flag(...)` in `femic.pipeline.tsa` to centralize THLB area + THLB
  flag assignment rules previously embedded in 00_data-prep.
- Rewired 00_data-prep to call `assign_thlb_area_and_flag(...)` instead of inline `thlb_area(...)`
  and `assign_thlb(...)` functions.
- Expanded `tests/test_pipeline_helpers.py` with deterministic THLB helper coverage and updated
  orchestration guardrails to assert `assign_thlb_area_and_flag(...)` seam usage.
- Queued next extraction slice: continue P2.2 by extracting remaining theme/shapefile post-processing
  orchestration (`has_managed_curve`, `extract_features`, per-TSA stand export transforms) into
  reusable helper seams.
- Added `src/femic/pipeline/stands.py` to centralize stand-export post-processing helpers:
  `should_skip_stands_export(...)`, `clean_stand_geometry(...)`,
  `extract_stand_features_for_tsa(...)`, `build_stands_column_map(...)`,
  `prepare_stands_export_frame(...)`, and `export_stands_shapefiles(...)`.
- Rewired 00_data-prep stand-export orchestration to consume the new stands helpers (skip-flag
  resolution, column-map construction, per-TSA feature extraction/transform, and shapefile write
  loop) instead of inline local function definitions.
- Exported stands helpers from `femic.pipeline.__init__` and added deterministic coverage in
  `tests/test_stands.py`; updated orchestration guardrails in
  `tests/test_legacy_orchestration_wiring.py` to assert
  `build_stands_column_map(...)`, `should_skip_stands_export(...)`, and
  `export_stands_shapefiles(...)` seam usage.
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (178 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by extracting remaining inline post-01b orchestration
  prints/warnings and path literals in `00_data-prep.py` into reusable logging/path helper seams so
  the script body approaches a pure stage-composition shell.
- Added `tipsy_stage_output_paths(...)` in `src/femic/pipeline/tipsy.py` to centralize legacy 01b
  per-TSA output CSV path construction.
- Added `emit_missing_au_mapping_warning(...)` in `src/femic/pipeline/tsa.py` to centralize the
  two-line warning emission for missing AU mapping diagnostics.
- Rewired 00_data-prep post-01b orchestration to consume the new helpers:
  `_should_skip_01b(...)` now uses `tipsy_stage_output_paths(...)`, and AU null-handling now uses
  `emit_missing_au_mapping_warning(...)` instead of inline `print(...)` statements.
- Exported new helpers via `femic.pipeline.__init__`, added deterministic helper tests in
  `tests/test_tipsy.py` and `tests/test_pipeline_helpers.py`, and updated AST guardrails in
  `tests/test_legacy_orchestration_wiring.py` to assert seam usage.
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (180 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by centralizing remaining `00_data-prep.py` hardcoded
  `./data/...` artifact path literals (checkpoints, intermediates, and exports) behind reusable path
  builders so stage orchestration uses structured path payloads instead of inline strings.
- Added `build_ria_vri_checkpoint_paths(...)` in `src/femic/pipeline/io.py` to centralize legacy
  VRI checkpoint artifact path construction (`ria_vri_vclr1p_checkpoint{1..8}.feather`).
- Rewired `00_data-prep.py` to call `build_ria_vri_checkpoint_paths(...)` and source checkpoint path
  variables from the returned path payload instead of embedding eight inline `./data/...` literals.
- Exported the new path helper via `femic.pipeline.__init__`, added deterministic helper coverage in
  `tests/test_pipeline_helpers.py`, and extended AST guardrails in
  `tests/test_legacy_orchestration_wiring.py` to assert seam usage.
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (181 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by centralizing remaining non-checkpoint
  `00_data-prep.py` `./data/...` path literals (VDYP input/output, TIPSY exports, and siteprod
  artifact prefixes) into reusable path builders so stage configuration is fully payload-driven.
- Added `LegacyDataArtifactPaths` and `build_legacy_data_artifact_paths(...)` in
  `src/femic/pipeline/io.py` to centralize non-checkpoint legacy `data/` artifact paths under a
  single reusable payload.
- Rewired `00_data-prep.py` to source non-checkpoint data artifact paths from
  `build_legacy_data_artifact_paths(...)`, including VDYP input/output paths, TIPSY input-column
  file path and prefix, siteprod artifacts, bundle root, THLB raster, and stands shapefile output
  directory.
- Exported new I/O path payload helpers via `femic.pipeline.__init__`, added deterministic coverage
  in `tests/test_pipeline_helpers.py`, and updated AST guardrails in
  `tests/test_legacy_orchestration_wiring.py` to assert
  `build_legacy_data_artifact_paths(...)` seam usage.
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (182 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by removing residual duplicated path-to-string
  coercion and remaining ad-hoc path joins in `00_data-prep.py` (favor passing `Path` objects
  through helper boundaries directly) so orchestration has a consistent typed path surface.
- Reworked `00_data-prep.py` path handling to keep legacy artifact paths as `Path` objects through
  helper boundaries (removed residual `str(...)` coercions for non-external artifact paths).
- Replaced remaining ad-hoc path joins in 00_data-prep with helper/path-native composition:
  `build_vdyp_cache_paths(...)` + `tipsy_params_excel_path(...)` now drive 01a resume-skip output
  checks; siteprod layer temp paths now use `Path` joins/globs instead of `%s` string templates.
- Replaced residual string-shell path checks/builds in this stage:
  `Path.is_file()` for local executable/artifact presence, list-based `subprocess.run(...)` calls
  with pathlike args, and `Path.read_text().splitlines()` for TIPSY column loading.
- Added `tipsy_params_excel_path(...)` in `src/femic/pipeline/tipsy.py`, exported it in
  `femic.pipeline.__init__`, added deterministic coverage in `tests/test_tipsy.py`, and updated AST
  guardrails in `tests/test_legacy_orchestration_wiring.py` to assert
  `build_vdyp_cache_paths(...)` + `tipsy_params_excel_path(...)` seam usage in 00_data-prep.
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (183 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by centralizing remaining inline external-data root
  resolution and path selection logic in `00_data-prep.py` (`_select_external_data_root`,
  candidate list assembly, VRI/TSA source roots) into reusable I/O helper seams.
- Added `LegacyExternalDataPaths` + `resolve_legacy_external_data_paths(...)` in
  `src/femic/pipeline/io.py` to centralize external data-root candidate resolution and canonical
  VRI/TSA source path construction.
- Rewired `00_data-prep.py` to consume `resolve_legacy_external_data_paths(...)`, removing inline
  `_select_external_data_root` and candidate-list assembly logic from the script body.
- Exported external-path helpers in `femic.pipeline.__init__`, added deterministic helper coverage
  in `tests/test_pipeline_helpers.py`, and updated AST orchestration guardrails in
  `tests/test_legacy_orchestration_wiring.py` to assert
  `resolve_legacy_external_data_paths(...)` seam usage.
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (184 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by extracting remaining inline siteprod raster
  export/stack orchestration in `00_data-prep.py` (ArcRasterRescue command assembly, temporary
  layer path enumeration, cleanup loop) into dedicated stage/helper seams.
- Added `src/femic/pipeline/siteprod.py` with reusable siteprod orchestration helpers:
  `parse_arc_raster_rescue_layer_mappings(...)`, `list_siteprod_layers(...)`,
  `build_siteprod_layer_tif_path(...)`, `enumerate_siteprod_layer_tif_paths(...)`, and
  `export_and_stack_siteprod_layers(...)`.
- Rewired `00_data-prep.py` siteprod stage to consume `list_siteprod_layers(...)` and
  `export_and_stack_siteprod_layers(...)`, removing inline ArcRasterRescue command assembly,
  temporary-layer path enumeration, and temp cleanup loop logic.
- Exported siteprod helpers via `femic.pipeline.__init__`, added deterministic coverage in
  `tests/test_siteprod.py`, and updated AST guardrails in
  `tests/test_legacy_orchestration_wiring.py` to assert
  `list_siteprod_layers(...)` + `export_and_stack_siteprod_layers(...)` seam usage.
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (188 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by extracting remaining inline siteprod sampling
  orchestration in `00_data-prep.py` (`siteprod_species_lookup`, `mean_siteprod` closure, and row
  apply wiring) into reusable helper seams under `femic.pipeline.siteprod`.
- Expanded `src/femic/pipeline/siteprod.py` with reusable siteprod sampling helpers:
  `DEFAULT_SITEPROD_SPECIES_LOOKUP`, `siteprod_species_lookup(...)`,
  `mean_siteprod_for_row(...)`, and `assign_siteprod_from_raster(...)`.
- Rewired `00_data-prep.py` checkpoint2 siteprod assignment to call
  `assign_siteprod_from_raster(...)`, removing inline `siteprod_species_lookup` and nested
  `mean_siteprod(...)` closure logic from the script.
- Exported new sampling helpers via `femic.pipeline.__init__`, extended
  `tests/test_siteprod.py` with lookup + row-mean + assignment coverage, and updated AST guardrails
  in `tests/test_legacy_orchestration_wiring.py` to assert
  `assign_siteprod_from_raster(...)` seam usage.
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (190 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by extracting remaining inline species-volume
  compilation orchestration in checkpoint3 (`compile_species_vol` local function, map dispatch, and
  per-species assignment loop) into reusable helper seams.
- Added `src/femic/pipeline/species_volume.py` with reusable checkpoint3 species-volume helpers:
  `species_volume_input_columns(...)`, `compile_species_volume_series(...)`, and
  `compile_species_volume_columns(...)`.
- Rewired checkpoint3 species-volume compilation in `00_data-prep.py` to call
  `compile_species_volume_columns(...)`, removing inline `compile_species_vol(...)`, manual column
  assembly, map dispatch, and per-species assignment loop.
- Exported species-volume helpers via `femic.pipeline.__init__`, added deterministic coverage in
  `tests/test_species_volume.py`, and updated AST guardrails in
  `tests/test_legacy_orchestration_wiring.py` to assert
  `compile_species_volume_columns(...)` seam usage.
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (193 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by extracting remaining inline checkpoint2
  pre-filter/fillna normalization block (species/soil/BCLCS/LIVE_VOL defaults and filters) into a
  dedicated reusable helper seam.
- Added `src/femic/pipeline/vri.py` with
  `normalize_and_filter_checkpoint2_records(...)` to centralize checkpoint2 fill-defaults and
  row-filter rules (species slots, soil/BCLCS defaults, operability filters).
- Rewired `00_data-prep.py` checkpoint2 normalization stage to call
  `normalize_and_filter_checkpoint2_records(...)`, removing the large inline fillna/filter block.
- Exported VRI helper seams via `femic.pipeline.__init__`, added deterministic unit coverage in
  `tests/test_vri.py`, and updated AST guardrails in
  `tests/test_legacy_orchestration_wiring.py` to assert
  `normalize_and_filter_checkpoint2_records(...)` seam usage.
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (195 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by extracting remaining inline conifer/deciduous
  classification helpers (`is_conif`, `is_decid`, `pconif`, `pdecid`, stand-type classifiers) from
  `00_data-prep.py` into reusable helper seams.
- Expanded `src/femic/pipeline/vri.py` with reusable stand-classification helpers:
  `is_conifer_species_code(...)`, `is_deciduous_species_code(...)`, `pconif(...)`, `pdecid(...)`,
  `classify_stand_cdm(...)`, `classify_stand_forest_type(...)`, and
  `assign_forest_type_from_species_pct(...)`.
- Rewired `00_data-prep.py` to remove inline conifer/deciduous classifier function definitions and
  call `assign_forest_type_from_species_pct(...)` for forest-type assignment.
- Exported new VRI classification helpers via `femic.pipeline.__init__`, expanded
  `tests/test_vri.py` coverage for all classification helpers, and updated AST guardrails in
  `tests/test_legacy_orchestration_wiring.py` to assert
  `assign_forest_type_from_species_pct(...)` seam usage.
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (198 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by extracting remaining inline stratum-code assembly
  logic (`stratify_stand` + `stratify_stand_lexmatch` partial wiring) from `00_data-prep.py` into
  reusable helper seams.
- Expanded `src/femic/pipeline/vri.py` with reusable stratum-code helpers:
  `stratify_stand(...)` and `assign_stratum_codes_with_lexmatch(...)`.
- Rewired `00_data-prep.py` to remove inline `stratify_stand`/`stratify_stand_lexmatch` wiring and
  call `assign_stratum_codes_with_lexmatch(...)` at both stratum derivation stages.
- Exported new VRI stratum helpers via `femic.pipeline.__init__`, expanded
  `tests/test_vri.py` with deterministic stratification coverage, and updated AST guardrails in
  `tests/test_legacy_orchestration_wiring.py` to assert
  `assign_stratum_codes_with_lexmatch(...)` seam usage count.
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (200 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by extracting the remaining inline THLB sampling
  closure (`mean_thlb`) into a reusable helper seam so raster masking logic is no longer defined
  inline in `00_data-prep.py`.
- Added reusable THLB raster sampling helpers in `src/femic/pipeline/tsa.py`:
  `mean_thlb_for_geometry(...)` and `assign_thlb_raw_from_raster(...)`.
- Rewired `00_data-prep.py` THLB sampling stage to call
  `assign_thlb_raw_from_raster(...)`, removing inline `with rio.open(...): mean_thlb(...)` closure
  logic.
- Exported new THLB raster helpers via `femic.pipeline.__init__`, expanded deterministic coverage in
  `tests/test_pipeline_helpers.py`, and updated AST guardrails in
  `tests/test_legacy_orchestration_wiring.py` to assert
  `assign_thlb_raw_from_raster(...)` seam usage.
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (201 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by extracting the remaining inline checkpoint83
  post-THLB stand-filter block (`BCLCS_LEVEL_2`, management base, BEC, species/site-index null
  filters) into a reusable helper seam in `femic.pipeline.vri`.
- Expanded `src/femic/pipeline/vri.py` with
  `filter_post_thlb_stands(...)` to centralize checkpoint83 post-THLB stand filtering rules.
- Rewired `00_data-prep.py` checkpoint83 post-THLB filtering stage to call
  `filter_post_thlb_stands(...)`, removing the remaining inline filter chain.
- Exported the new VRI filter helper via `femic.pipeline.__init__`, expanded deterministic coverage
  in `tests/test_vri.py`, and updated AST guardrails in
  `tests/test_legacy_orchestration_wiring.py` to assert
  `filter_post_thlb_stands(...)` seam usage.
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (202 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by extracting remaining inline species-list
  derivation (`set().union(...)` over `SPECIES_CD_1..6`) into a reusable helper seam so derived
  species universes are no longer assembled ad hoc inside `00_data-prep.py`.
- Expanded `src/femic/pipeline/vri.py` with
  `derive_species_list_from_slots(...)` to centralize species-universe derivation from
  `SPECIES_CD_1..6` slot columns.
- Rewired `00_data-prep.py` to call `derive_species_list_from_slots(...)` instead of inline
  `set().union(...)` species-list assembly.
- Exported the new species-list helper via `femic.pipeline.__init__`, expanded deterministic
  coverage in `tests/test_vri.py`, and updated AST guardrails in
  `tests/test_legacy_orchestration_wiring.py` to assert
  `derive_species_list_from_slots(...)` seam usage.
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (203 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by extracting remaining inline post-bundle warning
  formatting for missing AU/curve mappings into a reusable diagnostics helper seam so 00_data-prep
  no longer assembles this warning text block inline.
- Added `emit_missing_au_curve_mapping_warning(...)` in `src/femic/pipeline/bundle.py` to
  centralize post-bundle missing AU/curve warning formatting and emission.
- Rewired `00_data-prep.py` post-bundle diagnostics to call
  `emit_missing_au_curve_mapping_warning(...)` instead of assembling warning text inline.
- Exported the new bundle diagnostics helper via `femic.pipeline.__init__`, expanded deterministic
  coverage in `tests/test_bundle.py`, and updated AST guardrails in
  `tests/test_legacy_orchestration_wiring.py` to assert
  `emit_missing_au_curve_mapping_warning(...)` seam usage.
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (204 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by extracting residual inline `f.shape` diagnostic
  notebook artifacts from `00_data-prep.py` into optional helper/log seams (or remove where dead)
  so the script body remains pure orchestration.
- Removed residual dead inline `f.shape` notebook diagnostic expressions from
  `00_data-prep.py` where they had no runtime effect.
- Verified this cleanup does not alter pipeline behavior; all required gates passed:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (204 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by removing remaining dead notebook preview artifacts
  (`au_table.head()`, `curve_table.head()`, `curve_points_table.head()`) so `00_data-prep.py`
  remains a pure orchestration script.
- Removed remaining dead notebook preview artifacts
  (`au_table.head()`, `curve_table.head()`, `curve_points_table.head()`) from `00_data-prep.py`.
- Verified no behavior change and full validation gate success:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (204 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by trimming residual notebook-only `if 1:` wrappers
  in `00_data-prep.py` where they no longer control branching, so orchestration flow is explicit.
- Removed residual notebook-only `if 1:` wrappers in `00_data-prep.py` that no longer controlled
  branching (01a stage block and checkpoint83 post-THLB block), leaving explicit orchestration
  flow.
- Verified behavior parity and full validation gate success:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (204 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by removing or gating remaining notebook-only plot
  diagnostics (`f.thlb_raw.describe()` / `f.thlb_raw.hist()`) so headless/script runs stay focused
  on pipeline outputs.
- Gated remaining notebook-only THLB diagnostics in `00_data-prep.py` behind
  `FEMIC_THLB_DIAGNOSTICS` (`0` default; enable with `1`/`true`/`yes`) so headless/script runs do
  not emit notebook-style plotting/stat calls unless explicitly requested.
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (204 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by removing remaining dead inline aggregate preview
  expressions (`f.query(...).groupby(...).sum()` and `f.groupby(...).sum()`) from
  `00_data-prep.py` so script-mode orchestration contains only side-effecting pipeline steps.
- Removed remaining dead inline aggregate preview expressions from `00_data-prep.py`
  (`f.query("thlb == 1").groupby(...).sum()` and `f.groupby("tsa_code").thlb_area.sum()`), leaving
  only side-effecting pipeline steps in this stage.
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (204 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by removing notebook carry-over no-op aliases like
  `stratify_stand = stratify_stand` if any remain, or mark completion of this cleanup tranche if
  none remain.
- Confirmed no residual notebook no-op alias assignments remained; removed adjacent dead empty cell
  marker artifacts in `00_data-prep.py` (`# --- cell 85 ---`, `# --- cell 101 ---`,
  `# --- cell 105 ---`) as part of the same cleanup tranche.
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (204 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by reducing residual generic exception handling in
  `00_data-prep.py` (e.g., broad `except:` blocks around helperable operations) into explicit helper
  seams or narrowed exception paths.
- Added `ensure_au_table_index(...)` in `src/femic/pipeline/bundle.py` and rewired
  `00_data-prep.py` to call it in place of the broad `try/except:` around
  `au_table.set_index("au_id", inplace=True)`.
- Exported the helper via `femic.pipeline.__init__`, expanded deterministic coverage in
  `tests/test_bundle.py`, and updated AST guardrails in
  `tests/test_legacy_orchestration_wiring.py` to assert `ensure_au_table_index(...)` seam usage.
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (206 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by narrowing broad `except Exception` around
  ipyparallel client initialization into explicit import/runtime exception paths (or helper seam)
  while preserving serial fallback behavior.
- Added `ParallelExecutionBackend` and `initialize_parallel_execution_backend(...)` in
  `src/femic/pipeline/stages.py` to centralize ipyparallel bootstrap + serial fallback behavior with
  explicit fallback exception classes (instead of broad `except Exception`), and rewired
  `00_data-prep.py` to consume that helper seam.
- Exported the new parallel backend seam via `femic.pipeline.__init__`, expanded deterministic
  coverage in `tests/test_pipeline_stages.py`, and updated AST guardrails in
  `tests/test_legacy_orchestration_wiring.py` to assert
  `initialize_parallel_execution_backend(...)` seam usage.
- Narrowed `stratify_stand(...)` row lookup fallback handling in `src/femic/pipeline/vri.py` from
  broad `except Exception` to explicit lookup errors (`KeyError`, `TypeError`, `IndexError`) and
  expanded coverage in `tests/test_vri.py` for attribute-style row objects.
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (209 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by narrowing remaining broad exception fallbacks in
  THLB helper seams (`mean_thlb_for_geometry(...)` / `assign_thlb_raw_from_raster(...)` in
  `src/femic/pipeline/tsa.py`) into explicit raster/row-lookup exception paths while preserving
  legacy default-on-error behavior.
- Narrowed broad THLB helper fallback scopes in `src/femic/pipeline/tsa.py`:
  `mean_thlb_for_geometry(...)` now catches explicit raster/mask runtime classes
  (`ValueError`, `TypeError`, `RuntimeError`, `OSError`) and
  `assign_thlb_raw_from_raster(...)` row geometry fallback now catches explicit lookup errors
  (`KeyError`, `TypeError`, `IndexError`).
- Expanded deterministic coverage in `tests/test_pipeline_helpers.py` to assert
  `mean_thlb_for_geometry(...)` still returns `default_on_error` for expected runtime failures while
  unexpected exceptions propagate.
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (211 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by auditing remaining broad `except Exception`
  handlers in pipeline helper modules that support legacy orchestration (next target:
  `src/femic/pipeline/vdyp_curves.py`) and narrow them to explicit operational fallback classes
  without changing emitted diagnostics.
- Narrowed remaining broad curve-smoothing exception handling in
  `src/femic/pipeline/vdyp_curves.py` by introducing an explicit
  `_curve_fit_fallback_exception_types()` tuple and applying it to both body-fit and toe-fit retry
  fallback paths in `process_vdyp_out(...)`.
- Preserved legacy fallback behavior for expected operational fit failures while allowing unexpected
  exceptions to propagate for visibility/debuggability.
- Expanded deterministic coverage in `tests/test_vdyp_curves.py` to assert:
  runtime body-fit failures still fallback to quasi-origin outputs, and unexpected body/toe failures
  (`ZeroDivisionError`) now propagate.
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (214 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by auditing broad fallback handlers in
  `src/femic/pipeline/vdyp_stage.py` and narrowing them to explicit subprocess/IO/parsing exception
  classes while preserving current logging semantics.
- Narrowed a first safe subset of broad exception handlers in `src/femic/pipeline/vdyp_stage.py`:
  `fit_stratum_curves(...)` now catches explicit curve-fit operational failures, and
  `execute_vdyp_batch(...)` now catches explicit subprocess execution and parse/import failure
  classes for `status=error` / `status=parse_error` logging paths.
- Preserved existing logging semantics for expected operational failures while allowing unexpected
  exceptions to propagate.
- Expanded deterministic coverage in `tests/test_vdyp_stage.py` to assert:
  `RuntimeError` curve-fit failures still skip species with `fit error` messages, and unexpected
  `ZeroDivisionError` failures in curve-fit, subprocess execution, and parse stages propagate.
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (217 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by narrowing the remaining broad exception handler in
  `execute_bootstrap_vdyp_runs(...)` (`dispatch_error` logging wrapper around `run_vdyp_fn`) into
  explicit run-stage exception classes while preserving JSONL diagnostics.
- Narrowed the remaining broad dispatch wrapper in
  `execute_bootstrap_vdyp_runs(...)` (`src/femic/pipeline/vdyp_stage.py`) to explicit
  `_bootstrap_dispatch_exception_types()` while preserving `dispatch_error` JSONL emission for known
  operational failures.
- Expanded deterministic coverage in `tests/test_vdyp_stage.py` to assert unexpected bootstrap
  dispatch failures (`ZeroDivisionError`) now propagate without being converted into
  `dispatch_error` records.
- Verified `src/femic/pipeline/vdyp_stage.py` now contains no `except Exception` handlers.
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (218 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by auditing remaining broad exception handlers in
  legacy-adapter modules (`src/femic/pipeline/tipsy.py`, `tipsy_config.py`, `tipsy_legacy.py`) and
  narrowing first safe operational fallback paths with explicit exception classes.
- Narrowed a first safe subset of broad exception fallbacks in tipsy adapter modules:
  `compute_vdyp_site_index(...)` and `compute_vdyp_oaf1(...)` in `src/femic/pipeline/tipsy.py`,
  forest-type mode fallback in `src/femic/pipeline/tipsy_config.py`, and species-slot unpack
  fallback in `tipsy_params_tsa40(...)` (`src/femic/pipeline/tipsy_legacy.py`).
- Preserved malformed-input fallback behavior for expected data-shape/key issues while allowing
  unexpected exceptions to propagate.
- Expanded deterministic coverage in `tests/test_tipsy.py`, `tests/test_tipsy_config.py`, and
  `tests/test_tipsy_legacy.py` to assert both expected fallback behavior and unexpected-error
  propagation.
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (222 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by narrowing the remaining broad exception wrapper in
  `build_tipsy_params_for_tsa(...)` (`src/femic/pipeline/tipsy.py`, around
  `evaluate_tipsy_candidate(...)`) to explicit candidate-evaluation data/runtime exception classes
  while preserving current debug message emission and re-raise behavior.
- Narrowed the remaining broad candidate-evaluation wrapper in
  `build_tipsy_params_for_tsa(...)` (`src/femic/pipeline/tipsy.py`) to explicit
  `_tipsy_candidate_exception_types()` while preserving legacy debug message emission and re-raise
  behavior for expected candidate-evaluation failures.
- Expanded deterministic coverage in `tests/test_tipsy.py` to assert:
  candidate `ValueError` paths still emit debug context then re-raise, and unexpected
  candidate-evaluation failures (`ZeroDivisionError`) propagate.
- Verified no `except Exception` handlers remain in tipsy adapter modules
  (`src/femic/pipeline/tipsy.py`, `tipsy_config.py`, `tipsy_legacy.py`).
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (224 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by auditing remaining broad exception handlers
  outside tipsy/vdyp modules (current highest-priority target: `src/femic/pipeline/tsa.py`) and
  narrowing operational fallback paths with explicit exception classes plus propagation tests.
- Narrowed the broad pre-VDYP resume checkpoint load handler in `01a_run-tsa.py` from
  `except Exception` to explicit pickle/IO/runtime classes
  (`OSError`, `EOFError`, `pickle.UnpicklingError`, `TypeError`, `AttributeError`,
  `ModuleNotFoundError`) while preserving existing failure message + non-fatal resume fallback
  behavior.
- Expanded AST guardrails in `tests/test_legacy_01a_structure.py` with
  `test_run01a_no_broad_exception_handlers` to prevent reintroduction of bare/broad exception
  handlers in `run_tsa(...)`.
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (225 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by narrowing the remaining broad exception handler in
  CLI entry wiring (`src/femic/cli/main.py`) with explicit command/runtime exception classes and
  targeted CLI regression coverage.
- Narrowed the remaining broad CLI debug-traceback handler in `src/femic/cli/main.py`
  (`_enable_rich_tracebacks`) to explicit optional-import failures
  (`ModuleNotFoundError`, `ImportError`) so unexpected import-time/runtime failures are no longer
  silently swallowed.
- Added targeted CLI coverage in `tests/test_cli_main.py` to assert missing optional `rich`
  dependency is ignored while unexpected import failures propagate.
- Completed broad-exception hardening audit for active orchestration/code paths:
  no `except Exception` or bare `except:` handlers remain in `src/`, `tests/`,
  `00_data-prep.py`, or `01a_run-tsa.py`.
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (227 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by replacing remaining sentinel `assert False`
  branches in legacy orchestration/helper modules with explicit typed errors carrying actionable
  context (start with legacy TIPSY builders in `src/femic/pipeline/tipsy_legacy.py`).
- Replaced sentinel `assert False` branches in legacy TIPSY builders
  (`src/femic/pipeline/tipsy_legacy.py`) with explicit typed errors carrying actionable context:
  `ValueError` for invalid unsupported species/BEC rule selections and `NotImplementedError` for
  explicitly unimplemented legacy forest-type branches.
- Added reusable error helpers (`_raise_invalid_legacy_tipsy_rule(...)`,
  `_raise_unimplemented_legacy_tipsy_rule(...)`) so failure paths are explicit and consistent.
- Expanded deterministic coverage in `tests/test_tipsy_legacy.py` to assert unsupported inputs raise
  typed/contextual errors and added an AST guardrail ensuring `tipsy_legacy.py` contains no
  `assert False` sentinels.
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (231 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by replacing remaining `assert False` sentinels in
  `src/femic/pipeline/vdyp_stage.py` (unreachable load-balanced branch and invalid `nsamples`
  guard) with explicit typed errors plus regression tests.
- Replaced remaining `assert False` sentinels in `src/femic/pipeline/vdyp_stage.py` with explicit
  typed errors:
  `NotImplementedError` for unsupported `ipp_mode='load_balanced'` branch in
  `run_vdyp_sampling(...)`, and `ValueError` for invalid `nsamples` mode values.
- Expanded deterministic coverage in `tests/test_vdyp_stage.py` to assert these branches now raise
  typed errors with informative messages.
- Verified no `assert False` sentinels remain in production orchestration/pipeline modules
  (`src/`, `00_data-prep.py`, `01a_run-tsa.py`).
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (232 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by auditing remaining broad `assert`-style runtime
  sentinels in production helper/orchestration paths (non-test) and replacing inappropriate
  runtime assertions with explicit typed errors where behavior is user/input dependent.
- Replaced remaining non-test runtime assertion control-flow checks with explicit typed errors in
  production modules:
  `resolve_tipsy_param_builder(...)` (`src/femic/pipeline/tipsy_config.py`),
  `run_legacy_subprocess(...)` (`src/femic/pipeline/stages.py`),
  `clean_stand_geometry(...)` (`src/femic/pipeline/stands.py`), and runtime config validation in
  `run_tsa(...)` (`01a_run-tsa.py`).
- Expanded deterministic coverage with new regression/guardrail tests in
  `tests/test_tipsy_config.py`, `tests/test_pipeline_stages.py`, `tests/test_stands.py`, and
  `tests/test_legacy_01a_structure.py` for new typed error branches and assertion-removal guards.
- Completed runtime assertion hardening audit:
  no `assert` statements remain in production orchestration/pipeline code
  (`src/`, `00_data-prep.py`, `01a_run-tsa.py`).
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (237 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by consolidating repeated legacy rule-error
  construction patterns (currently duplicated across TIPSY/VDYP helper seams) into shared diagnostic
  helpers where practical, while preserving existing external behavior and messages.
- Added shared diagnostics formatting helpers in `src/femic/pipeline/diagnostics.py`
  (`format_context_kv(...)`, `build_contextual_error_message(...)`) to centralize contextual
  error-string construction.
- Rewired legacy TIPSY and VDYP typed-error branches to use shared diagnostics formatting:
  `src/femic/pipeline/tipsy_legacy.py` and `src/femic/pipeline/vdyp_stage.py`, preserving existing
  behavior while reducing duplicated message assembly logic.
- Added deterministic coverage in `tests/test_diagnostics.py` and verified existing regression
  coverage still exercises the rewired TIPSY/VDYP error branches.
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (240 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by consolidating repeated structured event payload
  assembly in VDYP/TIPSY warning/error logging paths into shared builders where this can be done
  without changing emitted field sets.
- Extended shared diagnostics utilities in `src/femic/pipeline/diagnostics.py` with
  `build_timestamped_event(...)` to centralize structured event payload construction.
- Rewired duplicated VDYP/TIPSY event payload assembly to use shared helpers without changing
  emitted field sets:
  `build_tipsy_warning_event(...)` (`src/femic/pipeline/tipsy.py`) and bootstrap/batch
  VDYP run event logging paths in `src/femic/pipeline/vdyp_stage.py`
  (`dispatch`, `dispatch_error`, `timeout`, `error`, `parse_error`, `ok|empty_output`).
- Added deterministic unit coverage in `tests/test_diagnostics.py` for the shared event helper and
  validated existing TIPSY/VDYP regression suites against the rewired event construction paths.
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (240 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by auditing remaining ad hoc timestamped event/log
  payload builders outside VDYP/TIPSY (if any) and consolidating them into shared diagnostics
  helpers where this can be done with zero field-shape drift.
- Continued event-payload consolidation by rewiring remaining ad hoc VDYP run-event builders in
  `src/femic/pipeline/vdyp_stage.py` (`cache_only`, `start`, and curve-input missing-output
  warning) to use shared `build_timestamped_event(...)` helper.
- Preserved emitted field shapes/status semantics for existing log consumers and regression tests.
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (240 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by evaluating whether `process_vdyp_out(...)`
  (`src/femic/pipeline/vdyp_curves.py`) can adopt shared timestamped event builder without
  changing its intentional single-base-event timestamp semantics; if not, explicitly document that
  rationale and mark this consolidation sub-track complete.
- Completed the queued `vdyp_curves.py` evaluation and successfully adopted shared event helpers
  without changing its single-base-event timestamp semantics: `process_vdyp_out(...)` now builds its
  base event via shared `build_timestamped_event(...)` exactly once per run and reuses that payload
  across emitted events.
- Extended `build_timestamped_event(...)` (`src/femic/pipeline/diagnostics.py`) to support optional
  `status` and explicit `timestamp` override so both per-event and base-event patterns are supported
  through one helper.
- Expanded deterministic coverage in `tests/test_diagnostics.py` for status-optional event payloads
  and validated `tests/test_vdyp_curves.py` against the rewired base-event construction path.
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (241 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by closing the event-consolidation sub-track with a
  quick repo-wide audit for remaining ad hoc `event` + `timestamp` payload construction in
  production code and either (a) rewire to shared diagnostics helpers or (b) document explicit
  exceptions where intentional.
- Closed the queued event-consolidation audit by rewiring the final ad hoc structured event path in
  `src/femic/pipeline/vdyp_curves.py` (`vdyp_curve_anchor`) to shared
  `build_timestamped_event(...)` while preserving one-timestamp-per-run semantics.
- Extended `build_timestamped_event(...)` (`src/femic/pipeline/diagnostics.py`) to support optional
  `status` and explicit timestamp override, enabling both per-event and base-event reuse patterns.
- Added `build_vdyp_stream_header(...)` in `src/femic/pipeline/vdyp_logging.py` and rewired
  `execute_vdyp_batch(...)` (`src/femic/pipeline/vdyp_stage.py`) to consume it, removing the last
  inline timestamped stream-header string assembly from execution flow.
- Expanded deterministic coverage in `tests/test_diagnostics.py`, `tests/test_vdyp_curves.py`, and
  `tests/test_vdyp_logging.py` for the rewired helpers and timestamp-semantics guard.
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (242 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by reducing duplicated fallback-event assembly inside
  `process_vdyp_out(...)` (`src/femic/pipeline/vdyp_curves.py`) via a small internal event-builder
  seam that reuses shared diagnostics helpers without changing emitted fields.
- Reduced duplicated fallback-event assembly in `process_vdyp_out(...)`
  (`src/femic/pipeline/vdyp_curves.py`) by adding a small internal `emit_curve_event(...)` seam that
  reuses shared diagnostics event helpers while preserving emitted field sets and timestamp/context
  semantics.
- Rewired all `process_vdyp_out(...)` event emissions (fallback, body-fit error, toe-fit success,
  toe-fit warning, quasi-origin anchor) through the new internal seam; behavior remains unchanged.
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (242 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by auditing duplicate formatting/serialization logic in
  logging helpers (`append_jsonl`, stream-header and related callers) for additional safe
  centralization seams now that event payload assembly is consolidated.
- Consolidated duplicate logging-format/serialization logic in `src/femic/pipeline/vdyp_logging.py`
  by introducing `serialize_jsonl_payload(...)` and `append_line(...)`, then rewiring
  `append_jsonl(...)` to use these shared seams.
- Preserved existing external behavior (`default=str` JSON serialization and newline-terminated line
  append semantics) while removing repeated parent-dir + line-write patterns.
- Expanded deterministic coverage in `tests/test_vdyp_logging.py` for payload serialization and
  generic line-appending helpers.
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (244 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by auditing whether remaining specialized appenders
  (plain-text stream append and JSONL append callsites) can share a single file-append primitive
  end-to-end without reducing clarity or changing output contract.
- Completed the queued append-primitive audit in `src/femic/pipeline/vdyp_logging.py` by adding a
  shared internal file-append helper (`_append_text_fragment(...)`) and rewiring both
  `append_line(...)` and `append_text(...)` to consume it.
- Preserved output contracts: `append_line(...)` still appends newline-terminated records and
  `append_text(...)` still appends exact text fragments.
- Expanded deterministic coverage in `tests/test_vdyp_logging.py` with
  `test_append_text_appends_without_overwriting` to guard append-vs-overwrite behavior.
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (245 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by auditing remaining direct append-file writes
  outside `vdyp_logging`/`append_line` callsites and centralizing them only where behavior can
  remain byte-for-byte unchanged.
- Completed the queued direct-append audit across production Python paths (`src/`,
  `00_data-prep.py`, `01a_run-tsa.py`, `01b_run-tsa.py`): no remaining direct file-append writes
  exist outside `src/femic/pipeline/vdyp_logging.py`.
- Confirmed the only append-file primitive in production code is now
  `_append_text_fragment(...)` via `append_line(...)`/`append_text(...)`; no behavior-preserving
  rewires were needed in this slice.
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (245 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by auditing duplicated newline/stream framing usage
  around legacy subprocess output (`run_legacy_subprocess` and VDYP batch stream capture) and
  centralizing safe formatting seams without altering emitted log text.
- Completed the queued subprocess/stream-format audit by adding explicit formatting seams for both
  line-forwarded legacy subprocess output and VDYP stream artifact capture.
- Added `stream_filtered_subprocess_output(...)` in `src/femic/pipeline/stages.py` and rewired
  `run_legacy_subprocess(...)` to consume this helper, preserving line text/newline behavior while
  centralizing known-noise filtering.
- Added `build_vdyp_stream_log_block(...)` in `src/femic/pipeline/vdyp_logging.py` and rewired
  `execute_vdyp_batch(...)` (`src/femic/pipeline/vdyp_stage.py`) to use it for both stdout/stderr
  stream block assembly (`header + stream + trailing newline`), removing duplicated inline framing.
- Expanded deterministic coverage in `tests/test_pipeline_stages.py` and
  `tests/test_vdyp_logging.py` for these new stream-formatting helper seams.
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (247 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by auditing duplicated VDYP subprocess command-string
  assembly/metadata capture in `execute_vdyp_batch(...)` and centralizing it behind a helper seam
  without changing emitted command text or event fields.
- Completed the queued `execute_vdyp_batch(...)` command/metadata consolidation slice with two
  shared helper seams in `src/femic/pipeline/vdyp_stage.py`:
  `build_vdyp_batch_command(...)` (legacy command-string assembly) and
  `collect_vdyp_batch_run_metadata(...)` (shared returncode/duration/file-size/head capture).
- Rewired `execute_vdyp_batch(...)` to consume these helpers for timeout/error/parse-error/ok
  logging paths while preserving emitted command text and event field shape.
- Expanded deterministic coverage in `tests/test_vdyp_stage.py` for both new helpers, including
  legacy command-string shape and metadata-field extraction behavior.
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (249 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by auditing duplicated base-context enrichment in
  VDYP run orchestration (`run_vdyp_for_stratum`, `execute_vdyp_batch`) and centralizing it via a
  helper seam without changing emitted context keys/values.
- Completed the queued VDYP base-context consolidation by adding
  `build_vdyp_run_context(...)` in `src/femic/pipeline/vdyp_stage.py`.
- Rewired both `run_vdyp_for_stratum(...)` and `execute_vdyp_batch(...)` to consume the shared
  context helper so run-id/log-path/bin/params context defaults are centralized while preserving
  existing `setdefault(...)` semantics and emitted context fields.
- Expanded deterministic coverage in `tests/test_vdyp_stage.py` for
  `build_vdyp_run_context(...)`, including default-key population and preservation of
  caller-provided context values.
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (251 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by auditing repeated VDYP run-event payload fields
  in `execute_vdyp_batch(...)` (timeout/error/parse_error/ok) and centralizing shared payload
  assembly without changing emitted event keys/values.
- Completed the queued VDYP run-event payload consolidation in
  `src/femic/pipeline/vdyp_stage.py` by adding `build_vdyp_run_event(...)` for shared base field
  assembly (`event/status/phase/feature_count/cache_hits/ply_rows/lyr_rows/cmd/context`).
- Rewired `execute_vdyp_batch(...)` timeout/error/parse_error/ok|empty_output paths to consume
  `build_vdyp_run_event(...)`, preserving emitted event keys/values while removing duplicated
  inline payload assembly.
- Expanded deterministic coverage in `tests/test_vdyp_stage.py` for
  `build_vdyp_run_event(...)`, including int normalization of count fields and passthrough extra
  event fields.
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (252 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by auditing duplicated event-emission callsites in
  `execute_vdyp_batch(...)` (`append_jsonl_(vdyp_log_path, ...)`) and centralizing them via a
  local helper seam without changing write order or payload content.
- Completed the queued VDYP event-emission callsite consolidation in
  `src/femic/pipeline/vdyp_stage.py` by adding a local `_emit_run_event(...)` seam inside
  `execute_vdyp_batch(...)`.
- Rewired timeout/error/parse_error/ok|empty_output paths to call `_emit_run_event(...)`, removing
  duplicated `append_jsonl_(vdyp_log_path, ...)` callsites while preserving event payload content
  and emission order.
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (252 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by auditing duplicated temporary-file basename/path
  extraction in `execute_vdyp_batch(...)` and centralizing it behind a helper seam without changing
  runtime filenames or downstream parse behavior.
- Completed the queued temporary-file extraction consolidation in
  `src/femic/pipeline/vdyp_stage.py` by adding `VdypBatchTempArtifacts` and
  `resolve_vdyp_batch_temp_artifacts(...)` to centralize basename/path derivation from temp files.
- Rewired `execute_vdyp_batch(...)` to consume resolved temp artifacts for infile writing, command
  assembly, output-table import path resolution, and run-metadata file stats while preserving
  runtime filename behavior.
- Expanded deterministic coverage in `tests/test_vdyp_stage.py` for
  `resolve_vdyp_batch_temp_artifacts(...)` (basename + full-path expectations).
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (253 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by auditing duplicated numeric coercion (`int(...)`)
  across VDYP batch run-event payload construction and consolidating this coercion at one seam
  without changing emitted values.
- Completed the queued VDYP numeric-coercion consolidation by adding
  `VdypRunEventCounts` + `normalize_vdyp_run_event_counts(...)` in
  `src/femic/pipeline/vdyp_stage.py` and routing shared count coercion through this seam.
- Rewired `build_vdyp_run_event(...)` to consume normalized count payloads and updated
  `execute_vdyp_batch(...)` to reuse the same normalized counts for both run-event emission and
  stream-header construction.
- Expanded deterministic coverage in `tests/test_vdyp_stage.py` for
  `normalize_vdyp_run_event_counts(...)` and updated `build_vdyp_run_event(...)` tests to assert
  unchanged emitted values under the new count wrapper.
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (254 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by auditing repeated `Path(...)` coercions in VDYP
  helpers (`build_vdyp_batch_command`, `resolve_vdyp_batch_temp_artifacts`,
  `collect_vdyp_batch_run_metadata`) and centralizing only where behavior remains unchanged.
- Completed the queued VDYP path-coercion consolidation by adding `_as_path(...)` in
  `src/femic/pipeline/vdyp_stage.py` and reusing it in:
  `build_vdyp_batch_command(...)`, `resolve_vdyp_batch_temp_artifacts(...)`, and
  `collect_vdyp_batch_run_metadata(...)`.
- Preserved behavior while reducing repeated inline `Path(...)` casts and broadened
  `collect_vdyp_batch_run_metadata(...)` to accept either `str` or `Path` path-like inputs.
- Expanded deterministic coverage in `tests/test_vdyp_stage.py` with a string-path metadata test
  to confirm unchanged size/head extraction behavior across path input types.
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (255 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by auditing repeated callable-cast setup in
  `execute_vdyp_batch(...)` and centralizing safe dependency-resolution/cast seams without changing
  runtime defaults or injection points.
- Completed the queued callable-resolution/cast consolidation in
  `src/femic/pipeline/vdyp_stage.py` by adding `VdypBatchExecutionDependencies` and
  `resolve_vdyp_batch_execution_dependencies(...)`.
- Rewired `execute_vdyp_batch(...)` to consume resolved dependency fields
  (`write_vdyp_infiles`, `import_vdyp_tables`, `append_jsonl`, `append_text`,
  `build_stream_header`, `build_stream_log_block`, `subprocess_run`) while preserving default
  runtime imports and explicit injection override behavior.
- Expanded deterministic coverage in `tests/test_vdyp_stage.py` with an injection-preservation test
  for `resolve_vdyp_batch_execution_dependencies(...)`.
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (256 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by auditing repeated ephemeral helper closures inside
  `execute_vdyp_batch(...)` (`_emit_run_event`) and promoting reusable pieces where this improves
  clarity without changing event emission semantics or order.
- Completed the queued closure-promotion slice in `src/femic/pipeline/vdyp_stage.py` by replacing
  the local `_emit_run_event` closure with reusable module helper `emit_vdyp_run_event(...)`.
- Rewired `execute_vdyp_batch(...)` timeout/error/parse_error/ok|empty_output branches to call
  `emit_vdyp_run_event(...)`, preserving event payload shape, write order, and log sink behavior.
- Expanded deterministic coverage in `tests/test_vdyp_stage.py` with
  `test_emit_vdyp_run_event_appends_payload` to assert helper emission semantics.
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (257 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by auditing repeated `dict(...)` defensive copies in
  VDYP helper seams (`build_vdyp_run_context`, `build_vdyp_run_event`) and centralizing copy policy
  where clarity improves without mutability regressions.
- Closed P2.2c by adding shared stage executor `execute_legacy_tsa_stage(...)` in
  `src/femic/pipeline/stages.py` and rewiring `00_data-prep.py` 01a/01b orchestration to use
  explicit kwargs builders (`_build_01a_run_kwargs`, `_build_01b_run_kwargs`) instead of inline
  module-load + per-TSA run-loop plumbing.
- Updated orchestration wiring guardrails in `tests/test_legacy_orchestration_wiring.py` to assert
  helper-driven 01a/01b dispatch and preserved explicit keyword handoff payloads.
- Added stage-helper regression coverage in `tests/test_pipeline_stages.py` for
  `execute_legacy_tsa_stage(...)` success and missing-symbol failure behavior.
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (259 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice (ASAP closure path): finish `P2.1b` by eliminating remaining
  implicit/global state handoff at 00->01a/01b boundaries, then close `P2.2a`/`P2.2b` with
  explicit major-step wrappers and thin orchestration sequencing.
- Reduced remaining `P2.1b` implicit-state handoff by removing `globals().get(...)` runtime
  injection in `00_data-prep.py` for 01a runtime config (`vdyp_out_cache`, `curve_fit_impl`) and
  replacing it with explicit stage-level variables passed through `_build_01a_run_kwargs(...)`.
- Added AST guardrail coverage in `tests/test_legacy_orchestration_wiring.py` to assert no
  `globals().get(...)` orchestration handoff remains.
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (260 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice (ASAP closure path): continue `P2.1b` by auditing remaining 01b
  hard-coded runtime paths and introducing explicit runtime config handoff (mirroring 01a-style
  typed runtime payload) to eliminate residual implicit file-path globals at stage boundaries.
- Closed remaining `P2.1b` boundary implicitness by introducing `Legacy01BRuntimeConfig` +
  `build_legacy_01b_runtime_config(...)` in `src/femic/pipeline/legacy_runtime.py` and wiring
  explicit runtime handoff from `00_data-prep.py` into `01b_run-tsa.py`.
- Refactored `01b_run-tsa.py` to require typed `runtime_config` and consume shared TIPSY path
  helpers (`tipsy_params_excel_path`, `tipsy_stage_output_paths`) plus runtime output-root/template
  settings instead of hard-coded stage-path literals.
- Extended orchestration/runtime guardrails in `tests/test_legacy_orchestration_wiring.py` and
  `tests/test_pipeline_stages.py` for 01b runtime config builder usage and explicit handoff.
- Marked `P2.1b` complete: 00->01a/01b stage boundaries now pass typed runtime payloads and no
  longer rely on implicit `globals().get(...)` runtime injection.
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (261 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice (ASAP closure path): close `P2.2a` by wrapping the largest remaining
  major orchestration block in `00_data-prep.py` (post-01b bundle + AU/curve assignment segment)
  behind a shared helper with explicit inputs/outputs, then sequence it under `P2.2b`.
- Closed `P2.2a` by wrapping the largest remaining post-01b orchestration block in
  `00_data-prep.py` behind explicit input/output helper
  `_run_post_01b_bundle_and_curve_assignment_stage(...)`, including bundle load/build,
  stratum/AU assignment, curve-id mapping, and checkpoint writes.
- Stage output handoff is now explicit (`f`, `au_table`, `curve_table`, `curve_points_table`),
  removing the last large inline notebook-style block from top-level execution flow.
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (261 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice (ASAP closure path): close `P2.2b` by adding one thin
  top-level orchestration function in `00_data-prep.py` that sequences the extracted stage calls
  with explicit intermediate payload handoff and minimal side effects.
- Closed `P2.2b` by adding `_run_legacy_tsa_orchestration_stage(...)` in `00_data-prep.py` to
  sequence 01a stage execution, 01b stage execution, and post-01b bundle/AU/curve assignment under
  one explicit handoff seam.
- Removed remaining inline top-level sequencing calls for 01a/01b and bundle-path stage dispatch;
  stage outputs now flow through the orchestration helper return payload.
- Queued next extraction slice (ASAP closure path): start `P2.3a` with smoke tests for extracted
  core helpers (path/validation and key deterministic transforms) to lock in current behavior before
  Phase 3 workflow hardening.
- Started and closed `P2.3a` by extending smoke coverage with CLI preflight file-validation tests
  (`tests/test_cli_main.py`) and lightweight transform smoke checks for TSA normalization/checkpoint
  path building (`tests/test_smoke.py`).
- Queued next extraction slice (ASAP closure path): start `P2.3b` by adding deterministic,
  small-sample assertions for one or two extracted core helpers where behavior contracts are
  currently implicit (without expanding runtime-heavy legacy integration scope).
- Closed `P2.3b` with deterministic, small-sample CLI preflight assertions in
  `tests/test_cli_main.py`, including exact missing-required-file failure behavior and stable error
  classification under controlled repo layouts.
- Marked `P2.3` complete now that both `P2.3a` and `P2.3b` are closed.
- Queued next extraction slice (ASAP closure path): begin Phase 3 (`P3.1a`) by validating and
  tightening Sphinx config/package surface (theme/extensions/autosummary defaults) now that Phase 2
  modularization + minimal helper test coverage are complete.
- Closed `P3.1a` by upgrading `docs/conf.py` with explicit extension defaults
  (`sphinx.ext.autodoc`, `sphinx.ext.autosummary`, `sphinx.ext.napoleon`,
  `sphinx.ext.viewcode`) plus optional enablement for `nbsphinx` and
  `sphinx_rtd_theme` when installed in the environment.
- Added `autosummary_generate = True`, notebook-checkpoint exclusions, and resilient theme/static
  settings so docs builds stay warning-clean under `-W` even when optional packages are absent.
- Queued next extraction slice (ASAP closure path): continue `P3.1` with `P3.1b` by adding
  `docs/reference/cli.rst` and wiring `docs/index.rst` to mirror current CLI help surface.
- Closed `P3.1b` by replacing the docs placeholder index with a real reference toctree and adding
  `docs/reference/cli.rst` containing the current `python -m femic --help` command/option surface
  (top-level plus `run`, `prep`, `vdyp`, `tsa`, and `tipsy` subcommand entries).
- Queued next extraction slice (ASAP closure path): close `P3.1c` with a GitHub Pages docs build
  workflow that runs Sphinx in CI and publishes `_build/html`.
- Closed `P3.1c` by adding `.github/workflows/docs-pages.yml` with PR/push docs build, strict
  `sphinx-build -W` gating, artifact upload, and deploy-to-Pages on pushes to `main`.
- Marked `P3.1` complete now that docs config, reference content, and Pages CI publishing are all
  in place.
- Queued next extraction slice (ASAP closure path): start `P3.2a` by mapping current `femic` CLI
  commands/subcommands to a draft Nemora task taxonomy table in docs.
- Closed `P3.2a` by adding `docs/reference/nemora-task-map.rst` and wiring it into docs index
  to map current CLI entries (`run`, `prep run`, `vdyp run/report`, `tsa run`,
  `tipsy validate`) to draft Nemora task keys.
- Queued next extraction slice (ASAP closure path): close `P3.2b` by inventorying extracted shared
  utilities and tagging top upstream candidates (diagnostics/logging/path/runtime helpers).
- Closed `P3.2b` by adding `docs/reference/nemora-upstream-candidates.rst` and wiring it into docs
  index with a prioritized inventory of extracted helper modules suitable for Nemora upstreaming.
- Marked `P3.2` complete now that CLI taxonomy mapping and upstream-candidate inventory are both in
  place.
- Queued next extraction slice (ASAP closure path): start `P3.3a` by adding a first config file
  schema for selecting TSA/mode flags and mapping it into existing run option parsing.
- Closed `P3.3a` by adding YAML/JSON run-profile loading
  (`load_pipeline_run_profile(...)`) and explicit CLI/profile merge logic
  (`resolve_effective_run_options(...)`) for `femic run` TSA/strata/mode selection.
- Added `--run-config` support in `femic run`, a template profile at
  `config/run_profile.example.yaml`, and reference docs for schema/precedence in
  `docs/reference/run-config.rst`.
- Added deterministic coverage for run-profile loading/validation and CLI integration in
  `tests/test_pipeline_helpers.py` and `tests/test_cli_main.py`.
- Queued next extraction slice (ASAP closure path): close `P3.3b` by extending run manifest payload
  metadata with profile/config provenance and versioned output-root annotations.
- Closed `P3.3b` by extending run metadata through `PipelineRunConfig`/`LegacyExecutionPlan` with
  output-root + config provenance fields and surfacing them in manifest payload sections
  (`config_provenance`, `outputs`, and output-root option/path annotations).
- Added manifest/run-config coverage updates in `tests/test_pipeline_helpers.py` and
  `tests/test_legacy_manifest.py` plus SHA256 helper coverage for profile provenance digests.
- Marked `P3.3` complete now that config selection/mode wiring and manifest/version metadata are
  both in place.
- Queued next extraction slice (ASAP closure path): start `P3.4a` by auditing bootstrap/sample
  randomness seams and introducing explicit seed controls where stochastic behavior still exists.
- Closed `P3.4a` by adding explicit deterministic seed controls across VDYP sampling helpers:
  `run_vdyp_sampling(...)`, `run_vdyp_for_stratum(...)`, and bootstrap dispatch sequencing with
  per-stratum/SI derived seeds.
- Added `FEMIC_SAMPLING_SEED` env support for deterministic bootstrap/sample draws and coverage in
  `tests/test_vdyp_stage.py` for fixed-seed sampling stability and per-dispatch seed derivation.
- Queued next extraction slice (ASAP closure path): close `P3.4b` by ensuring run manifests capture
  full runtime/tool version metadata consistently for config-driven and non-config runs.
- Closed `P3.4b` by extending manifest payload runtime metadata capture with an explicit
  `runtime_parameters` block and seed/config provenance fields (`FEMIC_SAMPLING_SEED`,
  `FEMIC_RUN_CONFIG_*`, output-root metadata).
- Added regression assertions in `tests/test_legacy_manifest.py` for runtime-parameter sections and
  seed/config provenance values.
- Marked `P3.4` complete now that deterministic seed control and runtime parameter/version metadata
  capture are both implemented.
- Queued next extraction slice (ASAP closure path): start `P3.5a` by updating README workflow docs
  to reflect run-config profiles, manifest provenance fields, and deterministic sampling controls.
- Closed `P3.5a` by updating `README.md` workflow documentation for config-driven runs
  (`--run-config`), deterministic sampling control (`FEMIC_SAMPLING_SEED`), and manifest metadata
  sections used for reproducibility/audit.
- Closed `P3.5b` by adding a concise end-to-end quickstart flow in `README.md` covering
  CLI help check, TIPSY config validation, single-TSA run, and VDYP diagnostics reporting.
- Marked `P3.5` complete now that workflow handoff docs and quickstart are both in place.
- Queued next extraction slice (ASAP closure path): run a final roadmap consistency pass and
  prepare branch for merge/deployment handoff.
- Completed final roadmap consistency pass: all Phase 1/2/3 checklist items are now checked,
  including parent closeout for `P2.1` (its sub-items were already complete).
- Branch is ready for merge/deployment handoff.
- Added `planning/TSA29_dataset_compile_plan.md` with an explicit runbook for compiling TSA 29,
  including the required `config/tipsy/tsa29.yaml` gate, config-driven run steps, diagnostics, and
  completion criteria.
- Debugged TSA29 TIPSY config bring-up blocker: replaced species-whitelist rule with a catch-all
  rule (`when: {}`) and added null defaults for optional schema columns (`SPP_2..5`, `PCT_2..5`,
  `GW_*`, `GW_age_*`) so `tipsy_params_columns` projection succeeds.
- Re-ran TIPSY stage directly from cached TSA29 artifacts (`vdyp_prep-tsa29.pkl`,
  `vdyp_results-tsa29.pkl`, `vdyp_curves_smooth-tsa29.feather`) and regenerated
  `data/tipsy_params_tsa29.xlsx` + `data/02_input-tsa29.dat` with 30 AU rows (10 strata x 3 SI).
- Immediate next queue: have user run BatchTIPSY against `data/02_input-tsa29.dat`, upload
  `data/04_output-tsa29.out`, then execute 01b/post-01b assembly to validate full end-to-end TSA29
  compile.
- Added a dedicated downstream CLI recovery path for manual BatchTIPSY handoff:
  `python -m femic tsa post-tipsy --tsa <code> [-v]`.
- Implemented `run_post_tipsy_bundle(...)` in `src/femic/workflows/legacy.py` to run 01b from
  cached TSA artifacts (`vdyp_prep-tsaXX.pkl`, `vdyp_curves_smooth-tsaXX.feather`) and rebuild
  `data/model_input_bundle/{au_table,curve_table,curve_points_table}.csv` without re-running the
  full 00/01a front-half.
- Added regression coverage for command wiring and downstream assembly in
  `tests/test_cli_main.py` and `tests/test_workflows_post_tipsy.py`.
- Immediate next queue: polish 01b runtime warnings (deprecated
  `delim_whitespace`, figure-close loop, lexsort warnings) and add a run manifest entry for the
  new `tsa post-tipsy` command.
- Added targeted `vdyp_io` ignore rules in `.gitignore` for generated scratch artifacts
  (`vdyp_err_*`, `vdyp_out_*`, `vdyp_ply_*`, `vdyp_lyr_*`, and tmp dirs/files) so `git status`
  stays clean while retaining tracked `vdyp_io/VDYP_CFG` assets.
- Updated ignore strategy to also exclude volatile local `vdyp_io/VDYP_CFG` runtime files
  (`VDYP7_BACK.ctl`, `VDYP7_VDYP.ctl`, `vdyp7.log`) and untracked them from git index so repeated
  model runs no longer generate persistent dirty-state churn.
- Closed queued runtime-noise cleanup for 01b:
  replaced deprecated `delim_whitespace` parsing with `sep="\\s+"`, pre-sorted the VDYP curve
  MultiIndex once before per-AU plotting, and added explicit `plt.close(fig)` in the loop to
  prevent figure accumulation warnings during `tsa post-tipsy` runs.
- Closed queued run-manifest/audit logging for `femic tsa post-tipsy`:
  added workflow-level manifest emission (`started`/`ok`/`failed`) with runtime metadata + output
  artifact checks, and wired CLI `--run-id`/`--log-dir` through the command.
- Started TSA29 TIPSY rule quality tuning: replaced single-species catch-all behavior with ordered
  provisional BEC/species-group rules (pine, fir, spruce, balsam pathways) including species mixes,
  adjusted density/utilization, and modest GW settings while preserving final catch-all coverage.
- Added regression coverage in `tests/test_tipsy_config.py` for key TSA29 rule matches
  (MS pine pathway and IDF fir pathway).
- Regenerated `data/tipsy_params_tsa29.xlsx` + `data/02_input-tsa29.dat` from cached TSA29
  artifacts using the tuned ruleset so next BatchTIPSY run can proceed immediately.
- Remaining immediate queue: run BatchTIPSY with the new TSA29 input, re-run
  `femic tsa post-tipsy --tsa 29`, then add managed-vs-unmanaged curve-dominance regression
  assertions from the refreshed outputs.
- Upgraded TSA29 TIPSY parameter rules to TSR-anchored assumptions using Williams Lake data
  package references:
  `reference/29ts_dpkg_2024-2.pdf` (Section 8.5) and
  `reference/williams_lake_tsa_data_package-2.pdf` (Section 6.3 Tables 23–25).
- Updated `config/tipsy/tsa29.yaml` from provisional heuristics to ordered BEC/species pathways
  with explicit treated/untreated proportions, regeneration delays, species mixes, densities, and
  genetic-worth values aligned to TSR assumptions, while preserving catch-all coverage.
- Synced TSA29 config tests in `tests/test_tipsy_config.py` to the new rule expectations.
- Fixed a TSA29 resume-path loader defect in `src/femic/pipeline/vdyp_stage.py` by adding
  fallback reads for plain Feather caches lacking GeoPandas metadata.
- Forced 01a rerun for TSA29 and regenerated `data/02_input-tsa29.dat` from cached artifacts
  under the new ruleset (30 AU rows retained; values changed materially).
- Immediate next queue:
  user runs BatchTIPSY with regenerated `data/02_input-tsa29.dat`, uploads refreshed
  `data/04_output-tsa29.out`, then we run
  `python -m femic tsa post-tipsy --tsa 29 --run-id <id> -v`
  and validate refreshed `tipsy_vdyp_tsa29-*.png` behavior.
- Added custom management-unit boundary mode for `femic run` profiles:
  `selection.boundary_path`, `selection.boundary_layer`, and `selection.boundary_code`
  now flow from run profile to legacy execution env (`FEMIC_BOUNDARY_*`).
- Implemented boundary-mode extraction in `00_data-prep.py`:
  when `FEMIC_BOUNDARY_PATH` is set, FEMIC unions that layer geometry and uses it as the
  VRI mask for the selected run code (e.g., `k3z`), forcing no-cache execution.
- Added a complete K3Z test-case scaffold:
  `config/run_profile.k3z.yaml`, `config/tipsy/tsak3z.yaml`, and
  `planning/K3Z_dataset_compile_plan.md`.
- Extended TIPSY config discovery/validation to support non-numeric case codes
  (`tsak3z.yaml`) in addition to numeric TSA configs.
- Removed numeric-TSA assumptions in downstream ID assembly by introducing a deterministic
  named-code AU prefix path in `src/femic/pipeline/bundle.py` and `src/femic/pipeline/tsa.py`.
- Ran smoke execution for K3Z (`--debug-rows 20`, no BatchTIPSY output yet):
  run completed and emitted manifest
  `vdyp_io/logs/run_manifest-k3z_smoke5_20260304_221317.json`,
  generating `data/02_input-tsak3z.dat` and `data/tipsy_params_tsak3z.xlsx`.
- Immediate next queue:
  run full K3Z step 1a without debug-row truncation, then user runs BatchTIPSY on
  `data/02_input-tsak3z.dat`, uploads `data/04_output-tsak3z.out`, and we execute
  `python -m femic tsa post-tipsy --tsa k3z --run-id <id> -v`.
- Hardened config-driven TIPSY mix output (`src/femic/pipeline/tipsy_config.py`) to eliminate
  known BatchTIPSY failure patterns in treated rows:
  normalize `SX -> SW`, drop treated broadleaf species from `f` mixes, enforce descending
  species order (dominant species in `SPP_1`), and force exact integer composition sums to 100.
- Added regression coverage in `tests/test_tipsy_config.py` for mix normalization and TSA29 rule
  behavior (`AT`/`SX` removed from treated `f` rows, dominant species promoted to `SPP_1`,
  `% composition == 100`).
- Validation gate completed for this slice:
  `.venv/bin/ruff format src tests`, `.venv/bin/ruff check src tests`,
  `.venv/bin/mypy src`, `.venv/bin/pytest`, `.venv/bin/pre-commit run --all-files`.
- Immediate next queue:
  regenerate TSA29 step 1a artifacts (`data/tipsy_params_tsa29.xlsx`, `data/02_input-tsa29.dat`)
  from a clean non-stalled run path, then rerun BatchTIPSY and post-tipsy downstream assembly.
- Added config-driven SI tuning support in `src/femic/pipeline/tipsy_config.py`:
  per-side `SI_offset` (or `si_offset`) can now be set in either `defaults.{e,f}` or any
  rule `assign.{e,f}` block; final per-side SI is computed as
  `round(computed_vdyp_si + SI_offset, 1)`.
- Updated TSA29 config defaults to apply a +2.0 managed-side SI bump directly in config:
  `config/tipsy/tsa29.yaml -> defaults.f.SI_offset: 2.0`.
- Added/updated tests in `tests/test_tipsy_config.py` for side-specific SI offset handling
  and TSA29 +2 SI expectations.
- Regenerated TSA29 step-1a artifacts from cached TSA29 prep outputs with the new config:
  `data/tipsy_params_tsa29.xlsx` and `data/02_input-tsa29.dat` now embed the +2 managed SI
  adjustment without manual dat editing.
- Extended TIPSY SI tuning from additive-only to linear transform support in
  `src/femic/pipeline/tipsy_config.py`:
  per-side config can now define `SI_c1` and `SI_c2` (plus lowercase aliases), applied as
  `SI_final = SI_c1 * SI_baseline + SI_c2` (with legacy `SI_offset` still honored).
- Updated TSA29 managed defaults to explicit linear form in `config/tipsy/tsa29.yaml`:
  `defaults.f.SI_c1: 1.0`, `defaults.f.SI_c2: 2.0` (equivalent to fixed +2 SI).
- Added regression tests in `tests/test_tipsy_config.py` for linear SI transform behavior and
  retained backward-compatible SI offset coverage.
- Updated TIPSY config docs/templates:
  `config/tipsy/README.md` and `config/tipsy/template.tsa.yaml` now describe SI linear tuning
  fields and usage.
- Added TSA29 VDYP smoothing override for pathological curve AU 21005 (`SBPS_PL`, `L`) in
  `src/femic/pipeline/vdyp_overrides.py`: `skip1=50`.
- Added default per-curve VDYP fit diagnostic plot generation in
  `src/femic/pipeline/vdyp_stage.py` during smoothing runs:
  each stratum/SI now emits `plots/vdyp_fitdiag_tsaXX-<stratumi>-<stratum>-<si>.png` showing
  observed 5-year binned median/IQR vs fitted curve.
- Re-ran TSA29 01a/01b and post-tipsy stages to validate integration:
  AU 21005 unmanaged curve corrected from early spike (peak 943.9 @ age 19) to a coherent shape
  (peak 96.3 @ age 223), and fresh overlays/diagnostics were written.
- Extended VDYP smoothing diagnostics in `src/femic/pipeline/vdyp_stage.py` to compare
  three fit flavours per stratum/SI on each default fitdiag PNG:
  baseline/current, sigma-asymmetric candidate, tail-blend candidate, plus conditional
  auto-skip candidate when heuristically detected and validation-approved.
- Extended `src/femic/pipeline/vdyp_curves.py` with two candidate-fit controls used by the new
  diagnostics:
  right-tail sigma reweighting (`sigma_right_scale`/`sigma_right_offset`) and optional
  right-tail linear blend (`tail_blend_enabled`, anchor/blend/slope controls).
- Added first-pass auto left-tail anomaly detection in `execute_curve_smoothing_runs(...)`:
  infer suggested `skip1` from early-age overshoot, rerun, and only accept candidate when it
  clears all validation gates (`rmse`, `tail_rmse`, `early_overshoot` vs baseline).
- Ran TSA29 targeted smoothing from cached prep/results artifacts (no full rerun required) and
  regenerated:
  `data/vdyp_curves_smooth-tsa29.feather`,
  `plots/vdyp_fitdiag_tsa29-*.png` (30 files),
  and comparison summary `plots/vdyp_fitdiag_tsa29_metrics_compare.csv`.
- Quick quantitative readout from `vdyp_fitdiag_tsa29_metrics_compare.csv`:
  best-overall-RMSE counts across 30 curves were `tail_blend=18`, `sigma_asym=9`, `current=3`;
  best-tail-RMSE counts were `sigma_asym=18`, `tail_blend=9`, `current=3`.
  Auto-skip was suggested in 18 curves but validated in 0 under current strict acceptance gates.
- Follow-up fit-logic revision based on visual QA feedback:
  removed `sigma_asym` candidate from default diagnostics and switched focus to a stronger
  tail-blend approach.
- Updated `src/femic/pipeline/vdyp_curves.py` tail blend algorithm to detect a rightmost linear
  binned segment automatically (maximal contiguous tail from the right that meets
  `R² >= tail_linear_min_r2` and `NRMSE <= tail_linear_max_nrmse`), then blend the current NLLS
  curve into that linear tail. If no credible linear tail exists, it naturally falls back to
  raw/current behavior (no tail override).
- New tail controls in `process_vdyp_out(...)`:
  `tail_linear_min_points`, `tail_linear_min_r2`, `tail_linear_max_nrmse`
  (with existing `tail_blend_years` and slope bounds still applied).
- Updated default fitdiag plotting in `src/femic/pipeline/vdyp_stage.py` to show:
  `current`, `tail_blend`, and validated `auto_skip` only.
- Re-ran TSA29 smoothing from cached artifacts and regenerated:
  `data/vdyp_curves_smooth-tsa29.feather`,
  30 plots at `plots/vdyp_fitdiag_tsa29-*.png`,
  and tail-only comparison summary at
  `plots/vdyp_fitdiag_tsa29_metrics_tail_only.csv`.
- Tail-only readout on TSA29 (30 curves):
  `tail_blend` improved overall RMSE on 17 curves and improved tail RMSE on 17 curves;
  auto-skip remained suggested in 18 curves.
- Tail-blend failure diagnosis + heuristic correction (2026-03-05 follow-up):
  identified that quantile fallback and non-age-constrained tail selection were still allowing
  early-age pseudo-linear segments to be blended (for example ESSF_SE-L anchoring near age 65),
  causing severe regressions.
- Updated right-tail detection in `src/femic/pipeline/vdyp_curves.py` to require
  preferred-age tail candidates (`tail_linear_prefer_min_age`, default 200) and skip blending
  entirely when no preferred candidate passes thresholds.
- Kept quantile fallback disabled for TSA29 diagnostic runs
  (`tail_linear_allow_quantile_fallback=False`) so non-linear tails naturally retain
  the current/NLLS curve.
- Regenerated TSA29 fit diagnostics + metrics with the stricter age-aware logic:
  `plots/vdyp_fitdiag_tsa29-*.png` and
  `plots/vdyp_fitdiag_tsa29_metrics_tail_only.csv`.
- New outcome (TSA29, 30 curves):
  no catastrophic tail-blend failures remain; worst RMSE regression is now ~0.045
  (`IDF_FDI-L`) instead of multi-unit failures.
- Relaxed-tail detection calibration pass (to capture more long near-linear segments):
  in `src/femic/pipeline/vdyp_stage.py` updated candidate tail thresholds to
  `tail_linear_min_r2=0.82`, `tail_linear_max_nrmse=0.12`,
  `tail_linear_prefer_min_age=190.0`.
- Re-ran TSA29 smoothing + diagnostics with relaxed thresholds:
  tail-blend detection increased from 22/30 to 26/30 curve pairs (4 still intentionally skipped).
- Updated summary (`plots/vdyp_fitdiag_tsa29_metrics_tail_only.csv`) shows broader tail capture
  with controlled but non-zero tradeoff:
  `tail_better_rmse=15/30`, `tail_better_tail_rmse=15/30`;
  worst remaining regression is moderate (`IDF_PL-H`, ΔRMSE ~ +0.67), with no catastrophic outliers.
- Added a detailed planning summary of this entire curve-fit enhancement stream at:
  `planning/VDYP_curve_fit_enhancements_2026-03-05.md`, including explicit TODO notes to
  continue tuning tail-fit hyperparameters later.
- Enhanced default fit diagnostic plotting for lecture/demo use:
  `src/femic/pipeline/vdyp_stage.py` now overlays raw per-sample VDYP curves
  (`Age` vs `Vdwb`) as fine low-alpha grey lines behind binned aggregates/fitted curves.
- Re-ran K3Z with updated fitting/plotting logic:
  `python -m femic run --run-config config/run_profile.k3z.yaml -v --run-id k3z_curvefit_enh_20260305`.
  Run completed and emitted manifest
  `vdyp_io/logs/run_manifest-k3z_curvefit_enh_20260305.json`.
- New K3Z fit diagnostics are available at `plots/vdyp_fitdiag_tsak3z-*.png` (9 plots for
  strata/SI combos with usable VDYP outputs: CWH_CW, CWH_FD, CWH_HW), with raw VDYP lines
  visible in the updated style.
- Ran full K3Z post-TIPSY integration using user-supplied BatchTIPSY output:
  copied `data/02_output-tsak3z.out` to expected runtime filename
  `data/04_output-tsak3z.out`, then executed
  `python -m femic run --run-config config/run_profile.k3z.yaml -v --resume --run-id k3z_posttipsy_20260306_062442`.
  Run completed successfully (manifest:
  `vdyp_io/logs/run_manifest-k3z_posttipsy_20260306_062442.json`) and regenerated K3Z artifacts,
  including `plots/strata-tsak3z.png`, `plots/tipsy_vdyp_tsak3z-*.png`,
  `data/tipsy_params_tsak3z.xlsx`, and `data/tipsy_curves_tsak3z.csv`.
- Debugged K3Z strata diagnostics regression and fixed summary/plot logic:
  `src/femic/pipeline/tsa.py::build_strata_summary(...)` now avoids reintroducing filtered strata
  as NaN rows, and falls back to unfiltered top strata when `min_standcount` removes everything
  (small custom boundaries).
- Improved strata plotting robustness in `src/femic/pipeline/plots.py`:
  relative-abundance ordering now tolerates missing `totalarea_p`,
  SI x-limits auto-expand to observed values (so high coastal SI is not clipped at 30),
  and sparse-strata `stripplot` points are overlaid on violins for visibility.
- Added K3Z-specific legacy TIPSY-vs-VDYP y-axis scaling helper
  `tipsy_vdyp_ylim_for_tsa(...)` (`0..1500` for `k3z`, default `0..600`) and wired
  `01b_run-tsa.py` to use it.
- Re-ran K3Z end-to-end with the fixes:
  `python -m femic run --run-config config/run_profile.k3z.yaml -v --run-id k3z_plotfix_20260306_063833`.
  Run completed (`status=ok`, manifest:
  `vdyp_io/logs/run_manifest-k3z_plotfix_20260306_063833.json`) with corrected
  01a diagnostics (`coverage 1.0`, `count 9`) and refreshed K3Z plot artifacts.
- Applied K3Z-focused scoping + comparison updates:
  set `TARGET_NSTRATA_BY_TSA["k3z"] = 4` in `src/femic/pipeline/tsa.py`
  to constrain the custom-boundary case to top-4 strata by area.
- Updated smoothing-output selection in `src/femic/pipeline/vdyp_stage.py` so K3Z
  exports tail-blend unmanaged curves (when available) to
  `vdyp_curves_smooth-tsak3z.feather` for downstream TIPSY-vs-VDYP comparison plots,
  while keeping fitdiag overlays unchanged (`current` + candidate curves).
- Added regression coverage:
  `tests/test_pipeline_helpers.py` now asserts `target_nstrata_for("k3z") == 4`,
  and `tests/test_vdyp_stage.py` now verifies K3Z smoothing output prefers tail-blend
  candidate curves when present.
- Deleted all stale K3Z plot artifacts (`plots/*tsak3z*`) and re-ran K3Z end-to-end:
  `python -m femic run --run-config config/run_profile.k3z.yaml -v --run-id k3z_n4_tailblend_20260306_064902`.
  Run completed (`status=ok`, manifest:
  `vdyp_io/logs/run_manifest-k3z_n4_tailblend_20260306_064902.json`) with
  01a diagnostics now reporting `count 4` and `coverage 0.9882` (top-4 strata only).
- Implemented adaptive SI split-count logic in `src/femic/pipeline/tsa.py` from per-stratum
  5th-95th percentile SI width:
  `< 5` -> `M` only, `5..10` -> `L/H`, `> 10` -> `L/M/H`.
- Wired the same adaptive SI quantile resolver into VDYP curve fitting
  (`src/femic/pipeline/vdyp_stage.py::fit_stratum_curves`) so fit outputs and AU definitions
  stay aligned for narrow-SI strata.
- Hardened SI assignment and AU mapping for variable split counts:
  `assign_si_levels_from_stratum_quantiles(...)` now supports optional
  `allowed_levels_by_stratum`, and `00_data-prep.py` passes allowed levels inferred from
  `au_table` so post-01b stand assignment cannot request non-existent SI bins.
- Updated TIPSY parameter assembly to tolerate missing per-stratum SI bins cleanly
  (`src/femic/pipeline/tipsy.py::build_tipsy_params_for_tsa` skips absent fit levels).
- Added regression coverage for adaptive split behavior and missing-level handling:
  `tests/test_pipeline_helpers.py`, `tests/test_tipsy.py`, `tests/test_vdyp_stage.py`.
- Re-validated K3Z end-to-end under the adaptive SI split logic:
  `FEMIC_NO_CACHE=1 PYTHONPATH=src .venv/bin/python -m femic run --run-config config/run_profile.k3z.yaml -v --run-id k3z_siwidth_verify_20260306_070055`.
  Run completed `status=ok` (manifest:
  `vdyp_io/logs/run_manifest-k3z_siwidth_verify_20260306_070055.json`), producing
  an 8-row K3Z TIPSY input table where `CWH_CW` is now correctly split into `L/H` only.
- Fixed K3Z comparison-plot scaling request:
  `src/femic/pipeline/plots.py::tipsy_vdyp_ylim_for_tsa(...)` now returns `0..2000`
  for `k3z` (was `0..1500`), with regression assertion updated in
  `tests/test_pipeline_helpers.py`.
- Fixed fitdiag regeneration behavior:
  1) `01a_run-tsa.py` now rebuilds smoothing outputs whenever `resume_effective=False`
     (so non-resume/no-cache runs do not silently reuse stale
     `vdyp_curves_smooth-tsa*.feather`), and
  2) `src/femic/pipeline/vdyp_stage.py` now emits fitdiag PNGs even when binned
     observations are missing (overlay is conditional, plot emission is unconditional).
- Fixed no-cache VDYP bootstrap cache reuse:
  `00_data-prep.py` now sets `force_run_vdyp = 1` whenever `_femic_no_cache` is active,
  preventing stale `data/vdyp_results-tsa*.pkl` reuse during no-cache/debug/custom-boundary runs.
- Fixed adaptive-SI bootstrap dispatch bug surfaced by forced reruns:
  `src/femic/pipeline/vdyp_stage.py::execute_bootstrap_vdyp_runs(...)` now skips missing/empty
  SI payloads per stratum (`status=skipped`, reason `missing_or_empty_si_sample`) instead of
  raising `KeyError` when a stratum has `L/H` only under adaptive split rules.
- Re-ran K3Z with forced fresh VDYP bootstraps:
  `FEMIC_NO_CACHE=1 PYTHONPATH=src .venv/bin/python -m femic run --run-config config/run_profile.k3z.yaml -v --run-id k3z_forcevdyp_fix_20260306_072037`.
  Run completed `status=ok` (manifest:
  `vdyp_io/logs/run_manifest-k3z_forcevdyp_fix_20260306_072037.json`) and regenerated
  current K3Z artifacts from fresh caches:
  `data/vdyp_results-tsak3z.pkl` (updated), 8 fitdiag plots (`plots/vdyp_fitdiag_tsak3z-*.png`)
  and 8 TIPSY-vs-VDYP comparison plots (`plots/tipsy_vdyp_tsak3z-*.png`).
- Extracted K3Z FSP stocking guidance from `data/bc/cfa/k3z/NICF-LP-Forest-Stewardship-Plan-Appendices-2020.pdf` (Appendix B, pp. 4-6) and replaced provisional K3Z TIPSY assumptions with FSP-informed mixed-species pathways in `config/tipsy/tsak3z.yaml`.
- Updated K3Z TIPSY rule set to use CWH-leading-species pathways (`CW/YC`, `HW/HM`, `FD/FDC`, `SS/SX`) with `Density=900`, `Regen_Delay=2`, and explicit mixed compositions summing to 100% instead of single-species 1400-sph defaults.
- Re-ran K3Z no-cache pipeline with new rules:
  `PYTHONPATH=src .venv/bin/python -m femic run --run-config config/run_profile.k3z.yaml -v --run-id k3z_fsp_rules_20260306_073524`.
  Run completed (`status=ok`, manifest `vdyp_io/logs/run_manifest-k3z_fsp_rules_20260306_073524.json`) and regenerated K3Z artifacts.
- Verified regenerated `data/02_input-tsak3z.dat` now reflects new FSP-informed parameters (8 rows; all rows `Density=900`, `Regen_Delay=2`, and mixed-species compositions such as `CW60/HW25/YC15`, `HW70/CW20/FD10`, `FD60/HW25/CW15`).
- Next: user runs BatchTIPSY with the refreshed K3Z DAT, uploads updated `data/04_output-tsak3z.out`, then we re-run post-TIPSY to evaluate whether TIPSY-vs-VDYP coherence improved under FSP-informed assumptions.
- Added a dedicated K3Z compile/iteration playbook at
  `planning/CFAK3Z_dataset_compile_plan.md`, adapted from TSA29 planning but
  rewritten for K3Z-specific constraints (small-area sparse strata, fixed BatchTIPSY
  field-map dependency, and iterative TIPSY-vs-VDYP tuning workflow).
- Documented next refinement queue for K3Z stratification:
  1) BEC subzone/variant/phase-based keys and
  2) top-N leading-species combination keys (start N=2, test N=3).
- Confirmed VRI attribute availability needed for this refinement from local 2019
  GDB (`BEC_SUBZONE`, `BEC_VARIANT`, `BEC_PHASE`, `SPECIES_CD_1..6`,
  `SPECIES_PCT_1..6`, SI fields).
- Confirmed `data/bc/vri/VEG_COMP_LYR_R1_POLY_2024.gdb.zip` currently fails unzip
  integrity checks (incomplete/corrupt), so K3Z refinement should proceed on
  existing readable VRI until a clean 2024 download is available.

- Added configurable stratum-key controls to the run-profile/env pipeline:
  `selection.stratification.bec_grouping` (`zone|subzone|variant|phase`),
  `selection.stratification.species_combo_count` (top-N species by `SPECIES_PCT_1..6`),
  and `selection.stratification.include_tm_species2_for_single`.
- Wired those controls from YAML -> effective run options -> legacy execution env
  (`FEMIC_STRAT_*`) -> `00_data-prep.py` -> `assign_stratum_codes_with_lexmatch(...)`,
  with backward-compatible defaults so existing TSA runs keep legacy behavior.
- Updated K3Z run profile to exercise finer strata by default:
  `config/run_profile.k3z.yaml` now sets `bec_grouping: subzone` and
  `species_combo_count: 2`.
- Confirmed local VRI schema supports this path (fields present in 2019 GDB):
  `BEC_SUBZONE`, `BEC_VARIANT`, `BEC_PHASE`, `SPECIES_CD_1..6`, `SPECIES_PCT_1..6`.
- Updated legacy external-data path resolution to prefer 2024 VRI when present, with
  automatic fallback to 2019:
  `bc/vri/2024/VEG_COMP_LYR_R1_POLY_2024.gdb` -> `bc/vri/2019/VEG_COMP_LYR_R1_POLY.gdb`.
- Added explicit source-path startup prints in `00_data-prep.py` so each run reports the
  exact VRI and TSA boundary datasets in use.
- Added regression coverage to lock 2024-first behavior:
  `tests/test_pipeline_helpers.py::test_resolve_legacy_external_data_paths_prefers_2024_vri_when_available`.
- Extended external-data resolver to also pick a paired VDYP input GDB (2024-first, then 2019)
  and wired `00_data-prep.py` to use that resolved path, with startup printout:
  `using VDYP input source: ...`.
- Verified 2024 K3Z runs now resolve both:
  `VEG_COMP_LYR_R1_POLY_2024.gdb` and
  `VEG_COMP_VDYP7_INPUT_POLY_AND_LAYER_2024.gdb`.
- Current blocker on 2024 K3Z compile quality:
  01a VDYP bootstrap events are all `empty_output`, resulting in
  `data/vdyp_curves_smooth-tsak3z.feather` with `0` rows and thus an empty
  `data/02_input-tsak3z.dat`. This points to a 2024 schema/field-mapping mismatch in
  VDYP input preparation rather than path resolution.
- Completed 2024 VDYP ID-domain fix for K3Z:
  in `run_vdyp_for_stratum(...)` (`src/femic/pipeline/vdyp_stage.py`), bootstrap dispatch now
  resolves sampled source `FEATURE_ID`s to the VDYP table key space using `MAP_ID` when direct
  `FEATURE_ID` overlap is absent, then maps returned VDYP outputs back to source IDs for cache
  compatibility.
- Added regression coverage for the map-join fallback:
  `tests/test_vdyp_stage.py::test_run_vdyp_for_stratum_maps_source_feature_ids_via_map_id`
  asserts that non-overlapping source IDs are bridged through `MAP_ID` and still return results
  keyed by original source `FEATURE_ID`.
- Re-ran full no-cache K3Z pipeline against 2024 VRI+VDYP inputs:
  `FEMIC_NO_CACHE=1 PYTHONPATH=src .venv/bin/python -u -m femic run --run-config config/run_profile.k3z.yaml -v --run-id k3z_vri2024_mapfix_20260307`.
  Run completed `status=ok` with non-empty outputs (`data/vdyp_curves_smooth-tsak3z.feather`
  rows `= 3588`, `data/02_input-tsak3z.dat` lines `= 13`) and VDYP report showing no empty-output
  failures (`status counts: dispatch=12, start=12, ok=12`).
- Consulted the local VRI metadata PDFs in `docs/reference` to avoid schema guessing while
  debugging (`vegcomp_poly_rank1_data_dictionaryv5_2019*.pdf`,
  `vegcomp_toc_data_dictionaryv5_2019.pdf`); practical takeaway for this run path remains:
  `MAP_ID` is the reliable bridge field across 2024 VRI rank1 samples and 2024 VDYP input layers
  when `FEATURE_ID` domains diverge.
- Added profile/env support for cumulative top-strata selection by area coverage:
  new config key `selection.stratification.top_area_coverage` (wired through CLI/profile/env as
  `FEMIC_STRAT_TOP_AREA_COVERAGE`) and 01a runtime (`target_area_coverage`) now drive
  `build_strata_summary(..., target_coverage=...)`.
- K3Z profile now sets `top_area_coverage: 0.95` in `config/run_profile.k3z.yaml`.
- Re-ran K3Z no-cache with 95% top-area cutoff:
  `FEMIC_NO_CACHE=1 PYTHONPATH=src .venv/bin/python -u -m femic run --run-config config/run_profile.k3z.yaml -v --run-id k3z_cov95_20260307`.
  Result: `coverage=0.95565930139286`, `count=13` strata in 01a (up from 4).
- BEC hierarchy check on selected strata: all selected strata are still identical at
  zone+subzone (`CWHvm`), and also at zone+subzone+variant (`CWHvm1`) and phase (all null),
  so deeper BEC hierarchy splitting cannot add signal for K3Z with current VRI attributes.
- SI split diagnostics for this 95% run show many sparse bins in the long-tail strata
  (`L/M/H` counts often 0-2 stands), with multiple `skipped` or `empty_output` VDYP events;
  this supports a likely next change to collapse SI splitting for sparse strata in K3Z.
- Implemented user-requested K3Z stratification reset and stabilization path:
  `top_area_coverage` lowered to `0.80`, adaptive SI-width split override removed,
  and SI bins restored to fixed quantile bands (`L=5..35`, `M=35..65`, `H=65..95`).
- Added post-fit adjacent SI-curve merge support in TIPSY AU assembly
  (`src/femic/pipeline/tipsy.py::build_tipsy_params_for_tsa`), with configurable
  relative-gap thresholds over a bounded age window; merged groups now map to a
  shared AU while preserving per-stratum diagnostics (`si-groups [...]`).
- Fixed merged-AU downstream regression failure in bundle assignment:
  `assign_curve_ids_from_au_table(...)` now handles duplicate `au_id` rows
  (introduced by SI merges) by collapsing to first non-null managed/unmanaged
  curve IDs before managed/unmanaged curve selection.
- Hardened stand-export AU lookup for merged AUs:
  `prepare_stands_export_frame(...)` now resolves `theme3` canfi species safely
  when `au_table` has duplicate `au_id` rows.
- Added regression tests for merged-AU duplicate-row behavior:
  `tests/test_bundle.py::test_assign_curve_ids_from_au_table_handles_duplicate_au_rows`
  and `tests/test_stands.py::test_prepare_stands_export_frame_handles_duplicate_au_rows`.
- Re-validated K3Z end-to-end with requested settings:
  `FEMIC_NO_CACHE=1 PYTHONPATH=src .venv/bin/python -u -m femic run --run-config config/run_profile.k3z.yaml -v --run-id k3z_cov80_fixedsi_merge_debug2_20260307`
  now completes `status=ok` (manifest:
  `vdyp_io/logs/run_manifest-k3z_cov80_fixedsi_merge_debug2_20260307.json`).
- Next tuning focus (as requested): keep fixed quantile SI bins, then adjust
  post-fit merge criteria to avoid over-fragmentation while preserving clearly
  distinct VDYP curve families.
- Implemented pre-fit SI-bin stabilization in `fit_stratum_curves(...)`:
  added `min_stands_per_si_bin` (default `25`) and automatic adjacent-bin collapse before
  NLLS fitting; collapse actions are now logged per stratum (for sparse K3Z bins this
  prevents fragile one- or two-stand regressions).
- Updated TIPSY SI-level merge logic in `build_tipsy_params_for_tsa(...)` to use a
  combined criterion instead of max-relative-gap alone:
  merge now requires both `max_relative_gap <= threshold` and
  `window_nrmse <= threshold` over a shared age window; merge diagnostics now print
  `gap/rmse/nrmse` values.
- Added deterministic config-driven species/siteprod overrides for weak mapping cases:
  `species_code_overrides` (for example `DR -> FD`) and
  `siteprod_si_fallback_by_species` are now supported by `tipsy_config` builders and
  consumed by candidate evaluation when siteprod SI is absent/invalid.
- Added requested stratum-level L/M/H overlay plot output:
  `execute_curve_smoothing_runs(...)` now emits
  `plots/vdyp_lmh_tsa<tsa>-<stratum>-<code>.png` so L/M/H best-fit curves are visible on
  one panel for ordering/material-difference QA.
- Wired legacy siteprod source resolution to prefer
  `data/bc/siteprod/Site_Prod_BC.gdb` (fallback to legacy root path), and surfaced the
  resolved path in 00-data-prep startup logging.
- Re-ran full no-cache K3Z with fresh 2024 VRI/VDYP + fresh siteprod source:
  `run_id=k3z_siteprod_refresh_20260307` completed `status=ok` with updated fitdiag,
  L/M/H overlay, and TIPSY-vs-VDYP plot outputs under `plots/`.
- Next tuning queue (explicitly requested): continue calibrating post-fit tail/merge
  hyperparameters and SI-bin collapse thresholds now that the new diagnostics are in place.
- Two-pass K3Z rebin regression root cause identified: stale TSA-specific VDYP feather caches
  (`data/vdyp_ply-tsak3z.feather`, `data/vdyp_lyr-tsak3z.feather`) were still being reused even
  under `FEMIC_NO_CACHE=1`, so first-pass VDYP key remap operated on mismatched IDs.
- Fixed loader precedence and cache refresh behavior:
  `load_vdyp_input_tables(...)` now prioritizes explicit `source_feature_ids` over `source_map_ids`,
  and 01a now forces VDYP source reload whenever `runtime_config.force_run_vdyp` is true.
- Fixed VDYP output remap robustness:
  `run_vdyp_for_stratum(...)` now maps per-table outputs back to resolved feature IDs via VDYP
  table attrs (`Map Name` + `Polygon`) before ID/order fallbacks, handling table-number keyed
  outputs and extra-table cases.
- Verified with fresh no-cache K3Z run
  (`run_id=k3z_twopass_fix5_20260307`): two-pass now reports
  `mapped VDYP SI for 194/251 rows` (was `0/251`), `missing=3 of 447` in cache-table rebuild
  (was `447/447`), and full downstream TIPSY/bundle stages complete without empty-curve failure.
- Added configurable SI-bin collapse threshold to run profiles:
  `modes.vdyp_min_stands_per_si_bin` now flows from YAML/CLI profile parsing into
  legacy env (`FEMIC_VDYP_MIN_STANDS_PER_SI_BIN`) and into 01a stratum fitting
  (`build_stratum_fit_run_config(min_stands_per_si_bin=...)`).
- Updated K3Z test profile for current iteration:
  `config/run_profile.k3z.yaml` now uses `top_area_coverage: 0.90` and
  `modes.vdyp_min_stands_per_si_bin: 10` (with `species_combo_count: 2`).
- Executed no-cache K3Z validation run with these settings:
  `tmp/k3z_sc2_restore.log` reports `coverage=0.90655`, `count=9` selected strata,
  and currently generated AU bundle has `27` AUs (`9 strata x 3 SI levels`), with
  Sitka spruce present (`CWHvm_HW+SS`).
- Executed comparison run for 3-species stratification under same thresholds:
  `tmp/k3z_sc3_run.log` reports `coverage=0.90153`, `count=25` selected strata;
  resulting AU bundle expanded to `66` AUs (`22 strata x 3 SI levels` after downstream
  consolidation), confirming species-combo=3 greatly increases fragmentation.
- Next suggested tuning step for teaching-case usability: keep species-combo=2 as
  default, then selectively carve SS-focused strata via explicit rule/override
  rather than globally increasing to species-combo=3.
- Added AU species-proportion curve export in post-TIPSY bundle assembly:
  for each AU, `curve_table/curve_points_table` now include
  `unmanaged_species_prop_<SPP>` and `managed_species_prop_<SPP>` curves (single-point at `x=1`).
- Species universe for these curves is pre-scanned from inventory checkpoint
  `data/ria_vri_vclr1p_checkpoint8.feather` using top-6 VRI slots (`SPECIES_CD_1..6` with
  positive `SPECIES_PCT_*`) scoped to selected TSA(s); this yields a full consistent per-AU
  species set (zero-valued curves emitted for absent species in a specific AU).
- Unmanaged species proportions are sourced from VDYP fit payload species shares per
  `(stratum_code, si_level)`; managed species proportions are sourced from
  `tipsy_sppcomp_tsa<tsa>.csv` proportions.
- Added regression coverage for species-proportion curve emission:
  `tests/test_bundle.py::test_build_bundle_tables_from_curves_adds_species_proportion_curves`.
- 2026-03-08 (TIPSY DAT hardening): finalized fixed-schema DAT rendering in `src/femic/pipeline/tipsy.py` using explicit row/header start maps, mandatory full schema columns (including blank GW/SPP slots), and fixed-length line emission so BatchTIPSY column mappings remain stable for sparse K3Z mixes.
- 2026-03-08 (verification): regenerated `data/02_input-tsak3z.dat` from `data/tipsy_params_tsak3z.xlsx`; row slices now cleanly parse expected values (`PCT_1=70`, `SI=23.9`, `SPP_2=CW`, `PCT_2=20`, `SPP_3=FD`, `PCT_3=10`) without `7023.` concatenation.
- 2026-03-08 (TIPSY DAT alignment fix #2): switched DAT row layout to exact 1-based BatchTIPSY wizard indices from the user screenshots (converted to 0-based in code), including sparse-field ranges like `PCT_1: 61-63`, `Regen_Method: 64`, `SI: 108-111`, `SPP_2: 129-131`, `PCT_2: 136-137`, etc.; line length now fixed at 231 chars to match GW_age_5 end column.
- 2026-03-08 (TIPSY DAT anti-regression hardening): introduced a single canonical `DEFAULT_TIPSY_BATCH_COLUMNS_1BASED` schema (directly mirroring BatchTIPSY wizard indices), derive 0-based starts/widths from it, and enforce per-row fixed-width slice validation before writing DAT output; generator now fails fast on any field overflow/misalignment.
- 2026-03-08: Per request, removed all prior plot files and ran a full fresh no-cache K3Z compile using current profile settings; produced a clean single set of regenerated K3Z plots for review (`run_id=k3z_fresh_20260308_032428`).
- 2026-03-08: Added a profile-driven managed-yield fallback mode for teaching/small-case stability (`modes.managed_curve_mode: vdyp_transform`) that synthesizes managed curves directly from VDYP unmanaged curves via configurable transforms (`x_scale`, `y_scale`, culmination-tail truncation, `max_age`).
- 2026-03-08: Applied this mode to K3Z profile (`x_scale=0.8`, `y_scale=1.2`, truncate tail, max age 300), cleared old plots, and reran a full fresh no-cache K3Z compile (`run_id=k3z_vdyp_managed_20260308_1`) producing a clean regenerated plot set.
- 2026-03-08: Added a new roadmap phase (`Phase 4`) to track `femic.fmg` delivery:
  Patchworks-first ForestModel XML + fragments shapefile generation from current FEMIC outputs,
  with Woodstock portability work carried in parallel but prioritized second.
- 2026-03-08: Added initial `femic.fmg` implementation in `src/femic/fmg/patchworks.py`:
  ForestModel XML writer, fragments shapefile builder, and high-level
  `export_patchworks_package(...)` orchestration wired from bundle/checkpoint artifacts.
- 2026-03-08: Added `femic export patchworks` CLI command in `src/femic/cli/main.py`
  with configurable TSA list, bundle/checkpoint paths, planning horizon, CC age window,
  output directory, and fragments CRS.
- 2026-03-08: Fixed Patchworks fragments export for feather checkpoints with WKB geometry payloads:
  exporter now normalizes bytes/memoryview/hex geometries before GeoDataFrame construction.
- 2026-03-08: Added regression coverage for Patchworks export in
  `tests/test_fmg_patchworks.py` and `tests/test_cli_main.py` (XML content, fragments fields,
  CLI wiring, WKB decode case).
- 2026-03-08: Updated user-facing docs for Patchworks export:
  `README.md` quickstart and `docs/reference/cli.rst` command reference.
- 2026-03-08: Ran full milestone validation gates after export implementation:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest`,
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W` all passing.
- 2026-03-08: Added fail-fast Patchworks validation in `src/femic/fmg/patchworks.py`:
  `validate_forestmodel_xml_tree(...)` now checks required ForestModel nodes/attrs,
  required define fields, curve-idref integrity, and CC treatment presence; and
  `validate_fragments_geodataframe(...)` now checks required fragment schema,
  value domains (`IFM`), geometry validity/non-null, uniqueness of `BLOCK`,
  numeric coercion, and positive area.
- 2026-03-08: Hooked validations into export orchestration:
  `export_patchworks_package(...)` now validates XML tree and fragments data before writing.
- 2026-03-08: Added regression tests for validation rules in
  `tests/test_fmg_patchworks.py` (missing curve-idref detection and invalid IFM rejection).
- 2026-03-08: Validated Patchworks package builds for both active test cases:
  `k3z` via direct CLI export from current bundle/checkpoint, and `tsa29` via
  a reconstructed TSA29 validation bundle/checkpoint built from cached TSA29 prep artifacts
  (`vdyp_prep-tsa29.pkl`, `vdyp_curves_smooth-tsa29.feather`,
  `tipsy_curves_tsa29.csv`, `tipsy_sppcomp_tsa29.csv`).
- 2026-03-08: Documented the Patchworks export contract in docs:
  `docs/reference/patchworks-export.rst` now captures required ForestModel XML
  structure and required fragments schema fields enforced by exporter validators.
- 2026-03-08: Added initial Woodstock compatibility export module
  `src/femic/fmg/woodstock.py` with `export_woodstock_package(...)`
  (CSV outputs from current FEMIC bundle/checkpoint artifacts), wired to
  CLI as `femic export woodstock`.
- 2026-03-08: Added shared FMG core dataclasses in `src/femic/fmg/core.py`
  (`CurvePoint`, `CurveDefinition`, `AnalysisUnitDefinition`, `BundleModelContext`)
  and bundle adapters in `src/femic/fmg/adapters.py` so Patchworks/Woodstock exporters
  consume one normalized AU/curve context instead of duplicating parsing logic.
- 2026-03-08: Refactored `src/femic/fmg/patchworks.py` and
  `src/femic/fmg/woodstock.py` to use shared adapters/context; revalidated exports:
  - Patchworks `k3z` (`au=14`, `fragments=218`, `curves=54`)
  - Woodstock `k3z` (`yield_rows=16162`, `area_rows=218`)
  - Woodstock `tsa29` from reconstructed validation bundle/checkpoint
    (`yield_rows=10050`, `area_rows=147959`).
- 2026-03-08: Added initial deterministic Patchworks XML fixture parity coverage
  (`tests/fixtures/fmg/forestmodel_minimal.xml`,
  `tests/test_fmg_patchworks.py::test_write_forestmodel_xml_matches_fixture`)
  as the first concrete step toward `P4.2b`.
- 2026-03-08: Completed core class migration milestone for `P4.2a` by adding
  explicit ForestModel/Treatment-related dataclasses in `src/femic/fmg/core.py`
  (`ForestModelDefinition`, `SelectDefinition`, `TreatmentDefinition`,
  `AttributeBinding`, `DefineFieldDefinition`, `TreatmentAssignment`) and moving
  Patchworks XML construction to `build_patchworks_forestmodel_definition(...)`
  + `forestmodel_definition_to_xml_tree(...)`.
- 2026-03-08: Expanded deterministic XML parity coverage for `P4.2b` with a
  richer multi-AU/species fixture:
  `tests/fixtures/fmg/forestmodel_multi_au.xml` and
  `tests/test_fmg_patchworks.py::test_write_forestmodel_xml_matches_multi_au_fixture`.
- 2026-03-08 next queue: start treatment transition/action parity work beyond
  baseline CC assignment (legacy semantics), and extend Woodstock compatibility
  outputs toward direct model ingest conventions.
- 2026-03-08: Started treatment transition/action parity by extending the
  Patchworks treatment model/serializer to emit `<transition>` assignments;
  baseline CC tracks now include `IFM -> 'managed'` transition assignment
  (configurable via `--cc-transition-ifm`).
- 2026-03-08: Extended Woodstock compatibility export toward direct-ingest
  conventions by adding `woodstock_actions.csv` and
  `woodstock_transitions.csv` outputs (plus CLI support for `--cc-min-age` /
  `--cc-max-age`).
- 2026-03-08 next queue: add configurable per-AU transition target fields
  (beyond IFM only), and evaluate adding Woodstock `.yld` writer/import parity
  helpers for tighter legacy interoperability.
- 2026-03-08: Implemented species-wise yield curve derivation in Patchworks XML:
  for each AU/IFM species, emit `feature.Yield.*.<SPP>` (and managed product
  equivalents) as `TotalVolume(age) * SpeciesProp(age)` with piecewise-linear
  species-proportion interpolation at total-curve ages.
- 2026-03-08: Added coverage for derived species yields in
  `tests/test_fmg_patchworks.py::test_build_forestmodel_xml_tree_adds_species_yield_curves`
  and regenerated deterministic XML fixtures to lock serializer parity.
- 2026-03-08: Updated Patchworks XML serialization to drop redundant repeated
  y-values on both far-left and far-right tails for non-`unity` curves (keep
  the inner edge points of each terminal plateau), matching Patchworks behavior
  of extending terminal points horizontally.
- 2026-03-08: Hardened Patchworks XML point serialization for schema safety:
  sanitize non-finite point values (replace non-finite `y` with `0.0`, drop
  non-finite `x`), enforce monotonic/deduped `x` ordering, and fix all-flat
  curve trimming to retain earliest age point (avoids degenerate `(299,0)` tails).
- 2026-03-08: Switched Patchworks XML curve IDs from opaque numeric aliases to
  readable deterministic identifiers (`managed_total_*`, `unmanaged_prop_*`,
  `au_*_managed_yield_*`), while preserving unique idref linkage.
- 2026-03-08: Updated Patchworks XML point formatting to emit integer age `x`
  values when age is integral (default case), while preserving float formatting
  only for genuinely non-integral x values.
- 2026-03-08: Updated Patchworks XML `y` formatting by curve family:
  volume-yield curves now round to 1 decimal place; normalized/proportion
  curves round to at most 5 decimals (avoids excessive precision noise).
- 2026-03-08: Added CC harvested-volume product consequences in Patchworks XML:
  each select now includes `product.HarvestedVolume.managed.Total.CC` and
  species-wise `product.HarvestedVolume.managed.<SPP>.CC` attributes bound to
  managed total/species yield curves; validated via refreshed fixtures/tests
  and regenerated `output/patchworks_k3z_validated/forestmodel.xml`.
- 2026-03-08: Audited Patchworks managed/unmanaged semantics against
  `reference/UserGuide.pdf` and corrected FMG export assumptions:
  fragments exporter now writes one stand-fragment row per block (`1 fragment = 1 block`)
  with binary IFM assignment (`managed`/`unmanaged`) using THLB signal precedence
  (`thlb` -> `thlb_fact` -> `thlb_area` -> `thlb_raw`), matching the simplified K3Z
  teaching model requirement.
- 2026-03-08: Removed redundant Patchworks CC transition IFM assignment:
  exporter no longer writes `assign IFM='managed'` within managed-only select
  statements by default; `--cc-transition-ifm` is now optional (unset by default),
  and only non-redundant transitions (e.g., `unmanaged`) are emitted.
- 2026-03-08: Renamed upstream bundle yield terminology from
  `managed/unmanaged` to `treated/untreated` to avoid semantic collision with
  Patchworks IFM keywords. Bundle assembly now emits:
  - `curve_type` values `treated` / `untreated`
  - species-proportion curve types `treated_species_prop_*` /
    `untreated_species_prop_*`
  while preserving back-compat aliases (`managed_curve_id` /
  `unmanaged_curve_id`) and adding canonical AU columns
  (`treated_curve_id` / `untreated_curve_id`).
- 2026-03-08: Split documentation source from development reference assets:
  moved non-Sphinx PDFs out of `docs/reference/` into top-level `reference/`
  (including `reference/vdyp/`), leaving `docs/` as Sphinx source only; updated
  path references in `config/tipsy/tsa29.yaml`, `ROADMAP.md`, and
  `CHANGE_LOG.md`, and added `reference/README.md` to document directory intent.
- 2026-03-09 (seral semantics correction; feature-only accounts):
  - Confirmed Patchworks model semantics issue: `product.Seral.*` attributes are
    conceptually invalid for inventory state and should not be exported.
  - Removed `product.Seral.*` emission from
    `build_patchworks_forestmodel_definition(...)`; seral output now remains
    `feature.Seral.*` only.
  - Updated tests/docs to enforce and document feature-only seral attributes.
  - Live K3Z model repair:
    - removed `product.Seral.*` attributes from
      `C:\Users\gep\Documents\msfm\msfm2025\k3z_patchworks_model\yield\forestmodel.xml`,
    - re-ran `femic patchworks matrix-build` and verified both
      `protoaccounts.csv` and `accounts.csv` now contain `feature.Seral.*` only.
- 2026-03-09 (seral treatment-area consequence accounts + map layer):
  - Added Patchworks exporter support for treatment-consequence seral area
    accounts in CC product tracks with labels:
    `product.Seral.area.<stage>.<au_id>.CC`.
  - Updated docs/tests to reflect this semantic split:
    - inventory/state: `feature.Seral.*`
    - treatment consequences: `product.Seral.area.*.*.CC`.
  - Live K3Z model update:
    - injected `product.Seral.area.*.*.CC` attributes in
      `yield/forestmodel.xml`,
    - re-ran `femic patchworks matrix-build` and verified accounts appear in
      `protoaccounts.csv` and `accounts.csv`.
  - Added Seral Stages map layer to
    `analysis/base.pin` using sample-style `DitherTheme` configuration
    (`feature.Seral.*`, caption `Dithered Seral Stage`, layer title
    `Seral Stages`).
- 2026-03-10 (Patchworks matrix-build account sync + seral wiring):
  - Added post-build `tracks/protoaccounts.csv -> tracks/accounts.csv` sync in
    `femic patchworks matrix-build`, with timestamped backup of existing
    `accounts.csv` before overwrite and manifest/CLI reporting of sync status.
  - Added optional `--seral-stage-config` YAML support to
    `femic export patchworks` to emit per-AU seral curves and
    `feature.Seral.*` / `product.Seral.*` attributes with default or per-AU
    override boundaries.
  - Added `config/seral.k3z.yaml` starter config for K3Z seral stage setup.
- 2026-03-10 (CC treatment min age logic update):
  - Updated Patchworks exporter so CC `minage` resolves to
    `CMAI(managed_total_curve) - 20` per AU (clamped to `0..cc_max_age`).
  - `cc_min_age` remains as a fallback only when managed yield curve metadata is
    unavailable for an AU.
- 2026-03-10 (tracked K3Z prototype model moved in-repo):
  - Moved/copy-synced the active K3Z Patchworks prototype model into the repo at
    `models/k3z_patchworks_model/` so it can be versioned and shared with
    students/collaborators.
  - Updated `config/patchworks.runtime.windows.yaml` matrix builder paths to
    point at `../models/k3z_patchworks_model/...` (config-relative paths).
  - Verified `femic patchworks preflight` and `femic patchworks matrix-build`
    run successfully against the in-repo model (`run_id=repo_model_move_verify_20260310`).
- 2026-03-10 (plot docs follow-up): queued a docs enhancement to include the
  regenerated K3Z strata/AU plots in the student-facing Sample Models guide
  after the next full pipeline rerun refreshes those artifacts.
  - Added pending roadmap item `P8.6d`:
    `Roll regenerated strata/AU build plots into user-facing K3Z docs`.
- 2026-03-10 (validation gate unblock for docs checkpoint): resolved
  cross-platform/runtime regressions so full repository quality gates pass in
  this Windows environment.
  - Normalized selected emitted path strings to POSIX form where tests and
    downstream interchange contracts require stable separators
    (`legacy env boundary path`, `release manifest paths`, VDYP context/command
    payload strings, stand export file target path string).
  - Added graceful no-op behavior for VDYP diagnostic plotting when
    `matplotlib` is unavailable.
  - Hardened species slot derivation to exclude NaN-like species tokens.
  - Re-ran required gates successfully:
    `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest`,
    `pre-commit run --all-files`, `sphinx-build -b html docs _build/html -W`.
- 2026-03-10 (Phase 9 rebrand planning kickoff): added a dedicated rebrand
  phase to move repository/project naming from `wbi_ria_yield` to `femic`,
  covering metadata, URLs, runtime path cleanup, slug sweep policy, and cutover
  validation workflow.
  - Created branch `feature/rebrand-femic` and marked `P9.5a` complete.
- 2026-03-10 (Phase 9 implementation slice 1): completed the first rebrand
  implementation pass across canonical metadata and operator-facing config/docs.
  - Updated project naming/title surfaces to `femic` in:
    `README.md`, `docs/conf.py`, `docs/index.rst`, and `CITATION.cff`.
  - Added explicit transition note in `README.md`:
    formerly `wbi_ria_yield`.
  - Updated target URLs to new slug endpoints:
    `github.com/UBC-FRESH/femic` and `ubc-fresh.github.io/femic`.
  - Removed old hard-coded slug path from `config/patchworks.runtime.yaml`;
    runtime now relies on `SPSHOME` env for install-home resolution.
  - Marked complete: `P9.1`, `P9.2a`, `P9.2b`, `P9.3a`, `P9.5b`.
- 2026-03-10 (Phase 9 implementation slice 2): validated post-rename runtime
  smoke behavior and locked env-driven Patchworks install-home handling with
  regression coverage.
  - Runtime checks:
    - `python -m femic --help` succeeds (CLI smoke).
    - `sphinx-build -b html docs _build/html -W` succeeds (docs smoke).
    - `femic patchworks preflight --config config/patchworks.runtime.windows.yaml`
      succeeds on this host.
    - `femic patchworks preflight --config config/patchworks.runtime.yaml`
      now fails only on missing local artifacts (jar/fragments/xml), not
      `SPSHOME` lookup when env is provided.
  - Added regression test in `tests/test_patchworks_runtime.py`:
    `test_load_patchworks_runtime_config_uses_env_spshome_when_field_missing`.
  - Marked complete: `P9.3b`, `P9.3c`, `P9.5c`.
  - GitHub Actions observation: latest `docs-pages` deployment currently
    advertises `https://ubc-fresh.github.io/wbi_ria_yield/`; need a post-merge
    main-branch deploy to confirm transition to `.../femic/`.
  - `P9.2c` remains pending until a post-merge docs-pages deployment confirms
    the new published URL target after rename.
- 2026-03-10 (Patchworks install-registration heuristic): updated preflight to
  explicitly warn when `SPSHOME` is missing from the process environment,
  reflecting the operational assumption that a correct Patchworks install should
  set `SPSHOME`.
  - Added warning text in `run_patchworks_preflight(...)`:
    missing `SPSHOME` indicates install/registration may be incomplete.
  - Added regression test:
    `tests/test_patchworks_runtime.py::test_run_patchworks_preflight_warns_when_env_spshome_missing`.
- 2026-03-10 (Pages post-rename verification + Node 24 readiness): confirmed
  docs are live under the renamed repo/docs URL and updated workflow defaults
  to avoid pending Node 20 action deprecation risk.
  - Confirmed GitHub Pages publish target is now `https://ubc-fresh.github.io/femic/`.
  - Updated `.github/workflows/docs-pages.yml` to set:
    `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24=true`.
  - Upgraded `actions/upload-pages-artifact` from `@v3` to `@v4`.
  - Marked `P9.2c` complete.
- 2026-03-10 (Phase 9 closure pass): completed legacy-slug sweep enforcement
  and notebook-output cleanup policy so rebrand phase can be closed.
  - Added `Notebook Output Cleanup Policy` section to
    `docs/guides/legacy-traceability.rst` with explicit output-clearing guidance
    and `nbconvert --clear-output` command.
  - Added docs contract checks in `tests/test_docs_contract.py` for:
    - required notebook cleanup policy section presence,
    - legacy slug reference restrictions (allowed in audit-trail files only).
  - Removed remaining transition slug mention from `README.md` to keep active
    user-facing docs/config free of historical slug references.
  - Marked complete: `P9.2`, `P9.4a`, `P9.4b`, `P9.4c`, and parent `P9.4`.
- 2026-03-10 (Phase 10 implementation slice 1: instance decoupling + bootstrap):
  implemented instance-rooted CLI path resolution and deployment workspace
  scaffolding as the first concrete Phase 10 delivery.
  - Added `src/femic/instance_context.py` with resolver precedence:
    `--instance-root` -> `FEMIC_INSTANCE_ROOT` -> CWD, plus legacy repo-root
    compatibility fallback warning.
  - Added shared `--instance-root` support across operational commands
    (`run`, `prep validate-case`, `tipsy validate`, `tsa post-tipsy`,
    export commands, and patchworks runtime commands), and rewired relative
    paths to resolve under instance root.
  - Added `femic instance init` (`instance` CLI namespace) with filesystem-first
    scaffold generation (`config/`, `config/tipsy/`, `data/`, `output/`,
    `vdyp_io/logs/`, `.gitignore`, `QUICKSTART.md`).
  - Added optional BC-wide VRI dataset bootstrap with built-in URLs and default
    yes/no prompt:
    `VEG_COMP_LYR_R1_POLY_2024.gdb.zip` and
    `VEG_COMP_VDYP7_INPUT_POLY_AND_LAYER_2024.gdb.zip`.
  - Added package-owned resources under `src/femic/resources/` for instance
    templates and legacy scripts (`00_data-prep.py`, `01a_run-tsa.py`,
    `01b_run-tsa.py`), and updated workflow runtime to execute packaged scripts
    by default (no hard dependency on repo-root script paths).
  - Added/updated tests for instance-context resolution, instance bootstrap,
    packaged legacy resource loading, and CLI wiring.
  - Marked complete: `P10.1a/P10.1b/P10.1c`, `P10.2a/P10.2b/P10.2c`,
    `P10.3a/P10.3b/P10.3c`.
- 2026-03-10 (Phase 10 scope extension: public-but-inaccessible dataset mirror):
  added a new Phase 10 workstream to publish missing FEMIC-required public
  datasets (including archived HectaresBC `misc*.tif` layers) through a
  DataLad-powered GitHub dataset repository with Arbutus special-remote object
  storage, then link that dataset back into FEMIC as a git submodule.
  - Added checklist `P10.6a/P10.6b/P10.6c/P10.6d` for inventory, publishing,
    submodule integration, and collaborator runbook coverage.
- 2026-03-10 (Phase 10 `P10.6a` complete: dataset inventory + provenance baseline):
  published the required dataset inventory for DataLad mirror planning, with
  explicit access mode and checksum status fields.
  - Added machine-readable registry:
    `metadata/required_datasets.yaml`
    covering VRI/VDYP provincial layers, TSA boundaries, Site_Prod_BC,
    HectaresBC `misc.thlb.tif`, support assets, and case-specific boundary
    geometry.
  - Added user-facing guide:
    `docs/guides/data-access-inventory.rst`
    and wired it into docs navigation.
  - Updated deployment-instance guide to reference the authoritative registry.
  - Marked `P10.6a` complete; next queued step is `P10.6b` (publish DataLad
    dataset repository and configure Arbutus special remote).
- 2026-03-10 (Phase 10 `P10.6d` complete: DataLad operator runbook + mirror seed):
  added maintainer/operator docs and seed artifacts so the mirror workflow can
  be executed deterministically once the dataset repo is created.
  - Added guide `docs/guides/public-data-mirror-runbook.rst` with
    create/publish steps plus collaborator clone/get/update commands.
  - Added `metadata/datalad_mirror_seed.csv` as the current
    `datalad_mirror.include=true` extraction from dataset registry.
  - Added maintainer bootstrap note:
    `planning/femic_public_data_datalad_bootstrap.md`.
  - Marked `P10.6d` complete; next queued implementation is
    `P10.6b` followed by `P10.6c`.
- 2026-03-11 (Phase 10 `P10.6c` complete + local `P10.6b` bootstrap):
  created a local DataLad dataset mirror repo and linked it back into FEMIC as
  a Git submodule at `external/femic-public-data`.
  - Created local dataset repo at `/home/gep/projects/femic-public-data` and
    mirrored current seed artifacts from this workspace:
    - `data/misc.thlb.tif`
    - `data/bc/tsa/FADM_TSA.gdb`
    - `data/bc/siteprod/Site_Prod_BC.gdb`
    - `data/bc/vri/2019/VEG_COMP_LYR_R1_POLY.gdb`
    - `data/bc/vri/2019/VEG_COMP_VDYP7_INPUT_POLY_AND_LAYER_2019.gdb`
  - Added submodule linkage in FEMIC:
    `external/femic-public-data`.
  - Marked `P10.6c` complete.
  - `P10.6b` remains open pending GitHub publish + Arbutus special-remote
    configuration + checksum backfill in `metadata/required_datasets.yaml`.
- 2026-03-11 (Phase 10 `P10.6b` execution hardening with lab KB template):
  aligned FEMIC DataLad mirror runbook/bootstrap docs to the known-good
  Arbutus S3 command sequence from the FRESH lab workflow workshop materials.
  - Updated `docs/guides/public-data-mirror-runbook.rst` to use explicit
    `git annex initremote arbutus-s3` setup, followed by
    `datalad create-sibling-github --publish-depends arbutus-s3`.
  - Added credential/export and recovery notes (`git annex enableremote`) to
    reduce clone/get failures caused by ordering/config mismatches.
  - Updated `planning/femic_public_data_datalad_bootstrap.md` with source links
    to the imported KB/workshop references in `tmp/`.
- 2026-03-11 (Phase 10 `P10.6b` creds bootstrap template standardization):
  added a repo-local Arbutus credentials template and ignore policy so
  maintainers can source AWS/S3 env vars consistently without risking secret
  commits.
  - Added template:
    `config/credentials/arbutus_env.template.sh`.
  - Updated `.gitignore` to ignore concrete credential scripts under
    `config/credentials/*.sh` while keeping `*.template.sh` tracked.
  - Updated `docs/guides/public-data-mirror-runbook.rst` and
    `planning/femic_public_data_datalad_bootstrap.md` to use the new template
    path in the `P10.6b` setup sequence.
- 2026-03-11 (Phase 10 `P10.6b` complete: published mirror repo + Arbutus upload):
  completed the publish phase for the FEMIC public-data mirror dataset.
  - Verified published dataset repository:
    `https://github.com/UBC-FRESH/femic-public-data`.
  - Verified `git-annex` object availability on `arbutus-s3` for mirrored
    seed artifacts, including:
    - `data/misc.thlb.tif`
    - `data/bc/vri/2019/VEG_COMP_LYR_R1_POLY.gdb/a00000009.gdbtable`
  - Backfilled checksum values in `metadata/required_datasets.yaml` for all
    current `datalad_mirror.include=true` artifacts and documented the
    deterministic directory-hash method for `*.gdb` datasets.
  - Marked `P10.6b` complete; with `P10.6a/P10.6c/P10.6d` already complete,
    parent `P10.6` is now complete.
- 2026-03-11 (Phase 10 `P10.4a` complete: canonical in-repo reference instance):
  established a maintainer reference deployment instance under
  `instances/reference/`, separate from package source templates.
  - Generated `instances/reference/` via `femic instance init` with
    `--no-download-bc-vri` for deterministic in-repo scaffolding.
  - Added docs section in `docs/guides/deployment-instances.rst` defining
    `instances/reference/` as the canonical maintainer reference location.
  - Added docs contract coverage in `tests/test_docs_contract.py` to require
    the reference instance path and key scaffold files.
  - Marked `P10.4a` complete; next execution step remains `P10.4b`.
- 2026-03-11 (Phase 10 `P10.4b` complete: docs/tests/examples repointed):
  repointed maintainer-facing workflow docs and template-instantiation tests to
  use the canonical in-repo reference instance layout.
  - Updated guides:
    `docs/guides/case-onboarding.rst`,
    `docs/guides/pipeline-overview.rst`,
    `docs/reference/run-config.rst`.
  - Updated README onboarding/run-config examples to reference
    `instances/reference/config/...` paths.
  - Updated tests to consume reference-instance templates:
    `tests/test_case_preflight_cli.py`,
    `tests/test_docs_contract.py`.
  - Marked `P10.4b` complete; next execution step is `P10.4c`.
- 2026-03-11 (Phase 10 `P10.4c` complete: repo-path coupling contract checks):
  enforced docs/config contract coverage against repo-root-coupled deployment
  wording and removed remaining active references.
  - Updated `README.md` external-data note to describe instance-root-relative
    behavior rather than repo-root assumptions.
  - Updated `docs/sample-models/k3z.rst` wording from "repository root" to
    workspace-root phrasing.
  - Added `tests/test_docs_contract.py` check to fail on forbidden active
    deployment wording (`repository root`, `repo root`, and host-specific
    `/home/gep/projects/` paths) across key docs/config files.
  - Marked `P10.4c` complete; with `P10.4a/P10.4b` already complete, parent
    `P10.4` is now complete.
- 2026-03-11 (Phase 10 `P10.5a` complete: package build/release checks):
  added automated and documented package-distribution checks and fixed runtime
  package metadata so wheel smoke installs are executable.
  - Added GitHub Actions workflow:
    `.github/workflows/package-release-checks.yml` running:
    `python -m build`, `twine check dist/*`, and wheel-install smoke
    (`femic --help`, `femic instance init ...`).
  - Added README maintainer section documenting equivalent local commands.
  - Expanded `pyproject.toml` runtime `dependencies` to include required
    import-time packages (for example `numpy`, `pandas`, `geopandas`, `scipy`,
    `rasterio`) discovered by wheel-smoke failure diagnostics.
  - Added docs contract test coverage requiring workflow presence and required
    packaging-check commands (`tests/test_docs_contract.py`).
  - Marked `P10.5a` complete; next execution step remains `P10.5b`.
- 2026-03-11 (Phase 10 `P10.5b` complete: clean-env installed-package preflight):
  extended publish-readiness verification to cover an installed-wheel case
  preflight run in a clean virtual environment.
  - Updated `.github/workflows/package-release-checks.yml` to run:
    installed `femic prep validate-case` after `femic instance init`.
  - Added CI fixture setup in workflow for minimal preflight prerequisites:
    required instance-local data/runtime placeholders, mock `wine` on `PATH`,
    and a minimal external-data tree via `FEMIC_EXTERNAL_DATA_ROOT`.
  - Extended `tests/test_docs_contract.py` package-workflow contract assertions
    to require installed-package preflight coverage.
  - Marked `P10.5b` complete; next execution step remains `P10.5c`.
- 2026-03-11 (Phase 10 `P10.5c` complete: install->instance->run docs finalization):
  finalized user-facing docs for installed-package execution flow.
  - Updated `README.md` quickstart to lead with:
    `python -m pip install femic` -> `femic instance init` -> `femic run ...`
    and switched primary command examples to installed CLI form.
  - Updated deployment/onboarding pipeline guides to use installed CLI commands
    as primary examples:
    `docs/guides/deployment-instances.rst`,
    `docs/guides/case-onboarding.rst`,
    `docs/guides/pipeline-overview.rst`.
  - Added docs contract checks in `tests/test_docs_contract.py` to require
    explicit installed-package workflow text.
  - Marked `P10.5c` complete; with `P10.5a/P10.5b` already complete, parent
    `P10.5` is now complete.
- 2026-03-11 (Phase 11 complete: K3Z standalone example instance + submodule):
  implemented and published the canonical full K3Z instance repository and
  linked it back into FEMIC for onboarding and reproducible case setup.
  - Defined contract note:
    `planning/femic_k3z_instance_repo_contract.md`.
  - Published public repo:
    `https://github.com/UBC-FRESH/femic-k3z-instance` with initial baseline
    tag `v0.1.0`.
  - Added submodule linkage:
    `external/femic-k3z-instance`.
  - Updated docs to reference the standalone K3Z repo + submodule workflow and
    added operator commands:
    `git submodule update --init --recursive`,
    `git submodule update --remote external/femic-k3z-instance`.
  - Added docs-contract assertions requiring K3Z repo and submodule references.
  - Marked `P11.1/P11.2/P11.3/P11.4/P11.5` complete.
- 2026-03-11 (Phase 12 planning kickoff): added a concrete execution phase for
  relocated K3Z rebuild validation and standalone K3Z documentation buildout,
  including explicit FHOPS-template alignment requirements for cross-project
  FRESH lab Sphinx consistency.
  - Added `P12.1/P12.2` for relocated Patchworks matrix-build execution,
    bugfix verification, and regression evidence capture.
  - Added `P12.3/P12.4` for standalone `femic-k3z-instance` Sphinx docs
    scaffolding and TSR-style user-guide expansion.
  - Added `P12.5` to formalize a shared FRESH lab Sphinx template baseline
    using FHOPS as canonical reference.
  - Added `P12.6` for documentation ownership, cadence, and release policy.
- 2026-03-11 (Phase 12 `P12.1a/P12.1b` execution on relocated K3Z instance):
  ran Windows native Patchworks preflight + blocks build + matrix build in
  `external/femic-k3z-instance`.
  - Added instance-local runtime config:
    `external/femic-k3z-instance/config/patchworks.runtime.windows.yaml`.
  - Executed successful runs with artifacts/logs under:
    `external/femic-k3z-instance/vdyp_io/logs/`
    (run ids: `k3z_relocated_20260311`, `k3z_relocated_20260311b`).
  - `accounts.csv` sync/backup behavior confirmed via manifest.
  - Noted structural drift from tracked baseline remains and requires follow-up
    under `P12.2` (for example lower account/treatment counts after rebuild).
- 2026-03-11 (Phase 12 scope extension: cross-platform geospatial bootstrap):
  added explicit `fiona`/`GDAL` hardening tasks for Linux/Windows local `.venv`
  bootstrap reliability.
  - Added `P12.7a` for OS-specific validated install rituals.
  - Added `P12.7b` for runtime/bootstrap environment detection.
  - Added `P12.7c` for geospatial dependency preflight checks.
  - Added `P12.7d` for Windows remediation runbook coverage.
- 2026-03-11 (Phase 13 planning kickoff): added a new cross-instance
  reproducibility phase that makes rebuild scripts/specs + invariant checks the
  default requirement for all new FEMIC deployment-instance projects.
  - Added `P13.1` contract definition tasks for required inputs, sequence, invariants, and failure taxonomy.
  - Added `P13.2` orchestration tasks for first-class CLI rebuild execution + manifest/report outputs.
  - Added `P13.3` per-instance rebuild spec/template tasks, including K3Z backfill as reference.
  - Added `P13.4` regression guardrail tasks (invariants, baseline diffs, allowlisted deltas, fail-fast behavior).
  - Added `P13.5` user-facing documentation/runbook tasks for authoring and interpreting rebuild reports.
  - Added `P13.6` enforcement tasks to make this mandatory in `instance init`, docs contracts, and release gates.
- 2026-03-11 (K3Z runtime validation feedback: species account completeness):
  user confirmed rebuilt K3Z launches in Patchworks without startup errors and
  now shows nonzero volume in species-wise accounts except `PL`.
  - Added follow-up task `P12.2d` to verify `PL` vs `PLC` semantics in this
    case and, if `PL` is not valid for current K3Z inputs, remove/trim `PL`
    from generated accounts/targets/docs to avoid student confusion.
- 2026-03-11 (Phase 12 `P12.1c` + `P12.2a/b/c` execution: reproducible K3Z rebuild checks):
  implemented and exercised a deterministic rebuild-and-validate script for the
  relocated K3Z instance.
  - Fixed and expanded `scripts/k3z/rebuild_k3z_instance.py` to:
    - execute full rebuild flow,
    - emit machine-readable report JSON,
    - record key artifact timestamps,
    - enforce species/seral/block-join invariants,
    - compare structural `tracks/*.csv` invariants against a baseline snapshot.
  - Added baseline snapshot: `scripts/k3z/k3z_tracks_baseline.json`.
  - Executed evidence runs:
    - `k3z_reprocheck_20260311_2` (baseline initialized with `--write-baseline`),
    - `k3z_reprocheck_20260311_3` (baseline regression check pass),
    - `k3z_reprocheck_20260311_4` (clean repeat pass after UTC warning fix).
  - Latest report confirms:
    `managed_area_ha=1781.3132360577583`, `passive_area_ha=0.0`,
    `block_join_csv_only=0`, `block_join_shp_only=0`,
    `seral_account_count=75`, `baseline_match=true`.
  - Marked complete: `P12.1c`, `P12.2a`, `P12.2b`, `P12.2c`.
  - Left open: `P12.2d` (`PL` vs `PLC` semantics cleanup for student-facing clarity).
- 2026-03-11 (Phase 12 terminology normalization complete): replaced
  legacy curve-source terminology across active FEMIC code/docs with
  `untreated/treated`, while preserving IFM terminology as
  `managed/unmanaged`.
  - Updated bundle/adapters/export logic and tests to use
    `untreated_curve_id`/`treated_curve_id` and
    `untreated_species_prop_*`/`treated_species_prop_*` naming.
  - Updated user-facing docs/metadata wording to remove legacy curve-source
    references and align with `untreated/treated`.
  - Completed `P12.8a/P12.8b/P12.8c`.
- 2026-03-11 (Phase 12 `P12.2d` completion): validated `PL` vs `PLC` behavior
  in K3Z and implemented zero-signal species trimming so `PL` no longer appears
  as an empty managed species account when no treated species-proportion signal
  exists for `PL`.
- 2026-03-11 (Phase 12 `P12.3a` complete: standalone K3Z Sphinx scaffold):
  created and published the baseline standalone docs scaffold in
  `external/femic-k3z-instance`.
  - Submodule commit pushed: `6c61c71` (`femic-k3z-instance/main`).
  - Added docs files: `docs/conf.py`, `docs/index.rst`,
    `docs/getting-started.rst`, `docs/model-anatomy.rst`,
    `docs/rebuild-and-qa.rst`, `docs/troubleshooting.rst`, and
    `docs/requirements.txt`.
  - Added publishing/build config: `.readthedocs.yaml` and
    `.github/workflows/docs-pages.yml`.
  - Added parent docs-contract check in `tests/test_docs_contract.py` requiring
    standalone K3Z docs scaffold presence and key toctree entries.
  - Verified standalone docs build:
    `python -m sphinx -b html docs docs/_build/html -W` in submodule root.
- 2026-03-11 (Phase 12 `P12.3b` complete + FEMIC RTD-theme alignment):
  published and validated standalone K3Z docs, then aligned FEMIC docs publish
  deps to the same Read the Docs theme baseline.
  - Verified `femic-k3z-instance` docs deployment run success and URL:
    `https://ubc-fresh.github.io/femic-k3z-instance/`.
  - Added FEMIC docs dependency file: `docs/requirements.txt`
    (`sphinx`, `sphinx-rtd-theme`).
  - Updated FEMIC docs workflow to install docs deps from
    `docs/requirements.txt` so GitHub Pages builds use RTD theme consistently.
- 2026-03-11 (Phase 12 `P12.3c` complete): added standalone K3Z docs acceptance
  checks for required navigation and section coverage.
  - Expanded docs contract tests in `tests/test_docs_contract.py` to require:
    - guide toctree structure in `external/femic-k3z-instance/docs/index.rst`,
    - required headings and command snippets in `getting-started.rst`,
    - required anatomy/edit-policy sections in `model-anatomy.rst`,
    - required reproducibility sections and script references in
      `rebuild-and-qa.rst`,
    - required troubleshooting topics in `troubleshooting.rst`.
- 2026-03-11 (Phase 12 roadmap amendment: TSR-grade K3Z data-package depth):
  refined Phase 12 docs scope to explicitly target BC small-unit data-package
  structure/depth expectations using three exemplar references.
  - Added `P12.4d/P12.4e/P12.4f/P12.4g/P12.4h` to enforce:
    exemplar section crosswalk, standalone K3Z data-package page set,
    evidence/provenance tables, student usability acceptance content, and
    publication acceptance criteria.
  - Added `P12.5e` to ensure FHOPS template alignment does not dilute
    BC data-package depth expectations.
  - Exemplar references for structure baseline:
    `reference/TFL26_Information_Package_Sept-2018_v1.1.pdf`,
    `reference/CFA_Analysis_Report.pdf`,
    `reference/FNWL_Analysis_Report.pdf`.
  - Next execution sequence locked:
    `P12.4d -> P12.4e -> P12.4f -> P12.4g -> P12.4h`.
- 2026-03-11 (Phase 12 `P12.4d/P12.4e/P12.4f/P12.4g` execution):
  added TSR-grade K3Z standalone data-package docs and acceptance checks using
  the TFL26/CFA/FNWL exemplar structure as the baseline.
  - Added standalone docs pages:
    `data-package-crosswalk.rst`, `land-base-and-netdown.rst`,
    `assumptions-registry.rst`, `base-case-analysis.rst`.
  - Wired new pages into standalone docs navigation in
    `external/femic-k3z-instance/docs/index.rst`.
  - Added docs-contract coverage in `tests/test_docs_contract.py` requiring:
    crosswalk sections, exemplar references, TSR-style required headings, and
    provenance-table columns plus operator usability sections.
  - Marked complete: `P12.4d`, `P12.4e`, `P12.4f`, `P12.4g`.
  - Remaining for `P12.4`: `P12.4h` (publish acceptance verification).
- 2026-03-11 (Phase 12 `P12.4h` completion): publication acceptance criteria
  verified for standalone K3Z TSR-style docs update.
  - Verified standalone docs warnings-as-errors build succeeds:
    `python -m sphinx -b html docs docs/_build/html -W` (submodule).
  - Verified parent docs-contract coverage includes required TSR headings and
    provenance/usability sections (`tests/test_docs_contract.py`).
  - Verified GitHub Pages deployment/run and live navigation for new pages:
    run `22981643203` (`success`) and URL
    `https://ubc-fresh.github.io/femic-k3z-instance/`.
- 2026-03-11 (Phase 12 `P12.4a/P12.4b/P12.4c` execution): expanded standalone
  K3Z docs to complete the core TSR-style data-package scope.
  - Added metadata/lineage page:
    `external/femic-k3z-instance/docs/metadata-and-lineage.rst`
    (artifact inventory, lineage chain, validation evidence, provenance policy).
  - Added operator runbook page:
    `external/femic-k3z-instance/docs/operator-runbook.rst`
    (fresh setup, rebuild, diagnostics, troubleshooting, release/publication
    checklists).
  - Added edit-policy/scenario guidance page:
    `external/femic-k3z-instance/docs/edit-policy-and-scenarios.rst`
    (editable/regenerate matrix and classroom scenario interpretation workflow).
  - Wired pages into standalone docs navigation in
    `external/femic-k3z-instance/docs/index.rst`.
  - Extended parent docs-contract checks to enforce required headings for the
    three new pages (`tests/test_docs_contract.py`).
  - Marked complete: `P12.4a`, `P12.4b`, `P12.4c`.
- 2026-03-11 (standalone-docs decoupling hardening): removed parent-repo path
  assumptions from standalone `femic-k3z-instance` docs so the instance docs
  remain valid when consumed outside a FEMIC submodule checkout.
  - Replaced parent-specific script/path references (for example
    `scripts/k3z/rebuild_k3z_instance.py` and `reference/...`) with
    instance-local FEMIC command workflows and generic exemplar citations.
  - Added docs-contract guard:
    `test_k3z_standalone_docs_do_not_reference_parent_repo_paths`.
- 2026-03-11 (Phase 12 `P12.5a/P12.5b/P12.5c/P12.5d/P12.5e` completion):
  standardized FEMIC + standalone K3Z docs stacks against an FHOPS-aligned
  Sphinx template baseline with automated drift checks.
  - Added baseline guide:
    `docs/guides/sphinx-template-baseline.rst` and wired it into Guides index.
  - Aligned both docs configs with shared template controls:
    `autodoc_typehints="description"`, RTD theme options
    (`collapse_navigation=False`, `navigation_depth=3`), and template path.
  - Aligned standalone docs workflow to match current Pages baseline
    (Node24 env flag, `configure-pages`, artifact/deploy action versions,
    pull-request/main gating parity).
  - Added docs-contract enforcement:
    `test_fhops_aligned_sphinx_template_contract`.
  - Confirmed K3Z TSR data-package depth pages remain required via existing
    docs contracts.
- 2026-03-11 (Phase 12 `P12.6a/P12.6b/P12.6c` completion): formalized docs
  ownership and release operations for standalone K3Z documentation.
  - Added standalone governance page:
    `external/femic-k3z-instance/docs/docs-ownership-and-release.rst`.
  - Wired new page into standalone docs navigation:
    `external/femic-k3z-instance/docs/index.rst`.
  - Captured ownership matrix, refresh cadence, release tagging policy, and
    contributor onboarding/review workflow requirements.
  - Extended docs-contract checks (`tests/test_docs_contract.py`) to require
    the new page and its core governance sections.
- 2026-03-11 (Phase 12 `P12.7a/P12.7b/P12.7c/P12.7d` completion): implemented
  cross-platform geospatial dependency bootstrap hardening with runtime checks.
  - Added OS-aware geospatial preflight module:
    `src/femic/geospatial_preflight.py` (platform detection, install hints,
    Fiona import check, GDAL visibility check, shapefile I/O smoke test).
  - Added CLI command:
    `femic prep geospatial-preflight` (supports `--strict-warnings` and
    `--skip-shapefile-smoke`).
  - Updated `femic instance init` to surface geospatial readiness guidance and
    OS-specific install hints when dependencies are not yet ready.
  - Added user guide:
    `docs/guides/geospatial-runtime-bootstrap.rst` and wired it into guides
    navigation.
  - Updated deployment + CLI reference docs and docs-contract/test coverage for
    the new command and guide requirements.
- 2026-03-11 (Phase 13 `P13.1a/P13.1b/P13.1c/P13.1d` completion): defined the
  canonical FEMIC instance rebuild contract in human-readable and
  machine-readable forms.
  - Added contract specification document:
    `planning/femic_instance_rebuild_contract.md`.
  - Added canonical YAML contract artifact:
    `planning/femic_instance_rebuild_contract.v1.yaml`.
  - Captured required inputs/config/runtime prerequisites, authoritative rebuild
    sequence, required post-rebuild invariants, and failure-class remediation
    message requirements.
  - Added docs-contract enforcement in `tests/test_docs_contract.py` for
    contract artifact presence and required schema keys/sections.
  - Linked pipeline guide primary sources to the new rebuild contract doc:
    `docs/guides/pipeline-overview.rst`.
- 2026-03-11 (Phase 13 `P13.2a` completion): added a reusable deterministic
  rebuild-runner abstraction with JSON report sink support.
  - Added module:
    `src/femic/rebuild_runner.py` with:
    `RebuildStep`, `RebuildRunner`, `StepOutcome`,
    `RebuildExecutionReport`, and `JsonRebuildReportSink`.
  - Runner now supports dependency graph ordering (deterministic topological
    sort), stop-or-continue failure behavior, and machine-readable report
    emission through sink abstraction.
  - Added unit tests:
    `tests/test_rebuild_runner.py` covering deterministic order, failure
    handling modes, JSON sink output, unknown dependency errors, and cycle
    detection.
- 2026-03-11 (Phase 13 `P13.2b` completion): added CLI support for
  non-interactive, instance-rooted rebuild execution with explicit run IDs.
  - Added `femic instance rebuild` command in `src/femic/cli/main.py`.
  - Command now executes deterministic rebuild steps through
    `RebuildRunner` with step dependencies:
    case preflight, geospatial preflight, upstream compile, post-TIPSY bundle,
    and optional Patchworks preflight + matrix build.
  - Added machine-readable report path emission:
    `vdyp_io/logs/instance_rebuild_report-<run_id>.json`.
  - Added CLI regression tests in `tests/test_cli_main.py` for base/with-Patchworks
    step graph construction and run-id/context wiring.
  - Updated CLI docs and contracts:
    `docs/reference/cli.rst`, `docs/guides/pipeline-overview.rst`,
    `tests/test_docs_contract.py`.
- 2026-03-11 (Phase 13 `P13.2c` completion): extended instance rebuild output
  reporting to include explicit manifest/log artifact references.
  - Added artifact-reference collector:
    `_collect_rebuild_artifact_references(...)` in `src/femic/cli/main.py`.
  - `femic instance rebuild` now enriches
    `instance_rebuild_report-<run_id>.json` with `artifact_references` that
    capture discovered run-manifest, Patchworks manifest/log, and report files.
  - Added CLI regression coverage:
    `tests/test_cli_main.py::test_collect_rebuild_artifact_references_filters_missing`.
  - Updated CLI reference docs to document report artifact-reference behavior:
    `docs/reference/cli.rst`.
- 2026-03-11 (Phase 13 `P13.2d` completion): added rebuild dry-run mode so
  operators can inspect full planned execution sequence without mutation.
  - Added `--dry-run` option to `femic instance rebuild` in
    `src/femic/cli/main.py`.
  - Dry-run now prints ordered step plan (with dependencies), run-id, and
    report path, then exits before constructing/running `RebuildRunner`.
  - Added CLI regression test:
    `tests/test_cli_main.py::test_instance_rebuild_dry_run_prints_plan_without_execution`.
  - Updated CLI docs/contracts:
    `docs/reference/cli.rst` and `tests/test_docs_contract.py`.
- 2026-03-11 (Phase 13 `P13.3a` completion): defined the standard YAML rebuild
  spec schema for instance command steps and invariants.
  - Added schema artifact:
    `planning/femic_instance_rebuild_spec_schema.v1.yaml`.
  - Schema now standardizes root keys (`instance`, `runtime`, `steps`,
    `invariants`) plus step and invariant field structure/constraints.
  - Linked schema from canonical rebuild contract:
    `planning/femic_instance_rebuild_contract.md`.
  - Added docs-contract enforcement:
    `tests/test_docs_contract.py::test_instance_rebuild_spec_schema_artifact_is_present_and_structured`.
- 2026-03-11 (Phase 13 `P13.3b` completion): shipped default rebuild-spec
  template in instance bootstrap scaffolding.
  - Added template artifact:
    `src/femic/resources/instance/config/rebuild.spec.yaml`.
  - Updated instance bootstrap template file list so
    `femic instance init` now always writes `config/rebuild.spec.yaml`.
  - Updated instance quickstart template and deployment docs to include
    rebuild-spec customization guidance.
  - Added/updated test coverage:
    `tests/test_instance_bootstrap.py` and `tests/test_docs_contract.py`.
- 2026-03-11 (Phase 13 `P13.3c` completion): backfilled K3Z as the reference
  rebuild-spec implementation using its known-valid sequence.
  - Added K3Z instance spec:
    `external/femic-k3z-instance/config/rebuild.spec.yaml`.
  - Updated K3Z standalone docs/rebuild runbook and README to treat
    `config/rebuild.spec.yaml` as the authoritative sequence source.
  - Extended parent docs-contract checks to require the K3Z rebuild spec and
    validate core schema-aligned fields and required step IDs.
- 2026-03-11 (Phase 13 `P13.3d` completion): added rebuild-spec schema
  validation with explicit diagnostics for malformed specs.
  - Added module:
    `src/femic/rebuild_spec.py` with load + validation helpers and
    human-readable issue reporting.
  - `femic instance rebuild` now validates `--spec` before planning/execution
    and exits with detailed field-level diagnostics on malformed specs.
  - Added command:
    `femic instance validate-spec --spec <path>` for direct schema checks.
  - Added tests:
    `tests/test_rebuild_spec.py`, plus CLI/contract coverage updates in
    `tests/test_cli_main.py` and `tests/test_docs_contract.py`.
  - Updated CLI reference docs for `--spec` and `instance validate-spec`.
- 2026-03-11 (Phase 13 `P13.4a` completion): added operational invariant
  extraction and evaluation for known regression risk dimensions.
  - Added module:
    `src/femic/rebuild_invariants.py` with metric collectors for managed area,
    managed species yield-account presence, seral-account presence,
    topology edge count, and matrix-builder block join mismatch detection.
  - `femic instance rebuild` now evaluates spec invariants against measured
    metrics, prints pass/warn/fail summaries with remediation text, and fails
    the command when any `severity: fatal` invariant regresses.
  - Rebuild reports now persist `metrics` and `invariant_results` sections
    alongside existing step outcomes and artifact references.
  - Added regression tests:
    `tests/test_rebuild_invariants.py`, and updated CLI/docs coverage in
    `docs/reference/cli.rst`.
- 2026-03-11 (Phase 13 `P13.4b` completion): added configurable baseline
  snapshot + structural diff support for rebuild outputs.
  - Added module:
    `src/femic/rebuild_baseline.py` to build/load/save baseline snapshots and
    diff key track-table + ForestModel XML structures.
  - `femic instance rebuild` now supports:
    `--baseline <path>` and `--write-baseline`, computes `baseline_match` /
    `baseline_diff_count` metrics, and records baseline diff payloads in the
    rebuild report under `baseline`.
  - Added tests:
    `tests/test_rebuild_baseline.py`, plus CLI/docs contract updates in
    `tests/test_cli_main.py` and `tests/test_docs_contract.py`.
- 2026-03-11 (Phase 13 `P13.4c` completion): added explicit baseline-diff
  allowlist mechanism so intentional output deltas are tracked in git.
  - Added allowlist support in baseline utilities:
    `load_diff_allowlist(...)` and `apply_diff_allowlist(...)` in
    `src/femic/rebuild_baseline.py`.
  - `femic instance rebuild` now supports:
    `--allowlist <path>` (default `config/rebuild.allowlist.yaml`) and records
    `baseline_allowlist_match` + `baseline_unexpected_diff_count` metrics.
  - Rebuild report `baseline` section now captures allowlist path/payload and
    filtered unexpected diff results.
  - Added allowlist template files:
    `src/femic/resources/instance/config/rebuild.allowlist.yaml` and
    `instances/reference/config/rebuild.allowlist.yaml`.
  - Updated instance scaffolding (`femic instance init`) and quickstart docs
    so every new instance starts with a tracked allowlist file.
- 2026-03-11 (Phase 13 `P13.4d` completion): rebuild now fails fast with
  explicit actionable regression summaries for unexpected baseline drift.
  - `femic instance rebuild` now enforces runtime threshold
    `runtime.baseline_unexpected_diff_threshold` (default `0`) and exits
    non-zero when `baseline_unexpected_diff_count` exceeds threshold.
  - Added operator-facing remediation output for unexpected diffs:
    review report baseline allowlist results, update tracked allowlist, or
    regenerate baseline with `--write-baseline`.
  - Rebuild report now includes `regression_gate` with step/invariant/baseline
    gate status fields.
  - Updated baseline schema/template docs:
    `planning/femic_instance_rebuild_spec_schema.v1.yaml`,
    `src/femic/resources/instance/config/rebuild.spec.yaml`,
    `instances/reference/config/rebuild.spec.yaml`.
  - Added regression coverage:
    `tests/test_cli_main.py::test_instance_rebuild_fails_when_unexpected_diffs_exceed_threshold`.
- 2026-03-11 (Phase 13 `P13.5a` completion): added user-facing rebuild
  reproducibility contract guide.
  - Added docs page:
    `docs/guides/rebuild-repro-contract.rst` covering purpose, contract
    sources, operator workflow, required evidence artifacts, and failure
    classes.
  - Added guide navigation entry in `docs/guides/index.rst`.
  - Added docs-contract coverage:
    `tests/test_docs_contract.py::test_rebuild_repro_contract_guide_covers_core_sections`.
- 2026-03-11 (Phase 13 `P13.5b` completion): added authoring guide for new
  instance rebuild specs with copy-ready templates and execution workflow.
  - Added docs page:
    `docs/guides/author-instance-rebuild-spec.rst`.
  - Covered required spec sections, step/invariant authoring rules, minimal
    YAML example, K3Z reference spec usage, and dry-run/full rebuild commands.
  - Added guide navigation entries/links in:
    `docs/guides/index.rst` and `docs/guides/rebuild-repro-contract.rst`.
  - Added docs-contract coverage:
    `tests/test_docs_contract.py::test_author_instance_rebuild_spec_guide_covers_core_sections`.
- 2026-03-11 (Phase 13 `P13.5c` completion): added operator guide for rebuild
  report interpretation and regression triage workflow.
  - Added docs page:
    `docs/guides/interpret-rebuild-reports.rst`.
  - Documented how to interpret `outcomes`, `invariant_results`, `baseline`,
    and `regression_gate` sections in instance rebuild reports.
  - Added explicit triage sequence for resolving step failures, fatal
    invariant regressions, and unexpected baseline drift.
  - Added guide navigation links in:
    `docs/guides/index.rst` and `docs/guides/rebuild-repro-contract.rst`.
  - Added docs-contract coverage:
    `tests/test_docs_contract.py::test_interpret_rebuild_reports_guide_covers_core_sections`.
- 2026-03-11 (Phase 13 `P13.5d` completion): added contributor policy text
  making rebuild spec + checks mandatory for all new instance repositories.
  - Added explicit policy section in
    `docs/guides/rebuild-repro-contract.rst` requiring:
    tracked `config/rebuild.spec.yaml`, tracked
    `config/rebuild.allowlist.yaml`, spec validation, deterministic rebuild
    checks, and preserved rebuild evidence artifacts.
  - Added matching baseline contributor checklist in
    `docs/guides/deployment-instances.rst`.
  - Added docs-contract enforcement:
    `tests/test_docs_contract.py::test_contributor_policy_requires_rebuild_spec_and_checks`.
- 2026-03-11 (Phase 13 `P13.6a` completion): extended instance scaffolding so
  all new instance workspaces include rebuild runbook placeholders by default.
  - Updated `femic instance init` template set in
    `src/femic/instance_bootstrap.py` to include
    `runbooks/REBUILD_RUNBOOK.md` and create `runbooks/` directory.
  - Added runbook template resource:
    `src/femic/resources/instance/runbooks/REBUILD_RUNBOOK.md`.
  - Synced maintainer reference instance placeholder:
    `instances/reference/runbooks/REBUILD_RUNBOOK.md`.
  - Updated bootstrap docs/quickstart references in
    `src/femic/resources/instance/QUICKSTART.md` and
    `docs/guides/deployment-instances.rst`.
  - Added regression checks in
    `tests/test_instance_bootstrap.py` and
    `tests/test_docs_contract.py`.
- 2026-03-11 (Phase 13 `P13.6b` completion): added docs-contract enforcement
  requiring rebuild-spec references in sample/new instance documentation.
  - Updated sample-model K3Z guide to include explicit rebuild workflow
    references:
    `config/rebuild.spec.yaml`,
    `config/rebuild.allowlist.yaml`,
    `runbooks/REBUILD_RUNBOOK.md`.
  - Updated case-onboarding guide template checklist to include rebuild
    spec/allowlist/runbook assets.
  - Added/extended docs-contract assertions in `tests/test_docs_contract.py`
    to enforce these references going forward.
- 2026-03-11 (Phase 13 `P13.6c` completion): added release-gate enforcement
  requiring passing reference-instance rebuild evidence.
  - Added tracked evidence artifact:
    `instances/reference/evidence/reference_rebuild_report.latest.json`
    with explicit `regression_gate` pass status fields.
  - Added GitHub Actions release-gate step in
    `.github/workflows/package-release-checks.yml`:
    `Reference instance rebuild evidence gate`.
  - Added docs + docs-contract enforcement for evidence path and required pass
    fields in:
    `docs/guides/deployment-instances.rst` and
    `tests/test_docs_contract.py`.
- 2026-03-11 (Phase 13 `P13.6d` completion): formalized closure policy that no
  new instance phase can close without reproducible rebuild evidence.
  - Added mandatory policy section under Phase 13 in `ROADMAP.md`.
  - Added matching policy milestone entry in `CHANGE_LOG.md`.
  - Added docs-contract enforcement in `tests/test_docs_contract.py` to ensure
    the policy note remains present in roadmap and changelog artifacts.
- 2026-03-11 (Roadmap status normalization): marked completed parent checklist
  items as done where all child tasks were already complete.
  - Updated parent status for:
    `P12.3`, `P12.4`, `P12.5`, `P13.3`, `P13.4`, `P13.5`, and `P13.6`.
- 2026-03-11 (Phase 14 kickoff, `P14.1a/P14.1b/P14.1c` completion): added
  CLI automation to promote rebuild reports into normalized evidence artifacts.
  - Added command:
    `femic instance promote-evidence` in `src/femic/cli/main.py`.
  - Command supports explicit `--report` input or auto-selects latest
    `instance_rebuild_report-*.json` under `--log-dir`, and writes normalized
    payloads to `--output` (default
    `evidence/reference_rebuild_report.latest.json`).
  - Updated CLI reference docs and docs-contract/CLI test coverage in:
    `docs/reference/cli.rst`,
    `tests/test_docs_contract.py`,
    `tests/test_cli_main.py`.
- 2026-03-11 (Phase 14 `P14.2a` completion): added maintainer helper command
  to refresh reference rebuild evidence from current logs.
  - Added command:
    `femic instance refresh-reference-evidence` in `src/femic/cli/main.py`.
  - Command wraps `instance promote-evidence` with reference defaults:
    `--reference-root instances/reference`,
    output `evidence/reference_rebuild_report.latest.json`,
    log dir `vdyp_io/logs`.
  - Updated docs and test/contract coverage in:
    `docs/reference/cli.rst`,
    `docs/guides/deployment-instances.rst`,
    `tests/test_cli_main.py`,
    `tests/test_docs_contract.py`.
- 2026-03-11 (Phase 14 `P14.2b` completion): added explicit contributor
  runbook release-prep step for evidence refresh.
  - Updated instance runbook templates:
    `src/femic/resources/instance/runbooks/REBUILD_RUNBOOK.md` and
    `instances/reference/runbooks/REBUILD_RUNBOOK.md` to include
    `femic instance refresh-reference-evidence --reference-root .`
    and expected post-refresh checks.
  - Updated `docs/guides/deployment-instances.rst` with contributor
    release-prep requirement text.
  - Added docs-contract enforcement in `tests/test_docs_contract.py`.
- 2026-03-11 (Phase 14 `P14.3a` completion): added optional trend-drift
  warning thresholds for rebuild evidence summaries.
  - Extended `femic instance promote-evidence` with:
    `--max-warn-increase` and `--max-baseline-diff-increase`.
  - Added trend delta + warnings payload in evidence artifacts under
    `trend_drift` (previous summary, increases, thresholds, warnings).
  - Propagated threshold options through
    `femic instance refresh-reference-evidence`.
  - Updated CLI/deployment docs and contract/tests in:
    `docs/reference/cli.rst`,
    `docs/guides/deployment-instances.rst`,
    `tests/test_cli_main.py`,
    `tests/test_docs_contract.py`.
- 2026-03-11 (Phase 14 `P14.3b` completion): added release-operator guidance
  for interpreting evidence trend drift across releases.
  - Expanded `docs/guides/interpret-rebuild-reports.rst` with
    `Evidence Trend Drift Across Releases`, including:
    `trend_drift` field interpretation, threshold semantics, and a
    thresholded release workflow using
    `femic instance refresh-reference-evidence`.
  - Extended docs-contract enforcement in `tests/test_docs_contract.py` to
    require the drift-interpretation section and key `trend_drift` markers.
- 2026-03-11 (Phase 15 kickoff): opened species-account semantic hardening
  plan for K3Z to resolve `PL`/`PLC` ambiguity and prevent silent
  species-wise null regressions.
  - Execution order for next implementation pass:
    `P15.1a -> P15.1b -> P15.1c -> P15.2a -> P15.2b -> P15.2c`.
- 2026-03-11 (Phase 15 `P15.1a` completion + `P15.1b` implementation support):
  audited current K3Z species surfaces and added runtime support to exclude
  known-empty account rows during `protoaccounts -> accounts` promotion.
  - Audit evidence from
    `external/femic-k3z-instance/models/k3z_patchworks_model/yield/forestmodel.xml`:
    `managed_prop_PL_*` and `unmanaged_prop_PL_*` curves are all zero; `PLC`
    retains non-zero signal.
  - Added optional runtime config key:
    `matrix_builder.accounts_exclude_regex` in
    `src/femic/patchworks_runtime.py`.
  - Matrix-build manifests now record
    `accounts_sync.excluded_patterns` and `accounts_sync.excluded_row_count`.
  - Added tests in `tests/test_patchworks_runtime.py` for config parsing and
    regex-based exclusion behavior.
  - Added operator docs in `docs/guides/patchworks-wine-runtime.rst`.
  - Next execution step: apply the exclusion pattern in K3Z instance runtime
    config and verify account/target surfaces after matrix rebuild.
- 2026-03-11 (Phase 15 `P15.1b` completion): applied K3Z runtime account
  exclusion policy and verified matrix-build output surfaces.
  - Updated
    `external/femic-k3z-instance/config/patchworks.runtime.windows.yaml` with
    `matrix_builder.accounts_exclude_regex: ["\\.PL(\\.|$)"]`.
  - Re-ran matrix build:
    `python -m femic patchworks matrix-build --config external/femic-k3z-instance/config/patchworks.runtime.windows.yaml --run-id k3z_plc_cleanup_20260312b`.
  - Verified `tracks/accounts.csv` no longer includes `.PL` account rows while
    `.PLC` rows remain.
  - Verified manifest
    `vdyp_io/logs/patchworks_matrixbuilder_manifest-k3z_plc_cleanup_20260312b.json`
    reports
    `accounts_sync.excluded_patterns=["\\.PL(\\.|$)"]` and
    `accounts_sync.excluded_row_count=5`.
  - Next execution step: `P15.1c` docs note for student-facing species-code
    interpretation.
- 2026-03-11 (Phase 15 `P15.1c` completion): added explicit student-facing
  PL/PLC interpretation guidance in both standalone K3Z docs and FEMIC sample
  model docs.
  - Updated
    `external/femic-k3z-instance/docs/base-case-analysis.rst` with
    `Species Code Note (PL vs PLC)` defining `PLC` as canonical and clarifying
    that absent `PL` accounts are expected for K3Z.
  - Updated `docs/sample-models/k3z.rst` with
    `Species Code Semantics: PL vs PLC` including the active exclusion policy.
  - Added docs-contract guard in `tests/test_docs_contract.py` so this
    semantics note remains present.
- 2026-03-11 (Phase 15 `P15.2a` completion): added species-account completeness
  invariant support and wired K3Z fatal checks for PLC present / PL absent.
  - Added `accounts.list` metric in `src/femic/rebuild_invariants.py` and
    added `contains` / `not_contains` comparator support.
  - Extended rebuild-spec comparator allowlists in:
    `src/femic/rebuild_spec.py` and
    `planning/femic_instance_rebuild_spec_schema.v1.yaml`.
  - Added test coverage in:
    `tests/test_rebuild_invariants.py` and `tests/test_rebuild_spec.py`.
  - Added K3Z invariant policy entries in:
    `external/femic-k3z-instance/config/rebuild.spec.yaml`
    for:
    `product.Yield.managed.PLC`,
    `product.HarvestedVolume.managed.PLC.CC`,
    and exclusion of `product.Yield.managed.PL`,
    `product.HarvestedVolume.managed.PL.CC`.
  - Updated invariant-authoring docs in:
    `docs/guides/author-instance-rebuild-spec.rst`.
  - Next execution step: implement `P15.2b` configurable expected-empty policy
    semantics in rebuild spec/allowlist patterns.
- 2026-03-11 (Phase 15 `P15.2b` completion): added reusable rebuild-spec
  `species_account_policy` support so expected-empty vs required-present
  account surfaces are configurable by instance.
  - Added policy-invariant builder in
    `src/femic/rebuild_invariants.py` that emits fatal `contains` /
    `not_contains` checks over `accounts.list`.
  - Wired policy expansion into `femic instance rebuild` in
    `src/femic/cli/main.py`.
  - Extended rebuild-spec validation + schema in:
    `src/femic/rebuild_spec.py` and
    `planning/femic_instance_rebuild_spec_schema.v1.yaml`.
  - Added tests in:
    `tests/test_rebuild_invariants.py` and
    `tests/test_rebuild_spec.py`.
  - Migrated K3Z to policy-based configuration in:
    `external/femic-k3z-instance/config/rebuild.spec.yaml`.
  - Updated authoring docs in:
    `docs/guides/author-instance-rebuild-spec.rst`.
  - Next execution step: implement `P15.2c` to ensure rebuild command gating
    behavior is explicit and fail-fast for unexpected species-account null/empty
    regressions under policy.
- 2026-03-11 (packaging hotfix): fixed wheel package-data omission that caused
  release workflow wheel-smoke failure when `femic instance init` attempted to
  copy `resources/instance/runbooks/REBUILD_RUNBOOK.md`.
  - Added package-data include in `pyproject.toml`:
    `resources/instance/runbooks/*`.
  - Verified build output now includes runbook template in wheel payload.
- 2026-03-11 (Phase 15 `P15.2c` completion): rebuild now fails hard when
  species-account policy expects nonzero product labels and regenerated tracks
  regress to zero/null signal.
  - Added new rebuild metric extraction:
    `products.nonzero_labels` from `tracks/products.csv` + `tracks/curves.csv`
    in `src/femic/rebuild_invariants.py`.
  - Extended `runtime.species_account_policy` with:
    `required_nonzero` and `expected_zero` (fatal invariants over
    `products.nonzero_labels`).
  - Added/updated tests:
    `tests/test_rebuild_invariants.py`,
    `tests/test_cli_main.py`.
  - Updated spec-authoring docs and schema:
    `docs/guides/author-instance-rebuild-spec.rst`,
    `planning/femic_instance_rebuild_spec_schema.v1.yaml`.
  - Next execution step: start `P15.3a` (operator diagnostics helper for
    account/target coverage by species and AU).
- 2026-03-11 (repo hygiene): scrubbed real SPS license username from docs,
  configs, tests, and tracked manifests.
  - Replaced `frst424@auth.spatial.ca` with neutral example
    `sps_user@auth.spatial.ca` across FEMIC + K3Z instance repo content.
  - Purpose: avoid shipping user-identifying credentials in public-facing
    documentation/config examples while preserving executable examples/tests.
- 2026-03-11 (Phase 15 `P15.3a` completion): added first-class operator
  diagnostics helper for account-surface QA.
  - Added `femic instance account-surface` command in
    `src/femic/cli/main.py`.
  - Added account-surface parser/summarizer in
    `src/femic/account_surface.py` that reports:
    species-level yield/harvest account coverage and AU-level seral account
    coverage from `tracks/accounts.csv`.
  - Added tests in:
    `tests/test_account_surface.py`, `tests/test_cli_main.py`.
  - Updated CLI docs in:
    `docs/reference/cli.rst`.
  - Next execution step: implement `P15.3b` deterministic troubleshooting flow
    for "total OK, species-wise empty" failure signatures.
- 2026-03-11 (Phase 15 `P15.3b` completion): added deterministic
  troubleshooting flow for "total OK, species-wise empty" failures and wired it
  into diagnostics output expectations.
  - Extended `femic instance account-surface` diagnostics in
    `src/femic/account_surface.py` to compute:
    `diagnosis.total_ok_species_empty_signature` plus ordered
    `recommended_next_checks`.
  - Updated CLI output in `src/femic/cli/main.py` to emit explicit
    troubleshooting steps when the signature is detected.
  - Added regression tests in:
    `tests/test_account_surface.py`, `tests/test_cli_main.py`,
    `tests/test_docs_contract.py`.
  - Updated docs:
    `docs/guides/troubleshooting.rst`,
    `docs/reference/cli.rst`,
    `external/femic-k3z-instance/docs/troubleshooting.rst`.
  - Next execution step: implement `P15.3c` to wire diagnostics outputs into
    rebuild evidence/runbook guidance.
- 2026-03-12 (Phase 15 `P15.3c` + `P15.4` completion): wired account-surface
  diagnostics into rebuild evidence and finalized user-facing species-account
  docs coverage for K3Z.
  - `femic instance rebuild` now writes `diagnostics.account_surface` into
    rebuild reports when tracks are available and emits summary console lines.
  - `femic instance promote-evidence` now carries
    `summary.account_surface_total_ok_species_empty_signature` and
    `summary.account_surface_species_count`.
  - Updated runbook guidance in:
    `instances/reference/runbooks/REBUILD_RUNBOOK.md`,
    `src/femic/resources/instance/runbooks/REBUILD_RUNBOOK.md`.
  - Added expected-empty account matrix/checklist docs in:
    `docs/sample-models/k3z.rst` and
    `external/femic-k3z-instance/docs/base-case-analysis.rst`.
  - Expanded docs contract checks in `tests/test_docs_contract.py` to lock
    required species-account interpretation sections.
  - Phase 15 checklist is now complete.
- 2026-03-12 (K3Z regression recovery): restored matrix-builder coherence for
  K3Z after block-key mismatch + missing-seral-account regression.
  - Root causes addressed:
    - runtime config drifted `forestmodel_xml_path` away from model-local
      `models/k3z_patchworks_model/yield/forestmodel.xml`.
    - `build-blocks` model-root inference selected instance root in mixed
      `output/` + `models/` layouts.
    - `patchworks.license_value: null` was interpreted as literal `"None"`
      instead of falling back to `SPS_LICENSE_SERVER` env.
  - Implemented fixes:
    - Patched `src/femic/patchworks_runtime.py`:
      - `infer_patchworks_model_dir()` now prefers `tracks`/`yield` sibling
        roots when present.
      - `load_patchworks_runtime_config()` now treats null/blank
        `patchworks.license_value` as env fallback.
    - Added/updated tests in `tests/test_patchworks_runtime.py` for both
      behaviors.
    - Rebuilt K3Z forestmodel with seral stage attributes from
      `data/model_input_bundle/*` + `config/seral.k3z.yaml`, then reran matrix
      build (`run_id: k3z_regression_fix_final_20260312c`).
    - Rebuilt model-local `blocks.shp`/`topology_blocks_200r.csv` with
      `BLOCK <- BLOCK` and verified join-key parity (`csv_only=0`,
      `shp_only=0`).
  - Validation status:
    - `tracks/accounts.csv` now contains `feature.Seral.*` rows again.
    - matrix-builder stderr reports successful completion with
      `Managed : 1781.3132360577583` and no passive area.
- 2026-03-12 (K3Z docs-figure refresh): regenerated instance appendix
  `tipsy_vdyp_tsak3z-*.png` overlays from current `vdyp_transform` rebuild
  outputs and aligned figure wording to treated/scaled-VDYP semantics.
  - Verified rebuild provenance from
    `vdyp_io/logs/k3z_rebuild_report-k3z_rethread_win_20260312_1300.json`:
    `tipsy_curve_mode=vdyp_transform`, `matrix_returncode=0`,
    `block_join_csv_only=0`, `block_join_shp_only=0`.
  - Updated K3Z appendix heading/captions to "Treated (Scaled-VDYP) Curve
    Overlays" so student-facing docs match the actual curve mode.
  - Next step: publish refreshed submodule docs commit and update parent
    submodule pointer so GitHub Pages serves the regenerated overlays.
- 2026-03-14 (TSA-key hardening): strengthened TSA selection/index seams so
  stage 01a does not fail from TSA dtype/key-format drift.
  - Added canonical TSA normalizer in `src/femic/pipeline/tsa.py` and
    upgraded `select_tsa_slice(...)` to:
    - try normalized candidates,
    - fall back to normalized-index masking,
    - emit clearer missing-key diagnostics with available normalized keys.
  - Updated `src/femic/pipeline/stages.py::prepare_tsa_index(...)` to
    normalize TSA values when indexing legacy tables (including stale cached
    int/mixed-case TSA tokens).
  - Added regression tests in `tests/test_pipeline_helpers.py` for
    mixed-case named TSA (`K3Z`) and normalized index preparation behavior.
  - Validation gates run:
    `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest`,
    `pre-commit run --all-files`.
- 2026-03-14 (TIPSY freshness guard): added fail-fast protection against stale
  BatchTIPSY outputs to prevent mismatched VDYP-vs-TIPSY overlays.
  - Added `validate_tipsy_output_is_fresh(...)` in
    `src/femic/pipeline/tipsy.py`.
  - Wired guard into both legacy 01b surfaces:
    `01b_run-tsa.py` and `src/femic/resources/legacy/01b_run-tsa.py`.
  - Default behavior now raises when `04_output-tsaXX.out` is older than
    `tipsy_params_tsaXX.xlsx`; temporary bypass available via
    `FEMIC_ALLOW_STALE_TIPSY_OUTPUT=1`.
  - Added regression tests in `tests/test_tipsy.py` for stale-detect and
    explicit-override paths.
  - Validation gates run:
    `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest`,
    `pre-commit run --all-files`.
- 2026-03-14 (BatchTIPSY input contract clarification): aligned docs + runtime
  checks so `02_input-tsaXX.dat` is explicitly treated as the canonical
  BatchTIPSY handoff input artifact.
  - Added `tipsy_input_dat_path(...)` helper in
    `src/femic/pipeline/tipsy.py`.
  - Updated `validate_tipsy_output_is_fresh(...)` to:
    - prioritize DAT freshness checks over workbook-only checks,
    - fail fast if canonical DAT is missing when 01b is run,
    - continue allowing explicit override via
      `FEMIC_ALLOW_STALE_TIPSY_OUTPUT=1`.
  - Wired DAT-path freshness validation in both 01b runtime surfaces:
    `01b_run-tsa.py`, `src/femic/resources/legacy/01b_run-tsa.py`.
  - Clarified docs in:
    `docs/guides/stage-01a-vdyp-tipsy-input.rst`,
    `docs/guides/stage-01b-post-tipsy.rst`,
    `docs/guides/pipeline-overview.rst`.
  - Added tests for DAT-path helper + missing-DAT guard in
    `tests/test_tipsy.py`.
  - Validation gates run:
    `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest`,
    `pre-commit run --all-files`, `.venv/bin/sphinx-build -b html docs _build/html -W`.
- 2026-03-15 (resume-skip contract fix for missing DAT): patched 01a skip logic
  to require canonical DAT output, preventing stale/missing handoff artifacts
  from being silently skipped in resume mode.
  - Root cause: `_should_skip_01a(...)` only required
    `tipsy_params_tsaXX.xlsx` + `vdyp_curves_smooth-tsaXX.feather`, so
    `02_input-tsaXX.dat` could be missing while 01a was still skipped.
  - Fixed in both active legacy surfaces:
    `00_data-prep.py`,
    `src/femic/resources/legacy/00_data-prep.py`
    by adding `tipsy_input_dat_path(tsa=...)` to required skip outputs.
  - Updated AST wiring expectations in
    `tests/test_legacy_orchestration_wiring.py`.
  - Validation gates run:
    `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest`,
    `pre-commit run --all-files`, `.venv/bin/sphinx-build -b html docs _build/html -W`.
- 2026-03-15 (BatchTIPSY column alignment repair): fixed DAT writer mapping so
  generated `02_input-tsaXX.dat` aligns with operator BatchTIPSY field ranges
  (including species/regeneration columns) and no longer produces blank-species
  parsing failures.
  - Root cause: `src/femic/pipeline/tipsy.py` encoded
    `Proportion: (31, 31)`, forcing one-character width and destabilizing
    fixed-width export behavior for real `0.3`/`0.85` values.
  - Fix applied in `src/femic/pipeline/tipsy.py`:
    `Proportion` widened to `(31, 39)` while preserving screenshot-locked
    BatchTIPSY anchors (`Regen_Method` 64, `SPP_1` 97-99, `SI` 108-111, etc.).
  - Updated regression in `tests/test_tipsy.py` to keep overflow guard
    behavior by asserting width overflow on `FIZ` (1-char field) instead of the
    now-wider `Proportion` field.
  - Regenerated `data/02_input-tsa29.dat` and mirrored
    `external/femic-tsa29-instance/data/02_input-tsa29.dat` from the corrected
    writer path.
  - Validation gates run:
    `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest`,
    `pre-commit run --all-files`, `.venv/bin/sphinx-build -b html docs _build/html -W`.

## 2026-03-16 - Set default strata coverage to 0.80 and regenerated TSA29 fit outputs
- Updated legacy stage-00 default so `FEMIC_STRAT_TOP_AREA_COVERAGE` now defaults
  to `0.8` (instead of `None`/top-N fallback) in:
  - `00_data-prep.py`
  - `src/femic/resources/legacy/00_data-prep.py`
- Executed a full TSA29 smooth-curve rebuild with
  `FEMIC_STRAT_TOP_AREA_COVERAGE=0.8`, confirming:
  - `coverage 0.8061826878755755`
  - `count 18`
  - `resume: loaded pre-VDYP checkpoint (18 strata)`
- Regenerated TSA29 diagnostics:
  - `plots/strata-tsa29.png`
  - all `plots/vdyp_fitdiag_tsa29-*.png`
  - all `plots/vdyp_lmh_tsa29-*.png`
  - refreshed `data/vdyp_curves_smooth-tsa29.feather`
  - refreshed curve-event log:
    `vdyp_io/logs/vdyp_curve_events-tsa29-tsa29_cov80_refit_20260316T0115Z.jsonl`

## 2026-03-16 - VDYP fit selection status accepted-for-now; proceed to TIPSY-vs-VDYP review
- Fit selection behavior after current tail/toe/censoring updates is marked **OK for now**:
  there is remaining minor selection weirdness in some AUs, but no pathological
  failures and no null-curve total failures.
- Per review direction, deferred additional generalized fit-logic tuning and
  moved forward to regenerated TIPSY-vs-VDYP comparison outputs for visual QA.
- Regenerated TSA29 comparison plots:
  - all `plots/tipsy_vdyp_tsa29-*.png` (54 plots, refreshed at 2026-03-16 05:49 UTC)

## 2026-03-16 - Deferred high TIPSY/VDYP ratio AU review; proceed to ws3 smoke
- Scanned refreshed TSA29 AU-wise TIPSY-vs-VDYP comparisons and ratio diagnostics.
- With VDYP LMH curves currently plausible, queued high-ratio outliers for later
  focused review (not immediate blockers):
  - `ICH_CW L`, `SBPS_SX L`, `MS_PL L`, `SBPS_SX M`, `IDF_FDI L`
  - `ICH_CW H`, `IDF_FDI M`, `SBS_SX M`, `IDF_FD L`, `ICH_CW M`
- Immediate sequence decision: continue now to ws3 smoke on freshly regenerated
  curve and AU outputs, then revisit these AU ratio outliers in a dedicated pass.

## 2026-03-16 - Phase 19 checklist housekeeping reconciliation
- Reconciled Phase 19 parent-task status against completed subtask notes and
  changelog evidence:
  - marked `P19.13` complete,
  - marked `P19.14` complete,
  - marked `P19.16`/`P19.16e` complete.
- Active near-term Phase 19 open gate remains `P19.5` (full Patchworks-enabled
  rebuild validation/evidence promotion in validated runtime host).
- Phase 20 remains intentionally deferred to separate branch per current
  execution priority.
- Added new open task `P19.17` to perform a full TSA29 instance Sphinx docs
  deep-dive and augment thin/missing sections before Phase 19 closeout.
- Prepared Windows 11 Patchworks smoke handoff pack for the remaining `P19.5`
  gate in `planning/tsa29_patchworks_win11_smoke_handoff.md`, including
  exact input artifacts, pass/fail checklist, and evidence-capture targets.
- 2026-03-18 (K3Z checkpoint1 feature export handoff): generated a dedicated
  K3Z checkpoint1 feature artifact and exported it to shapefile, then published
  into the K3Z instance repo for downstream use.
  - Source extraction: masked 2024 VRI source
    `data/bc/vri/2024/VEG_COMP_LYR_R1_POLY_2024.gdb` with K3Z tenure boundary
    `data/bc/cfa/k3z/CFA K3Z Tenure.shp`.
  - Generated artifacts:
    `data/ria_vri_vclr1p_checkpoint1-tsak3z.feather`,
    `data/shp/ria_vri_vclr1p_checkpoint1-tsak3z.{shp,shx,dbf,prj,cpg}`,
    `data/shp/ria_vri_vclr1p_checkpoint1-tsak3z_fieldmap.csv`.
  - Published same artifacts in `external/femic-k3z-instance` and pushed
    submodule commit `a762076` to `origin/main`.

- 2026-03-20 (Phase 21 Windows smoke verification): synced this branch to
  parent commit `d289971` and K3Z submodule commit `ff7bd11`, then reran the
  K3Z Patchworks preflight + Matrix Builder on the validated Windows host.
  - Preflight passed with:
    `python -m femic patchworks preflight --config config/patchworks.runtime.windows.yaml --instance-root external/femic-k3z-instance`
  - Matrix Builder passed with:
    `python -m femic patchworks matrix-build --config config/patchworks.runtime.windows.yaml --instance-root external/femic-k3z-instance --run-id k3z_og_smoke_20260319`
  - Evidence/log paths:
    `external/femic-k3z-instance/vdyp_io/logs/patchworks_matrixbuilder_stdout-k3z_og_smoke_20260319.log`,
    `external/femic-k3z-instance/vdyp_io/logs/patchworks_matrixbuilder_stderr-k3z_og_smoke_20260319.log`,
    `external/femic-k3z-instance/vdyp_io/logs/patchworks_matrixbuilder_manifest-k3z_og_smoke_20260319.json`.
  - Smoke result summary:
    `returncode=0`, `Total=1781.3132360577583`, `Managed=1781.3132360577583`,
    `Passive=0.0`.
  - Verified compiled OG feature-account surface in K3Z tracks and published
    refreshed track tables in `external/femic-k3z-instance` commit `69322b2`.
  - Downstream Patchworks launch/UI smoke also passed: the revised K3Z model
    opened successfully in Patchworks and the new `og1`/`og2` accounts were
    visible and looked correct in the live model interface.

- 2026-03-20 (Phase 22 scaffold foundation): completed the first CT/fert scaffolding slice on branch `feature/k3z-ct-fert-treatment-scaffold` with matching K3Z instance branch `feature/k3z-ct-fert-treatment-option`.
  - Added a new silviculture-config path contract to Patchworks export (`--silviculture-config`) and threaded it through parent CLI/export plumbing without changing current runtime behavior.
  - Added a dedicated treatment-path fragment/XML field `SILV_STATE` with default value `baseline`, keeping `ORIGIN` reserved for natural/planted semantics.
  - Added silviculture scaffold templates:
    - parent bootstrap template: `src/femic/resources/instance/config/silviculture.case_template.yaml`
    - K3Z instance config: `external/femic-k3z-instance/config/silviculture.k3z.yaml`
  - Updated deterministic XML fixtures and regression coverage so the new define-field / fragment-schema contract is enforced before CT/fert treatment logic lands.
  - Next execution target remains Phase 22 treatment mechanics: provisional QMD support, CT curve/treatment synthesis, then fert chain logic.
- 2026-03-20 (Phase 22 CT/QMD slice): implemented the first treatment-mechanics pass on the active feature branches and verified that the optional K3Z variant compiles cleanly in Windows Patchworks Matrix Builder.
  - Pivoted `SILV_STATE` semantics from atomic placeholders to stacked treatment-path states: `baseline`, `cc_pl`, `cc_pl_ct`, `cc_pl_ct_f1`, `cc_pl_ct_f1_f2`, `cc_pl_ct_f1_f2_f3`.
  - Added provisional K3Z QMD feature curves and accounts (`feature.QMD.managed.<au_id>`, `feature.QMD.unmanaged.<au_id>`) with YAML-facing assumptions kept in the silviculture scaffold.
  - Added commercial thinning (`CT`) treatment support for the two initial eligible AUs (`985502001`, `985502002`), planted-only via `ORIGIN='planted'`, with per-AU age/removal parameters and temporary BA:volume conversion.
  - Added post-CT residual-volume curve synthesis so the CT path conserves the no-CT endpoint approximately by subtracting harvested volume at CT age from the planted baseline trajectory.
  - Regenerated the K3Z variant ForestModel XML and patched the validated fragments shapefile to carry `SILV_STATE`, then ran Matrix Builder smoke: `python -m femic patchworks matrix-build --config config/patchworks.runtime.windows.yaml --instance-root external/femic-k3z-instance --run-id k3z_ct_qmd_smoke_20260320`.
  - Smoke evidence: `external/femic-k3z-instance/vdyp_io/logs/patchworks_matrixbuilder_{stdout,stderr,manifest}-k3z_ct_qmd_smoke_20260320.*`; result `returncode=0`, `Managed=1692.2475729276887`, `Passive=89.06566313006975` (retention still active at 5%).
  - Generated tracks now include `CT` products (`product.HarvestedVolume.managed.Total.CT`, species-wise CT harvested volume) plus the provisional QMD account surface; next execution target is the fert1/fert2/fert3 chain.
- 2026-03-20 (Phase 22 fert-chain smoke): completed the first full CT + `fert1`/`fert2`/`fert3` compile pass on the optional K3Z variant and verified it downstream in live Patchworks.
  - Added YAML-driven fertilization sequencing and response-curve synthesis so eligible K3Z CT tracks now expose `F1`, `F2`, and `F3` in addition to `CT`.
  - Added a CT timing guard so effective CT age is pulled back to at most `F1_age - 10` when needed, ensuring there is space for the full fertilization chain.
  - Fresh Matrix Builder rerun: `python -m femic patchworks matrix-build --config config/patchworks.runtime.windows.yaml --instance-root external/femic-k3z-instance --run-id k3z_ct_f123_rerun_20260320`.
  - Fresh evidence/logs: `external/femic-k3z-instance/vdyp_io/logs/patchworks_matrixbuilder_{stdout,stderr,manifest}-k3z_ct_f123_rerun_20260320.*`.
  - Rerun result: `returncode=0`, with compiled tracks now materializing `CT`, `F1`, `F2`, and `F3` treatment rows plus the matching `product.Treated.managed.{CT,F1,F2,F3}` account/product surface.
  - Downstream Patchworks smoke passed: pulling on the `F3` treated-area target induced the expected upstream treatment chain (`F2`, `F1`, `CT`, `CC`) in prior timesteps.
- 2026-03-20 (Phase 22 docs follow-up queued): expand the standalone `femic-k3z-instance` Sphinx docs so they describe the full current K3Z Patchworks surface, not just the newest CT/fert slice.
  - Docs backlog now explicitly includes both:
    - Phase 21 OG rollout coverage (`feature.Area.og1.*`, `feature.Area.og2.*`, `og1`/`og2` curve semantics, and how those accounts appear in compiled Patchworks outputs), and
    - Phase 22 optional CT/QMD/fert variant coverage (YAML parameters, `SILV_STATE` path semantics, provisional curve heuristics, and how student groups pull the optional branch into their instance forks).
- 2026-03-20 (Phase 22 standalone docs pass): updated the standalone `femic-k3z-instance` Sphinx docs to reflect the current full K3Z Patchworks surface, including both the Phase 21 OG rollout and the optional Phase 22 CT/QMD/fert variant.
  - Updated K3Z docs pages: `getting-started.rst`, `model-anatomy.rst`, `assumptions-registry.rst`, `base-case-analysis.rst`, `operator-runbook.rst`, `edit-policy-and-scenarios.rst`, `rebuild-and-qa.rst`, and `metadata-and-lineage.rst`.
  - Added explicit documentation for `og1` / `og2` feature-area accounts, current OG curve semantics, optional branch usage (`feature/k3z-ct-fert-treatment-option`), `SILV_STATE` treatment-path semantics, provisional QMD outputs, and CT/F1/F2/F3 operator expectations.
  - Validation passed: `python -m sphinx -b html external/femic-k3z-instance/docs external/femic-k3z-instance/docs/_build/html -W`.
- 2026-03-20: CT/fert coexistence QA found that `ctfert.pin` now launches cleanly after fixing target-script account-path resolution. Follow-up on map layers is complete: `analysis/ctfert.pin` now includes `CT`, `F1`, `F2`, and `F3` in Current Treatments / Latest Treatments. Remaining open blocker for `P22.9e`: a clean variant rebuild from canonical K3Z inputs is currently blocked because the instance only carries `data/ria_vri_vclr1p_checkpoint1-tsak3z.feather`, while Patchworks export currently requires a later checkpoint that already includes `au`.
- 2026-03-20: repository process tightened in `AGENTS.md`: all non-trivial implementation plans must be recorded in `ROADMAP.md` before execution proceeds. Phase 22 coexistence work is now explicitly tracked under `P22.9` so the single-branch / multi-variant K3Z strategy is visible and auditable outside of chat.
- 2026-03-20 (Phase 23 Windows clean-start progress): the native Windows K3Z rerun now reaches the real VDYP handoff stage using the instance-local 2024 VRI stack, and the failure signature is narrowed enough to drive the next fixes deterministically.
  - Confirmed instance-local 2024 inputs are in use when `femic run` is launched without `FEMIC_EXTERNAL_DATA_ROOT`: `data/bc/vri/2024/VEG_COMP_LYR_R1_POLY_2024.gdb`, `data/bc/vri/2024/VEG_COMP_VDYP7_INPUT_POLY_AND_LAYER_2024.gdb`, plus local TSA/siteprod junctions under the K3Z instance.
  - Added/validated Windows-specific runtime fixes already working: no Wine preflight requirement on Windows, ArcGIS Pro (`propy.bat`) fallback for SiteProd raster export/stack, and shared-root fallback for `vdyp_params-landp` existence checks.
  - Fresh evidence from `k3z_windows_2024_native_20260320_i` shows the blocking seam is now the actual native VDYP command assembly, not source-data access: VDYP is launched, but the command still dispatches `-p vdyp_params-landp` without a `-c <VDYP_CFG>` argument, producing empty outputs and `proc_stderr_head` = `ERROR: Unable to open parameter file name: 'vdyp_params-landp'` + `FATAL: VDYP7 Configuration Folder ('-c') has not been supplied.`
  - Downstream `01b` stale-BatchTIPSY failure is therefore currently interpreted as a secondary symptom of empty VDYP outputs, not the primary blocker.
  - Immediate next execution order for `P23.2`: fix Windows VDYP command assembly (`-p` resolved path + `-c` config dir), rerun clean-start K3Z on 2024 VRI, then revisit fresh 01b/TIPSY regeneration only after non-empty VDYP tables are confirmed.
- 2026-03-20: P22.9e corrective plan narrowed after the first canonical checkpoint7 regeneration succeeded mechanically but rebuilt the wrong K3Z landbase.
  - The regenerated checkpoint7 currently produces `au=27`, `fragments=260`, and raw THLB-driven unmanaged area, whereas the live teaching baseline is intentionally `THLB=1` everywhere with `fragments=218` across 14 AUs.
  - Corrective approach for the canonical rebuild: regenerate an AU-bearing checkpoint7 from `checkpoint1`, but preserve the current baseline footprint by using the tracked baseline fragment feature/AU mask as the authoritative K3Z teaching surface.
  - Success condition for `P22.9e`: the rebuilt CT/fert variant compiles from canonical upstream inputs and still behaves as an additive extension of the live baseline rather than a broader raw landbase reintroduction.

- 2026-03-20 (Phase 23 Windows native VDYP breakthrough): a clean-start K3Z rerun against the instance-local 2024 VRI stack (`run_id=k3z_windows_2024_native_20260320_l`) now succeeds through VRI load, ArcGIS Pro SiteProd export, VDYP bootstrap, two-pass SI rebin, and TIPSY-input generation on native Windows. The fixes that unlocked this were: (1) resolving `vdyp_params-landp` from FEMIC source root, (2) adding `-c <VDYP_CFG>` to the Windows VDYP command, (3) ensuring the `-c` path ends with a trailing slash so native VDYP can find `*.ctr` files, and (4) materializing `external/femic-k3z-instance/vdyp_io/VDYP.INI` so the parameter file's relative `-ini .\vdyp_io\VDYP.INI` reference resolves inside the instance. The remaining blocker is no longer Windows VDYP; it is the expected manual BatchTIPSY freshness boundary in Stage 01b (`external/femic-k3z-instance/data/04_output-tsak3z.out` is older than the newly generated `external/femic-k3z-instance/data/02_input-tsak3z.dat`). Treat the next execution order as: run BatchTIPSY manually on the fresh `02_input-tsak3z.dat`, replace `04_output-tsak3z.out`, rerun FEMIC Stage 01b/post-TIPSY, then decide whether to automate or explicitly preserve that GUI boundary in Phase 23 docs.

- 2026-03-20 (Phase 23 K3Z Windows handoff simplification): during the native Windows rerun, the remaining BatchTIPSY friction narrowed to a small low-yield tail in the K3Z treated AU set. The next remediation path is now explicit:
  - Exclude the `CWHvm_CW+YC` and `CWHvm_CW+PLC` K3Z strata from BatchTIPSY parameter generation altogether so Windows 01a no longer tries to produce treated TIPSY rows for those low-yield pathways.
  - Treat those same strata as fully netted out of THLB in Patchworks export by forcing `RETENTION = 1.0` for all matching fragments, while keeping their unmanaged VDYP/state surface available in the baseline model.
  - Immediate execution order: add config-driven TIPSY stratum exclusion + full-retention fragment overrides, rerun K3Z Stage 01a on instance-local 2024 VRI, confirm the regenerated `external/femic-k3z-instance/data/02_input-tsak3z.dat` no longer contains the problematic `PLC` treated row, then hand the fresh DAT to BatchTIPSY.

- 2026-03-20: K3Z Windows/TIPSY remediation plan narrowed further after operator review.
  - Accepted modeling simplification for the canonical K3Z rebuild: stop compiling BatchTIPSY rows for the low-yield `CWHvm_CW+YC` and `CWHvm_CW+PLC` strata, and instead net those strata out of THLB completely by forcing `RETENTION = 1.0` for matching fragments.
  - Accepted replacement teaching logic for the remaining treated TIPSY species mixes:
    - FD-pair AUs: `900 FD + 3100 HW`
    - CW-pair AUs: `900 CW + 3100 HW`
    - all other remaining treated AUs: `600 CW + 300 FD + 3100 HW`
  - Follow-through requirement: the user-facing K3Z docs must state this explicitly so students understand why these strata no longer appear in the treated/TIPSY handoff and why their area shows up only in the retained/unmanaged side of the baseline model.

- 2026-03-21 (Phase 23 true-TIPSY evaluation pass): after refreshing external/femic-k3z-instance/data/04_output-tsak3z.out, the downstream-only 	sa post-tipsy path was repaired to read schema-v2 dyp_prep-tsak3z.pkl checkpoints and to execute  1b_run-tsa.py from the instance root so relative ./data and ./plots paths resolve correctly. A true-TIPSY managed-curve rerun completed successfully with 
un_id=k3z_post_tipsy_true_tipsy_20260321_d, rebuilt external/femic-k3z-instance/data/model_input_bundle/curve_table.csv and curve_points_table.csv, refreshed the current external/femic-k3z-instance/data/tipsy_curves_tsak3z.csv and 	ipsy_sppcomp_tsak3z.csv, and regenerated the current external/femic-k3z-instance/plots/tipsy_vdyp_tsak3z-*.png comparison set for the remaining treated AUs. The excluded low-yield strata (22006, 22008) no longer participate in BatchTIPSY and their stale comparison plots were removed so operator review now focuses only on the retained treated AU set. Next decision point: inspect the refreshed plots and decide whether K3Z should keep dyp_transform as the teaching baseline or switch the managed-curve baseline to true TIPSY output.

- 2026-03-21 (Phase 23 VDYP smoothing triage): operator review of the refreshed K3Z TIPSY-vs-VDYP plots accepted the current true-TIPSY output for now, but flagged a new regression in some smoothed VDYP unmanaged curves: sharp post-peak drop-off followed by an implausible upward blend ramp into the flat tail. The next bounded experiment is to rerun only the cached K3Z smoothing plus downstream handoff from existing `vdyp_results-tsak3z.pkl` and `vdyp_prep-tsak3z.pkl` inputs while (1) removing the hard-coded `tail_blend_override_k3z` selection, (2) relaxing the default toe/right-shift policy away from the current global `body_c_min=20` and `toe_shift_years=20`, and then (3) regenerating downstream DAT/post-TIPSY comparison artifacts without rerunning raw VDYP.
- 2026-03-21 (Phase 23 cached smoothing experiment): reran the K3Z VDYP smoothing stage and downstream post-TIPSY artifacts without rerunning raw VDYP, using cached `external/femic-k3z-instance/data/vdyp_results-tsak3z.pkl` plus `vdyp_prep-tsak3z.pkl`. For this bounded trial, the hard-coded `tail_blend_override_k3z` path was disabled by default in `src/femic/pipeline/vdyp_stage.py`, and the rerun used relaxed fit defaults (`FEMIC_BODY_C_MIN=5`, `FEMIC_VDYP_TOE_SHIFT_YEARS=5`). The smoothing rebuild completed with `run_id=k3z_vdyp_smooth_relax_20260321_b`, rewrote `external/femic-k3z-instance/data/vdyp_curves_smooth-tsak3z.feather`, and recorded events in `external/femic-k3z-instance/vdyp_io/logs/vdyp_curve_events-tsak3z-k3z_vdyp_smooth_relax_20260321_b.jsonl`. Selection counts in that event log were `tail_blend=14`, `primary_nlls=10`, `censored_refit=3`, and importantly there were no `tail_blend_override_k3z` selections. Then `python -m femic tsa post-tipsy --instance-root external/femic-k3z-instance --tsa k3z --run-id k3z_post_tipsy_smooth_relax_20260321_b` completed successfully, refreshing the current `tipsy_vdyp_tsak3z-*.png` comparison plots for the retained treated AUs (timestamps around 2026-03-21 00:50). Next operator step: visually compare these refreshed plots against the backup snapshot under `external/femic-k3z-instance/plots/backup_smoothing_20260321_004810` and decide whether the relaxed smoothing policy is a keeper.
- 2026-03-21 (Phase 23 cached smoothing experiment, pass 2): a second bounded K3Z smoothing rerun pushed the toe and tail policy further in the same cached-results-only workflow. This pass kept `FEMIC_K3Z_FORCE_TAIL_BLEND=0` and used `FEMIC_BODY_C_MIN=0`, `FEMIC_VDYP_TOE_SHIFT_YEARS=0`, `FEMIC_TAIL_LINEAR_MIN_R2=0.45`, `FEMIC_TAIL_LINEAR_MAX_NRMSE=0.35`, `FEMIC_TAIL_LINEAR_PREFER_MIN_AGE=120`, `FEMIC_TAIL_LINEAR_FLAT_SLOPE_ABS=0.10`, `FEMIC_TAIL_LINEAR_MIN_SPAN_YEARS=40`, and `FEMIC_TAIL_BLEND_YEARS=60`. The smoothing rebuild completed with `run_id=k3z_vdyp_smooth_relax_20260321_c`, rewrote `external/femic-k3z-instance/data/vdyp_curves_smooth-tsak3z.feather`, and refreshed downstream post-TIPSY artifacts with `run_id=k3z_post_tipsy_smooth_relax_20260321_c`. The new event log is `external/femic-k3z-instance/vdyp_io/logs/vdyp_curve_events-tsak3z-k3z_vdyp_smooth_relax_20260321_c.jsonl`, and the refreshed `tipsy_vdyp_tsak3z-*.png` plots now carry timestamps around 2026-03-21 00:54. Selection counts in this pass were `tail_blend=20` and `primary_nlls=7`, so the longer-tail policy is materially more permissive than pass 1; operator review is needed to decide whether the visual result is better enough to keep.
- 2026-03-21 (Phase 23 cached smoothing experiment, pass 3 planned): operator review judged pass 2 as moving in the right direction but still too constrained on both the toe and tail. The next bounded trial will keep the cached-results-only workflow and push the same knobs further: allow an earlier body shift (`body_c_min < 0` if tolerated), keep `toe_shift_years=0`, and relax tail-detection / tail-span preferences again so more curves can carry longer, gentler tails before blend selection is considered harmful.
- 2026-03-21 (Phase 23 cached smoothing experiment, pass 3): pushed the toe/tail policy further with `FEMIC_BODY_C_MIN=-20`, `FEMIC_VDYP_TOE_SHIFT_YEARS=0`, `FEMIC_TAIL_LINEAR_MIN_R2=0.20`, `FEMIC_TAIL_LINEAR_MAX_NRMSE=0.50`, `FEMIC_TAIL_LINEAR_PREFER_MIN_AGE=90`, `FEMIC_TAIL_LINEAR_FLAT_SLOPE_ABS=0.20`, `FEMIC_TAIL_LINEAR_MIN_SPAN_YEARS=20`, and `FEMIC_TAIL_BLEND_YEARS=90`, still with `FEMIC_K3Z_FORCE_TAIL_BLEND=0`. Cached smoothing reran successfully with `run_id=k3z_vdyp_smooth_relax_20260321_d`, followed by downstream post-TIPSY refresh `run_id=k3z_post_tipsy_smooth_relax_20260321_d`. The new event log is `external/femic-k3z-instance/vdyp_io/logs/vdyp_curve_events-tsak3z-k3z_vdyp_smooth_relax_20260321_d.jsonl`; selection counts shifted to `tail_blend=15`, `primary_nlls=9`, `censored_refit=3` versus pass 2's `tail_blend=20`, `primary_nlls=7`. The refreshed `tipsy_vdyp_tsak3z-*.png` plots now carry timestamps around 2026-03-21 00:58 and should be compared against the previous pass backup under `external/femic-k3z-instance/plots/backup_smoothing_20260321_005744`.
- 2026-03-21 (Phase 23 fit-override interface note): K3Z VDYP smoothing does not yet expose a user-facing YAML interface for per-stratum/per-SI fit-parameter overrides. Current override surfaces are (a) global run/env knobs such as `FEMIC_VDYP_TOE_SHIFT_YEARS` and tail-linearity env vars, and (b) the code-level per-TSA override map in `src/femic/pipeline/vdyp_overrides.py`. Immediate practical path: use the existing override map for the pathological `CWHvm_DR+HW` curves while continuing to relax the global tail policy; follow-up task remains to promote these per-curve fit overrides into a documented YAML/config surface for case-specific tuning.

## Phase 23 Addendum: VDYP Fit Policy Config Surface (Nice-to-Have Later)
- [ ] P23.6 Replace code-level VDYP fit overrides with a YAML-backed policy surface
  - [ ] P23.6a Define FEMIC-level default VDYP fit/tail/toe parameters in a human-readable YAML config artifact instead of hard-coded Python defaults where practical.
  - [ ] P23.6b Add per-instance YAML override support so case-specific fit rules (for example K3Z CWHvm_DR+HW tail relaxation) do not require editing src/femic/pipeline/vdyp_overrides.py.
  - [ ] P23.6c Preserve a narrow code-level fallback seam only for exceptional cases that truly cannot be expressed cleanly in YAML.
  - [ ] P23.6d Update developer/operator docs to explain the new config surface, override precedence, and when not to override fit behavior.
  - [ ] P23.6e Open and link a dedicated GitHub feature-request issue before implementation so the design and tradeoffs are traceable outside the roadmap.

- 2026-03-21 (Phase 23 fit-policy config follow-up): the current src/femic/pipeline/vdyp_overrides.py seam is acceptable as a short-term debugging lever, but it is too cludgey to remain the long-term user/deployment interface. Added low-priority P23.6 to migrate VDYP fit defaults and per-instance override rules into human-readable YAML, keep Python overrides as a narrow fallback only, and update user/developer docs when that interface lands. A dedicated GitHub feature-request issue should be opened when this moves from backlog to active work.

- 2026-03-21 (Phase 23 K3Z lock-in): accepted the current K3Z managed-curve and smoothing policy as the working baseline for now.
  - `config/run_profile.k3z.yaml` now uses `managed_curve_mode: tipsy` in both FEMIC and the standalone K3Z instance.
  - Current K3Z treated-curve baseline is: real BatchTIPSY output, driven by VDYP-derived SI, with CW+YC / CW+PLC excluded from BatchTIPSY and retained out of THLB via `RETENTION = 1.0`.
  - Current unmanaged smoothing checkpoint is the 2026-03-21 relaxed toe/tail policy plus extra DR+HW overrides; refreshed `tipsy_vdyp_tsak3z-*.png` plots are the review artifact of record.


- 2026-03-21 (Phase 22 coexistence expansion): added a third planned K3Z variant, pctct, so the single-branch coexistence model now targets three upstream-distinct variants on one mainline instance: baseline, ctfert, and pctct. The new variant will add a pre-commercial thinning (PCT) gate ahead of CT, apply it at age 10 by default, remove hardwood ingress while retaining the planted conifer component at a 900 stems/ha residual target, and require PCT before CT can fire. Follow-through requirement: extend the variant config/runtime/PIN surface (tracks_pctct, forestmodel_pctct.xml, analysis/pctct.pin, output/patchworks_k3z_pctct_validated/) and update standalone K3Z docs so students choose among the three variants by config/PIN rather than by Git branch.




- 2026-03-21 (Phase 22 closeout bookkeeping): roadmap status reconciled with the work that actually landed on main. `P22.9f`, `P22.9g`, and the parent `P22.10` checkbox are now marked complete because the standalone K3Z docs teach variant selection by config/PIN, the three-variant coexistence layout is merged to `main` in both repos, and `pctct.pin` smoke passed in live Patchworks. `P22.9e` remains open intentionally as the one unresolved canonical-rebuild cleanup item for the CT/fert variant.

- 2026-03-21 (Phase 22 pctct scaffold): implemented the third coexisting K3Z variant as a real compile target rather than just a roadmap stub. Parent FEMIC now supports `pre_commercial_thinning` silviculture config, new `SILV_STATE` values (`cc_pl_pct`, `cc_pl_pct_ct`), and post-PCT conifer-only managed species surfaces. The K3Z instance now carries `config/patchworks.variant.pctct.yaml`, `config/patchworks.runtime.pctct.windows.yaml`, `config/silviculture.k3z.pctct.yaml`, `models/k3z_patchworks_model/analysis/pctct.pin`, `models/k3z_patchworks_model/yield/forestmodel_pctct.xml`, `models/k3z_patchworks_model/tracks_pctct/`, and `output/patchworks_k3z_pctct_validated/`. Windows Matrix Builder smoke passed with `run_id=k3z_pctct_smoke_20260321`; remaining open work is the user-facing docs/runbook update under `P22.10g`.

- 2026-03-21 (Phase 23 docs sync): the standalone K3Z docs and the parent Phase 23 operator guides were reconciled with the accepted K3Z teaching baseline.
  - `external/femic-k3z-instance/docs/figure-appendix.rst` now describes the treated overlay figures as real TIPSY-vs-VDYP comparisons instead of the old scaled-VDYP wording.
  - The treated overlay appendix and plot inventory intentionally omit AUs `22006` and `22008`, because `CWHvm_CW+YC` and `CWHvm_CW+PLC` are now excluded from the treated/TIPSY pathway and retained out of THLB via `RETENTION = 1.0`.
  - Parent/operator docs now document the known-good Windows bootstrap sequence, the low-yield treated-strata netdown decision, and the simplified K3Z treated species-mix logic as the current baseline rather than as temporary operator lore.

- 2026-03-21 (Phase 23 Windows bootstrap/DataLad docs): promoted the Windows workstation ritual from tribal knowledge into the parent docs.
  - `docs/guides/geospatial-runtime-bootstrap.rst` now records the authoritative Windows/Linux runtime surfaces, required executables, and the known-good Windows bootstrap sequence for `.venv`, git/git-annex/DataLad, native VDYP, Java, Patchworks, and ArcGIS Pro fallback.
  - `docs/guides/public-data-mirror-runbook.rst` now includes a Windows-specific collaborator workflow, `.venv\Scripts\datalad.exe` usage, annex-backed payload smoke checks, and recovery guidance when GIS tools dirty the public-data submodule.
  - `docs/guides/deployment-instances.rst` now points Windows users at the bootstrap/runtime guide explicitly.


- 2026-03-21 (Phase 23 Windows preflight hardening): case preflight now understands the real Windows deployment shape instead of assuming every shared asset lives under the instance root. `src/femic/cli/main.py` now falls back from instance-local paths to the FEMIC source tree for shared Windows assets such as `data/tipsy_params_columns`, `vdyp_io/VDYP_CFG`, `VDYP7/VDYP7/VDYP7Console.exe`, and `ria_maptiles.csv`, so `femic prep validate-case --instance-root external/femic-k3z-instance --run-config config/run_profile.k3z.yaml` passes on the known-good workstation. The same preflight path now also checks for `git` and `git-annex` on Windows and runs lightweight annex/DataLad smoke checks (`git -C external/femic-public-data annex version` and `datalad status external/femic-public-data`) whenever the case depends on the annex-backed public-data submodule. This closes `P23.1c` and `P23.4c`.





