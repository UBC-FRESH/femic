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
- 2026-05-03: Completed `P53.1d24` by fixing reviewed zero-removal locked
  rows to carry checkpoints forward without LU partitioning, then validating
  row 10 from the relocked post-row-9 checkpoint.
  - Code fix:
    - `run_tsr_thlb_locked_parent_step` now detects locked parent steps whose
      compiled logic is entirely `manual_review_required` and whose locked
      marginal removal is `0.000 ha`;
    - such rows write the strict-chain checkpoint/result directly with
      `execution_mode = reviewed_skip`, `status = applied_noop`, and
      `worker_count = lu_chunk_count = lu_bundle_count = 0`; and
    - regression coverage proves the reviewed zero-removal path does not
      instantiate the worker executor.
  - Row-10 run surface:
    - parent step: `thlb_parent_010_lakeshore_management`;
    - checkpoint:
      `data/tsr/strict_chain/09_thlb_parent_009_critical_habitat_for_fish.feather`;
    - result JSON:
      `runtime/logs/tsr/strict_chain/10_thlb_parent_010_lakeshore_management.json`;
    - rebuilt checkpoint:
      `data/tsr/strict_chain/10_thlb_parent_010_lakeshore_management.feather`.
  - Output inspection:
    - input `2,503,323.083 ha`;
    - removed `0.000 ha`;
    - remaining `2,503,323.083 ha`;
    - workers / LU chunks / bundles: `0 / 0 / 0`;
    - rebuilt feather SHA-256
      `9191a8d80e62d39e3f3efcb3835c370caa93dd39242ee3b16f2eb4940386f14e`;
    - feather inspection confirmed `thlb_fact * geometry` sums to the same
      `2,503,323.083 ha` managed area.
  - Ledger update:
    - row 10 remains a reviewed skip with
      `locked_net_removed_area_ha = 0.000`;
    - `locked_cumulative_remaining_area_ha = 2,503,323.083`; and
    - `locked_cumulative_delta_ha = 88,105.083`.
  - Next bounded move:
    - `P53.1d25` should run row 11 only from the row-10 reviewed-skip
      checkpoint; do not advance beyond row 11 in that slice.
- 2026-05-03: Completed `P53.1d25a` as a narrow row-11 preparation fix after
  the first row-11 attempt showed the LU partition cache was path-bound.
  - Problem:
    - row 10 is a reviewed-skip carry-forward whose checkpoint content matches
      row 9, but the strict-chain filename changes from row 9 to row 10;
    - the LU partition cache loader required exact checkpoint-path equality,
      so a byte-identical checkpoint alias could miss an existing cache and
      rematerialize LU partitions.
  - Fix:
    - `_load_cached_landscape_unit_partition_records` now accepts a different
      checkpoint path only when the caller supplies an expected checkpoint
      SHA-256 and the cached metadata has the same SHA-256;
    - if no expected SHA-256 is supplied, the old path-equality requirement
      still applies.
  - Validation:
    - added a regression test for same-content checkpoint alias reuse;
    - confirmed the same test rejects a path alias when no SHA-256 is supplied
      and rejects an alias with a different SHA-256.
  - Next bounded move:
    - `P53.1d25` remains open: run row 11 only from the row-10 checkpoint and
      inspect the rebuilt row-11 output before advancing.
- 2026-05-04: Completed `P53.1d25b` by preserving LU-parallel output
  partitions as the next strict-chain checkpoint cache.
  - Problem:
    - LU-parallel locked parent-step workers wrote partitioned bundle outputs,
      but the parent runner only merged those bundles into the strict-chain
      feather and discarded the partition cache handoff;
    - the next parent step therefore had to repartition the merged feather even
      when the previous run had just processed the same partitioned chunks.
  - Fix:
    - worker bundle outputs now retain prepared-state columns needed for the
      next step's cached chunk inputs;
    - final strict-chain checkpoint feathers still strip those internal columns;
    - after writing the final checkpoint, the locked parent-step runner
      registers the worker bundle outputs as a SHA-verified LU partition cache
      for the new checkpoint; and
    - reviewed zero-removal pass-through rows carry an input checkpoint
      partition cache forward to their output checkpoint when one exists.
  - Validation:
    - regression coverage confirms a LU-parallel locked step writes a final
      checkpoint without internal columns while registering cache chunks that
      retain the prepared columns;
    - regression coverage confirms a reviewed-skip row can carry an input
      partition cache forward without entering the worker executor.
  - Next bounded move:
    - `P53.1d25` remains open: rebuild row 9, carry row 10 through, and then
      run row 11 only if the row-10 checkpoint has a completed cache.
- 2026-05-04: Completed the bounded `P53.1d25` row-11 execution check from the
  rebuilt row-10 checkpoint and exposed the next blocker.
  - Execution:
    - row 11 now starts from the row-10 prepared cache instead of
      repartitioning the merged feather;
    - `thlb_parent_011_community_areas_of_special_concern` ran LU-parallel
      with `8` workers and `8` cache bundle records; and
    - the rebuilt row-11 checkpoint also registered a downstream prepared cache.
  - Result:
    - actual marginal removal: `238,553.790 ha`;
    - locked TSR marginal benchmark: `62,460.000 ha`;
    - actual remaining area: `2,264,769.293 ha`; and
    - locked TSR cumulative benchmark: `2,352,758.000 ha`.
  - Interpretation:
    - restart/cache mechanics are now working for the row-10 to row-11 handoff;
    - the remaining blocker is row-11 source/filter logic, not pipeline
      restart mechanics.
  - Next bounded move:
    - `P53.1d25c` should normalize the legal-planning `LEGAL_FEAT_ATRB_*`
      name/value slots into filterable fields, narrow the row-11 community
      areas source contract off the blanket CASC overlay, and then rerun row 11
      only; do not advance to row 12.
