Hydrology Domain Contract
=========================

Purpose
-------

This page is the short source-of-truth contract for the public hydrologic
domain used by FEMIC P114. It defines the domain manifest, layer roles,
watershed/receptor/gauge links, source registry, audit rules, and public-data
boundary.

The contract is metadata and provenance only. It does not download data or run
a hydrology model.

Quick Contract
--------------

- Schema: ``femic.hydrology.domain.v1``.
- Source registry: ``femic.hydrology.sources.v1``.
- Default CRS: ``EPSG:3005``.
- Required roles: ``watershed``, ``stream``, ``road``, ``dem``.
- Required records: at least one watershed and one receptor.
- Gauges: optional, but a missing gauge produces a calibration warning.
- Layer CRS must match the domain CRS exactly.
- Relative layer paths resolve against an explicit data root.
- No private, Indigenous, or licence-restricted data in tracked files.

Domain Manifest
---------------

A domain manifest records:

- ``domain_id``, ``name``, ``created_utc``, ``crs``, and ``resolution_m``;
- ``layers`` with role, path, format, CRS, geometry, source ID, required
  fields, licence, checksum, size, and optional resolution;
- ``watersheds`` with ID, name, area, layer, and optional feature ID;
- ``receptors`` with ID, name, type, watershed, layer, feature, capacity,
  damage-curve ID, and notes;
- ``gauges`` with ID, station name, watershed, optional layer, drainage area,
  period of record, and record URL;
- ``caveats`` and ``provenance``.

Allowed layer roles are ``watershed``, ``stream``, ``road``, ``dem``,
``land_cover``, ``soil``, ``climate``, ``gauge``, ``receptor``, and ``hru``.

Allowed receptor types are ``community``, ``infrastructure``,
``channel_capacity``, and ``ecological``.

Source Registry
---------------

The registry provides public source families with source ID, title, role,
catalogue URL, service URL, licence, native CRS, required fields, and notes.
A layer may omit ``source_id`` only when its provenance is documented
elsewhere.

Climate, soil, gauge, and receptor sources may need a reviewed local layer. A
source registry entry is a starting point, not a licence to assume a layer is
usable.

Audit Rules
-----------

The local audit:

- validates the manifest structure and cross-references;
- checks every layer file exists;
- compares declared and actual size;
- verifies optional SHA-256 checksums;
- resolves relative paths against the supplied data root or manifest
  directory;
- reports missing gauges as a warning.

The audit does not validate geospatial fields or geometry quality. P114.2 owns
field-level and bundle-level validation.

Cross-References
----------------

- :doc:`../../guides/hydrology-domain-contract`
- :doc:`../api/femic-hydrology-domain`
- :doc:`instance-and-data-roots`
