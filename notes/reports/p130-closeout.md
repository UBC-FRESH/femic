# Phase close-out report: P130 Refresh the GNN fit-pipeline pin

Phase: P130 Refresh the GNN fit-pipeline pin
Parent issue: #566
Pull request: #568, `feature/p130-gnn-fit-pin` into `main`
Evidence head: `e997167`, the commit that bumps the GNN gitlink and updates the planning surfaces
Report commit: the commit that refreshes this report. Its CI run is posted on the pull request.
Date: 2026-11-02
Status: queued for approval. Not merged.

## Recommendation

Approve these actions. The agent carries them out in this order, and reads back each result.

1. Squash-merge pull request #568, and delete the branch `feature/p130-gnn-fit-pin`.
2. Close child issue #567 with a closeout comment that cites the merge commit.
3. Close parent issue #566 with a closeout comment that cites the merge commit.
4. Do not create a new parent FEMIC phase. The fit pipeline is pinned.

Settings changes, each with its exact command. Each one runs only after its own approval.

- None.

## 1. Objectives and acceptance

| Criterion | Evidence | Status |
| --- | --- | --- |
| Bump GNN to the merged P16 head | `9402e12` -> `f7d9dfb` (GNN PR #93) | met |
| Leave TSA 27 and TSA 23 unchanged | TSA 27 `8961ab7`; TSA 23 `83ddbfd` | met |
| No FEMIC source, test, contract, model, or instance content change | The change set is one gitlink plus `ROADMAP.md` and `CHANGE_LOG.md` | met |
| Available verification passes, or the limitation is recorded | `git diff --cached --submodule` shows only the GNN gitlink; the parent has no seeded validator/dashboard | met with the stated limit |

## 2. Workflow compliance

- Parent issue before the branch: issue #566 was created before the branch; child
  issue #567 was created immediately after and linked as a sub-issue.
- Branch from `main`: `feature/p130-gnn-fit-pin` was created from `origin/main`
  at `12b007c`.
- Commit messages that start with task IDs: `e997167` (`P130.1 ...`) and the report
  commit.
- Gates for each commit: section 3.
- Roadmap and changelog in step: both were changed in `e997167`; the report commit
  only adds this report.
- Child issues closed with closeout evidence: #567 remains open until the merge is
  approved, per the workflow.
- Approval gates: the maintainer's `go` instruction approved the pin refresh; merge,
  branch deletion, and issue closure wait for approval of this report.

## 3. Gate evidence

At `e997167`:

```text
external/femic-gnn-instance | 2 +-
1 file changed, 1 insertion(+), 1 deletion(-)
```

Gitlink values:

```text
external/femic-gnn-instance   f7d9dfbd36a5b3c3fdd16ba9992d2db698129d1d
external/femic-tsa27-instance 8961ab75c0cef36aa9fd73f8bc2070dbce4529f6
external/femic-tsa23-instance 83ddbfd0bdad53de5d85dfc40d54a869ba882555
```

The parent repository has no seeded `scripts/check_workflow.py` or
`scripts/dashboard.py`; the available CI jobs are `build`, `guard`, and
`package-release-checks`.

## 4. CI evidence

| Run ID | Head commit | Conclusion | Notes |
| --- | --- | --- | --- |
| 41419866961, 41419867017, 41419866957 | `7b1fd9c` | success | `build` passed in 3m34s; `guard` in 11s; `package-release-checks` in 1m18s. The only later change is this CI-table refresh. |

## 5. Deviations

| Deviation | Cause | Remedy |
| --- | --- | --- |
| No parent workflow validator or dashboard | The FEMIC repository does not ship the seeded scripts | The gitlink diff, submodule values, and CI jobs are the available evidence |
| The worktree submodule is uninitialized | The pin bump changes a gitlink without checking out the instance worktree | The committed value is verified with `git diff --cached --submodule` and matches GNN PR #93 |

## 6. Next phase

Recommended default: **no new phase** until the private upload arrives.

The ingest, dry-run, fit, and pre-registration chain is complete and pinned. The next
event is Ken's LAZ upload; run the P14 ingest kit and review coverage before the fit.

## 7. Decision

- [ ] Approve as written.
- [ ] Approve with the changes stated here: <changes>.
