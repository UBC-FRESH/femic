# Phase 24 Docs Benchmark Validation (2026-03-22)

## Purpose

This note closes the remaining validation work for Phase 24 by checking the new
docs system against the real maintenance tasks named in `P24.4a`.

The question is not whether the docs are elegant in isolation. The question is
whether a maintainer can complete or confidently orient through these tasks
without relying on undocumented tribal memory.

## Benchmarks

### 1. Patchworks runtime setup

Task:
- bootstrap a host for Patchworks runtime work
- choose the correct host mode (Windows native vs Linux/Wine)
- verify prerequisites
- run preflight and launch Matrix Builder

Primary docs used:
- `docs/reference/contracts/recovery-and-external-runtime-boundaries.rst`
- `docs/reference/contracts/repo-runtime-invariants.rst`
- `docs/guides/geospatial-runtime-bootstrap.rst`
- `docs/guides/patchworks-wine-runtime.rst`
- `docs/guides/cross-platform-runtime-smoke.rst`
- `docs/reference/api/femic-patchworks-runtime.rst`

Verdict:
- sufficient

Why:
- the host split is explicit
- the preflight-before-launch sequence is explicit
- required runtime surfaces (`patchworks.jar`, Java/Wine, `SPSHOME`, license
  wiring, `xvfb`) are explicit
- runtime artifacts and failure seams are explicit

Residual friction:
- there is still more narrative depth for Linux/Wine than for native Windows
  Patchworks launch

### 2. K3Z variant rebuild / amend loop

Task:
- modify bundled K3Z instance content under `external/`
- validate the instance contract
- run deterministic rebuild/evidence flow
- decide which changes belong in the parent repo vs the submodule repo

Primary docs used:
- `docs/reference/contracts/instance-and-data-roots.rst`
- `docs/reference/contracts/repo-runtime-invariants.rst`
- `docs/guides/deployment-instances.rst`
- `docs/guides/rebuild-repro-contract.rst`
- `docs/guides/author-instance-rebuild-spec.rst`
- `docs/sample-models/k3z.rst`
- `docs/reference/api/femic-rebuild-runner.rst`

Verdict:
- sufficient

Why:
- the bundled-instance amend/rebuild loop is explicit
- the parent-repo vs submodule-repo split is explicit
- required validation and rebuild commands are explicit
- rebuild evidence expectations are explicit

Residual friction:
- none that block the task

### 3. SiteProd defaults and fallback behavior

Task:
- understand which SiteProd source FEMIC prefers by default
- understand when FEMIC uses canonical `siteprod.tif` +
  `siteprod.bandmap.json`
- understand when FEMIC falls back to ArcRasterRescue or Windows ArcGIS Pro

Primary docs used:
- `docs/reference/contracts/stage-boundaries-and-canonical-artifacts.rst`
- `docs/guides/stage-00-data-prep.rst`
- `docs/guides/geospatial-runtime-bootstrap.rst`
- `docs/reference/api/femic-pipeline-siteprod.rst`
- `docs/reference/api/femic-pipeline-io.rst`

Verdict:
- sufficient, but scattered

Why:
- the canonical artifact preference is explicit
- the ArcRasterRescue vs Windows ArcGIS Pro fallback split is explicit
- the code-level ownership and failure seams are explicit

Residual friction:
- a maintainer still has to read both a guide and the API page to get the full
  default-resolution story quickly

### 4. DataLad / public-data bootstrap

Task:
- initialize annex-backed public data in a fresh clone
- materialize payloads
- set `FEMIC_EXTERNAL_DATA_ROOT`
- confirm the data root is usable before preflight or runtime

Primary docs used:
- `docs/reference/contracts/repo-runtime-invariants.rst`
- `docs/reference/contracts/instance-and-data-roots.rst`
- `docs/guides/developer-environment-bootstrap.rst`
- `docs/guides/public-data-mirror-runbook.rst`
- `docs/guides/deployment-instances.rst`
- `docs/guides/geospatial-runtime-bootstrap.rst`

Verdict:
- sufficient

Why:
- fresh-clone Linux and Windows flows are explicit
- `git annex` / DataLad prerequisites are explicit
- `FEMIC_EXTERNAL_DATA_ROOT` export and its purpose are explicit
- smoke/acceptance checks are explicit

Residual friction:
- none that block the task

## Summary

Overall result:
- `P24.4a` passes

The current docs are now sufficient to complete or reliably orient through the
benchmark tasks named in the roadmap without depending on undocumented tribal
knowledge.

The remaining problems are quality-of-life issues, not blocking gaps:
- native Windows Patchworks runtime setup still relies on a few details spread
  across multiple pages
- SiteProd default/fallback behavior is documented clearly, but not yet in one
  short operator-facing summary

## Recommended follow-up

Track the remaining non-blocking documentation polish as a separate follow-up
issue rather than keeping Phase 24 open for indefinite refinement.
