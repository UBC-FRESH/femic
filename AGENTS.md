# Codex Agent Operating Notes

## Fresh Clone Bootstrap (Read First)

Before running FEMIC commands in a new clone, complete this baseline setup in
the repo root:

1. Create/activate local virtual environment and install editable dev deps:
   - Linux/macOS:
     - `python -m venv .venv`
     - `. .venv/bin/activate`
   - Windows PowerShell:
     - `python -m venv .venv`
     - `.venv\Scripts\Activate.ps1`
   - then:
     - `python -m pip install --upgrade pip setuptools wheel`
     - `python -m pip install -r requirements-dev.txt`
2. Confirm toolchain from the active `.venv`:
   - `python -m femic --help`
   - `ruff --version`
   - `mypy --version`
   - `pytest --version`
   - `pre-commit --version`
   - `sphinx-build --version`
   - `gh --version`
   - `gh auth status`
3. Initialize submodules and materialize annex-backed public data:
   - `git submodule update --init --recursive`
   - `git annex version` (must work from shell; install system package if missing)
   - `datalad --version` (provided by `.venv` via `datalad[full]`)
   - `git -C external/femic-public-data annex enableremote arbutus-s3`
   - `datalad get -r external/femic-public-data/data`
   - if you are bootstrapping a new DataLad dataset or FEMIC instance dataset
     with an Arbutus special remote from Windows, read
     `docs/guides/public-data-mirror-runbook.rst` first and do not improvise
     the auth/bootstrap order
   - Windows-specific Arbutus reminders:
     - check `femic prep arbutus-auth-status` before improvising any local
       Arbutus recovery steps
     - use `femic prep arbutus-auth-init` to scaffold the local auth/profile
       files when the workflow is missing or stale
     - `%USERPROFILE%\.config\femic\arbutus.env` must use plain `KEY=VALUE`
       lines with no quotes
     - interactive loader usage needs an execution-policy-bypassed session
     - validate bucket visibility with a direct `HeadBucket` probe before
       running `git annex initremote`
4. Export `FEMIC_EXTERNAL_DATA_ROOT` before case preflight/runs when using the
   linked mirror:
   - Linux/macOS:
     - `export FEMIC_EXTERNAL_DATA_ROOT=$PWD/external/femic-public-data/data`
   - Windows PowerShell:
     - `$env:FEMIC_EXTERNAL_DATA_ROOT="$PWD\\external\\femic-public-data\\data"`
5. Run preflight checks before long workflows:
   - `femic prep validate-case --instance-root external/femic-k3z-instance --run-config config/run_profile.k3z.yaml`
   - `femic prep geospatial-preflight`
6. Before Stage 00/01 runs, confirm external runtime boundaries are explicit:
   - ArcRasterRescue: use the existing patched fork workflow; if auto-discovery
     fails, set `FEMIC_ARC_RASTER_RESCUE_EXE` to the compiled executable path.
   - BatchTIPSY freshness: treat `03_input-tsaXX.csv` as canonical; XLSX is a
     mirror only. Do not assume a stale block means rerun is required without
     checking whether CSV content actually changed.
   - BatchTIPSY/BTC runtime install:
     - if `TIPSYbtc.exe` is missing from the current Windows dev environment,
       install TIPSY 4.7 from:
       `https://www2.gov.bc.ca/assets/gov/farming-natural-resources-and-industry/forestry/stewardship/forest-analysis-inventory/software/tipsy47.msi`
     - default expected installed path is:
       `C:\Program Files\TIPSY 4.7\BTC\TIPSYbtc.exe`
     - if FEMIC cannot auto-discover it after install, set either
       `FEMIC_BATCHTIPSY_EXE` or pass `--btc-exe`.
   - BC Data Catalogue discovery quickstart:
     - resolve/classify one likely BCDC layer:
       - `& .\.venv\Scripts\python.exe -m femic data bcdc-resolve WHSE_FOREST_VEGETATION.F_OWN`
     - exercise a real direct-download-capable case:
       - `& .\.venv\Scripts\python.exe -m femic data bcdc-resolve SITE_PROD_BC --download-direct --download-root data\downloads\bcdc --manifest-path runtime\logs\bcdc_site_prod_bc_manifest.json`
     - in PowerShell, quote multi-word free-text queries so they are passed as
       one query:
       - `& .\.venv\Scripts\python.exe -m femic data bcdc-resolve "Silviculture Activities History"`
7. If you are running inside VS Code/Cursor on Windows and Codex file links are
   broken (assistant-rendered local file links open in the browser instead of
   the editor), bootstrap-fix the IDE before doing deeper FEMIC work:
   - patch repo:
     - `https://github.com/UBC-FRESH/codex-local-file-link-patch`
   - agent bootstrap notes:
     - `https://github.com/UBC-FRESH/codex-local-file-link-patch/blob/main/AGENTS.md`
   - primary fix command:
     - `powershell -ExecutionPolicy Bypass -File .\apply_codex_local_file_link_patch.ps1`
   - after patching:
     - run `Developer: Reload Window`
   - do this early if file navigation is broken; it is a Windows VS Code/Codex
     productivity workaround, not a FEMIC runtime requirement on Linux.

For the compact docs source of truth behind these operating notes, see:
- `docs/reference/contracts/index.rst`
- `docs/reference/contracts/patchworks-model-semantics.rst`
- `docs/reference/contracts/repo-runtime-invariants.rst`
- `docs/reference/contracts/instance-and-data-roots.rst`
- `docs/reference/contracts/stage-boundaries-and-canonical-artifacts.rst`
- `docs/reference/contracts/recovery-and-external-runtime-boundaries.rst`

## Patchworks Model Semantics Guardrails

These rules are repo-level contracts, not case-specific heuristics:

- `managed` / `unmanaged` in Patchworks means treatment eligibility only:
  - `managed` area may receive scheduled treatments;
  - `unmanaged` area may not.
- `natural` / `treated` origin means curve provenance only:
  - natural-origin area belongs on the untreated / VDYP-style curve lane;
  - treated-origin area belongs on the treated / plantation / TIPSY-style
    curve lane.
- Do not infer `managed = treated` or `unmanaged = natural`.
- Retention is orthogonal to origin:
  - retention may move area from `managed` to `unmanaged`;
  - retention does not, by itself, change origin.
- Do not use first-growth curve availability, `hasfg`, or similar curve-family
  presence as a proxy for Patchworks IFM state.
- After Patchworks-facing rebuilds, validate species-share and runtime-signal
  sanity explicitly:
  - compare published source-share tables against rebuilt `indsp.*` outputs;
  - treat "Matrix Builder succeeded" as necessary but not sufficient; and
  - fail the sanity check when nonzero source share produces zero runtime
    signal, or vice versa.

Do not treat symlinked pointer files in `external/femic-public-data` as usable
inputs until `datalad get` has completed.

Canonical repository root for FEMIC work is the active checkout root.
Use the repo you are actually in, not a machine-specific absolute path copied
from another environment.

If any tool/session metadata, stale terminal context, or editor integration
mentions the legacy `wbi_ria_yield` path, treat that as stale context only.
Do not use it for command execution, patch application, file references, or
reasoning about the active repo. Always pin command working directories and
file operations to the active FEMIC checkout explicitly.

When contributing to this repository as the coding agent:

1. Before wrapping up a development milestone (feature, roadmap phase, or PR), run:
   - `ruff format src tests`
   - `ruff check src tests`
   - `mypy src`
   - `pytest`
   - `pre-commit run --all-files` (once hooks are installed).
2. Address any linter or type-check warnings promptly; avoid suppressions unless discussed.
3. Prefer module-level constants for Typer argument defaults (prevents B008) and keep line length
   <= 100 characters.
4. Document notable behaviour changes in the README or docs as part of the same change set.
5. Before starting any non-trivial plan (anything larger than a small isolated fix or one-file cleanup),
   document that plan in `ROADMAP.md` under the appropriate phase/task structure. Do not let
   material implementation planning live only in chat. If the roadmap does not yet contain
   the plan, update the roadmap first, then execute.
6. Whenever you plan or complete work, update the "Detailed Next Steps Notes" section in
   `ROADMAP.md` so the leading edge of the implementation plan stays current. Consult that section
   before proposing new next steps to ensure we continue in sequence rather than jumping around.
6a. Keep roadmap parent-task status synchronized with child subtasks:
   - if every listed child subtask under a roadmap task is checked off, check off the parent task
     in the same change set unless the parent line explicitly covers additional still-open scope;
   - do not leave top-level roadmap tasks unchecked after all of their child subtasks are marked
     complete;
   - when a parent task intentionally stays open despite completed children, add a brief note in
     the roadmap/planning surface explaining why.
7. After each deliverable or roadmap milestone, append the same progress summary reported to the user
   to `CHANGE_LOG.md` (Markdown format, newest entries last) so the repository carries an auditable
   narrative of changes.
8. When documentation files change, run `sphinx-build -b html docs _build/html -W` (or the equivalent
   project helper) before finalising the work to ensure Sphinx warnings are treated as errors.
9. Before launching a new task or plan, review the latest entries in `CHANGE_LOG.md` alongside the
   roadmap notes to confirm the proposed work is consistent with recorded progress and avoids
   backtracking.
10. Never publish machine-specific personal paths or identifiers in repo-tracked docs, planning
   notes, changelog entries, issue comments, or user-facing examples:
   - do not include personal home-directory paths such as `C:\Users\<name>\...`,
     `/home/<name>/...`, institutional OneDrive paths, or other workstation-specific absolute
     paths unless the path itself is the subject of the contract being documented;
   - normalize examples to placeholders, repo-relative paths, environment variables, or generic
     install roots instead;
   - if a real external-install path must be documented, prefer stable vendor roots such as
     `C:\Program Files\...` over personal workstation locations;
   - before finalizing a docs/planning hygiene pass, do a quick search for leaked personal-path
     fragments if there is any chance examples were copied from a live shell session.
10a. Use all-lowercase names for new files and directories whenever FEMIC controls the path:
   - new canonical runtime package paths, docs files, metadata files, runbooks, config files, and
     generated artifact directories should default to lowercase names;
   - preserve mixed-case only when it is part of archival legacy evidence, upstream source payloads
     we are not renaming, or external tool/runtime contracts outside FEMIC control;
   - do not carry legacy mixed-case pathing forward into new canonical rebuild surfaces unless there
     is a concrete external-contract reason to do so.
11. Commit early and often using roadmap task/subtask granularity:
   - prefer small, thematic commits over large mixed commits;
   - create at least one commit per completed roadmap task (or tightly related subtask bundle);
   - reference the phase/task ID in commit messages when applicable (for example, `P19.12`).
   Do this continuously during implementation so progress is checkpointed without user prompting.
12. Treat GitHub issue hygiene as a required part of the development workflow:
   - before starting a new feature, bug, docs push, or other non-trivial task, ensure `gh` is
     available in the active shell and authenticated as the intended active GitHub user;
   - if `gh` is unavailable or unauthenticated, treat that as a workflow blocker for issue hygiene:
     stop, report the blocker clearly, and do not pretend the GitHub side of the workflow is current;
   - start with a non-mutating audit before editing issue state:
     - `gh issue list --state open`
     - `gh issue list --state closed`
     - `gh issue view <n> --json ...`
     so you understand the current title/body/label/state before mutating anything;
   - use GitHub built-in issue `Type` as the canonical work-kind field for FEMIC issues:
     `Bug`, `Feature`, or `Task`;
   - do not mirror issue `Type` into duplicate work-kind labels such as `bug`, `enhancement`,
     `feature`, or `task`;
   - use labels only for orthogonal metadata that `Type` does not express, such as platform,
     subsystem, or workflow tags (for example `documentation`, `windows`, `k3z`, `tsa29`,
     `patchworks`, `data`, `good first issue`, `help wanted`);
   - use GitHub to find an existing relevant open issue first; if none exists, create a new issue
     (`feature`, `bug`, `docs`, or similar as appropriate) before substantial implementation;
   - link the governing GitHub issue in `ROADMAP.md` when the task becomes active so roadmap notes
     and repo-hosted planning stay connected;
   - when work status changes materially, update the issue accordingly (comment, retitle, relabel,
     close on merge, or otherwise reconcile status) so the GitHub tracker reflects reality and does
     not leave dropped or duplicated work behind.
   - treat progress comments as mandatory, not optional:
     - when a roadmap task, roadmap subtask bundle, phase closeout, or equivalent milestone is
       completed, post a matching GitHub progress comment on the governing issue;
     - when the workflow uses parent/child issues, keep both the active child issue and the parent
       issue current with concise progress comments whenever status changes materially;
     - local updates in `ROADMAP.md`, `CHANGE_LOG.md`, commits, or chat do not substitute for the
       required GitHub comment trail;
     - before declaring a milestone wrapped up, verify that the required GitHub comment(s) were
       actually posted successfully from the active shell/session.
   - prefer `gh issue edit` for issue titles, bodies, and labels, but prefer `gh api graphql` for
     maintainer-authored comment edits and any metadata surface that `gh issue edit` handles
     poorly; document the exact successful command pattern in repo notes/docs if you need the
     GraphQL fallback.
   - when sending Markdown bodies to `gh` from PowerShell, prefer body files or quoted here-strings
     over inline escaped strings; avoid hand-built escape sequences that can inject control
     characters such as `\f`, `\r`, `\t`, or `\v` into issue text.
   - when closing an issue, add a final closeout comment first that summarizes what was implemented,
     points to the primary user-facing docs and relevant repo paths, states the validation outcome,
     and explains why any remaining caveats do not block closure; do not close issues with only an
     implicit or chat-only rationale.
