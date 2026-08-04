# Phase 110 Next Steps: Register FEMIC Model-Build Providers

Parent phase: [FEMIC #305](https://github.com/UBC-FRESH/femic/issues/305)

Implementation task: P110.2, tracked in FEMIC issue `#306` (closed)

Status: **complete** — implementation and synchronization surfaces updated.

Namespace decision: register a provider whose metadata id is `femic.model_build`
with six node types. This preserves the existing graph references from
`femic.plan_model_from_spec()` without requiring FreshForge core changes or
graph reference changes. The existing `femic` provider (`FemicFreshForgeProvider`)
remains unchanged and handles the generic FEMIC contracts.

Finalization:
- Provider id: `femic.model_build`
- Node types: `inventory`, `source_preflight`, `typed_compile_emit`,
  `dataset_lint_import`, `structural_verify`, `package_evidence`
- Entry point: `"femic.model_build" = "femic.freshforge:model_build_provider_factory"`
- Implementation class: `FemicModelBuildProvider` in `src/femic/freshforge.py`
- Execution: metadata-only; stage execution deferred to the next phase
- Synchronization: ROADMAP.md, CHANGE_LOG.md, and this plan doc updated
  to reflect completion. Next phase owns the first executable generic workflow
  slice.

## Purpose

P110.1 now emits a deterministic six-node FreshForge graph for a validated
`ModelBuildSpec`, but the graph is not provider-resolvable: FreshForge reports
one `node.provider.unavailable` diagnostic for each `femic.model_build.*` stage.
The next step is to register honest provider metadata for those stage names so
the graph can be structurally and provider-aware validated without pretending
that execution is already implemented.

This task is deliberately narrower than the first executable build workflow.
It establishes the provider contract and planning boundary first. FEMIC remains
the domain-facing control plane; FreshForge remains the owner of provider
registry, validation, planning, and execution semantics; ws3 remains the owner
of typed model construction and engine verification.

## Current evidence

- `femic.plan_model_from_spec()` emits exactly six stable stages:
  `inventory`, `source_preflight`, `typed_compile_emit`,
  `dataset_lint_import`, `structural_verify`, and `package_evidence`.
- FreshForge structural validation accepts the generated graph.
- FreshForge planning currently reports six unavailable-provider diagnostics
  and returns zero executable plan nodes.
- FEMIC already has an entry-point-discoverable provider in
  `src/femic/freshforge.py` with metadata, node validation, and an execution
  compatibility shim for its older generic contracts.
- FreshForge already provides `ProviderRegistry`, provider metadata, entry-point
  discovery, provider-aware validation, and deterministic `create_run_plan()`.

## Proposed implementation sequence

### 1. Define the six provider contracts

Extend FEMIC's provider metadata with the exact six node types referenced by
`src/femic/model_workflow.py`:

- `model_build.inventory`
- `model_build.source_preflight`
- `model_build.typed_compile_emit`
- `model_build.dataset_lint_import`
- `model_build.structural_verify`
- `model_build.package_evidence`

The provider reference parser treats the final dotted component as the node
type and the preceding portion as the provider id. Therefore the current graph
references resolve as provider id `femic.model_build` and node types such as
`inventory`; the implementation must either preserve that namespace exactly or
revise both compiler and metadata together. The selected representation must
be documented and tested rather than inferred from a sample.

Each contract must declare the fields the compiler already emits:

- common inputs: `source_root`, `output_root`, `requested_sections`;
- common parameters: `model_id`, `request_sha256`, `target_engine`,
  `approval_mode`;
- common artifacts: `workflow_id`, `model_id`;
- stage-specific outputs and dependency expectations where the FreshForge
  contract supports them.

Do not add shell commands, generated Python, raw Woodstock text, or private
instance paths to provider metadata.

### 2. Reconcile provider namespace and entry-point discovery

Confirm the provider reference syntax against FreshForge's parser and registry.
The six graph references currently use `femic.model_build.<stage>`, while the
existing entry point registers provider id `femic`. Resolve this mismatch in the
smallest coherent way:

- preferred option: use provider id `femic` with node types named
  `model_build.inventory`, `model_build.source_preflight`, and so on; or
- if preserving the current references is required, register a provider whose
  metadata id is `femic.model_build` and update the entry point/registry tests
  accordingly.

The compiler and provider metadata must agree exactly. No provider should be
reported available merely because a prefix matches.

### 3. Preserve non-executing behavior

Keep `plan_model_from_spec()` non-mutating. Provider registration must make
structural and provider-aware validation possible, but it must not execute any
node, create declared source/output directories, or write a `WorkspaceManifest`.

Until stage implementations exist, provider execution should remain explicitly
unavailable or return a structured not-implemented diagnostic through the
provider boundary. This task must not claim a runnable model build merely
because a node type resolves in the registry.

### 4. Add focused provider tests

Add or extend tests to cover:

- metadata contains all six model-build node types;
- each compiler-generated provider reference resolves through an explicit
  registry containing the FEMIC provider;
- provider-aware validation reports no unavailable-provider diagnostics for the
  registered metadata;
- planning distinguishes resolved metadata from executable implementation;
- existing generic FEMIC provider contracts remain available and unchanged;
- duplicate registration and malformed provider references retain FreshForge's
  existing diagnostics;
- planning remains non-mutating for source, output, and scratch paths;
- the existing workflow, dispatch, adapter, and ws3 smoke tests remain green.

Use an explicit in-process registry in unit tests where possible so tests do not
depend on the host's installed entry points. Add one discovery test only if the
repository package metadata makes the entry point deterministic in the current
environment.

### 5. Synchronize the planning surfaces

Update these surfaces in the same milestone:

- `ROADMAP.md`: add P110.2, keep the executable build workflow open, and update
  the Detailed Next Steps Notes section;
- `CHANGE_LOG.md`: record the provider-contract decision and verification;
- this planning note: record the final namespace choice, implementation status,
  and any deferred execution work;
- GitHub parent issue #305: add P110.2 to the child-task checklist and state
  that provider resolution is separate from provider execution;
- GitHub P110.2 issue: include scope, out-of-scope boundaries, acceptance,
  verification commands, risks, and artifacts.

## Implementation notes

- Provider class: `FemicModelBuildProvider` in `src/femic/freshforge.py`
- Factory: `model_build_provider_factory()` returns a provider instance
- Entry point: `"femic.model_build" = "femic.freshforge:model_build_provider_factory"`
- Tests: five new tests in `tests/test_model_workflow.py`
- Metadata-only registration — no shell commands, execution hooks, or instance paths
- Existing `FemicFreshForgeProvider` (provider id `femic`) left unchanged

## Out of scope

- Executing any of the six stages.
- Creating or populating `WorkspaceManifest` from node results.
- Implementing the full inventory, compile, lint/import, verification, or
  packaging algorithms.
- Changing FreshForge core APIs unless a concrete compatibility defect is
  demonstrated by a focused test.
- Adding instance-specific workflows, private data bindings, or an LLM layer.
- Closing the Phase 110 parent issue or opening a phase PR.

## Acceptance gate

This task is complete when:

1. all six compiler provider references resolve against the intended FEMIC
   provider metadata;
2. FreshForge structural and provider-aware validation returns no
   unavailable-provider errors for the generated graph;
3. the plan remains explicitly non-executing and does not mutate any declared
   workspace paths;
4. execution readiness is not overstated when stage implementations are still
   deferred;
5. focused tests cover metadata, registry resolution, diagnostics, namespace
   behavior, and regression compatibility; and
6. local roadmap, planning, changelog, and GitHub issue surfaces agree.

## Verification commands

```text
cd femic
ruff format --check src/femic/freshforge.py src/femic/model_workflow.py tests
ruff check src/femic/freshforge.py src/femic/model_workflow.py tests
PYTHONPATH=src:/home/gep/projects/ws3:/home/gep/projects/freshforge/src \
  python -m pytest -q \
  tests/test_freshforge_workflows.py \
  tests/test_model_workflow.py \
  tests/test_model_dispatch.py \
  tests/test_model_build.py \
  tests/test_ws3_bridge.py \
  tests/test_ws3_smoke.py
git diff --check
```

Run the relevant FreshForge provider/validation tests separately with its local
repository environment. Full repository checks remain a separate closeout gate
and must not be implied by this provider-registration milestone.

## Deferred follow-up

After P110.2, the next implementation task is the first executable generic
workflow slice: connect one or more registered stages to the existing typed ws3
adapter, capture provider-owned artifacts and diagnostics, and populate a
`WorkspaceManifest` only after explicit approval. The six-stage graph should
remain inspectable throughout that transition.
