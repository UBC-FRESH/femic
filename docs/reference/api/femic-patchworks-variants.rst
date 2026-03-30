``femic.patchworks_variants`` Module
====================================

The :mod:`femic.patchworks_variants` module owns FEMIC's registry-backed
Patchworks variant resolution seam.

Current responsibilities include:

- loading the packaged built-in Patchworks variant registry;
- merging an optional user overlay registry from ``~/.femic/variants.yaml``;
- resolving built-in instance roots through repo-local ``external/...`` paths
  when present and otherwise through the packaged-install managed built-in
  root recorded in ``~/.femic/user.yaml``;
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
- planning/executing registry-declared materialization before launch;
- exposing read-only materialization-plan summaries for operator inspection;
- exposing dataset-root grouped materialization summaries for operator-facing
  inspection and consent; and
- preserving richer metadata for future runtime/scenario/materialization
  orchestration.

Operational shape
-----------------

In user-facing terms, this module is the registry seam behind:

- ``instances list``
- ``variants list/show/register/update/remove``
- ``variants materialization-plan``
- ``run-variant``
- ``scenarios list``
- ``run-scenario``
- ``run-default-scenario``
- ``scenario-sets list/show``
- ``run-scenario-set``
- ``run-default-scenario-set``

The current built-in proof surface is the shipped K3Z registry family. This
module therefore owns more than plain `.pin` lookup: it also owns default
scenario resolution, default scenario-set resolution, scenario-set metadata,
and grouped materialization summaries for launch-time consent.

It also now owns the user-facing built-in install hint seam. When a shipped
built-in variant is requested but its instance repository is missing from both
repo-local ``external/...`` and the configured managed built-in root, the
registry layer returns a direct hint to install that built-in rather than
letting later file-resolution failures leak out.

For the operator-facing workflow, examples, and K3Z built-in usage pattern,
see :doc:`../../guides/patchworks-variant-and-scenario-management`.

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