13. Monitor the incoming issue ideas list in `planning/incoming_ideas.md` as part of normal task
    triage:
   - when the developer asks "what next" or otherwise invites the agent to propose follow-on work,
     consult `planning/incoming_ideas.md` alongside `ROADMAP.md`, `CHANGE_LOG.md`, and open GitHub
     issues;
   - if an incoming idea is adopted, reflect it in the normal planning surfaces as appropriate
     (`ROADMAP.md`, GitHub issue, branch creation, or similar);
   - once the developer explicitly green-lights running with an idea, edit
     `planning/incoming_ideas.md` to remove that idea from the queue or narrow it to the remaining
     unclaimed scope so the list stays current.
14. When working on Patchworks-facing changes, preserve the rebuild order:
   - if code or config changes affect ForestModel XML semantics in any way (for example exporter
     logic, silviculture YAML, seral YAML, treatment/state attributes, feature/product/account
     source labels, or curve construction), regenerate the relevant `yield/forestmodel*.xml`
     files before running `femic patchworks matrix-build`;
   - do not treat a successful matrix build against stale checked-in XML as validation of the new
     exporter/config change;
   - after regenerating XML, rerun matrix build so `features.csv`, `protoaccounts.csv`, and
     `accounts.csv` are synced to the same contract;
   - if the full `femic export patchworks` path is blocked by a known checkpoint/fragments seam,
     regenerate the XML through the lower-level bundle-table builder first, then run matrix build
     against the refreshed XML rather than skipping directly to matrix build.
15. Treat smoke-testing of known-working behavior as a required validation step, not an optional
   courtesy:
   - after any Patchworks-facing rebuild, do not report "all clear", "green light", or equivalent
     unless you have inspected the concrete rebuilt outputs that are most likely to reveal
     regressions in the touched surface;
   - "matrix build succeeded" is necessary but not sufficient when the changed surface already had
     known-good behavior before the edit;
   - choose a necessary-and-sufficient smoke test set for the actual change. This should usually
     include some combination of:
     - targeted inspection of regenerated `tracks/*/{features,protoaccounts,accounts}.csv`;
     - targeted inspection of the rebuilt ForestModel XML or curve tables;
     - checking representative known-good accounts, attributes, products, or targets that the
       change could plausibly break;
     - launching the most relevant representative Patchworks surfaces when the user-facing runtime
       behavior is part of the claimed success signal;
   - prefer a small number of representative, high-signal checks over rote exhaustive scanning, but
     those checks must be capable of catching obvious regressions in the changed contract;
   - when there is an obvious low-cost, high-reward direct check of the exact thing users will
     touch, do it proactively without waiting for the developer to remind or prompt you;
   - do not make the developer manually discover obvious regressions that could have been caught by
     a cheap direct inspection or launch smoke on the rebuilt output;
   - if you did not inspect the relevant rebuilt outputs directly, say so explicitly and do not
     present the result as verified.
