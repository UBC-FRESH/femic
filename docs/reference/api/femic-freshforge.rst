``femic.freshforge`` Module
===========================

The :mod:`femic.freshforge` module owns FEMIC's optional FreshForge provider
integration.

It intentionally keeps FreshForge behind the optional ``femic[freshforge]``
dependency boundary. Normal FEMIC imports do not import FreshForge eagerly.

Responsibilities
----------------

- expose provider id ``femic`` through ``freshforge.providers`` entry-point
  discovery;
- describe reusable FEMIC model-build stages as non-executing FreshForge node
  types;
- validate broad node parameters, inputs, outputs, and artifact declarations;
- leave instance-specific workflow composition to instance repositories; and
- preserve the boundary that FreshForge planning does not execute FEMIC.

API
---

.. automodule:: femic.freshforge
   :members:
   :undoc-members:
   :show-inheritance:
