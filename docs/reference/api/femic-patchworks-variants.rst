``femic.patchworks_variants`` Module
====================================

The :mod:`femic.patchworks_variants` module owns FEMIC's registry-backed
Patchworks variant resolution seam.

Current responsibilities include:

- loading the packaged built-in Patchworks variant registry;
- merging an optional user overlay registry from ``~/.femic/variants.yaml``;
- resolving named variants to concrete instance roots, runtime configs, and
  analysis ``.pin`` paths; and
- preserving richer metadata for future runtime/scenario/materialization
  orchestration.

Primary entry points
--------------------

- :func:`load_patchworks_variant_registry`
- :class:`PatchworksVariantRegistry`
- :class:`PatchworksVariantDefinition`

.. automodule:: femic.patchworks_variants
   :members:
   :undoc-members:
   :show-inheritance:
