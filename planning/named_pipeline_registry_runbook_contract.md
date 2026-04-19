# Named Pipeline Registry And Runbook Contract

Status
------

- Governing GitHub issue: `#167`
- Governing umbrella: `#163`
- Governing roadmap task: `P53.1b`
- Working branch: `feature/issue-163-pipeline-refactor-umbrella`
- This note is contract-first planning only.
- It does **not** implement the named-pipeline runner.

Purpose
-------

FEMIC already has many of the right primitive seams:

- instance-local run profiles;
- recipe records such as TSR source-layer and THLB recipe YAMLs;
- explicit restart seams such as `aflb_checkpoint.feather`,
  `aflb_yield_ready_checkpoint.feather`, and
  `lhlb_curve_ready_checkpoint.feather`; and
- operator-facing runbooks under `runbooks/`.

What is still missing is a single contract that answers:

1. what a **named pipeline** is;
2. where FEMIC looks for pipeline definitions;
3. how a **runbook** selects a pipeline and a restart seam; and
4. how the current recipe-based TSR/THLB surfaces map into that model.

This planning note defines that contract tightly enough for the follow-on
implementation child to add a runner without making product-shape decisions.

Design Goals
------------

1. Preserve the proven recipe primitives.
   - Named pipelines wrap existing recipe/config/checkpoint surfaces.
   - They do not replace direct low-level commands during the first rollout.
2. Keep the operator concept simple.
   - Operators should think in terms of "run this named pipeline from this
     runbook", not "remember the legacy stage script chain".
3. Keep registry layering explicit and auditable.
   - Built-in, user, instance-local, and explicitly named registries should
     merge predictably.
4. Make restart seams first-class.
   - A runbook must be able to declare either "start from scratch" or "resume
     from this named seam/checkpoint policy".
5. Preserve current instance-local practice.
   - Existing `config/`, `runbooks/`, and instance-root conventions should
     remain the anchor rather than introducing a parallel workspace model.

Core Concepts
-------------

### Pipeline

A pipeline is a named, versioned execution contract that resolves to:

- a pipeline id;
- a human label and short description;
- a pipeline kind;
- an ordered sequence of recipe steps;
- a set of supported named restart seams; and
- optional default overlays/parameter bindings.

A pipeline is **not** a free-form shell script and is **not** a replacement for
the underlying recipe contracts.

### Registry

A registry is a YAML document that declares one or more named pipelines.

The contract-first rollout will support these registry tiers:

1. built-in system registry shipped inside FEMIC;
2. optional user registry under FEMIC config home; and
3. optional instance-local registry under the instance `config/` tree.

Additional explicit registry files may be listed by a runbook, but there is no
separate "network registry" contract in the first implementation issue.
Public/user-contributed registries are handled as ordinary explicit file paths.

### Runbook

A runbook is an instance-local YAML document that names:

- the selected pipeline;
- the intended instance root;
- the run profile / overlays / parameter files the pipeline should use; and
- the restart-seam policy for this run.

This is distinct from the existing human-authored Markdown operator notes in
`runbooks/REBUILD_RUNBOOK.md`. That Markdown file remains the operator guide;
the new runbook YAML becomes the machine-readable execution contract.

Registry Contract
-----------------

### Default discovery locations

Recommended default registry paths:

1. built-in system registry:
   - `src/femic/resources/pipelines/registry.yaml`
2. user registry:
   - Windows: `%USERPROFILE%\\.femic\\pipelines.yaml`
   - Linux/macOS: `~/.femic/pipelines.yaml`
3. instance-local registry:
   - `<instance_root>/config/pipelines.yaml`

The implementation child should treat missing user or instance registries as
normal, not as errors.

### Registry merge rule

Registry load order:

1. built-in system registry
2. user registry
3. instance-local registry
4. any explicit extra registry paths named in the runbook

Merge policy:

- merge by `pipeline_id`;
- later registries override earlier registries for the same `pipeline_id`;
- duplicate `pipeline_id` in the same file is invalid;
- unknown top-level keys should be rejected in the first implementation issue
  rather than silently ignored.

### Registry document shape

Recommended top-level shape:

```yaml
schema_version: 1
registry_kind: pipeline_registry
pipelines:
  - pipeline_id: tsr.thlb_netdown
    label: TSR THLB netdown
    kind: tsr
    summary: Run the reviewed TSR THLB reconstruction lane.
    default_instance_runbook: runbooks/pipelines/tsr.thlb_netdown.yaml
    seams:
      - seam_id: scratch
        stage_label: Full pipeline start
      - seam_id: aflb
        checkpoint_path: data/tsr/aflb_checkpoint.feather
      - seam_id: aflb_yield_ready
        checkpoint_path: data/tsr/aflb_yield_ready_checkpoint.feather
      - seam_id: lhlb_curve_ready
        checkpoint_path: data/tsr/lhlb_curve_ready_checkpoint.feather
    recipes:
      - recipe_id: tsr.source_layers
        recipe_kind: tsr_source_layers
        default_recipe_path: config/tsr/source_layers.recipe.yaml
      - recipe_id: tsr.thlb_netdown
        recipe_kind: tsr_thlb_netdown
        default_recipe_path: config/tsr/thlb_netdown.recipe.yaml
```

### Required pipeline fields

Each pipeline entry must declare:

- `pipeline_id`
- `label`
- `kind`
- `summary`
- `recipes`
- `seams`

Each recipe item must declare:

- `recipe_id`
- `recipe_kind`

Optional per-recipe fields:

- `default_recipe_path`
- `default_config_path`
- `notes`

Each seam item must declare:

- `seam_id`
- either `checkpoint_path` or an explicit `start_mode: scratch`

Optional per-seam fields:

- `stage_label`
- `baseline_signal`
- `checkpoint_kind`
- `notes`

Runbook Contract
----------------

### Default location

Machine-readable pipeline runbooks should live under:

- `<instance_root>/runbooks/pipelines/*.yaml`

This keeps them close to the existing human runbook surface while separating
machine-readable execution contracts from operator prose.

### Runbook document shape

Recommended top-level shape:

```yaml
schema_version: 1
runbook_kind: femic_pipeline_runbook
label: TSA29 TSR THLB reviewed lane
pipeline_id: tsr.thlb_netdown
instance_root: .
run_profile: config/run_profile.tsa29.yaml
registry_paths: []
overlay_paths:
  - config/tsr/overlay.yaml
parameter_files: []
restart:
  seam_id: aflb_yield_ready
  checkpoint_path: data/tsr/aflb_yield_ready_checkpoint.feather
```

### Required runbook fields

- `schema_version`
- `runbook_kind`
- `label`
- `pipeline_id`
- `instance_root`
- `restart`

### Optional runbook fields

- `run_profile`
- `registry_paths`
- `overlay_paths`
- `parameter_files`
- `notes`

### Restart object contract

Required fields:

- `seam_id`

Optional fields:

- `checkpoint_path`
- `policy`

Policy rules:

- `seam_id: scratch` means start from pipeline scratch and should not require a
  checkpoint path.
- any seam with a checkpoint-backed restart should allow an explicit
  `checkpoint_path` override.
- if `checkpoint_path` is omitted for a checkpoint-backed seam, the runner
  should use the seam's declared default path from the resolved pipeline entry.

Compatibility Mapping For Current FEMIC
---------------------------------------

The first implementation should treat the current TSR/THLB lane as the anchor
proof case for named pipelines.

Recommended first-class pipeline ids:

- `tsr.source_layers`
- `tsr.thlb_netdown`
- `tsr.yield_bridge`

Recommended initial seam vocabulary for the TSR THLB lane:

- `scratch`
- `aflb`
- `aflb_yield_ready`
- `lhlb`
- `lhlb_curve_ready`
- `thlb_final`

Current surfaces that should map directly rather than be renamed away:

- `config/run_profile.<case>.yaml`
- `config/tsr/overlay.yaml`
- `config/tsr/source_layers.recipe.yaml`
- `config/tsr/thlb_netdown.recipe.yaml`
- `data/tsr/aflb_checkpoint.feather`
- `data/tsr/aflb_yield_ready_checkpoint.feather`
- `data/tsr/lhlb_curve_ready_checkpoint.feather`

The first runner issue should build on those exact surfaces instead of creating
parallel config trees.

TSA29 Proof-Lane Pressure Test
------------------------------

The current TSA29 reviewed THLB lane is a strong enough real-world example to
pressure-test the proposed registry and runbook contract.

### Observed current inputs

From the live TSA29 instance and docs, the proof lane already has these stable
machine-readable inputs:

- run profile:
  - `config/run_profile.tsa29.yaml`
- instance overlay:
  - `config/tsr/overlay.yaml`
- source-layer recipe:
  - `config/tsr/source_layers.recipe.yaml`
- THLB recipe:
  - `config/tsr/thlb_netdown.recipe.yaml`
- restart-grade checkpoints:
  - `data/tsr/aflb_checkpoint.feather`
  - `data/tsr/aflb_yield_ready_checkpoint.feather`
  - `data/tsr/lhlb_checkpoint.feather`
  - `data/tsr/lhlb_curve_ready_checkpoint.feather`

### Observed current command chain

The current reproducible reviewed TSR THLB path documented in
`docs/guides/tsr-intelligence-workflow.rst` is:

1. `femic tsr index`
2. `femic tsr fetch --tsa 29`
3. `femic tsr extract --tsa 29`
4. `femic tsr recipe-init --instance-root ... --tsa 29`
5. `femic tsr source-layers-build`
6. `femic tsr source-layers-run`
7. `femic tsr thlb-netdown-build`
8. `femic tsr thlb-netdown-workbench-build`
9. `femic tsr thlb-netdown-run`
10. `femic tsr thlb-netdown-workbench-lock`
11. `femic tsr overlay-init` / `overlay-report`

The named-pipeline runner does **not** need to wrap all of that in its first
implementation slice. It only needs to prove one stable, reviewable pipeline
surface from the currently accepted chain.

### Recommended proof pipeline for the first runner child

The first runner child should target one pipeline id only:

- `tsr.thlb_reviewed`

That proof pipeline should resolve to the already accepted reviewed THLB lane:

- source-layer recipe surface;
- THLB netdown recipe surface;
- optional yield-bridge seam selection; and
- explicit reconstructed THLB execution.

### Recommended initial seam set for `tsr.thlb_reviewed`

Required seams for the first runner child:

- `scratch`
- `aflb`
- `aflb_yield_ready`
- `lhlb_curve_ready`

These seams are sufficient because:

- `scratch` covers full reviewed execution;
- `aflb` and `aflb_yield_ready` are now proven restart seams under `#164`; and
- `lhlb_curve_ready` already exists as the supported downstream restart seam
  for late THLB exploration.

### Worked runbook example for the proof lane

Recommended instance-local runbook example:

```yaml
schema_version: 1
runbook_kind: femic_pipeline_runbook
label: TSA29 reviewed TSR THLB proof lane
pipeline_id: tsr.thlb_reviewed
instance_root: .
run_profile: config/run_profile.tsa29.yaml
overlay_paths:
  - config/tsr/overlay.yaml
restart:
  seam_id: aflb_yield_ready
  checkpoint_path: data/tsr/aflb_yield_ready_checkpoint.feather
```

### Pressure-test conclusions

The pressure test narrows the contract in three useful ways:

1. The first runner does not need generic recipe mutation.
   - It only needs to resolve known recipe/config/checkpoint paths from a
     pipeline entry and a runbook.
2. The first runner should be read-mostly and orchestration-only.
   - It should call proven existing recipe/CLI helpers instead of inventing a
     new execution engine.
3. The first runner can stay TSR-only.
   - Patchworks/ws3 and other workflow families should remain out of scope
     until the contract is proven by the TSR THLB lane.

Out Of Scope For `#167`
-----------------------

This contract issue should **not** decide or implement:

- a new generic `femic run-pipeline` CLI surface;
- migration of every existing FEMIC workflow family into named pipelines;
- remote registry publication/distribution protocols;
- mutation commands for editing pipeline registries; or
- replacement of existing direct recipe commands.

Those belong in the follow-on implementation child after this contract note is
accepted.

Recommended Follow-on Child
---------------------------

The next feature child after `#167` should implement:

- pipeline registry loading and resolution;
- runbook loading/validation;
- one concrete named-pipeline execution surface for the `tsr.thlb_reviewed`
  proof lane;
- seam-aware restart selection from the runbook contract; and
- read-only inspection/listing commands if needed to make that runner usable.

Minimum Scope For The Runner Child
----------------------------------

The next implementation child should stay intentionally narrow.

### In scope

- load and merge pipeline registries from the default tiers plus explicit extra
  runbook registry paths;
- load one machine-readable runbook from `runbooks/pipelines/*.yaml`;
- resolve one pipeline id, one restart seam, and the concrete instance-local
  config/checkpoint paths for that runbook;
- expose one proof command that launches the existing reviewed TSR THLB lane by
  delegating to current FEMIC helpers rather than reimplementing them; and
- emit a small summary showing the resolved pipeline id, seam id, recipe paths,
  run profile, and checkpoint path actually used.

### Out of scope

- registry-editing commands;
- generalized multi-family pipeline execution;
- replacement of existing `femic tsr ...` commands;
- broad migration of historic runbooks/instances; and
- speculative support for remote registry distribution.

### Recommended proof command surface

The next child may choose the exact command name, but it should implement only
one proof-oriented surface equivalent in spirit to:

- `femic pipelines run --runbook runbooks/pipelines/tsr.thlb_reviewed.yaml`

That command should:

- resolve the runbook and pipeline;
- map the selected seam to the existing TSR THLB execution path; and
- delegate into the already-proven helper/CLI surfaces.

Acceptance Criteria For Closing `#167`
--------------------------------------

`#167` is ready to close when the repo contains:

- a planning/spec note that fixes the registry tiers, merge order, and file
  locations;
- a planning/spec note that fixes the runbook YAML contract and restart object
  shape;
- an explicit compatibility mapping from current TSR/THLB recipe surfaces into
  named-pipeline ids and seam ids; and
- a narrow enough contract that the next implementation child can execute
  without making product-shape decisions.
