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
- describe K3Z model-build stages as non-executing FreshForge node types;
- validate broad node parameters, inputs, outputs, and artifact declarations;
- build the canonical K3Z FreshForge workflow document/spec; and
- preserve the boundary that FreshForge planning does not execute FEMIC.

API
---

.. automodule:: femic.freshforge
   :members:
   :undoc-members:
   :show-inheritance:
