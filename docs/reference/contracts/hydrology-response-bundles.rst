Hydrology Response Bundle Contract
==================================

Purpose
-------

This page is the source-of-truth contract for FEMIC P114.8 response and
flood-risk packaging. It defines bundle identity, layout, manifest fields,
checksums, applicability, pinning, and the WS4/FHOPS read handshake.

Quick Contract
--------------

- Response manifest schema: ``femic.hydrology.response.v1``.
- Flood-risk schema: ``femic.hydrology.flood_risk.v1``.
- Build-plan schema: ``femic.hydrology.response_plan.v1``.
- Manifest name: ``manifest.json``.
- Artifact root: ``artifacts/<role>/``.
- Provenance root: ``provenance/``.
- Required roles: ``response_surface``, ``flood_risk``, ``domain``,
  ``disturbance_ledger``.
- Optional roles: ``surrogate_model``, ``surrogate_validation``,
  ``frequency_fit``, ``frequency_pairing``, ``tier0_screening``,
  ``benchmark_check``.
- Every artifact records schema, media type, size, and SHA-256.
- Consumers pin ``bundle_id`` and ``bundle_version`` and verify checksums.
- Tracked fixtures must use public or synthetic data only. No private,
  Indigenous, or licence-restricted data belongs in a tracked bundle.
- This is not a regulatory flood map or a design-flood service.

Plan Contract
-------------

A plan is a JSON object with:

- ``schema_version`` equal to ``femic.hydrology.response_plan.v1``;
- non-empty ``bundle_version``, ``domain_id``, ``ledger_id``, and
  ``response_surface_id``;
- a non-empty ``artifacts`` list;
- optional ``applicability_domain`` and ``uncertainty`` objects;
- optional ``caveats`` and ``provenance`` objects.

Each artifact entry records ``role``, relative ``path``, optional
``schema_version``, and optional ``description``. Roles are unique within a
plan. Paths are resolved relative to the plan file.

Artifact schema expectations:

``response_surface``
   ``femic.hydrology.flood_response.v1``

``flood_risk``
   ``femic.hydrology.flood_risk.v1``

``surrogate_model``
   ``femic.hydrology.surrogate_model.v1``

``frequency_fit``
   ``femic.hydrology.flood_frequency.v1``

``tier0_screening``
   ``femic.hydrology.screening.v1``

``domain``
   ``femic.hydrology.domain.v1``

``disturbance_ledger``
   ``femic.hydrology.disturbance.v1``

``surrogate_validation``, ``frequency_pairing``, and ``benchmark_check`` are
opaque JSON artifacts at this layer and must record their own caveats.

Manifest Contract
-----------------

The manifest records:

- ``bundle_id`` and ``bundle_name``;
- ``bundle_version`` and ``generated_utc``;
- ``domain_id``, ``ledger_id``, and ``response_surface_id``;
- artifact records with relative path, role, schema, media type, size, and
  SHA-256;
- response-surface summary and flood-risk summary;
- ``applicability_domain`` and ``uncertainty``;
- ``consumer_contract``;
- caveats and provenance.

``bundle_id`` is ``hydro-response-`` followed by a deterministic digest of the
canonical plan and materialized artifact records. Identical inputs produce the
same ``bundle_id``; ``bundle_name`` appends the bundle version.

Artifact and Path Rules
-----------------------

- Artifact paths must remain inside the bundle.
- The manifest must not reference absolute paths.
- The builder copies bytes without rewriting artifact JSON.
- Domain and ledger artifact IDs must match the plan; the flood-risk table must
  name the planned response surface.
- Artifact checksums are lowercase SHA-256 over exact file bytes.
- The builder refuses to overwrite a non-bundle directory.
- ``--overwrite`` replaces only a directory containing a valid FEMIC response
  manifest.

Flood-Risk Table Contract
-------------------------

A flood-risk table records:

- ``table_id``, ``generated_utc``, ``source_surface_id``, and ``baseline_name``;
- one row per ``receptor_id`` and ``return_period``;
- ``watershed_id``;
- baseline and scenario peak flow in cubic metres per second;
- ``ratio`` equal to scenario/baseline flow;
- optional exceedance probability in ``[0, 1]``;
- optional expected annual damage, non-negative;
- caveats.

The table is a screening product. It does not define a regulatory flood
construction level, floodway, or design flood.

Applicability And Uncertainty
-----------------------------

The manifest records the applicability domain supplied by the plan or extracted
from a packaged surrogate model. Consumers must refuse queries outside that
domain unless a reviewed extrapolation is explicitly approved.

Uncertainty recorded in the plan is merged with available held-out surrogate
metrics (``rmse``, ``mae``, ``r2``, ``coverage_95``). It is descriptive
metadata, not a calibrated predictive distribution.

Consumer Handshake
------------------

WS4 P49 and FHOPS P14 must:

1. Resolve the pinned ``bundle_id`` and ``bundle_version``.
2. Read and validate ``manifest.json``.
3. Verify all artifact sizes and SHA-256 values.
4. Read the response surface, then the flood-risk table.
5. Read the applicability domain and refuse unsupported queries.
6. Preserve CRS, units, return periods, caveats, and producer provenance.
7. Avoid re-running FEMIC discovery, frequency fitting, or surrogate training.

Recommended read order:

.. code-block:: text

   manifest.json
   artifacts/response_surface/*.json
   artifacts/flood_risk/*.json
   artifacts/surrogate_model/*.json
   artifacts/domain/*.json
   artifacts/disturbance_ledger/*.json

Cross-References
----------------

- :doc:`../../guides/hydrology-response-bundles`
- :doc:`hydrology-flood-frequency`
- :doc:`hydrology-surrogate-models`
- :doc:`hydrology-domain`
- :doc:`hydrology-disturbance-ledger`
- :doc:`../api/femic-hydrology-response-bundle`
