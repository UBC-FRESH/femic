# P120 INV-01 inventory closure — close-out package

## Header

Phase: P120
Parent issue: #536
Pull request: https://github.com/UBC-FRESH/femic/pull/538 (draft)
Evidence head: `6c84405` on `feature/p120-inv01-inventory`
Report date: 2026-11-01
Status: blocked by baseline repository gates and pending CI; do not merge without maintainer approval

## Recommendation

1. Approve the BA-only default product.
2. Keep height and volume as research-only attributes with explicit card/config paths.
3. Do not merge the phase pull request until the full repository gates are green or the maintainer explicitly accepts a documented baseline exception.
4. After approval, merge the parent and public-instance pull requests and advance the instance pointer.

## Objectives and acceptance

| Criterion | Evidence | Status |
| --- | --- | --- |
| Height tested on strict and time-lag sets | strict 19 in range, RMSE 2.54 m; TSA 23 strict 6, RMSE 4.18 m | met |
| Default contains only supported attributes | `config/inventory/default.yaml` contains BA only | met |
| Public docs state coverage and limits | instance and parent docs updated on branch | met |
| Tests, lint, types, Sphinx pass | tests and Sphinx pass; ruff/mypy have baseline failures | not met |
| Pull request queued for approval | parent #538 and instance #46 are drafts | pending |

## Workflow compliance

- Parent issue #536 and child issue #537 exist; child is linked as a sub-issue.
- The phase branch is `feature/p120-inv01-inventory`.
- The P120 commit starts with the task ID.
- The roadmap and changelog were updated in the same change set.
- The public-instance change is on a separate branch and is not merged: https://github.com/UBC-FRESH/femic-tsa23-instance/pull/46.

### Deviations

- The preceding INV-01 work was merged before P120 existed and did not use
  `feature/p120-*` branches, P120 issues, task-ID commit prefixes, or per-phase
  closeout reports. This report records that history as a deviation; it cannot
  make the earlier work compliant retroactively.
- The repository has no `scripts/check_workflow.py` or `scripts/dashboard.py`,
  so the seed workflow validator/dashboard cannot be run in this checkout.
- Full-repository `ruff` and `mypy` gates are red with pre-existing failures,
  not introduced by P120. The P120 change is documentation/config only.

## Gate evidence

- `PYTHONPATH=src pytest -q tests/test_lidar_inventory.py` -> 21 passed.
- `sphinx-build -b html docs _build/html -W` -> build succeeded.
- `ruff check src tests` -> 696 errors, baseline.
- `mypy src` -> 23 errors, baseline.
- One-row default-config CLI smoke test resolved `tsa23-idf-ba-2026`.
- `resolve_inventory_model_path` correctly rejects `height` and `volume` on the
  BA-only default config.

## CI evidence

Parent PR #538: `guard` passed; `build` and `package-release-checks` were pending
at the last check. The instance PR has no checks configured. CI must be
rechecked before merge.

## Deviations and risks

- The public instance currently still defaults to height + BA until the instance
  pull request is approved and merged.
- The strict validation population is 38 plots; TSA 23 has only 7 independent
  plots. The BA result remains a pilot, not operational.
- Height and volume are withheld from the default because their independent
  errors are not defensible.

## Next phase

No next phase is proposed until P120 is approved or the maintainer chooses a
different product decision. The immediate next action is the gate/CI review and
the two pull requests.

## Decision

Approve the BA-only default and merge only after the gate deviation is resolved
or explicitly waived. Do not promote volume or height.
