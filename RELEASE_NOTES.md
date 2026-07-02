# FEMIC 0.2.0a1

FEMIC 0.2.0a1 is an alpha release for the core decoupling milestone completed
across P80-P94. It marks the shift from a parent package that knew about named
example model instances to a core package that provides reusable engines,
schemas, runners, validators, CLI plumbing, and extension mechanisms.

## Highlights

- Added FreshForge provider integration for FEMIC model-building workflows.
- Added executable FreshForge orchestration support for explicit workflow runs,
  while keeping validation, inspection, and planning as non-mutating surfaces.
- Moved MKRF-specific FreshForge, workflow, and legacy XML builder code into
  the MKRF instance package.
- Added instance-owned extension paths for K3Z FMG/pipeline policies, TSA29
  named-pipeline contracts, TSA29 TSR adjudication overlays, Patchworks
  variant registries, and instance catalog metadata.
- Removed named example-instance coupling from `src/femic`; example model
  instances under `external/` are optional deployments, not FEMIC core package
  dependencies.
- Tightened regression coverage so new named `mkrf`, `k3z`, `tsa29`, `tfl6`,
  or `femic-*-instance` references under `src/femic` fail unless a future
  roadmap phase explicitly reopens the allowlist.

## Alpha Scope

This release is intended for FRESH development and early integration testing.
The extension APIs are usable, but still provisional while the example instance
packages continue to settle around the new boundaries.

FreshForge remains optional. Because FreshForge and figrecover do not yet have
PyPI releases, FEMIC's PyPI metadata does not include direct Git URL
dependencies for them. Install those optional tools explicitly from their
source repositories when needed. Example-instance providers, catalogs,
registries, and overlays are discovered only when the relevant instance package
is installed or an explicit user registry/config file is supplied.

## Known Caveats

- Full local `mypy src` still has pre-existing typing debt outside P95 in
  pandas/SciPy-heavy pipeline modules.
- Full local `pytest` still has environment-sensitive baseline failures outside
  P95, including checks that require local email configuration, external
  runtime availability, or materialized example-instance payloads.
- This release does not make example instances part of the FEMIC wheel. That is
  intentional: K3Z, TSA29, MKRF, TFL6, and future examples are optional
  deployments that can be installed, removed, or renamed independently of FEMIC
  core.

## Release Artifacts

- Version: `0.2.0a1`
- Tag: `v0.2.0a1`
- GitHub release title: `FEMIC 0.2.0a1`
- Publication target: TestPyPI validation first, then GitHub pre-release and
  PyPI publication.
