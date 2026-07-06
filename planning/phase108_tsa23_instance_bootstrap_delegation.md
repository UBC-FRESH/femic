# Phase 108 TSA23 Instance Bootstrap Delegation Pilot

## Purpose

P108 is a controlled test of using Agent Workbench-style delegation on a real
FEMIC project launch. Codex acts as coordinator: it creates the phase structure,
GitHub issue tree, branch, budget/accounting surface, and supervisor ticket.
The delegated local supervisor is expected to execute the actual TSA23 instance
bootstrap work on the P108 branch.

## Project Intent

The target is a new standalone `femic-tsa23-instance` repository linked under
the parent FEMIC checkout at `external/femic-tsa23-instance`.

The instance is intended for a graduate-student MASc thesis modelling project
that needs a new Patchworks model. It should therefore resemble the TSA29
standalone instance structure more than the older teaching-only scaffolds, while
still borrowing the recent TFL 6 workflow discipline for planning, issue
hygiene, source provenance, FreshForge workflows, and student-facing
documentation trajectory.

## Reference Repositories

Use references carefully:

- `external/femic-tfl6-instance` is the process and workflow maturity
  reference: issue/roadmap discipline, source-layer planning, THLB/model-design
  phase sequencing, FreshForge workflow evolution, publication QA, and teaching
  docs.
- `external/femic-tsa29-instance` is the closer structural reference:
  standalone package shape, `pyproject.toml`, `src/`, tests, config, runbooks,
  docs, DataLad/git-annex publication policy, and instance-owned FEMIC
  extensions.

Do not copy TFL 6 or TSA29 modelling assumptions into TSA23. Any borrowed
surface must be recorded as copied, adapted, rejected, or deferred.

## Coordinator Accounting

Coordinator token and cash cost are part of the experiment.

The P108 coordinator launch span is recorded under ignored runtime path:

- `runtime/supervisor_tokens/p108_coordinator_launch/`

The start checkpoint was taken after initial audit and partial issue recovery,
so it is not a complete cost record for every token spent before P108 branch
creation. From the checkpoint onward, the coordinator launch/delegation setup
must be measured with Agent Workbench supervisor-token commands and summarized
before P108.1 closes.

The delegated supervisor must continue this discipline for any additional paid
coordinator spans. Local Ollama/Copilot worker tokens may be treated as zero
cash cost only when the run evidence shows they used the configured local model
path.

## Delegation Boundary

The delegated supervisor may:

- use `gh` to create or edit GitHub issues, comments, and a P108 PR;
- create or initialize `UBC-FRESH/femic-tsa23-instance` if the repo is absent
  and authenticated `gh` access permits;
- add `external/femic-tsa23-instance` as a parent submodule;
- create and commit public-safe instance bootstrap files;
- update roadmap, changelog, and planning surfaces; and
- write an ignored final result report.

The delegated supervisor must not:

- merge the P108 PR;
- close parent issue `#302`;
- publish releases;
- run Patchworks, Matrix Builder, TIPSY/BTC, or broad model rebuilds;
- promote unreviewed TSA23 facts into accepted model contracts;
- track raw TSR PDF text, transcripts, provider details, credentials, or
  personal paths; or
- proceed past a real blocker by creating substitute artifacts.

## Expected Result

The expected output is not a runnable model. The expected output is a public-safe
TSA23 instance launch scaffold and a PR-ready parent FEMIC branch that Codex or
the maintainer can review, reject, or merge.

The delegated supervisor should stop with:

- P108 child issues updated and closed where complete;
- a P108 PR open from `feature/p108-tsa23-instance-bootstrap-delegation` to
  `main`;
- an ignored delegated result report under `runtime/agent_jobs/`; and
- exact blockers, if any, recorded with failed commands and error text.
