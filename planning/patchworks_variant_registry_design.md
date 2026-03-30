# Patchworks Variant Registry Design Notes

Status
------

- Governing GitHub issue: `#60`
- Governing roadmap task: `P49.5`
- Working branch: `feature/issue-60-patchworks-pin-launch`
- Landed slices so far:
  - built-in + user-overlay registry loading
  - `instances list`, `variants list`, `variants show`
  - `run-variant <variant-id>` delegating to the proven headless runner
  - registry-declared `datalad-get` materialization with a default
    `100 MiB` approval threshold
  - user-overlay mutation commands:
    - `variants register`
    - `variants update`
    - `variants remove`
  - registry-backed scenario execution:
    - `scenarios list <variant-id>`
    - `run-scenario <variant-id> <scenario-id>`
- Immediate next edge:
  - decide whether materialization should stay as raw `datalad-get` actions
    or grow a friendlier dataset-summary consent surface
  - then widen into registry-backed scenario-set execution

Purpose
-------

The already-proven Patchworks headless seam is still too low-level for normal
operator use because it requires a raw `.pin` path and assumes the caller
already knows the right runtime config and data state.

The next useful surface is a FEMIC-owned variant registry that can:

- expose built-in example-instance variants out of the box;
- let users register their own named variants cleanly;
- resolve a variant name to the real Patchworks launch inputs; and
- materialize required data before launch instead of failing late.

Design Expansion From Developer Notes
-------------------------------------

The registry should not be treated as only a name-to-`.pin` alias map. The
more useful long-term shape is a richer execution contract that can carry:

- instance metadata
- variant-family membership
- per-variant runtime parameters
- named scenario definitions
- scenario sets

That means the registry should be able to grow from:

- "launch this `.pin`"

into:

- "launch this variant with the right runtime envelope, then run one or more
  named scenarios with predeclared save/report/analyze settings"

without replacing the already-proven explicit primitive seams underneath.

Design Goals
------------

1. Preserve the proven primitive seam.
   - Keep `femic patchworks run-headless <pin>` unchanged.
   - Treat the registry-backed launch surface as a higher-level wrapper, not a
     replacement for explicit-path control.
2. Make built-in variants work immediately.
   - FEMIC should ship registry entries for bundled example-instance variants
     such as the K3Z Patchworks family.
3. Support user-managed extensions and overrides.
   - Users should be able to register or modify variants without editing FEMIC
     source code.
4. Check data prerequisites before launch.
   - If a variant depends on annex/DataLad payloads or other materialization
     steps, FEMIC should handle those before Patchworks is launched.
5. Guard larger downloads explicitly.
   - If required downloads exceed a configured threshold, FEMIC should require
     explicit user consent with a size estimate.

Registry Shape
--------------

Recommended storage model:

- built-in registry file(s) shipped inside FEMIC resources;
- user registry file in FEMIC config home, likely:
  - Windows: `%USERPROFILE%\\.femic\\variants.yaml`
  - Linux/macOS: `~/.femic/variants.yaml`

Recommended merge rule:

- load built-ins first;
- overlay user entries by `variant_id`;
- allow user entries to add new ids or override built-in metadata explicitly.

Suggested entry shape:

```yaml
variants:
  - variant_id: k3z.base
    label: "K3Z base"
    kind: patchworks
    instance_id: k3z
    variant_family: baseline
    instance_root: external/femic-k3z-instance
    analysis_pin: models/k3z_patchworks_model/analysis/base.pin
    runtime_config: config/patchworks.runtime.windows.yaml
    default: true
    runtime:
      java_max_memory: 4g
      default_stage_label: null
    notes:
      - "Canonical baseline K3Z Patchworks launch surface."
    materialization:
      - kind: datalad-get
        dataset_root: external/femic-public-data
        relpaths:
          - data
        estimated_bytes: null
    scenarios:
      - scenario_id: even_flow_smoke
        label: "Even-flow smoke"
        mode: max-even-flow-smoke
        target: product.Yield.managed.Total
        save_stage_label: analysis/headless_runs/even_flow_smoke
        reports: []
        analyse:
          iterations: 100000
          improvement: 0.0
```

Possible higher-level top shape:

```yaml
instances:
  - instance_id: k3z
    label: "K3Z example instance"
    instance_root: external/femic-k3z-instance
    variant_families:
      - baseline
      - intensive
      - pct
      - overlay
    defaults:
      variant_id: k3z.base
      scenario_set_id: proving_ground

variants:
  ...

scenario_sets:
  - scenario_set_id: proving_ground
    label: "K3Z proving-ground scenarios"
    mode: sequential
    scenarios:
      - k3z.base/even_flow_smoke
      - k3z.intensive_light/even_flow_smoke
```

Core fields
-----------

- `variant_id`
  - stable user-facing registry key, e.g. `k3z.base`, `k3z.intensive_light`
- `instance_id`
  - stable grouping key for variants that belong to the same base model or
    case instance
- `variant_family`
  - optional family bucket such as `baseline`, `intensive`, `pct`, `overlay`
- `label`
  - readable display name
- `kind`
  - start with `patchworks`; leave room for future `ws3`, etc.
- `instance_root`
  - instance root or submodule root relative to the active FEMIC checkout
- `analysis_pin`
  - real Patchworks `.pin` path relative to `instance_root`
- `runtime_config`
  - matching Patchworks runtime config path relative to `instance_root`
- `default`
  - optional marker for the sensible default variant for an instance
- `runtime`
  - optional runtime overrides such as:
    - Java max-memory ceiling
    - default save/output directories
    - other future Patchworks launcher knobs
- `materialization`
  - ordered list of prerequisite actions FEMIC should run before launch
- `scenarios`
  - optional named scenario definitions attached to the variant

Scenario Definition Shape
-------------------------

The registry should leave room for richer scenario execution contracts such as:

- named scenario id / label
- target activation order
- periodic min/max values
- periodic weights
- penalty function shape / linearity
- saved stage/output name
- report-save selections
- `analyse` settings:
  - iteration cap
  - improvement threshold
  - other stability controls

That can start small by reusing the existing headless `scenario_mode` seam and
later expand into more explicit YAML-defined scenario surfaces.

Scenario Sets
-------------

The registry should also be able to group scenarios into scenario sets so FEMIC
can later support:

- sequential scenario batches
- parallel scenario batches where safe
- named proving-ground suites
- teaching/demo suites for a whole variant family

This does **not** need to be fully implemented in the first slice, but the
registry shape should avoid blocking it.

Current landed slice
--------------------

The first registry-backed scenario-set slice is now in hand.

Current tracked support is intentionally narrow:

- top-level named ``scenario_sets`` in the built-in and user overlay registries
- sequential execution only
- ``femic patchworks scenario-sets list``
- ``femic patchworks run-scenario-set <scenario-set-id>``
- reuse of the existing named-scenario and headless Patchworks runner contract
  for each step

The shipped built-in proof set is:

- ``k3z.proving_ground``
  - ``k3z.base/even_flow_smoke``
  - ``k3z.intensive_light_standstructure/even_flow_smoke``

Direct smoke evidence:

- ``python -m femic patchworks scenario-sets list``
- ``python -m femic patchworks run-scenario-set k3z.proving_ground --run-id issue60_scenario_set --log-dir vdyp_io/logs``
- inspected outputs:
  - manifests:
    - ``vdyp_io/logs/patchworks_headless_manifest-issue60_scenario_set_01.json``
    - ``vdyp_io/logs/patchworks_headless_manifest-issue60_scenario_set_02.json``
  - both saved stages kept:
    - ``product.Yield.managed.Total``
    - ``flow.even.product.Yield.managed.Total``
    active in ``scenario/targetStatus.csv``
  - both stages retained non-empty ``scenario/schedule.csv`` files

Next edge after this slice:

- keep scenario-set execution sequential for now;
- a small follow-on convenience slice is now also landed:
  - optional variant-level ``default_scenario_id``
  - ``femic patchworks run-default-scenario <variant-id>``
  - thin wrapper over the existing named-scenario runner
- decide whether the next operator-facing value is:
  - richer materialization consent/reporting; or
  - scenario-set metadata such as labels, families, or default-set aliases;
- defer parallel scenario-set execution until there is a clear safety contract
  for Patchworks process concurrency.

Future DataLad-Linked Deployment Seam
-------------------------------------

The registry should also leave room for a later DataLad-linked deployment mode.

Two related futures are worth preserving explicitly:

1. Registry-management actions could be mirrored into a linked DataLad-managed
   local deployment dataset.
   - adding, removing, or modifying variants in FEMIC could optionally trigger
     analogous tracked changes in the linked dataset repo;
   - this would help keep FEMIC's local execution registry aligned with a
     reproducible deployment/data workspace contract.

2. Variant/scenario execution could optionally run in a DataLad-aware mode.
   - CLI idea:
     - `--use-datalad`
   - API idea:
     - `use_datalad=True`
   - In that mode, FEMIC would log the scenario-run operation as part of a
     fuller model-lifecycle reproducibility contract, rather than treating the
     run as an untracked local side effect.

This is out of scope for the first `P49.5` landing, but the registry and
launch-surface design should not block a future where:

- variant registration is tied to a DataLad-managed local deployment; and
- scenario/scenario-set execution can be wrapped in reproducibility logging.

Materialization Actions
-----------------------

Start with one supported action family:

- `datalad-get`
  - `dataset_root`
  - `relpaths`
  - optional `estimated_bytes`

Later expansion could support:

- `annex-get`
- local file existence checks
- generated-cache bootstrap

Consent Guardrail
-----------------

Recommended default:

- auto-run materialization without prompting when the total estimated size is
  unknown or <= `100 MiB`
- require explicit consent when estimated size > `100 MiB`

Suggested CLI behavior:

- print:
  - variant id
  - materialization actions
  - estimated download size when known
- require one of:
  - interactive `y/N` confirmation; or
  - `--yes` / `--allow-large-download`

If the size is unknown:

- print that the estimate is unavailable;
- let policy decide whether unknown counts as prompt-required.

CLI Surface
-----------

Suggested command family:

- `femic patchworks instances list`
- `femic patchworks variants list`
- `femic patchworks variants show <variant-id>`
- `femic patchworks variants register ...`
- `femic patchworks variants update <variant-id> ...`
- `femic patchworks variants remove <variant-id>`
- `femic patchworks run-variant <variant-id>`
- later:
  - `femic patchworks scenarios list <variant-id>`
  - `femic patchworks run-scenario <variant-id> <scenario-id>`
  - `femic patchworks run-scenario-set <scenario-set-id>`

Minimal first landed slice
--------------------------

1. built-in registry loading
2. user-registry loading/merge
3. `instances list`, `variants list`, and `variants show`
4. `run-variant <variant-id>` that:
   - resolves instance root / runtime config / `.pin`
   - runs prerequisite materialization checks
   - prompts for larger downloads when required
   - delegates to the existing proven headless runner

Important scoping rule:

- support rich metadata in the registry contract now;
- implement only the minimum execution subset needed for a clean first landing;
- do not block the first slice on full scenario-set orchestration.

Non-Goals For The First Slice
-----------------------------

- full install-time mutation of user config home
- exhaustive size estimation for every annex-backed payload
- automatic registration of arbitrary non-Patchworks workflows
- replacing the explicit-path `run-headless` primitive

Current Best Built-In Seed Source
---------------------------------

The bundled K3Z variant metadata already exposes the right launch fields:

- `external/femic-k3z-instance/config/patchworks.variant.*.yaml`

Those files already carry:

- `variant_id`
- `patchworks.analysis_pin`
- `patchworks.runtime_config`

So the first built-in registry loader should reuse that existing metadata
instead of duplicating it by hand.
