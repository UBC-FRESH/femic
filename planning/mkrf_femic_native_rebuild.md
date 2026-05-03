# MKRF FEMIC-Native Rebuild Notes

Issue: `#173`

## Summary

This note is the active planning surface for the from-scratch MKRF rebuild
lane.

Current publication status:

- the first canonical MKRF alpha release is now published as
  `femic-mkrf-instance` release `v0.0.1a1`;
- instance PR `UBC-FRESH/femic-mkrf-instance#2` and parent PR `#179` are
  merged;
- instance discussion announcement
  `UBC-FRESH/femic-mkrf-instance#3` is posted; and
- follow-on archival/reference publication work is tracked in
  `UBC-FRESH/femic-mkrf-instance#1`.

Current post-release status:

- the CT legacy-parity repair under `#180` is complete; and
- the follow-on archival/reference publication issue
  `UBC-FRESH/femic-mkrf-instance#1` is now also complete.
- the next MKRF modeling lane is the post-legacy CT redesign governed by
  `#182`.

It starts after the legacy archaeology / PoC benchmark program recorded in:

- `planning/mkrf_legacy_decompile.md`

The governing posture for this lane is:

- use the standalone K3Z/TSA29 FEMIC instance pattern as the default
  architecture;
- treat the current MKRF PoC package and benchmark surfaces as comparison
  evidence only;
- carry forward legacy behavior only when it is justified by reviewed source
  evidence or benchmark necessity.

## Current rebuild contract

### Governing architecture defaults

- standalone instance repo remains the canonical owner of runtime/config/docs;
- parent FEMIC repo remains a pointer/lineage and integration surface;
- canonical rebuild contracts live under `config/`;
- canonical user-facing/operator docs live under `docs/`;
- the future canonical runtime package lives under `models/` as a rebuild
  surface distinct from the current PoC package:
  `models/mkrf_patchworks_model_poc/`.

### What is benchmark/reference evidence only

- the current PoC runtime package;
- PoC benchmark saved-stage and report surfaces;
- accepted legacy compiled-runtime evidence;
- reviewed workbook/XML/runtime translations recovered during the archaeology
  lane.

These are acceptance/comparison surfaces, not automatic architecture contracts.

### Carry-forward gate

Any legacy behavior carried into the new rebuild must satisfy at least one of:

- justified by reviewed source evidence from the upstream legacy corpus; or
- justified by benchmark necessity because dropping it would break an accepted
  comparison surface the team still cares about.

Anything satisfying neither test should be treated as removable PoC/legacy
residue.

## Active phase map

### `P60.1` Define the target instance contract and acceptance gates

Completed:

- `P60.1a`
  set the governing standalone-instance pattern using K3Z/TSA29 conventions;
- `P60.1b`
  fixed the PoC package as benchmark/reference evidence only; and
- `P60.1c`
  required explicit evidence or benchmark necessity for any legacy behavior
  carried forward.

This phase starts from the closed PoC handoff already established in the
legacy note:

- the current PoC runtime package under
  `models/mkrf_patchworks_model_poc/` is benchmark/intermediate evidence only;
- the Phase 59 standalone docs lane is complete enough that the benchmark lane
  no longer needs to be treated as under-documented; and
- the rebuild lane is free to move forward without reopening PoC archaeology
  unless a later acceptance gate requires it.

### `P60.2` Define the canonical FEMIC-native MKRF instance layout

Completed:

- `P60.2a`
  fixed the canonical top-level layout contract:
  `.github/`, `config/`, `data/`, `docs/`, `models/`, `metadata/`,
  `runbooks/`, plus root repo docs.

Completed:

- `P60.2a`
  fixed the canonical top-level layout contract;
- `P60.2b`
  fixed the authoritative rebuild sequencing and validation contract; and
- `P60.2c`
  fixed the separation boundary between benchmark/reference artifacts and the
  new source-faithful build surfaces.

### Downstream phases

- `P60.3`
  reconstruct the raw-source geometry-to-runtime pipeline from
  `03_MappingAnalysisData/*`;
- `P60.4`
  rebuild the target/control lane from reviewed source contracts instead of
  checkpoint loading;
- `P60.5`
  build the canonical AU table and AU-wise first-growth curve lane;
- `P60.6`
  build the provisional expert-rule managed AU-wise TIPSY/BTC lane;
- `P60.7`
  fix bad curve cases before runtime generation continues;
- `P60.8`
  rebuild the full MKRF runtime package from source-faithful inputs;
- `P60.9`
  validate the rebuilt model against the accepted PoC benchmark and relevant
  legacy evidence; and
- `P60.10`
  publish closeout docs and decide whether umbrella issue `#172` can close.

### Current active edge

The current active implementation edge is:

- `P60.10`
  complete; umbrella issue `#172` is now closed, so the Phase 60
  from-scratch MKRF rebuild lane is fully closed at the planning surface.

`P60.10e` semantic-repair result:

- the canonical MKRF runtime package now publishes an explicit runtime
  `origin` field using the reviewed age rule:
  - `AGE_2020 >= 80` in 2020 -> `natural`
  - `AGE_2020 < 80` in 2020 -> `treated`
- Patchworks IFM (`managed/unmanaged`) is now decoupled from curve provenance
  (`natural/treated`) in the canonical generator;
- first-growth / `hasfg` availability is no longer used as a proxy for:
  - IFM state;
  - unmanaged-vs-managed yield logic; or
  - species-family emission;
- `EM/EN/FM/THN` output families are still published, but now derive from
  explicit origin + treatment semantics rather than `hasfg` / AU-prefix
  shortcuts;
- the canonical analysis surface now publishes
  `analysis/runtime_species_share_audit.csv`; and
- the new `femic instance mkrf-audit-runtime-sanity` helper now checks
  canonical saved-stage `indsp.*` outputs against that audit directly.

Validation result from the same slice:

- canonical package regeneration succeeded;
- Matrix Builder run `mkrf_rebuild_p60_10e_20260502c` completed cleanly;
- canonical even-flow smoke
  `mkrf_canonical_evenflow_semantic_smoke_20260502a` completed cleanly; and
- the saved-stage sanity audit reported zero failures, including nonzero
  managed `Hw` / `Dr` species signal that the earlier conflated runtime had
  incorrectly flattened.

Parent-doc guardrails landed in the same slice:

- `AGENTS.md`
- `docs/reference/contracts/index.rst`
- new compact Patchworks semantics contract page under
  `docs/reference/contracts/`
- `docs/reference/patchworks-export.rst`
- `docs/guides/vscode-coding-agent-onboarding.rst`

`P60.10d` closeout result:

- audited umbrella issue `#172` against the completed archaeology / PoC scope
  (`P55`-`P59`) and the completed canonical rebuild scope (`P60`);
- confirmed that no remaining canonical rebuild work still belongs to the
  archaeology umbrella; and
- posted the final closeout comment and closed `#172`.

Phase 60 closeout result:

- the canonical MKRF rebuild lane under `#173` now has:
  - a published runtime/package claim boundary;
  - a runnable canonical control lane;
  - repaired IFM/origin semantics;
  - a `100000`-iteration canonical `v0` validation baseline; and
  - documented runtime sanity auditing.
- the archaeology umbrella `#172` is closed and remains the archival record of
  the reverse-engineering / PoC benchmark program rather than an active work
  queue.

Retained `P60.10a` docs closeout target list for reference:

- parent docs:
  - `docs/sample-models/mkrf.rst`
  - `docs/sample-models/mkrf-metadata-lineage.rst`
- instance docs/readmes:
  - `external/femic-mkrf-instance/README.md`
  - `external/femic-mkrf-instance/docs/index.rst`
  - `external/femic-mkrf-instance/docs/getting-started.rst`
  - `external/femic-mkrf-instance/docs/operator-runbook.rst`
  - `external/femic-mkrf-instance/docs/evidence-and-boundaries.rst`
  - `external/femic-mkrf-instance/docs/rebuild-and-qa.rst`
  - `external/femic-mkrf-instance/docs/data-package-crosswalk.rst`
  - `external/femic-mkrf-instance/docs/metadata-and-lineage.rst`
- required documentation correction across that set:
  - keep `models/mkrf_patchworks_model_poc/` framed as benchmark/reference
    evidence only;
  - teach `models/mkrf_patchworks_model/` as the canonical rebuild runtime
    package;
  - keep accepted legacy-only control seams (`THLB4070(...)`, `UWR(...)`,
    `InitialTargets/00_Target_Descriptions.bsh`) outside the canonical claim
    boundary unless a later rebuild task explicitly reopens them.

`P60.10a` status:

- complete; the parent pointer docs plus the targeted instance README/docs
  surfaces now teach the canonical rebuild lane first while keeping the PoC
  lane explicitly labeled as benchmark/reference evidence; and
- both the parent docs tree and the standalone instance docs tree now pass
  Sphinx HTML builds with warnings treated as errors.

Immediate `P60.10b` closeout question:

- record the final claim boundary in docs/planning language:
  - canonical runtime/package rebuild is complete and accepted;
  - PoC and legacy surfaces remain benchmark/reference evidence only; and
  - accepted legacy-only control seams stay outside the canonical claim
    boundary unless a later control-lane rebuild task explicitly reopens them.

`P60.10b` status:

- complete; the canonical MKRF rebuild claim now explicitly covers the
  runtime/package lane under `models/mkrf_patchworks_model/`, including the
  canonical XML, spatial, tracks, analysis, and accepted runtime Patchworks
  config surfaces;
- retained PoC and legacy surfaces, including
  `models/mkrf_patchworks_model_poc/`, legacy compiled controls/tracks, and
  benchmark report/control artifacts, are now explicitly benchmark/reference
  evidence only rather than part of the canonical rebuild claim; and
- the unresolved control-lane seams `THLB4070(...)`, `UWR(...)`, and
  `InitialTargets/00_Target_Descriptions.bsh` remain outside the canonical
  rebuild claim boundary for this phase unless a later task explicitly reopens
  source-faithful control-lane reconstruction.

Immediate `P60.10c` runnable-control result:

- the canonical runtime/package lane now publishes a runnable minimal control
  surface:
  - `models/mkrf_patchworks_model/analysis/base.pin`
  - `models/mkrf_patchworks_model/analysis/headless_runtime_common.bsh`
  - `models/mkrf_patchworks_model/scripts/targets/flowtargets.bsh`
- the built-in `mkrf.base` variant now points at the canonical rebuild package,
  while the retained PoC control lane remains separately addressable as
  `mkrf.poc_base`; and
- the canonical package proved runnable through headless Patchworks with the
  real even-flow harvest-volume smoke run
  `mkrf_canonical_evenflow_smoke`, whose saved stage under
  `runtime/logs/headless_stage/mkrf_canonical_evenflow_smoke/` contains:
  - non-empty `scenario/schedule.csv` with real `CC` and `CT` activity;
  - active `product.yield.managed.total` and
    `flow.even.product.yield.managed.total` targets; and
  - sane `targetSummary.csv` values with substantial harvest volume and
    near-zero even-flow residuals.

In shorthand:

- `P60.3`
  rebuild the raw-source geometry-to-runtime pipeline from
  `03_MappingAnalysisData/*` as a source-faithful lane, not by reusing PoC
  runtime/checkpoint substitutes;
- `P60.4`
  rebuild the target/control lane from reviewed source contracts instead of
  legacy checkpoint loading or unexplained compiled helper seams;
- `P60.5`
  build the canonical AU table, assign stands to AUs, and compile AU-wise
  first-growth VDYP curves with FEMIC NLLS before runtime generation;
- `P60.6`
  bootstrap the AU-wise managed/planted lane from expert planting rules plus
  stand-derived managed site index and keep it explicitly provisional;
- `P60.7`
  fix bad curve cases and record the curve-quality acceptance gate before
  runtime generation continues;
- `P60.8`
  rebuild the full MKRF runtime package from source-faithful inputs and publish
  the new canonical runtime outputs;
- `P60.9`
  validate the rebuilt model against the accepted PoC benchmark surfaces and
  the legacy evidence that still matters for acceptance; and
- `P60.10`
  publish closeout docs and decide whether umbrella legacy-recovery issue
  `#172` can close once the from-scratch rebuild is complete.

Current shorthand status:

- `P60.8a`
  complete; the canonical package now publishes source-faithful spatial,
  analysis, XML, and lineage surfaces under
  `models/mkrf_patchworks_model/`;
- `P60.8b`
  complete; Patchworks preflight and Matrix Builder now run cleanly against
  the canonical package and rebuild `tracks/` from that package rather than
  from PoC surfaces; and
- `P60.8c`
  complete; the canonical package, generated runtime outputs, and lineage
  surfaces stayed synchronized through the `P60.9a` parity rollout and now
  provide the stable baseline for the remaining acceptance work.

Resolved `P60.9b` / `P60.9c` acceptance boundary:

- the canonical rebuild currently has no rebuilt control/entrypoint lane under
  `models/mkrf_patchworks_model/analysis`, `initial_targets`, `scripts`, or
  `targets`;
- the relevant control evidence surfaces still live in:
  - the accepted PoC lane under
    `models/mkrf_patchworks_model_poc/analysis/base.pin` and
    `models/mkrf_patchworks_model_poc/analysis/ScenarioSet.bsh`; and
  - the legacy compiled lane under
    `data/legacy_mkrf/compiled_controls/entrypoints/baseMKRF.pin` and
    `data/legacy_mkrf/compiled_controls/entrypoints/ScenarioSet.bsh`;
- unresolved helper seams remain the same benchmark-only seams already pinned
  from the PoC stage:
  - `THLB4070(...)`
  - `UWR(...)`
  - `InitialTargets/00_Target_Descriptions.bsh`; and
- unless a later source-faithful control-lane task is opened explicitly, these
  should be treated as legacy/PoC acceptance evidence rather than canonical
  regressions.

Immediate `P60.9a` rollout order now fixed:

- first restore PoC-style state and seral family parity in the canonical
  runtime surface;
- then restore managed yield/product breadth parity for `merch.total` and
  managed `indsp.*` families using rebuild-owned managed payloads;
- then restore unmanaged total/state yield parity from the canonical
  first-growth/runtime curve lane; and
- then validate whether unmanaged `indsp.*` can be restored from a
  rebuild-owned unmanaged species-share contract.

Current `P60.9a` benchmark read after clean canonical run
`mkrf_rebuild_p60_9a_20260501e`:

- managed breadth parity is materially in place:
  - managed `EN/EM/FM/THN` families now emit in the canonical runtime;
  - managed `merch.total` families emit; and
  - managed `indsp.{Ba,Cw,Dec,Dr,Fd,Hw,Oth,Yc}` families emit in
    `features.csv`, `products.csv`, and `accounts.csv`;
- unmanaged yield parity is now materially in place:
  - unmanaged `feature.yield.unmanaged.state.EM` and `EN` emit in the
    canonical runtime;
  - unmanaged `feature.yield.unmanaged.indsp.*` now emits in
    `features.csv` and `accounts.csv` from rebuild-owned
    `stand_au_assignment.csv` species-share aggregation; and
  - unmanaged products remain absent, which is PoC-consistent because the
    accepted PoC `products.csv` is managed-only; and
- canonical vs PoC family diff is now narrow:
  - accepted redesign: `feature.area.unmanaged.state.THN` and
    `feature.yield.unmanaged.state.THN`, because the PoC sources those from a
    special numeric unmanaged AU family (`2201`, `2204`, ...) that the
    canonical rebuild does not preserve after AU normalization;
  - no remaining unmanaged `indsp.*` gap remains on the feature/account
    surface.

## Immediate working rules for `P60.2+`

- Do not let the current PoC package path become the canonical rebuild path.
- Do not use checkpoint-derived or compiled-runtime artifacts as substitutes
  for raw-source rebuild claims.
- Prefer K3Z/TSA29 sequencing and validation structure unless MKRF-specific
  source evidence requires a different contract.
- When a later task needs an explicit acceptance gate, define it in terms of:
  - source evidence,
  - canonical generated outputs, and
  - benchmark comparison surfaces,
  not ad hoc convenience artifacts.

## `P60.2b` Rebuild sequencing and validation contract

The canonical MKRF rebuild lane should use the same high-level sequencing
discipline as the standalone K3Z/TSA29 pattern, while keeping the PoC package
and checkpoint-driven surfaces out of the claim boundary.

### Authoritative rebuild sequence

The ordered rebuild sequence for the future canonical MKRF lane is:

1. validate instance case and runtime contracts
   - case/config sanity;
   - required external/runtime prerequisites; and
   - docs/runtime path agreement for the active instance lane.
2. validate geospatial runtime readiness
   - shapefile/GDAL/Fiona I/O;
   - required upstream source surfaces materialized and readable; and
   - no checkpoint-derived substitutes standing in for claimed raw source.
3. compile the upstream source lane
   - source-driven preparation from `03_MappingAnalysisData/*`;
   - reviewed source-input contracts only; and
   - explicit lineage capture for the produced intermediate artifacts.
4. complete the post-yield/model-input bundle lane
   - normalized model-input tables;
   - canonical bundle/config surfaces under `config/`; and
   - explicit publication of the generated inputs that will feed the canonical
     runtime package.
5. run Patchworks preflight against the canonical rebuild package
   - runtime config;
   - XML/track/control prerequisites; and
   - launch/runtime prerequisites such as licensing and JVM wiring.
6. publish the canonical geometry/block/topology runtime surfaces
   - source-faithful runtime spatial handoff under the rebuild package;
   - explicit block/topology generation where required; and
   - separation from accepted PoC compiled-runtime evidence.
7. run Matrix Builder for the canonical rebuild package
   - regenerate runtime tracks from the canonical rebuild package;
   - synchronize XML/tracks/accounts/control surfaces to the same contract; and
   - record runtime manifests/logs as rebuild evidence.
8. run acceptance validation against benchmark/reference surfaces
   - compare selected outputs against the accepted PoC benchmark surfaces;
   - compare legacy evidence where it still matters for acceptance; and
   - record accepted redesign choices versus unresolved regressions.

