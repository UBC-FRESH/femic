``femic.freshforge`` Module
===========================

The :mod:`femic.freshforge` module owns FEMIC's optional FreshForge provider
integration.

It intentionally keeps FreshForge behind the optional ``femic[freshforge]``
dependency boundary. Normal FEMIC imports do not import FreshForge eagerly.

Responsibilities
----------------

- expose provider IDs ``femic`` and ``femic.mkrf`` through
  ``freshforge.providers`` entry-point discovery;
- describe reusable FEMIC model-build stages as FreshForge node types;
- validate broad node parameters, inputs, outputs, and artifact declarations;
- execute existing FEMIC CLI commands only when ``freshforge run`` is called;
- leave instance-specific workflow composition to instance repositories; and
- preserve the boundary that FreshForge validation, inspection, and planning do
  not execute FEMIC.

API
---

.. automodule:: femic.freshforge
   :members:
   :undoc-members:
   :show-inheritance:
