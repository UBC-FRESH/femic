# Phase 113 — WBI AOI Model-Build Pipelines (TSAs 08/16/24/40/41)

Tracking issue: `UBC-FRESH/femic#316` (WBI birds repro dependency).
Branch: `feature/p113-wbi-aoi-model-build`.

## Goal

Deliver the femic + FreshForge model-build path for the five WBI birds AOI
management units (TSAs 08/16/24/40/41) so the manuscript repro chain
(`UBC-FRESH/wbi-birds`) is self-bootstrappable from fresh public data through
the ws3 handoff (`inputs/ws3/<model>.{lan,are,yld,act,trn}`).

## Findings that shape the work

- The shipped FreshForge surface is the generic `femic` provider (8 node
  types: `validate_case`, `geospatial_preflight`, `compile_upstream`,
  `accepted_btc_handoff`, `btc_post_tipsy`, `export_patchworks`,
  `patchworks_preflight`, `matrix_build`) plus `femic.materialization`.
- **There is no Woodstock/ws3 node**: `femic export woodstock` and
  `femic instance ws3-smoke` are CLI-only, so a per-MU graph cannot currently
  deliver the sections the engine consumes. P113.1 closes this.
- The P110 `femic.model_build.*` six-stage graph is **documentation-only** in
  this checkout (`src/femic/model_build.py` ships records, not providers).
  P113 builds on the shipped generic graph instead; the P110 gap is tracked
  separately.
- The open `p115-ws3-export-package` branch adds `export_ws3_package()` to
  `femic.ws3_bridge` (bundle + checkpoint -> ws3 sections). P113.1 stays on
  main's `build_ws3_sections_from_femic_woodstock` and adds a thin CLI; if P115
  merges first, P113.1 may collapse onto it.
- Per-MU parameters already exist in main: `config/tipsy/tsa08|16|24|40|41.yaml`
  (expert-authored TIPSY rules) and `config/vdyp_fit_policy.yaml`
  (`tsa_overrides` for the five TSAs, recovered from the `wbi_ria_yield` era).
- Fresh data lane is built in: `femic instance init --download-bc-vri`
  downloads VRI 2024 L1 R1 + VDYP7-input 2024; `pipeline/io.py` already prefers
  the 2024 paths over 2019.

## Decisions

- **Instance layout**: five public instance repos, one per management unit —
  `UBC-FRESH/femic-tsa08-instance`, `femic-tsa16-instance`,
  `femic-tsa24-instance`, `femic-tsa40-instance`, `femic-tsa41-instance`.
  Each is a DataLad-managed dataset under the UBC-FRESH org, wired into femic
  as an `external/` git submodule, with the established instance structure
  (see below). This answers open question 2 in `UBC-FRESH/wbi-birds`
  `planning/femic-map.md` (femic-style instances).
- **Artifact set per MU**: both. The instance keeps the model-input bundle
  (`data/model_input_bundle/`) and exports Woodstock CSVs
  (`output/woodstock/`) + ws3 sections (`output/ws3/<model>.{lan,...}`); the
  engine stages only the sections, with checksums recorded in the instance
  manifest (open questions 1 and 3).
- **Data lane**: fresh **VRI 2025** — `VEG_COMP_LYR_R1_POLY_2025` +
  `VEG_COMP_VDYP7_INPUT_POLY_AND_LAYER_2025`, resolved via
  `femic data bcdc-resolve`; direct zips under
  `https://pub.data.gov.bc.ca/datasets/02dba161-fdb7-48ae-a4bb-bd6ef017c36d/current/`
  (AOI-scoped WFS fetch is available as an alternative: five-TSA bbox
  `830258,878714,1393732,1682754` EPSG:3005). FADM TSA boundaries + SiteProd
  come from `external/femic-public-data` (`arbutus-s3`, verified reachable).
  Extend `BC_VRI_DOWNLOADS` + `pipeline/io.py` resolution candidates to prefer
  the 2025 vintage over 2024/2019.

## Instance structure (consistency requirement)

Each instance repo mirrors the established instance layout (exemplar:
`UBC-FRESH/femic-tsa29-instance`):

- DataLad dataset (`.datalad/config`, annex `.gitattributes` rules) under
  `UBC-FRESH`; wired as a femic `external/` git submodule.
- `config/`: `run_profile.tsa<code>.yaml`, `tipsy/tsa<code>.yaml`,
  `rebuild.spec.yaml`, `rebuild.allowlist.yaml`,
  `patchworks.runtime.windows.yaml`.
- `workflows/freshforge/tsa<code>_model_build_workflow.yaml` (P113.3).
- `docs/`: Sphinx site (`conf.py`, `index.rst`, content pages) +
  `.github/workflows/docs-pages.yml` publishing to GitHub Pages.
- `README.md`, `QUICKSTART.md`, `ROADMAP.md`, `CHANGE_LOG.md`.
- `data/` (annex-backed intermediates + per-MU clips), `output/`, `models/`,
  `runbooks/`, `evidence/`.

## Tasks

- [x] P113.1 — FreshForge ws3 handoff nodes + CLI.
  - [x] `femic.export_woodstock` node (wraps `femic export woodstock`).
  - [x] `femic.ws3_bridge` node (wraps a new `femic export ws3-sections` CLI
        around `build_ws3_sections_from_femic_woodstock`).
  - [x] Tests: provider metadata + command construction + CLI round-trip on the
        minimal 4-CSV fixture.
- [x] P113.2 — Five per-MU instance repos.
  - [x] Create `UBC-FRESH/femic-tsa<code>-instance` for 08/16/24/40/41
        (DataLad datasets, public); scaffold via `femic instance init`; per-MU
        run profile + TIPSY config + rebuild spec + runbooks.
  - [x] Standard structure incl. Sphinx docs site + GitHub Pages workflow.
  - [x] Fresh VRI 2025 + FADM data lane documented and materialized.
  - [x] Wire as submodules (`external/`); README/QUICKSTART present
        (instance-catalog entry points deferred).
- [x] P113.3 — Per-MU model-build graphs.
  - [x] `workflows/freshforge/tsa<code>_model_build_workflow.yaml` per MU,
        plan-green (`freshforge validate|plan`; six-node chain).
  - [x] Documented instance roots + data contract; closed the femic-map open
        questions (see `UBC-FRESH/wbi-birds` `planning/femic-map.md`).
- [x] P113.4 — Executable smoke on TSA24 (2026-10-12).
  - [x] Compile lane on fresh VRI clip (VDYP via Wine; TIPSY/BTC via Wine,
        TIPSYbtc extracted from the public TIPSY 4.7 MSI).
  - [x] Bundle -> Woodstock CSVs -> ws3 sections (species splits; periods
        contract for `.are` ages and `.act` action timing).
  - [x] Engine handshake: `build_model` + one ε-scenario on the genuine export
        (optimal; harvest 41.9M m3, birds 59.4M).

## Out of scope

- Patchworks Matrix Builder acceptance for the five MUs (the engine path does
  not need it; the generic graph keeps the nodes available).
- The P110 `femic.model_build.*` provider implementation (tracked separately).
- Manuscript-side scenario grids and analysis (owned by `UBC-FRESH/wbi-birds`).

## Verification

- `ruff format src tests` / `ruff check src tests` / `mypy src` / `pytest`
- `femic export ws3-sections` round-trip on the `tests/test_ws3_bridge.py`
  fixture
- `freshforge plan` green for each per-MU graph in a femic-installed
  environment
- Engine-side: `wbi.compile_instance` + `build_model` + one ε-scenario on the
  TSA24 export
