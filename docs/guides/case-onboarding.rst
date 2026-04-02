Case Onboarding Template
========================

This guide defines the minimum assets needed to onboard a new forest
management unit (FMU) or custom-boundary case into FEMIC.

Template Files
--------------

- Run profile template:
  ``config/run_profile.case_template.yaml``
- Rebuild spec template:
  ``config/rebuild.spec.yaml``
- Rebuild allowlist template:
  ``config/rebuild.allowlist.yaml``
- Rebuild runbook placeholder:
  ``runbooks/REBUILD_RUNBOOK.md``
- TIPSY parameter starter template:
  ``config/tipsy/template.case.yaml``

Onboarding Workflow
-------------------

1. Initialize an instance workspace (if not already done):

   .. code-block:: bash

      femic instance init

   Maintainer in-repo reference workspace:

   .. code-block:: bash

      cd instances/reference

2. Copy run-profile template:

   .. code-block:: bash

      cp config/run_profile.case_template.yaml config/run_profile.<case>.yaml

3. Set case identity:

   - For FMU/code mode: set ``selection.tsa``.
   - For custom boundary mode: set ``selection.boundary_path``,
     ``selection.boundary_layer``, and ``selection.boundary_code``.

4. Copy TIPSY template:

   .. code-block:: bash

      cp config/tipsy/template.case.yaml config/tipsy/tsa<code>.yaml

   The current compatibility filename contract still uses the legacy
   ``tsa<code>.yaml`` / ``tsak3z.yaml`` pattern even when the case is a
   non-TSA FMU.

5. Validate and customize rebuild control files:

   - update ``config/rebuild.spec.yaml`` with case-specific step/invariant thresholds,
   - update ``config/rebuild.allowlist.yaml`` for intentional baseline drift,
   - record operator notes in ``runbooks/REBUILD_RUNBOOK.md``.

6. Fill TIPSY rule metadata and rule assignments using local TSR/FSP evidence.

7. Validate config before running:

   .. code-block:: bash

      femic tipsy validate --config-dir config/tipsy --tsa <code>

8. Run single-command case preflight:

   .. code-block:: bash

      femic prep validate-case --run-config config/run_profile.<case>.yaml

9. Dry-run and compile:

   .. code-block:: bash

      femic run --run-config config/run_profile.<case>.yaml --dry-run
      femic run --run-config config/run_profile.<case>.yaml

   Source-checkout equivalent:

   .. code-block:: bash

      PYTHONPATH=src python -m femic prep validate-case --run-config config/run_profile.<case>.yaml

Required Input Checklist
------------------------

- Boundary and inventory:

  - Case boundary geometry path exists and is readable.
  - VRI input source path exists and has required fields.

- FEMIC runtime:

  - ``femic --help`` succeeds.
  - ``wine`` and VDYP assets are available for non-resume upstream runs.

- TIPSY handoff:

  - Case TIPSY YAML exists and validates.
  - BatchTIPSY fixed-width column mapping is known and stable.

- Post-run QA:

  - Strata diagnostics generated.
  - VDYP fit diagnostics generated.
  - Managed vs untreated overlay diagnostics generated after post-TIPSY stage.

Acceptance Criteria for Onboarded Case
--------------------------------------

- Upstream run finishes with manifest and run-scoped logs.
- BatchTIPSY handoff files are generated and parseable.
- Post-TIPSY bundle compiles without missing AU/curve mapping failures.
- Export commands complete for target downstream platform(s).

K3Z Example Instance Baseline
-----------------------------

Use the canonical K3Z example instance repository when you need a known-good
full payload baseline:

- ``https://github.com/UBC-FRESH/femic-k3z-instance``
- linked in FEMIC at ``external/femic-k3z-instance``

From a FEMIC checkout:

.. code-block:: bash

   git submodule update --init --recursive

To pull latest K3Z baseline updates:

.. code-block:: bash

   git submodule update --remote external/femic-k3z-instance

TSA29 Example Instance Baseline
-------------------------------

Use the canonical TSA29 example instance repository when you need a current,
student-usable baseline with rebuild/evidence wiring:

- ``https://github.com/UBC-FRESH/femic-tsa29-instance``
- linked in FEMIC at ``external/femic-tsa29-instance``

From a FEMIC checkout:

.. code-block:: bash

   git submodule update --init --recursive

To pull latest TSA29 baseline updates:

.. code-block:: bash

   git submodule update --remote external/femic-tsa29-instance

Working With a Local Coding Agent
---------------------------------

If the onboarding workflow will be driven from VS Code with a local coding
agent in the same checkout, read this guide before assigning larger rebuild or
instance-maintenance tasks:

- ``docs/guides/vscode-coding-agent-onboarding.rst``

That guide explains the expected planning, supervision, and validation loop for
agent-assisted FEMIC work.
