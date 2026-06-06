# Phase 69: TSA29 Patchworks Rebuild on the New THLB and Yield Surfaces

## Governing Issue and Branches

- Instance issue: `UBC-FRESH/femic-tsa29-instance#6`
- Parent branch: `feature/tsa29-patchworks-rebuild-new-inputs`
- Instance branch: `feature/tsa29-patchworks-rebuild-new-inputs`

## Contract

This lane rebuilds the TSA29 Patchworks-facing model package on top of the
currently accepted upstream inputs:

- the locked TSA29 THLB chain through row 23; and
- the accepted smoothed VDYP plus refreshed TIPSY yield surfaces.

The rebuild must not silently drop surviving AFLB area that falls past the
direct top-N AU selection surface.

## Critical Requirement

Past-top-N strata must still receive deterministic AU assignment. If the direct
selection surface does not cover all surviving AFLB area, use the
lexicographical stratum-matching imputation logic so no remaining modeled area
is left without an AU by accident.

## Planned Execution Shape

### P69.1

Initialization is in progress:
- issue opened;
- parent/instance feature branches created; and
- the remaining initialization task is to keep the lexicographical-imputation
  requirement explicit in the planning and implementation surfaces.

### P69.2

Expected implementation bundle:
- regenerate the TSA29 model-input bundle from the current locked THLB and
  accepted curve surfaces;
- rebuild the TSA29 Patchworks package on that regenerated bundle;
- apply/verify lexicographical AU imputation for past-top-N strata if needed;
- inspect the rebuilt Patchworks-facing outputs directly.

Current progress:
- recovered and recommitted the strict row-23 THLB checkpoint surface needed by
  downstream Patchworks export;
- patched `src/femic/fmg/patchworks.py` so zero/tiny-area checkpoint rows are
  dropped before fragments export, which fixed the row-23 export failure;
- reran `femic export patchworks` from
  `data/tsr/strict_chain/23_thlb_parent_023_future_roads.feather`;
- confirmed the written fragments shapefile now round-trips with `0`
  nonpositive `AREA_HA` rows;
- reran `femic patchworks matrix-build` successfully on the rebuilt package;
- replaced the hanging topology rebuild seam by aligning the rebuild contract
  to the shipped TSA29 analysis surface:
  - `femic patchworks build-blocks --config config/patchworks.runtime.windows.yaml --no-topology`
  - preserve the tracked header-only
    `models/tsa29_patchworks_model/blocks/topology_blocks_0r.csv` file that
    the shared analysis/PIN lane already loads;
- reran `femic patchworks build-blocks --no-topology` successfully and
  confirmed the rebuilt `blocks.shp` surface now completes without the
  topology subprocess hang.

### P69.3

Expected validation/publication bundle:
- run the necessary Patchworks-facing validation checks;
- update docs/evidence only if the rebuilt package is accepted; and
- close the issue and publish the resulting branch/PR state.

Current progress:
- rebuilt the validated TSA29 Patchworks export after raising the fragment
  export area floor to `0.001 ha`, which reduced the fragments surface from
  `447,022` block parts to `421,945`;
- collapsed sub-`0.001 ha` managed/unmanaged retention splits onto the dominant
  side during fragments export so Patchworks no longer emits block-area
  precision-limit warnings at launch;
- disabled Matrix Builder successful-output auto-close in the TSA29 Windows
  runtime config so FEMIC no longer force-stops Patchworks while track files
  are still being written;
- reran:
  - `femic export patchworks --tsa 29 --bundle-dir data/model_input_bundle --checkpoint data/tsr/strict_chain/23_thlb_parent_023_future_roads.feather --output-dir output/patchworks_tsa29_validated`
  - `femic patchworks build-blocks --config config/patchworks.runtime.windows.yaml --no-topology`
  - `femic patchworks matrix-build --config config/patchworks.runtime.windows.yaml --run-id p69_3a_tsa29_matrix_rebuild_20260606c`
- verified the rebuilt `models/tsa29_patchworks_model/tracks/blocks.csv`
  no longer truncates at the final row and now has `0` malformed records;
- ran a real headless Patchworks launch smoke:
  - `femic patchworks run-headless models/tsa29_patchworks_model/analysis/base.pin --config config/patchworks.runtime.windows.yaml --run-id p69_3a_tsa29_launch_smoke_20260606d --iterations 1 --improvement 0.0`
- confirmed the rebuilt package now launches cleanly:
  - headless manifest `returncode=0`
  - terminal marker `[FEMIC headless] saveStage completed`
  - saved stage directory with `543` output files
  - no `blocks.csv` parse error and no block-area precision-limit warnings in
  the launch stderr log.
- updated the TSA29 instance docs/evidence surfaces to record accepted package
  evidence:
  - added `external/femic-tsa29-instance/evidence/patchworks_test01_scenario_20260606.md`
    summarizing the representative interactive `test01` scenario and its
    harvest-level comparison against the 2014 Williams Lake TSA public
    discussion paper;
  - updated:
    - `external/femic-tsa29-instance/README.md`
    - `external/femic-tsa29-instance/docs/rebuild-and-qa.rst`
    - `external/femic-tsa29-instance/docs/data-and-provenance.rst`
    so the refreshed package points directly at that accepted scenario
    evidence; and
  - reran the TSA29 instance Sphinx build warning-clean after those docs
    updates.
