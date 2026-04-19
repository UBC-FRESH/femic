# Phase 52 TSR Reconstruction Notes

- Source: former `ROADMAP.md` lines `8702-10536`.
- Governing lane: TSR/THLB reconstruction and comparison work centered on issue `#128` and its children.

## Extracted Roadmap Notes

- 2026-04-11 (Tracker hygiene after closing `#131`):
  - `#122` now has enough delivered child work to close cleanly:
    - recipe schema/templates;
    - source-layer acquisition/build/run;
    - THLB recipe extraction and reviewed execution bridge;
    - TSA29 validation/reconciliation lane;
    - stage-aware parser/report/workbench/docs improvements; and
    - the strict reconstructed runner now finishing end to end on full TSA29.
  - Remaining open work should live under `#128`, not keep the old recipe-template umbrella artificially open.
  - `#128` should now be read narrowly:
    - the strict reconstructed lane is operational and documented;
    - the reviewed TSA29 bridge lane is still the benchmark-convergent working lane; and
    - the remaining question is why strict reconstructed THLB still lands so far below TSR.
- 2026-04-11 (`#128` should start with an explain-first comparison artifact):
  - Governing problem statement:
    - strict reconstructed full-TSA THLB currently lands at `903,685.409 ha`
      versus the TSR-reported `1,660,053.000 ha`, so the next move should be
      a parent-step comparison inventory, not another blind semantics edit.
  - First deliverable:
    - add `femic tsr thlb-reconstruction-compare` to emit
      `config/tsr/thlb_reconstruction_comparison.{md,json}` from the existing
      reviewed recipe/status and reconstructed audit/status surfaces.
  - Comparison contract:
    - group by parent step rather than compiled-step noise;
    - compare strict reconstructed vs TSR, reviewed bridge vs TSR, and strict
      vs reviewed together in the same report;
    - classify each parent-step difference using a bounded bucket set such as:
      - `close_match`;
      - `reviewed_bridge_only`;
      - `strict_overcut_candidate`;
      - `strict_undercut_candidate`;
      - `blocked_or_missing_source`;
      - `manual_or_reviewed_override`;
      - `aspatial_bridge_difference`; and
      - `not_comparable`.
  - Acceptance bar for this slice:
    - the report must make the largest strict-gap contributors obvious in
      plain language and identify whether the next corrective move should
      target reviewed bridge choices, strict overcuts, strict undercuts, or
      missing-source / blocked seams.
  - `#128` should now be read more narrowly:
    - runtime/usability of the strict reconstructed lane is solved;
    - docs/report/warm-start/fallback child work is solved; and
    - the remaining open problem is the large benchmark-reconciliation gap between the strict reconstructed THLB result and the TSR-reported THLB target.

- 2026-04-11 (`#128` comparison artifact landed on TSA29):
  - Added `femic tsr thlb-reconstruction-compare` and the new instance-local outputs:
    - `config/tsr/thlb_reconstruction_comparison.md`
    - `config/tsr/thlb_reconstruction_comparison.json`
  - The report now compares three surfaces parent-step by parent-step:
    - strict reconstructed vs TSR benchmark;
    - reviewed bridge vs TSR benchmark; and
    - strict reconstructed vs reviewed bridge.
  - The live TSA29 comparison output currently reports:
    - strict reconstructed THLB: `903,685.409 ha`
    - reviewed bridge THLB: `1,592,878.936 ha`
    - TSR reported THLB: `1,660,053.000 ha`
    - strict vs TSR delta: `-756,367.591 ha`
    - reviewed vs TSR delta: `-67,174.064 ha`
    - strict vs reviewed delta: `-689,193.528 ha`
  - The biggest current parent-step contributors are now explicit instead of hidden in chat:
    - `Non-forest` shows up as a major `reviewed_bridge_only` difference;
    - `Critical habitat for fish`, `Land not administered by the Province`, and `Wildlife habitat areas` show up as `strict_overcut_candidate` seams; and
    - `Sites with low growing timber potential` remains a `blocked_or_missing_source` contributor in the strict lane.
  - This means the next `#128` move should be chosen from this inventory rather than from another blind round of code edits.
- 2026-04-11 (`#128` comparison artifact needs engineering triage, not just buckets):
  - The current strict-vs-reviewed report identifies where the biggest gaps are, but it still does not cleanly answer the engineering question:
    - is this step wrong because FEMIC logic is too broad / too weak (`model_endogenous`)?
    - wrong because the required public data is unavailable or blocked (`data_exogenous`)?
    - different because the reviewed TSA29 lane is intentionally carrying an accepted bridge/skip/fallback (`reviewed_bridge_choice`)?
    - or genuinely mixed?
  - The next refinement to `thlb_reconstruction_comparison.{md,json}` should therefore add explicit per-parent-step fields such as:
    - `problem_ownership`
    - `difference_nature`
    - `engineering_interpretation`
    - `recommended_next_move`
  - Because `#128` is explicitly TSA29-first, it is acceptable to seed deterministic per-step interpretation overrides for the major TSA29 seams when a generic bucket alone is too vague to support decision-making.
- 2026-04-11 (`#128` engineering triage fields landed in the comparison artifact):
  - The TSA29 comparison report now persists, for each parent step:
    - `problem_ownership`
    - `difference_nature`
    - `engineering_interpretation`
    - `recommended_next_move`
  - This means the report itself now distinguishes between:
    - strict-lane logic problems we own (`model_endogenous`);
    - blocked/missing-data seams (`data_exogenous`);
    - accepted reviewed bridges/skips/fallbacks (`reviewed_bridge_choice`);
    - and genuinely mixed seams.
  - The next `#128` move should therefore be chosen from the report itself, not reconstructed from chat:
    - attack the largest `model_endogenous` seams first;
    - use `data_exogenous` seams to justify documented aspatial fallback or skip logic;
    - and leave `reviewed_bridge_choice` seams alone unless we intentionally reopen the accepted reviewed TSA29 bridge contract.
- 2026-04-11 (`#128` comparison contract correction: strict-vs-TSR comes first):
  - The report should not emotionally center strict-vs-reviewed deltas.
  - Governing interpretation order:
    - primary benchmark: strict reconstructed vs TSR;
    - secondary context: strict reconstructed vs reviewed; and
    - practical meaning: a step is a top-priority repair when strict is materially bad against TSR, not merely because strict differs from reviewed.
  - Immediate implementation follow-up:
    - add `tsr_fit_class` / `tsr_fit_interpretation` fields;
    - demote the reviewed bucket language to explanatory context;
    - add a stepwise adjudication queue that says whether to:
      - fix strict logic;
      - improve data/source coverage;
      - keep the reviewed bridge;
      - use documented aspatial fallback; or
      - defer a low-priority seam.
  - TSA29-first interpretation target:
    - step 2 should read as close enough to TSR and therefore not a top-priority repair even though reviewed is much lighter;
    - step 9 should still read as a real strict-lane problem because strict is badly high against TSR itself.
- 2026-04-11 (`#128` next phase: one-step-at-a-time adjudication pass):
  - Use `config/tsr/thlb_reconstruction_comparison.{md,json}` as the governing ledger.
  - Work parent steps in row-order sequence, one step at a time, instead of jumping between whichever seam looks most exciting.
  - For each parent step, answer in order:
    - is strict close enough to TSR already?
    - if not, is the gap mainly:
      - FEMIC logic we own;
      - missing/weak data we do not own;
      - or an accepted reviewed bridge/fallback choice?
    - what is the single next action:
      - `fix_strict_logic`
      - `improve_data_or_source`
      - `keep_reviewed_bridge`
      - `use_documented_aspatial_fallback`
      - `defer_low_priority`
  - This is an **active repair queue**, not a passive classification exercise:
    - once a step has been understood well enough to choose an action, implement that action immediately if it is actionable now;
    - only leave the step as analysis-only when the chosen action is explicitly:
      - `defer_low_priority`; or
      - a documented "wait for later" bridge/data decision such as `keep_reviewed_bridge` or `improve_data_or_source`.
  - Do not silently “fix ahead” on later steps while earlier-step interpretation is still unresolved.
  - Do not move to the next parent step after deciding `fix_strict_logic` or `use_documented_aspatial_fallback` unless the corresponding code/report change has actually been landed and checkpointed.
  - Reassess the whole-ladder read only after working through the final parent step again; that is the point where we should answer:
    - is strict THLB now close enough overall, or
    - still fundamentally “fix me” status?
- 2026-04-12 (Execution-discipline hardening after repeated scope drift):
  - For the active TSR/THLB adjudication game, `one step at a time` now means one bounded unit only:
    - one code change; or
    - one validation run; or
    - one report rebuild; or
    - one docs/issue/planning update.
  - Do **not** bundle implementation, broad rerun, and downstream validation together unless the developer explicitly asks for that bundle.
  - Before any expensive or broad command, report:
    - the exact command;
    - the one question it answers; and
    - why a smaller run is not enough.
  - After each bounded unit:
    - stop;
    - report; and
    - wait for the next instruction.
  - For this adjudication track specifically:
    - do not run downstream parent steps when the current question is about one parent step only;
    - do not launch whole-lane reruns just because they would eventually be needed; and
    - treat scope expansion as a correctness failure, not as initiative.
  - `scope breach` is the explicit stop word:
    - stop background work immediately;
    - return to the last agreed bounded unit; and
    - do not widen scope again until the developer does so explicitly.
- 2026-04-11 (`#128` strict-lane adjudication baseline artifact checkpoint):
  - The first full successful LU-wise strict-reconstructed TSA29 state should be preserved as a restart point before step-by-step adjudication begins.
  - Governing snapshot:
    - `external/femic-tsa29-instance/runtime/logs/tsr/reconstructed_lu/ria_vri_vclr1p_checkpoint1.20260411T203327Z`
  - Rationale:
    - without a tracked checkpoint of the per-step/per-LU feather outputs, a bad mid-adjudication experiment could force another ~96 minute full strict rerun just to get back to the start of the game.
  - Hygiene follow-up:
    - ignore future untracked `runtime/logs/tsr/reconstructed_lu/` scratch spill in the TSA29 submodule while keeping the tracked baseline snapshot and committed comparison artifacts as the clean adjudication starting point.
- 2026-04-11 (`#128` step 2 adjudicated):
  - Parent step:
    - `thlb_parent_002_land_not_administered_by_the_province`
  - Governing read:
    - strict removed area: `713,594.208 ha`
    - TSR benchmark marginal area: `697,033.000 ha`
    - strict-vs-TSR delta: `+16,561.208 ha`
  - Interpretation:
    - strict is close enough to TSR here for practical exploratory use even though the reviewed bridge lane is much lighter;
    - the large strict-vs-reviewed gap is not the governing benchmark for this step.
  - Adjudication action:
    - `defer_low_priority`
  - Next-move rule:
    - do not spend time tuning step 2 yet;
    - revisit only after higher-priority strict-vs-TSR seams are worked through.
- 2026-04-11 (`#128` step 3 adjudicated):
  - Parent step:
    - `thlb_parent_003_non_forest`
  - Governing read:
    - strict removed area: `1,690.701 ha`
    - TSR benchmark marginal area: `1,105,908.000 ha`
    - strict-vs-TSR delta: `-1,104,217.299 ha`
  - Interpretation:
    - this is a real seam, but not a simple “missing data” problem;
    - the strict lane is only doing the narrow direct waterbody/FMLB-style check while the reviewed lane carries a much broader non-forest bridge;
    - because reconstructed mode starts from `checkpoint1_aflb_initialization`, this early `GLB -> AFLB` stepwise delta is also a baseline-conditioned diagnostic rather than a literal raw-GLB replay.
  - Adjudication action:
    - `keep_reviewed_bridge`
  - Next-move rule:
    - do not rush into code edits for step 3 yet;
    - first decide and document the intended strict non-forest semantics, then revisit whether that bridge should stay accepted or be translated into strict logic later.
- 2026-04-11 (`#128` step 4 adjudicated):
  - Parent step:
    - `thlb_parent_004_roads_and_landings`
  - Governing read:
    - strict removed area: `0.000 ha`
    - reviewed removed area: `1,557.111 ha`
    - TSR benchmark marginal area: `50,434.000 ha`
    - strict-vs-TSR delta: `-50,434.000 ha`
  - Interpretation:
    - this is not just a case where the strict lane found no roads;
    - TSA29 section 6.2.3 explicitly says existing roads, trails, and landings are modeled non-spatially through partial AFLB reductions because the features are too small and incomplete to delineate reliably at landscape scale;
    - the current strict lane only executes the two narrow permanent-road buffer rules, and those buffers found no active LU-clipped fragments in the reconstructed run;
    - the current reviewed result is only a Williams Lake LU smoke proof, not a full-TSA bridge result, so the tiny reviewed number is not the real target either.
  - Adjudication action:
    - `use_documented_aspatial_fallback`
  - Next-move rule:
    - do not waste time tuning the current tiny spatial-only road result;
    - formalize an explicit aspatial AFLB reduction for existing roads, trails, and landings in the strict lane if we need this step to behave more like TSR.
- 2026-04-11 (`#128` step 4 implementation target locked):
  - Governing fallback target:
    - use `50,434 ha` for the strict-lane step-4 aspatial AFLB deduction.
  - Why this is the implementation target:
    - `50,434 ha` is the live `benchmark_marginal_area_ha` already parsed into the recipe and comparison ledger for `thlb_parent_004_roads_and_landings`;
    - the stepwise adjudication contract says strict-vs-TSR is the governing benchmark; and
    - the Table 6 category totals in the TSR text sum to about `50,433 ha`, which aligns with the benchmark after rounding.
  - Explicit non-target:
    - do **not** use the conflicting prose sentence `32,526 ha` as the fallback target.
  - Implementation rule:
    - formalize step 4 as a documented `aspatial_area_reduction` in the strict lane;
    - compute the remaining fallback as:
      - `max(0, 50,434 ha - exact_step4_removed_area_ha)`
    - for the current TSA29 strict run, the exact step-4 spatial substeps remove `0 ha`, so the effective fallback target is the full `50,434 ha`.
- 2026-04-11 (`#128` step 4 implemented and validated):
  - Implementation landed:
    - step 4 compiled logic now uses a documented `aspatial_area_reduction` fallback in the strict lane;
    - smoke-only approved review logic no longer freezes compiled logic during full-TSA rebuilds, so the old Williams Lake LU smoke placeholder does not override the new step-4 contract.
  - Reconstructed runner fix landed:
    - the diagnostic/resume runner now passes the TSR total-area benchmark through to `aspatial_area_reduction`, so step-only replay does not mislabel those rows as `unsupported`.
  - Step-only validation rule followed:
    - resume from the saved post-step-3 LU baseline;
    - run reconstructed diagnostic indices `3:6` only;
    - do not rerun downstream parent steps as part of step-4 validation.
  - Validated result:
    - step 4 exact road buffers still removed `0 ha`;
    - step 4 fallback removed exactly `50,434 ha`;
    - strict-vs-TSR delta for step 4 is now `0 ha`;
    - step 4 should now be treated as `defer_low_priority` instead of an active strict-lane blocker.
- 2026-04-11 (`#128` strict-lane baseline caveat for the remaining adjudication pass):
  - The current strict reconstructed lane is **not** yet a literal raw-GLB replay of the full TSA29 Table 3 ladder.
  - Current strict baseline:
    - `checkpoint1_aflb_initialization`
  - Practical consequence:
    - early `GLB -> AFLB` parent-step marginal deltas are baseline-conditioned diagnostics, not literal raw-GLB stepwise replays.
  - Working rule for the rest of the adjudication pass:
    - keep using the current strict-vs-TSR ledger to sort out stepwise strict logic/seam problems;
    - do **not** treat the current early-step marginal numbers as the final word on strict-lane correctness.
  - Required closure task before `#128` can close:
    - start the strict lane from a true raw-GLB geometry baseline;
    - rerun the full strict lane end to end from that raw GLB start;
    - confirm the resulting stepwise and cumulative behavior is sane before calling the strict lane “done”.

- 2026-04-12 (`#128` active next move: raw-GLB reset before further stepwise adjudication):
  - Pause the current one-step-at-a-time adjudication sequence here.
  - Use `data/ria_vri_vclr1p_checkpoint1.feather` as the raw geometry universe, but stop pre-filtering it into AFLB during reconstructed initialization.
  - Governing implementation order:
    - switch reconstructed initialization to `checkpoint1_raw_glb_initialization`;
    - rerun the full strict TSA29 lane from the top with the normal reconstructed command;
    - rebuild the strict-vs-TSR comparison ledger from that new run;
    - snapshot the new LU-wise strict baseline artifacts; and
    - restart adjudication from step 2 on the rebuilt ledger.
  - Do not continue adjudicating step 6+ from the old AFLB-conditioned strict run.

- 2026-04-11 (`#131` completed: LU-wise reconstructed THLB runtime is now operational on full TSA29):
  - Completion summary:
    - replaced the old reconstructed full-area row-batch exact overlay path with cached LU-wise decomposition over checkpoint1/AFLB;
    - carried LU chunk state forward through reconstructed steps so only touched chunks are re-cut;
    - kept explicit reconstructed aspatial fallback from `#132` working in the same lane;
    - added reconstructed timing summaries so the live audit/status surfaces show total runtime, timing buckets, and the slowest steps in plain language; and
    - completed the real production command `femic tsr thlb-netdown-run --execution-mode reconstructed` on full TSA29 without silent stand-binary fallback.
  - Governing full-TSA result:
    - runtime finished in about `96.09 min`;
    - exact fragment-overlay steps: `17`;
    - explicit aspatial fallback steps: `2`;
    - blocked exact-overlay steps: `0`;
    - debug stand-binary fallback steps: `0`;
    - LU-wise exact-overlay chunks touched: `1025`; and
    - final reconstructed THLB managed area: `903685.409 ha`.
  - Important plain-language read:
    - the strict geometry-first reconstructed lane is now operationally usable;
    - it is still slower than the reviewed TSA29 bridge lane, but it no longer dies on the old step-002 wall; and
    - the next performance question, if it ever matters again, is optional LU-bundled parallelization rather than basic viability.

- 2026-04-11 (Issue `#131` active again: LU-wise exact decomposition for reconstructed THLB runtime closure):
  - Objective:
    - keep the reviewed TSA29 parent-step lane untouched;
    - make the strict reconstructed lane finish in practical time by cutting the land base one Landscape Unit at a time instead of trying to cut the whole TSA at once; and
    - close `#131` with a real full-TSA reconstructed run rather than leaving it parked on timeout evidence.
  - Implementation direction:
    - reuse the existing LU partition/cache helpers already proven in the parent-step lane;
    - initialize checkpoint1/AFLB once, materialize cached LU chunk files once, and then carry those chunk files forward as the reconstructed step state;
    - for each spatial `exclude` step, load only the LU chunks touched by the exclusion geometry and run exact overlay inside those chunks instead of building one full-TSA candidate set;
    - preserve exactness by clipping per LU, keeping `SOURCE_FEATURE_ID` lineage, and regenerating global `FEATURE_ID` values only when merged output is written;
    - keep reconstructed explicit aspatial fallback from `#132` working in the same lane without auto-converting blocked spatial rows into fallback.
  - Acceptance target:
    - reconstructed tests prove LU-wise exact overlay returns the same binary THLB result as the current exact row-batch path on controlled inputs;
    - TSA29 reconstructed smoke still completes with exact overlay and no silent stand-binary fallback; and
    - the real full-TSA reconstructed run completes with practical wall time, clear audit/status reporting, and enough evidence to close `#131`.

- 2026-04-11 (Issue `#132` active: add explicit aspatial fallback for blocked THLB target-area steps in reconstructed mode only):
  - Objective:
    - keep the reviewed TSA29 parent-step/notebook lane unchanged;
    - fill the missing seam in `femic tsr thlb-netdown-run --execution-mode reconstructed` so recipe rows already compiled as `aspatial_reduction` or `aspatial_area_reduction` execute honestly instead of remaining outside the reconstructed runnable set; and
    - keep fallback explicit, recipe-driven, and visibly separate from exact spatial overlay.
  - Implementation direction:
    - expand reconstructed runnable actions from `use_land_base`, `no_deduction`, and `exclude` to also include `aspatial_reduction` and `aspatial_area_reduction`;
    - reuse the existing aspatial reduction helpers already used by the reviewed parent-step lane instead of inventing a second deduction path;
    - label those reconstructed rows as `aspatial_fallback` in runtime/audit/status surfaces;
    - do not auto-convert blocked spatial `exclude` rows into fallback unless the recipe row itself is already compiled as aspatial; and
    - keep `manual_review_required` and `reference_only` rows non-executable.
  - Acceptance target:
    - reconstructed tests prove `aspatial_reduction` and `aspatial_area_reduction` now execute in reconstructed mode;
    - reconstructed audit/status reporting separates exact overlay, explicit aspatial fallback, blocked exact overlay, debug stand-binary fallback, and no-deduction rows; and
    - a TSA29 reconstructed smoke run shows explicit aspatial fallback steps where the reviewed recipe already carries them, without changing the practical reviewed TSA29 lane.
- 2026-04-11: Issue `#132` is complete.
  - Reconstructed THLB now executes recipe rows already compiled as:
    - `aspatial_reduction`
    - `aspatial_area_reduction`
  - The change is intentionally narrow:
    - reconstructed runner only;
    - no reviewed parent-step/notebook lane behavior changed; and
    - blocked spatial `exclude` rows are still not auto-converted into fallback.
  - Reconstructed audit/status reporting now separates:
    - exact fragment overlay;
    - explicit `aspatial_fallback`;
    - blocked exact overlay; and
    - debug stand-binary fallback.
  - TSA29 reconstructed smoke proof:
    - `femic tsr thlb-netdown-run --instance-root external/femic-tsa29-instance --execution-mode reconstructed --auto-map-id-smoke-subset`
      completed successfully on `MAP_ID 092O071`;
    - smoke result recorded:
      - `fragment_overlay_step_count = 12`
      - `aspatial_fallback_step_count = 1`
      - `aspatial_fallback_area_ha = 297.242`
      - `blocked_exact_overlay_step_count = 0`
      - `stand_binary_fallback_step_count = 0`
    - live reconstructed status/audit surfaces now show the fallback bucket explicitly without presenting it as exact spatial reproduction.

- 2026-04-11 (Issue `#136` active: add no-LLM THLB warm-start checklist templates from recurring TSR netdown patterns):
  - Objective:
    - keep the current THLB recipe/status/workbench surfaces as canonical reviewed state;
    - add one explicit no-LLM warm-start artifact pair:
      - editable YAML template under `config/tsr/`; and
      - plain-language checklist Markdown under `workbench/tsr/`;
    - seed the first version from a bounded packaged THLB motif library rather than a broad corpus-mining engine.
  - Implementation direction:
    - reuse the existing stage-aware parent-step structure, exact-logic summaries, source-linkage state, and override state already carried by the reviewed THLB recipe;
    - classify each parent step into a small fixed warm-start status set (`compiled_ready`, `review_pattern_match`, `blocked_missing_source`, `manual_or_aspatial`, `no_pattern_match`);
    - match recurring motifs deterministically from current parent-step fields such as stage, candidate operation type, candidate layers/fields/values, execution class, and linked source status;
    - keep the new checklist/template explicitly non-canonical so it never auto-promotes into executable THLB logic.
  - Acceptance target:
    - `femic tsr thlb-netdown-warmstart-build --instance-root external/femic-tsa29-instance`
      emits:
      - `config/tsr/thlb_warmstart.yaml`; and
      - `workbench/tsr/thlb_netdown.warmstart.md`;
    - TSA29 late-step examples like steps `013`, `014`, `018`, `021`, and `023` render with plain-language review guidance that matches current accepted FEMIC state.
- 2026-04-11: Issue `#136` is complete.
  - Added a packaged bounded motif library at
    `src/femic/resources/tsr/thlb_warmstart_patterns.yaml`.
  - Added deterministic warm-start generation over the reviewed THLB recipe in
    `src/femic/tsr_catalog/recipes.py`, with CLI wiring for:
    - `femic tsr thlb-netdown-warmstart-build --instance-root PATH`
  - Default warm-start outputs are now:
    - `config/tsr/thlb_warmstart.yaml`
    - `workbench/tsr/thlb_netdown.warmstart.md`
  - The warm-start pair is explicitly non-canonical:
    - canonical executable THLB logic remains
      `config/tsr/thlb_netdown.recipe.yaml`
  - TSA29 acceptance result:
    - `femic tsr thlb-netdown-warmstart-build --instance-root external/femic-tsa29-instance`
      emitted the paired artifacts successfully;
    - emitted counts:
      - `milestone_count = 4`
      - `parent_step_count = 20`
      - `warmstart_status_compiled_ready = 11`
      - `warmstart_status_manual_or_aspatial = 9`
    - refreshed TSA29 review surfaces now point to
      `workbench/tsr/thlb_netdown.warmstart.md`
      without promoting it into canonical THLB logic.

- 2026-04-10 (Issue `#138` active: add a Windows ArcGIS Pro review-project
  emit command for FEMIC instances):
  - Objective:
    - emit a ready-to-open ArcGIS Pro `.aprx` plus manifest for an existing
      FEMIC instance so a human can inspect downloaded GIS layers and local
      context layers visually without hand-loading them one by one.
  - Implementation plan for this slice:
    - add `femic prep arcgis-review-project --instance-root PATH` with
      optional `--output-dir` and `--project-name`;
    - reuse the existing ArcGIS Pro Python resolution/execution seam already
      used by SiteProd fallback instead of duplicating `propy.bat`
      discovery logic in an ad hoc script;
    - generalize the TSA29 prototype script into core code that discovers
      reviewable `.shp` / `.gpkg` layers from the instance, applies simple
      deterministic naming/order/transparency defaults, and emits:
      - one `.aprx`;
      - one manifest JSON; and
      - helper `.lyrx` files under the same output root;
    - keep v1 intentionally review-oriented:
      - all layers default to `visible = off`;
      - no auto-launch of ArcGIS Pro; and
      - no change to FEMIC's canonical processing pipeline.
  - Acceptance target:
    - unit/CLI tests cover layer discovery, classification, manifest shaping,
      and clean ArcGIS-missing failure messages; and
    - a real Windows/ArcGIS Pro TSA29 run emits a usable project bundle whose
      manifest matches the loaded layers.