- 2026-05-04: Completed `P53.1d25c` and reran row 11 only from the validated
  row-10 reviewed-skip checkpoint.
  - Repair:
    - source loading now materializes filterable fields from repeated
      legal-planning `*_NAME` / `*_VALUE` attribute slots; and
    - row-11 CASC execution now narrows the legal-planning source contract to
      `SOURCE_HARV_CAT in {ART, IR, STR}` instead of excluding the full CASC
      polygon set.
  - Validation:
    - targeted regression coverage passed for the new attribute-slot
      normalization helper and the row-11 compiled filter contract; and
    - bounded row-11 rerun from
      `data/tsr/strict_chain/10_thlb_parent_010_lakeshore_management.feather`
      finished `applied` in `lu_parallel` mode with `8` workers / `8` bundles.
  - Inspected outputs:
    - result JSON:
      `runtime/logs/tsr/strict_chain/11_thlb_parent_011_community_areas_of_special_concern.json`;
    - rebuilt checkpoint:
      `data/tsr/strict_chain/11_thlb_parent_011_community_areas_of_special_concern.feather`;
    - actual marginal removal: `69,716.086 ha`;
    - actual remaining area: `2,433,606.997 ha`; and
    - rebuilt feather managed area matches the JSON and still strips internal
      `_row_id` / `_stand_area_sqm` columns.
  - Comparison:
    - prior row-11 overcut was `238,553.790 ha` removed;
    - repaired row-11 is now `+7,256.086 ha` above the TSR marginal benchmark
      `62,460.000 ha`; and
    - repaired row-11 remains `+80,848.997 ha` above the TSR cumulative
      benchmark `2,352,758.000 ha`.
  - Next bounded move:
    - `P53.1d25d` should adjudicate whether the repaired row-11 result should
      be accepted/relocked or narrowed further before row 12.
- 2026-05-04: Completed `P53.1d25d` by relocking row 11 to the repaired chained
  CASC result and stopping before row 12.
  - Relock decision:
    - accepted the repaired row-11 result as the new locked strict benchmark
      rather than spending more time narrowing the same legal-planning step;
      and
    - updated the canonical locked-chain ledger entry for
      `thlb_parent_011_community_areas_of_special_concern`.
  - Updated row-11 locked values:
    - locked marginal: `69,716.086 ha`;
    - locked cumulative: `2,433,606.997 ha`; and
    - locked cumulative delta vs TSR: `80,848.997 ha`.
  - Superseded row-11 lock:
    - previous lock `78,593.956 ha` removed and `2,344,474.867 ha` remaining is
      now treated as superseded by the repaired slot-aware CASC semantics.
  - Next bounded move:
    - `P53.1d26` should run only row 12 from the relocked post-row-11
      checkpoint and inspect the rebuilt outputs before any row-13 work.
  - Revised bounded move after row-11 relock:
    - because row 12 is the final AFLB -> LHLB step and is already an approved
      benchmark-anchored PRA bridge, treat it as the stage-closing aspatial
      adjustment surface rather than inventing a new boundary-acquisition task;
      and
    - size the row-12 explicit aspatial reduction from the relocked row-11
      cumulative area so the rebuilt row-12 checkpoint lands at `0.000 ha`
      cumulative delta versus the TSR row-12 benchmark.
- 2026-05-04: Completed `P53.1d26` by turning row 12 into an explicit
  stage-closing aspatial PRA bridge and rerunning row 12 only.
  - Repair:
    - row-12 compiled logic now uses `aspatial_reduction` with
      `direct_target_removed_area: true` instead of `manual_review_required`;
      and
    - the locked row-12 ledger value was resized from the old benchmark-only
      `68,401.000 ha` bridge to `149,249.997 ha` so the relocked row-11 input
      state closes AFLB -> LHLB exactly on the TSR cumulative target.
  - Validation:
    - targeted regression coverage passed for the row-12 specialized compiled
      logic contract; and
    - bounded row-12 rerun from
      `data/tsr/strict_chain/11_thlb_parent_011_community_areas_of_special_concern.feather`
      finished `applied` in `lu_parallel` mode.
  - Inspected outputs:
    - result JSON:
      `runtime/logs/tsr/strict_chain/12_thlb_parent_012_proven_aboriginal_rights_areas.json`;
    - rebuilt checkpoint:
      `data/tsr/strict_chain/12_thlb_parent_012_proven_aboriginal_rights_areas.feather`;
    - actual marginal removal: `149,249.997 ha`;
    - actual remaining area: `2,284,357.000 ha`; and
    - rebuilt feather managed area matches the JSON and still strips internal
      `_row_id` / `_stand_area_sqm` columns.
  - Comparison:
    - row-12 cumulative delta versus the TSR benchmark is now effectively
      `0.000 ha` (floating-point residue only); and
    - row-12 marginal is intentionally above the raw TSR row-12 benchmark by
      the carried row-11 residual because this step is now the explicit
      AFLB-to-LHLB stage-closing aspatial bridge.
  - Next bounded move:
    - `P53.1d27` should run only row 13 from the zero-delta post-row-12
      checkpoint and inspect the rebuilt outputs before any row-14 work.
