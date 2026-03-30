``femic.patchworks_variants`` Module
====================================

The :mod:`femic.patchworks_variants` module owns FEMIC's registry-backed
Patchworks variant resolution seam.

Current responsibilities include:

- loading the packaged built-in Patchworks variant registry;
- merging an optional user overlay registry from ``~/.femic/variants.yaml``;
- writing user overlay entries for register/update/remove flows;
- resolving named scenarios attached to variants;
- resolving one default scenario per variant when the registry provides one or
  when a variant carries exactly one scenario;
- resolving named scenario sets that bundle registered scenarios across one or
  more variants;
- resolving one default scenario set per instance when the registry provides
  one;
- preserving richer scenario-set metadata such as instance membership,
  families, default markers, and notes;
- resolving named variants to concrete instance roots, runtime configs, and
  analysis ``.pin`` paths; and
- planning/executing registry-declared materialization before launch; and
- preserving richer metadata for future runtime/scenario/materialization
  orchestration.

Primary entry points
--------------------

- :func:`load_patchworks_variant_registry`
- :func:`load_patchworks_user_registry_overlay`
- :func:`build_patchworks_variant_materialization_plan`
- :func:`materialize_patchworks_variant`
- :func:`upsert_patchworks_user_variant_entry`
- :func:`remove_patchworks_user_variant_entry`
- :class:`PatchworksVariantRegistry`
- :class:`PatchworksVariantDefinition`
- :class:`PatchworksVariantScenarioDefinition`
- :class:`PatchworksScenarioSetDefinition`

.. automodule:: femic.patchworks_variants
   :members:
   :undoc-members:
   :show-inheritance:
