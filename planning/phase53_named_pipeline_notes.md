# Phase 53 Named Pipeline Notes

- Source: former `ROADMAP.md` lines `16689-17021`.
- Governing lane: named-pipeline, yield-bridge, and strict reproducibility work under `#163`, `#164`, `#167`, `#168`, and `#169`.

## Extracted Roadmap Notes

- 2026-04-18: Opened the post-THLB-reconciliation umbrella for the deeper pipeline/runbook refactor.
  - Governing umbrella issue:
    - `#163` — refactor FEMIC around named pipelines built from recipe sequences.
  - First concrete child issue:
    - `#164` — add an explicit `AFLB -> strata/AU/yield -> THLB` interruption seam inside the THLB workflow.
  - Working interpretation:
    - the recently validated TSA29 strict THLB lane exposed that THLB is not logically one uninterrupted recipe chain;
    - it must pause after AFLB to derive strata, define AUs, satisfy VDYP/TIPSY/FANSIER yield dependencies, and then resume late-stage THLB.
  - Current bounded next step for this new arc:
    - audit the current runtime path against the desired seam and document exactly where FEMIC already has reusable artifacts (`aflb_checkpoint`, strata/AU helpers, VDYP cache checks, BTC/TIPSY runners, yield-curve compile logic) versus where the interruption/resume contract is still implicit.
- 2026-04-18: Completed the first `#164` seam audit and turned it into a concrete artifact/command contract.
  - Audit result:
    - the repo already has most of the functional pieces:
      - restart-grade THLB checkpoints (`aflb_checkpoint`, `lhlb_checkpoint`, `lhlb_curve_ready_checkpoint`);
      - stratification and AU helpers in `src/femic/pipeline/tsa.py`;
      - top-area coverage config in `selection.stratification.top_area_coverage`;
      - VDYP prep/result caches; and
      - BTC/TIPSY resume surfaces via `femic tsa post-tipsy` and `femic tsa btc-post-tipsy`.
  - The missing contract is the explicit bridge between:
    - `AFLB`
    - strata/AU/yield compilation
    - and downstream THLB continuation.
  - Proposed new canonical artifacts for `#164`:
    - `data/tsr/aflb_strata_checkpoint.feather`
    - `data/tsr/aflb_au_checkpoint.feather`
    - `data/tsr/aflb_yield_bridge_manifest.json`
    - `data/tsr/aflb_yield_ready_checkpoint.feather`
  - Proposed first command surface:
    - `femic tsr build-yield-bridge --instance-root ... --run-config ... --tsa ...`
  - Working spec note is now captured in:
    - `planning/aflb_yield_bridge_seam.md`
  - Next bounded implementation step:
    - formalize the manifest schema and publish the first two restart seams (`aflb_strata_checkpoint` and `aflb_au_checkpoint`) before wiring the full VDYP/TIPSY resume bridge.
- 2026-04-18: Active `#164` implementation scope is the first artifact-only slice, not the full yield bridge.
  - This bounded slice will publish only:
    - `data/tsr/aflb_strata_checkpoint.feather`
    - `data/tsr/aflb_au_checkpoint.feather`
    - `data/tsr/aflb_yield_bridge_manifest.json`
  - It will not yet:
    - run VDYP/TIPSY/FANSIER;
    - publish `aflb_yield_ready_checkpoint.feather`; or
    - generalize into the broader named-pipeline registry under `#163`.
  - Current execution precondition:
    - local `external/femic-tsa29-instance/data/tsr/aflb_checkpoint.feather` may be absent after the generated-artifact hygiene cleanup, so the first command surface must either regenerate that upstream checkpoint explicitly or fail with a clear remediation message instead of assuming the file is still present.
- 2026-04-18: The next bounded `#164` slice is `P53.2c.1`, still inside the existing `build-yield-bridge` command.
  - Implementation target:
    - add conservative cache-sufficiency inspection for the current AFLB-derived strata/AU selection without widening into VDYP/TIPSY/FANSIER execution.
  - Required outputs for this slice:
    - extend `data/tsr/aflb_yield_bridge_manifest.json` with stable provenance for the current AFLB/run-config/selection state; and
    - add a three-state cache verdict (`sufficient`, `insufficient`, `blocked_missing_inputs`) plus evidence/reason details.
  - Required inspection surfaces:
    - prior `aflb_yield_bridge_manifest.json` when present;
    - `data/vdyp_results-tsaXX.pkl`;
    - `data/vdyp_curves_smooth-tsaXX.feather`;
    - `data/model_input_bundle/{au_table,curve_table,curve_points_table}.csv`; and
    - optional supporting evidence from post-TIPSY/BTC manifests and `03_input` / `04_output` / `04_error` handoff files.
  - Scope boundary:
    - keep missing `curve_table.csv` / `curve_points_table.csv` in `blocked_missing_inputs`;
    - treat absent post-TIPSY/BTC evidence as `insufficient`, not blocked; and
    - do not publish `aflb_yield_ready_checkpoint.feather` yet.
- 2026-04-18: Opened parked bug `#166` for branch-level full-suite pytest failures discovered during the `P53.2c.1` milestone sweep.
  - Current policy:
    - keep those failures out of the active yield-bridge delivery lane unless a future slice explicitly targets them.
  - Current failing surfaces recorded in `#166`:
    - the branch-level failures currently sit in `tests/test_tsr_recipes.py` and `tests/test_tsr_step13_attributes.py`.
- 2026-04-18: The next bounded `#164` slice after cache inspection is `P53.2d.1`, still on `femic tsr build-yield-bridge`.
  - Implementation target:
    - promote a cache-sufficient AFLB AU checkpoint into `data/tsr/aflb_yield_ready_checkpoint.feather` using existing local bundle/cache artifacts only.
  - Required outputs for this slice:
    - `data/tsr/aflb_yield_ready_checkpoint.feather`;
    - manifest `yield_ready` status/path metadata; and
    - CLI/result reporting for `yield_ready_status`.
  - Shared implementation seam:
    - factor a small reusable AU-table-to-curve assignment helper so the AFLB yield-ready promotion and late-stage step13 curve-ready enrichment use the same bundle mapping semantics.
  - Scope boundary:
    - do not launch BTC/TIPSY/FANSIER;
    - do not resume downstream THLB execution yet; and
    - if cache sufficiency is not `sufficient`, stop after writing the manifest and bounded strata/AU artifacts with a clear remediation message.
- 2026-04-18: The next bounded `#164` slice after `P53.2d.1` is `P53.2d.2`, focused on downstream THLB acceptance of the yield-ready restart seam.
  - Implementation target:
    - accept `data/tsr/aflb_yield_ready_checkpoint.feather` as an explicit `--checkpoint-path` surface for downstream reconstructed THLB runs without changing default checkpoint discovery order.
  - Required behavior:
    - recognize a distinct restart mode such as `aflb_yield_ready_checkpoint_restart`;
    - skip only `GLB -> AFLB` steps, not `AFLB -> LHLB`;
    - validate that the checkpoint carries downstream-ready fields (`stratum`, `stratum_matched`, `si_level`, `au`, `curve1`, `curve2`); and
    - surface the new restart signal in THLB run metadata/audit output.
  - Scope boundary:
    - explicit checkpoint only;
    - no auto-discovery preference changes;
    - no auto-build of the yield bridge from THLB commands; and
    - no new command surface.
- 2026-04-18: Completed `P53.2d.2` under `#164` by teaching downstream THLB runners to accept the new yield-ready restart seam explicitly.
  - Implemented behavior:
    - reconstructed THLB runs now recognize `data/tsr/aflb_yield_ready_checkpoint.feather` as `aflb_yield_ready_checkpoint_restart`;
    - explicit yield-ready restarts skip only `GLB -> AFLB` while still executing `AFLB -> LHLB` and `LHLB -> THLB`; and
    - both `thlb-netdown-run` and `thlb-netdown-step-run` accept the explicit checkpoint path without adding new flags.
  - Guardrails:
    - explicit yield-ready checkpoints now fail fast unless they contain `stratum`, `stratum_matched`, `si_level`, `au`, `curve1`, and `curve2`;
    - default checkpoint auto-discovery order remains unchanged; and
    - THLB commands still do not auto-build the AFLB yield bridge.
  - Validation:
    - targeted recipe tests cover restart-mode recognition, invalid yield-ready rejection, and parent-step acceptance;
    - targeted CLI tests cover explicit checkpoint forwarding and restart-signal summary output; and
    - lint/type checks passed on the touched surface.
- 2026-04-18: The next bounded `#164` slice after THLB restart acceptance is `P53.2d.3`, still on `femic tsr build-yield-bridge`.
  - Implementation target:
    - execute the real AFLB yield bridge from existing VDYP cache when cache sufficiency is `insufficient`, rather than stopping after inspection.
  - Required behavior:
    - keep the existing fast path for `cache_sufficiency == sufficient`;
    - treat `blocked_missing_inputs` as a hard stop;
    - on `insufficient`, compile fresh bridge-owned `tipsy_params_tsaXX.xlsx`, `02_input-tsaXX.dat`, and `03_input-tsaXX.csv`;
    - then run either `btc-post-tipsy` or `post-tipsy` helper workflows based on managed-curve mode; and
    - republish `aflb_yield_ready_checkpoint.feather` from the rebuilt bundle outputs.
  - Provenance/reporting requirements:
    - extend the manifest with execution-path metadata (`local_cache`, `post_tipsy_resume`, or `btc_post_tipsy`);
    - record 02/03/04 handoff paths plus post-TIPSY/BTC manifest evidence; and
    - surface the execution path in CLI summary output.
  - Scope boundary:
    - reuse the existing VDYP cache only;
    - do not add a new VDYP rerun lane yet;
    - defer FANSIER; and
    - keep the command surface unchanged.
- 2026-04-18: Completed `P53.2d.3` under `#164` by turning the yield bridge into a real execution path when reusable VDYP cache exists.
  - Implemented behavior:
    - `femic tsr build-yield-bridge` still fast-paths `sufficient` cache cases to local promotion;
    - `blocked_missing_inputs` remains a hard stop; and
    - rebuildable `insufficient` cases now compile fresh `tipsy_params_tsaXX.xlsx`, `02_input-tsaXX.dat`, and `03_input-tsaXX.csv`, then run `btc-post-tipsy` or `post-tipsy` based on managed-curve mode before republishing `aflb_yield_ready_checkpoint.feather`.
  - Provenance/reporting:
    - the manifest now records execution-path metadata, bridge handoff artifact paths, post-TIPSY/BTC manifest evidence, and execution failure reasons;
    - the CLI summary now prints `yield_bridge_execution_path`; and
    - CLI failure messaging now prefers the bridge execution failure reason when yield-ready publication does not complete.
  - Scope boundary preserved:
    - no new CLI command;
    - no VDYP rerun lane;
    - FANSIER still deferred; and
    - downstream THLB restart acceptance remains unchanged from `P53.2d.2`.
- 2026-04-18: The next bounded `#164` slice after the execution bridge is `P53.2d.4`, focused on real TSA29 proof and issue closeout.
  - Implementation target:
    - run the bridge on the real TSA29 instance, inspect the concrete artifacts, smoke the downstream THLB restart seam from `aflb_yield_ready_checkpoint.feather`, and close the issue if the evidence is good.
  - Required execution steps:
    - regenerate `data/tsr/aflb_checkpoint.feather` first if the local TSA29 hygiene cleanup removed it;
    - run `femic tsr build-yield-bridge --instance-root external/femic-tsa29-instance --run-config config/run_profile.tsa29.yaml --tsa 29`;
    - inspect the rebuilt manifest, yield-ready checkpoint, bundle tables, and runtime manifests; and
    - run one downstream THLB smoke from `--checkpoint-path data/tsr/aflb_yield_ready_checkpoint.feather`.
  - Closeout requirements:
    - mark the `P53.2*` issue-164 work complete in roadmap notes/checklists as appropriate;
    - append the final validation summary to `CHANGE_LOG.md`; and
    - post an explicit GitHub closeout note on `#164` before closing it.
- 2026-04-18: `P53.2d.4` real TSA29 validation proved the bridge itself, but blocked issue closeout on one remaining downstream restart seam.
  - Real TSA29 bridge proof succeeded:
    - republished `data/tsr/aflb_checkpoint.feather` and `data/tsr/lhlb_checkpoint.feather` from the reconstructed THLB lane;
    - `femic tsr build-yield-bridge --instance-root external/femic-tsa29-instance --run-config config/run_profile.tsa29.yaml --tsa 29` completed successfully;
    - the bridge manifest recorded `slice_status = yield_ready_from_bridge_execution`;
    - the execution path was `btc_post_tipsy`; and
    - `data/tsr/aflb_yield_ready_checkpoint.feather` was published with `371627` rows.
  - Remaining blocker before `#164` can close:
    - downstream THLB smoke from `--checkpoint-path data/tsr/aflb_yield_ready_checkpoint.feather` failed during step-13 curve-ready enrichment;
    - current failure surface is `KeyError` from `assign_stratum_matches_from_au_table(...)` / `build_stratum_lexmatch_alias_map(...)`; and
    - the missing-index strata named in the real run included `MS_PLI`, `IDF_FD`, `MS_PL`, `ESSF_BL`, `ESSF_PL`, `ESSF_SE`, and `ESSF_PLI`.
  - Immediate next bounded slice:
    - repair the real-instance compatibility seam between the new AFLB yield-ready checkpoint and the downstream step-13/LHLB curve-ready enrichment path, then rerun the same explicit-yield-ready THLB smoke before attempting issue closeout again.
- 2026-04-18: The next bounded `#164` slice after the real TSA29 proof blocker is `P53.2d.5`, focused on step-13 compatibility and closeout retry.
  - Implementation target:
    - teach late-stage curve-ready compilation to reuse precomputed yield-ready fields when the restart checkpoint already carries valid `stratum_matched`, `si_level`, `au`, `curve1`, and `curve2` assignments.
  - Scope boundary:
    - keep normal `lhlb_checkpoint.feather` step-13 compilation behavior unchanged;
    - do not reopen the yield-bridge execution path; and
    - rerun only the same explicit-yield-ready THLB smoke needed to answer the closeout question.
- 2026-04-18: Completed `P53.2d.5` and closed the last real TSA29 blocker for `#164`.
  - Step-13 compatibility fix:
    - late-stage curve-ready compilation now reuses precomputed `stratum_matched`, `si_level`, and `au` assignments when a yield-ready restart checkpoint already carries them;
    - the normal `lhlb_checkpoint.feather` step-13 derivation path remains unchanged; and
    - a focused regression test now guards against step 13 recomputing those yield-ready fields.
  - Real closeout validation passed:
    - the same explicit restart smoke now succeeds:
      - `femic tsr thlb-netdown-run --instance-root external/femic-tsa29-instance --execution-mode reconstructed --checkpoint-path data/tsr/aflb_yield_ready_checkpoint.feather --map-id 093B023 --no-aflb-gpkg --no-lhlb-gpkg --no-lhlb-curve-ready-gpkg`;
    - the run reported `baseline_signal = aflb_yield_ready_checkpoint_restart`;
    - it wrote `data/tsr/lhlb_curve_ready_checkpoint.feather`; and
    - the previous step-13 `KeyError` did not recur.
  - Validation status for issue closeout:
    - targeted `#164` tests passed;
    - `ruff check src tests` and `mypy src` passed;
    - full `pytest` still fails only on the already-parked unrelated set tracked under `#166`; and
    - `#164` is now closeout-ready because the explicit AFLB -> strata/AU/yield -> THLB seam itself is complete and the remaining branch-level failures are outside this issue's scope.
- 2026-04-18: With `#164` closed, the next rollout-management move under umbrella `#163` is to open exactly one new child issue for the registry/runbook contract layer.
  - Intended child scope:
    - define named pipeline identity and naming rules;
    - define registry discovery/layering and lookup precedence;
    - define the runbook contract for selecting a pipeline and restart seam; and
    - keep full named-pipeline runner implementation explicitly out of scope.
  - Rollout constraint:
    - do not open multiple new feature children under `#163` until the contract-first child has narrowed the next implementation seam.
- 2026-04-18: Opened `#167` as the next active child under umbrella `#163`.
  - Child issue:
    - `#167` — define named pipeline registry and runbook contracts.
  - Why this child now:
    - `#164` already proved the interruption/resume seam pattern;
    - the next unresolved architecture boundary is the contract for named pipeline identity, registry layering, and runbook seam selection; and
    - the full named-pipeline runner should remain out of scope until `#167` is decision-complete.
- 2026-04-18: Started `#167` by landing the first contract spec note for named pipeline registries and machine-readable runbooks.
  - Spec note:
    - `planning/named_pipeline_registry_runbook_contract.md`
  - Current contract decisions captured there:
    - default registry tiers and file locations (built-in, user, instance-local, explicit extras);
    - merge order and override policy by `pipeline_id`;
    - the first YAML contract shape for pipeline registries;
    - the first YAML contract shape for machine-readable pipeline runbooks;
    - restart object policy for scratch vs checkpoint-backed seams; and
    - compatibility mapping from current TSR/THLB recipe surfaces into future named-pipeline ids and seam ids.
  - Immediate next bounded step for `#167`:
    - pressure-test the proposed contract against the current TSR THLB proof lane and identify the narrowest implementation child needed to load registries and resolve one runbook without broad workflow migration.
- 2026-04-18: Pressure-tested the `#167` contract against the live TSA29 reviewed THLB proof lane.
  - Pressure-test result:
    - the current TSA29 lane already provides stable run-profile, recipe, overlay, and checkpoint surfaces that fit the proposed registry/runbook model without inventing a parallel config tree.
  - Additional spec decisions now captured:
    - the first runner child should target one proof pipeline id only: `tsr.thlb_reviewed`;
    - the first runner child only needs seams `scratch`, `aflb`, `aflb_yield_ready`, and `lhlb_curve_ready`;
    - the first runner should be orchestration-only and delegate to the existing TSR helpers/commands; and
    - Patchworks/ws3 and broader multi-family execution remain out of scope for that first runner child.
  - Immediate next bounded step for `#167`:
    - open or draft the runner-implementation child using the now-pressure-tested minimum scope instead of a broad generic pipeline-execution ticket.
- 2026-04-18: The next rollout-management move after the `#167` pressure test is to open one narrow runner child, not to start broad pipeline execution work.
  - Intended child scope:
    - registry loading and merge resolution;
    - runbook loading and validation;
    - one proof command for `tsr.thlb_reviewed`; and
    - seam-aware delegation into the existing TSR reviewed THLB lane.
  - Explicit non-goals for that child:
    - no registry mutation commands;
    - no multi-family pipeline runner;
    - no replacement of existing `femic tsr ...` commands; and
    - no Patchworks/ws3 pipeline execution.
- 2026-04-18: Opened `#168` as the first named-pipeline runner implementation child under umbrella `#163`.
  - Child issue:
    - `#168` — implement the first named-pipeline proof runner from runbooks.
  - Implementer-facing scope:
    - load registry tiers plus explicit runbook registry paths;
    - load one machine-readable runbook;
    - resolve the proof pipeline id `tsr.thlb_reviewed`;
    - support seams `scratch`, `aflb`, `aflb_yield_ready`, and `lhlb_curve_ready`; and
    - delegate into the existing reviewed TSR THLB lane instead of inventing a new execution engine.
  - Rollout relationship:
    - `#167` remains the contract-definition child; and
    - `#168` is the first narrow execution child that should consume that contract without widening into multi-family pipeline work.
- 2026-04-18: Implemented the first proof-oriented named-pipeline runner surface for `#168`.
  - Delivered code surfaces:
    - new module `src/femic/named_pipelines.py` for built-in registry loading, registry layering, runbook loading, runbook-to-plan resolution, and proof-runner dispatch;
    - packaged built-in registry resource under `src/femic/resources/pipelines/registry.yaml`; and
    - new CLI surface `femic pipelines run --runbook ... [--instance-root ...]`.
  - Current bounded proof scope:
    - only `pipeline_id = tsr.thlb_reviewed`;
    - only seams `scratch`, `aflb`, `aflb_yield_ready`, and `lhlb_curve_ready`; and
    - execution is orchestration-only, delegating into the existing reviewed TSR THLB lane via reconstructed mode.
  - Validation state for this slice:
    - focused named-pipeline and CLI tests passed;
    - full `pytest` returned only the same eight unrelated parked failures tracked under `#166`; and
    - no new runner-specific failures remained after restoring the existing THLB CLI outcome-count summary.
  - Next bounded step for `#168`:
    - pressure-test the new `femic pipelines run` surface with a checked-in proof runbook or real TSA29 smoke path without widening into registry-mutation commands or multi-family execution.
- 2026-04-19: The next bounded `#168` slice will use the checked-in proof-runbook option rather than mutating the TSA29 submodule.
  - Implementation target:
    - add one repo-tracked machine-readable proof runbook for `tsr.thlb_reviewed` that is intended to run with an explicit `--instance-root`.
  - Scope boundary:
    - do not modify `external/femic-tsa29-instance` just to host the runbook;
    - do not broaden into registry-mutation commands or automatic default-runbook discovery; and
    - keep validation focused on runbook loading, plan resolution, CLI wiring, and proof-command delegation.
- 2026-04-19: Added the first checked-in proof runbook for `#168` and taught the CLI to accept repo-tracked runbook paths cleanly.
  - Delivered surfaces:
    - repo-tracked machine-readable runbook `runbooks/pipelines/tsa29.tsr.thlb_reviewed.aflb_yield_ready.yaml`;
    - `femic pipelines run` now prefers an existing cwd/repo-relative runbook path before falling back to the instance root; and
    - focused coverage now validates both the checked-in runbook contract and the CLI wiring for that path.
  - Validation state for this slice:
    - focused named-pipeline / CLI tests passed;
    - `ruff check src tests`, `mypy src`, `sphinx-build -b html docs _build/html -W`, and `pre-commit run --all-files` passed; and
    - full `pytest` still returned only the same eight unrelated failures parked under `#166`.
  - Next bounded step for `#168`:
    - use the checked-in proof runbook for one real TSA29 runner smoke (`femic pipelines run --runbook ... --instance-root external/femic-tsa29-instance`) without widening into broader pipeline-engine work.
- 2026-04-19: Pivot the active `#168` proof target from the reviewed scaffold lane to the strict product lane.
  - Product decision:
    - the strict reconstructed THLB lane is the real named-pipeline target;
    - the reviewed lane should be treated as legacy scaffolding or explanatory context, not the primary product proof.
  - Immediate implementation target:
    - add `pipeline_id = tsr.thlb_strict`;
    - add a checked-in TSA29 strict proof runbook; and
    - retarget the next real smoke to that strict runbook with the same bounded restart seam set.
  - Scope boundary:
    - do not widen into a generic multi-family pipeline engine;
    - do not add registry-mutation commands; and
    - keep the strict pipeline implementation on the existing reconstructed TSR THLB runner surface rather than inventing a new execution engine.
- 2026-04-19: The strict TSA29 named-pipeline smoke completed successfully from the checked-in strict runbook.
  - Smoke command:
    - `femic pipelines run --runbook runbooks/pipelines/tsa29.tsr.thlb_strict.aflb_yield_ready.yaml --instance-root external/femic-tsa29-instance`
  - Observed strict-lane runtime evidence:
    - LU-wise reconstructed runtime artifacts advanced through parent-step directories such as step `006`, `008`, `011`, `013`, `016`, `018`, `019`, `021`, and `023`;
    - later strict restart artifacts were written for `curve_threshold_checkpoint`, `lhlb_checkpoint`, `thlb_step13_compile_attributes`, `lhlb_curve_ready_checkpoint`, and the final `thlb_reconstructed_status_report`; and
    - the wrapper process exited cleanly after writing the final summary.
  - End-of-run strict summary:
    - pipeline id `tsr.thlb_strict`;
    - baseline signal `aflb_yield_ready_checkpoint_restart`;
    - full input (not MAP_ID subset);
    - `step_count = 37`;
    - `outcome_applied = 21`;
    - `outcome_applied_noop = 9`;
    - `outcome_unsupported = 7`; and
    - `final_managed_area_ha = 559,967.504`.
  - Closeout interpretation for `#168`:
    - the first named-pipeline proof runner is now demonstrated on the strict product lane rather than only on the reviewed scaffold lane.
- 2026-04-19: Opened `#169` as the next active child under umbrella `#163`.
  - Tracker split:
    - `#168` stays closed as the first proof-runner/orchestration child; and
    - `#169` is now the active strict reproducibility validation child.
  - Governing strict validation contract:
    - authoritative reference is the latest TSA29 locked-chain strict result, not the older frozen workbench snapshot and not the mutable live recipe;
    - first proof target is chained-restart stepwise plus final reproduction through step `23`; and
    - mutable live recipe drift must fail fast instead of silently becoming the validation surface.
  - Immediate next bounded step for `#169`:
    - define the TSA29-specific strict-validation contract surface and validation path before attempting broader multi-instance machinery.
- 2026-04-19: The next bounded `#169` implementation slice is strict contract binding plus fail-fast runner enforcement.
  - Governing mismatch:
    - the checked-in TSA29 strict runbook currently resolves the mutable live THLB recipe path via the built-in registry; and
    - that live execution surface is not the same thing as the latest locked-chain strict reference.
  - Bounded implementation target:
    - add a runbook-level validation contract block that points at the locked-chain ledger/comparison artifacts and the required recipe path; and
    - teach the named-pipeline runner to error before execution when that contract is active but the resolved strict recipe path still points at the mutable live recipe.
  - Scope boundary:
    - this slice does not yet prove chained-restart reproduction against the locked-chain result;
    - it only prevents another false-positive strict smoke from the wrong execution surface.
- 2026-04-19: The next bounded `#169` implementation slice is strict recipe rebinding through the validation contract.
  - Governing need:
    - the fail-fast guard now correctly rejects the mutable live recipe surface; and
    - the checked-in TSA29 strict runbook still needs a bounded way to resolve the required locked recipe path without depending on mutable instance registry state.
  - Bounded implementation target:
    - let `validation_contract.required_recipe_path` explicitly bind the THLB recipe path for strict validation runbooks; and
    - keep the rest of named-pipeline resolution unchanged.
  - Scope boundary:
    - this slice still does not run or prove the chained-restart locked-chain comparison;
    - it only makes the checked-in strict validation runbook executable against the correct recipe surface.
- 2026-04-19: Completed the bounded `#169` strict recipe rebinding slice.
  - Delivered behavior:
    - `build_named_pipeline_execution_plan(...)` now lets
      `validation_contract.required_recipe_path` bind the THLB recipe path for
      strict validation runbooks;
    - the checked-in TSA29 strict runbook now resolves to
      `workbench/tsr/thlb_netdown.locked.recipe.yaml` without depending on
      mutable instance-local registry overrides; and
    - missing required validation recipe files still fail before execution.
  - Focused validation:
    - `.\.venv\Scripts\python.exe -m pytest tests/test_named_pipelines.py -q`
    - `.\.venv\Scripts\python.exe -m pytest tests/test_cli_main.py -k "pipelines_run" -q`
    - `.\.venv\Scripts\python.exe -m ruff check src/femic/named_pipelines.py src/femic/cli/main.py tests/test_named_pipelines.py tests/test_cli_main.py`
    - `.\.venv\Scripts\python.exe -m mypy src`
  - Next bounded step:
    - use this locked recipe binding as the execution surface for the first
      chained-restart stepwise comparison against the TSA29 locked-chain ledger.
- 2026-04-19: The next bounded `#169` implementation slice is post-run strict contract scoring against the locked-chain ledger.
  - Governing need:
    - the strict runbook can now resolve the correct locked recipe surface; and
    - the runner still needs to distinguish "executed successfully" from
      "reproduced the validated strict result surface correctly."
  - Bounded implementation target:
    - after `run_tsr_thlb_netdown_recipe(...)` returns for the
      `tsa29_locked_chain_strict` contract, load the run audit JSON plus the
      locked-chain ledger;
    - compare per-parent-step marginal and cumulative values against the locked
      ledger up to the latest locked row; and
    - fail fast on the first contract mismatch instead of treating the run as a
      successful strict validation.
  - Scope boundary:
    - this slice does not yet rerun the real TSA29 instance; and
    - it does not add generic multi-instance validation machinery beyond the
      current TSA29 strict contract kind.
- 2026-04-19: Completed the bounded `#169` post-run strict contract scoring slice.
  - Delivered behavior:
    - `run_named_pipeline_runbook(...)` now validates
      `tsa29_locked_chain_strict` runs against the locked-chain ledger
      immediately after execution;
    - the validator loads the locked ledger plus the THLB audit JSON, compares
      per-parent-step marginal and cumulative values up to the latest locked
      row, and raises a contract mismatch on the first divergence; and
    - successful strict validations now report a compact validation summary so
      "run completed" and "locked contract reproduced" are distinct surfaces.
  - Focused validation:
    - `.\.venv\Scripts\python.exe -m pytest tests/test_named_pipelines.py -q`
    - `.\.venv\Scripts\python.exe -m pytest tests/test_cli_main.py -k "pipelines_run" -q`
    - `.\.venv\Scripts\python.exe -m ruff check src/femic/named_pipelines.py src/femic/cli/main.py tests/test_named_pipelines.py tests/test_cli_main.py`
    - `.\.venv\Scripts\python.exe -m mypy src`
  - Next bounded step:
    - rerun the checked-in TSA29 strict named pipeline against the locked
      recipe surface and let this new validator tell us whether the run matches
      the locked-chain contract or fails on a specific parent-step mismatch.
- 2026-04-19: The next bounded `#169` cleanup slice is to purge TSA29 legacy checkpoint fallback surfaces before any more strict validation.
  - Governing problem:
    - active TSA29 code/docs still contain legacy `ria_vri_vclr1p_checkpoint*.feather`
      fallback paths and historical checkpoint1-era guidance that are now
      incompatible with the validated strict lane contract.
  - Bounded implementation target:
    - hard-block active TSA29 strict/workbench code paths from auto-discovering
      or accepting legacy `ria_vri_vclr1p_checkpoint*.feather` inputs;
    - switch active step-13 default input away from checkpoint7 fallback;
    - scrub active docs/notes that still advertise checkpoint1-era TSA29 strict
      starts as current guidance; and
    - delete the stale TSA29 `data/ria_vri_vclr1p_checkpoint*.feather` files so
      they cannot be reused accidentally.
  - Scope boundary:
    - this slice is cleanup/guardrail work only;
    - it does not attempt another strict validation run.
- 2026-04-19: Completed the bounded `#169` TSA29 legacy checkpoint purge slice.
  - Delivered guardrails:
    - active TSA29 THLB/workbench code paths now reject legacy
      `ria_vri_vclr1p_checkpoint*.feather` fallback discovery and explicit use;
    - step-13 attribute compilation now defaults to
      `data/tsr/lhlb_checkpoint.feather` instead of legacy checkpoint7; and
    - the stale TSA29 `data/ria_vri_vclr1p_checkpoint1..8.feather` files plus
      the old step9 checkpoint1-era TSA29 recipe variants were deleted.
  - Docs/note cleanup:
    - active TSA29-facing CLI/guides now say current strict validation must use
      explicit validated `data/tsr/*.feather` seam checkpoints; and
    - historical checkpoint1-era Phase 52 / comparison notes are now labeled as
      audit-history context only rather than current execution guidance.
  - Focused validation:
    - `.\.venv\Scripts\python.exe -m pytest tests/test_tsr_recipes.py -k "find_tsr_checkpoint_path_rejects_tsa29_legacy_fallback or find_curve_ready_thlb_checkpoint_path_rejects_tsa29_legacy_fallback or default_workbench_checkpoint_path_prefers_step13_attribute_checkpoint" -q`
    - `.\.venv\Scripts\python.exe -m pytest tests/test_tsr_step13_attributes.py -q`
    - `.\.venv\Scripts\python.exe -m ruff check src/femic/tsr_catalog/recipes.py src/femic/tsr_catalog/step13_attributes.py src/femic/cli/main.py tests/test_tsr_recipes.py tests/test_tsr_step13_attributes.py`
    - `.\.venv\Scripts\python.exe -m mypy src`
    - `.\.venv\Scripts\python.exe -m sphinx -b html docs _build/html -W`
  - Next bounded step:
    - return to `P53.1d4` only after using the validated strict-lane recipe and
      explicit `data/tsr/*.feather` seam checkpoints as the sole TSA29 basis.
- 2026-04-18: Opened `#165` to fix the TSA29 submodule generated-artifact hygiene seam that made VS Code SCM and parent `git status` disagree.
  - Root cause:
    - the parent repo had a local config override `submodule.external/femic-tsa29-instance.ignore=untracked`, so parent `git status` could look clean while the submodule itself still had hundreds of untracked generated artifacts.
  - High-volume offender roots observed inside `external/femic-tsa29-instance`:
    - `runtime/logs/glb_build/`
    - `runtime/logs/tsr/raw_glb_clip_*/`
    - `runtime/logs/tsr/lu_partition_profiles/`
    - `data/tsr/*.gpkg`
    - `data/tsr/post_step*_restart/`
    - `workbench/arcgis_review/`
  - Required fix:
    - teach the submodule to ignore its own generated artifacts correctly;
    - clean the existing untracked set; and
    - remove the parent masking config so CLI and VS Code report the same state.
- 2026-04-19: The next bounded `#169` observability slice is to add always-on
  real-time user-visible runtime events for `femic pipelines run`.
  - Governing problem:
    - long TSA29 proof runs currently print a preflight/summary surface and then
      go silent while the underlying THLB execution works, making it too easy to
      lose trust in bounded runtime behavior.
  - Bounded implementation target:
    - add a structured runtime-event model spanning pipeline start/preflight,
      parent-step start/progress/finish, compiled-step start/finish, validation,
      and final success/failure;
    - thread an event sink from `femic pipelines run` through
      `run_named_pipeline_runbook(...)` into `run_tsr_thlb_netdown_recipe(...)`
      and the inner reconstructed executor;
    - mirror the same line-based event stream under `runtime/logs/tsr/`; and
    - adapt existing LU-parallel progress snapshots into parent-step progress
      events instead of leaving them notebook-only.
  - Scope boundary:
    - observability only; no scientific logic or strict-lane semantics change in
      this slice.
- 2026-04-19: Completed `P53.1d6` by adding always-on live runtime events to
  `femic pipelines run`.
  - What shipped:
    - `run_named_pipeline_runbook(...)` now emits line-based pipeline
      start/preflight/validation/finish/failure events and mirrors them to a
      dedicated runtime event log under `runtime/logs/tsr/`;
    - `run_tsr_thlb_netdown_recipe(...)` now accepts a runtime event sink and
      emits parent-step start/finish plus compiled-step start/finish events from
      both reconstructed and hybrid THLB execution paths; and
    - LU-parallel reconstructed exclusion work now reuses existing per-bundle
      progress JSON snapshots to surface `parent_step_progress` events instead
      of leaving that state notebook-only.
  - Focused validation:
    - `.\.venv\Scripts\python.exe -m pytest tests/test_named_pipelines.py -q`
    - `.\.venv\Scripts\python.exe -m pytest tests/test_cli_main.py -k "pipelines_run" -q`
    - `.\.venv\Scripts\python.exe -m pytest tests/test_tsr_recipes.py -k "runtime_events or parent_progress" -q`
    - `.\.venv\Scripts\python.exe -m ruff check src/femic/named_pipelines.py src/femic/cli/main.py src/femic/tsr_catalog/recipes.py tests/test_named_pipelines.py tests/test_cli_main.py tests/test_tsr_recipes.py`
    - `.\.venv\Scripts\python.exe -m mypy src`
- 2026-04-19: The next bounded `#169` slice is a strict preflight seam-benchmark gate.
  - Governing problem:
    - the current TSA29 strict named-pipeline path is fail-fast on recipe/contract
      wiring and post-run locked-chain divergence, but it still spends time
      executing when the selected start seam already misses the validated strict
      benchmark it is supposed to reproduce.
  - Bounded implementation target:
    - add a preflight validator in `run_named_pipeline_runbook(...)` for the
      `tsa29_locked_chain_strict` contract;
    - map `aflb` and `aflb_yield_ready` to locked row 5 and compare the explicit
      `data/tsr/*.feather` seam checkpoint area against that locked cumulative
      reference before execution;
    - treat `scratch` as a targeted unsupported preflight seam in this slice
      unless a trustworthy validated raw-start comparison surface is explicitly
      defined; and
    - emit explicit runtime preflight events and fail before
      `run_tsr_thlb_netdown_recipe(...)` when the seam surface is already off the
      validated strict reproduction path.
  - Scope boundary:
    - no new rerun campaign;
    - no generic multi-instance seam-preflight framework; and
    - no new runbook schema expansion.
- 2026-04-19: Completed `P53.1d7` by making TSA29 strict validation reproducibility-first.
  - What shipped:
    - `run_named_pipeline_runbook(...)` now runs a seam-aware strict preflight before
      `run_tsr_thlb_netdown_recipe(...)` whenever the validation contract is
      `tsa29_locked_chain_strict`;
    - `aflb` and `aflb_yield_ready` now map to locked row 5
      (`thlb_parent_005_analysis_forest_land_base`) and are rejected before
      execution when their explicit `data/tsr/*.feather` seam checkpoint area
      already disagrees with the locked-chain reference; and
    - `scratch` now fails with a targeted contract error instead of guessing or
      consulting any legacy fallback surface.
  - Runtime surface:
    - the live event stream now emits `pipeline_validation_preflight_started`
      before execution; and
    - successful preflight writes seam/row/expected/actual/delta fields through
      `pipeline_validation_preflight_finished`, while failures surface the same
      mismatch in `pipeline_run_failed`.
  - Acceptance signal:
    - the checked-in TSA29 strict runbook now aborts immediately in preflight
      instead of progressing into parent steps when started from the current
      `aflb_yield_ready` seam; and
    - the bounded acceptance run reported locked row 5 expected
      `3110576.671 ha`, actual seam area `4378802.489 ha`, delta
      `1268225.818 ha`.
- 2026-04-19: Completed `P53.1d8` by wiring strict `scratch` to the raw-source GLB builder.
  - What shipped:
    - `tsa29_locked_chain_strict` preflight for seam `scratch` now calls the
      raw-source GLB builder instead of erroring out as undefined;
    - the checked-in runbook
      `runbooks/pipelines/tsa29.tsr.thlb_strict.scratch.yaml` now validates
      locked-chain row 1 from the clipped VRI/TSA boundary build path; and
    - successful scratch preflight stops after row 1 instead of spilling into
      step 002 or the downstream THLB executor.
  - Acceptance signal:
    - `femic pipelines run --runbook runbooks/pipelines/tsa29.tsr.thlb_strict.scratch.yaml --instance-root external/femic-tsa29-instance`
      completed in bounded step-001 mode;
    - locked row 1 expected `4933664.212 ha`, actual raw GLB `4933664.212 ha`,
      delta `0.000 ha`; and
    - the runtime event stream and mirrored event log both show
      `validated_parent_step_count=1` and an immediate stop before step 002.
