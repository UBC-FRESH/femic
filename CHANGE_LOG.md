# Change Log

## 2026-03-22
- Made pre-stacked SiteProd the default Stage 00 runtime path when canonical `siteprod.tif` + `siteprod.bandmap.json` are present, falling back to ArcRasterRescue/ArcPy only when those artifacts are missing.
- Added canonical SiteProd artifact resolution helpers and band-map loading so per-stand SiteProd assignment works without runtime layer discovery.
- Verified the real Windows K3Z clean-start path now uses external 2024 VRI plus canonical SiteProd artifacts, skips ArcRasterRescue/ArcPy, runs native VDYP successfully, regenerates `02_input-tsak3z.dat`, and resumes cleanly through `femic tsa post-tipsy` after a refreshed BatchTIPSY handoff.

## 2026-02-24
- Added the `femic` Typer CLI scaffold under `src/femic` with stub commands and module entry point.
- Added `typer` and `rich` to `requirements.txt` to support the new CLI.
- Created `ROADMAP.md` (moved from planning) with phased refactor tasks, a Next Focus list, and detailed next steps.
- Added `AGENTS.md` contributor operating notes.
- Added `pyproject.toml` with a `femic` console script entrypoint and verified `python -m femic --help` works in the venv.
- Wired `femic run` to the legacy `00_data-prep.py` pipeline with `--tsa`/`--resume` overrides and resume-aware skips.
- Fixed the legacy workflow wrapper to locate `00_data-prep.py` from the repo root.
- Added preflight checks in `femic run` for Wine, VDYP assets, and required data inputs.
- Made `--resume` skip the AU/curve table rebuild when cached model input bundle CSVs exist.
- Replaced downstream bundle naming with `model_input_bundle` (no legacy auto-copy).
- Removed legacy `data/spadescbm_bundle` directory.
- Normalized TSA codes to zero-padded strings when loading data to avoid `KeyError: '08'`.
- Added a fail-fast guard with null-summary diagnostics when AU assignment yields no rows.
- Rebuilt `scsi_au` from the bundle `au_table` on resume to restore AU lookups.
- Added a `--debug-rows` CLI option to limit VRI input rows for faster debugging.
- Re-applied debug row limiting after checkpoint reloads to keep the dataset small.
- Fixed debug row helper ordering so early checkpoint loads can call it.
- Skipped strata without VDYP curves to prevent failures in debug runs.
- Disabled cached checkpoint/output reuse when debug rows are enabled.
- Resolved external dataset paths relative to the repo root (`../data`).
- Added `FEMIC_EXTERNAL_DATA_ROOT` override for external dataset locations.
- Fixed raster masking calls to pass geometry lists for MultiPolygon support.

## 2026-02-26
- Guarded AU/curve assignment against missing stratum+SI mappings and emit a warning summary before
  dropping unmapped rows.
- Documented missing AU/curve mapping behavior in the README and roadmap notes.

## 2026-02-28
- Added `planning/VDYP_debug_notes.md` capturing missing-curve causes and VDYP fragility notes.
- Expanded the roadmap with VDYP diagnostics + metadata hardening tasks.
- Added VDYP run diagnostics with JSONL logs and extra preflight checks for the Wine runner.
- Added curve-fit diagnostics plus toe-fit auto-trimming with warning fallback logging.
- Documented VDYP diagnostic log locations in the README and roadmap notes.
- Switched curve anchoring to quasi-origin `(1, 1e-6)` to preserve positive-value filtering.
- Added pre-VDYP TSA prep checkpoints (`data/vdyp_prep-tsa{tsa}.pkl`) for warm-start debugging.
- Made pre-VDYP checkpoint serialization robust by removing non-picklable fit-function closures.
- Added missing validation scaffolding (`tests/`, `docs/`, `.pre-commit-config.yaml`) so required
  repo checks run successfully.
- Completed a TSA 08 rerun and verified curve-event logs record quasi-origin points
  (`first_age=1.0`, `first_volume=1e-06`).
- Added `femic vdyp report` (new `src/femic/vdyp/reporting.py`) to summarize VDYP JSONL diagnostics,
  including status/stage/phase counts, parse errors, and first-point anchor conformance.
- Added fallback handling in `run_vdyp(nsamples=\"auto\")` for small strata (`n < min_samples`) to run
  all available records instead of failing with `AssertionError`.
- Added extra missing-output guards in curve smoothing/TIPSY input stages so absent
  stratum+SI VDYP outputs emit warning events and do not crash immediately.
- Forced a fresh TSA 08 debug rerun (`--debug-rows 500`) and captured populated diagnostics:
  `vdyp_runs.jsonl` (77 events) and `vdyp_curve_events.jsonl` (26 events).

## 2026-03-01
- Hardened `process_vdyp_out` against sparse/degenerate curve inputs by falling back to a
  quasi-origin-anchored curve with warning metadata instead of crashing on empty MAI/argmax
  calculations.
- Updated VDYP stratum+SI registration so `scsi_au`/`au_scsi` entries are created only for combos
  that survive operability/species filters and have usable VDYP results.
- Hardened AU/curve table assembly in `00_data-prep.py` to skip VDYP curve combos missing AU
  mappings and print a summarized warning instead of raising `KeyError`.
- Re-ran a forced fresh TSA 08 debug run (`femic run --tsa 08 --resume --debug-rows 500`) to
  verify progress; run now completes end-to-end with populated diagnostics
  (`vdyp_runs.jsonl`: 77 events, `vdyp_curve_events.jsonl`: 27 events).
- Replaced most row-wise `swifter.apply(...)` usage with pandas `.apply(...)` by default
  (optional opt-in via `FEMIC_USE_SWIFTER=1`) to reduce nondeterministic debug-run behavior.
- Added `FEMIC_DISABLE_IPP` control (default enabled) so debug runs do not depend on an
  ipyparallel controller.
- Added `FEMIC_SKIP_STANDS_SHP` control and defaulted it to on during debug runs to skip final
  TSA shapefile export while iterating.
- Investigated persistent end-of-run `sys.excepthook` noise; message still appears despite
  successful run completion (`exit code 0`), but no longer blocks pipeline outputs/log generation.
- Updated `CITATION.cff` repository metadata URL to
  `https://github.com/UBC-FRESH/wbi_ria_yield`.
- Fixed `fit_stratum` row selection to keep DataFrame shape (`f_.loc[[sc]]`) and prevent
  singleton-stratum `KeyError: np.False_` failures in SI filtering.
- Added empty-species safeguards in TIPSY input assembly: stratum+SI combinations with no
  species candidates now emit `no_species_candidates` warnings and are skipped instead of
  raising `IndexError`.
- Made `swifter` import lazy in `00_data-prep.py` so monkeypatching is only enabled when
  `FEMIC_USE_SWIFTER=1`, reducing side effects in default debug runs.
- Changed `run_data_prep` to run `00_data-prep.py` in a subprocess and stream filtered output,
  eliminating persistent non-fatal legacy shutdown noise from normal `femic run` logs.
- Reviewed and reconciled roadmap next-focus status:
  marked completed items for README quickstart and VDYP diagnostics hardening,
  updated NF2a wording to reflect subprocess execution, and added new NF7/NF8 work queues
  for operator-facing run artifacts and deterministic regression checks.
- Added `femic run` options `--run-id` and `--log-dir`, propagated through the legacy wrapper as
  `FEMIC_RUN_ID` and `FEMIC_LOG_DIR`.
- Added per-run manifest emission at `run_manifest-<run_id>.json` with command metadata,
  options, env flags, TSA list, checkpoint presence, and expected run-scoped log paths.
- Switched VDYP diagnostic outputs to run-scoped TSA files:
  `vdyp_runs-tsa{tsa}-{run_id}.jsonl` and `vdyp_curve_events-tsa{tsa}-{run_id}.jsonl`.
- Added deterministic TSA08 VDYP regression fixtures and tests for stable summary counts.
- Added warning-budget guardrails in `femic vdyp report` with threshold flags
  (`--max-curve-warnings`, `--max-first-point-mismatches`, parse-error maxima, and minimum event
  counts) and non-zero exit on budget violations.
- Added raw VDYP process stream artifact capture per TSA/run:
  `vdyp_stdout-tsa{tsa}-{run_id}.log` and `vdyp_stderr-tsa{tsa}-{run_id}.log`.
- Expanded run manifest payloads with runtime/package versions, resolved key paths, and
  per-TSA artifact existence inventory for run/curve JSONL and stdout/stderr artifacts.
- Reconciled Phase 1 roadmap checkboxes with completed NF deliverables so roadmap state now shows
  Phase 1 complete and Phase 2 as the active next implementation frontier.
- Started Phase 2 extraction by adding `src/femic/pipeline/{io,vdyp,tsa,plots}.py` helper modules.
- Updated legacy workflow to consume shared pipeline helpers for TSA normalization, run-path
  resolution, and VDYP artifact log path construction.
- Added unit tests for new pipeline helper modules and updated manifest tests to import shared
  VDYP path builders.
- Replaced hardcoded default TSA list in pipeline helpers with dev-config-driven defaults from
  `config/dev.toml` (`[run].default_tsa_list`), using `["08"]` fallback for local testing.
- Added `PipelineRunConfig` and `build_pipeline_run_config` so `femic run` now passes explicit
  typed run settings from CLI to legacy workflow wrapper (first `P2.1b` seam).
- Added `LegacyExecutionPlan` and `build_legacy_execution_plan` so legacy subprocess command/env/
  path/checkpoint resolution is centralized in pipeline helpers instead of inline workflow code.
- Added `femic.pipeline.stages.run_legacy_subprocess` plus tests, and refactored legacy workflow
  to call this stage executor for filtered subprocess streaming.
- Added `femic.pipeline.manifest` and moved run-manifest payload/version/file-write logic out of
  workflow wrapper into reusable helpers; updated workflow/tests to consume the new module.
- Added `femic.pipeline.pre_vdyp` to centralize pre-VDYP checkpoint serialization/load/save and
  refactored `01a_run-tsa.py` to use these helpers; added dedicated unit tests.
- Removed the redundant roadmap `Next Focus` section after folding completed items into phase
  status/checklist tracking.
- Added `femic.pipeline.vdyp_io` for shared VDYP infile writer and output table parser helpers,
  refactored `01a_run-tsa.py` to consume them, and added unit tests.
- Added `femic.pipeline.vdyp_sampling.nsamples_from_curves` and refactored legacy auto-sampling
  loop to call this helper; added focused unit tests for empty and finite-result cases.
- Added `femic.pipeline.vdyp_logging` for run-id resolution, run-scoped VDYP log paths, and JSONL/
  text append helpers; refactored `01a_run-tsa.py` to consume these helpers and added unit tests.
- Updated `femic.pipeline.vdyp.build_vdyp_log_paths` to reuse
  `femic.pipeline.vdyp_logging.build_tsa_vdyp_log_paths`, removing duplicate VDYP artifact filename
  construction logic.
- Added `femic.pipeline.vdyp_curves` with reusable quasi-origin anchoring, toe-fill, and
  `process_vdyp_out` helpers; refactored `01a_run-tsa.py` to consume this module and added focused
  unit tests for empty-input and toe-fit-fallback behavior.
- Added `femic.pipeline.tipsy` with shared VDYP-derived scalar helpers
  (`compute_vdyp_site_index`, `compute_vdyp_oaf1`) and refactored TSA-specific TIPSY parameter
  builders in `01a_run-tsa.py` to use these helpers; added dedicated unit tests.
- Added `evaluate_tipsy_candidate` and `build_tipsy_warning_event` to
  `femic.pipeline.tipsy`, and refactored `01a_run-tsa.py` TIPSY AU selection to consume these
  helpers for centralized eligibility checks and standardized warning-event payloads.
- Added draft TIPSY manual-handoff config scaffolding in `config/tipsy/` (`README.md` and
  `template.tsa.yaml`) and documented the human-in-the-loop TIPSY boundary in `README.md`,
  including variability expectations across legacy TSA rule implementations.
- Added `femic.pipeline.tipsy_config` with TSA YAML loading/validation and config-rule parameter
  generation, plus optional runtime wiring in `01a_run-tsa.py` to use
  `config/tipsy/tsa{tsa}.yaml` (or `.yml`) when present (legacy in-code dict logic remains fallback).
- Added `config/tipsy/tsa08.yaml` as the first concrete TSA migration to config-driven TIPSY rules,
  and extended config assignment resolution to support dynamic tokens like
  `$leading_species_tipsy` for legacy-compatible species normalization (`SX -> SW`).
- Added `config/tipsy/tsa16.yaml` as a second concrete migration (capturing higher-complexity
  multi-species/GW assignment logic) and expanded tests to validate repo-backed TSA16 config loading
  and rule selection.
- Added `config/tipsy/tsa24.yaml` with BEC-dependent branching (`SBS`/`ESSF`) translated from legacy
  rules, and expanded tests to validate repo-backed TSA24 rule selection for both branches.
- Added `config/tipsy/tsa40.yaml` and `config/tipsy/tsa41.yaml`, completing migration coverage for
  the original five TSA rule examples, and extended config token resolution with
  `$species_rank_<n>_tipsy` / `$species_pct_<n>` for dynamic species composition assignments.
- Updated legacy run behavior to require TSA YAML TIPSY config by default (fail-fast when missing),
  with explicit opt-in fallback to legacy in-code dispatch via `FEMIC_TIPSY_USE_LEGACY=1`; added a
  test asserting all five migrated TSA config files are present/loadable.
- Added `femic tipsy validate` CLI command to validate config-driven TIPSY handoff files
  (`config/tipsy/tsaXX.yaml`) and report missing requested TSAs before pipeline execution.
- Reduced notebook-script global coupling at the 00/01a/01b stage boundary by changing
  `01a_run-tsa.run_tsa(...)` and `01b_run-tsa.run_tsa(...)` to accept explicit runtime args, and
  updating `00_data-prep.py` to pass these values directly instead of setting `tsa`/`stratum_col`
  module globals before invocation.
- Replaced broad legacy module namespace injection (`__dict__.update(globals())`) with explicit,
  validated context binding through `femic.pipeline.legacy_context.bind_legacy_module_context(...)`
  plus scoped 01a/01b symbol allowlists, and added tests for the new binder.
- Extracted VDYP batch prep/run/import orchestration into new
  `femic.pipeline.vdyp_stage.execute_vdyp_batch(...)` helper and rewired `01a_run-tsa.py` to call
  this stage seam for subprocess execution + structured run logging.
- Added `tests/test_vdyp_stage.py` coverage for success, parse-error, and timeout behavior of the
  extracted VDYP stage helper.
- Extracted bootstrap dispatch orchestration into
  `femic.pipeline.vdyp_stage.execute_bootstrap_vdyp_runs(...)` and rewired the `force_run_vdyp`
  branch in `01a_run-tsa.py` to use the shared helper for per-stratum SI run-context logging and
  result accumulation.
- Extended `tests/test_vdyp_stage.py` with bootstrap success and dispatch-error coverage.
- Extracted curve-smoothing dispatch orchestration into
  `femic.pipeline.vdyp_stage.execute_curve_smoothing_runs(...)` and rewired `01a_run-tsa.py` to
  consume returned smoothed-curve records for `vdyp_smoothxy` table assembly and downstream plot
  overlays.
- Extended `tests/test_vdyp_stage.py` with curve-smoothing coverage for missing-output warning
  logging and per-curve kwarg-override propagation.
- Extracted legacy VDYP overlay plotting into
  `femic.pipeline.vdyp_stage.plot_curve_overlays(...)` and rewired `01a_run-tsa.py` to delegate
  per-stratum overlay plotting through this shared helper.
- Reduced the explicit 01a legacy context allowlist by removing stale symbols no longer used after
  stage extraction (`Path`, `curve_fit`, `shlex`, `subprocess`).
- Extended `tests/test_vdyp_stage.py` with overlay-plot orchestration assertions for plot calls and
  axis/legend behavior.
- Extracted smooth-curve table assembly/write into
  `femic.pipeline.vdyp_stage.build_smoothed_curve_table(...)` and rewired `01a_run-tsa.py` to use
  this helper for consolidated DataFrame construction + feather persistence.
- Reduced `RUN_01A_CONTEXT_SYMBOLS` further by dropping no-longer-used symbols
  (`_curve_fit`, `wraps`) after curve-table helper extraction.
- Extended `tests/test_vdyp_stage.py` with `build_smoothed_curve_table(...)` coverage for assembled
  rows and output write callback behavior.
- Extracted VDYP result-resolution branching into
  `femic.pipeline.vdyp_stage.load_or_build_vdyp_results_tsa(...)` and rewired `01a_run-tsa.py` to
  use this helper for force-run/bootstrap, per-TSA cache loads, combined-cache fallback, and cache
  persistence.
- Reduced `RUN_01A_CONTEXT_SYMBOLS` again by removing stale `pickle` dependency after migrating
  cache/load orchestration into the shared stage helper.
- Extended `tests/test_vdyp_stage.py` with `load_or_build_vdyp_results_tsa(...)` coverage for
  force-run, TSA-cache, combined-cache, and compat-loader fallback paths.
- Extracted VDYP polygon/layer table loading into
  `femic.pipeline.vdyp_stage.load_vdyp_input_tables(...)` and rewired `01a_run-tsa.py` to use this
  shared loader instead of inline source/feather branch logic.
- Reduced `RUN_01A_CONTEXT_SYMBOLS` again by removing stale `gpd` dependency after input-table
  loader extraction.
- Extended `tests/test_vdyp_stage.py` with `load_vdyp_input_tables(...)` coverage for feather-cache
  reads and source-geodatabase load+persist behavior.
- Added `femic.pipeline.vdyp_stage.build_curve_fit_adapter(...)` and rewired `01a_run-tsa.py` to
  build a local `curve_fit` adapter from `curve_fit_impl`, centralizing legacy
  `maxfev -> max_nfev` compatibility handling.
- Removed obsolete `wraps_impl` argument plumbing from `01a_run-tsa.run_tsa(...)` and the
  `00_data-prep.py` `run_tsa(...)` callsite.
- Extended `tests/test_vdyp_stage.py` with `build_curve_fit_adapter(...)` coverage for
  `maxfev` translation and existing `max_nfev` passthrough behavior.
- Reduced additional legacy global-state coupling by extending `01a_run-tsa.run_tsa(...)` with
  explicit path/export arguments (`vdyp_results_*`, `vdyp_input_pandl_path`,
  `vdyp_{ply,lyr}_feather_path`, `tipsy_params_columns`, `tipsy_params_path_prefix`) and passing
  these from `00_data-prep.py`.
- Trimmed `RUN_01A_CONTEXT_SYMBOLS` to remove now-redundant path/export globals after the signature
  handoff refactor.
- Extended `01a_run-tsa.run_tsa(...)` to accept mutable run-state/data inputs explicitly
  (`results`, `vdyp_results`, `vdyp_curves_smooth`, `scsi_au`, `au_scsi`, `tipsy_params`,
  `si_levelquants`, `species_list`, `vdyp_curves_smooth_tsa_feather_path_prefix`) and passed these
  from `00_data-prep.py`.
- Trimmed `RUN_01A_CONTEXT_SYMBOLS` again so context binding now only injects baseline runtime
  helper modules/flags instead of per-run dataset/state payload variables.
- Converted `01b_run-tsa.run_tsa(...)` to accept explicit runtime data inputs
  (`results`, `au_scsi`, `tipsy_curves`, `vdyp_curves_smooth`) with direct argument passing from
  `00_data-prep.py`.
- Removed all 01b legacy context payload requirements by setting `RUN_01B_CONTEXT_SYMBOLS = ()`
  and localizing `matplotlib.pyplot`/`seaborn` imports inside `01b_run-tsa.py`.
- Extracted TIPSY table assembly/export logic into `femic.pipeline.tipsy`
  (`build_tipsy_input_table`, `write_tipsy_input_exports`) and rewired `01a_run-tsa.py` to
  delegate xlsx/dat output generation through these helpers.
- Extended `tests/test_tipsy.py` with coverage for TIPSY export helper behavior (row assembly,
  empty-input error, and output file writes).
- Extracted config-vs-legacy TIPSY builder selection into
  `femic.pipeline.tipsy_config.resolve_tipsy_param_builder(...)` and rewired `01a_run-tsa.py` to
  use this shared resolver instead of inline branch logic.
- Extended `tests/test_tipsy_config.py` with resolver coverage for config-preferred, forced-legacy,
  and missing-config failure behavior.
- Localized `distance`/`itertools`/`operator`/`os` imports inside `01a_run-tsa.run_tsa(...)`,
  removing these requirements from injected legacy context.
- Trimmed `RUN_01A_CONTEXT_SYMBOLS` accordingly; 01a context now only injects
  `_femic_resume_effective`, `kwarg_overrides`, `np`, `pd`, `plt`, and `sns`.
- Extracted TIPSY candidate-selection/AU-assignment orchestration into
  `femic.pipeline.tipsy.build_tipsy_params_for_tsa(...)` and rewired `01a_run-tsa.py` to delegate
  eligibility filtering, warning logging, and `scsi_au`/`au_scsi`/`tipsy_params` map updates.
- Added explicit runtime arguments to `01a_run-tsa.run_tsa(...)` for
  `resume_effective`, `force_run_vdyp`, and `kwarg_overrides_for_tsa`, with direct argument passing
  from `00_data-prep.py`.
- Localized `numpy`/`pandas`/`matplotlib`/`seaborn` imports inside `01a_run-tsa.run_tsa(...)` and
  reduced `RUN_01A_CONTEXT_SYMBOLS` to `()`, eliminating required 01a context injection.
- Extended `tests/test_tipsy.py` with `build_tipsy_params_for_tsa(...)` coverage for success,
  missing-VDYP warning, and no-species warning paths.
- Extracted legacy in-code TIPSY rule implementations and exclusion setup from `01a_run-tsa.py`
  into `femic.pipeline.tipsy_legacy` and rewired 01a to consume
  `build_tipsy_exclusion()`/`get_legacy_tipsy_builders()` from this module.
- Added `tests/test_tipsy_legacy.py` with coverage for legacy TSA key dispatch, exclusion-map
  presence, and baseline TSA08 builder output fields.
- Added legacy-context regression tests asserting `RUN_01A_CONTEXT_SYMBOLS` and
  `RUN_01B_CONTEXT_SYMBOLS` are empty and that binding with an empty required-symbol list is a
  no-op.
- Removed `bind_legacy_module_context(...)` callsites and related legacy-context imports from
  `00_data-prep.py` now that both 01a/01b required-symbol lists are empty.
- Removed the inactive `if 0:` duplicate TIPSY export branch in `01a_run-tsa.py`, leaving the
  helper-driven export path (`build_tipsy_input_table` + `write_tipsy_input_exports`) as the single
  active flow.
- Removed `legacy_context` symbol re-exports from `femic.pipeline.__init__` to reflect current
  runtime behavior (no required legacy context injection path in the active orchestration flow).
- Removed additional inactive `if 0:` notebook-era debug/reload blocks from `00_data-prep.py`
  (manual checkpoint rollback/cache/load snippets and dormant shapefile export path) to reduce dead
  code around active orchestration logic.
- Added `tests/test_legacy_orchestration_wiring.py` AST-based regression checks that enforce explicit
  01a/01b `run_tsa(...)` keyword handoff arguments and verify no
  `bind_legacy_module_context(...)` call remains in `00_data-prep.py`.
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
  checks (wine/bin/params), default log-path resolution, run-event logging, batch execution, and
  sampling orchestration handoff.
- Rewired `01a_run-tsa.py` bootstrap execution to call `run_vdyp_for_stratum(...)` directly and
  removed nested `run_vdyp`/`_tsa_log_path` definitions from `run_tsa(...)`.
- Extended `tests/test_vdyp_stage.py` with `run_vdyp_for_stratum(...)` coverage and updated
  `tests/test_legacy_01a_structure.py` guardrails to assert 01a no longer calls
  `run_vdyp_sampling(...)` directly and no longer defines nested `run_vdyp`.
- Added `femic.pipeline.vdyp_stage.build_run_vdyp_for_stratum_runner(...)`, a reusable helper that
  binds per-TSA runtime context (`tsa`, `run_id`, VDYP tables, fit hooks, and run-log paths) into
  a bootstrap-compatible `run_vdyp_fn(sample_table, **kwargs)` callable.
- Rewired `01a_run-tsa.py` bootstrap flow to build `run_vdyp_fn` through
  `build_run_vdyp_for_stratum_runner(...)`, removing inline lambda assembly of
  `run_vdyp_for_stratum(...)` kwargs from `run_tsa(...)`.
- Extended `tests/test_vdyp_stage.py` with forwarding/binding coverage for the new runner-builder
  helper, and updated `tests/test_legacy_01a_structure.py` guardrails to assert 01a calls the
  builder helper and no longer calls `run_vdyp_for_stratum(...)` directly.
- Added `femic.pipeline.vdyp_stage.build_bootstrap_vdyp_results_runner(...)`, a reusable helper
  that binds per-TSA bootstrap dispatch inputs into a zero-argument callback compatible with
  `load_or_build_vdyp_results_tsa(...)`.
- Rewired `01a_run-tsa.py` to pass `run_bootstrap_fn` produced by
  `build_bootstrap_vdyp_results_runner(...)`, removing inline
  `run_bootstrap_fn=lambda: execute_bootstrap_vdyp_runs(...)` closure assembly.
- Extended `tests/test_vdyp_stage.py` with coverage for bootstrap-runner binding/forwarding and
  updated `tests/test_legacy_01a_structure.py` guardrails to assert 01a uses the builder helper
  and does not pass an inline lambda to `run_bootstrap_fn`.
- Added `femic.pipeline.vdyp_stage.build_fit_stratum_curves_runner(...)`, a reusable helper that
  binds stratum-fit context into `compile_one_fn(stratumi, sc)` callbacks for
  `compile_strata_fit_results(...)`.
- Rewired `01a_run-tsa.py` to build/pass `compile_one_fn` via
  `build_fit_stratum_curves_runner(...)`, removing inline fit-call closure assembly in the pre-VDYP
  compilation path.
- Extended `tests/test_vdyp_stage.py` with fit-runner binding coverage and updated
  `tests/test_legacy_01a_structure.py` guardrails so 01a must call the builder helper and must not
  pass inline lambdas to `compile_one_fn`.
- Extracted legacy notebook fit functions from `01a_run-tsa.py` into
  `femic.pipeline.vdyp_curves` (`legacy_fit_func1`, `legacy_fit_func1_bounds_func`,
  `legacy_fit_func2`, `legacy_fit_func2_bounds_func`) and rewired 01a to consume these shared
  helpers.
- Extended `tests/test_vdyp_curves.py` with deterministic checks for legacy fit-function outputs and
  bounds, and updated `tests/test_legacy_01a_structure.py` guardrails to assert 01a no longer
  defines nested legacy fit functions.
- Added `femic.pipeline.tsa.apply_stratum_alias_map(...)` to encapsulate selected-strata retention
  and alias-fallback assignment for `*_matched` stratum columns.
- Rewired `01a_run-tsa.py` to call `apply_stratum_alias_map(...)` for stratum matching, removing
  the final nested helper definition (`match_stratum`) from `run_tsa(...)`.
- Extended `tests/test_pipeline_helpers.py` with deterministic alias-application coverage and
  updated `tests/test_legacy_01a_structure.py` guardrails to assert 01a calls the helper and has no
  nested `match_stratum`.
- Added `femic.pipeline.vdyp_stage.CurveSmoothingPlotConfig` and
  `build_curve_smoothing_plot_config(...)` to centralize legacy curve-smoothing plot defaults
  (plot toggle, `figsize`, palette setup, `palette_flavours`, `alphas`) behind a shared stage
  helper seam.
- Rewired `01a_run-tsa.py` curve-smoothing overlay path to call
  `build_curve_smoothing_plot_config(...)` and consume returned defaults instead of defining inline
  smoothing plot/palette constants.
- Extended `tests/test_vdyp_stage.py` with deterministic defaults coverage for the new helper and
  updated `tests/test_legacy_01a_structure.py` guardrails to assert 01a calls this helper and no
  longer assigns inline smoothing `palette_flavours`/`alphas` constants.
- Removed dead `legacy_fit_func2`/`legacy_fit_func2_bounds_func` imports and local
  `fit_func2`/`fit_func2_bounds_func` assignments from `01a_run-tsa.py`; these values were no
  longer consumed by active stage paths.
- Added `tests/test_legacy_01a_structure.py` guardrails asserting `run_tsa(...)` no longer assigns
  local legacy fit2 bindings.
- Removed inline TIPSY staging constant assignments from `01a_run-tsa.py`
  (`min_operable_years`, `si_iqrlo_quantile`, local `verbose`) and now rely on
  `build_tipsy_params_for_tsa(...)` shared defaults.
- Extended `tests/test_legacy_01a_structure.py` with guardrails asserting 01a no longer assigns
  these constants inline and does not override corresponding
  `build_tipsy_params_for_tsa(...)` keyword defaults.
- Extended `CurveSmoothingPlotConfig` / `build_curve_smoothing_plot_config(...)` to include overlay
  axis defaults (`xlim`, `ylim`) and rewired `01a_run-tsa.py` to pass
  `smooth_plot_cfg.xlim`/`smooth_plot_cfg.ylim` to `plot_curve_overlays(...)` instead of inline
  tuple literals.
- Extended `tests/test_vdyp_stage.py` defaults coverage for new axis config fields and added
  `tests/test_legacy_01a_structure.py` AST guardrails asserting overlay axes are sourced from
  `smooth_plot_cfg`.
- Added `StrataDistributionPlotConfig` and `build_strata_distribution_plot_config(...)` in
  `femic.pipeline.plots` to centralize 01a stratum-distribution plotting defaults.
- Rewired the 01a stratum-distribution plotting block to consume
  `build_strata_distribution_plot_config(...)` values instead of inline constants.
- Extended `tests/test_pipeline_helpers.py` with defaults coverage for the new helper and added AST
  guardrails in `tests/test_legacy_01a_structure.py` asserting 01a calls the helper and no longer
  assigns inline strata-plot constants.
- Rewired `01a_run-tsa.py` strata diagnostic plot output writes to call
  `femic.pipeline.plots.strata_plot_paths(...)` and save to helper-provided PDF/PNG paths instead
  of inline `"plots/strata-tsa%s.*"` literals.
- Added AST guardrails in `tests/test_legacy_01a_structure.py` asserting 01a calls
  `strata_plot_paths(...)` and no longer embeds inline strata output path literals.
- Added `femic.pipeline.plots.resolve_strata_plot_ordering(...)` to centralize
  abundance-vs-lexical stratum ordering for distribution plots.
- Rewired `01a_run-tsa.py` to call `resolve_strata_plot_ordering(...)`, removing the inline
  `sort_lex` branch and local ordering assembly.
- Extended `tests/test_pipeline_helpers.py` with deterministic ordering coverage for default and
  lexical modes, and added AST guardrails in `tests/test_legacy_01a_structure.py` asserting 01a
  calls the helper and no longer assigns local `sort_lex`.
- Added `femic.pipeline.plots.plot_strata_site_index_diagnostics(...)` to encapsulate early 01a
  stratum diagnostics plotting (`site_index_median` histogram + abundance-vs-SI scatter).
- Rewired `01a_run-tsa.py` to call `plot_strata_site_index_diagnostics(...)` and removed direct
  inline histogram/scatter plotting calls from `run_tsa(...)`.
- Extended `tests/test_pipeline_helpers.py` with deterministic coverage for this helper and added
  AST guardrails in `tests/test_legacy_01a_structure.py` asserting 01a calls the helper and no
  longer invokes direct `plt.scatter(...)` for this stage.
- Added `femic.pipeline.plots.render_strata_distribution_plot(...)` to encapsulate 01a stratum
  distribution rendering (barplot + violinplot + labels + xlim + PDF/PNG writes).
- Rewired `01a_run-tsa.py` to call `render_strata_distribution_plot(...)`, removing direct inline
  seaborn bar/violin calls and save-path plumbing from `run_tsa(...)`.
- Extended `tests/test_pipeline_helpers.py` with deterministic coverage for the new rendering helper
  and added AST guardrails in `tests/test_legacy_01a_structure.py` asserting 01a calls the helper
  and no longer performs direct `sns.barplot(...)`/`sns.violinplot(...)` calls in this stage.
- Added `femic.pipeline.tipsy_config.resolve_tipsy_runtime_options(...)` to centralize
  `FEMIC_TIPSY_CONFIG_DIR`/`FEMIC_TIPSY_USE_LEGACY` environment resolution.
- Rewired `01a_run-tsa.py` to call `resolve_tipsy_runtime_options(...)` instead of reading
  `os.environ` directly for TIPSY config/legacy flags.
- Extended `tests/test_tipsy_config.py` with defaults/override coverage for the new helper and
  added AST guardrails in `tests/test_legacy_01a_structure.py` asserting 01a no longer reads
  `os.environ` directly for this stage.
- Added `StratumFitRunConfig` and `build_stratum_fit_run_config(...)` in
  `femic.pipeline.vdyp_stage` to centralize pre-VDYP stratum fit-stage defaults.
- Rewired `01a_run-tsa.py` pre-VDYP fit compilation path to consume
  `build_stratum_fit_run_config(...)` instead of assigning fit-stage constants inline.
- Extended `tests/test_vdyp_stage.py` with defaults coverage for the new helper and added AST
  guardrails in `tests/test_legacy_01a_structure.py` asserting 01a calls the helper and no longer
  assigns inline stratum fit-stage constants.
- Added `femic.pipeline.pre_vdyp.pre_vdyp_checkpoint_path(...)` to centralize per-TSA pre-VDYP
  checkpoint path construction.
- Rewired `01a_run-tsa.py` to call `pre_vdyp_checkpoint_path(...)` instead of constructing
  `"./data/vdyp_prep-tsa%s.pkl"` inline.
- Extended `tests/test_pre_vdyp.py` with path-helper coverage and added AST guardrails in
  `tests/test_legacy_01a_structure.py` asserting 01a calls the helper and no longer embeds
  `vdyp_prep-tsa` literals.

## 2026-03-02
- Added `femic.pipeline.vdyp.build_vdyp_cache_paths(...)` to centralize per-TSA cache path
  templates for `vdyp_results-tsa*.pkl` and `vdyp_curves_smooth-tsa*.feather`.
- Rewired `01a_run-tsa.py` to source per-TSA cache artifact paths via
  `build_vdyp_cache_paths(...)` instead of inline `%`-formatted string templates.
- Expanded helper/guardrail coverage:
  `tests/test_pipeline_helpers.py` now validates `build_vdyp_cache_paths(...)`, and
  `tests/test_legacy_01a_structure.py` asserts 01a calls the helper and no longer assigns inline
  VDYP cache path templates.
- Removed local `os.path` checks from `01a_run-tsa.py` in favor of `Path(...).is_file()` for
  checkpoint/cache existence checks, reducing stale local import coupling.
- Added an AST guardrail in `tests/test_legacy_01a_structure.py` asserting `run_tsa(...)` no longer
  imports `os` locally for path checks.
- Ran full required validation gate successfully:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (154 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Updated the Phase 2 task checklist in `ROADMAP.md` with explicit `P2.1b` subtask status
  (cache-path extraction done, local path-check cleanup done, remaining handoff/signature reduction
  still queued).
- Queued the next execution batch in roadmap notes:
  `vdyp_cache_paths` payload handoff from 00->01a, `run_tsa(...)` argument surface reduction via
  typed config payload, and extraction of 00_data-prep 01a/01b module-load orchestration helpers.
- Added `Legacy01ARuntimeConfig` in `src/femic/pipeline/legacy_runtime.py` and rewired
  `01a_run-tsa.run_tsa(...)` to consume this typed runtime payload instead of a long list of
  individual path/runtime parameters.
- Collapsed 00->01a VDYP cache handoff to a single `vdyp_cache_paths` payload built in
  `00_data-prep.py` via `build_vdyp_cache_paths(...)` and passed through runtime config.
- Added shared legacy orchestration helpers in `src/femic/pipeline/stages.py`:
  `load_legacy_module(...)` and `run_legacy_tsa_loop(...)`, and rewired 00_data-prep 01a/01b loops
  to use them.
- Added direct-script import fallback in `00_data-prep.py` that prepends `src/` when needed so
  `python 00_data-prep.py` can resolve `femic.pipeline` helpers without requiring prior editable
  install.
- Expanded tests and guardrails:
  `tests/test_pipeline_stages.py` now covers new stage helpers,
  `tests/test_legacy_orchestration_wiring.py` validates runtime-config + shared helper wiring, and
  `tests/test_legacy_01a_structure.py` checks cache-path reads from `runtime_config`.
- Added reusable stage-setup helpers in `src/femic/pipeline/stages.py`:
  `initialize_legacy_tsa_stage_state(...)`, `prepare_tsa_index(...)`, and
  `should_skip_if_outputs_exist(...)`.
- Added `build_legacy_01a_runtime_config(...)` in `src/femic/pipeline/legacy_runtime.py` so
  00_data-prep no longer assembles the 01a runtime payload inline.
- Rewired `00_data-prep.py` to use these helpers for stage-state initialization, TSA index setup,
  resume output-skip checks, and 01a runtime-config construction.
- Expanded tests:
  `tests/test_pipeline_stages.py` now covers the new setup/runtime helpers and
  `tests/test_legacy_orchestration_wiring.py` asserts 00-data-prep wiring uses these helper seams.
- Added `src/femic/pipeline/bundle.py` to centralize model-input bundle pathing and I/O helpers
  (`resolve_bundle_paths`, `bundle_tables_ready`, `load_bundle_tables`, `write_bundle_tables`,
  `ensure_scsi_au_from_table`).
- Rewired 00_data-prep post-01b bundle orchestration to consume shared bundle helpers for
  resume-time bundle reads, path wiring, CSV writes, and `scsi_au` backfill.
- Added `tests/test_bundle.py` with deterministic coverage for bundle path readiness, table
  load/write behavior, TSA normalization, and `scsi_au` reconstruction from AU tables.
- Expanded `tests/test_legacy_orchestration_wiring.py` guardrails to assert 00_data-prep calls
  bundle helper seams.
- Added `build_bundle_tables_from_curves(...)` and `BundleAssemblyResult` to
  `src/femic/pipeline/bundle.py`, extracting the heavy AU/curve table assembly loop from
  00_data-prep into a reusable helper.
- Rewired 00_data-prep to call `build_bundle_tables_from_curves(...)` and consume returned
  diagnostics for missing AU mappings while preserving existing warning output behavior.
- Expanded `tests/test_bundle.py` with deterministic coverage for managed/unmanaged curve assembly
  and missing AU-mapping diagnostics.
- Extended `tests/test_legacy_orchestration_wiring.py` guardrails to assert
  `build_bundle_tables_from_curves(...)` seam usage in 00_data-prep.
- Added residual post-bundle strata helpers in `src/femic/pipeline/tsa.py`:
  `assign_stratum_matches_from_au_table(...)` and
  `assign_si_levels_from_stratum_quantiles(...)`.
- Rewired 00_data-prep to use these helpers for stratum matching against AU-table strata and SI
  level assignment by quantile bands, replacing the corresponding inline loops.
- Expanded `tests/test_pipeline_helpers.py` with deterministic coverage for both new TSA helpers.
- Extended `tests/test_legacy_orchestration_wiring.py` guardrails to assert
  `assign_stratum_matches_from_au_table(...)` and
  `assign_si_levels_from_stratum_quantiles(...)` seam usage in 00_data-prep.
- Added AU assignment/null-diagnostics helpers to `src/femic/pipeline/tsa.py`:
  `lookup_scsi_au_base`, `assign_au_ids_from_scsi`, `summarize_missing_au_mappings`,
  `build_au_assignment_null_summary`, and `validate_nonempty_au_assignment`.
- Rewired the 00_data-prep AU assignment stage to consume these helpers, removing inline
  `_lookup_scsi_au` / `au_from_scsi` logic and preserving warning + fail-fast behavior.
- Expanded `tests/test_pipeline_helpers.py` with deterministic AU helper coverage and updated
  `tests/test_legacy_orchestration_wiring.py` guardrails to assert AU helper seam usage.
- Added `assign_curve_ids_from_au_table(...)` to `src/femic/pipeline/bundle.py` to centralize
  managed/unmanaged curve ID assignment from AU table records.
- Rewired 00_data-prep to call `assign_curve_ids_from_au_table(...)` instead of inline
  `assign_curve1`/`assign_curve2` function definitions and row-wise assignments.
- Expanded `tests/test_bundle.py` with deterministic curve-id assignment coverage and updated
  `tests/test_legacy_orchestration_wiring.py` guardrails to assert
  `assign_curve_ids_from_au_table(...)` seam usage.
- Added `assign_thlb_area_and_flag(...)` to `src/femic/pipeline/tsa.py` to centralize THLB area and
  THLB binary-flag assignment rules.
- Rewired 00_data-prep to call `assign_thlb_area_and_flag(...)` instead of inline `thlb_area` and
  `assign_thlb` functions.
- Expanded `tests/test_pipeline_helpers.py` with deterministic THLB helper coverage and updated
  `tests/test_legacy_orchestration_wiring.py` guardrails to assert
  `assign_thlb_area_and_flag(...)` seam usage.
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

## 2026-03-02
- Completed the queued append-primitive audit in `src/femic/pipeline/vdyp_logging.py` by adding a
  shared internal file-append helper (`_append_text_fragment(...)`) and rewiring both
  `append_line(...)` and `append_text(...)` to consume it.
- Preserved output contracts: `append_line(...)` still appends newline-terminated records and
  `append_text(...)` still appends exact text fragments.
- Expanded deterministic coverage in `tests/test_vdyp_logging.py` with
  `test_append_text_appends_without_overwriting` to guard append-vs-overwrite behavior.
- Completed validation gate for this slice:
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
- Completed validation gate for this slice:
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
- Completed validation gate for this slice:
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
- Completed validation gate for this slice:
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
- Completed validation gate for this slice:
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
- Completed validation gate for this slice:
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
- Completed validation gate for this slice:
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
- Completed validation gate for this slice:
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
- Completed validation gate for this slice:
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
- Completed validation gate for this slice:
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
- Completed validation gate for this slice:
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
- Completed validation gate for this slice:
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
- Completed validation gate for this slice:
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
- Completed validation gate for this slice:
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
- Completed validation gate for this slice:
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
- Completed validation gate for this slice:
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
- Marked `P2.2` complete in `ROADMAP.md` now that `P2.2a`/`P2.2b`/`P2.2c` are all closed.
- Completed validation gate for this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest`,
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice (ASAP closure path): start `P2.3a` with smoke tests for extracted
  core helpers (path/validation and key deterministic transforms) to lock in current behavior before
  Phase 3 workflow hardening.
- Started and closed `P2.3a` by extending smoke coverage with CLI preflight file-validation tests
  (`tests/test_cli_main.py`) and lightweight transform smoke checks for TSA normalization/checkpoint
  path building (`tests/test_smoke.py`).
- Completed validation gate for this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest`,
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice (ASAP closure path): start `P2.3b` by adding deterministic,
  small-sample assertions for one or two extracted core helpers where behavior contracts are
  currently implicit (without expanding runtime-heavy legacy integration scope).
- Closed `P2.3b` with deterministic, small-sample CLI preflight assertions in
  `tests/test_cli_main.py`, including exact missing-required-file failure behavior and stable error
  classification under controlled repo layouts.
- Marked `P2.3` complete in `ROADMAP.md` now that both `P2.3a` and `P2.3b` are closed.
- Completed validation gate for this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest`,
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice (ASAP closure path): begin Phase 3 (`P3.1a`) by validating and
  tightening Sphinx config/package surface (theme/extensions/autosummary defaults) now that Phase 2
  modularization + minimal helper test coverage are complete.
- Closed `P3.1a` by upgrading `docs/conf.py` with explicit extension defaults
  (`sphinx.ext.autodoc`, `sphinx.ext.autosummary`, `sphinx.ext.napoleon`,
  `sphinx.ext.viewcode`) plus optional enablement for `nbsphinx` and
  `sphinx_rtd_theme` when installed in the environment.
- Added `autosummary_generate = True`, notebook-checkpoint exclusions, and resilient theme/static
  settings so docs builds stay warning-clean under `-W` even when optional packages are absent.
- Completed validation gate for this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest`,
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice (ASAP closure path): continue `P3.1` with `P3.1b` by adding
  `docs/reference/cli.rst` and wiring `docs/index.rst` to mirror current CLI help surface.
- Closed `P3.1b` by replacing the docs placeholder index with a real reference toctree and adding
  `docs/reference/cli.rst` containing the current `python -m femic --help` command/option surface
  (top-level plus `run`, `prep`, `vdyp`, `tsa`, and `tipsy` subcommand entries).
- Completed validation gate for this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest`,
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice (ASAP closure path): close `P3.1c` with a GitHub Pages docs build
  workflow that runs Sphinx in CI and publishes `_build/html`.
- Closed `P3.1c` by adding `.github/workflows/docs-pages.yml` with PR/push docs build, strict
  `sphinx-build -W` gating, artifact upload, and deploy-to-Pages on pushes to `main`.
- Marked `P3.1` complete in `ROADMAP.md` now that docs config, reference content, and Pages CI
  publishing are all in place.
- Completed validation gate for this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest`,
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice (ASAP closure path): start `P3.2a` by mapping current `femic` CLI
  commands/subcommands to a draft Nemora task taxonomy table in docs.
- Closed `P3.2a` by adding `docs/reference/nemora-task-map.rst` and wiring it into docs index
  to map current CLI entries (`run`, `prep run`, `vdyp run/report`, `tsa run`,
  `tipsy validate`) to draft Nemora task keys.
- Completed validation gate for this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest`,
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice (ASAP closure path): close `P3.2b` by inventorying extracted shared
  utilities and tagging top upstream candidates (diagnostics/logging/path/runtime helpers).
- Closed `P3.2b` by adding `docs/reference/nemora-upstream-candidates.rst` and wiring it into docs
  index with a prioritized inventory of extracted helper modules suitable for Nemora upstreaming.
- Marked `P3.2` complete in `ROADMAP.md` now that CLI taxonomy mapping and upstream-candidate
  inventory are both in place.
- Completed validation gate for this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest`,
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
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
- Completed validation gate for this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest`,
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice (ASAP closure path): close `P3.3b` by extending run manifest payload
  metadata with profile/config provenance and versioned output-root annotations.
- Closed `P3.3b` by extending run metadata through `PipelineRunConfig`/`LegacyExecutionPlan` with
  output-root + config provenance fields and surfacing them in manifest payload sections
  (`config_provenance`, `outputs`, and output-root option/path annotations).
- Added manifest/run-config coverage updates in `tests/test_pipeline_helpers.py` and
  `tests/test_legacy_manifest.py` plus SHA256 helper coverage for profile provenance digests.
- Marked `P3.3` complete in `ROADMAP.md` now that config selection/mode wiring and
  manifest/version metadata are both in place.
- Completed validation gate for this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest`,
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice (ASAP closure path): start `P3.4a` by auditing bootstrap/sample
  randomness seams and introducing explicit seed controls where stochastic behavior still exists.
- Closed `P3.4a` by adding explicit deterministic seed controls across VDYP sampling helpers:
  `run_vdyp_sampling(...)`, `run_vdyp_for_stratum(...)`, and bootstrap dispatch sequencing with
  per-stratum/SI derived seeds.
- Added `FEMIC_SAMPLING_SEED` env support for deterministic bootstrap/sample draws and coverage in
  `tests/test_vdyp_stage.py` for fixed-seed sampling stability and per-dispatch seed derivation.
- Completed validation gate for this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest`,
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice (ASAP closure path): close `P3.4b` by ensuring run manifests capture
  full runtime/tool version metadata consistently for config-driven and non-config runs.
- Closed `P3.4b` by extending manifest payload runtime metadata capture with an explicit
  `runtime_parameters` block and seed/config provenance fields (`FEMIC_SAMPLING_SEED`,
  `FEMIC_RUN_CONFIG_*`, output-root metadata).
- Added regression assertions in `tests/test_legacy_manifest.py` for runtime-parameter sections and
  seed/config provenance values.
- Marked `P3.4` complete in `ROADMAP.md` now that deterministic seed control and runtime
  parameter/version metadata capture are both implemented.
- Completed validation gate for this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest`,
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice (ASAP closure path): start `P3.5a` by updating README workflow docs
  to reflect run-config profiles, manifest provenance fields, and deterministic sampling controls.
- Closed `P3.5a` by updating `README.md` workflow documentation for config-driven runs
  (`--run-config`), deterministic sampling control (`FEMIC_SAMPLING_SEED`), and manifest metadata
  sections used for reproducibility/audit.
- Closed `P3.5b` by adding a concise end-to-end quickstart flow in `README.md` covering
  CLI help check, TIPSY config validation, single-TSA run, and VDYP diagnostics reporting.
- Marked `P3.5` complete in `ROADMAP.md` now that workflow handoff docs and quickstart are in
  place.
- Completed validation gate for this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest`,
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice (ASAP closure path): run a final roadmap consistency pass and
  prepare branch for merge/deployment handoff.
- Completed final roadmap consistency pass: all Phase 1/2/3 checklist items are now checked,
  including parent closeout for `P2.1` (its sub-items were already complete).
- Branch is ready for merge/deployment handoff.
- Added `planning/TSA29_dataset_compile_plan.md` with an explicit runbook for compiling TSA 29,
  including the required `config/tipsy/tsa29.yaml` gate, config-driven run steps, diagnostics, and
  completion criteria.
- Debugged TSA29 TIPSY config mismatch and rebuilt ruleset for functional AU coverage:
  `config/tipsy/tsa29.yaml` now uses a catch-all matching rule (`when: {}`) with
  `Density=1400` and `SPP_1=$leading_species_tipsy`.
- Added null defaults for optional TIPSY schema fields (`SPP_2..5`, `PCT_2..5`, `GW_*`,
  `GW_age_*`) so table projection to `data/tipsy_params_columns` succeeds for every AU.
- Re-ran the TSA29 TIPSY stage directly from cached outputs and regenerated
  `data/tipsy_params_tsa29.xlsx` and `data/02_input-tsa29.dat` (30 AU rows).
- Current blocker moved downstream to manual BatchTIPSY handoff (`04_output-tsa29.out`) before 01b
  and final bundle assembly can be validated.
- Added `femic tsa post-tipsy` command to run downstream stages only (01b + bundle assembly)
  after manual BatchTIPSY output is uploaded.
- Implemented `run_post_tipsy_bundle(...)` in `src/femic/workflows/legacy.py` to:
  load cached TSA prep/smoothed-curve artifacts, execute 01b per TSA, and rebuild
  `data/model_input_bundle/{au_table,curve_table,curve_points_table}.csv`.
- Added regression tests:
  `tests/test_workflows_post_tipsy.py` (workflow output assembly) and
  `tests/test_cli_main.py` (CLI command behavior and wiring).
- Updated user docs for the new downstream recovery command in `README.md` and
  `docs/reference/cli.rst`.
- Added `.gitignore` coverage for generated `vdyp_io` scratch files:
  `vdyp_err_*.err`, `vdyp_out_*.out`, `vdyp_ply_*.csv`, `vdyp_lyr_*.csv`, and `tmp*`.
  This removes hundreds of transient artifacts from normal `git status` output.
- Added `.gitignore` entries for volatile local runtime files under `vdyp_io/VDYP_CFG`
  (`VDYP7_BACK.ctl`, `VDYP7_VDYP.ctl`, `vdyp7.log`) and removed them from git tracking index so
  local model execution no longer dirties the branch on every run.
- Cleaned up 01b downstream runtime warnings:
  switched TIPSY output parsing to `sep="\\s+"` (pandas deprecation fix), pre-sorted VDYP
  stratum/SI index before per-AU lookups, and closed each Matplotlib figure after save to avoid
  open-figure buildup warnings during large TSA runs.
- Added manifest/audit logging for `femic tsa post-tipsy` runs via
  `run_post_tipsy_bundle_with_manifest(...)`, including run status, duration, runtime metadata, and
  output artifact existence checks.
- Extended `femic tsa post-tipsy` with `--run-id` and `--log-dir`, and now prints the generated
  manifest path (e.g., `vdyp_io/logs/run_manifest-<run_id>.json`).
- Added regression coverage for post-tipsy manifest emission and updated CLI/docs references.
- Tuned `config/tipsy/tsa29.yaml` from a single catch-all rule to ordered provisional
  BEC/species-group pathways (pine/fir/spruce/balsam) with explicit species mixes, density, DBH
  utility thresholds, and modest GW settings; retained a final catch-all for full AU coverage.
- Added TSA29-specific regression checks in `tests/test_tipsy_config.py` for representative
  MS-pine and IDF-fir rule matching behavior.
- Regenerated TSA29 TIPSY input artifacts (`data/tipsy_params_tsa29.xlsx`,
  `data/02_input-tsa29.dat`) from cached pipeline outputs using the tuned ruleset.
- Upgraded TSA29 parameterization from provisional tuning to TSR-anchored assumptions by extracting
  guidance from Williams Lake TSA data packages:
  `reference/29ts_dpkg_2024-2.pdf` (Section 8.5) and
  `reference/williams_lake_tsa_data_package-2.pdf` (Section 6.3 Tables 23–25).
- Reworked `config/tipsy/tsa29.yaml` rule assignments for pine/fir/spruce/balsam pathways with
  explicit treated-vs-untreated proportions, regen delays, species mixes, densities, and GW values
  tied to TSR assumptions; retained fallback coverage.
- Updated TSA29 expectations in `tests/test_tipsy_config.py` to match the new rules.
- Fixed a resumed-run bug in `src/femic/pipeline/vdyp_stage.py` where
  `geopandas.read_feather(...)` crashed on plain Feather caches lacking geo metadata by adding a
  pandas fallback for both polygon/layer cache loads.
- Forced TSA29 01a rerun and regenerated `data/02_input-tsa29.dat` under the new ruleset
  (same 30 AU rows, materially updated per-AU parameters).
- Added custom management-unit boundary support to run profiles:
  `selection.boundary_path`, `selection.boundary_layer`, `selection.boundary_code` now parse
  through `PipelineRunProfile`/`PipelineRunConfig` and are exported as `FEMIC_BOUNDARY_*`.
- Updated `00_data-prep.py` boundary ingestion to support custom geometry masks:
  in boundary mode FEMIC reads the provided layer, unions geometry, validates requested run code
  coverage, and clips VRI extraction to that geometry.
- Added K3Z case scaffolding:
  `config/run_profile.k3z.yaml`, `config/tipsy/tsak3z.yaml`, and
  `planning/K3Z_dataset_compile_plan.md`.
- Extended TIPSY config discovery and validation to support named case codes
  (for example `tsak3z.yaml`) in addition to numeric TSA files.
- Removed numeric-only TSA assumptions in AU/curve ID paths by adding deterministic named-code
  prefixing in `src/femic/pipeline/bundle.py` and `src/femic/pipeline/tsa.py`.
- Added/updated coverage in `tests/test_pipeline_helpers.py`, `tests/test_tipsy_config_cli.py`,
  and `tests/test_bundle.py` for profile boundary fields, named TIPSY configs, and named-case
  bundle ID behavior.
- Executed K3Z smoke run (`--debug-rows 20`) successfully through full legacy workflow with
  missing-BatchTIPSY fallback, producing manifest
  `vdyp_io/logs/run_manifest-k3z_smoke5_20260304_221317.json` and K3Z step-1a artifacts
  (`data/02_input-tsak3z.dat`, `data/tipsy_params_tsak3z.xlsx`).
- Hardened config-driven TIPSY treated-row mix normalization in
  `src/femic/pipeline/tipsy_config.py`:
  `SX -> SW` normalization across species slots, treated broadleaf removal with share
  reallocation, dominant-species-first slot ordering, and exact integer `%` rounding to 100.
- Added regression tests in `tests/test_tipsy_config.py` for normalized mix behavior and TSA29
  expectations (no treated `AT`/`SX` in `f` rows, dominant species in `SPP_1`, sum of
  `PCT_1..PCT_5 == 100`).
- Completed validation gate for this slice:
  `.venv/bin/ruff format src tests`, `.venv/bin/ruff check src tests`,
  `.venv/bin/mypy src`, `.venv/bin/pytest`, `.venv/bin/pre-commit run --all-files`.
- Installed `pandas-stubs` into `.venv` to satisfy strict `mypy src` import-typing requirements.
- TSA29 full rerun remains pending due run-path stall/noise during heavy `FEMIC_NO_CACHE=1`
  data-prep stage; immediate next action is deterministic regeneration of step-1a outputs and
  BatchTIPSY revalidation.
- Added config-driven SI offset support for TIPSY rule assignments in
  `src/femic/pipeline/tipsy_config.py`:
  per-side `SI_offset`/`si_offset` can be declared in config defaults or per-rule assignments,
  and is applied as an additive adjustment to computed VDYP SI before row export.
- Updated `config/tipsy/tsa29.yaml` to include `defaults.f.SI_offset: 2.0`, enabling a
  managed-side +2 SI bump directly from config (no manual `.dat` edits required).
- Added regression coverage in `tests/test_tipsy_config.py` for side-specific SI offset
  behavior and updated TSA29 expected SI values under the new +2 managed offset.
- Regenerated TSA29 step-1a artifacts from cached TSA29 prep data with the new config:
  `data/tipsy_params_tsa29.xlsx` and `data/02_input-tsa29.dat`.
- Completed validation gate for this slice:
  `.venv/bin/ruff format src tests`, `.venv/bin/ruff check src tests`,
  `.venv/bin/mypy src`, `.venv/bin/pytest`, `.venv/bin/pre-commit run --all-files`.
- Extended TIPSY config SI tuning to support linear transforms in
  `src/femic/pipeline/tipsy_config.py` via `SI_c1` and `SI_c2` (with lowercase aliases).
  Final SI is now computed per side as:
  `SI_final = SI_c1 * SI_baseline + SI_c2` (plus legacy additive `SI_offset` if present).
- Updated TSA29 config to linear-form managed SI bump in `config/tipsy/tsa29.yaml`:
  `defaults.f.SI_c1: 1.0`, `defaults.f.SI_c2: 2.0` (equivalent to previous fixed +2 offset).
- Added regression coverage in `tests/test_tipsy_config.py` for linear SI transform behavior.
- Updated TIPSY config docs/templates with SI transform guidance:
  `config/tipsy/README.md`, `config/tipsy/template.tsa.yaml`.
- Revalidated and regenerated TSA29 step-1a outputs under linear-form config:
  `data/tipsy_params_tsa29.xlsx` and `data/02_input-tsa29.dat` (matches the prior manual +2
  scenario).
- Completed validation gate for this slice:
  `.venv/bin/ruff format src tests`, `.venv/bin/ruff check src tests`,
  `.venv/bin/mypy src`, `.venv/bin/pytest`, `.venv/bin/pre-commit run --all-files`,
  `.venv/bin/sphinx-build -b html docs _build/html -W`.
- Added TSA29 VDYP override in `src/femic/pipeline/vdyp_overrides.py` for
  `("SBPS_PL", "L"): {"skip1": 50}` to correct pathological unmanaged curve behavior in AU 21005.
- Added default VDYP fit diagnostic plot output in `src/femic/pipeline/vdyp_stage.py` during
  smoothing runs:
  `plots/vdyp_fitdiag_tsaXX-<stratumi>-<stratum>-<si>.png` now overlays observed 5-year binned
  median/IQR with the fitted best-fit curve for visual QA.
- Re-ran TSA29 01a/01b and post-tipsy stages; AU 21005 unmanaged curve changed from a pathological
  early spike (max 943.91 at age 19) to a coherent trajectory (max 96.29 at age 223).
- Generated targeted AU21005 diagnostics:
  `plots/diag_au21005_fit_check.png` and companion CSVs for observed bins/current/candidate curve
  comparison.
- Completed validation gate for this slice:
  `.venv/bin/ruff format src tests`, `.venv/bin/ruff check src tests`,
  `.venv/bin/mypy src`, `.venv/bin/pytest`, `.venv/bin/pre-commit run --all-files`.
- Expanded VDYP fit-comparison diagnostics:
  `src/femic/pipeline/vdyp_curves.py` now supports right-tail sigma asymmetry and optional
  right-tail linear blend controls; `src/femic/pipeline/vdyp_stage.py` now computes and overlays
  `current`, `sigma_asym`, `tail_blend`, and conditionally validated `auto_skip` candidates on
  each `plots/vdyp_fitdiag_tsaXX-*.png`.
- Added heuristic auto left-tail anomaly handling in smoothing runs:
  infer a suggested `skip1` from early-age overshoot, rerun candidate fit, and only surface it
  when strict quality gates improve baseline (`rmse`, `tail_rmse`, `early_overshoot`).
- Ran TSA29 targeted smoothing directly from cached TSA artifacts and regenerated
  `data/vdyp_curves_smooth-tsa29.feather` plus 30 fitdiag PNGs with multi-flavour overlays.
- Added quantitative comparison artifact
  `plots/vdyp_fitdiag_tsa29_metrics_compare.csv` (30 stratum+SI rows):
  best RMSE counts = tail blend 18, sigma asymmetry 9, current 3;
  best tail-RMSE counts = sigma asymmetry 18, tail blend 9, current 3.
  Auto-skip was suggested for 18 curves but validated for 0 under current acceptance criteria.
- Refined VDYP improved-fit comparison workflow to drop the sigma-asymmetry candidate from
  default diagnostics and focus on current-vs-tail-blend evaluation.
- Reworked right-tail blending in `src/femic/pipeline/vdyp_curves.py`:
  the tail logic now auto-detects the maximal rightmost near-linear binned segment
  (`R²` + normalized-RMSE gates), fits the main NLLS body on the left as before, and blends into
  the detected linear tail. When no acceptable linear segment exists, tail override is skipped.
- Added configurable linear-tail detection controls:
  `tail_linear_min_points`, `tail_linear_min_r2`, `tail_linear_max_nrmse`.
- Updated fitdiag overlays in `src/femic/pipeline/vdyp_stage.py` to display only:
  `current`, `tail_blend`, and validated `auto_skip`.
- Regenerated TSA29 curve-smoothing artifacts and diagnostics from cached TSA inputs:
  `data/vdyp_curves_smooth-tsa29.feather` and 30 refreshed
  `plots/vdyp_fitdiag_tsa29-*.png` files.
- Added tail-focused summary artifact
  `plots/vdyp_fitdiag_tsa29_metrics_tail_only.csv`:
  tail blend improved overall RMSE on 17/30 curves and tail RMSE on 17/30 curves
  (auto-skip still suggested in 18 curves under current heuristic).
- Diagnosed residual tail-blend regressions: detector could still pick early-age
  pseudo-linear segments when no acceptable late-age segment existed, leading to severe errors.
- Updated `src/femic/pipeline/vdyp_curves.py` linear-tail selection to require
  preferred-age candidates (`tail_linear_prefer_min_age`, default 200) and return no blend when
  none exist (instead of dropping to non-preferred segments).
- Added tests in `tests/test_vdyp_curves.py` for:
  1) no-blend behavior when no linear/preferred segment is available, and
  2) preference for late linear segments when present.
- Re-ran TSA29 diagnostic smoothing with the revised heuristic and regenerated
  `plots/vdyp_fitdiag_tsa29-*.png` plus refreshed
  `plots/vdyp_fitdiag_tsa29_metrics_tail_only.csv`.
- Post-fix metrics: catastrophic tail-blend outliers were removed; worst RMSE regression dropped
  to ~0.045 (from prior multi-unit failures), while preserving blend improvements where suitable
  late-age linear tails exist.
- Ran a relaxed-linearity tuning pass to address missed long near-linear late tails:
  updated stage-level candidate settings to
  `tail_linear_min_r2=0.82`, `tail_linear_max_nrmse=0.12`,
  `tail_linear_prefer_min_age=190.0`.
- Regenerated TSA29 diagnostics (`plots/vdyp_fitdiag_tsa29-*.png`) and refreshed
  `plots/vdyp_fitdiag_tsa29_metrics_tail_only.csv`.
- Relaxed thresholds increased detected blended tails from 22/30 to 26/30 curves.
  Resulting quality tradeoff remained bounded (no catastrophic regressions), with
  `tail_better_rmse=15/30`, `tail_better_tail_rmse=15/30`, and worst observed
  `?RMSE ~ +0.67` (`IDF_PL-H`).
- Added detailed implementation summary document:
  `planning/VDYP_curve_fit_enhancements_2026-03-05.md`, including history, current controls,
  observed metrics, and explicit follow-up note to keep tuning tail-fit hyperparameters later.
- Updated VDYP fit diagnostics to include raw per-sample VDYP trajectories as faint grey lines
  (low-alpha) behind binned summaries/fitted curves in
  `src/femic/pipeline/vdyp_stage.py`, for teaching/demo visualization of raw -> smoothed workflow.
- Re-ran full K3Z case with updated curve-fit/plotting stack:
  `--run-id k3z_curvefit_enh_20260305`; run completed and wrote manifest
  `vdyp_io/logs/run_manifest-k3z_curvefit_enh_20260305.json`.
- Generated updated K3Z fitdiag outputs:
  `plots/vdyp_fitdiag_tsak3z-*.png` (9 plots for available VDYP strata/SI combinations).
- Ran K3Z end-to-end with user-provided BatchTIPSY output by mapping
  `data/02_output-tsak3z.out` to the runtime-expected `data/04_output-tsak3z.out`
  and executing:
  `python -m femic run --run-config config/run_profile.k3z.yaml -v --resume --run-id k3z_posttipsy_20260306_062442`.
- Run finished `status=ok` (manifest:
  `vdyp_io/logs/run_manifest-k3z_posttipsy_20260306_062442.json`) and regenerated current K3Z
  post-TIPSY outputs, including `plots/strata-tsak3z.png`,
  `plots/tipsy_vdyp_tsak3z-*.png`, `data/tipsy_params_tsak3z.xlsx`,
  and `data/tipsy_curves_tsak3z.csv`.
- Fixed K3Z strata diagnostics bug where `build_strata_summary(...)` could return NaN
  abundance/coverage rows after `min_standcount` filtering by:
  1) keeping filtered frames as `.copy()` and
  2) falling back to unfiltered top strata when small custom-boundary runs would
     otherwise filter out all strata.
- Improved strata plotting robustness in `src/femic/pipeline/plots.py`:
  abundance ordering now falls back from `totalarea_p` to `coverage`,
  SI axes auto-expand to observed min/max values, and sparse-point strip overlays are
  drawn on top of violin plots for low-sample strata.
- Added `tipsy_vdyp_ylim_for_tsa(...)` and wired `01b_run-tsa.py` to use it;
  K3Z TIPSY-vs-VDYP comparison plots now use a `0..1500` y-axis range.
- Added regression tests in `tests/test_pipeline_helpers.py` covering:
  small-boundary standcount fallback behavior, K3Z y-limit helper behavior,
  and stripplot invocation in strata distribution rendering.
- Re-ran K3Z end-to-end with fixes:
  `python -m femic run --run-config config/run_profile.k3z.yaml -v --run-id k3z_plotfix_20260306_063833`;
  run completed `status=ok` (manifest:
  `vdyp_io/logs/run_manifest-k3z_plotfix_20260306_063833.json`) with corrected
  strata diagnostics (`coverage 1.0`) and refreshed K3Z outputs.
- Scoped K3Z strata selection to top 4 strata by area by adding
  `TARGET_NSTRATA_BY_TSA["k3z"] = 4` in `src/femic/pipeline/tsa.py`.
- Updated K3Z downstream unmanaged-curve selection so comparison plots use
  tail-blend curves when available:
  `src/femic/pipeline/vdyp_stage.py::execute_curve_smoothing_runs(...)` now writes
  tail-blend output for `tsa == "k3z"` into `vdyp_curves_smooth-tsak3z.feather`
  (fitdiag visualization still shows current + candidate overlays).
- Added tests:
  `tests/test_pipeline_helpers.py` asserts `target_nstrata_for("k3z") == 4`;
  `tests/test_vdyp_stage.py` validates K3Z tail-blend output preference.
- Deleted stale K3Z plot artifacts (`plots/*tsak3z*`) and recompiled K3Z from scratch:
  `python -m femic run --run-config config/run_profile.k3z.yaml -v --run-id k3z_n4_tailblend_20260306_064902`.
  Run completed `status=ok` (manifest:
  `vdyp_io/logs/run_manifest-k3z_n4_tailblend_20260306_064902.json`) with
  step-1a diagnostics now showing `count 4` and `coverage 0.9882`.
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
  `vdyp_io/logs/run_manifest-k3z_siwidth_verify_20260306_070055.json`) and emitted
  an 8-row K3Z TIPSY input table where `CWH_CW` is correctly split into `L/H` only.
- Updated K3Z comparison plot y-range:
  `src/femic/pipeline/plots.py::tipsy_vdyp_ylim_for_tsa(...)` now returns `(0.0, 2000.0)`
  for `k3z` (previously `(0.0, 1500.0)`), and test expectation was updated in
  `tests/test_pipeline_helpers.py`.
- Fixed fitdiag regeneration behavior in non-resume runs:
  `01a_run-tsa.py` now rebuilds smoothed curves whenever `resume_effective=False`
  instead of only when the smooth-feather cache is missing.
- Hardened fitdiag emission in `src/femic/pipeline/vdyp_stage.py`:
  diagnostic PNGs now emit even when binned observations are unavailable (observed overlays
  are conditional); this prevents silent drop-out of fitdiag files.
- Fixed no-cache VDYP bootstrap reuse:
  `00_data-prep.py` now sets `force_run_vdyp = 1` whenever `_femic_no_cache` is true,
  so stale `data/vdyp_results-tsa*.pkl` cannot be reused during no-cache runs.
- Fixed adaptive-SI bootstrap dispatch bug:
  `src/femic/pipeline/vdyp_stage.py::execute_bootstrap_vdyp_runs(...)` now skips missing/empty
  SI payloads and logs a `status=skipped` event (`missing_or_empty_si_sample`) instead of
  raising `KeyError` when strata have fewer than three SI bins.
- Re-ran full K3Z no-cache pipeline with forced fresh VDYP:
  `FEMIC_NO_CACHE=1 PYTHONPATH=src .venv/bin/python -m femic run --run-config config/run_profile.k3z.yaml -v --run-id k3z_forcevdyp_fix_20260306_072037`.
  Run completed `status=ok` (manifest:
  `vdyp_io/logs/run_manifest-k3z_forcevdyp_fix_20260306_072037.json`) and regenerated
  fresh K3Z artifacts including:
  `data/vdyp_results-tsak3z.pkl` (updated timestamp),
  8 fitdiag plots (`plots/vdyp_fitdiag_tsak3z-*.png`), and
  8 comparison plots (`plots/tipsy_vdyp_tsak3z-*.png`).
- Extracted K3Z stocking parameter guidance from
  `data/bc/cfa/k3z/NICF-LP-Forest-Stewardship-Plan-Appendices-2020.pdf`
  (Appendix B, pages 4-6) and converted `config/tipsy/tsak3z.yaml` from
  placeholder defaults to FSP-informed CWH pathway rules.
- Replaced K3Z TIPSY assumptions with mixed-species, 900 sph pathways keyed by
  leading species group (`CW/YC`, `HW/HM`, `FD/FDC`, `SS/SX`) plus an FSP-style
  fallback rule; all compositions now sum to 100 and avoid single-species
  placeholder stocking.
- Executed refreshed K3Z run with new TIPSY rules:
  `PYTHONPATH=src .venv/bin/python -m femic run --run-config config/run_profile.k3z.yaml -v --run-id k3z_fsp_rules_20260306_073524`.
  Run completed successfully (`status=ok`) with manifest
  `vdyp_io/logs/run_manifest-k3z_fsp_rules_20260306_073524.json`.
- Verified regenerated `data/02_input-tsak3z.dat` now carries the new rule
  outputs (8 AUs, `Density=900`, `Regen_Delay=2`, mixed species such as
  `CW60/HW25/YC15`, `HW70/CW20/FD10`, `FD60/HW25/CW15`).
- Added `planning/CFAK3Z_dataset_compile_plan.md` by cloning the TSA29 planning
  structure and adapting it to K3Z-specific compile constraints, including fixed
  BatchTIPSY field-map handling and small-area stratification caveats.
- Recorded next K3Z refinement experiments in the new plan:
  BEC subzone/variant/phase stratification and top-N leading-species combination
  stratification (N=2 first, then N=3 trial).
- Verified local VRI schema support for these experiments from
  `data/bc/vri/2019/VEG_COMP_LYR_R1_POLY.gdb`:
  `BEC_ZONE_CODE`, `BEC_SUBZONE`, `BEC_VARIANT`, `BEC_PHASE`,
  `SITE_INDEX`, `EST_SITE_INDEX*`, `SPECIES_CD_1..6`, `SPECIES_PCT_1..6`.
- Verified `data/bc/vri/VEG_COMP_LYR_R1_POLY_2024.gdb.zip` is currently corrupt/
  incomplete (`End-of-central-directory signature not found`) and cannot be
  unzipped yet.
- Implemented configurable stratum-key controls in the run-profile pipeline and
  wired them end-to-end into legacy 00-data-prep execution:
  - `selection.stratification.bec_grouping` (`zone|subzone|variant|phase`)
  - `selection.stratification.species_combo_count` (top-N by `SPECIES_PCT_1..6`)
  - `selection.stratification.include_tm_species2_for_single`
  These now flow through `src/femic/pipeline/io.py` -> CLI effective options ->
  legacy env (`FEMIC_STRAT_*`) -> `00_data-prep.py`.
- Refactored `src/femic/pipeline/vri.py` stratum builders to support:
  - BEC grouping levels beyond zone (`subzone`, `variant`, `phase`)
  - Species-combination keys using ranked top-N species shares
  while preserving legacy default behavior for existing TSA runs.
- Updated K3Z profile defaults in `config/run_profile.k3z.yaml` to start from
  finer stratification (`bec_grouping: subzone`, `species_combo_count: 2`) and
  documented new options in `config/run_profile.example.yaml`.
- Updated K3Z planning doc (`planning/CFAK3Z_dataset_compile_plan.md`) with the
  new stratification controls and expected console confirmation output.
- Added/updated regression coverage for new stratification plumbing and behavior:
  `tests/test_vri.py` and `tests/test_pipeline_helpers.py`.
- Validation run status:
  - `.venv/bin/ruff check src tests` passed
  - `.venv/bin/mypy src` passed
  - `.venv/bin/pytest` passed (`312 passed`)
  - `.venv/bin/pre-commit run --all-files` passed
- Switched legacy VRI source auto-resolution to prefer 2024 VRI datasets when available,
  with 2019 fallback preserved for compatibility:
  `bc/vri/2024/VEG_COMP_LYR_R1_POLY_2024.gdb` before
  `bc/vri/2019/VEG_COMP_LYR_R1_POLY.gdb`.
  Implemented in `src/femic/pipeline/io.py::resolve_legacy_external_data_paths(...)`.
- Added startup visibility in `00_data-prep.py` to print the resolved VRI path and TSA
  boundaries path at run start, so active data-source selection is explicit.
- Added regression coverage:
  `tests/test_pipeline_helpers.py::test_resolve_legacy_external_data_paths_prefers_2024_vri_when_available`.
- Validation run status:
  - `.venv/bin/ruff format src tests 00_data-prep.py` passed
  - `.venv/bin/ruff check src tests` passed
  - `.venv/bin/mypy src` passed
  - `.venv/bin/pytest` passed (`313 passed`)
  - `.venv/bin/pre-commit run --all-files` passed
- Extended external source resolution so VRI and VDYP input layers are selected together
  from the same preferred vintage (2024 first, then 2019 fallback):
  - VRI candidates: `bc/vri/2024/VEG_COMP_LYR_R1_POLY_2024.gdb`,
    `bc/vri/2019/VEG_COMP_LYR_R1_POLY.gdb`
  - VDYP input candidates:
    `bc/vri/2024/VEG_COMP_VDYP7_INPUT_POLY_AND_LAYER_2024.gdb`,
    `bc/vri/2019/VEG_COMP_VDYP7_INPUT_POLY_AND_LAYER_2019.gdb`,
    `VEG_COMP_VDYP7_INPUT_POLY_AND_LAYER_2019.gdb`
  Implemented in `src/femic/pipeline/io.py::resolve_legacy_external_data_paths(...)`.
- Updated `00_data-prep.py` to consume the resolved external VDYP input path and print all
  active source paths at runtime:
  - `using VRI source: ...`
  - `using TSA boundaries source: ...`
  - `using VDYP input source: ...`
- Added regression assertions in `tests/test_pipeline_helpers.py` for the new
  `vdyp_input_pandl_path` resolution behavior (including 2024-preferred selection).
- Added a non-fatal guard in `00_data-prep.py` for empty AU-table outcomes after 01b/bundle
  assembly so no-cache exploratory runs can complete and preserve diagnostics even when
  no TIPSY-compatible AU mapping exists.
- Executed fresh 2024 K3Z runs (`k3z_vri2024_refresh2_20260307`,
  `k3z_vri2024_zone1_fixvdyp_20260307`) and confirmed 2024 sources were selected; however,
  VDYP run logs show `empty_output` across bootstrap events, yielding empty smoothed curves
  and an empty `data/02_input-tsak3z.dat` (next debugging target: 2024 VDYP input prep/schema alignment).
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
- Consulted local VRI metadata PDFs in `docs/reference` while debugging
  (`vegcomp_poly_rank1_data_dictionaryv5_2019*.pdf`,
  `vegcomp_toc_data_dictionaryv5_2019.pdf`); practical takeaway for this run path remains:
  `MAP_ID` is the reliable bridge field across 2024 VRI rank1 samples and 2024 VDYP input layers
  when `FEATURE_ID` domains diverge.
- Added profile/env support for cumulative top-strata selection by area coverage:
  new config key `selection.stratification.top_area_coverage` (wired through CLI/profile/env as
  `FEMIC_STRAT_TOP_AREA_COVERAGE`) and 01a runtime (`target_area_coverage`) now drive
  `build_strata_summary(..., target_coverage=...)`.
- Updated K3Z profile to `top_area_coverage: 0.95` in
  `config/run_profile.k3z.yaml`.
- Re-ran K3Z no-cache with 95% top-area cutoff:
  `FEMIC_NO_CACHE=1 PYTHONPATH=src .venv/bin/python -u -m femic run --run-config config/run_profile.k3z.yaml -v --run-id k3z_cov95_20260307`.
  01a now selects `13` strata at cumulative coverage `0.95565930139286`.
- BEC hierarchy check for selected K3Z strata:
  all selected strata remain identical at zone+subzone (`CWHvm`), and also at
  zone+subzone+variant (`CWHvm1`) with phase null throughout; deeper BEC hierarchy
  does not add partition signal for this case.
- SI split diagnostics on the 95% run show frequent sparse SI bins in tail strata
  (many `L/M/H` bins with 0-2 stands), with corresponding VDYP `skipped`/`empty_output`
  events; this supports collapsing SI splits for sparse K3Z strata in the next tuning step.
- Implemented requested K3Z stratification reset: lowered `top_area_coverage` to `0.80`, removed adaptive SI-width split overrides, and restored fixed SI quantile bins (`L=5..35`, `M=35..65`, `H=65..95`).
- Added post-fit adjacent SI-curve merge behavior in TIPSY AU assembly (`src/femic/pipeline/tipsy.py`), including per-stratum merge diagnostics (`si-groups`) and shared-AU mapping for merged SI levels.
- Fixed merged-AU downstream bundle failure by making `assign_curve_ids_from_au_table(...)` robust to duplicate `au_id` rows (select first non-null managed/unmanaged curve IDs before managed/unmanaged assignment).
- Hardened stand export for merged AUs by resolving duplicate-`au_id` lookups in `prepare_stands_export_frame(...)` to a stable `canfi_species` scalar.
- Added regression tests:
  - `tests/test_bundle.py::test_assign_curve_ids_from_au_table_handles_duplicate_au_rows`
  - `tests/test_stands.py::test_prepare_stands_export_frame_handles_duplicate_au_rows`
- Re-ran K3Z end-to-end with no-cache and requested settings:
  `FEMIC_NO_CACHE=1 PYTHONPATH=src .venv/bin/python -u -m femic run --run-config config/run_profile.k3z.yaml -v --run-id k3z_cov80_fixedsi_merge_debug2_20260307`.
  Run completed successfully (`status=ok`, manifest: `vdyp_io/logs/run_manifest-k3z_cov80_fixedsi_merge_debug2_20260307.json`).
- Implemented pre-fit SI-bin stabilization in `src/femic/pipeline/vdyp_stage.py::fit_stratum_curves(...)`:
  added `min_stands_per_si_bin` (default `25`) and automatic adjacent-bin collapse before NLLS;
  collapse actions are logged per stratum.
- Updated SI-level AU merge behavior in `src/femic/pipeline/tipsy.py::build_tipsy_params_for_tsa(...)`:
  merges now require both bounded max-relative-gap and bounded age-window NRMSE
  (plus existing common-age checks), with per-pair `gap/rmse/nrmse` diagnostics.
- Added deterministic weak-species override hooks for config-driven TIPSY:
  `species_code_overrides` and `siteprod_si_fallback_by_species` are now supported in
  `src/femic/pipeline/tipsy_config.py` and used during candidate evaluation/assignment.
- Updated `config/tipsy/tsa29.yaml` and `config/tipsy/tsak3z.yaml` with explicit
  `species_code_overrides` (`SX->SW`, `DR->FD`) plus `siteprod_si_fallback_by_species`.
- Added requested L/M/H comparison diagnostics: `execute_curve_smoothing_runs(...)` now emits
  per-stratum overlays (`plots/vdyp_lmh_tsa*-*.png`) showing L/M/H best-fit VDYP curves on one plot.
- Wired site productivity source resolution to prefer the fresh dataset path
  `data/bc/siteprod/Site_Prod_BC.gdb` (with fallback), and surfaced the active siteprod path
  in startup logging.
- Re-ran full no-cache K3Z compile against 2024 VRI/VDYP + fresh siteprod source:
  `FEMIC_NO_CACHE=1 PYTHONPATH=src .venv/bin/python -u -m femic run --run-config config/run_profile.k3z.yaml -v --run-id k3z_siteprod_refresh_20260307`
  completed `status=ok` and regenerated current K3Z fitdiag/TIPSY comparison artifacts.
- Isolated the K3Z two-pass SI rebin failure to pipeline regressions (not a BC schema change):
  stale TSA-specific VDYP feathers were being reused under no-cache runs and output remap
  did not robustly handle table-number keyed VDYP outputs with extra tables.
- Fixed `load_vdyp_input_tables(...)` precedence to prefer explicit `source_feature_ids`
  when both feature IDs and map IDs are provided, with map-id fallback only if feature-id
  lookup returns empty.
- Updated 01a VDYP-table load behavior to force source reads whenever
  `runtime_config.force_run_vdyp` is true, preventing stale TSA-scoped VDYP caches from
  contaminating no-cache debug runs.
- Hardened `run_vdyp_for_stratum(...)` remap logic to use VDYP output table attrs
  (`vdyp_map_name` + `vdyp_polygon_id`) back to resolved feature IDs before key/order fallbacks.
- Updated `import_vdyp_tables(...)` to key outputs by `Table Number` (preserving map/polygon attrs)
  to avoid polygon-key collisions/overwrites in mixed-map batches.
- Added regression tests for:
  - feature-id loader precedence when both feature IDs and map IDs are supplied
  - table-number output remap via VDYP table attrs
  - map-id and map+polygon remap paths
- Revalidated no-cache K3Z two-pass run:
  `FEMIC_NO_CACHE=1 PYTHONPATH=src .venv/bin/python -u -m femic run --run-config config/run_profile.k3z.yaml -v --run-id k3z_twopass_fix5_20260307`
  now reports `two-pass SI rebin: mapped VDYP SI for 194/251 rows` and completes downstream
  TIPSY/bundle stages (previously `0/251` with empty downstream outputs).
- 2026-03-08: Added configurable SI-bin collapse threshold for 01a fitting (`modes.vdyp_min_stands_per_si_bin` -> `FEMIC_VDYP_MIN_STANDS_PER_SI_BIN` -> runtime `min_stands_per_si_bin`).
- 2026-03-08: Updated `config/run_profile.k3z.yaml` for requested test settings (`top_area_coverage: 0.90`, `vdyp_min_stands_per_si_bin: 10`).
- 2026-03-08: Re-ran no-cache K3Z with requested settings; 01a selected 9 strata at 90.655% coverage, AU bundle contains 27 AUs, and SS remains represented (`CWHvm_HW+SS`).
- 2026-03-08: Ran comparison compile with `species_combo_count: 3`; 01a selected 25 strata at 90.153% coverage and downstream AU bundle expanded to 66 AUs (22 strata x 3 SI levels), indicating substantially higher fragmentation than combo=2.
- 2026-03-08: Added run-profile docs for `vdyp_min_stands_per_si_bin` in `config/run_profile.example.yaml` and `docs/reference/run-config.rst`.
- 2026-03-08: Added species-proportion curve export to post-TIPSY bundle assembly. For each AU, bundle `curve_table.csv` and `curve_points_table.csv` now include `unmanaged_species_prop_<SPP>` and `managed_species_prop_<SPP>` curves (single-point `x=1`, `y=proportion`) when inventory species-universe scanning is available.
- 2026-03-08: Implemented TSA-scoped inventory pre-scan of top-6 VRI species from `data/ria_vri_vclr1p_checkpoint8.feather` (`SPECIES_CD_1..6` + positive `SPECIES_PCT_*`) so each AU receives a full, consistent species curve set (zero for absent species).
- 2026-03-08: Wired unmanaged species proportions from VDYP fit payload species shares and managed species proportions from `tipsy_sppcomp_tsa<tsa>.csv`.
- 2026-03-08: Added regression test `tests/test_bundle.py::test_build_bundle_tables_from_curves_adds_species_proportion_curves` and updated README notes for the new bundle behavior.
- 2026-03-08: Hardened TIPSY DAT export to a truly fixed schema in `src/femic/pipeline/tipsy.py`.
  - Switched DAT writing to explicit start-position rendering (header + row), instead of `pandas.to_string` heuristics.
  - Enforced full 32-column schema on every DAT row, including blank columns, so sparse K3Z rows do not collapse/shift downstream fields.
  - Kept line lengths fixed and removed variable trailing-trim behavior.
  - Updated/added tests in `tests/test_tipsy.py` for stable header-start expectations.
- 2026-03-08: Regenerated `data/02_input-tsak3z.dat` from `data/tipsy_params_tsak3z.xlsx` with the fixed writer. Verified row-field slices preserve intended values (for example `PCT_1=70`, `SI=23.9`, `SPP_2=CW`, `PCT_2=20`, `SPP_3=FD`, `PCT_3=10`) instead of prior concatenation.
- 2026-03-08: Rebased TIPSY DAT writer field ranges to the exact BatchTIPSY GUI indices from user screenshots (instead of inferred spacing), eliminating merged-token failures like `900P`/`0.95I`.
- 2026-03-08: Added anti-regression hardening for TIPSY DAT generation.
  - Canonicalized all DAT field positions as one 1-based BatchTIPSY schema constant copied from the GUI index spec.
  - Added strict row validation (`_validate_tipsy_dat_row`) to fail on width overflow or slice mismatch before file write.
  - Added regression test `test_write_tipsy_input_exports_fails_fast_on_width_overflow`.
  - Regenerated `data/02_input-tsak3z.dat` via the hardened writer.
- 2026-03-08: Cleared stale plot artifacts (`plots/*`) and executed a full fresh no-cache K3Z run from top of pipeline with current `config/run_profile.k3z.yaml` parameters (`run_id=k3z_fresh_20260308_032428`).
- 2026-03-08: Run completed successfully and regenerated 52 K3Z plot artifacts (strata, VDYP fitdiag, L/M/H overlays, and TIPSY-vs-VDYP AU plots), with manifest at `vdyp_io/logs/run_manifest-k3z_fresh_20260308_032428.json`.
- 2026-03-08: Implemented synthetic managed-yield fallback mode for unstable TIPSY cases.
  - New run-profile modes: `managed_curve_mode` (`tipsy|vdyp_transform`), `managed_curve_x_scale`, `managed_curve_y_scale`, `managed_curve_truncate_at_culm`, `managed_curve_max_age`.
  - New helper module `src/femic/pipeline/managed_curves.py` for AU-wise VDYP->managed curve synthesis.
  - Updated `01b_run-tsa.py` to apply `vdyp_transform` mode and overwrite managed yield outputs (`tipsy_curves_tsa*.csv`) with transformed curves.
  - Added regression coverage in `tests/test_managed_curves.py` and run-profile parsing/env propagation coverage in `tests/test_pipeline_helpers.py`.
  - Updated `config/run_profile.k3z.yaml` to use `vdyp_transform` with `x=0.8`, `y=1.2`, truncated post-culmination tail.
- 2026-03-08: Cleared old plot artifacts and ran a full no-cache K3Z compile with synthetic managed curves (`run_id=k3z_vdyp_managed_20260308_1`), regenerating fresh K3Z strata/fitdiag/LMH/TIPSY-vs-VDYP plots and model-input bundle tables.
- 2026-03-08: Extended `ROADMAP.md` with a new `Phase 4` for `femic.fmg` delivery, including tracked subtasks for proprietary Patchworks guide handling, Python 3 port of legacy fmg core, Patchworks ForestModel XML generation, fragments shapefile generation from BC VRI, Woodstock carry-over, and end-to-end validation.

## 2026-03-08 - Phase 4 kickoff: Patchworks export path
- Added new module `src/femic/fmg/patchworks.py` plus `src/femic/fmg/__init__.py` with:
  `build_forestmodel_xml_tree(...)`, `write_forestmodel_xml(...)`,
  `build_fragments_geodataframe(...)`, `write_fragments_shapefile(...)`, and
  `export_patchworks_package(...)`.
- Added `femic export patchworks` CLI in `src/femic/cli/main.py` for TSA-scoped export of
  `forestmodel.xml` and `fragments.shp` from existing FEMIC bundle/checkpoint outputs.
- Fixed checkpoint geometry handling for export: fragments builder now decodes WKB payloads
  (bytes/memoryview/hex string) before GeoDataFrame construction, resolving smoke-run
  failures against `data/ria_vri_vclr1p_checkpoint7.feather`.
- Added regression tests in `tests/test_fmg_patchworks.py` and `tests/test_cli_main.py` for:
  XML/treatment/curve references, fragments field content, CLI wiring, and WKB geometry decode.
- Updated docs for the new workflow:
  `README.md` (Patchworks export quickstart) and `docs/reference/cli.rst` (command reference).
- Verified with full quality gates:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest`,
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W` all passed.
- Verified runtime smoke export:
  `PYTHONPATH=src .venv/bin/python -m femic export patchworks --tsa k3z --output-dir output/patchworks_k3z_smoke`
  completed successfully (`au=14`, `fragments=218`, `curves=54`).

## 2026-03-08 - Patchworks export validation hardening (P4.4b, P4.6a)
- Added strict export validators in `src/femic/fmg/patchworks.py`:
  - `validate_forestmodel_xml_tree(...)` for required root attributes, `<input>/<output>`,
    required `<define field=...>` entries, curve/idref integrity, and CC treatment presence.
  - `validate_fragments_geodataframe(...)` for required columns, CRS presence, geometry sanity,
    numeric constraints, unique block IDs, positive area, and valid `IFM` values.
- Wired both validators into `export_patchworks_package(...)` so malformed exports fail before write.
- Expanded regression tests in `tests/test_fmg_patchworks.py` to cover:
  missing curve-idref detection and invalid `IFM` rejection.
- Added explicit export contract docs in `docs/reference/patchworks-export.rst`
  and linked it from `docs/index.rst` to record required XML/fragments fields.
- Re-validated direct K3Z export:
  `PYTHONPATH=src .venv/bin/python -m femic export patchworks --tsa k3z --output-dir output/patchworks_k3z_validated`
  succeeded (`au=14`, `fragments=218`, `curves=54`).
- Completed TSA29 export validation path from cached artifacts by reconstructing
  a TSA29 bundle/checkpoint under `output/patchworks_tsa29_validation/` and exporting with:
  `PYTHONPATH=src .venv/bin/python -m femic export patchworks --tsa 29 --bundle-dir output/patchworks_tsa29_validation/bundle --checkpoint output/patchworks_tsa29_validation/checkpoint7-tsa29.feather --output-dir output/patchworks_tsa29_validated`
  succeeded (`au=30`, `fragments=147959`, `curves=660`).

## 2026-03-08 - Woodstock compatibility export bootstrap (P4.2c)
- Added `src/femic/fmg/woodstock.py` with a Python 3 Woodstock compatibility export path:
  `export_woodstock_package(...)` now emits:
  - `woodstock_yields.csv` (long-form AU/IFM/age/volume curve rows)
  - `woodstock_areas.csv` (stand/AU/IFM/age/area table from checkpoint geometry/areas)
- Added CLI command `femic export woodstock` in `src/femic/cli/main.py`.
- Added regression tests:
  - `tests/test_fmg_woodstock.py`
  - new CLI wiring tests in `tests/test_cli_main.py`
- Updated docs:
  - `README.md` quickstart snippet for Woodstock compatibility export
  - `docs/reference/cli.rst` export command reference updates

## 2026-03-08 - Shared FMG core/adapters refactor (P4.2a foundation, P4.3 consolidation)
- Added shared core dataclasses in `src/femic/fmg/core.py`:
  `CurvePoint`, `CurveDefinition`, `AnalysisUnitDefinition`, `BundleModelContext`.
- Added shared bundle adapters in `src/femic/fmg/adapters.py`:
  - `normalize_tsa_code(...)`
  - `build_bundle_model_context_from_tables(...)`
  - `build_bundle_model_context(...)`
- Refactored Patchworks export (`src/femic/fmg/patchworks.py`) to consume
  shared `BundleModelContext` for AU/curve/species maps and retained prior
  user-facing counts (`curve_count` now sourced from original curve-table row count in context).
- Refactored Woodstock export (`src/femic/fmg/woodstock.py`) to consume
  shared `BundleModelContext` instead of local AU/curve parsing.
- Added adapter regression coverage in `tests/test_fmg_adapters.py`.
- Revalidated exporter flows after refactor:
  - Patchworks `k3z`: `au=14`, `fragments=218`, `curves=54`
  - Woodstock `k3z`: `yield_rows=16162`, `area_rows=218`
  - Woodstock `tsa29` (validation bundle/checkpoint): `yield_rows=10050`, `area_rows=147959`

## 2026-03-08 - Initial XML fixture parity coverage (P4.2b groundwork)
- Added deterministic Patchworks XML fixture:
  `tests/fixtures/fmg/forestmodel_minimal.xml`.
- Added parity test:
  `tests/test_fmg_patchworks.py::test_write_forestmodel_xml_matches_fixture`,
  which asserts serialized XML output is byte-identical to fixture content for
  a stable minimal AU/curve case.

## 2026-03-08 - Core ForestModel/Treatment class migration (P4.2a)
- Expanded `src/femic/fmg/core.py` with explicit ForestModel/Treatment classes:
  `ForestModelDefinition`, `SelectDefinition`, `TreatmentDefinition`,
  `AttributeBinding`, `DefineFieldDefinition`, `TreatmentAssignment`.
- Refactored `src/femic/fmg/patchworks.py` so XML generation now follows:
  shared bundle context -> `build_patchworks_forestmodel_definition(...)`
  -> `forestmodel_definition_to_xml_tree(...)` -> write/validate.
- Added regression test
  `tests/test_fmg_patchworks.py::test_build_patchworks_forestmodel_definition_contains_treatment`
  to assert treatment-bearing select blocks are present in the core definition.
- Revalidated patchworks export smoke:
  `PYTHONPATH=src .venv/bin/python -m femic export patchworks --tsa k3z --output-dir output/patchworks_k3z_modelclass_smoke`
  succeeded (`au=14`, `fragments=218`, `curves=54`).

## 2026-03-08 - Expanded deterministic XML fixture parity (P4.2b)
- Added richer multi-AU/species fixture parity coverage for Patchworks XML:
  - `tests/fixtures/fmg/forestmodel_multi_au.xml`
  - `tests/test_fmg_patchworks.py::test_write_forestmodel_xml_matches_multi_au_fixture`
- Marked `P4.2` and `P4.2b` complete in `ROADMAP.md` and updated the
  detailed next-step queue toward treatment transition/action parity and
  Woodstock ingest conventions.

## 2026-03-08 - Treatment transition + Woodstock ingest table extensions
- Extended Patchworks treatment serialization for transition semantics:
  - `TreatmentDefinition` now supports `transition_assignments`
  - serializer now emits `<transition><assign .../></transition>` blocks
  - default CC treatment includes transition assignment `IFM='managed'`
- Added new Patchworks CLI/export control:
  - `--cc-transition-ifm` (default `managed`)
- Extended Woodstock compatibility package outputs:
  - `woodstock_actions.csv` (baseline CC action rows by AU)
  - `woodstock_transitions.csv` (baseline managed transition rows by AU)
  - corresponding result metadata (`action_rows`, `transition_rows`)
  - CLI now accepts `--cc-min-age` / `--cc-max-age` for Woodstock export too
- Updated docs for new export behavior:
  - `README.md` (new Woodstock output files)
  - `docs/reference/cli.rst` (new options)
  - `docs/reference/woodstock-export.rst` (new reference page)
  - `docs/index.rst` and `docs/reference/patchworks-export.rst`
- Revalidated runtime smoke exports:
  - `femic export patchworks --tsa k3z` (`au=14`, `fragments=218`, `curves=54`)
  - `femic export woodstock --tsa k3z`
    (`yield_rows=16162`, `area_rows=218`, `action_rows=14`,
    `transition_rows=14`)

## 2026-03-08 - Patchworks species-wise yield curve derivation
- Extended `src/femic/fmg/patchworks.py` to derive species-wise yield curves from
  total-volume and species-proportion curves:
  - unmanaged: `feature.Yield.unmanaged.<SPP>`
  - managed: `feature.Yield.managed.<SPP>` and `product.Yield.managed.<SPP>`
- Derivation logic now evaluates species proportions at total-curve ages using
  constant or piecewise-linear interpolation, then multiplies by total volume.
- Added regression coverage:
  `tests/test_fmg_patchworks.py::test_build_forestmodel_xml_tree_adds_species_yield_curves`.
- Regenerated deterministic XML fixture baselines to include derived species
  yield attributes/curves:
  - `tests/fixtures/fmg/forestmodel_minimal.xml`
  - `tests/fixtures/fmg/forestmodel_multi_au.xml`
- Updated docs:
  - `docs/reference/patchworks-export.rst`
  - `README.md`

## 2026-03-08 - Patchworks XML flat-tail deduplication
- Updated Patchworks XML serialization to remove redundant repeated far-left
  and far-right y-values for non-`unity` curves while preserving the inner edge
  points of terminal plateaus.
- Added regression coverage:
  `tests/test_fmg_patchworks.py::test_forestmodel_xml_trims_repeated_curve_values_on_both_tails`.
- Documented behavior in `docs/reference/patchworks-export.rst`.

## 2026-03-08 - Patchworks XML non-finite value and all-flat curve hardening
- Hardened curve-point serialization in `src/femic/fmg/patchworks.py`:
  - non-finite `y` values are coerced to `0.0`
  - non-finite `x` values are dropped
  - points are sorted/normalized to monotonic `x` with duplicate-`x` collapse
- Fixed all-flat curve trimming edge case so single-point flat curves retain
  the earliest age point instead of collapsing to max-age `(299,0)` points.
- Added regression tests:
  - `test_forestmodel_xml_all_flat_curve_keeps_earliest_point`
  - `test_forestmodel_xml_sanitizes_nan_point_values`

## 2026-03-08 - Readable Patchworks curve IDs
- Replaced opaque numeric XML curve IDs (`C<id>`) with readable deterministic
  ids while preserving uniqueness and stable idref linkage:
  - `managed_total_<id>`, `unmanaged_total_<id>`
  - `managed_prop_<SPP>_<id>`, `unmanaged_prop_<SPP>_<id>`
  - `au_<au_id>_<managed|unmanaged>_yield_<SPP>` for derived species-yield curves
- Updated serializer curve ordering to deterministic lexical ordering
  (`unity` first, then sorted readable ids).

## 2026-03-08 - Integer age formatting for Patchworks curve x-values
- Updated Patchworks XML point serialization to format integral age `x` values
  as integers (for example `x="10"` instead of `x="10.000000"`).
- Kept fallback float formatting for non-integral `x` values to preserve
  compatibility with transformed or custom curves.
- Updated fixture baselines and regression expectations accordingly.

## 2026-03-08 - Patchworks y-value precision policy by curve family
- Updated Patchworks XML `y` formatting to reduce precision noise:
  - volume-yield curves (`managed_total_*`, `unmanaged_total_*`,
    `au_*_..._yield_*`) are now rounded to 1 decimal place
  - normalized/proportion curves are now rounded to at most 5 decimals
- Updated fixture baselines and tests accordingly.
- Updated fixture baselines and tests to assert new id conventions.

## 2026-03-08 - CC harvested-volume product consequences (species-wise)
- Added Patchworks product consequence attributes for CC harvested volume in
  `src/femic/fmg/patchworks.py`:
  - `product.HarvestedVolume.managed.Total.CC`
  - `product.HarvestedVolume.managed.<SPP>.CC`
- Bound harvested-volume attributes to managed total/species yield curves so
  per-species harvested volume tracks managed species-yield definitions.
- Extended regression checks in `tests/test_fmg_patchworks.py` and regenerated
  deterministic XML fixtures:
  - `tests/fixtures/fmg/forestmodel_minimal.xml`
  - `tests/fixtures/fmg/forestmodel_multi_au.xml`
- Regenerated validated K3Z Patchworks export:
  `output/patchworks_k3z_validated/forestmodel.xml`.

## 2026-03-08 - Patchworks managed/unmanaged semantics audit and fragment fix
- Reviewed `reference/UserGuide.pdf` semantics for block-vs-fragment,
  managed/unmanaged components, and treatment eligibility.
- Simplified fragments export logic in `src/femic/fmg/patchworks.py` for the
  K3Z teaching model:
  - exactly one output row per stand fragment (`1 fragment = 1 block`);
  - each row is assigned a single IFM state (`managed` or `unmanaged`);
  - `BLOCK` values are unique per row (no multi-row block components);
  - IFM assignment uses THLB signal precedence:
    `thlb` > `thlb_fact` > `thlb_area` > `thlb_raw` (positive => managed).
- Tightened IFM transition semantics by validating `cc_transition_ifm` to
  accepted IFM values (`managed` or `unmanaged`).
- Added/updated regression coverage in `tests/test_fmg_patchworks.py`:
  - one-row-per-fragment behavior
  - binary IFM assignment from THLB signals
  - invalid `cc_transition_ifm` rejection.
- Updated user-facing docs:
  - `docs/reference/patchworks-export.rst`
  - `README.md`

## 2026-03-08 - Remove redundant IFM=managed transition assignment
- Updated Patchworks treatment export to avoid redundant transition logic:
  CC tracks no longer emit `assign field="IFM" value="'managed'"` inside managed-only
  select statements.
- Changed default `cc_transition_ifm` to unset (`None`), making transition IFM assignment
  optional.
- Kept explicit non-redundant transitions supported (for example
  `--cc-transition-ifm unmanaged`).
- Updated CLI/docs:
  - `src/femic/cli/main.py`
  - `docs/reference/cli.rst`
  - `docs/reference/patchworks-export.rst`
- Updated regression coverage in `tests/test_fmg_patchworks.py` and refreshed
  XML fixture baselines.

## 2026-03-08 - Upstream yield terminology rename to untreated/treated
- Updated upstream bundle table assembly (`src/femic/pipeline/bundle.py`) to use
  canonical curve terminology:
  - `curve_type`: `untreated` and `treated`
  - species proportions: `untreated_species_prop_<SPP>` and
    `treated_species_prop_<SPP>`
- Added canonical AU columns:
  - `untreated_curve_id`
  - `treated_curve_id`
- Preserved backward compatibility by still emitting legacy alias columns:
  - `unmanaged_curve_id`
  - `managed_curve_id`
- Updated AU curve assignment defaults to canonical columns with fallback to
  legacy names when loading older tables.
- Updated FMG adapter compatibility (`src/femic/fmg/adapters.py`) so it accepts
  either canonical (`untreated/treated`) or legacy (`unmanaged/managed`) curve
  names and column names.
- Updated Patchworks curve-id normalization (`src/femic/fmg/patchworks.py`) so
  canonical upstream curve types map correctly to Patchworks IFM semantics.
- Updated docs/tests:
  - `README.md`
  - `tests/test_bundle.py`
  - `tests/test_fmg_adapters.py`

## 2026-03-08 - Docs tree cleanup (Sphinx source vs reference assets)
- Moved non-Sphinx reference assets out of `docs/reference/` into top-level
  `reference/` (including `reference/vdyp/`) so `docs/` remains documentation
  source only.
- Added `reference/README.md` to document purpose and boundaries of the new
  reference-asset directory.
- Updated path references that pointed to moved PDFs:
  - `config/tipsy/tsa29.yaml`
  - `ROADMAP.md`
  - `CHANGE_LOG.md`

## 2026-03-08 - Phase 5 docs recovery and guides expansion
- Added a new Sphinx `Guides` information architecture and wired it into
  `docs/index.rst` so pipeline walkthrough content is first-class and separate
  from API/contract reference pages.
- Added curated workflow guides under `docs/guides/` covering:
  - end-to-end pipeline walkthrough,
  - Stage 00 data prep assumptions/checkpoints,
  - Stage 01a strata/VDYP/TIPSY-input workflow,
  - Stage 01b post-TIPSY integration,
  - bundle/export workflow,
  - diagnostics interpretation,
  - troubleshooting/recovery,
  - known limitations and human-in-the-loop boundaries.
- Added notebook provenance artifacts:
  - `docs/guides/legacy-traceability.rst`
  - `docs/guides/legacy_notebook_coverage.csv`
  preserving markdown-cell-level mapping from legacy notebooks into current docs,
  including explicit `mapped` vs `retired` status.
- Added docs contract tests in `tests/test_docs_contract.py` for:
  - required guides/toctree presence,
  - completeness of notebook markdown coverage mapping,
  - high-value CLI option drift checks between Typer help output and
    `docs/reference/cli.rst`.
- Added a README documentation section linking the published site and clarifying
  Guides vs Reference scope.
- Updated `ROADMAP.md` with a new `Phase 5: Documentation Recovery + Expansion`
  checklist and detailed next-step notes; remaining work in this phase is
  deployment validation (`P5.7`) after push/publish.

## 2026-03-08 - Phase 5 publish validation and docs workflow deploy guard
- Verified GitHub Pages deployment for Phase 5 guide expansion on `main`:
  - live landing page now shows both `Guides` and `Reference` navigation blocks;
  - direct guide URLs under `/guides/*.html` return HTTP 200.
- Completed roadmap `P5.7` deployment-validation tasks and recorded direct URL
  checks for all new guide pages.
- Updated docs workflow deploy condition in `.github/workflows/docs-pages.yml`
  so deploy runs for both `push` and manual `workflow_dispatch` on `main`
  (while still excluding pull-request events).

## 2026-03-08 - Phase 6 kickoff: case onboarding templates and guide
- Started `Phase 6: Deployment Readiness and Case Onboarding` in `ROADMAP.md`
  and marked `P6.1` complete.
- Added reusable case onboarding templates:
  - `config/run_profile.case_template.yaml` (TSA + custom-boundary profile scaffold)
  - `config/tipsy/template.case.yaml` (new-case TIPSY config starter)
- Added onboarding guide page:
  - `docs/guides/case-onboarding.rst`
  including required-input and acceptance checklists.
- Wired onboarding page into guides navigation (`docs/guides/index.rst`) and
  linked onboarding assets from `README.md`.
- Extended docs contract checks in `tests/test_docs_contract.py` to assert
  onboarding templates exist and remain part of maintained docs structure.

## 2026-03-08 - Phase 6 P6.2: one-command case preflight validation
- Added a new CLI command: `femic prep validate-case`.
- `prep validate-case` now validates case prerequisites from a run profile before
  long compile runs, including:
  - run-profile parsing/structure validity,
  - boundary-mode integrity (`selection.boundary_path` / `selection.boundary_code`),
  - required case TIPSY config presence/validation,
  - required external source datasets (VRI, VDYP input, TSA boundaries, siteprod),
  - log directory readiness warnings.
- Added explicit remediation-oriented error messages for missing prerequisites.
- Added `--strict-warnings` mode to fail preflight when warnings are present.
- Updated CLI reference docs with `prep validate-case` options:
  - `--run-config`, `--tipsy-config-dir`, `--strict-warnings`.
- Updated onboarding guide to include the new single-command preflight step.
- Added regression tests in `tests/test_case_preflight_cli.py` covering:
  - successful validation,
  - missing TIPSY config failure,
  - boundary-code required failure,
  - strict-warning failure behavior.
- Extended docs contract checks to include `prep validate-case` option drift.

## 2026-03-08
- Added Phase 7 roadmap section for Patchworks runtime integration, Wine execution, and UBC VPN-linked licensing checks.
- Added `reference/Patchworks/` to `.gitignore` so proprietary Patchworks binaries/docs are not published from this repo.
- Added `src/femic/patchworks_runtime.py` with config loading, Wine path translation, license parsing, preflight checks, deterministic Matrix Builder command assembly, and log/manifest capture.
- Added new CLI group `femic patchworks` with:
  - `patchworks preflight` (Wine/Java/jar/input/license checks, optional reachability skip)
  - `patchworks matrix-build` (direct Matrix Builder or interactive AppChooser mode under Wine)
- Added baseline runtime config file `config/patchworks.runtime.yaml` for local execution wiring.
- Added new operator guides:
  - `docs/guides/patchworks-wine-runtime.rst`
  - `docs/guides/ubc-vpn-license-connectivity.rst`
- Updated docs navigation and CLI reference to include Patchworks runtime commands/options.
- Added tests for Patchworks runtime helpers and CLI wiring:
  - `tests/test_patchworks_runtime.py`
  - extended `tests/test_cli_main.py` and `tests/test_docs_contract.py`.
- Updated README with Patchworks runtime command examples and proprietary-runtime boundary note.
- Closed Phase 7 git-protection follow-up by verifying `reference/Patchworks/` is ignored and no proprietary Patchworks bundle files are tracked in the repository index.
- Updated roadmap status so P7.1 is complete; next practical Phase 7 task is live UBC VPN + Wine license-server validation.
- Fixed Patchworks runtime config relative-path resolution so sample config paths work from repo root when config lives under `config/`.
- Added `femic export release` student-facing packaging command, including strict required-artifact validation and versioned release directory output.
- Added release package outputs: `release_manifest.json` (SHA256 file inventory) and `HANDOFF.md` (operator checklist/commands).
- Added tests for release packaging and CLI wiring (`tests/test_release_packaging.py`, `tests/test_cli_main.py`) and expanded docs CLI contract coverage.
- Updated export workflow docs to include release package generation step.
- Re-ran `femic patchworks preflight` after runtime-config path fix: artifact-path errors resolved; remaining failures are environment-dependent (`java -version` in Wine and license host reachability without active UBC VPN).

## 2026-03-09 - Patchworks licensing behavior fix (no direct reachability probe)
- Refactored Patchworks runtime preflight so FEMIC validates environment/config
  only and no longer performs DNS/TCP reachability probes against license host
  or inferred ports.
- Added required `patchworks.spshome` config support (with `SPSHOME` env
  fallback) and fail-fast validation when missing.
- Ensured `SPSHOME` is injected into the Wine subprocess environment for
  `femic patchworks matrix-build` alongside `SPS_LICENSE_SERVER`.
- Removed CLI `patchworks preflight --skip-license-reachability` and updated
  runtime/docs/tests accordingly.
- Updated operator docs to state license validation is performed by Patchworks
  at launch, not by FEMIC preflight.

## 2026-03-09 - Live Patchworks runtime validation follow-up
- Committed and ran live `femic patchworks preflight` with updated runtime
  config; preflight now passes with env/config-only validation and no port
  probing.
- Updated `config/patchworks.runtime.yaml` `patchworks.spshome` to the actual
  Wine-visible local install path:
  `Z:\\home\\gep\\projects\\wbi_ria_yield\\reference\\Patchworks`.
- Ran `femic patchworks matrix-build`; command wrapper returned code 0 but
  Patchworks did not produce `tracks/` output and stderr captured runtime
  blockers: missing `mrsidget2_64` native library, missing X display peer
  context, and `Not licensed or no connection to license server`.

## 2026-03-09 - Patchworks matrix-build hardening + headless launch support
- Added `patchworks.use_xvfb` runtime config support; when enabled FEMIC wraps
  Wine launch with `xvfb-run -a` for headless environments.
- Updated Patchworks command assembly to inject Windows-side runtime vars before
  Java launch:
  - `set "SPSHOME=..."`
  - `set "PATH=%PATH%;<SPSHOME>;<SPSHOME>\\lib"`
  - `java -Djava.library.path="<SPSHOME>\\lib" -jar patchworks.jar ...`
- Added deterministic matrix-build failure detection:
  - scan combined process output for fatal signatures (licensing/native runtime
    failures),
  - require non-empty matrix output directory for non-interactive runs.
- Installed `xvfb` in the container and re-ran matrix-build; failure is now
  explicit and actionable (`Not licensed or no connection to license server`,
  `IP Helper Library GetAdaptersAddresses function failed`, and missing
  output artifacts), instead of silent return-code-only success.

## 2026-03-09 - ForestModel schema-order fix for Matrix Builder
- User-run Matrix Builder on Windows surfaced a ForestModel parse error:
  top-level `<input>` placement invalid for the current schema implementation.
- Updated Patchworks XML serialization order in
  `src/femic/fmg/patchworks.py` to emit root children as:
  `curve*`, `define*`, `input`, `output`, `select*`.
- Regenerated deterministic Patchworks XML fixtures:
  - `tests/fixtures/fmg/forestmodel_minimal.xml`
  - `tests/fixtures/fmg/forestmodel_multi_au.xml`
- Re-exported `output/patchworks_k3z_validated/forestmodel.xml` with corrected
  element ordering for immediate external Matrix Builder retest.

## 2026-03-09 - Patchworks select-statement AU type fix
- User Matrix Builder run on Windows surfaced expression typing failure:
  `AU` (integer) compared against quoted string literal in `<select statement>`.
- Updated Patchworks exporter to emit numeric AU predicates:
  `AU eq <integer>` (no quotes), while preserving quoted string comparisons
  for categorical fields (`IFM`, `treatment`).
- Regenerated Patchworks fixtures and re-exported
  `output/patchworks_k3z_validated/forestmodel.xml` with corrected select
  statement typing.

## 2026-03-09 - Patchworks XML header mode alignment (XSD over DTD)
- Updated Patchworks XML writer to emit the XSD model hint used by current
  Patchworks sample models:
  `<?xml-model href="https://www.spatial.ca/ForestModel.xsd"?>`.
- Removed legacy DTD DOCTYPE header emission from generated ForestModel XML to
  avoid parser-mode/order conflicts observed in Matrix Builder.
- Regenerated K3Z ForestModel export and updated tests expecting XML header
  content accordingly.

## 2026-03-09 - Native Windows Patchworks runtime + artifact-based completion
- Added native Windows support for `femic patchworks` runtime execution:
  - preflight now uses host `java` on Windows (no Wine requirement),
  - matrix-build now launches `java -jar patchworks.jar ...` directly on
    Windows with `cwd` set to the Patchworks install directory.
- Kept Linux behavior unchanged (`wine cmd /c ...`) so existing container
  runtime paths continue to work.
- Hardened non-interactive matrix-build preconditions and completion semantics:
  - create matrix output directory before launch,
  - evaluate success using output artifact presence + fatal-log signatures,
    not JVM return code alone (matches observed Patchworks `Process.main(argv)`
    background-thread behavior).
- Extended runtime manifest payload with both `raw_returncode` and effective
  FEMIC `returncode` for clearer operator diagnostics.
- Updated docs and tests:
  - `README.md` Patchworks runtime notes now describe native Windows behavior
    and artifact-based completion checks,
  - expanded `tests/test_patchworks_runtime.py` coverage for Windows preflight
    launcher selection and artifact-driven success handling.

## 2026-03-09 - K3Z Patchworks model folder reorganization (sample-aligned)
- Created a new sample-aligned K3Z model root at:
  `C:\Users\gep\Desktop\msfm2025\k3z_patchworks_model`
  with top-level folders matching Patchworks `sample_2024` conventions
  (`analysis`, `blocks`, `data`, `imagery`, `misc`, `roads`, `scenarios`,
  `scripts`, `tracks`, `yield`).
- Mapped current K3Z artifacts into the reorganized layout:
  - `fragments.*` -> `...\data\`
  - `forestmodel.xml` -> `...\yield\forestmodel.xml`
  - seeded `...\scripts\` from `reference/Patchworks-202502/sample_2024/scripts`.
- Updated Windows runtime config to target the new structure:
  `config/patchworks.runtime.windows.yaml` now points matrix-builder inputs/
  outputs at `...\k3z_patchworks_model\data`, `...\yield`, and `...\tracks`.
- Verified end-to-end on Windows with:
  `femic patchworks matrix-build --run-id win_native_k3z_reorg_20260309`
  completing with `returncode=0` and refreshed track CSV outputs under the new
  `tracks/` folder.

## 2026-03-09 - Adapted K3Z `prepareBlocks.bsh` for FEMIC workflow
- Replaced the copied sample script at
  `C:\Users\gep\Desktop\msfm2025\k3z_patchworks_model\scripts\dataPrep\prepareBlocks.bsh`
  with a FEMIC-specific adaptation.
- Updated script assumptions/paths to K3Z model layout:
  - fragments: `data/fragments.*`
  - ForestModel XML: `yield/forestmodel.xml` (required; no sample fallback)
  - tracks output: `tracks/`.
- Switched matrix build invocation to direct API usage:
  `new ca.spatial.tracks.builder.Process(...).execute(false)` plus
  synchronized wait for completion (instead of `AppChooser.invoke(...)`).
- Kept legacy C5 dissolve/join logic as optional toggles, with safe skip
  behavior when `data/fragments_blocks_lu.csv` is absent.

## 2026-03-09 - Added `patchworks build-blocks` (1:1 stand:block + topology)
- Added a new CLI command:
  `python -m femic patchworks build-blocks --config <runtime.yaml>`
  that prepares Patchworks block artifacts directly from fragments for PIN setup.
- Added runtime helpers in `src/femic/patchworks_runtime.py`:
  - infer model root from runtime config paths,
  - build `blocks/blocks.shp` in strict 1:1 mode (`BLOCK <- FEATURE_ID/FRAGS_ID`),
  - optionally generate `blocks/topology_blocks_<radius>r.csv`
    with schema `BLOCK1,BLOCK2,DISTANCE,LENGTH`, including exterior `-9999` rows.
- Added CLI wiring + options in `src/femic/cli/main.py`:
  - `--model-dir`
  - `--fragments-shp`
  - `--topology-radius` (default `200.0`)
  - `--with-topology/--no-topology`
- Updated docs:
  - `README.md` Patchworks runtime workflow now includes `build-blocks`
  - `docs/reference/cli.rst` includes the new subcommand and options.
- Added regression coverage:
  - `tests/test_patchworks_runtime.py` for model-root inference and
    blocks/topology artifact generation.
  - `tests/test_cli_main.py` for `patchworks build-blocks` CLI success/failure.
  - `tests/test_docs_contract.py` for CLI/docs option drift checks.
- Updated `config/patchworks.runtime.windows.yaml` to point to active K3Z model
  under `C:\Users\gep\Documents\msfm\msfm2025\k3z_patchworks_model`.
- Live run verification:
  - Command: `python -m femic patchworks build-blocks --config config/patchworks.runtime.windows.yaml --topology-radius 200`
  - Output: `blocks/blocks.shp` and `blocks/topology_blocks_200r.csv`
    created with `218` blocks and `928` topology rows.

## 2026-03-09 - Patchworks IFM tuning controls for THLB `[0,1]` checkpoints
- Confirmed legacy THLB assignment path remains unchanged in 00 pipeline parity:
  `assign_thlb_area_and_flag` still uses fixed thresholds (`93` for TSA08,
  `69` for TSA24, else `50`) and percent-style `thlb_raw` semantics.
- Added explicit export-time controls so operators can tune IFM assignment
  deterministically when checkpoint THLB signals are continuous/binary:
  - `--ifm-source-col` (select signal column, e.g. `thlb_raw`)
  - `--ifm-threshold` (managed when signal > threshold)
  - `--ifm-target-managed-share` (top-N stands managed by signal rank)
  - with validation that threshold/share options are mutually exclusive.
- Wired options through:
  - `src/femic/fmg/patchworks.py`
  - `src/femic/fmg/__init__.py`
  - `src/femic/cli/main.py`
- Updated docs:
  - `README.md`
  - `docs/reference/cli.rst`
  - `docs/reference/patchworks-export.rst`
- Added regression coverage:
  - `tests/test_fmg_patchworks.py` (threshold override, target-share mode,
    conflicting-option validation)
  - `tests/test_cli_main.py` (CLI wiring)
  - `tests/test_docs_contract.py` (help/docs option contract)
- Validation:
  - `ruff format src tests` passed
  - `ruff check src tests` passed
  - `mypy src` passed
  - targeted tests passed (`tests/test_fmg_patchworks.py`,
    `tests/test_cli_main.py`, `tests/test_docs_contract.py`)
  - `sphinx -b html docs _build/html -W` passed
  - full `pytest` still has pre-existing unrelated failures in this Windows env
    (path-separator expectations, optional plotting deps, and `derive_species`
    NaN handling outside this change set).

## 2026-03-10 - Patchworks accounts sync, seral export support, and CC min-age update
- Added automatic matrix-build account promotion in
  `src/femic/patchworks_runtime.py`: when `tracks/protoaccounts.csv` exists,
  FEMIC now writes `tracks/accounts.csv` after build and creates a timestamped
  backup (`accounts_backup_<timestamp>.csv`) if an existing `accounts.csv` is
  present.
- Added matrix-build manifest/CLI reporting for the account-sync step
  (`accounts_sync.status`, source/target paths, and optional backup path).
- Added optional `--seral-stage-config` support to
  `femic export patchworks` (wired through CLI and exporter) so ForestModel XML
  can emit per-AU seral curves and bind `feature.Seral.*` and
  `product.Seral.*` attributes with default and per-AU YAML overrides.
- Added `config/seral.k3z.yaml` as a starter K3Z seral-stage config.
- Updated Patchworks CC treatment `minage` semantics to use
  `CMAI(managed_total_curve) - 20` per AU (clamped to `0..--cc-max-age`);
  fallback to `--cc-min-age` applies only when no managed curve is available.
- Updated docs (`README.md`, `docs/reference/patchworks-export.rst`,
  CLI/docs references) and tests (`tests/test_fmg_patchworks.py`,
  `tests/test_patchworks_runtime.py`, `tests/test_cli_main.py`) to match the
  new behavior.

## 2026-03-09 - Seral account semantics fix (`feature` only, no `product.Seral`)
- Corrected Patchworks seral export semantics: removed `product.Seral.*`
  attribute emission from `src/femic/fmg/patchworks.py`.
- Kept seral-stage inventory/state attributes as `feature.Seral.*` only.
- Updated regression coverage in `tests/test_fmg_patchworks.py` to assert
  `product.Seral.*` is not present in exported XML.
- Updated docs in `docs/reference/patchworks-export.rst` to remove
  `product.Seral.*` guidance.
- Repaired live K3Z model XML at
  `C:\Users\gep\Documents\msfm\msfm2025\k3z_patchworks_model\yield\forestmodel.xml`
  and re-ran Matrix Builder (`run_id=feature_seral_only_20260310`), confirming
  `tracks/protoaccounts.csv` and `tracks/accounts.csv` now include
  `feature.Seral.*` accounts only.

## 2026-03-09 - Added seral treatment-area consequence accounts and map layer
- Added Patchworks exporter support for treatment-consequence seral area
  accounts in CC product tracks:
  `product.Seral.area.<stage>.<au_id>.CC`.
- Updated `tests/test_fmg_patchworks.py` and
  `docs/reference/patchworks-export.rst` to reflect the semantic split:
  `feature.Seral.*` for inventory state and `product.Seral.area.*.*.CC` for
  treatment consequences.
- Patched live K3Z ForestModel XML to add
  `product.Seral.area.<stage>.<au_id>.CC` attributes and re-ran
  `femic patchworks matrix-build` (`run_id=seral_area_accounts_20260310`);
  verified these accounts now appear in:
  - `tracks/protoaccounts.csv`
  - `tracks/accounts.csv`.
- Added a Seral Stages map layer to live model PIN:
  `C:\Users\gep\Documents\msfm\msfm2025\k3z_patchworks_model\analysis\base.pin`
  using sample-style `DitherTheme` config (`feature.Seral.*` themes with
  legend title `Seral Stages`).

## 2026-03-10 - Moved K3Z Patchworks prototype model into repo for tracking
- Added in-repo tracked prototype model at:
  `models/k3z_patchworks_model/` (analysis/blocks/data/scripts/tracks/yield).
- Updated `config/patchworks.runtime.windows.yaml` matrix builder paths to use
  config-relative in-repo locations:
  `../models/k3z_patchworks_model/...`.
- Verified runtime against the in-repo model:
  - `python -m femic patchworks preflight --config config/patchworks.runtime.windows.yaml`
  - `python -m femic patchworks matrix-build --config config/patchworks.runtime.windows.yaml --run-id repo_model_move_verify_20260310`
  - matrix build completed with `returncode=0` and accounts sync.

## 2026-03-10 - Added Sample Models docs section and detailed K3Z guide
- Added a new top-level Sphinx docs navigation section in `docs/index.rst`:
  `Sample Models`.
- Added `docs/sample-models/index.rst` and wired it into the docs toctree.
- Added a detailed K3Z user-facing guide at `docs/sample-models/k3z.rst`
  covering:
  - model purpose/scope and authoritative source path
    (`models/k3z_patchworks_model`),
  - full model anatomy mapping (`analysis/`, `blocks/`, `data/`, `scripts/`,
    `tracks/`, `yield/` and supporting folders),
  - repo-based rebuild workflow (`preflight`, `build-blocks`, `matrix-build`)
    with expected artifacts and runtime log/manifest paths,
  - runtime config pathing notes for
    `config/patchworks.runtime.windows.yaml`,
  - matrix-builder account sync behavior
    (`protoaccounts.csv -> accounts.csv` + timestamped backup),
  - current assumptions/parameters, safe-to-edit vs regenerate guidance,
    seral semantics, and common troubleshooting signatures.
- Added new planning phase to `ROADMAP.md`:
  `Phase 8: K3Z Metadata + Student-Facing How-To Documentation Program`,
  including explicit sub-steps for metadata lineage, assumption registry,
  component mapping, edit policy matrix, scenario guidance, and docs QA.
- Updated `ROADMAP.md` Detailed Next Steps Notes with a matching entry tied to
  the current in-repo K3Z model state.

## 2026-03-10 - Roadmap progress checkboxes updated for delivered K3Z docs work
- Updated `ROADMAP.md` Phase 8 checklist statuses so completed items are
  visibly checked off instead of all pending.
- Marked completed starter tasks:
  - `P8.2a/P8.2b` (defaults + file/CLI mapping),
  - `P8.3a/P8.3b/P8.3c` (component traceability and PIN map/report wiring),
  - `P8.4a/P8.4b` (edit-policy matrix + regeneration runbooks),
  - `P8.6a/P8.6b/P8.6c` (onboarding/checklist, troubleshooting cookbook,
    collaborator change-management notes).
- Left deeper metadata and QA items pending (`P8.1*`, `P8.2c`, `P8.4c`,
  `P8.5*`, `P8.7*`) to reflect remaining scope accurately.

## 2026-03-10 - Completed P6.4 onboarding regression scenario tests
- Added new-case onboarding smoke coverage in
  `tests/test_case_preflight_cli.py`:
  - instantiate run-profile from `config/run_profile.case_template.yaml`,
  - instantiate TIPSY config from `config/tipsy/template.case.yaml`,
  - validate the derived case with `femic prep validate-case`.
- Added template-driven boundary-mode compatibility coverage:
  - derived profile with `selection.boundary_path` + `selection.boundary_code`,
  - matching `tsa<boundary_code>.yaml` TIPSY config,
  - successful `prep validate-case` preflight.
- Added docs linkage contract in `tests/test_docs_contract.py` to enforce that
  `docs/guides/case-onboarding.rst` continues to reference:
  - `config/run_profile.case_template.yaml`,
  - `config/tipsy/template.case.yaml`,
  - `python -m femic prep validate-case`.
- Updated `ROADMAP.md` checklist status:
  - `P6.4`, `P6.4a`, `P6.4b`, and `P6.4c` are now checked complete.

## 2026-03-10 - Completed P8.1 K3Z metadata inventory + lineage baseline
- Added new Sample Models docs page:
  `docs/sample-models/k3z-metadata-lineage.rst`.
- Documented:
  - source dataset inventory feeding `data/`, `yield/`, and `blocks/`,
  - transformation lineage chain from FEMIC bundle/checkpoint through
    export/sync/build-blocks/matrix-build,
  - provenance versioning policy for future model refreshes.
- Added machine-readable lineage registry under the tracked model:
  `models/k3z_patchworks_model/metadata/lineage_registry.yaml` with:
  - artifact-to-source mappings,
  - canonical build commands,
  - notes on account sync and generated-artifact handling.
- Updated docs navigation and linking:
  - added `k3z-metadata-lineage` to `docs/sample-models/index.rst`,
  - linked metadata lineage references from `docs/sample-models/k3z.rst`.
- Updated `ROADMAP.md`:
  - marked `P8.1`, `P8.1a`, `P8.1b`, and `P8.1c` complete,
  - appended matching Detailed Next Steps Notes entry.

## 2026-03-10 - Completed P8.2c and P8.4c in K3Z guide
- Expanded `docs/sample-models/k3z.rst` with a new
  `Parameter Risk and Suggested Ranges` section documenting practical guardrails
  and risk notes for key student-tuned controls:
  - IFM managed share/threshold behavior,
  - topology radius sensitivity,
  - seral boundary consistency expectations,
  - CC min-age override risks,
  - horizon/target-coupling caution.
- Added `Backup and Recovery Conventions` section to the same guide covering:
  - run-log/manifest retention,
  - automatic `tracks/accounts.csv` timestamp backup behavior during matrix-build,
  - git checkpoint discipline before high-impact edits,
  - regeneration-first recovery flow for generated artifact families.
- Updated roadmap status:
  - `P8.2c` and `P8.4c` checked complete,
  - parent items `P8.2` and `P8.4` now fully complete.

## 2026-03-10 - Completed P8.5 scenario interpretation guidance
- Expanded `docs/sample-models/k3z.rst` with a new
  `Scenario Comparison Guidance` section for teaching use.
- Added within-scenario and cross-scenario interpretation workflow for:
  - inventory-stage trajectories (`feature.Seral.*`),
  - treatment-stage trajectories (`product.Seral.area.<stage>.<au_id>.CC`).
- Added a minimum report-template matrix linking core classroom questions to:
  - account sources,
  - suggested period/stage/AU aggregations.
- Updated roadmap status:
  - `P8.5a`, `P8.5b`, and `P8.5c` checked complete,
  - parent item `P8.5` now fully complete.

## 2026-03-10 - Completed P8.7 docs QA and release-readiness checks
- Extended docs contract coverage in `tests/test_docs_contract.py`:
  - verifies Sample Models navigation wiring from `docs/index.rst` and
    `docs/sample-models/index.rst`,
  - enforces required K3Z guide sections in `docs/sample-models/k3z.rst`,
  - enforces required metadata-lineage sections in
    `docs/sample-models/k3z-metadata-lineage.rst`.
- Added `Release Readiness Checklist` section to
  `docs/sample-models/k3z.rst` for student/collaborator distribution workflow.
- Updated roadmap status:
  - `P8.7a`, `P8.7b`, and `P8.7c` checked complete,
  - parent item `P8.7` now fully complete.

## 2026-03-10 - Queued K3Z plot integration follow-up in roadmap
- Added pending roadmap item `P8.6d`:
  `Roll regenerated strata/AU build plots into user-facing K3Z docs`.
- Added matching Detailed Next Steps note in `ROADMAP.md`, appended at the end
  of the running chronological list.

## 2026-03-10 - Validation gate unblock and cross-platform path/runtime fixes
- Resolved 8 Windows validation failures that were blocking full quality-gate
  completion:
  - normalized selected serialized path outputs to POSIX form for stable
    cross-platform contract behavior:
    - `FEMIC_BOUNDARY_PATH` in legacy execution env payload,
    - `release_manifest.json` file `path` entries,
    - VDYP run context path fields and batch command IO dir segment,
    - stand shapefile export target path string.
  - made VDYP diagnostic/overlay plot emitters no-op when `matplotlib` is not
    installed (instead of failing smoothing execution).
  - updated species-slot derivation to filter NaN-like entries.
- Validation gates now pass in this environment:
  - `ruff format src tests`
  - `ruff check src tests`
  - `mypy src`
  - `pytest` (`403 passed`)
  - `pre-commit run --all-files`
  - `sphinx-build -b html docs _build/html -W`

## 2026-03-10 - Added Phase 9 rebrand roadmap (`wbi_ria_yield` -> `femic`)
- Added new `ROADMAP.md` phase:
  `Phase 9: Repository + Project Rebrand (wbi_ria_yield -> femic)`.
- Planned checklist scope includes:
  - metadata/title rebrand (`README`, docs title, citation metadata),
  - URL endpoint updates (GitHub repo slug + GitHub Pages URL),
  - runtime config cleanup for old absolute path assumptions,
  - legacy-slug sweep policy and notebook-output handling,
  - cutover validation gates and post-rename smoke checks.
- Created dedicated branch for rebrand work:
  `feature/rebrand-femic` (and marked `P9.5a` complete in roadmap).

## 2026-03-10 - Phase 9 implementation slice 1 (metadata/docs/config rebrand)
- Updated canonical project naming surfaces to `femic`:
  - `README.md` title,
  - `docs/conf.py` project name,
  - `docs/index.rst` landing title,
  - `CITATION.cff` title.
- Added explicit transition marker in `README.md`:
  formerly `wbi_ria_yield`.
- Updated target publication/repository URLs to new slug:
  - `https://ubc-fresh.github.io/femic/`
  - `https://github.com/UBC-FRESH/femic`
- Removed old hard-coded local repo-slug assumption from
  `config/patchworks.runtime.yaml` by dropping static `patchworks.spshome`
  path; runtime now resolves install home from `SPSHOME` env when needed.
- Updated roadmap status:
  - marked `P9.1` complete (`P9.1a/P9.1b/P9.1c`),
  - marked `P9.2a` and `P9.2b` complete,
  - marked `P9.3a` complete,
  - marked `P9.5b` complete.

## 2026-03-10 - Phase 9 implementation slice 2 (runtime/post-rename smoke)
- Confirmed new repository remote + branch publication on renamed origin:
  - origin URL now `https://github.com/UBC-FRESH/femic.git`
  - pushed `feature/rebrand-femic` with upstream tracking.
- Performed post-rename smoke checks:
  - `python -m femic --help` succeeds.
  - `sphinx-build -b html docs _build/html -W` succeeds.
  - `femic patchworks preflight --config config/patchworks.runtime.windows.yaml`
    succeeds on this host.
  - `femic patchworks preflight --config config/patchworks.runtime.yaml` now
    reports missing local artifacts (jar/fragments/xml) without requiring
    hard-coded `spshome` in config.
- Added regression coverage for env-driven install-home resolution:
  - `tests/test_patchworks_runtime.py::test_load_patchworks_runtime_config_uses_env_spshome_when_field_missing`.
- Updated roadmap status:
  - marked `P9.3b`, `P9.3c`, and `P9.5c` complete.
  - kept `P9.2c` pending until a post-merge docs-pages deploy verifies the
    renamed published URL endpoint.
- Observed in GitHub Actions that the latest `docs-pages` deployment record
  still points to `https://ubc-fresh.github.io/wbi_ria_yield/`; a new
  main-branch deploy is still required to confirm the `.../femic/` endpoint.

## 2026-03-10 - Patchworks preflight warns on missing SPSHOME env
- Updated Patchworks preflight semantics to surface install-registration
  confidence explicitly:
  - when `SPSHOME` is absent from the current process environment,
    `run_patchworks_preflight(...)` now emits a warning that Patchworks may not
    be correctly installed/registered on the host.
- Added regression coverage:
  - `tests/test_patchworks_runtime.py::test_run_patchworks_preflight_warns_when_env_spshome_missing`.
- Full validation gates re-run and passing after this change.

## 2026-03-10 - GitHub Pages rename verification + Node 24 action opt-in
- Confirmed docs deployment after repo rename is live at:
  `https://ubc-fresh.github.io/femic/`.
- Addressed GitHub Actions Node 20 deprecation warning in docs workflow by:
  - setting `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24=true` in
    `.github/workflows/docs-pages.yml`,
  - upgrading `actions/upload-pages-artifact` from `@v3` to `@v4`.
- Updated roadmap status:
  - marked `P9.2c` complete.

## 2026-03-10 - Phase 9 closure pass (legacy-slug sweep + notebook policy)
- Completed final rebrand cleanup and policy enforcement to close Phase 9:
  - removed residual transition slug mention from `README.md` so active
    user-facing docs/config no longer reference `wbi_ria_yield`,
  - added `Notebook Output Cleanup Policy` to
    `docs/guides/legacy-traceability.rst` with explicit
    `jupyter nbconvert --clear-output --inplace ...` guidance,
  - added docs contract checks in `tests/test_docs_contract.py` to enforce:
    - presence of the notebook cleanup policy section,
    - legacy slug references restricted to audit-trail files only
      (`ROADMAP.md`, `CHANGE_LOG.md`).
- Updated roadmap status:
  - marked `P9.2` complete,
  - marked `P9.4a`, `P9.4b`, `P9.4c`, and parent `P9.4` complete.

## 2026-03-10 - Phase 10 slice 1: instance decoupling + deployment bootstrap
- Added first-class instance-root resolution in `src/femic/instance_context.py`
  with precedence:
  - `--instance-root`
  - `FEMIC_INSTANCE_ROOT`
  - current working directory
  and legacy repo-root fallback warnings for transition compatibility.
- Added shared `--instance-root` option wiring across operational CLI surfaces:
  `run`, `prep validate-case`, `tipsy validate`, `tsa post-tipsy`,
  `export patchworks|woodstock|release`, and
  `patchworks preflight|matrix-build|build-blocks`.
- Added `femic instance init` command (`instance` CLI namespace) to scaffold
  filesystem-first deployment workspaces with:
  - `config/`, `config/tipsy/`, `data/`, `output/`, `vdyp_io/logs/`,
    workspace `.gitignore`, and `QUICKSTART.md`.
- Added built-in BC dataset bootstrap URLs and optional download/extract flow
  (default prompt `Y/n`) for:
  - `VEG_COMP_LYR_R1_POLY_2024.gdb.zip`
  - `VEG_COMP_VDYP7_INPUT_POLY_AND_LAYER_2024.gdb.zip`
  into standard instance paths under `data/`.
- Added package-owned resources under `src/femic/resources/`:
  - instance templates (`resources/instance/...`)
  - legacy scripts (`resources/legacy/00_data-prep.py`,
    `01a_run-tsa.py`, `01b_run-tsa.py`).
- Updated legacy workflow runtime to execute packaged legacy scripts by default
  (`src/femic/workflows/legacy_resources.py` + `src/femic/workflows/legacy.py`),
  removing hard dependency on repo-root script paths.
- Updated `pyproject.toml` package-data configuration so instance templates and
  legacy scripts ship with installed wheels.
- Added docs updates for the new workflow:
  - `docs/guides/deployment-instances.rst`
  - `docs/guides/case-onboarding.rst`
  - `docs/reference/cli.rst`
  - `README.md` quickstart.
- Added/updated tests:
  - `tests/test_instance_context.py`
  - `tests/test_instance_bootstrap.py`
  - `tests/test_legacy_resources.py`
  - `tests/test_cli_main.py`
  - `tests/test_pipeline_helpers.py`
- Extended Phase 10 roadmap scope with a dedicated DataLad dataset-repo
  workstream for "public but not directly accessible" dependencies
  (including archived HectaresBC `misc*.tif` layers), plus planned Git
  submodule linkage back into FEMIC.

## 2026-03-10 - Completed P10.6a dataset inventory baseline for DataLad planning
- Added machine-readable dataset registry:
  `metadata/required_datasets.yaml`.
- Captured required external/input dataset families with:
  - canonical instance paths,
  - source URL/publisher,
  - access mode (`direct_http`, `manual_catalog_retrieval`, `archive_only`,
    `operator_supplied`),
  - license/provenance notes,
  - checksum fields (`sha256` + status),
  - DataLad mirror inclusion flags/rationale.
- Explicitly inventoried archived HectaresBC THLB dependency:
  `misc.thlb.tif` as a mirror-priority dataset.
- Added docs page:
  `docs/guides/data-access-inventory.rst` and linked it from guides index and
  deployment-instance guide.
- Updated roadmap state:
  - marked `P10.6a` complete,
  - appended matching Detailed Next Steps note for queued `P10.6b`.

## 2026-03-10 - Added DataLad mirror runbook and seed manifest (`P10.6d`)
- Added user-facing guide:
  `docs/guides/public-data-mirror-runbook.rst`.
- Wired guide into docs navigation and deployment-instance references.
- Added mirror candidate seed manifest:
  `metadata/datalad_mirror_seed.csv`.
- Added maintainer bootstrap note:
  `planning/femic_public_data_datalad_bootstrap.md`.
- Updated roadmap state:
  - marked `P10.6d` complete,
  - retained `P10.6b/P10.6c` as next execution steps.

## 2026-03-11 - Linked local DataLad public-data repo as FEMIC submodule (`P10.6c`)
- Created local DataLad dataset repository:
  `/home/gep/projects/femic-public-data`.
- Mirrored current seed artifacts into canonical mirror paths:
  - `data/misc.thlb.tif`
  - `data/bc/tsa/FADM_TSA.gdb`
  - `data/bc/siteprod/Site_Prod_BC.gdb`
  - `data/bc/vri/2019/VEG_COMP_LYR_R1_POLY.gdb`
  - `data/bc/vri/2019/VEG_COMP_VDYP7_INPUT_POLY_AND_LAYER_2019.gdb`
- Added submodule linkage in FEMIC:
  `external/femic-public-data`.
- Updated roadmap state:
  - marked `P10.6c` complete,
  - kept `P10.6b` open pending GitHub publish + Arbutus special-remote setup
    and checksum backfill.

## 2026-03-11 - Hardened P10.6b runbook using lab DataLad/Arbutus templates
- Incorporated known-good command ordering from:
  - `tmp/datalad-kb-page.md`
  - `tmp/lab-data-workflow-workshop` references
    (`arbutus_s3/datalad_s3_setup.md`, `scripts/create_github_sibling.sh`,
    `workflows/common_errors.md`).
- Updated `docs/guides/public-data-mirror-runbook.rst` to document explicit
  Arbutus S3 special-remote setup:
  - `git annex initremote arbutus-s3 ...`
  - `datalad create-sibling-github --publish-depends arbutus-s3 ...`
  - `datalad push --to origin`
- Added recovery note for clone/get issues:
  `git annex enableremote arbutus-s3`.
- Updated `planning/femic_public_data_datalad_bootstrap.md` to track the KB
  source material and standardized remote terminology (`Arbutus S3`).

## 2026-03-11 - Added repo-local Arbutus credentials template
- Added credentials template:
  `config/credentials/arbutus_env.template.sh`.
- Updated `.gitignore` to ignore concrete credentials under
  `config/credentials/*.sh` while preserving tracked template files
  (`!config/credentials/*.template.sh`).
- Updated DataLad mirror docs/bootstrap instructions to use:
  - `cp config/credentials/arbutus_env.template.sh config/credentials/arbutus_env.sh`
  - `source config/credentials/arbutus_env.sh`
  before running `git annex initremote` / `datalad` publish steps.

## 2026-03-11 - Completed P10.6b DataLad mirror publish + Arbutus upload
- Confirmed published dataset repository:
  `https://github.com/UBC-FRESH/femic-public-data`.
- Confirmed `arbutus-s3` special-remote object presence for mirrored seed
  artifacts, including:
  - `data/misc.thlb.tif`
  - `data/bc/vri/2019/VEG_COMP_LYR_R1_POLY.gdb/a00000009.gdbtable`
- Backfilled `sha256` checksum values in `metadata/required_datasets.yaml` for
  all current mirror-scope datasets (`datalad_mirror.include=true`).
- Added explicit checksum methodology note for directory artifacts (`*.gdb`):
  deterministic tar-stream SHA256.
- Updated roadmap state:
  - marked `P10.6b` complete,
  - marked parent `P10.6` complete.

## 2026-03-11 - Completed P10.4a canonical maintainer reference instance
- Added canonical in-repo maintainer reference instance at:
  `instances/reference/`.
- Generated reference scaffold from current package templates via:
  `femic instance init --instance-root instances/reference --no-download-bc-vri --yes`.
- Updated deployment-instance guide with a dedicated section documenting
  `instances/reference/` usage and refresh command.
- Added docs contract test coverage requiring:
  - `instances/reference/` path presence,
  - expected scaffold files (`run_profile.case_template.yaml`,
    `template.case.yaml`, `QUICKSTART.md`),
  - deployment guide mention of `instances/reference/`.
- Updated roadmap state:
  - marked `P10.4a` complete,
  - left `P10.4b/P10.4c` pending.

## 2026-03-11 - Completed P10.4b docs/tests/examples repoint to instance layout
- Repointed maintainer-facing workflow docs to the canonical in-repo reference
  instance:
  - `docs/guides/case-onboarding.rst`
  - `docs/guides/pipeline-overview.rst`
  - `docs/reference/run-config.rst`
- Updated README onboarding/run-config examples to use
  `instances/reference/config/...` paths.
- Updated template-instantiation and docs-contract tests to use/reference the
  canonical `instances/reference/` layout:
  - `tests/test_case_preflight_cli.py`
  - `tests/test_docs_contract.py`
- Updated roadmap state:
  - marked `P10.4b` complete,
  - left `P10.4c` pending.

## 2026-03-11 - Completed P10.4c repo-path coupling contract enforcement
- Removed remaining active repo-root-coupled deployment wording:
  - `README.md` external-data note now describes instance-root-relative
    behavior.
  - `docs/sample-models/k3z.rst` now uses workspace-root phrasing.
- Added docs/config contract test coverage in `tests/test_docs_contract.py`
  preventing reintroduction of:
  - `repository root`
  - `repo root`
  - host-specific `/home/gep/projects/` deployment path references
- Updated roadmap state:
  - marked `P10.4c` complete,
  - marked parent `P10.4` complete.

## 2026-03-11 - Completed P10.5a package build/release checks
- Added CI workflow:
  `.github/workflows/package-release-checks.yml` with:
  - `python -m build`
  - `twine check dist/*`
  - wheel-install smoke (`femic --help`, `femic instance init ...`)
- Added README maintainer instructions for running the same checks locally.
- Fixed package runtime metadata by expanding `pyproject.toml` dependencies so
  wheel installs are executable (resolved smoke-failure on missing `numpy` and
  related runtime imports).
- Added contract test in `tests/test_docs_contract.py` requiring packaging
  workflow presence and key command coverage.
- Updated roadmap state:
  - marked `P10.5a` complete,
  - left `P10.5b/P10.5c` pending.

## 2026-03-11 - Completed P10.5b installed-package preflight verification
- Extended `.github/workflows/package-release-checks.yml` with a clean-env
  installed-wheel preflight smoke:
  - `pip install dist/*.whl`
  - `femic instance init ...`
  - `femic prep validate-case ...`
- Added workflow fixture setup for deterministic preflight execution in CI:
  - minimal instance-local required files/directories (`data/*`,
    `vdyp_io/VDYP_CFG`, `VDYP7/VDYP7/VDYP7Console.exe`),
  - minimal TIPSY config + run profile,
  - mock `wine` on `PATH`,
  - external dataset tree via `FEMIC_EXTERNAL_DATA_ROOT`.
- Extended docs contract checks in `tests/test_docs_contract.py` to require
  installed-package preflight coverage in the packaging workflow.
- Updated roadmap state:
  - marked `P10.5b` complete,
  - left `P10.5c` pending.

## 2026-03-11 - Completed P10.5c install-instance-run docs finalization
- Updated README quickstart to document installed-package-first workflow:
  `python -m pip install femic` -> `femic instance init` -> `femic run ...`.
- Updated guide command examples to use installed CLI commands as primary:
  - `docs/guides/deployment-instances.rst`
  - `docs/guides/case-onboarding.rst`
  - `docs/guides/pipeline-overview.rst`
- Added docs contract coverage in `tests/test_docs_contract.py` to require
  installed-package workflow guidance in README and key guides.
- Updated roadmap state:
  - marked `P10.5c` complete,
  - marked parent `P10.5` complete.

## 2026-03-11 - Completed P8.6d K3Z regenerated strata/AU plot rollout
- Added user-facing K3Z docs section:
  `Regenerated Strata/AU Build Plots` in
  `docs/sample-models/k3z.rst`.
- Documented required regenerated plot artifacts for teaching/release review:
  - `plots/strata-tsak3z.png`
  - `plots/vdyp_lmh_tsak3z-*.png`
  - `plots/tipsy_vdyp_tsak3z-*.png`
- Updated K3Z release-readiness checklist to require regenerated plot presence.
- Extended docs contract checks in `tests/test_docs_contract.py` to enforce:
  - presence of the new K3Z section,
  - presence of the three plot artifact references.
- Updated roadmap state:
  - marked `P8.6d` complete,
  - marked parent `P8.6` complete.

## 2026-03-11 - Normalized P8.3 parent status
- Marked parent `P8.3` complete in roadmap because all child items
  (`P8.3a`, `P8.3b`, `P8.3c`) were already complete.

## 2026-03-11 - Normalized P10.1/P10.2/P10.3 parent statuses
- Marked roadmap parent items `P10.1`, `P10.2`, and `P10.3` complete because
  all corresponding child tasks were already complete.

## 2026-03-11 - Completed Phase 11 K3Z standalone instance repository + submodule linkback
- Published new public K3Z example instance repository:
  `https://github.com/UBC-FRESH/femic-k3z-instance`
  with initial baseline tag `v0.1.0`.
- Added FEMIC submodule linkage for canonical pull-through access:
  `external/femic-k3z-instance`
  (tracked in `.gitmodules` on `branch = main`).
- Added planning contract note documenting include/exclude rules, provenance,
  update cadence, and operator update workflow:
  `planning/femic_k3z_instance_repo_contract.md`.
- Updated docs to wire the new canonical K3Z instance source:
  - `docs/guides/deployment-instances.rst`
  - `docs/guides/case-onboarding.rst`
  - `docs/sample-models/k3z.rst`
- Added docs contract checks in `tests/test_docs_contract.py` requiring:
  - `UBC-FRESH/femic-k3z-instance` mention,
  - `external/femic-k3z-instance` mention,
  - submodule init/update command coverage.
- Completed acceptance validation flow for linkage and docs-contract gates.

## 2026-03-11 - Fixed K3Z treated species-account alias loss (`FD` -> `FDC`)
- Fixed treated species-proportion assembly in
  `src/femic/pipeline/bundle.py` by normalizing legacy TIPSY species codes to
  canonical FEMIC species codes before writing bundle curves.
- Added alias handling:
  - `FD` maps to `FDC` (with additive merge behavior if canonical code is also
    present).
- Added regression coverage in `tests/test_bundle.py`:
  - `test_build_bundle_tables_from_curves_maps_tipsy_fd_to_fdc`
- Rebuilt K3Z post-TIPSY bundle and Patchworks export and verified affected
  AU curves now carry non-zero `FDC` where source TIPSY species mix contains
  non-zero `FD`.

## 2026-03-11 - Archived legacy notebooks out of repo root
- Moved legacy notebooks from repository root into dedicated archive folder:
  - `00_data-prep.ipynb`
  - `01a_run-tsa.ipynb`
  - `01b_run-tsa.ipynb`
  -> `reference/legacy_notebooks/`
- Updated docs and contract tests to follow the new archive location:
  - `docs/guides/legacy-traceability.rst`
  - `docs/guides/index.rst`
  - `tests/test_docs_contract.py`
- Verified all quality gates remain passing after relocation (`ruff`, `mypy`,
  `pytest`, `pre-commit`, `sphinx -W`).

## 2026-03-11 - Added Phase 12 roadmap plan for relocated K3Z validation + docs program
- Expanded `ROADMAP.md` with new `Phase 12` to cover:
  - relocated K3Z Patchworks rebuild validation (`P12.1`),
  - bugfix/regression verification after matrix rebuild (`P12.2`),
  - standalone `femic-k3z-instance` Sphinx scaffolding and publishing (`P12.3`),
  - TSR-style K3Z user-guide expansion (`P12.4`),
  - cross-project FRESH lab Sphinx template alignment using FHOPS as
    canonical reference (`P12.5`),
  - docs ownership/update cadence/release policy (`P12.6`).
- Appended matching detailed next-steps roadmap note so the leading execution
  plan now reflects this new docs and validation workstream.

## 2026-03-11 - Ran relocated K3Z Patchworks compile flow (Phase 12 `P12.1a/P12.1b`)
- Added instance-local Patchworks runtime config:
  `external/femic-k3z-instance/config/patchworks.runtime.windows.yaml`.
- Executed on Windows native runtime against relocated K3Z instance:
  - `femic patchworks preflight`
  - `femic patchworks build-blocks`
  - `femic patchworks matrix-build`
- Captured run logs/manifests under:
  `external/femic-k3z-instance/vdyp_io/logs/`
  (run ids: `k3z_relocated_20260311`, `k3z_relocated_20260311b`).
- Confirmed matrix manifest success and `protoaccounts.csv -> accounts.csv`
  sync/backup behavior.
- Recorded remaining structural drift for follow-up under `P12.2`.

## 2026-03-11 - Added cross-platform `fiona`/`GDAL` bootstrap planning to roadmap
- Extended `Phase 12` with `P12.7` to address geospatial dependency reliability
  across Linux and Windows local `.venv` bootstraps.
- Added concrete subtasks for:
  - OS-specific validated install rituals (`P12.7a`),
  - runtime/bootstrap OS detection and branching (`P12.7b`),
  - geospatial preflight checks (`P12.7c`),
  - Windows remediation runbook coverage (`P12.7d`).

## 2026-03-11 - Added Phase 13 roadmap for reproducible instance rebuild enforcement
- Added `Phase 13: Instance Rebuild Repro Framework (Default for All New Instances)` to `ROADMAP.md`.
- Added detailed task/subtask structure covering:
  - canonical rebuild contract definition,
  - first-class rebuild orchestration + reporting,
  - per-instance rebuild spec templates,
  - regression guardrails (invariants + baselines + allowlisted deltas),
  - user-facing docs and runbooks,
  - enforcement as default policy for all new FEMIC instance projects.
- Added matching `Detailed Next Steps Notes` entry tying this phase to immediate implementation sequencing.

## 2026-03-11 - Added deterministic K3Z rebuild evidence + baseline regression checks
- Fixed and expanded `scripts/k3z/rebuild_k3z_instance.py` so it now:
  - runs full relocated K3Z rebuild sequence,
  - writes a machine-readable rebuild report,
  - records key artifact timestamps,
  - enforces invariants for managed-area, block joins, seral accounts, and
    required managed species yields,
  - compares structural `tracks/*.csv` outputs against a baseline snapshot.
- Added baseline file: `scripts/k3z/k3z_tracks_baseline.json`.
- Executed reproducibility runs:
  - `k3z_reprocheck_20260311_2` (baseline initialization),
  - `k3z_reprocheck_20260311_3` (baseline comparison pass),
  - `k3z_reprocheck_20260311_4` (repeat pass after UTC warning cleanup).
- Latest run evidence (`k3z_reprocheck_20260311_4`) confirms:
  - `managed_area_ha = 1781.3132360577583`,
  - `passive_area_ha = 0.0`,
  - `block_join_csv_only = 0`, `block_join_shp_only = 0`,
  - `seral_account_count = 75`,
  - `baseline_match = true`.
- Added explicit roadmap follow-up (`P12.2d`) to validate `PL` vs `PLC`
  semantics and trim `PL` outputs if they are not valid for current K3Z inputs.

## 2026-03-11 - Standardized curve-source terminology to untreated/treated
- Added and completed roadmap work item `P12.8` to normalize curve-source
  terminology across active FEMIC source/docs.
- Replaced curve-source naming in code/tests/docs from legacy terms to
  `untreated/treated`, including:
  - bundle columns: `untreated_curve_id` / `treated_curve_id`,
  - curve types: `untreated` / `treated`,
  - species-proportion curve types:
    `untreated_species_prop_<SPP>` / `treated_species_prop_<SPP>`.
- Kept IFM semantics unchanged as `managed/unmanaged`.
- Updated operator/user docs language to align with the new terminology.

## 2026-03-11 - Completed K3Z PL vs PLC cleanup (`P12.2d`)
- Verified current K3Z treated species composition has signal for `PLC` but not
  `PL`.
- Updated Patchworks export assembly to omit zero-signal species accounts so
  empty managed species boxes (for `PL`) are not emitted when no species-prop
  signal exists.
- Confirmed K3Z rebuild regression checks still pass after this change.

## 2026-03-11 - Added standalone Sphinx scaffold for femic-k3z-instance (P12.3a)
- Created standalone K3Z instance docs scaffold inside
  `external/femic-k3z-instance`:
  - `docs/conf.py`, `docs/index.rst`, `docs/getting-started.rst`,
    `docs/model-anatomy.rst`, `docs/rebuild-and-qa.rst`,
    `docs/troubleshooting.rst`, `docs/requirements.txt`.
- Added standalone docs publishing/build config in submodule:
  - `.readthedocs.yaml`
  - `.github/workflows/docs-pages.yml`
- Updated submodule `.gitignore` for docs build output and added README docs
  build instructions.
- Added parent repository docs contract test
  (`tests/test_docs_contract.py`) requiring K3Z standalone docs scaffold
  existence and key navigation entries.
- Submodule docs commit pushed to `UBC-FRESH/femic-k3z-instance`:
  `6c61c71`.
- Validation gates run:
  - K3Z standalone docs build:
    `python -m sphinx -b html docs docs/_build/html -W`
  - FEMIC main repo gates:
    `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest`,
    `pre-commit run --all-files`, `python -m sphinx -b html docs _build/html -W`.

## 2026-03-11 - Published K3Z docs and aligned FEMIC docs to RTD theme deps
- Verified `femic-k3z-instance` GitHub Pages docs are online at:
  `https://ubc-fresh.github.io/femic-k3z-instance/` (`docs-pages` deploy success).
- Added FEMIC docs dependency manifest:
  - `docs/requirements.txt` with `sphinx>=7.0` and `sphinx-rtd-theme>=2.0`.
- Updated FEMIC docs workflow (`.github/workflows/docs-pages.yml`) to install
  docs dependencies from `docs/requirements.txt` so published FEMIC docs use
  the same Read the Docs theme baseline.

## 2026-03-11 - Added standalone K3Z docs acceptance checks (P12.3c)
- Expanded docs-contract coverage in `tests/test_docs_contract.py` to enforce
  required standalone K3Z docs navigation and section content under
  `external/femic-k3z-instance/docs/`.
- New checks require:
  - guide toctree structure in `docs/index.rst`,
  - required headings and command snippets in `docs/getting-started.rst`,
  - required anatomy/edit-policy sections in `docs/model-anatomy.rst`,
  - required reproducibility sections and rebuild-script reference in
    `docs/rebuild-and-qa.rst`,
  - required troubleshooting topics in `docs/troubleshooting.rst`.

## 2026-03-11 - Amended Phase 12 roadmap for TSR-grade K3Z data-package docs
- Refined `P12.4` scope to explicitly target BC small-unit timber supply
  data-package structure/depth quality.
- Added concrete roadmap subtasks:
  - `P12.4d` exemplar section crosswalk (`TFL26`, `CFA`, `FNWL`),
  - `P12.4e` standalone K3Z data-package page set,
  - `P12.4f` evidence/provenance table requirements,
  - `P12.4g` student usability acceptance content requirements,
  - `P12.4h` publication acceptance criteria (`-W` build, docs-contract,
    GitHub Pages verification).
- Added `P12.5e` to ensure FHOPS template alignment preserves BC data-package
  depth expectations.
- Added matching `ROADMAP.md` detailed next-steps note with locked execution
  sequence:
  `P12.4d -> P12.4e -> P12.4f -> P12.4g -> P12.4h`.

## 2026-03-11 - Added TSR-style K3Z standalone data-package docs (`P12.4d/e/f/g`)
- Added standalone K3Z docs pages in `external/femic-k3z-instance/docs/`:
  - `data-package-crosswalk.rst`
  - `land-base-and-netdown.rst`
  - `assumptions-registry.rst`
  - `base-case-analysis.rst`
- Wired the new pages into standalone docs navigation via
  `external/femic-k3z-instance/docs/index.rst`.
- Added docs-contract checks in `tests/test_docs_contract.py` to enforce:
  - exemplar crosswalk coverage and references (`TFL26`, `CFA`, `FNWL`),
  - required TSR-style section headings,
  - provenance table columns (`Update Date`, `Source Path/URL`,
    `Transform Stage`, `QA Status`),
  - operator-facing usability sections (`What to Edit vs Regenerate`,
    `How to Validate Reruns`).
- Marked roadmap tasks complete: `P12.4d`, `P12.4e`, `P12.4f`, `P12.4g`
  (with `P12.4h` remaining as publish acceptance verification).

## 2026-03-11 - Completed `P12.4h` publish acceptance verification
- Verified standalone `femic-k3z-instance` docs build with warnings-as-errors:
  `python -m sphinx -b html docs docs/_build/html -W`.
- Verified docs-contract coverage for required TSR-style sections/provenance
  and operator usability content in `tests/test_docs_contract.py`.
- Verified published GitHub Pages deployment and live nav for new pages:
  - run `22981643203` (`success`)
  - `https://ubc-fresh.github.io/femic-k3z-instance/`

## 2026-03-11 - Completed `P12.4a/P12.4b/P12.4c` TSR core docs buildout
- Added standalone K3Z metadata/lineage page:
  `external/femic-k3z-instance/docs/metadata-and-lineage.rst`.
- Added standalone K3Z operator runbook page:
  `external/femic-k3z-instance/docs/operator-runbook.rst`.
- Added standalone K3Z edit-policy/scenario guidance page:
  `external/femic-k3z-instance/docs/edit-policy-and-scenarios.rst`.
- Wired all three pages into standalone docs navigation in
  `external/femic-k3z-instance/docs/index.rst`.
- Extended parent docs-contract tests (`tests/test_docs_contract.py`) to
  require these pages and their key section headings.
- Marked roadmap items complete: `P12.4a`, `P12.4b`, `P12.4c`.

## 2026-03-11 - Decoupled standalone K3Z docs from parent-repo path assumptions
- Removed parent-repo file/path references from standalone
  `femic-k3z-instance` docs (for example `scripts/k3z/...` and `reference/...`)
  and replaced them with instance-local FEMIC command workflows plus generic
  exemplar citations.
- Updated standalone docs pages:
  `rebuild-and-qa.rst`, `operator-runbook.rst`, `data-package-crosswalk.rst`,
  `assumptions-registry.rst`, `base-case-analysis.rst`,
  `metadata-and-lineage.rst`.
- Added parent docs-contract guard in `tests/test_docs_contract.py`:
  `test_k3z_standalone_docs_do_not_reference_parent_repo_paths`.

## 2026-03-11 - Completed FHOPS-aligned Sphinx template consistency (`P12.5`)
- Added canonical baseline guide:
  `docs/guides/sphinx-template-baseline.rst` and linked it from
  `docs/guides/index.rst`.
- Aligned FEMIC and standalone K3Z Sphinx configs with shared template
  settings:
  - `autodoc_typehints = "description"`
  - RTD theme options (`collapse_navigation=False`, `navigation_depth=3`)
  - `templates_path = ["_templates"]`
- Aligned standalone docs Pages workflow to current baseline:
  Node24 env flag, `configure-pages`, `upload-pages-artifact@v4`,
  deploy gating parity.
- Added docs-contract checklist test:
  `test_fhops_aligned_sphinx_template_contract`.
- Preserved K3Z TSR data-package depth requirements via existing contract tests.

## 2026-03-11 - Operationalized K3Z docs ownership + release workflow (`P12.6`)
- Added standalone K3Z docs governance page:
  `external/femic-k3z-instance/docs/docs-ownership-and-release.rst`.
- Wired the page into standalone docs navigation via:
  `external/femic-k3z-instance/docs/index.rst`.
- Documented:
  - ownership matrix (primary/backup owners by docs area),
  - refresh cadence (rebuild/monthly/quarterly/event-driven),
  - release tagging/versioning policy for docs + model snapshots,
  - contributor onboarding and review checklist.
- Extended parent docs-contract tests (`tests/test_docs_contract.py`) to
  require the governance page and core headings.

## 2026-03-11 - Completed geospatial bootstrap hardening (`P12.7`)
- Added OS-aware geospatial preflight module:
  `src/femic/geospatial_preflight.py`.
  - Detects host OS family and emits platform-specific Fiona/GDAL install hints.
  - Checks Fiona importability, GDAL version visibility, and shapefile I/O smoke.
- Added CLI command:
  `femic prep geospatial-preflight` with options
  `--strict-warnings` and `--skip-shapefile-smoke`.
- Updated `femic instance init` to emit geospatial readiness/install guidance
  when Fiona/GDAL are not yet available.
- Added geospatial bootstrap guide:
  `docs/guides/geospatial-runtime-bootstrap.rst` and linked it from
  `docs/guides/index.rst`.
- Updated docs references:
  `docs/guides/deployment-instances.rst`,
  `docs/reference/cli.rst`, and instance template
  `src/femic/resources/instance/QUICKSTART.md`.
- Added tests:
  `tests/test_geospatial_preflight.py`,
  CLI coverage updates in `tests/test_cli_main.py`,
  docs-contract coverage in `tests/test_docs_contract.py`.

## 2026-03-11 - Defined canonical instance rebuild contract (`P13.1`)
- Added canonical human-readable rebuild contract:
  `planning/femic_instance_rebuild_contract.md`.
- Added machine-readable contract artifact:
  `planning/femic_instance_rebuild_contract.v1.yaml`.
- Contract now explicitly defines:
  - required inputs/config/runtime prerequisites,
  - authoritative rebuild step sequence and expected outputs,
  - required post-rebuild invariants,
  - failure classes and remediation message requirements.
- Added docs-contract test coverage in `tests/test_docs_contract.py` to enforce
  contract artifact presence and required schema/section keys.
- Linked pipeline guide primary sources to the rebuild contract doc in
  `docs/guides/pipeline-overview.rst`.

## 2026-03-11 - Added deterministic rebuild runner abstraction (`P13.2a`)
- Added reusable rebuild orchestration module:
  `src/femic/rebuild_runner.py`.
- New primitives:
  - `RebuildStep` (step definition + dependencies),
  - `RebuildRunner` (deterministic dependency-ordered execution),
  - `StepOutcome` / `RebuildExecutionReport` (machine-readable execution report),
  - `JsonRebuildReportSink` (report artifact persistence).
- Runner behavior supports:
  - deterministic topological ordering,
  - configurable stop-on-failure or continue-on-failure execution,
  - explicit error capture per step.
- Added regression/unit coverage in `tests/test_rebuild_runner.py`:
  deterministic order, failure modes, report sink writing, unknown dependency
  rejection, and cycle detection.

## 2026-03-11 - Added CLI instance rebuild execution (`P13.2b`)
- Added new CLI command:
  `femic instance rebuild` in `src/femic/cli/main.py`.
- Command executes deterministic non-interactive rebuild steps via
  `RebuildRunner` with dependency ordering:
  case preflight, geospatial preflight, upstream compile, post-TIPSY bundle,
  and optional Patchworks preflight + matrix build.
- Added run-id and instance-root support for rebuild execution:
  `--run-id`, `--instance-root`, and optional `--with-patchworks`.
- Added machine-readable report output path:
  `vdyp_io/logs/instance_rebuild_report-<run_id>.json`.
- Updated tests:
  `tests/test_cli_main.py` and `tests/test_docs_contract.py`.
- Updated docs:
  `docs/reference/cli.rst` and `docs/guides/pipeline-overview.rst`.

## 2026-03-11 - Added rebuild report artifact references (`P13.2c`)
- Extended `femic instance rebuild` report handling to include explicit
  artifact references for generated manifests/logs.
- Added helper in `src/femic/cli/main.py`:
  `_collect_rebuild_artifact_references(log_dir, run_id)`.
- Rebuild reports (`instance_rebuild_report-<run_id>.json`) now include
  `artifact_references` with discovered:
  - run manifests,
  - Patchworks manifests,
  - Patchworks stdout/stderr logs,
  - rebuild report file.
- Added regression coverage:
  `tests/test_cli_main.py::test_collect_rebuild_artifact_references_filters_missing`.
- Updated CLI docs in `docs/reference/cli.rst`.

## 2026-03-11 - Added instance rebuild dry-run planning mode (`P13.2d`)
- Added `--dry-run` to `femic instance rebuild`.
- Dry-run prints full planned step sequence (including dependency ordering),
  run-id, and report path, and exits without executing rebuild mutations.
- Added regression coverage:
  `tests/test_cli_main.py::test_instance_rebuild_dry_run_prints_plan_without_execution`.
- Updated CLI docs/contract checks:
  `docs/reference/cli.rst`, `tests/test_docs_contract.py`.

## 2026-03-11 - Defined rebuild spec schema (`P13.3a`)
- Added standard YAML schema artifact:
  `planning/femic_instance_rebuild_spec_schema.v1.yaml`.
- Schema now defines required root structure for instance rebuild specs:
  `schema_version`, `instance`, `runtime`, `steps`, and `invariants`.
- Standardized step and invariant field structure/constraints (for example
  `step_id`, `kind`, dependency lists, invariant comparator/severity fields).
- Linked schema from canonical contract doc:
  `planning/femic_instance_rebuild_contract.md`.
- Added docs-contract enforcement:
  `tests/test_docs_contract.py::test_instance_rebuild_spec_schema_artifact_is_present_and_structured`.

## 2026-03-11 - Shipped default rebuild spec template in instance init (`P13.3b`)
- Added default rebuild-spec template:
  `src/femic/resources/instance/config/rebuild.spec.yaml`.
- Updated instance bootstrap template list so `femic instance init` writes:
  `config/rebuild.spec.yaml` for every new instance workspace.
- Updated instance quickstart template:
  `src/femic/resources/instance/QUICKSTART.md`.
- Updated deployment docs:
  `docs/guides/deployment-instances.rst`.
- Updated test/contracts:
  `tests/test_instance_bootstrap.py`,
  `tests/test_docs_contract.py`.

## 2026-03-11 - Added K3Z reference rebuild spec (`P13.3c`)
- Added K3Z rebuild-spec source-of-truth:
  `external/femic-k3z-instance/config/rebuild.spec.yaml`.
- Backfilled known-valid K3Z command sequence and baseline invariants into this
  spec (case preflight, geospatial preflight, compile/post-TIPSY, Patchworks
  preflight/build-blocks/matrix-build).
- Updated standalone K3Z docs/README to reference the rebuild spec as the
  primary authority:
  `external/femic-k3z-instance/docs/rebuild-and-qa.rst`,
  `external/femic-k3z-instance/README.md`.
- Added contract checks in parent repo:
  `tests/test_docs_contract.py` now requires K3Z rebuild-spec presence and
  validates core schema-aligned fields and required step IDs.

## 2026-03-11 - Added rebuild-spec schema validation diagnostics (`P13.3d`)
- Added rebuild-spec validation module:
  `src/femic/rebuild_spec.py`.
- `femic instance rebuild` now validates `--spec` (default:
  `config/rebuild.spec.yaml`) before execution and prints clear field-level
  diagnostics for malformed specs.
- Added explicit validation command:
  `femic instance validate-spec --spec <path>`.
- Added tests:
  `tests/test_rebuild_spec.py`,
  `tests/test_cli_main.py` (validation diagnostics path),
  `tests/test_docs_contract.py` (CLI contract coverage).
- Updated CLI docs:
  `docs/reference/cli.rst`.

## 2026-03-11 - Added rebuild invariant guardrails for known-risk dimensions (`P13.4a`)
- Added rebuild invariant metric/evaluation module:
  `src/femic/rebuild_invariants.py`.
- `femic instance rebuild` now:
  - computes post-run metrics for managed area, managed species yield-account
    presence, seral account presence, topology edge count, and block-join
    mismatch detection from matrix-builder logs,
  - evaluates configured spec invariants against those metrics,
  - prints pass/warn/fail invariant summaries with remediation hints,
  - fails with exit code `1` on any `severity: fatal` invariant regression.
- Rebuild report payloads now include:
  - `metrics`,
  - `invariant_results`.
- Added tests:
  `tests/test_rebuild_invariants.py`.
- Updated CLI reference docs:
  `docs/reference/cli.rst`.

## 2026-03-11 - Added baseline snapshot/diff support for rebuild outputs (`P13.4b`)
- Added baseline snapshot module:
  `src/femic/rebuild_baseline.py`.
- Added structural snapshot support for key track tables and ForestModel XML
  shape counts, including JSON save/load and diff utilities.
- `femic instance rebuild` now supports:
  - `--baseline PATH` (baseline JSON location),
  - `--write-baseline` (initialize/update baseline),
  - report-level `baseline` payload output with diff details.
- Rebuild metrics now include:
  - `baseline_match`,
  - `baseline_diff_count`.
- Added tests:
  `tests/test_rebuild_baseline.py`, plus CLI/docs contract updates in
  `tests/test_cli_main.py` and `tests/test_docs_contract.py`.

## 2026-03-11 - Added baseline diff allowlist mechanism (`P13.4c`)
- Added allowlist parsing/filtering helpers in:
  `src/femic/rebuild_baseline.py`
  (`load_diff_allowlist`, `apply_diff_allowlist`).
- `femic instance rebuild` now supports:
  - `--allowlist PATH` (default `config/rebuild.allowlist.yaml`),
  - `baseline_allowlist_match` and `baseline_unexpected_diff_count` metrics.
- Rebuild report baseline payload now includes:
  - allowlist path/payload,
  - filtered unexpected diff summary.
- Added default allowlist templates:
  `src/femic/resources/instance/config/rebuild.allowlist.yaml` and
  `instances/reference/config/rebuild.allowlist.yaml`.
- Updated instance scaffold/quickstart to include allowlist by default.
- Added/updated tests:
  `tests/test_rebuild_baseline.py`,
  `tests/test_instance_bootstrap.py`,
  `tests/test_cli_main.py`,
  `tests/test_docs_contract.py`.

## 2026-03-11 - Added fail-fast regression gate for unexpected diffs (`P13.4d`)
- `femic instance rebuild` now fails when
  `baseline_unexpected_diff_count` exceeds
  `runtime.baseline_unexpected_diff_threshold` (default `0`).
- Added explicit remediation summary output when this gate trips:
  review allowlist results, update tracked allowlist, or regenerate baseline.
- Rebuild reports now include a `regression_gate` section capturing:
  - step failure status,
  - fatal invariant failure status,
  - baseline unexpected-diff threshold evaluation status.
- Updated rebuild-spec schema/template docs:
  `planning/femic_instance_rebuild_spec_schema.v1.yaml`,
  `src/femic/resources/instance/config/rebuild.spec.yaml`,
  `instances/reference/config/rebuild.spec.yaml`.
- Added regression test:
  `tests/test_cli_main.py::test_instance_rebuild_fails_when_unexpected_diffs_exceed_threshold`.

## 2026-03-11 - Added Rebuild Repro Contract guide (`P13.5a`)
- Added new user-facing guide page:
  `docs/guides/rebuild-repro-contract.rst`.
- Guide now documents:
  - what the rebuild repro contract is and why it exists,
  - authoritative contract/schema source files,
  - expected operator workflow,
  - required rebuild evidence artifacts,
  - failure-class expectations.
- Added guide to navigation:
  `docs/guides/index.rst`.
- Added docs-contract test coverage:
  `tests/test_docs_contract.py::test_rebuild_repro_contract_guide_covers_core_sections`.

## 2026-03-11 - Added rebuild-spec authoring guide with copy-ready examples (`P13.5b`)
- Added new guide:
  `docs/guides/author-instance-rebuild-spec.rst`.
- Guide includes:
  - required spec structure,
  - minimal copy-ready YAML example,
  - step/invariant authoring rules,
  - K3Z reference-spec pointer,
  - dry-run and full rebuild command examples.
- Updated docs navigation/linking:
  `docs/guides/index.rst`,
  `docs/guides/rebuild-repro-contract.rst`.
- Added docs-contract test coverage:
  `tests/test_docs_contract.py::test_author_instance_rebuild_spec_guide_covers_core_sections`.

## 2026-03-11 - Added rebuild report interpretation and triage guide (`P13.5c`)
- Added new guide:
  `docs/guides/interpret-rebuild-reports.rst`.
- Guide now covers:
  - report location and top-level payload structure,
  - step outcome interpretation,
  - invariant result interpretation,
  - baseline/allowlist diff interpretation,
  - regression-gate semantics and triage workflow.
- Updated docs navigation/linking:
  `docs/guides/index.rst`,
  `docs/guides/rebuild-repro-contract.rst`.
- Added docs-contract test coverage:
  `tests/test_docs_contract.py::test_interpret_rebuild_reports_guide_covers_core_sections`.

## 2026-03-11 - Added mandatory contributor policy for new instance repos (`P13.5d`)
- Added explicit contributor policy section to:
  `docs/guides/rebuild-repro-contract.rst`.
- Policy now requires for new instance repositories:
  - tracked `config/rebuild.spec.yaml`,
  - tracked `config/rebuild.allowlist.yaml`,
  - `femic instance validate-spec` in QA,
  - `femic instance rebuild` checks before milestone closure,
  - retained rebuild evidence artifacts.
- Added matching baseline checklist section to:
  `docs/guides/deployment-instances.rst`.
- Added docs-contract enforcement:
  `tests/test_docs_contract.py::test_contributor_policy_requires_rebuild_spec_and_checks`.

## 2026-03-11 - Added rebuild runbook placeholders to instance scaffolding (`P13.6a`)
- Extended instance bootstrap templates in:
  `src/femic/instance_bootstrap.py` to include
  `runbooks/REBUILD_RUNBOOK.md`.
- Added scaffolded placeholder file:
  `src/femic/resources/instance/runbooks/REBUILD_RUNBOOK.md`.
- Synced maintainer reference instance scaffold:
  `instances/reference/runbooks/REBUILD_RUNBOOK.md`.
- Updated bootstrap docs:
  `src/femic/resources/instance/QUICKSTART.md`,
  `docs/guides/deployment-instances.rst`.
- Added/updated tests:
  `tests/test_instance_bootstrap.py`,
  `tests/test_docs_contract.py`.

## 2026-03-11 - Enforced rebuild-spec references in sample/new instance docs (`P13.6b`)
- Updated docs content to explicitly reference rebuild control artifacts:
  - `docs/sample-models/k3z.rst`,
  - `docs/guides/case-onboarding.rst`.
- Required references now include:
  - `config/rebuild.spec.yaml`,
  - `config/rebuild.allowlist.yaml`,
  - `runbooks/REBUILD_RUNBOOK.md`.
- Added docs-contract enforcement in:
  `tests/test_docs_contract.py` so these references remain mandatory.

## 2026-03-11 - Added reference-instance rebuild evidence release gate (`P13.6c`)
- Added tracked evidence artifact:
  `instances/reference/evidence/reference_rebuild_report.latest.json`.
- Added package-release workflow gate:
  `.github/workflows/package-release-checks.yml` now includes
  `Reference instance rebuild evidence gate` and enforces passing
  `regression_gate` fields.
- Updated deployment docs with evidence requirements:
  `docs/guides/deployment-instances.rst`.
- Added docs-contract coverage:
  `tests/test_docs_contract.py` now requires evidence artifact presence,
  release-workflow gate wiring, and passing evidence payload fields.

## 2026-03-11 - Added phase-closure policy requiring rebuild evidence (`P13.6d`)
- Added explicit Phase 13 closure policy in `ROADMAP.md`:
  no new instance phase closes without reproducible rebuild evidence.
- Added matching changelog policy milestone (this entry) to keep the policy
  auditable in both planning and historical records.

## 2026-03-11 - Normalized roadmap parent-status checkboxes
- Updated `ROADMAP.md` parent checklist items to `done` where all child items
  were already complete.
- Normalized parent statuses for:
  `P12.3`, `P12.4`, `P12.5`, `P13.3`, `P13.4`, `P13.5`, `P13.6`.

## 2026-03-11 - Added rebuild-evidence promotion CLI (`P14.1`)
- Added new command:
  `femic instance promote-evidence` in `src/femic/cli/main.py`.
- Command can ingest an explicit rebuild report (`--report`) or auto-select the
  latest `instance_rebuild_report-*.json` from `--log-dir`, then write a
  normalized evidence artifact to `--output`.
- Normalized payload now includes:
  `status`, `regression_gate`, invariant summary counts, and source report path.
- Updated docs and contract/test coverage:
  `docs/reference/cli.rst`,
  `tests/test_docs_contract.py`,
  `tests/test_cli_main.py`.

## 2026-03-11 - Added maintainer evidence-refresh helper (`P14.2a`)
- Added new command:
  `femic instance refresh-reference-evidence` in `src/femic/cli/main.py`.
- Command refreshes reference evidence using default maintainer paths:
  `instances/reference` root,
  `vdyp_io/logs` source,
  `evidence/reference_rebuild_report.latest.json` output.
- Updated docs and tests:
  `docs/reference/cli.rst`,
  `docs/guides/deployment-instances.rst`,
  `tests/test_cli_main.py`,
  `tests/test_docs_contract.py`.

## 2026-03-11 - Added contributor runbook evidence-refresh step (`P14.2b`)
- Updated runbook templates:
  `src/femic/resources/instance/runbooks/REBUILD_RUNBOOK.md`,
  `instances/reference/runbooks/REBUILD_RUNBOOK.md`.
- Added release-prep command step:
  `femic instance refresh-reference-evidence --reference-root .`
  plus required post-refresh evidence checks.
- Updated deployment guidance:
  `docs/guides/deployment-instances.rst`.
- Added docs-contract enforcement in:
  `tests/test_docs_contract.py`.

## 2026-03-11 - Added optional evidence trend-drift warning thresholds (`P14.3a`)
- Extended `femic instance promote-evidence` with:
  - `--max-warn-increase`,
  - `--max-baseline-diff-increase`.
- Evidence payloads now include `trend_drift` with:
  previous summary snapshot, computed deltas, configured thresholds, and
  warning messages when thresholds are exceeded.
- Propagated threshold options to:
  `femic instance refresh-reference-evidence`.
- Updated docs and test coverage:
  `docs/reference/cli.rst`,
  `docs/guides/deployment-instances.rst`,
  `tests/test_cli_main.py`,
  `tests/test_docs_contract.py`.

## 2026-03-11 - Added trend-drift interpretation guide coverage (`P14.3b`)
- Expanded `docs/guides/interpret-rebuild-reports.rst` with a dedicated
  "Evidence Trend Drift Across Releases" section.
- Added operator guidance for interpreting:
  `trend_drift.previous_summary`,
  `trend_drift.warn_increase`,
  `trend_drift.baseline_diff_increase`,
  threshold fields, and warning semantics.
- Added thresholded release workflow examples using:
  `femic instance refresh-reference-evidence --max-warn-increase ... --max-baseline-diff-increase ...`.
- Extended docs-contract checks in `tests/test_docs_contract.py` to enforce
  the new section and required drift markers.

## 2026-03-11 - Opened Phase 15 for K3Z species-account semantics hardening
- Added new roadmap phase:
  `Phase 15: K3Z Species-Account Semantics + Output Hygiene`.
- Added concrete task tree to:
  - resolve `PL` vs `PLC` account semantics for K3Z,
  - add rebuild invariants for species-account completeness,
  - add operator diagnostics for account-surface QA,
  - add required docs/contracts for species-account interpretation.
- Added detailed next-steps execution sequence in `ROADMAP.md`:
  `P15.1a -> P15.1b -> P15.1c -> P15.2a -> P15.2b -> P15.2c`.

## 2026-03-11 - Added protoaccounts exclusion support for species-surface hygiene (`P15.1a`)
- Audited current K3Z species surfaces and confirmed `PL` curves are currently
  zero-signal while `PLC` retains non-zero signal in
  `external/femic-k3z-instance/models/k3z_patchworks_model/yield/forestmodel.xml`.
- Extended Patchworks runtime config with optional:
  `matrix_builder.accounts_exclude_regex` (regex list) in
  `src/femic/patchworks_runtime.py`.
- During non-interactive matrix build, `protoaccounts -> accounts` promotion
  now supports row filtering by `ATTRIBUTE`/`ACCOUNT` regex match.
- Matrix-build manifest `accounts_sync` now records:
  `excluded_patterns` and `excluded_row_count`.
- Added regression coverage in `tests/test_patchworks_runtime.py` for:
  config parsing and regex-based account exclusion behavior.
- Updated operator docs in `docs/guides/patchworks-wine-runtime.rst`.

## 2026-03-11 - Applied K3Z `PL` exclusion policy and validated output (`P15.1b`)
- Updated K3Z instance runtime config:
  `external/femic-k3z-instance/config/patchworks.runtime.windows.yaml`
  with:
  `matrix_builder.accounts_exclude_regex: ["\\.PL(\\.|$)"]`.
- Re-ran matrix build for K3Z:
  `python -m femic patchworks matrix-build --config external/femic-k3z-instance/config/patchworks.runtime.windows.yaml --run-id k3z_plc_cleanup_20260312b`.
- Verified
  `external/femic-k3z-instance/models/k3z_patchworks_model/tracks/accounts.csv`
  no longer contains `.PL` account rows and retains `.PLC` account rows.
- Verified manifest evidence in
  `vdyp_io/logs/patchworks_matrixbuilder_manifest-k3z_plc_cleanup_20260312b.json`:
  `accounts_sync.excluded_patterns=["\\.PL(\\.|$)"]`,
  `accounts_sync.excluded_row_count=5`.

## 2026-03-11 - Added explicit student guidance for PL vs PLC semantics (`P15.1c`)
- Updated standalone K3Z docs:
  `external/femic-k3z-instance/docs/base-case-analysis.rst`
  with a dedicated `Species Code Note (PL vs PLC)` section.
- Updated FEMIC sample-model docs:
  `docs/sample-models/k3z.rst`
  with `Species Code Semantics: PL vs PLC`, including explicit interpretation
  guidance that missing `PL` account boxes are expected in K3Z.
- Added docs-contract enforcement in:
  `tests/test_docs_contract.py`
  requiring the PL/PLC semantics section/marker text in the sample-model page.

## 2026-03-11 - Added species-account completeness invariants (`P15.2a`)
- Extended rebuild invariant metrics with `accounts.list` in:
  `src/femic/rebuild_invariants.py`.
- Added invariant comparators:
  `contains`, `not_contains`
  in:
  `src/femic/rebuild_invariants.py`,
  `src/femic/rebuild_spec.py`,
  `planning/femic_instance_rebuild_spec_schema.v1.yaml`.
- Added tests for new metric/comparators in:
  `tests/test_rebuild_invariants.py`,
  `tests/test_rebuild_spec.py`.
- Added K3Z fatal invariants in:
  `external/femic-k3z-instance/config/rebuild.spec.yaml`
  requiring:
  `product.Yield.managed.PLC`,
  `product.HarvestedVolume.managed.PLC.CC`,
  and forbidding:
  `product.Yield.managed.PL`,
  `product.HarvestedVolume.managed.PL.CC`.
- Updated invariant authoring docs:
  `docs/guides/author-instance-rebuild-spec.rst`.

## 2026-03-11 - Added configurable species-account policy in rebuild specs (`P15.2b`)
- Added optional runtime policy block:
  `runtime.species_account_policy`
  with:
  `required_present` and `expected_absent` account lists.
- Added policy-to-invariant expansion in:
  `src/femic/rebuild_invariants.py`
  and wired it into:
  `src/femic/cli/main.py` (`femic instance rebuild`).
- Extended rebuild spec validation and schema in:
  `src/femic/rebuild_spec.py`,
  `planning/femic_instance_rebuild_spec_schema.v1.yaml`.
- Added regression coverage in:
  `tests/test_rebuild_invariants.py`,
  `tests/test_rebuild_spec.py`.
- Migrated K3Z to policy-based config in:
  `external/femic-k3z-instance/config/rebuild.spec.yaml`.
- Updated authoring guide:
  `docs/guides/author-instance-rebuild-spec.rst`.

## 2026-03-11 - Fixed wheel package-data omission for instance runbook template
- Added missing package-data include in `pyproject.toml`:
  `resources/instance/runbooks/*`.
- This restores wheel-install smoke behavior where
  `femic instance init` copies:
  `femic/resources/instance/runbooks/REBUILD_RUNBOOK.md`.
- Verified distribution build now contains the runbook resource in both sdist
  and wheel build outputs.

## 2026-03-11 - Enforced fail-fast species-account null regression gate (`P15.2c`)
- Added rebuild metric `products.nonzero_labels` computed from
  `tracks/products.csv` joined to `tracks/curves.csv` maxima in
  `src/femic/rebuild_invariants.py`.
- Extended runtime species-account policy invariants with:
  - `required_nonzero` (must appear in `products.nonzero_labels`)
  - `expected_zero` (must not appear in `products.nonzero_labels`)
- Rebuild gating impact:
  - `femic instance rebuild` now exits nonzero when these fatal policy checks
    fail, preventing silent species-wise null/zero regressions.
- Updated tests:
  - `tests/test_rebuild_invariants.py` (metric extraction + nonzero policy)
  - `tests/test_cli_main.py` (fatal invariant regression exits with code 1)
- Updated documentation/spec references:
  - `docs/guides/author-instance-rebuild-spec.rst`
  - `planning/femic_instance_rebuild_spec_schema.v1.yaml`

## 2026-03-11 - Scrubbed SPS username from docs/config/tests/manifests
- Replaced `frst424@auth.spatial.ca` with neutral example
  `sps_user@auth.spatial.ca` across tracked repository content.
- Updated affected areas:
  - FEMIC runtime config examples (`config/`, `instances/reference/`,
    `src/femic/resources/instance/config/`)
  - User docs (`docs/guides/patchworks-wine-runtime.rst`,
    `docs/guides/ubc-vpn-license-connectivity.rst`)
  - Patchworks runtime tests (`tests/test_patchworks_runtime.py`,
    `tests/test_cli_main.py`)
  - K3Z tracked manifests/config in `external/femic-k3z-instance/`.

## 2026-03-11 - Added account-surface QA diagnostics helper (`P15.3a`)
- Added new command:
  - `femic instance account-surface`
- Added account-surface summarizer:
  - `src/femic/account_surface.py`
  - summarizes account/target coverage proxies from `tracks/accounts.csv`:
    - species-level `product.Yield.managed.*` and
      `product.HarvestedVolume.managed.*.CC` presence,
    - AU-level `feature.Seral.*.<au>` and
      `product.Seral.area.*.<au>.CC` coverage.
- Added CLI wiring and JSON output support in:
  - `src/femic/cli/main.py`
- Added regression tests:
  - `tests/test_account_surface.py`
  - `tests/test_cli_main.py`
- Updated command reference docs:
  - `docs/reference/cli.rst`

## 2026-03-11 - Added deterministic species-empty troubleshooting flow (`P15.3b`)
- Extended account-surface diagnostics:
  - `src/femic/account_surface.py` now computes:
    `diagnosis.total_ok_species_empty_signature` and
    `diagnosis.recommended_next_checks`.
  - When `tracks/products.csv` + `tracks/curves.csv` are available,
    diagnostics now distinguishes account presence from nonzero label signal.
- Updated CLI behavior:
  - `src/femic/cli/main.py` prints explicit next-check steps when
    `total OK, species-wise empty` is detected.
- Updated troubleshooting docs:
  - `docs/guides/troubleshooting.rst`
  - `external/femic-k3z-instance/docs/troubleshooting.rst`
  - `docs/reference/cli.rst`
- Added tests:
  - `tests/test_account_surface.py`
  - `tests/test_cli_main.py`
  - `tests/test_docs_contract.py` (required troubleshooting snippets).

## 2026-03-12 - Wired account-surface diagnostics into rebuild evidence and closed Phase 15 (`P15.3c`, `P15.4`)
- `femic instance rebuild` now writes `diagnostics.account_surface` to
  `instance_rebuild_report-<run_id>.json` when tracks are available.
- `femic instance promote-evidence` now carries account-surface QA fields:
  - `summary.account_surface_total_ok_species_empty_signature`
  - `summary.account_surface_species_count`
- Updated runbook guidance to include deterministic species-surface diagnostics:
  - `instances/reference/runbooks/REBUILD_RUNBOOK.md`
  - `src/femic/resources/instance/runbooks/REBUILD_RUNBOOK.md`
- Added/updated user-facing docs for expected-empty species accounts and
  validation checklist:
  - `docs/sample-models/k3z.rst`
  - `external/femic-k3z-instance/docs/base-case-analysis.rst`
  - `docs/reference/cli.rst`
  - `docs/guides/troubleshooting.rst`
- Expanded tests/docs-contract coverage:
  - `tests/test_cli_main.py`
  - `tests/test_docs_contract.py`
  - `tests/test_account_surface.py`

## 2026-03-12 - Fixed K3Z matrix-builder regression (block-key mismatch + missing seral accounts)
- Recovered K3Z model coherence after regression where Patchworks reported
  `218` shapefile/csv block join mismatches and missing `feature.Seral.*`
  accounts.
- Runtime + code fixes:
  - Updated `external/femic-k3z-instance/config/patchworks.runtime.windows.yaml`:
    - `matrix_builder.forestmodel_xml_path` now points to
      `../models/k3z_patchworks_model/yield/forestmodel.xml`.
    - `patchworks.license_value: null` (env-driven license credential).
  - Patched `src/femic/patchworks_runtime.py`:
    - `infer_patchworks_model_dir()` now prefers shared model root when
      `tracks/` and `yield/` are sibling folders.
    - `load_patchworks_runtime_config()` now treats null/blank
      `patchworks.license_value` as fallback to `SPS_LICENSE_SERVER` env.
- Regenerated K3Z model artifacts:
  - Rebuilt `yield/forestmodel.xml` (and output mirror) with seral-stage
    feature/product attributes enabled from `config/seral.k3z.yaml`.
  - Rebuilt model-local `blocks/blocks.shp` + `blocks/topology_blocks_200r.csv`
    with `BLOCK <- BLOCK`.
  - Reran matrix builder successfully:
    `run_id=k3z_regression_fix_final_20260312c`.
  - `tracks/accounts.csv` resynced from `protoaccounts.csv` with backup.
- Post-fix checks:
  - block join parity check now reports `csv_only=0`, `shp_only=0`.
  - `tracks/accounts.csv` now includes `feature.Seral.regenerating|young|immature|mature|overmature`.
  - Matrix-builder stderr confirms completion with managed area
    `1781.3132360577583` ha, passive area `0.0`.
- Validation gates passed:
  - `ruff format src tests`
  - `ruff check src tests`
  - `mypy src`
  - `pytest` (`489 passed`)
  - `pre-commit run --all-files`
  - `sphinx-build -b html docs _build/html -W`

## 2026-03-12 - Added roadmap phases 16-18 for API docs, submodule-first K3Z student docs, and PyPI release path
- Extended `ROADMAP.md` with new phases:
  - `Phase 16: Full Developer API Documentation Coverage (FEMIC Package)`
  - `Phase 17: K3Z TSR-Style Student Documentation (Submodule-First)`
  - `Phase 18: Packaging and Publication to PyPI`
- Locked implementation defaults in roadmap notes:
  - canonical K3Z student docs live in
    `external/femic-k3z-instance/docs/`;
  - FEMIC docs keep a concise pointer/overview page (no duplicated deep K3Z narrative);
  - API docs target public-surface module coverage with Google-style docstrings;
  - release execution path is TestPyPI first, then production PyPI.
- Recorded phase-start constraint:
  `P17.0` must first sync the `external/femic-k3z-instance` submodule baseline
  before K3Z docs enhancements proceed.

## 2026-03-12 - Started Phase 16/17 execution: synced K3Z submodule baseline and added API docs scaffold
- Completed `P17.0` (submodule baseline sync):
  - Fast-forwarded `external/femic-k3z-instance` from `e3285ad` to `9748707`
    (`origin/main`) so standalone docs and rebuild spec contract files are
    present in this workspace.
- Completed initial API documentation milestones:
  - `P16.1`: Added API contract page at `docs/reference/api/index.rst`
    defining scope/exclusions (`femic.resources` excluded, private members
    excluded by default).
  - `P16.3`: Added Sphinx API module index at
    `docs/reference/api/modules.rst` and wired docs landing page entry in
    `docs/index.rst`.
  - `P16.4`: Added docs-contract test
    `test_api_reference_pages_are_in_docs_tree_and_list_public_modules` in
    `tests/test_docs_contract.py`.
- Build-system/doc tooling update:
  - Added `src/` path injection in `docs/conf.py` so autodoc/autosummary can
    import `femic` modules during docs builds.
- Validation gates passed for this checkpoint:
  - `ruff format src tests`
  - `ruff check src tests`
  - `mypy src`
  - `pytest` (`490 passed`)
  - `pre-commit run --all-files`
  - `sphinx-build -b html docs _build/html -W`

## 2026-03-12 - Completed Phase 16 docstring coverage pass (`P16.2`)
- Added missing public docstrings and normalized style (Google-style concise
  summaries) across key runtime/CLI/doc-facing modules:
  - `src/femic/__main__.py`
  - `src/femic/cli/main.py`
  - `src/femic/patchworks_runtime.py`
  - `src/femic/pipeline/io.py`
  - `src/femic/pipeline/plots.py`
  - `src/femic/pipeline/tipsy_legacy.py`
  - `src/femic/rebuild_runner.py`
  - `src/femic/vdyp/reporting.py`
- Verified public-surface docstring completeness via AST scan:
  - `0` missing docstrings for non-private defs in `src/femic`
    (excluding resource payload modules).
- Validation gates passed after docstring updates:
  - `ruff format src tests`
  - `ruff check src tests`
  - `mypy src`
  - `pytest` (`490 passed`)
  - `pre-commit run --all-files`
  - `sphinx-build -b html docs _build/html -W`

## 2026-03-12 - Completed Phase 17 TSR-style K3Z docs expansion in submodule (`P17.1`, `P17.2`, `P17.3`, `P17.5`)
- Updated standalone docs information architecture:
  - Added `figure-appendix` to
    `external/femic-k3z-instance/docs/index.rst`.
- Added TSR-style land-base and area-accounting content:
  - `external/femic-k3z-instance/docs/land-base-and-netdown.rst` now includes:
    - analysis-area map section,
    - total area/THLB summary table,
    - AU area table,
    - explicit THLB netdown placeholder table (baseline netdown currently 0).
- Added figure appendix and cross-references:
  - New page:
    `external/femic-k3z-instance/docs/figure-appendix.rst`
    with core teaching figure catalog and full `plots/` inventory.
  - Added base-case linkages in
    `external/femic-k3z-instance/docs/base-case-analysis.rst`.
  - Updated crosswalk mapping in
    `external/femic-k3z-instance/docs/data-package-crosswalk.rst`.
- Added map artifact for student docs:
  - `external/femic-k3z-instance/docs/_static/k3z_analysis_area_map.png`
    generated from `output/patchworks_k3z_validated/fragments/fragments.shp`.
- Expanded docs contract checks in `tests/test_docs_contract.py` for new
  appendix and required section headings.
- Validation gates passed for this checkpoint:
  - `ruff format src tests`
  - `ruff check src tests`
  - `mypy src`
  - `pytest` (`490 passed`)
  - `pre-commit run --all-files`
  - `sphinx-build -b html docs _build/html -W`
  - `sphinx-build -b html external/femic-k3z-instance/docs external/femic-k3z-instance/_build/html -W`

## 2026-03-12 - Completed FEMIC-side K3Z pointer-page consolidation (`P17.4`)
- Replaced FEMIC K3Z sample-model page with concise pointer contract:
  - `docs/sample-models/k3z.rst` now points users to canonical standalone docs
    in `UBC-FRESH/femic-k3z-instance` and its published docs site.
  - Maintains FEMIC-local integration guidance only:
    submodule sync commands and rebuild spec/runbook paths.
- Updated docs contract tests to enforce pointer-page model:
  - `tests/test_docs_contract.py` now checks required pointer sections, canonical
    links, and submodule command snippets instead of legacy deep narrative
    section headings.
- Phase 17 is now fully complete (`P17.0` through `P17.5`).
- Validation gates passed for this checkpoint:
  - `ruff format src tests`
  - `ruff check src tests`
  - `mypy src`
  - `pytest` (`490 passed`)
  - `pre-commit run --all-files`
  - `sphinx-build -b html docs _build/html -W`
  - `sphinx-build -b html external/femic-k3z-instance/docs external/femic-k3z-instance/_build/html -W`

## 2026-03-12 - Phase 18 packaging runbook + deterministic wheel checks + publish workflow scaffolding (`P18.1`)
- Completed `P18.1` and prepared `P18.2/P18.3` automation:
  - Added release runbook:
    `docs/guides/pypi-release-runbook.rst` and linked it from
    `docs/guides/index.rst`.
  - Added local packaging helper:
    `scripts/release_package_checks.sh` covering
    `python -m build`, `twine check`, wheel install smoke, and wheel
    reproducibility checks with fixed `SOURCE_DATE_EPOCH`.
  - Updated CI packaging checks:
    `.github/workflows/package-release-checks.yml` now sets deterministic build
    epoch and verifies wheel hash stability across consecutive builds.
  - Added staged publication workflows:
    `.github/workflows/publish-testpypi.yml` and
    `.github/workflows/publish-pypi.yml`.
  - Updated release instructions in `README.md` to use the helper script and
    runbook.
- Validation gates passed:
  - `ruff format src tests`
  - `ruff check src tests`
  - `mypy src`
  - `pytest` (`491 passed`)
  - `pre-commit run --all-files`
  - `sphinx-build -b html docs _build/html -W`
  - `scripts/release_package_checks.sh`
- Remaining Phase 18 work:
  - execute actual TestPyPI publish + smoke (`P18.2`),
  - execute production PyPI publish (`P18.3`),
  - record final version/hash/date traceability (`P18.4`).

## 2026-03-12 - K3Z appendix now renders actual plot figures inline
- Updated canonical student docs in
  `external/femic-k3z-instance/docs/figure-appendix.rst` to include rendered
  figures, not just filenames.
- Added inline figure blocks for:
  - analysis-area map (`docs/_static/k3z_analysis_area_map.png`),
  - strata distribution plot,
  - all `vdyp_lmh_tsak3z-*.png` figures,
  - all `vdyp_fitdiag_tsak3z-*.png` figures,
  - all `tipsy_vdyp_tsak3z-*.png` figures.
- Kept filename/source references in figure captions for traceability.
- Updated parent docs contract checks in `tests/test_docs_contract.py` to
  enforce new appendix section headings and figure directives.
- Validation checks passed:
  - `pytest tests/test_docs_contract.py`
  - `sphinx-build -b html external/femic-k3z-instance/docs external/femic-k3z-instance/_build/html -W`
  - `sphinx-build -b html docs _build/html -W`

## 2026-03-12 - Refreshed K3Z appendix overlays to treated/scaled-VDYP outputs
- Regenerated all `tipsy_vdyp_tsak3z-*.png` figures in
  `external/femic-k3z-instance/plots/` from current rebuilt K3Z inputs:
  - `data/tipsy_curves_tsak3z.csv` (treated curves)
  - `data/vdyp_curves_smooth-tsak3z.feather` (reference VDYP)
  - `data/model_input_bundle/au_table.csv` (AU -> stratum/SI + managed IDs)
- Updated K3Z appendix wording in
  `external/femic-k3z-instance/docs/figure-appendix.rst` to use treated/scaled
  terminology (`Treated (Scaled-VDYP) Curve Overlays`).
- Updated parent docs contract expectation in `tests/test_docs_contract.py` to
  match the new heading text.
- Verification performed (no guessing):
  - Rebuild report confirms `tipsy_curve_mode=vdyp_transform`,
    `matrix_returncode=0`.
  - Matrix-builder log confirms successful track rebuild with full managed area.
- Validation:
  - `pytest tests/test_docs_contract.py -q` (pass)
  - `sphinx-build -b html external/femic-k3z-instance/docs external/femic-k3z-instance/_build/html -W` (pass)
  - Full repo gates were re-run; one pre-existing main-docs API autosummary
    warning set still fails `docs _build/html -W` and remains outside this K3Z
    figure-refresh scope.

## 2026-03-12 - Phase 18 TestPyPI execution attempt blocked by trusted-publisher configuration
- Triggered GitHub Actions workflow `publish-testpypi` against `main`:
  `https://github.com/UBC-FRESH/femic/actions/runs/23022440859`.
- Packaging/build validation succeeded in workflow; publish step failed with:
  `invalid-publisher` (no matching trusted publisher configured on TestPyPI for
  emitted OIDC claims).
- Captured key claims for setup alignment:
  - repository: `UBC-FRESH/femic`
  - workflow ref:
    `UBC-FRESH/femic/.github/workflows/publish-testpypi.yml@refs/heads/main`
  - environment: `testpypi`
- Updated release runbook with explicit trusted-publisher setup and
  troubleshooting guidance:
  `docs/guides/pypi-release-runbook.rst`.
- Phase 18 status after this execution:
  - `P18.1` complete,
  - `P18.2` blocked pending TestPyPI trusted publisher config,
  - `P18.3/P18.4` pending `P18.2` completion.

## 2026-03-12 - Clarified token-free TestPyPI bootstrap path in dev release docs
- Updated `docs/guides/pypi-release-runbook.rst` to document the validated
  OIDC-first entry point when no project-level `Add project` button is present.
- Added account-level TestPyPI pending-publisher flow via:
  `https://test.pypi.org/manage/account/publishing/`.
- Documented expected behavior that first successful trusted publish creates the
  `femic` TestPyPI project and attaches the publisher.
- Reframed token upload instructions as fallback only.

## 2026-03-12 - Fixed publish-testpypi smoke-step shell parsing failure
- Investigated failing workflow run:
  `https://github.com/UBC-FRESH/femic/actions/runs/23023081990`.
- Root cause:
  - publish to TestPyPI succeeded,
  - failure occurred afterward in smoke step due to shell quoting in version
    extraction command (`syntax error near unexpected token tomllib.loads`).
- Updated workflow:
  `/.github/workflows/publish-testpypi.yml`
  to use a simpler, robust Python one-liner for version extraction.
- Local validation gates passed:
  - `ruff format src tests`
  - `ruff check src tests`
  - `mypy src`
  - `pytest`
  - `pre-commit run --all-files`
  - `sphinx-build -b html docs _build/html -W`

## 2026-03-12 - Completed Phase 18 P18.2 with pre-release TestPyPI publish (`0.1.1a1`)
- Bumped package version in `pyproject.toml` from `0.1.0` to `0.1.1a1`
  (PEP 440 pre-release) to avoid immutable-version re-upload errors.
- Updated production publish workflow to match TestPyPI safety behavior:
  - `.github/workflows/publish-pypi.yml` now sets `skip-existing: true`,
  - includes post-publish smoke install (`femic --help`) using repo version.
- Diagnosed TestPyPI smoke failure caused by index propagation delay after
  successful upload (run: `23023687076`), then added retry loops to both:
  - `.github/workflows/publish-testpypi.yml`
  - `.github/workflows/publish-pypi.yml`
- Re-ran TestPyPI workflow to green:
  `https://github.com/UBC-FRESH/femic/actions/runs/23023751656`.
- Validation gates passed locally after workflow updates:
  - `ruff format src tests`
  - `ruff check src tests`
  - `mypy src`
  - `pytest` (`491 passed`)
  - `pre-commit run --all-files`
  - `sphinx-build -b html docs _build/html -W`

## 2026-03-12 - Phase 18 P18.3 attempt blocked by production PyPI trusted publisher
- Triggered production workflow:
  `https://github.com/UBC-FRESH/femic/actions/runs/23023862800`.
- Build and artifact validation stages succeeded; failure occurred at
  `Publish to PyPI` with:
  `invalid-publisher` (OIDC token valid, but no matching trusted publisher on
  production PyPI).
- Debug claims from workflow:
  - `sub`: `repo:UBC-FRESH/femic:environment:pypi`
  - `repository`: `UBC-FRESH/femic`
  - `workflow_ref`:
    `UBC-FRESH/femic/.github/workflows/publish-pypi.yml@refs/heads/main`
  - `ref`: `refs/heads/main`
  - `environment`: `pypi`
- Outcome:
  - workflow logic is aligned with TestPyPI and functioning as intended,
  - final unblock is a PyPI-side trusted publisher entry matching the above
    claims; once configured, rerun `publish-pypi`.

## 2026-03-12 - Completed Phase 18 P18.3/P18.4 with production PyPI publish (`0.1.1a1`)
- Triggered production workflow after publisher alignment:
  `https://github.com/UBC-FRESH/femic/actions/runs/23024083304`.
- Workflow passed end-to-end:
  - build and `twine check`,
  - publish to PyPI,
  - post-publish smoke install from PyPI (`femic --help`).
- Published artifact traceability (PyPI API):
  - `femic-0.1.1a1-py3-none-any.whl`
    `sha256=09c8dfca3539815b149dee77145ba525eae33f239e88a3e3e63879d6fcc0d699`
    uploaded `2026-03-12T21:10:52.402225Z`.
  - `femic-0.1.1a1.tar.gz`
    `sha256=10fb2e43abdecb0dcee5c40096230462aca9cab5e2cc7c28687a7bd8258154d7`
    uploaded `2026-03-12T21:10:53.810540Z`.
- Phase 18 status: all checklist items complete (`P18.1`–`P18.4`).

## 2026-03-14 - Phase 19 kickoff: TSA29 instance repo published and linked as submodule
- Published standalone TSA29 instance repository and release tag:
  `https://github.com/UBC-FRESH/femic-tsa29-instance` (`v0.1.0`).
- Added parent-repo contract and planning artifact:
  `planning/tsa29-instance-contract.md`.
- Delivered TSA29 snapshot-first baseline in standalone repo with:
  - runnable configs (`run_profile.tsa29.yaml`, `tipsy/tsa29.yaml`),
  - rebuild contract files (`rebuild.spec.yaml`, `rebuild.allowlist.yaml`),
  - curated TSA29 bundle/output artifacts,
  - canonical student docs (Sphinx) including figure appendix with rendered
    plots,
  - lineage/checksum/evidence metadata (`metadata/*`, `evidence/*`).
- Applied thin-instance policy for large artifacts:
  externalized very large files and tracked their hashes and manifests
  (`metadata/large_artifacts.sha256`,
  `output/patchworks_tsa29_validated/ARTIFACTS.md`).
- Linked TSA29 back into FEMIC:
  - added submodule `external/femic-tsa29-instance`,
  - added FEMIC pointer page `docs/sample-models/tsa29.rst`,
  - updated guide references in deployment/onboarding docs,
  - added docs-contract tests for TSA29 submodule/docs presence.
- Remaining Phase 19 item:
  `P19.5` (full Patchworks-enabled rebuild validation and evidence promotion to
  green status).

## 2026-03-14 - Extended TSA29 plan for dual-output pipeline and ws3 smoke tests
- Created dedicated feature branch to firewall ongoing TSA29 compile work from
  `main`:
  `feature/compile-tsa29-instance-ws3-fork`.
- Extended TSA29 planning contract in
  `planning/TSA29_dataset_compile_plan.md` to require pipeline fork outputs:
  - Patchworks branch (secondary teaching/training path),
  - Woodstock branch (primary ws3 research path).
- Added explicit ws3 integration contract:
  - create/link ws3 model instance using FEMIC Woodstock outputs,
  - execute ws3 simulation smoke test,
  - record ws3 smoke evidence and sanity checks.
- Updated roadmap to track this as open Phase 19 work:
  - `P19.9 Add dual-output fork contract (Patchworks + Woodstock)`,
  - `P19.10 Add ws3 smoke-test integration and evidence gate`.

## 2026-03-14 - Added dual-export orchestration and ws3 smoke command path (`P19.9`)
- Implemented `femic export dual` to produce Patchworks + Woodstock outputs in
  a single command execution using shared bundle/checkpoint inputs.
- Implemented `femic instance ws3-smoke` to validate Woodstock export
  structure/sanity and optionally execute a ws3 simulation command.
- Added new runtime helper module:
  `src/femic/ws3_smoke.py` with JSON evidence output and optional stdout/stderr
  capture for ws3 command runs.
- Updated docs for operator usage:
  - `docs/reference/cli.rst`
  - `docs/guides/model-input-bundle-and-export.rst`
  - `docs/guides/pipeline-overview.rst`
- Added regression coverage:
  - `tests/test_ws3_smoke.py`
  - new `export dual` / `instance ws3-smoke` CLI wiring tests in
    `tests/test_cli_main.py`
- Phase status:
  `P19.9` complete; `P19.10` remains open pending execution against a real ws3
  model instance and captured green evidence.

## 2026-03-14 - Added builtin ws3 bridge smoke integration (`P19.10` progress)
- Added `src/femic/ws3_bridge.py` with
  `build_ws3_sections_from_femic_woodstock(...)` to convert FEMIC Woodstock CSV
  exports into ws3-compatible Woodstock section files
  (`.lan/.are/.yld/.act/.trn`).
- Extended `src/femic/ws3_smoke.py` so ws3 smoke can:
  - build bridge section files,
  - optionally inject a local ws3 checkout via `--ws3-repo-path`,
  - run builtin `ws3.forest.ForestModel` load/compile/schedule smoke logic,
  - emit bridge metadata in JSON evidence output.
- Extended CLI options:
  - `femic export dual`: `--ws3-repo-path`, `--ws3-builtin-smoke`,
    `--ws3-bridge-dir`.
  - `femic instance ws3-smoke`: `--ws3-repo-path`, `--builtin-model-smoke`,
    `--ws3-bridge-dir`.
- Updated docs/tests for this contract:
  - `docs/reference/cli.rst`, `docs/reference/api/modules.rst`
  - `tests/test_ws3_bridge.py`, `tests/test_ws3_smoke.py`,
    `tests/test_cli_main.py`, `tests/test_docs_contract.py`
- Validation gates passed locally:
  - `ruff format src tests`
  - `ruff check src tests`
  - `mypy src`
  - `pytest` (`500 passed`)
  - `pre-commit run --all-files`
  - `sphinx-build -b html docs _build/html -W`

## 2026-03-14 - Completed Phase 19 `P19.10` ws3 evidence gate on TSA29
- Generated a complete TSA29 Woodstock package in the instance repo:
  `external/femic-tsa29-instance/output/woodstock_tsa29_validated/`
  including `woodstock_yields.csv`, `woodstock_areas.csv`,
  `woodstock_actions.csv`, `woodstock_transitions.csv`.
- Executed real ws3 smoke gate against TSA29 outputs with local ws3 checkout:
  `femic instance ws3-smoke --instance-root external/femic-tsa29-instance --woodstock-dir output/woodstock_tsa29_validated --output evidence/ws3_smoke_report.latest.json --ws3-repo-path /home/gep/projects/ws3`.
- Smoke result was green:
  - `status=ok`
  - rows `(y/a/ac/t)=(10050/147959/30/30)`
  - `inventory_area=2172195.127`
  - evidence written at
    `external/femic-tsa29-instance/evidence/ws3_smoke_report.latest.json`.
- Published TSA29 instance updates to
  `UBC-FRESH/femic-tsa29-instance` commit `afc5f8b` with evidence + Woodstock
  outputs + ws3 bridge section files.

## 2026-03-14 - Hardened TSA key/index handling to prevent stage-01a key-format failures
- Added canonical TSA normalizer in `src/femic/pipeline/tsa.py` and upgraded
  `select_tsa_slice(...)` to:
  - try normalized candidate keys,
  - fall back to normalized-index masking when index dtype/tokens drift,
  - raise clearer diagnostics including available normalized TSA keys.
- Updated `src/femic/pipeline/stages.py::prepare_tsa_index(...)` to normalize
  TSA values during index preparation so stale int/mixed-case checkpoint data
  does not break downstream TSA selection.
- Added regression coverage in `tests/test_pipeline_helpers.py` for:
  - mixed-case named TSA lookup (`K3Z` -> `k3z`) via `select_tsa_slice(...)`,
  - normalized `prepare_tsa_index(...)` output for numeric/string/named TSA
    values.
- Ran local validation gates successfully:
  - `ruff format src tests`
  - `ruff check src tests`
  - `mypy src`
  - `pytest` (`504 passed`)
  - `pre-commit run --all-files`

## 2026-03-14 - Added fail-fast stale BatchTIPSY output guard for 01b overlays
- Added `validate_tipsy_output_is_fresh(...)` in
  `src/femic/pipeline/tipsy.py` to detect when `04_output-tsaXX.out` is older
  than the current `tipsy_params_tsaXX.xlsx`.
- Wired the guard into both legacy 01b entry surfaces:
  - `01b_run-tsa.py`
  - `src/femic/resources/legacy/01b_run-tsa.py`
- Default behavior now fails fast with a clear rerun instruction, preventing
  silent mismatches in VDYP-vs-TIPSY plot generation and post-TIPSY artifacts.
- Added opt-out env override for controlled debugging:
  `FEMIC_ALLOW_STALE_TIPSY_OUTPUT=1`.
- Added regression coverage in `tests/test_tipsy.py`:
  - stale-output error path
  - override-allowed path
- Validation gates run:
  - `ruff format src tests`
  - `ruff check src tests`
  - `mypy src`
  - `pytest` (`506 passed`)
  - `pre-commit run --all-files`

## 2026-03-14 - Clarified canonical BatchTIPSY DAT contract in docs and runtime checks
- Clarified pipeline semantics:
  - `02_input-tsaXX.dat` is the canonical BatchTIPSY input handoff,
  - `tipsy_params_tsaXX.xlsx` is a human-readable companion.
- Added `tipsy_input_dat_path(...)` helper in `src/femic/pipeline/tipsy.py`.
- Tightened `validate_tipsy_output_is_fresh(...)` behavior:
  - DAT freshness is now preferred when available,
  - running 01b with a missing canonical DAT now fails fast with a clear error,
  - stale-output checks continue to support explicit override via
    `FEMIC_ALLOW_STALE_TIPSY_OUTPUT=1`.
- Wired DAT-aware freshness checks into both legacy 01b surfaces:
  - `01b_run-tsa.py`
  - `src/femic/resources/legacy/01b_run-tsa.py`
- Updated user-facing workflow docs:
  - `docs/guides/stage-01a-vdyp-tipsy-input.rst`
  - `docs/guides/stage-01b-post-tipsy.rst`
  - `docs/guides/pipeline-overview.rst`
- Added tests in `tests/test_tipsy.py` for:
  - DAT path helper,
  - stale-output detection with DAT present,
  - required-DAT failure path.
- Validation gates run:
  - `ruff format src tests`
  - `ruff check src tests`
  - `mypy src`
  - `pytest` (`508 passed`)
  - `pre-commit run --all-files`
  - `.venv/bin/sphinx-build -b html docs _build/html -W`

## 2026-03-15 - Fixed resume-skip contract gap that allowed missing `02_input-tsaXX.dat`
- Root cause of missing DAT in resume workflows:
  `_should_skip_01a(...)` only required
  `tipsy_params_tsaXX.xlsx` and `vdyp_curves_smooth-tsaXX.feather`, so FEMIC
  could skip 01a even when canonical BatchTIPSY handoff DAT was absent.
- Patched both legacy stage-00 surfaces to include DAT in 01a skip gating:
  - `00_data-prep.py`
  - `src/femic/resources/legacy/00_data-prep.py`
  by adding `tipsy_input_dat_path(tsa=...)` to required output paths.
- Updated orchestration wiring regression expectations:
  - `tests/test_legacy_orchestration_wiring.py`
- Validation gates run:
  - `ruff format src tests`
  - `ruff check src tests`
  - `mypy src`
  - `pytest` (`508 passed`)
  - `pre-commit run --all-files`
  - `.venv/bin/sphinx-build -b html docs _build/html -W`

## 2026-03-15 - Repaired BatchTIPSY DAT column alignment for TSA29 handoff
- Fixed TIPSY DAT export mapping in `src/femic/pipeline/tipsy.py` by widening
  `Proportion` from `(31, 31)` to `(31, 39)` so real values like `0.3` and
  `0.85` serialize without column-map corruption.
- Preserved operator screenshot-locked BatchTIPSY anchors (including
  `Regen_Method` at column 64, species code fields at `97-99`/`129-131`/etc,
  and SI at `108-111`) and regenerated `data/02_input-tsa29.dat` from the
  corrected writer path.
- Mirrored corrected DAT into TSA29 instance submodule:
  `external/femic-tsa29-instance/data/02_input-tsa29.dat`.
- Updated overflow regression in `tests/test_tipsy.py` to assert width-fail on
  `FIZ` (1-char field), since `Proportion` is now intentionally wider.
- Validation gates run:
  - `ruff format src tests`
  - `ruff check src tests`
  - `mypy src`
  - `pytest` (`508 passed`)
  - `pre-commit run --all-files`
  - `.venv/bin/sphinx-build -b html docs _build/html -W`

## 2026-03-15 - Added explicit Phase 19 siteprod dependency investigation note
- Added a planning decision gate to
  `planning/TSA29_dataset_compile_plan.md` to answer whether siteprod raster SI
  values are actually required in current default compile paths (strata/AU/VDYP/TIPSY/other).
- Recorded matching roadmap note under `ROADMAP.md` "Detailed Next Steps Notes":
  - if siteprod is not required, disable it in default path and make opt-in.
  - if siteprod is required, harden no-data handling so sparse no-data stands
    cannot destabilize clean runs.

## 2026-03-15 - Split VDYP parallelization into a separate non-blocking phase
- Added `Phase 20: VDYP Parallelization and Runtime Observability (Non-Blocking)`
  to `ROADMAP.md` with scoped tasks (`P20.1`-`P20.6`) covering contract,
  profiling, optional AU-level parallel path, deterministic merge checks, and
  runtime heartbeat logging.
- Added a matching `ROADMAP.md` detailed-notes guardrail that Phase 20 must
  not block TSA29 Phase 19 completion (`P19.5`), and should ship opt-in first.
- Extended `planning/TSA29_dataset_compile_plan.md` with a dedicated deferred
  follow-on section that captures the same non-blocking rule and expected
  parity/benchmark deliverables for future VDYP parallelization.

## 2026-03-15 - Drafted Phase 20 P20.1 acceptance checklist
- Added an execution-ready `P20.1` checklist in
  `planning/TSA29_dataset_compile_plan.md` with concrete contract gates for:
  - VDYP-only scope boundary,
  - serial vs parallel parity invariants and float tolerance policy,
  - deterministic merge/re-run hash stability,
  - worker failure handling + serial fallback policy,
  - runtime heartbeat/observability minimums,
  - benchmark and rollout gates (opt-in first, default only after evidence).
- Added a corresponding `ROADMAP.md` detailed next-step note marking `P20.1`
  as drafted and ready for implementation sequencing.

## 2026-03-15 - Queued Phase 19 strata-coverage tuning without interrupting active run
- Added a Phase 19 in-flight planning note to keep the currently monitored
  clean TSA29 run unchanged, while queuing a next-run tuning change to raise
  stratum coverage from the observed ~`0.656` (~10 strata) toward the preferred
  ~`0.8` target.
- Recorded this in:
  - `planning/TSA29_dataset_compile_plan.md` ("Active Run Follow-Up Notes"),
  - `ROADMAP.md` ("Detailed Next Steps Notes").
- Explicitly deferred Phase 20 execution to a separate branch after TSA29 is
  stable enough for graduate-student handoff.

## 2026-03-15 - Switched VDYP explicit feature-id source loads to full-read default
- Updated `src/femic/pipeline/vdyp_stage.py` so explicit feature-id source mode
  now defaults to full-layer `read_file(...)` + in-memory `FEATURE_ID` filter
  (better fit for high-memory hosts), instead of mandatory chunked
  `FEATURE_ID IN (...)` queries.
- Kept chunked feature-id reads as an explicit fallback path by setting
  `source_feature_id_chunk_size` to a positive value.
- Removed explicit `driver=\"FileGDB\"` kwargs from VDYP source reads to avoid
  repeated `OpenFileGDB ... does not support open option DRIVER` runtime
  warnings.
- Updated/validated affected tests in `tests/test_vdyp_stage.py`:
  - `.venv/bin/pytest -q tests/test_vdyp_stage.py -k \"load_vdyp_input_tables\"`
    (`7 passed`)
  - `.venv/bin/ruff check src/femic/pipeline/vdyp_stage.py tests/test_vdyp_stage.py`
    (`All checks passed`)

## 2026-03-15 - Fixed stale pre-VDYP resume checkpoint reuse across strata config changes
- Added signature-aware pre-VDYP checkpoint helpers in
  `src/femic/pipeline/pre_vdyp.py`:
  - `build_vdyp_prep_signature(...)`
  - `save_vdyp_prep_checkpoint(..., signature=...)`
  - `load_vdyp_prep_checkpoint(..., expected_signature=...)`
- Patched both 01a surfaces to persist and validate checkpoint signatures:
  - `01a_run-tsa.py`
  - `src/femic/resources/legacy/01a_run-tsa.py`
- Resume behavior now rejects stale pre-VDYP caches when strata-selection
  parameters change (for example `FEMIC_STRAT_TOP_AREA_COVERAGE`), forcing a
  rebuild instead of silently loading old 10-strata payloads.
- Added tests in `tests/test_pre_vdyp.py` for:
  - signature mismatch rejection,
  - legacy list-payload backward compatibility.

## 2026-03-15 - Added TSA29 curve-quality follow-up tasks to Phase 19 roadmap
- Converted reviewer feedback on TSA29 diagnostics into explicit open Phase 19
  tasks in `ROADMAP.md`:
  - `P19.12` stratum SI plot readability/zoom/outlier-visibility controls.
  - `P19.13` VDYP NLLS failure detection + ordered auto-reparameterization
    fallback sequence (including early-age point censoring and age-20
    merchantable floor option).
  - `P19.14` tail-blend heuristic relaxation and selection-policy revision
    against straight NLLS fits.
  - `P19.15` TSA29 rerun + curve-stability evidence publication.
- Added a matching dated entry under `ROADMAP.md` "Detailed Next Steps Notes"
  to keep implementation sequencing anchored to this feedback.

## 2026-03-15 - Completed P19.12 stratum SI diagnostic readability and auditability
- Updated `src/femic/pipeline/plots.py` to improve plot interpretability:
  - Added deterministic strip-point thinning (`stripplot_max_points` +
    `stripplot_min_points_per_stratum`) and reduced default strip opacity/size.
  - Replaced outlier-driven axis expansion with quantile-centered SI windowing
    (`site_index_focus_quantiles`, `site_index_focus_padding`) constrained by a
    configurable cap (`site_index_xlim`).
  - Added `StrataDistributionPlotMetadata` return payload with SI window,
    total/window/overlay point counts, and clipped low/high counts.
- Updated legacy stage logging in
  `src/femic/resources/legacy/01a_run-tsa.py` to emit plot metadata for
  auditable trimming diagnostics.
- Added/updated tests in `tests/test_pipeline_helpers.py`:
  - config defaults cover new readability controls,
  - render helper returns metadata and expected SI window,
  - outlier clipping and strip-point thinning behavior is regression-tested.

## 2026-03-15 - P19.12 follow-up: fixed strata SI plot lower bound at zero
- Updated `src/femic/pipeline/plots.py` so strata diagnostic SI window keeps a
  fixed lower bound at `site_index_xlim[0]` (default `0`), preventing left-tail
  violin clipping caused by quantile-centered lower bounds.
- Kept quantile-based upper bound behavior unchanged for focused readability.
- Updated plot helper tests in `tests/test_pipeline_helpers.py` to assert SI
  lower-bound behavior and prevent regression.
- Regenerated TSA29 strata diagnostics to confirm rendered SI axis starts at
  `0`.

## 2026-03-15 - P19.12 follow-up: switched strata diagnostics to PNG-only default
- Updated `src/femic/pipeline/plots.py` to stop writing `strata-tsaXX.pdf` by
  default; only `strata-tsaXX.png` is written unless `write_pdf=True` is
  explicitly set in `StrataDistributionPlotConfig`.
- Updated `tests/test_pipeline_helpers.py` to assert PNG-only default behavior
  and added regression coverage for optional PDF emission when requested.

## 2026-03-15 - Completed P19.13a VDYP fit-quality gate warnings
- Updated `src/femic/pipeline/vdyp_stage.py` to evaluate baseline NLLS curve
  plausibility before downstream acceptance and emit structured warning events
  when quality gates fail.
  - Added checks for non-finite/negative curve outputs.
  - Added metric-based gate thresholds for `mape` and early-age overshoot.
  - Added `vdyp_curve_fit` warning events with
    `stage=fit_quality_gate`, `reason=fit_quality_gate_failed`, and
    machine-readable `failure_reasons`.
- Added `tests/test_vdyp_stage.py` regression coverage to force an implausible
  fit and verify fit-quality gate warnings are logged.

## 2026-03-15 - Completed P19.13b left-toe outlier censor re-fit path
- Updated `src/femic/pipeline/vdyp_stage.py` to add a left-toe outlier
  detection pass from observed 5-year bins and generate a censored re-fit
  candidate (`skip1` uplift) for incoherent early-age points.
- Added deterministic selection criteria requiring improved early-age
  overshoot plus RMSE or MAPE improvement before accepting the censored curve.
- Added structured `vdyp_curve_fit` event logging for left-toe censor decisions
  (`stage=left_toe_censor`, selected/rejected) including baseline and candidate
  fit metrics for auditability.
- Added regression test coverage in `tests/test_vdyp_stage.py` to verify left-toe
  censor candidate selection and output curve replacement behavior.

## 2026-03-15 - Completed P19.13c merchantable-volume floor candidate
- Updated `src/femic/pipeline/vdyp_curves.py` so `process_vdyp_out(...)` can
  optionally apply a merchantable-volume floor (`merchantable_floor_enabled`,
  `merchantable_floor_age`, `merchantable_floor_value`) and emit
  `merchantable_floor` stage events.
- Updated `src/femic/pipeline/vdyp_stage.py` to evaluate a merchantable-floor
  candidate whenever baseline curves show non-trivial pre-age-20 volume, then
  select/reject that candidate with structured event logging and RMSE
  guardrails.
- Added regression tests:
  - `tests/test_vdyp_curves.py` verifies floor application through age 20.
  - `tests/test_vdyp_stage.py` verifies stage-level merchantable-floor
    selection and output substitution.

## 2026-03-15 - Completed P19.13d ordered fallback policy + selection events
- Updated `src/femic/pipeline/vdyp_stage.py` to apply explicit fallback-path
  ordering for output curve selection:
  `primary_nlls -> reparameterized_nlls -> censored_refit -> merchantable_floor`,
  with existing K3Z tail-blend override retained.
- Added per-stratum/SI `vdyp_curve_fit` selection events
  (`stage=fallback_policy`, `reason=curve_selected`) with selected path,
  available candidates, and selected metrics.
- Added regression test in `tests/test_vdyp_stage.py` to verify policy-order
  selection and event emission.

## 2026-03-15 - Completed P19.14a configurable/relaxed tail-linearity thresholds
- Updated `src/femic/pipeline/vdyp_stage.py` so tail-blend candidate defaults are
  no longer hard-coded per run and now come from:
  - environment-backed defaults (`FEMIC_TAIL_LINEAR_MIN_POINTS`,
    `FEMIC_TAIL_LINEAR_MIN_R2`, `FEMIC_TAIL_LINEAR_MAX_NRMSE`,
    `FEMIC_TAIL_LINEAR_PREFER_MIN_AGE`, `FEMIC_TAIL_BLEND_YEARS`), and
  - per-stratum/per-SI `kwarg_overrides_for_tsa` values when supplied.
- Relaxed baseline tail defaults used by stage candidate generation to improve
  eligibility of plausible late-linear tails while retaining deterministic
  thresholds.
- Added regression tests in `tests/test_vdyp_stage.py` confirming:
  - per-stratum tail override values are respected, and
  - env-provided defaults are applied when no explicit overrides are present.

## 2026-03-15 - Completed P19.14b tail-blend selection criteria + tie-breaks
- Updated `src/femic/pipeline/vdyp_stage.py` with explicit objective selection
  criteria for tail-blend vs straight NLLS using:
  - required tail-RMSE improvement with non-harm guardrails on RMSE/MAPE/early
    overshoot, and
  - deterministic tie-break behavior for near-equal tail fits.
- Added structured decision logging (`vdyp_curve_fit`,
  `stage=tail_blend_selection`) capturing selected/rejected outcomes, decision
  predicates, and baseline/candidate metrics.
- Integrated accepted tail-blend candidate into non-K3Z fallback output
  selection path (`selected_path=tail_blend`) while preserving K3Z-specific
  tail-blend override behavior.
- Added regression test in `tests/test_vdyp_stage.py` verifying tail-blend
  selection and fallback-policy selected path emission.

## 2026-03-15 - Completed P19.14c fit diagnostics for selected path + residuals
- Updated `src/femic/pipeline/vdyp_stage.py` fit diagnostic plotting to:
  - overlay the final selected output curve and selected-path label,
  - include a residual subplot (`selected - observed median` by age bin), and
  - annotate estimated tail-blend window (anchor/end age) when tail-blend
    metadata is available.
- Moved diagnostic plotting to run after fallback-path selection so each plot
  reflects the actual curve that will be carried forward.

## 2026-03-15 - Completed P19.15b reviewer-facing strata/SI fit-status table
- Added `summarize_curve_selection_rows(...)` in `src/femic/vdyp/reporting.py`
  to parse `vdyp_curve_fit` events and produce per-stratum/SI selection rows
  containing:
  - selected path,
  - fit-quality gate failure flag,
  - left-toe censor selection flag,
  - merchantable-floor selection flag,
  - tail-blend selection flag.
- Extended `femic vdyp report` in `src/femic/cli/main.py` with
  `--selection-summary-out` to write this reviewer-facing summary table to CSV.
- Added regression coverage in:
  - `tests/test_vdyp_reporting.py` for row extraction/flagging logic,
  - `tests/test_vdyp_report_cli.py` for CSV output generation.

## 2026-03-15 - Completed P19.15a.1 THLB empty-slice guard for post-TIPSY stability
- Patched `mean_thlb_for_geometry(...)` in `src/femic/pipeline/tsa.py` to avoid
  calling `np.mean` on empty valid-cell masks; now returns the configured
  fallback when no valid cells are present.
- Added non-finite guard on computed THLB means so invalid numeric outputs also
  fall back safely.
- Added regression coverage in `tests/test_pipeline_helpers.py` to lock the
  empty-valid-cell fallback behavior and prevent warning-flood regressions.
- Updated `ROADMAP.md`:
  - checked off Phase 19 subtask `P19.15a.1`,
  - appended matching detail in "Detailed Next Steps Notes".

## 2026-03-15 - Completed P19.15 TSA29 curve-QA rerun + stability evidence publish
- Re-ran TSA29 curve QA with updated policy stack and published stability evidence:
  - stratum coverage run at `top_area_coverage=0.80` selected 18 strata
    (`coverage=0.8061826878755755`),
  - regenerated `plots/strata-tsa29.png`,
  - regenerated all 54 AU overlays `plots/tipsy_vdyp_tsa29-*.png`.
- Generated reviewer-facing selection summary CSV from curve-event logs:
  `vdyp_io/logs/curve_selection_summary-tsa29-20260315T184955Z.csv`
  (`primary_nlls=12`, `tail_blend=19`, `merchantable_floor=22`,
  `censored_refit=1`).
- Completed post-TIPSY finalize and refreshed model-input bundle outputs:
  - `data/model_input_bundle/au_table.csv`
  - `data/model_input_bundle/curve_table.csv`
  - `data/model_input_bundle/curve_points_table.csv`
  - manifest: `vdyp_io/logs/run_manifest-post_tipsy_20260315T190051Z.json`.
- Published canonical instance evidence in `external/femic-tsa29-instance`:
  - `evidence/curve_stability_report.20260315.md`
  - `evidence/curve_selection_summary-tsa29-20260315T184955Z.csv`
  - docs link update in `docs/rebuild-and-qa.rst`.

## 2026-03-15 - Completed P19.15d composable censoring + selected-curve gate rescue
- Updated `src/femic/pipeline/vdyp_stage.py` branching logic so left-toe
  censoring composes with downstream candidate generation (tail blend and
  merchantable floor) instead of acting as an exclusive terminal override.
- Added selected-curve gate rescue: when the initially selected curve still
  fails fit-quality checks, FEMIC now evaluates available candidates and
  reselects in ordered priority:
  `tail_blend -> merchantable_floor -> reparameterized_nlls -> censored_refit -> primary_nlls`,
  with explicit warning events for rescue or unresolved failures.
- Added env-configurable tail-blend selection thresholds (`FEMIC_TAIL_SELECT_*`)
  and relaxed default ratios so tail-blend can be selected more often for
  borderline but non-harmful candidates.
- Preserved K3Z tail-blend override behavior while preventing non-K3Z runs from
  silently carrying non-finite/failed primary selections when better candidates
  exist.
- Added/updated regression coverage in `tests/test_vdyp_stage.py` for:
  - composable left-toe censor + tail-blend behavior,
  - selected-curve gate rescue selection, and
  - existing tail-blend/left-toe/floor policy interactions.

## 2026-03-15 - Corrected merchantable-floor behavior to right-shifted toe ramp
- Updated `src/femic/pipeline/vdyp_curves.py` merchantable-floor logic in
  `process_vdyp_out(...)` to shift the fitted curve right by
  `merchantable_floor_age` years instead of hard-clamping ages `<= floor_age`
  to a flat value.
- This preserves the fitted exponential toe-ramp shape (smooth onset after age
  20 by default) while still enforcing the merchantable floor on the delayed
  interval.
- Added explicit event metadata for auditability:
  `stage=merchantable_floor`, `mode=right_shift`, `shift_years=<floor_age>`.
- Updated `tests/test_vdyp_curves.py` to verify that post-floor ages match a
  delayed baseline curve and that the curve begins rising immediately after the
  floor window (`age=21` for a 20-year floor).

## 2026-03-15 - Applied toe-shift defaults to all fit paths with config override
- Updated `src/femic/pipeline/vdyp_stage.py` so every smoothing run starts with
  a default toe-shift (`toe_shift_years`) applied to baseline and candidate fit
  kwargs, using `FEMIC_VDYP_TOE_SHIFT_YEARS` (default `20.0`) unless overridden.
- Updated `src/femic/pipeline/vdyp_stage.py` to skip separate
  merchantable-floor candidate evaluation when toe-shift is already active,
  preventing mixed post-hoc-only behavior.
- Updated `src/femic/pipeline/io.py` and `src/femic/cli/main.py` to add
  run-profile/config support for `modes.vdyp_toe_shift_years`, wiring it into
  legacy runtime env as `FEMIC_VDYP_TOE_SHIFT_YEARS`.
- Updated config templates:
  - `config/run_profile.example.yaml`
  - `config/run_profile.case_template.yaml`
  - `instances/reference/config/run_profile.case_template.yaml`
  with documented `vdyp_toe_shift_years` guidance.
- Added/updated regression coverage:
  - `tests/test_vdyp_stage.py` (default/env toe-shift propagation; floor-candidate gate),
  - `tests/test_vdyp_curves.py` (up-front toe-shift behavior),
  - `tests/test_pipeline_helpers.py` (run-profile parsing + env export).
- Validation gates run:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest`,
  `pre-commit run --all-files`, `.venv/bin/sphinx-build -b html docs _build/html -W`.

## 2026-03-15 - Completed P19.16a-d dominant-recovery selection hardening
- Updated `src/femic/pipeline/vdyp_stage.py` to prevent catastrophic
  baseline-curve retention by adding:
  - dominant-recovery selection logic for both left-toe-censor and tail-blend
    candidates (allows selection when baseline is catastrophic and candidate
    improvements are decisive),
  - catastrophic fit gate reason (`catastrophic_mape`) and new early
    underfit metric (`early_underfit`) with gate threshold control, and
  - expanded rescue telemetry fields (`rescue_trigger_gate_reasons`,
    `rescue_order`, `gate_by_path`) plus detailed candidate decision payloads.
- Added new environment knobs in `execute_curve_smoothing_runs(...)`:
  `FEMIC_FIT_GATE_CATASTROPHIC_MAPE`,
  `FEMIC_FIT_GATE_MAX_EARLY_UNDERFIT`,
  `FEMIC_DOMINANT_RECOVERY_MAX_METRIC_RATIO`.
- Updated reviewer-summary parsing in `src/femic/vdyp/reporting.py` so
  `fit_quality_gate_failed` is flagged for selected-curve rescue/unresolved
  fit-gate events as well as base fit-gate failures.
- Added regression coverage:
  - `tests/test_vdyp_stage.py::test_execute_curve_smoothing_runs_selects_dominant_recovery_tail_blend_candidate`
  - `tests/test_vdyp_reporting.py::test_summarize_curve_selection_rows_flags_selected_curve_gate_rescue`
- Targeted TSA29 cached rerun evidence from
  `vdyp_io/logs/vdyp_curve_events-tsa29-p1916_rerun_20260315T2212Z.jsonl`
  confirms prior catastrophic cases now route through dominant recovery:
  - `MS_PLI H`: `left_toe_censor_selected` with
    `dominant_recovery.selected=true` (previously catastrophic `primary_nlls`),
  - `IDF_FDI L`: `left_toe_censor_selected` with
    `dominant_recovery.selected=true` (previously catastrophic `primary_nlls`).
- Validation gates run:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest`,
  `pre-commit run --all-files`,
  `python -m sphinx -b html docs _build/html -W` (via `.venv/bin/python`).

## 2026-03-15 - Tuned TSA29 `MS_PLI L` to a linear post-200 tail
- Updated `src/femic/pipeline/vdyp_overrides.py` with a TSA29 case-specific
  override for `("MS_PLI", "L")` to bias right-tail blending toward a
  near-linear continuation after age ~200:
  `tail_linear_min_points=20`, `tail_linear_min_r2=0.6`,
  `tail_linear_max_nrmse=0.25`, `tail_linear_allow_quantile_fallback=1.0`,
  `tail_anchor_quantile=0.70`, `tail_blend_years=10.0`.
- Added `tests/test_vdyp_overrides.py` coverage to lock the new override
  payload for this case.
- Reran only the `MS_PLI L` smoothing case from cached TSA29 outputs and
  regenerated `plots/vdyp_fitdiag_tsa29-01-MS_PLI-L.png`; selected path remains
  `tail_blend` with an approximately linear tail after age 200 (no pronounced
  curved decline).

## 2026-03-15 - Generalized left-toe discontinuity censoring (no case-specific override)
- Updated `src/femic/pipeline/vdyp_stage.py` left-toe censor detection to catch
  additional early discontinuity classes without per-case tuning:
  - symmetric early low-shoulder discontinuities (`next_median/current` + abs gap),
  - local slope-kink discontinuities (first-step slope vs following-step scale).
- Added strict structural non-harm acceptance for left-toe censor candidates
  when inferred censor depth is substantial (default `skip_delta >= 4`) and
  candidate RMSE/tail-RMSE/MAPE stay within tight ratio guardrails.
- Removed the temporary TSA29 `("MS_PLI", "L")` override from
  `src/femic/pipeline/vdyp_overrides.py` so this case now depends on generalized
  fit logic.
- Added regression coverage in `tests/test_vdyp_stage.py`:
  `test_execute_curve_smoothing_runs_censors_early_low_discontinuity_points`.
- Targeted `MS_PLI L` rerun from cached TSA29 outputs now logs
  `left_toe_censor_selected` (`skip1_after=6`) and chooses
  `selected_path=censored_refit`.

## 2026-03-15 - Migrated VDYP body/tail fitting to 5-year bins + long-tail detection
- Updated `src/femic/pipeline/vdyp_curves.py` so `process_vdyp_out(...)` now
  builds and fits against 5-year binned median observations via
  `build_observed_bins_for_fit(...)` instead of annual-age medians.
- Reworked `detect_linear_tail_segment(...)` to use right-to-left contiguous
  break detection with a composite straight-ish gate:
  low `nrmse` and (`r2` threshold OR near-flat slope), plus minimum tail-span
  requirement to avoid selecting tiny terminal segments.
- Added new tail controls in runtime defaults (`src/femic/pipeline/vdyp_stage.py`):
  `FEMIC_TAIL_LINEAR_FLAT_SLOPE_ABS` and
  `FEMIC_TAIL_LINEAR_MIN_SPAN_YEARS`.
- Updated layered curve-path behavior:
  structural left-toe discontinuity censoring (`skip_delta >= 4`) is accepted,
  and tail blend is selected when a valid straight-ish tail segment is detected.
- Added regression coverage in `tests/test_vdyp_curves.py` for:
  - 5-year bin aggregation correctness,
  - long flat-tail detection with low-R2 acceptance via flat-slope gate,
  - body-fit input ages using 5-year bins.
- Targeted TSA29 `MS_PLI L` rerun now reports:
  `left_toe_censor_selected` (`skip1_after=6`) and `tail_blend_selected`
  with detected tail anchor near age `180` (span `120` years).

## 2026-03-15 - Finalized Phase 19 follow-up validation + refreshed `MS_PLI L` fitdiag
- Fixed a strict-typing regression in
  `src/femic/pipeline/vdyp_curves.py` by replacing dynamic
  `emit_curve_event(..., **tail_meta)` expansion with explicit numeric tail
  fields, eliminating `mypy` kwargs incompatibility.
- Updated `tests/test_vdyp_stage.py` expectations for the new
  `tail_blend_selection` decision payload shape (`policy=layered_when_detected`
  and `tail_detected` flags) and preserved quantile-fallback coverage.
- Revalidated the repository gates:
  `ruff format src tests`, `ruff check src tests`,
  `PYTHONPATH=src python -m mypy src`, `PYTHONPATH=src python -m pytest`,
  `python -m pre_commit run --all-files`,
  `sphinx-build -b html docs _build/html -W`.
- Re-ran only TSA29 `MS_PLI L` smoothing from cached VDYP inputs and refreshed
  `plots/vdyp_fitdiag_tsa29-01-MS_PLI-L.png` plus
  `tmp/vdyp_curve_events-tsa29-ms_pli_l-rerun.jsonl`.
- Current telemetry confirms long straight-tail detection
  (`anchor_age=180`, `tail_span_years=120`); remaining issue is candidate
  non-finite rejection that still leaves `selected_path=primary_nlls` for this
  case.

## 2026-03-16 - Replaced clamp-based toe shift with toe location-parameter transform
- Updated `src/femic/pipeline/vdyp_curves.py` so `toe_shift_years` is now
  applied only in toe fitting/evaluation (`fill_curve_left(...)`) via a
  location transform, rather than through global age clamping in
  `process_vdyp_out(...)`.
- This removes the `x=0` toe-domain artifact that previously caused
  `legacy_fit_func2` (`a*x^b*x^-a`) to emit `NaN/Inf` on early ages under
  positive toe shift.
- Added regression update in `tests/test_vdyp_curves.py` to verify toe shift
  keeps curve values finite while primarily affecting the left-end toe ramp.
- Reran TSA29 `MS_PLI L` from cached inputs and regenerated
  `plots/vdyp_fitdiag_tsa29-01-MS_PLI-L.png`; event log now has no
  `candidate_rejected_non_finite` records for this case.

## 2026-03-16 - Removed accidental second toe shift on legacy location parameter
- Updated `src/femic/pipeline/vdyp_curves.py` `fill_curve_left(...)` so
  `toe_shift_years` is ignored for toe models with an explicit location
  parameter (`popt.size >= 3`, legacy `fit_func1`) and no longer mutates `c`.
- Updated splice blend-width logic to use effective shift (zero when location
  already exists), preventing toe-shift configuration from implicitly widening
  blend windows in legacy fits.
- Updated regression in `tests/test_vdyp_curves.py` to assert that enabling
  `toe_shift_years` does not apply a second shift for legacy location-parameter
  toe models.
- Reran TSA29 `MS_PLI L` from cached VDYP outputs and regenerated
  `plots/vdyp_fitdiag_tsa29-01-MS_PLI-L.png`; telemetry confirms no non-finite
  candidate rejection and no double-shift plateau behavior.

## 2026-03-16 - Set default strata coverage to 0.80 and regenerated TSA29 fit outputs
- Changed legacy stage-00 default for `FEMIC_STRAT_TOP_AREA_COVERAGE` to `0.8`
  in `00_data-prep.py` and `src/femic/resources/legacy/00_data-prep.py` so
  no-override runs default to coverage-driven strata selection rather than
  top-N fallback.
- Reran TSA29 smooth-curve fitting with coverage targeting enabled and confirmed
  `coverage 0.8061826878755755`, `count 18`, and checkpoint reuse at 18 strata.
- Regenerated TSA29 artifacts:
  - `plots/strata-tsa29.png`
  - all `plots/vdyp_fitdiag_tsa29-*.png`
  - all `plots/vdyp_lmh_tsa29-*.png`
  - `data/vdyp_curves_smooth-tsa29.feather`
  - `vdyp_io/logs/vdyp_curve_events-tsa29-tsa29_cov80_refit_20260316T0115Z.jsonl`

## 2026-03-16 - Accepted current VDYP fit status and regenerated TSA29 TIPSY-vs-VDYP plots
- Recorded current VDYP fit selection status as acceptable for this phase:
  minor non-pathological selection oddities remain, but no null-curve/total-failure
  outcomes were observed.
- Regenerated TSA29 TIPSY-vs-VDYP comparison figures for review:
  - `plots/tipsy_vdyp_tsa29-*.png` (54 refreshed plots, latest timestamp 2026-03-16 05:49 UTC).
- Notes:
  - 01b stale TIPSY output freshness guard was bypassed for this refresh via
    `FEMIC_ALLOW_STALE_TIPSY_OUTPUT=1` to allow immediate comparison plotting.

## 2026-03-16 - Queued high-ratio AU follow-up and passed ws3 smoke on fresh outputs
- Scanned refreshed TSA29 AU-wise TIPSY-vs-VDYP comparisons plus ratio diagnostics
  and queued later follow-up for high TIPSY/VDYP outlier AUs (VDYP LMH currently
  treated as plausible for this pass):
  - `ICH_CW L`, `SBPS_SX L`, `MS_PL L`, `SBPS_SX M`, `IDF_FDI L`
  - `ICH_CW H`, `IDF_FDI M`, `SBS_SX M`, `IDF_FD L`, `ICH_CW M`
- Recorded matching deferred-review note in `ROADMAP.md` under Detailed Next Steps.
- Executed end-to-end dual export + ws3 smoke using freshly regenerated artifacts:
  - `PYTHONPATH=src python -m femic export dual --tsa 29 --with-ws3-smoke --ws3-command true --no-ws3-builtin-smoke`
  - Result: `ws3 smoke ok`, message:
    `Woodstock checks passed and ws3 smoke command exited cleanly.`
  - Evidence/report:
    `evidence/ws3_smoke_report.latest.json`

## 2026-03-16 - Reconciled Phase 19 roadmap parent-task status with completed work
- Updated `ROADMAP.md` Phase 19 checklist bookkeeping to match completed
  subtask/evidence history:
  - marked `P19.13` complete (all `P19.13a-f` complete),
  - marked `P19.14` complete (all `P19.14a-d` complete),
  - marked `P19.16` and `P19.16e` complete based on completed cached TSA29
    smoothing reruns, regenerated fit diagnostics, and reviewer-facing notes.
- Confirmed current near-term open Phase 19 gate remains `P19.5` (full
  Patchworks-enabled rebuild validation/evidence promotion in validated host),
  while Phase 20 remains deferred to a separate branch.

## 2026-03-16 - Added Phase 19 TSA29 Sphinx docs deep-dive task (`P19.17`)
- Added new open Phase 19 task in `ROADMAP.md` to run a full TSA29 instance
  Sphinx documentation deep-dive and augmentation pass:
  - `P19.17a` audit thin/missing sections across TSA29 instance docs,
  - `P19.17b` expand weak sections with concrete guidance + artifact links,
  - `P19.17c` rerun docs build with warnings-as-errors and publish closure note.

## 2026-03-16 - Added Windows 11 Patchworks smoke handoff pack for `P19.5`
- Added `planning/tsa29_patchworks_win11_smoke_handoff.md` with:
  - exact TSA29 input artifact paths for Patchworks smoke execution,
  - current ws3-validated companion counts/reports for reference,
  - stepwise Windows 11 Patchworks smoke procedure,
  - pass/fail checklist and required evidence-capture outputs.
- Recorded matching roadmap note under Detailed Next Steps to keep immediate
  Phase 19 execution sequence aligned around final `P19.5` closure.

## 2026-03-18 - Generated and published K3Z checkpoint1 feature + shapefile export
- Built a dedicated K3Z checkpoint1 feature artifact by masking the 2024 VRI
  source (`data/bc/vri/2024/VEG_COMP_LYR_R1_POLY_2024.gdb`) with K3Z tenure
  boundary (`data/bc/cfa/k3z/CFA K3Z Tenure.shp`), preserving `tsa_code='k3z'`.
- Wrote local artifacts:
  - `data/ria_vri_vclr1p_checkpoint1-tsak3z.feather`
  - `data/shp/ria_vri_vclr1p_checkpoint1-tsak3z.{shp,shx,dbf,prj,cpg}`
  - `data/shp/ria_vri_vclr1p_checkpoint1-tsak3z_fieldmap.csv`
- Published equivalent artifacts into `external/femic-k3z-instance` and pushed
  instance repo commit `a762076` on `main`.

## 2026-03-20 - Added K3Z old-growth (`og1`/`og2`) feature attributes and refreshed model XML
- Implemented generalized old-growth curve synthesis in
  `src/femic/fmg/patchworks.py` and attached new feature attributes to both
  managed and unmanaged selects:
  - per-AU: `feature.Area.og1.<au_id>`, `feature.Area.og2.<au_id>`
  - totals: `feature.Area.og1.total`, `feature.Area.og2.total`
- OG curve definitions:
  - `og1`: linear ramp from unmanaged-curve CMAI age (`0`) to unmanaged
    peak-yield age (`1`).
  - `og2`: fixed policy step (`249 -> 0`, `250 -> 1`).
- Added regression coverage in `tests/test_fmg_patchworks.py` and refreshed
  deterministic XML fixtures:
  - `tests/fixtures/fmg/forestmodel_minimal.xml`
  - `tests/fixtures/fmg/forestmodel_multi_au.xml`
- Updated operator docs in `README.md` Patchworks export section to document
  emitted OG attribute families and curve semantics.
- Regenerated K3Z instance ForestModel XML with the new OG accounts:
  `external/femic-k3z-instance/models/k3z_patchworks_model/yield/forestmodel.xml`.
- Recorded matching plan/progress notes in `ROADMAP.md` under new Phase 21 and
  Detailed Next Steps.


## 2026-03-20 - Verified K3Z OG rollout on Windows Patchworks host and regenerated compiled tracks
- Synced to parent branch `feature/compile-tsa29-instance-ws3-fork` commit
  `d289971` and K3Z submodule commit `ff7bd11`, then executed a fresh Windows
  Patchworks smoke run using:
  - `python -m femic patchworks preflight --config config/patchworks.runtime.windows.yaml --instance-root external/femic-k3z-instance`
  - `python -m femic patchworks matrix-build --config config/patchworks.runtime.windows.yaml --instance-root external/femic-k3z-instance --run-id k3z_og_smoke_20260319`
- Smoke evidence captured in the K3Z instance log directory:
  - `external/femic-k3z-instance/vdyp_io/logs/patchworks_matrixbuilder_stdout-k3z_og_smoke_20260319.log`
  - `external/femic-k3z-instance/vdyp_io/logs/patchworks_matrixbuilder_stderr-k3z_og_smoke_20260319.log`
  - `external/femic-k3z-instance/vdyp_io/logs/patchworks_matrixbuilder_manifest-k3z_og_smoke_20260319.json`
- Matrix Builder completed successfully with:
  - `returncode=0`
  - `Total=1781.3132360577583`
  - `Managed=1781.3132360577583`
  - `Passive=0.0`
- Verified that the compiled K3Z tracks now include the expected old-growth
  feature-account families (for example `feature.Area.og1.<au_id>`,
  `feature.Area.og2.<au_id>`, `feature.Area.og1.total`,
  `feature.Area.og2.total`) and published the refreshed track tables in
  `external/femic-k3z-instance` commit `69322b2`.


## 2026-03-20 - Added Phase 22 CT/fert silviculture scaffold foundation
- Added a new Patchworks export silviculture-config contract and CLI option:
  - `--silviculture-config` on `femic export patchworks`
  - `--silviculture-config` on `femic export dual`
- Introduced a dedicated treatment-path fragment/XML field `SILV_STATE` with
  allowed values `baseline`, `ct`, `fert1`, `fert2`, `fert3`.
- Updated Patchworks fragment validation and deterministic XML fixtures so
  `SILV_STATE` is now part of the enforced export contract alongside `ORIGIN`
  and `RETENTION`.
- Added instance scaffolding templates for future CT/fert work:
  - `src/femic/resources/instance/config/silviculture.case_template.yaml`
  - `external/femic-k3z-instance/config/silviculture.k3z.yaml`
- Kept behavior intentionally non-disruptive for this slice: no CT/fert
  treatments or curve synthesis are active yet; this change only establishes
  the config/state plumbing needed for the next implementation pass.

## 2026-03-20 - Added Phase 22 CT/QMD treatment-mechanics slice for the optional K3Z variant
- Pivoted treatment-path state semantics from atomic placeholders to stacked
  path labels that match the current K3Z regeneration logic:
  - `baseline`
  - `cc_pl`
  - `cc_pl_ct`
  - `cc_pl_ct_f1`
  - `cc_pl_ct_f1_f2`
  - `cc_pl_ct_f1_f2_f3`
- Added support for multiple track treatments on a single Patchworks select so
  planted baseline tracks can expose both `CC` and `CT` where eligible.
- Added provisional QMD curve synthesis and exported QMD feature-account
  surface for K3Z: `feature.QMD.managed.<au_id>` and
  `feature.QMD.unmanaged.<au_id>`.
- Implemented the first commercial thinning treatment pass for the two initial
  K3Z AUs (`985502001`, `985502002`):
  - planted-only gating via `ORIGIN='planted'`,
  - per-AU CT age (default 40),
  - configurable BA-removal fraction and BA:volume conversion,
  - CT product/account emission including species-wise and total harvested
    volume outputs.
- Added provisional post-CT residual-yield logic by subtracting CT harvested
  volume at treatment age from the planted baseline total-yield curve, keeping
  the no-CT endpoint approximately conserved.
- Regenerated the K3Z variant ForestModel XML and patched the validated
  fragments shapefile to include `SILV_STATE`, then verified a green Windows
  Matrix Builder smoke on the optional instance branch:
  - `python -m femic patchworks matrix-build --config config/patchworks.runtime.windows.yaml --instance-root external/femic-k3z-instance --run-id k3z_ct_qmd_smoke_20260320`
  - result: `returncode=0`, `Managed=1692.2475729276887`,
    `Passive=89.06566313006975`
- Generated K3Z tracks now include `CT` treatment rows, CT harvested-volume
  products, and the provisional QMD account surface.

## 2026-03-20 - Completed Phase 22 fert-chain smoke on the optional K3Z CT/fert variant
- Extended the Phase 22 optional K3Z silviculture variant so the CT path now carries the full provisional fertilization chain: `F1`, `F2`, and `F3`.
- Added YAML-driven fertilization sequencing and temporary growth-response curve synthesis in `src/femic/fmg/patchworks.py`, keeping `ORIGIN` reserved for natural/planted semantics while `SILV_STATE` carries the stacked treatment path.
- Added a CT timing guard so effective CT age is reduced to at most `F1_age - 10` when needed, ensuring there is enough room for the full CT -> F1 -> F2 -> F3 sequence within a rotation.
- Regenerated the optional K3Z variant ForestModel XML and recompiled the Patchworks tracks with a fresh Windows Matrix Builder run:
  - `python -m femic patchworks matrix-build --config config/patchworks.runtime.windows.yaml --instance-root external/femic-k3z-instance --run-id k3z_ct_f123_rerun_20260320`
- Fresh smoke evidence captured in:
  - `external/femic-k3z-instance/vdyp_io/logs/patchworks_matrixbuilder_stdout-k3z_ct_f123_rerun_20260320.log`
  - `external/femic-k3z-instance/vdyp_io/logs/patchworks_matrixbuilder_stderr-k3z_ct_f123_rerun_20260320.log`
  - `external/femic-k3z-instance/vdyp_io/logs/patchworks_matrixbuilder_manifest-k3z_ct_f123_rerun_20260320.json`
- Verified compiled K3Z outputs now materialize the full treatment chain in tracks/accounts/products, including `CT`, `F1`, `F2`, and `F3`.
- Downstream live-Patchworks smoke also passed: pulling on the `F3` treated-area target induced the expected earlier treatment chain (`F2`, `F1`, `CT`, `CC`) across prior time steps.

## 2026-03-20 - Updated standalone K3Z docs for OG and optional CT/fert variant
- Expanded the standalone `femic-k3z-instance` Sphinx docs so they now describe both the current old-growth account surface and the optional CT/QMD/fertilization teaching variant.
- Updated these K3Z docs pages:
  - `docs/getting-started.rst`
  - `docs/model-anatomy.rst`
  - `docs/assumptions-registry.rst`
  - `docs/base-case-analysis.rst`
  - `docs/operator-runbook.rst`
  - `docs/edit-policy-and-scenarios.rst`
  - `docs/rebuild-and-qa.rst`
  - `docs/metadata-and-lineage.rst`
- Added explicit documentation for:
  - Phase 21 old-growth surfaces (`feature.Area.og1.*`, `feature.Area.og2.*`) and current `og1`/`og2` curve semantics,
  - optional branch workflow for `feature/k3z-ct-fert-treatment-option`,
  - `SILV_STATE` treatment-path semantics,
  - provisional QMD outputs,
  - CT/F1/F2/F3 compiled-surface and live-Patchworks smoke expectations.
- Validation passed:
  - `python -m sphinx -b html external/femic-k3z-instance/docs external/femic-k3z-instance/docs/_build/html -W`


## 2026-03-21 - Added a coexisting K3Z PCT->CT variant scaffold
- Extended the Phase 22 coexistence design so K3Z now supports a third upstream-distinct variant alongside `baseline` and `ctfert`: `pctct`.
- Added parent-side `pre_commercial_thinning` silviculture support in `src/femic/fmg/patchworks.py`, including new `SILV_STATE` values (`cc_pl_pct`, `cc_pl_pct_ct`), PCT gating, and post-PCT conifer-only managed species surfaces that remove the HW ingress component before CT.
- Added K3Z instance variant assets for `pctct`:
  - `config/patchworks.variant.pctct.yaml`
  - `config/patchworks.runtime.pctct.windows.yaml`
  - `config/silviculture.k3z.pctct.yaml`
  - `models/k3z_patchworks_model/analysis/pctct.pin`
  - `models/k3z_patchworks_model/yield/forestmodel_pctct.xml`
  - `models/k3z_patchworks_model/tracks_pctct/`
  - `output/patchworks_k3z_pctct_validated/`
- Windows Matrix Builder smoke passed for the new variant:
  - `python -m femic patchworks matrix-build --instance-root external/femic-k3z-instance --config config/patchworks.runtime.pctct.windows.yaml --run-id k3z_pctct_smoke_20260321`
- Verified the compiled `tracks_pctct` surface contains the intended `PCT -> CT -> CC` path and does not materialize any fertilization treatments.
- Hardened `pctct.pin` and `ctfert.pin` map-layer styling to use simple solid colors instead of unsupported patterned BeanShell symbol constants, then confirmed `pctct.pin` launches and a quick Patchworks smoke shows `CT` pulls on `PCT` and `CC` in earlier periods as expected.
- Updated the standalone K3Z docs/runbook pages so baseline, `ctfert`, and `pctct` are all documented as coexisting config/PIN-driven variants inside one instance checkout.

## 2026-03-21 - Locked K3Z onto real TIPSY managed curves + relaxed VDYP smoothing policy
- Switched both K3Z run-profile copies to `managed_curve_mode: tipsy`, replacing the previous `vdyp_transform` teaching baseline.
- Regenerated the K3Z `tipsy_vdyp_tsak3z-*.png` comparison plots from the accepted real-TIPSY handoff.
- Locked in the current relaxed unmanaged smoothing policy (looser toe/tail defaults plus stronger `CWHvm_DR+HW` overrides) as the working K3Z checkpoint for now.
- Updated K3Z docs to reflect the real-TIPSY baseline and removed treated-curve figure references for the fully retained `CWHvm_CW+YC` and `CWHvm_CW+PLC` AUs.

## 2026-03-21 - Codified the Phase 23 K3Z Windows/TIPSY teaching baseline
- Documented the known-good Windows K3Z bootstrap path in the parent Phase 23 guides and marked `P23.2c`, `P23.2d`, `P23.2e`, and `P23.5d` complete in the roadmap.
- Updated the parent Stage 01a guide so the accepted K3Z teaching baseline is explicit: real BatchTIPSY managed curves, `CWHvm_CW+YC` / `CWHvm_CW+PLC` excluded from the treated path, `RETENTION = 1.0` for those low-yield strata, and the simplified treated species-mix logic for the remaining AUs.
- Synced the standalone K3Z instance config/docs to that same baseline by switching `config/run_profile.k3z.yaml` to `managed_curve_mode: tipsy`, updating `config/tipsy/tsak3z.yaml`, and refreshing the user-facing docs (`assumptions-registry.rst`, `getting-started.rst`, `operator-runbook.rst`, `rebuild-and-qa.rst`, and `figure-appendix.rst`).
- Cleaned the K3Z figure appendix so treated overlays are described as real TIPSY-vs-VDYP comparisons and no longer list the excluded low-yield treated AUs `22006` and `22008`.
- Validation passed:
  - `python -m sphinx -b html external/femic-k3z-instance/docs external/femic-k3z-instance/docs/_build/html -W`


## 2026-03-21 - Hardened Windows case preflight for shared assets and annex-backed data
- Updated `src/femic/cli/main.py` so Windows case preflight resolves shared runtime assets from the FEMIC source tree when they are not duplicated inside the instance root, matching the real K3Z workstation layout for `tipsy_params_columns`, `vdyp_io/VDYP_CFG`, `VDYP7Console.exe`, and `ria_maptiles.csv`.
- Added Windows runtime prerequisite checks for `git` and `git-annex` in `_preflight_checks(...)`.
- Added annex/DataLad smoke checks for annex-backed public data during `prep validate-case` whenever the active case depends on paths under `external/femic-public-data`.
- Verified the real Windows K3Z command now passes again: `python -m femic prep validate-case --instance-root external/femic-k3z-instance --run-config config/run_profile.k3z.yaml` (with `FEMIC_EXTERNAL_DATA_ROOT` pointing at `external/femic-public-data/data`).
- Added focused regression coverage in `tests/test_cli_main.py` for source-root fallback, missing `git-annex`, and annex/DataLad smoke behavior.

## 2026-03-21 - Locked the Windows K3Z clean-start and resume boundary into tests and docs
- Added explicit regression coverage in `tests/test_vdyp_stage.py` for native Windows VDYP command assembly, including `-c <VDYP_CFG>` injection and trailing-slash handling for the config directory.
- Updated parent docs to show the exact known-good Windows K3Z clean-start path from the FEMIC checkout: `femic run` to the BatchTIPSY freshness boundary, then `femic tsa post-tipsy` as the intended downstream resume point.
- Marked `P23.2a` and `P23.2b` complete now that the native-Windows command path is tested and the operator-facing clean-start/resume sequence is documented explicitly.

## 2026-03-21 - Added a cross-platform smoke and acceptance guide for Phase 23
- Added `docs/guides/cross-platform-runtime-smoke.rst` as the user-facing Phase 23 guide for Windows and Linux runtime rituals, smoke workflows, and acceptance criteria.
- Wired the new guide into the guides index and deployment-instance docs so operators can find the cross-platform contract from the normal docs path.
- Marked `P23.5a`, `P23.5b`, and `P23.5c` complete now that the smoke workflows and acceptance gate are written down explicitly.


## 2026-03-21 - Hardened fresh-clone dev bootstrap and DataLad materialization guidance (P23.6)
- Added an explicit agent startup checklist in `AGENTS.md` so fresh-clone work always begins with:
  - local `.venv` activation,
  - editable dev install (`python -m pip install -r requirements-dev.txt`),
  - toolchain smoke checks,
  - DataLad/git-annex/arbutus-s3 bootstrap,
  - `FEMIC_EXTERNAL_DATA_ROOT` export before case preflight/runs.
- Added a dedicated user-facing guide: `docs/guides/developer-environment-bootstrap.rst`, and linked it in `docs/guides/index.rst`.
- Updated user-facing runtime/runbook docs to make annex payload materialization requirements explicit (`git annex enableremote arbutus-s3` + `datalad get -r external/femic-public-data/data`):
  - `README.md`
  - `docs/guides/geospatial-runtime-bootstrap.rst`
  - `docs/guides/public-data-mirror-runbook.rst`
  - `docs/guides/deployment-instances.rst`
  - `docs/guides/cross-platform-runtime-smoke.rst`
  - `docs/guides/stage-01a-vdyp-tipsy-input.rst`
  - `docs/guides/stage-01b-post-tipsy.rst`
  - `docs/guides/pipeline-overview.rst`
- Added packaging affordances so fresh-clone setup is one command:
  - new `requirements-dev.txt` (`-e .[dev]`)
  - new `project.optional-dependencies.dev` in `pyproject.toml`
  - `requirements.txt` now includes `datalad[full]`.
- Fixed small gating regressions uncovered while running mandatory checks:
  - typing fixes in `src/femic/pipeline/tipsy.py`, `src/femic/workflows/legacy.py`, and `src/femic/cli/main.py`
  - docs-contract compatibility update in `tests/test_docs_contract.py` for the K3Z figure appendix treated-curve heading rename.
- Validation passed in repo-local `.venv`:
  - `ruff format src tests`
  - `ruff check src tests`
  - `mypy src`
  - `pytest`
  - `pre-commit run --all-files`
  - `sphinx-build -b html docs _build/html -W`

## 2026-03-21 - Re-ran Linux Phase 23 parity checks after restoring git-annex/DataLad runtime
- Completed Linux-side runtime bootstrap recovery before parity rerun:
  - installed OS-level `git-annex` (`sudo apt-get install -y git-annex`),
  - enabled annex special remote in the linked public-data dataset (`git -C external/femic-public-data annex enableremote arbutus-s3`),
  - materialized annex-backed payloads (`datalad get -r external/femic-public-data/data`) so VRI/SiteProd/TSA geodatabases are locally present.
- Re-ran `P23.3a` on Linux using an isolated K3Z instance clone:
  - `femic run --instance-root <tmp_k3z_clone> --run-config config/run_profile.k3z.yaml --run-id k3z_linux_p233a_20260321_r2`
  - preflight passed, but Stage 00 failed before VDYP launch with:
    - `FileNotFoundError: ArcRasterRescue executable not found: ../ArcRasterRescue/build/arc_raster_rescue.exe`
  - run manifest captured at:
    - `<tmp_k3z_clone>/vdyp_io/logs/run_manifest-k3z_linux_p233a_20260321_r2.json` (`status=failed`, `exit_code=1`).
- Re-ran `P23.3b` on Linux using an isolated K3Z instance clone:
  - `femic tsa post-tipsy --instance-root <tmp_k3z_clone> --run-config config/run_profile.k3z.yaml --tsa k3z --run-id k3z_linux_p233b_20260321_r2`
  - failed with the existing freshness guard:
    - `Stale BatchTIPSY output detected: .../04_output-tsak3z.out is older than .../tipsy_params_tsak3z.xlsx`
  - run manifest captured at:
    - `<tmp_k3z_clone>/vdyp_io/logs/run_manifest-k3z_linux_p233b_20260321_r2.json` (`status=failed`, `exit_code=1`).
- Phase 23 Linux parity remains open (`P23.3a`, `P23.3b`, `P23.3c`) with two explicit blockers now recorded in `ROADMAP.md`:
  - missing Linux-usable ArcRasterRescue boundary for Stage 00 SiteProd processing,
  - stale BatchTIPSY output relative to current handoff artifacts for post-TIPSY resume.

## 2026-03-21 - Applied ArcRasterRescue/TIPSY boundary fixes and reran Linux parity checks
- Implemented runtime fixes to align with existing project workflow rather than inventing new behavior:
  - ArcRasterRescue executable resolution now supports `FEMIC_ARC_RASTER_RESCUE_EXE` plus source-root/instance-root fallback resolution.
  - ArcRasterRescue FileGDB invocation now normalizes the `.gdb/` argument form required by the patched fork tooling.
  - `run_vdyp_for_stratum(...)` now resolves relative `vdyp_binpath` via `FEMIC_SOURCE_ROOT` fallback (matching existing params fallback behavior).
- Implemented TIPSY freshness-policy corrections:
  - `02_input-tsaXX.dat` is now authoritative for stale detection.
  - freshness checks now support DAT-hash sidecars (`04_output-tsaXX.out.input_sha256`) so unchanged DAT content does not repeatedly force manual BatchTIPSY reruns.
  - Stage 01b now skips BatchTIPSY freshness gating when `managed_curve_mode != tipsy` (`vdyp_transform` path).
- Added/updated regression coverage:
  - `tests/test_siteprod.py` for ArcRasterRescue source-root/env-override resolution and `.gdb/` invocation normalization.
  - `tests/test_tipsy.py` for DAT fingerprint acceptance/mismatch behavior and sidecar write behavior.
  - `tests/test_vdyp_stage.py` for `FEMIC_SOURCE_ROOT` fallback of relative VDYP executable paths.
- Updated docs/agent guidance:
  - `AGENTS.md`
  - `docs/guides/stage-00-data-prep.rst`
  - `docs/guides/stage-01a-vdyp-tipsy-input.rst`
  - `docs/guides/stage-01b-post-tipsy.rst`
  - `docs/guides/geospatial-runtime-bootstrap.rst`
  - `docs/guides/cross-platform-runtime-smoke.rst`
- Linux rerun evidence after these fixes:
  - `P23.3a` command `femic run ... --run-id k3z_linux_p233a_20260321_r4` progressed through SiteProd extraction and pre-VDYP checkpointing, then failed with
    `RuntimeError: VDYP executable not found: /tmp/femic_p23a_r4_Ch5Y9R/VDYP7/VDYP7/VDYP7Console.exe`
    (manifest: `/tmp/femic_p23a_r4_Ch5Y9R/vdyp_io/logs/run_manifest-k3z_linux_p233a_20260321_r4.json`, `status=failed`, `exit_code=1`).
  - `P23.3b` command `femic tsa post-tipsy ... --run-id k3z_linux_p233b_20260321_r5_only` no longer failed at stale-TIPSY freshness checks, but failed later in 01b plotting/indexing with
    `KeyError: 'L'` from `vdyp_curves_by_scsi.loc[sc, si_level]`
    (manifest: `/tmp/femic_p23b_r5_dC7Rio/vdyp_io/logs/run_manifest-k3z_linux_p233b_20260321_r5_only.json`, `status=failed`, `exit_code=1`).
- Phase 23 remains open pending final Linux end-to-end confirmation for `P23.3a` and resolution/characterization of the new `P23.3b` plotting/index mismatch blocker.

## 2026-03-21 - Completed Linux P23.3b post-TIPSY parity rerun and hardened 01b plotting resilience
- Added two additional 01b runtime guards in `src/femic/resources/legacy/01b_run-tsa.py`:
  - missing `(stratum_code, si_level)` comparison keys in `vdyp_curves_by_scsi` now warn and continue,
  - missing AU->(stratum, SI) map entries now warn and continue without aborting the whole post-TIPSY run.
- Added regression coverage for 01b overlay guard behavior:
  - `tests/test_legacy_01b_runtime.py`.
- Linux verification:
  - `femic tsa post-tipsy --instance-root /tmp/femic_p23b_r5_dC7Rio --run-config config/run_profile.k3z.yaml --tsa k3z --run-id k3z_linux_p233b_20260321_r8`
  - result: success (`post-tipsy completed`), bundle tables regenerated, comparison plots regenerated.
  - manifest: `/tmp/femic_p23b_r5_dC7Rio/vdyp_io/logs/run_manifest-k3z_linux_p233b_20260321_r8.json`.
- Phase status:
  - `P23.3b` can now be marked complete from Linux evidence.
  - `P23.3a` remains pending final clean-start Stage 01a->BatchTIPSY boundary confirmation.
- Additional bounded `P23.3a` check:
  - attempted `timeout 900 femic run --instance-root /tmp/femic_p23a_r6_KpHxKg --run-config config/run_profile.k3z.yaml --run-id k3z_linux_p233a_20260321_r6_resume --resume`,
  - run remained in long-running Stage 00 legacy execution and did not reach a terminal boundary within the timeout window; process was terminated and `P23.3a` remains open.

## 2026-03-21 - Narrowed Linux P23.3a root cause and added source-root runtime-asset staging
- Root cause from Linux `P23.3a` reruns was narrowed from generic “missing VDYP output” to a concrete runtime-path seam:
  - bootstrap dispatch calls ran,
  - `vdyp_stderr` repeatedly reported `FATAL: VDYP7 Configuration Folder ('-c') has not been supplied`,
  - generated `vdyp_out_*.out` files were empty, so two-pass SI rebin mapped `0/46`.
- Confirmed behavior by direct replay:
  - same captured VDYP command failed from `/tmp` instance roots,
  - replay succeeded from source root and produced non-empty `vdyp_out` output,
  - indicating legacy relative runtime assets (`./vdyp_io/VDYP_CFG`, `./vdyp_io/VDYP.INI`) were missing in temp instance clones.
- Implemented runtime hardening in `src/femic/pipeline/vdyp_stage.py`:
  - added `ensure_local_vdyp_runtime_assets(...)`,
  - wired `run_vdyp_for_stratum(...)` to stage missing `vdyp_io/VDYP_CFG` and `vdyp_io/VDYP.INI` from `FEMIC_SOURCE_ROOT` before Wine VDYP dispatch.
- Added Linux clone resilience for Stage 00 in `src/femic/resources/legacy/00_data-prep.py`:
  - when instance-local `data/tipsy_params_columns` is missing, fallback now resolves from `$FEMIC_SOURCE_ROOT/data/tipsy_params_columns`.
- Added/updated regression/docs/roadmap artifacts:
  - `tests/test_vdyp_stage.py`: `test_ensure_local_vdyp_runtime_assets_stages_cfg_and_ini`.
  - docs updates: `docs/guides/geospatial-runtime-bootstrap.rst`, `docs/guides/cross-platform-runtime-smoke.rst`, `docs/guides/stage-01a-vdyp-tipsy-input.rst`.
  - roadmap updates: `ROADMAP.md` (`P23.3a` blocker text + Detailed Next Steps evidence entry).
- Status:
  - targeted tests for the new staging seam pass,
  - full clean-start Linux `P23.3a` run to the BatchTIPSY handoff boundary is still pending final confirmation.

## 2026-03-21 - Linux P23.3a clean-start rerun still blocked before VDYP boundary
- Executed a fresh Linux `P23.3a` clean-start verification run after landing source-root runtime-asset staging fixes:
  - tmp instance: `/tmp/femic_p23a_final_bF2EN4`
  - run id: `k3z_linux_p233a_20260321_r13_final`
  - command: `python -m femic run --instance-root /tmp/femic_p23a_final_bF2EN4 --run-config config/run_profile.k3z.yaml --run-id k3z_linux_p233a_20260321_r13_final`
- Preflight checks passed:
  - `python -m femic prep validate-case --instance-root /tmp/femic_p23a_final_bF2EN4 --run-config config/run_profile.k3z.yaml`
  - `python -m femic prep geospatial-preflight`
- Observed blocker:
  - run advanced through ArcRasterRescue extraction logs up to `... processing species SW`,
  - then produced no additional progress logs for multiple minutes,
  - no `vdyp_runs-...jsonl` / `vdyp_stderr-...log` artifacts were created for the run id,
  - no active ArcRasterRescue child process remained,
  - process was manually interrupted to avoid indefinite runtime.
- Evidence:
  - shell log: `/tmp/femic_p23a_r13_final.log`
  - manifest: `/tmp/femic_p23a_final_bF2EN4/vdyp_io/logs/run_manifest-k3z_linux_p233a_20260321_r13_final.json` (left in `status=started` after interruption).
- Phase status impact:
  - `P23.3b` remains complete,
  - `P23.3a` and Linux sign-off for `P23.3c` remain open pending a clean run that reaches Stage 01a -> BatchTIPSY handoff.

## 2026-03-21 - Added fail-fast Stage 00 ArcRasterRescue diagnostics and corrected SW-stall interpretation
- Hardened `src/femic/pipeline/siteprod.py` ArcRasterRescue export behavior:
  - added per-layer launch/completion diagnostics with elapsed time,
  - added timeout-bounded execution (`FEMIC_ARC_RASTER_RESCUE_TIMEOUT_SEC`, default `900`),
  - added explicit `RuntimeError` on timeout/non-zero returncode with species/layer and stderr context.
- Improved legacy stage streaming observability:
  - `src/femic/pipeline/io.py` now sets `PYTHONUNBUFFERED=1` by default in legacy execution env.
- Added regression coverage:
  - `tests/test_siteprod.py` now covers timeout and non-zero ArcRasterRescue failure diagnostics.
  - `tests/test_pipeline_helpers.py` now asserts `PYTHONUNBUFFERED=1` in execution-plan env.
- Validation:
  - `ruff check` passed on touched files,
  - targeted tests passed (`test_siteprod` export-stack diagnostics and execution-plan env assertion).
- Linux diagnostic rerun outcome (`k3z_linux_p233a_20260321_r15_diag_unbuffered`, `/tmp/femic_p23a_diag2_P0qEiG`):
  - corrected previous interpretation that Stage 00 was stuck at `species SW`;
  - artifact evidence showed progression beyond ArcRasterRescue export:
    - temp `site_prod_bc_*.tif` files dropped to zero,
    - `data/siteprod.tif` grew to full stacked output,
    - `data/ria_vri_vclr1p_checkpoint2.feather` and `...checkpoint3.feather` were created.
  - run was manually interrupted before reaching VDYP/TIPSY handoff boundary to keep iteration bounded.

## 2026-03-21 - Linux P23.3a converged to expected BatchTIPSY boundary; P23.3 parity closed
- Executed a full uninterrupted Linux clean-start `P23.3a` rerun:
  - tmp instance: `/tmp/femic_p23a_finalrun_rC45UW`
  - run id: `k3z_linux_p233a_20260321_r16_full`
  - log: `/tmp/femic_p23a_r16_full.log`
  - manifest: `/tmp/femic_p23a_finalrun_rC45UW/vdyp_io/logs/run_manifest-k3z_linux_p233a_20260321_r16_full.json`
- Observed terminal behavior confirms expected Stage 01a contract:
  - ArcRasterRescue completed all species exports and stacking,
  - Stage 00 checkpoints regenerated (`checkpoint2`, `checkpoint3`, `checkpoint4`, `vdyp_prep-tsak3z.pkl`),
  - VDYP bootstrap + two-pass SI rebin completed (`mapped VDYP SI for 38/46 rows`, rebuilt bins `missing=0 of 114`),
  - run terminated at expected BatchTIPSY freshness boundary:
    `RuntimeError: Stale BatchTIPSY output detected: data/04_output-tsak3z.out is older than data/02_input-tsak3z.dat`.
- Interpretation:
  - this is the intended Stage 01a handoff boundary behavior, not a Linux runtime crash.
- Phase status update:
  - `P23.3a` marked complete with real Linux evidence,
  - `P23.3c` Linux parity sign-off marked complete (with prior `P23.3b` pass),
  - top-level `P23.3` parity work is now closed.

## 2026-03-22 - Added coherence-based TIPSY timestamp mismatch handling (warn-by-default, strict override available)
- Implemented `P23.7` to reduce false-positive Stage 01b halts during dev/test loops when BatchTIPSY output is structurally coherent with current inputs.
- Updated `src/femic/pipeline/tipsy.py` freshness behavior:
  - added `assess_tipsy_input_output_coherence(...)` to compare input/output structure using:
    - expected AUs/tables from `TIPSY_inputTBL` (`AU`, `TBLno`, `SI>0`),
    - observed table IDs from `04_output-tsaXX.out`.
  - when DAT is newer than output and no DAT fingerprint sidecar exists:
    - coherent pair => default warning and continue,
    - incoherent pair => hard error (existing fail-fast behavior).
  - added strict override flag path in validator (`strict_timestamp_mismatch`) so coherent timestamp mismatch can still be treated as an error.
- Wired strict override env switch through Stage 01b runtime:
  - `FEMIC_STRICT_TIPSY_TIMESTAMP_MISMATCH=1` in `src/femic/resources/legacy/01b_run-tsa.py`.
- Kept existing explicit bypass intact:
  - `FEMIC_ALLOW_STALE_TIPSY_OUTPUT=1` still skips freshness gating for explicit debugging only.
- Added regression coverage in `tests/test_tipsy.py`:
  - coherent stale pair warns-and-continues by default,
  - coherent stale pair raises in strict mode,
  - missing table/AU coverage reports incoherent outcome.
- Updated user-facing docs:
  - `docs/guides/stage-01b-post-tipsy.rst` now documents coherence-based default behavior and strict override usage.

## 2026-03-22 - Fixed THLB raster fallback for Linux tmp-clone parity reruns (P23.8)
- Added `resolve_legacy_thlb_raster_path(...)` in `src/femic/pipeline/io.py`:
  - prefer instance-local `data/misc.thlb.tif`,
  - fallback to `FEMIC_EXTERNAL_DATA_ROOT/misc.thlb.tif` when instance-local raster is absent.
- Updated `src/femic/resources/legacy/00_data-prep.py`:
  - now resolves THLB raster path through fallback helper,
  - logs selected THLB source path and explicit fallback context,
  - post-01b THLB assignment now uses resolved path rather than assuming instance-local raster is always present.
- Added regression coverage in `tests/test_pipeline_io.py`:
  - instance path precedence,
  - external fallback when instance path is missing,
  - deterministic behavior when both are missing.
- Updated docs: `docs/guides/stage-00-data-prep.rst` now states THLB raster resolution order for tmp-clone workflows.
- Verification evidence:
  - `pytest -q tests/test_pipeline_io.py` -> `3 passed`.
  - `femic tsa post-tipsy --instance-root /tmp/femic_p23a_live_session_ax08cp --run-config config/run_profile.k3z.yaml --tsa k3z --run-id k3z_linux_p238_thlbfix_20260322` -> `RC=0` (`post-tipsy completed`).
  - bounded full-run replay logs now show fallback path selection (`using THLB raster source (fallback): .../external/femic-public-data/data/misc.thlb.tif`) and no longer fail immediately at `misc.thlb.tif` missing-path boundary before timeout.

## 2026-03-22 - Published canonical SiteProd TIFF to femic-public-data (P23.9)
- Copied known-good Linux parity SiteProd artifact into DataLad dataset:
  - source: `/tmp/femic_p23a_finalrun_rC45UW/data/siteprod.tif`
  - destination: `external/femic-public-data/data/bc/siteprod/siteprod.tif`
  - SHA256 verified equal for source/destination:
    `307c177608a93b57b8df6d743256651fc8e50399753cbbcf34f97b876b6f926d`.
- Saved and pushed dataset history:
  - `datalad save` commit in `femic-public-data`: `b73dba7290e28ae893cc13e9a1ecbacd15b39904`
  - pushed to GitHub `UBC-FRESH/femic-public-data` `main`
  - pushed `git-annex` metadata branch.
- Uploaded annex payload to cloud special remote:
  - `git annex copy --to arbutus-s3 data/bc/siteprod/siteprod.tif`
  - verified `git annex whereis` includes `arbutus-s3`
  - verified missing-copy check is zero:
    `git annex find data/bc/siteprod/siteprod.tif --not --in arbutus-s3` -> none.

## 2026-03-22 - Published SiteProd band-map sidecar for pre-stacked TIFF runtime (P23.10)
- Added canonical machine-readable sidecar:
  - `external/femic-public-data/data/bc/siteprod/siteprod.bandmap.json`
  - includes `bands_1_based`, `bands_0_based`, and `ordered_species` for `siteprod.tif`.
- Mapping derivation:
  - species set from `list_siteprod_layers(...)` against `Site_Prod_BC.gdb`;
  - order set to lexicographic species-code order, matching stacked TIFF assembly semantics (`site_prod_bc_<SPECIES>.tif` sorted glob order).
  - validated against published `siteprod.tif` band count (`22`).
- Saved and pushed DataLad dataset update:
  - `femic-public-data` commit: `b23ce8290862915b518322cbf59f6c92f2d46654`
  - pushed to GitHub `main`
  - pushed `git-annex` metadata branch.
- Distribution note:
  - `siteprod.bandmap.json` is Git-tracked text (not annexed), so it is distributed via GitHub branch sync rather than `arbutus-s3` annex object transfer.

## 2026-03-22 - Added curated API docs for femic.pipeline.vdyp_stage (Phase 24 P24.1d/P24.1e)
- Replaced the autosummary-only `femic.pipeline.vdyp_stage` landing page with a hand-authored API page:
  - `docs/reference/api/femic-pipeline-vdyp-stage.rst`
- Documented the module's:
  - Stage 01a role and operational boundaries
  - main sub-flows from input loading through batch execution, bootstrap orchestration, and curve smoothing
  - key entrypoints, runtime contracts, artifacts, and common failure seams
  - cross-links back to the relevant guides and supporting API modules
- Updated `docs/reference/api/modules.rst` so the curated page is the visible high-priority module page while the generated autodoc page remains reachable through a hidden toctree.
- Repaired `ROADMAP.md` encoding corruption and refreshed the Detailed Next Steps notes so Phase 24 is the active leading-edge plan again.
- Verification:
  - `C:\Users\gep\projects\femic\.venv\Scripts\python.exe -m sphinx -b html docs _build\html -W` completed successfully.

## 2026-03-22 - Clarified bundled example-instance maintenance and scripted bootstrap docs (Phase 24 P24.2b/P24.2d)
- Expanded `docs/guides/developer-environment-bootstrap.rst` with copy-paste Linux/macOS and Windows PowerShell bootstrap scripts covering:
  - local `.venv` creation/activation
  - editable dev dependency install
  - toolchain verification
  - submodule and DataLad materialization
  - `FEMIC_EXTERNAL_DATA_ROOT` export
  - preflight checks against the bundled K3Z instance
- Expanded `docs/guides/deployment-instances.rst` to document how the bundled example instances under `external/` should actually be maintained:
  - clarified that `external/femic-k3z-instance` and `external/femic-tsa29-instance` are submodules, not ordinary sample folders
  - documented the amend/rebuild loop for bundled instances
  - explained the parent-repo vs submodule-repo commit boundary
  - linked the bundled-instance release flow back to each instance-local rebuild runbook
- Updated `README.md` so repo-root readers see the same Linux/Windows bootstrap commands and the same `external/` amend/rebuild workflow without needing to infer it from scattered docs pages.
- Refreshed `ROADMAP.md` Detailed Next Steps notes so this bundled-instance/source-of-truth docs pass is tracked as active Phase 24 work.
- Verification:
  - `C:\Users\gep\projects\femic\.venv\Scripts\python.exe -m sphinx -b html docs _build\html -W` completed successfully.

## 2026-03-22 - Added curated API docs for femic.pipeline.io (Phase 24 P24.1d/P24.1e)
- Replaced the autosummary-only `femic.pipeline.io` landing page with a hand-authored API page:
  - `docs/reference/api/femic-pipeline-io.rst`
- Documented the module's:
  - role as FEMIC's path-resolution and run-configuration seam
  - main dataclass contracts and profile-normalization flow
  - external-data, SiteProd, and THLB artifact-selection rules
  - legacy subprocess env/command handoff and the main path/bootstrap failure seams
  - cross-links back to the deployment/bootstrap and run-config guides
- Updated `docs/reference/api/modules.rst` so the curated `femic.pipeline.io` page is the visible high-priority module page while the generated autodoc page remains reachable through a hidden toctree.
- Refreshed `ROADMAP.md` Detailed Next Steps notes so the `femic.pipeline.io` rewrite is tracked as active Phase 24 work.
- Verification:
  - `C:\Users\gep\projects\femic\.venv\Scripts\python.exe -m sphinx -b html docs _build\html -W` completed successfully.

## 2026-03-22 - Added curated API docs for femic.pipeline.tipsy (Phase 24 P24.1d/P24.1e)
- Replaced the autosummary-only `femic.pipeline.tipsy` landing page with a hand-authored API page:
  - `docs/reference/api/femic-pipeline-tipsy.rst`
- Documented the module's:
  - BatchTIPSY handoff role across the Stage 01a/01b boundary
  - canonical DAT-vs-XLSX contract and fixed-width export rules
  - candidate evaluation and per-AU parameter generation flow
  - freshness, fingerprint, and coherence-based stale-output acceptance logic
  - main operator/debugging failure seams around DAT layout and stale `04_output` reuse
- Updated `docs/reference/api/modules.rst` so the curated `femic.pipeline.tipsy` page is the visible high-priority module page while the generated autodoc page remains reachable through a hidden toctree.
- Refreshed `ROADMAP.md` Detailed Next Steps notes so the `femic.pipeline.tipsy` rewrite is tracked as active Phase 24 work.
- Verification:
  - `C:\Users\gep\projects\femic\.venv\Scripts\python.exe -m sphinx -b html docs _build\html -W` completed successfully.

## 2026-03-22 - Added curated API docs for femic.fmg.patchworks (Phase 24 P24.1d/P24.1e)
- Replaced the autosummary-only `femic.fmg.patchworks` landing page with a hand-authored API page:
  - `docs/reference/api/femic-fmg-patchworks.rst`
- Documented the module's:
  - role as FEMIC's Patchworks export synthesis layer
  - top-level export flow from bundle/checkpoint surfaces into `forestmodel.xml` and fragments shapefile outputs
  - main contract surfaces around curve derivation, fragment field requirements, IFM/origin/silviculture state wiring, and retention handling
  - distinction between export-time validation here and later runtime launch in `femic.patchworks_runtime`
  - main failure seams around fragments validation, XML structure drift, IFM assignment, and config misuse
- Updated `docs/reference/api/modules.rst` so the curated `femic.fmg.patchworks` page is the visible high-priority module page while the generated autodoc page remains reachable through a hidden toctree.
- Refreshed `ROADMAP.md` Detailed Next Steps notes so the `femic.fmg.patchworks` rewrite is tracked as active Phase 24 work.
- Verification:
  - `C:\Users\gep\projects\femic\.venv\Scripts\python.exe -m sphinx -b html docs _build\html -W` completed successfully.

## 2026-03-22 - Added curated API docs for femic.patchworks_runtime (Phase 24 P24.1d/P24.1e)
- Replaced the autosummary-only `femic.patchworks_runtime` landing page with a hand-authored API page:
  - `docs/reference/api/femic-patchworks-runtime.rst`
- Documented the module's:
  - role as FEMIC's Patchworks runtime/preflight/launch seam after export synthesis
  - host-mode split between native Windows and Wine/Linux execution
  - runtime config, preflight, command-launch, and manifest/log capture flow
  - blocks/topology preparation path and the main runtime artifacts
  - key failure seams around launcher prerequisites, license/env wiring, fatal stderr signatures, and output-not-ready conditions
- Updated `docs/reference/api/modules.rst` so the curated `femic.patchworks_runtime` page is the visible high-priority module page while the generated autodoc page remains reachable through a hidden toctree.
- Refreshed `ROADMAP.md` Detailed Next Steps notes so the `femic.patchworks_runtime` rewrite is tracked as active Phase 24 work.
- Verification:
  - `C:\Users\gep\projects\femic\.venv\Scripts\python.exe -m sphinx -b html docs _build\html -W` completed successfully.

## 2026-03-22 - Added curated API docs for femic.workflows.legacy (Phase 24 P24.1d/P24.1e)
- Replaced the autosummary-only `femic.workflows.legacy` landing page with a hand-authored API page:
  - `docs/reference/api/femic-workflows-legacy.rst`
- Documented the module's:
  - role as FEMIC's orchestration seam around the still-active legacy stage scripts
  - two main execution paths: Stage 00 subprocess launch and cached post-TIPSY 01b-plus-bundle rebuild
  - script-bundle resolution, temporary env/cwd overrides, manifest expectations, and bundle-output contracts
  - main failure seams around missing cached 01a artifacts, mis-resolved legacy script roots, and managed-curve override drift
- Updated `docs/reference/api/modules.rst` so the curated `femic.workflows.legacy` page is the visible high-priority module page while the generated autodoc page remains reachable through a hidden toctree.
- Refreshed `ROADMAP.md` Detailed Next Steps notes so the `femic.workflows.legacy` rewrite is tracked as active Phase 24 work.
- Verification:
  - `C:\Users\gep\projects\femic\.venv\Scripts\python.exe -m sphinx -b html docs _build\html -W` completed successfully.

## 2026-03-22 - Added curated API docs for femic.pipeline.siteprod (Phase 24 P24.1d/P24.1e)
- Replaced the autosummary-only `femic.pipeline.siteprod` landing page with a hand-authored API page:
  - `docs/reference/api/femic-pipeline-siteprod.rst`
- Documented the module's:
  - role as FEMIC's SiteProd species-mapping, band-map loading, fallback export, and stand-level raster-assignment seam
  - preferred canonical `siteprod.tif` + `siteprod.bandmap.json` runtime path versus ArcRasterRescue and Windows ArcGIS Pro fallback behavior
  - main contract surfaces around executable resolution, timeout behavior, FileGDB layer enumeration, temporary raster stacking, and per-stand masking
  - main failure seams around species-code drift, invalid band maps, ArcRasterRescue resolution failures, and raster masking surprises
- Updated `docs/reference/api/modules.rst` so the high-priority operational modules section is now fully curated instead of mixing curated pages with remaining autosummary-only stubs.
- Refreshed `ROADMAP.md` Detailed Next Steps notes so the `femic.pipeline.siteprod` rewrite is tracked as active Phase 24 work.
- Verification:
  - `C:\Users\gep\projects\femic\.venv\Scripts\python.exe -m sphinx -b html docs _build\html -W` completed successfully.

## 2026-03-22 - Queued bounded closure criteria for Phase 24 `P24.1d`
- Refined `ROADMAP.md` so `P24.1d` now has an explicit closure queue instead of one open-ended rewrite bucket.
- Recorded that the original first-wave high-priority operational module rewrites are already complete within `P24.1d`.
- Queued the remaining support-module rewrite bundle needed before `P24.1d` can be checked off:
  - `femic.instance_context`
  - `femic.instance_bootstrap`
  - `femic.geospatial_preflight`
  - `femic.pipeline.bundle`
  - `femic.pipeline.legacy_runtime`
  - `femic.pipeline.manifest`
- Added an explicit closure-sweep requirement so any API pages left as autosummary-only must be intentionally classified as acceptable generated-only surfaces rather than silently remaining unfinished.

## 2026-03-22 - Added curated support-module API docs for `P24.1d.2`
- Added hand-authored API pages for the remaining support modules that still carry important runtime/repo contracts:
  - `docs/reference/api/femic-instance-context.rst`
  - `docs/reference/api/femic-instance-bootstrap.rst`
  - `docs/reference/api/femic-geospatial-preflight.rst`
  - `docs/reference/api/femic-pipeline-bundle.rst`
  - `docs/reference/api/femic-pipeline-legacy-runtime.rst`
  - `docs/reference/api/femic-pipeline-manifest.rst`
- Updated `docs/reference/api/modules.rst` to add a curated support-contract modules section so those pages are visible entrypoints instead of buried as generated-only stubs.
- Marked `P24.1d.2` complete in `ROADMAP.md`; the remaining work to clear `P24.1d` is now the closure sweep and any final promotions that sweep identifies.
- Verification:
  - `C:\Users\gep\projects\femic\.venv\Scripts\python.exe -m sphinx -b html docs _build\html -W`
  - `C:\Users\gep\projects\femic\.venv\Scripts\python.exe -m ruff format src tests`
  - `C:\Users\gep\projects\femic\.venv\Scripts\python.exe -m ruff check src tests`
  - `C:\Users\gep\projects\femic\.venv\Scripts\python.exe -m mypy src`
  - `C:\Users\gep\projects\femic\.venv\Scripts\python.exe -m pytest`
  - `C:\Users\gep\projects\femic\.venv\Scripts\pre-commit.exe run --all-files`

## 2026-03-22 - Closed Phase 24 `P24.1d` with final rebuild/release API docs and closure sweep
- Added the final curated rebuild/release API pages needed to clear the remaining promoted blockers:
  - `docs/reference/api/femic-rebuild-spec.rst`
  - `docs/reference/api/femic-rebuild-baseline.rst`
  - `docs/reference/api/femic-rebuild-invariants.rst`
  - `docs/reference/api/femic-rebuild-runner.rst`
  - `docs/reference/api/femic-release-packaging.rst`
- Updated `docs/reference/api/modules.rst` and `docs/reference/api/index.rst` so the bounded curated set is explicit across operational, support-contract, and rebuild/release modules.
- Added `planning/phase24_api_docs_closure_sweep.md` to classify every remaining generated-only API page as either intentionally acceptable generated-only or promoted-and-rewritten.
- Marked `P24.1d.3`, `P24.1d.4`, `P24.1d.5`, and top-level `P24.1d` complete in `ROADMAP.md`.
- Verification:
  - `C:\Users\gep\projects\femic\.venv\Scripts\python.exe -m sphinx -b html docs _build\html -W`
  - `C:\Users\gep\projects\femic\.venv\Scripts\python.exe -m ruff format src tests`
  - `C:\Users\gep\projects\femic\.venv\Scripts\python.exe -m ruff check src tests`
  - `C:\Users\gep\projects\femic\.venv\Scripts\python.exe -m mypy src`
  - `C:\Users\gep\projects\femic\.venv\Scripts\python.exe -m pytest`
  - `C:\Users\gep\projects\femic\.venv\Scripts\pre-commit.exe run --all-files`

## 2026-03-22 - Closed Phase 24 `P24.1e` and completed the API-doc rebuild milestone
- Added concise "Typical Usage" example sections across the curated API pages so the rewritten docs now show realistic call shapes instead of only ownership/contract prose.
- Updated the curated operational, support-contract, and rebuild/release API pages to pair:
  - start-here orientation
  - pipeline-role/boundary notes
  - realistic CLI or Python entrypoint examples
- Marked `P24.1e` complete in `ROADMAP.md` and, with `P24.1a` through `P24.1e` now complete, marked top-level `P24.1` complete as well.
- Verification:
  - `C:\Users\gep\projects\femic\.venv\Scripts\python.exe -m sphinx -b html docs _build\html -W`
  - `C:\Users\gep\projects\femic\.venv\Scripts\python.exe -m ruff format src tests`
  - `C:\Users\gep\projects\femic\.venv\Scripts\python.exe -m ruff check src tests`
  - `C:\Users\gep\projects\femic\.venv\Scripts\python.exe -m mypy src`
  - `C:\Users\gep\projects\femic\.venv\Scripts\python.exe -m pytest`
  - `C:\Users\gep\projects\femic\.venv\Scripts\pre-commit.exe run --all-files`

## 2026-03-22 - Closed Phase 24 `P24.2`, `P24.3`, and `P24.4b` with contract docs, acceptance checks, and portability cleanup
- Added a compact technical-contract section in the main docs tree:
  - `docs/reference/contracts/index.rst`
  - `docs/reference/contracts/repo-runtime-invariants.rst`
  - `docs/reference/contracts/instance-and-data-roots.rst`
  - `docs/reference/contracts/stage-boundaries-and-canonical-artifacts.rst`
  - `docs/reference/contracts/recovery-and-external-runtime-boundaries.rst`
- Kept the contract layer inside the same human-facing Sphinx tree rather than creating an agent-only parallel doc system, and cross-linked it from:
  - `docs/index.rst`
  - `docs/reference/api/index.rst`
  - `README.md`
  - `AGENTS.md`
- Extended `tests/test_docs_contract.py` so the new contract pages, navigation links, and required section markers are enforced going forward.
- Swept the live docs/contributor surfaces for machine-specific path leakage and replaced hard-coded examples with portable patterns such as `$PWD`, including:
  - `AGENTS.md`
  - `docs/guides/pipeline-overview.rst`
  - `docs/guides/stage-01a-vdyp-tipsy-input.rst`
  - `docs/guides/stage-01b-post-tipsy.rst`
  - `docs/guides/cross-platform-runtime-smoke.rst`
  - `docs/guides/patchworks-wine-runtime.rst`
- Purged the remaining mojibake/garbled-text issues from `ROADMAP.md` so the Phase 24 section and older damaged lines are back to clean UTF-8 text.
- Marked `P24.2`, `P24.3`, and `P24.4b` complete in `ROADMAP.md`, and updated Detailed Next Steps to point at the remaining benchmark/gap-closeout work under `P24.4a` and `P24.4c`.
- Verification:
  - `C:\Users\gep\projects\femic\.venv\Scripts\python.exe -m ruff format src tests`
  - `C:\Users\gep\projects\femic\.venv\Scripts\python.exe -m ruff check src tests`
  - `C:\Users\gep\projects\femic\.venv\Scripts\python.exe -m mypy src`
  - `C:\Users\gep\projects\femic\.venv\Scripts\python.exe -m pytest`
  - `C:\Users\gep\projects\femic\.venv\Scripts\pre-commit.exe run --all-files`
  - `C:\Users\gep\projects\femic\.venv\Scripts\python.exe -m sphinx -b html docs _build\html -W`

## 2026-03-22 - Closed Phase 24 `P24.4a` and `P24.4c` with benchmark validation and follow-up issue draft
- Added `planning/phase24_docs_benchmark_validation.md` to benchmark the current docs against the real maintenance tasks named in the roadmap:
  - Patchworks runtime setup
  - bundled K3Z variant rebuild/amend loops
  - SiteProd default/fallback orientation
  - DataLad/public-data bootstrap
- Recorded the benchmark result that the current docs are now sufficient for those tasks without relying on undocumented tribal knowledge.
- Added `planning/phase24_docs_followup_issue.md` as the draft follow-up GitHub feature issue for the remaining non-blocking polish items:
  - a more explicit native Windows Patchworks runtime quickstart
  - a more compact operator-facing SiteProd default-resolution summary
- Marked `P24.4a`, `P24.4c`, and top-level `P24.4` complete in `ROADMAP.md`, and updated Detailed Next Steps to point at the benchmark closeout artifact instead of the earlier open plan note.
- Verification:
  - `C:\Users\gep\projects\femic\.venv\Scripts\python.exe -m ruff format src tests`
  - `C:\Users\gep\projects\femic\.venv\Scripts\python.exe -m ruff check src tests`
  - `C:\Users\gep\projects\femic\.venv\Scripts\python.exe -m mypy src`
  - `C:\Users\gep\projects\femic\.venv\Scripts\python.exe -m pytest`
  - `C:\Users\gep\projects\femic\.venv\Scripts\pre-commit.exe run --all-files`
  - `C:\Users\gep\projects\femic\.venv\Scripts\python.exe -m sphinx -b html docs _build\html -W`

## 2026-03-22 - Closed Phase 19 `P19.17` with TSA29 instance docs deep-dive
- Expanded the thin standalone TSA29 instance docs pages in `external/femic-tsa29-instance/docs/` so they now carry clearer workflow and evidence guidance:
  - `getting-started.rst`
  - `data-and-provenance.rst`
  - `land-base-and-assumptions.rst`
  - `rebuild-and-qa.rst`
  - `troubleshooting.rst`
  - `docs-ownership-and-release.rst`
- Added concrete procedural guidance for:
  - snapshot-first vs rebuild-capable use
  - authoritative provenance/evidence files
  - current published warning-state interpretation
  - known TSA29 Stage 01a Linux rebuild limitation
  - release/update ownership for the standalone TSA29 docs set
- Hardened the TSA29 standalone Sphinx config (`external/femic-tsa29-instance/docs/conf.py`) so local docs builds no longer fail hard when `sphinx_rtd_theme` is missing.
- Marked `P19.17`, `P19.17a`, `P19.17b`, and `P19.17c` complete in `ROADMAP.md`.
- Verification:
  - `C:\Users\gep\projects\femic\.venv\Scripts\python.exe -m sphinx -b html docs _build\html -W`
    with `workdir=C:\Users\gep\projects\femic\external\femic-tsa29-instance`







## 2026-03-23 - Started Phase 25 K3Z student-overlay planning for baseline-derived RETENTION subvariants
- Created `planning/msfm-rec2group-k3z-overlay.md` to define the new K3Z-only overlay workflow on branch `feature/k3z-student-overlay`.
- Added `Phase 25: K3Z Student Overlay RETENTION Subvariants` to `ROADMAP.md` so the work is tracked outside chat, with tasks covering:
  - student-overlay source/import contract and `FEATURE_ID` join validation;
  - repo-local `tmp/` import of the abandoned student GIS inventory;
  - four baseline-derived K3Z subvariants driven by `basecase_riparian`, `basecase_sum`, `scenario1_sum`, and `scenario2_sum`;
  - validation/doc follow-through for join coverage and managed/unmanaged area deltas.
- Recorded the immediate tooling constraint that the uploaded `tmp/Fragments_Retention_HSmith.xls` cannot yet be inspected from the current venv because `.xls` support (`xlrd`) is missing, so schema verification is the first execution step before implementation starts.

## 2026-03-23 - Executed Phase 25 K3Z student overlay import, join, and four baseline-derived subvariant compiles
- Installed `xlrd` into the repo venv and verified the uploaded `tmp/Fragments_Retention_HSmith.xls` workbook directly from the active FEMIC environment.
- Confirmed the real student workbook field names are:
  - `FEATURE_ID1`
  - `Basecase_Riparian`
  - `BaseCase_Sum`
  - `Scenario1_Sum`
  - `Scenario2_Sum`
- Normalized that workbook into repo-local audit artifacts:
  - `tmp/k3z_student_overlay_retention_join.csv`
  - `tmp/k3z_student_overlay_retention_join.feather`
  - `tmp/k3z_overlay_retention_summary.csv`
- Proved complete 218-row join coverage for the real K3Z teaching surface using the practical bridge:
  - student `FEATURE_ID1`
  - `models/k3z_patchworks_model/blocks/blocks.shp` `FEATURE_ID`
  - shared `BLOCK`
  - `output/patchworks_k3z_validated/fragments/fragments.shp`
- Added four coexisting baseline-derived overlay runtime surfaces in the K3Z instance repo:
  - runtime configs:
    - `config/patchworks.runtime.overlay.basecase_riparian.windows.yaml`
    - `config/patchworks.runtime.overlay.basecase_sum.windows.yaml`
    - `config/patchworks.runtime.overlay.scenario1_sum.windows.yaml`
    - `config/patchworks.runtime.overlay.scenario2_sum.windows.yaml`
  - variant specs:
    - `config/patchworks.variant.overlay.basecase_riparian.yaml`
    - `config/patchworks.variant.overlay.basecase_sum.yaml`
    - `config/patchworks.variant.overlay.scenario1_sum.yaml`
    - `config/patchworks.variant.overlay.scenario2_sum.yaml`
  - Patchworks PIN entrypoints:
    - `models/k3z_patchworks_model/analysis/overlay_basecase_riparian.pin`
    - `models/k3z_patchworks_model/analysis/overlay_basecase_sum.pin`
    - `models/k3z_patchworks_model/analysis/overlay_scenario1_sum.pin`
    - `models/k3z_patchworks_model/analysis/overlay_scenario2_sum.pin`
- Refactored baseline PIN reuse so baseline-derived overlays share one common PIN body in `external/femic-k3z-instance/models/k3z_patchworks_model/analysis/base_variant_common.bsh`.
- Generated four overlay-specific fragments datasets:
  - `output/patchworks_k3z_overlay_basecase_riparian_validated/fragments/fragments.shp`
  - `output/patchworks_k3z_overlay_basecase_sum_validated/fragments/fragments.shp`
  - `output/patchworks_k3z_overlay_scenario1_sum_validated/fragments/fragments.shp`
  - `output/patchworks_k3z_overlay_scenario2_sum_validated/fragments/fragments.shp`
- Ran Patchworks preflight successfully for all four overlay runtime configs.
- Ran Patchworks matrix-builder successfully for all four overlay subvariants, producing:
  - `models/k3z_patchworks_model/tracks_overlay_basecase_riparian/`
  - `models/k3z_patchworks_model/tracks_overlay_basecase_sum/`
  - `models/k3z_patchworks_model/tracks_overlay_scenario1_sum/`
  - `models/k3z_patchworks_model/tracks_overlay_scenario2_sum/`
- Validation snapshot from `tmp/k3z_overlay_retention_summary.csv`:
  - baseline retained area: `89.065662 ha`
  - `basecase_riparian`: `164.305456 ha` retained (`+75.239794 ha`)
  - `basecase_sum`: `379.898530 ha` retained (`+290.832868 ha`)
  - `scenario1_sum`: `546.841710 ha` retained (`+457.776048 ha`)
  - `scenario2_sum`: `622.819694 ha` retained (`+533.754032 ha`)

## 2026-03-23 - Fixed Phase 25 overlay PIN launch to respect active overlay account surfaces
- Live Patchworks testing showed `overlay_basecase_riparian.pin` launches cleanly and matches the expected retention math, but `overlay_basecase_sum.pin` failed while defining `flow.even.product.Yield.managed.PLC`.
- Root cause was in `external/femic-k3z-instance/models/k3z_patchworks_model/scripts/targets/flowTargets.bsh`: the shared target script was still hard-wired to baseline `../tracks/accounts.csv`, so overlay wrapper PINs leaked baseline managed-species targets into overlay launches.
- Confirmed the account-surface difference is real and expected:
  - `tracks_overlay_basecase_riparian` still includes managed `PLC`;
  - `tracks_overlay_basecase_sum`, `tracks_overlay_scenario1_sum`, and `tracks_overlay_scenario2_sum` do not.
- Updated `flowTargets.bsh` so it resolves `accounts.csv` from the active wrapper PIN's `tracks_path_prefix` when present, falling back to baseline `../tracks/accounts.csv` only for the baseline surface.
- Expected effect: overlay PINs now define even-flow / NDY targets only for the managed yield accounts that actually exist in their own compiled tracks surface, preventing launch-time failures when higher-retention overlays remove a species from the managed side.

## 2026-03-23 - Hardened Phase 25 overlay flow-target fix with explicit tracks-path wiring
- The first overlay flow-target fix was still too indirect for BeanShell launch behavior.
- Reworked `external/femic-k3z-instance/models/k3z_patchworks_model/scripts/targets/flowTargets.bsh` so account discovery accepts an explicit tracks-path prefix argument instead of trying to infer it from interpreter state.
- Updated all active K3Z PIN call sites that use shared flow-target setup to pass their own `tracks_path_prefix` explicitly:
  - `models/k3z_patchworks_model/analysis/base_variant_common.bsh`
  - `models/k3z_patchworks_model/analysis/ctfert.pin`
  - `models/k3z_patchworks_model/analysis/pctct.pin`
- Expected effect: baseline, overlay, CT/fert, and PCT->CT launches now all build flow targets from the accounts table that belongs to the active tracks surface, not whichever tracks folder the shared script would otherwise default to.

## 2026-03-23 - Recompiled Phase 25 `scenario2_sum` after workbook edit removed the tiny managed sliver
- The user manually edited `tmp/Fragments_Retention_HSmith.xls` for block `59`, changing the `Scenario2_Sum` value from the prior sliver-causing fraction to full retention (`1.0` in the edited workbook).
- Rebuilt the normalized overlay join artifacts from the edited workbook and reran only the `scenario2_sum` overlay subvariant with run id `k3z_overlay_scenario2_sum_20260323_b`.
- Post-rerun block `59` now has:
  - `AREA_HA = 1.427842`
  - `RETENTION = 1.0`
  - managed remainder = `0.0 ha`
  - unmanaged portion = `1.42784211 ha`
- This removes the previous Patchworks small-block precision warning source, which had been caused by a managed remainder of only `0.0001427842 ha` under the earlier `0.9999` retention value.
- Refreshed `scenario2_sum` landscape totals now read:
  - retained area = `622.819837 ha`
  - managed area = `1158.493400 ha`
- Live status after this rerun: all four overlay subvariants are now launching cleanly.

## 2026-03-23 - Recovered missing K3Z CT/fert variant surface exposed during Phase 25 launch QA
- Live launch of `external/femic-k3z-instance/models/k3z_patchworks_model/analysis/ctfert.pin` failed after the overlay target-path hardening, but the deeper issue was not the overlay subvariants themselves.
- `ctfert.pin` was still configured to load `../tracks_ctfert/`, while the checked-out K3Z instance no longer carried the full CT/fert artifact family:
  - `config/patchworks.runtime.ctfert.windows.yaml`
  - `config/patchworks.variant.ctfert.yaml`
  - `config/silviculture.k3z.ctfert.yaml`
  - `models/k3z_patchworks_model/tracks_ctfert/`
  - `models/k3z_patchworks_model/yield/forestmodel_ctfert.xml`
  - `output/patchworks_k3z_ctfert_validated/`
- Restored that CT/fert surface from historical K3Z submodule commit `5e11bfb` (`Recover K3Z ctfert variant with additive retention behavior`) so the active instance once again matches what `ctfert.pin` expects to launch.
- Verified the recovered surface with:
  - `.\.venv\Scripts\python.exe -m femic patchworks preflight --instance-root external/femic-k3z-instance --config config/patchworks.runtime.ctfert.windows.yaml`
- Result: CT/fert preflight now passes again, and the overlay flow-target fix is no longer blocked by missing CT/fert artifacts in the instance checkout.

## 2026-03-23 - Expanded K3Z standalone docs for variants/subvariants and fixed parent docs clean-checkout CI
- Added a new Phase 26 docs milestone in `ROADMAP.md` covering the K3Z docs push, parent `docs-pages` repair, and the urgent follow-up note for the `pctct` species-wise account regression.
- Expanded the canonical standalone K3Z docs in `external/femic-k3z-instance/docs/` with new dedicated pages for:
  - the full variant/subvariant launch matrix;
  - intensive-silviculture treatment logic and sequencing;
  - `og1` / `og2` old-growth attribute semantics.
- Updated the existing standalone K3Z guide pages (`getting-started`, `model-anatomy`, `operator-runbook`, `rebuild-and-qa`, `edit-policy-and-scenarios`) so they now route readers to the deeper variant/treatment/old-growth pages instead of leaving that detail fragmented across multiple pages.
- Documented the current overlay provenance and join contract in the standalone K3Z docs, including:
  - workbook key quirk `FEATURE_ID1`;
  - the four student retention columns `Basecase_Riparian`, `BaseCase_Sum`, `Scenario1_Sum`, and `Scenario2_Sum`;
  - the bridge through `blocks.shp` into the canonical fragments surface;
  - the fact that higher-retention overlays can legitimately drop managed species accounts when those species disappear from the managed side.
- Refreshed the parent FEMIC pointer page `docs/sample-models/k3z.rst` so it now explicitly routes readers to the standalone K3Z docs for variant selection, overlay subvariants, treatment sequencing, and `og1` / `og2` semantics.
- Diagnosed the parent `docs-pages` GitHub Actions failure to the clean-checkout API-doc surface: curated pages under `docs/reference/api/` were referencing `docs/reference/api/generated/*.rst` pages that existed locally but were not tracked in git.
- Added the generated API `.rst` stubs to the repo and extended `tests/test_docs_contract.py` so curated API pages now fail tests if they reference missing or untracked generated docs.
- Recorded the next urgent post-docs follow-up explicitly in the roadmap: `pctct` currently materializes only total managed yield/account surfaces in `forestmodel_pctct.xml` and `tracks_pctct`, so species-wise managed yield / harvested-volume accounts need to be restored in a separate bug-fix milestone.

## 2026-03-23 - Polished and closed out the K3Z docs upgrade branch
- Tightened the standalone K3Z docs with a more practical launch-selector layer in `getting-started.rst`, `variants-and-subvariants.rst`, and `operator-runbook.rst` so students/operators can choose the right surface quickly.
- Corrected an accuracy nit in `model-anatomy.rst` (`config/silviculture.k3z.ctfert.yaml` is the CT/fert config path) and added a dedicated CT/fert QA section in `rebuild-and-qa.rst`.
- Made the docs more operator-safe by documenting the currently known `pctct` limitation explicitly across the K3Z guide set and troubleshooting workflow: the `PCT -> CT` treatment path is real, but species-wise managed growing-stock / harvest-volume accounts still need a separate bug fix.
- Revalidated the milestone after the polish pass with:
  - parent docs build (`.\.venv\Scripts\python.exe -m sphinx -b html docs _build\html -W`);
  - standalone K3Z docs build (`..\..\.venv\Scripts\python.exe -m sphinx -b html docs docs\_build\html -W`);
  - `ruff format src tests`;
  - `ruff check src tests`;
  - `mypy src`;
  - `pytest`;
  - `pre-commit run --all-files`.

## 2026-03-24 - Corrected K3Z PCT docs terminology for `HW`
- Updated the standalone K3Z docs so `HW` is described accurately as Western Hemlock rather than as "hardwood".
- Corrected the affected `pctct` wording in:
  - `external/femic-k3z-instance/docs/getting-started.rst`
  - `external/femic-k3z-instance/docs/model-anatomy.rst`
  - `external/femic-k3z-instance/docs/silviculture-logic.rst`
- Removed the misleading "conifer-only" summary in favor of wording that simply states the `HW` species component is removed from the managed composition.
- Rebuilt the standalone K3Z docs with warnings-as-errors:
  - `..\..\.venv\Scripts\python.exe -m sphinx -b html docs docs\_build\html -W`

## 2026-03-24 - Restored species-wise managed accounts for the K3Z `pctct` variant
- Started the distinct bug-fix branch `bugfix/k3z-pctct-species-accounts` and recorded Phase 27 in `ROADMAP.md` before implementation.
- Diagnosed the regression all the way through the checked-in artifact surface:
  - the parent FEMIC export path can still generate species-wise `pctct` managed yield / harvested-volume surfaces;
  - the checked-in K3Z `pctct` ForestModel/tracks surface had gone stale and was the layer collapsed to `product.Yield.managed.Total` / `feature.Yield.managed.Total` only.
- Repaired the checked-in K3Z `pctct` surface by:
  - refreshing `external/femic-k3z-instance/models/k3z_patchworks_model/yield/forestmodel_pctct.xml` from a current good species-wise export probe;
  - rerunning Patchworks Matrix Builder for `config/patchworks.runtime.pctct.windows.yaml`;
  - updating `tracks_pctct/{accounts,protoaccounts,products,features,curves,treatments}.csv` so species-wise managed yield / harvested-volume accounts are present again alongside `PCT` and `CT`.
- Removed the now-stale `pctct` limitation notes from the standalone K3Z docs and updated the runbook/QA language to treat any future `Total`-only `pctct` surface as a regression, not expected behavior.
- Added a parent repo contract test in `tests/test_docs_contract.py` that fails if the checked-in `pctct` ForestModel/tracks surface ever regresses back to `Total`-only managed accounts.
- Validation evidence:
  - standalone K3Z docs build passed (`..\..\.venv\Scripts\python.exe -m sphinx -b html docs docs\_build\html -W`);
  - `python -m femic instance account-surface --instance-root external/femic-k3z-instance --config config/patchworks.runtime.pctct.windows.yaml` reported `accounts=264`, `species=8`, and `complete_species=8`;
  - `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest`, and `pre-commit run --all-files` all passed.

## 2026-03-24 - Clarified that missing `pctct` species accounts is now only a regression playbook
- Tightened `external/femic-k3z-instance/docs/troubleshooting.rst` so it explicitly says the checked-in `pctct` surface should now retain species-wise managed yield / harvest-volume accounts.
- The "PCT->CT Variant Shows Total Managed Yield But Species Accounts Are Missing" section is now framed as a future-regression workflow, not as a current limitation.
- Rebuilt the standalone K3Z docs with warnings-as-errors:
  - `..\..\.venv\Scripts\python.exe -m sphinx -b html docs docs\_build\html -W`

## 2026-03-24 - Closed the K3Z overlay guidance gap for students and operators
- Completed `P25.4b` by adding a dedicated standalone K3Z docs page,
  `external/femic-k3z-instance/docs/overlay-subvariants-workflow.rst`, that
  documents the overlay source contract, `FEATURE_ID1` key quirk, `blocks.shp`
  bridge, subvariant meaning map, repeatable launch pairings, validation
  totals, and an audit checklist in one place.
- Updated the surrounding standalone K3Z guide pages so overlay guidance is now
  easy to find from `getting-started.rst`, `variants-and-subvariants.rst`,
  `operator-runbook.rst`, `rebuild-and-qa.rst`, and
  `edit-policy-and-scenarios.rst`.
- Extended `tests/test_docs_contract.py` so the overlay workflow page and its
  required headings/snippets are checked in the parent repo contract tests.
- Validation evidence:
  - standalone K3Z docs build passed (`..\..\.venv\Scripts\python.exe -m sphinx -b html docs docs\_build\html -W`);
  - parent docs build passed (`.\.venv\Scripts\python.exe -m sphinx -b html docs _build\html -W`);
  - targeted docs contract coverage passed (`.\.venv\Scripts\python.exe -m pytest tests/test_docs_contract.py -k "k3z_instance_standalone_docs"`);
  - `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest`, and `pre-commit run --all-files` all passed.

## 2026-03-24 - Closed Phase 22 `P22.9e` for the K3Z CT/fert canonical rebuild
- Started branch `feature/k3z-ctfert-canonical-rebuild`, updated `ROADMAP.md`
  first, and resumed from the already-recorded `P22.9e` blocker/corrective-plan
  notes instead of replaying the whole CT/fert variant history.
- Probed the current canonical CT/fert export directly with:
  `femic export patchworks --tsa k3z --instance-root external/femic-k3z-instance --output-dir output/patchworks_k3z_ctfert_probe_p229e --seral-stage-config config/seral.k3z.yaml --silviculture-config config/silviculture.k3z.ctfert.yaml`
  and confirmed the raw export still lands on the broader surface
  (`au=27`, `fragments=219`, `curves=976`) rather than the accepted teaching
  footprint.
- Proved the accepted checked-in CT/fert fragments surface is deterministic and
  policy-explainable:
  - it preserves the baseline 218-fragment geometry footprint exactly;
  - it differs from baseline only on 9 fragments in low-yield AUs `985502006`
    and `985502008`;
  - those 9 fragments are retained out of THLB via `RETENTION = 1.0`.
- Verified the canonical rebuild seam by pairing the fresh canonical CT/fert
  ForestModel with the accepted checked-in CT/fert fragments surface and
  rerunning Matrix Builder via probe run `k3z_ctfert_p229e_probe`.
- Results from that probe:
  - Patchworks matrix-builder completed successfully against the accepted
    218-fragment CT/fert surface;
  - the probe produced the expected CT/fert treatment surface (`CT`, `F1`,
    `F2`, `F3`);
  - the fresh canonical ForestModel hash matched the checked-in
    `models/k3z_patchworks_model/yield/forestmodel_ctfert.xml`;
  - the probe `tracks_ctfert` account/treatment coverage matched the current
    checked-in CT/fert tracks surface.
- Tightened the recorded CT/fert rebuild contract in:
  - `external/femic-k3z-instance/config/patchworks.variant.ctfert.yaml`
  - `external/femic-k3z-instance/docs/rebuild-and-qa.rst`
- Added parent regression coverage in `tests/test_docs_contract.py` so future
  drift fails tests if the checked-in CT/fert fragments surface stops matching
  the baseline geometry footprint or the expected 9 full-retention overrides.

## 2026-03-24 - Aligned `pctct` rebuild contract wording with `ctfert`
- Tightened `external/femic-k3z-instance/config/patchworks.variant.pctct.yaml`
  so it now mirrors the explicit `ctfert` rebuild-contract style: refresh the
  canonical ForestModel from current bundle/checkpoint inputs, but keep the
  accepted checked-in `pctct` fragments surface unless the
  baseline-footprint invariants still hold.
- Updated the standalone K3Z runbook/QA docs in:
  - `external/femic-k3z-instance/docs/rebuild-and-qa.rst`
  - `external/femic-k3z-instance/docs/operator-runbook.rst`
  so the `pctct` guidance now matches `ctfert` structurally and differs only in
  treatment-sequence expectations.
- Added a parent regression test in `tests/test_docs_contract.py` that locks
  the `pctct` fragments contract to exact baseline geometry parity with no
  `AU` / `IFM` / `RETENTION` / `ORIGIN` / `SILV_STATE` drift.

## 2026-03-24 - Closed `P23.11` with YAML-backed VDYP fit policy defaults and instance overlays
- Opened GitHub feature issue `#9`, `Move VDYP fit overrides from code to a
  YAML-backed policy surface`, before implementation so the design/tradeoffs
  are traceable outside the roadmap.
- Replaced the hard-coded TSA override map as the primary operator surface with
  tracked YAML defaults in `config/vdyp_fit_policy.yaml`.
- Added instance-local YAML overlay support in
  `src/femic/pipeline/vdyp_overrides.py`, with auto-discovery from
  `<instance_root>/config/vdyp_fit_policy.yaml` and merge precedence:
  explicit runtime override map -> instance-local YAML -> FEMIC default YAML ->
  narrow code fallback for missing/malformed shared defaults.
- Landed the accepted K3Z-specific `CWHvm_DR+HW` smoothing exceptions in
  `external/femic-k3z-instance/config/vdyp_fit_policy.yaml` so that case-level
  tuning no longer requires editing parent FEMIC source code.
- Updated operator/developer docs in:
  - `docs/guides/stage-01a-vdyp-tipsy-input.rst`
  - `docs/guides/troubleshooting.rst`
  - `external/femic-k3z-instance/docs/getting-started.rst`
  - `external/femic-k3z-instance/docs/edit-policy-and-scenarios.rst`
  so the new config surface, precedence rules, and intended use are explicit.
- Extended regression coverage in `tests/test_vdyp_overrides.py` for:
  - default YAML reproduction of known TSA overrides;
  - K3Z instance overlay loading;
  - instance-overlay merge precedence;
  - narrow fallback behavior;
  - malformed instance-policy rejection.
- Validation passed with:
  - `.\.venv\Scripts\python.exe -m sphinx -b html docs _build\html -W`
  - `..\..\.venv\Scripts\python.exe -m sphinx -b html docs docs\_build\html -W`
  - `ruff format src tests`
  - `ruff check src tests`
  - `mypy src`
  - `pytest`
  - `pre-commit run --all-files`

## 2026-03-24 - Tightened `AGENTS.md` workflow contract around GitHub issue tracking
- Updated `AGENTS.md` bootstrap expectations so fresh working shells now verify
  both `gh --version` and `gh auth status` alongside the existing FEMIC toolchain
  checks.
- Added an explicit development-workflow rule that each new non-trivial
  feature/bug/docs task must:
  - confirm GitHub CLI availability/auth for the active user;
  - search for an existing open GitHub issue first, or create one before
    substantial implementation;
  - link the governing issue back into `ROADMAP.md` when work becomes active;
  - reconcile the issue status as work progresses/closes so roadmap planning and
    GitHub tracking stay aligned and reduce tail-chasing / dropped-ball risk.

## 2026-03-24 - Retargeted K3Z `pctct` to the updated Issue 14 AU cohort
- Retargeted `external/femic-k3z-instance/config/silviculture.k3z.pctct.yaml`
  so `PCT` and `CT` eligibility now applies only to `985502000`, `985503000`,
  `985502001`, and `985503001`.
- Updated `external/femic-k3z-instance/config/tipsy/tsak3z.yaml` so those four
  Issue 14 AUs now use the requested `900 CW + 3100 HW` planted regeneration
  mix.
- Refreshed the standalone K3Z docs in:
  - `external/femic-k3z-instance/docs/assumptions-registry.rst`
  - `external/femic-k3z-instance/docs/getting-started.rst`
  - `external/femic-k3z-instance/docs/model-anatomy.rst`
  - `external/femic-k3z-instance/docs/rebuild-and-qa.rst`
  - `external/femic-k3z-instance/docs/silviculture-logic.rst`
  so the `pctct` variant now documents the correct four-AU footprint, the
  matching regen assumption, and the current rebuild/validation contract.
- Regenerated:
  - `external/femic-k3z-instance/models/k3z_patchworks_model/yield/forestmodel_pctct.xml`
  - `external/femic-k3z-instance/output/patchworks_k3z_pctct_validated/forestmodel.xml`
  - `external/femic-k3z-instance/models/k3z_patchworks_model/tracks_pctct/`
  from the updated config and verified that `PCT` / `CT` treatment states now
  materialize only for the four Issue 14 AUs, while non-target AUs such as
  `985502002` remain only in the baseline/CC land-base surface as expected.
- Validation passed with:
  - `..\..\.venv\Scripts\python.exe -m sphinx -b html docs docs\_build\html -W`
  - `python -m femic patchworks matrix-build --instance-root external/femic-k3z-instance --config config/patchworks.runtime.pctct.windows.yaml --run-id k3z_pctct_issue14_20260324`
  - `python -m femic instance account-surface --instance-root external/femic-k3z-instance --config config/patchworks.runtime.pctct.windows.yaml`
  - `ruff format src tests`
  - `ruff check src tests`
  - `mypy src`
  - `pytest`
  - `pre-commit run --all-files`
- Filled the local `.venv` gaps that were blocking the repo-wide gates by
  installing `openpyxl` and `pandas-stubs`.
- Confirmed remaining boundary from Issue 14: light/moderate/heavy PCT
  intensity options still require a deeper model design because the current
  `pctct` implementation compiles only one post-PCT managed state
  (`cc_pl_pct`), not multiple intensity-specific treatment paths.

## 2026-03-24 - Added three coexisting age-10 PCT choices to K3Z `pctct`
- Extended parent Patchworks export logic in
  `src/femic/fmg/patchworks.py` so `pre_commercial_thinning` can now compile
  multiple labeled PCT treatments from the same planted starting state, each
  with its own post-PCT state and per-species stem-removal target.
- Added parent regression coverage in:
  - `tests/test_fmg_patchworks.py`
  - `tests/test_docs_contract.py`
  proving that one variant can materialize `PCT_LIGHT`, `PCT_MODERATE`, and
  `PCT_HEAVY` in parallel while still routing `CT` from each resulting PCT
  state.
- Updated `external/femic-k3z-instance/config/silviculture.k3z.pctct.yaml` so
  the four Issue 14 AUs now expose three age-10 PCT choices:
  - `PCT_LIGHT` (`900 CW + 2100 HW`)
  - `PCT_MODERATE` (`900 CW + 1100 HW`)
  - `PCT_HEAVY` (`900 CW + 100 HW`)
- Refreshed the standalone K3Z docs and Patchworks entrypoint in:
  - `external/femic-k3z-instance/docs/getting-started.rst`
  - `external/femic-k3z-instance/docs/model-anatomy.rst`
  - `external/femic-k3z-instance/docs/operator-runbook.rst`
  - `external/femic-k3z-instance/docs/rebuild-and-qa.rst`
  - `external/femic-k3z-instance/docs/silviculture-logic.rst`
  - `external/femic-k3z-instance/models/k3z_patchworks_model/analysis/pctct.pin`
  so the three PCT flavors are explicit and visually distinguishable in
  Patchworks.
- Regenerated:
  - `external/femic-k3z-instance/models/k3z_patchworks_model/yield/forestmodel_pctct.xml`
  - `external/femic-k3z-instance/output/patchworks_k3z_pctct_validated/forestmodel.xml`
  - `external/femic-k3z-instance/models/k3z_patchworks_model/tracks_pctct/`
  from the updated multi-PCT config.
- Validation passed with:
  - `..\..\.venv\Scripts\python.exe -m sphinx -b html docs docs\_build\html -W`
  - `python -m femic patchworks matrix-build --instance-root external/femic-k3z-instance --config config/patchworks.runtime.pctct.windows.yaml --run-id k3z_pctct_multi_pct_20260324`
  - `python -m femic instance account-surface --instance-root external/femic-k3z-instance --config config/patchworks.runtime.pctct.windows.yaml`
  - `ruff check src tests`
  - `mypy src`
  - `pytest`
  - `pre-commit run --all-files`

## 2026-03-24 - Split K3Z `pctct` into light/moderate/heavy single-intensity subvariants
- Replaced the stacked multi-PCT K3Z teaching surface with three explicit
  single-intensity subvariants:
  - `pctct_light`
  - `pctct_moderate`
  - `pctct_heavy`
- Added tracked K3Z config/runtime/PIN surfaces for those subvariants in:
  - `external/femic-k3z-instance/config/patchworks.variant.pctct_*.yaml`
  - `external/femic-k3z-instance/config/patchworks.runtime.pctct_*.windows.yaml`
  - `external/femic-k3z-instance/config/silviculture.k3z.pctct_*.yaml`
  - `external/femic-k3z-instance/models/k3z_patchworks_model/analysis/pctct_*.pin`
- Kept the Issue 14 AU footprint and regen assumption constant across all three
  subvariants:
  - eligible AUs remain `985502000`, `985503000`, `985502001`, `985503001`
  - planted regen mix remains `900 CW + 3100 HW`
- Moved the PCT intensity choice out of one stacked tracks surface and into the
  three subvariant configs:
  - `pctct_light` removes `1000` HW stems/ha
  - `pctct_moderate` removes `2000` HW stems/ha
  - `pctct_heavy` removes `3000` HW stems/ha
- Refreshed the standalone K3Z docs/contracts so they now describe the new
  `pctct_*` launch matrix, generic `PCT`/`CT` labels, and the simplified state
  machine `cc_pl -> cc_pl_pct -> cc_pl_pct_ct`.
- Regenerated and checked in:
  - `external/femic-k3z-instance/models/k3z_patchworks_model/yield/forestmodel_pctct_light.xml`
  - `external/femic-k3z-instance/models/k3z_patchworks_model/yield/forestmodel_pctct_moderate.xml`
  - `external/femic-k3z-instance/models/k3z_patchworks_model/yield/forestmodel_pctct_heavy.xml`
  - `external/femic-k3z-instance/models/k3z_patchworks_model/tracks_pctct_light/`
  - `external/femic-k3z-instance/models/k3z_patchworks_model/tracks_pctct_moderate/`
  - `external/femic-k3z-instance/models/k3z_patchworks_model/tracks_pctct_heavy/`
  - `external/femic-k3z-instance/output/patchworks_k3z_pctct_light_validated/`
  - `external/femic-k3z-instance/output/patchworks_k3z_pctct_moderate_validated/`
  - `external/femic-k3z-instance/output/patchworks_k3z_pctct_heavy_validated/`
- Used the checked-in K3Z bundle tables to regenerate the three ForestModels,
  then rebuilt all three tracks surfaces against copies of the accepted
  baseline fragments surface so the 218-fragment teaching footprint stays
  unchanged across the new subvariants.
- Validation passed with:
  - `..\..\.venv\Scripts\python.exe -m sphinx -b html docs docs\_build\html -W`
  - `python -m femic patchworks matrix-build --instance-root external/femic-k3z-instance --config config/patchworks.runtime.pctct_light.windows.yaml --run-id k3z_pctct_light_20260324`
  - `python -m femic patchworks matrix-build --instance-root external/femic-k3z-instance --config config/patchworks.runtime.pctct_moderate.windows.yaml --run-id k3z_pctct_moderate_20260324`
  - `python -m femic patchworks matrix-build --instance-root external/femic-k3z-instance --config config/patchworks.runtime.pctct_heavy.windows.yaml --run-id k3z_pctct_heavy_20260324`
  - `python -m femic instance account-surface --instance-root external/femic-k3z-instance --config config/patchworks.runtime.pctct_light.windows.yaml` -> `accounts=265`, `species=8`, `complete_species=8`, `au=14`
  - `python -m femic instance account-surface --instance-root external/femic-k3z-instance --config config/patchworks.runtime.pctct_moderate.windows.yaml` -> `accounts=265`, `species=8`, `complete_species=8`, `au=14`
  - `python -m femic instance account-surface --instance-root external/femic-k3z-instance --config config/patchworks.runtime.pctct_heavy.windows.yaml` -> `accounts=264`, `species=8`, `complete_species=8`, `au=14`
  - `ruff format src tests`
  - `ruff check src tests`
  - `mypy src`
  - `pytest`
  - `pre-commit run --all-files`

## 2026-03-24 - Removed the dead `residual_stems_per_ha` PCT knob
- Removed `residual_stems_per_ha` from the active K3Z PCT config surfaces:
  - `external/femic-k3z-instance/config/silviculture.k3z.pctct.yaml`
  - `external/femic-k3z-instance/config/silviculture.k3z.pctct_light.yaml`
  - `external/femic-k3z-instance/config/silviculture.k3z.pctct_moderate.yaml`
  - `external/femic-k3z-instance/config/silviculture.k3z.pctct_heavy.yaml`
- Removed the same dead setting from the instance template at
  `src/femic/resources/instance/config/silviculture.case_template.yaml` so new
  cases do not inherit a non-functional knob.
- Simplified `src/femic/fmg/patchworks.py` so PCT config resolution no longer
  parses or stores `residual_stems_per_ha`; the active fixed-stem-removal path
  now reflects the real operative controls only:
  `source_total_stems_per_ha` plus `remove_stems_per_ha`.
- Updated `tests/test_fmg_patchworks.py` to remove the stale dead-setting
  fixture input.
- Validation passed with:
  - `ruff format src tests`
  - `ruff check src tests`
  - `mypy src`
  - `pytest`
  - `pre-commit run --all-files`

## 2026-03-24 - Removed the retired single-surface `pctct` alias
- Removed the now-redundant legacy K3Z `pctct` launch/config/build surface
  after `pctct_light`, `pctct_moderate`, and `pctct_heavy` stuck the landing:
  - `external/femic-k3z-instance/config/patchworks.variant.pctct.yaml`
  - `external/femic-k3z-instance/config/patchworks.runtime.pctct.windows.yaml`
  - `external/femic-k3z-instance/config/silviculture.k3z.pctct.yaml`
  - `external/femic-k3z-instance/models/k3z_patchworks_model/analysis/pctct.pin`
  - `external/femic-k3z-instance/models/k3z_patchworks_model/yield/forestmodel_pctct.xml`
  - `external/femic-k3z-instance/models/k3z_patchworks_model/tracks_pctct/`
  - `external/femic-k3z-instance/output/patchworks_k3z_pctct_validated/`
- Updated the remaining parent/K3Z docs so they point only at the supported
  `pctct_light`, `pctct_moderate`, and `pctct_heavy` subvariants.
- Added a parent docs-contract regression test that fails if the retired
  single-surface `pctct` files reappear.

## 2026-03-24 - Retargeted the K3Z student treatment family to PCT-only `pct_*`
- Replaced the active K3Z `pctct_*` subvariant family with the renamed
  PCT-only `pct_light`, `pct_moderate`, and `pct_heavy` surfaces:
  - `external/femic-k3z-instance/config/patchworks.variant.pct_*.yaml`
  - `external/femic-k3z-instance/config/patchworks.runtime.pct_*.windows.yaml`
  - `external/femic-k3z-instance/config/silviculture.k3z.pct_*.yaml`
  - `external/femic-k3z-instance/models/k3z_patchworks_model/analysis/pct_*.pin`
- Removed the `commercial_thinning` leg from the active PCT YAMLs so the
  managed treatment path now ends at `cc_pl_pct`; the rebuilt PCT-only
  ForestModels/tracks no longer materialize `CT` products or the
  `cc_pl_pct_ct` state.
- Regenerated and checked in the PCT-only artifact family:
  - `external/femic-k3z-instance/models/k3z_patchworks_model/yield/forestmodel_pct_*.xml`
  - `external/femic-k3z-instance/models/k3z_patchworks_model/tracks_pct_*/`
  - `external/femic-k3z-instance/output/patchworks_k3z_pct_*_validated/`
- Updated the remaining parent/K3Z docs and regression tests so they now
  describe the `pct_*` launch matrix, PCT-only treatment chain, and removal of
  the retired `pctct_*` paths.
- Validation passed with:
  - `python -m femic patchworks matrix-build --instance-root external/femic-k3z-instance --config config/patchworks.runtime.pct_light.windows.yaml --run-id k3z_pct_light_20260324_rebuild`
  - `python -m femic patchworks matrix-build --instance-root external/femic-k3z-instance --config config/patchworks.runtime.pct_moderate.windows.yaml --run-id k3z_pct_moderate_20260324_rebuild`
  - `python -m femic patchworks matrix-build --instance-root external/femic-k3z-instance --config config/patchworks.runtime.pct_heavy.windows.yaml --run-id k3z_pct_heavy_20260324_rebuild`
  - `python -m femic instance account-surface --instance-root external/femic-k3z-instance --config config/patchworks.runtime.pct_light.windows.yaml` -> `accounts=232`, `species=8`, `complete_species=8`, `au=14`
  - `python -m femic instance account-surface --instance-root external/femic-k3z-instance --config config/patchworks.runtime.pct_moderate.windows.yaml` -> `accounts=232`, `species=8`, `complete_species=8`, `au=14`
  - `python -m femic instance account-surface --instance-root external/femic-k3z-instance --config config/patchworks.runtime.pct_heavy.windows.yaml` -> `accounts=232`, `species=8`, `complete_species=8`, `au=14`
  - `ruff format src tests`
  - `ruff check src tests`
  - `mypy src`
  - `pytest`
  - `sphinx-build -b html docs _build/html -W`
  - `..\..\.venv\Scripts\python.exe -m sphinx -b html docs docs\_build\html -W`
  - `pre-commit run --all-files`

## 2026-03-24 - Closed Issue 14 with an explicit closeout note
- Added a final GitHub issue 14 closeout comment that:
  - summarizes the delivered `pct_light`, `pct_moderate`, and `pct_heavy`
    PCT-only scope;
  - points readers to the primary standalone K3Z docs under
    `external/femic-k3z-instance/docs/` and the parent pointer page at
    `docs/sample-models/k3z.rst`;
  - explains why the remaining checkpoint7/export caveat does not block the
    user-facing Issue 14 deliverable.
- Closed GitHub issue 14 after the explicit closeout note was posted.
- Tightened `AGENTS.md` so future issue closures must include a final
  closeout comment naming what shipped, where the docs live, the validation
  result, and why any remaining caveats do not block closure.

## 2026-03-24 - Surfaced K3Z TIPSY-vs-VDYP yield-curve plots in the user-facing docs
- Added a dedicated standalone K3Z guide page at
  `external/femic-k3z-instance/docs/yield-curve-comparisons.rst` so students
  can find and interpret the treated TIPSY-vs-VDYP comparison plots directly
  from the published docs.
- Linked that page into the main K3Z navigation flow from
  `index.rst`, `getting-started.rst`, `base-case-analysis.rst`,
  `model-anatomy.rst`, and `data-package-crosswalk.rst`.
- Kept `figure-appendix.rst` as the full figure catalog / filename-traceability
  surface, but added a cross-link back to the new student-facing comparison
  page.
- Documented the current exclusion of AUs `22006` and `22008` from the treated
  comparison set so students understand why those plots are absent.
- Validation passed with standalone K3Z docs build:
  - `sphinx-build -b html docs docs\_build\html -W`
- Parent quality gates also passed:
  - `ruff format src tests`
  - `ruff check src tests`
  - `mypy src`
  - `pytest`
  - `pre-commit run --all-files`
- GitHub issue 13 now carries an explicit closeout note and is closed as
  implemented.

## 2026-03-24 - Corrected K3Z treated overlay provenance back to raw BatchTIPSY
- Opened GitHub issue 17 after operator review caught that the checked-in
  `tipsy_vdyp_tsak3z-*.png` docs figures were not trustworthy.
- Verified that `external/femic-k3z-instance/data/tipsy_curves_tsak3z.csv`
  matches the old `vdyp_transform` scaled-VDYP synthesis path exactly, rather
  than a curve table reconstructed from raw `04_output-tsak3z.out`.
- Rebuilt the treated overlay figure family directly from:
  - `external/femic-k3z-instance/data/04_output-tsak3z.out`
  - `external/femic-k3z-instance/data/vdyp_curves_smooth-tsak3z.feather`
  - `external/femic-k3z-instance/data/model_input_bundle/au_table.csv`
- Replaced the tracked
  `external/femic-k3z-instance/plots/tipsy_vdyp_tsak3z-*.png` files with the
  regenerated raw-BatchTIPSY-vs-VDYP overlays.
- Updated the standalone K3Z docs pages
  `yield-curve-comparisons.rst` and `figure-appendix.rst` so they now describe
  the treated overlay provenance explicitly as raw `04_output-tsak3z.out`
  BatchTIPSY output against a VDYP reference curve, and restored AUs `22006`
  and `22008` to the rendered gallery because they are present in the accepted
  raw BatchTIPSY artifact used for this correction.

## 2026-03-24 - Corrected K3Z managed-curve bundle lineage back to raw BatchTIPSY
- Confirmed that the deeper stale lineage extended beyond the docs plots into:
  - `external/femic-k3z-instance/data/tipsy_curves_tsak3z.csv`
  - the treated managed rows in
    `external/femic-k3z-instance/data/model_input_bundle/curve_points_table.csv`
- Rebuilt both tracked managed-curve artifacts directly from
  `external/femic-k3z-instance/data/04_output-tsak3z.out`, restoring exact
  agreement between the tracked treated managed curves and raw BatchTIPSY
  output for all 14 treated AUs.
- Rebuilt the tracked K3Z ForestModel XML family from the corrected bundle:
  - `models/k3z_patchworks_model/yield/forestmodel.xml`
  - `models/k3z_patchworks_model/yield/forestmodel_ctfert.xml`
  - `models/k3z_patchworks_model/yield/forestmodel_pct_light.xml`
  - `models/k3z_patchworks_model/yield/forestmodel_pct_moderate.xml`
  - `models/k3z_patchworks_model/yield/forestmodel_pct_heavy.xml`
- Synchronized the matching `output/patchworks_k3z*_validated/forestmodel.xml`
  copies so the tracked validated output surfaces stay aligned with the rebuilt
  XMLs.
- Reran Patchworks Matrix Builder successfully for the full K3Z runtime family:
  baseline, `ctfert`, `pct_light`, `pct_moderate`, `pct_heavy`,
  `overlay.basecase_riparian`, `overlay.basecase_sum`,
  `overlay.scenario1_sum`, and `overlay.scenario2_sum`.
- Verified by direct XML inspection that the treated managed yield curves in
  all five ForestModel XMLs now use the raw-TIPSY decadal point structure
  rather than the old yearly transformed curve shape.
- Validation passed with:
  - `python -m femic patchworks matrix-build --instance-root external/femic-k3z-instance --config config/patchworks.runtime.windows.yaml --run-id k3z_true_tipsy_baseline_20260324`
  - `python -m femic patchworks matrix-build --instance-root external/femic-k3z-instance --config config/patchworks.runtime.ctfert.windows.yaml --run-id k3z_true_tipsy_ctfert_20260324`
  - `python -m femic patchworks matrix-build --instance-root external/femic-k3z-instance --config config/patchworks.runtime.pct_light.windows.yaml --run-id k3z_true_tipsy_pct_light_20260324`
  - `python -m femic patchworks matrix-build --instance-root external/femic-k3z-instance --config config/patchworks.runtime.pct_moderate.windows.yaml --run-id k3z_true_tipsy_pct_moderate_20260324`
  - `python -m femic patchworks matrix-build --instance-root external/femic-k3z-instance --config config/patchworks.runtime.pct_heavy.windows.yaml --run-id k3z_true_tipsy_pct_heavy_20260324`
  - `python -m femic patchworks matrix-build --instance-root external/femic-k3z-instance --config config/patchworks.runtime.overlay.basecase_riparian.windows.yaml --run-id k3z_true_tipsy_overlay_basecase_riparian_20260324`
  - `python -m femic patchworks matrix-build --instance-root external/femic-k3z-instance --config config/patchworks.runtime.overlay.basecase_sum.windows.yaml --run-id k3z_true_tipsy_overlay_basecase_sum_20260324`
  - `python -m femic patchworks matrix-build --instance-root external/femic-k3z-instance --config config/patchworks.runtime.overlay.scenario1_sum.windows.yaml --run-id k3z_true_tipsy_overlay_scenario1_sum_20260324`
  - `python -m femic patchworks matrix-build --instance-root external/femic-k3z-instance --config config/patchworks.runtime.overlay.scenario2_sum.windows.yaml --run-id k3z_true_tipsy_overlay_scenario2_sum_20260324`
  - `ruff format src tests`
  - `ruff check src tests`
  - `mypy src`
  - `pytest`
  - `pre-commit run --all-files`

## 2026-03-24 - Replaced numeric AU ids with human-readable Patchworks labels
- Reworked the Patchworks/ForestModel export naming seam in
  `src/femic/fmg/patchworks.py` so user-facing AU labels are now derived from
  `stratum_code` + `si_level` instead of exposing raw numeric AU ids.
- Human-readable account names now read like
  `feature.Seral.CWHvm-HW+FDC-H.mature` and
  `feature.Area.og1.CWHvm-HW+FDC-H`, with a TSA-prefix fallback applied only
  when duplicate readable AU labels would otherwise collide across TSAs.
- Extended the same readable-token policy into adjacent exported curve ids and
  readable XML ids where it improves operator readability, while intentionally
  preserving numeric AU ids in internal `AU eq ...` select clauses and related
  join semantics.
- Updated the regression suite and XML fixtures to lock the new naming
  behavior in place, including a duplicate-label test that verifies TSA-based
  disambiguation.
- Updated the parent Patchworks export docs plus the standalone K3Z operator
  and analysis docs so the documented account names match the exported model
  surface.
- Validation passed with:
  - `ruff format src tests`
  - `ruff check src tests`
  - `mypy src`
  - `pytest`
  - `pre-commit run --all-files`
  - `sphinx-build -b html docs _build/html -W`
  - standalone K3Z `sphinx-build -b html docs docs\_build\html -W`

## 2026-03-25 - Corrected human-readable AU rollout to use Patchworks-safe tokens
- Reopened GitHub issue `#2` after confirming the first rollout only updated
  the generator/tests/docs while the shipped K3Z runtime XML and track surfaces
  still exposed numeric AU labels.
- Regenerated the tracked K3Z ForestModel XML family from the updated exporter:
  - `external/femic-k3z-instance/models/k3z_patchworks_model/yield/forestmodel.xml`
  - `external/femic-k3z-instance/models/k3z_patchworks_model/yield/forestmodel_ctfert.xml`
  - `external/femic-k3z-instance/models/k3z_patchworks_model/yield/forestmodel_pct_light.xml`
  - `external/femic-k3z-instance/models/k3z_patchworks_model/yield/forestmodel_pct_moderate.xml`
  - `external/femic-k3z-instance/models/k3z_patchworks_model/yield/forestmodel_pct_heavy.xml`
- Found that Patchworks parses attribute `label=` values as expressions, so the
  first human-readable format using `-` and `+` (for example
  `CWHvm-HW+FDC-H`) was illegal and caused XML-load failure even though the XML
  structure itself was otherwise valid.
- Rebuilt the human-readable naming contract to use syntax-safe readable AU
  tokens derived from the same metadata, for example `CWHvm_HW_FDC_H`.
- Updated the exporter, regression tests, XML fixtures, and K3Z docs so the
  shipped account-name contract now consistently uses the syntax-safe AU token
  form for `feature.Area.og*`, `feature.Seral.*`, `product.Seral.area.*`, and
  `feature.QMD.*` surfaces.
- Reran Patchworks Matrix Builder successfully for the full K3Z runtime family:
  baseline, `ctfert`, `pct_light`, `pct_moderate`, `pct_heavy`,
  `overlay.basecase_riparian`, `overlay.basecase_sum`,
  `overlay.scenario1_sum`, and `overlay.scenario2_sum`.
- Verified directly from the synced `tracks*/accounts.csv` surfaces that the
  shipped runtime accounts now expose syntax-safe readable AU tokens such as
  `feature.Area.og1.CWHvm_HW_FDC_H` and
  `feature.Seral.CWHvm_HW_FDC_H.mature`.
- Validation passed with:
  - focused `pytest tests/test_fmg_patchworks.py tests/test_account_surface.py tests/test_cli_main.py tests/test_docs_contract.py`
  - `ruff format src tests`
  - `ruff check src tests`
  - `mypy src`
  - `pytest`
  - `pre-commit run --all-files`
  - `sphinx-build -b html docs _build/html -W`
  - standalone K3Z `sphinx-build -b html docs docs\_build\html -W`

## 2026-03-25 - Opened Issue 21 and branched the next K3Z CT/fert subvariant expansion
- Created GitHub issue `#21` to track the next K3Z CT/fert feature:
  expand eligibility from medium-SI-only `FDC+HW` / `CW+HW` AUs to the full
  low/medium/high-SI cohort and add two SI-specific fert-response subvariants.
- Cut matching feature branches in the parent repo and K3Z submodule:
  `feature/k3z-ctfert-si-subvariants`.
- Added Phase 36 kickoff notes to `ROADMAP.md` covering the requested boost
  profiles:
  - subvariant A: `L=15%`, `M=10%`, `H=5%`
  - subvariant B: `L=20%`, `M=10%`, with fert disabled entirely on `H` SI AUs
    instead of compiling a 0%-effect pass-through fert path.

## 2026-03-25 - Added CT/fert RETENTION overlay requirement to Phase 36
- Updated `ROADMAP.md` so the Phase 36 CT/fert subvariant work explicitly
  includes overlaying curated `RETENTION` values from
  `tmp/CTFert Fragments/fragments_updated3_Usedinbasecase.shp` onto both new
  CT/fert subvariants.
- Recorded that this curated overlay should replace the current placeholder
  `0.05` retention values before final Matrix Builder validation and closeout.

## 2026-03-25 - Implemented and validated the new K3Z CT/fert SI-profile subvariants
- Added two new K3Z CT/fert subvariants in the K3Z instance:
  - `ctfert_l15h5`
  - `ctfert_l20h0`
- Expanded CT eligibility from the original medium-SI-only cohort to the six
  `L/M/H` analysis units in the `CWHvm_FDC+HW` / `CWHvm_CW+HW` strata:
  `985501001`, `985502001`, `985503001`, `985501002`, `985502002`,
  `985503002`.
- Implemented per-AU fertilization gating and SI-specific response overrides in
  `src/femic/fmg/patchworks.py`, so:
  - `ctfert_l15h5` uses fert boosts `L=15%`, `M=10%`, `H=5%`;
  - `ctfert_l20h0` uses fert boosts `L=20%`, `M=10%`, and disables fert
    entirely on the `H` cohort while still keeping CT available there.
- Added regression coverage in `tests/test_fmg_patchworks.py` for:
  - per-AU fert response overrides,
  - skipping the fert chain on ineligible AUs,
  - preserving stand age across CT / `F1` / `F2` / `F3`.
- Fixed the CT/fert age-reset bug by emitting the Patchworks-schema-legal
  treatment attribute `adjust="R"` on CT / `F1` / `F2` / `F3`, after first
  confirming that the earlier `adjusts="'R'"` form was rejected by
  `ForestModel.xsd`.
- Added the new K3Z runtime/config/PIN surfaces:
  - `config/patchworks.variant.ctfert_l15h5.yaml`
  - `config/patchworks.variant.ctfert_l20h0.yaml`
  - `config/patchworks.runtime.ctfert_l15h5.windows.yaml`
  - `config/patchworks.runtime.ctfert_l20h0.windows.yaml`
  - `config/silviculture.k3z.ctfert_l15h5.yaml`
  - `config/silviculture.k3z.ctfert_l20h0.yaml`
  - `models/k3z_patchworks_model/analysis/ctfert_l15h5.pin`
  - `models/k3z_patchworks_model/analysis/ctfert_l20h0.pin`
- Rebuilt the new ForestModel XMLs:
  - `external/femic-k3z-instance/models/k3z_patchworks_model/yield/forestmodel_ctfert_l15h5.xml`
  - `external/femic-k3z-instance/models/k3z_patchworks_model/yield/forestmodel_ctfert_l20h0.xml`
- Replaced the placeholder retention surface on both new validated outputs with
  the curated overlay from
  `tmp/CTFert Fragments/fragments_updated3_Usedinbasecase.shp`, and verified
  both resulting fragment surfaces match that source exactly across the
  accepted 218-fragment geometry footprint.
- Updated the standalone K3Z docs plus the parent K3Z pointer page so the new
  CT/fert SI-profile subvariants are documented in the launch matrix, operator
  runbook, rebuild/QA guide, model anatomy, scenario guidance, and
  silviculture logic pages.
- Reran Patchworks Matrix Builder successfully for:
  - `config/patchworks.runtime.ctfert_l15h5.windows.yaml`
  - `config/patchworks.runtime.ctfert_l20h0.windows.yaml`
- Verified from the compiled tracks that:
  - `ctfert_l15h5` materializes the full `CT -> F1 -> F2 -> F3` chain on the
    eligible `L/M/H` cohort;
  - `ctfert_l20h0` leaves the `H` cohort on `cc_pl_ct` only, while the `L/M`
    cohort continues through `cc_pl_ct_f1`, `cc_pl_ct_f1_f2`, and
    `cc_pl_ct_f1_f2_f3`.
- Validation passed with:
  - `python -m femic patchworks matrix-build --instance-root external/femic-k3z-instance --config config/patchworks.runtime.ctfert_l15h5.windows.yaml --run-id k3z_ctfert_l15h5`
  - `python -m femic patchworks matrix-build --instance-root external/femic-k3z-instance --config config/patchworks.runtime.ctfert_l20h0.windows.yaml --run-id k3z_ctfert_l20h0`
  - `python -m femic instance account-surface --instance-root external/femic-k3z-instance --config config/patchworks.runtime.ctfert_l15h5.windows.yaml`
  - `python -m femic instance account-surface --instance-root external/femic-k3z-instance --config config/patchworks.runtime.ctfert_l20h0.windows.yaml`
  - `ruff format src tests`
  - `ruff check src tests`
  - `mypy src`
  - `pytest`
  - `pre-commit run --all-files`
  - `sphinx-build -b html docs _build/html -W`
  - standalone K3Z `python -m sphinx -b html docs docs/_build/html -W`

## 2026-03-26 - Phase 36 CT Final-Felling Gap Control Follow-Up

- Added a configurable commercial-thinning `final_felling_gap_factor` control
  in `src/femic/fmg/patchworks.py`.
- Replaced the old flat post-CT residual-yield subtraction with a ramped
  post-thinning final-felling gap:
  - the gap is still `1.0 x CT harvest volume` at CT age;
  - it now ramps linearly to the configured target factor at `cmai_argmax`;
  - values below `0.0` are rejected.
- Added focused regression coverage in `tests/test_fmg_patchworks.py` for the
  ramp math and the compiled XML behavior.
- Updated the K3Z SI-profile CT/fert subvariant configs:
  - `external/femic-k3z-instance/config/silviculture.k3z.ctfert_l15h5.yaml`
  - `external/femic-k3z-instance/config/silviculture.k3z.ctfert_l20h0.yaml`
  Both now set `commercial_thinning.final_felling_gap_factor: 0.0`.
- Regenerated the shipped ForestModel XMLs:
  - `external/femic-k3z-instance/models/k3z_patchworks_model/yield/forestmodel_ctfert_l15h5.xml`
  - `external/femic-k3z-instance/models/k3z_patchworks_model/yield/forestmodel_ctfert_l20h0.xml`
- Rebuilt the compiled `tracks_ctfert_l15h5` and `tracks_ctfert_l20h0`
  surfaces with Matrix Builder against the accepted curated fragments overlay.
- Updated the standalone K3Z docs in:
  - `external/femic-k3z-instance/docs/silviculture-logic.rst`
  - `external/femic-k3z-instance/docs/variants-and-subvariants.rst`
- Validation passed with:
  - `python -m femic patchworks matrix-build --instance-root external/femic-k3z-instance --config config/patchworks.runtime.ctfert_l15h5.windows.yaml --run-id k3z_ctfert_l15h5_gap0_20260326`
  - `python -m femic patchworks matrix-build --instance-root external/femic-k3z-instance --config config/patchworks.runtime.ctfert_l20h0.windows.yaml --run-id k3z_ctfert_l20h0_gap0_20260326`
  - `python -m femic instance account-surface --instance-root external/femic-k3z-instance --config config/patchworks.runtime.ctfert_l15h5.windows.yaml`
  - `python -m femic instance account-surface --instance-root external/femic-k3z-instance --config config/patchworks.runtime.ctfert_l20h0.windows.yaml`
  - `ruff format src tests`
  - `ruff check src tests`
  - `mypy src`
  - `pytest`
  - `pre-commit run --all-files`
  - `sphinx-build -b html docs _build/html -W`
  - standalone K3Z `python -m sphinx -b html docs docs/_build/html -W`

## 2026-03-26 - Phase 36 Legacy CT/Fert Retirement and XML Curve Thinning

- Patched `src/femic/fmg/adapters.py` so unmanaged/VDYP total-yield curves are
  thinned to decadal knots in the shipped ForestModel XML output while managed
  TIPSY curves retain their original point density.
- Added regression coverage in:
  - `tests/test_fmg_adapters.py`
  - `tests/test_fmg_patchworks.py`
- Retired the legacy single-surface `ctfert` launch path from the standalone
  K3Z instance by removing:
  - `external/femic-k3z-instance/config/patchworks.runtime.ctfert.windows.yaml`
  - `external/femic-k3z-instance/config/patchworks.variant.ctfert.yaml`
  - `external/femic-k3z-instance/config/silviculture.k3z.ctfert.yaml`
  - `external/femic-k3z-instance/models/k3z_patchworks_model/analysis/ctfert.pin`
  - `external/femic-k3z-instance/models/k3z_patchworks_model/yield/forestmodel_ctfert.xml`
  - `external/femic-k3z-instance/models/k3z_patchworks_model/tracks_ctfert/`
  - `external/femic-k3z-instance/output/patchworks_k3z_ctfert_validated/`
- Updated the active K3Z docs and contracts so only `ctfert_l15h5` and
  `ctfert_l20h0` remain documented launch surfaces, and explicitly recorded
  that their validated fragment outputs use curated `RETENTION` values
  overlaid from
  `tmp/CTFert Fragments/fragments_updated3_Usedinbasecase.shp` rather than the
  older uniform `0.05` placeholder.
- Regenerated the shipped K3Z ForestModel XML family:
  - `external/femic-k3z-instance/models/k3z_patchworks_model/yield/forestmodel.xml`
  - `external/femic-k3z-instance/models/k3z_patchworks_model/yield/forestmodel_ctfert_l15h5.xml`
  - `external/femic-k3z-instance/models/k3z_patchworks_model/yield/forestmodel_ctfert_l20h0.xml`
  - `external/femic-k3z-instance/models/k3z_patchworks_model/yield/forestmodel_pct_light.xml`
  - `external/femic-k3z-instance/models/k3z_patchworks_model/yield/forestmodel_pct_moderate.xml`
  - `external/femic-k3z-instance/models/k3z_patchworks_model/yield/forestmodel_pct_heavy.xml`
- Rebuilt Matrix Builder successfully for:
  - `config/patchworks.runtime.windows.yaml`
  - `config/patchworks.runtime.ctfert_l15h5.windows.yaml`
  - `config/patchworks.runtime.ctfert_l20h0.windows.yaml`
- Validation passed with:
  - `pytest tests/test_docs_contract.py tests/test_fmg_adapters.py tests/test_fmg_patchworks.py`
  - `ruff check src tests`
  - `mypy src`
  - `sphinx-build -b html docs _build/html -W`
  - standalone K3Z `python -m sphinx -b html docs docs/_build/html -W`

## 2026-03-26 - Phase 37 K3Z QMD Approximation Upgrade

- Replaced the old placeholder K3Z QMD age heuristic in
  `src/femic/fmg/patchworks.py` with a reverse-engineered approximation that
  back-solves diameter from stand yield, height, and trees per hectare.
- Added per-AU QMD support loading in `src/femic/fmg/adapters.py` using the
  accepted K3Z artifact surfaces:
  - `external/femic-k3z-instance/data/tipsy_curves_tsak3z.csv`
  - `external/femic-k3z-instance/data/tipsy_params_tsak3z.xlsx`
  - `external/femic-k3z-instance/data/ria_vri_vclr1p_checkpoint1-tsak3z.feather`
  - `external/femic-k3z-instance/data/vdyp_lyr-tsak3z.feather`
- Managed baseline QMD now uses accepted BatchTIPSY-supported yield, height,
  and TPH inputs where those managed curves exist; unmanaged baseline QMD now
  uses accepted yield plus a linear site-index height assumption and
  VDYP-side stems-per-hectare proxies reconstructed from the accepted
  checkpoint/layer data.
- Preserved the existing CT/fert QMD response multipliers on top of the
  rebuilt base QMD curves rather than the older hand-tuned placeholder.
- Added focused regression coverage in `tests/test_fmg_patchworks.py` for the
  new QMD volume backsolve path.
- Regenerated the shipped K3Z CT/fert XMLs:
  - `external/femic-k3z-instance/models/k3z_patchworks_model/yield/forestmodel_ctfert_l15h5.xml`
  - `external/femic-k3z-instance/models/k3z_patchworks_model/yield/forestmodel_ctfert_l20h0.xml`
- Rebuilt the compiled `tracks_ctfert_l15h5` and `tracks_ctfert_l20h0`
  surfaces with Matrix Builder against the accepted curated fragments overlay.
- Updated the standalone K3Z docs to replace the old placeholder-QMD wording
  with the new approximation contract in:
  - `external/femic-k3z-instance/docs/model-anatomy.rst`
  - `external/femic-k3z-instance/docs/operator-runbook.rst`
  - `external/femic-k3z-instance/docs/silviculture-logic.rst`
  - `external/femic-k3z-instance/docs/variants-and-subvariants.rst`
- Validation passed with:
  - `python -m femic patchworks matrix-build --instance-root external/femic-k3z-instance --config config/patchworks.runtime.ctfert_l15h5.windows.yaml --run-id k3z_ctfert_l15h5_qmd_upgrade_retry_20260326`
  - `python -m femic patchworks matrix-build --instance-root external/femic-k3z-instance --config config/patchworks.runtime.ctfert_l20h0.windows.yaml --run-id k3z_ctfert_l20h0_qmd_upgrade_retry_20260326`
  - `python -m femic instance account-surface --instance-root external/femic-k3z-instance --config config/patchworks.runtime.ctfert_l15h5.windows.yaml`
  - `python -m femic instance account-surface --instance-root external/femic-k3z-instance --config config/patchworks.runtime.ctfert_l20h0.windows.yaml`
  - `ruff format src tests`
  - `ruff check src tests`
  - `mypy src`
  - `pytest`
  - `pre-commit run --all-files`
  - `sphinx-build -b html docs _build/html -W`
  - standalone K3Z `python -m sphinx -b html docs docs/_build/html -W`

## 2026-03-26 - Phase 37 QMD Surface Cleanup

- Removed stale dead QMD metadata knobs from the active CT/fert silviculture
  YAMLs:
  - `external/femic-k3z-instance/config/silviculture.k3z.ctfert_l15h5.yaml`
  - `external/femic-k3z-instance/config/silviculture.k3z.ctfert_l20h0.yaml`
- Deleted the old `qmd.source: "synthetic"` and placeholder-note fields so the
  config surface no longer advertises a behavior that is no longer implemented.
- Confirmed the active user-facing docs already describe the shipped CT/fert
  QMD outputs as approximate reconstructed curves rather than placeholder
  scaffolding.

## 2026-03-26 - Phase 37 AU-Wise Mean-QMD Account Normalization

- Updated `src/femic/patchworks_runtime.py` so the
  `protoaccounts.csv -> accounts.csv` promotion step computes AU-wise managed
  and unmanaged area denominators from the validated fragments surface using
  `AREA_HA`, `IFM`, and `RETENTION`.
- Replaced the default `SUM=1` multipliers on the AU-wise
  `feature.QMD.{managed,unmanaged}.*` account rows with reciprocal area
  multipliers, converting those surfaces from raw `cm*ha` aggregates into
  mean-QMD `cm` accounts.
- Added focused regression coverage in `tests/test_patchworks_runtime.py` for
  the QMD-account normalization behavior.
- Refreshed the shipped CT/fert account surfaces:
  - `external/femic-k3z-instance/models/k3z_patchworks_model/tracks_ctfert_l15h5/accounts.csv`
  - `external/femic-k3z-instance/models/k3z_patchworks_model/tracks_ctfert_l20h0/accounts.csv`
- Validation passed with:
  - `pytest tests/test_patchworks_runtime.py`

## 2026-03-26 - Phase 38 PCT Age-Retention Bug Kickoff

- Opened GitHub bug issue `#25`:
  - `Fix possible PCT absolute-offset reset bug in K3Z pct subvariants`
- Created the matching bug branch in both repos:
  - parent repo: `bug/k3z-pct-adjust-r`
  - K3Z submodule: `bug/k3z-pct-adjust-r`
- Added Phase 38 roadmap tasks to audit the active `pct_light`,
  `pct_moderate`, and `pct_heavy` treatment-age semantics, apply the same
  age-retention fix used earlier for CT/fert if needed, and rerun Matrix
  Builder plus targeted Patchworks validation before closeout.

## 2026-03-26 - Phase 38 PCT Age-Retention Bug Fix

- Confirmed the suspected PCT age-retention bug was real:
  - the shipped `forestmodel_pct_light.xml`, `forestmodel_pct_moderate.xml`,
    and `forestmodel_pct_heavy.xml` omitted `adjust="R"` on the `PCT`
    treatment nodes;
  - the compiled `tracks_pct_light/treatments.csv`,
    `tracks_pct_moderate/treatments.csv`, and
    `tracks_pct_heavy/treatments.csv` therefore showed `PCT ... ADJUST=A`.
- Updated `src/femic/fmg/patchworks.py` so exported `PCT` treatments retain
  stand age after treatment using `adjust="R"`.
- Added regression coverage in `tests/test_fmg_patchworks.py` to assert that
  the generated `PCT` treatment node carries `adjust="R"`.
- Regenerated the shipped K3Z PCT ForestModel XML family:
  - `external/femic-k3z-instance/models/k3z_patchworks_model/yield/forestmodel_pct_light.xml`
  - `external/femic-k3z-instance/models/k3z_patchworks_model/yield/forestmodel_pct_moderate.xml`
  - `external/femic-k3z-instance/models/k3z_patchworks_model/yield/forestmodel_pct_heavy.xml`
- Rebuilt the compiled PCT tracks:
  - `external/femic-k3z-instance/models/k3z_patchworks_model/tracks_pct_light/`
  - `external/femic-k3z-instance/models/k3z_patchworks_model/tracks_pct_moderate/`
  - `external/femic-k3z-instance/models/k3z_patchworks_model/tracks_pct_heavy/`
- Validation passed with:
  - `pytest tests/test_fmg_patchworks.py`
  - `python -m femic patchworks matrix-build --instance-root external/femic-k3z-instance --config config/patchworks.runtime.pct_light.windows.yaml --run-id k3z_pct_light_adjust_r_xmlrefresh_20260326`
  - `python -m femic patchworks matrix-build --instance-root external/femic-k3z-instance --config config/patchworks.runtime.pct_moderate.windows.yaml --run-id k3z_pct_moderate_adjust_r_xmlrefresh_20260326`
  - `python -m femic patchworks matrix-build --instance-root external/femic-k3z-instance --config config/patchworks.runtime.pct_heavy.windows.yaml --run-id k3z_pct_heavy_adjust_r_xmlrefresh_20260326`

## 2026-03-26 - Intake Queue Contract Update

- Updated `AGENTS.md` so the coding-agent contract explicitly requires
  monitoring `planning/incoming_ideas.md` during normal "what next" triage.
- Expanded the header in `planning/incoming_ideas.md` so it now reads as a
  clearer intake-policy document for both human developers and the coding
  agent, including queue purpose, usage rules, removal rules, and basic queue
  hygiene expectations.

## 2026-03-26 - Phase 39 GitHub Issue Type Policy Kickoff

- Opened GitHub issue `#28`:
  - `Adopt GitHub issue Type as FEMIC's canonical work-kind classifier`
- Created the working branch:
  - `feature/github-issue-type-policy`
- Confirmed the live FEMIC GitHub issue-type surface already provides the three
  built-in work kinds the new policy expects:
  - `Task`
  - `Bug`
  - `Feature`
- Added Phase 39 rollout tasks to `ROADMAP.md` covering maintainer-doc updates,
  label normalization, open-issue backfill, and final validation/closeout.

## 2026-03-26 - Phase 39 GitHub Issue Type Policy Rollout

- Updated `AGENTS.md` so FEMIC issue hygiene now explicitly requires:
  - built-in GitHub issue `Type` as the canonical work-kind field;
  - no duplicate work-kind labels such as `bug`, `enhancement`, `feature`, or `task`;
  - labels reserved for orthogonal metadata only.
- Added the orthogonal FEMIC labels needed for the lightweight taxonomy:
  - `windows`
  - `k3z`
  - `tsa29`
  - `patchworks`
  - `data`
- Backfilled built-in issue `Type` on the open issue set:
  - `#11 -> Bug`
  - `#10 -> Task`
  - `#8 -> Task`
  - `#27 -> Feature`
  - `#28 -> Task`
- Backfilled orthogonal labels on the open issue set:
  - `#11 -> windows, data`
  - `#10 -> tsa29`
  - `#8 -> documentation, windows, patchworks`
  - `#27 -> k3z, patchworks`
- Deleted the duplicate work-kind labels `bug` and `enhancement` from the FEMIC
  repo after confirming the open issue set no longer depended on them.
- Removed the harvested-stem QMD product-account idea from
  `planning/incoming_ideas.md` because it has now been promoted into GitHub as
  issue `#27`.

## 2026-03-26 - Phase 40 Harvested-Stem QMD Product Accounts Kickoff

- Resumed GitHub issue `#27` as the next active K3Z QMD work item:
  - `Add harvested-stem QMD product accounts to K3Z CT/fert and port across variants`
- Added Phase 40 to `ROADMAP.md` covering:
  - product-account export/runtime-path audit;
  - harvested-stem QMD `product` accounts for the active `ctfert_*` family;
  - normalization and shipped-track refresh for the CT/fert pilot slice;
  - regression coverage, docs, and issue-closeout notes for the pilot.
- Updated `ROADMAP.md` Detailed Next Steps Notes so the immediate execution
  order is pinned before implementation starts.

## 2026-03-26 - Phase 40 CT/Fert Harvested-Stem QMD Pilot

- Added harvested-stem QMD product-account support to
  `src/femic/fmg/patchworks.py`, behind the new
  `qmd.harvested_product_accounts_enabled` silviculture-config flag.
- Enabled that flag in the active K3Z CT/fert pilot surfaces:
  - `external/femic-k3z-instance/config/silviculture.k3z.ctfert_l15h5.yaml`
  - `external/femic-k3z-instance/config/silviculture.k3z.ctfert_l20h0.yaml`
- The active CT/fert pilot contract now exports these AU-wise event-level
  product rows:
  - `product.QMD.managed.<au_token>.CC`
  - `product.QMD.managed.<au_token>.CT`
  - `product.Treated.managed.<au_token>.CC`
  - `product.Treated.managed.<au_token>.CT`
- The QMD product rows are the harvested-stem numerator surfaces. Mean
  harvested diameter for a given AU/treatment combination is read as:
  - `product.QMD.managed.<au_token>.<treatment>`
    divided by
    `product.Treated.managed.<au_token>.<treatment>`
- Regenerated the shipped CT/fert ForestModel XML family directly from the
  current bundle tables plus the updated silviculture YAMLs:
  - `external/femic-k3z-instance/models/k3z_patchworks_model/yield/forestmodel_ctfert_l15h5.xml`
  - `external/femic-k3z-instance/models/k3z_patchworks_model/yield/forestmodel_ctfert_l20h0.xml`
- Rebuilt the shipped CT/fert tracks with Matrix Builder:
  - `external/femic-k3z-instance/models/k3z_patchworks_model/tracks_ctfert_l15h5/`
  - `external/femic-k3z-instance/models/k3z_patchworks_model/tracks_ctfert_l20h0/`
- The refreshed shipped `accounts.csv` surfaces now expose the new AU-wise
  harvested-QMD product rows cleanly, and
  `femic instance account-surface` now reports:
  - `accounts=283 species=6 complete_species=6 au=14`
    for both active CT/fert subvariants.
- Added regression coverage in:
  - `tests/test_fmg_patchworks.py`
  - `tests/test_patchworks_runtime.py`
  - `tests/test_docs_contract.py`
- Updated user-facing K3Z docs explaining the difference between standing
  `feature.QMD.*` surfaces and harvested-stem `product.QMD.*` surfaces:
  - `external/femic-k3z-instance/docs/model-anatomy.rst`
  - `external/femic-k3z-instance/docs/operator-runbook.rst`
  - `external/femic-k3z-instance/docs/variants-and-subvariants.rst`
- Validation passed with:
  - `python -m pytest`
  - `python -m ruff format src tests`
  - `python -m ruff check src tests`
  - `python -m mypy src`
  - `python -m pre_commit run --all-files`
  - `python -m sphinx -b html docs _build/html -W`
  - `python -m sphinx -b html external/femic-k3z-instance/docs external/femic-k3z-instance/docs/_build/html -W`
  - `python -m femic patchworks matrix-build --instance-root external/femic-k3z-instance --config config/patchworks.runtime.ctfert_l15h5.windows.yaml --run-id k3z_ctfert_l15h5_qmd_products_20260326`
  - `python -m femic patchworks matrix-build --instance-root external/femic-k3z-instance --config config/patchworks.runtime.ctfert_l20h0.windows.yaml --run-id k3z_ctfert_l20h0_qmd_products_20260326`
  - `python -m femic instance account-surface --instance-root external/femic-k3z-instance --config config/patchworks.runtime.ctfert_l15h5.windows.yaml`
  - `python -m femic instance account-surface --instance-root external/femic-k3z-instance --config config/patchworks.runtime.ctfert_l20h0.windows.yaml`
- The broader port across the remaining active K3Z variants is intentionally
  still pending on issue `#27`; this slice only completes the validated
  `ctfert_*` pilot.
- 2026-03-26 (Phase 40 CT/fert ratio-account correction): converted the
  launched `ctfert_*` harvested-stem QMD surface from raw numerator accounts to
  live Patchworks `RatioAccount` registration so the public `product.QMD.*`
  values resolve directly to mean harvested diameter in `cm`.
  - Renamed the shipped harvested-QMD attribute/account inputs in
    `src/femic/fmg/patchworks.py` from:
    - `product.QMD.managed.<au_token>.<treatment>`
    to:
    - `product.QMDNumerator.managed.<au_token>.<treatment>`
  - Added K3Z BeanShell helper:
    - `external/femic-k3z-instance/models/k3z_patchworks_model/scripts/targets/qmdRatioAccounts.bsh`
    which registers live:
    - `product.QMD.managed.<au_token>.<treatment>`
    via `control.addRatioAccount(...)` with scale `1`, using the matching
    `product.QMDNumerator.*` numerator and `product.Treated.*` denominator.
  - Wired that runtime ratio-account setup into:
    - `external/femic-k3z-instance/models/k3z_patchworks_model/analysis/ctfert_l15h5.pin`
    - `external/femic-k3z-instance/models/k3z_patchworks_model/analysis/ctfert_l20h0.pin`
  - Rebuilt and revalidated:
    - `external/femic-k3z-instance/models/k3z_patchworks_model/yield/forestmodel_ctfert_l15h5.xml`
    - `external/femic-k3z-instance/models/k3z_patchworks_model/yield/forestmodel_ctfert_l20h0.xml`
    - `external/femic-k3z-instance/models/k3z_patchworks_model/tracks_ctfert_l15h5/`
    - `external/femic-k3z-instance/models/k3z_patchworks_model/tracks_ctfert_l20h0/`
  - Updated regression coverage and docs in:
    - `tests/test_fmg_patchworks.py`
    - `tests/test_patchworks_runtime.py`
    - `tests/test_docs_contract.py`
    - `external/femic-k3z-instance/docs/model-anatomy.rst`
    - `external/femic-k3z-instance/docs/operator-runbook.rst`
  - Validation passed with:
    - `python -m ruff format src tests`
    - `python -m ruff check src tests`
    - `python -m mypy src`
    - `python -m pytest`
    - `python -m pre_commit run --all-files`
    - `sphinx-build -b html docs _build/html -W`
    - `sphinx-build -b html external/femic-k3z-instance/docs external/femic-k3z-instance/docs/_build/html -W`
    - `python -m femic patchworks matrix-build --instance-root external/femic-k3z-instance --config config/patchworks.runtime.ctfert_l15h5.windows.yaml --run-id k3z_ctfert_l15h5_qmd_ratio_accounts_20260326`
    - `python -m femic patchworks matrix-build --instance-root external/femic-k3z-instance --config config/patchworks.runtime.ctfert_l20h0.windows.yaml --run-id k3z_ctfert_l20h0_qmd_ratio_accounts_20260326`
    - `python -m femic instance account-surface --instance-root external/femic-k3z-instance --config config/patchworks.runtime.ctfert_l15h5.windows.yaml`
    - `python -m femic instance account-surface --instance-root external/femic-k3z-instance --config config/patchworks.runtime.ctfert_l20h0.windows.yaml`
  - Issue `#27` remains open because the wider port across the other active K3Z
    variants is still pending by design.

## 2026-03-26 - Phase 40 Harvested-Stem QMD Rollout Across Baseline, Overlay, and PCT

- Extended the harvested-stem QMD ratio-account contract from the validated
  `ctfert_*` pilot across the remaining active K3Z launch surfaces:
  - baseline `base`
  - overlay subvariants `basecase_riparian`, `basecase_sum`,
    `scenario1_sum`, and `scenario2_sum`
  - PCT-only subvariants `pct_light`, `pct_moderate`, and `pct_heavy`
- Added baseline silviculture opt-in:
  - `external/femic-k3z-instance/config/silviculture.k3z.base.yaml`
- Enabled the harvested-product QMD export path in:
  - `external/femic-k3z-instance/config/silviculture.k3z.pct_light.yaml`
  - `external/femic-k3z-instance/config/silviculture.k3z.pct_moderate.yaml`
  - `external/femic-k3z-instance/config/silviculture.k3z.pct_heavy.yaml`
- Extended `src/femic/fmg/patchworks.py` so the PCT family now exports:
  - AU-wise standing QMD feature accounts:
    - `feature.QMD.managed.<au_token>`
  - AU-wise harvested-QMD numerator product attributes:
    - `product.QMDNumerator.managed.<au_token>.PCT`
    - `product.QMDNumerator.managed.<au_token>.CC`
  - matching AU-wise treated-area denominator attributes:
    - `product.Treated.managed.<au_token>.PCT`
    - `product.Treated.managed.<au_token>.CC`
- Wired the live Patchworks ratio-account helper into:
  - `external/femic-k3z-instance/models/k3z_patchworks_model/analysis/base_variant_common.bsh`
  - `external/femic-k3z-instance/models/k3z_patchworks_model/analysis/pct_light.pin`
  - `external/femic-k3z-instance/models/k3z_patchworks_model/analysis/pct_moderate.pin`
  - `external/femic-k3z-instance/models/k3z_patchworks_model/analysis/pct_heavy.pin`
- Rebuilt the shipped baseline/overlay/PCT ForestModel XML and tracks surfaces:
  - `external/femic-k3z-instance/models/k3z_patchworks_model/yield/forestmodel.xml`
  - `external/femic-k3z-instance/models/k3z_patchworks_model/yield/forestmodel_pct_light.xml`
  - `external/femic-k3z-instance/models/k3z_patchworks_model/yield/forestmodel_pct_moderate.xml`
  - `external/femic-k3z-instance/models/k3z_patchworks_model/yield/forestmodel_pct_heavy.xml`
  - `external/femic-k3z-instance/models/k3z_patchworks_model/tracks/`
  - `external/femic-k3z-instance/models/k3z_patchworks_model/tracks_overlay_basecase_riparian/`
  - `external/femic-k3z-instance/models/k3z_patchworks_model/tracks_overlay_basecase_sum/`
  - `external/femic-k3z-instance/models/k3z_patchworks_model/tracks_overlay_scenario1_sum/`
  - `external/femic-k3z-instance/models/k3z_patchworks_model/tracks_overlay_scenario2_sum/`
  - `external/femic-k3z-instance/models/k3z_patchworks_model/tracks_pct_light/`
  - `external/femic-k3z-instance/models/k3z_patchworks_model/tracks_pct_moderate/`
  - `external/femic-k3z-instance/models/k3z_patchworks_model/tracks_pct_heavy/`
- Updated docs/tests so the shipped baseline, overlay, and PCT surfaces now
  document the same harvested-QMD numerator / denominator / ratio-account
  contract already used by `ctfert_*`.
- Issue `#27` remains open until the widened rollout validation and final
  closeout note are fully checkpointed on this branch.

## 2026-03-26 - Phase 41 Harvest Utilization Factor Kickoff

- Promoted the next K3Z teaching-assumption idea into the normal tracked
  workflow under GitHub issue `#31`.
- Initially staged this as a baseline-retention change, then pivoted the
  branch/issue/roadmap to the better implementation path:
  - keep fragment-level `RETENTION` unchanged
  - add downstream harvested-volume utilization factors instead
- Current governing tracker:
  - `#31` `Add K3Z harvest utilization factor for recovered merchantable volume`
- Current working branch:
  - `feature/k3z-harvest-utilization-factor`
- Current Phase 41 target behavior:
  - apply harvested-volume utilization in the
    `protoaccounts.csv -> accounts.csv` promotion layer
  - use treatment-specific factors:
    - `CC = 0.85`
    - `CT = 0.75`
  - leave standing growing-stock curves and fragment-level `RETENTION`
    untouched

## 2026-03-26 - Phase 41 Harvest Utilization Runtime Wiring

- Implemented downstream harvested-volume utilization support in
  `src/femic/patchworks_runtime.py` by extending the
  `protoaccounts.csv -> accounts.csv` promotion step with a
  treatment-specific `SUM` multiplier map.
- Added runtime-config support for:
  - `matrix_builder.harvested_volume_utilization_by_treatment`
- Current active teaching assumptions:
  - `CC = 0.85`
  - `CT = 0.75`
- Applied those runtime-config settings across the active K3Z launch surfaces:
  - baseline `base`
  - CT/fert `ctfert_l15h5` and `ctfert_l20h0`
  - overlay `basecase_riparian`, `basecase_sum`, `scenario1_sum`,
    and `scenario2_sum`
  - PCT-only `pct_light`, `pct_moderate`, and `pct_heavy`
- Kept the implementation intentionally downstream-only:
  - ForestModel XML and standing yield curves are unchanged
  - fragment-level `RETENTION` handling is unchanged
  - only promoted harvested-volume accounts are scaled
- Added runtime regression coverage in:
  - `tests/test_patchworks_runtime.py`
- Targeted validation passed:
  - `python -m pytest tests/test_patchworks_runtime.py`

## 2026-03-27 - Phase 42 Stems-Per-Ha Kickoff

- Promoted the next K3Z teaching-model idea into the normal tracked workflow
  under GitHub issue `#33`.
- Created the new working branch:
  - `feature/k3z-stems-per-ha-accounts`
- Defined the initial rollout target as standing stems-per-ha
  curves/attributes/accounts across the active K3Z launch surfaces:
  - baseline `base`
  - CT/fert `ctfert_l15h5` and `ctfert_l20h0`
  - PCT-only `pct_light`, `pct_moderate`, and `pct_heavy`
  - baseline-derived overlays if the standing account contract is shared
- Current implementation intent:
  - reuse the best available managed/unmanaged stems-per-ha support data
    already present in the K3Z handoff artifacts where possible
  - add AU-wise `feature.StemsPerHa.managed.<au_token>` and
    `feature.StemsPerHa.unmanaged.<au_token>` surfaces
  - regenerate the shipped K3Z account surfaces so downstream users pulling
    from `main` receive the new rows immediately after merge

## 2026-03-27 - Phase 42 Stems-Per-Ha Rollout

- Added AU-wise standing stems-per-ha support to the active K3Z family:
  - baseline `base`
  - `ctfert_l15h5`
  - `ctfert_l20h0`
  - `pct_light`
  - `pct_moderate`
  - `pct_heavy`
  - baseline-derived overlays that reuse the baseline account contract
- Exporter/runtime implementation:
  - added `feature.StemsPerHa.managed.<au_token>` and
    `feature.StemsPerHa.unmanaged.<au_token>` support in
    `src/femic/fmg/patchworks.py`
  - normalized `feature.StemsPerHa.*` rows during
    `protoaccounts.csv -> accounts.csv` promotion in
    `src/femic/patchworks_runtime.py` so the shipped accounts read as standing
    stems/ha rather than total stem counts
  - used accepted TIPSY `TPH` support for managed stems where available and
    checkpoint-derived AU medians for unmanaged/fallback support
  - carried treatment-state stems forward with simple teaching-model rules:
    `PCT` scales by residual-stems fraction, `CT` scales by
    `(1 - removal_fraction)`, and fert leaves standing stems unchanged
- Rebuilt the shipped K3Z ForestModel XML family:
  - `forestmodel.xml`
  - `forestmodel_ctfert_l15h5.xml`
  - `forestmodel_ctfert_l20h0.xml`
  - `forestmodel_pct_light.xml`
  - `forestmodel_pct_moderate.xml`
  - `forestmodel_pct_heavy.xml`
- Rebuilt Matrix Builder outputs for baseline, CT/fert, PCT, and all four
  overlay surfaces so downstream users pulling from `main` get refreshed
  `features.csv`, `protoaccounts.csv`, and `accounts.csv` files immediately
- Updated user-facing K3Z docs:
  - `external/femic-k3z-instance/docs/model-anatomy.rst`
  - `external/femic-k3z-instance/docs/operator-runbook.rst`
  - `external/femic-k3z-instance/docs/variants-and-subvariants.rst`
- Validation completed:
  - targeted regression checks for stems-per-ha exporter/runtime logic
  - `ruff format src tests`
  - `ruff check src tests`
  - `mypy src`
  - `pytest`
  - `pre-commit run --all-files`
  - parent Sphinx build
  - standalone K3Z Sphinx build
  - Matrix Builder reruns for all active K3Z runtime configs
  - `femic instance account-surface` spot checks:
    - baseline `accounts=311 species=7 complete_species=7 au=14`
    - `ctfert_l15h5` `accounts=308 species=6 complete_species=6 au=14`
    - `pct_light` `accounts=318 species=7 complete_species=7 au=14`

## 2026-03-27 - Phase 43 Intensive-Silviculture Variant Kickoff

- Promoted the next K3Z idea from `planning/incoming_ideas.md` into the normal
  tracked workflow under GitHub issue `#36`.
- Created the new working branch in the parent repo and K3Z submodule:
  - `feature/k3z-all-intensive-silviculture`
- Defined the kickoff scope as a planning-first pass for a new K3Z teaching
  surface that combines the current intensive silviculture treatments:
  - `PCT`
  - `CT`
  - `F1`
  - `F2`
  - `F3`
- Recorded the immediate design questions that must be answered before code
  changes begin:
  - what AU coverage the combined surface should inherit from the current
    `pct_*` and `ctfert_*` families;
  - what exact state chain and treatment order the combined variant should use;
  - whether the combined rollout should be one surface or a small subvariant
    family;
  - how the new surface should align with the current QMD, stems-per-ha,
    harvested-QMD, and harvested-volume account contracts.

## 2026-03-27 - Phase 43 Intensive-Silviculture Variant Implementation

- Implemented a new K3Z full-intensive teaching family under GitHub issue
  `#36`, using three launchable subvariants:
  - `intensive_light`
  - `intensive_moderate`
  - `intensive_heavy`
- Fixed the combined contract around the full 8-AU union of the current
  `pct_*` and `ctfert_l15h5` families, while reusing the accepted
  `ctfert_l15h5` SI-response profile on the CT/fert side.
- Compiled the combined state chain:
  - `cc_pl -> cc_pl_pct -> cc_pl_pct_ct -> cc_pl_ct_f1 -> cc_pl_ct_f1_f2 -> cc_pl_ct_f1_f2_f3`
- Added the new K3Z variant/runtime/silviculture/PIN surfaces plus the common
  analysis helper:
  - `config/patchworks.variant.intensive_*.yaml`
  - `config/patchworks.runtime.intensive_*.windows.yaml`
  - `config/silviculture.k3z.intensive_*.yaml`
  - `models/k3z_patchworks_model/analysis/intensive_*.pin`
  - `models/k3z_patchworks_model/analysis/intensive_variant_common.bsh`
- Rebuilt the shipped ForestModel XMLs, Matrix Builder tracks, and validated
  fragment outputs for all three full-intensive subvariants.
- Reused the accepted curated CT/fert retained-area overlay from
  `tmp/CTFert Fragments/fragments_updated3_Usedinbasecase.shp` for the new
  `intensive_*` family instead of inventing a separate retained-area policy.
- Extended regression coverage so the parent exporter test suite now checks the
  combined `PCT -> CT -> F1 -> F2 -> F3` path and the docs-contract suite
  checks the new checked-in intensive surfaces.
- Updated the user-facing docs and operator runbooks so the new
  `intensive_light`, `intensive_moderate`, and `intensive_heavy` surfaces are
  documented alongside baseline, `ctfert_*`, `pct_*`, and overlay launches.
- Validation completed:
  - `python -m pytest tests/test_fmg_patchworks.py tests/test_docs_contract.py`
  - `ruff format src tests`
  - `ruff check src tests`
  - `mypy src`
  - `pytest`
  - `pre-commit run --all-files`
  - parent Sphinx build
  - standalone K3Z Sphinx build
  - Matrix Builder reruns for `intensive_light`, `intensive_moderate`, and
    `intensive_heavy`
- Posted the implementation/validation status note to GitHub issue `#36`; the
  issue remains open pending PR merge.

## 2026-03-27 - Phase 44 Stem-Height Account Kickoff

- Promoted the next K3Z idea from `planning/incoming_ideas.md` into the normal
  tracked workflow under GitHub issue `#38`.
- Created the new working branch in the parent repo and K3Z submodule:
  - `feature/k3z-height-accounts`
- Defined the kickoff scope as a planning-first pass for AU-wise standing
  stem-height curves, attributes, and downstream accounts across the active K3Z
  launch family.
- Recorded the immediate design questions that must be answered before code
  changes begin:
  - what height support data should be used on the managed and unmanaged sides;
  - what AU-wise attribute/account naming contract should be used;
  - how treatment-state height should behave across `ctfert_*`,
    `intensive_*`, and `pct_*`;
  - how the new height-account family should align with the current QMD and
    stems-per-ha teaching surfaces.

## 2026-03-27 - Patchworks XML Rebuild Guardrail

- Added an explicit agent-facing guardrail to `AGENTS.md` for Patchworks-facing
  work:
  - regenerate the relevant `yield/forestmodel*.xml` files before running
    `femic patchworks matrix-build` whenever exporter logic or silviculture /
    seral config changes affect ForestModel semantics;
  - do not treat matrix-build results from stale XML as validation of the new
    change;
  - if the full export path is blocked by a known checkpoint/fragments seam,
    rebuild the XML through the lower-level bundle-table builder first, then
    rerun matrix build against the refreshed XML.

## 2026-03-27 - Phase 44 Stem Height Accounts Implemented

- Implemented AU-wise standing stem-height support across the active K3Z
  family under GitHub issue `#38`.
- Added exporter/runtime support for:
  - `feature.Height.managed.<au_token>`
  - `feature.Height.unmanaged.<au_token>`
- Reused the accepted QMD support logic rather than inventing a separate
  height model:
  - managed height uses the TIPSY managed-height handoff where available;
  - unmanaged height uses the same site-index fallback path already used by
    the approximate QMD builder.
- Treatment-state height currently carries forward unchanged through `PCT`,
  `CT`, and fertilization state chains unless the managed source curve itself
  changes.
- Normalized the downstream `feature.Height.*` accounts during
  `protoaccounts.csv -> accounts.csv` promotion so live Patchworks values read
  as mean standing height in `m`, not height-area totals.
- Rebuilt the shipped K3Z ForestModel XML family and reran Matrix Builder for:
  - baseline
  - `ctfert_l15h5`
  - `ctfert_l20h0`
  - `pct_light`
  - `pct_moderate`
  - `pct_heavy`
  - `intensive_light`
  - `intensive_moderate`
  - `intensive_heavy`
  - `overlay.basecase_riparian`
  - `overlay.basecase_sum`
  - `overlay.scenario1_sum`
  - `overlay.scenario2_sum`
- Added regression coverage in the exporter/runtime tests plus docs-contract
  assertions requiring checked-in `feature.Height.*` accounts on the active K3Z
  family.
- Updated the standalone K3Z docs so `feature.Height.*` is documented
  alongside the existing standing QMD and standing stems-per-ha surfaces in:
  - `docs/model-anatomy.rst`
  - `docs/operator-runbook.rst`
  - `docs/variants-and-subvariants.rst`

## 2026-03-27 - Phase 45 K3Z XML/Fragments Layout Kickoff

- Promoted the K3Z package-layout cleanup from `planning/incoming_ideas.md`
  into the normal tracked workflow under GitHub issue `#40`.
- Created the new working branch in the parent repo and K3Z submodule:
  - `task/k3z-output-xml-layout`
- Defined the kickoff scope as normalizing the K3Z runtime package so each
  variant uses the `forestmodel.xml` file colocated with its validated
  fragments surface under `output/patchworks_k3z*_validated/`, rather than the
  duplicate `models/k3z_patchworks_model/yield/*.xml` family.
- Recorded the initial audit result:
  - the variant-local output directories already carry the matching
    `forestmodel.xml` files beside the validated fragments;
  - the current confusion comes from runtime configs and docs still pointing at
    the duplicate `yield/*.xml` copies instead of those colocated output-local
    XMLs.

## 2026-03-27 - Phase 45 K3Z XML/Fragments Layout Normalized

- Normalized the active K3Z runtime package so the canonical Matrix Builder
  input pair is now the output-local validated pair:
  - `output/patchworks_k3z*_validated/forestmodel.xml`
  - `output/patchworks_k3z*_validated/fragments/fragments.*`
- Updated the active K3Z runtime configs and variant configs to point at those
  output-local XMLs instead of the duplicate
  `models/k3z_patchworks_model/yield/forestmodel*.xml` family.
- Deleted the stale duplicate ForestModel XML family from
  `external/femic-k3z-instance/models/k3z_patchworks_model/yield/`.
- Backfilled missing output-local canonical XML mirrors for the active
  `ctfert_*` and overlay variants so every shipped validated fragments surface
  now has the matching `forestmodel.xml` beside it.
- Updated the parent/runtime inference logic in `src/femic/patchworks_runtime.py`
  so the K3Z validated-layout pairing is recognized cleanly when
  `forestmodel.xml` lives beside `fragments/` under `output/patchworks_k3z*_validated/`.
- Updated both the parent and standalone K3Z docs, plus the machine-readable
  lineage registries, so users are told unambiguously which XML/fragments pair
  belongs together for Matrix Builder rebuilds.
- Validation passed:
  - targeted `pytest tests/test_patchworks_runtime.py tests/test_docs_contract.py`
  - full `ruff check src tests`
  - full `mypy src`
  - full `pytest`
  - parent Sphinx build
  - standalone K3Z Sphinx build
  - representative Patchworks `matrix-build` reruns for baseline,
    `ctfert_l15h5`, `pct_light`, `intensive_light`, and
    `overlay.basecase_sum` after refreshing the output-local canonical XMLs
- The first representative matrix-build reruns exposed a real follow-on seam:
  some output-local canonical XMLs were stale relative to the latest height/QMD
  feature work, so the branch now also refreshes those output-local XMLs from
  the latest generated K3Z XML content before treating them as canonical.
- Added docs-contract coverage that explicitly checks representative
  output-local canonical XMLs still carry the managed QMD and managed height
  feature families, so this stale-output-local-XML regression is now guarded.

## 2026-03-27 - Phase 46 VS Code and Coding-Agent Onboarding Docs Kickoff

- Promoted the VS Code plus coding-agent onboarding-docs idea from
  `planning/incoming_ideas.md` into the normal tracked workflow under GitHub
  issue `#42`.
- Created the new working branch:
  - `task/docs-vscode-coding-agent-onboarding`
- Defined the kickoff scope as adding a FEMIC-specific Sphinx guide that
  explains:
  - how to set up the local VS Code development environment;
  - how to work effectively with a local coding agent in this repo;
  - what the human developer still needs to supervise, validate, and steer.

## 2026-03-27 - Phase 46 VS Code and Coding-Agent Onboarding Docs Implemented

- Added a new parent Sphinx guide:
  - `docs/guides/vscode-coding-agent-onboarding.rst`
- The new guide covers:
  - local VS Code workspace setup for a FEMIC checkout;
  - minimum bootstrap/toolchain expectations before delegating work;
  - practical prompt-scoping guidance for a local coding agent;
  - the human review/supervision loop that still matters in FEMIC;
  - FEMIC-specific seams to watch for, such as stale generated artifacts,
    submodule drift, external runtime blockers, and issue-hygiene drift;
  - how this repo-specific workflow might later generalize into a broader
    reusable template for similar scientific-computing projects.
- Linked the new guide into the normal onboarding flow from:
  - `docs/guides/index.rst`
  - `docs/guides/developer-environment-bootstrap.rst`
  - `docs/guides/deployment-instances.rst`
  - `docs/guides/case-onboarding.rst`
- Added docs-contract coverage so the new guide page, core sections, and key
  FEMIC-specific markers are now tested.
- Validation passed:
  - `python -m pytest tests/test_docs_contract.py`
  - `python -m sphinx -b html docs _build/html -W`

## 2026-03-27 - Phase 47 Matrix Builder Window Automation Kickoff

- Promoted the Matrix Builder window-automation idea from
  `planning/incoming_ideas.md` into the normal tracked workflow under GitHub
  issue `#44`.
- Created the new working branch:
  - `feature/matrix-builder-window-automation`
- Defined the kickoff scope as automating closure of the Matrix Builder GUI
  window for the local native-Windows coding-agent workflow, while preserving
  log/manifest evidence and not masking real runtime failures.
- Identified the likely implementation seam in the parent repo:
  - `src/femic/patchworks_runtime.py`
  - specifically the native-Windows noninteractive `run_patchworks_command(...)`
    path used by `femic patchworks matrix-build`.

## 2026-03-27 - Phase 48 BatchTIPSY automation investigation kicked off

- Adopted the incoming-ideas BatchTIPSY automation feature into the normal
  workflow.
- Created GitHub issue `#46`: `Investigate and automate BatchTIPSY in local
  Windows rebuild workflow`.
- Created working branch `feature/batchtipsy-automation` in the parent repo and
  matching branch `feature/batchtipsy-automation` in the K3Z submodule.
- Added Phase 48 planning to `ROADMAP.md` with an explicit feasibility-first
  structure:
  - trace the real Windows BatchTIPSY seam;
  - implement the narrowest credible automation slice;
  - if full automation is not feasible, capture the blocker map cleanly so a
    later attempt has a much better starting point.

## 2026-03-27 - Phase 48 notes updated with BTC genetic-gain defaults clue

- Added `planning/batchtipsy_automation_approach.md` to capture the current
  BatchTIPSY cutover direction, the proven BTC CLI seam, and the remaining
  output-format uncertainty.
- Recorded the installed BTC defaults file
  `C:\Program Files\TIPSY 4.7\BTC\gw.txt` as a likely first source for default
  FEMIC genetic gain settings when generating BTC-compatible input.
- Noted in the roadmap/planning surface that the `gw.txt` defaults are framed
  by BTC itself as exploratory / educational rather than operational.

## 2026-03-27 - Phase 48 notes updated with BTC OAF defaults clue

- Recorded the installed BTC defaults file
  `C:\Program Files\TIPSY 4.7\BTC\oafs.txt` as a likely first source for
  default FEMIC OAF settings during the BTC cutover.
- Captured that `oafs.txt` appears to define packaged defaults and response
  metadata for:
  - `OAF1`
  - `OAF2`
  - `DR`
  - `AT`
  - `ArmV`
  - `ArmM`
  - `DSG`
  - `DSC`
- Added the OAF-default clue to the repo planning surfaces so it is part of the
  implementation plan rather than a chat-only observation.

## 2026-03-27 - Phase 48 notes updated with BTC output-field map clue

- Recorded the installed BTC field map
  `C:\Program Files\TIPSY 4.7\BTC\OutputColumns.txt` as the likely first
  output-field mapping reference if FEMIC can unlock a richer supported BTC
  non-GUI output mode.
- Captured that the file appears to expose stable BTC keys for many indicators
  we care about, including:
  - `Volume*`
  - `BasalArea*`
  - `MeanDBHg*`
  - `StemCount*`
  - diameter-class stock and mortality outputs
- Noted in the planning surfaces that `OutputColumns.txt` is a valuable clue
  and probable mapping layer, but not yet a proven live parser contract until a
  richer CLI/project output mode is demonstrated.

## 2026-03-27 - Phase 47 Matrix Builder Window Automation Implemented

- Added Windows-only supervised Matrix Builder execution in
  `src/femic/patchworks_runtime.py` for noninteractive native-Windows
  `femic patchworks matrix-build` runs.
- Replaced the old simple blocking `subprocess.run(...)` behavior on that path
  with a `Popen`-based supervisor that:
  - watches for fresh output activity in the target tracks directory;
  - attempts a narrow GUI close against matching Matrix Builder process
    windows;
  - force-stops the lingering Matrix Builder Java process if the visible window
    ignores the normal close signal.
- Added runtime-config control knobs:
  - `matrix_builder.auto_close_window_on_success`
  - `matrix_builder.auto_close_settle_seconds`
  - `matrix_builder.auto_close_timeout_seconds`
- Enabled those knobs in the parent Windows Patchworks runtime template and in
  the shipped K3Z Windows runtime configs so the local coding-agent rebuild
  workflow benefits immediately.
- Expanded the emitted Matrix Builder manifest to record Windows automation
  details, including launched PID, baseline/remaining matching process IDs,
  close method, and any force-stopped PIDs.
- Updated the parent onboarding/API docs plus the standalone K3Z operator
  runbook so the new Windows behavior and its caveats are documented.
- Validation passed:
  - `pytest tests/test_patchworks_runtime.py`
  - `ruff format src tests`
  - `ruff check src tests`
  - `mypy src`
  - full `pytest`
  - `pre-commit run --all-files`
  - parent Sphinx build
  - standalone K3Z Sphinx build
- Live Windows proof:
  - an initial smoke showed that `WM_CLOSE` / `.CloseMainWindow()` alone was
    insufficient because the visible `Matrix Builder` window stayed open;
  - the final smoke succeeded with `close_method = force_stop`, and the
    `Matrix Builder` process/window disappeared without manual user
    intervention;
  - a residual follow-up then proved the lingering Patchworks launcher
    `cmd.exe` shell tree can also be detected and cleaned up automatically, so
    the local coding-agent workflow no longer depends on a human to dismiss
    either visible window.
- Extended the Phase 48 BatchTIPSY automation planning notes toward the BTC
  cutover path by recording:
  - `C:\Program Files\TIPSY 4.7\BTC\gw.txt` as the best current candidate clue
    for default FEMIC genetic-gain settings;
  - `C:\Program Files\TIPSY 4.7\BTC\oafs.txt` as the best current candidate
    clue for default FEMIC OAF settings and packaged response metadata;
  - `C:\Program Files\TIPSY 4.7\BTC\OutputColumns.txt` as the likely first
    output-field map if FEMIC can unlock a richer supported BTC output mode
    beyond the default TSR volume/height CSV;
  - `C:\Program Files\TIPSY 4.7\BTC\TableRange.txt` as a likely BTC
    report/output range preset clue rather than a primary stand-parameter
    defaults source.
  - `C:\Program Files\TIPSY 4.7\BTC\FertRespMOF.txt` as the best current
    candidate clue for default FEMIC fertilizer-response settings during the
    BTC cutover.
  - `C:\Program Files\TIPSY 4.7\BTC\vriSpecies.txt` as the best current
    candidate clue for mapping VRI species codes into BTC / TIPSY species
    handling during the BTC CSV cutover.
  - confirmed from `userguide1.4.pdf` that BTC CLI supports:
    - `/TSR` using `TimberSupply.rpt`
    - `/FLP` using `ForestLandscapePlan.rpt`
    - direct `.btc` project loading from the command line
    - standard exit codes `0`, `2`, and `5`
  - confirmed a second unattended BTC CLI seam:
    - `/FLP` works from a writable local scratch directory and returns gross
      volume plus crown closure in CSV form.
  - shifted the preferred first automation target to a default unattended
    `/TSR + /FLP` mode so FEMIC can recover merchantable volume, height, gross
    volume, and crown closure without a human in the loop.
  - recorded the richer manual BTC `Yield` report as the best current optional
    fallback for extra indicators such as MAI, basal area, DBHg, stems/ha, and
    crop-tree fields.
  - documented the current stand-block parsing rule for richer `Yield` CSV
    outputs:
    - preserve input stand order
    - split output blocks whenever age decreases
    - fail fast if block count mismatches input stand count or if ages are not
      strictly increasing within a block
  - found a stronger rich-output clue via the manual BTC `Timber Supply SQL`
    report:
    - `MSYT_output.sql` / `MSYT_error.sql` include explicit `BTC_STAND` /
      `BTC_ERROR` schemas
    - rows carry `StandID`, `RowID`, and `feature_id`
    - this removes the stand-ID ambiguity of the plain `Yield` CSV and is now
      the preferred rich optional-mode output contract when available
- 2026-03-28 (Phase 48 BTC report-template tooling): added the first FEMIC-side
  BTC custom-report generator and validated the `/TSR` report-coupling seam.
  - Added parser/writer utilities in `src/femic/pipeline/tipsy.py` for:
    - reading existing BTC `.rpt` templates
    - cloning/extending curated column sets
    - writing vetted replacement report files
  - Added CLI surface:
    - `femic tipsy write-btc-report-template`
  - Added built-in presets:
    - `tsr-unattended-default`
    - `timber-supply-sql`
  - Live reverse-engineering results on the copied BTC install:
    - stock `TimberSupply.rpt` under `/TSR` still works cleanly
    - swapping in `ForestLandscapePlan.rpt` as `TimberSupply.rpt` makes `/TSR`
      emit FLP-style `gVol_*` and `CC_*` output cleanly
    - a small transposed TSR+FLP mashup also runs cleanly and yields all four
      unattended indicators in one `/TSR` output file:
      - merchantable volume
      - height
      - gross volume
      - crown closure
  - Important constraints learned:
    - `TimberSupply SQL.rpt` is not a safe drop-in `/TSR` replacement; it
      loads but crashes during `BatchProcess()`
    - oversized `AllFieldsSQL.rpt`-style templates can crash even earlier
      during report load/startup
    - unattended FEMIC BTC mode should therefore target vetted compatible
      transposed templates, not arbitrary SQL/database/all-fields report swaps
  - Validation passed:
    - `.venv\\Scripts\\python.exe -m pytest tests/test_tipsy.py tests/test_tipsy_report_cli.py`
    - `.venv\\Scripts\\python.exe -m ruff check src/femic/pipeline/tipsy.py src/femic/cli/main.py tests/test_tipsy.py tests/test_tipsy_report_cli.py`
- 2026-03-28 (Phase 48 BTC runner smoke): proved the first end-to-end
  unattended `/TSR` runner seam on the local Windows host.
  - Added supervised BTC runtime preparation and CLI execution support in
    `src/femic/pipeline/tipsy.py` plus the new
    `femic tipsy run-btc` surface in `src/femic/cli/main.py`.
  - Fixed a CLI handoff bug so `--report-preset tsr-unattended-default`
    preserves the preset identity all the way into the runtime layer instead of
    being flattened into a generic custom-template render.
  - Fixed default output/error destination handling so runs against read-only
    sample inputs keep returned files in writable scratch rather than trying to
    copy them back into `Program Files`.
  - Live proof:
    - copied BTC install staged under `tmp/btc_runner_smoke`
    - stock `TimberSupply.rpt` patched in place with the vetted transposed
      unattended mashup
    - supervised `/TSR` run completed with exit code `0`
    - no lingering `TIPSYbtc.exe` process remained
    - manifest `btc_manifest-btc_runner_smoke_20260328_d.json` recorded
      status `ok`
    - returned output columns include:
      - `feature_id`
      - `MVcon_*`, `MVdec_*`
      - `HTcon_*`, `HTdec_*`
      - `gVol_*`
      - `CC_*`
  - Validation passed:
    - `.venv\\Scripts\\python.exe -m pytest tests/test_tipsy.py tests/test_tipsy_report_cli.py`
    - `.venv\\Scripts\\python.exe -m ruff check src/femic/pipeline/tipsy.py src/femic/pipeline/__init__.py src/femic/cli/main.py tests/test_tipsy.py tests/test_tipsy_report_cli.py`
- 2026-03-28 (Phase 48 MSYT writer slice): added the first canonical Stage 01a
  BTC input writer.
  - Added a conservative `MSYT.csv` writer in `src/femic/pipeline/tipsy.py`
    that maps the current TIPSY `f`-table payload onto BTC's sample-schema
    columns.
  - Added canonical path helper:
    - `03_input-tsaXX.csv`
  - The first slice uses:
    - AU as `feature_id` / `opening_id`
    - planted treatment-unit fields from `SPP_n`, `PCT_n`, `Density`,
      `Regen_Delay`, `GW_n`, `OAF1`, `OAF2`, and `SI`
    - empty natural treatment-unit fields for now
  - Updated the legacy Stage 01a runner so `01a_run-tsa.py` now emits
    `03_input-tsaXX.csv` beside the older artifacts using the same built
    `f`-table payload.
  - Validation passed:
    - `.venv\\Scripts\\python.exe -m pytest tests/test_tipsy.py tests/test_tipsy_report_cli.py`
    - `.venv\\Scripts\\python.exe -m ruff check src/femic/pipeline/tipsy.py src/femic/pipeline/__init__.py src/femic/resources/legacy/01a_run-tsa.py tests/test_tipsy.py tests/test_tipsy_report_cli.py`
    - `.venv\\Scripts\\python.exe -m mypy src/femic/pipeline/tipsy.py src/femic/pipeline/__init__.py`
- 2026-03-28 (Phase 48 BTC post-TIPSY parser slice): broadened the legacy
  post-TIPSY seam so unattended BTC `/TSR` CSV output can flow back into FEMIC
  managed-curve assembly.
  - Added `parse_btc_tsr_transposed_output(...)` in
    `src/femic/pipeline/tipsy.py` to convert the vetted transposed BTC output
    into long-form FEMIC curve rows keyed by the existing `20000 + AU`
    managed-curve convention.
  - The first-cut parser currently maps:
    - `Yield = MVcon + MVdec`
    - `Height = max(HTcon, HTdec)`
    - `GrossYield = gVol`
    - `CrownCover = CC`
    - `DBHq = NaN`
    - `TPH = NaN`
  - Updated the legacy `src/femic/resources/legacy/01b_run-tsa.py` path so it
    now branches to the BTC CSV parser whenever the returned TIPSY artifact is
    `.csv`, while preserving the old fixed-width `.out` parser as a temporary
    compatibility path.
  - Exported the new parser from `src/femic/pipeline/__init__.py` and added a
    focused regression test in `tests/test_tipsy.py` that proves the returned
    `feature_id` rows map back to FEMIC managed-curve ids correctly.
  - Validation passed:
    - `.venv\\Scripts\\python.exe -m pytest tests/test_tipsy.py tests/test_tipsy_report_cli.py`
    - `.venv\\Scripts\\python.exe -m ruff check src/femic/pipeline/tipsy.py src/femic/pipeline/__init__.py src/femic/resources/legacy/01b_run-tsa.py tests/test_tipsy.py tests/test_tipsy_report_cli.py`
    - `.venv\\Scripts\\python.exe -m mypy src/femic/pipeline/tipsy.py src/femic/pipeline/__init__.py`
- 2026-03-28 (Phase 48 BTC orchestration slice): tied the new Stage 01a MSYT
  writer, unattended BTC runner, and BTC CSV parser together into one actual
  workflow surface.
  - Added `run_btc_and_post_tipsy_bundle_with_manifest(...)` in
    `src/femic/workflows/legacy.py`.
  - Added the new CLI command:
    - `femic tsa btc-post-tipsy`
  - The new orchestration path now:
    - reads `data/03_input-tsaXX.csv`
    - runs unattended BTC `/TSR`
    - writes `data/04_output-tsaXX.csv` / `data/04_error-tsaXX.csv`
    - resumes the existing post-TIPSY bundle assembly against the returned CSV
      seam
  - Preserved the legacy `femic tsa post-tipsy` contract so it still defaults
    to the old `.out` seam unless explicitly overridden by orchestration code.
  - Added regression coverage in:
    - `tests/test_workflows_post_tipsy.py`
    - `tests/test_tipsy_report_cli.py`
  - Validation passed:
    - `.venv\\Scripts\\python.exe -m pytest tests/test_tipsy.py tests/test_tipsy_report_cli.py tests/test_workflows_post_tipsy.py`
    - `.venv\\Scripts\\python.exe -m ruff check src/femic/pipeline/tipsy.py src/femic/pipeline/__init__.py src/femic/resources/legacy/01b_run-tsa.py src/femic/workflows/legacy.py src/femic/cli/main.py tests/test_tipsy.py tests/test_tipsy_report_cli.py tests/test_workflows_post_tipsy.py`
    - `.venv\\Scripts\\python.exe -m mypy src/femic/pipeline/tipsy.py src/femic/pipeline/__init__.py src/femic/workflows/legacy.py`
- 2026-03-28 (Phase 48 K3Z BTC smoke follow-up): fixed the unattended BTC
  parser identity rule for real K3Z managed-curve ids and proved the runner +
  parser on the shipped K3Z instance data.
  - Updated `parse_btc_tsr_transposed_output(...)` so returned BTC
    `feature_id` values are preserved as-is when they are already in FEMIC
    managed-curve-id space (`>= 20000`) and only lifted with `20000 + id`
    for legacy/raw stand ids.
  - Added regression coverage in `tests/test_tipsy.py` for both cases:
    - raw `feature_id=1000 -> AU=21000`
    - existing managed `feature_id=21000 -> AU=21000`
  - Generated a real K3Z BTC input handoff at:
    - `external/femic-k3z-instance/data/03_input-tsak3z.csv`
  - Proved a real unattended BTC `/TSR` run succeeds against that K3Z input:
    - run id: `k3z_btc_tsr_smoke_20260328`
    - returned transposed CSV includes 14 stands and 79 columns
    - parsed output preserves the expected K3Z managed ids `21000..23003`
  - Proved the remaining blocker is now downstream legacy post-TIPSY resume,
    not BTC:
    - `femic tsa btc-post-tipsy --instance-root external/femic-k3z-instance --tsa k3z`
      stops on missing
      `external/femic-k3z-instance/data/vdyp_prep-tsak3z.pkl`
  - Validation passed:
    - `.venv\\Scripts\\python.exe -m pytest tests/test_tipsy.py tests/test_tipsy_report_cli.py tests/test_workflows_post_tipsy.py`
    - `.venv\\Scripts\\python.exe -m ruff check src/femic/pipeline/tipsy.py src/femic/pipeline/__init__.py src/femic/resources/legacy/01b_run-tsa.py src/femic/workflows/legacy.py src/femic/cli/main.py tests/test_tipsy.py tests/test_tipsy_report_cli.py tests/test_workflows_post_tipsy.py`
    - `.venv\\Scripts\\python.exe -m mypy src/femic/pipeline/tipsy.py src/femic/pipeline/__init__.py src/femic/workflows/legacy.py`
- 2026-03-28 (Phase 48 K3Z downstream rebuild fallback): stopped fighting the
  missing `vdyp_prep-tsak3z.pkl` seam and taught the downstream post-TIPSY
  bundle builder to resume from the shipped cached artifact set instead.
  - Added a new fallback in `src/femic/workflows/legacy.py`:
    - when `vdyp_prep-tsaXX.pkl` is missing but `data/model_input_bundle/au_table.csv`
      exists, FEMIC now reconstructs the legacy AU<->(stratum, SI) maps from
      the persisted AU table instead of failing immediately.
  - Added regression coverage in `tests/test_workflows_post_tipsy.py`.
  - Real K3Z smoke now succeeds end to end:
    - generated `external/femic-k3z-instance/data/03_input-tsak3z.csv`
    - ran `femic tsa btc-post-tipsy --instance-root external/femic-k3z-instance --tsa k3z`
    - completed with `au_rows=27`, `curve_rows=41`, `curve_points=8244`
  - The successful downstream rebuild refreshed the shipped K3Z artifacts:
    - `data/tipsy_curves_tsak3z.csv`
    - `data/model_input_bundle/{au_table,curve_table,curve_points_table}.csv`
    - `plots/tipsy_vdyp_tsak3z-*.png`
    - and the new BTC seam files:
      - `data/03_input-tsak3z.csv`
      - `data/04_output-tsak3z.csv`
      - `data/04_error-tsak3z.csv`
  - Validation passed:
    - `.venv\\Scripts\\python.exe -m pytest tests/test_tipsy.py tests/test_tipsy_report_cli.py tests/test_workflows_post_tipsy.py`
    - `.venv\\Scripts\\python.exe -m ruff check src/femic/pipeline/tipsy.py src/femic/pipeline/__init__.py src/femic/resources/legacy/01b_run-tsa.py src/femic/workflows/legacy.py tests/test_tipsy.py tests/test_tipsy_report_cli.py tests/test_workflows_post_tipsy.py`
    - `.venv\\Scripts\\python.exe -m mypy src/femic/pipeline/tipsy.py src/femic/pipeline/__init__.py src/femic/workflows/legacy.py`
- 2026-03-28 (Phase 48 next-bank planning): pulled the top three BTC-rich-output
  ideas from `planning/incoming_ideas.md` into tracked Phase 48 tasks.
  - Added roadmap subtasks:
    - `P48.2d1` stand-table / DBH-class stem-count indicator bank
    - `P48.2d2` log-grade / lumber-grade product-output bank
    - `P48.2d3` QMD revisit against richer BTC-native diameter signals
  - Tightened the plan so these are explicitly FEMIC-level optional
    indicator-bank activation switches, with a dedicated K3Z
    intensive-silviculture proving-ground subvariant as the safe first
    full-pipeline test surface rather than the active student-facing variants.
  - Opened the matching GitHub task issues:
    - `#47`
    - `#48`
    - `#49`
  - Removed those adopted ideas from the incoming queue so the inbox now
    reflects only still-unclaimed work.
- 2026-03-28 (Phase 48 first stand-table bank probe reality check): tested the
  first richer stand-table fields against the unattended `/TSR` seam and
  confirmed that this bank is still exploratory rather than near-trivial.
  - Starting from the proven safe unattended transposed `/TSR` mashup
    (`MVcon`, `MVdec`, `HTcon`, `HTdec`, `gVol`, `CC`), probed these richer
    additions one at a time:
    - `DBHg`
    - `SPH`
    - `StemCount000`
    - `StemCount125`
    - `StemCount175`
    - `Crop250VolUtil125`
    - `Crop250DBHgMean`
    - `Crop250LiveCrown`
  - Every first-cut stand-table probe failed at BTC execution time with stacked
    `.NET` modal crash dialogs.
  - Representative failure was a `System.NullReferenceException` in
    `TIPSY.frmTIPSY.BatchProcess()`.
  - Updated `ROADMAP.md`, `planning/batchtipsy_automation_approach.md`, and
    GitHub issue `#46` so the current contract is explicit:
    - the unattended `/TSR` seam is proven only for the conservative default
      bank;
    - richer stand-table outputs should be treated as exploratory seam-finding
      work until a compatible template family or alternate BTC mode is proven.
- 2026-03-28 (Phase 48 full-installation easter-egg note): broadened the
  BatchTIPSY reverse-engineering plan to cover the full installed
  `C:\Program Files\TIPSY 4.7\` tree rather than only the obvious BTC files.
  - Added the new clue from `CBM/TIPSY-CBM.pdf` page 1:
    - BatchTIPSY command-line switch `-RGM`, described as creating one regime
      file per processed line for later TIPSY-to-CBM loading.
  - Updated the planning surfaces so Phase 48 now explicitly includes:
    - mining all packaged PDFs for CLI/runtime/report clues;
    - extracting `.chm` help content into a platform-independent,
      human-readable, machine-scannable format;
    - and continuing the broader "easter egg hunt" across Tcl/report/config
      files for under-documented runtime seams.
  - Also recorded the more strategic interpretation of the same clue:
    - although `-RGM` was surfaced from the TIPSY-CBM context, regime-file
      export may also be the missing seam needed to unlock batch FANSIER
      workflows in FEMIC.
    - future planning should therefore consider both:
      - FEMIC -> BTC/BatchTIPSY -> regime files -> TIPSY-CBM
      - FEMIC -> BTC/BatchTIPSY -> regime files -> FANSIER
- 2026-03-28 (Phase 48 docs/contract sweep): switched the current-facing
  parent and K3Z docs from the old DAT/OUT BatchTIPSY seam to the new
  BTC-first contract.
  - Updated the contract pages and Stage 01 guides so the default supported
    seam is now:
    - `03_input-tsaXX.csv`
    - unattended `TIPSYbtc.exe /TSR`
    - returned `04_output-tsaXX.csv` / `04_error-tsaXX.csv`
    - `femic tsa btc-post-tipsy`
  - Demoted `02_input-*.dat` / `04_output-*.out` to legacy compatibility notes
    instead of teaching them as the normal operator path.
  - Updated the CLI/API reference pages and active K3Z runbooks to point at the
    new BTC-first resume flow.
- 2026-03-28 (Phase 48 post-cutover regression triage kickoff): opened a new
  bug track for the K3Z QMD-account regression discovered immediately after the
  core unattended BTC cutover landed.
  - Current symptom report:
    - shipped K3Z `base` and `ctfert_l15h5` launch cleanly in Patchworks, but
      both standing `feature.QMD.*` and harvested `product.QMD.*` accounts
      appear empty
  - Current leading hypothesis:
    - the QMD account families still exist syntactically, but the upstream
      attribute values or curve bindings may now be null/empty somewhere in the
      track/XML/managed-curve path
  - Planning surfaces now treat this as the next active Phase 48 bug task
    rather than part of the richer optional BTC indicator-bank expansion
- 2026-03-28 (Phase 48 K3Z QMD regression fix): repaired the post-cutover K3Z
  QMD-account collapse on the working managed-density fallback path and recorded
  the current BTC stand-structure seam boundary explicitly.
  - Confirmed root cause:
    - the core unattended BTC seam currently emits no live managed `TPH`
      signal in `tipsy_curves_tsak3z.csv`;
    - managed QMD generation in the Patchworks exporter was still expecting
      managed `TPH` curve points, so managed QMD surfaces collapsed even though
      the QMD feature/product account names still existed in XML and tracks.
  - Repair that is now in place:
    - managed standing stems-per-ha and managed QMD now fall back to Stage 01a
      / BTC-input stand density when managed `TPH` is absent.
  - Rebuilt and smoke-checked the active K3Z family directly:
    - `base`
    - `ctfert_*`
    - `pct_*`
    - `intensive_*`
    - overlays
  - Direct smoke evidence after rebuild:
    - representative `feature.QMD.managed.*` rows are present again in
      `features.csv`;
    - representative `feature.QMD.managed.*` rows now have non-zero `SUM`
      multipliers in `accounts.csv`;
    - representative `product.QMDNumerator.managed.*` rows are present again on
      the relevant treatment surfaces.
  - Confirmed follow-on boundary:
    - first attempts to restore a live BTC-native managed stand-structure
      signal through unattended `/TSR` still fail, even using the exact stock
      `Yield.rpt` token forms:
      - `SPH:000`
      - `DBHg:000`
      - `BasalArea:000`
    - those richer stand-table signals remain optional-bank seam work under
      issue `#47`, not blockers to closing the K3Z QMD regression bug.
  - Tightened the agent contract again:
    - obvious low-cost, high-reward direct smoke checks must be done
      proactively, without waiting for the developer to prompt for them.
  - Added the missing direct whole-family smoke pass before closeout:
    - reran Matrix Builder across the full active K3Z variant family
      (`base`, `ctfert_*`, `pct_*`, `intensive_*`, and overlay surfaces);
    - then explicitly verified across every rebuilt track family that
      `feature.QMD.managed.*` accounts/features and
      `product.QMDNumerator.managed.*` product accounts are populated and
      non-null in the runtime-facing CSV surfaces;
    - user also confirmed live Patchworks launches of `base.pin` and
      `ctfert_l15h5.pin` show QMD accounts back online.
## 2026-03-28 - Phase 48 stand-table bank ratchet plan tightened

- Reframed issue `#47` around a strict one-column-at-a-time unattended `/TSR`
  ratchet from the current known-good template instead of large speculative
  report-template jumps.
- Added the parallel seam-detection mission: every failing BTC report token
  should now be recorded as a clue about the hidden `/TSR` compatibility
  pattern, not just as a rejection.
- Updated `ROADMAP.md` and `planning/batchtipsy_automation_approach.md` to make
  the two-track method explicit before starting the next stand-table bank probe
  loop.

## 2026-03-28 - Phase 48 unattended BTC stand-table probe now leaves a compatibility ledger

- Extended `femic tipsy probe-btc-columns` so each probe result now records:
  - output/error artifact existence,
  - BTC modal auto-close behavior,
  - a failure classification,
  - and clue hits from stock reports, `OutputColumns.txt`, and BTC Tcl files.
- Added an always-written machine-readable compatibility ledger for issue `#47`
  probe runs.
- Proved the first unattended seven-column stand-table batch can now run
  without any user dialog-clicking.
- First batch result:
  - `MAI`
  - `BasalArea:000`
  - `DBHg:000`
  - `SPH:000`
  - `StemCount000`
  - `StemCount125`
  - `StemCount175`
  all failed cleanly in the current transposed unattended `/TSR` seam with:
  - exit code `1`,
  - no output CSV,
  - FEMIC auto-closing the BTC/.NET modal path,
  - and failure classification `missing_output_exit_1`.
- 2026-03-28 (Phase 48 TSR horizon alignment): updated FEMIC's stock-based
  unattended `TimberSupply.rpt` patch path so the default TSR overlay uses:
  - `TableRange=0-350:10|#	MAX=350	INC=10`
  instead of the older 120-year range, aligning the BTC unattended output
  horizon with FEMIC's longer VDYP curve timeline.
- 2026-03-28 (Phase 48 critical `/TSR` overlay breakthrough): confirmed that
  plain installed `TIPSYbtc.exe /TSR` consults the per-user
  `Documents\\BatchTIPSY Composer\\TimberSupply.rpt` overlay before falling
  back to the stock installed report, and that preserving the stock TSR report
  structure is the key to safe unattended extension.
  - With the broken user overlay present, plain installed `/TSR` failed.
  - With the overlay removed, stock `/TSR` succeeded again.
  - With the overlay replaced by a stock-based safe enhanced TSR template,
    plain installed `/TSR` also succeeded again.
  - Re-running the first stand-table batch against that real overlay seam then
    showed that all seven previously “failing” candidates actually pass:
    - `MAI`
    - `BasalArea:000`
    - `DBHg:000`
    - `SPH:000`
    - `StemCount000`
    - `StemCount125`
    - `StemCount175`
  - This means the copied-install/generated-template seam was too pessimistic:
    the real `/TSR` game is about preserving the hidden stock
    `TimberSupply.rpt` contract and extending it conservatively through the
    live overlay path.
- 2026-03-28 (Phase 48 Windows overlay path portability): replaced the
  machine-specific BTC overlay lookup in FEMIC source code with a generic
  Windows Documents-folder resolver so unattended `/TSR` probing and runtime
  patching no longer assume a user-specific OneDrive directory name.
- 2026-03-29 (Phase 48 first optional BTC bank switch): wired the first FEMIC
  optional unattended BTC indicator-bank switch,
  `--indicator-bank stand-structure-basic`, through the real per-user TSR
  overlay seam with backup/restore.
  - The bank now carries:
    - `MAI`
    - `BasalArea:000`
    - `DBHg:000`
    - `SPH:000`
    - `StemCount000`
    - `StemCount125`
    - `StemCount175`
  - The key implementation fix was to stop treating the copied-install-local
    `TimberSupply.rpt` as authoritative when a live user overlay exists;
    FEMIC now patches the real user-overlay report path for the TSR preset so
    requested bank columns actually appear in returned output.
  - Real smoke proof now exists for:
    - `femic tipsy run-btc <MSYT.csv> --indicator-bank stand-structure-basic`
    which returns the conservative default families plus:
    - `MAI_*`
    - `BasalArea000_*`
    - `DBHg000_*`
    - `SPH000_*`
    - `StemCount000_*`
    - `StemCount125_*`
    - `StemCount175_*`
    while preserving the 350-year TSR horizon.
- 2026-03-29 (Phase 48 proving-ground rollout rule): tightened the plan for
  issue `#47` so the first stand-structure bank rollout uses a dedicated K3Z
  `intensive_*` proving-ground surface rather than modifying any current
  student-facing variants.
  - The bank-enabled BTC/TIPSY managed-curve bundle can exist at the shared
    K3Z data layer.
  - But the new Patchworks feature/account bindings should first be surfaced
    only on a dedicated pilot surface, so the full FEMIC -> BTC -> Patchworks
    lifecycle can be validated without risking active class projects.
- 2026-03-29 (Phase 48 first K3Z stand-structure proving ground): completed the
  first bank rollout on the dedicated K3Z proving-ground surface
  `intensive_light_standstructure`.
  - Added the dedicated K3Z proving-ground configs and launch entrypoint:
    - `config/silviculture.k3z.intensive_light_standstructure.yaml`
    - `config/patchworks.variant.intensive_light_standstructure.yaml`
    - `config/patchworks.runtime.intensive_light_standstructure.windows.yaml`
    - `models/k3z_patchworks_model/analysis/intensive_light_standstructure.pin`
  - Fixed the Patchworks `protoaccounts -> accounts` promotion bug where the
    new stand-structure bank rows were collapsing to token-only keys and
    therefore missing their area-normalized `SUM` overrides.
  - Rebuilt the proving-ground Matrix Builder surface and confirmed:
    - the new managed feature bindings exist in the validated `forestmodel.xml`
    - `tracks_intensive_light_standstructure/accounts.csv` now carries 84
      managed stand-structure rows with nontrivial reciprocal-area `SUM`
      multipliers
    - ordinary `base` and `ctfert_l15h5` tracks remain at zero rows for the
      new bank, so the first Patchworks rollout stayed quarantined to the
      proving-ground surface
  - Targeted validation passed:
    - `pytest tests/test_patchworks_runtime.py tests/test_tipsy.py tests/test_tipsy_report_cli.py tests/test_workflows_post_tipsy.py`
    - `ruff check src/femic/patchworks_runtime.py src/femic/pipeline/tipsy.py src/femic/fmg/core.py src/femic/fmg/adapters.py src/femic/fmg/patchworks.py tests/test_patchworks_runtime.py tests/test_tipsy.py tests/test_tipsy_report_cli.py tests/test_workflows_post_tipsy.py`
    - `mypy src/femic/patchworks_runtime.py src/femic/pipeline/tipsy.py src/femic/fmg/core.py src/femic/fmg/adapters.py src/femic/fmg/patchworks.py`
- 2026-03-29 (Phase 48 proving-ground manual validation note): recorded the
  developer's quick manual Patchworks check after launching
  `intensive_light_standstructure`.
  - Developer summary: the new bank "looks pretty good".
  - Interpretation:
    - the first unattended BTC stand-structure bank is broadly working end to
      end in the intended proving-ground runtime;
    - later slower indicator-by-indicator interpretation, validation, and
      possible pruning of bank contents is still expected, but that follow-on
      review is not a blocker to the initial proving-ground landing.
- 2026-03-28 (Phase 49 headless Patchworks kickoff): promoted the no-GUI
  Patchworks runner idea out of the inbox and into the active tracked workflow.
  - Opened GitHub issue `#54` for the headless Patchworks runner and scenario
    orchestration seam.
  - Added Phase 49 to `ROADMAP.md` and wired the new governing tracker into
    the implementation notes.
  - Promoted `planning/patchworks_nogui_mode.md` from an inbox note into an
    active planning surface for the first minimal unattended
    launch/run/report/exit slice.
- 2026-03-28 (Phase 49 headless Patchworks failure supervision): taught the
  Windows headless Patchworks runner to supervise the proving-ground launch
  actively instead of launching and waiting forever.
  - FEMIC now watches the headless trace/log outputs for explicit success and
    failure markers.
  - On failure, FEMIC now kills the Patchworks Java process tree itself and
    returns a normal CLI failure result with trace/manifest evidence instead of
    leaving dead console shells for the human to close.
  - Real proving-ground smoke `p49_smoke_20260328i` still fails in the known
    Patchworks scheduler seam (`Not suspended` during
    `resume()/waitForIterations()`), but the human babysitting problem for dead
    failed runs is now removed.
- 2026-03-28 (Phase 49 first successful headless Patchworks save-stage proof):
  proved the first real unattended Patchworks run/save/exit seam on the K3Z
  proving-ground model.
  - The critical fix was in the proving-ground BeanShell helper:
    `waitForIterations(...)` must own scheduler startup in this no-GUI path;
    pre-issuing `control.resume()` caused the earlier
    `java.lang.IllegalStateException: Not suspended` failure.
  - Real proving-ground smoke `p49_smoke_20260328j` now:
    - launches and initializes headlessly;
    - waits one iteration successfully;
    - suspends cleanly after the wait;
    - saves stage `analysis/headless_runs/p49_smoke_20260328j`;
    - writes a manifest with `returncode=0`,
      `terminal_state=success`, and `saved_file_count=1695`;
    - returns control without any human cleanup because FEMIC terminates the
      Patchworks Java tree automatically after the success marker.
- 2026-03-28 (Phase 49 target-activation edge clarified): after inspecting the
  first successful saved proving-ground stage, confirmed that the current
  no-GUI seam is still saving a passive default state.
  - `scenario/schedule.csv` was empty in the first successful saved stage,
    so the next Patchworks headless milestone is now explicit:
    activate one existing flow target, set a modest minimum annual value, run
    a bounded wait/save cycle, and inspect `targetStatus.csv`,
    `targetSummary.csv`, and `schedule.csv` directly to prove a real scenario
    action occurred.
- 2026-03-28 (Phase 49 first real headless scenario smoke): extended the
  proving-ground no-GUI Patchworks seam from passive save-stage proof to a
  real saved scheduling smoke.
  - FEMIC now supports a minimal headless scenario mode,
    `max-even-flow-smoke`, with optional target and minimum-annual controls.
  - Direct activation of `flow.even.product.Yield.managed.Total` proved that
    target activation changed objective state but still left `schedule.csv`
    empty.
  - Switching the smoke to the underlying
    `product.Yield.managed.Total` target produced the first fully useful
    proving-ground result (`p49_smoke_20260328p`):
    - `targetStatus.csv` shows `product.Yield.managed.Total` active;
    - `targetSummary.csv` shows non-zero managed-yield currents and derived
      `flow.even.product.Yield.managed.Total` values;
    - `schedule.csv` is non-empty and contains real managed treatments;
    - FEMIC saved the stage and self-terminated the Patchworks Java tree
      cleanly after the success marker.
- 2026-03-28 (Phase 49 two-phase even-flow headless smoke): proved the real
  seed-then-even-flow scheduler pattern on the K3Z proving ground.
  - the proving-ground BeanShell helper now treats
    `max-even-flow-smoke` as a two-phase headless scenario:
    1. seed the underlying `product.Yield.managed.Total` target so the final
       period is not mathematically empty;
    2. suspend;
    3. activate the companion
       `flow.even.product.Yield.managed.Total` target; and
    4. run the second wait phase before saving the stage.
  - real proving-ground smoke `p49_smoke_20260328q` now shows both targets
    active in `scenario/targetStatus.csv`, non-zero currents for both in
    `scenario/targetSummary.csv`, and a non-empty `schedule.csv` (677 lines)
    with real managed treatments.
- 2026-03-28 (Phase 49 default-target headless usability proof): confirmed the
  same two-phase even-flow seam works through the normal CLI/default-target
  path, not just a hand-crafted target override.
  - real proving-ground smoke `p49_smoke_20260328r` omitted
    `--scenario-target` and relied on FEMIC's default
    `product.Yield.managed.Total` resolution;
  - the saved stage still recorded both
    `product.Yield.managed.Total` and
    `flow.even.product.Yield.managed.Total` as active; and
  - `schedule.csv` remained non-empty (788 lines).
- 2026-03-28 (Phase 49 base-K3Z closeout proof): shifted the authoritative
  proving-ground smoke from the intensive variant to the real base K3Z surface
  and baked in useful scheduler defaults for `max-even-flow-smoke`.
  - FEMIC now defaults `max-even-flow-smoke` to `100000` iterations when the
    user leaves `--iterations` at its placeholder value.
  - The headless helper now configures the even-flow companion target with:
    - minimum = maximum = `0` for all periods
    - minimum weight = maximum weight = `100` for all periods
  - Real base-K3Z smoke `p49_base_closeout_20260328a` proved the full seam on
    `analysis/base.pin`:
    - both `product.Yield.managed.Total` and
      `flow.even.product.Yield.managed.Total` were active;
    - `targetSummary.csv` showed nearly level even-flow deviations around zero
      and strong non-zero underlying managed-yield currents;
    - `schedule.csv` was non-empty (341 lines).
- 2026-03-28 (Phase 49 upgraded base-K3Z proving-ground recipe): strengthened
  the same headless seam from live K3Z operator guidance and verified the
  stronger target recipe on the real base surface.
  - The headless helper now also:
    - forces `product.Yield.managed.Total` into linear penalty mode;
    - sets a generous maximum of `200000` in every period at default weight;
    - seeds a `10000` minimum before the even-flow companion is activated.
  - Real base-K3Z smoke `p49_base_closeout_20260328b` against `analysis/base.pin`
    completed cleanly with both targets active.
  - `targetStatus.csv` showed:
    - `product.Yield.managed.Total` active with `LINEAR=true`; and
    - `flow.even.product.Yield.managed.Total` active in min/max mode.
  - `targetSummary.csv` showed the base target stabilized around `122200` per
    period inside the `100000..200000` band, while even-flow deviations stayed
    tightly clustered near zero.
  - `schedule.csv` remained non-empty (480 lines).
- 2026-03-29 (Issue #49 BTC-native managed QMD preference on the K3Z proving
  ground): revised the managed QMD exporter so the stand-structure proving
  ground now prefers richer BTC-native diameter signals instead of relying only
  on the older volume/height/stems approximation.
  - Exporter change:
    - `src/femic/fmg/patchworks.py` now builds managed QMD in this order when
      the first BTC stand-structure bank is present:
      - direct `DBHg000`
      - QMD reconstructed from `BasalArea000` plus `SPH000` /
        `StemCount000`
      - fallback to the older approximation
    - the existing CT/fert QMD response multipliers remain in place on top of
      that revised managed baseline.
  - Focused validation:
    - `pytest tests/test_fmg_patchworks.py -q`
    - `ruff check src/femic/fmg/patchworks.py tests/test_fmg_patchworks.py`
  - Proving-ground rebuild evidence:
    - checkpoint-based full export remains blocked on the known K3Z
      `checkpoint1` vs `checkpoint7/au` seam, so the refreshed
      `output/patchworks_k3z_intensive_light_standstructure_validated/forestmodel.xml`
      was regenerated through the lower-level bundle-table builder first;
    - `femic patchworks matrix-build --instance-root external/femic-k3z-instance --config config/patchworks.runtime.intensive_light_standstructure.windows.yaml --run-id k3z_intensive_light_standstructure_qmd_20260329a`
      then completed successfully against that refreshed XML.
  - Direct output inspection:
    - in the rebuilt ForestModel XML, representative managed QMD curves now
      match the corresponding BTC-native `DBHg000` curve directly (for example
      `au_CWHvm_FDC_HW_M_managed_qmd` matches
      `au_CWHvm_FDC_HW_M_managed_DBHg000` on the refreshed proving ground);
    - rebuilt `tracks_intensive_light_standstructure/{protoaccounts,accounts}.csv`
      still carry the managed standing and harvested-QMD surfaces, including
      `feature.QMD.managed.CWHvm_FDC_HW_M`,
      `product.QMDNumerator.managed.CWHvm_FDC_HW_M.{PCT,CT,CC}`, and their
      live ratio-account surfaces.
  - Headless Patchworks smoke:
    - `femic patchworks run-headless models/k3z_patchworks_model/analysis/intensive_light_standstructure.pin --instance-root external/femic-k3z-instance --config config/patchworks.runtime.intensive_light_standstructure.windows.yaml --run-id k3z_intensive_light_standstructure_qmd_smoke_20260329a --scenario-mode max-even-flow-smoke --scenario-min-annual 10000`
      completed cleanly and initially saved a full report bundle under the
      tracked `analysis/headless_runs/...` tree, which prompted a follow-up
      runtime cleanup/guardrail pass;
    - `scenario/targetStatus.csv` shows both
      `product.Yield.managed.Total` and
      `flow.even.product.Yield.managed.Total` active;
    - `scenario/schedule.csv` is non-empty and includes real managed
      `PCT`, `CT`, and `CC` actions;
    - saved target reports confirm the QMD surfaces are live in runtime-facing
      outputs, for example:
      - `targets/feature_QMD_managed_CWHvm_FDC_HW_M.csv`
      - `targets/product_QMD_managed_CWHvm_FDC_HW_M_CT.csv`
      - `targets/product_QMDNumerator_managed_CWHvm_FDC_HW_M_CT.csv`
  - Documentation updates:
    - updated the parent API docs plus the standalone K3Z docs to describe the
      revised managed-QMD preference order and the proving-ground headless QA
      path.
  - Follow-up runtime hygiene:
    - `src/femic/patchworks_runtime.py` now defaults unattended
      `reportWriter.saveStage(...)` output to
      `vdyp_io/logs/headless_stage/<run_id>` instead of the tracked
      `analysis/` tree when `--stage-label` is omitted;
    - the standalone K3Z `.gitignore` now ignores `vdyp_io/logs/`,
      `models/k3z_patchworks_model/analysis/headless_runs/`, and
      variant-track `accounts_backup_*.csv` spill files so future runtime
      save-outs stay out of Git status by default.
- 2026-03-29 (Issue #48 kickoff planning / TIPSY field ledger): promoted the
  next BTC cutover edge to the umbrella "remaining optional indicator banks"
  task and added a durable planning ledger so optional-bank scope is tracked
  in-repo instead of only in chat.
  - Added `planning/tipsy_indicator_bank_checklist.md`, a grouped checkbox
    inventory covering all 216 fields from `planning/AllFieldsSQL.rpt`.
  - Marked the currently shipped `stand-structure-basic` family coverage as
    landed in that checklist and left the remaining candidate banks unchecked.
  - Updated `ROADMAP.md` so `P48.2d2` now explicitly references the new
    checklist, treats issue `#48` as the governing tracker, and starts from
    the current first product-oriented candidate families (`log-grades`,
    `lumber-2-or-better`, `lumber-graded`, `lumber-degraded`,
    `industrial-logs`, and `residual-fibre`).
  - Follow-up BTC installation cross-reference:
    - scraped `C:\Program Files\TIPSY 4.7\BTC\OutputColumns.txt` and
      `C:\Program Files\TIPSY 4.7\BTC\btpfields.txt` against
      `planning/AllFieldsSQL.rpt`;
    - confirmed `btpfields.txt` behaves like a BTP input-field map rather than
      an output-column inventory;
    - found additional output names in `OutputColumns.txt` that are absent from
      `AllFieldsSQL.rpt`, especially:
      - threshold-specific raw aliases such as `BasalArea000`,
        `MeanDBHg000`, `StemCount000`, `Volume000`, `MAI000`, and `VPT000`;
      - Carbon / CO2e output families; and
      - `CrownCover` / `Crown_Bulk_Density`;
    - recorded those supplemental output-only fields in
      `planning/tipsy_indicator_bank_checklist.md` so they are not forgotten
      during future optional-bank rollout work.
- 2026-03-29 (Issue #48 scope rewrite): widened GitHub issue `#48` from one
  specific grade-oriented bank into the umbrella tracker for "add all missing
  optional BTC/TIPSY indicators, grouped into logical banks".
  - The active plan no longer assumes we need a separate GitHub issue for each
    small bank family.
  - `ROADMAP.md` now mirrors that broader issue framing while still keeping the
    current first implementation candidates product-oriented.
- 2026-03-29 (Issue #48 first shipped product bank): added the `log-grades`
  optional BTC indicator bank to FEMIC and validated it against the live
  unattended `/TSR` overlay seam.
  - `src/femic/pipeline/tipsy.py` now ships a `log-grades` bank containing:
    - `Logs_Grade_D`
    - `Logs_Grade_F`
    - `Logs_Grade_H`
    - `Logs_Grade_I`
    - `Logs_Grade_J`
    - `Logs_Grade_U`
    - `Logs_Grade_X`
    - `Logs_Grade_Y`
    - `Logs_Grade_All`
  - The generic BTC transposed-output parser already preserved arbitrary bank
    aliases once they were added to the bank map, so no separate parser seam
    was required beyond the new bank definition.
  - Added focused test coverage for:
    - bank column expansion;
    - runtime TSR template injection; and
    - transposed-output parsing of `Logs_Grade_*` fields.
- 2026-03-29 (Issue #48 follow-on shipped product banks): added the
  `lumber-2-or-better` and `residual-fibre` optional BTC indicator banks after
  both families probed cleanly through the live unattended `/TSR` overlay seam.
  - `src/femic/pipeline/tipsy.py` now also ships:
    - `lumber-2-or-better`:
      - `Lumber_2_or_Better_2x4`
      - `Lumber_2_or_Better_2x6`
      - `Lumber_2_or_Better_2x8`
      - `Lumber_2_or_Better_2x10`
      - `Lumber_2_or_Better_All`
      - `LRF_2_or_Better_All`
    - `residual-fibre`:
      - `Residual_Chips`
      - `Residual_Sawdust`
      - `Residual_Shavings`
      - `Residual_Trim`
      - `Residual_Bark`
  - Added focused test coverage for:
    - bank column expansion; and
    - runtime TSR template injection for both new bank families.
- 2026-03-29 (Issue #48 BTC runtime-path cleanup): moved supervised BTC/TIPSY
  CLI defaults out of the historical `vdyp_io/logs` namespace and into
  dedicated `tipsy_io` runtime roots.
  - `femic tipsy run-btc` and `femic tipsy probe-btc-columns` now default
    manifests/logs under `tipsy_io/logs`.
  - default BTC scratch now resolves under `tipsy_io/scratch/btc-<run_id>`
    instead of `<log_dir>/btc_scratch-<run_id>`.
  - bootstrap/runtime guardrails now create and ignore `tipsy_io/logs` and
    `tipsy_io/scratch` so BTC supervision is easier to read and stays out of
    tracked repo state.
  - docs now explicitly warn that live unattended `/TSR` overlay smokes are
    sequential-only because they share the same per-user `TimberSupply.rpt`
    seam.
- 2026-03-29 (Issue #48 checklist reset to canonical BTC field map): rewrote
  the optional-bank ledger so it is now driven by installed BTC
  `OutputColumns.txt` rather than the older GUI-built `AllFieldsSQL.rpt`
  approximation.
  - `planning/tipsy_indicator_bank_checklist.md` now groups the full canonical
    BTC output inventory into logical bank buckets, with every real
    `OutputColumns.txt` token represented exactly once.
  - `planning/AllFieldsSQL.rpt` is now treated only as a secondary alias/report
    template reference instead of the source-of-truth inventory.
  - The only currently known `AllFieldsSQL.rpt`-only noncanonical names are:
    - `Volume:Auto:Con`
    - `Volume:Auto:Dec`
    - `Height:Auto:Con`
    - `Height:Auto:Dec`
    - `last`
  - `ROADMAP.md` and issue `#48` were widened accordingly so the active task is
    now “finish the remaining logical banks from the canonical ledger,” not
    only the earlier first-wave product families.
- 2026-03-29 (Issue #48 second-wave product banks): added the `lumber-graded`,
  `lumber-degraded`, and `industrial-logs` optional BTC indicator banks after
  all three full families probed cleanly through the live unattended `/TSR`
  overlay seam.
  - `src/femic/pipeline/tipsy.py` now also ships:
    - `lumber-graded`
    - `lumber-degraded`
    - `industrial-logs`
  - Added focused test coverage for:
    - bank column expansion; and
    - runtime TSR template injection for the new product-bank cluster.
- 2026-03-29 (Issue #48 remaining canonical bank sweep): pushed the current
  unattended `/TSR` probe harness across the remaining unshipped canonical
  `OutputColumns.txt` bank families and confirmed that the failures are real
  seam selectivity, not a broken probe harness.
  - Sanity check:
    - re-probed the previously clean `log-grades` bank with the current
      bank-probe logic and got `accepted=9`, `failed=0`, with the expected
      `Logs_Grade_*` headers present in the returned CSV.
  - Exception cluster:
    - `yield-and-age-core` failed both as a whole-bank batch probe and as
      one-token fallback probes (`Year`, then the reduced post-`Year` set),
      all with the same BTC signature:
      - `exit_code=1`
      - no output CSV
      - no error CSV
      - auto-closed BTC modal dialog
  - Silent-omission cluster:
    - the following families completed BTC `/TSR` runs successfully, but every
      requested token was omitted from the returned transposed CSV:
      - `crop250-stand-quality`
      - `mortality-summary`
      - `genetics-fertilization-and-oaf`
      - `tass-and-site-index-raw`
      - `crown-and-fire`
      - `biomass-live`
      - `biomass-dead`
      - `carbon`
      - `co2e`
      - `mortality-size-classes`
      - `diameter-class-stems`
      - `diameter-class-volume`
      - `diameter-class-vpt`
  - Naming-layer mismatch clue:
    - `stand-structure-threshold-raw` also omitted all canonical raw names
      such as `BasalArea000` and `MeanDBHg000`, while the already landed stand
      structure bank still works with the older report-token forms
      `BasalArea:000`, `DBHg:000`, and `SPH:000`.
    - That family now looks more like a report-token alias problem than a
      broken unattended seam.
- 2026-03-29 (Issue #48 depth-first stock-matrix probe slice): added
  variant-aware BTC probing and ran the first representative stock-syntax
  experiments against the copied-install `/TSR` seam.
  - The probe harness now supports a stock-matrix variant mode that can try:
    - the generic transposed TSR line;
    - exact stock report lines copied from shipped `.rpt` files;
    - stock-transposed adapted lines; and
    - explicit alias-token variants for naming-mismatch cases.
  - The parser/runtime path was tightened to:
    - read shipped BTC `.rpt` files with UTF-8 BOM handling;
    - preserve exact stock column lines verbatim when probing;
    - use short ASCII header overrides on generated transposed variants; and
    - kill probe attempts immediately once a BTC modal exception dialog is
      detected.
  - New in-repo planning ledger:
    - `planning/tipsy_tsr_variant_probe_ledger.md`
  - Live representative results:
    - `Mortality_Height_Mean`, `Mortality_DBHg_Mean`, and
      `Mortality_Basal_Area` all failed across generic transposed, exact stock
      `Mortality.rpt`, and stock-transposed adapted variants with the same
      signature:
      - `exit_code=1`
      - no output CSV
      - no error CSV
      - auto-closed BTC modal dialog
    - `BasalArea000`, `MeanDBHg000`, and `StemCount000` all failed across
      generic canonical, alias-transposed, and exact stock `Yield.rpt`
      variants with that same modal-signature failure.
  - Current inference:
    - width-bearing stock syntax does not rescue the mortality family through
      copied-install `/TSR`; and
    - the known-good threshold report-token spellings (`BasalArea:000`,
      `DBHg:000`, `SPH:000`) appear to depend on the live user-overlay seam
      rather than working generically in copied-install stock-matrix probes.
- 2026-03-29 (Issue #48 live-overlay correction and next bank tranche): moved
  the active probe workflow back onto the real user-overlay
  `TimberSupply.rpt` seam and proved three more optional bank families there.
  - Overlay-only differential probes passed cleanly for:
    - control:
      - `Logs_Grade_D`
    - representative omitted-family tokens:
      - `Mortality_Height_Mean`
      - `Crop250VolUtil125`
      - `CrownCover`
    - sibling follow-up tokens:
      - `Mortality_Stems`
      - `Mortality_DBHg_Mean`
      - `Mortality_Basal_Area`
      - `Mortality_Volume_Total`
      - `Crop250DBHgMean`
      - `Crop250LiveCrown`
      - `Crown_Bulk_Density`
  - Direct header inspection confirmed returned age-series columns for all of
    those fields on the real overlay seam.
  - `src/femic/pipeline/tipsy.py` now ships three additional optional banks:
    - `mortality-summary`
    - `crop250-stand-quality`
    - `crown-and-fire`
  - Whole-bank live overlay smokes also passed for all three new switches:
    - `--indicator-bank mortality-summary`
    - `--indicator-bank crop250-stand-quality`
    - `--indicator-bank crown-and-fire`
  - Planning/docs surfaces updated:
    - `planning/tipsy_indicator_bank_checklist.md`
    - `planning/tipsy_tsr_variant_probe_ledger.md`
    - `docs/reference/api/femic-pipeline-tipsy.rst`
- 2026-03-29 (Issue #48 biomass/carbon overlay tranche): kept extending the
  live user-overlay seam and proved the biomass/carbon/CO2e families plus the
  remaining crown/fire support metrics.
  - Representative overlay-only probes passed with real returned age-series
    headers for:
    - `Biomass_Live_Total`
    - `Biomass_Dead_Total`
    - `Carbon_Live_Total`
    - `Carbon_Dead_Total`
    - `CO2e_Live_Total`
    - `CO2e_Dead_Total`
    - `mean_height_to_crown_base`
    - `mean_crown_length`
  - Based on that signal, whole-bank live overlay smokes also passed for:
    - `biomass-live`
    - `biomass-dead`
    - `carbon`
    - `co2e`
    - expanded `crown-and-fire`
  - `src/femic/pipeline/tipsy.py` now ships those additional optional banks,
    and `crown-and-fire` now includes:
    - `CrownCover`
    - `mean_height_to_crown_base`
    - `mean_crown_length`
    - `Crown_Bulk_Density`
  - Direct header inspection confirmed representative returned columns such as:
    - `Biomass_Live_Wood_*`, `Biomass_Live_Total_*`
    - `Biomass_Dead_Wood_*`, `Biomass_Dead_Total_*`
    - `Carbon_Live_Total_*`, `Carbon_Dead_Total_*`
    - `CO2e_Live_Total_*`, `CO2e_Dead_Total_*`
    - `mean_height_to_crown_base_*`, `mean_crown_length_*`
  - Planning/docs/checklist surfaces updated:
    - `planning/tipsy_indicator_bank_checklist.md`
    - `planning/tipsy_tsr_variant_probe_ledger.md`
    - `docs/reference/api/femic-pipeline-tipsy.rst`
- 2026-03-29 (Issue #48 histogram/class overlay tranche): fixed one real
  false-negative bug in the live probe harness, then shipped the remaining
  histogram/class banks through the real user-overlay seam.
  - Probe harness fix:
    - default one-token probes now force short ASCII header aliases; and
    - returned-header detection no longer assumes alnum-only prefixes, so
      stock BTC headers like `Logs (Grade)_10` are no longer misclassified as
      missing.
  - Representative live overlay probes passed for:
    - `Logs_Grade_D`
    - `Mortality_Stems_Size_Class_5`
    - `Mortality_Volume_Size_Class_5`
    - `Mortality_VPT_Size_Class_5`
    - `Stems_Diameter_Class_0`
    - `Volume_Diameter_Class_0`
    - `VPT_Diameter_Class_0`
  - Whole-bank live overlay smokes then passed for:
    - `mortality-size-classes`
    - `diameter-class-stems`
    - `diameter-class-volume`
    - `diameter-class-vpt`
  - `src/femic/pipeline/tipsy.py` now ships those four additional optional
    banks, and direct header inspection confirmed returned columns such as:
    - `Mortality_Stems_Size_Class_5_*`
    - `Mortality_Volume_Size_Class_5_*`
    - `Mortality_VPT_Size_Class_5_*`
    - `Stems_Diameter_Class_0_*`
    - `Volume_Diameter_Class_0_*`
    - `VPT_Diameter_Class_0_*`
  - Planning/docs/checklist surfaces updated:
    - `planning/tipsy_indicator_bank_checklist.md`
    - `planning/tipsy_tsr_variant_probe_ledger.md`
    - `docs/reference/api/femic-pipeline-tipsy.rst`
    - `ROADMAP.md`
- 2026-03-29 (Issue #48 scalar-status overlay tranche): shipped the last clean
  compact scalar/status banks through the real user-overlay seam.
  - Representative live overlay probes passed with real returned age-series
    headers for:
    - `GWgain`
    - `FertGain`
    - `OAFremoval`
    - `OAFmortality`
    - `OAFimpact`
    - `OAF`
    - `YearTASS_Base`
    - `HeightSindex_Base`
    - `YearTASS_Full`
    - `HeightSindex_Full`
  - Based on that signal, whole-bank live overlay smokes also passed for:
    - `genetics-fertilization-and-oaf`
    - `tass-and-site-index-raw`
  - `src/femic/pipeline/tipsy.py` now ships those two additional optional
    banks, and direct header inspection confirmed returned columns such as:
    - `GWgain_*`
    - `FertGain_*`
    - `OAF_*`
    - `YearTASS_Base_*`
    - `HeightSindex_Base_*`
    - `YearTASS_Full_*`
    - `HeightSindex_Full_*`
  - Planning/docs/checklist surfaces updated:
    - `planning/tipsy_indicator_bank_checklist.md`
    - `planning/tipsy_tsr_variant_probe_ledger.md`
    - `docs/reference/api/femic-pipeline-tipsy.rst`
    - `ROADMAP.md`
- 2026-03-29 (Issue #48 threshold-triplet design rule): recorded and
  partially codified the bank-design rule that when BTC exposes the same
  metric at `{000,125,175}` top-diameter merchantable cutoffs, FEMIC should
  treat that triplet as one atomic mapped-bank unit.
  - `src/femic/pipeline/tipsy.py` now carries an explicit reusable cutoff
    suffix constant/helper and uses that helper for the shipped
    `stand-structure-basic` `StemCount{000,125,175}` triplet.
  - Planning/docs were updated to make the same rule explicit for the
    unresolved `stand-structure-threshold-raw` family so the intended landing
    shape is the full three-threshold set per metric, not a single-threshold
    partial bank unless a live-overlay blockage is proven and documented.
- 2026-03-29 (Issue #48 threshold raw bank): proved and landed the full
  `stand-structure-threshold-raw` bank through the real live user-overlay
  `TimberSupply.rpt` seam.
  - Live overlay probes accepted all twenty-one threshold-triplet tokens on the
    generic transposed line:
    `Volume000/125/175`, `BasalArea000/125/175`, `MeanDBHg000/125/175`,
    `MAI000/125/175`, `VPT000/125/175`, `Juvenille_Volume000/125/175`, and
    `Juvenille_Percent000/125/175`.
  - `src/femic/pipeline/tipsy.py` now ships
    `--indicator-bank stand-structure-threshold-raw`, while
    `tests/test_tipsy.py`, `planning/tipsy_indicator_bank_checklist.md`,
    `planning/tipsy_tsr_variant_probe_ledger.md`, `docs/reference/api/femic-pipeline-tipsy.rst`,
    and `ROADMAP.md` were updated to reflect that the only unresolved canonical
    family left under Issue `#48` is now `yield-and-age-core`.
- 2026-03-29 (Issue #48 yield-and-age bank closeout): live-overlay-only
  isolation recovered a coherent shipped `yield-and-age-core` bank while also
  clarifying the remaining non-bank caveats.
  - The new bank now ships `Year`, `TotalAge`, `BHAge`, `StandAge`,
    `HeightSindex`, `Height`, `Volume`, `VPT`, `HeightTassTop`,
    `HeightTassMean`, and `HeightTassPredom`.
  - `CC` and `VolumeGross` were not added to the bank because they are already
    part of the unattended TSR base preset.
  - `Juvenille_Volume` and `Juvenille_Percent` still trigger live-overlay BTC
    modal failures as non-threshold totals, while their `000/125/175` variants
    remain shipped through `stand-structure-threshold-raw`.
  - This leaves Issue `#48` with no remaining unshipped logical banks, only the
    documented juvenile-total caveat.
- 2026-03-29 (Issue #56 P48.3 BTC cutover closeout): reconciled the remaining
  cutover-wide tracker/docs drift and recorded the installed-tree audit in a
  durable repo note.
  - `ROADMAP.md` now treats `P48.3` as complete under GitHub issue `#56`
    rather than leaving the old closed issue `#46` as the apparent governing
    tracker.
  - Added `planning/tipsy_install_tree_audit_20260329.md` as the auditable
    installed-tree summary for `C:\Program Files\TIPSY 4.7\`.
  - The audit confirms:
    - BTC CLI can start from saved `.btc` projects, `/TSR`, or `/FLP`;
    - BatchTIPSY-to-CBM documentation explicitly advertises the `-RGM`
      regime-file seam;
    - `OutputColumns.txt` is the canonical BTC output ledger for FEMIC bank
      planning;
    - packaged config/default files such as `oafs.txt` and `utiliz.txt` expose
      useful model semantics for future reverse-engineering work.
  - Full local CHM HTML decompile was not available through `hh.exe` in this
    environment, but machine-readable topic inventories were still extracted
    from the compiled help files and saved under
    `tipsy_io/logs/p48_3_install_audit/chm/`.
- 2026-03-29 (Issue #57 tracked CHM archive): archived the installed TIPSY help
  corpus into tracked repo files for future reverse-engineering work.
  - Fully extracted the installed `.chm` files for:
    - `TIPSY45`
    - `Fansier`
    - `SiteTools`
    - `Plotsy2`
  - The working seam was path-sensitive:
    - `hh.exe -decompile` failed from long paths with spaces;
    - the same command succeeded once both input and output lived under a
      short, no-space path such as `C:\chm\...`.
  - The extracted help trees are now tracked under:
    - `reference/tipsy/chm_extracted/TIPSY45/`
    - `reference/tipsy/chm_extracted/Fansier/`
    - `reference/tipsy/chm_extracted/SiteTools/`
    - `reference/tipsy/chm_extracted/Plotsy2/`
  - Added repo-local provenance notes in:
    - `reference/tipsy/README.md`
    - `reference/tipsy/chm_extracted/README.md`