### Required validation gates

Each phase above must answer a distinct question and emit explicit evidence:

- **contract gate**
  - are the rebuild inputs/config/runtime assumptions explicit and valid?
- **source gate**
  - are the claimed raw-source inputs materialized and actually being used?
- **publication gate**
  - were canonical rebuild artifacts generated into the intended package
    surfaces rather than borrowed from PoC/checkpoint evidence?
- **runtime gate**
  - can the canonical rebuild package pass Patchworks preflight and matrix build?
- **acceptance gate**
  - does the rebuilt package behave acceptably against the benchmark/reference
    surfaces the team still cares about?

### Required evidence surfaces

The rebuild lane should leave behind, at minimum:

- rebuild-spec / allowlist / run-config state under `config/`;
- lineage and evidence ledgers under `metadata/`;
- runtime logs/manifests for preflight, matrix build, and representative runs;
- canonical generated runtime artifacts under the new rebuild package in
  `models/`; and
- benchmark comparison summaries that tie rebuilt outputs back to the accepted
  PoC evidence surface.

### Explicit non-goals for this contract

This sequencing contract does not allow:

- treating `models/mkrf_patchworks_model_poc/` as the canonical rebuild
  package;
- using checkpoint-derived or compiled-runtime artifacts as substitutes for raw
  source while claiming a source-faithful rebuild;
- skipping Patchworks preflight/matrix-build and treating static file presence
  as rebuild validation; or
- treating unexplained legacy seams as required by default just because they
  existed in the PoC lane.

## `P60.2c` Benchmark/reference separation contract

The canonical rebuild lane must keep the accepted PoC evidence surfaces and the
new source-faithful build surfaces distinct in both pathing and claim language.

### Benchmark/reference evidence surface

The following remain benchmark/reference evidence only:

- `models/mkrf_patchworks_model_poc/` and its generated runtime artifacts;
- accepted PoC benchmark saved-stage and report surfaces;
- accepted compiled legacy runtime evidence preserved for comparison;
- reviewed archaeology outputs such as workbook/XML/runtime translations; and
- any checkpoint target-state or helper seams that exist only to preserve PoC
  comparability.

These surfaces may be used for:

- comparison;
- acceptance-gate benchmarking; and
- lineage/documentation.

They may not be used as substitutes for canonical rebuild outputs when making a
source-faithful claim.

### Canonical rebuild surface

The future canonical MKRF rebuild lane must publish its own distinct surfaces:

- source-driven contracts under `config/`;
- source-faithful generated metadata and ledgers under `metadata/`;
- canonical generated runtime artifacts under a rebuild package in `models/`;
- rebuild-owned docs/runbooks under the standalone instance repo; and
- rebuild-owned runtime logs/manifests and acceptance summaries.

The canonical rebuild package must not reuse the PoC package path or hide new
generated artifacts inside PoC evidence directories.

### Required separation rules

- PoC and canonical rebuild runtime packages must remain path-distinct.
- Acceptance summaries must say explicitly whether they describe:
  - PoC benchmark/reference evidence; or
  - canonical rebuild outputs.
- Raw-source publication claims must point back to the upstream source lane,
  not to PoC compiled-runtime or checkpoint artifacts.
- If a PoC artifact is copied or reused for comparison, it must remain labeled
  as benchmark/reference evidence rather than being silently promoted.

### Practical implication for later phases

For `P60.3+`, every new generated artifact should answer one of two questions:

- is this a benchmark/reference surface preserved from the PoC lane? or
- is this a canonical rebuild output generated from the source-faithful lane?

If the answer is unclear, the artifact boundary is wrong and should be fixed
before stronger rebuild claims are made.

## `P60.3a` Starting source contract for geometry publication

Before any source-driven geometry rebuild work starts, the canonical upstream
starting contract is now fixed to the publication boundary already recovered
from the legacy evidence review.

### Upstream starting surface

The starting geometry source for the rebuild lane is:

- `03_MappingAnalysisData/Resultant.gdb/Resultant`

Recovered legacy evidence says:

- source feature count: `1873`
- source geometry type: `MultiPolygon`

This is the authoritative immediate precursor to legacy runtime
`Spatial/fragments.*`.

### Recovered legacy publication rule

The legacy runtime publication from `Resultant` to `fragments.*` was:

- filter:
  - `CONTCLAS != 'X'`
- excluded rows:
  - `110`
- published runtime rows:
  - `1763`
- published geometry family:
  - shapefile `Polygon`

The excluded rows were all non-forest runtime exclusions, not part of the
managed runtime fragment surface.

### Recovered field projection

The recovered runtime field projection from `Resultant` to `fragments.*` is:

- `Operability -> Operabilit`
- `Shape_Length -> Shape_Leng`
- `Shape_Area -> Shape_Area`
- `CONTCLAS -> CONTCLAS`
- `AGE_2020 -> AGE_2020`
- `AU_EX -> AU_EX`
- `AU_FU -> AU_FU`
- `RES_KEY -> RES_KEY`
- `CT_eligib -> CT_eligib`

Recovered verification from the legacy evidence lane:

- shared `RES_KEY` count: `1763`
- core-field mismatches: `0`
- true multipart shared features: `0`

So the legacy publication appears to have been:

- a narrowed runtime publication of `Resultant`; not
- an independently derived geometry family.

### What this means for the rebuild lane

`P60.3a` may start from the recovered `Resultant -> fragments` publication
contract above, but it may not treat the existing compiled `fragments.*`
payloads as the source of truth.

Allowed use of the recovered contract:

- as the starting hypothesis for source-driven publication logic; and
- as a comparison target for the rebuilt publication step.

Not allowed:

- treating legacy `Spatial/fragments.*` as raw source;
- treating archival instance copies of `fragments.*` as raw source; or
- treating checkpoint-derived geometry artifacts as substitutes for
  `Resultant.gdb/Resultant`.

This means the remaining work in `P60.3a` is implementation and verification of
that publication from upstream source surfaces, not further ambiguity about the
starting contract.

## `P60.3b` Runtime spatial/package handoff contract

Once the source-driven geometry publication step is rebuilt, the canonical MKRF
rebuild lane must publish an explicit runtime spatial handoff under the future
rebuild package in `models/`.

### Required runtime spatial package surfaces

The canonical rebuild package must publish, at minimum:

- `Spatial/fragments.*`
  - the runtime block-geometry surface used by Patchworks;
- `Spatial/topo_frag100.csv`
  - the topology sidecar required by the runtime package; and
- package-local lineage evidence showing exactly which source-driven
  publication run produced those files.

These are canonical rebuild outputs only when they are generated from the
source-faithful lane established in `P60.3a`.

### Required lineage for the handoff

The runtime spatial handoff must leave behind enough evidence to answer:

- which upstream source feature class was used;
- which filter/publication rule was applied;
- which field projection was applied;
- which runtime package path received the published outputs; and
- which rebuild run/log/manifest produced the handoff.

At minimum, the lineage surface for the handoff should capture:

- source feature count before publication;
- published feature count after publication;
- excluded feature count and reason;
- runtime field projection;
- output checksums / artifact identity; and
- the exact rebuild run or manifest ID that produced the package.

### Required acceptance checks

The runtime spatial handoff should not be treated as accepted unless all of the
following are true:

- the published runtime geometry surface is path-distinct from the PoC package;
- the published row count and field projection match the intended publication
  rule for the canonical rebuild lane;
- the runtime package contains both `fragments.*` and `topo_frag100.csv`;
- topology generation is tied explicitly to the published runtime geometry
  surface rather than borrowed from an archival compiled-runtime lane; and
- the handoff leaves enough evidence to compare the rebuilt publication against
  the recovered legacy publication contract from `P60.3a`.

### Non-goals and rejection cases

The runtime spatial/package handoff is not acceptable if it:

- copies `Spatial/fragments.*` or `topo_frag100.csv` forward from the PoC
  package;
- copies those files from archival compiled legacy evidence;
- uses checkpoint-derived geometry artifacts as the runtime publication source;
  or
- publishes runtime spatial outputs without a traceable source/run lineage.

So `P60.3b` is not "put files under `Spatial/`." It is the contract that the
new canonical runtime package receives its own source-driven spatial runtime
lane, with explicit lineage and acceptance checks.

## `P60.3c` Claim-surface exclusion rule for checkpoints and compiled-runtime artifacts

The source-faithful rebuild claim surface must exclude checkpoint-derived and
compiled-runtime artifacts as causal inputs.

### Rejected input classes for source-faithful claims

The following are not acceptable as upstream rebuild inputs:

- legacy compiled runtime `Spatial/fragments.*`;
- legacy compiled runtime `Spatial/topo_frag100.csv`;
- archival instance copies of those compiled runtime artifacts;
- checkpoint-derived geometry exports or restart artifacts; and
- any convenience copy of a previously generated runtime spatial package.

These remain valid only as:

- benchmark/reference evidence;
- debug aids; or
- comparison targets for rebuilt outputs.

### Required claim-language rule

If a later Phase 60 result depends on any of the rejected classes above, it may
be described as:

- a benchmark comparison;
- a PoC/runtime validation step; or
- a debug/recovery aid.

It may not be described as:

- a source-faithful rebuild input;
- a raw-source publication step; or
- evidence that the canonical rebuild was generated from upstream source
  surfaces.

### Naming rule for canonical rebuild outputs

Where FEMIC controls new path creation in the canonical rebuild lane, use
all-lowercase names for new files and directories.

Preserve mixed-case only when it is part of:

- archival legacy evidence;
- upstream source payloads we are not renaming; or
- external tool/runtime contracts outside FEMIC control.

This keeps the new canonical rebuild lane from inheriting the legacy model's
mixed-case path surface as an avoidable source of path errors.

## `P60.4a` Source-driven control-surface replacement contract

The canonical MKRF rebuild must replace the PoC checkpoint-backed
target-control lane with a source-driven FEMIC-native control surface.

### Rejected control inputs for the canonical rebuild

The following PoC/legacy control inputs are not acceptable as canonical rebuild
inputs:

- `analysis/initialTargetSummary.csv`
- `analysis/initialTargetStatus.csv`
- saved scenario target-state exports used only to reload a prior scenario
  state;
- fail-fast or partial helper reconstructions in legacy-style
  `InitialTargets/*.bsh`; and
- any control surface that exists only because the PoC needed a runnable
  checkpoint-backed lane.

Those files remain valid only as:

- benchmark/reference evidence;
- runtime smoke aids; or
- comparison surfaces for acceptance gates.

### Source-driven control authorities

The replacement control lane should be driven from the reviewed source
authorities already recovered in the archaeology program:

- `Targets/000_Targets_Builder.xlsx`
  - primary target-family content authority;
- recovered target script fragments such as:
  - `Targets/01_harvest.bsh`
  - `Targets/06_patch.bsh`
  - `Targets/07_flow.bsh`
- `ScenarioSet.bsh`
  - authority for scenario composition and required helper families; and
- original legacy analyst documentation where it clarifies target intent or
  scenario interpretation.

The workbook-generated target families already evidenced in the legacy corpus
include, at minimum:

- `Harvest`
- `grn`
- `biod`
- `wat`
- `vqo`
- `Routes`
- `patch`

### Required replacement outcome

The canonical rebuild lane must publish a new control surface that:

- is generated from reviewed source contracts rather than scenario checkpoints;
- can express the target families the team still intends to preserve;
- makes helper/function reconstruction explicit rather than hidden inside an
  inherited checkpoint lane; and
- keeps benchmark-only legacy helper mysteries separate from the canonical
  architecture unless they later satisfy the carry-forward gate.

### Acceptance rule for `P60.4a`

`P60.4a` is only satisfied when the rebuild lane can point to a distinct
source-driven control authority and say:

- these are the source tables/contracts that define the new control lane; and
- these checkpoint-backed target-state files are no longer the causal input for
  canonical rebuild runs.

It is not enough to keep the PoC checkpoint files around and reinterpret them
as source.

## `P60.4b` Scenario-target semantic carry-forward matrix

Legacy scenario-target semantics should be preserved, replaced, or deferred
according to the carry-forward gate:

- preserve only if justified by reviewed source evidence; or
- preserve only if benchmark necessity makes them part of the accepted PoC
  comparison surface.

Everything else is replaceable or deferrable in the canonical rebuild lane.

### Preserve as source-evidenced target families

The following target families are justified by reviewed source evidence from
the legacy corpus and may carry forward as canonical semantic families in the
rebuild lane:

- `Harvest`
  - workbook authority present in `000_Targets_Builder.xlsx`;
- `flow`
  - workbook authority present in `Harvest` plus recovered `07_flow.bsh`;
- `patch`
  - recovered script evidence present in `06_patch.bsh`;
- `grn`
  - workbook authority present in `000_Targets_Builder.xlsx`;
- `biod`
  - workbook authority present in `000_Targets_Builder.xlsx`;
- `wat` / ECA-like watershed target families
  - workbook authority present in `wat` and `ECA_targets`;
- `vqo`
  - workbook authority present in `vqo` and `VQO_targets`; and
- `Routes`
  - workbook authority present, though not currently active in the accepted
    PoC scenario lane.

These families should be reconstructed from their reviewed source contracts,
not by copying checkpoint target state.

### Preserve as benchmark-facing scenario semantics only when needed

Some semantics are not source-authoritative architecture by themselves, but may
still matter as acceptance surfaces if the rebuild is compared back to the PoC
benchmark lane.

For now, the accepted benchmark requires only:

- a harvested scenario lane that can generate the report-pair KPI surfaces used
  in the PoC benchmark; and
- enough target/control semantics to reproduce a meaningful harvested run for
  benchmark comparison.

That means benchmark necessity does **not** currently force the canonical
rebuild to inherit every legacy helper/function name or checkpoint-era control
wrapper as-is.

### Deferred unresolved helper semantics

The following helper families remain deferred because the current recovered
legacy corpus does not support a source-faithful reconstruction of their exact
helper semantics:

- `THLB4070(...)`
- `UWR(...)`

These may remain:

- benchmark/deferred seams documented from the PoC lane; and
- future reconstruction targets only if new source evidence appears or a later
  acceptance gate proves they are benchmark-critical.

They are **not** default requirements for the canonical rebuild architecture.

### Replacement rule for helper/interface shape

Even where a target family is preserved, the exact legacy helper/interface
shape does not need to be preserved unless:

- source evidence explicitly requires it; or
- benchmark necessity requires it for accepted comparison behavior.

So the canonical rebuild may:

- preserve target-family intent and parameterization; while
- replacing the legacy helper/wrapper shape with a FEMIC-native control
  contract.

### Practical carry-forward decision

For `P60.4b`, the rebuild lane should proceed as follows:

- reconstruct source-evidenced target families from workbook/script evidence;
- keep unresolved helper families such as `THLB4070(...)` and `UWR(...)`
  deferred by default;
- do not inherit checkpoint-era helper wrappers as architecture; and
- require any future exception to satisfy the existing carry-forward gate.

## `P60.4c` Exclusion rule for unexplained compiled control seams

Unexplained compiled control seams from the legacy package must stay out of the
canonical rebuild unless a later acceptance gate proves they are required.

### Excluded by default

The following should be treated as excluded from the canonical rebuild
architecture unless later justified explicitly:

- missing legacy helper-wrapper layers such as
  `InitialTargets/00_Target_Descriptions.bsh`;
- unresolved helper families such as:
  - `THLB4070(...)`
  - `UWR(...)`
- checkpoint-era target-state reload surfaces used only to recover prior
  scenario state; and
- any compiled control/helper seam that is visible in the legacy runtime lane
  but not reconstructable from reviewed source evidence.

### Allowed role for these seams

These seams may remain in project knowledge only as:

- benchmark caveats;
- deferred archaeology notes;
- comparison/debug context; or
- future reconstruction candidates if stronger evidence appears.

They are not canonical rebuild requirements by default.

### Acceptance-gate exception rule

A previously excluded control seam may enter the canonical rebuild lane only if
the team can point to a documented acceptance gate showing one of:

- reviewed source evidence now exists for the seam; or
- benchmark necessity now shows that removing the seam breaks an accepted
  comparison surface the rebuild must preserve.

Without one of those two justifications, the correct action is:

- leave the seam out of the canonical build; and
- record the omission as an intentional redesign boundary, not an accidental
  gap.

### Practical rule for later implementation

For `P60.4c` and later implementation work:

- reconstruct source-evidenced control families;
- replace legacy helper/interface shape where appropriate with FEMIC-native
  control contracts; and
- refuse to smuggle unresolved compiled helper seams back into the build just
  because they existed in the PoC or legacy runtime package.

## `P60.4d` Canonical AU key and AU-wise first-growth curve contract

The canonical rebuild lane should not inherit the legacy one-curve-per-stand
first-growth behavior. It should move to the same AU-wise unmanaged-curve
discipline already used elsewhere in FEMIC.

### Canonical AU identity rule

For the Phase 60 rebuild lane, the canonical AU key should be built from:

- `bec_zone`
- `bec_subzone`
- `bec_variant`
- `leading_species_1`
- `leading_species_2`

This replaces the earlier broader AU rule for the canonical rebuild lane unless
some later acceptance gate explicitly requires another dimension back in.

### Ordered top-2 species rule

`leading_species_1` and `leading_species_2` should be the top two species by
share, in descending share order.

That means:

- `cw+hw` and `hw+cw` are different AU keys when dominance flips; and
- the canonical rebuild is not using an unordered species pair.

### First-growth curve consolidation rule

VDYP-derived first-growth evidence may begin as stand-level evidence, but the
canonical rebuild must consolidate it to one unmanaged/first-growth curve per
AU.

The required curve-consolidation behavior is:

- aggregate stand-level first-growth evidence to the canonical AU level;
- fit AU-wise unmanaged/first-growth curves using the existing FEMIC NLLS
  functions and policy style already used for K3Z; and
- publish AU-wise unmanaged/first-growth curves as the runtime-facing surface
  consumed by the canonical XML/track-generation lane.

The legacy one-curve-per-stand first-growth implementation remains valid only
as benchmark/reference evidence. It is not part of the canonical rebuild
architecture unless a later benchmark gate proves the AU-wise NLLS approach is
insufficient.

### Publication and acceptance rule

Before `P60.5a` can be considered satisfied, the rebuild lane should publish:

- an explicit AU table proving the canonical AU key is being used;
- traceable lineage from stand-level VDYP first-growth evidence into AU-wise
  first-growth surfaces; and
- curve-fit diagnostics and acceptance checks for the AU-wise NLLS-fitted
  unmanaged curves.

In other words, `P60.5a` should consume the AU-wise first-growth lane, not
recreate a stand-wise unmanaged curve contract inside the canonical runtime
package.

## `P60.5` Canonical AU table and AU-wise first-growth curve lane

The canonical rebuild lane needs an explicit upstream model-input step between
source/control reconstruction and runtime-package generation.

This step exists to make AU definition, stand assignment, and unmanaged
first-growth curve synthesis explicit instead of hiding them inside runtime
generation.

### `P60.5a` Canonical AU table publication

The rebuild lane should publish a canonical AU table built from source-driven
geometry using:

- `bec_zone`
- `bec_subzone`
- `bec_variant`
- `leading_species_1`
- `leading_species_2`

The AU table should be a canonical generated surface with its own lineage and
acceptance checks, not an implied side effect of later runtime generation.

### Source fields and deterministic keying rule

`P60.5a` should derive the AU key from the published source geometry lane,
using reviewed source fields that can populate:

- `bec_zone`
- `bec_subzone`
- `bec_variant`
- top-2 leading species by share

The two leading species must be ordered by descending share, with a stable
deterministic tie-break if shares are equal.

Default tie-break rule:

- if the first two species shares are equal, break the tie by species code in
  ascending lexical order so AU assignment remains deterministic.

### Canonical AU publication surface

The rebuild lane should publish a canonical AU table as a generated model-input
surface under a lowercase FEMIC-controlled path.

Default publication surface:

- `data/model_input_bundle/au_table.csv`

The AU table should include, at minimum:

- a stable canonical `au_id`;
- `bec_zone`
- `bec_subzone`
- `bec_variant`
- `leading_species_1`
- `leading_species_2`
- enough provenance fields to tie each AU back to the reviewed source geometry
  and the stand/record assignment lane that follows in `P60.5b`.

### AU identifier rule

The canonical `au_id` should be deterministic and derived from the AU key
rather than inherited from legacy numeric AU identifiers.

That means the rebuild lane should not reuse:

- legacy numeric AU ids from the PoC/runtime package; or
- stand-wise legacy identifiers masquerading as canonical AU ids.

### Acceptance rule for `P60.5a`

`P60.5a` is only satisfied when the rebuild lane can point to:

- a generated `data/model_input_bundle/au_table.csv` built from the reviewed
  source geometry lane;
- an explicit mapping rule from source geometry fields into
  `bec_zone + bec_subzone + bec_variant + ordered top-2 leading species`;
- deterministic species-order handling, including the tie-break rule; and
- lineage evidence showing the AU table is canonical rebuild output rather than
  a reinterpretation of legacy or PoC AU surfaces.

### `P60.5b` Stand-to-AU assignment lineage

The rebuild lane should assign source stands/records to the canonical AUs and
publish:

- assignment lineage from source records into AU ids;
- diagnostics for unmatched/merged/sparse cases; and
- explicit evidence that the runtime lane is using the canonical AU table
  rather than reusing legacy AU assignments.

### Source-to-AU assignment inputs

`P60.5b` should use the published source geometry lane and the canonical AU
table from `P60.5a` to assign source records into canonical AU ids.

The assignment contract should be explicit about:

- which source records are being assigned;
- which fields are used to populate the canonical AU key;
- how leading-species shares are converted into
  `leading_species_1` / `leading_species_2`; and
- how records that do not fit the canonical AU key are surfaced for review.

### Required assignment publication surface

The rebuild lane should publish a canonical stand-to-AU assignment surface as a
generated model-input artifact under a lowercase FEMIC-controlled path.

Default publication surface:

- `data/model_input_bundle/stand_au_assignment.csv`

The assignment surface should include, at minimum:

- a stable source record identifier;
- the canonical `au_id`;
- the AU key fields used for the assignment;
- enough source-side provenance to connect the assignment back to the published
  source geometry lane; and
- explicit status fields for accepted, unmatched, or exceptional assignment
  outcomes.

### Required diagnostics

`P60.5b` should publish diagnostics that make assignment quality reviewable
before AU-wise curve compilation begins.

At minimum, diagnostics should answer:

- how many source records were assigned;
- how many were unmatched;
- whether any records were dropped because the top-2 species key could not be
  resolved cleanly;
- whether any very small or sparse AU groups were created; and
- whether any deterministic tie-breaks were used for equal species shares.

### Acceptance rule for `P60.5b`

`P60.5b` is only satisfied when the rebuild lane can point to:

- a generated `data/model_input_bundle/stand_au_assignment.csv`;
- explicit lineage from source records into canonical `au_id` values;
- diagnostics that make unmatched/sparse/exception cases visible; and
- evidence that later AU-wise first-growth curve synthesis will consume this
  assignment surface rather than legacy AU mappings or stand-wise runtime
  identifiers.

### `P60.5c` AU-wise first-growth VDYP curve synthesis

The rebuild lane should compile AU-wise unmanaged/first-growth VDYP curves by:

- starting from stand-level VDYP unmanaged/first-growth evidence;
- joining that evidence to the canonical AU assignment surface published by
  `P60.5b`;
- aggregating the unmanaged/first-growth evidence to one AU-wise fitting lane
  per canonical `au_id`;
- fitting one unmanaged/first-growth curve per canonical AU with the existing
  FEMIC NLLS functions and policy style already used for K3Z; and
- publishing both the AU-wise curve surface and its fit diagnostics as explicit
  canonical model-input artifacts.

### Canonical publication surfaces

`P60.5c` should publish, at minimum:

- `data/model_input_bundle/first_growth_au_curves.csv`
- `data/model_input_bundle/first_growth_au_fit_diagnostics.csv`

The first file is the canonical runtime-facing unmanaged/first-growth curve
surface. The second file is the review/debug surface that proves how each AU
curve was fit and whether it satisfied the acceptance gate.

### Required lineage

The AU-wise first-growth lane should leave behind traceable lineage showing:

- the source unmanaged/first-growth records used for each AU fit;
- the canonical `au_id` each source record was assigned to;
- the sample counts contributing to each AU fit;
- the age/value domain used for fitting; and
- the exact FEMIC NLLS policy family used for the accepted fit.

### Required diagnostics

`P60.5c` should publish diagnostics that make fit quality reviewable rather
than implicit. At minimum, the diagnostics surface should make the following
visible per AU:

- AU identifier and AU key fields;
- contributing stand/record count;
- fitted function/policy family;
- acceptance status;
- sparse-sample warning status;
- fit-quality metrics sufficient to compare accepted vs rejected candidate
  fits; and
- any fallback/rescue path that was required before acceptance.

### Acceptance rule for `P60.5c`

`P60.5c` is only satisfied when the rebuild lane can point to:

- a generated `data/model_input_bundle/first_growth_au_curves.csv`;
- a generated
  `data/model_input_bundle/first_growth_au_fit_diagnostics.csv`;
- explicit lineage from stand-level unmanaged/first-growth VDYP evidence into
  canonical `au_id`-indexed AU curves; and
- evidence that later runtime generation will consume this AU-wise curve
  surface instead of the legacy stand-wise unmanaged curve inventory.

The legacy one-curve-per-stand first-growth implementation remains benchmark
evidence only. It is not a canonical rebuild input or output surface.

### `P60.5d` Canonical top-N AU selection by cumulative area coverage

The canonical rebuild lane should not assume that the full AU universe becomes
the runtime selection surface by default.

Instead, the rebuild lane should publish an explicit top-N AU selection using
the same cumulative-area coverage pattern already used elsewhere in FEMIC.

#### Selection rule

Default canonical rule:

- sort canonical AUs by descending covered area; then
- select the smallest top-N AU subset whose cumulative area reaches at least
  `95%` of the covered area in the assignment universe.

This is the default rule-of-thumb for the canonical rebuild lane unless a
later acceptance gate proves that a different coverage threshold is required.

#### Canonical publication surface

The rebuild lane should publish the selected AU subset as a generated
model-input artifact under a lowercase FEMIC-controlled path.

Default publication surface:

- `data/model_input_bundle/selected_au_table.csv`

This surface should remain distinct from the full AU universe in
`au_table.csv`.

#### Required lineage and diagnostics

`P60.5d` should leave behind enough evidence to answer:

- total AU count in the full universe;
- selected AU count in the canonical top-N subset;
- total covered area in the assignment universe;
- cumulative covered area captured by the selected subset; and
- which AUs were excluded by the cutoff.

#### Runtime dependency rule

Unless a later acceptance gate says otherwise, downstream runtime generation in
`P60.6+` should consume the explicit selected AU subset rather than silently
using the full AU universe.

#### Implemented baseline result

The earlier provisional `80%` cutoff is no longer the governing contract for
the canonical rebuild lane.

The current MKRF selected-AU bundle now reflects the `95%` rule:

- `66` canonical AUs in the full published AU universe;
- `31` selected AUs in the canonical top-N subset; and
- realized covered-area share `0.950222` for the current `95%` cutoff.

### `P60.5e` Canonical AU and yield diagnostic plot bundle

The canonical AU input lane should publish a reproducible diagnostic plot set
for the selected AU bundle rather than relying on ad hoc inspection.

At minimum, that plot set should include:

- an updated strata/site-index distribution plot for the selected AU lane,
  with the site-index axis sized for productive MKRF values;
- AU-wise VDYP diagnostic fit plots for the selected AU subset;
- AU-wise VDYP low/medium/high site-index comparison plots for the selected
  AU subset; and
- AU-wise VDYP-vs-TIPSY comparison plots using the same logic pattern as the
  existing K3Z diagnostic surface.

These plots should be regenerated from checked-in builder commands, not from
ephemeral shell scripts.

The diagnostic plot bundle should stay synchronized with the current selected
AU cutoff. Regenerating plots against a stale `selected_au_table.csv` does not
satisfy `P60.5e`.

#### Implemented baseline result

The current MKRF plot bundle has been regenerated from the selected-AU lane
using the checked-in FEMIC command path and now includes:

- `plots/strata-tsamkrf.png` and `plots/strata-tsamkrf.pdf` with site-index
  axis upper bound `50`;
- `31` AU-wise `vdyp_lmh_tsamkrf-*.png` plots;
- `87` AU-wise `vdyp_fitdiag_tsamkrf-*.png` plots; and
- `4` `tipsy_vdyp_tsamkrf-*.png` comparison plots.

- `66` canonical AUs in the full published AU universe;
- `14` selected AUs in the default top-N subset; and
- realized covered-area share `0.808706` for the default `80%` cutoff.

## `P60.6` Provisional expert-rule managed AU-wise TIPSY/BTC lane

The canonical rebuild now has a distinct managed/planted bootstrap lane between
the AU-wise unmanaged first-growth work and the final runtime-package
generation step.

This lane is intentionally provisional:

- it is valid as rebuild scaffolding and diagnostic evidence;
- it is not yet the final reviewed MKRF managed-rule contract; and
- it must later be replaced or confirmed by reviewed managed configuration
  before final Phase 60 closeout.

### Published managed bootstrap surfaces

The managed bootstrap lane must publish, at minimum:

- `data/model_input_bundle/stand_origin_assignment.csv`
- `data/model_input_bundle/managed_au_bootstrap_table.csv`
- `data/model_input_bundle/managed_au_msyt.csv`
- `data/model_input_bundle/managed_au_run_manifest.json`

If BTC is available and runs successfully, it should also publish:

- `data/model_input_bundle/managed_au_curves.csv`

### Current implemented result

The current managed bootstrap attempt is now reproducible through checked-in
FEMIC code and CLI commands:

- `femic instance mkrf-build-managed-au-inputs`
- `femic instance mkrf-build-managed-au-curves`

Current observed MKRF result:

- selected canonical AUs: `31`
- included managed bootstrap AUs: `31`
- unmatched selected AUs: `0`
- AUs using logging-origin median managed SI: `29`
- AUs using all-stand median managed SI fallback: `2`
- compiled managed/planted curves: `31`

The managed BTC lane now runs successfully through the checked-in builder path,
but only when it uses the same copied-install/live-overlay unattended TSR mode
as the known-good direct `femic tipsy run-btc` path. The generated
`managed_au_run_manifest.json` records the successful BTC run and the canonical
`managed_au_curves.csv` output.

### Managed origin, SI, and species payload rule

The canonical AU identity remains unchanged:

- `bec_zone`
- `bec_subzone`
- `bec_variant`
- `leading_species_1`
- `leading_species_2`

Managed site index is treated as an AU attribute rather than a new AU key
dimension.

The managed lane now uses `AGE_2020` to classify stand origin explicitly:

- `AGE_2020 >= 80` -> `fire_origin`
- `AGE_2020 < 80` -> `logging_origin`

That classification is published in:

- `data/model_input_bundle/stand_origin_assignment.csv`

The managed lane now derives one deterministic `managed_si` per selected
canonical AU from assigned stands rather than legacy managed-AU lookup:

1. median site index of assigned `logging_origin` stands, if present;
2. else median site index of all assigned stands; or
3. else leave the AU unmatched.

The canonical expert-rule authority for species mix, density, and CT/clearcut
metadata is now:

- `config/tipsy/tsamkrf.yaml`

The current first-pass managed planting rules are:

- `cwh_dm_x`
  - density: `1500 sph`
  - mix: `FD 45 / CW 45 / PW 10`
  - baseline system: `clearcut`
  - `ct_eligible = true`
  - `ct_target_age = 40`
  - `ct_on_fire_origin = false`
- `cwh_vm_1`
  - density: `1500 sph`
  - mix: `FD 45 / CW 45 / PW 10`
  - baseline system: `clearcut`
  - `ct_eligible = true`
  - `ct_target_age = 40`
  - `ct_on_fire_origin = false`
- `cwh_vm_2`
  - density: `1500 sph`
  - mix: `CW 70 / FD 15 / PW 5 / BA 5 / SS 5`
  - baseline system: `clearcut`
  - `ct_eligible = true`
  - `ct_target_age = 40`
  - `ct_on_fire_origin = false`

The vm2 rule is intentionally provisional until the AU key carries an
elevation discriminator that can support a separate high-elevation
`YC`-bearing family.

### Claim boundary for `P60.6`

The accepted claim for this lane is:

- reproducible AU-wise managed/planted BTC input generation exists;
- reproducible AU-wise managed/planted BTC curve compilation now exists for
  the full current selected AU subset;
- the AU-wise planted lane is structurally compatible with the canonical
  rebuild architecture; and
- a real BTC attempt can be made and leave behind explicit success or blocker
  evidence.

The following are still *not* claimed:

- reviewed final MKRF TIPSY rule semantics;
- final canonical managed silviculture behavior; or
- benchmark parity on planted-stand behavior.

## `P60.7` Bad-curve gate before runtime generation

Canonical runtime generation is blocked until the rebuilt curve lane is good
enough to trust as a canonical input surface.

This gate exists because the current selected-unit comparison plots already
show obviously bad cases, including:

- `tipsy_vdyp_tsamkrf-11-CWHvm1_CW+FDC.png`
- `tipsy_vdyp_tsamkrf-12-CWHdmx_CW+FDC.png`

In those cases the rebuilt first-growth curve is effectively near-null while
the rebuilt managed curve is large. That is not an acceptable input state for
canonical runtime generation.

### `P60.7a` Audit contract

Audit the bad curve cases against:

- raw VDYP source rows;
- stand-to-unit assignment lineage;
- first-growth fit diagnostics;
- managed bootstrap lineage; and
- comparison plot outputs.

The goal is to determine whether each bad case comes from:

- wrong source field choice;
- wrong units or scaling interpretation;
- wrong grouping or stand-to-unit assignment;
- bad fit or aggregation behavior; or
- a truly expected source-data pattern that should be documented explicitly.

Published audit outputs:

- `data/model_input_bundle/bad_curve_audit_summary.csv`
- `data/model_input_bundle/bad_curve_audit_detail.csv`

Current audit result:

- `15` flagged units out of `31` selected units

Those outputs are now the canonical input to `P60.7b`.

### `P60.7b` Correction contract

If the bad cases are not expected source patterns, fix the relevant source
ingestion, assignment, grouping, or curve-fit logic and regenerate:

- `first_growth_au_curves.csv`
- `first_growth_au_fit_diagnostics.csv`
- `managed_au_curves.csv` if the managed side is implicated; and
- the selected-unit diagnostic/comparison plots.

The corrected outputs must be published through checked-in FEMIC builders, not
shell-only ad hoc fixes.

Current correction rule now in force:

- stands with `AGE_2020 < 80` are not treated as first-growth stands for the
  canonical VDYP first-growth lane;
- they are excluded from `first_growth_au_curves.csv` synthesis and associated
  first-growth diagnostics; and
- they remain candidates for the managed/planted lane instead of being used to
  anchor first-growth VDYP curves.

Implemented `P60.7b` correction outcomes now in force:

- units with no old-support stands are reclassified as managed-only after the
  age-floor rule instead of being kept as first-growth blockers; and
- severe right-tail underfit against observed 5-year VDYP medians originally
  triggered an `observed_bin_tail_rescue` fit path to clear the final surviving
  bad first-growth blocker (`cwh_vm_1_cw_hw`).

Follow-on modeling constraint from the subsequent review discussion now in
force:

- canonical first-growth AU curves must be AU-local only;
- do not publish whole-curve sibling or same-BEC borrowing into the canonical
  `first_growth_au_curves.csv` surface; and