- 2026-04-19: Completed `P53.1d10` by rebuilding `tsr.thlb_strict` to execute only locked validated step logic.
  - What shipped:
    - `src/femic/tsr_catalog/recipes.py` now exposes `run_tsr_thlb_locked_parent_step(...)`, a direct locked-step executor that runs exactly one approved locked parent step from one explicit checkpoint to the next checkpoint, emits compiled-step runtime events, and writes deterministic outputs under `data/tsr/strict_chain/`;
    - `src/femic/named_pipelines.py` now sequences `tsa29_locked_chain_strict` over that locked-step executor, validates milestone rows in place against `thlb_locked_chain_ledger.json`, and starts later seams from the already validated row order instead of replaying upstream rows; and
    - strict transformation rows now fail before execution if the locked recipe surface does not mark them approved or if their locked compiled logic is missing.
  - Guardrail:
    - `tsr.thlb_strict` no longer has a reachable path back to `run_tsr_thlb_parent_step(...)`; strict tests now monkeypatch that old runner to explode and prove the locked-step executor is the only path used.
  - Focused validation:
    - `.\.venv\Scripts\python.exe -m pytest tests/test_named_pipelines.py -q`
    - `.\.venv\Scripts\python.exe -m pytest tests/test_tsr_recipes.py -k "run_tsr_thlb_locked_parent_step_executes_one_locked_step" -q`
    - `.\.venv\Scripts\python.exe -m ruff check src/femic/named_pipelines.py src/femic/tsr_catalog/recipes.py src/femic/tsr_catalog/__init__.py tests/test_named_pipelines.py tests/test_tsr_recipes.py`
    - `.\.venv\Scripts\python.exe -m mypy src`
- 2026-04-19: Completed `P53.1d10d` by LU-parallelizing the strict locked-step executor.
  - What shipped:
    - `run_tsr_thlb_locked_parent_step(...)` now reuses the existing LU partition/bundle worker machinery, emits `parent_step_progress` events from bundle progress files, and returns strict-step results with `execution_mode=lu_parallel` instead of forcing one monolithic serial pass;
    - strict bounded transformation steps now run from cached or freshly materialized LU chunks and merge the bundle outputs back into the deterministic strict-chain checkpoint; and
    - the focused strict-step unit test now proves the locked executor uses LU chunk/bundle execution metadata rather than silently falling back to serial mode.
  - Focused validation:
    - `.\.venv\Scripts\python.exe -m pytest tests/test_tsr_recipes.py -k "run_tsr_thlb_locked_parent_step_executes_one_locked_step" -q`
    - `.\.venv\Scripts\python.exe -m pytest tests/test_named_pipelines.py -q`
    - `.\.venv\Scripts\python.exe -m ruff check src/femic/tsr_catalog/recipes.py tests/test_tsr_recipes.py src/femic/named_pipelines.py tests/test_named_pipelines.py`
    - `.\.venv\Scripts\python.exe -m mypy src`
- 2026-04-19: Completed `P53.1d10e` by making the pre-worker LU partition phase visible.
  - Diagnosis:
    - the strict `glb -> step2` run was spending several minutes before bundle worker launch selecting intersecting landscape units and materializing LU partition chunks for the first time, with no runtime events during that phase; and
    - after inspecting the live state directly, the `glb_checkpoint.feather` partition cache was shown to cover 132 selected LUs / 131 chunk records, so the strict run was stalling before bundle progress rather than inside compiled-step chunk work.
  - Fix:
    - `run_tsr_thlb_locked_parent_step(...)` now emits explicit `parent_step_progress` events for LU cache hits, LU selection start/finish, and LU partition materialization start/finish, so the strict runner no longer appears hung before bundle workers begin reporting progress.
  - Focused validation:
    - `.\.venv\Scripts\python.exe -m pytest tests/test_tsr_recipes.py -k "run_tsr_thlb_locked_parent_step_executes_one_locked_step" -q`
    - `.\.venv\Scripts\python.exe -m ruff check src/femic/tsr_catalog/recipes.py tests/test_tsr_recipes.py`
    - `.\.venv\Scripts\python.exe -m mypy src`
- 2026-04-19: Completed `P53.1d10f` by restoring the strict executor to the documented CPU-aware LU worker sizing path.
  - Diagnosis:
    - the strict locked-step executor had drifted onto a bad rule that defaulted `worker_count` from LU chunk count, which attempted to launch 131 workers for the 131 cached step-2 chunks and immediately tripped Python's Windows `ProcessPoolExecutor` cap.
  - Fix:
    - `run_tsr_thlb_locked_parent_step(...)` now reuses `_resolve_reconstructed_parallel_settings(...)`, which restores the documented `min(8, cpu_count)` worker cap and the matching default of `bundle_count = worker_count`.
  - Focused validation:
    - `.\.venv\Scripts\python.exe -m pytest tests/test_tsr_recipes.py -k "run_tsr_thlb_locked_parent_step_executes_one_locked_step or run_tsr_thlb_locked_parent_step_uses_cpu_aware_parallel_defaults" -q`
    - `.\.venv\Scripts\python.exe -m ruff check src/femic/tsr_catalog/recipes.py tests/test_tsr_recipes.py`
    - `.\.venv\Scripts\python.exe -m mypy src`
- 2026-04-19: Completed `P53.1d10g` by making strict LU cache reuse schema-aware.
  - Diagnosis:
    - the strict locked-step executor was reusing cached LU chunk directories on row count + area alone, which let stale chunk caches through even when they predated the current strict-state columns.
  - Fix:
    - `run_tsr_thlb_locked_parent_step(...)` now passes the current checkpoint column set into `_load_cached_landscape_unit_partition_records(...)`, so cache reuse requires a schema match that includes `_row_id`, `_stand_area_sqm`, `thlb_fact`, and `thlb`.
  - Focused validation:
    - `.\.venv\Scripts\python.exe -m pytest tests/test_tsr_recipes.py -k "run_tsr_thlb_locked_parent_step_executes_one_locked_step or run_tsr_thlb_locked_parent_step_passes_expected_columns_to_cache_lookup" -q`
    - `.\.venv\Scripts\python.exe -m ruff check src/femic/tsr_catalog/recipes.py tests/test_tsr_recipes.py`
    - `.\.venv\Scripts\python.exe -m mypy src`
- 2026-04-19: Completed `P53.1d10h` by syncing the locked row-2 fallback contract and unblocking production F_OWN overlays on LU bundles.
  - Diagnosis:
    - the accepted strict row-2 treaty/title fallback already existed in `src/femic/tsr_catalog/recipes.py`, but `external/femic-tsa29-instance/workbench/tsr/thlb_netdown.locked.recipe.yaml` still carried stale `manual_review_required` metadata for `thlb_parent_002_land_not_administered_by_the_province_compiled_02`; and
    - the strict extent-mismatch guard was still treating a valid `production_full_tsa` F_OWN artifact as wrong-scope merely because one LU bundle bbox is much smaller than the full-TSA source extent.
  - Fix:
    - synced the locked row-2 `compiled_02` entry to the accepted `aspatial_area_reduction` contract with the documented combined NStQ + Tsilhqot'in fallback target of `191,246 ha`; and
    - updated `_evaluate_source_extent_mismatch(...)` so a reviewed `production_full_tsa` overlay is allowed to be broader than a single LU bundle while smoke/AOI-scoped artifacts still fail reuse checks.
  - Focused validation:
    - `.\.venv\Scripts\python.exe -m pytest tests/test_tsr_recipes.py -k "evaluate_source_extent_mismatch_allows_production_full_tsa_overlay_for_lu_bundle or tsa29_locked_recipe_step2_uses_aspatial_area_reduction" -q`
    - `.\.venv\Scripts\python.exe -m ruff check src/femic/tsr_catalog/recipes.py tests/test_tsr_recipes.py`
    - `.\.venv\Scripts\python.exe -m mypy src`
- 2026-04-21: Completed `P53.1d10i` by correcting strict row-2 parent-step accounting to use the true before/after net change.
  - Diagnosis:
    - row 2 was now executing the right GIS and aspatial logic, but strict validation still only credited the exact overlay removal from `compiled_01`, which dropped the `compiled_02` direct-target deduction out of the parent-step marginal.
  - Fix:
    - `run_tsr_thlb_locked_parent_step(...)` now computes the parent-step marginal from the true checkpoint before/after net change instead of summing only exact same-parent removal helpers.
  - Outcome:
    - bounded `glb -> step2` rerun now lands at `696,931.685 ha` removed / `4,236,732.527 ha` remaining;
    - versus the locked chain this is `+150.361 ha` marginal / `-150.361 ha` cumulative; and
    - versus the TSR step-wise benchmark this is `-101.315 ha` marginal / `+130.527 ha` cumulative.
- 2026-05-03: Reopened `P53.1d9` after a fresh TSA29 strict named-pipeline
  row-2 rerun under `#169` found the first current locked-chain mismatch.
  - Run surface:
    - `runbooks/pipelines/tsa29.tsr.thlb_strict.glb_to_step2.yaml` now starts
      from the materialized strict GLB checkpoint and reaches row-2 validation.
  - Current mismatch:
    - row 2
      `thlb_parent_002_land_not_administered_by_the_province` removes
      `888,284.260 ha` against locked `696,781.324 ha`;
    - cumulative remaining area is `4,045,379.953 ha` against locked
      `4,236,882.888 ha`.
  - Diagnosis:
    - `compiled_01` removes `697,037.127 ha`;
    - `compiled_02` then removes another `191,247.132 ha`;
    - `compiled_02` is the documented `191,246 ha` NStQ/Tsilhqot'in residual
      fallback, so the row-2 named pipeline is double-counting that fallback
      after applying the parent-level marginal.
  - Next bounded repair:
    - `P53.1d9d` should make strict row-2 execution treat the
      direct-target residual as non-additive when the parent-level row-2
      marginal has already been applied, then rerun only the same
      `glb -> step 002` runbook and inspect the rebuilt result JSON/feather.
