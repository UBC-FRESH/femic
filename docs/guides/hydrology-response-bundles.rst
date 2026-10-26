Hydrology Response Bundles
==========================

Purpose
-------

P114.8 packages the outputs of the hydrology ladder into one pinned consumer
artifact. WS4 and FHOPS should read this bundle instead of re-running FEMIC
domain discovery, frequency fitting, or surrogate training.

A response bundle contains:

- a return-period response surface;
- a receptor-level flood-risk table;
- optional surrogate model, validation, frequency, screening, pilot, and
  model-card artifacts;
- the hydrology domain and disturbance-ledger provenance digests; and
- a manifest with deterministic identity, checksums, applicability domain,
  uncertainty, caveats, and a consumer contract.

The response manifest uses ``femic.hydrology.response.v1``. The flood-risk table
uses ``femic.hydrology.flood_risk.v1``. The build plan uses
``femic.hydrology.response_plan.v1``.

This is a planning and screening surface, not a regulatory flood map or a
design-flood service.

Bundle Layout
-------------

.. code-block:: text

   hydrology-response-<bundle-id>-<version>/
     manifest.json
     artifacts/
       response_surface/response_surface.json
       flood_risk/flood_risk.json
       surrogate_model/surrogate_model.json
       surrogate_validation/surrogate_validation.json
       frequency_fit/frequency_fit.json
       frequency_pairing/frequency_pairing.json
       tier0_screening/screening.json
       domain/domain.json
       disturbance_ledger/disturbance.json
       benchmark_check/benchmark.json
       validation_report/validation_report.json
       model_card/model_card.json
       pilot_run/pilot_run.json
     provenance/
       response_plan.json

Artifact paths are relative to the bundle root. The manifest records the media
type, schema, size, and SHA-256 of every file.

Build A Bundle
--------------

Write a plan that names local JSON artifacts:

.. code-block:: json

   {
     "schema_version": "femic.hydrology.response_plan.v1",
     "bundle_version": "2026.10.0",
     "domain_id": "fixture-domain",
     "ledger_id": "fixture-ledger",
     "response_surface_id": "fixture-surface",
     "artifacts": [
       {
         "role": "response_surface",
         "path": "response_surface.json",
         "schema_version": "femic.hydrology.flood_response.v1"
       },
       {
         "role": "flood_risk",
         "path": "flood_risk.json",
         "schema_version": "femic.hydrology.flood_risk.v1"
       },
       {
         "role": "domain",
         "path": "domain.json",
         "schema_version": "femic.hydrology.domain.v1"
       },
       {
         "role": "disturbance_ledger",
         "path": "disturbance.json",
         "schema_version": "femic.hydrology.disturbance.v1"
       }
     ],
     "applicability_domain": {
       "feature_names": ["harvest_fraction"],
       "min_values": {"harvest_fraction": 0.0},
       "max_values": {"harvest_fraction": 0.6},
       "mean_values": {"harvest_fraction": 0.3},
       "scale_values": {"harvest_fraction": 0.2},
       "max_distance": 3.0
     },
     "uncertainty": {"interval": "95%", "basis": "surrogate held-out"},
     "caveats": ["Screening only; hydrologist review required."]
   }

Build and inspect from Python:

.. code-block:: python

   from pathlib import Path
   from femic.hydrology.response_bundle import (
       audit_hydrology_response_bundle,
       build_hydrology_response_bundle,
   )

   result = build_hydrology_response_bundle(
       Path("plan.json"),
       Path("bundles/hydrology-response-2026.10.0"),
   )
   audit = audit_hydrology_response_bundle(result.bundle_dir)
   print(result.manifest.bundle_id, audit.is_valid)

Build and inspect from the CLI:

.. code-block:: shell

   python -m femic hydrology bundle \
     --plan plan.json \
     --output-dir bundles/hydrology-response-2026.10.0

   python -m femic hydrology inspect \
     bundles/hydrology-response-2026.10.0 --json

Use ``--overwrite`` only to replace an existing FEMIC response bundle. The
builder refuses to overwrite an arbitrary directory.

Flood-Risk Table
----------------

The flood-risk table records one row per receptor and return period:

.. code-block:: python

   from femic.hydrology.response_bundle import (
       FloodRiskRow,
       build_flood_risk_table,
       write_flood_risk_table,
   )

   table = build_flood_risk_table(
       (
           FloodRiskRow(
               receptor_id="receptor-1",
               watershed_id="watershed-1",
               return_period=100.0,
               baseline_peak_flow_m3s=120.0,
               scenario_peak_flow_m3s=150.0,
               ratio=1.25,
               expected_annual_damage=42000.0,
           ),
       ),
       source_surface_id="fixture-surface",
       baseline_name="baseline",
   )
   write_flood_risk_table(table, Path("flood_risk.json"))

Ratios must equal scenario flow divided by baseline flow. Return periods must
be greater than one year. Flows must be positive and finite.

Pinning And Consumer Read Order
-------------------------------

Consumers must:

1. Pin ``bundle_id`` and ``bundle_version`` from ``manifest.json``.
2. Verify every artifact SHA-256 before use.
3. Read the response surface and flood-risk table before optional artifacts.
4. Check the query against ``applicability_domain`` and refuse unsupported
   queries unless a reviewed extrapolation is approved.
5. Preserve the recorded CRS, units, return periods, and caveats.

Recommended read order:

.. code-block:: text

   manifest.json
   artifacts/response_surface/*.json
   artifacts/flood_risk/*.json
   artifacts/surrogate_model/*.json
   artifacts/domain/*.json
   artifacts/disturbance_ledger/*.json
   artifacts/validation_report/*.json
   artifacts/model_card/*.json

WS4 P49 consumes the response surface and flood-risk table as landscape-level
schedule constraints and screening objectives. FHOPS P14 consumes the same
bundle for operational road and harvest integration. Neither consumer should
re-run FEMIC discovery or hydrology to use a pinned bundle.

Determinism And Audit
---------------------

``bundle_id`` is derived from the canonical plan and artifact checksums. Given
the same plan and input bytes, the identity is stable. ``generated_utc`` can be
overridden for reproducible fixtures.

``audit_hydrology_response_bundle`` validates the manifest schema, required
roles, consumer contract, artifact paths, sizes, and checksums.

Limits
------

- A valid bundle is internally consistent, not hydrologically correct.
- The bundle does not establish public-gauge calibration.
- Applicability domains are model-specific and may be empty when no surrogate
  is packaged.
- Flood-risk rows are decision-support screening values, not regulatory
  floodplain mapping.
- Hydrologist review is required before operational use.

See Also
--------

- :doc:`hydrology-flood-frequency`
- :doc:`hydrology-surrogate-models`
- :doc:`hydrology-disturbance-ledger`
- :doc:`../reference/contracts/hydrology-response-bundles`
- :doc:`../reference/api/femic-hydrology-response-bundle`
