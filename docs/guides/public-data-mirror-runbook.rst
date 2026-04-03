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
   Prepare credentials/environment before remote setup.

   Linux/macOS pattern:

   .. code-block:: bash

      cp config/credentials/arbutus_env.template.sh config/credentials/arbutus_env.sh
      # edit config/credentials/arbutus_env.sh with real values
      source config/credentials/arbutus_env.sh

   Windows PowerShell pattern (recommended for local-user secrets):

   - create ``%USERPROFILE%\.config\femic\arbutus.env`` with plain
     ``KEY=VALUE`` lines;
   - do **not** wrap values in quotes; and
   - keep this file outside the repo.

   Example:

   .. code-block:: text

      AWS_ACCESS_KEY_ID=<key-id>
      AWS_SECRET_ACCESS_KEY=<secret-key>
      AWS_DEFAULT_REGION=ca-west-1
      S3_ENDPOINT_URL=https://object-arbutus.cloud.computecanada.ca
      S3_BUCKET_NAME=<unique-bucket-name>

   Then load it in a bypassed PowerShell session:

   .. code-block:: powershell

      Set-ExecutionPolicy -Scope Process Bypass -Force
      . $env:USERPROFILE\.config\femic\load-arbutus-env.ps1

   At minimum, the following variables must be set in-shell:

   .. code-block:: bash

      export AWS_ACCESS_KEY_ID=<key-id>
      export AWS_SECRET_ACCESS_KEY=<secret-key>
      export AWS_DEFAULT_REGION=ca-west-1

   Lowest-noise validation order before remote init:

   1. Load the env file.
   2. Confirm required variables are non-empty.
   3. Probe bucket visibility directly.
   4. Only then run ``git annex initremote``.

   Minimal Windows probe sequence:

   .. code-block:: powershell

      Set-ExecutionPolicy -Scope Process Bypass -Force
      . $env:USERPROFILE\.config\femic\load-arbutus-env.ps1
      Get-Item Env:AWS_ACCESS_KEY_ID
      Get-Item Env:AWS_SECRET_ACCESS_KEY
      Get-Item Env:S3_ENDPOINT_URL
      Get-Item Env:S3_BUCKET_NAME

      $probe = Join-Path $env:TEMP 'arbutus-head-bucket.py'
      @'
      import os
      import boto3
      from botocore.config import Config
      from botocore.exceptions import ClientError

      session = boto3.session.Session(
          aws_access_key_id=os.environ['AWS_ACCESS_KEY_ID'],
          aws_secret_access_key=os.environ['AWS_SECRET_ACCESS_KEY'],
          region_name=os.environ['AWS_DEFAULT_REGION'],
      )
      client = session.client(
          's3',
          endpoint_url=os.environ['S3_ENDPOINT_URL'],
          config=Config(s3={'addressing_style': 'path'}),
      )
      for bucket in ['<unique-bucket-name>']:
          try:
              client.head_bucket(Bucket=bucket)
              print(f'head_ok:{bucket}')
          except ClientError as exc:
              print(
                  f"head_error:{bucket}:{exc.response.get('Error', {}).get('Code', 'unknown')}"
              )
      '@ | Set-Content -LiteralPath $probe -Encoding ascii
      .venv\Scripts\python.exe $probe
      Remove-Item $probe -Force

   Initialize the Arbutus S3 special remote only after the bucket probe is
   returning ``head_ok``. Host must be the endpoint hostname, not a ``ria+``
   URL:

   .. code-block:: bash

      git annex initremote arbutus-s3 \
        type=S3 \
        encryption=none \
        bucket=<unique-bucket-name> \
        public=yes \
        publicurl=https://object-arbutus.cloud.computecanada.ca/<unique-bucket-name> \
        host=object-arbutus.cloud.computecanada.ca \
        protocol=https \
        port=80 \
        requeststyle=path \
        autoenable=true \
        chunk=1GiB \
        storageclass=STANDARD

   If ``initremote`` says the bucket already exists and cannot be reused
   because its ``annex-uuid`` belongs to a different special remote:

   - inspect the bucket contents first;
   - if the bucket contains real payload, stop and treat it as an ownership
     conflict; and
   - if the bucket contains only a stale lone ``annex-uuid`` marker from an
     aborted initialization attempt, clear that marker and retry
     ``initremote``.

   Create/reconfigure GitHub sibling and wire publication dependency so one
   push publishes Git metadata and annexed content:

   .. code-block:: bash

      git annex copy --to arbutus-s3 --all
      git config remote.origin.datalad-publish-depends arbutus-s3
      datalad create-sibling-github -d . \
        --github-organization UBC-FRESH \
        --name origin \
        --publish-depends arbutus-s3 \
        --existing reconfigure \
        femic-public-data

      git push origin main
      git push origin git-annex

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

   On Windows, prefer explicit materialization checks for required runtime
   assets. If ``datalad get`` is not the active entry point in the current
   shell, use ``git annex get`` directly and confirm placement with
   ``git annex whereis``:

   .. code-block:: powershell

      git annex enableremote arbutus-s3
      git annex get data/misc.thlb.tif
      git annex whereis data/misc.thlb.tif

Collaborator Workflow (Clone/Get/Update)
----------------------------------------

The mirror repo is linked into FEMIC at
``external/femic-public-data``. Collaborators should use:

.. code-block:: bash

   python -m venv .venv
   . .venv/bin/activate
   python -m pip install --upgrade pip setuptools wheel
   python -m pip install -r requirements-dev.txt
   git submodule update --init --recursive
   git annex version
   datalad --version
   git -C external/femic-public-data annex enableremote arbutus-s3
   datalad get -r external/femic-public-data/data

On Windows, prefer the `.venv`-scoped executable explicitly:

.. code-block:: powershell

   python -m venv .venv
   .venv\Scripts\Activate.ps1
   python -m pip install --upgrade pip setuptools wheel
   python -m pip install -r requirements-dev.txt
   git submodule update --init --recursive
   git annex version
   .venv\Scripts\datalad.exe --version
   git -C external/femic-public-data annex enableremote arbutus-s3
   .venv\Scripts\datalad.exe get -r external/femic-public-data/data

On Linux/macOS:

.. code-block:: bash

   git -C external/femic-public-data annex enableremote arbutus-s3
   datalad get -r external/femic-public-data/data

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
- DataLad installed inside `.venv` (`python -m pip install -r requirements-dev.txt`)
- use `.venv\Scripts\datalad.exe` explicitly if `datalad` is not on `PATH`

Recommended smoke checks on Windows:

.. code-block:: powershell

   git --version
   git annex version
   .venv\Scripts\datalad.exe --version
   git -C external/femic-public-data annex enableremote arbutus-s3
   .venv\Scripts\datalad.exe get -r external/femic-public-data/data
   git -C external/femic-public-data annex version

If you are creating/publishing a new DataLad dataset with an Arbutus special
remote from Windows, the common low-cost failure checks are:

- confirm ``%USERPROFILE%\.config\femic\arbutus.env`` uses plain
  ``KEY=VALUE`` with no quotes;
- use ``Set-ExecutionPolicy -Scope Process Bypass -Force`` before dot-sourcing
  ``load-arbutus-env.ps1`` interactively;
- do not start with ``git annex testremote``; start with a direct bucket probe
  plus the single ``git annex initremote`` attempt; and
- if a cold clone still shows thin placeholders after enable/get, use
  ``git annex get`` for the specific required assets and confirm with
  ``git annex whereis``.

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
- Fresh-clone smoke test can run:
  - ``git annex version``
  - ``git -C external/femic-public-data annex enableremote arbutus-s3``
  - ``datalad get -r external/femic-public-data/data``
- Windows collaborator smoke can run:
  - ``git annex version``
  - ``git -C external/femic-public-data annex enableremote arbutus-s3``
  - ``.venv\Scripts\datalad.exe get -r external/femic-public-data/data``
  - ``git -C external/femic-public-data annex version``
- Windows maintainer bootstrap for a new dataset can run:
  - load local Arbutus env file without quoted values
  - direct ``HeadBucket`` probe returns ``head_ok``
  - ``git annex initremote arbutus-s3 ...`` succeeds
  - ``git annex copy --to arbutus-s3 --all`` succeeds
  - ``git push origin main`` and ``git push origin git-annex`` succeed
  - fresh clone can ``git annex enableremote arbutus-s3`` and materialize required assets