- 2026-05-03: Completed `P53.1d9` / `P53.1d9d` by validating the bounded
  TSA29 strict row-2 named-pipeline runbook cleanly against the locked chain.
  - Fix:
    - strict locked execution now drops the row-2 NStQ/Tsilhqot'in residual
      fallback from additive compiled logic when the parent-level row-2
      marginal already carries the combined locked contract; and
    - the remaining parent-level aspatial reduction is rewritten from the
      locked-chain ledger marginal and apportioned across LU chunks against
      the row-2 input denominator rather than applied once per chunk.
  - Acceptance run:
    - `.\.venv\Scripts\python.exe -m femic pipelines run --runbook runbooks/pipelines/tsa29.tsr.thlb_strict.glb_to_step2.yaml --instance-root external/femic-tsa29-instance`
    - locked row-2 expected `696,781.324 ha`, actual `696,781.324 ha`,
      delta `0.000 ha`;
    - locked cumulative expected `4,236,882.888 ha`, actual
      `4,236,882.888 ha`, delta `0.000 ha`; and
    - the named-pipeline summary reported maximum marginal and cumulative
      locked-chain deltas of `0.000 ha`.
  - Output inspection:
    - result JSON:
      `external/femic-tsa29-instance/runtime/logs/tsr/strict_chain/02_thlb_parent_002_land_not_administered_by_the_province.json`;
    - output feather:
      `external/femic-tsa29-instance/data/tsr/strict_chain/02_thlb_parent_002_land_not_administered_by_the_province.feather`;
    - inspected summaries show only `compiled_01` contributing to row-2
      removal, with `696,781.324 ha` removed and `4,236,882.888 ha`
      remaining.
  - Next bounded step:
    - return to `P53.1d4` and rerun the checked-in TSA29 strict named
      pipeline against the locked recipe surface to find the next remaining
      locked-chain mismatch, if any.
- 2026-05-03: Completed `P53.1d4` by rerunning the checked-in
  scratch-to-final TSA29 strict named-pipeline runbook against the locked
  recipe surface and recording the first remaining mismatch.
  - Run:
    - `.\.venv\Scripts\python.exe -m femic pipelines run --runbook runbooks/pipelines/tsa29.tsr.thlb_strict.scratch_full.yaml`
  - Result:
    - row 1 preflight validated the raw-source GLB at `4,933,664.212 ha`;
    - row 2 validated cleanly at `696,781.324 ha` removed and
      `4,236,882.888 ha` remaining; and
    - row 3 `thlb_parent_003_non_forest` is the first remaining mismatch.
  - Inspected row-3 outputs:
    - result JSON:
      `external/femic-tsa29-instance/runtime/logs/tsr/strict_chain/03_thlb_parent_003_non_forest.json`;
    - output feather:
      `external/femic-tsa29-instance/data/tsr/strict_chain/03_thlb_parent_003_non_forest.feather`;
    - row-3 marginal matches the locked chain:
      expected `1,075,872.217 ha`, actual `1,075,872.217 ha`, delta
      `0.000 ha`;
    - row-3 cumulative remaining area does not:
      expected `3,161,010.671 ha`, actual `3,857,791.995 ha`, delta
      `696,781.324 ha`.
  - Diagnosis:
    - the row-3 locked executor started from GLB area
      `4,933,664.212 ha` instead of the row-2 strict-chain checkpoint
      remaining area `4,236,882.888 ha`;
    - the row-3 output feather carries `thlb_fact` weighted area
      `3,857,791.995 ha`, confirming the rebuilt output matches the failed
      cumulative validator signal; and
    - the next repair should be the narrow strict-chain checkpoint handoff
      between row 2 and row 3, not another row-2 fallback-accounting change.
- 2026-05-03: The immediate `P53.1d11` repair is to preserve THLB state across
  strict locked-step handoff.
  - Root cause:
    - the outer named-pipeline sequence does pass each strict step's output
      path into the next step, but `run_tsr_thlb_locked_parent_step(...)`
      currently resets loaded checkpoint `thlb_fact` and `thlb` columns to
      fully active during input preparation.
  - Bounded implementation target:
    - preserve existing `thlb_fact` / `thlb` columns when a strict-chain
      checkpoint already carries them;
    - initialize those columns only for raw GLB-style inputs that do not yet
      carry THLB state; and
    - rerun only the scratch-to-step-3 path to prove row 2 feeds row 3 before
      advancing to later parent steps.
- 2026-05-03: Completed `P53.1d11` and validated strict handoff through row 3.
  - Fix:
    - `run_tsr_thlb_locked_parent_step(...)` now preserves incoming
      `thlb_fact` / `thlb` state when loading strict-chain checkpoints;
    - raw GLB-style inputs still initialize to fully active THLB state; and
    - LU partition cache metadata now includes the checkpoint file checksum so
      same-path, same-schema, same-area caches cannot hide changed THLB state.
  - Bounded validation:
    - reran scratch through `thlb_parent_003_non_forest` only;
    - row 3 consumed the row-2 checkpoint with input area `4,236,882.888 ha`;
    - row 3 removed `1,075,872.217 ha` and left `3,161,010.671 ha`;
    - the named-pipeline validator reported maximum marginal and cumulative
      locked-chain deltas of `0.000 ha`; and
    - inspected row-3 JSON and feather outputs confirm the rebuilt feather's
      `thlb_fact` weighted area is `3,161,010.671 ha`.
- 2026-05-03: Completed `P53.1d12` by validating strict row 4 from the
  row-3 strict-chain checkpoint and recording the first row-4 mismatch.
  - Run surface:
    - executed only `thlb_parent_004_roads_and_landings` from
      `data/tsr/strict_chain/03_thlb_parent_003_non_forest.feather`.
  - Result JSON:
    - `runtime/logs/tsr/strict_chain/04_thlb_parent_004_roads_and_landings.json`.
  - Output feather:
    - `data/tsr/strict_chain/04_thlb_parent_004_roads_and_landings.feather`.
  - Validator comparison:
    - input area `3,161,010.671 ha`;
    - locked row-4 marginal `50,434.000 ha`, actual reported marginal
      `50,434.299 ha`, delta `+0.299 ha`;
    - locked row-4 cumulative `3,110,576.671 ha`, actual reported cumulative
      `3,110,576.373 ha`, delta `-0.298 ha`.
  - Output inspection:
    - the rebuilt row-4 feather still has `thlb_fact` weighted area
      `3,161,010.671 ha`, matching the row-3 input area rather than the
      reported row-4 remaining area;
    - row-4 `compiled_01` and `compiled_02` report no exact spatial removal;
    - row-4 `compiled_03` reports the aspatial fallback removal
      `50,434.299 ha`.
  - Next bounded repair:
    - make the row-4 aspatial area fallback write the deducted state into the
      chained output checkpoint before advancing to row 5.
- 2026-05-03: The immediate `P53.1d13` repair is to persist strict row-4
  aspatial area fallback deductions into chained THLB state.
  - Root cause:
    - `_apply_aspatial_area_reduction(...)` currently shrinks
      `FEMIC_EFFECTIVE_AREA_SQM` / `_stand_area_sqm` while deliberately leaving
      `thlb_fact` unchanged;
    - strict chained validation carries managed area via `_stand_area_sqm *
      thlb_fact`, so the row-4 JSON can report the fallback removal while the
      output feather still carries the row-3 managed area.
  - Bounded implementation target:
    - add strict locked-step behavior that persists `aspatial_area_reduction`
      fallbacks into `thlb_fact` / `thlb` state for chained checkpoints;
    - keep canonical geometry/source area fields unchanged; and
    - rerun only row 4 from the validated row-3 checkpoint.
- 2026-05-03: Completed `P53.1d13` by persisting the row-4 aspatial area
  fallback into chained THLB state.
  - Fix:
    - strict locked execution now marks `aspatial_area_reduction` fallbacks as
      THLB-state-persistent;
    - reconstructed LU fallback execution writes those deductions into
      `thlb_fact` / `thlb` instead of only shrinking effective area fields; and
    - locked strict fallback targets use the locked ledger marginal directly
      rather than rescaling the already-locked value.
  - Bounded validation:
    - reran only `thlb_parent_004_roads_and_landings` from
      `data/tsr/strict_chain/03_thlb_parent_003_non_forest.feather`;
    - row-4 input area was `3,161,010.671 ha`;
    - row 4 removed `50,434.000 ha`;
    - row-4 output remaining area was `3,110,576.671 ha`, with residual
      cumulative delta `0.000359 ha` from source precision.
  - Output inspection:
    - rebuilt row-4 feather `thlb_fact` weighted area is
      `3,110,576.671 ha`;
    - canonical source area fields remain unchanged; and
    - `thlb_fact` now carries the row-4 deduction for the next chained step.
- 2026-05-03: The immediate `P53.1d14` validation target is strict row 5
  only.
  - Row 5 (`thlb_parent_005_analysis_forest_land_base`) is a
    reference-only milestone, not a transformation.
  - The bounded run surface is therefore a locked-chain reference validation
    from `data/tsr/strict_chain/04_thlb_parent_004_roads_and_landings.feather`.
  - Acceptance is that the carried checkpoint `thlb_fact` area matches the
    locked row-5 cumulative remaining area before any row-6 transformation is
    attempted.
