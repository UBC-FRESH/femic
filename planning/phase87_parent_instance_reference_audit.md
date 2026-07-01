# Phase 87 Parent Instance Reference Audit

Date: 2026-07-01

Scope: parent FEMIC package source under `src/`. This audit excludes `tests/`,
`docs/`, `external/`, and repo root planning/changelog text, except where
`src/femic/resources/**` is called out separately as packaged runtime data.

Search terms:

```text
mkrf|k3z|tsa29|tsa_29|tfl6|femic-mkrf|femic-k3z|femic-tsa29|femic-tfl6
```

Summary finding: P86 removed the obvious MKRF workflow package and
`femic instance mkrf-*` command boundary problem, but FEMIC core still contains
direct model-instance coupling. The largest remaining code-level coupling is:

- MKRF legacy ForestModel XML builders in `femic.fmg`;
- K3Z legacy adapter/default behavior in `femic.fmg` and `femic.pipeline`;
- TSA29 strict validation and adjudication logic in `femic.named_pipelines` and
  `femic.tsr_catalog.recipes`;
- packaged resource registries and templates that still ship K3Z/MKRF/TSA29
  paths as built-in defaults.

No direct `tfl6` or `femic-tfl6` references were found under `src/`.

## Hit Inventory

Approximate match counts by file from `rg --count-matches`:

| File | Count | Primary instance(s) | Notes |
| --- | ---: | --- | --- |
| `src/femic/resources/patchworks/variants.builtin.yaml` | 136 | K3Z, MKRF | Packaged Patchworks scenario/variant registry. |
| `src/femic/fmg/patchworks.py` | 103 | MKRF | Real implementation code for legacy MKRF XML recovery/emission. |
| `src/femic/tsr_catalog/recipes.py` | 62 | TSA29 | Real implementation and adjudication logic for TSA29 strict/reviewed TSR lanes. |
| `src/femic/named_pipelines.py` | 21 | TSA29 | Real execution/validation hooks for `tsa29_locked_chain_strict`. |
| `src/femic/fmg/adapters.py` | 10 | K3Z | Real adapter defaults and source filenames for K3Z legacy data. |
| `src/femic/pipeline/vdyp_stage.py` | 8 | K3Z | Runtime branch/env override for K3Z VDYP fit selection. |
| `src/femic/cli/main.py` | 6 | TSA29, MKRF, K3Z | Mostly CLI help/defaults plus one TSA29-specific report command docstring. |
| `src/femic/fmg/__init__.py` | 4 | MKRF | Public exports for MKRF legacy XML builders. |
| `src/femic/resources/builtins/instances.builtin.yaml` | 9 | K3Z, TSA29 | Built-in instance catalog. |
| `src/femic/resources/instance/config/patchworks.runtime.windows.yaml` | 3 | K3Z | Generic instance template still points at K3Z paths. |
| `src/femic/resources/patchworks/btc_indicator_bank_compile_recipes.yaml` | 2 | K3Z | BTC indicator recipe comments/market proxy notes. |
| `src/femic/patchworks_runtime.py` | 2 | K3Z | Comments only. |
| `src/femic/pipeline/tsa.py` | 3 | K3Z | Generic helper with K3Z-specific stratum-count override. |
| `src/femic/pipeline/plots.py` | 1 | K3Z | K3Z-specific plot y-limit. |
| `src/femic/pipeline/vdyp_overrides.py` | 1 | TSA29 | Default fallback override comment and data key. |
| `src/femic/resources/instance/config/tipsy/template.case.yaml` | 1 | K3Z | Template comment only. |

## MKRF Findings

### MKRF-1: `femic.fmg.patchworks` still owns MKRF legacy XML implementation

Evidence:

- `src/femic/fmg/patchworks.py:65` and `:68` define MKRF review-extract paths
  under `metadata/mkrf_xlsm_review/...`.
- `src/femic/fmg/patchworks.py:71` and `:80` define MKRF-specific output and
  required-field constants.
- `src/femic/fmg/patchworks.py:2315` defines
  `build_legacy_mkrf_forestmodel_xml_tree`.
- `src/femic/fmg/patchworks.py:2527` defines
  `emit_legacy_mkrf_forestmodel_xml`.
- `src/femic/fmg/__init__.py:17` and `:18` import these builders into the
  public `femic.fmg` namespace; `:64` and `:65` export them.

Assessment: this is the same class of boundary issue as P86, just in a
different subsystem. FEMIC core still contains a mature MKRF-specific
scientific/runtime implementation. It belongs in the MKRF instance package or a
separately installable MKRF companion package, with FEMIC core retaining only
generic ForestModel/Patchworks XML primitives.

Recommended action: create a follow-on phase to move the legacy MKRF
ForestModel XML builder and its tests into `external/femic-mkrf-instance` under
`mkrf_femic`, leaving generic XML construction helpers in FEMIC only if they are
truly instance-neutral.

### MKRF-2: Parent CLI still documents MKRF-specific export input semantics

Evidence:

- `src/femic/cli/main.py:1248` describes
  "Optional MKRF-first translated Input Variables YAML."

Assessment: this is not a command namespace leak, but it is still an
instance-specific mental model in a generic export option. It likely exists
because the generic exporter was generalized from MKRF evidence.

Recommended action: reword as generic "legacy translated Input Variables YAML"
after MKRF XML builder extraction, or move the option to MKRF-owned CLI if it is
not used outside MKRF.

### MKRF-3: Parent packaged Patchworks variant registry still ships MKRF entries

Evidence:

- `src/femic/resources/patchworks/variants.builtin.yaml:5` registers
  `instance_id: mkrf`.
- `src/femic/resources/patchworks/variants.builtin.yaml:148` registers
  `variant_id: mkrf.base`.
- `src/femic/resources/patchworks/variants.builtin.yaml:167` registers
  `variant_id: mkrf.poc_base`.

Assessment: this is packaged data rather than Python implementation, but it
still hardcodes instance paths under `external/femic-mkrf-instance`. It creates
a parent package expectation that MKRF is a built-in runtime surface.

Recommended action: after MKRF owns its implementation package, move MKRF
Patchworks variant definitions into the MKRF instance repo or into an
entry-point-discoverable registry. Parent FEMIC should support loading external
variant registries rather than shipping MKRF-specific variants by default.

## K3Z Findings

### K3Z-1: `femic.fmg.adapters` has hardcoded K3Z data filenames and case code

Evidence:

- `src/femic/fmg/adapters.py:230` reads `tipsy_params_tsak3z.xlsx`.
- `src/femic/fmg/adapters.py:253` reads `03_input-tsak3z.csv`.
- `src/femic/fmg/adapters.py:297` and `:355` read
  `tipsy_curves_tsak3z.csv`.
- `src/femic/fmg/adapters.py:409` and `:410` read
  `ria_vri_vclr1p_checkpoint1-tsak3z.feather` and
  `vdyp_lyr-tsak3z.feather`.
- `src/femic/fmg/adapters.py:424`, `:436`, `:456`, and `:461` hardcode
  `k3z` in assignment/lookup logic.

Assessment: this is real adapter logic, not just examples. It is probably
legacy K3Z adapter code inside what now looks like a generic `femic.fmg`
module. This should become either:

- instance-owned K3Z adapter code, if still required for K3Z; or
- a generic adapter parameterized by filename/case-code config.

Recommended action: split `femic.fmg.adapters` into generic adapter primitives
and K3Z adapter bindings. Move the K3Z bindings into the K3Z instance repo if
that repo is expected to be first-class in the same way MKRF now is.

### K3Z-2: K3Z runtime defaults remain in generic CLI and instance templates

Evidence:

- `src/femic/cli/main.py:1271` defaults release packaging to
  `output/patchworks_k3z_validated`.
- `src/femic/resources/instance/config/patchworks.runtime.windows.yaml:10`
  points fragments to `../output/patchworks_k3z_validated/fragments/fragments.dbf`.
- `src/femic/resources/instance/config/patchworks.runtime.windows.yaml:11`
  points tracks to `../models/k3z_patchworks_model/tracks`.
- `src/femic/resources/instance/config/patchworks.runtime.windows.yaml:12`
  points ForestModel XML to `../output/patchworks_k3z_validated/forestmodel.xml`.

Assessment: these are not implementation algorithms, but they make K3Z the
implicit generic template. That is bad package hygiene now that FEMIC has
multiple instance repos.

Recommended action: replace K3Z paths in generic templates with case-neutral
placeholder paths such as `models/<case>_patchworks_model/...` or move K3Z
templates into the K3Z instance repository.

### K3Z-3: K3Z-specific VDYP and plotting behavior remains in generic pipeline

Evidence:

- `src/femic/pipeline/plots.py:25` defines `tipsy_vdyp_ylim_for_tsa`.
- `src/femic/pipeline/plots.py:31` returns `(0.0, 2000.0)` when `tsa == "k3z"`.
- `src/femic/pipeline/tsa.py:11` defines `TARGET_NSTRATA_BY_TSA`.
- `src/femic/pipeline/tsa.py:18` adds `"k3z": 4`.
- `src/femic/pipeline/vdyp_stage.py:3595` reads
  `FEMIC_K3Z_FORCE_TAIL_BLEND`.
- `src/femic/pipeline/vdyp_stage.py:3597` branches on `tsa == "k3z"`.
- `src/femic/pipeline/vdyp_stage.py:3644` excludes K3Z from later gate-rescue
  logic.

Assessment: these are algorithm/runtime branches keyed to one instance. They
should not live as special-case checks in generic pipeline functions.

Recommended action: replace K3Z branches with instance/run-profile policy
configuration:

- plot y-limits from config;
- target stratum count from run profile or AU/stratification config;
- VDYP fit-selection policy from `config/vdyp_fit_policy.yaml` or a typed
  equivalent.

### K3Z-4: Parent packaged Patchworks registry is dominated by K3Z scenarios

Evidence:

- `src/femic/resources/patchworks/variants.builtin.yaml:9` through `:147`
  define many `k3z.*` variants and paths under `external/femic-k3z-instance`.
- `src/femic/resources/patchworks/variants.builtin.yaml:179` defines
  `k3z.proving_ground`.

Assessment: this is packaged data, not Python implementation, but it makes
parent FEMIC carry a K3Z scenario catalogue. It is defensible only if FEMIC
intentionally ships K3Z as a built-in teaching/demo instance. Even then, this
registry should probably be supplied by the K3Z instance package.

Recommended action: move built-in K3Z variants to K3Z ownership after a generic
external/entry-point variant registry mechanism exists.

## TSA29 Findings

### TSA29-1: `named_pipelines.py` has hardcoded TSA29 strict-chain execution

Evidence:

- `src/femic/named_pipelines.py:988` defines
  `_validate_tsa29_locked_chain_strict_result`.
- `src/femic/named_pipelines.py:1194` defines
  `_resolve_tsa29_locked_chain_strict_row_order`.
- `src/femic/named_pipelines.py:1205` and `:1219` resolve TSA29 locked-chain
  ledger entries.
- `src/femic/named_pipelines.py:1336` defines
  `_materialize_tsa29_glb_checkpoint_from_result`.
- `src/femic/named_pipelines.py:1367` defines
  `_validate_tsa29_locked_chain_strict_preflight`.
- `src/femic/named_pipelines.py:1518` defines
  `_run_tsa29_strict_sequence_from_checkpoint`.
- `src/femic/named_pipelines.py:1701` and `:1853` branch on
  `contract_kind == "tsa29_locked_chain_strict"`.

Assessment: this is real execution/validation code for one instance-specific
research lane. It is more deeply embedded than the P86 MKRF command wrappers
were. It probably grew because TSA29 was the active adjudication workbench.

Recommended action: do not rip this out casually. First define a generic
"strict locked-chain validation contract" interface, then move TSA29-specific
ledger semantics and row interpretation into the TSA29 instance repo or a
TSA29 adapter package.

### TSA29-2: `tsr_catalog.recipes` has large TSA29-specific TSR interpretation
logic

Evidence:

- `src/femic/tsr_catalog/recipes.py:277` defines
  `_TSA29_TABLE3_ROW_CLASSIFICATIONS`.
- `src/femic/tsr_catalog/recipes.py:5670`, `:5712`, `:5766`, and `:5784`
  branch on `resolved_instance_root.name.casefold() == "femic-tsa29-instance"`.
- `src/femic/tsr_catalog/recipes.py:5762` defines
  `_reject_tsa29_legacy_checkpoint_path`.
- `src/femic/tsr_catalog/recipes.py:16084` defines
  `_tsa29_reconstruction_gap_interpretation_override`.
- `src/femic/tsr_catalog/recipes.py:16089` checks
  `recipe.tsa.tsa_id == "tsa_29"`.
- Many strings between roughly `:2692` and `:4205` encode TSA29 TSR source
  interpretation notes and accepted public-layer limitations.
- `src/femic/tsr_catalog/recipes.py:17402` documents a "TSA29-first THLB
  comparison report".

Assessment: this is a mixture of general TSR machinery and TSA29 adjudication
knowledge. It is not just a path leak. It is a real domain-interpretation
bundle embedded in the parent package.

Recommended action: split the TSR recipe engine from instance-specific
adjudication overlays. The long-term shape should be:

- FEMIC core owns TSR extraction, recipe schemas, execution primitives, and
  generic reports;
- instance repos own reviewed/adopted interpretations, locked-chain ledgers,
  no-op decisions, and gap overrides;
- optional adapters can register instance-specific validators/report sections.

### TSA29-3: TSA29 fallback override remains in generic VDYP override defaults

Evidence:

- `src/femic/pipeline/vdyp_overrides.py:35` comments that TSA29 suppresses a
  pathological early-age spike for `SBPS_PL` low-SI curve.
- The default override map includes `"29": {("SBPS_PL", "L"): {"skip1": 50}}`.

Assessment: this is a relatively small data default, but it is still an
instance/TSA-specific policy in core. This is less severe than the named
pipeline/TSR embedding because it is table-like and already fits a config shape.

Recommended action: move TSA-specific curve overrides into instance
`config/vdyp_fit_policy.yaml` files, and keep core defaults minimal or purely
provincial/generic.

