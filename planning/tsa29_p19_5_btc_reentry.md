# TSA29 `P19.5` BTC-First Re-entry

## Why This Note Exists

Issue `#10` and the late-March `P19.5` notes in this clone still frame TSA29
closeout around the legacy manual BatchTIPSY DAT/out seam:

- `02_input-tsa29.dat`
- `04_output-tsa29.out`

That is no longer the best current representation of FEMIC's intended TIPSY
contract.

The newer parent baseline in the current fresh validation checkout has already
shifted the supported workflow to a BTC-first seam:

1. Stage 01a writes canonical `03_input-tsaXX.csv`.
2. FEMIC launches unattended `TIPSYbtc.exe /TSR`.
3. BTC returns `04_output-tsaXX.csv` and `04_error-tsaXX.csv`.
4. `femic tsa btc-post-tipsy` resumes the existing downstream bundle flow.

This note records the re-entry plan for bringing TSA29 onto that current
contract.

## Current Situation

### Stronger TSA29 source workspace

The active source workspace at the current repo root remains the better TSA29
forensic/source workspace because it retains:

- parent branch `bug/p19.5-tsa29-rebuild-triage`;
- TSA29 submodule branch `bug/p19.5-tsa29-rebuild-triage`;
- TSA29 submodule commit `5413e23`;
- repaired TSA29 runtime/config/runbook state;
- checkpoint and boundary artifacts that were missing from the thinner fresh
  validation clone.

### Better parent BTC baseline elsewhere

The fresh validation checkout now carries the reference BTC-first parent
surfaces:

- CLI:
  - `femic tsa btc-post-tipsy`
  - `femic tipsy run-btc`
- workflow wrapper:
  - `run_btc_and_post_tipsy_bundle_with_manifest(...)`
- contract/docs:
  - canonical `03_input-*.csv`
  - unattended BTC `/TSR`
  - returned `04_output-*.csv` / `04_error-*.csv`

### TSA29 has not caught up yet

Even in the newer parent clone, the TSA29 standalone instance still advertises
legacy BatchTIPSY artifacts in its docs:

- `data/02_input-tsa29_si_plus2.dat`
- `data/04_output-tsa29.out`

So the parent framework has moved, but the TSA29 instance contract has not yet
been fully migrated.

## Re-entry Goal

Re-scope `P19.5` so the final TSA29 closeout answers the current reproducibility
question:

- can TSA29 be rebuilt and evidenced against the BTC-first parent workflow on a
  clean/current checkout, with current Patchworks/runtime wiring, without
  relying on stale manual DAT/out assumptions?

## Execution Plan

1. Preserve and commit only the permanent issue-`#10` contract fixes.
   - Treat the active repo root as the source/forensic workspace.
   - Keep the permanent payload focused on:
     - env-driven Patchworks licensing on Windows
     - output-local `forestmodel.xml` beside validated fragments
     - TSA29 Windows auto-close config
     - docs/runbook/README wording that matches the BTC-first + output-local
       contract
     - deletion of stale duplicate TSA29 XML files
   - Keep large runtime spill, restored checkpoints, plots, and scratch outputs
     out of the intentional Git payload unless they are explicitly promoted as
     accepted evidence.

2. Add a formal provenance audit for the TIPSY seam.
   - For one final closeout run ID, preserve chain-of-custody showing:
     - `femic run` emitted fresh `data/03_input-tsa29.csv`
     - unattended BTC consumed that exact fresh CSV
     - BTC emitted fresh `data/04_output-tsa29.csv` / `data/04_error-tsa29.csv`
     - `femic tsa btc-post-tipsy` rebuilt fresh:
       - `data/tipsy_curves_tsa29.csv`
       - `data/tipsy_sppcomp_tsa29.csv`
       - `data/model_input_bundle/*`
       - `plots/tipsy_vdyp_tsa29-*.png`
   - Preserve matching manifests/mtimes and record explicitly whether the
     reviewed plots came from the fresh BTC-first seam or from stale artifacts.

3. Keep the null-volume triage narrow for issue `#10`.
   - After provenance is proven fresh, inspect the regenerated
     `tipsy_vdyp_tsa29-*.png` family only far enough to answer whether the
     apparent null/no-volume pattern is a fresh runtime result.
   - Treat blank/null BTC output as a blocker for issue `#10`.
   - If the fresh seam is proven and the pattern remains, hand that behavior
     off to the next TSA29 v0 issue instead of widening `#10` into a full
     model-behavior investigation.

4. Validate from a fresh/current parent checkout.
   - Do not treat the already-dirty forensic workspace as the final
     reproducibility proof.
   - Run the final acceptance/evidence pass from the fresh validation checkout
     at `F:\projects\tmp\femic-issue10-closeout-20260402-clean` after the
     intended issue-`#10` commits are in place.
   - Point `FEMIC_EXTERNAL_DATA_ROOT` at the already-materialized shared public
     data mirror under the source workspace:
     `F:\projects\femic\external\femic-public-data\data`.
   - Final execution order:
     1. `femic prep validate-case --instance-root external/femic-tsa29-instance --run-config config/run_profile.tsa29.yaml`
     2. `femic prep geospatial-preflight --instance-root external/femic-tsa29-instance`
     3. `femic run --instance-root external/femic-tsa29-instance --run-config config/run_profile.tsa29.yaml --run-id <closeout_id>`
     4. `femic tsa btc-post-tipsy --instance-root external/femic-tsa29-instance --run-config config/run_profile.tsa29.yaml --tsa 29 --run-id <closeout_id>`
     5. regenerate validated fragments only if the thin checkout still
        externalizes them
     6. `femic patchworks preflight --instance-root external/femic-tsa29-instance --config config/patchworks.runtime.windows.yaml`
     7. `femic patchworks build-blocks --instance-root external/femic-tsa29-instance --config config/patchworks.runtime.windows.yaml --with-topology --topology-backend patchworks-raster`
     8. `femic patchworks matrix-build --instance-root external/femic-tsa29-instance --config config/patchworks.runtime.windows.yaml --run-id <closeout_id>`

5. Close or re-block issue `#10` with contemporary evidence.
   - Close only when:
     - the runtime/docs/runbook agree on the Windows native Patchworks path
     - live runtime config no longer points at `models/.../yield/forestmodel.xml`
     - live runtime config no longer injects literal
       `sps_user@auth.spatial.ca`
     - the final closeout run proves a single auditable fresh seam from
       `03_input-tsa29.csv` through fresh BTC CSVs to fresh post-TIPSY
       curves/bundle/plots
     - `femic patchworks matrix-build` completes with `returncode=0` and no
       recorded failures
   - If the fresh seam is clean but null/no-volume TIPSY behavior remains,
     record that explicitly and move it into the next TSA29 v0 issue.

## Immediate Next Task

The planned fresh validation checkout rerun has now completed successfully from
`F:\projects\tmp\femic-issue10-closeout-20260402-clean` using run ID
`tsa29_issue10_closeout_20260402f`.

Closeout outcome:

- issue `#10` is satisfied as a BTC-first rebuild-contract, provenance, and
  evidence closeout;
- the clean-clone evidence proved the reviewed TSA29 null/no-volume pattern is
  fresh behavior, not stale artifact residue;
- the remaining behavior investigation now belongs to follow-on issue `#79`
  rather than reopening the issue-`#10` contract closeout.
