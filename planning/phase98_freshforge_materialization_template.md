# P98 FreshForge Model-Instance Materialization Template

## Purpose

Recent MKRF, TFL6, and TSA29 deployment tests showed that the manual
model-instance bootstrap ritual is too fragile for new users. The documented
sequence is deterministic, but it crosses too many tools: Git submodules,
repo-root virtual environments, FEMIC installation, FreshForge installation,
DataLad, git-annex, special remote enablement, and targeted payload
materialization.

P98 records the parent FEMIC plan for a reusable FreshForge workflow template
that can be specialized by small instance-owned overlay configuration. The
goal is to make the ritual executable and inspectable instead of asking users
to manually reproduce it from prose.

The execution-surface decision is recorded in
`planning/phase98_materialization_execution_surface.md`: P98.4 should start as
a FEMIC-owned optional FreshForge provider namespace with generic,
config-driven nodes, while instance repositories supply only small overlay
YAML files.

## Planned Workflow Family

The first generic materialization workflow should cover these node families:

1. toolchain check for Git, Python, FEMIC, FreshForge, DataLad, and git-annex;
2. submodule initialization/update for the requested model instance;
3. repo-root virtual-environment creation or validation;
4. package install check for FEMIC and any instance-owned adapter packages;
5. git-annex repository initialization and `arbutus-s3` enablement;
6. targeted `datalad get` or `git annex get` for required model/data paths;
7. annex availability audit for required payload families; and
8. user-facing materialization report.

## Overlay Configuration

The reusable template should be driven by a small instance overlay rather than
hardcoded instance names. Expected overlay fields:

- instance path;
- special remote name, defaulting to `arbutus-s3`;
- required materialization paths;
- optional public-data mirror paths;
- install extras or instance package paths; and
- report output path.

## Boundaries

- P98 is a planned parent FEMIC/FreshForge workflow family, not part of the
  first TFL6 FreshForge model-build workflow.
- The template should not make MKRF, TFL6, TSA29, or any future example
  instance a core FEMIC dependency.
- A tiny bootstrap script may be needed later because FreshForge itself must
  exist before it can run the workflow. The deterministic ritual should still
  live in the FreshForge workflow, not in a bespoke per-instance script.