### TSA29-4: Built-in instance catalog ships TSA29 as a built-in example

Evidence:

- `src/femic/resources/builtins/instances.builtin.yaml:18` registers
  `builtin_id: tsa29`.
- `src/femic/resources/builtins/instances.builtin.yaml:20` points to
  `https://github.com/UBC-FRESH/femic-tsa29-instance.git`.

Assessment: this is a catalog reference, not runtime implementation. It is
probably acceptable if FEMIC intentionally supports installing curated example
instances. The concern is not the existence of the catalog, but the fact that
other code paths assume TSA29-specific semantics inside generic engines.

Recommended action: retain only lightweight catalog metadata in core. Move
instance behavior into the instance package or config.

## TFL6 Findings

No direct `tfl6` or `femic-tfl6` references were found under `src/`.

Assessment: TFL6 currently appears cleaner than MKRF, K3Z, and TSA29 from the
parent-package coupling perspective.

## Resource Findings

The `src/femic/resources/**` tree intentionally packages default data. Those
references are lower risk than Python branches, but they still matter because
they shape installed-package behavior.

Notable resources:

- `src/femic/resources/patchworks/variants.builtin.yaml`: K3Z/MKRF built-in
  Patchworks variants and scenario sets.
- `src/femic/resources/builtins/instances.builtin.yaml`: K3Z/TSA29 instance
  clone/install catalog.
- `src/femic/resources/instance/config/patchworks.runtime.windows.yaml`: generic
  instance template still contains K3Z paths.
- `src/femic/resources/patchworks/btc_indicator_bank_compile_recipes.yaml`:
  comments refer to K3Z-specific CT/market species assumptions.

Recommendation: distinguish "catalog of known public example instances" from
"generic template defaults". Catalog entries may remain in core for now if the
intent is to provide a launcher/discovery surface. Generic templates should not
use K3Z paths or assumptions.

## Severity Ranking

1. High: MKRF legacy XML builders in `femic.fmg.patchworks` and exports in
   `femic.fmg.__init__`.
2. High: TSA29 strict-chain validation in `femic.named_pipelines`.
3. High: TSA29 TSR interpretation/adjudication overlays in
   `femic.tsr_catalog.recipes`.
4. Medium-high: K3Z data adapters in `femic.fmg.adapters`.
5. Medium: K3Z runtime branches in `pipeline.vdyp_stage`, `pipeline.plots`, and
   `pipeline.tsa`.
6. Medium: K3Z/MKRF built-in Patchworks variant registry.
7. Low-medium: K3Z paths in generic instance template.
8. Low: CLI help strings/comments that mention K3Z/MKRF/TSA29 as examples.

## Proposed Follow-On Phases

### P87: Extract MKRF legacy ForestModel XML builder

Move `build_legacy_mkrf_forestmodel_xml_tree`,
`emit_legacy_mkrf_forestmodel_xml`, MKRF review-extract constants, and related
tests from `femic.fmg` into `external/femic-mkrf-instance/src/mkrf_femic`.
Leave only reusable XML helper primitives in FEMIC core.

### P88: De-K3Z generic templates and pipeline branches

Replace K3Z-specific defaults in generic CLI/templates/pipeline code with
case-neutral config surfaces. Candidate surfaces:

- release package default Patchworks dir;
- packaged `patchworks.runtime.windows.yaml` template;
- plot y-limits;
- target stratum counts;
- VDYP tail-blend/gate-rescue policy.

Move K3Z-specific adapter bindings into the K3Z instance repo if that repo is
being promoted to the same first-class ownership model as MKRF.

### P89: Separate TSA29 strict validation from generic named pipelines

Define a generic strict locked-chain validation interface, then move TSA29
ledger row-order semantics, strict checkpoint handling, and parent-step
validation into the TSA29 instance repo or a TSA29 adapter package.

### P90: Split TSR engine from instance adjudication overlays

Keep generic TSR extraction/recipe execution in FEMIC core. Move TSA29 reviewed
interpretation text, no-op tail decisions, reconstruction-gap overrides, and
instance-root checkpoint prohibitions into instance-owned overlays.

### P91: Externalize Patchworks variant registries

Keep core support for loading built-in and user registries, but allow instance
packages to expose Patchworks variant registries through explicit config or
entry points. Move K3Z/MKRF variant definitions out of core once that mechanism
exists.

## Immediate Recommendation

Start with P87. It is the closest structural analogue to P86: concrete
MKRF-owned implementation still lives in parent code, and the new
`mkrf_femic` package provides a natural home for it. After that, tackle K3Z
template/branch cleanup before attempting the deeper TSA29 split. The TSA29
work is important but riskier because it currently blends execution machinery,
reviewed TSR interpretation, and active research adjudication decisions.
