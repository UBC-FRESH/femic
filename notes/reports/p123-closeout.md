# Phase close-out report: P123 Refresh merged instance pins

Phase: P123 Refresh merged instance pins
Parent issue: #545
Pull request: #547, `feature/p123-instance-pin-refresh` into `main`
Evidence head: `cbb037b`, the commit that bumps the three gitlinks and updates the planning surfaces
Report commit: the commit that refreshes this report. Its CI run is posted on the pull request.
Date: 2026-11-02
Status: queued for approval. Not merged.

## Recommendation

Approve these actions. The agent carries them out in this order, and reads back each result.

1. Squash-merge pull request #547, and delete the branch `feature/p123-instance-pin-refresh`.
2. Close child issue #546 with a closeout comment that cites the merge commit.
3. Close parent issue #545 with a closeout comment that cites the merge commit.
4. Do not create a new parent FEMIC phase for this work. The next inventory
   proposals belong to the instance repositories: GNN P12 point-cloud feasibility,
   TSA 27 P7 ALS feasibility, and optionally TSA 23 P124 BA-only consumer test.

Settings changes, each with its exact command. Each one runs only after its own approval.

- None.

## 1. Objectives and acceptance

| Criterion | Evidence | Status |
| --- | --- | --- |
| Bump the GNN pin to the merged P11 head | `7103af5` -> `316c7d0` (GNN PR #76) | met |
| Bump the TSA 27 pin to the merged P6 head | `ec81d0b` -> `59c98e5` (TSA 27 PR #39) | met |
| Bump the TSA 23 pin to the merged P123 head | `4170451` -> `4dc9c31` (TSA 23 PR #51) | met |
| No FEMIC source, test, contract, model, or instance content change | `git diff --cached --stat` shows only the three gitlinks; the other changes are `ROADMAP.md` and `CHANGE_LOG.md` | met |
| Available verification passes, or the limitation is recorded | `git submodule status` shows the new commits; the parent repository has no `scripts/check_workflow.py` or `scripts/dashboard.py`, so the pin bump is verified by the gitlink diff and the merged instance PRs | met with the stated limit |

## 2. Workflow compliance

- Parent issue before the branch: issue #545 was created before the branch; child
  issue #546 was created immediately after and linked as a sub-issue.
- Branch from `main`: `feature/p123-instance-pin-refresh` was created from
  `origin/main` at `c34181b`.
- Commit messages that start with task IDs: `cbb037b` (`P123.1 ...`) and the
  report commit.
- Gates for each commit: section 3.
- Roadmap and changelog in step: both were changed in `cbb037b`; the report commit
  only adds this report.
- Child issues closed with closeout evidence: #546 remains open until the merge is
  approved, per the workflow.
- Approval gates: the maintainer's `go` instruction approved the merge/closeout
  sequence; merge, branch deletion, and issue closure are executed only after this
  report is approved.
- No settings, tag, release, or package publication is included.

## 3. Gate evidence

Submodule verification at `cbb037b`:

```text
-316c7d059125109964639f39b23f81151e252b1c external/femic-gnn-instance
-4dc9c317210494caab1ab316e29748e1ffd982ef external/femic-tsa23-instance
-59c98e5d4d0feed83c73a4e5088c8669eaf2f35a external/femic-tsa27-instance
```

Gitlink diff:

```text
external/femic-gnn-instance   | 2 +-
external/femic-tsa23-instance | 2 +-
external/femic-tsa27-instance | 2 +-
3 files changed, 3 insertions(+), 3 deletions(-)
```

The parent repository has no `scripts/check_workflow.py` or `scripts/dashboard.py`;
the available CI jobs are `build`, `guard`, and `package-release-checks`.

## 4. CI evidence

| Run ID | Head commit | Conclusion | Notes |
| --- | --- | --- | --- |
| 41400594335, 41400594349, 41400594340 | `516b337` | success | `build` passed in 3m53s; `guard` passed in 9s; `package-release-checks` passed in 1m7s. The only later change is the CI-table refresh in this report. |

## 5. Deviations

| Deviation | Cause | Remedy |
| --- | --- | --- |
| No parent workflow validator or dashboard | The FEMIC repository does not ship the seeded `scripts/check_workflow.py` or `scripts/dashboard.py` | The gitlink diff, submodule status, and CI jobs are recorded as the available evidence |
| The worktree submodules are uninitialized, so `git submodule status` prefixes the commits with `-` | The pin bump changes gitlinks without checking out the instance worktrees | The committed gitlink values are verified with `git diff --cached --submodule` and match the merged instance PRs |

## 6. Next phase

Recommended default: **no new parent FEMIC phase**. The pin refresh is complete.

The next work is in the instance repositories, if the maintainer continues the
inventory track:
- GNN P12 point-cloud inventory feasibility.
- TSA 27 P7 ALS inventory feasibility.
- Optional TSA 23 P124 BA-only consumer test.

Reason: the parent repository's role here is the pin, not new model work; the
instance phases already carry the proposed scope and acceptance criteria.

## 7. Decision

- [ ] Approve as written.
- [ ] Approve with the changes stated here: <changes>.