- 2026-05-03: Completed `P53.1d14` by running the row-5 reference-only
  validation and recording the first checkpoint-area helper mismatch.
  - Run surface:
    - started from
      `data/tsr/strict_chain/04_thlb_parent_004_roads_and_landings.feather`;
    - targeted `thlb_parent_005_analysis_forest_land_base`; and
    - stopped before any row-6 transformation.
  - Validator result:
    - locked row-5 marginal `0.000 ha`, actual `0.000 ha`;
    - locked row-5 cumulative `3,110,576.671 ha`;
    - named-pipeline reference helper cumulative `4,933,664.212 ha`;
    - cumulative delta `1,823,087.541 ha`.
  - Output inspection:
    - the row-4 checkpoint carries `FEATURE_AREA_SQM * thlb_fact =
      3,110,576.671 ha`;
    - `FEATURE_AREA_SQM` alone sums to `4,933,664.212 ha`; and
    - the checkpoint does not carry `_stand_area_sqm`, so
      `_managed_area_ha_from_checkpoint(...)` falls through to geometry/full
      area and ignores the chained `thlb_fact` state.
  - Next bounded repair:
    - make strict reference-only checkpoint-area validation honor
      `FEATURE_AREA_SQM * thlb_fact` when `_stand_area_sqm` is absent, then
      rerun row 5 only.
- 2026-05-03: Completed `P53.1d15` by fixing strict reference-only
  checkpoint-area validation and rerunning row 5 only.
  - Fix:
    - `_managed_area_ha_from_checkpoint(...)` now uses carried `thlb_fact`
      state with `_stand_area_sqm`, `FEATURE_AREA_SQM`, or other available
      area fields before falling back to unmanaged geometry area.
  - Focused checks:
    - added a regression test for checkpoints with `FEATURE_AREA_SQM` and
      `thlb_fact` but no `_stand_area_sqm`;
    - ran the existing explicit checkpoint-area test and the new regression
      test; and
    - ran `ruff check` on the touched code/tests.
  - Bounded validation:
    - reran only `thlb_parent_005_analysis_forest_land_base` from
      `data/tsr/strict_chain/04_thlb_parent_004_roads_and_landings.feather`;
    - row 5 finished as `reference_validated`;
    - actual carried area was `3,110,576.671359 ha`;
    - locked row-5 cumulative was `3,110,576.671000 ha`; and
    - residual cumulative delta was `0.000359 ha`.
  - Output inspection:
    - the row-4 checkpoint still has raw `FEATURE_AREA_SQM` sum
      `4,933,664.212 ha`; and
    - the validated carried managed area is
      `FEATURE_AREA_SQM * thlb_fact = 3,110,576.671 ha`.
  - Next bounded validation:
    - validate the production strict named-pipeline GLB -> AFLB stage in one
      pass from the validated GLB seam through row 5 before moving on to row 6
      / AFLB -> LHLB.
- 2026-05-03: The immediate `P53.1d16` validation target is the production
  strict named-pipeline GLB -> AFLB stage in a single pass.
  - Reason:
    - the stepwise row-2 through row-5 chain now validates cleanly, but the
      original problem was that the production named-pipeline stage run was not
      yielding the expected AFLB result.
  - Bounded run surface:
    - add a checked-in strict runbook that starts at seam `glb` and stops at
      `thlb_parent_005_analysis_forest_land_base`;
    - execute it through `femic pipelines run`; and
    - inspect the resulting row-2, row-3, row-4, and row-5 validation signals,
      including the row-4 feather carried `thlb_fact` area.
  - Acceptance:
    - the one-pass GLB -> AFLB run must report locked row-5 cumulative
      `3,110,576.671 ha` with only source-precision residual before any
      AFLB -> LHLB row is attempted.
- 2026-05-03: Completed `P53.1d16` by validating the production strict
  named-pipeline GLB -> AFLB stage in a single pass.
  - Run surface:
    - added checked-in runbook
      `runbooks/pipelines/tsa29.tsr.thlb_strict.glb_to_aflb.yaml`;
    - ran `femic pipelines run` from seam `glb`; and
    - stopped at `thlb_parent_005_analysis_forest_land_base` before any row-6
      AFLB -> LHLB transformation.
  - Production pipeline result:
    - validated parent-step count `5`;
    - latest locked parent step `thlb_parent_005_analysis_forest_land_base`;
    - expected final managed area `3,110,576.671 ha`;
    - actual final managed area `3,110,576.671 ha`;
    - maximum marginal and cumulative locked-chain deltas reported as
      `0.000 ha`.
  - Output inspection:
    - row-2 JSON/feather: `696,781.324 ha` removed and
      `4,236,882.888 ha` carried in `FEATURE_AREA_SQM * thlb_fact`;
    - row-3 JSON/feather: `1,075,872.217 ha` removed and
      `3,161,010.671 ha` carried in `FEATURE_AREA_SQM * thlb_fact`;
    - row-4 JSON/feather: `50,434.000 ha` removed and
      `3,110,576.671 ha` carried in `FEATURE_AREA_SQM * thlb_fact`;
    - row 5 runtime event finished as `reference_validated`; and
    - no row-6 transformation was attempted.
  - Next bounded validation:
    - validate the production strict named-pipeline AFLB -> LHLB stage through
      row 12, stopping before row 13 / LHLB -> THLB.
- 2026-05-03: The immediate `P53.1d17` validation target is the production
  strict named-pipeline AFLB -> LHLB stage.
  - Boundary:
    - rows 6 through 12 are `land_base_stage = aflb_to_lhlb`;
    - row 13 is the first `lhlb_to_thlb` transformation and must not run in
      this slice.
  - Bounded run surface:
    - add a checked-in strict runbook that starts at seam `glb` and stops at
      `thlb_parent_012_proven_aboriginal_rights_areas`;
    - execute it through `femic pipelines run`; and
    - inspect the rebuilt stage outputs rather than relying only on command
      success.
  - Acceptance:
    - the production one-pass run must validate through locked row 12 and stop
      before row 13, or report the first specific AFLB -> LHLB mismatch.
- 2026-05-03: Completed `P53.1d17` by running the production strict
  AFLB -> LHLB stage validation and recording the first row-6 blocker.
  - Run surface:
    - added checked-in runbook
      `runbooks/pipelines/tsa29.tsr.thlb_strict.glb_to_lhlb.yaml`;
    - ran `femic pipelines run` from seam `glb`;
    - targeted `thlb_parent_012_proven_aboriginal_rights_areas`; and
    - intended to stop before row 13 / LHLB -> THLB.
  - Result:
    - GLB -> AFLB prefix still validated through row 5;
    - row 5 finished as `reference_validated` at `3,110,576.671 ha`;
    - row 6 `thlb_parent_006_parks_protected_areas_area_base_tenures`
      started, then the strict locked contract guard failed before execution;
    - no row-6 JSON or feather output was written.
  - Failure:
    - `Strict pipeline step is not approved on the locked recipe surface:
      thlb_parent_006_parks_protected_areas_area_base_tenures`.
  - Contract evidence:
    - row 6 is the first `aflb_to_lhlb` transformation;
    - recipe row 6 has `ratchet_state: benchmarked`, not `approved`;
    - compiled row-6 logic is present and `ready`;
    - locked ledger row 6 carries `locked_net_removed_area_ha = 306,327.000`
      and `locked_cumulative_remaining_area_ha = 2,804,249.671`; and
    - locked source kind is `exact_plus_residual_bridge`.
  - Next bounded repair:
    - reconcile strict row-6 locked recipe approval/ratchet-state semantics,
      then rerun the AFLB -> LHLB stage from the validated AFLB checkpoint
      without replaying GLB -> AFLB.
- 2026-05-03: The immediate `P53.1d18` execution target is to stop tripping
  over the row-6 metadata gate and run the actual AFLB -> LHLB recipe logic.
  - Fix:
    - strict validation may execute locked rows marked `benchmarked` when
      compiled logic exists, instead of requiring only `approved`.
  - Bounded run surface:
    - start from
      `data/tsr/strict_chain/04_thlb_parent_004_roads_and_landings.feather`,
      the validated AFLB checkpoint state;
    - use seam `aflb` so strict validation starts after row 5; and
    - target `thlb_parent_012_proven_aboriginal_rights_areas`.
  - Scope boundary:
    - do not replay GLB -> AFLB rows 2-5;
    - do not run row 13 / LHLB -> THLB.
- 2026-05-03: Completed `P53.1d18` by making the AFLB -> LHLB suffix run
  start from the validated AFLB checkpoint and expose the first real row-7
  recipe/data mismatch.
  - Fixes:
    - strict validation now treats locked rows marked `ratchet_state:
      benchmarked` as executable when compiled logic exists;
    - the `aflb` and `aflb_yield_ready` strict seams now route through the
      locked parent-step sequence instead of falling through to the generic
      broad THLB runner; and
    - focused regression coverage now proves an `aflb` strict run executes
      only through the requested `target_parent_step_id` even when later
      recipe rows are present.
  - Corrected run surface:
    - runbook:
      `runbooks/pipelines/tsa29.tsr.thlb_strict.aflb_to_lhlb.yaml`;
    - start checkpoint:
      `data/tsr/strict_chain/04_thlb_parent_004_roads_and_landings.feather`;
    - target:
      `thlb_parent_012_proven_aboriginal_rights_areas`; and
    - runtime event log:
      `runtime/logs/tsr/named_pipeline_events-tsr_thlb_strict-20260503T234033Z.log`.
  - Output inspection:
    - row 6 wrote
      `data/tsr/strict_chain/06_thlb_parent_006_parks_protected_areas_area_base_tenures.feather`;
    - row 6 result JSON reports input `3,110,576.671 ha`, removal
      `306,327.000 ha`, remaining `2,804,249.671 ha`, and status
      `applied_with_blockers`;
    - row 7 wrote
      `data/tsr/strict_chain/07_thlb_parent_007_old_growth_management_areas.feather`
      before strict validation failed;
    - row 7 result JSON reports input `2,804,249.671 ha`, removal
      effectively `0.000 ha`, remaining `2,804,249.671 ha`, and status
      `blocked_missing_source`; and
    - the named-pipeline validator fails row 7 against the locked ledger:
      expected marginal `223,638.262 ha`, actual `0.000 ha`, expected
      cumulative `2,580,611.409 ha`, actual `2,804,249.671 ha`.
  - Scope correction:
    - earlier bad runs that replayed upstream rows or passed the intended
      stage boundary are not the accepted validation signal for this slice;
    - the accepted signal is the corrected suffix run from the row-4 AFLB
      checkpoint to the first strict row-7 mismatch.
  - Next bounded repair:
    - `P53.1d19` should stay on row 7 and reconcile the current strict OGMA
      delta before advancing. After materializing `RMP_OGMA_LEGAL.gpkg` from
      annex and fixing the extent guard to use the recorded full artifact
      extent, row 7 executes from the row-6 strict-chain checkpoint and removes
      about `166,228 ha`, but the locked chain expects `223,638.262 ha`.
      The next bounded action is to prove restart stability by running locked
      step 6 from the validated AFLB checkpoint, saving the post-step-6
      checkpoint, then running locked step 7 twice from that exact checkpoint
      and comparing output hashes and managed-area totals; do not propose new
      work or run downstream steps.
