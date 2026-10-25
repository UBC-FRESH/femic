``femic.hydrology.bundle`` Module
==================================

The :mod:`femic.hydrology.bundle` module packages a reviewed hydrology domain
into a portable, versioned data bundle. It plans layers, reports gaps, copies
local sources, records licences and checksums, and audits bundle completeness.
It does not download public layers or run a hydrology model.

Use this page when you are assembling or auditing the public data bundle for
forest hydrology and flood-risk work.

Start Here If...
----------------

Use this page first if you are trying to:

- audit which domain layers are still missing before a build;
- package local BCDC/WFS/DataLad layers into a reproducible bundle;
- verify layer sizes and SHA-256 values;
- inspect bundle completeness and gaps; or
- hand a pinned hydrology data bundle to later P114 work.

Typical Usage
-------------

.. code-block:: python

   from pathlib import Path
   from femic.hydrology.bundle import (
       audit_hydrology_bundle,
       build_hydrology_bundle,
       plan_hydrology_bundle,
   )

   plan = plan_hydrology_bundle(
       domain,
       bundle_dir=Path("data/hydrology/bundle-v1"),
       aoi_bbox_epsg3005=(1148000, 391900, 1149900, 393500),
       sources={"watersheds": Path("data/raw/watersheds.gpkg")},
   )
   result = build_hydrology_bundle(
       Path("metadata/hydrology/domain.json"),
       Path("data/hydrology/bundle-v1"),
       aoi_bbox_epsg3005=(1148000, 391900, 1149900, 393500),
       sources=sources,
   )
   audit = audit_hydrology_bundle(result.bundle_dir)

Key Entry Surfaces
------------------

- :func:`plan_hydrology_bundle`
  Plan layer paths and report missing sources.
- :func:`build_hydrology_bundle`
  Atomically copy sources and write ``bundle.json``.
- :func:`audit_hydrology_bundle`
  Validate the manifest and audit materialized layer files.
- :func:`validate_hydrology_bundle_manifest`
  Check the structural bundle contract.
- :func:`load_hydrology_bundle_manifest`
  Load a bundle manifest.
- :func:`write_hydrology_bundle_manifest`
  Persist a bundle manifest.
- :class:`HydrologyBundleManifest`
  Versioned bundle contract with layers, gaps, checksums, and provenance.

Cross-References
----------------

- :doc:`../../guides/hydrology-data-bundle`
- :doc:`../contracts/hydrology-data-bundle`
- :doc:`femic-hydrology-domain`
- :doc:`../cli`

.. toctree::
   :hidden:

   generated/femic.hydrology.bundle

.. automodule:: femic.hydrology.bundle
   :members:
   :undoc-members:
   :show-inheritance:
