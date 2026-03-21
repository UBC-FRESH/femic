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

Do not treat symlinked pointer files in `external/femic-public-data` as usable
inputs until `datalad get` has completed.

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

Treat these steps as the minimum bar for every milestone so manual reminders are not required.
