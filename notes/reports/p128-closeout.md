# Phase close-out report: P128 Refresh the GNN ingest pin

Phase: P128 Refresh the GNN ingest pin
Parent issue: #560
Pull request: #562, `feature/p128-gnn-ingest-pin` into `main`
Evidence head: `44db2b9`, the commit that bumps the GNN gitlink and updates the planning surfaces
Report commit: the commit that refreshes this report. Its CI run is posted on the pull request.
Date: 2026-11-02
Status: queued for approval. Not merged.

## Recommendation

Approve these actions. The agent carries them out in this order, and reads back each result.

1. Squash-merge pull request #562, and delete the branch `feature/p128-gnn-ingest-pin`.
2. Close child issue #561 with a closeout comment that cites the merge commit.
3. Close parent issue #560 with a closeout comment that cites the merge commit.
4. Do not create a new parent FEMIC phase. The ingest readiness work is pinned.

Settings changes, each with its exact command. Each one runs only after its own approval.

- None.

## 1. Objectives and acceptance

| Criterion | Evidence | Status |
| --- | --- | --- |
| Bump GNN to the merged P14 head | `fdc949b` -> `e338821` (GNN PR #86) | met |
| Leave TSA 27 and TSA 23 unchanged | TSA 27 `8961ab7`; TSA 23 `83ddbfd` | met |
| No FEMIC source, test, contract, model, or instance content change | The change set is one gitlink plus `ROADMAP.md` and `CHANGE_LOG.md` | met |
| Available verification passes, or the limitation is recorded | `git diff --cached --submodule` shows only the GNN gitlink; the parent has no seeded validator/dashboard | met with the stated limit |

## 2. Workflow compliance

- Parent issue before the branch: issue #560 was created before the branch; child
  issue #561 was created immediately after and linked as a sub-issue.
- Branch from `main`: `feature/p128-gnn-ingest-pin` was created from `origin/main`
  at `d70a77e`.
- Commit messages that start with task IDs: `44db2b9` (`P128.1 ...`) and the report
  commit.
- Gates for each commit: section 3.
- Roadmap and changelog in step: both were changed in `44db2b9`; the report commit
  only adds this report.
- Child issues closed with closeout evidence: #561 remains open until the merge is
  approved, per the workflow.
- Approval gates: the maintainer's `go` instruction approved the pin refresh; merge,
  branch deletion, and issue closure wait for approval of this report.

## 3. Gate evidence

At `44db2b9`:

```text
external/femic-gnn-instance | 2 +-
1 file changed, 1 insertion(+), 1 deletion(-)
```

Gitlink values:

```text
external/femic-gnn-instance   e338821998044d1a3b5ad31e0cca555f79e8545d
external/femic-tsa27-instance 8961ab75c0cef36aa9fd73f8bc2070dbce4529f6
external/femic-tsa23-instance 83ddbfd0bdad53de5d85dfc40d54a869ba882555
```

The parent repository has no seeded `scripts/check_workflow.py` or
`scripts/dashboard.py`; the available CI jobs are `build`, `guard`, and
`package-release-checks`.

## 4. CI evidence

| Run ID | Head commit | Conclusion | Notes |
| --- | --- | --- | --- |
| pending | report commit | pending | The report commit's `build`, `guard`, and `package-release-checks` runs are posted on pull request #562 before approval. |

## 5. Deviations

| Deviation | Cause | Remedy |
| --- | --- | --- |
| No parent workflow validator or dashboard | The FEMIC repository does not ship the seeded scripts | The gitlink diff, submodule values, and CI jobs are the available evidence |
| The worktree submodule is uninitialized | The pin bump changes a gitlink without checking out the instance worktree | The committed value is verified with `git diff --cached --submodule` and matches GNN PR #86 |

## 6. Next phase

Recommended default: **no new parent FEMIC phase**.

The ingest kit is ready and the P13 request is clarified as a fallback. The next
event is the private LAZ upload. When it arrives, run the P14 ingest kit and review
the coverage before any derived-public product is created.

## 7. Decision

- [ ] Approve as written.
- [ ] Approve with the changes stated here: <changes>.
