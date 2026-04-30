# Refactor Roadmap

Historical roadmap narrative and superseded structural snapshots: `planning/roadmap_notes_archive.md`

## Phase 1: Stabilize Runtime + Inputs
- [x] P1.1 Stand up Typer CLI entrypoint (FHOPS-style, nemora-compatible)
  - [x] P1.1a Expose the `femic` console script (Forest Estate Modelling Integration Core)
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
  - [x] P5.4a Add "what good looks like" checks for strata, fit diagnostics, and
    TIPSY-vs-VDYP overlays
  - [x] P5.4b Document common failure signatures and deterministic remedies
  - [x] P5.4c Add manual BatchTIPSY handoff checklist and fixed-width DAT caveats
- [x] P5.5 Preserve traceability to legacy notebooks
  - [x] P5.5a Add "Legacy Notebook Traceability" docs page with cell-index mapping
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
  - [x] P7.5a Add step-by-step "Patchworks under Wine" guide
  - [x] P7.5b Add "VPN + licensing diagnostics" guide
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
  - [x] P10.5c Final docs updates for "install package + create instance + run".
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
- [x] P19.5 Execute BTC-first rebuild validation and publish evidence (`#10`)
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
- [x] P19.17 Execute TSA29 instance Sphinx docs deep-dive and augmentation pass
  - [x] P19.17a Audit TSA29 instance Sphinx pages for thin/missing sections
    (workflow steps, assumptions, artifact references, troubleshooting detail).
  - [x] P19.17b Expand weak sections with concrete procedural guidance and
    explicit cross-links to current TSA29 compile/smoke evidence artifacts.
  - [x] P19.17c Rebuild docs with warnings-as-errors and publish a short
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
- [x] P22.9 Co-locate baseline and CT/fert variants inside one K3Z instance on main
  - [x] P22.9a Define the coexistence pattern: variant selection happens by
    config/PIN/runtime target, not by Git branch.
  - [x] P22.9b Add distinct K3Z variant config YAMLs documenting baseline and
    CT/fert build instructions plus their variant-specific runtime targets.
  - [x] P22.9c Add distinct CT/fert runtime/build surfaces (`tracks_ctfert`,
    `forestmodel_ctfert.xml`, `output/patchworks_k3z_ctfert_validated/`,
    `analysis/ctfert.pin`) so baseline and variant can coexist in one instance.
  - [x] P22.9d Fix shared target-script path assumptions so each PIN resolves
    accounts/validation against its own active tracks folder.
  - [x] P22.9e Rebuild the CT/fert variant from canonical K3Z inputs while
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
- [x] P23.7 Reduce false-positive BatchTIPSY freshness halts during development loops
  - [x] P23.7a When `02_input` is newer than `04_output` and DAT fingerprint sidecar is absent, perform a structural coherence check between TIPSY input parameters and output tables (AU/table coverage) before deciding to halt.
  - [x] P23.7b Default behavior should warn-and-continue when coherence checks pass, rather than hard-failing on timestamp mismatch alone.
  - [x] P23.7c Add a non-default strict override switch to escalate coherent timestamp mismatch back to an error for users who want hard freshness gating.
  - [x] P23.7d Add regression tests and docs updates for the new default + strict override behavior.
- [x] P23.8 Resolve Linux THLB raster path seam for clean tmp-clone reruns
  - [x] P23.8a When instance-local `data/misc.thlb.tif` is absent, resolve THLB raster from `FEMIC_EXTERNAL_DATA_ROOT` (or other canonical external data root) instead of hard-failing late in post-TIPSY bundle assembly.
  - [x] P23.8b Add diagnostics so logs show which THLB raster path was selected (instance-local vs external-root fallback).
  - [x] P23.8c Add regression coverage for THLB path fallback and preserve existing behavior when instance-local raster is present.
  - [x] P23.8d Update Linux parity notes/docs to reflect this runtime expectation explicitly.
- [x] P23.9 Publish canonical stacked SiteProd TIFF artifact to `femic-public-data`
  - [x] P23.9a Promote a known-good `siteprod.tif` artifact from Linux parity runs into `external/femic-public-data/data/bc/siteprod/`.
  - [x] P23.10 Make pre-stacked SiteProd the default runtime path when `siteprod.tif` + `siteprod.bandmap.json` are present.
    - [x] P23.10a Resolve preferred SiteProd source from canonical artifacts first (instance-local or external mirror), falling back to ArcRasterRescue/ArcPy only when the stacked TIFF or band-map sidecar is missing.
    - [x] P23.10b Log the selected SiteProd source path and whether fallback export/stack was used.
    - [x] P23.10c Ensure Windows K3Z runs proceed without ArcRasterRescue or ArcPy when canonical SiteProd TIFF + band-map artifacts are present.
    - [x] P23.10d Preserve ArcRasterRescue/ArcPy fallback behavior for hosts/environments where canonical SiteProd artifacts are absent.
    - [x] P23.10e Add tests, docs, and changelog coverage for the new default path.
  - [x] P23.9b `datalad save` the new artifact and push dataset history to GitHub (`UBC-FRESH/femic-public-data` main + git-annex metadata branch).
  - [x] P23.9c Upload annex content to `arbutus-s3` and verify `git annex find ... --not --in arbutus-s3` returns zero for the new SiteProd TIFF.
- [x] P23.10 Publish canonical SiteProd band-map sidecar for pre-stacked TIFF runtime use
  - [x] P23.10a Add `external/femic-public-data/data/bc/siteprod/siteprod.bandmap.json` with machine-readable species-to-band mapping for `siteprod.tif` (1-based + 0-based + ordered list).
  - [x] P23.10b Push `femic-public-data` dataset update to GitHub `main` and keep `git-annex` metadata branch synchronized.
  - [x] P23.10c Verify cloud distribution state: if sidecar is annexed, ensure `arbutus-s3` copy exists; if Git-tracked text, document that it is distributed via Git branch sync.

- [x] P23.11 Replace code-level VDYP fit overrides with a YAML-backed policy surface
  - [x] P23.11a Define FEMIC-level default VDYP fit/tail/toe parameters in a human-readable YAML config artifact instead of hard-coded Python defaults where practical.
  - [x] P23.11b Add per-instance YAML override support so case-specific fit rules (for example K3Z CWHvm_DR+HW tail relaxation) do not require editing src/femic/pipeline/vdyp_overrides.py.
  - [x] P23.11c Preserve a narrow code-level fallback seam only for exceptional cases that truly cannot be expressed cleanly in YAML.
  - [x] P23.11d Update developer/operator docs to explain the new config surface, override precedence, and when not to override fit behavior.
  - [x] P23.11e Open and link a dedicated GitHub feature-request issue before implementation so the design and tradeoffs are traceable outside the roadmap.

## Phase 24: FEMIC API Docs Rebuild + Agent-Friendly Technical Documentation
- [x] P24.1 Rebuild FEMIC API docs to a usable depth/quality standard
  - [x] P24.1a Audit the current API docs surface and identify modules/pages that are too terse, too dense, or effectively unusable.
  - [x] P24.1b Define a target API-doc style guide using `ws3` and `fhops` as reference exemplars for depth, structure, and narrative density.
  - [x] P24.1c Prioritize the first FEMIC modules/packages to rewrite (CLI, pipeline, fmg, instance/bootstrap, public-data/runtime helpers).
  - [x] P24.1d Replace low-value autosummary-only pages with hand-authored API narrative that explains purpose, contracts, common call patterns, and failure modes.
    - [x] P24.1d.1 Rewrite the first-wave high-priority operational module pages:
      `femic.cli.main`, `femic.pipeline.vdyp_stage`, `femic.pipeline.io`,
      `femic.pipeline.tipsy`, `femic.pipeline.siteprod`,
      `femic.fmg.patchworks`, `femic.patchworks_runtime`, and
      `femic.workflows.legacy`.
    - [x] P24.1d.2 Add curated support-module pages for the remaining execution
      seams that still carry important repo/runtime contracts:
      `femic.instance_context`, `femic.instance_bootstrap`,
      `femic.geospatial_preflight`, `femic.pipeline.bundle`,
      `femic.pipeline.legacy_runtime`, and `femic.pipeline.manifest`.
    - [x] P24.1d.3 Run a closure sweep across the remaining autosummary-only API
      pages and classify each one as either:
      acceptable generated-only surface, or still-needs-curated-page.
    - [x] P24.1d.4 Promote any support modules from the closure sweep that still
      block comprehension of real maintenance tasks into one final curated docs
      pass, then update `docs/reference/api/modules.rst` and `docs/reference/api/index.rst`
      to reflect the bounded curated set explicitly.
    - [x] P24.1d.5 Mark `P24.1d` complete once every generated-only page left in
      the API tree is explicitly considered acceptable as generated-only or has
      been replaced by a curated narrative page.
  - [x] P24.1e Add examples and "how this fits into the pipeline" notes for the most important public entrypoints.
- [x] P24.2 Add a lightweight docs contract for coding-agent-friendly technical consumption
  - [x] P24.2a Define what agent-friendly documentation means for FEMIC without creating a totally separate parallel docs universe.
  - [x] P24.2b Add concise machine-friendly reference surfaces for repo invariants, runtime prerequisites, stage boundaries, canonical artifacts, and recovery workflows.
  - [x] P24.2c Make sure those surfaces are generated from or embedded in the same human-facing docs tree wherever practical, so they do not drift.
  - [x] P24.2d Add explicit "source of truth" pages for frequently confused seams (instance roots, external data roots, public-data/DataLad usage, BatchTIPSY boundary, Patchworks runtime assumptions).
- [x] P24.3 Establish doc architecture that serves both humans and embedded coding agents
  - [x] P24.3a Keep one primary documentation system, but introduce structured sub-surfaces for fast technical lookup (tables, contracts, checklists, invariants, file/path maps).
  - [x] P24.3b Decide where `AGENTS.md`, operator runbooks, API docs, and roadmap notes should cross-link so an agent can orient quickly without browsing the entire repo.
  - [x] P24.3c Add guidance for when detailed narrative is needed versus when a concise machine-readable contract is better.
- [x] P24.4 Validate the new docs system against real maintenance tasks
  - [x] P24.4a Use recent real tasks (Patchworks runtime setup, K3Z variant rebuilds, SiteProd defaults, DataLad bootstrap) as benchmark tasks and confirm the docs are enough to complete them without tribal knowledge.
  - [x] P24.4b Add docs acceptance checks for required API-doc sections and agent-facing contract pages.
  - [x] P24.4c Record a follow-up GitHub feature issue for any remaining agent-facing docs gaps that should be iterated outside this phase.

## Phase 25: K3Z Student Overlay RETENTION Subvariants
- [x] P25.1 Capture the student-overlay import/join contract and execution plan
  - [x] P25.1a Record the source/provenance handoff for the abandoned student GIS
    inventory, the repo-local `tmp/` import target, and the required join key
    contract (`FEATURE_ID` -> `FEATURE_ID`).
  - [x] P25.1b Verify the student layer carries the four alternative RETENTION
    fields (`basecase_riparian`, `basecase_sum`, `scenario1_sum`,
    `scenario2_sum`) and document expected null/join-coverage checks against
    the canonical K3Z fragments shapefile.
  - [x] P25.1c Define the planning/execution workflow in
    `planning/msfm-rec2group-k3z-overlay.md`, including the first-pass schema
    validation step for the uploaded student export in `tmp/`.
- [x] P25.2 Import and join the student GIS inventory to the canonical K3Z fragments
  - [x] P25.2a Materialize a repo-local copy of the student inventory under
    `tmp/` without depending on the abandoned fork at runtime.
  - [x] P25.2b Join the imported student layer to the actual K3Z instance
    fragments shapefile on `FEATURE_ID`.
  - [x] P25.2c Preserve only the four alternative RETENTION columns plus the
    key provenance fields needed to audit the overlay.
- [x] P25.3 Compile four baseline-derived K3Z Patchworks subvariants from the joined overlay
  - [x] P25.3a Treat the current baseline K3Z variant as the fixed starting
    point and create one subvariant per alternative RETENTION field.
  - [x] P25.3b Ensure each subvariant changes only fragment RETENTION / resulting
    unmanaged-vs-managed area balance, leaving all other baseline inputs and
    teaching assumptions unchanged.
  - [x] P25.3c Add explicit config/runtime/PIN naming so students can launch the
    overlay subvariants without ambiguity.
- [x] P25.4 Validate and document the overlay subvariant workflow
  - [x] P25.4a Add checks for join coverage, null RETENTION values, and expected
    managed/unmanaged area deltas across the four subvariants.
  - [x] P25.4b Update K3Z runbooks/student guidance so the overlay source,
    subvariant meanings, and launch workflow are auditable and repeatable.

