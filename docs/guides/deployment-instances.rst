Deployment Instance Setup
=========================

FEMIC now supports deployment-instance-first execution. The Python package is
generic; case-specific configs, local data paths, and generated artifacts live
in your instance workspace.

Create an Instance
------------------

From an empty directory:

.. code-block:: bash

   python -m pip install femic
   femic instance init

By default this scaffolds:

- ``config/`` and ``config/tipsy/`` templates
- ``config/rebuild.spec.yaml`` default rebuild spec template
- ``runbooks/REBUILD_RUNBOOK.md`` rebuild runbook placeholder
- ``data/`` and ``data/downloads/``
- ``output/``
- ``vdyp_io/logs/``
- workspace ``.gitignore`` and ``QUICKSTART.md``

Canonical In-Repo Reference Instance (Maintainers)
--------------------------------------------------

FEMIC now carries a canonical maintainer reference instance at:

- ``instances/reference/``

This path is for maintainers and docs/tests reference only; deployment users
should still create their own instance roots outside the source tree.

To refresh this reference instance from current package templates:

.. code-block:: bash

   PYTHONPATH=src python -m femic instance init \
     --instance-root instances/reference \
     --no-download-bc-vri \
     --yes

BC VRI Auto-Download
--------------------

``femic instance init`` prompts (default ``Y``) to download standard BC-wide
VRI datasets into ``data/downloads/`` and extract them into
``data/bc/vri/2024/``:

- ``VEG_COMP_LYR_R1_POLY_2024.gdb.zip``
- ``VEG_COMP_VDYP7_INPUT_POLY_AND_LAYER_2024.gdb.zip``

You can skip this step:

.. code-block:: bash

   femic instance init --no-download-bc-vri

Or run non-interactive bootstrap:

.. code-block:: bash

   femic instance init --yes

Installed-Package Preflight Check
---------------------------------

After initializing an instance, run case preflight before long compile jobs:

.. code-block:: bash

   femic prep validate-case --run-config config/run_profile.case_template.yaml

Then verify geospatial dependencies (Fiona/GDAL):

.. code-block:: bash

   femic prep geospatial-preflight

Instance Root Resolution
------------------------

Operational commands accept ``--instance-root`` and otherwise resolve paths by:

1. ``--instance-root``
2. ``FEMIC_INSTANCE_ROOT`` environment variable
3. current working directory

This allows running FEMIC from any location while keeping all deployment files
scoped to one workspace root.

See also: ``docs/guides/data-access-inventory.rst`` and
``metadata/required_datasets.yaml`` for dataset provenance, access mode, and
checksum/mirroring status.

For DataLad mirror clone/get/update workflow, see
``docs/guides/public-data-mirror-runbook.rst``.
Mirror datasets are linked in-repo via submodule:
``external/femic-public-data``.

Windows users should also follow `docs/guides/geospatial-runtime-bootstrap.rst`
and use `.venv\Scripts\datalad.exe` explicitly if DataLad is not on `PATH`.

For the cross-platform smoke and acceptance contract, see
`docs/guides/cross-platform-runtime-smoke.rst`.

Canonical K3Z Example Instance Repository
-----------------------------------------

FEMIC publishes a standalone, full K3Z teaching instance at:

- ``https://github.com/UBC-FRESH/femic-k3z-instance``

The same repository is linked back into FEMIC via git submodule:

- ``external/femic-k3z-instance``

Clone FEMIC with submodules initialized:

.. code-block:: bash

   git clone https://github.com/UBC-FRESH/femic.git
   cd femic
   git submodule update --init --recursive

Refresh the K3Z example submodule to latest upstream commit:

.. code-block:: bash

   git submodule update --remote external/femic-k3z-instance

Canonical TSA29 Example Instance Repository
-------------------------------------------

FEMIC publishes a standalone TSA29 teaching/research instance at:

- ``https://github.com/UBC-FRESH/femic-tsa29-instance``

The same repository is linked back into FEMIC via git submodule:

- ``external/femic-tsa29-instance``

Refresh the TSA29 example submodule to latest upstream commit:

.. code-block:: bash

   git submodule update --remote external/femic-tsa29-instance

Contributor Baseline for New Instance Repositories
--------------------------------------------------

When standing up a new instance repository, treat these as mandatory:

- commit ``config/rebuild.spec.yaml`` and ``config/rebuild.allowlist.yaml``,
- validate spec structure with
  ``femic instance validate-spec --spec config/rebuild.spec.yaml``,
- run deterministic rebuild checks with
  ``femic instance rebuild --spec config/rebuild.spec.yaml``,
- retain generated rebuild report/manifests for review.

This policy is enforced by FEMIC roadmap/docs contracts for Phase 13.

Reference Instance Release Gate Evidence
----------------------------------------

FEMIC release checks now require a tracked reference-instance rebuild evidence
artifact with a passing regression gate:

- ``instances/reference/evidence/reference_rebuild_report.latest.json``

The release gate expects:

- ``status: "ok"``
- ``regression_gate.step_failure: false``
- ``regression_gate.fatal_invariant_failure: false``
- ``regression_gate.unexpected_diff_regression: false``

Maintainer evidence refresh command:

.. code-block:: bash

   python -m femic instance refresh-reference-evidence

Optional drift-warning thresholds (long-lived repos):

.. code-block:: bash

   python -m femic instance refresh-reference-evidence \
     --max-warn-increase 0 \
     --max-baseline-diff-increase 0

Contributor release-prep runbook step:

- add this command to your instance ``runbooks/REBUILD_RUNBOOK.md`` release
  checklist and confirm the refreshed evidence payload reports ``status: ok``
  before opening/reviewing a release PR.
