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
- ``runtime/logs/`` for non-VDYP manifests/reports
- ``vdyp_io/logs/`` for VDYP-specific event/stdout logs
- ``vdyp_io/scratch/`` for disposable raw VDYP batch spill
- workspace ``.gitignore`` and ``QUICKSTART.md``

Visible User Workspace Root
---------------------------

For packaged installs, FEMIC now also carries a small user-config contract at:

- Linux/macOS: ``~/.femic/user.yaml``
- Windows: ``%USERPROFILE%\.femic\user.yaml``

That config records two path families:

- ``paths.managed_external_root``
  machine-managed built-in instance installs and support repositories
- ``paths.user_instance_root``
  the visible user workspace root for new working instances

Default packaged-install roots are:

- Linux/macOS:
  - managed built-ins: ``~/.femic/external``
  - visible user instances: ``~/femic/instances``
- Windows:
  - managed built-ins: ``%USERPROFILE%\.femic\external``
  - visible user instances: ``%USERPROFILE%\femic\instances``

Inspect or adjust those roots with:

.. code-block:: bash

   python -m femic instance config show
   python -m femic instance config set-managed-external-root "<path>"
   python -m femic instance config set-user-instance-root "<path>"

If you want FEMIC to create a new working instance under the configured
visible user root, use ``--instance-name`` instead of manually constructing
an absolute path:

.. code-block:: bash

   python -m femic instance init --instance-name my_new_case

That resolves to:

- Linux/macOS: ``~/femic/instances/my_new_case`` by default
- Windows: ``%USERPROFILE%\femic\instances\my_new_case`` by default

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

For fresh-clone developer setup (local `.venv`, editable install, and annex
materialization ritual), see
``docs/guides/developer-environment-bootstrap.rst``.

For practical VS Code plus local coding-agent onboarding in this repo, see
``docs/guides/vscode-coding-agent-onboarding.rst``.

If that onboarding is happening inside a Windows VS Code/Cursor Codex session
and assistant-rendered local file links are opening in the browser instead of
the editor, use the maintained recovery patch repo before pushing further into
instance setup:

- ``https://github.com/UBC-FRESH/codex-local-file-link-patch``

Registry-Backed Patchworks Variants
-----------------------------------

FEMIC now loads Patchworks variants from installed instance packages, explicit
in-process providers, and an optional user overlay at
``~/.femic/variants.yaml``. Core FEMIC no longer ships K3Z or MKRF Patchworks
variant definitions by default.

In a source checkout, install the example instance packages before using their
registry entries:

.. code-block:: bash

   python -m pip install -e external/femic-k3z-instance
   python -m pip install -e external/femic-mkrf-instance

Use the registry-backed surfaces when launching installed K3Z or MKRF
Patchworks variants:

.. code-block:: bash

   python -m femic patchworks instances list
   python -m femic patchworks variants list --instance-id k3z
   python -m femic patchworks run-variant k3z.base --run-id k3z_registry_smoke

For the fuller operator-facing workflow, including scenarios, scenario sets,
and materialization consent, see
``docs/guides/patchworks-variant-and-scenario-management.rst``.

If you request a variant whose owning instance package or user registry is not
installed/loaded, FEMIC reports the variant as unknown. Install the owning
instance package or provide an explicit registry overlay.

At minimum, materialize annex-backed payloads before case preflight:

.. code-block:: bash

   git submodule update --init --recursive
   git -C external/femic-public-data annex enableremote arbutus-s3
   datalad get -r external/femic-public-data/data
   export FEMIC_EXTERNAL_DATA_ROOT=$PWD/external/femic-public-data/data

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

Working With Bundled Example Instances Under ``external/``
----------------------------------------------------------

The directories under ``external/`` are not just sample folders. In this
checkout they are git submodules that mirror the standalone instance
repositories.

Treat them as follows:

- use ``external/femic-k3z-instance`` and ``external/femic-tsa29-instance`` as
  the canonical bundled runtime roots when you want to run the published
  teaching examples from this FEMIC checkout;
- make FEMIC code/docs/tooling changes in the parent repository;
- make case-specific instance content changes inside the submodule working tree;
- if an instance change should persist upstream, commit it in the submodule
  repository first, then update the parent FEMIC submodule pointer in a
  separate parent-repo commit.

At minimum, start from a bootstrapped parent checkout first:

Linux/macOS:

.. code-block:: bash

   git submodule update --init --recursive
   git -C external/femic-public-data annex enableremote arbutus-s3
   datalad get -r external/femic-public-data/data

Windows PowerShell:

.. code-block:: powershell

   git submodule update --init --recursive
   git -C external/femic-public-data annex enableremote arbutus-s3
   .venv\Scripts\datalad.exe get -r external/femic-public-data/data

Then export the public-data root before instance validation/runs:

Linux/macOS:

.. code-block:: bash

   export FEMIC_EXTERNAL_DATA_ROOT=$PWD/external/femic-public-data/data

Windows PowerShell:

.. code-block:: powershell

   $env:FEMIC_EXTERNAL_DATA_ROOT="$PWD\external\femic-public-data\data"

Bundled Example Instance Amend/Rebuild Loop
-------------------------------------------

Use this loop whenever you want to extend or amend one of the bundled example
instances under ``external/``.

1. Pick the instance root you are changing.

   K3Z:
   ``external/femic-k3z-instance``

   TSA29:
   ``external/femic-tsa29-instance``

2. Make your instance edits in the submodule tree.

   Common edit surfaces include:

   - ``config/run_profile.*.yaml``
   - ``config/tipsy/*.yaml``
   - ``config/rebuild.spec.yaml``
   - ``config/rebuild.allowlist.yaml``
   - tracked model/runbook/docs content inside the instance repo

3. Validate the instance contract before a long rebuild.

   Linux/macOS:

   .. code-block:: bash

      femic prep validate-case --instance-root external/femic-k3z-instance --run-config config/run_profile.k3z.yaml
      femic prep geospatial-preflight
      femic instance validate-spec --instance-root external/femic-k3z-instance --spec config/rebuild.spec.yaml

   Windows PowerShell:

   .. code-block:: powershell

      femic prep validate-case --instance-root external/femic-k3z-instance --run-config config/run_profile.k3z.yaml
      femic prep geospatial-preflight
      femic instance validate-spec --instance-root external/femic-k3z-instance --spec config/rebuild.spec.yaml

4. Run the deterministic rebuild/evidence path.

   Linux/macOS:

   .. code-block:: bash

      femic instance rebuild --instance-root external/femic-k3z-instance --spec config/rebuild.spec.yaml --baseline config/rebuild.baseline.json --allowlist config/rebuild.allowlist.yaml --run-config config/run_profile.k3z.yaml --run-id <run-id>

   Windows PowerShell:

   .. code-block:: powershell

      femic instance rebuild --instance-root external/femic-k3z-instance --spec config/rebuild.spec.yaml --baseline config/rebuild.baseline.json --allowlist config/rebuild.allowlist.yaml --run-config config/run_profile.k3z.yaml --run-id <run-id>

   Review:

   - ``external/femic-k3z-instance/runtime/logs/instance_rebuild_report-<run-id>.json``
   - any manifests/logs referenced by that report

5. Refresh tracked evidence when the rebuild result is the new accepted
   baseline.

   .. code-block:: bash

      femic instance refresh-reference-evidence --reference-root external/femic-k3z-instance

6. Commit in the correct repository.

   - If the change is only for local experimentation, keep it as an uncommitted
     submodule working-tree change.
   - If the change belongs to the example instance itself, commit inside
     ``external/femic-k3z-instance`` or ``external/femic-tsa29-instance``.
   - If FEMIC should now point at a new instance commit, return to the parent
     FEMIC repo and commit the updated submodule pointer separately.
   - For release-oriented instance updates, also follow the instance-local
     runbook in ``external/femic-k3z-instance/runbooks/REBUILD_RUNBOOK.md`` or
     ``external/femic-tsa29-instance/runbooks/REBUILD_RUNBOOK.md``.

Parent Repo vs Submodule Repo
-----------------------------

A simple rule helps avoid messy history:

- edit the parent FEMIC repo when you are changing shared Python code, shared
  docs, CLI behavior, tests, or developer bootstrap workflow;
- edit the submodule repo when you are changing example-instance configs,
  tracked outputs, runbooks, example-model docs, or other case payloads under
  ``external/femic-k3z-instance`` / ``external/femic-tsa29-instance``.

If you are changing both, make two commits:

- one commit in the submodule repository;
- one commit in FEMIC updating code/docs and the submodule pointer.

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