## Phase 26: K3Z Variant Docs Upgrade + Parent Docs CI Repair
- [x] P26.1 Expand the canonical standalone K3Z docs for variants, subvariants, and old-growth semantics
  - [x] P26.1a Add dedicated standalone K3Z docs pages for variant/subvariant navigation, intensive-silviculture logic, and `og1` / `og2` semantics.
  - [x] P26.1b Update the existing standalone K3Z getting-started, model-anatomy, operator-runbook, rebuild/QA, and scenario pages so they summarize and link to the deeper variant/treatment/old-growth pages rather than holding fragmented partial detail.
  - [x] P26.1c Document the full K3Z runtime matrix for `base`, `ctfert`, `pctct`, and the four baseline-derived overlay subvariants (`basecase_riparian`, `basecase_sum`, `scenario1_sum`, `scenario2_sum`), including launch pairings, artifact families, intended teaching use, and expected account-surface consequences.
- [x] P26.2 Publish detailed treatment-logic and overlay provenance guidance
  - [x] P26.2a Document the exact `ctfert` treatment parameters, gating fields, sequencing, and assumptions from `config/silviculture.k3z.ctfert.yaml`, including CT/F1/F2/F3 timing and the retained low-yield strata policy.
  - [x] P26.2b Document the exact `pctct` treatment parameters, gating fields, sequencing, and assumptions from `config/silviculture.k3z.pctct.yaml`, including planted-only PCT, HW removal, and the `CC -> PCT -> CT` chain.
  - [x] P26.2c Record the student overlay provenance and join contract (`FEATURE_ID1` bridge, four workbook RETENTION columns, `blocks.shp` join path, and managed-species dropout behavior under high-retention overlays).
- [x] P26.3 Repair parent FEMIC docs Pages builds so clean-checkout Sphinx runs are reliable
  - [x] P26.3a Land the missing tracked `docs/reference/api/generated/*.rst` stubs referenced by the curated API pages so the parent docs build succeeds from a clean checkout, not just a warm working tree.
  - [x] P26.3b Add docs-contract coverage that fails when curated API pages reference untracked/nonexistent generated docs.
  - [x] P26.3c Refresh the lightweight parent `docs/sample-models/k3z.rst` pointer page so it explicitly routes readers to the standalone K3Z docs for variant selection, overlay subvariants, treatment sequencing, and old-growth semantics.

## Phase 27: K3Z `pctct` Species-Account Regression Fix
- [x] P27.1 Diagnose why `pctct` drops species-wise managed yield / harvested-volume accounts
  - [x] P27.1a Compare the `pctct` export/build path against baseline and `ctfert` from ForestModel XML through Matrix Builder outputs.
  - [x] P27.1b Identify the exact seam where the checked-in `pctct` surface collapsed from species-wise managed outputs to `product.Yield.managed.Total` / `feature.Yield.managed.Total` only.
- [x] P27.2 Restore species-wise managed surfaces for `pctct`
  - [x] P27.2a Refresh the checked-in K3Z `pctct` ForestModel/tracks surface from the current good species-wise export path and add a regression guard so stale `Total`-only artifacts cannot ship again.
  - [x] P27.2b Rebuild the checked-in K3Z `pctct` artifact surface (`forestmodel_pctct.xml`, `tracks_pctct`, and dependent tracked CSVs) so the instance matches the repaired logic.
- [x] P27.3 Validate and document the repair
  - [x] P27.3a Verify the repaired `pctct` surface in both compiled artifacts and live Patchworks expectations.
  - [x] P27.3b Update docs/runbooks only where operator-facing expectations materially change.

## Phase 28: K3Z `pctct` Expanded Treatment Eligibility
- [x] P28.1 Retarget the `pctct` eligible-AU set to the current Issue 14 cohort
  - [x] P28.1a Confirm the active Issue 14 AU cohort is the medium/high SI `HW+FDC` / `FDC+HW` set only (`985502000`, `985503000`, `985502001`, `985503001`) and that it stays compatible with the existing `PCT remove_species = HW` teaching logic without pulling in the known low-yield/full-retention strata.
  - [x] P28.1b Update the `pctct` silviculture config, regen/TIPSY assumptions, and checked-in compiled artifact surface so `PCT`/`CT` materialize only for the Issue 14 AU cohort.
- [x] P28.2 Refresh operator-facing K3Z guidance for the broader `pctct` footprint
  - [x] P28.2a Update the standalone K3Z docs anywhere they currently say the `pctct` path is limited to the original two eligible AUs or otherwise point at the wrong AU cohort.
  - [x] P28.2b Keep the rebuild/runbook contract explicit about what should now appear in `forestmodel_pctct.xml` and `tracks_pctct`, and record separately that Issue 14's requested light/moderate/heavy PCT intensity knob is not yet representable in the current single-path `pctct` model surface.
- [x] P28.3 Validate the broader `pctct` surface
  - [x] P28.3a Re-run focused validation that proves the expanded AU set appears in the checked-in `pctct` ForestModel/tracks artifacts without regressing the `PCT -> CT` chain.
  - [x] P28.3b Run the required parent-repo quality gates that are practical from this checkout and record any remaining blocked validation separately if local runtime prerequisites prevent a full `tracks_pctct` rebuild.

## Phase 29: K3Z `pctct` Multi-Intensity PCT Paths
- [x] P29.1 Teach parent FEMIC to compile multiple coexisting PCT paths in one variant
  - [x] P29.1a Extend the silviculture config / export logic so `pre_commercial_thinning` can describe multiple labeled PCT treatments, each with its own post-PCT state and per-species stem-removal target.
  - [x] P29.1b Generate matching post-PCT species-proportion / yield surfaces and CT follow-on states for each configured PCT treatment without regressing the existing `PCT -> CT` chain.
- [x] P29.2 Rebuild K3Z `pctct` around light/moderate/heavy PCT choices
  - [x] P29.2a Update the K3Z `pctct` silviculture config so the same four Issue 14 AUs expose three age-10 PCT treatments: remove `1000`, `2000`, and `3000` stems/ha of `HW`.
  - [x] P29.2b Refresh the K3Z PIN/docs/runtime surface so the three PCT flavors are distinguishable in Patchworks and in the standalone operator docs.
- [x] P29.3 Validate the coexisting multi-intensity surface
  - [x] P29.3a Add/refresh parent regression coverage for the new multi-PCT export behavior.
  - [x] P29.3b Rebuild the checked-in K3Z `pctct` ForestModel/tracks surface and rerun local matrix-build / QA checks so the variant is ready for live testing.

## Phase 30: K3Z `pctct` Split Into Single-Intensity Subvariants
- [x] P30.1 Replace the stacked `pctct` teaching surface with three simpler subvariants
  - [x] P30.1a Define explicit `pctct_light`, `pctct_moderate`, and `pctct_heavy` runtime/variant/PIN/build surfaces so each subvariant carries only one age-10 `PCT` flavor ahead of `CT`.
  - [x] P30.1b Revert the K3Z silviculture/docs/contracts from the coexisting `PCT_LIGHT` / `PCT_MODERATE` / `PCT_HEAVY` surface to three separate single-`PCT` subvariant surfaces, each still scoped to Issue 14's four eligible AUs.
- [x] P30.2 Rebuild and validate the three single-intensity `pctct` subvariants
  - [x] P30.2a Regenerate each checked-in ForestModel/tracks/output surface (`light`, `moderate`, `heavy`) and confirm each preserves the accepted 218-fragment baseline geometry footprint.
  - [x] P30.2b Run focused matrix-build/account-surface/docs/QA checks on all three subvariants so the user can test them directly in Patchworks without relying on the stacked-treatment path.

## Phase 31: K3Z PCT-Only Subvariants
- [x] P31.1 Replace the `pctct_*` family with PCT-only `pct_*` subvariants
  - [x] P31.1a Rename the K3Z variant/runtime/PIN/silviculture/build surfaces from `pctct_light`, `pctct_moderate`, and `pctct_heavy` to `pct_light`, `pct_moderate`, and `pct_heavy`.
  - [x] P31.1b Remove the `commercial_thinning` leg from those subvariants so the treatment path stops at `cc_pl_pct` and no `CT` products/states remain in the PCT-only family.
- [x] P31.2 Rebuild the checked-in K3Z PCT-only artifact surface
  - [x] P31.2a Regenerate `forestmodel_pct_*.xml`, `tracks_pct_*`, and `output/patchworks_k3z_pct_*_validated` against the accepted baseline fragments geometry.
  - [x] P31.2b Refresh the PCT-only PINs and any runtime/build metadata so Patchworks launch pairings follow the renamed `pct_*` family cleanly.
- [x] P31.3 Reconcile docs, contracts, and issue tracking with the PCT-only scope
  - [x] P31.3a Update parent/K3Z docs and tests to remove `PCT -> CT` wording, remove retired `pctct_*` references, and describe the new PCT-only launch matrix.
  - [x] P31.3b Run the required validation gates, append the progress summary to `CHANGE_LOG.md`, and post the implementation status back to GitHub issue 14.
  - [x] P31.3c Add the explicit issue-closeout note naming the doc locations, closure rationale, and non-blocking rebuild caveat; then close GitHub issue 14.

## Phase 32: K3Z TIPSY-vs-VDYP Plot Docs Integration
- [x] P32.1 Audit the current K3Z docs and plot artifacts for TIPSY-vs-VDYP coverage
  - [x] P32.1a Identify the authoritative existing plot files, where they are generated, and which doc pages should surface them for students.
  - [x] P32.1b Confirm whether the right delivery shape is direct embedding in the standalone K3Z Sphinx docs, a gallery/index page, or both.
- [x] P32.2 Integrate the comparison plots into the user-facing K3Z docs
  - [x] P32.2a Add or update the relevant K3Z Sphinx pages so students can find and interpret the TIPSY-vs-VDYP yield-curve plots without leaving the docs.
  - [x] P32.2b Ensure figure paths/build rules are stable for the checked-in docs surface and update any supporting captions/runbook text.
- [x] P32.3 Validate the docs build and reconcile issue tracking
  - [x] P32.3a Run the required K3Z/parent docs checks for the changed pages.
  - [x] P32.3b Append the progress summary to `CHANGE_LOG.md` and update GitHub issue 13 with an implementation/closeout note as appropriate.

## Phase 33: K3Z True-TIPSY Plot Provenance Correction
- [x] P33.1 Verify and regenerate the current K3Z comparison plot artifacts
  - [x] P33.1a Re-run the K3Z post-TIPSY plotting path against the accepted cached inputs and confirm what legends/series the current pipeline actually emits.
  - [x] P33.1b Compare the regenerated overlays against the currently checked-in `plots/tipsy_vdyp_tsak3z-*.png` set and identify whether the repository is carrying stale scaled-VDYP artifacts.
- [x] P33.2 Reconcile docs and tracked plots with the verified true-TIPSY baseline
  - [x] P33.2a Replace or withdraw any student-facing docs surface that points at stale comparison figures.
  - [x] P33.2b Update standalone K3Z docs, roadmap/changelog, and GitHub issue tracking so the plot provenance is explicit and no scaled-VDYP confusion remains.
- [x] P33.3 Validate the corrective fix
  - [x] P33.3a Run the required K3Z docs build and any parent gates touched by the corrective change.
  - [x] P33.3b Post the verification/closeout note back to GitHub issue 17.
- [x] P33.4 Repair deeper managed-curve artifact provenance
  - [x] P33.4a Trace whether the tracked managed-curve CSV and model-input bundle curve tables still derive from the old scaled-VDYP synthesis path.
  - [x] P33.4b Regenerate any contaminated tracked managed-curve artifacts from raw `data/04_output-tsak3z.out` and update dependent docs/history accordingly.
  - [x] P33.4c Run the affected validation/gates again and reconcile GitHub issue 17 with the deeper artifact-lineage result.

## Phase 34: Human-Readable AU Labels in Patchworks Surfaces
- [x] P34.1 Replace numeric AU labels in Patchworks-facing account surfaces
  - [x] P34.1a Add a deterministic human-readable AU label helper derived from `stratum_code` + `si_level`.
  - [x] P34.1b Use that helper in Patchworks/ForestModel attribute labels that currently expose raw numeric AU ids in user-facing account names.
- [x] P34.2 Propagate human-readable AU labels into adjacent ForestModel naming surfaces
  - [x] P34.2a Replace raw numeric AU tokens in generated curve ids / related readable XML ids where practical without breaking internal references.
  - [x] P34.2b Preserve numeric AU ids only where they are required for joins/select statements or other internal model semantics.
- [x] P34.3 Update validation/docs/tests for the new naming policy
  - [x] P34.3a Update regression tests and account-surface parsing to recognize human-readable AU labels.
  - [x] P34.3b Document the naming format in the relevant user/developer docs and reconcile GitHub issue #2 with the implementation status.

## Phase 35: Correct Human-Readable AU Labels in Shipped K3Z Runtime Artifacts
- [x] P35.1 Regenerate the tracked K3Z ForestModel XML family with readable AU labels
  - [x] P35.1a Rebuild `forestmodel.xml`, `forestmodel_ctfert.xml`, and the `forestmodel_pct_*` family from the updated exporter.
  - [x] P35.1b Verify the regenerated XMLs no longer expose numeric AU labels like `feature.Area.og1.985501000`.
- [x] P35.2 Validate the actual runtime launch surfaces
  - [x] P35.2a Confirm the active `analysis/*.pin` launch path resolves the regenerated readable labels in the shipped runtime outputs.
  - [x] P35.2b Rerun Matrix Builder for the active K3Z runtime variants to ensure the corrected XML family is valid end-to-end.
- [x] P35.3 Reconcile repo narrative and GitHub issue status
  - [x] P35.3a Update docs/CHANGE_LOG/issue #2 with the corrective rollout details and validation evidence.
  - [ ] P35.3b Close issue #2 only after the tracked runtime artifacts are verified, merged, and the closeout note explains the original gap and the repair.

## Phase 36: K3Z CT/Fert SI-Class Expansion and Response-Profile Subvariants
- [x] P36.1 Expand the CT/fert eligible-AU cohort from medium-only to low/medium/high SI classes
  - [x] P36.1a Confirm the six target AUs covering the `L/M/H` SI classes of the `FDC+HW` and `CW+HW` strata.
  - [x] P36.1b Preserve the current single CT treatment parameters while extending the eligible-AU wiring.
- [x] P36.2 Add two SI-specific CT/fert response-profile subvariants
  - [x] P36.2a Compile one subvariant with fert boosts `L=15%`, `M=10%`, `H=5%`.
  - [x] P36.2b Compile one subvariant with fert boosts `L=20%`, `M=10%`, and no fert enabled on `H` SI AUs.
- [x] P36.3 Overlay the curated CT/fert RETENTION surface onto both new subvariants
  - [x] P36.3a Load `RETENTION` values from `tmp/CTFert Fragments/fragments_updated3_Usedinbasecase.shp` and apply them to both new CT/fert subvariant fragment surfaces.
  - [x] P36.3b Replace the current placeholder `0.05` retention values with the curated overlay values before final Matrix Builder validation.
- [x] P36.4 Rebuild K3Z runtime surfaces and close out the tracker
  - [x] P36.4a Regenerate XML/tracks/runtime/PIN/docs surfaces for the new subvariants and validate them with Matrix Builder.
  - [x] P36.4b Update GitHub issue #21, docs, roadmap, and changelog with the final subvariant semantics, RETENTION overlay provenance, and validation results.
- [x] P36.5 Add configurable CT post-thinning final-felling gap control
  - [x] P36.5a Add a commercial-thinning YAML knob that controls how much of the CT removal remains as a final-felling volume gap by `cmai_argmax`, with `1.0` preserving the current full-gap behavior and `0.0` closing the gap entirely by `cmai_argmax`.
  - [x] P36.5b Rebuild `ctfert_l15h5` and `ctfert_l20h0` with the new CT gap control set to `0.0`, then rerun Matrix Builder and the standard validation gates.
- [x] P36.6 Thin K3Z VDYP-derived XML yield curves to decadal knots
  - [x] P36.6a Thin unmanaged/VDYP total-yield curves to one point per 10 years in the exporter while preserving boundary points.
  - [x] P36.6b Regenerate the shipped K3Z ForestModel XML family from the updated exporter and rerun the relevant Matrix Builder checks.
- [x] P36.7 Retire the legacy single-surface `ctfert` launch path
  - [x] P36.7a Remove the superseded `ctfert` config, PIN, XML, tracks, and validated-output surfaces so only the SI-profile `ctfert_*` family remains active.
  - [x] P36.7b Update docs/tests/contracts to document the curated RETENTION overlay provenance and prevent the retired legacy `ctfert` alias from returning unnoticed.

## Phase 37: Upgrade K3Z Placeholder QMD Curves (Issue #22)
- [x] P37.1 Audit the accepted QMD input surface and current placeholder logic
  - [x] P37.1a Trace the current QMD exporter path in `src/femic/fmg/patchworks.py` and document exactly which managed/unmanaged curve inputs it consumes today.
  - [x] P37.1b Confirm the accepted K3Z inputs available for stand yield, site index, and trees per hectare from the BatchTIPSY and VDYP artifact surfaces.
- [x] P37.2 Replace the placeholder age-heuristic QMD builder with a reverse-engineered approximation
  - [x] P37.2a Derive unmanaged and managed baseline QMD curves from accepted stand yield, a linear height-by-site-index assumption, and trees-per-hectare inputs.
  - [x] P37.2b Preserve the existing CT/fert QMD response wiring, but rebase it onto the rebuilt baseline QMD curves instead of the current hand-tuned placeholder formula.
- [x] P37.3 Rebuild and validate the shipped K3Z runtime surfaces
  - [x] P37.3a Regenerate the affected K3Z ForestModel XML family and rerun Matrix Builder on the active CT/fert `ctfert_l15h5` and `ctfert_l20h0` variants.
  - [x] P37.3b Update docs/CHANGE_LOG/issue #22 with the approximation details, validation evidence, and any remaining caveats.
- [x] P37.4 Normalize AU-wise QMD accounts to mean-diameter units
  - [x] P37.4a Compute AU-wise managed and unmanaged area denominators from the
    active validated fragments surface plus `RETENTION` values.
  - [x] P37.4b Replace the default `SUM=1` multipliers on the AU-wise
    `feature.QMD.{managed,unmanaged}.*` account rows so the compiled
    `accounts.csv` reports mean QMD in `cm` rather than `cm*ha`.
  - [x] P37.4c Rebuild the active CT/fert tracks and validate the normalized
    QMD account surface end-to-end.

## Phase 38: Audit and Repair K3Z PCT Treatment Age-Retention Semantics
- [x] P38.1 Confirm whether the active K3Z `pct_*` subvariants still reset stand age after PCT
  - [x] P38.1a Inspect the generated `forestmodel_pct_light.xml`, `forestmodel_pct_moderate.xml`, and `forestmodel_pct_heavy.xml` treatment definitions for the same age-retention omission previously found in the CT/fert family.
  - [x] P38.1b Verify the compiled `tracks_pct_* / treatments.csv` surfaces and live Patchworks behavior to confirm whether the suspected absolute-offset reset bug is real.
- [x] P38.2 Apply the PCT treatment-age retention fix if needed
  - [x] P38.2a Update the exporter so PCT treatments retain stand age after treatment using the same corrected Patchworks treatment attribute semantics used for CT/fert.
  - [x] P38.2b Regenerate the affected K3Z `forestmodel_pct_*` XML family and rebuild the shipped `tracks_pct_*` surfaces.
- [x] P38.3 Revalidate and close out the bug
  - [x] P38.3a Rerun Matrix Builder for `pct_light`, `pct_moderate`, and `pct_heavy`, plus any targeted live Patchworks checks needed to confirm the repair.
  - [x] P38.3b Update docs/CHANGE_LOG/GitHub issue #25 with the final repair details, validation evidence, and closeout rationale.

## Phase 39: Adopt GitHub Issue Type as FEMIC's Canonical Work-Kind Classifier
- [x] P39.1 Publish the FEMIC issue metadata policy in repo maintainer docs
  - [x] P39.1a Record that GitHub built-in `Type` is the canonical work-kind field using `Bug`, `Feature`, and `Task`.
  - [x] P39.1b Record the small orthogonal label set that remains valid after the transition.
- [x] P39.2 Normalize the live FEMIC GitHub label surface
  - [x] P39.2a Add the orthogonal labels needed for current workflow coverage: `windows`, `k3z`, `tsa29`, `patchworks`, and `data`.
  - [x] P39.2b Retire duplicate work-kind labels from active use, specifically `bug` and `enhancement`, once the open issue set has been backfilled with `Type`.
- [x] P39.3 Backfill `Type` and orthogonal labels onto the open issue set
  - [x] P39.3a Set built-in `Type` on the open FEMIC issue set, starting with `#11 -> Bug`, `#10 -> Task`, `#8 -> Task`, `#27 -> Feature`, and the governing rollout tracker `#28 -> Task`.
  - [x] P39.3b Apply orthogonal labels only where they add domain or platform information, e.g. `windows`, `k3z`, `tsa29`, `patchworks`, `data`, and existing `documentation`.
- [x] P39.4 Validate the new issue-metadata workflow and close out the tracker
  - [x] P39.4a Confirm the repo can now answer `type:` and label-based queries cleanly without duplicate work-kind labels.
  - [x] P39.4b Update `CHANGE_LOG.md` and GitHub issue `#28` with the completed rollout details and closeout rationale.

## Phase 40: Add Harvested-Stem QMD Product Accounts to K3Z CT/Fert
- [x] P40.1 Audit the current product-account export and runtime promotion path
  - [x] P40.1a Trace how `product.*` labels and curves are exported for the active K3Z CT/fert family in `src/femic/fmg/patchworks.py`.
  - [x] P40.1b Trace how `protoaccounts.csv -> accounts.csv` promotion currently handles `product` rows in `src/femic/patchworks_runtime.py`.
- [x] P40.2 Add harvested-stem QMD product accounts for the active K3Z CT/fert family
  - [x] P40.2a Define a naming contract for harvested-stem QMD `product` accounts that remains clearly distinct from the existing standing-stock `feature.QMD.*` surfaces.
  - [x] P40.2b Export harvested-stem QMD product rows for `ctfert_l15h5` and `ctfert_l20h0` by AU and treatment type.
- [x] P40.3 Validate the harvested-stem QMD product-account surface
  - [x] P40.3a Add the matching AU/treatment treated-area companion rows needed to recover mean harvested diameter from the event-level QMD numerator surfaces.
  - [x] P40.3b Regenerate the shipped `tracks_ctfert_l15h5/` and `tracks_ctfert_l20h0/` account surfaces and verify the new rows appear cleanly.
- [x] P40.4 Add regression coverage and document the new CT/fert pilot surface
  - [x] P40.4a Add tests covering the exporter/runtime logic and the shipped account names.
  - [x] P40.4b Update docs, `CHANGE_LOG.md`, and GitHub issue #27 with the CT/fert pilot implementation details and the follow-on porting plan.
  - [x] P40.4c Correct the CT/fert pilot to use live Patchworks RatioAccounts for harvested mean QMD.
    - [x] P40.4c.i Rename the shipped harvested-QMD export rows to an internal numerator surface so the public `product.QMD.*` names are no longer raw area-weighted totals.
    - [x] P40.4c.ii Add a BeanShell helper on the active `ctfert_*` launch surfaces that registers `product.QMD.*` as `control.addRatioAccount(...)` meta accounts with scale `1`.
    - [x] P40.4c.iii Rebuild the active `ctfert_*` tracks and update the docs/tests so they describe `product.QMD.*` as runtime ratio accounts rather than direct checked-in `accounts.csv` rows.
- [x] P40.5 Port the harvested-stem QMD product-account logic across the remaining active K3Z variants
  - [x] P40.5a Decide which non-CT/fert variants should expose AU-wise harvested-stem QMD product rows and whether they need explicit opt-in config flags.
  - [x] P40.5b Extend the validated account/docs surface beyond `ctfert_*` only after the CT/fert pilot contract has been accepted.

## Phase 41: Add K3Z Harvest Utilization Factors for Recovered Merchantable Volume
- [x] P41.1 Audit the downstream harvested-volume account promotion path
  - [x] P41.1a Trace where `protoaccounts.csv -> accounts.csv` promotion already rewrites `SUM` multipliers so utilization can be applied without altering XML curves.
  - [x] P41.1b Confirm which harvested-volume account names should receive treatment-specific utilization scaling across the active K3Z variants.
- [x] P41.2 Apply treatment-specific utilization factors in the account-promotion layer
  - [x] P41.2a Add runtime-config support for harvested-volume utilization factors by treatment type.
  - [x] P41.2b Apply `CC = 0.85` and `CT = 0.75` to the active K3Z runtime surfaces while leaving standing yield curves and fragment-level `RETENTION` untouched.
- [x] P41.3 Revalidate, document, and close out the utilization change
  - [x] P41.3a Rerun the relevant K3Z validation steps, including account-surface checks and any targeted live checks needed to confirm the recovered-volume contract.
  - [x] P41.3b Update user-facing docs, `CHANGE_LOG.md`, and GitHub issue #31 with the final utilization-factor behavior and validation results.

## Phase 42: Add Stems-Per-Ha Curves, Attributes, and Accounts to Active K3Z Variants
- [x] P42.1 Audit current stems-per-ha source data and exporter seams
  - [x] P42.1a Trace the best available managed and unmanaged stems-per-ha
    support data already present in the K3Z handoff artifacts and
    `src/femic/fmg/adapters.py`.
  - [x] P42.1b Confirm where the Patchworks exporter should bind standing
    stems-per-ha feature surfaces without colliding with the existing yield,
    harvested-volume, and QMD account contracts.
- [x] P42.2 Define and implement the standing stems-per-ha account contract
  - [x] P42.2a Add AU-wise `feature.StemsPerHa.managed.<au_token>` and
    `feature.StemsPerHa.unmanaged.<au_token>` surfaces for the active K3Z
    variants.
  - [x] P42.2b Extend the shipped baseline, CT/fert, PCT, and overlay K3Z
    tracks/account surfaces so downstream users get the new rows from `main`.
- [x] P42.3 Validate and document the stems-per-ha rollout
  - [x] P42.3a Add regression coverage for the exporter/runtime/account-surface
    changes.
  - [x] P42.3b Update user-facing K3Z docs, `CHANGE_LOG.md`, and GitHub issue
    #33 with source provenance, meaning, and validation results.

## Phase 43: Add a K3Z Variant with the Full Intensive Silviculture Chain
- [x] P43.1 Design the combined treatment-path contract before implementation
  - [x] P43.1a Audit the accepted `pct_*` and `ctfert_*` state chains, AU
    coverage, and timing rules so the new variant can reuse the existing
    teaching assumptions where they already work.
  - [x] P43.1b Decide the canonical combined-state naming contract and
    treatment order for the new surface, including how `PCT`, `CT`, `F1`,
    `F2`, and `F3` compose on planted stands.
  - [x] P43.1c Decide whether the combined surface should ship as one profile
    or as a small family of subvariants if current SI-profile or PCT-intensity
    choices cannot be collapsed cleanly.
- [x] P43.2 Implement the combined intensive-silviculture variant surface
  - [x] P43.2a Add the required K3Z silviculture/runtime/PIN config surfaces
    for the new combined variant family.
  - [x] P43.2b Extend the exporter/runtime logic only as needed to support the
    chosen combined treatment chain without regressing the existing `pct_*` and
    `ctfert_*` families.
  - [x] P43.2c Rebuild the shipped ForestModel XML, tracks, and validated
    fragment outputs for the new surface.
- [x] P43.3 Validate, document, and close out the new intensive-silviculture surface
  - [x] P43.3a Run the normal K3Z validation gates and Matrix Builder rebuilds
    for the new surface.
  - [x] P43.3b Update the standalone K3Z docs, `CHANGE_LOG.md`, and GitHub
    issue #36 with the final launch contract and validation results.

## Phase 44: Add Stem Height Curves, Attributes, and Accounts to K3Z
- [x] P44.1 Define the K3Z stem-height account contract before implementation
  - [x] P44.1a Audit the currently available height support data on the managed
    and unmanaged sides so the new standing-height surfaces reuse accepted
    inputs instead of inventing a parallel approximation path unnecessarily.
  - [x] P44.1b Decide the AU-wise naming contract for standing stem-height
    attributes and downstream accounts so it stays parallel to the current QMD
    and stems-per-ha families.
  - [x] P44.1c Decide how treatment-state height should behave on the `ctfert_*`,
    `intensive_*`, and `pct_*` families, including which state transitions
    should carry height forward unchanged versus reusing a treatment-adjusted
    surface.
- [x] P44.2 Implement stem-height support across the active K3Z family
  - [x] P44.2a Extend the exporter/runtime logic to emit AU-wise stem-height
    feature attributes and normalized downstream accounts.
  - [x] P44.2b Rebuild the shipped K3Z XML/tracks/account surfaces for the
    active launch families that should expose the new accounts.
  - [x] P44.2c Add regression coverage for the new height-account contract in
    both exporter/runtime tests and docs-contract checks.
- [x] P44.3 Validate, document, and close out the K3Z stem-height rollout
  - [x] P44.3a Run the normal validation gates plus representative K3Z Matrix
    Builder/account-surface checks.
  - [x] P44.3b Update standalone K3Z docs, `CHANGE_LOG.md`, and GitHub issue
    #38 with the final contract and validation results.

## Phase 45: Normalize K3Z ForestModel XML Location Beside Validated Fragments
- [x] P45.1 Make the variant-local `output/.../forestmodel.xml` files the canonical K3Z runtime XMLs
  - [x] P45.1a Audit the current baseline, overlay, `pct_*`, `ctfert_*`, and
    `intensive_*` runtime configs and docs to identify every remaining
    reference to `models/k3z_patchworks_model/yield/*.xml`.
  - [x] P45.1b Update the K3Z runtime configs so each variant points to the
    `forestmodel.xml` file living beside its matching validated fragments
    surface under `output/patchworks_k3z*_validated/`.
  - [x] P45.1c Remove the stale duplicate `models/k3z_patchworks_model/yield/*.xml`
    family once all K3Z runtime references have been redirected.
- [x] P45.2 Rebuild and validate the K3Z runtime package layout after the XML move
  - [x] P45.2a Run representative Matrix Builder rebuilds against the new
    output-local XML/fragments pairings.
  - [x] P45.2b Run representative account-surface checks to confirm the runtime
    path cleanup does not change the compiled K3Z account contract.
- [x] P45.3 Document and close out the K3Z package-layout normalization
  - [x] P45.3a Update the standalone K3Z docs and parent docs so users are told
    unambiguously which XML/fragments pair belongs together for Matrix Builder
    rebuilds.
  - [x] P45.3b Update `CHANGE_LOG.md` and GitHub issue #40 with the final path
    contract and validation results.

## Phase 46: Add VS Code and Coding-Agent Onboarding Guide
- [x] P46.1 Define the scope and contract for the onboarding guide
  - [x] P46.1a Decide where the new guide should live in the parent Sphinx docs
    tree and how it should be linked from the current onboarding/developer
    entry points.
  - [x] P46.1b Write down the minimum environment-setup contract for a new
    contributor using VS Code plus a local coding agent in this repo.
  - [x] P46.1c Define the human/agent collaboration guidance that should be
    taught explicitly, including prompt hygiene, planning expectations,
    validation expectations, and supervision responsibilities.
- [x] P46.2 Author the new onboarding guide and integrate it into the docs tree
  - [x] P46.2a Add the new Sphinx guide page with FEMIC-specific setup
    instructions for a local VS Code plus coding-agent workflow.
  - [x] P46.2b Link the guide from the relevant parent docs pages so new users
    can discover it from normal onboarding entry points.
  - [x] P46.2c Keep the first pass FEMIC-specific, but note where the approach
    could later generalize into a broader reusable template for similar FRESH
    lab projects.
- [x] P46.3 Validate and close out the onboarding-docs addition
  - [x] P46.3a Run parent docs validation and any related docs-contract checks.
  - [x] P46.3b Update `CHANGE_LOG.md` and GitHub issue #42 with the final docs
    scope, guidance areas, and validation outcome.

## Phase 47: Automate Matrix Builder Window Closure In Local Windows Workflow
- [x] P47.1 Trace the current Windows Matrix Builder launch seam and define the
  automation contract
  - [x] P47.1a Confirm exactly where the parent runtime launches Matrix Builder
    on native Windows and how it currently decides success/failure.
  - [x] P47.1b Decide the minimum safe closure contract for the GUI window so
    automation does not hide real Patchworks failures or interfere with
    unrelated user windows.
  - [x] P47.1c Decide whether the automation should be always-on for native
    Windows matrix-build runs or behind an explicit runtime config knob.
- [x] P47.2 Implement supervised Windows Matrix Builder execution
  - [x] P47.2a Replace the simple blocking Windows `subprocess.run(...)` path
    with a supervised launch path that can detect the spawned Matrix Builder
    process/window and observe output-directory readiness.
  - [x] P47.2b Add the narrowest possible Windows-only close/terminate
    automation so the local coding-agent workflow can finish without a human
    manually dismissing the Matrix Builder window.
  - [x] P47.2c Preserve run logs, manifest evidence, and explicit failure
    reporting so a closed window is not mistaken for a successful build.
- [x] P47.3 Validate, document, and close out the workflow automation
  - [x] P47.3a Add targeted runtime tests for the supervised Windows launch and
    auto-close behavior.
  - [x] P47.3b Update operator/onboarding docs so users know the new Windows
    matrix-build behavior and any caveats.
  - [x] P47.3c Update `CHANGE_LOG.md` and GitHub issue #44 with the final
    behavior, validation outcome, and any remaining limitations.

## Phase 48: Investigate And Automate BatchTIPSY In Local Windows Workflow
- [x] P48.1 Replace the legacy DAT/OUT BatchTIPSY seam with the BTC MSYT CSV seam
  - [x] P48.1a Confirm the supported Windows BTC CLI contract around
    `TIPSYbtc.exe /TSR <input_csv> <output_csv> <error_csv>`, including
    executable discovery, working-directory expectations, and manifest-worthy
    runtime details.
  - [x] P48.1b Treat `C:\Program Files\TIPSY 4.7\BTC\Samples\MSYT.csv` as the
    first reference schema for the new canonical Stage 01a handoff artifact.
  - [x] P48.1c Broaden the post-TIPSY contract so FEMIC consumes returned BTC
    CSV outputs directly instead of assuming legacy fixed-width `.out` output.
- [x] P48.2 Implement the first credible end-to-end BTC CSV slice
  - [x] P48.2a Add deterministic Stage 01a BTC `MSYT.csv` input generation from
    the existing TIPSY payload, replacing the old DAT handoff as the active
    supported workflow.
  - [x] P48.2b Add Windows BTC executable discovery and a supervised CLI runner
    around `TIPSYbtc.exe /TSR`, including:
  - [x] P48.2c Add post-TIPSY parsing for returned BTC CSV outputs, including a
    clear replacement plan for old `.out`-era support fields such as `TPH` and
    `DBHq` when richer non-GUI BTC outputs are not yet proven.
  - [ ] P48.2d If richer indicator output remains GUI-only, support it as an
    optional manual BTC mode instead of blocking the default unattended
    `/TSR` mashup rollout.
    - [x] P48.2d1 Add a stand-table indicator bank from BTC bindings and wire
      DBH-class stem counts behind a FEMIC-level optional activation switch,
      piloting first on a dedicated K3Z intensive-silviculture proving-ground
      subvariant rather than modifying the active student-facing variants.
      Current status:
    - [ ] P48.2d2 Add the remaining optional BTC/TIPSY indicators in logical
      banks and wire those behind FEMIC-level optional activation switches,
      again piloting first on dedicated K3Z intensive-silviculture
      proving-ground subvariants rather than the active student-facing
      variants. Track on GitHub issue #48.
    - [x] P48.2d3 Revisit the current K3Z QMD curves and either:
  - [x] P48.2e Add a FEMIC-side BTC custom-report template generator so vetted
    `.rpt` files can be authored from curated or user-specified output-column
    lists instead of hand-edited inside the BTC GUI.
- [x] P48.3 Validate, document, and close out the cutover
  - [x] P48.3a Add tests for BTC executable discovery, MSYT CSV writing, CLI
    argument assembly, and returned BTC CSV parsing.
  - [x] P48.3b Update operator/docs/contracts to describe BTC `MSYT.csv` input,
    BTC CLI `/TSR`, returned CSV outputs, and any remaining gaps in richer
    stock-level indicator support.
  - [x] P48.3c Reconcile the repo narrative and GitHub tracker state now that
    the landed BTC CSV seam, optional-bank rollout, and cutover closeout notes
    live across issues `#48`, `#49`, and `#56`.
  - [x] P48.3d Perform a full deep-dive audit of the installed
    `C:\Program Files\TIPSY 4.7\` tree as part of the ongoing BTC seam
    reverse-engineering effort, including:
- [x] P48.4 Archive extracted installed-help trees for future reverse-engineering
  - [x] P48.4a Use the working short-path `hh.exe -decompile` workaround to
    extract every installed `.chm` under `C:\Program Files\TIPSY 4.7\`.
  - [x] P48.4b Stage the extracted help trees into a tracked repo reference
    location with provenance notes and lightweight indexing.
  - [x] P48.4c Update planning/docs/changelog/GitHub tracking so the archived
    help corpus becomes part of FEMIC's durable TIPSY reverse-engineering
    reference set.
- [x] P48.5 Reverse-engineer the undocumented BTC `/No_GUI` seam
  - [x] P48.5a Probe the installed BTC executable with a real saved `.btc`
    project and compare:
  - [x] P48.5b Record concrete runtime evidence:
  - [x] P48.5c Update planning/docs/changelog/GitHub tracking with the proven
    seam or a blocker map if `/No_GUI` remains under-documented after probing.
- [ ] P48.6 Investigate BTC-to-FAN$IER linkage seams
  - [x] P48.6a Mine the extracted FAN$IER help corpus and adjacent BTC/TIPSY
    docs for concrete handoff artifacts:
  - [x] P48.6b Inspect the installed BTC/FAN$IER runtime surface for file
    formats, sample assets, and CLI or batch clues that refine the likely
    FEMIC handoff contract.
  - [ ] P48.6c Record a concrete linkage map:

- [x] P48.7 Triage and repair the post-cutover K3Z QMD regression
  - [x] P48.7a Reproduce the current K3Z launch-time symptom on the shipped
    `base` and `ctfert_l15h5` surfaces, and confirm whether the empty values
    affect:
  - [x] P48.7b Trace the failure upstream from Patchworks accounts through:
  - [x] P48.7c Repair the broken QMD path without perturbing the other active
    K3Z variants unnecessarily, then rebuild and validate the affected K3Z
    surfaces.

## Phase 49: Add a Headless Patchworks Runner and Scenario Orchestration Layer
- [ ] P49 Add a headless Patchworks runner and scenario orchestration layer
  - [x] P49.1 Confirm and document the real no-GUI Patchworks seam from the
    shipped BeanShell/runtime surfaces and local API docs.
  - [x] P49.2 Add a FEMIC-side headless Patchworks runner API/CLI that can:
  - [x] P49.3 Add a first proving-ground scenario-definition path so FEMIC can
    inject run parameters and report destinations into a generated BeanShell
    control script instead of depending on manual Patchworks interaction.
  - [x] P49.4 Prove the full lifecycle on a representative K3Z proving-ground
    surface by:
  - [x] P49.5 Add a registry-backed Patchworks variant launch surface on top of
    the proven headless runner.
  - [x] P49.6 Reconcile Sphinx docs for BTC, FAN$IER, and Patchworks
    operator/runtime surfaces.
  - [x] P49.7 Add packaged-install built-in instance install and user
    workspace-root management.
  - [x] P49.8 Adopt Forest Estate Modelling Integration Core as the FEMIC
    expansion.

## Phase 50: Restore Dropped Species-Wise K3Z Yield / Harvest-Volume Accounts
- [x] P50.1 Repair the K3Z species-universe source contract in post-TIPSY bundle assembly
  - [x] P50.1a Confirm and fix the current fallback seam in `_load_species_universe_for_tsas(...)` so the active K3Z instance can recover species-universe input from shipped checkpoint artifacts instead of depending only on `checkpoint8`.
  - [x] P50.1b Restore `treated_species_prop_*` / `untreated_species_prop_*` bundle curves for the current K3Z data package.
- [x] P50.2 Rebuild the affected active K3Z Patchworks surfaces
  - [x] P50.2a Regenerate the affected K3Z ForestModel XML family from the repaired species-proportion bundle path.
  - [x] P50.2b Rerun Matrix Builder for the active K3Z family so checked-in `tracks/*` surfaces once again carry species-wise managed yield / harvested-volume accounts.
- [x] P50.3 Validate and close the regression
  - [x] P50.3a Re-run representative `femic instance account-surface` checks for baseline, one `ctfert_*`, and one `pct_*` surface to confirm the `total OK, species-wise empty` diagnosis is gone.
  - [x] P50.3b Run a harvest-producing Patchworks smoke and directly inspect saved runtime outputs to confirm species-wise harvested product volume is observable in live scenario artifacts.
  - [x] P50.3c Update `CHANGE_LOG.md`, K3Z troubleshooting/operator docs, and GitHub issue `#64` with the repaired contract and validation evidence.

## Phase 51: Add BTC Log-Grade Harvested Product Families to K3Z CTFert Variants
- [x] P51.1 Add the narrow CC-only log-grade exporter surface for the two ctfert variants
  - [x] P51.1a Use the existing shipped BTC `log-grades` bank as the upstream source and emit new harvested product/account families for `Logs_Grade_{D,F,H,I,J,U,X,Y,All}`.
  - [x] P51.1b Keep the rollout scoped to `ctfert_l15h5` and `ctfert_l20h0`, and keep the family CC-only with no CT exposure in this slice.
- [x] P51.2 Wire the ctfert variants and rebuild the affected checked-in Patchworks artifacts
  - [x] P51.2a Update the two ctfert silviculture surfaces so they explicitly request the `log-grades` bank.
  - [x] P51.2b Regenerate the affected validated ForestModel XML plus `tracks_ctfert_l15h5/` and `tracks_ctfert_l20h0/` products/protoaccounts/accounts outputs before Matrix Builder validation.
- [x] P51.3 Validate the narrow rollout and close issue `#65`
  - [x] P51.3a Add focused exporter tests that prove the new log-grade family is present, complete, CC-only, and ctfert-only.
  - [x] P51.3b Inspect rebuilt XML/tracks directly and run one representative harvest-producing Patchworks smoke on a repaired ctfert surface to confirm live saved outputs include the new family.
  - [x] P51.3c Update `CHANGE_LOG.md`, the relevant K3Z docs, and GitHub issue `#65` with the rollout evidence and closeout note.
- [x] P51.4 Harden the log-grade bank semantics and reopen issue `#65`
  - [x] P51.4a Add a first-class BTC indicator-bank compile-recipe contract, with `log-grades` as the first recipe-backed bank and a shipped reference recipe inside FEMIC.
  - [x] P51.4b Change the default `log-grades` recipe to emit only `D/F/H/I/J/U/X/Y`, while preserving an explicit opt-in flag for `Logs_Grade_All`.
  - [x] P51.4c Add user-tweakable per-grade ratio scaling factors to the recipe contract, normalized by FEMIC so they rebalance grade shares without creating or destroying harvested volume.
  - [x] P51.4c1 Add treatment-specific ratio override support so CT can intentionally skew toward lower-grade small-log material instead of inheriting CC-oriented TIPSY grade shares.
  - [x] P51.4d Add a user recipe-overlay seam rooted at `~/.femic/recipe-overlays` so reference recipes stay repo-owned while local ratio tweaks stay user-owned.
  - [x] P51.4e Apply the same harvested-volume utilization multiplier to emitted log-grade product accounts so the explicit grade family sums to effective harvested volume at runtime.
  - [x] P51.4f Rebuild the broader affected K3Z family, rerun Matrix Builder, and directly inspect both static tracks/XML and one harvest-producing runtime smoke for the corrected semantics across managed and natural-origin harvest surfaces.
- [ ] P51.5 Extend K3Z log-grade surfaces from total-volume teaching accounts into AU/species splits and value-account layers
  - [ ] P51.5a Add AU-wise, species-wise log-grade harvested product/account families using the same additive compile-recipe logic now used for total harvested volume.
  - [ ] P51.5b Scrape the 2025 coast log market reports attached to issue `#65` and convert the species x grade price tables into a FEMIC-owned, user-overridable input surface.
  - [ ] P51.5c Add new value-account families that multiply AU/species/log-grade harvested volumes by the price matrix coefficients so users can aggregate upward inside Patchworks with `duplicateAccount()` patterns.
  - [ ] P51.5d Document the teaching/bridge rationale, the market-report provenance, and the user override seams in both user-facing and dev-facing docs.
- [x] P51.6 Add state-aware `CC` log-grade mix overrides after prior silviculture (`#78`)
  - [x] P51.6a Extend the log-grade compile-recipe seam so exact `SILV_STATE` values can override `CC` ratio weights without affecting other `CC` surfaces.
  - [x] P51.6b Expose the new state-aware `CC` override shape through the shipped recipe plus `~/.femic/recipe-overlays`.
  - [x] P51.6c Add focused exporter tests proving post-CT `CC` can differ from baseline `CC` while harvested-volume normalization still holds.
  - [x] P51.6d Update the relevant docs and user overlay example for the new exact-state override seam.

## Phase 52: TSR Recipe Templates for Source-Layer Acquisition and THLB Netdown
Notes: `planning/phase52_tsr_reconstruction_notes.md`

- [x] P52.1 Define the recipe schema and instance-local template lifecycle (`#123`)
  - [x] P52.1a Add packaged template YAML for:
  - [x] P52.1b Add loader/validator support for the new recipe surfaces.
  - [x] P52.1c Add `femic tsr recipe-init` with idempotent refresh/overwrite behavior.
- [x] P52.2 Build and execute the reusable source-layer recipe (`#124`)
  - [x] P52.2a Add `femic tsr source-layers-build` so TSR candidate facts + current BCDC knowledge become a reviewable acquisition recipe.
  - [x] P52.2b Add `femic tsr source-layers-run` so safe public acquisition, reuse, and override seams can be executed from the recipe instead of rediscovered ad hoc.
  - [x] P52.2c Persist per-entry provenance, current acquisition strategy, local artifact path, and blocked/override-required state.
- [x] P52.3 Extract TSA THLB netdown logic into a reviewable recipe (`#125`)
  - [x] P52.3a Add `femic tsr thlb-netdown-build` to derive ordered, provenance-preserving netdown steps from TSR source documents.
  - [x] P52.3b Normalize high-confidence predicates/operators while preserving raw TSR wording for later review.
  - [x] P52.3c Compose the THLB recipe against logical source-layer recipe ids rather than hard-coded one-off file paths.
- [x] P52.4 Execute the THLB netdown recipe into stand-level overlays (`#126`)
  - [x] P52.4a Add `femic tsr thlb-netdown-run` with a bounded supported operation set sufficient for TSA29 acceptance.
  - [x] P52.4b Emit a stand-level `thlb_fact` artifact plus a structured per-step audit report.
  - [x] P52.4c Keep unsupported or low-confidence steps explicit as `needs_review`, `unsupported`, or `blocked_missing_source` instead of guessing silently.
- [x] P52.5 Document the convergent, reproducible TSA29 acceptance path (`#127`)
  - [x] P52.5a Add worked docs for recipe init/build/run/report and the relationship between canonical TSR JSON, reviewed recipes, and user overrides.
  - [x] P52.5b Record the TSA29 proving-ground case from fresh clone through source-layer acquisition and THLB recipe execution.
  - [x] P52.5c Make the convergence and reproducibility contract explicit: when a user approves the finished instance, FEMIC should expose the fully scripted steps needed to rebuild that same product from a clean environment.
- [x] P52.6 Promote THLB execution from hybrid bridge to raw-land-base fragment reconstruction (`#128`)
  - [x] P52.6a Restore and validate AFLB-style checkpoint1 land-base initialization for reconstructed THLB (`#129`).
  - [x] P52.6b Add a TSA29 `MAP_ID`-based smoke subset ladder for fast overlay proving-ground runs (`#130`).
  - [x] P52.6b1 Add stage-aware GLB/AFLB/LHLB/THLB parsing and recipe schema for TSR netdown logic (`#134`).
  - [x] P52.6b2 Improve THLB status reports and recipe review UX with stage groups, exact logic, and lock state (`#135`).
  - [x] P52.6b3 Add a generated THLB notebook workbench and lock/export flow (`#137`).
  - [x] P52.6b4 Improve DWDS follow-up retrieval and artifact materialization after order submission (`#140`).
  - [ ] P52.6b5 Run full-TSA29 THLB step-by-step validation and reconcile the recipe against TSR benchmarks (`#141`).
  - [ ] P52.6b6 Benchmark LU-wise local-process parallel THLB execution for TSA-scale netdown (`#143`).
- [x] P52.6c Execute fragment-first TSR THLB reconstruction from reviewed recipe steps (`#131`).
  - [x] P52.6c1 Replace reconstructed full-area row-batch exact overlay with LU-wise exact decomposition over cached checkpoint1 partitions.
  - [x] P52.6c2 Carry reconstructed LU chunk state forward across steps so exact spatial exclusions update only touched LU chunks instead of rebuilding the full TSA each step.
  - [x] P52.6c3 Prove the production reconstructed run finishes on full TSA29 with explicit exact-overlay vs aspatial-fallback reporting and no silent stand-binary fallback.
  - [x] P52.6d Add explicit end-of-workflow aspatial fallback for blocked TSR target-area steps (`#132`).
    - [x] P52.6d1 Extend reconstructed runner step selection/execution to include explicit `aspatial_reduction` and `aspatial_area_reduction` rows.
    - [x] P52.6d2 Distinguish exact spatial overlay, explicit aspatial fallback, blocked exact overlay, and no-deduction rows in reconstructed audit/status outputs.
    - [x] P52.6d3 Prove the reconstructed fallback contract on a TSA29 smoke run without changing the reviewed parent-step lane.
- [x] P52.6e Document the reconstruction ladder and comparison contract (`#133`).
- [x] P52.6f Model TSR Section 7.1.5 broadleaf volume exclusions in conifer-leading stands as a later yield-assumption lane, not a THLB area-netdown step (`#139`).
  - [x] P52.6f1 Add a narrow TSA29-first `yield_assumptions_path` seam to post-TIPSY / BTC-post-TIPSY CLI, run-profile, and workflow manifests.
  - [x] P52.6f2 Apply TSA29 section 7.1.5 untreated broadleaf-volume exclusion inside the assembled bundle tables before writing `model_input_bundle`.
  - [x] P52.6f3 Prove the bundle adjustment on TSA29 and keep THLB step 15 wording explicitly limited to broadleaf-leading area exclusion.
- [x] P52.6g Add an ArcGIS Pro review-project emit command for instance-local GIS inspection (`#138`).
  - [x] P52.6g1 Reuse the shared ArcGIS Pro Python runner seam and expose `femic prep arcgis-review-project`.
  - [x] P52.6g2 Discover instance-local review layers and emit a manifest-backed `.aprx` bundle with all layers off by default.
  - [x] P52.6g3 Prove the command on TSA29 with a real Windows/ArcGIS Pro project build.
- [x] P52.6h Add explicit no-LLM THLB warm-start checklist/template artifacts (`#136`).
  - [x] P52.6h1 Add a packaged bounded THLB motif library plus a deterministic warm-start builder over the reviewed parent-step recipe.
  - [x] P52.6h2 Expose `femic tsr thlb-netdown-warmstart-build` and emit paired Markdown/YAML review artifacts under the instance root.
  - [x] P52.6h3 Prove the warm-start output on TSA29 and link the new artifact from the existing THLB review surfaces without making it canonical logic.
- [x] P52.6i Build a TSA29-first strict-vs-reviewed THLB comparison artifact (`#128`).
  - [x] P52.6i1 Add `femic tsr thlb-reconstruction-compare` to emit Markdown/JSON comparison artifacts without rerunning THLB execution.
  - [x] P52.6i2 Compare three surfaces per parent step:
  - [x] P52.6i3 Bucket the biggest parent-step differences in plain language so the next modeling follow-up is chosen from evidence instead of guesswork.
  - [x] P52.6i4 Recenter the TSA29 comparison artifact so strict-vs-TSR is the governing score, strict-vs-reviewed is explanatory context, and the report emits a stepwise adjudication queue.

## Phase 53: Named Pipeline / Runbook Refactor
Notes: `planning/phase53_named_pipeline_notes.md`

- [ ] P53.1 Open the named-pipeline umbrella and define the architecture boundary (`#163`)
  - [ ] P53.1a Treat named pipelines as the primary workflow abstraction:
  - [ ] P53.1b Define the registry/runbook contracts needed to replace the legacy monolithic-script mental model without invalidating the recipe-based work already completed under `#122` and its children (`#167`).
  - [ ] P53.1c Identify the first bounded child seams needed to prove the architecture incrementally rather than attempting a one-shot rewrite.
  - [ ] P53.1d Validate the TSA29 strict named pipeline against the locked-chain contract (`#169`).
    - [x] P53.1d1 Bind the checked-in TSA29 strict runbook to an explicit locked validation contract and fail fast if it still resolves the mutable live recipe.
    - [x] P53.1d2 Let the strict validation contract bind the checked-in TSA29 runbook to the required locked recipe path so the proof surface can execute against the right contract.
    - [x] P53.1d3 Validate strict named-pipeline run results against the locked-chain ledger immediately after execution so wrong-result runs fail as contract mismatches instead of looking superficially successful.
    - [ ] P53.1d4 Rerun the checked-in TSA29 strict named pipeline against the locked recipe surface and record whether the validator reports a clean locked-chain match or the first specific parent-step mismatch.
    - [x] P53.1d5 Purge TSA29 legacy `ria_vri_vclr1p_checkpoint*.feather` fallback surfaces from active code/docs and delete the stale checkpoint files so strict validation cannot silently drift onto them.
    - [x] P53.1d6 Add always-on real-time user-observable runtime output for `femic pipelines run`, including parent-step events, compiled-step subevents, and mirrored live event logs under `runtime/logs/tsr/`.
    - [x] P53.1d7 Add a strict preflight seam-benchmark gate so TSA29 strict named-pipeline runs abort before execution when the selected start surface already disagrees with the locked-chain reference for that seam.
    - [x] P53.1d8 Wire the strict `scratch` seam to the raw-source GLB builder so named-pipeline step 001 validates from clipped VRI/TSA geometry and stops there before step 002.
    - [ ] P53.1d9 Add a bounded strict row-2 named-pipeline runbook that materializes the GLB checkpoint from step 001, runs only `thlb_parent_002_*`, and validates that single step against the locked chain.
      - [x] P53.1d9a Normalize the materialized `glb_checkpoint.feather` area columns from clipped geometry so step-002 input area cannot drift back onto preserved source-layer area attributes.
      - [x] P53.1d9b Sequence strict scratch pipelines over the locked parent-step recipe order so milestone rows validate in place and each transformation row chains its bounded output checkpoint into the next locked step.
      - [x] P53.1d9c Add an explicit strict `glb` seam so step-002 validation can start from the saved validated GLB checkpoint without rebuilding row 1.
    - [x] P53.1d10 Rebuild `tsr.thlb_strict` to execute only locked validated step logic.
      - [x] P53.1d10a Replace strict transformation-step execution with a dedicated locked-step executor that uses only the locked recipe parent-step contract and explicit checkpoints.
      - [x] P53.1d10b Hard-ban the old broad parent-step runner from `tsr.thlb_strict` and fail immediately if strict execution tries to reach it.
    - [x] P53.1d10c Chain deterministic strict-step checkpoints under `data/tsr/strict_chain/` and validate milestone rows in place against the locked ledger.
    - [x] P53.1d10d LU-parallelize the strict locked-step executor so bounded strict transformation runs use cached LU partitions/bundles instead of one monolithic serial pass.
    - [x] P53.1d10e Emit explicit progress events for LU partition cache lookup/materialization so strict LU-wise steps do not appear hung before worker bundles start.
    - [x] P53.1d10f Reuse the established CPU-aware LU worker/bundle sizing helper in the strict locked-step executor so Windows step runs default back to the documented `8 workers / 8 bundles` pattern instead of one worker per LU chunk.
    - [x] P53.1d10g Make strict LU cache reuse schema-aware so `tsr.thlb_strict` refuses stale chunk caches unless they match the current checkpoint column set, including strict-state columns such as `thlb_fact`.
    - [x] P53.1d10h Sync locked row-2 aspatial fallback metadata and stop falsely blocking production full-TSA F_OWN overlays on LU bundles.
    - [x] P53.1d10i Correct strict row-2 parent-step accounting to use the true before/after net change so direct-target aspatial deductions are included in marginal validation.
- [x] P53.2 Add the first explicit interruption/resume seam inside the THLB workflow (`#164`)
  - [x] P53.2a Formalize AFLB as the expected checkpoint where THLB pauses to derive strata/AUs and yield-model artifacts.
  - [x] P53.2b Add a user-parameterizable top-N strata coverage rule with `80%` default.
  - [x] P53.2c Define cache-sufficiency checks for reusing local VDYP samples versus rerunning VDYP under the active sampling-intensity settings.
  - [x] P53.2d Compile TIPSY input parameters, run TIPSY (and optionally FANSIER), compile yield curves, and resume downstream THLB from a restart-safe yield bridge artifact.

## Phase 54: Bootstrap MKRF Standalone Instance
Notes: `planning/mkrf_instance_bootstrap.md`

- [x] P54.1 Bootstrap `femic-mkrf-instance` as a private standalone FEMIC repository (`#171`)
  - [x] P54.1a Create the private `UBC-FRESH/femic-mkrf-instance` repository and record the thin-baseline publication contract.
  - [x] P54.1b Scaffold the standard FEMIC instance skeleton for `mkrf`, including rebuild spec, allowlist, runbook, and private/WIP README guidance.
  - [x] P54.1c Initialize the repo as a large-only DataLad/git-annex dataset with `.gitattributes` / ignore policy that keeps small canonical text in Git and annexes bulky payload families.
  - [x] P54.1d Create and validate the dedicated Arbutus bucket / `arbutus-s3` special remote for the instance without exposing anonymous public access.
  - [x] P54.1e Publish a thin baseline plus one non-sensitive annex smoke artifact, then cold-clone and materialization-smoke the repo.
  - [x] P54.1f Link `femic-mkrf-instance` back into FEMIC as submodule `external/femic-mkrf-instance` and update parent docs/changelog pointers only as needed.

## Phase 55: Recover the Legacy 2016 MKRF Patchworks Model into FEMIC-Ready Metadata
Notes: `planning/mkrf_legacy_decompile.md`

- [x] P55.1 Launch the MKRF legacy archaeology lane in the parent FEMIC repo (`#172`)
  - [x] P55.1a Open the umbrella issue and create the issue-backed feature branch for the archaeology-first milestone.
  - [x] P55.1b Inventory the authoritative legacy corpus under `MKRF_Cosmin_Model/MKRF`, including the compiled `PW_MKRF` bundle, `03_MappingAnalysisData`, and `05_Documents`.
  - [x] P55.1c Publish the first-pass artifact manifest and bagging/tagging map in the parent repo as reviewable metadata surfaces.
  - [x] P55.1d Record the compiled-model anatomy, FEMIC crosswalk, unresolved seams, and next bounded step in the planning note.
- [x] P55.2 Import the stable compiled-package anatomy into `femic-mkrf-instance` as review metadata (`#172`)
  - [x] P55.2a Add instance-local metadata summarizing the compiled `PW_MKRF` package entrypoints and stable families without publishing bulky legacy payloads.
  - [x] P55.2b Add an instance-local reference note documenting the compiled package anatomy and current review-only boundary.
  - [x] P55.2c Update the MKRF instance README/runbook/lineage metadata so the compiled-package intake is part of the thin-baseline contract.
- [x] P55.3 Import the small compiled control layer into `femic-mkrf-instance` as archival reference files (`#172`)
  - [x] P55.3a Copy the legacy control entrypoints (`baseMKRF.pin`, `runME.bsh`, `ScenarioSet.bsh`) into an archival lane inside the MKRF instance.
  - [x] P55.3b Copy the selected legacy `Scripts/*.bsh` and `Targets/*.bsh` files into the same archival/reference lane.
  - [x] P55.3c Update instance-local metadata/docs so the copied controls are explicitly archival-only and the next bounded move narrows to one bulky compiled family.
- [x] P55.4 Import the compiled legacy track tables into `femic-mkrf-instance` as archival reference payload (`#172`)
  - [x] P55.4a Copy the legacy `Tracks/*.csv` family into an archival lane inside the MKRF instance without claiming a runnable rebuild surface.
  - [x] P55.4b Update instance-local metadata/docs so the archival track tables are part of the review contract and the next bounded move narrows to the spatial runtime family.
- [x] P55.5 Import the compiled legacy spatial runtime family into `femic-mkrf-instance` as archival reference payload (`#172`)
  - [x] P55.5a Copy `Spatial/fragments.*` plus `Spatial/topo_frag100.csv` into an archival lane inside the MKRF instance without claiming a runnable rebuild surface.
  - [x] P55.5b Update instance-local metadata/docs so the archival spatial family is part of the review contract and the next bounded move narrows again.
- [x] P55.6 Resolve the governing editable-source seam for the legacy MKRF XML builder lane (`#172`)
  - [x] P55.6a Extract and review the embedded VBA from `XML/002_base.xlsm` so the workbook-driven XML builder flow is inspectable.
  - [x] P55.6b Record the authority chain across `002_base.xlsm`, `baseMKRF.xml`, `Curves.xml`, `001_makeCurves_XML.py`, and `003_MakeAccounts.py`.
  - [x] P55.6c Update parent and instance metadata/docs so the workbook data surfaces are now treated as the governing editable-source seam and the next bounded move narrows to workbook-surface extraction.
- [x] P55.7 Map the governing MKRF workbook surfaces into FEMIC-facing input families (`#172`)
  - [x] P55.7a Inventory the materialized workbook tabs, named ranges, and `Codes` registry surfaces that feed the SPS XML serializer.
  - [x] P55.7b Classify each workbook surface by XML role and likely future FEMIC home.
  - [x] P55.7c Update parent and instance metadata/docs so the next bounded move narrows to materializing workbook-owned values into tracked review tables.
- [x] P55.8 Materialize the governing MKRF workbook-owned values into tracked review tables (`#172`)
  - [x] P55.8a Export the active workbook surfaces (`Input Variables`, `Netdown`, `Curve Library`, `Attrib`, and `Treat`) into tracked CSV/YAML review artifacts.
  - [x] P55.8b Keep the extracted tables explicitly labeled as review evidence, not live FEMIC config.
  - [x] P55.8c Update parent and instance metadata/docs so the next bounded move narrows to one specific workbook-surface refactor seam.
- [x] P55.9 Roll out the first FEMIC-native MKRF `Input Variables` translation (`#172`)
  - [x] P55.9a Add the normalized MKRF-first `Input Variables` config contract plus lineage metadata under `external/femic-mkrf-instance/config/legacy_xml_builder/`.
  - [x] P55.9b Wire the live subset (`description`, `start_year`, `horizon_years`) into the existing Patchworks exporter as an explicit opt-in input path without changing default K3Z/TSA29 behavior.
  - [x] P55.9c Keep unsupported legacy expressions/constants/include hooks explicit in docs/metadata and narrow the next bounded move based on what this first live translation reveals.
- [x] P55.10 Extend the translated MKRF `Input Variables` seam into a block-layout/export contract (`#172`)
  - [x] P55.10a Make the legacy block/area/age/exclude expressions live in Patchworks export as an explicit opt-in MKRF-first contract.
  - [x] P55.10b Pass through and validate the checkpoint source columns required by those live legacy expressions in the exported fragments surface.
  - [x] P55.10c Update parent and instance metadata/docs so the next bounded move narrows to the remaining staged `Input Variables` surfaces.
- [x] P55.11 Operationalize the translated MKRF `additional_stratification_columns` seam (`#172`)
  - [x] P55.11a Make the workbook-owned additional stratification column bindings live in the opt-in MKRF fragments export surface.
  - [x] P55.11b Pass through and validate the checkpoint source columns required by those live additional stratification bindings.
  - [x] P55.11c Update parent and instance metadata/docs so the next bounded move narrows to the remaining staged `Input Variables` semantics.
- [x] P55.12 Operationalize the translated MKRF `treatment_eligibility_expression` seam (`#172`)
  - [x] P55.12a Make the workbook-owned treatment-eligibility expression live as an opt-in MKRF fragments/export field.
  - [x] P55.12b Evaluate the treatment-eligibility expression against the live additional stratification bindings and legacy constants with clear failure handling for unresolved symbols.
  - [x] P55.12c Update parent and instance metadata/docs so the next bounded move narrows to the remaining staged workbook semantics.
- [x] P55.13 Operationalize the remaining legacy matrix-builder constants seam (`#172`)
  - [x] P55.13a Add an explicit MKRF-first constants contract for `managed`, `unmanaged`, `operable`, `lowoper`, and deferred `frd`.
  - [x] P55.13b Restrict live legacy expression symbol resolution to constants marked as live export/build inputs when the contract is present.
  - [x] P55.13c Update parent and instance metadata/docs so deferred formula-like constants remain review evidence only.
- [x] P55.14 Adjudicate the remaining staged MKRF `Input Variables` semantics (`#172`)
  - [x] P55.14a Decide and document whether `max_inventory_age` is a live exporter/build input or review metadata only.
  - [x] P55.14b Classify each legacy include-fragment hook (`beforeCurves`, `afterCurves`, `afterRetention`, `afterUnmanaged`, `afterStratum`, `afterAttributes`) as live, preserved review metadata, or blocked by missing source/runtime context.
  - [x] P55.14c Update the translated Input Variables contract and lineage surfaces without activating include hooks, `Netdown`, `Treat`, or upstream mapping data.
- [x] P55.15 Translate the legacy `Curve Library` surface into an explicit review-to-build contract (`#172`)
  - [x] P55.15a Map workbook curve names and curve table extract columns to FEMIC-native curve registry/table fields.
  - [x] P55.15b Decide which curve rows can become live Patchworks XML curve inputs from tracked extracts and which remain review evidence.
  - [x] P55.15c Add focused validation that the translated curve contract preserves legacy curve identifiers, age axes, and generated-XML include expectations.
- [x] P55.16 Translate the legacy `Netdown` surface into an explicit review-to-build contract (`#172`)
  - [x] P55.16a Map workbook `netdownCriteria`, `netdownNames`, and `netdownFactors` into candidate FEMIC netdown rule metadata.
  - [x] P55.16b Decide which netdown rules can safely become live retention/export behavior from current checkpoint fields.
  - [x] P55.16c Keep missing upstream/source-field requirements explicit rather than substituting compiled spatial or track artifacts as raw inputs.
- [x] P55.17 Translate the legacy `Attrib` surface into an explicit review-to-build contract (`#172`)
  - [x] P55.17a Map workbook `attributes` rows to candidate Patchworks feature/product/account builders and identify formula dependencies such as `frd`.
  - [x] P55.17b Decide which attribute rows are live-build candidates versus review-only formulas pending `Netdown`, curve, or `Treat` dependencies.
  - [x] P55.17c Add focused validation for any activated attribute/account rows against the reviewed workbook extracts.
- [x] P55.18 Translate the legacy `Treat` stratum bundle into an explicit review-to-build contract (`#172`)
  - [x] P55.18a Map `stratumCriteria`, `stratumFeatures`, `stratumSuccession`, `stratumProducts`, `stratumTreatments`, and `stratumFactors` into FEMIC-native stratum metadata.
  - [x] P55.18b Decide which treatment/state/product rows can be activated without relying on unreviewed include hooks or upstream mapping data.
  - [x] P55.18c Validate activated stratum semantics against workbook extracts and copied archival track tables without claiming full legacy rebuild equivalence.
- [x] P55.19 Reconcile the workbook-derived ForestModel contract against compiled legacy outputs (`#172`)
  - [x] P55.19a Compare the translated build contract to archival `baseMKRF.xml`, `Curves.xml`, and copied `Tracks/*.csv` at the contract surface level.
  - [x] P55.19b Identify remaining gaps that require `03_MappingAnalysisData/*`, road-network discovery, report/output intake, or direct workbook publication.
  - [x] P55.19c Publish a go/no-go rebuild readiness note before any claim that the MKRF instance has a runnable FEMIC rebuild surface.

## Phase 56: Close MKRF Rebuild Readiness Gaps
Notes: `planning/mkrf_legacy_decompile.md`

- [x] P56.1 Plan post-P55 rebuild gap closure from the no-go readiness review (`#172`)
  - [x] P56.1a Convert the P55.19 no-go blockers into an ordered implementation boundary without starting payload intake or builder activation.
  - [x] P56.1b Decide which blockers require generated XML, compiled track evidence publication, builder design, source-input publication, or readiness criteria.
  - [x] P56.1c Update planning/lineage notes so P56.2 is the next bounded implementation move.
- [x] P56.2 Reconcile generated XML artifacts (`#172`)
  - [x] P56.2a Locate/materialize `baseMKRF.xml`, `Curves.xml`, and/or `CSV/CURVE_TABLE.csv` as explicit review artifacts.
  - [x] P56.2b Compare generated XML fragments against translated contracts without activating `beforeCurves` or XML builders.
  - [x] P56.2c Record generator/input gaps and decide whether direct workbook publication is required.
- [x] P56.3 Import or verify existing legacy compiled track-table evidence (`#172`)
  - [x] P56.3a Confirm readable legacy source CSVs for `Tracks/curves.csv`, `features.csv`, and `products.csv`.
  - [x] P56.3b Import them into the MKRF instance as archival/reference evidence only if DataLad/git-annex can track them correctly.
  - [x] P56.3c Compare their contract surfaces to Curve Library, Attrib, Treat, and account metadata without running matrix build.
- [x] P56.4 Design builder activation and matrix-build handoff order (`#172`)
  - [x] P56.4a Define activation order for curve, retention, attribute, stratum, full XML emission, and matrix-build handoff surfaces.
  - [x] P56.4b Separate legacy compiled-output evidence from future FEMIC-regenerated XML and track outputs.
  - [x] P56.4c Preserve default exporter behavior and keep MKRF activation opt-in until validation gates are met.
- [x] P56.5 Resolve real MKRF source-input publication boundary (`#172`)
  - [x] P56.5a Identify fragments/checkpoint/boundary inputs required by the MKRF run profile.
  - [x] P56.5b Decide whether `03_MappingAnalysisData/*`, roads, outputs, or direct workbook publication are required for reproducibility.
  - [x] P56.5c Keep raw source inputs distinct from checkpoints, compiled artifacts, and the `Base TFL26` literal-description mismatch.
- [x] P56.6 Publish rebuild-readiness milestone criteria (`#172`)
  - [x] P56.6a Define acceptance criteria for moving from metadata recovery to runnable rebuild candidate.
  - [x] P56.6b Publish a go/no-go checklist requiring legacy evidence reconciliation plus future FEMIC-generated XML and matrix-build proof.
  - [x] P56.6c Keep runnable rebuild claims blocked until all readiness criteria are met.

## Phase 57: Build Minimal Runnable MKRF Patchworks Instance
Notes: `planning/mkrf_legacy_decompile.md`

- [x] P57.1 Plan the runnable MKRF model boundary and acceptance gates (`#172`)
  - [x] P57.1a Define minimal runnable as FEMIC-managed XML emission, Patchworks matrix build, generated-track inspection, and Patchworks launch proof.
  - [x] P57.1b Adopt the existing legacy compiled fragments/topology as accepted runtime inputs for the first runnable proof without claiming raw-source reconstruction.
  - [x] P57.1c Record the compatibility-passthrough boundary for deferred formula-heavy Attrib XML blocks.
- [x] P57.2 Materialize the runtime model directory from accepted legacy runtime inputs (`#172`)
  - [x] P57.2a Create the MKRF model layout with `XML/`, `Spatial/`, `Tracks/`, `Scripts/`, `Targets/`, and analysis entrypoint surfaces.
  - [x] P57.2b Copy or materialize legacy `fragments.*` and `topo_frag100.csv` as runtime inputs using DataLad/git-annex where required.
  - [x] P57.2c Sanitize copied control scripts so runtime paths are instance-relative and do not expose machine-specific source paths.
- [x] P57.3 Implement opt-in MKRF XML emission from translated contracts (`#172`)
  - [x] P57.3a Emit Input Variables, output table bindings, defines/constants, Curve Library curves, and generated yield curves from `CSV/CURVE_TABLE.csv`.
  - [x] P57.3b Emit Netdown retention rules, unmanaged tracks, default succession, and CC/CT treatment definitions.
  - [x] P57.3c Keep the MKRF builder opt-in and preserve default non-MKRF exporter behavior.
- [x] P57.4 Add explicit compatibility passthrough for deferred Attrib formulas (`#172`)
  - [x] P57.4a Extract the deferred formula-heavy Attrib XML blocks from reconciled `baseMKRF.xml` under a named compatibility contract.
  - [x] P57.4b Inline passthrough blocks only after validating their required curves, defines, and labels against the emitted XML surface.
  - [x] P57.4c Keep passthrough status visible as a runnable-minimum caveat rather than claiming fully native Attrib reimplementation.
- [x] P57.5 Wire MKRF Patchworks runtime config to the generated model directory (`#172`)
  - [x] P57.5a Point matrix-builder paths at the generated MKRF XML, accepted fragments, and generated `Tracks/` directory.
  - [x] P57.5b Add or update the MKRF Patchworks variant/launch registration surface if needed for launch proof.
  - [x] P57.5c Validate Patchworks preflight without starting matrix build.
- [x] P57.6 Run matrix build against FEMIC-emitted XML and accepted spatial inputs (`#172`)
  - [x] P57.6a Run Patchworks matrix builder from the generated model directory.
  - [x] P57.6b Require generated `Tracks/{curves,features,products,treatments,accounts,blocks}.csv` evidence.
  - [x] P57.6c Preserve logs/manifests as runtime evidence without overwriting archival legacy evidence.
- [x] P57.7 Compare generated track tables against legacy compiled evidence (`#172`)
  - [x] P57.7a Compare generated curves/features/products/treatments/accounts/blocks surfaces to legacy compiled tracks at the accepted smoke level.
  - [x] P57.7b Record expected differences caused by compatibility passthrough or accepted runtime-boundary caveats.
  - [x] P57.7c Keep raw-source reconstruction and exact legacy equivalence out of the minimal runnable claim.
- [x] P57.8 Prove Patchworks launch with the generated model (`#172`)
  - [x] P57.8a Launch the generated MKRF PIN through the Patchworks runtime seam.
  - [x] P57.8b Capture launch logs/manifests and inspect the most relevant generated model surfaces.
  - [x] P57.8c Do not claim launch success unless the generated model opens/runs from the generated runtime directory.
- [x] P57.9 Publish minimal runnable closeout docs and caveats (`#172`)
  - [x] P57.9a Update instance README/runbook/lineage metadata with the runnable proof boundary.
  - [x] P57.9b Update parent planning/changelog and tests with the minimal runnable status.
  - [x] P57.9c Record next-phase caveats for native Attrib completion, raw-source reconstruction, and broader scenario/runtime validation.

## Phase 58: Harden MKRF Beyond the Minimal Runnable Boundary
Notes: `planning/mkrf_legacy_decompile.md`

- [x] P58.1 Plan the post-minimal-runnable hardening sequence (`#172`)
  - [x] P58.1a Convert the remaining minimal-runnable caveats into an ordered bounded sequence without starting new rebuild lanes ad hoc.
  - [x] P58.1b Keep native Attrib replacement, raw-source reconstruction, and broader runtime/scenario validation as distinct contracts.
  - [x] P58.1c Publish the next active bounded move before any further MKRF implementation.
- [x] P58.2 Replace the MKRF Attrib compatibility passthrough with a native FEMIC builder (`#172`)
  - [x] P58.2a Rebuild the currently deferred formula-heavy Attrib feature/product surfaces from the translated workbook contract instead of copying legacy `<select>` blocks.
  - [x] P58.2b Prove the native Attrib surfaces preserve the accepted minimal-runnable behavior before removing the passthrough.
  - [x] P58.2c Keep any remaining unsupported formula dependencies explicit rather than silently collapsing them into static constants or copied XML.
- [x] P58.3 Reconstruct the raw-source input lane from the legacy planning corpus (`#172`)
  - [x] P58.3a Materialize and review the true upstream source surfaces under `03_MappingAnalysisData/*` that are required for reproducible fragments/topology generation.
  - [x] P58.3b Separate raw-source reconstruction from checkpoint-derived or compiled-runtime substitutes.
  - [x] P58.3c Publish the reproducibility boundary before claiming a source-faithful MKRF rebuild.
- [x] P58.4 Broaden scenario and runtime validation beyond the minimal launch proof (`#172`)
  - [x] P58.4a Resolve the `InitialTargets` / scenario-target seam enough to exercise a representative nontrivial runtime path.
    - PoC boundary recorded on 2026-04-29: the active AAC-max `ScenarioSet.bsh` helper names `THLB4070(...)` and `UWR(...)` remain unmapped in the recovered corpus, so the PoC lane accepts them as deferred missing legacy seams instead of blocking completion.
    - For the PoC runtime benchmark, use the legacy `Outputs/001_Base/scenario/{targetSummary,targetStatus}.csv` checkpoint surfaces as the accepted target-control lane loaded through `analysis/base.pin`.
  - [x] P58.4b Define and run a bounded smoke suite over generated XML, generated tracks, and at least one representative launch/runtime scenario.
    - PoC smoke boundary recorded on 2026-04-29: generated MKRF XML and generated track tables remained on the accepted runtime lane, and the checkpoint-backed `analysis/base.pin` loaded in Patchworks GUI with active targets and a saved representative scenario under `analysis/scenarios/foo`.
  - [x] P58.4c Record which runtime behaviors remain unvalidated after the broadened smoke suite.
    - Remaining PoC caveats recorded on 2026-04-29: the runtime proof covers the accepted benchmark lane only, not source-faithful reconstruction of `THLB4070(...)` / `UWR(...)`, not full helper-library recovery under `InitialTargets/00_Target_Descriptions.bsh`, and not headless-launcher automation guarantees.
- [x] P58.5 Close Phase 58 as the PoC / reverse-engineering benchmark lane (`#172`)
  - [x] P58.5a Record that the accepted `500/501` versus `650/651` merch-tail variance remains a deferred fidelity question for the later from-scratch rebuild rather than a PoC blocker.
  - [x] P58.5b Record that exact compiled curve-id preservation is not required for the PoC benchmark lane and belongs to later comparison work only if it affects a real rebuild acceptance gate.
  - [x] P58.5c Pin unresolved legacy helper seams `THLB4070(...)`, `UWR(...)`, and the missing `InitialTargets/00_Target_Descriptions.bsh` library to the later from-scratch rebuild instead of spending more PoC effort on them.
- [x] P58.6 Benchmark one representative scenario on legacy versus the PoC FEMIC instance (`#172`)
  - [x] P58.6a Run one representative benchmark scenario on both the legacy MKRF package and the current PoC FEMIC lane.
  - [x] P58.6b Compare a small KPI set and record whether the outputs generally line up without requiring exact parity.
  - [x] P58.6c Record the accepted benchmark variances explicitly so the PoC lane closes on a real side-by-side behavior check, not launch proof alone.
- [x] P58.7 Recast the current runtime package explicitly as the MKRF PoC intermediate (`#172`)
  - [x] P58.7a Rename the current runtime package to `models/mkrf_patchworks_model_poc` so the PoC surface can coexist cleanly with the later canonical rebuild in the same instance repo.
  - [x] P58.7b Update roadmap, planning notes, changelog, and issue trail so the current checked-in runtime package is treated as the MKRF PoC intermediate.
  - [x] P58.7c Keep the future from-scratch rebuild lane separate from the PoC runtime package and avoid implying the current checked-in path is the final canonical MKRF model.

## Phase 59: Publish MKRF PoC User-Facing Technical Docs
Notes: `planning/mkrf_legacy_decompile.md`

- [x] P59.1 Publish MKRF PoC Sphinx docs using the K3Z instance docs as the template (`#175`)
  - [x] P59.1a Match the K3Z instance docs scope, depth, formatting, and structure rather than inventing a one-off MKRF docs shape.
  - [x] P59.1b Make the docs explicit that the current MKRF model is a PoC benchmark/intermediate, not the final canonical rebuild.
  - [x] P59.1c Publish the docs through the existing Sphinx/GitHub Pages workflow with the same operator-facing quality bar as K3Z, using a standalone MKRF PoC chapter set built from:
    `index`, `getting-started`, `model-anatomy`, `data-package-crosswalk`,
    `metadata-and-lineage`, `operator-runbook`, `rebuild-and-qa`,
    `troubleshooting`, and MKRF-specific PoC pages for benchmark results,
    legacy evidence/runbook boundaries, and accepted caveats/deferred seams.
- [x] P59.2 Document the MKRF PoC benchmark/runtime lane and accepted claim boundary (`#175`)
  - [x] P59.2a Teach the accepted runtime package, generated XML/tracks, spatial lane, and representative benchmark scenario surfaces.
  - [x] P59.2b Record the accepted PoC caveats, including unresolved helper seams and accepted benchmark variances.
  - [x] P59.2c Distinguish clearly between benchmark/reference evidence and the later from-scratch rebuild contract.
- [x] P59.3 Publish closeout docs metadata and handoff to the real rebuild phase (`#175`)
  - [x] P59.3a Update parent and instance docs/runbooks so the PoC documentation lane is complete and auditable.
  - [x] P59.3b Link the finished PoC docs lane to the next from-scratch rebuild phase without blurring the two contracts.
  - [x] P59.3c Confirm the PoC docs are good enough that the team can stop treating the benchmark lane as under-documented.

## Phase 60: From-Scratch MKRF FEMIC-Native Rebuild
Notes: `planning/mkrf_femic_native_rebuild.md`

- [x] P60.1 Define the target instance contract and acceptance gates for the new MKRF rebuild (`#173`)
  - [x] P60.1a Make K3Z/TSA29-style FEMIC instance organization and workflow conventions the governing default for the new MKRF rebuild.
  - [x] P60.1b Treat PoC artifacts as benchmark/reference evidence only, not as the target architecture contract.
  - [x] P60.1c Require that any legacy behavior carried forward into the new rebuild be justified by source evidence or benchmark necessity.
- [ ] P60.2 Define the canonical FEMIC-native MKRF instance layout using K3Z/TSA29 patterns (`#173`)
  - [x] P60.2a Decide the canonical repo/instance/runtime/doc surface layout before source-driven rebuild work starts.
  - [x] P60.2b Define the rebuild sequencing and validation contracts for the new instance lane.
  - [x] P60.2c Keep benchmark/reference artifacts clearly separated from the new source-faithful build surfaces.
- [ ] P60.3 Reconstruct the raw-source geometry-to-runtime pipeline from `03_MappingAnalysisData/*` (`#173`)
  - [ ] P60.3a Rebuild the geometry publication path from upstream source surfaces rather than accepted compiled-runtime substitutes.
  - [ ] P60.3b Rebuild the runtime spatial/package handoff with explicit lineage and acceptance checks.
  - [ ] P60.3c Keep checkpoint-derived or compiled-runtime artifacts out of the source-faithful rebuild claim surface.
- [ ] P60.4 Rebuild the target/control lane from reviewed source contracts instead of legacy checkpoint loading (`#173`)
  - [ ] P60.4a Replace the PoC checkpoint-backed target-control lane with a source-driven FEMIC-native control surface.
  - [ ] P60.4b Reconstruct or replace legacy scenario-target semantics only where they are justified by source evidence or benchmark necessity.
  - [ ] P60.4c Keep unexplained legacy compiled control seams out of the new build unless they become required by a documented acceptance gate.
- [ ] P60.5 Rebuild the full MKRF runtime package from source-faithful inputs (`#173`)
  - [ ] P60.5a Generate the runtime XML, tracks, and control surfaces from the new FEMIC-native rebuild lane.
  - [ ] P60.5b Re-run Matrix Builder and runtime assembly against the rebuilt source-faithful package.
  - [ ] P60.5c Keep generated outputs and lineage surfaces synchronized as the new canonical MKRF runtime package.
- [ ] P60.6 Validate the rebuilt model against the PoC benchmark and legacy evidence (`#173`)
  - [ ] P60.6a Compare the rebuilt runtime against the accepted PoC benchmark surfaces.
  - [ ] P60.6b Compare the rebuilt runtime against relevant legacy evidence where it still matters for acceptance.
  - [ ] P60.6c Record which observed differences are accepted redesign choices versus unresolved regressions.
- [ ] P60.7 Publish closeout docs and decide whether `#172` can close (`#173`)
  - [ ] P60.7a Update the parent and instance docs/runbooks to teach the new MKRF rebuild lane.
  - [ ] P60.7b Record the final claim boundary between benchmark archaeology and the new source-faithful rebuild.
  - [ ] P60.7c Decide whether the umbrella legacy-recovery issue `#172` can close once the from-scratch rebuild phase is complete.

## Phase 61: First-Class Windows Arbutus Auth Workflow

- [x] P61.1 Plan and define the Windows Arbutus auth workflow contract (`#174`)
  - [x] P61.1a Add the first-class auth workflow to the roadmap before implementation starts.
  - [x] P61.1b Define the user-local file contract for shared credentials, profile registry, and status marker.
  - [x] P61.1c Preserve legacy single-bucket `S3_BUCKET_NAME` compatibility only as a migration bridge.
- [x] P61.2 Add multi-profile Windows Arbutus auth status/init commands (`#174`)
  - [x] P61.2a Add `femic prep arbutus-auth-status` as the non-mutating auth/profile/marker probe.
  - [x] P61.2b Add `femic prep arbutus-auth-init` to scaffold missing local files, prompt for missing values, and validate `HeadBucket`.
  - [x] P61.2c Keep secrets out of CLI flags, command output, and persisted non-secret marker files.
- [x] P61.3 Persist a non-secret known-working marker for the current environment (`#174`)
  - [x] P61.3a Write `%USERPROFILE%\\.config\\femic\\arbutus-status.yaml` only after successful validation.
  - [x] P61.3b Mark saved state stale when host/user, env file mtime, profile config, shell env, or validation results drift.
  - [x] P61.3c Support optional dataset/remote validation without treating it as globally required for every profile.
- [x] P61.4 Integrate the workflow into existing validation and docs (`#174`)
  - [x] P61.4a Update `prep validate-case` Windows Arbutus messaging to point at the new status/init workflow and current marker state.
  - [x] P61.4b Add a dedicated Windows Arbutus auth/bootstrap guide and update existing developer/public-data docs.
  - [x] P61.4c Update `AGENTS.md` so agents check the status command/marker first instead of improvising auth recovery.
- [x] P61.5 Validate, document, and publish the workflow (`#174`)
  - [x] P61.5a Add focused tests for fresh bootstrap, stale/current markers, legacy compatibility, and dataset remote checks.
  - [x] P61.5b Run targeted CLI/docs validation and keep Sphinx warning-free.
  - [x] P61.5c Post matching GitHub progress comments so the issue trail documents the workflow end to end.
