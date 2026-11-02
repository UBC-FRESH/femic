# Phase close-out report: P125 Refresh the TSA 23 consumer-test pin

Phase: P125 Refresh the TSA 23 consumer-test pin
Parent issue: #551
Pull request: #553, `feature/p125-tsa23-consumer-pin` into `main`
Evidence head: `529bcb0`, the commit that bumps the TSA 23 gitlink and updates the planning surfaces
Report commit: the commit that refreshes this report. Its CI run is posted on the pull request.
Date: 2026-11-02
Status: queued for approval. Not merged.

## Recommendation

Approve these actions. The agent carries them out in this order, and reads back each result.

1. Squash-merge pull request #553, and delete the branch `feature/p125-tsa23-consumer-pin`.
2. Close child issue #552 with a closeout comment that cites the merge commit.
3. Close parent issue #551 with a closeout comment that cites the merge commit.
4. Do not create a new parent FEMIC phase. The instance consumer-test phase is complete.

Settings changes, each with its exact command. Each one runs only after its own approval.

- None.

## 1. Objectives and acceptance

| Criterion | Evidence | Status |
| --- | --- | --- |
| Bump TSA 23 to the merged P124 head | `4dc9c31` -> `83ddbfd` (TSA 23 PR #54) | met |
| Leave GNN and TSA 27 unchanged | GNN `a65d62b`; TSA 27 `3aacbea` | met |
| No FEMIC source, test, contract, model, or instance content change | The change set is one gitlink plus `ROADMAP.md` and `CHANGE_LOG.md` | met |
| Available verification passes, or the limitation is recorded | `git diff --cached --submodule` shows only the TSA 23 gitlink; the parent has no seeded validator/dashboard | met with the stated limit |

## 2. Workflow compliance

- Parent issue before the branch: issue #551 was created before the branch; child
  issue #552 was created immediately after and linked as a sub-issue.
- Branch from `main`: `feature/p125-tsa23-consumer-pin` was created from
  `origin/main` at `858ca1c`.
- Commit messages that start with task IDs: `529bcb0` (`P125.1 ...`) and the report
  commit.
- Gates for each commit: section 3.
- Roadmap and changelog in step: both were changed in `529bcb0`; the report commit
  only adds this report.
- Child issues closed with closeout evidence: #552 remains open until the merge is
  approved, per the workflow.
- Approval gates: the maintainer's `go` instruction approved the pin refresh; merge,
  branch deletion, and issue closure wait for approval of this report.

## 3. Gate evidence

At `529bcb0`:

```text
external/femic-tsa23-instance | 2 +-
1 file changed, 1 insertion(+), 1 deletion(-)
```

Gitlink values:

```text
external/femic-gnn-instance   a65d62bfcb62bb880a21c84d8115ca71639bfc33
external/femic-tsa27-instance 3aacbea397cbb0a692356530eff4e2f575b05b15
external/femic-tsa23-instance 83ddbfd0bdad53de5d85dfc40d54a869ba882555
```

The parent repository has no seeded `scripts/check_workflow.py` or
`scripts/dashboard.py`; the available CI jobs are `build`, `guard`, and
`package-release-checks`.

## 4. CI evidence

| Run ID | Head commit | Conclusion | Notes |
| --- | --- | --- | --- |
| 41407024144, 41407024289, 41407024224 | `3c1e850` | success | `build` passed in 4m20s; `guard` in 9s; `package-release-checks` in 1m10s. The only later change is this CI-table refresh. |

## 5. Deviations

| Deviation | Cause | Remedy |
| --- | --- | --- |
| No parent workflow validator or dashboard | The FEMIC repository does not ship the seeded scripts | The gitlink diff, submodule values, and CI jobs are the available evidence |
| The worktree submodule is uninitialized | The pin bump changes a gitlink without checking out the instance worktree | The committed value is verified with `git diff --cached --submodule` and matches TSA 23 PR #54 |

## 6. Next phase

Recommended default: **no new parent FEMIC phase**.

The TSA 23 P124 consumer test is complete. The BA pilot is consumer-readable as a
report-only attribute and remains non-operational. A production use would need a
refit, more plots, and an explicit model decision; none is proposed here.

## 7. Decision

- [ ] Approve as written.
- [ ] Approve with the changes stated here: <changes>.
