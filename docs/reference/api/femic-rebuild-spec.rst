``femic.rebuild_spec`` Module
=============================

The :mod:`femic.rebuild_spec` module owns FEMIC's rebuild-spec loading and
schema-style validation contract. It turns ``config/rebuild.spec.yaml`` into a
validated mapping, enforces the allowed root/step/invariant structure, and is
the code-level gate that keeps instance rebuild flows deterministic and
auditable rather than loosely scripted.

If you are debugging why ``femic instance validate-spec`` rejects a rebuild
spec, which comparators or step kinds are allowed, or how FEMIC decides whether
an instance spec is structurally valid before a rebuild run starts, this is the
first module to read. In practice it owns:

- YAML rebuild-spec loading
- required root/step/invariant key validation
- allowed enum-style values for step kinds, severities, and comparators
- uniqueness and dependency-reference validation for step and invariant ids

Start Here If...
----------------

Use this page first if you are trying to:

- author or debug ``config/rebuild.spec.yaml``
- understand the minimum schema FEMIC expects for deterministic instance
  rebuilds
- inspect why a spec fails validation before any actual rebuild step runs

Typical maintenance path:

1. Start with :func:`load_rebuild_spec` for raw file-loading behavior.
2. Move to :func:`validate_rebuild_spec_payload` for schema and rule failures.
3. Inspect the module-level constants when extending the allowed schema.

Typical Usage
-------------

The usual maintenance flow is to validate the YAML payload before trying to run
any rebuild steps:

.. code-block:: python

   from pathlib import Path
   from femic.rebuild_spec import load_rebuild_spec, validate_rebuild_spec_payload

   payload = load_rebuild_spec(Path("config/rebuild.spec.yaml"))
   errors = validate_rebuild_spec_payload(payload)
   assert not errors, errors

How This Fits Into The Pipeline
-------------------------------

This module sits at the front of the rebuild workflow:

1. instance-maintenance docs and templates define a rebuild spec
2. CLI validation/rebuild commands load that spec through this module
3. downstream rebuild execution, invariant evaluation, and evidence reporting
   only proceed once the spec passes structure validation

That means this module owns the *spec structure contract*, not the actual step
execution or metric evaluation behavior.

Key Entry Surfaces
------------------

The highest-value entrypoints in this module are:

- :func:`load_rebuild_spec`
- :func:`validate_rebuild_spec_payload`

The main schema constants are also useful because they make the accepted
surface explicit:

- ``REBUILD_SPEC_REQUIRED_ROOT_KEYS``
- ``REBUILD_SPEC_REQUIRED_STEP_KEYS``
- ``REBUILD_SPEC_REQUIRED_INVARIANT_KEYS``
- ``ALLOWED_STEP_KINDS``
- ``ALLOWED_INVARIANT_SEVERITIES``
- ``ALLOWED_INVARIANT_COMPARATORS``

Core Contracts
--------------

The most important runtime contracts in this module are:

- rebuild specs must be YAML mappings with schema version ``1.0``
- required root sections are ``instance``, ``runtime``, ``steps``, and
  ``invariants``
- step IDs and invariant IDs must be unique
- step dependency references must resolve to declared step IDs
- runtime species-account policy fields must use the expected list structure

Failure Seams To Watch
----------------------

The common failure boundaries in this module are:

- malformed YAML root shape
  non-mapping root payloads fail immediately
- schema drift
  undocumented new keys or values in rebuild specs will fail until validation
  rules are updated here
- dependency/reference mistakes
  typos in ``depends_on`` or duplicate ids can look like runner bugs later if
  spec validation is skipped

Cross-References
----------------

Guides and references that pair especially closely with this module:

- :doc:`../../guides/author-instance-rebuild-spec`
- :doc:`../../guides/rebuild-repro-contract`
- :doc:`../../guides/deployment-instances`
- :doc:`../cli`

Related API pages:

- :doc:`femic-rebuild-runner`
- :doc:`femic-rebuild-invariants`

.. toctree::
   :hidden:

   generated/femic.rebuild_spec

.. automodule:: femic.rebuild_spec
   :members:
   :undoc-members:
   :show-inheritance:
   :noindex:
