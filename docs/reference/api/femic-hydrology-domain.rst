``femic.hydrology.domain`` Module
==================================

The :mod:`femic.hydrology.domain` module owns FEMIC's public hydrologic domain
and receptor contract. It defines layers, watersheds, downstream receptors,
hydrometric gauges, the public source registry, structural validation, and a
local file audit. It does not download layers or run a hydrology model.

Use this page when you are defining or auditing the spatial domain for forest
hydrology and flood-risk work.

Start Here If...
----------------

Use this page first if you are trying to:

- define a public watershed, stream, road, and DEM domain;
- link downstream receptors and hydrometric gauges to watersheds;
- register layer provenance, licences, checksums, and source IDs; or
- audit whether a domain's local layer files exist and match their checksums.

Typical Usage
-------------

.. code-block:: python

   from pathlib import Path
   from femic.hydrology.domain import (
       audit_hydrology_domain,
       build_hydrology_domain,
       write_hydrology_domain_manifest,
   )

   domain = build_hydrology_domain(...)
   write_hydrology_domain_manifest(
       domain,
       Path("metadata/hydrology/domain.json"),
   )
   audit = audit_hydrology_domain(
       Path("metadata/hydrology/domain.json"),
       data_root=Path("."),
   )

Key Entry Surfaces
------------------

- :func:`hydrology_source_registry`
  Return the default public source families.
- :func:`find_hydrology_source`
  Resolve one source ID.
- :func:`build_hydrology_domain`
  Build and validate a domain manifest.
- :func:`validate_hydrology_domain`
  Check roles, IDs, cross-references, CRS, licences, and checksums.
- :func:`write_hydrology_domain_manifest`
  Persist the manifest as JSON.
- :func:`load_hydrology_domain_manifest`
  Load a manifest.
- :func:`audit_hydrology_domain`
  Validate and audit local layer files.
- :class:`HydrologyDomainManifest`
  Versioned domain contract with layers, watersheds, receptors, gauges, and
  provenance.

Cross-References
----------------

- :doc:`../../guides/hydrology-domain-contract`
- :doc:`../contracts/hydrology-domain`
- :doc:`femic-pipeline-io`
- :doc:`../cli`

.. toctree::
   :hidden:

   generated/femic.hydrology.domain

.. automodule:: femic.hydrology.domain
   :members:
   :undoc-members:
   :show-inheritance:
