# Phase close-out report: P124 Refresh pins after instance feasibility phases

Phase: P124 Refresh pins after instance feasibility phases
Parent issue: #548
Pull request: #550, `feature/p124-post-feasibility-pin-refresh` into `main`
Evidence head: `8238f41`, the commit that bumps the GNN and TSA 27 gitlinks and updates the planning surfaces
Report commit: the commit that refreshes this report. Its CI run is posted on the pull request.
Date: 2026-11-02
Status: queued for approval. Not merged.

## Recommendation

Approve these actions. The agent carries them out in this order, and reads back each result.

1. Squash-merge pull request #550, and delete the branch `feature/p124-post-feasibility-pin-refresh`.
2. Close child issue #549 with a closeout comment that cites the merge commit.
3. Close parent issue #548 with a closeout comment that cites the merge commit.
4. Do not create a new parent FEMIC phase. The instance feasibility phases are complete.

Settings changes, each with its exact command. Each one runs only after its own approval.

- None.

## 1. Objectives and acceptance

| Criterion | Evidence | Status |
| --- | --- | --- |
| Bump the GNN pin to the merged P12 head | `316c7d0` -> `a65d62b` (GNN PR #79) | met |
| Bump the TSA 27 pin to the merged P7 head | `59c98e5` -> `3aacbea` (TSA 27 PR #42) | met |
| Leave the TSA 23 pin unchanged | `4dc9c31` (TSA 23 PR #51) | met |
| No FEMIC source, test, contract, model, or instance content change | The change set is two gitlinks plus `ROADMAP.md` and `CHANGE_LOG.md` | met |
| Available verification passes, or the limitation is recorded | `git diff --cached --submodule` shows only the two gitlinks; the parent has no seeded validator/dashboard | met with the stated limit |

## 2. Workflow compliance

- Parent issue before the branch: issue #548 was created before the branch; child
  issue #549 was created immediately after and linked as a sub-issue.
- Branch from `main`: `feature/p124-post-feasibility-pin-refresh` was created from
  `origin/main` at `f8f23a8`.
- Commit messages that start with task IDs: `8238f41` (`P124.1 ...`) and the report
  commit.
- Gates for each commit: section 3.
- Roadmap and changelog in step: both were changed in `8238f41`; the report commit
  only adds this report.
- Child issues closed with closeout evidence: #549 remains open until the merge is
  approved, per the workflow.
- Approval gates: the maintainer's `go` instruction approved the pin refresh; merge,
  branch deletion, and issue closure wait for approval of this report.

## 3. Gate evidence

At `8238f41`:

```text
external/femic-gnn-instance   | 2 +-
external/femic-tsa27-instance | 2 +-
2 files changed, 2 insertions(+), 2 deletions(-)
```

Gitlink values:

```text
external/femic-gnn-instance   a65d62bfcb62bb880a21c84d8115ca71639bfc33
external/femic-tsa27-instance 3aacbea397cbb0a692356530eff4e2f575b05b15
external/femic-tsa23-instance 4dc9c317210494caab1ab316e29748e1ffd982ef
```

The parent repository has no seeded `scripts/check_workflow.py` or
`scripts/dashboard.py`; the available CI jobs are `build`, `guard`, and
`package-release-checks`.

## 4. CI evidence

| Run ID | Head commit | Conclusion | Notes |
| --- | --- | --- | --- |
| pending | report commit | pending | The report commit's `build`, `guard`, and `package-release-checks` runs are posted on pull request #550 before approval. |

## 5. Deviations

| Deviation | Cause | Remedy |
| --- | --- | --- |
| No parent workflow validator or dashboard | The FEMIC repository does not ship the seeded scripts | The gitlink diff, submodule values, and CI jobs are the available evidence |
| The worktree submodules are uninitialized | The pin bump changes gitlinks without checking out the instance worktrees | The committed values are verified with `git diff --cached --submodule` and match the merged instance PRs |

## 6. Next phase

Recommended default: **no new parent FEMIC phase**.

The instance feasibility phases are complete:
- GNN P12: no-go; needs point clouds over recent plots or recent plots in the footprint.
- TSA 27 P7: no-go; needs re-measured overlapping plots or contemporary point clouds.
- TSA 23 P124: not started; no compiled TSA 23 WS4 dataset is present, and the BA
  pilot is a 25 m cell product rather than a fragment table.

Reason: the remaining work is data acquisition and a compiled consumer dataset, not
a parent FEMIC code phase.

## 7. Decision

- [ ] Approve as written.
- [ ] Approve with the changes stated here: <changes>.