16. Treat TSR/THLB runner selection and rerun equivalence as a contract surface, not an
   implementation detail:
   - before any TSR/THLB rerun, identify which execution lane you are using and whether it matches
     the question being asked:
     - `femic tsr thlb-netdown-run` is the generic flattened recipe/executability runner;
     - `femic tsr thlb-netdown-step-run` / `run_tsr_thlb_parent_step` are reviewed parent-step
       cumulative runners; and
     - MAP_ID / LU smoke runs are a separate validation lane from full-TSA runs;
   - if the user asks to confirm, recheck, stabilize, or compare a previously reported TSR/THLB
     benchmark result, default to the same runner, checkpoint, baseline signal, subset/full-TSA
     scope, and stop-line that produced the earlier result;
   - do not silently substitute a different runner just because it is easier or more generic;
   - if you intentionally change any of the following, tell the user before treating the result as
     comparable:
     - runner / command path;
     - checkpoint;
     - baseline signal;
     - full-TSA vs smoke/subset scope; or
     - target parent step / stop-line;
   - if the available runner cannot answer the user’s actual question, say so plainly before
     running anything and either choose the correct instrument or frame the fallback as a different
     check with a different answer surface;
   - if a rerun that was supposed to confirm a prior number produces a materially different result,
     stop and disclose that mismatch immediately before reframing, interpreting, or substituting a
     different metric;
   - never present a generic flattened THLB final-area result as though it were a parent-step
     cumulative benchmark reconciliation result unless the user explicitly asked for the flattened
     run surface;
   - for strict THLB reconstruction comparison work under `#128`-style analysis:
     - treat strict-vs-TSR as the governing benchmark;
     - treat strict-vs-reviewed as explanatory context only; and
     - do not escalate a parent step to a top-priority repair merely because it differs from the
       reviewed lane if the strict result is already close enough to TSR;
   - for THLB stepwise accounting across strict, reviewed, and comparison surfaces:
     - treat `net_removed_area_ha` as the canonical marginal metric;
     - require that it equal the true before/after change in currently active managed area caused
       by that step;
     - treat gross candidate/matched/touched areas as secondary diagnostics only; and
     - treat milestone/reference rows as cumulative checkpoints with no marginal deduction;
   - for THLB cumulative answers during step-by-step adjudication:
     - use `config/tsr/thlb_locked_chain_ledger.json` as the canonical chained source for locked
       cumulative remaining area and TSR cumulative deltas;
     - do not answer cumulative questions from branch-local bounded step artifacts; and
     - if a branch-local remaining area is mentioned for debugging, label it explicitly as
       non-cumulative;
   - for Windows multiprocessing safety, do not launch LU-parallel THLB parent-step reruns from
     stdin / here-string Python; use the CLI entrypoint or a saved script file instead.
17. Treat developer-imposed scope boundaries as a hard execution contract:
   - if the developer says `one step at a time`, `one bounded move`, or equivalent, do exactly one
     bounded unit of work before stopping and reporting;
   - a bounded unit means one of:
     - one code change;
18. Treat "raw source input" and "checkpoint" as mutually exclusive concepts:
   - a checkpoint is a derived intermediate artifact used for resume/debug only;
   - a checkpoint is never an acceptable substitute for raw source input when the
     task is to validate, rebuild, or debug the baseline geometry itself;
   - if the developer asks to start from raw geometry, use the actual upstream
     source dataset (for example the provincial VRI source plus the reviewed TSA
     boundary), not an instance-local checkpoint feather;
   - before diagnosing GLB/AFLB/THLB area mismatches, verify that the claimed
     raw source is truly materialized and readable rather than an annex pointer,
     cache stub, or other derived artifact.
     - one validation run;
     - one report rebuild; or
     - one issue/planning/docs update;
     not a bundle of several of those unless the developer explicitly asks for the bundle;
   - do not combine implementation plus broad rerun plus downstream validation into one "helpful"
     bundle without explicit approval;
   - before any expensive or broad command, state plainly:
     - the exact command;
     - the single question it answers; and
     - why a smaller run is not enough;
   - after each bounded unit:
     - stop;
     - report the result;
     - and wait for the next instruction rather than doing "while I'm here" follow-on work;
   - for active TSR/THLB adjudication work, do not run downstream parent steps or whole-lane suffixes
     when the current question is about one parent step only;
   - treat scope expansion as a correctness failure, not as initiative;
   - if the developer says `scope breach`, immediately:
     - stop any running background work;
     - return to the last explicitly agreed bounded unit; and
     - do not propose broader execution until the developer re-expands scope.

Treat these steps as the minimum bar for every milestone so manual reminders are not required.

## TSR Intelligence Quickstart

When working with BC Timber Supply Review source documents:

1. Refresh the canonical TSR registry:
   - `python -m femic tsr index`
2. Fetch only the TSA you are actively working on:
   - `python -m femic tsr fetch --tsa 29`
3. Extract candidate facts for that TSA:
   - `python -m femic tsr extract --tsa 29`
4. Initialize the reviewed instance-local overlay:
   - `python -m femic tsr overlay-init --instance-root external/femic-tsa29-instance --tsa 29`
5. Inspect adopted-vs-canonical state:
   - `python -m femic tsr overlay-report --instance-root external/femic-tsa29-instance`

Important boundary:
- canonical discovery artifacts live under `metadata/tsr/`
- cached PDFs live under `~/.femic/tsr/` by default
- reviewed/adopted instance-local facts live under `config/tsr/overlay.yaml`
- do not auto-promote unresolved candidate facts into live instance contracts
