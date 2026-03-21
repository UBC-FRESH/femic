Public Data Mirror Runbook
==========================

This runbook covers the FEMIC DataLad mirror workflow for datasets that are
public but not consistently directly downloadable.

Use this guide together with:

- ``metadata/required_datasets.yaml`` (authoritative inventory)
- ``metadata/datalad_mirror_seed.csv`` (current mirror candidate list)

Scope
-----

The mirror currently targets datasets where source access is unstable or
decommissioned (for example archived HectaresBC ``misc.thlb.tif``).

Maintainer Workflow (Create/Publish Mirror Repo)
------------------------------------------------

1. Create a public GitHub repo for mirrored assets (for example
   ``UBC-FRESH/femic-public-data``).
2. Initialize a DataLad dataset in a local checkout:

   .. code-block:: bash

      datalad create -c text2git femic-public-data
      cd femic-public-data

3. Copy/acquire datasets listed in ``metadata/datalad_mirror_seed.csv`` into
   matching relative paths under the dataset root.
4. Compute and record checksums for mirrored artifacts in
   ``metadata/required_datasets.yaml``.
5. Configure Arbutus S3 special remote and GitHub publication dependency.
   Prepare credentials/environment before remote setup:

   .. code-block:: bash

      cp config/credentials/arbutus_env.template.sh config/credentials/arbutus_env.sh
      # edit config/credentials/arbutus_env.sh with real values
      source config/credentials/arbutus_env.sh

   At minimum, the following variables must be set in-shell:

   .. code-block:: bash

      export AWS_ACCESS_KEY_ID=<key-id>
      export AWS_SECRET_ACCESS_KEY=<secret-key>
      export AWS_DEFAULT_REGION=ca-west-1

   Initialize the Arbutus S3 special remote (host must be endpoint hostname,
   not a ``ria+`` URL):

   .. code-block:: bash

      git annex initremote arbutus-s3 \
        type=S3 \
        encryption=none \
        bucket=<unique-bucket-name> \
        public=yes \
        publicurl=https://object-arbutus.cloud.computecanada.ca/<unique-bucket-name> \
        host=object-arbutus.cloud.computecanada.ca \
        protocol=https \
        requeststyle=path \
        autoenable=true

   Create/reconfigure GitHub sibling and wire publication dependency so one
   push publishes Git metadata and annexed content:

   .. code-block:: bash

      datalad create-sibling-github -d . \
        --github-organization UBC-FRESH \
        --name origin \
        --publish-depends arbutus-s3 \
        --existing reconfigure \
        femic-public-data

      datalad push --to origin

6. Verify fresh clone and selective retrieval works:

   .. code-block:: bash

      cd ..
      datalad clone git@github.com:UBC-FRESH/femic-public-data.git mirror-smoke
      cd mirror-smoke
      datalad get data/misc.thlb.tif

   If retrieval fails in a clone where the special remote is not auto-enabled:

   .. code-block:: bash

      git annex enableremote arbutus-s3
      datalad get data/misc.thlb.tif

Collaborator Workflow (Clone/Get/Update)
----------------------------------------

The mirror repo is linked into FEMIC at
``external/femic-public-data``. Collaborators should use:

.. code-block:: bash

   git submodule update --init --recursive

On Windows, prefer the `.venv`-scoped executable explicitly:

.. code-block:: powershell

   .venv\Scripts\datalad.exe get external/femic-public-data/data/misc.thlb.tif

On Linux/macOS:

.. code-block:: bash

   datalad get external/femic-public-data/data/misc.thlb.tif

To refresh metadata and retrieve updated artifacts:

.. code-block:: bash

   git submodule update --remote external/femic-public-data
   datalad update --merge external/femic-public-data
   datalad get -r external/femic-public-data/data

Windows Notes
-------------

The known-good Windows bootstrap pattern is:

- `git` on user `PATH`
- `git-annex` on user `PATH`
- DataLad installed inside `.venv`
- use `.venv\Scripts\datalad.exe` explicitly if `datalad` is not on `PATH`

Recommended smoke checks on Windows:

.. code-block:: powershell

   git --version
   git annex version
   .venv\Scripts\datalad.exe --version
   .venv\Scripts\datalad.exe get external/femic-public-data/data/misc.thlb.tif
   git -C external/femic-public-data annex version

If a repo looks dirty because a GIS library touched internal sidecar files,
recover it before continuing with FEMIC work:

.. code-block:: powershell

   .venv\Scripts\datalad.exe status external/femic-public-data

Then either rerun `datalad get` for missing payloads or restore the submodule to
its recorded clean state before proceeding.

Acceptance Checks
-----------------

- ``metadata/required_datasets.yaml`` and mirror repo paths agree.
- Every mirrored dataset has a populated ``checksum.value``.
- Fresh-clone smoke test can retrieve ``misc.thlb.tif`` via ``datalad get``.
- Windows collaborator smoke can run:
  - ``git annex version``
  - ``.venv\Scripts\datalad.exe get external/femic-public-data/data/misc.thlb.tif``
  - ``git -C external/femic-public-data annex version``

