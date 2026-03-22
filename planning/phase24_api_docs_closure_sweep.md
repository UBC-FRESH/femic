# Phase 24 API Docs Closure Sweep (2026-03-22)

## Purpose
This artifact closes the loop for `P24.1d` by explicitly classifying every API
page that remains generated-only after the curated rewrite passes.

The goal is to avoid an unbounded "rewrite forever" standard. Generated-only
pages are acceptable when they are:

- package namespace surfaces with little or no standalone narrative value;
- leaf/helper modules whose operational meaning is already explained by a
  curated parent/seam page plus Guides;
- niche integration modules that are useful mainly for symbol discovery.

Modules should be promoted to curated pages when they still block comprehension
of real maintenance work because they own cross-module contracts, reproducible
artifact policy, or high-leverage runtime boundaries.

## Promoted in the final closure pass

These modules were still important enough to warrant curated pages before
closing `P24.1d`:

- `femic.rebuild_spec`
  - reason: owns rebuild-spec schema and validation contract.
- `femic.rebuild_baseline`
  - reason: owns baseline snapshot/diff contract used in regression gating.
- `femic.rebuild_invariants`
  - reason: owns rebuild metric collection and invariant evaluation.
- `femic.rebuild_runner`
  - reason: owns deterministic rebuild step execution/report semantics.
- `femic.release_packaging`
  - reason: owns student-facing release bundle contract and artifact minimums.

## Acceptable generated-only pages

### Package namespace surfaces

- `femic`
- `femic.cli`
- `femic.fmg`
- `femic.pipeline`
- `femic.vdyp`

Rationale:
- these are namespace/grouping surfaces rather than primary maintenance seams;
- curated children now carry the real operational narrative.

### Subsumed by curated parent or seam pages

- `femic.account_surface`
- `femic.fmg.adapters`
- `femic.fmg.core`
- `femic.fmg.woodstock`
- `femic.pipeline.diagnostics`
- `femic.pipeline.legacy_context`
- `femic.pipeline.managed_curves`
- `femic.pipeline.plots`
- `femic.pipeline.pre_vdyp`
- `femic.pipeline.species_volume`
- `femic.pipeline.stages`
- `femic.pipeline.stands`
- `femic.pipeline.tipsy_config`
- `femic.pipeline.tipsy_legacy`
- `femic.pipeline.tsa`
- `femic.pipeline.vdyp`
- `femic.pipeline.vdyp_curves`
- `femic.pipeline.vdyp_io`
- `femic.pipeline.vdyp_logging`
- `femic.pipeline.vdyp_overrides`
- `femic.pipeline.vdyp_sampling`
- `femic.pipeline.vri`
- `femic.vdyp.reporting`
- `femic.workflows.legacy_resources`

Rationale:
- these modules are real code, but their operational role is already explained
  by the curated pages for `femic.pipeline.vdyp_stage`,
  `femic.pipeline.tipsy`, `femic.pipeline.siteprod`,
  `femic.workflows.legacy`, `femic.pipeline.bundle`, and related Guides;
- generated autodoc remains useful for symbol discovery and parameter details
  without needing a separate hand-authored intro for each leaf helper.

### Specialized or secondary integration surfaces

- `femic.ws3_bridge`
- `femic.ws3_smoke`

Rationale:
- these are narrower integration/testing helpers, not first-line runtime seams;
- generated docs are sufficient until WS3-oriented maintenance becomes a larger
  recurring workflow in FEMIC itself.

## Closure decision

After the rebuild/release promotion pass above, every API page left as
generated-only is explicitly classified as acceptable generated-only.

That satisfies the intended finish line for:

- `P24.1d.3` classify the remaining generated-only pages;
- `P24.1d.4` promote any pages that still blocked comprehension of real
  maintenance tasks;
- `P24.1d.5` confirm the remaining generated-only pages are intentionally left
  generated-only rather than silently unfinished.
