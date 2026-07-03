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
    - [x] P53.1d4 Rerun the checked-in TSA29 strict named pipeline against the locked recipe surface and record whether the validator reports a clean locked-chain match or the first specific parent-step mismatch.
    - [x] P53.1d5 Purge TSA29 legacy `ria_vri_vclr1p_checkpoint*.feather` fallback surfaces from active code/docs and delete the stale checkpoint files so strict validation cannot silently drift onto them.
    - [x] P53.1d6 Add always-on real-time user-observable runtime output for `femic pipelines run`, including parent-step events, compiled-step subevents, and mirrored live event logs under `runtime/logs/tsr/`.
    - [x] P53.1d7 Add a strict preflight seam-benchmark gate so TSA29 strict named-pipeline runs abort before execution when the selected start surface already disagrees with the locked-chain reference for that seam.
    - [x] P53.1d8 Wire the strict `scratch` seam to the raw-source GLB builder so named-pipeline step 001 validates from clipped VRI/TSA geometry and stops there before step 002.
    - [x] P53.1d9 Add a bounded strict row-2 named-pipeline runbook that materializes the GLB checkpoint from step 001, runs only `thlb_parent_002_*`, and validates that single step against the locked chain.
      - [x] P53.1d9a Normalize the materialized `glb_checkpoint.feather` area columns from clipped geometry so step-002 input area cannot drift back onto preserved source-layer area attributes.
      - [x] P53.1d9b Sequence strict scratch pipelines over the locked parent-step recipe order so milestone rows validate in place and each transformation row chains its bounded output checkpoint into the next locked step.
      - [x] P53.1d9c Add an explicit strict `glb` seam so step-002 validation can start from the saved validated GLB checkpoint without rebuilding row 1.
      - [x] P53.1d9d Fix strict row-2 named-pipeline fallback accounting so the NStQ/Tsilhqot'in direct-target residual is not double-counted when the locked row-2 parent already carries the combined parent-level marginal contract.
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
    - [x] P53.1d11 Preserve strict-chain checkpoint THLB state across locked parent-step handoff so each step starts from the previous step's managed-area state instead of reinitializing to GLB.
    - [x] P53.1d12 Validate strict row 4 from the row-3 checkpoint and record the first roads-and-landings mismatch.
    - [x] P53.1d13 Persist strict row-4 aspatial area fallback deductions into chained THLB state before any row-5 validation.
    - [x] P53.1d14 Validate strict row 5 as a reference-only milestone from the validated row-4 checkpoint and record the first checkpoint-area helper mismatch before advancing to row 6.
    - [x] P53.1d15 Make strict reference-only checkpoint-area validation honor carried `thlb_fact` state when `_stand_area_sqm` is absent, then rerun row 5 only.
    - [x] P53.1d16 Validate the production strict named-pipeline GLB -> AFLB single-pass runbook through row 5 before advancing into AFLB -> LHLB.
    - [x] P53.1d17 Validate the production strict named-pipeline AFLB -> LHLB stage through row 12 and record the first row-6 locked-state blocker before advancing into LHLB -> THLB.
    - [x] P53.1d18 Reconcile strict row-6 locked recipe approval/ratchet-state semantics and validate AFLB -> LHLB from the validated AFLB checkpoint without replaying GLB -> AFLB.
    - [x] P53.1d19 Repair or materialize the strict row-7 OGMA source/removal path, then rerun only the AFLB -> LHLB suffix from the row-6 strict-chain checkpoint.
    - [x] P53.1d20 Validate strict row 8 from the relocked post-row-7 checkpoint before advancing farther through AFLB -> LHLB.
    - [x] P53.1d21 Reconcile or relock strict row 8 to the reproducible chained wildlife-habitat result before advancing to row 9.
    - [x] P53.1d22 Validate strict row 9 from the relocked post-row-8 checkpoint before advancing farther through AFLB -> LHLB.
    - [x] P53.1d23 Reconcile or relock strict row 9 to the reproducible chained critical-fish-habitat result before advancing to row 10.
    - [x] P53.1d24 Validate strict row 10 from the relocked post-row-9 checkpoint before advancing farther through AFLB -> LHLB.
    - [x] P53.1d25a Reuse SHA-verified LU partition caches across content-identical strict-chain checkpoint aliases before rerunning row 11.
    - [x] P53.1d25b Preserve LU-parallel output partitions as the next strict-chain checkpoint cache before rerunning row 11.
    - [x] P53.1d25c Normalize row-11 legal-planning attribute-slot filters and narrow the Community Areas of Special Concern source selection before advancing to row 12.
    - [x] P53.1d25d Adjudicate the repaired row-11 CASC result against the locked and TSR benchmarks before advancing to row 12.
    - [x] P53.1d25 Validate strict row 11 from the row-10 reviewed-skip checkpoint before advancing farther through AFLB -> LHLB.
    - [x] P53.1d26 Convert row 12 into an explicit aspatial PRA bridge sized to land the AFLB -> LHLB stage on the TSR cumulative target, then validate row 12 only from the relocked post-row-11 checkpoint.
    - [x] P53.1d27 Validate strict row 13 from the zero-delta post-row-12 checkpoint before advancing farther through LHLB -> THLB.
    - [x] P53.1d28 Reconcile or relock strict row 13 to the reproducible zero-delta-post-row-12 result before advancing to row 14.
    - [x] P53.1d29 Repair strict LHLB seam publication so row 13 auto-publishes the official `lhlb_checkpoint` / `lhlb_curve_ready_checkpoint` restart artifacts, then resume row 14 from that seam.
    - [x] P53.1d30 Validate strict row 14 from the official `lhlb_curve_ready_checkpoint` restart seam before advancing to row 15.
    - [x] P53.1d31 Relock strict row 14 to the reproducible official curve-ready seam result before advancing to row 15.
    - [x] P53.1d32 Probe strict row 15 from the official `lhlb_curve_ready_checkpoint` restart seam and record whether the late-stage runner reproduces the locked contract or exposes the next seam defect.
    - [x] P53.1d33 Relock strict row 15 to the reproducible official curve-ready seam rerun result before advancing to row 16.
    - [x] P53.1d34 Backtrack to the last clean chained point and relock row 14 to the true chained step-13 -> step-14 result before advancing to a true chained row 15.
    - [x] P53.1d35 Validate the true chained step-15 result by deriving curve-ready fields onto the rebuilt step-14 output and running only step 15.
    - [x] P53.1d36 Relock row 15 to the true chained step-14 -> step-15 result before any row-16 execution.
    - [x] P53.1d37 Validate the true chained step-16 result by deriving the needed curve-ready fields onto the rebuilt step-15 output and running only step 16.
    - [x] P53.1d38 Harden TSR source-artifact materialization checks so annex pointer stubs are treated as unmaterialized blockers before GIS reads, then return to the row-16 rerun.
    - [x] P53.1d39 Relock row 16 to the true chained step-15 -> step-16 result before any row-17 execution.
    - [x] P53.1d40 Validate the true chained step-17 result by running only step 17 from the rebuilt row-16 output.
    - [x] P53.1d42 Add strict parent-step source-artifact auto-materialization/preflight so annex-backed GIS inputs are materialized before LU work starts and only hard-fail when materialization still cannot produce a readable payload (`#184`).
    - [x] P53.1d41 Materialize the PSP source artifact required by row 17 and rerun only step 17 from the rebuilt row-16 output.
    - [x] P53.1d43 Audit and repair the row-17 PSP overlay input/filter surface so the chained strict deduction does not undercut the previous benchmark because of a shrunken source geometry contract.
    - [x] P53.1d44 Search for a broader benchmark-equivalent public/materializable row-17 geometry surface and confirm whether it is admissible in the reproducible pipeline.
    - [x] P53.1d45 Relock row 17 to the current public/materializable chained PSP result when no broader admissible public geometry surface can be found.
    - [x] P53.1d46 Run only step 18 from the rebuilt row-17 output.
    - [x] P53.1d47 Preserve true LU-granular cache records across chained strict late-stage steps so downstream runs do not warm-start from worker-bundle mega-chunks.
    - [x] P53.1d48 Relock row 18 to the true chained step-17 -> step-18 result after rebuilding the row-17 LU cache to true LU chunks.
    - [x] P53.1d49 Run only step 19 from the rebuilt row-18 output.
    - [x] P53.1d50 Relock row 19 to the true chained step-18 -> step-19 result before any row-20 execution.
    - [x] P53.1d51 Run only step 20 from the rebuilt row-19 output.
    - [x] P53.1d52 Relock row 20 to the true chained step-19 -> step-20 result before any row-21 execution.
    - [x] P53.1d53 Run only step 21 from the rebuilt row-20 output.
    - [x] P53.1d54 Relock row 21 to the true chained step-20 -> step-21 result before any row-23 execution.
    - [x] P53.1d55 Run only step 23 from the rebuilt row-21 output.
    - [x] P53.1d56 Relock row 23 to the true chained step-21 -> step-23 result before any downstream execution.
    - [x] P53.1d59 Normalize the `femic-public-data` parent pointer to the current canonical submodule head and purge the TSA29 generated runtime/output noise so downstream work starts from a clean tracked state.
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
- [x] P60.2 Define the canonical FEMIC-native MKRF instance layout using K3Z/TSA29 patterns (`#173`)
  - [x] P60.2a Decide the canonical repo/instance/runtime/doc surface layout before source-driven rebuild work starts.
  - [x] P60.2b Define the rebuild sequencing and validation contracts for the new instance lane.
  - [x] P60.2c Keep benchmark/reference artifacts clearly separated from the new source-faithful build surfaces.
- [x] P60.3 Reconstruct the raw-source geometry-to-runtime pipeline from `03_MappingAnalysisData/*` (`#173`)
  - [x] P60.3a Rebuild the geometry publication path from upstream source surfaces rather than accepted compiled-runtime substitutes.
  - [x] P60.3b Rebuild the runtime spatial/package handoff with explicit lineage and acceptance checks.
  - [x] P60.3c Keep checkpoint-derived or compiled-runtime artifacts out of the source-faithful rebuild claim surface.
- [x] P60.4 Rebuild the target/control lane from reviewed source contracts instead of legacy checkpoint loading (`#173`)
  - [x] P60.4a Replace the PoC checkpoint-backed target-control lane with a source-driven FEMIC-native control surface.
  - [x] P60.4b Reconstruct or replace legacy scenario-target semantics only where they are justified by source evidence or benchmark necessity.
  - [x] P60.4c Keep unexplained legacy compiled control seams out of the new build unless they become required by a documented acceptance gate.
  - [x] P60.4d Define the canonical AU key and AU-wise first-growth curve lane before runtime generation.
- [x] P60.5 Build the canonical AU table and AU-wise first-growth curve lane (`#173`)
  - [x] P60.5a Define and publish the canonical AU table from source geometry using `bec_zone + bec_subzone + bec_variant + ordered top-2 leading species`.
  - [x] P60.5b Assign source stands/records to the canonical AUs and publish assignment lineage and diagnostics.
  - [x] P60.5c Compile AU-wise first-growth VDYP curves with FEMIC NLLS and publish fit diagnostics and acceptance checks.
  - [x] P60.5d Publish the canonical top-N AU selection using a `95%` cumulative-area coverage rule so downstream runtime generation consumes an explicit selected AU subset rather than the full AU universe by default.
  - [x] P60.5e Recompile the canonical AU strata, diagnostic VDYP, and VDYP-vs-TIPSY plots from the selected-AU bundle.
- [x] P60.6 Build the provisional managed AU-wise TIPSY/BTC lane (`#173`)
  - [x] P60.6a Publish the canonical managed AU bootstrap table from legacy managed evidence.
  - [x] P60.6b Build an AU-wise BTC `msyt.csv` input surface for planted stands.
  - [x] P60.6c Attempt BTC and publish AU-wise managed/planted curves or an explicit blocker manifest.
  - [x] P60.6d Record the provisional claim boundary for the managed bootstrap lane.
  - [x] P60.6e Replace the legacy-managed bootstrap ceiling with an expert-rule managed compile driven by `AGE_2020` origin classes and MKRF planning guidance captured in `config/tipsy/tsamkrf.yaml`.
- [x] P60.7 Fix bad curve cases before canonical runtime generation (`#177`)
  - [x] P60.7a Audit the bad first-growth and managed comparison cases against raw source rows, assignment lineage, and fit diagnostics.
  - [x] P60.7b Correct the source field choice, grouping, assignment, or fit logic as needed and regenerate the affected curve bundles.
  - [x] P60.7c Rebuild the canonical diagnostic/comparison plots and record the curve-quality acceptance gate for downstream runtime generation.
- [x] P60.8 Rebuild the full MKRF runtime package from source-faithful inputs (`#173`)
  - [x] P60.8a Generate the runtime XML, tracks, and control surfaces from the new FEMIC-native rebuild lane, consuming AU-wise unmanaged/first-growth curves rather than legacy stand-wise first-growth curves.
  - [x] P60.8b Re-run Matrix Builder and runtime assembly against the rebuilt source-faithful package.
  - [x] P60.8c Keep generated outputs and lineage surfaces synchronized as the new canonical MKRF runtime package.
- [x] P60.9 Validate the rebuilt model against the PoC benchmark and legacy evidence (`#173`)
  - [x] P60.9a Compare the rebuilt runtime against the accepted PoC benchmark surfaces.
    - [x] P60.9a1 Add PoC-style state/seral parity families to the canonical rebuild runtime surface.
    - [x] P60.9a2 Add managed yield/product breadth parity for merch-total and species-split families from rebuild-owned managed payloads.
    - [x] P60.9a3 Add unmanaged yield parity families from the canonical first-growth/runtime curve lane, including rebuild-owned unmanaged `indsp.*` feature/account parity from `stand_au_assignment.csv` species-share aggregation.
    - [x] P60.9a4 Compare canonical vs PoC `accounts.csv`, `features.csv`, and `products.csv` by family presence and record achieved parity versus accepted/source-blocked gaps.
  - [x] P60.9b Compare the rebuilt model against the legacy control/entrypoint evidence that still matters for acceptance, especially the benchmark `base.pin` / `ScenarioSet.bsh` / target-description helper lane.
  - [x] P60.9c Record which observed differences are accepted redesign choices versus unresolved regressions.
- [x] P60.10 Publish closeout docs and decide whether `#172` can close (`#173`)
  - [x] P60.10a Update the parent and instance docs/runbooks to teach the new MKRF rebuild lane, especially the parent pointer docs and the still-PoC-framed instance docs surfaces.
  - [x] P60.10b Record the final claim boundary between benchmark archaeology and the new source-faithful rebuild.
  - [x] P60.10c Publish a minimal canonical runnable control lane for `models/mkrf_patchworks_model/` and prove one real even-flow harvest-volume smoke on the canonical package.
  - [x] P60.10d Decide whether the umbrella legacy-recovery issue `#172` can close once the from-scratch rebuild phase is complete.
  - [x] P60.10e Repair MKRF runtime semantics so IFM (`managed/unmanaged`) is decoupled from curve provenance (`natural/treated`), add species-signal sanity audits, and update parent agent-facing Patchworks guardrails.

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

## Phase 62: Publish the First Canonical MKRF Alpha Release

- [x] P62.1 Prepare and merge the MKRF canonical `v0.0.1a1` release PR lane (`#173`)
  - [x] P62.1a Commit and push the current parent and instance repo releaseable state on explicit branches.
  - [x] P62.1b Open and merge the required GitHub PRs so both repos have the canonical `v0` checkpoint on their default branches.
  - [x] P62.1c Keep the release note, docs, and submodule pointer surfaces synchronized across both repos.
- [x] P62.2 Publish the `femic-mkrf-instance` `v0.0.1a1` alpha release (`#173`)
  - [x] P62.2a Create the GitHub release/tag `v0.0.1a1` in `femic-mkrf-instance`.
  - [x] P62.2b Mark it explicitly as an alpha / pre-release for developers and very curious testers rather than a production-ready build.
  - [x] P62.2c Summarize the release as the first canonical MKRF rebuild checkpoint after the archaeology -> PoC -> canonical-lane sequence.
- [x] P62.3 Publish the `v0.0.1a1` release announcement and open the next legacy-publication feature issue
  - [x] P62.3a Post a `femic-mkrf-instance` repository discussion announcement for `v0.0.1a1`.
  - [x] P62.3b Summarize the major work completed so far and the cautionary alpha-release boundary.
  - [x] P62.3c Open the follow-on feature issue to publish the full legacy MKRF model inside `femic-mkrf-instance` as a recorded/reference surface for later canonical rebuild iterations.

## Phase 63: Post-Release MKRF Docs Cleanup

- [x] P63.1 Fix stale PoC-only framing that survived the canonical `v0.0.1a1` release (`femic-mkrf-instance#4`)
  - [x] P63.1a Audit the published instance docs for pages that still teach `models/mkrf_patchworks_model_poc/` as the active package.
  - [x] P63.1b Update the affected pages so `models/mkrf_patchworks_model/` is the active runtime/package lane and the PoC package is benchmark/reference evidence only.
  - [x] P63.1c Rebuild instance docs and verify the published operator-facing pages no longer drift back to PoC-only framing.
- [x] P63.2 Publish MKRF strata and yield-curve figure surfaces in the standalone instance docs (`femic-mkrf-instance#5`)
  - [x] P63.2a Audit the existing `plots/` artifact set and select the subset that belongs in the public operator docs.
  - [x] P63.2b Add MKRF docs pages and toctree links for strata distribution plus yield-curve/fit-diagnostic figures, following the proven K3Z figure-gallery pattern.
  - [x] P63.2c Rebuild the standalone instance docs and verify the rendered figure pages publish cleanly.
- [x] P63.3 Fix MKRF docs image publication by moving published figure assets off annex-backed `plots/` (`femic-mkrf-instance#6`)
  - [x] P63.3a Copy the published MKRF figure subset into a docs-owned non-annex asset path.
  - [x] P63.3b Override the instance annex rules for the published docs figure asset path so those PNGs are committed as regular git files.
  - [x] P63.3c Repoint/republish the standalone figure pages and verify the live `_static` figure URLs return actual PNG payloads rather than annex pointer text.
- [x] P63.4 Add canonical MKRF `base.pin` map-layer parity for operator GUI use (`#173`)
  - [x] P63.4a Carry the PoC treatment-layer themes into the canonical generated `analysis/base.pin`.
  - [x] P63.4b Carry the PoC patch-layer themes into the canonical generated `analysis/base.pin` using canonical field names and guards.
  - [x] P63.4c Regenerate the canonical runtime package and verify the generated `analysis/base.pin` exposes the new map-layer block.
- [x] P63.5 Expand canonical MKRF docs for treatment logic, AU/yield mapping, and non-top-N AU remap (`#173`)
  - [x] P63.5a Add standalone instance docs pages for canonical treatment/state logic and AU/yield-curve mapping.
  - [x] P63.5b Update the existing guide pages so operators land on those new logic docs instead of shallow package-only descriptions.
  - [x] P63.5c Rebuild the standalone instance docs and verify the new treatment/AU/remap explanations render warning-clean.

## Phase 64: Restore MKRF CT Legacy Parity

- [x] P64.1 Record the CT legacy-parity contract and current divergence (`#180`)
  - [x] P64.1a Update the roadmap/planning surfaces so the post-`v0.0.1a1` CT follow-up is governed by `#180`.
  - [x] P64.1b Document the exact legacy and PoC CT behavior from source XML, including the `0.4` treatment-year extraction and `0.6` thinned standing lane.
  - [x] P64.1c Record the current canonical CT divergence explicitly so the runtime repair is judged against the legacy/PoC contract rather than ad hoc interpretation.
- [x] P64.2 Repair canonical MKRF CT runtime logic to match legacy/PoC (`#180`)
  - [x] P64.2a Emit the legacy/PoC CT select statement and transition contract in the canonical generator, including `retain="20"` and `au='thn_'+au`.
  - [x] P64.2b Drive THN state/yield behavior from the thinned AU lane while preserving canonical CC regeneration behavior back to the treated/post-clearcut lane.
  - [x] P64.2c Split CT treatment-year extracted products (`0.4 * base curve`) from post-CT standing THN yields (`0.6 * base curve(x)`).
- [x] P64.3 Prove CT parity in tests, rebuilt runtime outputs, and published docs (`#180`)
  - [x] P64.3a Add focused regression coverage for CT select/transition semantics and the legacy `0.4`/`0.6` split.
  - [x] P64.3b Regenerate the canonical runtime package, rerun Matrix Builder, and rerun the canonical even-flow smoke at `100000` iterations.
  - [x] P64.3c Inspect representative rebuilt CT-active outputs, keep parent/instance docs warning-clean, and record the parity result in repo/GitHub surfaces.

## Phase 65: Publish the Full Legacy MKRF Package as an Archival Reference Lane

- [x] P65.1 Record the archival-publication contract and inventory the already-copied legacy payload (`femic-mkrf-instance#1`)
  - [x] P65.1a Update roadmap/planning surfaces so the next MKRF lane is governed by `femic-mkrf-instance#1`.
  - [x] P65.1b Confirm which legacy controls, tracks, spatial files, and generated XML surfaces are already present under `external/femic-mkrf-instance/data/legacy_mkrf/`.
  - [x] P65.1c Define the archival-only publication boundary so the canonical rebuild lane remains the active runtime surface.
- [x] P65.2 Publish a first-class legacy archive doc lane inside `femic-mkrf-instance` (`femic-mkrf-instance#1`)
  - [x] P65.2a Add explicit instance docs/README coverage for the complete legacy package surface and how it differs from the PoC and canonical lanes.
  - [x] P65.2b Link the archive surface from the operator/lineage docs so later developers can inspect the full legacy package locally without reopening the archaeology program.
  - [x] P65.2c Rebuild the standalone instance docs warning-clean after wiring the new legacy-archive surface into the guide.
- [x] P65.3 Close the archival-publication issue with repo and tracker hygiene (`femic-mkrf-instance#1`)
  - [x] P65.3a Post a final `femic-mkrf-instance#1` comment summarizing the published archival lane and its boundary.
  - [x] P65.3b Push the instance and parent pointer updates required for the published docs/metadata state.
  - [x] P65.3c Close `femic-mkrf-instance#1` once the archival lane is documented and the canonical lane remains the default.

## Phase 66: Redesign MKRF CT Response Beyond Legacy Parity

- [x] P66.1 Record the redesign contract and release framing (`#182`)
  - [x] P66.1a Update roadmap/planning surfaces so the next MKRF modeling lane is governed by `#182`.
  - [x] P66.1b Record the legacy proportional-gap CT model as benchmark/reference only and the bucketed constant-absolute-gap CT model as the new canonical target.
  - [x] P66.1c Record that the release boundary for this redesign is `v0.0.2a1`, not a continuation of `v0.0.1a1`.
- [x] P66.2 Replace canonical MKRF CT with a bucketed constant-absolute-gap standing-yield model (`#182`)
  - [x] P66.2a Replace the single schedulable `CT` treatment with 10-year midpoint CT bucket treatments (`CT40`, `CT50`, `CT60`, ...) covering age windows such as `35-44`, `45-54`, and `55-64`.
  - [x] P66.2b Emit per-bucket thinned AU/state lanes so each bucket uses a precompiled constant-absolute-gap post-CT standing response anchored to the bucket midpoint age.
  - [x] P66.2c Preserve explicit CT treatment-year extraction, thinned-lane semantics, and CC follow-on behavior while keeping the bucketed redesign as the canonical default rather than an experimental sidecar.
- [x] P66.3 Prove the redesign against runtime outputs, docs, and release framing (`#182`)
  - [x] P66.3a Add focused regression coverage for the bucketed constant-absolute-gap CT behavior and its difference from the legacy proportional-gap rule.
  - [x] P66.3b Regenerate the canonical runtime package, rerun Matrix Builder, and rerun the canonical `100000`-iteration even-flow smoke.
  - [x] P66.3c Inspect representative lower-bucket and higher-bucket CT outputs, confirm CT-vs-no-CT full-rotation harvested-volume behavior, rebuild parent/instance docs warning-clean, and record the `v0.0.2a1` framing in repo/GitHub surfaces.

## Phase 67: Promote Smoothed AU-Level VDYP First-Growth Curves Beyond MKRF

- [x] P67.1 Record the shared/default promotion lane for AU-level first-growth VDYP synthesis (`#187`)
  - [x] P67.1a Open the parent feature issue with the accepted MKRF evidence basis, rationale, and default-method acceptance criteria.
  - [x] P67.1b Open the TSA29-only child issue and record the downstream adoption boundary (`#188`).
- [x] P67.2 Promote `smoothed_bin_pchip` to the default AU-level first-growth / unmanaged VDYP synthesis method (`#187`)
  - [x] P67.2a Audit where first-growth default-selection currently lives across the MKRF-specific builder and reusable VDYP-stage machinery.
  - [x] P67.2b Expose the promoted default without breaking legacy callers that still rely on older NLLS-oriented behavior.
  - [x] P67.2c Update docs/contracts/tests so `smoothed_bin_pchip` is the official default and NLLS is clearly legacy/fallback.
- [x] P67.3 Adopt the promoted default on the TSA29 instance lane (`#188`)
  - [x] P67.3a Switch the TSA29 AU-level first-growth build path to the promoted default and regenerate the relevant instance outputs.
  - [x] P67.3b Patch the promoted selector to suppress low-age humps, far-right tail bumps, excess wobble, and bad toe shape, then rerun TSA29 diagnostics/outputs.
  - [x] P67.3c Validate TSA29 residual/shape diagnostics against AU binned medians and record explicit insufficient-support AU treatment.

## Phase 68: TSA29 Comparison Plot Refresh and Instance Docs Rebuild

- [x] P68.1 Review and lock the TSA29 TIPSY-vs-VDYP comparison plot library (`UBC-FRESH/femic-tsa29-instance#4`)
  - [x] P68.1a Confirm the accepted comparison family is the refreshed `54`-plot set:
    - `plots/tipsy_vdyp_tsa29-21000..21017.png`
    - `plots/tipsy_vdyp_tsa29-22000..22017.png`
    - `plots/tipsy_vdyp_tsa29-23000..23017.png`
  - [x] P68.1b Explicitly retire the stale `.out`-derived `30`-plot assumption from Phase 68 notes, docs, and acceptance checks.
  - [x] P68.1c Keep the comparison-plot acceptance work isolated on `external/femic-tsa29-instance` branch `feature/tsa29-tipsy-vdyp-comparison-refresh`.
  - [x] P68.1d Lock the accepted comparison plot set with the committed instance artifact refresh and issue updates; defer the final branch/PR bundle to overall Phase 68 closeout rather than treating the plot contract itself as still open.
  - [x] P68.1e Normalize the parent/runtime handoff contract to make BTC CSV the only canonical TIPSY input/output lane (`#190`), then remove TSA29 DAT/`.out` trap artifacts.
  - [x] P68.1f Audit the official TSR 2024 managed-AU taxonomy against the current TSA29 managed/TIPSY lane and build a cross-reference table for rule coverage and catchall hits.
  - [x] P68.1g Reduce `tsa29_all_aus_catchall` dominance before the next TSA29 BTC/TIPSY rerun by:
    - promoting the obvious Table 40-aligned managed-AU families out of catchall into explicit TSA29 proxy rules;
    - lowering the residual fallback plantation density to `1100` stems/ha; and
    - resetting the TSA29 treated SI transform to the user-requested `SI_c1=1.0`, `SI_c2=0.0` for the next clean shape-read rerun.
  - [x] P68.1h Re-anchor the TSA29 TIPSY comparison rerun on current live builder output, not stale exported workbook/CSV artifacts, and verify there are no inverted `L/M/H` SI ladders in the rebuilt managed AU surface before regenerating comparison plots.
    - use fresh regenerated canonical TIPSY input artifact (`03_input-tsa29.csv`) as the only admissible rerun input surface;
    - apply the additional agreed remaps before rerun:
      - explicit remaps:
        - expand the ICH cedar proxy to match the `HW` alias that appears on live TSA29 cedar rows;
        - pin `MS_PL` low-site rows back into the existing MS pine proxy; and
        - pin `SBPS_PL` / `SBPS_PLI` high-site rows back into the existing poor-site SBPS pine proxy; and
      - provisional remap notes:
        - `ESSF_PL`, `ESSF_PLI`, `ICH_SX`, and `SBPS_SX` remain unresolved local-extension families and should stay out of any silent auto-remap in this bounded move;
    - rerun BTC/post-TIPSY only after those remaps are on the live builder surface and validated.
  - [x] P68.1i Remove the dead-end TSA29 workbook mirror from the active comparison/docs lane so Phase 68 uses only the canonical CSV handoff surface.
  - [x] P68.1j Apply narrow provisional treated-side SI uplift pins for the remaining weak low-yield TIPSY families, regenerate fresh `03_input-tsa29.csv`, rerun BTC/post-TIPSY, and compare the refreshed overlays on the CSV-only lane.
  - [x] P68.1k Remove the dead workbook dependency from the legacy post-TIPSY comparison-plot seam so `femic tsa btc-post-tipsy` can complete on the CSV-only TSA29 lane.
- [x] P68.2 Reread and rebuild TSA29-instance docs/figure surfaces (`UBC-FRESH/femic-tsa29-instance#3`)
  - [x] P68.2a Reread the instance docs with focus on pages that mention or embed yield-curve comparisons.
  - [x] P68.2b Update figure references, galleries, counts, and narrative interpretation to match the accepted `54`-plot comparison library.
  - [x] P68.2c Refresh any docs pages that should surface the accepted comparison plots, including yield-curve and figure-appendix style pages if present.
  - [x] P68.2d Run the TSA29-instance Sphinx build and keep it warning-clean.
  - [x] P68.2e Lock the docs refresh with an instance commit, issue update, and PR.

## Phase 69: MKRF CT Fd-Leading Follow-Up and Hw Ingrowth Recalibration

- [x] P69.1 Record the Anna/Sean CT follow-up contract (`UBC-FRESH/femic-mkrf-instance#15`)
  - [x] P69.1a Open the follow-up parent and child issue set for broadened Cw/Fd eligibility, CT species priority, Hw ingrowth recalibration, and full runtime QA (`UBC-FRESH/femic-mkrf-instance#16`-`#19`).
  - [x] P69.1b Update parent and instance planning surfaces so the follow-up is governed by `UBC-FRESH/femic-mkrf-instance#15`, not reopened under the closed CT implementation parent `#8`.
- [x] P69.2 Broaden the canonical MKRF CT eligibility and prescription surface (`UBC-FRESH/femic-mkrf-instance#16`, `#17`)
  - [x] P69.2a Replace the strict `Cw >15%` species gate with inclusive base planted `Cw + Fd >=50%` so Fd-leading and pure-Fd-style plantations are not excluded solely because `Cw == 0`.
  - [x] P69.2b Document and implement CT retention/removal priority as retain Cw first, then Fd; remove Hw first, then Fd only as needed for the active removal target.
  - [x] P69.2c Regenerate CT eligibility and intensity audits and sync the eligible-AU contract/config lists to the regenerated 26-of-31 AU result.
- [x] P69.3 Recalibrate planted Hw ingrowth and prove the runtime (`UBC-FRESH/femic-mkrf-instance#18`, `#19`)
  - [x] P69.3a Change the landscape planted-Hw ingrowth default from `50%` to `30%` while preserving AU-level and stand-level override surfaces.
  - [x] P69.3b Document Anna's 18-survey MKRF evidence as the active parameter basis and Jaeck et al. 1984 as supporting context.
  - [x] P69.3c Regenerate managed inputs, runtime package, CT/Hw audit artifacts, Matrix Builder tracks, and the default `mkrf.base` smoke; run saved-stage sanity audit and targeted pytest.
- [x] P69.4 Publish the follow-up branch bundle and tracker closeout (`UBC-FRESH/femic-mkrf-instance#15`)
  - [x] P69.4a Post implementation/QA comments back to `#16`-`#19` and the parent `#15`.
  - [x] P69.4b Commit and push the instance and parent follow-up branches with the submodule pointer update.
  - [x] P69.4c Open the follow-up PRs for the instance/runtime package and parent FEMIC pointer/code changes.
  - [x] P69.4d Close the issue set once `UBC-FRESH/femic-mkrf-instance#20` and `UBC-FRESH/femic#193` are reviewed/merged.

## Phase 70: MKRF Patchworks Map-Layer Presentation Fix

- [x] P70.1 Record the Patchworks GUI map-layer bug (`UBC-FRESH/femic-mkrf-instance#21`)
  - [x] P70.1a Open the bug issue for treatment legend labels, forest outline presentation, and age-class layer coverage.
- [x] P70.2 Update the canonical MKRF ``base.pin`` map-layer generator (`UBC-FRESH/femic-mkrf-instance#21`)
  - [x] P70.2a Replace generic CT legend entries with the active treatment labels ``CT35``, ``CT40``, and ``CT45`` for current/latest treatment layers.
  - [x] P70.2b Rename/restyle the default block layer as a very light gray ``Forest Outline`` context layer.
  - [x] P70.2c Add a hidden-by-default ``Age Class (20-year)`` layer keyed to dynamic mean fragment age via ``0.5 * (MANAGEDOFFSET + UNMANAGEDOFFSET)`` with an explicit yellow-green graduated color ramp.
- [x] P70.3 Prove the map-layer fix against generated artifacts and runtime smoke (`UBC-FRESH/femic-mkrf-instance#21`)
  - [x] P70.3a Regenerate the canonical runtime package so ``models/mkrf_patchworks_model/analysis/base.pin`` carries the updated map layers.
  - [x] P70.3b Run targeted pytest, Patchworks preflight, default ``mkrf.base`` smoke, saved-stage sanity audit, and instance docs build.
- [x] P70.4 Publish the map-layer bugfix branch and close issue `UBC-FRESH/femic-mkrf-instance#21`
  - [x] P70.4a Push the instance and parent branches and open PRs.
  - [x] P70.4b Merge the instance/runtime PR, then merge the parent generator/submodule-pointer PR.
  - [x] P70.4c Close issue `UBC-FRESH/femic-mkrf-instance#21` after PR merge.

## Phase 71: Rebuild the TSA29 Patchworks Model on the New THLB and Yield Surfaces

- [x] P71.1 Record and initialize the TSA29 Patchworks-rebuild lane (`UBC-FRESH/femic-tsa29-instance#6`)
  - [x] P71.1a Open the TSA29-instance feature issue for rebuilding the
    Patchworks model on the newly accepted THLB and yield surfaces.
  - [x] P71.1b Create the dedicated parent/submodule feature branches for that
    rebuild lane.
  - [x] P71.1c Record the requirement that past-top-N strata must receive AU
    assignment through the lexicographical stratum-matching imputation logic so
    no surviving AFLB area is silently left out of the model.
- [x] P71.2 Rebuild TSA29 model-input and Patchworks package surfaces on the new inputs
  - [x] P71.2a Regenerate the TSA29 model-input bundle from the current locked
    THLB and accepted curve libraries.
  - [x] P71.2b Rebuild the TSA29 Patchworks package on that regenerated bundle,
    including any required past-top-N AU imputation.
  - [x] P71.2c Inspect the rebuilt Patchworks-facing outputs directly rather
    than treating command success as proof.
- [x] P71.3 Validate and publish the refreshed TSA29 model package
  - [x] P71.3a Run the necessary Patchworks-facing validation checks on the
    rebuilt package.
  - [x] P71.3b Update TSA29 instance docs/evidence surfaces for the refreshed
    package if the rebuild is accepted.
  - [x] P71.3c Close the governing issue and publish the resulting branch/PR
    updates.

## Phase 72: Publish the TSA29 `v1.0.0-alpha1` Release

- [x] P72.1 Prepare the TSA29 release lane and merge gate (`UBC-FRESH/femic-tsa29-instance#8`)
  - [x] P72.1a Open the governing TSA29-instance release issue for the `v1.0.0-alpha1` milestone.
  - [x] P72.1b Treat the release boundary as post-merge only: do not cut the release from `feature/tsa29-patchworks-rebuild-new-inputs`; first merge:
    - `UBC-FRESH/femic-tsa29-instance#7`
    - `UBC-FRESH/femic#195`
  - [x] P72.1c Refresh the release-facing TSA29 docs/notes so the alpha milestone is described as:
    - the first standalone TSA29 release where the Patchworks model rebuilds, launches, and produces sane output on the accepted THLB/yield lane; and
    - an alpha-quality research/prototype milestone rather than a final production contract.
- [x] P72.2 Publish `femic-tsa29-instance` `v1.0.0-alpha1`
  - [x] P72.2a Fast-forward the TSA29 instance checkout to merged `main` and verify the merged release candidate surfaces directly.
  - [x] P72.2b Confirm the launch-critical DataLad/annex payloads and release-facing evidence/docs are in the intended published state.
  - [x] P72.2c Create the `v1.0.0-alpha1` tag and GitHub pre-release in `UBC-FRESH/femic-tsa29-instance`.
  - [x] P72.2d Record the release in the parent changelog/planning surfaces and publish the matching closeout comments.

## Phase 73: MKRF Stand Stratification Revisions

- [x] P73.1 Record the MKRF stand-stratification revision issue set (`UBC-FRESH/femic-mkrf-instance#25`)
  - [x] P73.1a Open separate child issues for minor-strata aggregation and major-strata site-series splitting (`UBC-FRESH/femic-mkrf-instance#26`, `#27`).
  - [x] P73.1b Record the BEC field-guide reference and Anna's note that the major-stratum split logic remains TBD for the site-series child.
- [x] P73.2 Implement the reviewed minor-strata aggregation pass (`UBC-FRESH/femic-mkrf-instance#26`)
  - [x] P73.2a Add explicit raw-to-canonical AU aggregation before selected-AU publication for:
    - `cwh_vm_2_ba_hw` -> `cwh_vm_2_hw_ba`
    - `cwh_dm_x_dr_mb` -> `cwh_dm_x_dr_act`
    - `cwh_dm_x_cw_dr` -> `cwh_dm_x_dr_cw`
    - `cwh_vm_1_ba_hw` -> `cwh_vm_1_hw_ba`
    - `cwh_vm_1_fdc_hw` -> `cwh_vm_1_fdc_x`
  - [x] P73.2b Preserve raw AU lineage in `stand_au_assignment.csv` and add `au_aggregation_audit.csv` so the aggregation is reviewable.
  - [x] P73.2c Regenerate AU inputs, selected AU table, managed inputs, managed curves, runtime package, Matrix Builder tracks, and the default `mkrf.base` smoke.
  - [x] P73.2d Fix runtime first-growth summary counts so manifests/XML report the selected runtime AU surface after aggregation.
  - [x] P73.2e Update MKRF docs/runbook surfaces for the AU aggregation audit and validation lane.
- [ ] P73.3 Publish the aggregation branch bundle and close child issue `UBC-FRESH/femic-mkrf-instance#26`
  - [ ] P73.3a Commit and push the instance and parent branches with the regenerated runtime artifacts and submodule pointer update.
  - [ ] P73.3b Post QA commands, run IDs, and audit summary back to `#26`.
  - [ ] P73.3c Open the instance and parent PRs for review.

## Phase 74: Bootstrap the TFL 6 FRST 558 Teaching Instance

- [x] P74.1 Create and link the standalone TFL 6 instance repository (`#199`)
  - [x] P74.1a Create the standalone teaching-instance repository, now
    `UBC-FRESH/femic-tfl6-instance`.
  - [x] P74.1b Add it under `external/femic-tfl6-instance` as a FEMIC
    submodule.
  - [x] P74.1c Seed the repository with FEMIC instance scaffolding and the
    modelwright-style workflow surfaces (`AGENTS.md`, `ROADMAP.md`,
    `CHANGE_LOG.md`, and `planning/`).
- [x] P74.2 Complete the instance Phase 1 bootstrap/build-plan gate (`#199`)
  - [x] P74.2a Inventory source payloads, record the TFL 6 AOI pivot, and
    materialize accepted 2025 VRI source/archive inputs without publishing
    machine-specific paths.
  - [x] P74.2b Record the K3Z-template adaptation boundary, TFL 6 source-layer
    and THLB recipe-planning surfaces, and adjusted teaching-validation
    benchmark targets.
  - [x] P74.2c Split cedar design, expansion design, runtime-package work, and
    future Phase 2 through Phase 5 parent/child issue trees before model
    compilation starts.
- [ ] P74.3 Complete Phase 1 closeout and merge the parent FEMIC PR (`#199`,
  `#200`)
  - [x] P74.3a Resolve the parent roadmap Phase 73 collision by preserving MKRF
    as Phase 73 and renumbering the TFL 6 bootstrap lane to Phase 74.
  - [ ] P74.3b Merge parent PR `UBC-FRESH/femic#200` after conflict resolution
    and required closeout checks.
  - [ ] P74.3c Close instance Phase 1 parent `UBC-FRESH/femic-tfl6-instance#4`
    after the parent FEMIC PR has merged.

## Phase 75: Evaluate `bcdata` and `designatedlands` for BC Data Discovery

- [x] P75.1 Create the side-by-side comparison contract (`#201`)
  - [x] P75.1a Audit FEMIC's current BCDC resolver/fetch/DWDS surfaces and
    document the comparable commands/APIs.
  - [x] P75.1b Define a fixed comparison corpus from known modelling
    source-layer discovery problems, including TFL 6/TSA-style RMZ, OGMA,
    shoreline/coastline, operability terrain/DEM, FADM/TFL boundary, DRA, FWA,
    and VRI queries.
  - [x] P75.1c Record the metrics for candidate recall, ranking,
    resource-classification accuracy, direct-download/WFS support, failure
    modes, speed, and reproducibility.
  - [x] P75.1d Add BC Gov `designatedlands` as a source-manifest and
    workflow-comparison input, especially for protected/designated lands,
    forestry restriction classes, overlap handling, and source CSV metadata.
- [x] P75.2 Run the `bcdata` versus FEMIC comparison (`#201`)
  - [x] P75.2a Capture baseline FEMIC resolver outputs for the comparison
    corpus.
  - [x] P75.2b Capture equivalent `bcdata` outputs with a reproducible R
    script or CLI harness.
  - [x] P75.2c Summarize cases where `bcdata` finds better, faster, more
    reliable, or otherwise useful results than FEMIC.
- [x] P75.3 Decide the integration boundary (`#201`)
  - [x] P75.3a Compare no-adoption, reference-oracle, optional `Rscript`
    bridge, and embedded Python-to-R dependency options.
  - [x] P75.3b Explicitly decide whether `reticulate` is relevant or the wrong
    dependency direction for FEMIC.
  - [x] P75.3c Compare `designatedlands` as a source-manifest reference,
    candidate recipe pattern, or external workflow to mine, rather than a
    lightweight FEMIC runtime dependency.
  - [x] P75.3d Record dependency, installation, CI, Windows, database, GDAL,
    and offline/cache implications before implementation.
- [x] P75.4 Implement the accepted path only if the comparison justifies it
  (`#201`)
  - [x] P75.4a Add the smallest maintainable optional bridge or FEMIC resolver
    improvements supported by the comparison results.
  - [x] P75.4b Add tests, CLI/API docs, and dependency guidance for any adopted
    path.
  - [x] P75.4c Record that the benchmark justified native resolver
    improvements, so the no-change branch is not the accepted path.

## Phase 76: THLB Checkpoint Input Format Support

- [x] P76.1 Accept explicit GeoPackage THLB checkpoint inputs (`#203`)
  - [x] P76.1a Preserve TSA29 legacy checkpoint rejection while documenting why
    Feather restart seams remain useful for large repeated runs.
  - [x] P76.1b Update the checkpoint loader so explicit Feather inputs still
    use the fast Feather path and explicit GeoPackage/vector inputs use the
    normal GeoPandas vector reader.
  - [x] P76.1c Update CLI/docs wording and targeted tests for explicit Feather
    and GeoPackage checkpoint inputs.
  - [x] P76.1d Run focused tests/docs validation, update issue comments, and
    publish the branch.

## Phase 77: TFL 6 Parent Documentation Publication

- [x] P77.1 Publish the TFL 6 instance pointer in parent FEMIC docs (`#204`)
  - [x] P77.1a Add TFL 6 to the parent sample-models toctree.
  - [x] P77.1b Add a parent TFL 6 pointer page that links the standalone
    instance repository, submodule path, roadmap, and Phase 2/Phase 3 docs
    surfaces.
  - [x] P77.1c Build parent Sphinx docs warning-clean and open the publication
    PR without starting TFL 6 Phase 4 implementation.
- [x] P77.2 Clarify the selected-AU curve-family and lexicographic remap
  contract in parent FEMIC docs (`#206`).
  - [x] P77.2a Update the Stage 01a and model-input bundle guides so selected
    top-area AU bins are the canonical curve-family universe.
  - [x] P77.2b Cross-reference the TFL 6 and MKRF instance examples that remap
    non-selected AU bins to selected curve families.
  - [x] P77.2c Build parent Sphinx docs warning-clean and keep this docs-only
    fix out of TFL 6 Phase 4 model-input implementation.
- [x] P77.3 Clarify the generic AFLB stand-universe and THLB/NTHLB retention
  contract in parent FEMIC docs and named-pipeline metadata (`#207`).
  - [x] P77.3a Update model-input bundle, Stage 01a, and pipeline-overview docs
    so AFLB/CMFLB is the growth universe and final THLB is a managed-share
    overlay.
  - [x] P77.3b Add named-pipeline registry seam notes so AFLB restart seams are
    described as yield-ready model-universe seams, not final-THLB-only seams.
  - [x] P77.3c Build parent Sphinx docs warning-clean and keep this docs-only
    correction out of TFL 6 bundle-table generation.

## Phase 78: `figrecover` Document-Figure Integration

- [x] P78.1 Plan the `figrecover` integration boundary (`#209`)
  - [x] P78.1a Treat `figrecover` as an optional FEMIC document-ingestion tool,
    not a required core runtime dependency.
  - [x] P78.1b Define where FEMIC wraps `figrecover` versus where users call
    `figrecover` directly for manual chart calibration and review.
  - [x] P78.1c Record the dependency, artifact, provenance, review-status,
    and TFL 6 MP11 pilot boundaries in
    `planning/phase78_figrecover_integration_notes.md`.
- [x] P78.2 Add optional dependency and environment checks (`#209`)
  - [x] P78.2a Add a FEMIC optional extra for figure recovery only after the
    dependency footprint is accepted.
  - [x] P78.2b Add a lightweight CLI preflight that reports whether
    `figrecover` and required PDF/image extras are importable.
  - [x] P78.2c Keep normal FEMIC install, THLB, VDYP, TIPSY, and Patchworks
    workflows working without `figrecover` installed.
- [x] P78.3 Define figure-recovery artifact conventions (`#209`)
  - [x] P78.3a Standardize corpus paths for public PDFs, rendered pages,
    figure crops, calibration specs, recovered CSV/JSON, overlays, review
    manifests, and accepted exports.
  - [x] P78.3b Require page, figure, source URL/checksum, calibration, tool
    version, extraction method, and human-review status before recovered values
    can be referenced by FEMIC planning or model-input work.
  - [x] P78.3c Keep private or unreleasable PDFs, crops, overlays, prompt logs,
    and recovered tables under ignored local paths unless explicitly sanitized.
- [x] P78.4 Add FEMIC CLI/API wrappers for auditable recovery workflows (`#209`)
  - [x] P78.4a Add commands to prepare a PDF corpus and write a figure-candidate
    manifest through `figrecover` when the optional dependency is installed.
  - [x] P78.4b Add commands to register reviewed recovered tables without
    promoting them directly into live model contracts.
  - [x] P78.4c Add tests using synthetic/public-safe fixtures rather than
    private PDFs or arbitrary downloaded documents.
- [x] P78.5 Pilot the workflow against the TFL 6 MP11 package (`#209`)
  - [x] P78.5a Align the parent FEMIC pilot with
    `UBC-FRESH/femic-tfl6-instance#42`, especially P6.1 source/provenance and
    P6.2 extraction-manifest needs.
  - [x] P78.5b Produce a small public-safe pilot manifest for selected MP11
    figure candidates before attempting broad extraction.
  - [x] P78.5c Record limitations and required human-review steps before any
    recovered values feed TFL 6 crosswalk or model-overhaul planning.
- [x] P78.6 Document and validate the integration (`#209`)
  - [x] P78.6a Add docs for installing FEMIC with the figure-recovery optional
    extra and for running the provenance-preserving workflow.
  - [x] P78.6b Add warning-clean Sphinx docs and focused tests for the wrapper
    behavior.
  - [x] P78.6c Post issue progress comments and update the changelog at each
    implementation milestone.

## Phase 79: Open LiDAR Acquisition And Terrain Analysis (`#211`)

Status: planned.

Goal: add first-class FEMIC package support for automated open LiDAR
point-cloud acquisition and derived terrain/hydrography analysis, so instance
repositories can build public-data proxies for steep slopes, stream
location/classification, and related THLB/riparian workflows without one-off
scripts.

- [ ] P79.1 Define open LiDAR source and tile-index contract (`#212`).
  - [ ] P79.1a Survey supported public source families such as LidarBC/open
    LiDAR.
  - [ ] P79.1b Define tile-index records, AOI intersection behaviour,
    metadata fields, and provenance requirements.
  - [ ] P79.1c Define dependency, storage, and generated-artifact boundaries.
- [ ] P79.2 Implement resumable LiDAR and DEM materialization manifests
  (`#213`).
  - [ ] P79.2a Define manifest schema for source URLs, checksums, local paths,
    status, and retry state.
  - [ ] P79.2b Implement resumable acquisition helpers.
  - [ ] P79.2c Add checksum and completeness validation.
  - [ ] P79.2d Add CLI/API preflight surfaces.
- [ ] P79.3 Add terrain raster and slope-product pipeline APIs (`#214`).
  - [ ] P79.3a Select optional dependency stack for point-cloud/raster work.
  - [ ] P79.3b Implement terrain raster derivation interfaces.
  - [ ] P79.3c Implement percent-slope and zonal-stat helpers.
  - [ ] P79.3d Add QA report outputs.
- [ ] P79.4 Add terrain-derived stream candidate workflows (`#215`).
  - [ ] P79.4a Define terrain-derived hydrography product contract.
  - [ ] P79.4b Add comparison metrics against existing public hydrography.
  - [ ] P79.4c Emit review manifests and caveat reports.
- [ ] P79.5 Add CLI docs tests and instance hooks for LiDAR workflows (`#216`).
  - [ ] P79.5a Add CLI commands for tile discovery/materialization and terrain
    products.
  - [ ] P79.5b Add docs and examples.
  - [ ] P79.5c Add tests for manifests and command behaviour.
  - [ ] P79.5d Add instance integration notes.
- [ ] P79.6 Pilot open LiDAR terrain workflow against TFL 6 needs (`#217`).
  - [ ] P79.6a Select a bounded TFL 6 AOI/test area.
  - [ ] P79.6b Run tile discovery/materialization.
  - [ ] P79.6c Build terrain/slope candidate products.
  - [ ] P79.6d Compare outputs against TFL 6 instance needs.
  - [ ] P79.6e Write pilot closeout and package follow-up list.

## Phase 80: FreshForge Provider Integration For FEMIC Model-Build Workflows (`#220`)

- [x] P80.1 Add optional FreshForge package boundary and provider entry point
  (`#221`).
  - [x] P80.1a Add optional `freshforge` extra.
  - [x] P80.1b Register FEMIC in the `freshforge.providers` entry-point group.
  - [x] P80.1c Keep normal FEMIC imports lazy and usable without FreshForge.
  - [x] P80.1d Expose a direct provider factory for tests and advanced callers.
- [x] P80.2 Implement non-executing FEMIC provider metadata and validation
  (`#222`).
  - [x] P80.2a Add provider id `femic` and reusable FEMIC model-build node
    types.
  - [x] P80.2b Validate broad required node parameters only.
  - [x] P80.2c Return FreshForge diagnostics for provider-owned validation
    failures.
  - [x] P80.2d Preserve the no-execution boundary: no file reads, artifact
    inspection, BTC launch, Patchworks launch, or FEMIC stage execution.
- [x] P80.3 Add generic FreshForge workflow example and defer concrete
  instance specs (`#223`).
  - [x] P80.3a Encode validate-case through matrix-build graph order.
  - [x] P80.3b Keep paths repo-relative and public-safe.
  - [x] P80.3c Represent BatchTIPSY and Patchworks seams as declared metadata
    and artifacts, not execution.
  - [x] P80.3d Keep K3Z-specific workflow composition out of `femic.freshforge`;
    concrete instance workflow documents belong in instance repositories.
- [x] P80.4 Add FreshForge integration docs and tests (`#224`).
  - [x] P80.4a Add provider, workflow, and packaging metadata tests.
  - [x] P80.4b Document FreshForge graph planning versus FEMIC execution
    surfaces.
  - [x] P80.4c Link the integration to existing rebuild specs and named
    pipeline vocabulary.
  - [x] P80.4d Verify Sphinx builds warning-clean.
- [x] P80.5 Close out FreshForge integration lifecycle (`#225`).
  - [x] P80.5a Run local acceptance checks and record the non-green full-suite
    baseline.
  - [x] P80.5b Inspect built wheel metadata for the FreshForge provider entry
    point.
  - [x] P80.5c Update roadmap and changelog closeout notes.
  - [x] P80.5d Comment on child and parent issues with verification results.
  - [x] P80.5e Open PR and verify PR CI/docs checks.
  - [x] P80.5f Merge after the full-suite baseline decision is resolved.

Phase 80 focused verification passed with:

- `python -m pip install -e .[dev,freshforge]`
- `ruff format src tests`
- `ruff check src tests`
- `mypy src/femic/freshforge.py`
- `pytest tests/test_freshforge_integration.py`
- `pytest tests/test_freshforge_integration.py tests/test_docs_contract.py::test_guides_pages_are_in_docs_tree`
- `sphinx-build -b html docs _build/html -W`
- `python -m build`
- `twine check dist/*`
- `freshforge providers --json`
- `freshforge validate examples/freshforge/model_build_workflow.yaml --json`
- `freshforge plan examples/freshforge/model_build_workflow.yaml --json`
- `pre-commit run --all-files`

Phase 80 artifact inspection passed: the sdist includes
`examples/freshforge/model_build_workflow.yaml`, and the wheel metadata
contains `[freshforge.providers] femic = femic.freshforge:provider_factory`.
The package uses a generic provider example and leaves K3Z-specific workflow
documents to the K3Z instance repository.

Full-repo acceptance is not yet green in this Windows workspace. `mypy src`
still reports existing broad typing issues outside `femic.freshforge`, including
missing stubs for pandas/geopandas/scipy/seaborn and pre-existing type errors
in Patchworks, VDYP, TSR, and MKRF modules. Full `pytest` reports 45 failures
across existing CLI, docs-contract, Patchworks, named-pipeline, TSR, TIPSY,
post-TIPSY, and WS3 smoke surfaces; the new FreshForge integration tests pass.
PR `#226` was squash-merged to `main` after its `docs-pages` build and
`package-release-checks` workflow passed on the feature branch.

## Phase 81: MKRF FreshForge Workflow Deployment (`#227`)

- [x] P81.1 Add MKRF instance-owned FreshForge workflow contract
  (`UBC-FRESH/femic-mkrf-instance#35`).
  - [x] P81.1a Create the MKRF feature branch and workflow directory.
  - [x] P81.1b Add `workflows/freshforge/mkrf_model_build_workflow.yaml`
    using reusable `femic.*` provider references.
  - [x] P81.1c Encode validate-case through matrix-build graph order with
    MKRF-owned parameters and artifact declarations only.
- [x] P81.2 Document MKRF FreshForge planning boundary
  (`UBC-FRESH/femic-mkrf-instance#35`).
  - [x] P81.2a Add FreshForge validate/inspect/plan commands to MKRF docs and
    runbook surfaces.
  - [x] P81.2b Preserve `femic instance rebuild` as the execution surface and
    state that FreshForge does not run FEMIC, BTC, Patchworks, DataLad, or
    artifact materialization.
- [x] P81.3 Add parent integration checks for the MKRF workflow (`#227`).
  - [x] P81.3a Add focused parent test coverage that loads the MKRF workflow
    artifact when the submodule is present.
  - [x] P81.3b Validate and plan the MKRF graph with the existing generic
    `femic.freshforge` provider.
- [x] P81.4 Verify and publish the MKRF FreshForge workflow deployment
  (`#227`, `UBC-FRESH/femic-mkrf-instance#35`).
  - [x] P81.4a Run FreshForge CLI validate/inspect/plan from the MKRF instance.
  - [x] P81.4b Run FEMIC rebuild-spec validation and dry-run execution
    surfaces.
  - [x] P81.4c Run docs/package checks and artifact metadata inspection.
  - [x] P81.4d Audit MKRF annex publication state with
    `git annex find --not --in arbutus-s3`.
  - [x] P81.4e Open PRs, sync issue comments, and update the parent submodule
    pointer.

Phase 81 depends on the P80 provider branch/PR because the MKRF workflow uses
the generic `femic.freshforge` provider entry point. MKRF owns the concrete
workflow document; FEMIC core must not add MKRF-specific workflow builder
functions. The workflow uses
`config/patchworks.runtime.mkrf_rebuild.windows.yaml`, the current canonical
MKRF Patchworks runtime config, rather than the retained PoC
`config/patchworks.runtime.windows.yaml` surface.

Phase 81 focused verification passed with:

- `freshforge providers --json` from `external/femic-mkrf-instance`;
- `freshforge validate workflows/freshforge/mkrf_model_build_workflow.yaml --json`;
- `freshforge inspect workflows/freshforge/mkrf_model_build_workflow.yaml --json`;
- `freshforge plan workflows/freshforge/mkrf_model_build_workflow.yaml --json`;
- `femic instance validate-spec --spec config/rebuild.spec.yaml`;
- `femic instance rebuild --spec config/rebuild.spec.yaml --dry-run --run-id mkrf_freshforge_plan`;
- `git annex find --not --in arbutus-s3` from the MKRF instance, which returned
  no unpublished annex keys;
- MKRF Sphinx docs build with `-W`;
- parent Ruff, targeted mypy, FreshForge tests, parent Sphinx docs, package
  build, `twine check`, pre-commit, and wheel entry-point inspection.

## Phase 82: TFL6 Expanded Patchworks Model Materialization (`#230`)

- [x] P82.1 Promote expanded non-scenario TFL6 `models/**` payloads to tracked
  instance artifacts (`UBC-FRESH/femic-tfl6-instance#156`).
  - [x] P82.1a Remove the TFL6 ignore boundary that leaves expanded
    Patchworks runtime model directories untracked.
  - [x] P82.1b Add annex policy for expanded model payloads so all
    non-scenario files under `models/` are tracked without relying only on
    release ZIP archives.
  - [x] P82.1c Commit the expanded non-scenario model tree in the TFL6
    instance repository.
- [x] P82.2 Publish and verify TFL6 model payload materialization.
  - [x] P82.2a Copy all annexed `models/**` keys to `arbutus-s3`.
  - [x] P82.2b Verify no `models/**` files remain untracked.
  - [x] P82.2c Verify no `models/**` annex keys are missing from
    `arbutus-s3`.
  - [x] P82.2d Prove fresh-environment materialization of the tracked model
    tree.
- [ ] P82.3 Update the parent FEMIC submodule pointer and closeout notes.
  - [x] P82.3a Update `external/femic-tfl6-instance` to the repaired TFL6
    commit.
  - [x] P82.3b Record verification in parent and instance changelogs.
  - [x] P82.3c Push branches and synchronize GitHub issue status.

Phase 82 supersedes the earlier TFL6 publication boundary for expanded
Patchworks model directories. Release ZIP archives remain useful reviewed
release artifacts, but runnable full materialization now requires the expanded
non-scenario `models/**` tree itself to be tracked and publicly retrievable
through the instance DataLad/git-annex surface. Patchworks smoke/scenario
output directories under `models/**/analysis/p*/` and
`models/**/analysis/headless_runs/` remain local run evidence, not required
fresh-clone model inputs.

## Phase 83: TSA29 Runtime Tracking Hygiene (`#232`)

- [x] P83.1 Remove tracked TSA29 `runtime/**` artifacts
  (`UBC-FRESH/femic-tsa29-instance#13`).
  - [x] P83.1a Add a broad TSA29 `runtime/` ignore rule.
  - [x] P83.1b Remove all tracked TSA29 `runtime/**` files from the Git index
    without deleting local working-tree copies.
  - [x] P83.1c Verify `git ls-files runtime` is empty in the TSA29 instance.
- [x] P83.2 Verify TSA29 clone and model materialization.
  - [x] P83.2a Verify the Patchworks block payload remains present on
    `arbutus-s3`.
  - [x] P83.2b Prove a fresh short-path Windows clone can check out TSA29
    without tracked `runtime/**` long-path failures.
  - [x] P83.2c Prove `datalad get -r models/tsa29_patchworks_model/blocks`
    materializes a valid polygon shapefile.
- [x] P83.3 Update parent pointer and close out.
  - [x] P83.3a Update `external/femic-tsa29-instance` to the cleaned TSA29
    commit.
  - [x] P83.3b Record verification in parent and instance changelogs.
  - [x] P83.3c Push branches, open PRs, and synchronize GitHub issue status.

