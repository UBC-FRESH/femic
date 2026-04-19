PyPI Release Runbook
====================

This runbook defines the phase-18 release path for FEMIC:

1. Package checks and deterministic wheel verification.
2. TestPyPI publication and install smoke.
3. Production PyPI publication using the exact same artifact set.
4. Release traceability updates in roadmap/changelog.

Pre-release prerequisites
-------------------------

- A clean git working tree.
- Passing quality gates:

  - ``ruff format src tests``
  - ``ruff check src tests``
  - ``mypy src``
  - ``pytest``
  - ``pre-commit run --all-files``
  - ``sphinx-build -b html docs _build/html -W``

- Packaging tools installed:

  .. code-block:: bash

     python -m pip install --upgrade build twine

Packaging and deterministic wheel checks
----------------------------------------

Run the project helper:

.. code-block:: bash

   scripts/release_package_checks.sh

The helper enforces:

- deterministic build epoch (``SOURCE_DATE_EPOCH``),
- ``python -m build``,
- ``twine check dist/*``,
- wheel install/init smoke,
- wheel reproducibility across consecutive builds.

Current known limitation
------------------------

The wheel is reproducible when ``SOURCE_DATE_EPOCH`` is fixed.
The ``sdist`` archive may still vary byte-wise across repeated local builds due
to upstream setuptools archive timestamp behavior.
Release flow therefore treats the wheel as the deterministic artifact and uses
the same built ``dist/*`` files for TestPyPI and PyPI publication.

TestPyPI publication and smoke
------------------------------

Preferred path: token-free trusted publishing (OIDC).

Before first TestPyPI publish:

1. Ensure GitHub environment ``testpypi`` exists in ``UBC-FRESH/femic``.
2. In TestPyPI, open account-level publishing settings:
   ``https://test.pypi.org/manage/account/publishing/``.
3. Add a pending publisher:
   - project name: ``femic``,
   - owner/repo: ``UBC-FRESH/femic``,
   - workflow: ``publish-testpypi.yml``,
   - environment: ``testpypi``.
4. Trigger GitHub workflow ``publish-testpypi`` on ``main``.

Notes:

- If there is no ``Add project`` button under ``/manage/projects``, this
  account-level pending-publisher flow is the correct entry point.
- First successful OIDC publish will create the TestPyPI project and attach the
  publisher.

Token fallback (not preferred)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If trusted publishing is temporarily unavailable, upload with token:

.. code-block:: bash

   export TWINE_USERNAME=__token__
   export TWINE_PASSWORD="$TEST_PYPI_API_TOKEN"
   python -m twine upload --repository-url https://test.pypi.org/legacy/ dist/*

Install smoke in a clean environment (after publish):

.. code-block:: bash

   python -m venv /tmp/femic-testpypi-smoke
   /tmp/femic-testpypi-smoke/bin/pip install --upgrade pip
   /tmp/femic-testpypi-smoke/bin/pip install \
     --index-url https://test.pypi.org/simple \
     --extra-index-url https://pypi.org/simple \
     femic==0.1.0
   /tmp/femic-testpypi-smoke/bin/femic --help

Production PyPI publication
---------------------------

Preferred path: token-free trusted publishing (OIDC).

Before first production publish:

1. PyPI project: ``femic``.
2. Publisher type: GitHub Actions.
3. Repository owner/name: ``UBC-FRESH/femic``.
4. Workflow filename: ``publish-pypi.yml``.
5. Environment name: ``pypi``.

Publish using workflow ``publish-pypi`` after TestPyPI validation passes.

Token fallback (not preferred):

.. code-block:: bash

   export TWINE_USERNAME=__token__
   export TWINE_PASSWORD="$PYPI_API_TOKEN"
   python -m twine upload dist/*

Post-release traceability checklist
-----------------------------------

After successful PyPI publication:

1. Create and push the matching git tag (for example ``v0.1.0``).
2. Record artifact hashes from ``sha256sum dist/*`` in ``CHANGE_LOG.md``.
3. Mark completed phase-18 checklist items in ``ROADMAP.md`` and update any
   linked planning note with validation outcomes.
4. Keep install instructions in ``README.md`` aligned with the published
   version.

Trusted publishing troubleshooting
----------------------------------

If GitHub Actions fails with ``invalid-publisher`` during publish:

- confirm the workflow filename and environment name exactly match the
  trusted-publisher entry on TestPyPI/PyPI,
- confirm repository owner/name is ``UBC-FRESH/femic``,
- confirm the publish job runs from ``refs/heads/main`` (or an allowed ref),
- re-run the workflow after saving trusted-publisher settings.
