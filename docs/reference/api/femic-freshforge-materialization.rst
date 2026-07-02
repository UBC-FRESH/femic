``femic.freshforge_materialization`` Module
===========================================

The :mod:`femic.freshforge_materialization` module owns FEMIC's optional
FreshForge provider for generic model-instance materialization workflows.

It is separate from :mod:`femic.freshforge`, which owns model-build stages.
The materialization provider is config-driven and must not hardcode named
example instances. Instance repositories supply overlay YAML files that
describe instance paths, install requirements, special remotes, materialization
paths, audit paths, and report paths.

API
---

.. automodule:: femic.freshforge_materialization
   :members:
   :undoc-members:
   :show-inheritance:
