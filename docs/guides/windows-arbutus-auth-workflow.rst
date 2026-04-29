Windows Arbutus Auth Workflow
=============================

Use this guide when a Windows FEMIC environment needs to publish or materialize
annexed content through an Arbutus S3 special remote.

FEMIC now treats this as a first-class workflow with two commands:

- ``femic prep arbutus-auth-status``
- ``femic prep arbutus-auth-init``

The workflow is user-local. It does not store secrets in the repository.

User-local files
----------------

The canonical Windows file set lives under ``%USERPROFILE%\.config\femic``:

- ``arbutus.env``
  shared credentials and endpoint values only
- ``load-arbutus-env.ps1``
  PowerShell loader for the current shell
- ``load-arbutus-env.sh``
  POSIX-shell loader for compatibility
- ``arbutus-profiles.yaml``
  named bucket/remote profiles
- ``arbutus-status.yaml``
  non-secret known-working marker written only after validation succeeds

Shared env contract
-------------------

For the current workflow, ``arbutus.env`` should contain only:

.. code-block:: text

   AWS_ACCESS_KEY_ID=...
   AWS_SECRET_ACCESS_KEY=...
   AWS_DEFAULT_REGION=...
   S3_ENDPOINT_URL=...

Do not wrap values in quotes.

Legacy compatibility:

- FEMIC still reads ``S3_BUCKET_NAME`` if it already exists in an older local
  env file.
- That legacy key is treated only as a migration bridge for a synthesized
  ``legacy-default`` profile.
- New setups should use ``arbutus-profiles.yaml`` instead.

Profile registry
----------------

``arbutus-profiles.yaml`` holds named bucket/remote combinations. Example:

.. code-block:: yaml

   profiles:
     public-data:
       bucket_name: ubc-fresh-femic-public-data
       remote_name: arbutus-s3
       dataset_path_hint: external/femic-public-data
       note: Known public-data mirror workflow.
     mkrf-instance:
       bucket_name: ubc-fresh-femic-mkrf-instance
       remote_name: arbutus-s3
       dataset_path_hint: external/femic-mkrf-instance
       note: MKRF instance publication workflow.

Status marker
-------------

``arbutus-status.yaml`` is the canonical non-secret marker that a profile is
known-working in the current environment.

It records:

- profile name
- bucket and endpoint
- remote name
- dataset path used for remote validation, if any
- access-key suffix only
- host/user identity
- env-file path and mtime
- loader paths present at validation time
- validation timestamp
- which checks passed

The marker becomes stale when any of these drift:

- host or user changes
- ``arbutus.env`` disappears or its mtime changes
- the selected profile changes
- the current shell is not loaded with the same shared env values
- ``HeadBucket`` fails now
- dataset remote validation was requested and now fails

Fresh bootstrap
---------------

Start with status:

.. code-block:: powershell

   femic prep arbutus-auth-status --profile public-data

If the local scaffolding is missing or stale, run init:

.. code-block:: powershell

   femic prep arbutus-auth-init --profile public-data --bucket ubc-fresh-femic-public-data --dataset external/femic-public-data

``arbutus-auth-init`` will:

- create missing local files under ``%USERPROFILE%\.config\femic``;
- prompt for missing shared values when the session is interactive;
- fail clearly in non-interactive sessions if required values are missing;
- validate ``HeadBucket`` for the selected profile; and
- optionally validate ``git annex enableremote <remote>`` for a dataset path.

Shell loading
-------------

``arbutus-auth-init`` and ``arbutus-auth-status`` can validate using values
they loaded themselves, but a child CLI process cannot inject variables into
the parent shell.

After a successful init, load the current PowerShell session with:

.. code-block:: powershell

   Set-ExecutionPolicy -Scope Process Bypass -Force
   . $env:USERPROFILE\.config\femic\load-arbutus-env.ps1

If execution policy still blocks dot-sourcing, use the inline fallback printed
by the CLI command.

Status checks
-------------

Use ``arbutus-auth-status`` whenever you want to know whether the current
environment is already good enough:

.. code-block:: powershell

   femic prep arbutus-auth-status --profile public-data
   femic prep arbutus-auth-status --profile mkrf-instance --dataset external/femic-mkrf-instance

The command answers:

- do the user-local files exist?
- is the current shell loaded with the shared env values?
- does the selected bucket pass ``HeadBucket``?
- if a dataset is supplied, does ``git annex enableremote`` work?
- is the saved known-working marker current or stale?

Relationship to ``prep validate-case``
--------------------------------------

``femic prep validate-case`` still performs the low-noise Windows Arbutus
checks needed for FEMIC case preflight, but it is no longer the primary auth
bootstrap workflow.

Use:

- ``femic prep arbutus-auth-status`` to inspect current vs stale state; and
- ``femic prep arbutus-auth-init`` to scaffold or refresh the local auth setup.

``validate-case`` now points back to this workflow instead of expecting users
or agents to improvise loader commands and bucket probes by hand.

Instance publication vs public-data mirror
------------------------------------------

The auth workflow is profile-based. One Windows environment can support
multiple Arbutus-backed datasets without rewriting a single-bucket env file.

Examples:

- public-data materialization:

  .. code-block:: powershell

     femic prep arbutus-auth-status --profile public-data --dataset external/femic-public-data
     git -C external/femic-public-data annex enableremote arbutus-s3

- instance publication:

  .. code-block:: powershell

     femic prep arbutus-auth-status --profile mkrf-instance --dataset external/femic-mkrf-instance
     git -C external/femic-mkrf-instance annex enableremote arbutus-s3

This guide describes auth/bootstrap only. For publication order and broader
maintainer workflow, see:

- ``docs/guides/public-data-mirror-runbook.rst``
- ``docs/guides/github-datalad-arbutus-pattern.rst``
