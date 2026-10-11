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

- **Instance layout**: one public instance repo
  (`UBC-FRESH/femic-wbi-aoi-instance`) hosting the five MUs as per-MU overlays
  (run profiles, TIPSY configs, rebuild spec, per-MU FreshForge graphs), wired
  into femic as `external/femic-wbi-aoi-instance`. This answers open question 2
  in `UBC-FRESH/wbi-birds` `planning/femic-map.md` (femic-style overlay, not
  engine-side instances).
- **Artifact set per MU**: both. The instance keeps the model-input bundle
  (`data/model_input_bundle/`) and exports Woodstock CSVs
  (`output/woodstock/`) + ws3 sections (`output/ws3/<model>.{lan,...}`); the
  engine stages only the sections, with checksums recorded in the instance
  manifest (open questions 1 and 3).
- **Data lane**: fresh VRI 2024 via `instance init --download-bc-vri`;
  FADM TSA boundaries + SiteProd from `external/femic-public-data`
  (`arbutus-s3`, verified reachable from this host). Record dataset ids +
  checksums in the instance evidence.

## Tasks

- [ ] P113.1 — FreshForge ws3 handoff nodes + CLI.
  - [ ] `femic.export_woodstock` node (wraps `femic export woodstock`).
  - [ ] `femic.ws3_bridge` node (wraps a new `femic export ws3-sections` CLI
        around `build_ws3_sections_from_femic_woodstock`).
  - [ ] Tests: provider metadata + command construction + CLI round-trip on the
        minimal 4-CSV fixture.
- [ ] P113.2 — WBI AOI instance/overlay machinery.
  - [ ] Create `UBC-FRESH/femic-wbi-aoi-instance`; scaffold via
        `femic instance init`; five per-MU overlays (run profiles + TIPSY
        configs + rebuild spec).
  - [ ] Fresh VRI 2024 + FADM data lane documented and materialized.
  - [ ] Wire as submodule; instance catalog/README.
- [ ] P113.3 — Per-MU model-build graphs.
  - [ ] `workflows/freshforge/wbi_tsa<code>_model_build_workflow.yaml` per MU,
        plan-green (`freshforge validate|inspect|plan`).
  - [ ] Documented instance roots + data contract; close the femic-map open
        questions.
- [ ] P113.4 — Executable smoke on at least one MU (TSA24).
  - [ ] Compile lane on fresh VRI clip (VDYP via Wine; TIPSY/BTC via Wine,
        TIPSYbtc extracted from the public TIPSY 4.7 MSI).
  - [ ] Bundle -> Woodstock CSVs -> ws3 sections.
  - [ ] Engine handshake: `wbi.compile_instance` + `build_model` + one
        scenario against the genuine export.

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