- if an AU has insufficient first-growth support, leave that as an explicit
  missing/flagged/managed-only condition rather than silently substituting a
  different AU's curve.

Current post-switch surface:

- `20` selected AUs publish AU-local `smoothed_bin_pchip` first-growth curves;
- `11` selected AUs remain `insufficient_source_stands` in
  `first_growth_au_fit_diagnostics.csv`;
- the rebuilt bad-curve audit now reports `8` flagged selected AUs, all in the
  `insufficient_source_stands` class; and
- the rebuilt comparison plot bundle now publishes `18`
  `tipsy_vdyp_tsamkrf-*.png` files, because borrowed first-growth comparison
  surfaces are no longer emitted.

Runtime-policy consequence now accepted for `P60.8`:

- the `8` flagged insufficient-support AUs are not awaiting a better first-growth
  fit policy;
- all `8` already have managed/planted curves in `managed_au_curves.csv`; and
- the canonical runtime package must therefore treat those `8` AUs as
  managed-only runtime units:
  - do not require first-growth curves for them;
  - do not synthesize fallback first-growth curves for them; and
  - do not revive sibling/same-BEC borrowing as a runtime convenience seam.

- smooth first-growth curves are preferred for the canonical MKRF rebuild lane
  because Patchworks-style long-horizon harvest scheduling is better served by
  smooth volume and MAI shapes than by piecewise linear connect-the-dots
  constructions;
- the `observed_bin_tail_rescue` seam is therefore treated only as an interim
  blocker-clearing move, not as the desired long-run curve-family contract; and
- the correction lane should replace that piecewise-linear tail rescue with a
  smoother data-shaped construction that stays close to the observed 5-year
  median bins without reverting to the earlier global NLLS underfit behavior.

Adopted MKRF first-growth curve-family refinement after the subsequent
case-by-case review discussion:

- the working compromise is now a **strongly smoothed observed-bin PCHIP**
  pattern for accepted first-growth AU curves;
- rationale:
  - the earlier raw-bin / connect-the-dots shapes were very accurate and very
    precise against the binned medians, but visually too lumpy;
  - the smoother global NLLS family was visually appealing but gave away too
    much accuracy/precision on real MKRF cases;
  - three one-case prototypes (`CWHvm1_HW+CW-H`, `CWHvm2_HW+CW-H`,
    `CWHdmx_HW+CW-H`) showed that a stronger median-bin smoothing pass still
    stayed very close to the observed bins while materially reducing visible
    lumpiness;
- implementation rule:
  - build 5-year observed median bins from the age-floor-filtered VDYP support
    set;
  - apply a strong local weighted smoother to those median bins;
  - fit a monotone shape-preserving PCHIP through the smoothed anchors; and
  - use that construction as the canonical accepted first-growth curve family
    wherever the AU has enough source support to fit directly.

### `P60.7c` Acceptance gate

The curve-quality gate is now satisfied for the current MKRF rebuild lane.

Accepted gate conditions now in force:

- all previously visible bad-curve cases were audited against raw source rows,
  assignment lineage, and fit behavior;
- the accepted direct-fit curve family is now:
  - strongly smoothed observed-bin PCHIP (`smoothed_bin_pchip`);
- whole-curve sibling / same-BEC borrowing is not part of the canonical
  first-growth publication contract;
- the canonical first-growth bundle now distinguishes clearly between:
  - `20` AU-local first-growth curves; and
  - `11` `insufficient_source_stands` rows that do not publish canonical
    first-growth curves;
- within that insufficient-support surface, the currently flagged selected AUs
  are:
  - `8` selected AUs;
  - all in `insufficient_source_stands`; and
  - all already covered by managed/planted curves in
    `managed_au_curves.csv`; and
- the canonical comparison surface now publishes only the comparisons that
  remain meaningful under the no-borrow contract:
  - `18` `tipsy_vdyp_tsamkrf-*.png` plots.

Why this is acceptable for downstream runtime generation:

- direct first-growth curves are now smooth and AU-local where the source
  support is adequate;
- weak-support AUs are explicit and auditable rather than hidden behind
  borrowed curves;
- the runtime policy for those weak-support AUs is explicit:
  - treat them as managed-only runtime units; and
  - do not require, synthesize, or borrow canonical first-growth curves for
    them.

This completes `P60.7c` and clears the way for `P60.8` runtime-package work.

## `P60.8a` Canonical runtime-package generation contract

The canonical rebuild lane must generate a new runtime package from the
source-faithful geometry, control, AU, and curve surfaces already defined in
`P60.3`, `P60.4`, and `P60.5`.

This is the first step where the rebuild lane becomes a full runnable package
rather than a collection of upstream contracts.

### Canonical package root

The canonical rebuild runtime package should live at:

- `models/mkrf_patchworks_model/`

This path is distinct from the accepted PoC package:

- `models/mkrf_patchworks_model_poc/`

The rebuild lane must not overwrite, borrow from, or silently alias the PoC
package path.

### Lowercase package layout

Because this is a new FEMIC-controlled runtime surface, the canonical rebuild
package should use lowercase names wherever FEMIC controls the path.

The minimum package layout should therefore be:

- `models/mkrf_patchworks_model/analysis/`
- `models/mkrf_patchworks_model/xml/`
- `models/mkrf_patchworks_model/tracks/`
- `models/mkrf_patchworks_model/spatial/`
- `models/mkrf_patchworks_model/scripts/`
- `models/mkrf_patchworks_model/targets/`
- `models/mkrf_patchworks_model/initial_targets/`

If Patchworks or another external runtime contract later proves that some path
must stay mixed-case, record that as an explicit runtime exception rather than
defaulting back to the legacy naming pattern.

### Required generated runtime surfaces

`P60.8a` should publish, at minimum:

- canonical runtime XML under `xml/`;
- canonical runtime tracks under `tracks/`;
- canonical runtime spatial publication under `spatial/`;
- canonical runtime control/analysis surfaces under `analysis/`,
  `scripts/`, `targets/`, and `initial_targets/`; and
- package-local lineage evidence that ties those outputs back to the source
  contracts already fixed in `P60.3` and `P60.4`.

Those runtime outputs must be generated from the canonical rebuild lane, not
copied from:

- the PoC package;
- archival compiled legacy runtime evidence; or
- checkpoint-derived helper/runtime surfaces.

### Current source-lane blocker

The canonical `P60.8a` package now has rebuild-owned XML and analysis/control
surfaces, but the spatial lane is still blocked on one missing upstream source
payload:

- `data/source/03_MappingAnalysisData/Resultant.gdb`

That expected instance-local source path is now fixed in the checked-in
contract:

- `external/femic-mkrf-instance/config/source_inputs.mkrf_rebuild.yaml`

Until that payload is materialized under the instance, `P60.8a` should be
treated as blocked on source availability rather than blocked on more
XML/control generation.

The canonical spatial publisher may not satisfy this blocker by substituting:

- `data/legacy_mkrf/compiled_spatial/*`;
- `models/mkrf_patchworks_model_poc/Spatial/*`; or
- checkpoint-derived geometry artifacts.

### Curve and AU dependency rule

The canonical runtime package must consume:

- the canonical AU table defined by
  `bec_zone + bec_subzone + bec_variant + ordered top-2 leading species`; and
- the AU-wise unmanaged/first-growth curves produced by `P60.5`; and
- the AU-wise managed/planted curve lane or explicit managed blocker evidence
  produced by `P60.6`.

That means the canonical XML and track-generation lane may not:

- emit one unmanaged/first-growth curve per stand; or
- bypass the AU-wise NLLS-fitted first-growth surface while still claiming a
  canonical rebuild runtime package.

### Acceptance rule for `P60.8a`

`P60.8a` is only satisfied when the rebuild lane can point to all of the
following:

- a path-distinct canonical runtime package under
  `models/mkrf_patchworks_model/`;
- explicit AU tables and AU-wise first-growth lineage feeding the runtime
  generation step;
- generated XML, tracks, spatial outputs, and control surfaces inside that
  canonical package; and
- package-local lineage evidence showing those outputs were generated from the
  source-faithful rebuild lane rather than copied from benchmark/reference
  artifacts.

## `P60.8b` Matrix Builder and runtime-assembly acceptance contract

After the canonical runtime package has been generated, the rebuild lane must
prove that Patchworks can assemble and use that package as a real runtime
surface.

This step is not satisfied by static file presence alone.

### Required runtime sequence

The canonical rebuild lane should, in order:

- run Patchworks preflight against the canonical package;
- run Matrix Builder against the canonical XML, control, and spatial surfaces
  under `models/mkrf_patchworks_model/`;
- regenerate the canonical runtime tracks from that Matrix Builder run; and
- assemble or launch the canonical runtime package far enough to prove the
  rebuilt package is actually runnable.

### Required generated evidence

`P60.8b` should leave behind, at minimum:

- preflight logs/manifests tied to the canonical package path;
- Matrix Builder logs/manifests tied to the canonical package path;
- regenerated `tracks/` outputs that come from that Matrix Builder run;
- runtime-stage or runtime-launch evidence showing the canonical package can be
  assembled as a working Patchworks surface; and