- 2026-05-03: Completed the bounded row-6/row-7 restart-stability check under
  `P53.1d19`.
  - Start checkpoint:
    - `data/tsr/strict_chain/04_thlb_parent_004_roads_and_landings.feather`;
    - managed area `3,110,576.671359 ha`; and
    - SHA-256 `3536fdeed6000e99337eb7cf5b11cf9df8eb75835799f24cc46dcb7bc497d7b6`.
  - Row 6 from the AFLB checkpoint:
    - output `data/tsr/strict_chain/06_thlb_parent_006_parks_protected_areas_area_base_tenures.feather`;
    - removed `306,327.000000 ha`;
    - remaining `2,804,249.671359 ha`; and
    - output SHA-256
      `7aa80adfff3340718c080bda17e7ecbc7414ee67e116110594b9f95591a99d90`.
  - Row 7 from the post-step-6 checkpoint:
    - first run removed `166,228.033503 ha` and left
      `2,638,021.637855 ha`;
    - second run from the same post-step-6 checkpoint removed the same
      `166,228.033503 ha` and left the same `2,638,021.637855 ha`;
    - both row-7 runs wrote identical output feather SHA-256
      `7f826f88e4d52cd48706a841a32e35b85951d0a6395c0b5c618474d7fb4c1037`; and
    - row-7 repeatability is therefore stable at the checkpoint/output level.
  - Remaining row-7 issue:
    - the stable chained row-7 result still removes `44,490.966497 ha` less
      than the TSR row-7 marginal benchmark `210,719.000 ha`; and
    - it leaves cumulative area `56,899.637855 ha` above the TSR cumulative
      target `2,581,122.000 ha`, so the next work must reconcile the
      chain-correct row-7 area gap before any row-8 validation.
- 2026-05-03: Completed `P53.1d19` by relocking row 7 to the reproducible
  chained PERM/ROT legal OGMA result.
  - Ledger update:
    - `locked_net_removed_area_ha = 166,228.034`;
    - `locked_cumulative_remaining_area_ha = 2,638,021.638`;
    - `locked_cumulative_delta_ha = 56,899.638`; and
    - `locked_source_note` now records that this relocked value supersedes the
      older AFLB-start row-7 bounded result because that value was not
      chain-comparable with the post-step-6 restart surface.
  - Rationale:
    - validated AFLB cumulative area matches the TSR/locked milestone;
    - step 6 marginal deduction matches its locked target from AFLB;
    - row 7 is deterministic from the saved post-step-6 checkpoint; and
    - the older `223,638.262 ha` row-7 value cannot be reproduced from the
      current validated chain.
  - Next bounded validation:
    - `P53.1d20` should run only row 8 from the relocked post-row-7
      checkpoint, then inspect the rebuilt output before deciding whether to
      advance farther through AFLB -> LHLB.
- 2026-05-03: Completed `P53.1d20` by validating strict row 8 from the
  relocked post-row-7 checkpoint and inspecting the rebuilt artifacts.
  - Input materialization:
    - row-8 UWR/WHA source GeoPackages were annex pointer stubs before this
      slice;
    - materialized only the five row-8 wildlife source artifacts from
      `external/femic-tsa29-instance/data/downloads/bcdc/`; and
    - verified the materialized files are readable EPSG:3005 GeoPackages.
  - Run surface:
    - runner: `run_tsr_thlb_locked_parent_step`;
    - parent step: `thlb_parent_008_wildlife_habitat_areas`;
    - checkpoint:
      `data/tsr/strict_chain/07_thlb_parent_007_old_growth_management_areas.feather`;
    - workers/bundles: `8 / 8`; and
    - no row-9 or downstream step was run.
  - Output inspection:
    - result JSON:
      `runtime/logs/tsr/strict_chain/08_thlb_parent_008_wildlife_habitat_areas.json`;
    - rebuilt checkpoint:
      `data/tsr/strict_chain/08_thlb_parent_008_wildlife_habitat_areas.feather`;
    - input `2,638,021.638 ha`;
    - removed `113,733.548 ha`;
    - remaining `2,524,288.089 ha`;
    - rebuilt feather SHA-256
      `1b371d721920be081946ad00680e962faee2abebe032a50543f3d74ba7934bc2`;
    - feather inspection confirmed `thlb_fact * geometry` sums to the same
      `2,524,288.089 ha` managed area.
  - Comparison:
    - old locked row-8 marginal: `131,567.592 ha`;
    - old locked row-8 cumulative: `2,449,043.817 ha`;
    - TSR row-8 cumulative: `2,427,066.000 ha`; and
    - current chained row-8 result is `97,222.089 ha` above the TSR
      cumulative target.
  - Next bounded move:
    - do not advance to row 9 yet;
    - reconcile or relock row 8 to the reproducible chained wildlife-habitat
      result under `P53.1d21`.
- 2026-05-03: User-directed follow-on for `P53.1d21` / `P53.1d22`:
  - relock row 8 to the inspected chained wildlife-habitat result:
    - `locked_net_removed_area_ha = 113,733.548`;
    - `locked_cumulative_remaining_area_ha = 2,524,288.089`; and
    - `locked_cumulative_delta_ha = 97,222.089`;
  - then run only row 9 from
    `data/tsr/strict_chain/08_thlb_parent_008_wildlife_habitat_areas.feather`;
  - do not advance beyond row 9 in this slice.
- 2026-05-03: Completed `P53.1d21` by relocking row 8 to the inspected
  chained wildlife-habitat result.
  - Ledger row 8 now records:
    - `locked_net_removed_area_ha = 113,733.548`;
    - `locked_cumulative_remaining_area_ha = 2,524,288.089`;
    - `locked_cumulative_delta_ha = 97,222.089`; and
    - a source note that this supersedes the older row-8 lock after the row-7
      relock changed the chained input state.
  - The next bounded run remains `P53.1d22`: row 9 only from the relocked
    row-8 checkpoint.
- 2026-05-03: Completed `P53.1d22` by validating strict row 9 from the
  relocked post-row-8 checkpoint and inspecting the rebuilt artifacts.
  - Input materialization:
    - row-9 legal-planning GeoPackage
      `WHSE_LAND_USE_PLANNING_RMP_PLAN_LEGAL_POLY_SVW.gpkg` was an annex
      pointer stub before this slice;
    - materialized that single row-9 source artifact; and
    - verified it is a readable EPSG:3005 GeoPackage with `761` CRITFISH
      features covering about `60,320.075 ha` raw source area.
  - Run surface:
    - runner: `run_tsr_thlb_locked_parent_step`;
    - parent step: `thlb_parent_009_critical_habitat_for_fish`;
    - checkpoint:
      `data/tsr/strict_chain/08_thlb_parent_008_wildlife_habitat_areas.feather`;
    - workers/bundles: `8 / 8`; and
    - no row-10 or downstream step was run.
  - Output inspection:
    - result JSON:
      `runtime/logs/tsr/strict_chain/09_thlb_parent_009_critical_habitat_for_fish.json`;
    - rebuilt checkpoint:
      `data/tsr/strict_chain/09_thlb_parent_009_critical_habitat_for_fish.feather`;
    - input `2,524,288.089 ha`;
    - removed `20,965.006 ha`;
    - remaining `2,503,323.083 ha`;
    - rebuilt feather SHA-256
      `9191a8d80e62d39e3f3efcb3835c370caa93dd39242ee3b16f2eb4940386f14e`;
    - feather inspection confirmed `thlb_fact * geometry` sums to the same
      `2,503,323.083 ha` managed area.
  - Comparison:
    - old locked row-9 marginal: `25,974.994 ha`;
    - old locked row-9 cumulative: `2,423,068.823 ha`;
    - TSR row-9 marginal: `11,521.000 ha`;
    - TSR row-9 cumulative: `2,415,545.000 ha`; and
    - current chained row-9 result is `87,778.083 ha` above the TSR
      cumulative target.
  - Next bounded move:
    - do not advance to row 10 yet;
    - reconcile or relock row 9 to the reproducible chained
      critical-fish-habitat result under `P53.1d23`.
- 2026-05-03: User-directed follow-on for `P53.1d23` / `P53.1d24`:
  - relock row 9 to the inspected chained critical-fish-habitat result:
    - `locked_net_removed_area_ha = 20,965.006`;
    - `locked_cumulative_remaining_area_ha = 2,503,323.083`; and
    - `locked_cumulative_delta_ha = 87,778.083`;
  - then run only row 10 from
    `data/tsr/strict_chain/09_thlb_parent_009_critical_habitat_for_fish.feather`;
  - do not advance beyond row 10 in this slice.
- 2026-05-03: Completed `P53.1d23` by relocking row 9 to the inspected
  chained critical-fish-habitat result.
  - Ledger row 9 now records:
    - `locked_net_removed_area_ha = 20,965.006`;
    - `locked_cumulative_remaining_area_ha = 2,503,323.083`;
    - `locked_cumulative_delta_ha = 87,778.083`; and
    - a source note that this supersedes the older row-9 lock after the row-8
      relock changed the chained input state.
  - The next bounded run remains `P53.1d24`: row 10 only from the relocked
    row-9 checkpoint.