- 2026-04-10 (Issue `#138` implemented: FEMIC can now emit a ready-to-open
  ArcGIS Pro review project for an instance):
  - Delivered command surface:
    - added `femic prep arcgis-review-project --instance-root PATH` with
      optional `--output-dir` and `--project-name`;
    - reused the shared ArcGIS Pro Python runner seam now centralized in
      `src/femic/arcgis_pro.py`; and
    - kept the feature explicitly review-only rather than introducing a new
      GIS processing backend.
  - Review-project behavior:
    - discover instance-local `.shp` / `.gpkg` layers under `data/` and
      `output/`;
    - skip smoke-scoped cached BCDC overlays under
      `data/downloads/bcdc/smoke`;
    - emit a manifest-backed `.aprx` plus helper `.lyrx` files under the
      chosen output root;
    - keep all layers off by default at launch; and
    - stage GeoPackage layers as helper shapefiles inside the emitted bundle
      when ArcGIS Pro compatibility requires it.
  - Acceptance result on TSA29:
    - a real Windows/ArcGIS Pro run emitted
      `runtime/logs/arcgis_review_acceptance_tsa29_clean/tsa29_arcgis_review_20260410c.aprx`
      and the matching manifest JSON;
    - the project included `79` layers;
    - the command skipped `3` smoke-scoped cached BCDC artifacts; and
    - `77` GeoPackage-backed review layers were staged into the emitted bundle
      so ArcGIS Pro could load them reliably.

- 2026-04-10 (Issue `#139` active: model TSA29 section `7.1.5`
  broadleaf-volume exclusions as a later post-TIPSY yield assumption):
  - Governing split:
    - THLB step `015` stays exactly what TSA29 section `6.4.5` says it is:
      exclude broadleaf-leading stands from THLB area;
    - TSA29 section `7.1.5` is a separate later yield assumption, not a THLB
      polygon-removal rule.
  - Implementation plan for this slice:
    - add one narrow `yield_assumptions_path` seam to `tsa post-tipsy`,
      `tsa btc-post-tipsy`, and `modes.yield_assumptions_path`;
    - default to `config/tsr/yield_assumptions.yaml` under the instance root
      when present, otherwise do nothing;
    - after `build_bundle_tables_from_curves(...)` and before
      `write_bundle_tables(...)`, inspect untreated species-proportion sidecar
      curves, identify conifer-leading untreated AUs with non-zero broadleaf
      share, scale the untreated total curve by the conifer share, zero the
      untreated broadleaf sidecars, and renormalize the remaining untreated
      conifer sidecars to sum to `1.0`;
    - leave treated curves untouched and keep the rule completely separate
      from THLB step `015`;
    - record adjusted AUs, broadleaf share used, total untreated volume
      removed, and the config path in the post-TIPSY manifest.
  - Acceptance target:
    - rerun TSA29 `post-tipsy` / `btc-post-tipsy`, inspect the regenerated
      bundle tables directly, and confirm only the intended untreated
      conifer-leading mixed AUs changed while THLB step `015` notes still read
      as broadleaf-leading area exclusion only.
- 2026-04-10 (Issue `#139` implemented: TSA29 broadleaf-volume exclusions now
  run in the post-TIPSY bundle lane instead of the THLB netdown lane):
  - Added the narrow `yield_assumptions_path` seam to:
    - `femic tsa post-tipsy`;
    - `femic tsa btc-post-tipsy`; and
    - `modes.yield_assumptions_path` in run-profile YAML.
  - Default behavior now auto-loads `config/tsr/yield_assumptions.yaml` from
    the instance root when it exists, otherwise post-TIPSY behaves exactly as
    before.
  - Implemented the TSA29 section `7.1.5` rule after bundle assembly and
    before bundle-table write:
    - detect conifer-leading untreated AUs from untreated species-proportion
      sidecars;
    - remove the broadleaf share from the untreated total curve;
    - zero untreated broadleaf species-proportion sidecars; and
    - renormalize the remaining untreated conifer sidecars to `1.0`.
  - Manifest/report evidence now records:
    - the assumptions config path;
    - adjusted AU ids and stratum labels;
    - untreated broadleaf/conifer shares; and
    - total untreated volume removed.
  - TSA29 proving-ground result:
    - `femic tsa btc-post-tipsy --instance-root external/femic-tsa29-instance --run-config config/run_profile.tsa29.yaml --tsa 29 --run-id issue139_btc_post_tipsy_20260410a`
      completed successfully;
    - the broadleaf-volume rule adjusted `6` untreated AUs:
      `IDF_FD H`, `SBPS_PL M`, `SBPS_PL H`, `SBPS_SX H`, `SBS_SX M`, and
      `SBS_SX H`;
    - manifest summary recorded `69,020.56` untreated volume removed; and
    - a scratch no-assumption comparison confirmed the treated curves for all
      adjusted AUs were unchanged while the untreated curves differed exactly
      where expected.
  - THLB boundary remained intact:
    - TSA29 step `015` wording in `config/tsr/thlb_netdown.status.md` still
      describes only the broadleaf-leading stand area exclusion and continues
      to defer section `7.1.5` to the later yield-assumption lane.

- 2026-04-10 (Issue `#140` active finish pass: wire DWDS follow-up back into
  the TSR source-layer recipe runner):
  - Current state:
    - the DWDS helper seam is already real and live-proven in
      `src/femic/bcdc_dwds.py`;
    - `femic data bcdc-order-followup` already reloads saved manifests, retries
      the public status seam, falls back through `pickupByGUID`, and
      materializes the recovered artifact; but
    - `femic tsr source-layers-run` still stops at `ordered` for `dwds_order`
      entries and does not automatically reuse those saved manifests on rerun.
  - Finish-pass target:
    - persist one instance-relative `order_manifest_path` per DWDS-backed
      source-layer recipe entry;
    - teach `run_tsr_source_layers_recipe(...)` to follow up an existing saved
      manifest before considering any new submission;
    - promote recovered artifacts back into `artifact_path` automatically and
      mark the entry `materialized`;
    - keep `--allow-order` narrow so it only gates new DWDS submission; and
    - reconcile roadmap / issue state so `P52.6b4` matches the real code state
      after the TSR integration seam is finished.
- 2026-04-10 (Issue `#140` finished: TSR source-layer reruns now reuse saved
  DWDS manifests instead of stopping at `ordered`):
  - Added per-entry `order_manifest_path` persistence for DWDS-backed
    source-layer recipe entries.
  - `run_tsr_source_layers_recipe(...)` now does this in order for
    `dwds_order` entries:
    - reuse an already materialized local artifact if the saved manifest still
      points at one;
    - otherwise follow up the saved DWDS manifest automatically and promote any
      recovered artifact back into `artifact_path`;
    - only submit a new DWDS order when no saved manifest exists and
      `--allow-order` is explicitly enabled.
  - Source-layer runner statuses are now honest about the DWDS lifecycle:
    - `ordered`
    - `followup_pending`
    - `materialized`
  - TSA29 proving-ground confirmation:
    - a scratch source-layer recipe built from the real PSP case and a real live
      DWDS manifest advanced cleanly to `materialized` without a new order
      submission and recovered
      `data/downloads/bcdc/WHSE_FOREST_VEGETATION_GRY_PSP_STATUS_ACTIVE/GRY_PSP_STATUS_ACTIVE.gpkg`.

- 2026-04-06 (Issue `#140` opened: improve DWDS follow-up retrieval and
  artifact materialization after order submission):
  - Proven live seam:
    - FEMIC successfully submitted a clipped DWDS order for TSA29 step `017`
      (`WHSE_FOREST_VEGETATION.GRY_PSP_STATUS_ACTIVE`) and received
      `order_id=2551251`;
    - the public `/order/{id}` probe still reported the known false-negative
      "order does not exist" response; and
    - the missing piece is now clearly post-submission retrieval/materialization,
      not order creation.
  - Immediate implementation target:
    - persist enough structured DWDS follow-up state that FEMIC can retry
      retrieval without re-submitting blindly;
    - probe for stronger post-submission seams than the current fragile
      `/order/{id}` endpoint; and
    - feed any recovered artifact path back into TSR source-layer and THLB
      workflows so DWDS-backed steps like TSA29 step `017` can become runnable.
- 2026-04-06 (Issue `#141` opened: full-TSA29 THLB retest and recipe
  reconciliation after the Williams Lake LU ratchet pass):
  - The single-LU work is now pre-validation evidence only; the next hardening
    pass must rerun the currently executable TSA29 ladder on the full dataset
    against the canonical 2024 Table 3 marginal/cumulative benchmarks.
  - Scope for `#141`:
    - rerun every executable transformation row in canonical Table 3 order
      while preserving milestone rows as non-runnable nodes;
    - keep the established stage split:
      - `GLB -> AFLB` on checkpoint1-style land-base surfaces; and
      - `AFLB -> LHLB -> THLB` on the curve-ready pre-legacy-THLB checkpoint;
    - treat current LU soft approvals as candidate confirmations rather than
      final acceptance; and
    - emit one explicit full-run validation summary under `config/tsr/`
      recording per-step full-TSA benchmark comparison, disposition, and
      AFLB/THLB lock readiness.
  - Full-TSA validation must explicitly confirm:
    - early-stage area deductions like step `023` still recompute from stable
      canonical area and only overwrite `FEMIC_EFFECTIVE_AREA_SQM`;
    - later-stage exclusions preserve geometry/fragments and lower
      harvestability in place (`thlb_fact` / `thlb = 0`);
    - and steps should only be reopened when full-TSA evidence materially
      misses the TSR benchmark or exposes a semantic error the LU smoke could
      not reveal.
  - Immediate reconciliation subtask:
    - refresh the BC-wide `WHSE_ADMIN_BOUNDARIES.FADM_TSA` artifact from the
      BC Data Catalogue, then use that fresh TSA boundary to rebuild the TSA29
      masked 2024 VRI stand universe from the BC-scale VRI source;
    - compare the resulting fresh GLB proxy against:
      - the current full-TSA29 GLB proxy already being used in `#141`; and
      - the TSR Table 3 total TSA area benchmark;
    - use that comparison to decide whether the current ~`225k ha` GLB excess
      is coming from a stale/incorrect TSA mask seam or from a deeper VRI/input
      surface mismatch.
  - Current decision checkpoint:
    - the refreshed `FADM_TSA` Williams Lake dissolve is effectively exact
      against the TSR Table 3 total (`4,933,664.338 ha` vs `4,933,635 ha`);
    - the current full-TSA post-step-23 AFLB remains `2,905,358.090 ha`, about
      `152,147.910 ha` low relative to the implied Table 3 benchmark
      (`3,057,506 ha`);
    - the exact reason the individual `GLB -> AFLB` marginal rows do not line
      up remains unresolved, but the resulting AFLB is close enough overall to
      count as "good enough" for TSA29 validation; and
    - treat the early full-TSA `GLB -> AFLB` pass as green-lit and move the
      active `#141` work down into `AFLB -> LHLB` / `LHLB -> THLB` validation.
- 2026-04-06 (Issue `#143` opened: LU-wise local-process parallel THLB
  benchmark side quest):
  - Motivation:
    - full-TSA THLB step validation under `#141` is currently too slow for
      rapid recipe iteration on this workstation; and
    - we need a contained answer to whether exact LU-clipped decomposition plus
      local multi-process execution can materially shorten the feedback loop
      without changing THLB semantics.
  - Scope for `#143`:
    - keep GeoPandas/Shapely as the GIS engine;
    - prototype a Windows-first local `ProcessPoolExecutor` backend;
    - clip the active working geometry to LU boundaries so every worker gets a
      disjoint exact spatial slice;
    - benchmark only the expensive spatial step classes:
      - `004 Roads and landings`;
      - `007 Old growth management areas`;
      - `018 Riparian areas`; and
      - `019 Buffered trails`;
    - compare serial vs LU-parallel runtime, parity, and basic memory signals
      on the current workstation with worker counts `1`, `2`, `4`, `8`; and
    - decide whether the feature is worth keeping before touching the main
      `#141` validation lane.
  - Guardrails:
    - no centroid/map-sheet stand assignment heuristics;
    - no ArcGIS backend revival after the closed `#142` benchmark result;
    - do not adopt the feature if LU-parallel merge-back changes removed area,
      remaining area, or later-stage `thlb_fact` / `thlb` semantics beyond a
      very small tolerance; and
    - keep the side quest on its own feature branch so any experimental mess
      can be abandoned cleanly if the benchmark result is negative.
- 2026-04-06 (Issue `#143` prototype landed: LU-wise local-process parallel
  THLB benchmark harness and backend toggle):
  - Implementation status:
    - added an experimental LU-parallel execution mode to the THLB parent-step
      runner using local `ProcessPoolExecutor` workers, with explicit
      `serial` vs `lu_parallel` mode selection and optional worker-count
      control;
    - added LU clipping helpers that split the active working geometry into
      disjoint landscape-unit slices before dispatch;
    - added a new benchmark entrypoint:
      - `femic tsr thlb-netdown-parallel-benchmark`
    - added benchmark result artifacts under:
      - `runtime/logs/tsr/parallel_benchmarks/`
    - kept GeoPandas/Shapely as the only GIS engine in scope for this side
      quest.
  - Validation status:
    - regression coverage was added for LU-parallel parity on a controlled
      fixture plus benchmark-summary generation;
    - validation gates passed:
      - `pytest tests/test_tsr_recipes.py tests/test_cli_main.py -q`
      - `ruff check src/femic/tsr_catalog/recipes.py src/femic/tsr_catalog/__init__.py src/femic/cli/main.py tests/test_tsr_recipes.py tests/test_cli_main.py`
      - `mypy src`
      - `sphinx-build -b html docs _build/html -W`
  - First live benchmark signal:
    - benchmarked step `004` (`Roads and landings`) on the `Williams Lake` LU;
    - serial result:
      - runtime about `71.0 s`
      - removed area `1470.416 ha`
    - LU-parallel (`2` workers) result:
      - runtime about `75.2 s`
      - removed area `1388.719 ha`
      - parity failed relative to serial
    - current interpretation:
    - the prototype is real and benchmarkable;
    - the current partial-LU path is not yet adoption-worthy; and
    - the parity drift likely reflects the difference between exact LU
      clipping in the parallel path and the current non-clipped serial LU
      subset reference, so any further benchmark claims need to use a cleaner
      reference contract (ideally full-TSA/all-LU).
- 2026-04-06 (Issue `#143` next slice: grouped-LU chunking plus notebook
  progress UX for full-TSA step-6 testing):
  - Immediate motivation:
    - one-LU-per-chunk granularity is not obviously delivering enough speedup;
    - the live 4-LU tests show the `lu_parallel` path itself is internally
      stable across `1`, `2`, and `4` workers; and
    - the next meaningful experiment is full-TSA step `006`
      (`Parks, protected areas, area-base tenures`) with `8` grouped LU bundles
      and visible progress reporting in the notebook.
  - Planned implementation:
    - add a grouped-LU bundle mode on top of the current LU-clipped chunk
      preparation so the runner can partition the active LU set into a smaller
      number of worker bundles (for example `8`) instead of one worker task per
      LU;
    - keep the chunk contract exact by grouping already-clipped LU slices,
      rather than reverting to centroid or map-sheet heuristics;
    - add optional progress reporting backed by per-worker progress files so the
      parent process and generated notebook can render one progress bar per
      worker bundle;
    - regenerate the TSA29 THLB workbench notebook so step `006` can be launched
      from the notebook using the grouped-LU `8`-worker path.
  - Guardrails:
    - do not claim parity or performance success until the full-TSA grouped
      benchmark is compared against the matching grouped/clipped serial
      reference;
    - keep the notebook progress UX optional and degrade cleanly to plain-text
      notes if widget support is unavailable.
- 2026-04-06 (Issue `#143` follow-up: step-6 tenure semantics note plus
  profiling-first optimization pass):
  - Tenure follow-up to preserve:
    - step `006` still lacks validated automation logic for the "small
      area-based tenures and woodlots" portion even though fetched public
      tenure-adjacent layers are already on disk;
    - likely next seam is to mine BC Data Catalogue metadata/dictionaries for:
      - `TA_CROWN_TENURES_SVW`;
      - `WHSE_TANTALIS.TA_CROWN_TENURES_SVW`; and
      - `WHSE_FOREST_TENURE.FTEN_MANAGED_LICENCE*_SVW`
      to find defensible field/value logic for the missing tenure classes; and
    - keep the current step-6 parks/protected-areas automation separate from
      that still-unresolved tenure sublogic.
  - Immediate profiling mission:
    - collect structured timing for the grouped-LU full-TSA step-6 path so we
      can separate:
      - LU-partition materialization/cache time;
      - worker feather/shard load time;
      - worker GIS execution time;
      - worker output-write time; and
      - parent-process merge/readback time;
    - use that profile to decide whether the next optimization should be:
      - preloading/caching larger LU bundles once before step 6;
      - reducing repeated shard reads by caching bundle-ready datasets; or
      - keeping the notebook kernel hot with preloaded data if file I/O turns
        out to dominate runtime.

- 2026-04-06 (Issue `#140` checkpoint landed: DWDS follow-up/materialization
  no longer stops at submission):
  - Added a manifest-driven follow-up lane in `src/femic/bcdc_dwds.py`:
    - reload existing DWDS order manifests;
    - retry the public order-status seam later; and
    - materialize the artifact into a download root when DWDS exposes a
      download URL.
  - Added CLI command:
    - `python -m femic data bcdc-order-followup ORDER_MANIFEST`
    - default behavior updates the saved manifest in place with:
      - `latest_followup_utc`;
      - `latest_followup_status_probe`;
      - `materialized_artifact_path` / bytes / content type when available; and
      - explicit follow-up warnings when the public seam still withholds a
        download URL.
  - Live TSA29 PSP follow-up result:
    - the original DWDS submission (`order_id=2551251`) is now re-probeable
      from FEMIC instead of being a dead-end manifest;
    - the public `/order/{id}` seam still returns the known false negative; and
    - FEMIC now records that state honestly in the manifest instead of stopping
      at raw submission metadata.
- 2026-04-06 (Issue `#140` email fallback added for live DWDS orders):
  - `femic data bcdc-order` now resolves the DWDS notification email in this
    order:
    - explicit `--email`;
    - `FEMIC_BCDC_DWDS_EMAIL`; then
    - `git config user.email`.
  - If none of those sources are available, FEMIC now fails early with a clear
    instruction instead of silently submitting a no-email order.
  - Live validation:
    - submitted a fresh PSP order for the TSA29 `Williams Lake` LU without
      `--email`;
    - FEMIC picked up the local git email and the order summary now reports
      `email: 0@01101.io`;
    - new order manifest:
      `runtime/logs/bcdc_psp_status_active_williams_lake_order_manifest_with_email.json`.
- 2026-04-06 (Issue `#142` closed: ArcGIS Pro THLB benchmark completed and not
  adopted):
  - The ArcGIS Pro subprocess side-quest was benchmarked head-to-head against
    the canonical GeoPandas/Shapely lane on the `Williams Lake` LU subset.
  - Results on this workstation:
    - step `003` (`Non-forest`):
      - GeoPandas about `18.4 s`;
      - ArcGIS about `145.5 s`;
      - output parity close enough to count as parity.
    - step `004` (`Roads and landings`):
      - GeoPandas about `70.0 s`;
      - ArcGIS about `190.4 s`;
      - ArcGIS still landed in `applied_with_unsupported` because one
        road-buffer substep failed.
    - steps `018` (`Riparian areas`) and `019` (`Buffered trails`):
      - GeoPandas completed in about `22.6 s` and `24.0 s`;
      - ArcGIS did not complete either step within an eight-minute timeout and
        had to be terminated manually.
  - Decision:
    - keep GeoPandas/Shapely as the canonical THLB GIS execution engine;
    - do not merge the ArcGIS experimental backend into the main THLB branch;
    - treat `#142` as answered `not worth extending` for now and return focus
      to `#141`.
- 2026-04-06 (Issue `#140` pickup-by-GUID retrieval seam discovered and wired
  into FEMIC follow-up):
  - Live TSA29 PSP order `2551234` proved the stronger public retrieval path:
    - DWDS sent an email saying the order was assembled;
    - the emailed `pickupByGUID` URL was an HTML launcher page, not the final
      package; and
    - that launcher page exposed the real
      `distribution.data.gov.bc.ca/...zip` URL for the assembled artifact.
  - FEMIC now mirrors that path in `follow_up_bcdc_dwds_order(...)`:
    - retry `/order/{id}` first;
    - if no download URL is exposed and `order_guid` exists, fetch the
      `pickupByGUID` launcher page;
    - parse the launcher HTML for the final distribution zip URL; then
    - download/materialize the artifact and record both URLs in the manifest.
  - User/agent-facing documentation must now treat DWDS notification email as
    part of the usable public-order workflow, not just as an optional courtesy,
    because the email-driven launcher may be the only discoverable route to the
    final package when `/order/{id}` is still unreliable.

- 2026-04-06 (Issue `#139` opened: split TSA29 step `015` area netdown from
  TSR Section `7.1.5` later yield-assumption logic):
  - The active TSA29 interpretation is now explicit:
    - `6.4.5 Non-merchantable timber profiles` stays in the THLB area-netdown
      lane only for the rule:
      - exclude **broadleaf-leading stands** from THLB;
    - `7.1.5 Volume exclusions for broadleaf species in coniferous stands`
      does **not** stay in the THLB area-netdown lane;
      it becomes a separate later-stage yield/volume assumption after AU
      compilation and VDYP/TIPSY/yield preparation.
  - Immediate follow-through:
    - keep TSA29 step `015` in the notebook/workbench ratchet flow as the
      broadleaf-leading-stand THLB exclusion only;
    - do not fold mixed conifer-stand deciduous-volume handling back into the
      THLB area-netdown recipe;
    - implement the `7.1.5` volume-exclusion logic under GitHub issue `#139`
      once the remaining THLB area-netdown steps are sorted out.

- 2026-04-03 (Issue `#83` reconciled and ready to close: Windows Codex local-link recovery docs were already landed):
  - GitHub issue `#83` no longer reflects missing implementation work; the
    requested Windows VS Code/Codex recovery guidance is already present in the
    current repo surfaces:
    - `AGENTS.md`
    - `README.md`
    - `docs/guides/vscode-coding-agent-onboarding.rst`
    - `docs/guides/case-onboarding.rst`
    - `docs/guides/deployment-instances.rst`
  - The shipped guidance already covers:
    - the maintained `codex-local-file-link-patch` repo;
    - the Windows-only scope of the workaround;
    - the PowerShell patch command; and
    - the post-patch `Developer: Reload Window` step.
  - Immediate follow-through:
    - post a closeout comment on GitHub issue `#83` pointing to the existing
      docs and close the issue as tracker reconciliation rather than new code
      or docs work.

- 2026-04-03 (Issue `#11` implemented: Windows `validate-case` now diagnoses
  canonical TSA FileGDB materialization before blaming GDAL):
  - What shipped:
    - extended the existing Windows annex/runtime seam inside
      `femic prep validate-case` instead of adding a new CLI command;
    - added a lightweight canonical TSA FileGDB layer probe against
      `external/femic-public-data/data/bc/tsa/FADM_TSA.gdb`;
    - the new helper now distinguishes:
      - missing geospatial backends (`pyogrio` / `fiona`);
      - missing or empty canonical FileGDB payloads;
      - pointer-like annex worktree exposure inside the FileGDB; and
      - generic read failures that still need the annex/materialization
        recovery sequence ruled out first;
    - the emitted Windows error path now points operators to the exact
      low-noise recovery sequence:
      - `git -C external/femic-public-data annex enableremote arbutus-s3`
      - `datalad get -r external/femic-public-data/data`
      - `git -C external/femic-public-data annex unlock data/bc/tsa/FADM_TSA.gdb`
      - rerun `femic prep validate-case`
    - `femic prep geospatial-preflight` stayed generic, while the Windows
      geospatial/runtime docs now explicitly explain that `validate-case` is
      the case-aware canonical TSA/FileGDB readability check and that ArcGIS
      Pro / `arcpy` is only a fallback recovery leg.
  - Validation:
    - focused CLI/runtime tests passed for the new Windows annex/FileGDB seam;
    - full docs-contract coverage passed after updating the Windows guides;
    - full repo validation passed:
      - `python -m ruff format src tests`
      - `python -m ruff check src tests`
      - `python -m mypy src`
      - `python -m pytest -q`
      - `python -m sphinx -b html docs _build/html -W`
      - `python -m pre_commit run --all-files`
  - Immediate follow-through:
    - post the implementation/validation closeout to GitHub issue `#11`;
    - close `#11` if no new Windows FileGDB scope is added in review.

- 2026-04-03 (Issue `#11` kickoff: diagnose canonical Windows TSA FileGDB
  materialization before users chase fake GDAL ghosts):
  - Governing issue:
    - GitHub issue `#11`
  - Planned branch:
    - `feature/issue-11-windows-filegdb-materialization`
  - Root-cause read for this pass:
    - the misleading Windows `FADM_TSA.gdb` failures are not automatically
      proof that GDAL/FileGDB support is broken on Windows;
    - on the known workstation, the more common seam is annex-backed
      `external/femic-public-data` worktree materialization, where the
      canonical TSA geodatabase can still present pointer-like/unusable content
      until the public-data checkout is properly materialized and unlocked;
    - `femic prep geospatial-preflight` should remain the generic
      package/runtime smoke, while `femic prep validate-case` should become the
      low-noise place to detect the active-case canonical TSA FileGDB seam.
  - Active implementation target:
    - extend the existing Windows annex/runtime helper inside
      `femic prep validate-case` rather than adding a new CLI command;
    - probe the canonical TSA boundary geodatabase with a lightweight layer-list
      read and distinguish:
      - missing geospatial libraries;
      - missing/unmaterialized annex payload;
      - pointer-like/unusable worktree exposure; and
      - genuine FileGDB read failure;
    - fail with the exact recommended recovery sequence:
      - `git -C external/femic-public-data annex enableremote arbutus-s3`
      - `datalad get -r external/femic-public-data/data`
      - `git -C external/femic-public-data annex unlock data/bc/tsa/FADM_TSA.gdb`
      - rerun `femic prep validate-case`
    - keep ArcGIS Pro / `arcpy` as documentation-only fallback guidance.
  - Validation target:
    - add focused regression tests for the new Windows FileGDB materialization
      seam inside `validate-case`;
    - update the Windows/bootstrap docs to distinguish
      `geospatial-preflight` from active-case FileGDB readability;
    - run the full lint/type/test/docs/pre-commit sweep once the narrow helper
      and docs are in place.

- 2026-04-03 (Issue `#80` validated and closeout-ready):
  - Delivered exactly the narrow layout split planned at kickoff:
    - durable VDYP runtime assets stay at `vdyp_io/VDYP.INI` and
      `vdyp_io/VDYP_CFG/**`;
    - disposable per-batch raw spill now lands under `vdyp_io/scratch/`;
    - VDYP-specific event/stdout evidence stays under `vdyp_io/logs/`.
  - Closeout evidence:
    - focused runtime-layout regressions passed;
    - full lint/type/test/docs/pre-commit gates passed;
    - direct TSA29 inspection now shows a clean `vdyp_io/` root with the old
      raw spill relocated into `vdyp_io/scratch/`.
  - Immediate follow-through:
    - checkpoint the branch commits and submodule pointers;
    - post the implementation/validation closeout on GitHub issue `#80` and
      close it if no further scope is added.

- 2026-04-03 (Issue `#80` active implementation: move raw VDYP batch spill,
  not the durable runtime contract):
  - Immediate execution order:
    - update the roadmap/changelog first and keep `#80` as the governing issue;
    - refactor the VDYP batch temp-file creation path so raw `.csv/.out/.err`
      spill lands in a dedicated scratch directory instead of the top-level
      `vdyp_io/` root;
    - leave `vdyp_io/VDYP.INI`, `vdyp_io/VDYP_CFG/**`, and the existing
      evidence-bearing log surfaces intact in this pass;
    - update instance bootstrap, tests, and docs/contracts to describe the new
      durable-runtime-versus-disposable-scratch boundary;
    - directly inspect the live TSA29 `vdyp_io/` tree after the code change so
      the fix is verified on a real representative instance rather than only in
      unit tests.

- 2026-04-03 (Issue `#81` rescue-guard fix validated):
  - Narrow scope delivered exactly as planned:
    - late `fit_quality_gate` rescue now considers only candidates that earlier
      policy stages actually accepted/selected;
    - raw rejected `tail_blend` no longer re-enters rescue comparison just
      because it clears `early_overshoot_exceeds_gate`.
  - Validation outcome for this pass:
    - focused regression coverage now locks the failure seam where
      `tail_blend_selection` rejects a worse tail curve and the final selected
      path must stay off `tail_blend`;
    - accepted-candidate rescue remains covered by the existing
      `merchantable_floor` rescue regression;
    - replaying the saved clean-clone TSA29 evidence through the live repo code
      now keeps both `ICH_SX / M` and `ICH_SX / H` on `primary_nlls` with
      `selected_curve_gate_unresolved` instead of rescuing to `tail_blend`.
  - Immediate follow-through:
    - run the full lint/type/test/docs gates;
    - post the validation closeout to GitHub issue `#81` and close it if the
      full repo gates stay green.

- 2026-04-03 (Issue `#81` active implementation: rescue guard, not broad tail retune):
  - Root-cause read for this pass:
    - the known TSA29 `ICH_SX / M` and `ICH_SX / H` mis-selections are not
      being caused by the earlier `tail_blend_selection` step;
    - in the saved clean-clone evidence, `tail_blend_selection` already rejects
      the raw `tail_blend` candidate for both cases, but the later
      `fit_quality_gate` rescue still revives raw `tail_blend` because it
      clears `early_overshoot_exceeds_gate`.
  - Active implementation target:
    - keep the issue narrow to the late rescue-candidate set;
    - allow gate rescue to consider only candidates that earlier policy stages
      actually accepted/selected;
    - do not broaden this pass into a general retune of tail-detection,
      tail-blend thresholds, or fit-quality gate constants.
  - Validation target for this pass:
    - add focused regression coverage for "rejected tail_blend must not be
      revived by gate rescue";
    - preserve at least one accepted-candidate gate-rescue path;
    - replay the saved TSA29 `ICH_SX / M` and `ICH_SX / H` evidence through the
      live repo code and confirm the final selected path no longer ends at
      `tail_blend`.

- 2026-04-03 (Issue `#82` closeout; issue `#81` is the next active VDYP follow-on):
  - Issue `#82` is now closeout-complete:
    - the polygon/layer batch writer was repaired so VDYP input CSVs now keep
      only the shared `FEATURE_ID` set and preserve stable within-feature layer
      ordering;
    - saved-batch replay confirmed the old bad TSA29 `ESSF_SE / H` sample no
      longer collapses to a one-table parse after the alignment fix;
    - narrow bucket rerun confirmed `ESSF_SE / H` now rebuilds as a plausible
      full smoothed curve instead of the broken near-two-point fallback.
  - Next active issue is `#81`:
    - focus now shifts from the batch-alignment seam to the fit-selection
      policy seam;
    - the intended next pass is to tighten rescue selection so
      `tail_blend` cannot replace a materially better primary/current fit just
      to satisfy the early-overshoot gate.

- 2026-04-03 (Issue `#82` active implementation: VDYP polygon/layer batch alignment):
  - Root-cause read for this pass:
    - the broken TSA29 `ESSF_SE / H` curve is currently traced to the sampled
      VDYP input-writer seam, not to stratum sizing;
    - the saved bad batch had `100` polygon rows but only `95` unique matching
      layer `FEATURE_ID`s, and the first polygon row had no corresponding layer
      row before VDYP consumed the batch.
  - Active implementation target:
    - repair `write_vdyp_infiles_plylyr(...)` so FEMIC only writes
      feature-aligned polygon/layer batches to VDYP;
    - preserve deterministic per-feature ordering for multi-layer rows instead
      of relying on an unstable generic sort;
    - add focused regression coverage for missing-layer and duplicated-layer
      cases so the sampled TSA29 failure shape stays reproducible in tests.
  - Validation target for this pass:
    - rerun the relevant narrow TSA29 Stage 01a bucket after the writer fix;
    - confirm `ESSF_SE / H` no longer degenerates into the broken near-two-point
      fallback curve and that AU `23009` regains a plausible VDYP overlay.

- 2026-04-03 (Issue `#79` follow-on VDYP bug split after plot QA):
  - The BTC/null-volume seam targeted by issue `#79` is now fixed and the
    Windows annex-raster blocker from the same clean-clone rerun is also
    resolved, but direct review of the regenerated TSA29 VDYP QA plots exposed
    two separate follow-on VDYP defects that should be handled outside issue
    `#79`:
    - issue `#82`: sampled VDYP polygon/layer temp files can become misaligned
      when polygons without matching layer rows are written into the same batch,
      collapsing healthy strata such as `ESSF_SE / H`;
    - issue `#81`: the fit-quality rescue policy can replace a materially better
      primary/current fit with a much worse `tail_blend` curve just to satisfy
      the early-overshoot gate (for example `ICH_SX / M` and `ICH_SX / H`).
  - Current closeout read on issue `#79`:
    - the original BTC acceptance criteria are satisfied;
    - the newly split VDYP bugs are real and worth fixing, but they do not
      reopen the repaired BTC natural-ingress contract itself;
    - issue `#79` should be treated as closeout-ready once its final closeout
      note explicitly links the two follow-on VDYP bug tickets.

- 2026-04-03 (Windows annex-pointer raster follow-up after issue `#79` validation):
  - The clean-clone TSA29 rerun exposed a narrower Windows-only public-data seam
    beyond the earlier missing-path fallback work:
    - `datalad get` / `git annex get` can still leave annexed raster worktree
      paths as tiny pointer stub files on native Windows submodule checkouts;
    - direct `rasterio.open(...)` against those worktree paths fails even when
      the real annex payload exists in the object store.
  - The intended fix for this pass is intentionally narrow:
    - add a Windows-only resolver for annex pointer-style raster paths;
    - use it only at the direct raster-open seams (`misc.thlb.tif`,
      canonical `siteprod.tif`);
    - leave Linux behavior unchanged and avoid broad new environment policy.
  - Completion evidence:
    - added a Windows-only annex-pointer resolver that maps tiny worktree stub
      files to the real annex payload under the submodule gitdir before direct
      raster opens;
    - wired that resolver into the THLB and SiteProd raster-open seams only;
    - confirmed the earlier failing clean-clone command now passes the old THLB
      blocker and completes:
      `femic run --instance-root external/femic-tsa29-instance --run-config config/run_profile.tsa29.yaml --run-id tsa29_issue79_windows_annexfix_20260403b`
      from `F:\projects\tmp\femic-issue10-closeout-20260402-clean`.

- 2026-04-03 (Issue `#79` implementation + fresh BTC/post-TIPSY validation):
  - Share audit result:
    - the problematic TSA29 `planted_percent < 100` rows were **not** caused by
      random arithmetic drift;
    - fresh `03_input-tsa29.csv` values such as `30`, `85`, and `90` trace
      directly to explicit `config/tipsy/tsa29.yaml` `Proportion` assignments,
      so the mixed-share behavior is currently treated as deliberate TSA29
      compile logic.
  - BTC seam fix now in place:
    - `build_btc_msyt_input_table()` now pairs the planted-side `f` payload with
      the matching natural-side `e` payload when emitting BTC `MSYT.csv`;
    - rows with `planted_percent < 100` now receive explicit
      `natural_species*` / `natural_density*` fields;
    - FEMIC now fails fast before BTC if a mixed-share row lacks a usable
      natural-ingress payload.
  - Fresh validation evidence from rerun `tsa29_issue79_20260403a` in
    `F:\projects\tmp\femic-issue10-closeout-20260402-clean`:
    - regenerated `03_input-tsa29.csv` now shows the old problem rows carrying
      real natural-ingress payload (for example `21000` / `22000` now include
      `natural_species1=Pl`, `natural_density1=871`, `natural_species2=At`,
      `natural_density2=100`);
    - fresh unattended BTC plus `femic tsa btc-post-tipsy` completed
      successfully against that regenerated handoff;
    - fresh `04_error-tsa29.csv` is now header-only;
    - fresh `04_output-tsa29.csv` now has `54/54` rows with positive
      non-null `gVol_*` output and `0` all-null rows.
  - Remaining validation caveat:
    - the full clean-clone `femic run` command still hit an unrelated THLB
      fallback-raster open failure in
      `F:\projects\femic\external\femic-public-data\data\misc.thlb.tif` after
      Stage 01a had already regenerated the canonical BTC handoff;
    - that raster-format issue did **not** block the issue-79 seam proof
      because the fresh Stage 01a outputs plus `femic tsa btc-post-tipsy`
      rerun were sufficient to validate the repaired BTC contract end to end.

- 2026-04-03 (Issue `#79` active implementation: mixed-share TSA29 BTC contract):
  - Root-cause audit now points at the BTC handoff seam rather than stale
    provenance or random arithmetic drift:
    - the fresh failing BTC rows in clean-clone `03_input-tsa29.csv` carry
      `planted_percent` values such as `30`, `85`, and `90`;
    - those values match explicit TSA29 rule `Proportion` settings already
      encoded in `config/tipsy/tsa29.yaml` (`0.30`, `0.85`, `0.90`) rather than
      an apparent downstream accounting error;
    - the current issue-79 working assumption is therefore that mixed-share
      planted input is deliberate TSA29 compile logic, but FEMIC exports it
      incompletely for BTC.
  - Active implementation target:
    - preserve the intended mixed-share TSA29 behavior;
    - repair the BTC export so any row with `planted_percent < 100` also carries
      explicit natural-ingress species/density payload;
    - fail fast before BTC if FEMIC is about to emit a mixed-share row without
      usable natural-ingress fields.
  - Validation target for this pass:
    - regenerate fresh `03_input-tsa29.csv`;
    - rerun the clean TSA29 BTC/post-TIPSY chain;
    - prove the 21 previously failing feature IDs no longer hit fresh
      `Natural has no Species` errors, or else document a narrower remaining
      contract gap explicitly before any further TSA29 prototype claims.

- 2026-04-03 (Issue #10 fresh-clone closeout achieved; follow-on moves to `#79`):
  - Fresh validation closeout completed from:
    - source workspace: `F:\projects\femic`
    - clean validation clone:
      `F:\projects\tmp\femic-issue10-closeout-20260402-clean`
    - shared public-data mirror:
      `F:\projects\femic\external\femic-public-data\data`
  - Clean-clone bootstrap and validation notes:
    - rebuilt the moved clean-clone `.venv` from scratch instead of trusting the
      migrated virtual environment;
    - restored only the minimal TSA29-local prerequisites needed for the clean
      rerun (`tipsy_params_columns`, `tsa_boundaries.feather`,
      `ria_vri_vclr1p_checkpoint1..8.feather`);
    - removed stale downstream TSA29 runtime products before rerun so the final
      evidence chain stayed single-lineage and auditable;
    - found a real packaging gap during the clean rerun and added `openpyxl` to
      `pyproject.toml` and `requirements.txt` because Stage 01a and tests write
      `tipsy_params_tsa29.xlsx`.
  - Fresh closeout run `tsa29_issue10_closeout_20260402f` now proves:
    - `femic prep validate-case --instance-root external/femic-tsa29-instance --run-config config/run_profile.tsa29.yaml`
      passed in the clean clone;
    - `femic prep geospatial-preflight` passed in the clean clone;
    - `femic run` emitted fresh `03_input-tsa29.csv` and Stage 01a/01b runtime
      artifacts;
    - unattended BTC completed with `exit_code=0` and wrote fresh
      `04_output-tsa29.csv` / `04_error-tsa29.csv`;
    - `femic tsa btc-post-tipsy` completed with fresh
      `tipsy_curves_tsa29.csv`, `tipsy_sppcomp_tsa29.csv`,
      `data/model_input_bundle/*`, and fresh `plots/tipsy_vdyp_tsa29-*.png`;
    - `femic export patchworks`, `femic patchworks build-blocks --with-topology --topology-backend patchworks-raster`,
      and `femic patchworks matrix-build --run-id tsa29_issue10_closeout_20260402f`
      all completed successfully in the clean clone;
    - the regenerated topology file
      `models/tsa29_patchworks_model/blocks/topology_blocks_200r.csv` is now
      non-empty (`29,954,243` bytes; `1,266,753` topology edges);
    - the fresh Matrix Builder manifest records `returncode=0`,
      `failures=[]`, inherited
      `SPS_LICENSE_SERVER=frst424@auth.spatial.ca`, and the output-local
      validated XML path beside the matching fragments set.
  - Fresh-provenance null-volume resolution:
    - the apparent TSA29 null/no-volume pattern is **not** stale artifact
      confusion;
    - fresh `04_output-tsa29.csv` contains `54` rows total, with `33` rows
      showing positive `gVol_*` output;
    - the remaining `21` all-null `gVol_*` rows line up exactly with fresh
      `04_error-tsa29.csv` rows reporting `Natural has no Species`;
    - there were no additional all-null volume rows outside that fresh BTC
      error set.
  - Closeout consequence:
    - issue `#10` can close as a rebuild-contract, provenance, and evidence
      closeout;
    - the remaining TSA29 v0 behavior investigation moves to follow-on issue
      `#79` (`TSA29 v0: investigate fresh BTC null-volume rows with "Natural has no Species" errors`).
  - Immediate next task:
    - use issue `#79` as the active surface for root-causing the fresh
      `Natural has no Species` subset and repairing the affected TSA29 BTC
      inputs without reopening issue `#10`.
  - Windows public-data hygiene follow-up:
    - local testing in `external/femic-public-data` showed Windows false-dirty
      churn was being amplified by `core.autocrlf=true` against annex-managed
      GIS payloads;
    - committed `external/femic-public-data` submodule fix `155711f`
      (`Harden binary GIS attributes for Windows clones`) to mark FileGDB
      payloads plus raster/feather/GPKG artifacts as binary (`-text`) in
      `.gitattributes`;
    - parent merge work should advance the public-data submodule pointer to
      `155711f` together with the existing TSA29 pointer update, but must still
      keep the large TSA29 runtime spill out of the intentional Git payload.
  - TSA29 merge-hygiene follow-up:
    - committed `external/femic-tsa29-instance` submodule fix `1b9a3cb`
      (`Ignore transient VDYP raw output spill`) to ignore the largest
      throwaway `vdyp_io` raw-output families
      (`vdyp_err_*.err`, `vdyp_lyr_*.csv`, `vdyp_out_*.out`,
      `vdyp_ply_*.csv`);
    - that change cut the TSA29 Git-visible worktree noise from roughly
      `7,886` files to `179` files without hiding the JSON evidence manifests;
    - remaining TSA29 dirt is now concentrated in still-meaningful runtime
      artifacts (`data/*`, `plots/*`, fragments, manifests, and local
      `VDYP_CFG` / `VDYP.INI`) rather than the transient raw spill.
    - follow-on issue `#80` now tracks redesigning the `vdyp_io` layout so the
      essential local runtime assets (`VDYP_CFG`, `VDYP.INI`) no longer live in
      the same directory as thousands of transient raw VDYP spill files that
      need periodic cleanup on Windows.
  - Non-VDYP runtime-log split:
    - redirected non-VDYP run/manifests/rebuild-report defaults from
      `vdyp_io/logs` to `runtime/logs` in the parent CLI/workflow defaults and
      in the TSA29/K3Z instance configs/docs;
    - moved the current TSA29 non-VDYP runtime artifacts (BTC manifests/logs,
      post-TIPSY run manifests, Patchworks matrix-builder manifests/logs) out
      of `vdyp_io/logs` into `runtime/logs`;
    - left true VDYP event/stdout logging under `vdyp_io/logs`, keeping
      `VDYP.INI` / `VDYP_CFG` untouched as essential runtime assets.

- 2026-04-02 (Issue #10 BTC-first TSA29 migration checkpoint):
  - Completed in this branch:
    - added repo-local planning note `planning/tsa29_p19_5_btc_reentry.md`;
    - updated the Phase 19 `P19.5` wording so issue `#10` now tracks the
      BTC-first rebuild/evidence closeout explicitly;
    - migrated the linked TSA29 instance docs/runbook/spec/runtime wiring so
      the active contract is now `03_input-tsa29.csv` -> unattended BTC ->
      `04_output-tsa29.csv` / `04_error-tsa29.csv` ->
      `femic tsa btc-post-tipsy`;
    - repaired the stale TSA29 Patchworks runtime config so it no longer points
      at K3Z model paths;
    - added the smallest necessary parent blocker fix so `femic instance rebuild`
      can honor a TSA29 spec that declares `btc_post_tipsy_bundle` instead of
      silently forcing the old legacy `post_tipsy_bundle` step;
    - refreshed docs/CLI contract tests to match current FMU-first wording and
      current checked-in K3Z artifact reality on `origin/main`.
  - Validation completed:
    - `python -m pytest tests/test_cli_main.py -k "instance_rebuild"`
    - `python -m pytest tests/test_docs_contract.py -k "tsa29"`
    - `python -m sphinx -b html docs _build/html -W`
    - `python -m sphinx -b html external/femic-tsa29-instance/docs external/femic-tsa29-instance/docs/_build/html -W`
    - `ruff format src tests`
    - `ruff check src tests`
    - `mypy src`
    - `pytest`
    - `pre-commit run --all-files`
  - Immediate next execution order:
    - checkpoint only the permanent contract/runtime/doc fixes, keeping large
      TSA29 runtime spill out of the intentional Git payload;
    - prove fresh-seam provenance explicitly for one final closeout run:
      `03_input-tsa29.csv` -> fresh BTC `04_output-tsa29.csv` /
      `04_error-tsa29.csv` -> fresh post-TIPSY curves/bundle/plots;
    - treat blank/null BTC output as a blocker, and treat any remaining
      fresh-provenance no-volume plot pattern as a follow-on TSA29 v0 issue
      rather than widening `#10` into a full behavior investigation;
    - run the final acceptance/evidence pass from a fresh/current FEMIC
      checkout using the approved Windows Patchworks contract:
      inherited `SPS_LICENSE_SERVER`, output-local validated XML/fragments,
      `patchworks-raster` topology backend, and successful Matrix Builder
      completion with `returncode=0`.

- 2026-04-02 (Issue #10 Patchworks + provenance checkpoint):
  - Current synced-workspace evidence now proves:
    - TSA29 Patchworks Matrix Builder succeeds when FEMIC inherits the real
      Windows `SPS_LICENSE_SERVER` value instead of overriding it with the old
      placeholder runtime config value;
    - TSA29 Matrix Builder must point at
      `output/patchworks_tsa29_validated/forestmodel.xml` beside the matching
      validated fragments, not at stale model-local
      `models/tsa29_patchworks_model/yield/forestmodel.xml`;
    - the reviewed `plots/tipsy_vdyp_tsa29-*.png` family in this forensic
      workspace was regenerated immediately after the fresh
      `tsa29_btc_boundary_smoke_20260402b` BTC-first run chain, not from the
      old historical DAT/out seam.
  - Verified current-workspace provenance chain:
    - `data/03_input-tsa29.csv` mtime `2026-04-02 01:34:59`
    - `data/04_output-tsa29.csv` / `data/04_error-tsa29.csv` mtimes
      `2026-04-02 01:37:17`
    - `data/tipsy_curves_tsa29.csv` mtime `2026-04-02 01:37:27`
    - `plots/tipsy_vdyp_tsa29-*.png` mtimes `2026-04-02 01:37:27` through
      `2026-04-02 01:37:34`
    - BTC manifest `tsa29_btc_boundary_smoke_20260402b_tsa29` records
      `TIPSYbtc.exe /TSR` consuming fresh `03_input-tsa29.csv` and returning
      fresh `04_output-tsa29.csv` / `04_error-tsa29.csv`
    - post-TIPSY manifest `tsa29_btc_boundary_smoke_20260402b` records fresh
      `tipsy_curves_tsa29.csv`, `tipsy_sppcomp_tsa29.csv`, and rebuilt bundle
      tables from the same run lineage.
  - Remaining closeout move:
    - repeat this same proof from a fresh/current checkout and use that run as
      the final issue-`#10` closeout evidence.

- 2026-04-02 (Issue #10 F-drive re-ground + clean validation plan):
  - Live workspace sanity check now confirms:
    - source repo root: `F:\projects\femic`
    - fresh validation checkout:
      `F:\projects\tmp\femic-issue10-closeout-20260402-clean`
    - both repos are on `work/p19.5-tsa29-btc-reentry`
    - the intended shared public-data mirror for
      `FEMIC_EXTERNAL_DATA_ROOT` remains
      `F:\projects\femic\external\femic-public-data\data`
  - Immediate execution order from this point:
    - finish editable bootstrap in the fresh validation checkout so
      `python -m femic` resolves from its local `.venv`;
    - restore only the missing TSA29-local prerequisite files needed for the
      clean closeout chain from the source workspace into the fresh clone;
    - remove stale downstream TSA29 runtime products in the fresh clone before
      the rerun so provenance stays single-lineage and auditable;
    - rerun `validate-case`, `geospatial-preflight`, the BTC-first TSA29 chain,
      and the Patchworks closeout steps from the clean checkout;
    - inspect the rebuilt BTC/TIPSY manifests and outputs explicitly to decide
      whether the apparent null-volume pattern is fresh behavior or stale-mix
      confusion before touching issue `#10` closure state.

- 2026-04-02 (Issue #10 BTC-first TSA29 re-entry plan):
  - Governing issue:
    - GitHub issue `#10`
  - Branch:
    - `work/p19.5-tsa29-btc-reentry`
  - Re-entry decision:
    - retire the stale TSA29 closeout framing built around the old manual
      BatchTIPSY DAT/out seam;
    - treat the freshly synced parent `origin/main` BTC workflow as the
      authoritative contract;
    - use the preserved pre-sync TSA29 backup snapshot as the forensic source
      for selective carry-forward only, without relying on any stale `C:`
      checkout paths.
  - Approved execution sequence:
    - migrate the TSA29 instance docs/runbook/spec/runtime wiring so the active
      seam is:
      - `data/03_input-tsa29.csv`
      - unattended BTC
      - `data/04_output-tsa29.csv`
      - `data/04_error-tsa29.csv`
      - `femic tsa btc-post-tipsy --run-config config/run_profile.tsa29.yaml --tsa 29 --run-id <id>`
    - keep legacy `02_input-tsa29*.dat` / `04_output-tsa29.out` references as
      historical or compatibility context only;
    - make only the smallest necessary parent-code blocker fixes if the current
      `origin/main` rebuild runner cannot honor the BTC-first TSA29 contract;
    - after migration, run the final acceptance/evidence pass from a fresh
      current FEMIC checkout rather than from the old forensic workspace.
  - Immediate execution order:
    - patch `ROADMAP.md`, `CHANGE_LOG.md`, and
      `planning/tsa29_p19_5_btc_reentry.md` so the approved re-entry plan lives
      in-repo and matches the updated GitHub issue `#10`;
    - migrate the linked TSA29 instance surfaces:
      `README.md`, `docs/getting-started.rst`,
      `docs/rebuild-and-qa.rst`, `docs/data-and-provenance.rst`,
      `docs/troubleshooting.rst`, `runbooks/REBUILD_RUNBOOK.md`,
      `config/rebuild.spec.yaml`, and
      `config/patchworks.runtime.windows.yaml`;
    - validate the migrated contract with focused docs/spec checks plus a
      targeted BTC-boundary smoke before attempting the final clean rebuild
      closeout.

- 2026-03-30 (Issue #65 kickoff): start the narrow K3Z ctfert log-grade harvested product/account rollout on branch `feature/issue-65-k3z-ctfert-log-grades`.
  - Governing issue:
    - GitHub issue `#65`
  - Rollout scope:
    - only `ctfert_l15h5`
    - only `ctfert_l20h0`
    - CC harvested product/account family only
    - no CT log-grade surfaces yet
    - no broader rollout to baseline, `pct_*`, `intensive_*`, or generalized treated surfaces yet
  - Immediate execution order:
    - wire the existing BTC `log-grades` bank into the shared Patchworks exporter only as far as needed for the two ctfert variants;
    - request the bank explicitly from the two ctfert silviculture configs;
    - rebuild the affected validated ForestModel XMLs before rerunning Matrix Builder on the two ctfert variants;
    - inspect rebuilt `products.csv`, `protoaccounts.csv`, and `accounts.csv` directly to confirm all expected grade members are present as CC-only families;
    - finish with one representative Patchworks smoke that schedules harvest volume and shows the new saved runtime log-grade family in concrete outputs.
- 2026-03-30 (Issue #65 progress): the narrow ctfert log-grade rollout is working end to end.
  - Shared exporter support now emits `product.Logs_Grade_{D,F,H,I,J,U,X,Y,All}.managed.Total.CC` only for the two active ctfert variants, and the adapter layer now loads `Logs_Grade_*` curves from the K3Z BTC export.
  - The two ctfert silviculture configs now request the existing BTC `log-grades` bank, `data/tipsy_curves_tsak3z.csv` now carries the `Logs_Grade_*` columns, and the rebuilt `tracks_ctfert_l15h5/` and `tracks_ctfert_l20h0/` products/protoaccounts/accounts surfaces now contain the full nine-member CC-only family.
  - The initial ctfert runtime smoke failure was traced to missing `headless_runtime_common.bsh` hooks in `analysis/ctfert_l15h5.pin` and `analysis/ctfert_l20h0.pin`; after restoring that shared headless contract, `femic patchworks run-headless ...ctfert_l15h5.pin --scenario-mode max-even-flow-smoke --run-id issue65_ctfert_loggrades_runtime_rerun` completed successfully.
  - Representative live runtime proof now exists at:
    - `external/femic-k3z-instance/vdyp_io/logs/headless_stage/issue65_ctfert_loggrades_runtime_rerun/targets/product_Logs_Grade_H_managed_Total_CC.csv`
    - `external/femic-k3z-instance/vdyp_io/logs/headless_stage/issue65_ctfert_loggrades_runtime_rerun/targets/product_Logs_Grade_D_managed_Total_CC.csv`
    proving that materially populated and zero-only CC log-grade surfaces are both saved at runtime and that no matching `...CT` log-grade products were introduced in this slice.
- 2026-03-31 (Issue #65 semantics correction): reopen the ctfert log-grade rollout on the same feature branch to repair the bank contract before final closeout.
  - Current interpretation issue:
    - raw BTC inspection shows `Logs_Grade_D/F/H/I/J/U/X/Y` behave like a partition of merchantable `Yield`, while `Logs_Grade_All` is a distinct scaled-log quantity that can exceed `Yield`;
    - carrying `Logs_Grade_All` as a peer product account in the additive K3Z harvested family is therefore misleading.
  - Immediate correction order:
    - add a generic bank compile-recipe seam in FEMIC, starting with a recipe-backed `log-grades` bank;
    - make the default log-grade recipe exclude `Logs_Grade_All`, but support an explicit `include_all_grades` opt-in when a model really wants it;
    - add user-tweakable per-grade ratio weights and normalize them inside FEMIC so users can shift grade shares without changing net harvested volume;
    - add treatment-specific ratio overrides so K3Z CT can deliberately favor `J/U/X/Y` material in line with early-age thinning from below and the BC coast grading manual's small-radius/utility/chipper grades;
    - keep the shipped reference recipe inside FEMIC and merge an optional user overlay from `~/.femic/recipe-overlays`;
    - apply the same harvested-volume utilization multiplier to the emitted log-grade harvested product accounts so the grade family sums to effective harvested volume rather than raw merchantable yield;
    - push the repaired recipe through the broader affected K3Z family, not just the two ctfert variants, so natural-origin harvest surfaces participate too;
    - finish with a harvest-producing headless smoke that confirms saved runtime grade-family totals line up with harvested-volume totals in concrete output files.
- 2026-03-31 (Issue #65 semantics correction closeout): the repaired compile-recipe
  contract is now in place and validated end to end.
  - The shipped reference recipe now excludes `Logs_Grade_All` by default, keeps
    an explicit opt-in path for that separate scaled-log metric, exposes
    user-tweakable ratio weights plus user overlay support, and normalizes the
    explicit grade family so it sums to `product.HarvestedVolume.*` instead of
    raw BTC merchantable yield.
  - K3Z runtime semantics are now deliberately split by treatment:
    - `CC` continues to follow the normalized BTC-derived grade mix;
    - `CT` now uses recipe-backed ratio overrides to bias harvested material
      toward `J/U/X/Y` small-log and utility/chipper classes in line with the
      BC coast grading manual and the teaching-instance "thinning from below"
      rationale.
  - The rebuilt broader K3Z family now carries the repaired contract through
    both managed and natural-origin harvest surfaces, and the representative
    ctfert runtime proof at
    `external/femic-k3z-instance/vdyp_io/logs/headless_stage/issue65_loggrade_ctfert_runtime_ctoverride`
    confirms:
    - some harvest occurs;
    - explicit `CT` and `CC` grade files are saved at runtime;
    - grade-family totals track harvested-volume totals within small rounding
      noise; and
    - `CT` output now shows a clearly lower-grade mix concentrated in
      `J/U/X/Y`.
  - Final validation is green:
    - `python -m ruff format src tests`
    - `python -m ruff check src tests`
    - `python -m mypy src`
    - `python -m pytest`
    - `python -m pre_commit run --all-files`
    - `python -m sphinx -b html docs _build/html -W`
    - `python -m sphinx -b html docs docs/_build/html -W` from the standalone
      K3Z docs root.
- 2026-03-31 (Issue #65 scope expansion parked): the next log-grade phase is now
  defined but intentionally parked while `main` is pushed and cleaned up.
  - Reopened issue `#65` and widened the follow-on scope to include:
    - AU-wise, species-wise log-grade harvested product/account splits;
    - user-overridable species x log-grade price surfaces built from the 2025
      coast market reports attached on the issue; and
    - derived value-account families that multiply AU/species/log-grade volume
      by the price matrix so users can aggregate upward with
      `duplicateAccount()` inside Patchworks.
  - This is planning-only at this point:
    - no new code shipped in this pass;
    - no new branch remains active; and
    - the work is parked on `main` until the stacked local commits are pushed
      and we circle back to implementation.
- 2026-03-31 (Issue #65 P51.5 reactivated): resume the widened log-grade follow-on
  on branch `feature/issue-65-log-grade-value-accounts`.
  - Governing issue:
    - GitHub issue `#65`
  - Immediate execution order:
    - add AU-wise, species-wise harvested log-grade product/account families on
      top of the repaired additive compile-recipe contract;
    - implement the species x grade split as a margin-preserving outer-product
      recipe:
      - use the already-working species-wise harvested-volume totals as one
        margin;
      - use the already-working log-grade totals as the other margin; and
      - compute each AU/species/log-grade cell as
        `species_total * grade_total / harvested_total` so species sums and
        grade sums both remain coherent with the existing harvested-volume
        contract;
    - apply the same cross-split logic to natural-origin/unmanaged harvested
      states so forest-wide harvested volume still equals the sum of the
      explicit species/grade family rather than only the managed/TIPSY-driven
      subset;
    - scrape the newly attached 2025 coast market-report PDFs from issue `#65`
      into a FEMIC-owned, user-overridable species x grade price surface;
    - keep the repo-owned reference price matrices inside FEMIC and merge an
      optional user overlay from `~/.femic/recipe-overlays`;
    - wire the first price-surface contract to distinguish second-growth and
      old-growth coast reports, with a simple runtime selector that maps
      managed/second-growth harvests to the second-growth matrix and
      natural-origin/old-growth harvests to the old-growth matrix unless
      overridden by recipe/user config;
    - add derived value-account families that multiply AU/species/log-grade
      harvested volumes by the price matrix coefficients;
    - rebuild the affected K3Z XML / tracks surfaces before rerunning Matrix
      Builder;
    - finish with a representative headless Patchworks smoke that writes
      species-wise harvested product volume outputs and confirms the new
      price-linked value surfaces are present in concrete runtime artifacts.
- 2026-03-31 (Issue #65 P51.5 progress): the AU/species/log-grade bridge and
  value-account layer are now wired into the shared K3Z export path.
  - The shipped `log-grades` recipe now carries:
    - `species_grade_split.enabled`;
    - matrix selectors for managed vs natural-origin harvest;
    - explicit market-species proxy mappings; and
    - FEMIC-owned reference price matrices in
      `src/femic/resources/patchworks/log_grade_price_matrices.yaml`.
  - Rebuilt K3Z XML and active track surfaces now contain:
    - AU/species/log-grade harvested products; and
    - matching AU/species/log-grade value products.
  - Runtime smoke on `base` and `ctfert_l15h5` confirms:
    - non-zero species-grade harvested outputs are saved;
    - non-zero value-account outputs are saved; and
    - the price-linked bridge is live in concrete Patchworks stage artifacts.
  - Acceptance note:
    - rebuilt static `products.csv` / `accounts.csv` surfaces now reconcile the
      AU/species/log-grade bridge against the existing harvested-volume margins
      on representative K3Z tracks;
    - Patchworks saved target CSVs still do not provide a clean whole-stage
      additive proof surface for this matrix layer, so closeout should rely on
      the rebuilt static track/account surfaces plus representative non-zero
      runtime target files rather than whole-stage target summation alone.
- 2026-03-31 (Issue #65 deterministic managed-AU crosswalk repair): stop
  guessing raw managed TIPSY rows from curve shape and use a first-class
  deterministic crosswalk instead.
  - Immediate execution order:
    - persist the raw local managed/unmanaged AU linkage in the bundle AU table
      alongside the existing namespaced K3Z AU ids;
    - extend the FMG bundle context to carry that linkage forward as normalized
      analysis-unit metadata;
    - replace the exact yield-curve matching seam in
      `femic.fmg.adapters` with deterministic lookup by the persisted/raw local
      managed AU id (with a reversible namespace-derived fallback only for old
      bundle tables);
    - add focused regression tests proving managed indicator curves and QMD
      support load through the deterministic crosswalk rather than curve-shape
      rediscovery; and
    - rebuild `ctfert_l15h5` first and verify `Logs_Grade*` products/accounts
      return before broadening any further `#65` closeout work.
- 2026-03-31 (Urgent bug prep): park the current `#65` feature slice behind a
  new upstream K3Z bug for ctfert species-universe narrowing.
  - Governing issue:
    - GitHub issue `#66`
  - Immediate symptom:
    - current `ctfert_*` surfaces only emit `CW/FDC/HW` in
      `feature.Yield.managed.*`, `product.HarvestedVolume.managed.*`, and the
      new `product.Logs_Grade*` families, while AU strata tokens such as
      `CWHvm_DR_HW_M`, `CWHvm_HW_BA_M`, and `CWHvm_HW_SS_M` clearly imply
      additional expected species (`DR`, `BA`, `SS`).
  - Key evidence:
    - the same ctfert species narrowing is already present on published
      `main` before the current `#65` feature branch;
    - `pct_*` surfaces still carry the broader species set
      (`CW/FDC/HW/PLC/YC`), so this is not a generic issue with the new
      species-grade bridge itself;
    - the new bridge is inheriting an already-too-narrow ctfert harvested
      species margin.
  - Additional reported symptom to verify on this bug track:
    - many blocks reportedly show no visible seral stage in Patchworks map
      views on the current main-branch state;
    - treat this as a potentially related regression signal until proven
      otherwise, and explicitly inspect seral-stage feature emission / XML
      wiring / matrix-build outputs during the bug investigation.
  - Immediate next steps:
    - switch to the dedicated bug branch
      `bug/issue-66-ctfert-species-universe` off `main`;
    - trace why ctfert harvested-volume species families on `main` already
      collapse to `CW/FDC/HW` even when AU strata naming implies additional
      species; and
    - restore the broader expected species membership before resuming
      additional `#65` feature work.
- 2026-03-31 (Issue #66 active fix): restore broader ctfert species families
  by repairing the missing `01a` fallback path in post-TIPSY bundle assembly.
  - Root cause:
    - when `vdyp_prep-tsa<tsa>.pkl` was missing, `run_post_tipsy_bundle(...)`
      rebuilt AU maps from the persisted bundle `au_table.csv` but silently set
      `vdyp_species_proportions[tsa] = {}`;
    - that left unmanaged species-proportion curves as zero dummy rows for the
      affected ctfert AUs and prevented the treated repair seam from
      reintroducing companion species such as `DR`, `BA`, and `SS`.
  - Repair:
    - added a new fallback that rebuilds unmanaged species proportions from the
      shipped `data/vdyp_lyr-tsak3z.feather` surface when `01a` prep is absent;
    - for each persisted `(stratum_code, si_level)` pair, the fallback matches
      the leading species pair in the AU token against the dominant-pair mix in
      `vdyp_lyr`, aggregates the full top-6 species composition, and normalizes
      it before bundle emission;
    - the treated repair seam now has a real unmanaged companion map to merge
      against the planted-species TIPSY mix.
  - Verified bundle result:
    - rebuilt `treated_species_prop_*` / `untreated_species_prop_*` rows for
      `CWHvm_DR+HW`, `CWHvm_HW+SS`, and `CWHvm_HW+BA` now carry non-zero
      `DR` / `SS` / `BA` values instead of zero dummy curves.
  - Verified ctfert rebuild result:
    - refreshed `tracks_ctfert_l15h5` and `tracks_ctfert_l20h0` now carry
      broader managed species families again in
      `feature.Yield.managed.*` and `product.HarvestedVolume.managed.*`;
    - representative species now present again include `DR`, `BA`, and `SS`.
  - Verified runtime result:
    - headless ctfert smoke `issue66_ctfert_runtime_species` wrote non-zero
      runtime targets for
      `product.HarvestedVolume.managed.{DR,BA,SS}.{CC,CT}`.
  - Broadened validation:
    - rebuilt validated XML plus Matrix Builder outputs across all active K3Z
      variants, not just the two ctfert surfaces;
    - static track reconciliation now shows species-wise
      `feature.Yield.managed.*` and `product.HarvestedVolume.managed.*`
      families present across base, PCT, ctfert, intensive, and overlay
      variants, with maximum species-vs-total curve differences only in the
      small rounding-noise range (`0.1` to `0.2`);
    - discovered and fixed a separate PCT runtime seam while doing the smoke
      pass: `pct_light.pin`, `pct_moderate.pin`, and `pct_heavy.pin` were
      missing the shared `headless_runtime_common.bsh` hook and never queued
      the FEMIC worker thread, so their earlier headless failures were not
      species-account regressions at all.
  - Runtime sweep result:
    - successful headless Patchworks smokes now exist for every active K3Z
      variant:
      `base`, `pct_light`, `pct_moderate`, `pct_heavy`,
      `ctfert_l15h5`, `ctfert_l20h0`,
      `intensive_light`, `intensive_moderate`, `intensive_heavy`,
      `intensive_light_standstructure`,
      `overlay_basecase_sum`, `overlay_scenario1_sum`,
      `overlay_scenario2_sum`, and `overlay_basecase_riparian`;
    - every smoke wrote a saved stage with `returncode=0`.
  - Seral-stage symptom status:
    - user live-tested `ctfert_l15h5` and confirmed blocks do carry seral
      stage attributes and managed/unmanaged area sums look good;
    - treat the earlier “missing seral stage” report as a non-reproduced
      student-side symptom, not an active FEMIC/K3Z defect.
  - Detailed Next Steps:
    - record the full all-variant validation and PCT headless-pin repair in
      `CHANGE_LOG.md`;
    - post a final closeout comment on GitHub issue `#66`;
    - merge/push the K3Z submodule rebuild + PCT headless-pin fix;
    - update the parent repo submodule pointer and close the bug.
- 2026-03-30 (Issue #64 kickoff): start the urgent K3Z species-account regression repair on branch `bug/issue-64-k3z-species-account-dropout`.
  - Current local evidence:
    - baseline and `pct_light` now report `species=1 complete_species=1` with the `total OK, species-wise empty` diagnosis;
    - checked-in K3Z tracks and validated XML have collapsed to `feature.Yield.*.Total` / `product.Yield.*.Total` / `product.HarvestedVolume.*.Total.*` only;
    - `external/femic-k3z-instance/data/model_input_bundle/curve_table.csv` is missing all `treated_species_prop_*` / `untreated_species_prop_*` rows;
    - the active K3Z instance ships `data/ria_vri_vclr1p_checkpoint1-tsak3z.feather`, while the species-universe loader is still hard-wired to `data/ria_vri_vclr1p_checkpoint8.feather`.
  - Immediate execution order:
    - repair the species-universe source fallback first;
    - rebuild the shared K3Z XML / tracks surfaces from the repaired bundle path;
    - then prove the recovery through both `account-surface` diagnostics and a harvest-producing Patchworks smoke with species-wise harvested output.
- 2026-03-30 (Issue #64 progress): the shared K3Z species-account contract is repaired and rehydrated on disk.
  - `_load_species_universe_for_tsas(...)` now falls back from missing `checkpoint8` to the shipped `data/ria_vri_vclr1p_checkpoint1-tsak3z.feather` case artifact when it contains `tsa_code` plus top-6 species columns.
  - `femic tsa btc-post-tipsy --run-config config/run_profile.k3z.yaml --tsa k3z --run-id issue64_species_fix` now reports `species proportion export enabled for 10 species`, and `data/model_input_bundle/curve_table.csv` once again contains `treated_species_prop_*` / `untreated_species_prop_*` rows.
  - Regenerated active validated K3Z ForestModel XMLs from the repaired bundle path and reran Matrix Builder across baseline, `ctfert_*`, `pct_*`, `intensive_*`, `intensive_light_standstructure`, and overlay runtime surfaces.
  - Representative validation now shows:
    - baseline `account-surface`: `accounts=213 species=6 complete_species=6 au=14`;
    - `pct_light` `account-surface`: `accounts=331 species=6 complete_species=6 au=14`;
    - `ctfert_l15h5` `account-surface`: `accounts=322 species=4 complete_species=4 au=14`.
  - Headless runtime smoke:
    - `femic patchworks run-variant k3z.base --scenario-mode max-even-flow-smoke --scenario-target product.HarvestedVolume.managed.CW.CC --scenario-min-annual 100 --run-id issue64_species_runtime --log-dir vdyp_io/logs`
    - produced non-empty `scenario/schedule.csv` plus `targets/product_HarvestedVolume_managed_CW_CC.csv` with non-zero per-period harvest values, proving species-wise harvested runtime output is back.
- 2026-03-30 (Issue #64 closeout): the repaired K3Z contract is now fully back in compliance with the pre-existing docs-contract expectations.
  - Rebuilt the baseline validated ForestModel against `config/silviculture.k3z.base.yaml` before rerunning baseline and overlay Matrix Builder surfaces, restoring the expected baseline `feature.Height.*`, `feature.QMD.*`, and `product.QMDNumerator.*` families alongside the repaired species-wise yield/harvested-volume accounts.
  - Final validation is green:
    - `python -m ruff format src tests`
    - `python -m ruff check src tests`
    - `python -m mypy src`
    - `python -m pytest`
    - `python -m pre_commit run --all-files`
    - `python -m sphinx -b html docs _build/html -W`
    - `python -m sphinx -b html external/femic-k3z-instance/docs external/femic-k3z-instance/docs/_build/html -W`
  - The representative runtime smoke remains the direct proof that live scenario output is no longer Total-only:
    - `vdyp_io/logs/headless_stage/issue64_species_runtime/targets/product_HarvestedVolume_managed_CW_CC.csv`
- The BTC/TIPSY cutover and optional indicator-bank rollout are complete
  through issues `#56`, `#57`, and `#58`.
- The current documented BTC contract should remain explicit everywhere:
  - the live user-overlay
    ``<Documents>\BatchTIPSY Composer\TimberSupply.rpt`` path is the only
    known-valid unattended FEMIC ``/TSR`` seam;
  - BTC `/No_GUI` is a reverse-engineering dead end, not a supported FEMIC
    runtime seam.
- The FAN$IER extraction seam is complete through issue `#59`:
  - tracked user-facing surfaces now include:
    - `femic fansier run-batch`
    - `femic fansier parse-batch-output`
    - `femic fansier run-and-parse`
  - the practical machine-ingest default remains:
    - `txt`
    - raw `0%` discount posture
    - short report for lean ingest, long report for broader archive/discovery
- The Patchworks registry/operator surface is complete through issue `#60`:
  - `instances list`
  - `variants list/show/register/update/remove`
  - `variants materialization-plan`
  - `scenarios list`
  - `scenario-sets list/show`
  - `run-variant`
  - `run-scenario`
  - `run-default-scenario`
  - `run-scenario-set`
  - `run-default-scenario-set`
- The docs reconciliation sweep is now complete under issue `#61`:
  - stale `#60` roadmap closeout notes were removed;
  - user-facing guides now cover:
    - unattended BTC/FAN$IER runtime and extraction;
    - Patchworks variant/scenario/scenario-set management;
  - the API/CLI reference now carries clearer operator-facing notes for the
    shipped BTC, FAN$IER, and Patchworks seams;
  - the contract/onboarding docs now surface the current proprietary-tool
    seams more directly for agents and maintainers.
- Issue `#62` packaged-install built-in instance install is now in place:
  - FEMIC now carries a packaged-install user config contract at
    `~/.femic/user.yaml` (or the Windows equivalent);
  - managed built-ins can now be listed/installed under the configured
    managed external root;
  - `femic instance init --instance-name <name>` now resolves through the
    configured visible user-instance root;
  - shipped Patchworks built-ins now resolve from repo-local `external/...`
    first and otherwise from the configured managed built-in root;
  - built-in Patchworks launches now fail with a direct install hint when the
    underlying built-in instance is missing.
- Issue `#63` expansion rename is now in place:
  - `Forest Estate Modelling Integration Core` is now the governing
    spelled-out expansion of FEMIC;
  - package metadata, CLI help, docs index, and planning/history surfaces now
    use the new expansion consistently;
  - the stable runtime identifiers `femic` / `FEMIC` were intentionally left
    unchanged.
- Keep issue `#8` open as the narrower follow-on docs task for native Windows
  Patchworks runtime orientation and the SiteProd default/fallback summary.
- The optional-bank rollout under GitHub issue `#48` is now complete:
  - treat the remaining missing optional BTC/TIPSY indicators as one umbrella
    rollout track, grouped into logical banks rather than split across a large
    pile of tiny issues;
  - start with the most downstream-useful product-oriented families, but keep
    the issue broad enough to absorb the other missing banks as they are
    proven;
  - probe each candidate bank through the proven live user-overlay
    `TimberSupply.rpt` seam, not through oversized clean-room replacement
    reports;
  - keep the rollout proving-ground-only first, following the same dedicated
    `intensive_*` K3Z pattern used for the stand-structure bank;
  - add a durable field-inventory ledger so optional-bank scope does not drift
    between turns.
  - treat the installed BTC `OutputColumns.txt` field map as the canonical
    indicator inventory for that ledger; keep `planning/AllFieldsSQL.rpt` only
    as a secondary GUI/report-template reference for alias discovery.
  - first new post-stand-structure bank result now in hand:
    - the full `log-grades` family (`D/F/H/I/J/U/X/Y/All`) probes cleanly
      through the live unattended `/TSR` overlay seam and is the next shipped
      optional bank candidate.
    - the `lumber-2-or-better` family and `residual-fibre` family also probe
      cleanly through that same seam, so the first product-oriented rollout can
      land as a small cluster of proven banks rather than a one-bank bottleneck.
    - the `lumber-graded`, `lumber-degraded`, and `industrial-logs` families
      also probe cleanly through that seam, so the full product-output bank
      block can be rolled forward as one cohesive second-wave slice.
  - issue `#48` should now be treated as the umbrella tracker for finishing all
    remaining logical banks from the canonical ledger, not just the earlier
    first-wave product families.
  - the live-overlay threshold-triplet recovery slice is now in hand too:
    - `stand-structure-threshold-raw` probes cleanly through the real
      user-overlay `TimberSupply.rpt` seam on the simple generic transposed
      line, without needing copied-install experiments or alias fallback to
      win;
    - the landed bank shape follows the explicit triplet rule and now includes
      `Volume000/125/175`, `BasalArea000/125/175`, `MeanDBHg000/125/175`,
      `MAI000/125/175`, `VPT000/125/175`, `Juvenille_Volume000/125/175`, and
      `Juvenille_Percent000/125/175`;
  - the final `yield-and-age-core` closeout slice is now also in hand:
    - live overlay one-token isolation plus a combined candidate run showed a
      coherent shipped subset:
      `Year`, `TotalAge`, `BHAge`, `StandAge`, `HeightSindex`, `Height`,
      `Volume`, `VPT`, `HeightTassTop`, `HeightTassMean`,
      `HeightTassPredom`;
    - `CC` and `VolumeGross` remain part of the unattended TSR base preset
      rather than the optional bank;
    - only the non-threshold `Juvenille_Volume` and `Juvenille_Percent` totals
      still modal-crash through the real live overlay seam, while their
      threshold-specific variants are already shipped in
      `stand-structure-threshold-raw`;
    - Issue `#48` now has no remaining unshipped logical banks.
  - operator-supervision cleanup to land alongside this work:
    - move BTC/TIPSY CLI default runtime artifacts from `vdyp_io/logs` into
      `tipsy_io/logs`, with default scratch under `tipsy_io/scratch`, so
      supervised BTC runs no longer look like VDYP runs at a glance;
    - treat live unattended `/TSR` overlay validation as strictly sequential,
      not parallel, because the user-overlay `TimberSupply.rpt` seam is shared
      across runs.
- The first optional unattended BTC indicator-bank switch is now wired through
  the live user-overlay TSR seam:
  - `--indicator-bank stand-structure-basic`
  - current safe contents:
    - `MAI`
    - `BasalArea:000`
    - `DBHg:000`
    - `SPH:000`
    - `StemCount000`
    - `StemCount125`
    - `StemCount175`
- The critical runtime rule is now:
  - preserve and extend the hidden stock `TimberSupply.rpt` contract through
    the real per-user overlay path under the current user's Documents folder;
  - do not rely on copied-install-local `TimberSupply.rpt` overrides alone
    when validating optional-bank output, because the live overlay can shadow
    them and create false conclusions.
- The next concrete implementation edge is:
  - revisit managed K3Z QMD using the live BTC-native diameter signals already
    present in the first stand-structure bank;
  - current evidence from `tipsy_curves_tsak3z.csv` is that `DBHg000` closely
    matches the QMD implied by BTC `BasalArea000` + `SPH000`, while FEMIC's
    older volume/height/stems approximation tends to run lower on the same
    live K3Z outputs;
  - so the first intended change is to prefer BTC-native managed diameter
    curves where available and retain the older approximation only as a
    fallback;
  - prove that revised contract first on
    `intensive_light_standstructure`, inspect rebuilt XML/tracks directly, and
    run the relevant Patchworks smoke before widening anything else.
- The headless Patchworks runtime guardrail is now:
  - let FEMIC default unattended `saveStage(...)` output to
    `vdyp_io/logs/headless_stage/<run_id>` so report bundles do not spill into
    tracked `analysis/` paths;
  - only use `--stage-label` for a custom destination when that different save
    location is intentional and reviewed.
- The new human-facing inventory ledger for indicator-bank planning is:
  - `planning/tipsy_indicator_bank_checklist.md`
  - source inventory: `planning/AllFieldsSQL.rpt`
  - cross-reference sources:
    - `C:\Program Files\TIPSY 4.7\BTC\OutputColumns.txt`
    - `C:\Program Files\TIPSY 4.7\BTC\btpfields.txt`
  - status rule:
    - `[x]` means the indicator family is already surfaced through a shipped
      FEMIC BTC path;
    - `[ ]` means the field is still only in planning inventory and has not
      yet been rolled into a shipped bank/switch.
  - current cross-reference finding:
    - `OutputColumns.txt` carries useful output names that are not present in
      `AllFieldsSQL.rpt`, especially the threshold-specific raw stand
      structure aliases (`BasalArea000`, `MeanDBHg000`, `StemCount000`, etc.)
      plus the Carbon / CO2e families;
    - `btpfields.txt` appears to be a BTP input-field map, not an output-field
      ledger, but it is still worth keeping as a side reference when we later
      work on BTC/BTP input-side features.
- Keep the parallel seam-detection mission alive:
  - for any future failing column, collect clues about report family, token
    syntax, stock report membership, and `OutputColumns.txt`/Tcl references so
    we can infer why some `/TSR` columns pass and others fail.
- The installed BTC defaults file `C:\Program Files\TIPSY 4.7\BTC\gw.txt`
  should be treated as a likely first source for default FEMIC genetic gain
  settings in the cutover, with explicit documentation that those defaults are
  exploratory / educational rather than an operational recommendation.
- The installed BTC defaults file `C:\Program Files\TIPSY 4.7\BTC\oafs.txt`
  should be treated as a likely first source for default FEMIC OAF settings in
  the cutover, including OAF1/OAF2 and packaged custom OAF response shapes.
- The installed BTC field map `C:\Program Files\TIPSY 4.7\BTC\OutputColumns.txt`
  should be treated as the likely first output-field mapping reference if we
  can unlock a richer non-GUI BTC output mode beyond the default TSR
  volume/height CSV.
