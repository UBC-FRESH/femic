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
   - BatchTIPSY freshness: treat `02_input-tsaXX.dat` as canonical; XLSX is a
     mirror only. Do not assume a stale block means rerun is required without
     checking whether DAT content actually changed.

For the compact docs source of truth behind these operating notes, see:
- `docs/reference/contracts/index.rst`
- `docs/reference/contracts/repo-runtime-invariants.rst`
- `docs/reference/contracts/instance-and-data-roots.rst`
- `docs/reference/contracts/stage-boundaries-and-canonical-artifacts.rst`
- `docs/reference/contracts/recovery-and-external-runtime-boundaries.rst`

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
7. After each deliverable or roadmap milestone, append the same progress summary reported to the user
   to `CHANGE_LOG.md` (Markdown format, newest entries last) so the repository carries an auditable
   narrative of changes.
8. When documentation files change, run `sphinx-build -b html docs _build/html -W` (or the equivalent
   project helper) before finalising the work to ensure Sphinx warnings are treated as errors.
9. Before launching a new task or plan, review the latest entries in `CHANGE_LOG.md` alongside the
   roadmap notes to confirm the proposed work is consistent with recorded progress and avoids
   backtracking.
10. Commit early and often using roadmap task/subtask granularity:
   - prefer small, thematic commits over large mixed commits;
   - create at least one commit per completed roadmap task (or tightly related subtask bundle);
   - reference the phase/task ID in commit messages when applicable (for example, `P19.12`).
   Do this continuously during implementation so progress is checkpointed without user prompting.
11. Treat GitHub issue hygiene as a required part of the development workflow:
   - before starting a new feature, bug, docs push, or other non-trivial task, ensure `gh` is
     available in the active shell and authenticated as the intended active GitHub user;
   - use GitHub to find an existing relevant open issue first; if none exists, create a new issue
     (`feature`, `bug`, `docs`, or similar as appropriate) before substantial implementation;
   - link the governing GitHub issue in `ROADMAP.md` when the task becomes active so roadmap notes
     and repo-hosted planning stay connected;
   - when work status changes materially, update the issue accordingly (comment, retitle, relabel,
     close on merge, or otherwise reconcile status) so the GitHub tracker reflects reality and does
     not leave dropped or duplicated work behind.
   - when closing an issue, add a final closeout comment first that summarizes what was implemented,
     points to the primary user-facing docs and relevant repo paths, states the validation outcome,
     and explains why any remaining caveats do not block closure; do not close issues with only an
     implicit or chat-only rationale.
12. Monitor the incoming issue ideas list in `planning/incoming_ideas.md` as part of normal task
    triage:
   - when the developer asks "what next" or otherwise invites the agent to propose follow-on work,
     consult `planning/incoming_ideas.md` alongside `ROADMAP.md`, `CHANGE_LOG.md`, and open GitHub
     issues;
   - if an incoming idea is adopted, reflect it in the normal planning surfaces as appropriate
     (`ROADMAP.md`, GitHub issue, branch creation, or similar);
   - once the developer explicitly green-lights running with an idea, edit
     `planning/incoming_ideas.md` to remove that idea from the queue or narrow it to the remaining
     unclaimed scope so the list stays current.

Treat these steps as the minimum bar for every milestone so manual reminders are not required.
