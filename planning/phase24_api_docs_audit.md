# Phase 24 API Docs Audit (2026-03-22)

## Purpose
This audit establishes the initial rewrite target list and style rules for the FEMIC API docs rebuild.
It is the concrete deliverable for:
- `P24.1a` audit the current API docs surface
- `P24.1b` define a target API-doc style guide using `ws3` and `fhops` as exemplars

## Bottom line
FEMIC's current API docs are overwhelmingly autosummary stubs. They are useful for symbol discovery, but not for understanding module purpose, contracts, workflow role, typical call patterns, invariants, or failure modes.

This is not a small presentation issue. For several of FEMIC's most important modules, the source-to-doc ratio is so extreme that the API pages are effectively unusable as documentation.

## Evidence from current FEMIC API pages
Representative source/doc size comparisons:

| Module | Source LOC | Current API page LOC |
| --- | ---: | ---: |
| `femic.cli.main` | 2700 | 32 |
| `femic.pipeline.io` | 824 | 33 |
| `femic.pipeline.siteprod` | 443 | 18 |
| `femic.pipeline.vdyp_stage` | 3468 | 44 |
| `femic.pipeline.tipsy` | 987 | 29 |
| `femic.fmg.patchworks` | 2647 | 23 |
| `femic.patchworks_runtime` | 1063 | 36 |
| `femic.workflows.legacy` | 564 | 17 |

The largest immediate pain points are:
- `femic.cli.main`
- `femic.pipeline.vdyp_stage`
- `femic.fmg.patchworks`
- `femic.patchworks_runtime`
- `femic.pipeline.io`
- `femic.pipeline.tipsy`

## What the current FEMIC API docs are missing
Across the generated pages, the most important missing pieces are:

1. Module purpose
- Why does this module exist?
- What part of the pipeline/runtime does it own?

2. Operational context
- When should someone call this module directly versus through the CLI/workflow?
- What stage boundary does it sit at?

3. Contracts and invariants
- Required inputs
- Produced artifacts
- Environment variables / path assumptions
- Failure conditions that are normal/expected versus exceptional

4. Typical usage
- Minimal working code examples
- Common call sequences
- "If you are trying to do X, start here" guidance

5. Cross-links
- Which guide page explains the workflow around this module?
- Which config/runtime docs matter?
- Which artifacts or submodules are source-of-truth?

## Useful patterns from FHOPS
FHOPS is the clearest immediate exemplar.

Good patterns worth copying:

1. Human-written package introductions before autodoc
- Example: `docs/api/fhops.planning.rst`
- Starts with a short explanation of purpose and scope
- Explains where the package fits in the system

2. Typical usage block
- FHOPS includes short code examples that show realistic call patterns
- This is much more useful than a bare symbol list

3. Practical subheadings before API dump
- Example sections like "Typical usage" and solver notes give the reader orientation before the autodoc block

4. Package-level grouping that mirrors real workflows
- FHOPS API docs are organized in a way that matches how developers think about the system

## Useful patterns from WS3
WS3 is less polished as an API-reference exemplar in this workspace, but it is still useful for two things:

1. Module-oriented coverage of the core conceptual surface
- `core`, `forest`, `financial`, `opt`, etc.
- The docs structure mirrors the conceptual decomposition of the system

2. Documentation architecture that feels like a book/manual
- More narrative and conceptual than a raw reference tree
- Helpful reminder that not everything needs to be autosummary-first

## Proposed Phase 24 style rules
These should become the working style guide for the FEMIC API rewrite.

1. Every important public module gets a hand-authored intro
- 1-3 paragraphs
- explain purpose, ownership, and where it fits in the pipeline/runtime

2. Every important module gets a "Start here if..." section
- helps both humans and coding agents orient quickly

3. Every important module gets at least one realistic usage example
- short, runnable, and tied to actual FEMIC workflows

4. Every important module gets an explicit contract section
- key inputs
- key outputs/artifacts
- config/env dependencies
- major failure modes / caveats

5. Autodoc stays, but follows narrative
- autodoc is still useful for completeness
- but it should come after the explanatory surface, not instead of it

6. Cross-link aggressively
- link API pages to guide pages, runbooks, configs, and source-of-truth artifact docs

7. Avoid parallel doc universes
- agent-friendly material should be embedded into the same docs tree as compact contract sections, tables, checklists, and "source of truth" pages
- not split into an entirely separate second documentation set

## First rewrite target set
Recommended first-wave rewrite order:

1. `femic.cli.main`
- user entrypoint
- huge surface area
- currently almost undocumented in a usable way

2. `femic.pipeline.vdyp_stage`
- one of the most complex and failure-prone runtime seams
- currently radically underdocumented relative to complexity

3. `femic.fmg.patchworks`
- critical export layer
- central to the teaching/runtime workflow

4. `femic.pipeline.io`
- path resolution and artifact selection logic are core system behavior
- especially important after recent external-data / SiteProd work

5. `femic.pipeline.tipsy`
- critical manual boundary and source of repeated operator confusion

6. `femic.patchworks_runtime`
- important operational/runtime seam

7. `femic.workflows.legacy`
- still central to real execution, despite the legacy label

## Agent-friendly docs approach
Recommended approach:
- keep one primary docs system
- add compact technical-contract surfaces inside it

Those compact surfaces should cover:
- repo invariants
- runtime prerequisites
- stage boundaries
- canonical artifacts
- external-data resolution rules
- recovery workflows
- file/path ownership maps

That gives us most of the benefit of "agent-facing docs" without creating a second parallel documentation product.

## Immediate next deliverables after this audit
1. Rewrite `docs/reference/api/index.rst`
- explain what the API reference is for
- explain how to use it alongside the guides

2. Replace the biggest stub pages with hand-authored versions first
- `femic.cli.main`
- `femic.pipeline.vdyp_stage`
- `femic.fmg.patchworks`

3. Add one compact technical-contract page in the main docs tree
- likely covering pipeline stage boundaries + canonical artifacts
- use it as the first agent-friendly docs surface