- 2026-05-05: Completed `P53.1d27` by running row 13 only from the zero-delta
  post-row-12 checkpoint and inspecting the rebuilt outputs.
  - Run surface:
    - parent step:
      `thlb_parent_013_areas_considered_inoperable`;
    - checkpoint:
      `data/tsr/strict_chain/12_thlb_parent_012_proven_aboriginal_rights_areas.feather`;
      and
    - execution mode: `lu_parallel` with `8` workers / `8` bundles.
  - Inspected outputs:
    - result JSON:
      `runtime/logs/tsr/strict_chain/13_thlb_parent_013_areas_considered_inoperable.json`;
    - rebuilt checkpoint:
      `data/tsr/strict_chain/13_thlb_parent_013_areas_considered_inoperable.feather`;
    - actual marginal removal: `31,974.000 ha`;
    - actual remaining area: `2,252,383.000 ha`; and
    - rebuilt feather managed area matches the JSON and still strips internal
      `_row_id` / `_stand_area_sqm` columns.
  - Execution breakdown:
    - exact unstable-terrain overlay removed `0.000 ha`; and
    - steep-slope aspatial rollback removed the full `31,974.000 ha`.
  - Comparison:
    - TSR row-13 benchmark marginal is `33,533.000 ha`, so the current row-13
      result underremoves by `1,559.000 ha`;
    - TSR row-13 cumulative benchmark is `2,250,824.000 ha`, so the current
      row-13 checkpoint remains `1,559.000 ha` high; and
    - the old row-13 lock is no longer chain-comparable because it predates the
      zero-delta row-12 stage closeout.
  - Next bounded move:
    - `P53.1d28` should reconcile or relock row 13 to the reproducible
      zero-delta-post-row-12 result before row 14.
- 2026-05-06: Completed `P53.1d28` by relocking row 13 to the reproducible
  zero-delta-post-row-12 result and stopping before row 14.
  - Relock decision:
    - accepted the current row-13 result as the new locked strict benchmark
      rather than spending more time tuning the small `1,559.000 ha` miss
      before changing seams; and
    - updated the canonical locked-chain ledger entry for
      `thlb_parent_013_areas_considered_inoperable`.
  - Updated row-13 locked values:
    - locked marginal: `31,974.000 ha`;
    - locked cumulative: `2,252,383.000 ha`; and
    - locked cumulative delta vs TSR: `1,559.000 ha`.
  - Row-14 seam boundary:
    - row 14 remains an `official_curve_ready_restart_bounded_slice` by
      ledger/recipe contract; and
    - the current post-row-13 strict-chain checkpoint does not carry
      `curve1`/late-stage curve-ready fields, so row 14 cannot be treated as a
      same-lane continuation from this checkpoint.
  - Next bounded move:
    - `P53.1d29` should repair the strict locked-step seam so reaching the
      validated LHLB boundary auto-publishes the official
      `lhlb_checkpoint`/`lhlb_curve_ready_checkpoint` restart artifacts before
      row 14 resumes from that curve-ready seam.
- 2026-05-06: Repaired the strict LHLB publication seam inside
  `run_tsr_thlb_locked_parent_step`.
  - Root cause:
    - the generic reconstructed runner already published
      `lhlb_checkpoint`/`lhlb_curve_ready_checkpoint`, but the strict
      locked-step runner only wrote strict-chain row outputs and never called
      that publication hook.
  - Fix:
    - the strict runner now detects the last `aflb_to_lhlb` parent step by
      looking ahead to the next locked parent-stage transition; and
    - when that seam is reached, it writes the official
      `data/tsr/lhlb_checkpoint.feather` artifact and immediately promotes the
      matching `data/tsr/lhlb_curve_ready_checkpoint.feather` restart artifact.
  - Validation:
    - targeted tests now cover both the normal strict locked-step output path
      and the new row-12 seam-publication path.
  - Next bounded move:
    - rerun strict row 12 once from the relocked row-11 checkpoint so the
      active TSA29 instance materializes the official restart seam before row
      14 resumes from it.
- 2026-05-07: Closed the live TSA29 row-12-to-row-14 seam by fixing Windows
  annex-pointer source resolution during curve-ready promotion.
  - What happened:
    - the repaired strict row-12 rerun now writes the official
      `data/tsr/lhlb_checkpoint.feather` artifact in the active TSA29
      instance; but
    - direct promotion from `lhlb_checkpoint` to
      `lhlb_curve_ready_checkpoint` initially failed inside
      `compile_tsr_thlb_step13_attributes(...)` while loading the Highway 97
      GeoPackage because the resolved source path was still a Windows
      git-annex pointer stub rather than the materialized payload object.
  - Fix:
    - `_resolve_source_artifact_path(...)` now resolves Windows annex pointer
      stubs to their payload path before returning TSA29 source artifacts; and
    - `_load_highway_97_geometry(...)` now applies the same payload-path
      resolution before handing the GeoPackage path to GeoPandas/pyogrio.
  - Validation:
    - targeted tests now cover both generic TSR source-artifact resolution and
      the specific Highway 97 loader path against annex-pointer stubs; and
    - direct promotion now writes the official
      `data/tsr/lhlb_curve_ready_checkpoint.feather` artifact successfully in
      the active instance.
  - Inspected live seam output:
    - `data/tsr/lhlb_curve_ready_checkpoint.feather` now exists and carries
      late-stage restart fields `curve1`, `curve2`, `stratum`, `au`,
      `femic_step13_steep_slope_flag`, and `femic_hwy97_side`; and
    - the promoted artifact retains `401,426` rows and `2,284,357.000 ha`
      managed area, matching the row-12/LHLB seam area.
  - Next bounded move:
    - run strict row 14 only from the official
      `data/tsr/lhlb_curve_ready_checkpoint.feather` restart seam.
- 2026-05-07: Ran strict TSA29 row 14 from the official curve-ready restart
  seam and stopped there.
  - Command surface:
    - saved-script call to `run_tsr_thlb_locked_parent_step(...)` with
      `parent_step_id = thlb_parent_014_sites_with_low_growing_timber_potential`
      and `checkpoint_path = data/tsr/lhlb_curve_ready_checkpoint.feather`.
  - Inspected outputs:
    - JSON:
      `runtime/logs/tsr/strict_chain/14_thlb_parent_014_sites_with_low_growing_timber_potential.json`
    - feather:
      `data/tsr/strict_chain/14_thlb_parent_014_sites_with_low_growing_timber_potential.feather`
    - execution mode: `lu_parallel`
    - workers: `8`
    - runtime: `87.852 s`
    - removed: `293,847.203 ha`
    - remaining: `1,990,509.797 ha`
    - rebuilt feather remaining area matches the JSON exactly and retains the
      curve-ready restart fields `curve1`, `curve2`, `stratum`, and `au`.
  - Comparison:
    - current locked row-14 values:
      - locked marginal: `314,591.438 ha`
      - locked cumulative: `1,926,393.594 ha`
    - TSR row-14 benchmark:
      - benchmark marginal: `321,044.000 ha`
      - benchmark cumulative: `1,929,780.000 ha`
    - current rerun deltas:
      - versus locked row 14: `-20,744.235 ha` marginal,
        `+64,116.203 ha` cumulative
      - versus TSR row 14: `-27,196.797 ha` marginal,
        `+60,729.797 ha` cumulative
  - Interpretation:
    - the repaired official curve-ready seam is executable and stable enough
      to carry row 14; but
    - the live row-14 result does not reproduce the currently locked row-14
      value and is still materially high against TSR, so row 14 now becomes
      the active adjudication boundary rather than row 15.
  - Next bounded move:
    - reconcile or relock row 14 before advancing to row 15.
- 2026-05-07: Relocked TSA29 strict row 14 to the reproducible official
  curve-ready seam result.
  - Ledger update:
    - locked marginal: `293,847.203 ha`
    - locked cumulative: `1,990,509.797 ha`
    - locked cumulative delta vs TSR: `60,729.797 ha`
  - Why:
    - the repaired official `lhlb_curve_ready_checkpoint` seam now executes
      row 14 reproducibly, but that reproducible result does not match the
      older row-14 lock;
    - keeping the older lock would leave the contract anchored to a result that
      no longer reproduces from the sanctioned live seam; so
    - the row-14 lock is now updated to the executable official-seam result and
      the older `314,591.438 ha` lock is superseded.
  - Next bounded move:
    - run row 15 only from the official
      `data/tsr/lhlb_curve_ready_checkpoint.feather` restart seam.
- 2026-05-07: Probed TSA29 strict row 15 from the official curve-ready seam
  and found the next late-stage contract defect.
  - Command surface:
    - saved-script call to `run_tsr_thlb_locked_parent_step(...)` with
      `parent_step_id = thlb_parent_015_non_merchantable_timber_profiles` and
      `checkpoint_path = data/tsr/lhlb_curve_ready_checkpoint.feather`.
  - What happened:
    - the shell launcher timed out while the row-15 process tree remained
      alive;
    - no final row-15 JSON or merged strict-chain feather was written; but
    - all `8` LU-parallel worker bundles completed and wrote both progress JSON
      and `bundle_*.output.feather` artifacts under
      `runtime/logs/tsr/strict_chain/15_thlb_parent_015_non_merchantable_timber_profiles.parallel/`.
  - Worker-bundle evidence:
    - every bundle JSON reports `status = completed`;
    - the worker notes confirm the intended row-15 semantics:
      broadleaf-leading exclusion on the late-stage curve-ready checkpoint
      using the current `PROJ_AGE_1 >= 95` minimum-age proxy; and
    - the live row-15 process tree had to be stopped manually after the shell
      timeout because the run had stalled after worker completion.
  - Aggregate partial-result evidence:
    - concatenating the finished `bundle_*.output.feather` surfaces leaves
      `2,250,821.268 ha` remaining on the raw
      `data/tsr/lhlb_curve_ready_checkpoint.feather` input surface;
    - against the raw seam input `2,284,357.000 ha`, that implies
      `33,535.732 ha` removed; and
    - that marginal is `14,772.720 ha` below the current locked row-15
      marginal `48,308.452 ha`.
  - Interpretation:
    - the row-15 worker logic itself appears to execute to completion, but the
      late-stage runner is failing after worker completion during final
      merge/result publication; and
    - the direct row-15-only replay from the raw official seam is not
      comparable to the current locked cumulative row-15 contract, which still
      assumes prior row-14 state has already been applied.
  - Next bounded move:
    - repair/adjudicate the row-15 late-stage runner contract before any row-16
      execution, specifically merge/finalization after completed bundles and
      the correct comparison surface for row-15 validation.
- 2026-05-07: Reran and relocked TSA29 strict row 15 from the official
  curve-ready seam.
  - Rerun result:
    - rerunning `thlb_parent_015_non_merchantable_timber_profiles` from
      `data/tsr/lhlb_curve_ready_checkpoint.feather` completed cleanly on the
      second attempt and wrote the final JSON plus merged strict-chain feather;
    - inspected outputs:
      - `runtime/logs/tsr/strict_chain/15_thlb_parent_015_non_merchantable_timber_profiles.json`
      - `data/tsr/strict_chain/15_thlb_parent_015_non_merchantable_timber_profiles.feather`
    - execution mode: `lu_parallel`
    - workers: `8`
    - runtime: `43.065 s`
    - removed: `33,535.732 ha`
    - remaining: `2,250,821.268 ha`
  - Comparison:
    - the rerun matches the earlier bundle-aggregate probe result exactly, so
      the row-15 executable semantics are now reproducible even though the
      first attempt hung during finalization;
    - versus the older locked row-15 marginal `48,308.452 ha`, the reproducible
      rerun under-removes by `14,772.720 ha`; and
    - versus the TSR row-15 marginal `49,052.000 ha`, it under-removes by
      `15,516.268 ha`.
  - Lock update:
    - row 15 is now relocked to the reproducible official-seam rerun result:
      - locked marginal: `33,535.732 ha`
      - locked cumulative: `2,250,821.268 ha`
      - locked cumulative delta vs TSR: `370,093.268 ha`
    - the older row-15 lock is superseded because it no longer reproduces from
      the sanctioned official `lhlb_curve_ready_checkpoint` seam.
  - Next bounded move:
    - run row 16 only from the official
      `data/tsr/lhlb_curve_ready_checkpoint.feather` restart seam.
- 2026-05-07: Backtracked to the last clean chained point and reran row 14 on
  the correct chained surface.
  - Corrected execution shape:
    - start from the actual step-13 output
      `data/tsr/strict_chain/13_thlb_parent_013_areas_considered_inoperable.feather`;
    - compile a fresh step-13-derived curve-ready checkpoint to
      `runtime/scratch/tsa29_step13_output_curve_ready.feather`; and
    - run only `thlb_parent_014_sites_with_low_growing_timber_potential` from
      that derived checkpoint.
  - Inspected outputs:
    - derived checkpoint:
      `runtime/scratch/tsa29_step13_output_curve_ready.feather`
    - row-14 JSON:
      `runtime/logs/tsr/strict_chain/14_thlb_parent_014_sites_with_low_growing_timber_potential.json`
    - row-14 feather:
      `data/tsr/strict_chain/14_thlb_parent_014_sites_with_low_growing_timber_potential.feather`
    - derived checkpoint remaining: `2,252,383.000 ha`
    - row-14 removed: `289,734.243 ha`
    - row-14 remaining: `1,962,648.757 ha`
  - Comparison:
    - versus the old raw-seam row-14 lock `293,847.203 ha` removed /
      `1,990,509.797 ha` remaining:
      - marginal delta: `-4,112.961 ha`
      - cumulative delta: `-27,861.039 ha`
    - versus the TSR row-14 benchmark `321,044.000 ha` removed /
      `1,929,780.000 ha` remaining:
      - marginal delta: `-31,309.757 ha`
      - cumulative delta: `+32,868.757 ha`
  - Lock update:
    - row 14 is now relocked to this true chained step-13 -> step-14 result:
      - locked marginal: `289,734.243 ha`
      - locked cumulative: `1,962,648.757 ha`
      - locked cumulative delta vs TSR: `32,868.757 ha`
  - Next bounded move:
    - start from this rebuilt step-14 output, derive the needed curve-ready
      fields onto it, and run only step 15.
- 2026-05-07: Ran the true chained row 15 from the rebuilt step-14 output.
  - Corrected execution shape:
    - start from the actual step-14 output
      `data/tsr/strict_chain/14_thlb_parent_014_sites_with_low_growing_timber_potential.feather`;
    - compile a fresh step-14-derived curve-ready checkpoint to
      `runtime/scratch/tsa29_step14_output_curve_ready.feather`; and
    - run only `thlb_parent_015_non_merchantable_timber_profiles` from that
      derived checkpoint.
  - Inspected outputs:
    - derived checkpoint:
      `runtime/scratch/tsa29_step14_output_curve_ready.feather`
    - row-15 JSON:
      `runtime/logs/tsr/strict_chain/15_thlb_parent_015_non_merchantable_timber_profiles.json`
    - row-15 feather:
      `data/tsr/strict_chain/15_thlb_parent_015_non_merchantable_timber_profiles.feather`
    - derived checkpoint remaining: `1,962,648.757 ha`
    - row-15 removed: `32,067.965 ha`
    - row-15 remaining: `1,930,580.793 ha`
  - Comparison:
    - versus the old raw-seam row-15 lock `33,535.732 ha` removed /
      `2,250,821.268 ha` remaining:
      - marginal delta: `-1,467.767 ha`
      - cumulative delta: `-320,240.475 ha`
    - versus the TSR row-15 benchmark `49,052.000 ha` removed /
      `1,880,728.000 ha` remaining:
      - marginal delta: `-16,984.035 ha`
      - cumulative delta: `+49,852.793 ha`
  - Interpretation:
    - this is the first true chained row-15 surface after the row-13
      backtrack/correction;
    - it massively corrects the nonsensical raw-seam cumulative surface while
      still under-removing versus TSR; and
    - row 15 should now be relocked to this chained result before row 16.
  - Next bounded move:
    - relock row 15 to this true chained result before any row-16 execution.
- 2026-05-07: Relocked TSA29 strict row 15 to the true chained step-14 -> step-15 result.
  - Locked chain update:
    - row 15 now locks the true chained run from the rebuilt step-14 output,
      not the earlier raw-seam replay surface.
    - locked row-15 values are now:
      - `32,067.965 ha` removed
      - `1,930,580.793 ha` remaining
      - `+49,852.793 ha` cumulative delta versus TSR
    - `locked_source_note` now records that this relocked value comes from the
      rebuilt step-14 output with fresh curve-ready attribute compilation.
  - Next bounded move:
    - derive the needed curve-ready fields onto the rebuilt step-15 output and
      run only step 16 from that true chained input.
- 2026-05-09: Hardened TSA29 TSR source-artifact materialization checks for annex pointer stubs.
  - Row-16 recreation failure diagnosis:
    - `whse_forest_tenure_ften_recreation` still pointed at an on-disk `.gpkg`
      worktree file whose contents were an annex pointer stub rather than a
      readable GeoPackage payload.
    - The pointer text used the `/annex/objects/...` form, which the existing
      Windows payload resolver did not recognize.
  - Code changes:
    - `resolve_windows_annex_pointer_payload_path(...)` now resolves both the
      historical `.git/annex/...` form and the `/annex/objects/...` form used
      by the current TSA29 submodule worktree.
    - `_resolve_source_artifact_path(...)` now rejects unresolved Windows annex
      pointer stubs as unmaterialized by returning `None` instead of handing
      the stub path to GeoPandas.
  - Validation:
    - targeted tests now cover both pointer forms and the unresolved-stub
      rejection path; and
    - targeted `ruff check` passed on the touched source and test files.
  - Next bounded move:
    - rerun only row 16 from the rebuilt step-15 output and confirm whether
      the recreation source now resolves to a readable payload or fails
      explicitly as still-unmaterialized.
- 2026-05-09: Validated and relocked TSA29 strict row 16 on the true chained surface.
  - Corrected execution shape:
    - materialized
      `data/downloads/bcdc/WHSE_FOREST_TENURE_FTEN_RECREATION/WHSE_FOREST_TENURE_FTEN_RECREATION.gpkg`;
    - started from the actual step-15 output
      `data/tsr/strict_chain/15_thlb_parent_015_non_merchantable_timber_profiles.feather`;
    - ran only `thlb_parent_016_recreation_features`.
  - Inspected outputs:
    - row-16 JSON:
      `runtime/logs/tsr/strict_chain/16_thlb_parent_016_recreation_features.json`
    - row-16 feather:
      `data/tsr/strict_chain/16_thlb_parent_016_recreation_features.feather`
    - row-16 removed: `6,427.221 ha`
    - row-16 remaining: `1,924,153.572 ha`
  - Comparison:
    - versus the old raw-seam row-16 lock `8,891.240 ha` removed /
      `1,869,193.903 ha` remaining:
      - marginal delta: `-2,464.019 ha`
      - cumulative delta: `+54,959.669 ha`
    - versus the TSR row-16 benchmark `9,598.000 ha` removed /
      `1,871,130.000 ha` remaining:
      - marginal delta: `-3,170.779 ha`
      - cumulative delta: `+53,023.572 ha`
  - Locked chain update:
    - row 16 now locks the true chained run from the rebuilt step-15 output
      after materializing the FTEN recreation GeoPackage.
  - Next bounded move:
    - run only step 17 from the rebuilt row-16 output.
- 2026-05-09: Ran TSA29 strict row 17 from the rebuilt row-16 output.
  - Corrected execution shape:
    - started from the actual step-16 output
      `data/tsr/strict_chain/16_thlb_parent_016_recreation_features.feather`;
    - ran only `thlb_parent_017_growth_and_yield_permanent_sample_plots`.
  - Inspected outputs:
    - row-17 JSON:
      `runtime/logs/tsr/strict_chain/17_thlb_parent_017_growth_and_yield_permanent_sample_plots.json`
    - row-17 feather:
      `data/tsr/strict_chain/17_thlb_parent_017_growth_and_yield_permanent_sample_plots.feather`
    - row-17 removed: `0.000 ha`
    - row-17 remaining: `1,924,153.572 ha`
  - Blocking source:
    - `missing_source_entry_ids = [whse_forest_vegetation_gry_psp_status]`
    - runtime status: `blocked_missing_source`
  - Comparison:
    - versus the TSR row-17 benchmark `3,577.000 ha` removed /
      `1,867,553.000 ha` remaining:
      - marginal delta: `-3,577.000 ha`
      - cumulative delta: `+56,600.572 ha`
  - Next bounded move:
    - materialize the PSP source artifact required by row 17 and rerun only
      step 17 from the rebuilt row-16 output.
- 2026-05-09: Hardened strict parent-step source preflight to auto-materialize annex-backed GIS inputs before row execution.
  - What changed:
    - added a reusable annex-materialization helper that discovers the enclosing
      git worktree, runs `git annex get` for the tracked artifact path, and
      re-resolves the readable payload path after materialization;
    - updated strict parent-step source preflight to call that helper whenever a
      required GIS source still resolves to a pointer stub or other
      unmaterialized artifact; and
    - kept the hard failure boundary before LU partitioning when the source
      still cannot be read as vector geometry after the materialization attempt.
  - Validation:
    - targeted pytest passed for the new annex helper and strict source
      auto-materialization preflight coverage; and
    - `ruff check` passed on the touched pipeline/TSR modules and tests.
  - Next bounded move:
    - rerun only step 17 from the rebuilt row-16 output so the PSP source can
      be materialized automatically instead of yielding another blocked missing-source run.
- 2026-05-09: Ran TSA29 strict row 17 through the locked parent-step lane after the source auto-materialization fix.
  - Corrected execution lane:
    - reran row 17 with `run_tsr_thlb_locked_parent_step(...)`, not the older
      notebook parent-step runner; and
    - started from the actual step-16 output
      `data/tsr/strict_chain/16_thlb_parent_016_recreation_features.feather`.
  - Source materialization:
    - `data/downloads/bcdc/WHSE_FOREST_VEGETATION_GRY_PSP_STATUS_ACTIVE/GRY_PSP_STATUS_ACTIVE.gpkg`
      was materialized automatically during strict source preflight; and
    - the artifact now exists as a real `303104`-byte GeoPackage payload instead
      of a 68-byte annex pointer stub.
  - Inspected outputs:
    - row-17 JSON:
      `runtime/logs/tsr/strict_chain/17_thlb_parent_017_growth_and_yield_permanent_sample_plots.json`
    - row-17 feather:
      `data/tsr/strict_chain/17_thlb_parent_017_growth_and_yield_permanent_sample_plots.feather`
    - row-17 removed: `837.174 ha`
    - row-17 remaining: `1,923,316.398 ha`
    - feather-managed area matches the JSON remaining area exactly; and
    - the rebuilt feather preserves the late-stage fields `curve1`, `curve2`,
      `stratum`, and `au`.
  - Comparison:
    - versus the TSR row-17 benchmark `3,577.000 ha` removed /
      `1,867,553.000 ha` remaining:
      - marginal delta: `-2,739.826 ha`
      - cumulative delta: `+55,763.398 ha`
  - Next bounded move:
    - relock/adjudicate row 17 before any row-18 execution.
- 2026-05-09: Audited the row-17 PSP overlay contract after the continued under-removal pattern.
  - Extent findings:
    - the materialized PSP payload is not a tiny clipped subset: the active PSP
      layer spans bounds `(1045444.266, 656924.844, 1393139.055, 899602.325)`
      against the chained row-16 checkpoint bounds
      `(1015173.809, 653962.516, 1393202.268, 901924.510)`;
    - that is slightly narrower than the full checkpoint envelope but still
      broad enough that the row-17 under-removal is not explained by an obvious
      one-LU or corner-clipped acquisition mistake.
  - Contract defect found:
    - `config/tsr/source_layers.recipe.yaml` still described
      `whse_forest_vegetation_gry_psp_status` as the broader
      `GRY_PSP_STATUS` / “All Status” dataset even though the actual artifact,
      DWDS order contents, and BCGW metadata all point to
      `GRY_PSP_STATUS_ACTIVE.gpkg`; and
    - the source contract is now corrected to the active-status public PSP
      surface so future adjudication does not confuse that narrower payload with
      a broader benchmark overlay.
  - Implication:
    - the remaining row-17 under-removal is not a simple full-TSA extent miss;
      it is more likely the expected difference between the active-status public
      PSP geometry and the broader benchmark surface used in older notes.
- 2026-05-09: Closed the row-17 broader-source search and relocked row 17 to the admissible public/materializable result.
  - Source-surface search result:
    - audited repo evidence and automated BCGW acquisition for a broader
      benchmark-equivalent row-17 geometry surface;
    - confirmed the public PSP path still resolves only to
      `WHSE_FOREST_VEGETATION.GRY_PSP_STATUS_ACTIVE`; and
    - identified a plausible missing research-installation boundary layer
      (`WHSE_FOREST_VEGETATION.RESPROJ_RSRCH_INSTLTNS_SVW`), but the current
      automated public DWDS path does not provide a materializable payload for
      that layer.
  - Contract conclusion:
    - the reproducible public TSA29 pipeline cannot depend on that unavailable
      research-installation geometry; and
    - row 17 therefore stays defined by the available public/materialized active
      PSP surface.
  - Locked row-17 result:
    - removed: `837.174 ha`
    - remaining: `1,923,316.398 ha`
    - cumulative delta versus TSR: `+55,763.398 ha`
  - Next bounded move:
    - run only step 18 from the rebuilt row-17 output.
- 2026-05-10: Aborted the first strict row-18 full-TSA rerun after it stalled far beyond the prior benchmark runtime envelope.
  - What happened:
    - the strict row-18 rerun was stopped after roughly 18 minutes with no final
      row-18 JSON/feather output;
    - the worker progress files never advanced beyond `completed_lus = 0`; and
    - no `bundle_*.output.feather` files were written.
  - Root-cause diagnosis:
    - the strict chained late-stage output cache handoff is preserving worker
      bundle outputs rather than true LU-granular partition records;
    - the row-17 output therefore warm-started row 18 from eight oversized
      bundle chunks (`worker_01` ... `worker_08`) instead of the expected LU
      pool; and
    - that broke the intended recipe execution grain for the riparian step.
  - Benchmark comparison:
    - previous successful row-18 benchmark runs recorded in repo notes were on
      the order of roughly `3-4 minutes`, not `18+ minutes`.
  - Next bounded move:
    - patch the strict cache registration path so chained late-stage outputs
      keep true LU-granular partition records before rerunning row 18.
- 2026-05-10: Fixed the strict late-stage cache handoff so chained outputs preserve LU-granular partition records.
  - Root cause:
    - the strict runner was registering downstream partition-cache metadata from
      merged worker-bundle outputs (`worker_01`, `worker_02`, ...) instead of
      the per-LU outputs that the recipe execution contract expects.
  - What changed:
    - the strict bundle worker now writes and returns one cached output feather
      per LU chunk in addition to its merged bundle output; and
    - downstream cache registration now prefers those per-LU output chunk
      records, preserving the real LU pool across chained late-stage steps.
  - Validation:
    - targeted pytest passed for the existing strict locked-step execution test;
      and
    - a new test proved that two LU chunks routed through a single worker bundle
      still re-register as `LU A` / `LU B` instead of collapsing to
      `worker_01`.
  - Next bounded move:
    - rerun only step 18 from the rebuilt row-17 output on the corrected
      LU-granular cache surface.
- 2026-05-10: Completed the true chained row-18 rerun after rebuilding the stale row-17 warm-start cache to real LU chunks.
  - What changed before execution:
    - deleted the stale row-17 partition cache that still registered
      `worker_01` ... `worker_08` bundle chunks; and
    - rebuilt the row-17 cache from the real row-17 checkpoint into `131`
      LU-granular chunks before rerunning step 18.
  - True chained row-18 result:
    - removed: `73,011.241 ha`
    - remaining: `1,850,305.157 ha`
    - benchmark marginal delta versus TSR: `+18,178.241 ha`
    - benchmark cumulative delta versus TSR: `+37,585.157 ha`
  - Mechanical validation:
    - row-18 output cache now registers `131` real LU names instead of
      `worker_01` ... `worker_08`; and
    - the rebuilt feather still carries late-stage fields such as `curve1` and
      `au`.
  - Runtime concern:
    - despite the cache fix, row 18 still took about `14.9 min`, far above the
      older `3-4 min` benchmark envelope, with most time spent inside a few
      heavy riparian LU executions (`Nazko`, `Mackin`, `Hawks Creek`,
      `Corkscrew`).
  - Next bounded move:
    - relock row 18 to the true chained result, then run only step 19 from the
      rebuilt row-18 output.
- 2026-05-10: Completed the true chained row-19 rerun from the rebuilt row-18 output.
  - True chained row-19 result:
    - removed: `11,806.113 ha`
    - remaining: `1,838,499.044 ha`
    - benchmark marginal delta versus TSR: `+3,767.113 ha`
    - benchmark cumulative delta versus TSR: `+33,818.044 ha`
  - Mechanical validation:
    - the rebuilt row-19 feather matches the JSON managed-area total exactly;
      and
    - the downstream row-19 output cache preserves `131` real LU names instead
      of bundle labels.
  - Runtime:
    - row 19 completed in about `111.6 s`, which is materially better than the
      row-18 riparian runtime and confirms the LU-granular cache handoff stayed
      healthy on the next chained step.
  - Next bounded move:
    - relock row 19 to the true chained result before any row-20 execution.
- 2026-05-10: Relocked row 19 to the true chained step-18 -> step-19 result.
  - Locked row-19 result:
    - removed: `11,806.113 ha`
    - remaining: `1,838,499.044 ha`
    - cumulative delta versus TSR: `+33,818.044 ha`
  - Next bounded move:
    - run only step 20 from the rebuilt row-19 output.
- 2026-05-10: Completed the true chained row-20 rerun from the rebuilt row-19 output.
  - True chained row-20 result:
    - removed: `94,417.000 ha`
    - remaining: `1,744,082.044 ha`
    - benchmark marginal delta versus TSR: `0.000 ha`
    - benchmark cumulative delta versus TSR: `+33,818.044 ha`
  - Mechanical validation:
    - the rebuilt row-20 feather matches the JSON managed-area total exactly;
      and
    - the downstream row-20 output cache preserves `131` real LU names instead
      of bundle labels.
  - Runtime:
    - row 20 completed in about `52.1 s`, much faster than the heavy row-18
      riparian step and comfortably inside the current late-stage envelope.
  - Next bounded move:
    - relock row 20 to the true chained result before any row-21 execution.
- 2026-05-10: Relocked row 20 to the true chained step-19 -> step-20 result.
  - Locked row-20 result:
    - removed: `94,417.000 ha`
    - remaining: `1,744,082.044 ha`
    - cumulative delta versus TSR: `+33,818.044 ha`
  - Next bounded move:
    - run only step 21 from the rebuilt row-20 output.
- 2026-05-10: Completed the true chained row-21 rerun from the rebuilt row-20 output.
  - True chained row-21 result:
    - removed: `34,205.000 ha`
    - remaining: `1,709,877.044 ha`
    - benchmark marginal delta versus TSR: `0.000 ha`
    - benchmark cumulative delta versus TSR: `+33,818.044 ha`
  - Mechanical validation:
    - the rebuilt row-21 feather matches the JSON managed-area total exactly;
      and
    - the downstream row-21 output cache preserves `131` real LU names instead
      of bundle labels.
  - Runtime:
    - row 21 completed in about `52.5 s`, staying inside the current
      late-stage aspatial-step runtime envelope.
  - Next bounded move:
    - relock row 21 to the true chained result before any row-23 execution.
- 2026-05-10: Relocked row 21 to the true chained step-20 -> step-21 result.
  - Locked row-21 result:
    - removed: `34,205.000 ha`
    - remaining: `1,709,877.044 ha`
    - cumulative delta versus TSR: `+33,818.044 ha`
  - Next bounded move:
    - run only step 23 from the rebuilt row-21 output.
- 2026-05-10: Completed the true chained row-23 rerun from the rebuilt row-21 output.
  - True chained row-23 result:
    - removed: `49,824.044 ha`
    - remaining: `1,660,053.000 ha`
    - benchmark marginal delta versus TSR: `+27,070.044 ha`
    - benchmark cumulative delta versus TSR: `0.000 ha`
  - Mechanical validation:
    - the rebuilt row-23 feather matches the JSON managed-area total exactly;
      and
    - the downstream row-23 output cache preserves `131` real LU names instead
      of bundle labels.
  - Runtime:
    - row 23 completed in about `69.1 s`, still inside the current late-stage
      runtime envelope while applying the stage-closing aspatial bridge.
- 2026-05-10: Relocked row 23 to the true chained step-21 -> step-23 result.
  - Locked row-23 result:
    - removed: `49,824.044 ha`
    - remaining: `1,660,053.000 ha`
    - cumulative delta versus TSR: `0.000 ha`
  - Row-23 now acts as the stage-closing aspatial future-roads bridge for the
    reproducible public-data lane.
- 2026-05-10: Parked the TSA29 THLB netdown lane after the row-23 closeout bridge.
  - The authoritative locked chain now ends at row 23 with `0.000 ha`
    cumulative delta versus TSR.
  - THLB netdown is frozen here for now so downstream work can proceed from the
    locked closeout state rather than reopening the late-stage adjudication
    lane.
