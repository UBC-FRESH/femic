Hydrology Data Bundle Contract
==============================

Purpose
-------

This page is the short source-of-truth contract for FEMIC P114.2 hydrology data
bundles. It defines the layout, manifest, licence/checksum rules, gap policy,
audit semantics, and DataLad boundary.

A bundle packages reviewed public or approved inputs. It does not download
layers or run a hydrology model.

Quick Contract
--------------

- Schema: ``femic.hydrology.bundle.v1``.
- Manifest: ``bundle.json``.
- Layer root: ``layers/<layer_id>/<filename>``.
- Required roles: ``watershed``, ``stream``, ``road``, ``dem``.
- Every layer records licence, format, CRS, source ID, relative path, status,
  size, and optional SHA-256.
- A build requires a local source for every domain layer.
- A plan may contain gaps; a build may not.
- No private, Indigenous, or licence-restricted data in tracked files.
- Large layers belong in DataLad/Arbutus, not git.

Bundle Layout
-------------

.. code-block:: text

   <bundle>/
     bundle.json
     layers/<layer_id>/<filename>

The manifest never stores the absolute bundle root, so it remains portable.
Relative layer paths are resolved against the bundle directory during audit.

Manifest Schema
---------------

Top-level fields:

- ``schema_version`` and ``bundle_id``.
- ``bundle_version`` and ``generated_utc``.
- ``domain_id`` and ``domain_sha256``.
- ``aoi_bbox_epsg3005``.
- ``summary`` with layer, materialized, gap, and completeness counts.
- ``layers``, ``gaps``, ``caveats``, and ``provenance``.

Each layer record carries:

- ``layer_id``, ``role``, ``source_id``, and ``relative_path``.
- ``format``, ``crs``, and ``licence_id``.
- ``status``: ``planned``, ``materialized``, or ``missing``.
- ``checksum_sha256``, ``size_bytes``, ``source_url``, and ``retrieval_utc``.

The bundle ID is deterministic from the domain digest, AOI, bundle version,
and layer metadata/checksums. It does not include the absolute output path.

Versioning And Pinning
----------------------

Pin the bundle ID and bundle version, then verify every layer's SHA-256 before
use. A changed domain, AOI, layer byte, licence, or bundle version produces a
different bundle ID.

Audit Rules
-----------

``audit_hydrology_bundle`` checks:

- manifest schema and required roles;
- bundle and domain identifiers;
- AOI bounds;
- licence presence;
- layer existence, size, and SHA-256;
- path containment inside the bundle;
- gaps and completeness.

A bundle is valid when its manifest and materialized files are internally
consistent. It is complete only when every layer is materialized, every
checksum matches, and no gaps remain.

Gap Policy
----------

A plan may be valid but incomplete. Gaps explain why a layer is not available.
A build refuses to proceed while any gap remains. This prevents a partial data
audit from being mistaken for a finished bundle.

DataLad Boundary
----------------

Commit ``bundle.json``, the domain manifest, and small metadata. Annex large
layers to the instance's Arbutus remote. Audit only after the annex pointers
are materialized; a pointer stub is not a layer payload.

Pilot Boundary
--------------

A pilot starts as a plan with no sources; the gap list is the public-data
audit. Record watershed/stream/road/DEM coverage, gauge period of record,
receptor evidence, and licence status before committing a pilot selection.

Cross-References
----------------

- :doc:`../../guides/hydrology-data-bundle`
- :doc:`hydrology-domain`
- :doc:`../api/femic-hydrology-bundle`
- :doc:`instance-and-data-roots`