Phase 83 treats TSA29 `runtime/` as local/generated only, matching MKRF and
TFL6. Curated evidence that needs to remain durable must live outside
`runtime/` in explicit evidence, docs, config, planning, or release surfaces.

## Phase 84: FreshForge Execution For MKRF Workflows

Parent issue: #234

Branch: `feature/p84-freshforge-execution-mkrf`

Status: complete

Goal: consume FreshForge Phase 6 execution support from FEMIC and MKRF so the
MKRF FreshForge workflow can explicitly run the canonical rebuild lane through
runtime-package regeneration and Patchworks Matrix Builder.

- [x] P84.1 Add executable FEMIC provider hooks (#235)
  - [x] Keep `femic.freshforge` lazy-import safe.
  - [x] Preserve validation, inspection, and planning behavior for existing
        provider references.
  - [x] Map generic FEMIC node types to existing `python -m femic ...`
        commands.
  - [x] Add command construction and mocked execution tests.
- [x] P84.2 Add MKRF executable provider namespace (#236)
  - [x] Add `femic.mkrf.*` metadata for MKRF runtime-package regeneration
        commands.
  - [x] Add provider validation for required broad parameters such as
        `instance_root`, `resultant_gdb`, and `run_id`.
  - [x] Register the MKRF provider through the `freshforge.providers` entry
        point without adding instance-specific workflow builders to FEMIC core.
- [x] P84.3 Update MKRF executable workflow and docs (#237;
       MKRF issue UBC-FRESH/femic-mkrf-instance#37)
  - [x] Replace the plan-only MKRF workflow with an explicit executable graph.
  - [x] Use the accepted MKRF source input, run config, Patchworks config, and
        model package paths.
  - [x] Update MKRF README/docs/runbook language from plan-only to explicit
        `freshforge run` execution.
- [x] P84.4 Validate MKRF FreshForge execution cycle (#238)
  - [x] Verify providers, validate, inspect, plan, and dry-run output.
  - [x] Attempt full local execution through Matrix Builder.
  - [x] Rerun after this machine has a usable Patchworks license; the previous
        FreshForge run reached `femic patchworks matrix-build`, then Patchworks
        exited with `No matching license`.
  - [x] Inspect produced run reports, FEMIC logs, regenerated model-input
  bundle files, and ForestModel XML.
  - [x] Inspect Matrix Builder manifest after the Patchworks license blocker is
        resolved.
- [x] P84.5 Close out execution integration (#239)
  - [x] Update roadmap and changelog closeout notes.
  - [x] Open PRs, merge implementation PRs, and verify checks.
  - [x] Record model-instance materialization as the next separate FreshForge
        workflow family.
  - [x] Close parent P84 after the portable-artifact closeout branch lands and
        the final issue comments are posted.

Phase 84 deliberately does not add model-instance materialization workflow
support. That is the next FreshForge deployment family after executable
workflow semantics are proven because it solves the separate user problem of
bootstrapping Git, Python, DataLad, git-annex, special remotes, virtual
environments, and required payload materialization before model workflows run.

P84.4/#238 is now validated. After connecting this machine through the UBC VPN,
the MKRF FreshForge run completed all nine planned nodes through Patchworks
Matrix Builder with `run_id=mkrf_freshforge_exec`; the Matrix Builder manifest
reported `returncode=0`, stderr reported `Done Matrix Builder.`, and the tracks
surface contained `features.csv` 98,413 rows, `protoaccounts.csv` 62 rows,
`accounts.csv` 62 rows, `curves.csv` 2,684,869 rows, and `products.csv`
140,196 rows. The portable tracked artifact fix landed through MKRF PR
`UBC-FRESH/femic-mkrf-instance#41` and parent PR `#243`; P84 is closed.

## Phase 85: FreshForge Instance Provider Boundary Repair

Parent issue: #241

Branch: `feature/p85-freshforge-instance-provider-boundary`

Status: complete

Goal: restore the provider namespace boundary after the Phase 84 executable
prototype put MKRF-specific FreshForge provider logic under `femic.mkrf` in
FEMIC core. FEMIC core should expose reusable FEMIC stages through provider id
`femic`; MKRF-specific orchestration belongs to the MKRF instance as provider
id `mkrf`.

- [x] P85.1 Remove MKRF FreshForge provider ownership from FEMIC core
  - [x] Remove the `femic.mkrf` provider id, factory, metadata, command
        builders, and entry point from `femic.freshforge`.
  - [x] Keep generic executable `femic.*` stages and lazy FreshForge imports.
  - [x] Update parent tests and docs so FEMIC core is instance-neutral.
- [x] P85.2 Add the MKRF-owned FreshForge adapter package
      (MKRF issue UBC-FRESH/femic-mkrf-instance#39)
  - [x] Add a lightweight installable `mkrf_freshforge` package in the MKRF
        instance repository.
  - [x] Register provider id `mkrf` through the `freshforge.providers` entry
        point.
  - [x] Move MKRF provider metadata and command construction into the instance
        adapter while continuing to call existing `python -m femic ...`
        compatibility commands.
- [x] P85.3 Update MKRF workflow and docs for `mkrf.*`
  - [x] Rewrite MKRF workflow provider references from `femic.mkrf.*` to
        `mkrf.*`.
  - [x] Document adapter installation and the boundary between FEMIC core,
        FreshForge, and instance-owned orchestration.
- [x] P85.4 Record the broader MKRF core extraction follow-up
  - [x] Inventory MKRF-specific core modules and `femic instance mkrf-*`
        commands.
  - [x] Add a follow-on phase for moving mature MKRF-specific workflow and
        pipeline code out of FEMIC core after the adapter path is proven.
- [x] P85.5 Verify, commit, push, and open PRs
  - [x] Run focused parent and MKRF adapter tests.
  - [x] Verify provider metadata no longer advertises `femic.mkrf` from FEMIC
        and advertises `mkrf` only from the MKRF adapter.
  - [x] Open linked parent and MKRF PRs.

Phase 85 intentionally does not remove the existing `femic instance mkrf-*`
compatibility commands. Those commands remain the execution target for the
MKRF adapter until a separate extraction phase moves mature MKRF-specific
scientific and workflow code into an instance-owned or companion package.

## Phase 86: Extract MKRF-Specific Workflow Code From FEMIC Core

Parent issue: #244

Branch: `feature/p86-extract-mkrf-workflow-code`

Status: complete

Goal: move mature MKRF-specific pipeline and workflow implementation out of
FEMIC core after the P85 adapter package boundary is proven. The current
inventory found MKRF-specific implementation surfaces in
`src/femic/workflows/mkrf.py`, `src/femic/pipeline/mkrf_au.py`,
`src/femic/pipeline/mkrf_first_growth.py`, `src/femic/pipeline/mkrf_managed.py`,
and `femic instance mkrf-*` CLI commands.

- [x] P86.1 Define the extraction target and compatibility policy
  - [x] Move mature MKRF code into the MKRF instance package under
        `external/femic-mkrf-instance`, not a new companion repository.
  - [x] Remove existing `femic instance mkrf-*` commands now; do not keep
        deprecated wrappers in FEMIC core.
  - [x] Keep FreshForge provider references as `mkrf.*`.
  - [x] Keep model-instance materialization out of P86.
- [x] P86.2 Move MKRF implementation behind the chosen package boundary
  - [x] Preserve current tests and command behavior during the move by
        migrating MKRF-specific unit tests into the MKRF instance package.
  - [x] Keep generic FEMIC package APIs instance-neutral by removing
        `femic.pipeline.mkrf_*`, `femic.workflows.mkrf`, and
        `femic instance mkrf-*` commands from FEMIC core.
- [x] P86.3 Update docs, tests, packaging, and FreshForge adapter commands
  - [x] Point the MKRF FreshForge adapter at `python -m mkrf_femic ...`
        commands in the MKRF instance package.
  - [x] Remove stale FEMIC-core MKRF ownership language from MKRF docs.
  - [x] Verify parent packaging no longer includes the removed FEMIC MKRF
        modules and still exposes only the generic `femic` FreshForge provider.

P86 was merged through parent PR `#245` after the MKRF instance package PR
merged and the parent submodule pointer was reconciled.

## Phase 87: Extract MKRF Legacy ForestModel XML Builder From FEMIC Core

Parent issue: #246

Branch: `feature/p87-extract-mkrf-legacy-xml-builder`

Status: complete

Goal: move the remaining MKRF-specific legacy ForestModel XML builder out of
`femic.fmg` and into the MKRF instance package. FEMIC core keeps generic
Patchworks/ForestModel primitives and generic export wording; the MKRF instance
owns the MKRF legacy builder API, tests, and docs. The broad instance-reference
audit for this lane is recorded in
`planning/phase87_parent_instance_reference_audit.md`.

- [x] P87.1 Record lifecycle and planning surfaces
  - [x] Open parent FEMIC issue `#246`.
  - [x] Open MKRF instance issue `UBC-FRESH/femic-mkrf-instance#44`.
  - [x] Commit the parent instance-reference audit report.
- [x] P87.2 Move MKRF legacy XML builder ownership into MKRF
  - [x] Add `mkrf_femic.legacy_xml` with the migrated MKRF builder API.
  - [x] Move MKRF-specific builder constants, helper functions, and tests out
        of parent FEMIC and into the MKRF instance package.
  - [x] Preserve generated XML behavior and output contracts.
- [x] P87.3 Remove MKRF legacy builder coupling from FEMIC core
  - [x] Remove `build_legacy_mkrf_forestmodel_xml_tree` and
        `emit_legacy_mkrf_forestmodel_xml` from `femic.fmg`.
  - [x] Remove MKRF-specific legacy XML helper code from
        `src/femic/fmg/patchworks.py`.
  - [x] Reword generic export CLI help so it no longer uses MKRF-first
        terminology.
- [x] P87.4 Verify and close out the paired lifecycle
  - [x] Run focused MKRF package tests and FreshForge workflow dry-run checks.
  - [x] Run focused parent FEMIC lint, tests, docs, and package checks.
  - [x] Merge MKRF first, update the parent submodule pointer, then merge the
        parent PR.

P87 is complete on the branch: MKRF PR `UBC-FRESH/femic-mkrf-instance#45`
merged to MKRF `main`, the parent submodule pointer was reconciled to merged
MKRF commit `c769e4c`, and parent PR `#247` passed package and docs checks
before merge.

## Phase 88: Define Instance Extension Boundaries for Arms-Length Example Repos

Parent issue: #248

Branch: `feature/p88-instance-extension-boundaries`

Status: complete

Goal: define and begin enforcing the boundary that FEMIC core must not depend
on named example instances linked under `external/`. FEMIC core owns generic
engines, schemas, runners, validators, registry loading, and CLI plumbing.
Instance repositories own instance-specific data, policies, registries,
workflows, adapters, and scientific interpretation.

- [x] P88.1 Record lifecycle and roadmap surfaces
  - [x] Open parent FEMIC issue `#248`.
  - [x] Open follow-on phase issues `#249` through `#254`.
  - [x] Update `ROADMAP.md` and `CHANGE_LOG.md` with the P88-P94 sequence.
- [x] P88.2 Document the boundary contract
  - [x] Add an instance-extension boundary contract to the technical docs.
  - [x] State that example submodules are deployments, not core package
        dependencies.
- [x] P88.3 Add a source audit guard
  - [x] Capture the current named-instance reference baseline from `src/femic`.
  - [x] Add a regression test that rejects new or increased named-instance
        references unless deliberately allowlisted during migration.
- [x] P88.4 Verify and close out P88
  - [x] Run focused tests for the new source audit guard.
  - [x] Run Sphinx warning-clean docs build.
  - [x] Post progress comments on issue `#248`.

## Phase 89: Extract K3Z Bindings and Pipeline Policies From FEMIC Core

Parent issue: #249

K3Z issue: UBC-FRESH/femic-k3z-instance#29

Branch: `feature/p89-extract-k3z-bindings`

K3Z branch: `feature/k3z-femic-package-policies`

Status: complete

Goal: create a K3Z-owned package/config surface and move K3Z-specific FMG
adapter bindings, source filenames, run defaults, plot limits, target-stratum
defaults, and VDYP fit-policy decisions out of `src/femic`.

- [x] P89.1 Record lifecycle and planning surfaces
  - [x] Use parent FEMIC issue `#249`.
  - [x] Open K3Z instance issue `UBC-FRESH/femic-k3z-instance#29`.
  - [x] Create parent branch `feature/p89-extract-k3z-bindings`.
  - [x] Create K3Z branch `feature/k3z-femic-package-policies`.
  - [x] Update `ROADMAP.md` and `CHANGE_LOG.md` before implementation.
- [x] P89.2 Add K3Z-owned package and policy surfaces
  - [x] Add installable `k3z_femic` package in the K3Z instance repo.
  - [x] Move K3Z FMG auxiliary support loaders into `k3z_femic`.
  - [x] Add K3Z-owned target-strata, plot-limit, and VDYP selection-policy config.
- [x] P89.3 Add generic FEMIC extension seams
  - [x] Let FMG context construction accept external auxiliary support data.
  - [x] Add generic FMG auxiliary-provider discovery.
  - [x] Replace K3Z-specific target-strata, plot-limit, and VDYP policy branches
        with config-driven generic options.
- [x] P89.4 Verify and close out
  - [x] Run focused K3Z package tests and docs checks.
  - [x] Run focused parent tests, lint, Sphinx, build, and package checks.
  - [x] Merge K3Z first, update parent submodule pointer, then merge parent.

## Phase 90: Extract TSA29 Strict Locked-Chain Workflow From FEMIC Core

Parent issue: #250
Instance issue: UBC-FRESH/femic-tsa29-instance#15

Status: complete

Goal: define a generic locked-chain validation interface, then move TSA29
locked-chain row ordering, ledger interpretation, checkpoint restrictions,
strict-chain preflight, and strict-sequence execution into a TSA29-owned
package or adapter.

- [ ] P90.1 Record lifecycle and planning surfaces
  - [x] Create parent branch `feature/p90-extract-tsa29-strict-chain`.
  - [x] Create TSA29 branch `feature/tsa29-femic-strict-chain`.
  - [x] Link parent issue `#250` and TSA29 issue
        `UBC-FRESH/femic-tsa29-instance#15`.
  - [x] Record matching starting notes in parent and TSA29 changelogs.
- [x] P90.2 Add generic named-pipeline contract-handler seam
  - [x] Define the contract handler protocol and registration/discovery API.
  - [x] Replace TSA29-specific branches in `femic.named_pipelines` with
        handler dispatch and clear missing-handler errors.
  - [x] Add fixture-handler tests for explicit registration, discovery,
        duplicate handling, and generic dispatch.
- [x] P90.3 Move TSA29 strict-chain contract into instance ownership
  - [x] Add installable `tsa29_femic` package in the TSA29 instance repo.
  - [x] Register `tsa29_locked_chain_strict` through
        `femic.named_pipeline_contracts`.
  - [x] Move TSA29 row-order, ledger, preflight, GLB materialization, strict
        sequence, and ledger-validation logic into `tsa29_femic`.
  - [x] Migrate TSA29-specific strict-chain tests into the TSA29 package.
- [x] P90.4 Verify and close out
  - [x] Run focused parent checks for named pipelines, boundary guard, typing,
        docs, and package artifacts.
  - [x] Run focused TSA29 package checks.
  - [x] Merge TSA29 first and update the parent submodule pointer to the
        merged TSA29 main commit.
  - [x] Merge parent P90 after PR checks pass.

## Phase 91: Split TSR Engine From TSA29 Adjudication Overlays

Parent issue: #251

TSA29 issue: UBC-FRESH/femic-tsa29-instance#17

Status: complete

Goal: keep generic TSR discovery, extraction, recipe execution, schemas, and
report primitives in FEMIC core while moving TSA29 interpretation text, no-op
decisions, gap overrides, and comparison-report special cases into
instance-owned overlays.

### Tasks

- [x] Create parent branch `feature/p91-tsr-adjudication-overlays`.
- [x] Create TSA29 branch `feature/tsa29-tsr-adjudication-overlays`.
- [x] Open TSA29 issue `UBC-FRESH/femic-tsa29-instance#17`.
- [x] Add generic TSR adjudication overlay provider registration and discovery
      in FEMIC core.
- [x] Move TSA29 row classifications, checkpoint policy, interpretation
      overrides, and active adjudication report notes into `tsa29_femic`.
- [x] Replace parent hardcoded TSA29 adjudication branches with provider-backed
      generic defaults and clear missing-provider errors.
- [x] Update parent and TSA29 tests for provider registration, TSA29 behavior
      preservation, and named-instance boundary counts.
- [x] Run focused parent and TSA29 verification.
- [x] Merge TSA29 first and update the parent submodule pointer.
- [x] Close P91
      after parent PR checks pass.

## Phase 92: Externalize Patchworks Variant Registries

Parent issue: #252
K3Z issue: UBC-FRESH/femic-k3z-instance#31
MKRF issue: UBC-FRESH/femic-mkrf-instance#46

Status: complete

Goal: extend Patchworks variant loading so instance packages and explicit
registry files can provide variants, then move K3Z and MKRF variant definitions
out of FEMIC core packaged resources.

- [x] P92.1 Add a generic Patchworks variant registry-provider seam in FEMIC
      core, including explicit registration, entry-point discovery, duplicate
      detection, and clear provider load diagnostics.
- [x] P92.2 Move K3Z Patchworks variant/scenario-set registry definitions into
      the K3Z instance package and expose them through an installed provider.
- [x] P92.3 Move MKRF Patchworks variant registry definitions into the MKRF
      instance package and expose them through an installed provider.
- [x] P92.4 Preserve explicit user registry overlays and CLI behavior while
      changing built-in K3Z/MKRF availability into installed-provider
      availability.
- [x] P92.5 Update docs, boundary guards, tests, and packaged resources so
      FEMIC core no longer ships K3Z/MKRF Patchworks variant definitions.
- [x] P92.6 Verify parent plus K3Z/MKRF instance checks, merge instance PRs
      first, update parent submodule pointers, and close P92.

## Phase 93: Remove Built-In Example Instance Catalog From FEMIC Core

Parent issue: #253
K3Z issue: UBC-FRESH/femic-k3z-instance#33
TSA29 issue: UBC-FRESH/femic-tsa29-instance#19

Status: complete

Goal: replace the packaged K3Z/TSA29 built-in instance catalog with external
catalog discovery or explicit user catalog files. FEMIC core should not ship
named example instance metadata by default.

- [x] P93.1 Add a generic instance catalog provider seam in FEMIC core,
      including explicit registration, entry-point discovery, duplicate
      detection, and optional explicit user catalog YAML loading.
- [x] P93.2 Move the K3Z installable instance catalog entry into the K3Z
      instance package and expose it through an installed provider.
- [x] P93.3 Move the TSA29 installable instance catalog entry into the TSA29
      instance package and expose it through an installed provider.
- [x] P93.4 Replace core tests/docs/CLI wording that treats K3Z/TSA29 as
      built-in FEMIC metadata with generic instance-catalog behavior.
- [x] P93.5 Reduce `src/femic/resources/builtins/instances.builtin.yaml` to an
      empty generic catalog shell and lower the P88 boundary allowlist.
- [x] P93.6 Verify parent plus K3Z/TSA29 instance checks, merge instance PRs
      first, update parent submodule pointers, and close P93.

## Phase 94: Complete Core Decoupling From Example Instances

Parent issue: #254

Branch: `feature/p94-final-core-decoupling`

Status: complete

Goal: scrub remaining named-instance references from `src/femic`, packaged
resources, generic templates, and generic CLI help. Close the umbrella only
after tests prove FEMIC core imports, builds, and passes generic checks without
example submodules present.

- [x] P94.1 Audit the post-P93 `src/femic` named-instance reference baseline
      and classify the remaining references as generic template/help debt,
      test-fixture debt, or allowed historical documentation outside core.
- [x] P94.2 Remove remaining named-instance references from `src/femic` code
      comments, generic CLI help text, packaged template resources, and generic
      runtime configuration templates.
- [x] P94.3 Tighten the P88 boundary guard so any named `mkrf`, `k3z`,
      `tsa29`, `tfl6`, or `femic-*-instance` reference under `src/femic`
      fails unless a future roadmap phase deliberately reopens the allowlist.
- [x] P94.4 Add regression coverage proving core catalog/variant behavior and
      package import paths work without installed example-instance providers or
      initialized `external/femic-*` submodules.
- [x] P94.5 Update docs and changelog to describe the final arms-length
      boundary: example instances are optional deployments, not FEMIC core
      package dependencies.
- [x] P94.6 Run parent validation, open/merge the P94 PR, and close the
      P88-P94 core decoupling sequence.

## Phase 95: Publish FEMIC 0.2.0a1 Core Decoupling Alpha

Parent issue: #262

Branch: `feature/p95-femic-0.2.0a1-release`

Status: complete

Goal: prepare and publish an alpha FEMIC release that marks the P80-P94
architecture milestone: FreshForge integration, instance-owned extension
boundaries, externalized registries/catalogs, and final removal of named
example-instance coupling from `src/femic`.

- [x] P95.1 Prepare release lifecycle surfaces
  - [x] Create parent branch `feature/p95-femic-0.2.0a1-release`.
  - [x] Open parent GitHub issue `#262`.
  - [x] Record the release checklist in `ROADMAP.md` before release edits.
- [x] P95.2 Synchronize package version surfaces
  - [x] Update `pyproject.toml` to `0.2.0a1`.
  - [x] Update `src/femic/__init__.py` to `0.2.0a1`.
  - [x] Add a focused test proving package metadata and `femic.__version__`
        remain synchronized.
- [x] P95.3 Add public release notes
  - [x] Add `RELEASE_NOTES.md` for `FEMIC 0.2.0a1`.
  - [x] Summarize P80-P94 as the release boundary.
  - [x] State alpha/provisional scope and known non-P95 baseline caveats.
- [x] P95.4 Run local release validation
  - [x] Run `ruff format src tests`.
  - [x] Run `ruff check src tests`.
  - [x] Run targeted `mypy` for touched release/version modules.
  - [x] Run the focused version metadata test and P94 boundary/catalog tests.
  - [x] Run `sphinx-build -b html docs _build/html -W`.
  - [x] Run `python -m build`.
  - [x] Run `twine check dist/*`.
  - [x] Inspect built wheel/sdist metadata for version `0.2.0a1`.
  - [x] Run full `mypy src` and full `pytest` as release-audit checks, noting
        known non-P95 baseline failures separately from release blockers.
        Full `mypy src` still reports the known pandas/SciPy/VDYP typing debt.
        Full `pytest` reports 19 known environment/runtime/baseline failures;
        focused P95 release validation is green.
- [x] P95.5 Open and merge the release PR
  - [x] Push the release branch and open the PR.
  - [x] Require GitHub build and `package-release-checks` to pass.
  - [x] Merge to `main` after release-prep checks pass.
- [x] P95.6 Publish staged and public release artifacts
  - [x] Tag `v0.2.0a1` from merged `main`.
  - [x] Run `publish-testpypi` and confirm TestPyPI smoke install.
        First TestPyPI attempt failed because publishable optional dependency
        metadata contained direct Git URL dependencies for FreshForge and
        figrecover. P95 now removes those direct URL dependencies from
        publishable package metadata and documents explicit source installs
        until those optional packages have PyPI releases.
  - [x] Create GitHub pre-release `FEMIC 0.2.0a1`.
  - [x] Run `publish-pypi` and confirm PyPI smoke install for
        `femic==0.2.0a1`.
- [x] P95.7 Close out P95
  - [x] Update `CHANGE_LOG.md` with release-prep and publication results.
  - [x] Post required progress and closeout comments on issue `#262`.
  - [x] Close issue `#262` after publication and smoke checks pass.

## Phase 96: FreshForge v0.1.0a4 Compatibility Refresh

Parent issue: #266

Branch: `feature/freshforge-v0.1.0a4-compatibility-refresh`

Status: complete

Goal: align FEMIC's optional FreshForge provider integration with the released
FreshForge `v0.1.0a4` provider protocol while keeping FEMIC's package metadata
PyPI-safe and preserving the explicit execution boundary.

- [x] P96.1 Prepare compatibility lifecycle surfaces
  - [x] Open parent GitHub issue `#266`.
  - [x] Create branch `feature/freshforge-v0.1.0a4-compatibility-refresh`.
  - [x] Record this roadmap plan before implementation.
- [x] P96.2 Align the FEMIC FreshForge provider with the released API
  - [x] Keep normal `import femic` FreshForge-free.
  - [x] Keep `femic[freshforge]` empty/PyPI-safe until FreshForge has a PyPI
        distribution.
  - [x] Add the released `run_node(...)` execution hook while preserving the
        existing execution implementation behind a compatibility seam.
  - [x] Update execution-result construction to the released FreshForge
        `v0.1.0a4` record type.
  - [x] Refresh FEMIC provider metadata version away from the stale
        `0.1.0a1` value.
- [x] P96.3 Refresh docs and examples for the released FreshForge tag
  - [x] Update README and FreshForge guide install commands from the old
        execution-engine feature branch to `v0.1.0a4`.
  - [x] Update run examples for the released FreshForge run CLI, including the
        current explicit-run boundary.
  - [x] Confirm the matrix command is documented as a later lane, not a P96
        workflow surface.
- [x] P96.4 Add compatibility tests and smoke checks
  - [x] Update FreshForge integration tests for provider metadata,
        `run_node(...)`, result records, and lazy imports.
  - [x] Install FreshForge from tag `v0.1.0a4` and run provider discovery,
        validation, inspection, planning, and safe run smoke checks.
  - [x] Run focused lint, type, pytest, Sphinx, build, and twine checks.
- [x] P96.5 Close out the compatibility refresh
  - [x] Update `CHANGE_LOG.md`.
  - [x] Post progress and closeout comments on issue `#266`.
  - [x] Open and merge the P96 PR after checks pass.

## Phase 97: Namespace-Aware FEMIC FreshForge Artifacts

Parent issue: #268

Branch: `feature/p97-freshforge-namespace-artifacts`

Status: complete

Goal: add report-only namespace-aware artifact metadata to FEMIC's generic
FreshForge provider by resolving workflow-declared artifact paths through the
FreshForge run context without changing FEMIC command outputs.

- [x] P97.1 Prepare lifecycle surfaces
  - [x] Open parent GitHub issue `#268`.
  - [x] Create branch `feature/p97-freshforge-namespace-artifacts`.
  - [x] Record this roadmap plan before implementation.
- [x] P97.2 Resolve declared artifact metadata through FreshForge run context
  - [x] Add a lazy helper that uses `context.resolve_path(...)` when available.
  - [x] Return resolved artifact paths as strings in `ProviderRunResult.artifacts`.
  - [x] Preserve non-string JSON-safe artifact metadata without path resolution.
  - [x] Keep FEMIC command construction, stdout/stderr data, and return-code
        behavior unchanged.
- [x] P97.3 Preserve the report-only boundary
  - [x] Do not automatically pass namespaced paths into FEMIC CLI options.
  - [x] Do not move existing FEMIC runtime outputs.
  - [x] Do not claim resolved artifact paths exist unless commands create them.
  - [x] Keep `validate`, `inspect`, and `plan` non-mutating.
- [x] P97.4 Update docs and tests
  - [x] Document namespace-aware artifact metadata and the report-only boundary.
  - [x] Document `freshforge run ... --namespace smoke --workdir
        runtime/freshforge` as the recommended smoke pattern.
  - [x] Add focused tests for no-namespace, namespace, absolute-path, and
        non-string artifact behavior.
  - [x] Verify returned artifacts remain JSON-serializable.
- [x] P97.5 Validate and close out
  - [x] Install editable dev dependencies and FreshForge `v0.1.0a4`.
  - [x] Run Ruff, targeted mypy, focused pytest, Sphinx, build, twine, and
        FreshForge CLI smoke checks.
  - [x] Update `CHANGE_LOG.md`.
  - [x] Post progress and closeout comments on issue `#268`.
  - [x] Open and merge the P97 PR after checks pass.

## Phase 98: FreshForge Template Workflow For Model-Instance Materialization (`#270`)

Status: implemented locally; PR closeout pending

Goal: design a reusable FreshForge workflow family for deterministic
model-instance materialization so MKRF, TFL6, TSA29, and future instances do
not require users to manually execute a long Git/DataLad/git-annex setup ritual
from prose documentation.

- [x] P98.1 Capture materialization workflow requirements.
  - [x] Record the shared failure pattern from recent user deployment tests.
  - [x] Define the generic workflow node families: toolchain check, submodule
        setup, virtual-environment validation, package install check, DataLad
        and git-annex checks, `arbutus-s3` enablement, required payload
        materialization, annex audit, and report generation.
  - [x] Keep the first planning note at
        `planning/phase98_freshforge_materialization_template.md`.
- [x] P98.2 Define the instance overlay contract.
  - [x] Support instance path, special remote name, required materialization
        paths, optional public-data mirror paths, install extras or instance
        packages, and report output path.
  - [x] Keep instance-specific values outside FEMIC core.
- [x] P98.3 Plan the execution surface.
  - [x] Decide that P98.4 should add a FEMIC-owned optional FreshForge provider
        namespace for model-instance materialization, using provider id
        `femic.materialization` and entry point
        `femic.materialization = femic.freshforge_materialization:provider_factory`.
  - [x] Keep the provider generic and config-driven so code does not name MKRF,
        TFL6, TSA29, K3Z, or any `external/femic-*-instance` path.
  - [x] Lock the planned node vocabulary: toolchain check, Python environment
        check, package install check, submodule initialization, git-annex
        initialization, special-remote enablement, required path
        materialization, annex availability audit, and report generation.
  - [x] Lock the overlay contract around instance root/path, optional submodule
        path, virtual-environment path, install requirements/extras, special
        remote name, required materialization paths, audit paths, and report
        path.
  - [x] Keep a tiny bootstrap helper as future scope only, because FreshForge
        must exist before it can run the workflow.
  - [x] Record the P98.4 implementation handoff in
        `planning/phase98_materialization_execution_surface.md`.
- [x] P98.4 Implement and test the reusable template.
  - [x] Do not implement materialization execution as part of the TFL6 Phase 17
        model-build workflow scaffold.
  - [x] Add the FEMIC-owned materialization FreshForge provider namespace and
        entry point.
  - [x] Add overlay parsing, validation, mocked execution tests, and a fixture
        FreshForge workflow.
  - [x] Prove the public-safe fixture workflow with FreshForge validate,
        inspect, plan, and run.
  - [x] Keep the first real instance overlay as a later TFL6 phase.

## Phase 99: FreshForge PyPI Dependency Cleanup (`#274`)

Status: complete

Goal: switch FEMIC's optional FreshForge dependency and install guidance from
the temporary GitHub tag workflow to the PyPI-published FreshForge alpha.

- [x] P99.1 Verify FreshForge PyPI availability.
  - [x] Confirm PyPI JSON reports `freshforge` version `0.1.0a5`.
  - [x] Confirm `pip install --index-url https://pypi.org/simple --dry-run
        freshforge==0.1.0a5` resolves in this environment.
- [x] P99.2 Update FEMIC dependency and docs.
  - [x] Set `femic[freshforge]` to install `freshforge==0.1.0a5`.
  - [x] Replace GitHub-tag install examples with PyPI extra guidance.
  - [x] Update the public-safe materialization fixture overlay package
        reference.
- [x] P99.3 Validate and close out.
  - [x] Run focused FreshForge provider/materialization tests.
  - [x] Run package metadata checks proving the extra carries
        `freshforge==0.1.0a5`.
  - [x] Update `CHANGE_LOG.md` and issue `#274`.

## Phase 100: First FreshForge Materialization Overlay For TFL6 (`#276`)

Status: complete

Goal: prove the first real model-instance materialization workflow using the
generic `femic.materialization` FreshForge provider, with TFL6 as the parent
checkout acceptance case.

- [x] P100.1 Create lifecycle and planning surfaces.
  - [x] Open parent issue `#276` and TFL6 issue `#160`.
  - [x] Create parent branch `feature/p100-tfl6-materialization-overlay`.
  - [x] Create TFL6 branch `feature/p18-freshforge-materialization-overlay`.
  - [x] Add `planning/phase100_tfl6_materialization_overlay.md`.
- [x] P100.2 Add TFL6-owned overlay and workflow.
  - [x] Add TFL6 materialization overlay and workflow YAML under
        `external/femic-tfl6-instance/workflows/freshforge/`.
  - [x] Use only the generic `femic.materialization.*` provider namespace.
  - [x] Keep runtime reports under ignored `runtime/freshforge/`.
- [x] P100.3 Validate parent-checkout materialization surfaces.
  - [x] Harden `femic.materialization.check_python_environment` so an existing
        configured venv is validated instead of recreated.
  - [x] Run provider discovery, validate, inspect, and plan from the parent
        checkout.
  - [x] Run the bounded FreshForge materialization workflow from the parent
        checkout.
  - [x] Verify required `models/**` payload availability and Arbutus remote
        coverage.
- [x] P100.4 Close out.
  - [x] Merge the TFL6 Phase 18 PR first.
  - [x] Update the parent TFL6 submodule pointer.
  - [x] Re-run parent validation after the pointer update.
  - [x] Update `CHANGE_LOG.md`, issue comments, and PR closeout records.

## Phase 101: FreshForge Materialization Overlay For MKRF (`#278`)

Status: complete

Goal: add the second real model-instance materialization workflow using the
generic `femic.materialization` FreshForge provider, with MKRF as the parent
checkout acceptance case after TFL6.

- [x] P101.1 Create lifecycle and planning surfaces.
  - [x] Open parent issue `#278` and MKRF issue `UBC-FRESH/femic-mkrf-instance#48`.
  - [x] Create parent branch `feature/p101-mkrf-materialization-overlay`.
  - [x] Create MKRF branch `feature/freshforge-materialization-overlay`.
  - [x] Add `planning/phase101_mkrf_materialization_overlay.md`.
- [x] P101.2 Add MKRF-owned overlay and workflow.
  - [x] Add MKRF materialization overlay and workflow YAML under
        `external/femic-mkrf-instance/workflows/freshforge/`.
  - [x] Use only the generic `femic.materialization.*` provider namespace.
  - [x] Install the MKRF editable adapter package during materialization so
        the `mkrf` FreshForge provider is available after bootstrap.
- [x] P101.3 Update MKRF docs and validate surfaces.
  - [x] Document parent-checkout materialization commands.
  - [x] Replace stale branch-era FreshForge `--run-id` / `--report` examples
        with the released `--workdir` / `--namespace` CLI shape.
  - [x] Run provider discovery, validate, inspect, and plan from the parent
        checkout.
  - [x] Run the bounded FreshForge materialization workflow from the parent
        checkout.
  - [x] Verify `models` and `data/source` payload availability and Arbutus
        remote coverage.
- [x] P101.4 Close out.
  - [x] Merge the MKRF materialization PR first.
  - [x] Update the parent MKRF submodule pointer.
  - [x] Re-run parent validation after the pointer update.
  - [x] Update `CHANGE_LOG.md`, issue comments, and PR closeout records.

## Phase 102: FreshForge Materialization Overlay For K3Z (`#280`)

Status: complete

Goal: add K3Z as the third model-instance materialization workflow using the
generic `femic.materialization` provider, while handling K3Z's current
plain-git storage mode without requiring DataLad/git-annex.

- [x] P102.1 Create lifecycle and planning surfaces.
  - [x] Open parent issue `#280` and K3Z issue
        `UBC-FRESH/femic-k3z-instance#35`.
  - [x] Create parent branch `feature/p102-k3z-materialization-overlay`.
  - [x] Create K3Z branch `feature/freshforge-materialization-overlay`.
  - [x] Add `planning/phase102_k3z_materialization_overlay.md`.
- [x] P102.2 Extend generic materialization for plain-git instances.
  - [x] Add optional overlay field `annex.enabled`, defaulting to `true`.
  - [x] Treat annex initialization, special-remote enablement, and annex audit
        nodes as no-op success nodes when annex is disabled.
  - [x] Make `materialize_paths` verify working-tree paths instead of running
        `datalad get` when annex is disabled.
- [x] P102.3 Add K3Z-owned overlay and workflow.
  - [x] Add K3Z materialization overlay and workflow YAML under
        `external/femic-k3z-instance/workflows/freshforge/`.
  - [x] Use only the generic `femic.materialization.*` provider namespace.
  - [x] Install the K3Z editable package during materialization so K3Z-owned
        FEMIC extension entry points are available after bootstrap.
- [x] P102.4 Update docs and validate surfaces.
  - [x] Document parent-checkout materialization commands in K3Z README and
        operator runbook.
  - [x] Run provider discovery, validate, inspect, and plan from the parent
        checkout.
  - [x] Run the bounded FreshForge materialization workflow from the parent
        checkout.
  - [x] Verify the workflow writes only ignored `runtime/freshforge/` output.
- [x] P102.5 Close out.
  - [x] Merge the K3Z materialization PR first.
  - [x] Update the parent K3Z submodule pointer.
  - [x] Re-run parent validation after the pointer update.
  - [x] Update `CHANGE_LOG.md`, issue comments, and PR closeout records.

## Phase 103: FreshForge Materialization Overlay For TSA29 (`#282`)

Status: complete

Goal: add TSA29 as the fourth model-instance materialization workflow using the
generic `femic.materialization` provider, with annex-enabled DataLad/git-annex
materialization through `arbutus-s3`.

- [x] P103.1 Create lifecycle and planning surfaces.
  - [x] Open parent issue `#282` and TSA29 issue
        `UBC-FRESH/femic-tsa29-instance#21`.
  - [x] Create parent branch `feature/p103-tsa29-materialization-overlay`.
  - [x] Create TSA29 branch `feature/freshforge-materialization-overlay`.
  - [x] Add `planning/phase103_tsa29_materialization_overlay.md`.
- [x] P103.2 Add TSA29-owned overlay and workflow.
  - [x] Add TSA29 materialization overlay and workflow YAML under
        `external/femic-tsa29-instance/workflows/freshforge/`.
  - [x] Use only the generic `femic.materialization.*` provider namespace.
  - [x] Install the TSA29 editable package during materialization so TSA29-owned
        FEMIC extension entry points are available after bootstrap.
- [x] P103.3 Update TSA29 docs and validate surfaces.
  - [x] Document parent-checkout materialization commands in TSA29 README,
        getting-started docs, and rebuild runbook.
  - [x] Run provider discovery, validate, inspect, and plan from the parent
        checkout.
  - [x] Run the bounded FreshForge materialization workflow from the parent
        checkout.
  - [x] Verify required payload availability and `arbutus-s3` remote coverage.
- [x] P103.4 Close out.
  - [x] Merge the TSA29 materialization PR first.
  - [x] Update the parent TSA29 submodule pointer.
  - [x] Re-run parent validation after the pointer update.
  - [x] Update `CHANGE_LOG.md`, issue comments, and PR closeout records.

## Phase 104: FreshForge Workflow Discovery And User Entry Points (`#284`)

Status: complete

Goal: add a small generic discovery layer so users can find existing
FreshForge workflows without knowing repo internals.

- [x] P104.1 Create lifecycle and planning surfaces.
  - [x] Open parent issue `#284`.
  - [x] Create branch `feature/p104-freshforge-workflow-discovery`.
  - [x] Add `planning/phase104_freshforge_workflow_discovery.md`.
- [x] P104.2 Add generic workflow discovery.
  - [x] Scan `examples/freshforge/*workflow.yaml`.
  - [x] Scan `external/*/workflows/freshforge/*workflow.yaml`.
  - [x] Report workflow id/name, provider refs, kind, load status, and
        diagnostics without hardcoding instance names.
- [x] P104.3 Add user-facing CLI helpers.
  - [x] Add `python -m femic freshforge workflows list`.
  - [x] Add `python -m femic freshforge workflows list --json`.
  - [x] Add `python -m femic freshforge workflows commands PATH`.
  - [x] Keep the commands non-mutating and FreshForge imports lazy.
- [x] P104.4 Update docs and validate.
  - [x] Add a workflow discovery section to the FreshForge guide.
  - [x] Run focused discovery tests and lint.
  - [x] Run Sphinx docs with warnings as errors.
  - [x] Confirm the boundary guard still rejects named-instance references in
        `src/femic`.
- [x] P104.5 Close out.
  - [x] Update `CHANGE_LOG.md`.
  - [x] Post progress and closeout comments on issue `#284`.
  - [x] Open and merge the parent PR after checks pass.

## Phase 105: TFL6 Executable FreshForge Model-Build Acceptance (`#286`)

Status: complete

Goal: promote the existing TFL6 model-build workflow from validation/planning
into a parent-checkout `freshforge run` acceptance path through Patchworks
Matrix Builder, using P104 workflow discovery as the user entry point and the
generic `femic.*` provider stages as the execution surface.

- [x] P105.1 Create lifecycle and planning surfaces.
  - [x] Open parent issue `#286`.
  - [x] Open TFL6 issue `UBC-FRESH/femic-tfl6-instance#162`.
  - [x] Create parent branch `feature/p105-tfl6-executable-model-build`.
  - [x] Create TFL6 branch `feature/p19-freshforge-executable-model-build`.
  - [x] Add `planning/phase105_tfl6_executable_model_build.md`.
- [x] P105.2 Update the TFL6 model-build workflow for parent-checkout
      execution.
  - [x] Change TFL6 workflow `instance_root` parameters from `.` to
        `external/femic-tfl6-instance`.
  - [x] Keep run config, Patchworks config, bundle, checkpoint, output, log,
        and artifact paths instance-relative.
  - [x] Remove `rebuild_spec` from the `validate_case` node so generic case
        preflight remains the first workflow stage.
- [x] P105.3 Update operator docs and discovery path.
  - [x] Document `python -m femic freshforge workflows list`.
  - [x] Document `python -m femic freshforge workflows commands
        external/femic-tfl6-instance/workflows/freshforge/tfl6_model_build_workflow.yaml`.
  - [x] Document separate rebuild-spec validation before execution.
  - [x] State that materialization should run first when the TFL6 submodule is
        thin or incomplete.
- [x] P105.4 Validate and run TFL6 executable acceptance.
  - [x] Run discovery, rendered commands, validate, inspect, and plan from the
        parent checkout.
  - [x] Resolve the generic SiteProd species alias gap exposed by TFL6
        broadleaf code `MB`.
  - [x] Replace the blocked upstream compile node with a generic accepted BTC
        handoff preflight that consumes the reviewed TFL6 `03_input`,
        `04_output`, and treated-curve artifacts.
  - [x] Remove the spreadsheet freshness requirement from the accepted BTC
        handoff path so post-TIPSY execution only requires the canonical BTC
        input CSV and recorded BatchTIPSY output.
  - [x] Run the FreshForge model-build workflow with `--workdir
        runtime/freshforge --namespace tfl6/model-build --json`.
  - [x] Inspect FreshForge run records, FEMIC runtime manifests, exported
        Patchworks package, Matrix Builder manifest, compiled tracks, and TFL6
        Git status.
- [x] P105.5 Close out.
  - [x] Merge the TFL6 PR first if workflow/docs changed.
  - [x] Update the parent TFL6 submodule pointer.
  - [x] Re-run parent validation after the pointer update.
  - [x] Update `CHANGE_LOG.md`, issue comments, and PR closeout records.

## Phase 106: MKRF Executable FreshForge Model-Build Acceptance (`#288`)

Status: active

Goal: promote the existing MKRF model-build workflow into the second
parent-checkout executable FreshForge acceptance lane, proving that generic
FEMIC provider stages work with the instance-owned `mkrf.*` provider namespace
and released FreshForge execution APIs.

- [x] P106.1 Create lifecycle and planning surfaces.
  - [x] Open parent issue `#288`.
  - [x] Open MKRF issue `UBC-FRESH/femic-mkrf-instance#50`.
  - [x] Create parent branch `feature/p106-mkrf-executable-model-build`.
  - [x] Create MKRF branch `feature/freshforge-executable-model-build`.
  - [x] Add parent and MKRF planning notes.
- [x] P106.2 Refresh the MKRF FreshForge adapter for released FreshForge.
  - [x] Replace old `execute_node(...)` / `ProviderExecutionResult` usage with
        `run_node(...)` / `ProviderRunResult`.
  - [x] Return deterministic command, return-code, stdout/stderr,
        diagnostics, outputs, and JSON-safe artifact metadata.
  - [x] Update MKRF tests from old execution symbols to
        `freshforge.execution.run_workflow`.
- [ ] P106.3 Update the MKRF model-build workflow for parent-checkout
      execution.
  - [ ] Change workflow `instance_root` parameters from `.` to
        `external/femic-mkrf-instance`.
  - [ ] Keep run config, Patchworks config, source data, model package, bundle,
        runtime, and artifact paths instance-relative.
  - [ ] Remove `rebuild_spec` from the `validate_case` node and document
        rebuild-spec validation as a separate pre-run check.
- [ ] P106.4 Update MKRF docs/runbooks and discovery path.
  - [ ] Route operators through `python -m femic freshforge workflows list`.
  - [ ] Document `python -m femic freshforge workflows commands
        external/femic-mkrf-instance/workflows/freshforge/mkrf_model_build_workflow.yaml`.
  - [ ] Document released `freshforge run --workdir runtime/freshforge
        --namespace mkrf/model-build --json` command shape.
  - [ ] State that materialization should run first when the MKRF submodule is
        thin or incomplete.
- [ ] P106.5 Validate and run MKRF executable acceptance.
  - [ ] Refresh local FreshForge to PyPI `freshforge==0.1.0a5`.
  - [ ] Run discovery, rendered commands, validate, inspect, and plan from the
        parent checkout.
  - [ ] Run the MKRF FreshForge model-build workflow from the parent checkout.
  - [ ] Inspect FreshForge records, MKRF runtime manifests, ForestModel XML,
        fragments, tracks, Matrix Builder manifest, and MKRF Git status.
  - [ ] Audit required MKRF model/source paths against `arbutus-s3`.
- [ ] P106.6 Close out.
  - [ ] Merge the MKRF PR first if workflow/docs/code changed.
  - [ ] Update the parent MKRF submodule pointer.
  - [ ] Re-run parent validation after pointer reconciliation.
  - [ ] Update `CHANGE_LOG.md`, issue comments, and PR closeout records.

### Detailed Next Steps Notes

- Active detailed planning now lives in:
  - `planning/phase106_mkrf_executable_model_build.md`
  - `planning/phase105_tfl6_executable_model_build.md`
  - `planning/phase104_freshforge_workflow_discovery.md`
  - `planning/phase103_tsa29_materialization_overlay.md`
  - `planning/phase102_k3z_materialization_overlay.md`
  - `planning/phase98_materialization_execution_surface.md`
  - `planning/phase98_freshforge_materialization_template.md`
  - `planning/phase87_parent_instance_reference_audit.md`
  - `planning/phase78_figrecover_integration_notes.md`
  - `planning/phase75_bcdata_resolver_evaluation_notes.md`
  - `planning/phase74_tfl6_instance_bootstrap_notes.md`
  - `planning/phase71_tsa29_patchworks_rebuild_notes.md`
  - `planning/phase72_tsa29_release_notes.md`
  - `planning/phase68_tsa29_comparison_docs_notes.md`
  - `planning/roadmap_notes_archive.md`
- Current edge:
  - `P106` / `#288` is active: MKRF is the second parent-checkout executable
    FreshForge model-build acceptance lane after TFL6. The first required
    implementation move is refreshing the instance-owned `mkrf.*` provider
    from the older branch-era `execute_node(...)` / `ProviderExecutionResult`
    API to the released FreshForge `run_node(...)` / `ProviderRunResult`
    contract before running the real MKRF model-build workflow.
  - `P105` / `#286` is complete: TFL6 Phase 19 promoted the TFL6-owned
    model-build graph into the first parent-checkout executable FreshForge
    acceptance lane through Matrix Builder. The workflow remains instance-owned
    under `external/femic-tfl6-instance`; FEMIC core keeps only generic
    `femic.*` provider stages and P104 workflow discovery helpers.
  - `P104` / `#284` is complete: FEMIC now has generic FreshForge workflow
    discovery and user-facing CLI helpers so users can list checked-out
    workflow documents and print copy-paste `freshforge validate`, `inspect`,
    `plan`, and `run --workdir runtime/freshforge --namespace ... --json`
    command blocks without knowing the repo path layout. PR `#285` merged with
    green build and package-release checks.
  - `P103` / `#282` is complete: the fourth real `femic.materialization`
    FreshForge workflow targets the TSA29 submodule from the parent FEMIC
    checkout. TSA29 is a DataLad/git-annex dataset, so the first overlay uses
    `annex.enabled: true` and `arbutus-s3` for the launch-critical model
    materialization path. The TSA29 PR has merged, the parent submodule pointer
    has been updated, and merged-pointer validation passed.
  - `P102` / `#280` is complete: the third real `femic.materialization`
    FreshForge workflow targets the K3Z submodule from the parent FEMIC
    checkout. K3Z is a plain-git snapshot, generic `annex.enabled: false`
    support is implemented, the K3Z PR has merged, the parent submodule pointer
    has been updated, and merged-pointer validation passed.
  - `P101` / `#278` is complete and merged: the second real
    `femic.materialization` FreshForge workflow targets the MKRF submodule
    materialization ritual from the parent FEMIC checkout. The MKRF
    materialization PR has merged, the parent submodule pointer has been
    updated, and merged-pointer validation passed.
  - `P100` / `#276` is complete and merged: the first real
    `femic.materialization` FreshForge workflow targets the TFL6 submodule
    materialization ritual from the parent FEMIC checkout. The TFL6 Phase 18 PR
    has merged, the parent submodule pointer has been updated, and
    merged-pointer validation passed.
  - `P99` / `#274` is complete and merged: FreshForge is now published on PyPI
    as `freshforge==0.1.0a5`, and FEMIC's optional dependency metadata plus
    docs use the normal `femic[freshforge]` install path.
  - `P98` / `#270` is complete: the reusable `femic.materialization`
    FreshForge provider supplies generic materialization nodes, overlay
    parsing/validation, mocked execution tests, and a public-safe report-only
    fixture workflow. Real MKRF, TFL6, K3Z, and TSA29 overlays remain
    follow-on instance phases.
  - `P97` / `#268` is complete: report-only namespace-aware FreshForge
    artifact metadata resolves workflow-declared artifact paths through
    FreshForge `RunContext.resolve_path(...)` for provider run records. FEMIC
    command construction remains unchanged, validation/inspection/planning
    remain non-mutating, and command-output routing remains deferred.
  - `P96` / `#266` is complete: FEMIC's optional FreshForge provider
    integration now targets released FreshForge `v0.1.0a4`. The provider
    exposes `run_node(...)`, returns `ProviderRunResult`, reports provider
    version `0.2.0a1`, and keeps validation/inspection/planning non-mutating.
    P99 superseded the temporary empty `femic[freshforge]` extra after the
    FreshForge PyPI package became available. Local smoke checks verified
    provider discovery, validate, inspect, plan, matrix help, and a safe
    one-node `freshforge run --namespace smoke --json` path.
  - `P95` / `#262` is complete: FEMIC `0.2.0a1` is published as the core
    decoupling alpha release. GitHub prerelease `FEMIC 0.2.0a1`, tag
    `v0.2.0a1`, TestPyPI workflow `28562782006`, and PyPI workflow
    `28562848866` all completed successfully after the optional-dependency
    metadata fix. PyPI JSON metadata confirms `0.2.0a1` with both wheel and
    sdist. The unrelated `external/femic-public-data` submodule state remains
    out of scope for this release lane.
  - `P94` / `#254` is complete: remaining named-instance references were
    scrubbed from `src/femic`, packaged resources, generic templates, and
    generic CLI help. The boundary guard now rejects any new named
    `mkrf`, `k3z`, `tsa29`, `tfl6`, or `femic-*-instance` reference under
    `src/femic` unless a future roadmap phase deliberately reopens the
    allowlist.
  - `P93` / `#253` is complete: the packaged K3Z/TSA29 built-in instance
    catalog is now replaced by external catalog discovery and explicit user
    catalog file support. K3Z and TSA29 own their installable instance catalog
    metadata through installed instance-package providers.
  - `P92` / `#252` is complete: Patchworks variant registry discovery now
    supports installed instance providers and user overlays, while K3Z/MKRF
    Patchworks variant definitions live in their instance packages under
    `UBC-FRESH/femic-k3z-instance#31` and
    `UBC-FRESH/femic-mkrf-instance#46`.
  - `P91` / `#251` is complete: generic TSR adjudication overlay dispatch now
    lives in FEMIC core, and TSA29 row classifications, checkpoint policy,
    reconstruction-gap interpretation overrides, and active adjudication report
    notes live in the TSA29-owned `tsa29_femic` package under issue
    `UBC-FRESH/femic-tsa29-instance#17`.
  - `P90` / `#250` is complete: generic named-pipeline contract-handler
    dispatch now lives in FEMIC core, and the TSA29 strict locked-chain
    contract implementation lives in the TSA29 instance package under issue
    `UBC-FRESH/femic-tsa29-instance#15`.
  - `P89` / `#249` is complete: K3Z-owned package/config surfaces now own the
    K3Z FMG auxiliary support and pipeline policy defaults.
  - `P88` / `#248` is complete locally: the arms-length extension boundary is
    documented, P89-P94 issues are open, and a source guard now prevents new
    named-instance references from entering `src/femic` without an explicit
    roadmap-linked allowlist update.
  - `P87` / `#246` is complete: the remaining MKRF-specific legacy ForestModel
    XML builder moved from parent `femic.fmg` into the MKRF instance package
    under `mkrf_femic.legacy_xml`; MKRF PR
    `UBC-FRESH/femic-mkrf-instance#45` is merged and parent PR `#247` passed
    required checks.
  - `P86` / `#244` is complete: MKRF-specific pipeline and workflow
    implementation now lives in the MKRF instance repository as installable
    package `mkrf_femic`, and parent FEMIC no longer exposes
    `femic instance mkrf-*`.
  - `P85` / `#241` is complete: FEMIC core owns the generic `femic`
    FreshForge provider, while the MKRF instance owns provider namespace
    `mkrf.*`.
  - `P84` / `#234` is complete: FreshForge execution was proven locally against
    the MKRF rebuild workflow through Patchworks Matrix Builder after the
    machine was connected through the UBC VPN.
  - `P83` / `#232` is complete pending parent PR merge: tracked TSA29
    `runtime/**` artifacts were removed from the instance Git index, the
    cleaned TSA29 PR was merged, and a fresh short-path Windows clone
    materialized `models/tsa29_patchworks_model/blocks` from `arbutus-s3` with
    a valid polygon shapefile header.
  - `P82` / `#230` is active: expanded TFL6 Patchworks runtime model
    directories, excluding scenario/run outputs under `analysis/`, must become
    tracked, public-annexed instance payloads so recursive DataLad
    materialization produces a runnable model tree without requiring a
    separate archive-unpack step.
  - `P80` / `#220` is complete: FEMIC exposes reusable model-building stages as
    a plan-only FreshForge provider. PR `#226` was squash-merged to `main`
    after focused local verification plus green docs and release-artifact
    checks.
  - `P81` / `#227` is complete: MKRF owns the first real instance-level
    FreshForge workflow contract at
    `workflows/freshforge/mkrf_model_build_workflow.yaml`; the next evolution is
    P84 executable orchestration.
  - `P79` / `#211` is planned: FEMIC will grow reusable open LiDAR
    acquisition, terrain-raster, slope, and terrain-derived hydrography
    workflows. The immediate TFL 6 instance uses a public DEM steep-slope
    repair lane first; this parent package phase is the reusable long-term
    implementation path.
  - `P78.6` / `#209` is complete: the optional document-figure recovery
    workflow is documented in `docs/guides/document-figure-recovery.rst`, the
    CLI reference includes `femic doc figures` commands, and
    `femic.document_figures` has a curated API page. Focused tests, scoped
    lint, and Sphinx warning-clean validation passed. The Phase 78 branch is
    ready for PR review and merge.
  - `P77.3` / `#207` complete: parent FEMIC docs and pipeline registry metadata
    now state that AFLB/CMFLB is the stand/growth universe, final THLB is a
    managed-share overlay, and NTHLB remains unmanaged/full-retention forest
    with untreated curve coverage.
  - `P77.2` / `#206` complete: parent FEMIC docs now clarify that top-area
    selected AU bins are the canonical curve-family universe, while
    non-selected AU bins or stands are remapped/imputed to selected curve
    families through the reviewed lexicographic remap audit. This was a
    docs-only correction and did not start TFL 6 Phase 4 model-input table
    generation.
  - `P77.1` complete under `#204`: the parent FEMIC TFL 6 docs pointer is
    wired into the sample-models toctree and builds warning-clean. Remaining
    publication work is the branch/PR lifecycle, not Phase 4 implementation.
  - `P68` complete
  - `P69.1` complete
  - `P69.2` complete
  - `P69.3` complete
  - `P69.4` complete; follow-up PRs are merged and the issue set is closed
  - `P70.1` complete
  - `P70.2` complete
  - `P70.3` complete
  - `P70.4` complete: branch publication, PRs, merge, and issue closeout are handled for `UBC-FRESH/femic-mkrf-instance#21`
  - `P71` complete locally and published for review via:
    - `UBC-FRESH/femic-tsa29-instance#7`
    - `UBC-FRESH/femic#195`
  - `P72.1` complete
  - `P72.2a` complete
  - `P72.2b` complete: a fresh thin clone at `C:\Users\gep\Projects\tsa29_release_coldclone_20260606a` now materializes the launch-critical Patchworks package from `arbutus-s3`, and the cold-clone docs build plus direct package-surface checks passed
  - `P72.2c` complete: `UBC-FRESH/femic-tsa29-instance` pre-release `v1.0.0-alpha1` is published from merged `main` commit `45af95c`
  - `P72.2d` complete: release closeout is recorded in the parent planning surfaces and governing TSA29 release issue `#8`
  - `P72` complete
  - `P73.1` complete
  - `P73.2` complete locally for `UBC-FRESH/femic-mkrf-instance#26`; publication and issue closeout remain next
  - `P74.1` complete under `#199`: `UBC-FRESH/femic-tfl6-instance` exists and
    is linked under `external/femic-tfl6-instance`.
  - `P74.2` complete: instance Phase 1 planning, source/data bootstrap,
    future Phase 2 through Phase 5 parent/child issue tree, and dependency
    order are recorded.
  - `P74.3a` complete: parent PR conflict resolution preserves MKRF as Phase
    73 and moves the TFL 6 bootstrap lane to Phase 74.
  - Current active edge for this PR is `P74.3b`: merge parent PR
    `UBC-FRESH/femic#200`, then close instance Phase 1 parent
    `UBC-FRESH/femic-tfl6-instance#4` under its closure rule.
  - `P75.1` complete under parent FEMIC issue `#201`: the comparison contract
    now names FEMIC's resolver/fetch/DWDS surfaces, fixes the initial query
    corpus, records comparison metrics, and scopes BC Gov `designatedlands` as
    manifest/workflow-pattern evidence.
  - `P75.2a` complete: FEMIC baseline resolver outputs were captured under
    `runtime/phase75/` for the fixed corpus, summarized in the Phase 75 planning
    note, and left untracked as runtime artifacts.
  - Current active edge for this lane is `P75.2b`: run the same query corpus
    through `bcdata` with a reproducible R script or CLI harness, then compare
    against the FEMIC baseline with special attention to the recent TFL 6
    source-layer resolution challenge.
  - `P75.2b` complete: `scripts/phase75_bcdata_resolve_baseline.r` captured
    the same corpus through `bcdata` into runtime-only CSV/JSON outputs.
  - `P75.2c` complete: the side-by-side comparison shows `bcdata` is useful
    evidence for free-text ranking improvements, but does not justify replacing
    FEMIC's resolver because FEMIC's object-name and curated alias logic wins
    important modelling-specific cases.
  - `P75.3a` and `P75.3b` complete: useful `bcdata` behaviour will be
    reimplemented natively in Python; no R, `bcdata`, `reticulate`, or embedded
    Python-to-R dependency is added to normal FEMIC runtime paths.
  - `P75.4` complete for the `bcdata` native-resolver path: FEMIC now carries
    targeted free-text aliases and DEM preference logic, tests, and docs
    attribution without adopting an R runtime dependency.
  - `P75.3c` and `P75.3d` complete: `designatedlands` is accepted only as an
    external source-manifest and overlay/restriction-class recipe reference,
    not as a FEMIC runtime dependency. The upstream dependency footprint
    includes GDAL/`ogr2ogr`, Rasterio/GeoPandas, PostGIS PostgreSQL, optional
    Docker, SQL overlay functions, and substantial raster-processing RAM.
  - `P75` complete: issue `#201` now has the comparison evidence, accepted
    native resolver improvements, `designatedlands` boundary decision, and
    closeout notes. Remaining work is branch/PR lifecycle only, not additional
    resolver implementation.
  - `P76.1` complete under `#203`: explicit GeoPackage/vector THLB checkpoint
    inputs are supported for TFL 6 while TSA29 Feather restart seams and
    legacy-checkpoint rejection remain intact.
