# Phase close-out report: P126 Refresh acquisition-request instance pins

Phase: P126 Refresh acquisition-request instance pins
Parent issue: #554
Pull request: #556, `feature/p126-acquisition-request-pins` into `main`
Evidence head: `c84d073`, the commit that bumps the GNN and TSA 27 gitlinks and updates the planning surfaces
Report commit: the commit that refreshes this report. Its CI run is posted on the pull request.
Date: 2026-11-02
Status: queued for approval. Not merged.

## Recommendation

Approve these actions. The agent carries them out in this order, and reads back each result.

1. Squash-merge pull request #556, and delete the branch `feature/p126-acquisition-request-pins`.
2. Close child issue #555 with a closeout comment that cites the merge commit.
3. Close parent issue #554 with a closeout comment that cites the merge commit.
4. Do not create a new parent FEMIC phase. The acquisition-request phases are complete.

Settings changes, each with its exact command. Each one runs only after its own approval.

- None.

## 1. Objectives and acceptance

| Criterion | Evidence | Status |
| --- | --- | --- |
| Bump GNN to the merged P13 head | `a65d62b` -> `f953f87` (GNN PR #82) | met |
| Bump TSA 27 to the merged P8 head | `3aacbea` -> `8961ab7` (TSA 27 PR #45) | met |
| Leave TSA 23 unchanged | `83ddbfd` (TSA 23 PR #54) | met |
| No FEMIC source, test, contract, model, or instance content change | The change set is two gitlinks plus `ROADMAP.md` and `CHANGE_LOG.md` | met |
| Available verification passes, or the limitation is recorded | `git diff --cached --submodule` shows only the two gitlinks; the parent has no seeded validator/dashboard | met with the stated limit |

## 2. Workflow compliance

- Parent issue before the branch: issue #554 was created before the branch; child
  issue #555 was created immediately after and linked as a sub-issue.
- Branch from `main`: `feature/p126-acquisition-request-pins` was created from
  `origin/main` at `86097ae`.
- Commit messages that start with task IDs: `c84d073` (`P126.1 ...`) and the report
  commit.
- Gates for each commit: section 3.
- Roadmap and changelog in step: both were changed in `c84d073`; the report commit
  only adds this report.
- Child issues closed with closeout evidence: #555 remains open until the merge is
  approved, per the workflow.
- Approval gates: the maintainer's `go` instruction approved the pin refresh; merge,
  branch deletion, and issue closure wait for approval of this report.

## 3. Gate evidence

At `c84d073`:

```text
external/femic-gnn-instance   | 2 +-
external/femic-tsa27-instance | 2 +-
2 files changed, 2 insertions(+), 2 deletions(-)
```

Gitlink values:

```text
external/femic-gnn-instance   f953f87181756c14da8f0efa131e9efc21d46cb5
external/femic-tsa27-instance 8961ab75c0cef36aa9fd73f8bc2070dbce4529f6
external/femic-tsa23-instance 83ddbfd0bdad53de5d85dfc40d54a869ba882555
```

The parent repository has no seeded `scripts/check_workflow.py` or
`scripts/dashboard.py`; the available CI jobs are `build`, `guard`, and
`package-release-checks`.

## 4. CI evidence

| Run ID | Head commit | Conclusion | Notes |
| --- | --- | --- | --- |
| 41409438747, 41409438742, 41409438750 | `9de118b` | success | `build` passed in 4m17s; `guard` in 8s; `package-release-checks` in 1m14s. The only later change is this CI-table refresh. |

## 5. Deviations

| Deviation | Cause | Remedy |
| --- | --- | --- |
| No parent workflow validator or dashboard | The FEMIC repository does not ship the seeded scripts | The gitlink diff, submodule values, and CI jobs are the available evidence |
| The worktree submodules are uninitialized | The pin bump changes gitlinks without checking out the instance worktrees | The committed values are verified with `git diff --cached --submodule` and match the merged instance PRs |

## 6. Next phase

Recommended default: **no new parent FEMIC phase**.

The GNN P13 and TSA 27 P8 acquisition-request packages are complete and pinned. The
next step is to send the request packages to the partner channels and wait for data.
No model phase is proposed until the data arrive.

## 7. Decision

- [ ] Approve as written.
- [ ] Approve with the changes stated here: <changes>.
