# TSA29 `P19.5` BTC-First Re-entry

## Why This Note Exists

Issue `#10` and the late-March `P19.5` notes in this clone still frame TSA29
closeout around the legacy manual BatchTIPSY DAT/out seam:

- `02_input-tsa29.dat`
- `04_output-tsa29.out`

That is no longer the best current representation of FEMIC's intended TIPSY
contract.

The newer parent baseline in `C:\Users\gep\projects\tmp\femic` has already
shifted the supported workflow to a BTC-first seam:

1. Stage 01a writes canonical `03_input-tsaXX.csv`.
2. FEMIC launches unattended `TIPSYbtc.exe /TSR`.
3. BTC returns `04_output-tsaXX.csv` and `04_error-tsaXX.csv`.
4. `femic tsa btc-post-tipsy` resumes the existing downstream bundle flow.

This note records the re-entry plan for bringing TSA29 onto that current
contract.

## Current Situation

### Stronger TSA29 source workspace

The active `C:\Users\gep\projects\femic` clone still appears to be the better
TSA29 forensic/source workspace because it retains:

- parent branch `bug/p19.5-tsa29-rebuild-triage`;
- TSA29 submodule branch `bug/p19.5-tsa29-rebuild-triage`;
- TSA29 submodule commit `5413e23`;
- repaired TSA29 runtime/config/runbook state;
- checkpoint and boundary artifacts that were missing from the thinner
  `tmp\femic` clone.

### Better parent BTC baseline elsewhere

The newer parent baseline in `C:\Users\gep\projects\tmp\femic` `main` now
contains the reference BTC-first surfaces:

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

1. Preserve current dirty state in this clone.
   - Treat `C:\Users\gep\projects\femic` as the source/forensic workspace.
   - Preserve both parent and `external/femic-tsa29-instance` work before any
     merge, rebase, or transplant.

2. Audit the minimal intentional carry-forward set.
   - Identify the TSA29-specific changes that still matter:
     - runtime wiring
     - runbook/docs updates
     - rebuild contract tweaks
     - canonical tracked artifacts
   - Exclude transient generated residue unless it is truly contractual.

3. Use the BTC-first parent as reference implementation.
   - Compare this clone against `C:\Users\gep\projects\tmp\femic` `main` for the
     parent workflow surfaces that implement:
     - `03_input-tsaXX.csv`
     - unattended BTC execution
     - CSV post-TIPSY resume

4. Migrate TSA29 onto the BTC-first seam.
   - Update TSA29 instance planning/runbook/docs so the active contract becomes:
     - `03_input-tsa29.csv`
     - unattended BTC
     - `04_output-tsa29.csv`
     - `04_error-tsa29.csv`
     - `femic tsa btc-post-tipsy`
   - Keep legacy DAT/out notes only as compatibility or historical context.

5. Validate from a fresh/current parent checkout.
   - Do not treat a rescued dirty branch run as the final reproducibility proof.
   - Run the acceptance/evidence pass from a fresh/current checkout after the
     minimal TSA29 carry-forward set is in place.

6. Close or re-block issue `#10` with contemporary evidence.
   - If the BTC-first TSA29 rebuild succeeds, publish refreshed evidence and
     close `P19.5`.
   - If it still fails, replace the stale DAT-era blocker narrative with the
     actual current failure mode.

## Immediate Next Task

The next concrete implementation step is to diff the current clone against the
BTC-first surfaces in `tmp\femic` and build the smallest safe migration set for
TSA29.