- enough lineage to connect those runtime results back to the canonical XML,
  AU table, AU-wise first-growth curves, and source-driven control surface.

### Acceptance rule for Matrix Builder outputs

The canonical rebuild lane must not treat Matrix Builder success as real unless
all of the following are true:

- the run targets the canonical package under `models/mkrf_patchworks_model/`;
- the runtime XML, spatial package, and control surfaces used by Matrix Builder
  are the canonical rebuild outputs rather than PoC or archival copies;
- the `tracks/` surfaces are regenerated by that run rather than reused from
  PoC, checkpoint, or archival runtime evidence; and
- the runtime assembly/launch evidence matches the same canonical package
  rather than a different package path.

### Explicit rejection rules

`P60.8b` is not satisfied by any of the following:

- running Matrix Builder against the PoC package and reinterpreting the result
  as a canonical rebuild check;
- copying previously generated `tracks/` outputs into the canonical package;
- validating only XML presence without a Matrix Builder run; or
- validating only Matrix Builder completion without any runtime-assembly or
  launch evidence tied to the canonical package.

## Post-`v0.0.1a1` CT legacy-parity follow-up (`#180`)

The next MKRF follow-up after the canonical `v0.0.1a1` alpha release is not a
new silviculture redesign. It is a legacy-parity repair for commercial
thinning (`CT`) semantics in the canonical lane.

### Governing behavioral contract

Use the source XML as the contract surface, not compiled runtime outputs as the
primary source of truth:

- legacy source XML:
  `external/femic-mkrf-instance/data/legacy_mkrf/generated_xml/baseMKRF.xml`
- PoC benchmark XML:
  `external/femic-mkrf-instance/models/mkrf_patchworks_model_poc/XML/baseMKRF.xml`

Both surfaces implement the same CT approximation:

- CT eligibility:
  `status in managed and oper in operable and ct eq 'Y' and not startswith(au,'t')`
- treatment contract:
  `label="CT"`, `minage="40"`, `maxage="150"`, `retain="20"`
- transition:
  `treatment='CT'` and `au='thn_'+au`
- treatment-year extracted harvest/product signal:
  `0.4 * base curve`
- post-thin standing THN signal for later ages:
  `0.6 * base curve(x)`

This is a constant proportional gap model. It is not the constant absolute gap
formulation `f(x) - 0.4 * f(x_ct)`.

### Current canonical divergence

The current canonical generator still diverges from the legacy/PoC contract in
the place that matters most for CT economics:

- it already carries the `0.6` residual/thinned standing logic; but
- it does not yet emit a distinct `0.4` CT treatment-year extraction surface;
- and it currently uses the simplified `au=auf` + `statecode='THN'` treatment
  contract instead of the legacy/PoC `au='thn_'+au` transition.

That means CT is still modeled as an obviously degraded option in the canonical
lane because the removed commercial volume is not being represented correctly.

### Required repair sequence

The CT parity follow-up should proceed in this order:

1. update instance and parent docs so they explain the exact legacy/PoC CT
   contract and the current canonical divergence clearly;
2. repair the canonical runtime generator so CT matches the legacy/PoC select,
   transition, and `0.4`/`0.6` split exactly; and
3. regenerate the canonical runtime package, rerun Matrix Builder, rerun the
   `100000`-iteration even-flow smoke, and inspect representative CT-active
   outputs before claiming parity.

### Out-of-scope improvement work

Do not redesign CT response curves in this follow-up. In particular, do not
replace the legacy proportional-gap model with:

- a constant absolute gap model;
- a post-thin growth boost / rebound model; or
- any new end-user CT calibration knobs.

Those are valid later enhancements, but they are not part of the legacy-parity
repair governed by `#180`.

### Implementation closeout

The CT legacy-parity implementation branch now matches that contract:

- the canonical generator emits the legacy/PoC CT select statement plus
  `retain="20"` and `au='thn_'+au`;
- the canonical yield/product logic now separates:
  - treatment-year CT extraction = `0.4 * base curve`; and
  - post-thin THN standing yield = `0.6 * base curve(x)`;
- the canonical runtime package has been regenerated from that repaired
  generator;
- Matrix Builder completed cleanly on the rebuilt canonical package;
- the canonical `100000`-iteration even-flow smoke completed cleanly; and
- representative rebuilt CT-active runtime outputs now prove the expected
  `0.4` / `0.6` split directly.

## Post-`v0.0.1a1` archival legacy-package publication (`femic-mkrf-instance#1`)

The next MKRF follow-up after the CT legacy-parity repair is to publish the
already-copied full legacy package as a first-class archival/reference lane in
the standalone instance docs and metadata surface.

### Governing publication contract

Treat this as a publication-clarity task, not a renewed archaeology/import
task. The required legacy payload is already present under:

- `external/femic-mkrf-instance/data/legacy_mkrf/compiled_controls/`
- `external/femic-mkrf-instance/data/legacy_mkrf/compiled_tracks/`
- `external/femic-mkrf-instance/data/legacy_mkrf/compiled_spatial/`
- `external/femic-mkrf-instance/data/legacy_mkrf/generated_xml/`

The work is to make that archive legible and first-class in the instance repo,
while keeping the active runtime boundary unchanged.

### Required boundary

The published docs and README surface must preserve this distinction:

- legacy package under `data/legacy_mkrf/` = archival/reference only;
- PoC package under `models/mkrf_patchworks_model_poc/` = retained
  benchmark/reference evidence only; and
- canonical package under `models/mkrf_patchworks_model/` = active
  runtime/operator lane.

No part of this archival publication work should repoint defaults back to the
legacy or PoC package.

### Required publication sequence

Proceed in this order:

1. record the archival-publication contract in roadmap/planning surfaces;
2. add one explicit legacy-archive docs lane plus matching README/lineage
   links inside `femic-mkrf-instance`;
3. rebuild standalone instance docs warning-clean; and
4. close `femic-mkrf-instance#1` only after the archive is easy to inspect
   locally and the canonical lane remains the default.

### Implementation closeout

The archival-publication issue is now complete:

- the full already-copied legacy package remains under
  `external/femic-mkrf-instance/data/legacy_mkrf/`;
- the standalone instance docs now include
  `docs/legacy-archive-reference.rst` as the first-class guide to that
  archive surface;
- the guide, anatomy, evidence, and crosswalk pages now link directly to the
  archive guide instead of only mentioning `data/legacy_mkrf/` in passing;
- the instance README now states explicitly that the legacy package is present
  for record/traceability/comparative debugging, not as the active runtime
  lane; and
- `femic-mkrf-instance#1` is closed after the standalone docs rebuilt
  warning-clean.

## Post-legacy MKRF CT redesign (`#182`)

The next MKRF modeling phase is no longer about legacy parity or publication.
It is a canonical CT redesign beyond the legacy proportional-gap model.

### Governing redesign contract

Treat the current legacy/PoC CT behavior as benchmark/reference only:

- treatment-year CT extraction:
  `0.4 * base curve`
- post-thin standing THN yield for later ages:
  `0.6 * base curve(x)`

The next canonical target is instead a bucketed constant-absolute-gap model:

- CT treatment-year extraction remains anchored at CT age; and
- post-CT THN standing volume should follow
  `base curve(x) - 0.4 * base curve(x_ct)` rather than a constant proportional
  gap.

Because canonical ForestModel XML does not expose a clean dynamic "age at
which CT was applied" state hook for this use case, the redesign will
discretize CT into precompiled treatment buckets rather than a single
continuous-age treatment.

Locked bucket contract:

- 10-year midpoint buckets;
- treatment labels `CT40`, `CT50`, `CT60`, ...;
- age windows `35-44`, `45-54`, `55-64`, ...; and
- per-bucket thinned AU/state lanes so extracted and residual curves stay
  auditable by bucket anchor age.

### Required runtime boundary

Unless the redesign proves otherwise, preserve the rest of the accepted CT
runtime contract:

- CT eligibility remains
  `status in managed and oper in operable and ct eq 'Y' and not startswith(au,'thn_')`;
- CT remains a transition to bucket-specific `thn_` AU/state lanes;
- CC remains valid from the thinned lane and returns the stand to the
  treated/post-clearcut pathway; and
- no new end-user CT knobs are introduced in this phase.

### Decision bar

Judge the redesign primarily on CT-vs-no-CT full-rotation harvested-volume
behavior.

The redesign should be treated as successful only if:

- CT treatment-year extraction remains explicit and nonzero;
- post-CT standing volume no longer drifts farther behind untreated curves
  solely because of the old proportional-gap artifact; and
- representative lower-bucket and higher-bucket CT outputs both remain
  numerically coherent under the precompiled bucket response contract; and
- the resulting CT + CC full-rotation harvested-volume behavior is defensible
  relative to the no-CT baseline.

### Release framing

This redesign is intended to ship as MKRF release `v0.0.2a1`.

That release tag must remain distinct from `v0.0.1a1`, which now refers to the
legacy-parity CT checkpoint rather than the redesign.
