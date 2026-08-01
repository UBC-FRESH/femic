# Phase 110: Coordinator-Driven FEMIC Model Construction

Parent issue: [UBC-FRESH/femic#305](https://github.com/UBC-FRESH/femic/issues/305)

Branch: `feature/p110-coordinator-model-build`

Status: active planning

## Purpose

Make FEMIC the Coordinator-facing control plane for reliable construction of
forest model instances. Complex workflows are represented and executed through
FreshForge; FEMIC owns domain requests, policies, manifests, and providers; ws3
owns forest-estate contracts and validation oracles.

The first target is a new ws3-backed model instance built from declared source
data and requested model scope. The workflow must produce evidence that a
Coordinator can inspect and use to decide whether to proceed.

## Non-negotiable boundaries

- No generic chat endpoint.
- No unchecked model-generated Python, shell commands, or Woodstock syntax.
- No silent mutation of a declared workspace.
- No workflow orchestration duplicated in FEMIC when FreshForge can own it.
- No instance-specific workflow builders in FEMIC or FreshForge core.
- No capability is accepted without a validator that can fail against real state.

## Artifact model

1. `ModelBuildSpec`: FEMIC-owned request describing source bindings, desired
   model scope, target engine, outputs, runtime policy, and approval mode.
2. FreshForge `WorkflowSpec`: generated execution graph with declared provider
   nodes, dependencies, inputs, outputs, and artifacts.
3. ws3 model contract: engine-level representation of themes, areas, yields,
   actions, transitions, outputs, horizon, and periods.
4. Workspace manifest: input hashes, spec hashes, package hashes, tool versions,
   workflow/run identifiers, validator results, and provenance references.

The model may fill leaf values in typed structures. Deterministic code emits
files that ws3 reads. The model does not directly emit executable code or raw
input syntax into the trusted path.

## First workflow

```text
request -> inventory -> source preflight -> typed spec proposal
        -> deterministic compile/emit -> dataset lint
        -> ws3 import -> structural verification -> package + manifest
```

`validate`, `inspect`, and `plan` are non-mutating. `dry_run` writes only to a
scratch workspace. `apply` requires explicit approval and remains confined to
the declared workspace. `run` is a separate permission with resource limits.

## Verification ladder

- L0: request and schema validation
- L1: input contract and keyword lint
- L2: ws3 section import
- L3: structural invariants: theme arity, development types, area bindings,
  yield coverage, action references, and transition closure
- L4: action compilation
- L5: bounded one-period solve or schedule smoke

Every workflow result declares the highest tier it cleared. Import success alone
is not model-build success.

## Staged work

### Stage 0: deterministic substrate

Build the request/spec records, workspace manifest, source inventory, deterministic
emission/adapters, and verification ladder without an LLM. Prove a round trip
against a public reference model before adding proposal generation.

### Stage 1: bounded model-spec proposal

Add a FEMIC capability that accepts a Developer request plus bounded inventory
and contract context, proposes typed leaf values, and validates the resulting
spec by emitting and running the verification ladder.

### Stage 2: input-data diagnosis and repair

Generalize the existing ws3 import diagnosis and Phase 9 linting into a
scratch-workspace repair loop. Each proposed edit must re-lint and re-import.

### Stage 3: execution and analysis

Expose read-only model runs with explicit resource limits and return artifact
handles, summaries, and manifests rather than unbounded output blobs.

### Stage 4: approved mutation

Represent changes as spec diffs. Re-emit and re-verify before applying an
approved diff to a workspace.

### Stage 5: instance and ecosystem rollout

Add concrete instance workflows in instance repositories, then extend the same
contract to upstream/downstream modules, production deployments, and teaching
profiles.

## Immediate next bounded task

Define the FEMIC `ModelBuildSpec` and workspace manifest, then write the first
round-trip contract test against a public ws3-backed fixture. Do not add an LLM
provider in that task. The output of this task becomes the acceptance artifact
for all later embedded-agent work.

## Related work

- FEMIC #207: canonical named-pipeline model-build flow
- FEMIC #220: FreshForge provider integration
- FEMIC #234: FreshForge execution for MKRF workflows
- FEMIC #241: FreshForge instance-provider boundary repair
- ws3 Phase 8: validated embedded capabilities
- FreshForge Phase 6: serial local workflow execution
