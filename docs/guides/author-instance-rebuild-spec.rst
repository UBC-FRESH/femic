How to Author a New Instance Rebuild Spec
=========================================

Purpose
-------

This guide explains how to create ``config/rebuild.spec.yaml`` for a new FEMIC
instance so rebuild execution is deterministic, auditable, and regression-safe.

Start from Template
-------------------

Start with the scaffolded template:

- ``config/rebuild.spec.yaml`` from ``femic instance init``
- schema reference:
  ``planning/femic_instance_rebuild_spec_schema.v1.yaml``

Validate structure before running rebuild:

.. code-block:: bash

   python -m femic instance validate-spec \
     --instance-root . \
     --spec config/rebuild.spec.yaml

Core Sections
-------------

Every spec must define:

- ``schema_version``
- ``instance``
- ``runtime``
- ``steps``
- ``invariants``

Minimal Copy-Ready Example
--------------------------

.. code-block:: yaml

   schema_version: "1.0"

   instance:
     case_id: "mycase"
     instance_root: "."

   runtime:
     run_config: "config/run_profile.mycase.yaml"
     tipsy_config_dir: "config/tipsy"
     patchworks_config: "config/patchworks.runtime.windows.yaml"
     log_dir: "runtime/logs"
     baseline_unexpected_diff_threshold: 0
     species_account_policy:
       required_present:
          - "product.Yield.managed.PLC"
       expected_absent:
          - "product.Yield.managed.PL"
       required_nonzero:
          - "product.Yield.managed.PLC"
          - "product.HarvestedVolume.managed.PLC.CC"
       expected_zero:
          - "product.Yield.managed.PL"

   steps:
     - step_id: "validate_case"
       kind: "femic_command"
       command: "femic prep validate-case --run-config ${runtime.run_config}"
       required: true
       depends_on: []
       mutable_artifacts: []
       expected_outputs:
         - "case preflight success signal"

     - step_id: "compile_upstream"
       kind: "femic_command"
       command: "femic run --run-config ${runtime.run_config}"
       required: true
       depends_on:
         - "validate_case"
       mutable_artifacts:
         - "data/*"
         - "runtime/logs/*"
       expected_outputs:
         - "run_manifest-<run_id>.json"

   invariants:
     - invariant_id: "managed_area_sanity"
       severity: "fatal"
       metric: "managed_area_ha"
       comparator: "gt"
       target: 0
       remediation: "Verify IFM assignment and matrix-builder inputs."

Step Authoring Rules
--------------------

- Keep ``step_id`` values lowercase snake-case and unique.
- Use ``depends_on`` to encode authoritative order explicitly.
- Mark mandatory steps ``required: true`` unless there is a real optional path.
- Keep ``mutable_artifacts`` specific enough for review (avoid broad ``*``).
- Declare operator-visible outputs in ``expected_outputs``.

Invariant Authoring Rules
-------------------------

- Use ``severity: fatal`` for true stop conditions.
- Use ``severity: warn`` for non-blocking diagnostics.
- Prefer metrics already emitted by rebuild:
  ``managed_area_ha``, ``block_join_mismatch_count``,
  ``seral_account_count``, ``accounts.list``, ``products.nonzero_labels``,
  ``baseline_match``,
  ``baseline_unexpected_diff_count``.
- Supported comparators:
  ``eq``, ``ne``, ``gt``, ``gte``, ``lt``, ``lte``, ``exists``,
  ``not_exists``, ``contains``, ``not_contains``.
- For species-account completeness policies, prefer
  ``runtime.species_account_policy`` so required/expected-empty account IDs and
  required-nonzero/expected-zero product labels are generated as fatal
  invariants automatically.
- Always include remediation text that tells the operator what to do next.

K3Z Reference Pattern
---------------------

K3Z is the canonical reference spec:

- ``external/femic-k3z-instance/config/rebuild.spec.yaml``

Use it when your instance includes Patchworks steps (preflight, build-blocks,
matrix-build) and stricter post-rebuild invariants.

Dry-Run and Execute
-------------------

Preview plan first:

.. code-block:: bash

   python -m femic instance rebuild \
     --instance-root . \
     --spec config/rebuild.spec.yaml \
     --dry-run

Run full rebuild:

.. code-block:: bash

   python -m femic instance rebuild \
     --instance-root . \
     --spec config/rebuild.spec.yaml \
     --baseline config/rebuild.baseline.json \
     --allowlist config/rebuild.allowlist.yaml \
     --with-patchworks
