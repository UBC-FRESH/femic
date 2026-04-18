# AFLB -> Yield Bridge -> THLB Seam (`#164`)

## Purpose

Define the first explicit interruption/resume seam that turns the current
legacy THLB + yield workflow into a restart-safe pipeline contract.

The motivating truth from the TSA29 THLB reconciliation work is:

- THLB is not logically one uninterrupted recipe chain;
- after the early land-base ladder reaches **AFLB**, FEMIC needs yield-model
  dependencies that are compiled from the **AFLB stand universe**; and
- only after those dependencies exist should the workflow resume the later
  THLB steps that depend on yield/operability context.

This note is the concrete execution contract for child issue `#164` under the
named-pipeline umbrella `#163`.

## Current Reusable Pieces Already in FEMIC

### Restart-grade THLB checkpoints

Strict TSR/THLB runs already emit restart-safe checkpoints:

- `data/tsr/aflb_checkpoint.feather`
- `data/tsr/lhlb_checkpoint.feather`
- `data/tsr/lhlb_curve_ready_checkpoint.feather`

Relevant code/docs:

- `src/femic/tsr_catalog/recipes.py`
- `src/femic/cli/main.py`
- `docs/guides/tsr-thlb-reconstruction-ladder.rst`
- `docs/reference/cli.rst`

This means the workflow already knows how to stop at a meaningful land-base
boundary and publish a restart artifact.

### Stratification / top-area coverage

The Stage 01a path already has the pieces needed to derive strata from an
input stand universe and cap the selected strata by cumulative area coverage.

Relevant surfaces:

- run-config contract:
  - `selection.stratification.top_area_coverage`
  - documented in `docs/reference/run-config.rst`
- helpers in `src/femic/pipeline/tsa.py`:
  - `build_strata_summary(...)`
  - `assign_si_levels_from_stratum_quantiles(...)`
  - `assign_au_ids_from_scsi(...)`

Important existing behavior:

- `build_strata_summary(...)` already supports `target_coverage`
- this is the natural starting point for the requested default `80%` coverage
  rule

### VDYP cache / resume surfaces

FEMIC already has durable VDYP preparation and per-TSA result cache seams:

- `src/femic/pipeline/pre_vdyp.py`
  - `load_vdyp_prep_checkpoint(...)`
  - `save_vdyp_prep_checkpoint(...)`
- `src/femic/pipeline/vdyp.py`
  - `vdyp_results_tsa_pickle_path`
- `src/femic/pipeline/vdyp_stage.py`

Legacy orchestration still treats these as part of the Stage 01a flow, but the
cache/resume surfaces already exist and can be promoted into a more explicit
pipeline seam.

### TIPSY/BTC/FANSIER handoff and resume

FEMIC already has a clear Stage 01a -> BTC -> Stage 01b contract:

- Stage 01a output:
  - canonical BTC input `03_input-<unit>.csv`
- external runtime boundary:
  - returned `04_output-<unit>.csv`
  - returned `04_error-<unit>.csv`
- Stage 01b resume:
  - `femic tsa post-tipsy`
  - `femic tsa btc-post-tipsy`

Relevant docs:

- `docs/guides/stage-01b-post-tipsy.rst`
- `docs/reference/contracts/stage-boundaries-and-canonical-artifacts.rst`

Relevant code:

- `src/femic/pipeline/tipsy.py`
  - `evaluate_tipsy_candidate(...)`
  - `build_tipsy_params_for_tsa(...)`
- `src/femic/cli/main.py`

### Existing late-stage yield enrichment seam

The current THLB workflow already has one late-stage enrichment checkpoint:

- `lhlb_curve_ready_checkpoint.feather`

Relevant code:

- `src/femic/tsr_catalog/step13_attributes.py`
- `src/femic/tsr_catalog/recipes.py`

This proves the repo already accepts the idea that a THLB checkpoint can be
promoted into a more specialized downstream restart artifact.

## What Is Still Missing

The missing part is not raw functionality. The missing part is the **explicit
pipeline seam** that connects:

1. THLB early-ladder land-base state (`AFLB`)
2. strata/AU/yield compilation
3. downstream THLB continuation

Right now those pieces live in different workflow lanes:

- TSR THLB strict lane owns `aflb_checkpoint`
- legacy Stage 01a/01b owns strata/AU/VDYP/TIPSY
- late-stage THLB restart owns `lhlb_curve_ready_checkpoint`

There is no canonical artifact contract that says:

> "Start from AFLB, derive the top-coverage strata and AU universe, satisfy
> the yield dependencies, then resume THLB from a restart-safe yield bridge."

## Proposed Canonical Seam

### Stop point

The interruption seam starts from:

- `data/tsr/aflb_checkpoint.feather`

This remains the canonical upstream boundary for the yield bridge.

### New bridge artifacts

The first implementation should add these restart-safe artifacts under
`data/tsr/`:

1. `aflb_strata_checkpoint.feather`
   - AFLB rows annotated with selected stratum key / coverage selection fields
   - enough metadata to explain which strata were retained under the active
     top-area coverage rule

2. `aflb_au_checkpoint.feather`
   - AFLB rows annotated with:
     - `stratum_matched`
     - `si_level`
     - `au`
   - this is the natural restart seam after strata/AU assignment

3. `aflb_yield_bridge_manifest.json`
   - records:
     - source AFLB checkpoint
     - active top-area coverage threshold
     - selected strata count / realized coverage
     - active VDYP sampling mode / intensity
     - whether VDYP cache reuse was accepted or a rerun was required
     - whether BTC/TIPSY and optional FANSIER were run
     - output bundle paths / timestamps / hashes

4. `aflb_yield_ready_checkpoint.feather`
   - restart-grade checkpoint that signals:
     - AFLB-derived strata/AU/yield dependencies are satisfied
     - downstream THLB may now resume without replaying the yield bridge

### Existing downstream artifacts to reuse

The yield bridge should reuse the existing bundle artifacts, not invent a
parallel yield table universe:

- `data/model_input_bundle/au_table.csv`
- `data/model_input_bundle/curve_table.csv`
- `data/model_input_bundle/curve_points_table.csv`

And the existing post-TIPSY resume contract remains valid:

- `femic tsa post-tipsy`
- `femic tsa btc-post-tipsy`

## Proposed Command Surface

The first implementation does **not** need the full named-pipeline registry.
It only needs one explicit bridge builder.

Recommended first command:

- `femic tsr build-yield-bridge --instance-root ... --run-config ... --tsa 29`

Suggested behavior:

1. require or discover `data/tsr/aflb_checkpoint.feather`
2. derive strata from AFLB using:
   - `selection.stratification.*`
   - default `top_area_coverage = 0.80` if not set
3. assign SI levels and AUs
4. inspect cache sufficiency for the active VDYP sampling contract
5. rerun VDYP only if the cache is not sufficient
6. compile TIPSY params
7. run BTC/TIPSY and optionally FANSIER if requested
8. run post-TIPSY bundle compilation
9. publish:
   - `aflb_strata_checkpoint.feather`
   - `aflb_au_checkpoint.feather`
   - `aflb_yield_bridge_manifest.json`
   - `aflb_yield_ready_checkpoint.feather`

Then the downstream THLB command can accept:

- `--checkpoint-path data/tsr/aflb_yield_ready_checkpoint.feather`

without replaying the yield bridge.

## Cache Sufficiency Contract

The first version should define cache sufficiency conservatively.

Cache reuse is acceptable only if all are true:

- source AFLB checkpoint identity matches the manifest
- selected strata / realized coverage still match the active settings
- active VDYP sampling mode/intensity still matches the cached run
- AU universe still matches (`_row_id` / AU coverage)
- required downstream bundle tables exist and pass basic coherence checks

Otherwise the bridge rebuilds the missing or stale steps.

## Narrowest First Implementation Path

To keep `#164` bounded, implement it in this order:

1. **Spec / manifest layer**
   - introduce the new artifact names and manifest schema

2. **AFLB -> strata/AU restart seam**
   - publish `aflb_strata_checkpoint` and `aflb_au_checkpoint`

3. **Cache sufficiency check**
   - decide whether existing VDYP/TIPSY outputs are good enough

4. **Bridge builder command**
   - run or resume the yield workflow from AFLB to `aflb_yield_ready_checkpoint`

5. **Downstream THLB restart acceptance**
   - allow later THLB commands to accept the new yield-ready checkpoint

Only after that should `#163` generalize the pattern into a broader named
pipeline registry.

## Why This Is The Right First Child Under `#163`

This seam is the best first proof-of-concept because it is:

- already grounded in real FEMIC checkpoint and recipe work;
- small enough to specify precisely;
- useful on its own even before the broader registry architecture exists; and
- a clean bridge between the legacy Stage 01a/01b yield workflow and the newer
  recipe/checkpoint-based TSR THLB workflow.
