# MKRF FEMIC-Native Rebuild Notes

Issue: `#173`

## Summary

This note is the active planning surface for the from-scratch MKRF rebuild
lane.

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

Active next bounded move:

- `P60.2b`
  define the authoritative rebuild sequencing and validation contract for the
  canonical MKRF rebuild lane.

Planned immediately after:

- `P60.2c`
  keep benchmark/reference artifacts clearly separated from the new
  source-faithful build surfaces.

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
  rebuild the full MKRF runtime package from source-faithful inputs;
- `P60.7`
  validate the rebuilt model against the accepted PoC benchmark and relevant
  legacy evidence; and
- `P60.8`
  publish closeout docs and decide whether umbrella issue `#172` can close.

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
  rebuild the full MKRF runtime package from source-faithful inputs and publish
  the new canonical runtime outputs;
- `P60.7`
  validate the rebuilt model against the accepted PoC benchmark surfaces and
  the legacy evidence that still matters for acceptance; and
- `P60.8`
  publish closeout docs and decide whether umbrella legacy-recovery issue
  `#172` can close once the from-scratch rebuild is complete.

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

### `P60.5c` AU-wise first-growth VDYP curve synthesis

The rebuild lane should compile AU-wise unmanaged/first-growth VDYP curves by:

- aggregating stand-level first-growth evidence to the canonical AU level;
- fitting AU-wise curves with the existing FEMIC NLLS functions and policy
  style already used for K3Z; and
- publishing curve-fit diagnostics and acceptance checks for the canonical
  AU-wise unmanaged curve lane.

The legacy one-curve-per-stand first-growth implementation remains benchmark
evidence only. It is not a canonical rebuild input or output surface.

## `P60.6a` Canonical runtime-package generation contract

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

`P60.5a` should publish, at minimum:

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

### Curve and AU dependency rule

The canonical runtime package must consume:

- the canonical AU table defined by
  `bec_zone + bec_subzone + bec_variant + ordered top-2 leading species`; and
- the AU-wise unmanaged/first-growth curves produced by the `P60.4d` contract.

That means the canonical XML and track-generation lane may not:

- emit one unmanaged/first-growth curve per stand; or
- bypass the AU-wise NLLS-fitted first-growth surface while still claiming a
  canonical rebuild runtime package.

### Acceptance rule for `P60.6a`

`P60.6a` is only satisfied when the rebuild lane can point to all of the
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

## `P60.6b` Matrix Builder and runtime-assembly acceptance contract

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

`P60.6b` should leave behind, at minimum:

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

`P60.6b` is not satisfied by any of the following:

- running Matrix Builder against the PoC package and reinterpreting the result
  as a canonical rebuild check;
- copying previously generated `tracks/` outputs into the canonical package;
- validating only XML presence without a Matrix Builder run; or
- validating only Matrix Builder completion without any runtime-assembly or
  launch evidence tied to the canonical package.
