``femic.freshforge`` Module
===========================

The :mod:`femic.freshforge` module owns FEMIC's optional FreshForge provider
integration.

It intentionally keeps FreshForge optional. Normal FEMIC imports do not import
FreshForge eagerly, and users install FreshForge alongside FEMIC when they need
workflow orchestration.

Responsibilities
----------------

- expose provider ID ``femic`` through ``freshforge.providers`` entry-point
  discovery;
- describe reusable FEMIC model-build stages as FreshForge node types;
- validate broad node parameters, inputs, outputs, and artifact declarations;
- execute existing FEMIC CLI commands only when ``freshforge run`` is called;
- leave instance-specific workflow composition and provider namespaces to
  instance repositories; and
- preserve the boundary that FreshForge validation, inspection, and planning do
  not execute FEMIC.

API
---

.. automodule:: femic.freshforge
   :members:
   :undoc-members:
   :show-inheritance:
