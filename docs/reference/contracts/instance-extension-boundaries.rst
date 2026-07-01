Instance Extension Boundaries
=============================

FEMIC core must be usable without any particular example model instance checked
out under ``external/``.

Ownership Contract
------------------

FEMIC core owns reusable modelling infrastructure:

- schemas, validators, loaders, and report primitives;
- generic pipeline stages and stage runners;
- generic Patchworks, BTC, VDYP, TSR, DataLad, and FreshForge integration
  surfaces;
- extension discovery and registry merge logic; and
- CLI plumbing that delegates to generic engines or explicitly discovered
  extensions.

Instance repositories own instance-specific modelling content:

- source-data bindings, accepted filenames, and reviewed overlays;
- model-specific run profiles, policy decisions, and workflow graphs;
- Patchworks variant/scenario registry entries;
- FreshForge providers or nodes whose semantics only make sense for one
  instance;
- TSR/THLB adjudication choices and locked-chain ledgers; and
- package entry points or registry files that advertise the instance to FEMIC
  or FreshForge.

The parent repository may link example instances as Git submodules for
developer convenience, but the installable FEMIC package must not assume those
submodules exist, keep their current names, or are materialized.

Allowed Coupling During Migration
----------------------------------

The current source tree still contains named-instance references that predate
this contract. They are migration debt, not precedent.

Until the decoupling phases are complete, new named-instance references under
``src/femic`` must be rejected unless they are deliberately added to the
temporary migration allowlist and tied to an active roadmap phase. Existing
allowlisted references should only decrease over time.

Target Extension Shape
----------------------

Instance-owned packages should expose metadata through explicit registries or
Python entry points. FEMIC core should merge those registrations with
user-supplied registry files and should report missing extensions as clear
configuration errors rather than import failures or broken default paths.

Curated examples such as K3Z, TSA29, MKRF, and TFL6 may remain in the source
checkout as submodules, but they are deployments of FEMIC, not dependencies of
FEMIC core.
